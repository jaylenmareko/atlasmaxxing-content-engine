#!/usr/bin/env python3
"""Create a research working tab: `R: [creator]` in the master workbook.

Ported from pc-engine-v2 2026-08-02. The only change is where the IDs come from:
this repo holds no brand values, so the spreadsheet pointer is read from
config/characters.json -> workspace. Everything else is the proven original.

Two regions:
  DATA (rows 2-31)    — Tier | Thumbnail | Link | Views | Likes | Notes |
                        Transcript | Storyboard | frames → (tier-tinted rows:
                        10 Gold / 10 Silver / 10 Bronze)
  FINDINGS (row 34+)  — Driver | Takeaway & Explanation | Gold Evidence |
                        Bronze Evidence (10 blank scaffold rows)

The four FINDINGS columns are AP6 in the `Research Rules` tab. The protocol that
governs what goes in them lives in that tab, not in this file.

Usage:
  python3 research_tab.py --creator <handle>
  python3 research_tab.py --creator <handle> --picks 10   # rows per tier
"""

import argparse
import json
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "config" / "characters.json"
WS = json.loads(CONFIG.read_text(encoding="utf-8"))["workspace"]
MASTER_DB_ID = WS["master_db_id"]
TAB_PREFIX = WS.get("research_tab_prefix", "R: ")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from google_sheets import get_sheets_service, write_range  # noqa: E402

# tier tint colors (rgb 0-1)
GOLD = {"red": 1.0, "green": 0.95, "blue": 0.80}
SILVER = {"red": 0.94, "green": 0.94, "blue": 0.94}
BRONZE = {"red": 0.99, "green": 0.90, "blue": 0.80}
HEADER_GREY = {"red": 0.85, "green": 0.85, "blue": 0.85}

DATA_HEADERS = ["Tier", "Thumbnail", "Link", "Views", "Likes", "Notes",
                "Transcript", "Storyboard", "Frames →"]
FINDINGS_HEADERS = ["Driver", "Takeaway & Explanation", "Gold Evidence", "Bronze Evidence"]


def create_tab(creator: str, picks: int) -> int:
    svc = get_sheets_service()
    title = f"{TAB_PREFIX}{creator}"

    info = svc.spreadsheets().get(spreadsheetId=MASTER_DB_ID).execute()
    existing = {s["properties"]["title"]: s["properties"]["sheetId"]
                for s in info["sheets"]}
    if title in existing:
        sys.exit(f"Tab '{title}' already exists — delete it first or use it.")

    data_start = 2                       # first data row
    findings_label_row = data_start + 3 * picks + 2   # blank gap after data
    findings_header_row = findings_label_row + 1
    n_findings_rows = 10

    r = svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={
        "requests": [{"addSheet": {"properties": {
            "title": title,
            "gridProperties": {"rowCount": findings_header_row + n_findings_rows + 10,
                               "columnCount": 60, "frozenRowCount": 1}}}}]
    }).execute()
    sid = r["replies"][0]["addSheet"]["properties"]["sheetId"]

    # headers + tier labels
    write_range(MASTER_DB_ID, f"'{title}'!A1:I1", [DATA_HEADERS])
    tiers = (["Gold"] * picks) + (["Silver"] * picks) + (["Bronze"] * picks)
    write_range(MASTER_DB_ID, f"'{title}'!A{data_start}:A{data_start + 3 * picks - 1}",
                [[t] for t in tiers])
    write_range(MASTER_DB_ID, f"'{title}'!A{findings_label_row}:A{findings_label_row}",
                [["FINDINGS"]])
    write_range(MASTER_DB_ID,
                f"'{title}'!A{findings_header_row}:D{findings_header_row}",
                [FINDINGS_HEADERS])

    def band(start_row, end_row, color):   # 1-based inclusive rows
        return {"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": start_row - 1,
                      "endRowIndex": end_row, "startColumnIndex": 0,
                      "endColumnIndex": 8},
            "cell": {"userEnteredFormat": {"backgroundColor": color}},
            "fields": "userEnteredFormat.backgroundColor"}}

    reqs = [
        # bold header row + findings headers + FINDINGS label
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                                                        "backgroundColor": HEADER_GREY}},
                        "fields": "userEnteredFormat(textFormat.bold,backgroundColor)"}},
        {"repeatCell": {"range": {"sheetId": sid,
                                  "startRowIndex": findings_label_row - 1,
                                  "endRowIndex": findings_header_row},
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat.textFormat.bold"}},
        {"repeatCell": {"range": {"sheetId": sid,
                                  "startRowIndex": findings_header_row - 1,
                                  "endRowIndex": findings_header_row,
                                  "startColumnIndex": 0, "endColumnIndex": 4},
                        "cell": {"userEnteredFormat": {"backgroundColor": HEADER_GREY}},
                        "fields": "userEnteredFormat.backgroundColor"}},
        # tier banding
        band(data_start, data_start + picks - 1, GOLD),
        band(data_start + picks, data_start + 2 * picks - 1, SILVER),
        band(data_start + 2 * picks, data_start + 3 * picks - 1, BRONZE),
        # data row heights (storyboard-readable)
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "ROWS",
                      "startIndex": data_start - 1, "endIndex": data_start + 3 * picks - 1},
            "properties": {"pixelSize": 220}, "fields": "pixelSize"}},
        # findings row heights (wrapped text)
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "ROWS",
                      "startIndex": findings_header_row,
                      "endIndex": findings_header_row + n_findings_rows},
            "properties": {"pixelSize": 110}, "fields": "pixelSize"}},
        # wrap text in findings region (A:D)
        {"repeatCell": {"range": {"sheetId": sid,
                                  "startRowIndex": findings_header_row,
                                  "endRowIndex": findings_header_row + n_findings_rows,
                                  "startColumnIndex": 0, "endColumnIndex": 4},
                        "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP",
                                                        "verticalAlignment": "TOP"}},
                        "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"}},
        # wrap notes + transcript in data region (user-readable, like Database col E)
        {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": data_start - 1,
                                  "endRowIndex": data_start + 3 * picks - 1,
                                  "startColumnIndex": 5, "endColumnIndex": 7},
                        "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP",
                                                        "verticalAlignment": "TOP"}},
                        "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"}},
    ]
    # column widths — Notes + Transcript both wide (user reads Gemini output in Notes)
    widths = [(0, 70), (1, 160), (2, 200), (3, 100), (4, 80), (5, 500), (6, 500), (7, 170)]
    for idx, px in widths:
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": idx, "endIndex": idx + 1},
            "properties": {"pixelSize": px}, "fields": "pixelSize"}})

    svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID,
                                   body={"requests": reqs}).execute()
    print(f"✅ tab '{title}' created — DATA rows {data_start}-{data_start + 3*picks - 1} "
          f"(tinted {picks}/tier), FINDINGS at row {findings_header_row}")
    return sid


def main():
    ap = argparse.ArgumentParser(description="Create a research working tab")
    ap.add_argument("--creator", required=True)
    ap.add_argument("--picks", type=int, default=10, help="videos per tier (default 10)")
    args = ap.parse_args()
    create_tab(args.creator, args.picks)


if __name__ == "__main__":
    main()
