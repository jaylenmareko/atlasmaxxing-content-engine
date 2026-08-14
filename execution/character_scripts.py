#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add a video block to a character's SCRIPTS tab, without rebuilding the tab.

The tab was previously produced by a builder that did deleteSheet + addSheet on every change.
That is destructive: it wipes anything the user edited (a pasted final script, a widened row,
a note in a spare cell) and silently resets every row height and column width. R29.

This module only ever does two things:
  * insertDimension  — open a gap directly under the VIDEOS banner (newest first)
  * updateCells      — write into that gap

Everything outside the gap is untouched, so user edits and sizing survive.

Nothing here is character-specific. The tab pointer comes from config/characters.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import google_sheets as gs  # noqa: E402

CONFIG = Path(__file__).resolve().parent.parent / "config" / "characters.json"

NCOLS = 9
CARD_COLS = [(1, 3), (3, 5), (5, 7), (7, 9)]   # B:C  D:E  F:G  H:I

INK = {"red": 0.11, "green": 0.12, "blue": 0.13}
PAPER = {"red": 1, "green": 1, "blue": 1}
BAND = {"red": 0.17, "green": 0.19, "blue": 0.22}
VBAND = {"red": 0.29, "green": 0.26, "blue": 0.42}
HEAD = {"red": 0.90, "green": 0.91, "blue": 0.93}
NEAR = {"red": 0.87, "green": 0.94, "blue": 0.88}
FAR = {"red": 0.99, "green": 0.91, "blue": 0.84}
LOCK = {"red": 0.83, "green": 0.92, "blue": 0.84}
MUTE = {"red": 0.42, "green": 0.45, "blue": 0.50}

# row heights, in the order the block is written
H_BANNER, H_LABELS, H_VALUES, H_TEXT, H_OPTBAND, H_CARDHDR, H_CARDBODY = 30, 24, 24, 132, 26, 40, 300


def cell(v, bold=False, size=9, color=None, bg=None, italic=False, ha="LEFT", va="TOP"):
    s = str(v)
    return {"userEnteredValue": {"formulaValue": s} if s.startswith("=") else {"stringValue": s},
            "userEnteredFormat": {
                "backgroundColor": bg or PAPER, "horizontalAlignment": ha, "verticalAlignment": va,
                "wrapStrategy": "WRAP",
                "textFormat": {"bold": bold, "italic": italic, "fontSize": size,
                               "foregroundColor": color or INK, "fontFamily": "Inter"},
                "padding": {"top": 6, "bottom": 6, "left": 8, "right": 8}}}


def _sheet_id(svc, ssid, title):
    info = svc.spreadsheets().get(spreadsheetId=ssid).execute()
    for s in info["sheets"]:
        if s["properties"]["title"] == title:
            return s["properties"]["sheetId"]
    raise SystemExit(f"tab {title!r} not found")


def find_banner(grid, text="VIDEOS"):
    """1-based row of the VIDEOS banner. New blocks go directly under it."""
    for i, r in enumerate(grid):
        if r and str(r[0]).strip().upper().startswith(text):
            return i + 1
    raise SystemExit(f"no {text!r} banner on this tab — is it the right one?")


def build_rows(vid, row_no, vtype, style, thumb_id, reel, doc, status, trigger,
               original, final, note, scripts):
    """Return (rows, merges_relative, heights_relative) for one video block."""
    rows, merges, heights = [], [], []

    def add(cells, height):
        rows.append({"values": cells + [cell("")] * (NCOLS - len(cells))})
        heights.append(height)
        return len(rows) - 1

    def merge(i, c0, c1, rowspan=1):
        merges.append((i, c0, c1, rowspan))

    i = add([cell(f"{vid}  ·  Row {row_no}  ·  {vtype}  ·  {style}",
                  bold=True, size=12, color=PAPER, bg=VBAND, va="MIDDLE")], H_BANNER)
    merge(i, 0, NCOLS)

    top = add([cell(f'=IMAGE("https://drive.google.com/thumbnail?id={thumb_id}&sz=w600", 1)')]
              + [cell(x, bold=True, bg=HEAD) for x in
                 ["ROW", "TYPE", "STYLE", "STATUS", "REFERENCE", "WORKING DOC", "OPTIONS", "TRIGGER"]],
              H_LABELS)
    add([cell(""), cell(row_no), cell(vtype), cell(style),
         cell(status, bold=True, bg=LOCK if "LOCK" in status.upper() else PAPER),
         cell(f'=HYPERLINK("{reel}","reel")'), cell(f'=HYPERLINK("{doc}","doc")'),
         cell(len(scripts)), cell(trigger, bold=True)], H_VALUES)

    for label, body, bg in [("ORIGINAL", original, HEAD), ("FINAL", final, LOCK), ("NOTE", note, HEAD)]:
        i = add([cell(""), cell(label, bold=True, bg=bg),
                 cell(body, size=10 if label != "NOTE" else 9,
                      italic=label == "NOTE", color=MUTE if label == "NOTE" else None,
                      bg=LOCK if (label == "FINAL" and body) else PAPER)],
                H_TEXT if label != "NOTE" else 34)
        merge(i, 2, NCOLS)
    merge(top, 0, 1, rowspan=5)          # thumbnail spans the info block

    i = add([cell("OPTIONS — read across and down. Card header is the route.",
                  bold=True, size=10, color=PAPER, bg=BAND)], H_OPTBAND)
    merge(i, 0, NCOLS)

    for base in range(0, len(scripts), 4):
        chunk = scripts[base:base + 4]
        hdr, body = [cell("")], [cell("")]
        for s in chunk:
            lvl = s.get("level", "")
            hdr += [cell(f"#{s['n']}  ·  {lvl}  ·  {s['fw']}  ·  {s['hook_t']}",
                         bold=True, bg=NEAR if lvl == "80-20" else FAR), cell("")]
            body += [cell("\n".join(s["body"]), size=10), cell("")]
        hi, bi = add(hdr, H_CARDHDR), add(body, H_CARDBODY)
        for c0, c1 in CARD_COLS[:len(chunk)]:
            merge(hi, c0, c1)
            merge(bi, c0, c1)

    add([cell("")], 12)
    return rows, merges, heights


def add_block(ssid, tab, dry_run=False, **kw):
    svc = gs.get_sheets_service()
    gid = _sheet_id(svc, ssid, tab)
    grid = svc.spreadsheets().values().get(
        spreadsheetId=ssid, range=f"'{tab}'!A:A").execute().get("values", [])
    banner = find_banner(grid)

    rows, merges, heights = build_rows(**kw)
    n = len(rows)
    start = banner            # 0-based index of the first inserted row

    if dry_run:
        print(f"[dry-run] would insert {n} rows at sheet row {start + 1}, under the VIDEOS "
              f"banner at row {banner}. Nothing outside rows "
              f"{start + 1}-{start + n} would be touched.")
        return

    # 1. open the gap. inheritFromBefore=False so the banner's formatting is not copied down.
    svc.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": [
        {"insertDimension": {"range": {"sheetId": gid, "dimension": "ROWS",
                                       "startIndex": start, "endIndex": start + n},
                             "inheritFromBefore": False}}]}).execute()

    # 2. fill it
    svc.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": [
        {"updateCells": {"rows": rows, "fields": "userEnteredValue,userEnteredFormat",
                         "start": {"sheetId": gid, "rowIndex": start, "columnIndex": 0}}}]}).execute()

    # 3. merges and row heights, both relative to the gap
    reqs = [{"mergeCells": {"range": {"sheetId": gid, "startRowIndex": start + i,
                                      "endRowIndex": start + i + span,
                                      "startColumnIndex": c0, "endColumnIndex": c1},
                            "mergeType": "MERGE_ALL"}} for i, c0, c1, span in merges]
    reqs += [{"updateDimensionProperties": {
        "range": {"sheetId": gid, "dimension": "ROWS",
                  "startIndex": start + i, "endIndex": start + i + 1},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}} for i, px in enumerate(heights)]
    svc.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": reqs}).execute()

    print(f"inserted {kw['vid']} as {n} rows at row {start + 1}. Column widths, every other "
          f"block and any edits you made are untouched.")


def main():
    ap = argparse.ArgumentParser(description="Insert a video block into a character's scripts tab.")
    ap.add_argument("--character", default="example")
    ap.add_argument("--payload", required=True, help="path to a json file with the block fields")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    chars = json.loads(CONFIG.read_text())["characters"]
    if a.character not in chars:
        raise KeyError(f"Unknown character {a.character!r}. Known: {', '.join(chars) or '(none)'}")
    ch = chars[a.character]
    tab = ch.get("scripts_tab", f"{a.character.title()} Scripts")
    add_block(ch["spreadsheet_id"], tab, dry_run=a.dry_run,
              **json.loads(Path(a.payload).read_text()))


if __name__ == "__main__":
    main()
