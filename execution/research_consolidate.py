#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consolidate the per-format `F:` sheets into ONE `Format Research` reference tab.

Why one tab: the four format sheets are a study. This is a LIBRARY — the thing a
recreation points at. `recreate <row>` addresses the Master DB `Database` tab by row
number; this tab gives format references the same addressing. So the hard requirement
is one video per row, contiguous, with the sheet row visible in column A.

Layout:
  row 1        title banner
  row 2        headers
  rows 3..N    one video per row, no banners in between — FORMAT is colour-coded
               instead, so grouping stays visible without breaking row addressing
  below        the driver findings from all four studies, grouped by format

Ordering is the recommended test order (Silent · Affiliate · Showcase · Tutorial),
then tier, then baseline multiple. Column A is =ROW() so it can never drift.

Nothing brand-specific lives here — content comes from the map/frames/findings JSON.

Usage:
  python3 research_consolidate.py --map m.json --frames f.json --mechanism me.json \
      --findings fi.json [--replace] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "config" / "characters.json"
WS = json.loads(CONFIG.read_text())["workspace"]
MASTER_DB_ID = WS["master_db_id"]
TAB = "Format Research"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import google_sheets as gs  # noqa: E402

HEADERS = ["ROW", "FORMAT", "TIER", "BASE×", "VIEWS", "CREATOR", "VARIANT", "PICK",
           "THUMB", "SCRIPT", "MECHANISM", "STORYBOARD", "LINK", "NOTES"]
WIDTHS = [56, 132, 74, 68, 92, 128, 96, 64, 150, 430, 410, 168, 176, 280]
BASE_COLS = len(HEADERS)
FRAME_W = 130
H_DATA = 200

INK = {"red": 0.169, "green": 0.188, "blue": 0.220}
PAPER = {"red": 1, "green": 1, "blue": 1}
TEXT = {"red": 0.11, "green": 0.12, "blue": 0.13}
MUTE = {"red": 0.42, "green": 0.45, "blue": 0.50}
HEAD = {"red": 0.90, "green": 0.91, "blue": 0.93}

# Test order, not alphabetical — this is the recommended sequence to shoot.
ORDER = ["SILENT", "AFFILIATE", "SHOWCASE", "TUTORIAL"]
FMT_LABEL = {
    "SILENT": "SILENT BUILD DEMO",
    "AFFILIATE": "AFFILIATE CONVERSION",
    "SHOWCASE": "AGENT SYSTEM SHOWCASE",
    "TUTORIAL": "NARRATED TUTORIAL",
}
FMT_BG = {
    "SILENT":    {"red": 0.867, "green": 0.910, "blue": 0.988},
    "AFFILIATE": {"red": 0.988, "green": 0.878, "blue": 0.878},
    "SHOWCASE":  {"red": 0.898, "green": 0.957, "blue": 0.910},
    "TUTORIAL":  {"red": 0.988, "green": 0.969, "blue": 0.847},
}
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
TIER_ORDER = {"Gold": 0, "Silver": 1, "Bronze": 2}
FINDINGS_HEADERS = ["DRIVER", "TAKEAWAY & EXPLANATION", "GOLD EVIDENCE", "BRONZE EVIDENCE"]


def cell(v, bold=False, size=9, color=None, bg=None, wrap="CLIP", va="TOP", ha="LEFT"):
    s = "" if v is None else str(v)
    key = "formulaValue" if s.startswith("=") else "stringValue"
    return {"userEnteredValue": {key: s},
            "userEnteredFormat": {"backgroundColor": bg or PAPER, "horizontalAlignment": ha,
                                  "verticalAlignment": va, "wrapStrategy": wrap,
                                  "textFormat": {"bold": bold, "fontSize": size,
                                                 "foregroundColor": color or TEXT}}}


def img(fid):
    return f'=IMAGE("https://drive.google.com/thumbnail?id={fid}&sz=w1000", 1)'


def build(rows, frames, mech, findings):
    data = sorted(rows, key=lambda r: (ORDER.index(r["fmt"]) if r["fmt"] in ORDER else 9,
                                       TIER_ORDER[r["tier"]], -r["bx"]))
    max_f = max([len(frames.get(r["code"], [])) for r in data] + [0])
    ncols = BASE_COLS + max_f
    pad = lambda v: v + [cell("") for _ in range(ncols - len(v))]

    out = []
    b = [cell("FORMAT RESEARCH  —  every reference video, one per row. Column A is the row to "
              "recreate from. Colour = format. Sorted in test order: Silent Build Demo · "
              "Affiliate Conversion · Agent System Showcase · Narrated Tutorial.",
              bold=True, size=10, color=PAPER, bg=INK, wrap="WRAP", va="MIDDLE")]
    out.append({"values": b + [cell("", bg=INK) for _ in range(ncols - 1)]})
    hdr = [cell(h, bold=True, size=10, color=PAPER, bg=INK, va="MIDDLE") for h in HEADERS]
    hdr += [cell(f"F{i+1}", bold=True, color=PAPER, bg=INK, va="MIDDLE", ha="CENTER")
            for i in range(max_f)]
    out.append({"values": hdr})

    for r in data:
        fb, tb = FMT_BG.get(r["fmt"], PAPER), TIER_BG[r["tier"]]
        vals = [
            cell("=ROW()", bold=True, bg=fb, va="MIDDLE", ha="CENTER"),
            cell(FMT_LABEL.get(r["fmt"], r["fmt"]), bold=True, bg=fb, va="MIDDLE"),
            cell(r["tier"], bold=True, bg=tb, va="MIDDLE"),
            cell(f"{r['bx']:.2f}×", bg=tb, va="MIDDLE", ha="CENTER"),
            cell(f"{r['views']:,}", bg=tb, va="MIDDLE", ha="RIGHT"),
            cell(r["creator"], va="MIDDLE"),
            cell(r["variant"], bold=r["variant"] != "PRIMARY",
                 bg=VAR_BG.get(r["variant"], PAPER), va="MIDDLE"),
            cell("", bg=PAPER, va="MIDDLE", ha="CENTER"),
            cell(r["thumb"]),
            cell(r["tr"] or "— no speech —", wrap="WRAP", color=None if r["tr"] else MUTE),
            cell(mech.get(r["code"], ""), wrap="WRAP"),
            cell(r["sb"]),
            cell(f'=HYPERLINK("{r["link"]}","{r["code"]}")', wrap="WRAP", color=MUTE),
            cell("", wrap="WRAP"),
        ]
        vals += [cell(img(f)) for f in frames.get(r["code"], [])]
        out.append({"values": pad(vals)})

    n_data = len(data)
    out.append({"values": pad([cell("")])})
    fb = [cell("DRIVERS  —  what separates Gold from Bronze in each format. Score a script "
               "against these before you shoot it.",
               bold=True, size=10, color=PAPER, bg=INK, wrap="WRAP", va="MIDDLE")]
    out.append({"values": fb + [cell("", bg=INK) for _ in range(ncols - 1)]})

    marks = []
    for k in ORDER:
        rowsf = findings.get(k) or []
        if not rowsf:
            continue
        marks.append(len(out))
        lab = [cell(FMT_LABEL[k], bold=True, size=10, bg=FMT_BG[k], va="MIDDLE")]
        out.append({"values": pad(lab)})
        out.append({"values": pad([cell(h, bold=True, bg=HEAD, va="MIDDLE")
                                   for h in FINDINGS_HEADERS])})
        for f in rowsf:
            out.append({"values": pad([cell(c, wrap="WRAP") for c in f])})
    return out, n_data, ncols, max_f, marks


def main():
    ap = argparse.ArgumentParser(description="Consolidate the F: sheets into one library tab")
    ap.add_argument("--map", required=True, type=Path)
    ap.add_argument("--frames", type=Path)
    ap.add_argument("--mechanism", type=Path)
    ap.add_argument("--findings", type=Path)
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = json.loads(a.map.read_text())["rows"]
    frames = json.loads(a.frames.read_text()) if a.frames else {}
    mech = json.loads(a.mechanism.read_text()) if a.mechanism else {}
    finds = json.loads(a.findings.read_text()) if a.findings else {}

    built, n_data, ncols, max_f, marks = build(rows, frames, mech, finds)
    counts = {k: sum(1 for r in rows if r["fmt"] == k) for k in ORDER}
    line = (f"{TAB}: {n_data} videos in rows 3–{n_data + 2} · {ncols} cols · frames≤{max_f} · "
            + " · ".join(f"{FMT_LABEL[k]} {v}" for k, v in counts.items()))
    if a.dry_run:
        print("[dry-run] " + line)
        return

    svc = gs.get_sheets_service()
    info = svc.spreadsheets().get(spreadsheetId=MASTER_DB_ID).execute()
    existing = {s["properties"]["title"]: s["properties"]["sheetId"] for s in info["sheets"]}
    if TAB in existing:
        if not a.replace:
            sys.exit(f"'{TAB}' exists — pass --replace.")
        svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={
            "requests": [{"deleteSheet": {"sheetId": existing[TAB]}}]}).execute()

    n = len(built)
    # Append after whatever tabs already exist, rather than a hardcoded index
    # — a fresh Master DB with only "Database" doesn't have the same tab
    # layout this script's original spreadsheet did, and a fixed index fails
    # with "index too high" as soon as the spreadsheet has fewer tabs than that.
    index = len(info["sheets"]) - (1 if TAB in existing else 0)
    r = svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={"requests": [
        {"addSheet": {"properties": {"title": TAB, "index": index, "gridProperties": {
            "rowCount": n + 20, "columnCount": ncols, "frozenRowCount": 2}}}}]}).execute()
    gid = r["replies"][0]["addSheet"]["properties"]["sheetId"]

    for i in range(0, n, 20):
        svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={"requests": [
            {"updateCells": {"rows": built[i:i + 20],
                             "fields": "userEnteredValue,userEnteredFormat",
                             "start": {"sheetId": gid, "rowIndex": i, "columnIndex": 0}}}]}).execute()

    reqs = [{"mergeCells": {"range": {"sheetId": gid, "startRowIndex": i, "endRowIndex": i + 1,
                                      "startColumnIndex": 0, "endColumnIndex": ncols},
                            "mergeType": "MERGE_ALL"}}
            for i in [0, n_data + 3] + marks]
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
            "range": {"sheetId": gid, "dimension": "ROWS", "startIndex": n_data + 4,
                      "endIndex": n}, "properties": {"pixelSize": 116}, "fields": "pixelSize"}},
    ]
    svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID,
                                   body={"requests": reqs}).execute()
    print("✅ " + line)


if __name__ == "__main__":
    main()
