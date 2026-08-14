#!/usr/bin/env python3
"""GSB tiering — apply the research math rules to a SortFeed export.

Implements research/rules.md:
  - Clustering Rule: consecutive-video view ratio > 2x = tier boundary
  - Tiers: Gold (top cluster) / Silver (baseline) / Bronze (below median)
  - 10x Variance Rule: warn when a tier's high/low spread exceeds 10x
  - Likes-to-views filter: flag rows under 1% (likely boosted)
  - Max 10 videos per tier, sorted by views

Input: CSV exported from SortFeed (or any CSV with a views column).
Column names are auto-detected (anything containing 'view', 'like', 'url'/
'link', 'title'/'caption'); override with --views-col etc. if needed.

Usage:
  python3 gsb_tier.py --csv ~/Downloads/creator_export.csv
  python3 gsb_tier.py --csv export.csv --json    # machine-readable output
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path


def parse_number(s: str) -> float | None:
    if s is None:
        return None
    s = str(s).strip().replace(",", "")
    if not s:
        return None
    m = re.fullmatch(r"([\d.]+)\s*([KkMmBb]?)", s)
    if not m:
        return None
    val = float(m.group(1))
    mult = {"k": 1e3, "m": 1e6, "b": 1e9}.get(m.group(2).lower(), 1)
    return val * mult


def find_col(headers: list[str], *needles: str) -> int | None:
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(n in hl for n in needles):
            return i
    return None


def load_csv(path: Path, views_col=None, likes_col=None, link_col=None, title_col=None):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = [r for r in reader if any(c.strip() for c in r)]
    headers = rows[0]
    vi = views_col if views_col is not None else find_col(headers, "view", "play")
    li = likes_col if likes_col is not None else find_col(headers, "like")
    ki = link_col if link_col is not None else find_col(headers, "url", "link", "reel", "video")
    ti = title_col if title_col is not None else find_col(headers, "title", "caption", "desc")
    if vi is None:
        sys.exit(f"Couldn't find a views column in: {headers} — use --views-col")

    videos = []
    for r in rows[1:]:
        views = parse_number(r[vi]) if vi < len(r) else None
        if not views:
            continue
        videos.append({
            "views": views,
            "likes": parse_number(r[li]) if li is not None and li < len(r) else None,
            "link": r[ki].strip() if ki is not None and ki < len(r) else "",
            "title": (r[ti].strip()[:80] if ti is not None and ti < len(r) else ""),
        })
    return videos


def tier(videos: list[dict]) -> dict:
    vids = sorted(videos, key=lambda v: -v["views"])
    n = len(vids)
    if n < 6:
        sys.exit(f"Only {n} usable videos — need more for meaningful tiers (5+ per tier ideal).")

    # Engagement flag (likes/views < 1% = likely boosted)
    for v in vids:
        v["flag"] = ""
        if v["likes"] is not None and v["views"] and (v["likes"] / v["views"]) < 0.01:
            v["flag"] = "⚠️ likes/views < 1% — possibly boosted"

    # Clustering Rule: boundary where consecutive ratio > 2x
    boundaries = []
    for i in range(n - 1):
        if vids[i]["views"] / max(vids[i + 1]["views"], 1) > 2:
            boundaries.append(i + 1)

    clusters = []
    start = 0
    for b in boundaries + [n]:
        clusters.append(vids[start:b])
        start = b

    if len(clusters) >= 3:
        gold = clusters[0]
        # Gold needs ≥3 videos — absorb following clusters until it does
        ci = 1
        while len(gold) < 3 and ci < len(clusters) - 1:
            gold = gold + clusters[ci]
            ci += 1
        bronze = clusters[-1]
        silver = [v for c in clusters[ci:-1] for v in c]
        method = f"natural gaps ({len(boundaries)} boundaries)"
    else:
        # Fallback: 33rd/66th percentile split
        g_end, s_end = n // 3, (2 * n) // 3
        gold, silver, bronze = vids[:g_end], vids[g_end:s_end], vids[s_end:]
        method = "percentile fallback (no clear 2x gaps)"

    out = {"method": method, "total": n, "tiers": {}}
    for name, group in (("GOLD", gold), ("SILVER", silver), ("BRONZE", bronze)):
        if not group:
            out["tiers"][name] = {"videos": [], "note": "empty"}
            continue
        hi, lo = group[0]["views"], group[-1]["views"]
        note = ""
        if lo and hi / lo > 10:
            note = f"⚠️ 10x variance rule violated ({hi/lo:.1f}x) — consider re-splitting"
        out["tiers"][name] = {
            "count": len(group),
            "views_range": [int(hi), int(lo)],
            "note": note,
            "videos": [{"views": int(v["views"]), "title": v["title"],
                        "link": v["link"], "flag": v["flag"]}
                       for v in group[:10]],
            "dropped_over_cap": max(0, len(group) - 10),
        }
    return out


def print_table(result: dict):
    print(f"Tiering method: {result['method']}  ({result['total']} videos)\n")
    for name, t in result["tiers"].items():
        if not t.get("videos"):
            print(f"{name}: empty\n")
            continue
        rng = t["views_range"]
        print(f"{name} — {t['count']} videos ({rng[0]:,} → {rng[1]:,} views) {t['note']}")
        for v in t["videos"]:
            flag = f"  {v['flag']}" if v["flag"] else ""
            print(f"  {v['views']:>12,}  {v['title'] or v['link']}{flag}")
        if t["dropped_over_cap"]:
            print(f"  (+{t['dropped_over_cap']} more past the 10-video cap)")
        print()


def mode_center(views: list[float]) -> float:
    """The baseline (Silver) per the book is the MODE — the most frequent
    view level. For continuous view counts, find the densest bin in log
    space and return its center."""
    import math
    logs = sorted(math.log10(v) for v in views if v > 0)
    if not logs:
        return 0
    bins = 24
    lo, hi = logs[0], logs[-1]
    width = (hi - lo) / bins or 1
    counts = [0] * bins
    for x in logs:
        counts[min(int((x - lo) / width), bins - 1)] += 1
    peak = counts.index(max(counts))
    return 10 ** (lo + (peak + 0.5) * width)


def pick_tiers(videos: list[dict], n: int, kill_engagement: bool = True) -> dict:
    """Research selection mode: kill <1% engagement, then top N (Gold),
    N closest to the MODE (Silver baseline, per the book), bottom N (Bronze).

    kill_engagement=False skips the likes/views kill — use it when the export's
    likes column is unreliable (e.g. SortFeed returns a constant garbage value),
    so tiers are formed by views alone."""
    vids = sorted(videos, key=lambda v: -v["views"])
    killed = [v for v in vids
              if kill_engagement and v["likes"] is not None and v["views"]
              and (v["likes"] / v["views"]) < 0.01]
    alive = [v for v in vids if v not in killed]
    m = len(alive)
    if m < 3 * n:
        print(f"⚠️  only {m} survivors — tiers will overlap less cleanly")

    gold = alive[:n]
    bronze = alive[-n:]
    # Silver = the n videos closest to the mode, excluding gold/bronze picks
    center = mode_center([v["views"] for v in alive])
    middle = [v for v in alive if v not in gold and v not in bronze]
    silver_sorted = sorted(middle, key=lambda v: abs(v["views"] - center))
    silver = silver_sorted[:n]
    silver.sort(key=lambda v: -v["views"])

    # Alternates per tier — backfill when a pick's video is dead/blocked
    return {
        "killed_engagement": len(killed),
        "survivors": m,
        "silver_mode_center": int(center),
        "GOLD": gold,
        "SILVER": silver,
        "BRONZE": bronze,
        "ALT": {"GOLD": alive[n:n + 3],
                "SILVER": silver_sorted[n:n + 3],
                "BRONZE": alive[-(n + 3):-n][::-1]},
    }


def print_picks(sel: dict):
    print(f"Engagement kill (<1% likes/views): {sel['killed_engagement']} removed, "
          f"{sel['survivors']} survive\n")
    for name in ("GOLD", "SILVER", "BRONZE"):
        group = sel[name]
        print(f"{name} — {len(group)} picks ({int(group[0]['views']):,} → {int(group[-1]['views']):,} views)")
        for v in group:
            print(f"  {int(v['views']):>12,}  {v['link']}")
        print()


def main():
    ap = argparse.ArgumentParser(description="GSB tiering per research/rules.md")
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--views-col", type=int, help="0-based views column override")
    ap.add_argument("--likes-col", type=int)
    ap.add_argument("--link-col", type=int)
    ap.add_argument("--title-col", type=int)
    ap.add_argument("--pick", type=int, metavar="N",
                    help="Research selection: top N / median-centered N / bottom N after engagement kill")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    videos = load_csv(args.csv, args.views_col, args.likes_col, args.link_col, args.title_col)
    if args.pick:
        sel = pick_tiers(videos, args.pick)
        if args.json:
            out = {k: (v if isinstance(v, int) else
                       [{"views": int(x["views"]), "link": x["link"]} for x in v])
                   for k, v in sel.items()}
            print(json.dumps(out, indent=2))
        else:
            print_picks(sel)
        return
    result = tier(videos)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_table(result)


if __name__ == "__main__":
    main()
