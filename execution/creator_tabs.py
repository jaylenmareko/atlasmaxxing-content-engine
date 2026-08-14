#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold a creator's CANVAS + SCRIPTS tab pair from a JSON spec.

Same shape as the first canvas built by hand: ink title banner → grey section banners
→ label rows → value/image rows → a `CLIP MAPS` banner that new blocks append under.
The scripts tab gets a TEMPLATES region (hooks + CTAs) and a `VIDEOS` banner, which is
the anchor `character_scripts.py` inserts against — so a scaffolded tab is immediately
usable by the existing block writer.

All content comes from the spec JSON. Nothing character- or brand-specific is in this
file; it only knows the shapes.

Spec:
{
  "slug": "...", "display": "...", "canvas_tab": "...", "scripts_tab": "...",
  "subtitle": "...",
  "sections": [
    {"banner": "...", "kind": "slots",  "labels": [...], "height": 150},
    {"banner": "...", "kind": "table",  "headers": [...], "rows": [[...], ...]}
  ],
  "hook_headers": [...], "hooks": [[id, ...], ...],
  "cta_headers":  [...], "ctas":  [[id, ...], ...],
  "canvas_index": 8, "scripts_index": 9
}

Both template tables are header-driven — a creator whose CTAs need to carry a rung, a
keyword and a fulfilment status just declares wider headers. Column widths stay global
(the widest value in a column decides), so the two tables share a width profile.

Usage:
  python3 creator_tabs.py --spec spec.json [--replace] [--dry-run]
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

NCOLS_CANVAS = 12
NCOLS_SCRIPTS = 9
CANVAS_W = [120, 290, 250, 240, 210, 210, 160, 180, 180, 150, 150, 210]
SCRIPTS_W = [90, 250, 90, 250, 110, 400, 230, 110, 220]

TITLE = {"red": 0.106, "green": 0.125, "blue": 0.153}
BANNER = {"red": 0.910, "green": 0.910, "blue": 0.910}
LABEL = {"red": 0.961, "green": 0.961, "blue": 0.961}
SUBHEAD = {"red": 0.851, "green": 0.851, "blue": 0.851}
PAPER = {"red": 1, "green": 1, "blue": 1}
TEXT = {"red": 0.11, "green": 0.12, "blue": 0.13}
MUTE = {"red": 0.42, "green": 0.45, "blue": 0.50}
INK = {"red": 0.169, "green": 0.188, "blue": 0.220}
HOOK_BG = {"red": 0.988, "green": 0.929, "blue": 0.839}
CTA_BG = {"red": 0.859, "green": 0.957, "blue": 0.969}
HEADROW = {"red": 0.898, "green": 0.910, "blue": 0.929}


def cell(v, bold=False, size=9, color=None, bg=None, wrap="WRAP", va="MIDDLE", ha="LEFT"):
    s = "" if v is None else str(v)
    key = "formulaValue" if s.startswith("=") else "stringValue"
    return {"userEnteredValue": {key: s},
            "userEnteredFormat": {"backgroundColor": bg or PAPER, "horizontalAlignment": ha,
                                  "verticalAlignment": va, "wrapStrategy": wrap,
                                  "textFormat": {"bold": bold, "fontSize": size,
                                                 "foregroundColor": color or TEXT}}}


def build_canvas(spec):
    n = NCOLS_CANVAS
    rows, heights, merges = [], [], []

    def add(vals, h, merge_full=False):
        rows.append({"values": vals + [cell("", bg=vals[0]["userEnteredFormat"]["backgroundColor"]
                                            if merge_full else None)
                                       for _ in range(n - len(vals))]})
        heights.append(h)
        if merge_full:
            merges.append((len(rows) - 1, 0, n))
        return len(rows) - 1

    add([cell(f"{spec['display']} — CREATOR CANVAS", bold=True, size=13, color=PAPER,
              bg=TITLE)], 32, merge_full=True)
    add([cell(spec.get("subtitle", ""), italic := False or False, size=9, color=MUTE)], 20,
        merge_full=False)

    for sec in spec["sections"]:
        add([cell(sec["banner"], bold=True, size=10, bg=BANNER)], 24, merge_full=True)
        if sec["kind"] == "slots":
            add([cell(x, bold=True, size=9, bg=LABEL) for x in sec["labels"]], 20)
            add([cell("") for _ in sec["labels"]], sec.get("height", 150))
        else:
            add([cell(x, bold=True, size=9, bg=SUBHEAD) for x in sec["headers"]], 20)
            for r in sec.get("rows", []) or [[""] * len(sec["headers"])]:
                add([cell(x, va="TOP") for x in r], sec.get("height", 34))

    add([cell("CLIP MAPS   ·   newest first   —   new blocks append directly under this bar",
              bold=True, size=10, bg=BANNER)], 26, merge_full=True)
    return rows, heights, merges


def build_scripts(spec):
    n = NCOLS_SCRIPTS
    rows, heights, merges = [], [], []

    def add(vals, h, merge_full=False):
        rows.append({"values": vals + [cell("") for _ in range(n - len(vals))]})
        heights.append(h)
        if merge_full:
            merges.append((len(rows) - 1, 0, n))
        return len(rows) - 1

    add([cell(f"{spec['display']} — SCRIPTS", bold=True, size=13, color=PAPER, bg=TITLE)],
        34, merge_full=True)
    add([cell('TEMPLATES — true across every video. Call them by ID: "HK03 + CTA02".',
              bold=True, size=10, color=PAPER, bg=INK)], 26, merge_full=True)

    add([cell(x, bold=True, size=9, bg=HEADROW) for x in spec.get(
        "hook_headers", ["HOOKS", "TEMPLATE", "FORMAT", "EXAMPLE  ·  PROVENANCE"])], 24)
    for h in spec.get("hooks", []):
        add([cell(h[0], bold=True, bg=HOOK_BG, ha="CENTER")] +
            [cell(x, va="TOP", color=MUTE if i == len(h) - 2 else None)
             for i, x in enumerate(h[1:])], 40)

    add([cell("") for _ in range(n)], 12)
    add([cell(x, bold=True, size=9, bg=HEADROW) for x in spec.get(
        "cta_headers", ["CTAs", "NAME", "FORMAT", "THE LINE"])], 24)
    for c in spec.get("ctas", []):
        add([cell(c[0], bold=True, bg=CTA_BG, ha="CENTER")] +
            [cell(x, va="TOP") for x in c[1:]], 40)

    add([cell("") for _ in range(n)], 12)
    add([cell("VIDEOS — newest first. Scroll for the next one.",
              bold=True, size=10, color=PAPER, bg=INK)], 28, merge_full=True)
    return rows, heights, merges


def write(svc, title, rows, heights, merges, ncols, widths, index, replace):
    info = svc.spreadsheets().get(spreadsheetId=MASTER_DB_ID).execute()
    ex = {s["properties"]["title"]: s["properties"]["sheetId"] for s in info["sheets"]}
    if title in ex:
        if not replace:
            sys.exit(f"'{title}' exists — pass --replace.")
        svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={
            "requests": [{"deleteSheet": {"sheetId": ex[title]}}]}).execute()
    n = len(rows)
    r = svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={"requests": [
        {"addSheet": {"properties": {"title": title, "index": index, "gridProperties": {
            "rowCount": n + 260, "columnCount": ncols, "frozenRowCount": 1}}}}]}).execute()
    gid = r["replies"][0]["addSheet"]["properties"]["sheetId"]
    svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={"requests": [
        {"updateCells": {"rows": rows, "fields": "userEnteredValue,userEnteredFormat",
                         "start": {"sheetId": gid, "rowIndex": 0, "columnIndex": 0}}}]}).execute()
    reqs = [{"mergeCells": {"range": {"sheetId": gid, "startRowIndex": i, "endRowIndex": i + 1,
                                      "startColumnIndex": c0, "endColumnIndex": c1},
                            "mergeType": "MERGE_ALL"}} for i, c0, c1 in merges]
    reqs += [{"updateDimensionProperties": {
        "range": {"sheetId": gid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}} for i, px in enumerate(widths)]
    reqs += [{"updateDimensionProperties": {
        "range": {"sheetId": gid, "dimension": "ROWS", "startIndex": i, "endIndex": i + 1},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}} for i, px in enumerate(heights)]
    svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID,
                                   body={"requests": reqs}).execute()
    return n


def main():
    ap = argparse.ArgumentParser(description="Scaffold a creator canvas + scripts tab pair")
    ap.add_argument("--spec", required=True, type=Path)
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    spec = json.loads(a.spec.read_text(encoding="utf-8"))

    cr, ch, cm = build_canvas(spec)
    sr, sh, sm = build_scripts(spec)
    if a.dry_run:
        print(f"[dry-run] {spec['canvas_tab']}: {len(cr)} rows, {len(cm)} banners")
        print(f"[dry-run] {spec['scripts_tab']}: {len(sr)} rows, "
              f"{len(spec.get('hooks', []))} hooks, {len(spec.get('ctas', []))} CTAs")
        return

    svc = gs.get_sheets_service()
    n1 = write(svc, spec["canvas_tab"], cr, ch, cm, NCOLS_CANVAS, CANVAS_W,
               spec.get("canvas_index", 8), a.replace)
    n2 = write(svc, spec["scripts_tab"], sr, sh, sm, NCOLS_SCRIPTS, SCRIPTS_W,
               spec.get("scripts_index", 9), a.replace)
    print(f"✅ {spec['canvas_tab']} — {n1} rows, CLIP MAPS bar ready")
    print(f"✅ {spec['scripts_tab']} — {n2} rows, "
          f"{len(spec.get('hooks', []))} hooks · {len(spec.get('ctas', []))} CTAs · "
          f"VIDEOS bar ready for character_scripts.py")


if __name__ == "__main__":
    main()
