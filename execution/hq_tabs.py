#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the two HQ tabs from a JSON spec: the CANVAS and the FORMATS reference table.

CANVAS   one row per idea. An idea becomes a video when it gets a number. Flat and
         sortable — no section banners inside the table, or filtering breaks.
         # · TYPE · STAGE · IDEA/VIDEO · FORMAT · SCRIPT · CAPTION · VALUE/ASSET · REF

FORMATS  one row per reference video worth copying. The columns a format decision
         actually needs: what it looked like, how it was built, what to say, what to copy.
         REF · SOURCE ROW · FORMAT · BASE× · VIEWS · CREATOR · THUMBNAIL · STORYBOARD ·
         SCRIPT TEMPLATE · RULES · LINK · FRAME 1..n

Image, link and frame cells are LIFTED from an existing research tab by row number, so
the spec only carries what a human wrote: the script template and the rules.

Nothing brand- or character-specific lives in this file. All content comes from the spec.

Spec:
{
  "master_db_id": "...",
  "source_tab": "Format Research",
  "source_cols": {"row":0,"format":1,"tier":2,"base":3,"views":4,"creator":5,
                  "thumb":8,"script":9,"mech":10,"story":11,"link":12,"frames_from":14},
  "canvas": {"tab": "...", "title": "...", "subtitle": "...", "index": 1,
             "headers": [...], "rows": [[...], ...], "video_types": ["VIDEO"]},
  "formats": {"tab": "...", "title": "...", "subtitle": "...", "index": 2,
              "refs": [{"source_row": 141, "script_template": "...", "rules": "..."}, ...]}
}

Usage:
  python3 hq_tabs.py --spec spec.json [--replace] [--drop TAB ...] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import google_sheets as gs  # noqa: E402

TITLE_BG = {"red": 0.106, "green": 0.125, "blue": 0.153}
BANNER_BG = {"red": 0.910, "green": 0.910, "blue": 0.910}
LABEL_BG = {"red": 0.961, "green": 0.961, "blue": 0.961}
HEAD_BG = {"red": 0.898, "green": 0.910, "blue": 0.929}
PAPER = {"red": 1, "green": 1, "blue": 1}
VIDEO_BG = {"red": 0.988, "green": 0.949, "blue": 0.878}
TEXT = {"red": 0.11, "green": 0.12, "blue": 0.13}
WHITE = {"red": 1, "green": 1, "blue": 1}
MUTE = {"red": 0.42, "green": 0.45, "blue": 0.50}

FORMAT_TINT = {
    "SILENT BUILD DEMO":     {"red": 0.906, "green": 0.949, "blue": 0.922},
    "AFFILIATE CONVERSION":  {"red": 0.988, "green": 0.910, "blue": 0.878},
    "AGENT SYSTEM SHOWCASE": {"red": 0.906, "green": 0.933, "blue": 0.980},
    "NARRATED TUTORIAL":     {"red": 0.988, "green": 0.965, "blue": 0.878},
}


def cell(v, bold=False, size=9, color=None, bg=None, ha="LEFT", va="MIDDLE", wrap="WRAP"):
    s = "" if v is None else str(v)
    key = "formulaValue" if s.startswith("=") else "stringValue"
    return {"userEnteredValue": {key: s},
            "userEnteredFormat": {"backgroundColor": bg or PAPER, "horizontalAlignment": ha,
                                  "verticalAlignment": va, "wrapStrategy": wrap,
                                  "textFormat": {"bold": bold, "fontSize": size,
                                                 "foregroundColor": color or TEXT}}}


def band(text, ncols, bg, fg, size=11):
    row = [cell(text, bold=True, size=size, color=fg, bg=bg, va="MIDDLE")]
    row += [cell("", bg=bg) for _ in range(ncols - 1)]
    return row


def grid(svc, ss_id, tab, index, ncols, nrows):
    """Create the tab if missing, size it, return its sheetId."""
    meta = svc.spreadsheets().get(spreadsheetId=ss_id).execute()
    for s in meta["sheets"]:
        if s["properties"]["title"] == tab:
            return s["properties"]["sheetId"]
    res = svc.spreadsheets().batchUpdate(spreadsheetId=ss_id, body={"requests": [
        {"addSheet": {"properties": {"title": tab, "index": index,
                                     "gridProperties": {"rowCount": max(nrows + 20, 60),
                                                        "columnCount": ncols}}}}]}).execute()
    return res["replies"][0]["addSheet"]["properties"]["sheetId"]


def lay(gid, rows, widths, heights, freeze=2, filt=None):
    """Rows → the batchUpdate requests that write and shape them.

    `filt` is the 0-based row index the filter's header sits on, or None for no filter.
    """
    ncols = len(widths)
    reqs = [{"updateCells": {"rows": [{"values": r} for r in rows],
                             "fields": "userEnteredValue,userEnteredFormat",
                             "start": {"sheetId": gid, "rowIndex": 0, "columnIndex": 0}}}]
    for i, w in enumerate(widths):
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": gid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": w}, "fields": "pixelSize"}})
    for i, h in heights:
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": gid, "dimension": "ROWS", "startIndex": i, "endIndex": i + 1},
            "properties": {"pixelSize": h}, "fields": "pixelSize"}})
    reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": gid, "gridProperties": {"frozenRowCount": freeze}},
        "fields": "gridProperties.frozenRowCount"}})
    if filt is not None:
        reqs.append({"setBasicFilter": {"filter": {"range": {
            "sheetId": gid, "startRowIndex": filt, "endRowIndex": len(rows),
            "startColumnIndex": 0, "endColumnIndex": ncols}}}})
    return reqs


def build_canvas(spec):
    """Header blocks first — banner, label row, values — then the flat sortable table.

    Same shape as the character canvas: ink title, grey section banners, pale label rows.
    The filter is set on the table range only, so the blocks above it never move.
    """
    c = spec["canvas"]
    heads = c["headers"]
    n = len(heads)
    rows = [band(c["title"], n, TITLE_BG, WHITE, size=12)]
    heights = [(0, 30)]

    def push(vals, h, bg=None, bold=False, size=9, color=None):
        vals = list(vals) + [""] * (n - len(vals))
        rows.append([cell(v, bold=bold, size=size, bg=bg, color=color) for v in vals])
        heights.append((len(rows) - 1, h))

    for sec in c.get("sections", []):
        push([sec["banner"]], 22, bg=BANNER_BG, bold=True, size=10)
        if sec.get("labels"):
            push(sec["labels"], 20, bg=LABEL_BG)
        for r in sec.get("rows", []):
            push(r, sec.get("height", 34))
        push([""], 14)

    push([c["table_banner"]], 22, bg=BANNER_BG, bold=True, size=10)
    filt = len(rows)
    rows.append([cell(h, bold=True, size=9, bg=HEAD_BG) for h in heads])
    heights.append((len(rows) - 1, 26))
    for r in c["rows"]:
        r = list(r) + [""] * (n - len(r))
        is_video = any(str(r[1]).upper().startswith(t) for t in c.get("video_types", ["VIDEO"]))
        bg = VIDEO_BG if is_video else PAPER
        rows.append([cell(v, bold=(j == 0 and is_video), bg=bg,
                          color=MUTE if (v == "" or str(v).startswith("—")) else None)
                     for j, v in enumerate(r)])
        heights.append((len(rows) - 1, 44))
    return rows, c["widths"], heights, filt


def build_formats(spec, src):
    f = spec["formats"]
    maxf = max((len(src[r["source_row"]]["frames"]) for r in f["refs"]), default=0)
    heads = ["REF", "SOURCE ROW", "FORMAT", "BASE ×", "VIEWS", "CREATOR", "THUMBNAIL",
             "STORYBOARD", "SCRIPT TEMPLATE", "SCRIPT EXAMPLE — what they actually said",
             "RULES — what to copy", "LINK"]
    heads += [f"FRAME {i+1}" for i in range(maxf)]
    n = len(heads)
    rows = [band(f["title"], n, TITLE_BG, WHITE, size=12),
            [cell(h, bold=True, size=9, bg=HEAD_BG) for h in heads]]
    heights = [(0, 34), (1, 30)]
    widths = [70, 80, 150, 70, 85, 115, 120, 120, 420, 420, 330, 105] + [95] * maxf
    prose = (8, 9, 10)
    for i, r in enumerate(f["refs"]):
        d = src[r["source_row"]]
        bg = FORMAT_TINT.get(d["format"], PAPER)
        vals = [f"REF {i+1:02d}", d["row"], d["format"], d["base"], d["views"], d["creator"],
                d["thumb"], d["story"], r["script_template"], d["script"] or "— no speech —",
                r["rules"], d["link"]]
        vals += d["frames"] + [""] * (maxf - len(d["frames"]))
        cells = [cell(v, bold=(j == 0), bg=(bg if j < 6 else PAPER),
                      size=8 if j in prose else 9, va="TOP" if j in prose else "MIDDLE")
                 for j, v in enumerate(vals)]
        rows.append(cells)
        heights.append((len(rows) - 1, 190))
    return rows, widths, heights, 1


def pull_source(svc, spec):
    """Lift image / link / frame formulas off the research tab, keyed by its row number."""
    sc = spec["source_cols"]
    tab = spec["source_tab"]
    # the research tab may live in the archive spreadsheet once it is out of the working file
    src_id = spec.get("source_db_id", spec["master_db_id"])
    vals = svc.spreadsheets().values().get(
        spreadsheetId=src_id, range=f"'{tab}'!A1:BZ400").execute().get("values", [])
    form = svc.spreadsheets().values().get(
        spreadsheetId=src_id, range=f"'{tab}'!A1:BZ400",
        valueRenderOption="FORMULA").execute().get("values", [])
    out = {}
    for v, fm in zip(vals, form):
        v = v + [""] * (80 - len(v))
        fm = fm + [""] * (80 - len(fm))
        try:
            rn = int(str(v[sc["row"]]).strip())
        except (ValueError, TypeError):
            continue
        out[rn] = {"row": rn, "format": v[sc["format"]], "base": v[sc["base"]],
                   "views": v[sc["views"]], "creator": v[sc["creator"]],
                   "script": v[sc["script"]], "mech": v[sc["mech"]],
                   "thumb": fm[sc["thumb"]], "story": fm[sc["story"]], "link": fm[sc["link"]],
                   "frames": [c for c in fm[sc["frames_from"]:] if str(c).startswith("=IMAGE")]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--replace", action="store_true", help="clear the tab before writing")
    ap.add_argument("--drop", nargs="*", default=[], help="tab titles to delete first")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    spec = json.loads(Path(a.spec).read_text())
    svc = gs.get_sheets_service()
    ss = spec["master_db_id"]

    for title in a.drop:
        meta = svc.spreadsheets().get(spreadsheetId=ss).execute()
        for s in meta["sheets"]:
            if s["properties"]["title"] == title:
                if a.dry_run:
                    print(f"  would delete tab {title}")
                else:
                    svc.spreadsheets().batchUpdate(spreadsheetId=ss, body={"requests": [
                        {"deleteSheet": {"sheetId": s["properties"]["sheetId"]}}]}).execute()
                    print(f"  deleted tab {title}")

    src = pull_source(svc, spec)
    print(f"  source rows available: {len(src)}")

    jobs = [("canvas", build_canvas(spec)), ("formats", build_formats(spec, src))]
    for key, (rows, widths, heights, filt) in jobs:
        conf = spec[key]
        print(f"  {conf['tab']}: {len(rows)} rows x {len(widths)} cols")
        if a.dry_run:
            continue
        gid = grid(svc, ss, conf["tab"], conf["index"], len(widths), len(rows))
        reqs = []
        if a.replace:
            reqs.append({"updateCells": {"range": {"sheetId": gid},
                                         "fields": "userEnteredValue,userEnteredFormat"}})
            reqs.append({"clearBasicFilter": {"sheetId": gid}})
        reqs.append({"updateSheetProperties": {
            "properties": {"sheetId": gid, "index": conf["index"],
                           "gridProperties": {"rowCount": len(rows) + 20,
                                              "columnCount": len(widths)}},
            "fields": "index,gridProperties.rowCount,gridProperties.columnCount"}})
        svc.spreadsheets().batchUpdate(spreadsheetId=ss, body={"requests": reqs}).execute()
        svc.spreadsheets().batchUpdate(spreadsheetId=ss, body={
            "requests": lay(gid, rows, widths, heights,
                            freeze=conf.get("freeze", 2), filt=filt)}).execute()
    print("done")


if __name__ == "__main__":
    main()
