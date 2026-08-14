#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build format research sheets — the pooled, cross-creator unit of analysis.

A `R: [creator]` tab is a scrape. A `F: [format]` tab is a STUDY. One creator's page
usually carries two or three formats, so research organised by creator compares unlike
things; FF1 in `Research Rules` says every tier must be the same format. This regroups
the scraped rows by format and re-tiers them.

Tiering is by BASELINE MULTIPLE, not absolute views (T5): views divided by that
creator's own median. Pooling creators on raw views tiers by audience size instead of
by performance. Gold >= 2.0x own baseline, Bronze <= 0.5x, Silver between.

Input is a map JSON: {"rows": [...], "median": {...}} where each row carries
creator · code · views · bx · tier · fmt · variant · tr · thumb · sb · link.
The classification lives in the map, not in this file — this repo stays mechanism.

Usage:
  python3 format_sheets.py --map /path/to/format_map.json --dry-run
  python3 format_sheets.py --map /path/to/format_map.json
  python3 format_sheets.py --map ... --only SILENT      # rebuild one sheet
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "config" / "characters.json"
WS = json.loads(CONFIG.read_text(encoding="utf-8"))["workspace"]
MASTER_DB_ID = WS["master_db_id"]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import google_sheets as gs  # noqa: E402

BASE_COLS = 11
HEADERS = ["TIER", "BASE×", "CREATOR", "VIEWS", "VARIANT",
           "THUMB", "SCRIPT", "MECHANISM", "STORYBOARD", "LINK", "NOTES"]
WIDTHS = [70, 70, 132, 92, 100, 150, 460, 420, 172, 190, 300]
FRAME_W = 130          # every frame gets its own column after the base block
NCOLS = BASE_COLS      # recomputed per sheet once the frame count is known
FINDINGS_HEADERS = ["DRIVER", "TAKEAWAY & EXPLANATION", "GOLD EVIDENCE", "BRONZE EVIDENCE"]
N_FINDINGS = 12
H_DATA = 200

INK = {"red": 0.169, "green": 0.188, "blue": 0.220}
PAPER = {"red": 1, "green": 1, "blue": 1}
TEXT = {"red": 0.11, "green": 0.12, "blue": 0.13}
MUTE = {"red": 0.42, "green": 0.45, "blue": 0.50}
HEAD = {"red": 0.90, "green": 0.91, "blue": 0.93}
TIER_BG = {
    "Gold":   {"red": 1.00, "green": 0.95, "blue": 0.80},
    "Silver": {"red": 0.94, "green": 0.94, "blue": 0.94},
    "Bronze": {"red": 0.99, "green": 0.90, "blue": 0.80},
}
VAR_BG = {
    "PRIMARY":   PAPER,
    "EXPLAINER": {"red": 0.949, "green": 0.910, "blue": 0.976},
    "NEWS":      {"red": 0.859, "green": 0.957, "blue": 0.969},
}

# Format key -> (tab title, one-line definition shown in the title banner)
FORMATS = {
    "SILENT": ("F: Silent Build Demo",
               "No speech. Trending audio, ONE static text overlay carrying the whole premise, "
               "and a screen recording of the artifact being built or revealed. CTA is a text "
               "overlay, never spoken."),
    "SHOWCASE": ("F: Agent System Showcase",
                 "Continuous VO over a dashboard or org chart of a system the creator built. "
                 "Enumerates the parts, one by one. DESCRIBES, never instructs — the viewer is "
                 "not asked to follow along.  ·  PRIMARY = the system is on screen.  "
                 "EXPLAINER = the same subject argued as a concept, with nothing shown."),
    "AFFILIATE": ("F: Affiliate Conversion",
                  "Panic or news hook on a named incumbent, then the replacement product, a "
                  "capability stack, ONE live micro-proof, and a comment gate for the link. The "
                  "only format here that ends in a transaction.  ·  PRIMARY = the full machine.  "
                  "NEWS = the hook alone, no gate."),
    "TUTORIAL": ("F: Narrated Tutorial",
                 "Imperative second-person steps the viewer can follow — go here, paste this, "
                 "then that. Numbered tool and skill lists are common. Usually comment-gated for "
                 "the prompt or the guide."),
}
TIER_ORDER = {"Gold": 0, "Silver": 1, "Bronze": 2}


def cell(v, bold=False, size=9, color=None, bg=None, wrap="CLIP", va="TOP", ha="LEFT"):
    s = "" if v is None else str(v)
    key = "formulaValue" if s.startswith("=") else "stringValue"
    return {"userEnteredValue": {key: s},
            "userEnteredFormat": {"backgroundColor": bg or PAPER, "horizontalAlignment": ha,
                                  "verticalAlignment": va, "wrapStrategy": wrap,
                                  "textFormat": {"bold": bold, "fontSize": size,
                                                 "foregroundColor": color or TEXT}}}


def img(file_id):
    return f'=IMAGE("https://drive.google.com/thumbnail?id={file_id}&sz=w1000", 1)'


def build_rows(fmt_key, rows, frames=None, mech=None, findings=None):
    """frames: {code: [drive_id, ...]}   mech: {code: text}   findings: [[4 cells], ...]"""
    frames, mech, findings = frames or {}, mech or {}, findings or []
    title, definition = FORMATS[fmt_key]
    data = sorted(rows, key=lambda r: (TIER_ORDER[r["tier"]], -r["bx"]))
    max_f = max([len(frames.get(r["code"], [])) for r in data] + [0])
    ncols = BASE_COLS + max_f
    pad = lambda vals: vals + [cell("") for _ in range(ncols - len(vals))]

    out = []
    banner = [cell(f"{title[3:].upper()}  —  {definition}", bold=True, size=10,
                   color=PAPER, bg=INK, wrap="WRAP", va="MIDDLE")]
    banner += [cell("", bg=INK) for _ in range(ncols - 1)]
    out.append({"values": banner})
    hdr = [cell(h, bold=True, size=10, color=PAPER, bg=INK, va="MIDDLE") for h in HEADERS]
    hdr += [cell(f"F{i+1}", bold=True, size=9, color=PAPER, bg=INK, va="MIDDLE", ha="CENTER")
            for i in range(max_f)]
    out.append({"values": hdr})

    for r in data:
        tb = TIER_BG[r["tier"]]
        vals = [
            cell(r["tier"], bold=True, bg=tb, va="MIDDLE"),
            cell(f"{r['bx']:.2f}×", bold=True, bg=tb, va="MIDDLE", ha="CENTER"),
            cell(r["creator"], bg=tb, va="MIDDLE"),
            cell(f"{r['views']:,}", bg=tb, va="MIDDLE", ha="RIGHT"),
            cell(r["variant"], bold=r["variant"] != "PRIMARY",
                 bg=VAR_BG.get(r["variant"], PAPER), va="MIDDLE"),
            cell(r["thumb"]),
            cell(r["tr"] or "— no speech —", wrap="WRAP", color=None if r["tr"] else MUTE),
            cell(mech.get(r["code"], ""), wrap="WRAP"),
            cell(r["sb"]),
            cell(f'=HYPERLINK("{r["link"]}","{r["code"]}")', wrap="WRAP", color=MUTE),
            cell("", wrap="WRAP"),
        ]
        vals += [cell(img(f)) for f in frames.get(r["code"], [])]
        out.append({"values": pad(vals)})

    out.append({"values": pad([cell("")])})
    fb = [cell("FINDINGS  —  one row per validated driver. Tactic + EOV + why it drives "
               "retention. P1–P4. Nothing lands here before the driver screen.",
               bold=True, size=10, color=PAPER, bg=INK, wrap="WRAP", va="MIDDLE")]
    fb += [cell("", bg=INK) for _ in range(ncols - 1)]
    out.append({"values": fb})
    out.append({"values": pad([cell(h, bold=True, bg=HEAD, va="MIDDLE")
                               for h in FINDINGS_HEADERS])})
    for i in range(max(N_FINDINGS, len(findings))):
        row = findings[i] if i < len(findings) else ["", "", "", ""]
        out.append({"values": pad([cell(c, wrap="WRAP") for c in row])})
    return out, len(data), ncols, max_f


def write_tab(svc, title, rows, n_data, ncols, max_f, replace):
    info = svc.spreadsheets().get(spreadsheetId=MASTER_DB_ID).execute()
    existing = {s["properties"]["title"]: s["properties"]["sheetId"] for s in info["sheets"]}
    if title in existing:
        if not replace:
            sys.exit(f"'{title}' exists — pass --replace to rebuild it.")
        svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={
            "requests": [{"deleteSheet": {"sheetId": existing[title]}}]}).execute()

    n = len(rows)
    r = svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={"requests": [
        {"addSheet": {"properties": {
            "title": title,
            # no frozen columns: the banner rows merge across the full width, and
            # Sheets refuses a merge that spans the frozen/non-frozen boundary.
            "gridProperties": {"rowCount": n + 10, "columnCount": ncols,
                               "frozenRowCount": 2}}}}]}).execute()
    gid = r["replies"][0]["addSheet"]["properties"]["sheetId"]

    # chunked — a row of 40 =IMAGE() formulas x 60 rows exceeds one request
    for i in range(0, n, 20):
        svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={"requests": [
            {"updateCells": {"rows": rows[i:i + 20],
                             "fields": "userEnteredValue,userEnteredFormat",
                             "start": {"sheetId": gid, "rowIndex": i,
                                       "columnIndex": 0}}}]}).execute()

    reqs = [{"mergeCells": {"range": {"sheetId": gid, "startRowIndex": i, "endRowIndex": i + 1,
                                      "startColumnIndex": 0, "endColumnIndex": ncols},
                            "mergeType": "MERGE_ALL"}} for i in (0, n_data + 3)]
    reqs += [{"updateDimensionProperties": {
        "range": {"sheetId": gid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}} for i, px in enumerate(WIDTHS)]
    if max_f:
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": gid, "dimension": "COLUMNS",
                      "startIndex": BASE_COLS, "endIndex": BASE_COLS + max_f},
            "properties": {"pixelSize": FRAME_W}, "fields": "pixelSize"}})
    reqs += [
        {"updateDimensionProperties": {
            "range": {"sheetId": gid, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 34}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": gid, "dimension": "ROWS", "startIndex": 2,
                      "endIndex": 2 + n_data},
            "properties": {"pixelSize": H_DATA}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": gid, "dimension": "ROWS", "startIndex": n_data + 3,
                      "endIndex": n_data + 4},
            "properties": {"pixelSize": 34}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": gid, "dimension": "ROWS", "startIndex": n_data + 5,
                      "endIndex": n_data + 5 + N_FINDINGS},
            "properties": {"pixelSize": 120}, "fields": "pixelSize"}},
    ]
    svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID,
                                   body={"requests": reqs}).execute()
    return n_data


def main():
    ap = argparse.ArgumentParser(description="Build pooled format research sheets")
    ap.add_argument("--map", required=True, type=Path)
    ap.add_argument("--frames", type=Path, help="{code: [drive_id,...]} json")
    ap.add_argument("--mechanism", type=Path, help="{code: text} json — the MECHANISM column")
    ap.add_argument("--findings", type=Path, help="{fmt: [[driver,takeaway,gold,bronze],…]}")
    ap.add_argument("--only", help="build a single format key")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = json.loads(a.map.read_text(encoding="utf-8"))["rows"]
    frames = json.loads(a.frames.read_text(encoding="utf-8")) if a.frames else {}
    mech = json.loads(a.mechanism.read_text(encoding="utf-8")) if a.mechanism else {}
    finds = json.loads(a.findings.read_text(encoding="utf-8")) if a.findings else {}
    keys = [a.only] if a.only else list(FORMATS)
    svc = None if a.dry_run else gs.get_sheets_service()

    for k in keys:
        sel = [r for r in rows if r["fmt"] == k]
        if not sel:
            print(f"⚠️  {k}: no rows, skipped")
            continue
        built, n_data, ncols, max_f = build_rows(k, sel, frames, mech, finds.get(k))
        title = FORMATS[k][0]
        tiers = {t: sum(1 for r in sel if r["tier"] == t) for t in ("Gold", "Silver", "Bronze")}
        line = (f"{title:<28} {n_data:>3} videos  "
                f"G{tiers['Gold']}/S{tiers['Silver']}/B{tiers['Bronze']}  "
                f"frames≤{max_f}  cols={ncols}  findings={len(finds.get(k, []))}")
        if a.dry_run:
            print("[dry-run] " + line)
            continue
        write_tab(svc, title, built, n_data, ncols, max_f, a.replace)
        print("✅ " + line)


if __name__ == "__main__":
    main()
