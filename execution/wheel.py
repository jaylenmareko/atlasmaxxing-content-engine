#!/usr/bin/env python3
"""
The wheel — returns N script *routes* for a video being recreated.

A route is not a script. It is the set of choices a script gets written against:

    STYLE (weights the pool)  x  FRAMEWORK  x  HOOK  x  STRUCTURE
      + TECHNIQUE (stacked, 2-3)  + PSYCHOLOGY (the why)  x  CHANGE LEVEL

Everything it picks from lives in the SCRIPTING MATRIX `LIBRARY` tab, one row per thing.
Nothing character-specific is in this file. The character comes from the canvas sheet.

Axes, and why they are separate:
  FRAMEWORK   what the video argues, in order      -> choose ONE   (the wheel's main spin)
  HOOK        the first three seconds              -> choose ONE   (respin alone = hook mode)
  STRUCTURE   beat map, clip count, length         -> choose ONE
  TECHNIQUE   line-level moves                     -> STACK 2-3    (not a choice-between)
  PSYCHOLOGY  the underlying driver                -> ONE, as rationale, never a constraint
  RULE        vetoes                               -> ALL of them, always

Style is a WEIGHTING, not a filter. Green screen is not 100% different from AI avatar;
it constrains delivery (segmentation, CTA placement, composited vs staged) and barely
touches the words. So a high-performing route is never excluded by style, only demoted.

Usage:
    python3 wheel.py --n 14 --style AI_AVATAR --type GROWTH --seed 820
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import google_sheets as gs  # noqa: E402

# Source of truth moved into the Master Video DB on 2026-07-30, at the user's direction:
# the rules have to be visible and editable in the same file as the work. The old
# SCRIPTING MATRIX -> LIBRARY tab is a superseded copy; do not read it.
CONFIG = Path(__file__).resolve().parent.parent / "config" / "characters.json"
MATRIX_ID = json.loads(CONFIG.read_text())["workspace"]["master_db_id"]
LIBRARY_TAB = "Script Rules"

# Style weights delivery, not words. A route is demoted, never dropped.
STYLE_WEIGHTS = {
    "AI_AVATAR": {
        # avatar holds frame and talks; long argument arcs carry, heavy staging does not
        "structure": {"S1": 1.3, "S2": 1.3, "S3": 0.8, "S4": 0.6, "S5": 1.1},
        "technique": {"T1": 1.2, "T2": 1.2, "T3": 1.0, "T4": 1.1, "T5": 0.5, "T6": 1.3, "T7": 1.2, "T8": 1.2},
    },
    "GREEN_SCREEN": {
        "structure": {"S1": 1.3, "S2": 1.0, "S3": 1.0, "S4": 0.7, "S5": 1.2},
        "technique": {"T1": 1.1, "T2": 1.3, "T3": 0.9, "T4": 1.1, "T5": 0.6, "T6": 1.2, "T7": 1.1, "T8": 0.8},
    },
    "TRANSFORMATION": {
        "structure": {"S1": 0.8, "S2": 0.9, "S3": 1.6, "S4": 0.8, "S5": 0.7},
        "technique": {"T1": 1.2, "T2": 0.8, "T3": 1.0, "T4": 1.4, "T5": 0.7, "T6": 1.0, "T7": 0.9, "T8": 0.9},
    },
    "SKITS": {
        "structure": {"S1": 0.7, "S2": 1.0, "S3": 0.9, "S4": 1.6, "S5": 1.0},
        "technique": {"T1": 0.9, "T2": 1.3, "T3": 1.2, "T4": 0.9, "T5": 0.5, "T6": 1.0, "T7": 1.0, "T8": 0.8},
    },
}

# Measured against the ORIGINAL script being recreated, not against each other.
# KEEP-FIRST naming, per the user 2026-07-30: the first number is what STAYS.
# The percentages are a figure of speech. What matters is which parts are allowed to move.
CHANGE_LEVELS = {
    "80-20": {
        "keep": "everything",
        "move": "the hook, and the CTA. Nothing else.",
        "invariant": "The recipe is frozen. Same ingredients, same amounts, same order, same timing, "
                     "same beat sequence. If an ingredient changed, this is not an 80-20.",
    },
    "20-80": {
        "keep": "the subject only",
        "move": "the framework, the mechanism, the structure, the proof",
        "invariant": "Still the same subject and the same character. This is where a genuinely new "
                     "framework goes, not a reworded version of the original.",
    },
}

# Default mix. The user wants mostly hook-and-CTA respins, with a few real swings.
DEFAULT_MIX = {"80-20": 9, "20-80": 5}


def load_library(spreadsheet_id=MATRIX_ID, tab=LIBRARY_TAB):
    """Read the flat LIBRARY tab and bucket it by KIND."""
    rows = gs.read_sheet(spreadsheet_id, f"{tab}!A1:I400")
    header, data = rows[0], rows[1:]
    out = {}
    for r in data:
        r = (r + [""] * len(header))[: len(header)]
        rec = dict(zip(header, r))
        if not rec["ID"].strip():
            continue
        out.setdefault(rec["KIND"], []).append(rec)
    return out


def _weighted_cycle(items, weights, n, rng):
    """
    Deal n picks so every item appears before any repeats (coverage first),
    with weights deciding the order inside each pass and who gets the extras.
    """
    picks, pool = [], []
    while len(picks) < n:
        if not pool:
            pool = list(items)
            # weight only affects ordering within the pass, so nothing is ever excluded
            pool.sort(key=lambda it: -rng.random() ** (1.0 / max(weights.get(it["ID"], 1.0), 0.01)))
        picks.append(pool.pop(0))
    return picks


def spin(lib, n=14, style="AI_AVATAR", vtype="GROWTH", seed=None, techniques_per=2, mix=None):
    """Return n routes. Coverage-first: no framework repeats until all are used."""
    rng = random.Random(seed)
    w = STYLE_WEIGHTS.get(style, {})
    sw, tw = w.get("structure", {}), w.get("technique", {})

    # A framework that declares the opposite TYPE is dropped, not adapted. FW11 is a
    # 90-180s product engine; drawing it for a growth video produced a script that had
    # to be rewritten past recognition, which defeats the point of picking it.
    def type_ok(rec):
        t = (rec.get("TYPE") or "").strip().upper()
        return t in ("", "—", "-", "BOTH", vtype)

    frameworks = [f for f in lib.get("FRAMEWORK", []) if type_ok(f)]
    hooks = lib.get("HOOK", [])
    structures = lib.get("STRUCTURE", [])
    techniques = lib.get("TECHNIQUE", [])
    psych = lib.get("PSYCHOLOGY", [])

    fw = _weighted_cycle(frameworks, {}, n, rng)
    hk = _weighted_cycle(hooks, {}, n, rng)
    st = _weighted_cycle(structures, sw, n, rng)

    # Build the change-level deal up front so the ratio is exact, not alternating.
    mix = mix or DEFAULT_MIX
    total = sum(mix.values())
    levels = []
    for lvl, count in mix.items():
        levels += [lvl] * round(count * n / total)
    levels = (levels + ["80-20"] * n)[:n]

    routes = []
    for i in range(n):
        tk = _weighted_cycle(techniques, tw, techniques_per * 2, rng)
        seen, chosen = set(), []
        for t in tk:
            if t["ID"] not in seen:
                seen.add(t["ID"])
                chosen.append(t)
            if len(chosen) == techniques_per:
                break
        routes.append(
            {
                "n": i + 1,
                "style": style,
                "type": vtype,
                "framework": fw[i],
                "hook": hk[i],
                "structure": st[i],
                "techniques": chosen,
                "psychology": psych[i % len(psych)] if psych else None,
                "change_level": levels[i],
                "brief": CHANGE_LEVELS[levels[i]],
            }
        )
    return routes


def render(routes, rules):
    """Human-readable route sheet — the 'why' column behind every script."""
    lines = [f"{len(routes)} routes\n"]
    for r in routes:
        lines.append(
            f"#{r['n']:>2}  [{r['change_level']}]  {r['framework']['ID']} {r['framework']['NAME']}\n"
            f"      hook      {r['hook']['ID']} {r['hook']['NAME']}\n"
            f"      structure {r['structure']['ID']} {r['structure']['NAME']}\n"
            f"      technique {', '.join(t['ID'] + ' ' + t['NAME'] for t in r['techniques'])}\n"
            f"      driver    {r['psychology']['NAME'] if r['psychology'] else '-'}\n"
        )
    lines.append(f"\n{len(rules)} rules apply to every route (vetoes, not choices).")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=14)
    ap.add_argument("--style", default="AI_AVATAR", choices=sorted(STYLE_WEIGHTS))
    ap.add_argument("--type", dest="vtype", default="GROWTH", choices=["GROWTH", "PRODUCT"])
    ap.add_argument("--seed", type=int, default=None, help="row number makes a good seed")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    lib = load_library()
    routes = spin(lib, n=a.n, style=a.style, vtype=a.vtype, seed=a.seed)
    if a.json:
        print(json.dumps(routes, ensure_ascii=False, indent=2))
    else:
        print(render(routes, lib.get("RULE", [])))


if __name__ == "__main__":
    main()
