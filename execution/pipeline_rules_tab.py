#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the `Pipeline Rules` tab — the five stages a video passes through.

Same idiom as `Research Rules`: one row per thing, flat and cell-addressable, tinted by
KIND, section banners in ink, row 1 frozen. Carries WHO and GATE for the same reason the
research protocol does — the points where the flow stops for the user have to be visible
on the page.

Where `Research Rules` covers how a format is DISCOVERED, this covers how a video is
BUILT: feeder -> format -> cta -> fulfilment -> on-screen asset. Mechanism in
`canvas/pipeline.md`; the values live in each character's canvas.

Nothing character-specific or brand-specific is in this file.

Usage:
  python3 pipeline_rules_tab.py                 # create (refuses if it exists)
  python3 pipeline_rules_tab.py --rebuild       # replace the tab in place
  python3 pipeline_rules_tab.py --dry-run       # print the row plan, touch nothing
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import google_sheets as gs  # noqa: E402

CONFIG = Path(__file__).resolve().parent.parent / "config" / "characters.json"
MASTER_DB_ID = json.loads(CONFIG.read_text())["workspace"]["master_db_id"]
TAB = "Pipeline Rules"

NCOLS = 9
HEADERS = ["ID", "KIND", "NAME", "WHO", "GATE",
           "WHAT IT IS (one line)", "DETAIL", "OUTPUT / EXAMPLE", "SOURCE"]
WIDTHS = [64, 112, 290, 92, 118, 380, 480, 360, 175]

INK = {"red": 0.169, "green": 0.188, "blue": 0.220}
PAPER = {"red": 1, "green": 1, "blue": 1}
TEXT = {"red": 0.11, "green": 0.12, "blue": 0.13}
MUTE = {"red": 0.42, "green": 0.45, "blue": 0.50}
HEADROW = {"red": 0.898, "green": 0.910, "blue": 0.929}

TINT = {
    "STAGE":   {"red": 0.867, "green": 0.910, "blue": 0.988},
    "SOURCE":  {"red": 0.898, "green": 0.957, "blue": 0.910},
    "SPEC":    {"red": 0.949, "green": 0.910, "blue": 0.976},
    "RUNG":    {"red": 0.859, "green": 0.957, "blue": 0.969},
    "ASSET":   {"red": 0.988, "green": 0.929, "blue": 0.847},
    "TYPE":    {"red": 0.988, "green": 0.969, "blue": 0.847},
    "GATE":    {"red": 0.988, "green": 0.878, "blue": 0.878},
    "RULE":    {"red": 0.988, "green": 0.867, "blue": 0.600},
}

CHECK = "✋ YOU"
PING = "📣 PING"
STOP = "🛑 BLOCKS POST"

# --------------------------------------------------------------------------------------
# One tuple per row: (ID, KIND, NAME, WHO, GATE, WHAT, DETAIL, OUTPUT, SOURCE)
# A bare string is a section banner.
# --------------------------------------------------------------------------------------
ROWS = [

"THE FIVE STAGES — every video passes through all five, in order. A stage with no output blocks the next one. Recreation (canvas/SPEC.md) is one implementation of stage 5.",

("ST1", "STAGE", "FEEDER — an observed demand", "YOU", "—",
 "A video is written from a demand that was observed, not from an idea someone had.",
 "Sources in descending signal: questions asked live (stream, DM, comments) · your own SOP, i.e. what you actually did that day · a competitor gap, a format in the corpus nobody in the niche runs · a step every tutorial skips. Record the question IN THE ASKER'S WORDS — rewriting it into a topic loses the hook, because the phrasing of the question is frequently the phrasing of the hook.",
 "One line in the IDEA FEEDER table on the canvas.", "user 2026-08-04"),

("ST2", "STAGE", "FORMAT — the shape that carries it", "CLAUDE", CHECK,
 "Choose which format carries the idea, then work to that format's spec.",
 "Format sets the CEILING. On identical subject matter from one operator in one month, format choice moved outcomes ~485×. It does NOT set the depth of the ask — see G5. A format is not specified until FS1–FS9 below all exist for it. A format described in one line is NAMED, not specified, and naming is what produces \"we have no direction\".",
 "A format ID + its filled spec row.", "Format Research · 29 findings"),

("ST3", "STAGE", "CTA — what the video asks for", "YOU", CHECK,
 "Decide what you are asking the viewer for. That decision sets what you then have to build.",
 "A video does not have A cta — it has a SLOT MAP. Asks can land at different timecodes and asks at different DEPTHS do not compete for the same viewer. Pick from the rungs R0–R3 below. Whatever you pick becomes a build order for stage 4.",
 "A rung + a keyword.", "user 2026-08-04"),

("ST4", "STAGE", "FULFILMENT — what the viewer receives", "BOTH", STOP,
 "The thing delivered after they comment. It must exist and be wired BEFORE the video posts.",
 "The only stage with a hard gate on posting. The common failure is running 1-2-3-5 and skipping this one: the video ships, comments land on a keyword wired to nothing, and the leads are gone. Four types — FT1–FT4 below. A keyword is LIVE only when the trigger fires, the copy is written and the destination resolves.",
 "A keyword marked LIVE in the canvas CTA LADDER.", "user 2026-08-04 · G1"),

("ST5", "STAGE", "ON-SCREEN ASSET — what appears in the video", "CLAUDE", "—",
 "The artifact shown on screen. Separate from fulfilment and routinely confused with it.",
 "Three kinds — AK1–AK3 below. Registered in the canvas ARTIFACT LIBRARY with a path and a rebuild command, so a later video reuses it instead of rebuilding it. Deadline is BEFORE RECORDING, where fulfilment's deadline is before posting; they are different work on different clocks.",
 "A file, registered with a rebuild command.", "canvas/pipeline.md"),

"THE TWO ASSET CLASSES — the distinction this whole tab exists to make. Both are needed. They are produced by different work, on different deadlines.",

("AC1", "ASSET", "ON-SCREEN asset", "CLAUDE", "—",
 "What appears IN the video.",
 "Deadline: before recording. Failure mode if missing: the video has nothing to look at. Durable — a built artifact survives into later videos and is the cheapest thing to reuse.",
 "e.g. a system diagram, a live screen recording, an analytics screenshot.", "user 2026-08-04"),

("AC2", "ASSET", "FULFILMENT asset", "BOTH", STOP,
 "What the viewer RECEIVES after commenting.",
 "Deadline: before POSTING. Failure mode if missing: a burned lead and a spent hook. Not durable in the same way — it is consumed per lead, but it is written once and reused across every video that shares the keyword.",
 "e.g. a prompt pack, a written guide, a long-form video.", "user 2026-08-04"),

("AK1", "TYPE", "On-screen · built artifact", "CLAUDE", "—",
 "A diagram, map or graph made for the video.",
 "The only kind that survives into later videos. Highest build cost, lowest marginal cost after the first use. Register the rebuild command, not just the file.", "", "canvas/pipeline.md"),

("AK2", "TYPE", "On-screen · live capture", "YOU", "—",
 "Screen recording of the real work being done.",
 "Most credible, least reusable. Needs a shot list before recording or the edit becomes the bottleneck. Chat interfaces read slow on playback — plan the speed-up in the edit.", "", "canvas/pipeline.md"),

("AK3", "TYPE", "On-screen · evidence", "YOU", "—",
 "Analytics, dashboards, receipts.",
 "Cheapest of the three, and the ONLY kind that substantiates a numeric claim made in the hook. If the hook names a dollar figure, this is not optional.", "", "canvas/pipeline.md"),

"FEEDER SOURCES — where ideas come from, in descending signal.",

("F1", "SOURCE", "Questions asked live", "YOU", "—",
 "Stream questions, DMs, comments.",
 "Highest signal: the asker is real and the wording is theirs. Keep the wording — it is usually the hook.", "", "user 2026-08-04"),

("F2", "SOURCE", "Your own SOP", "YOU", "—",
 "What you actually did that day.",
 "Whatever is routine to the operator is usually opaque to the audience. The most-asked questions are frequently about the least interesting part of the job.", "", "user 2026-08-04"),

("F3", "SOURCE", "Competitor gap", "CLAUDE", "—",
 "A format present in the research corpus that nobody in the niche runs.",
 "Read off Format Research. The corpus records which formats a creator does and does not run; the gap is the cheapest untested hypothesis available.", "", "Format Research"),

("F4", "SOURCE", "Tutorial / long-form gap", "BOTH", "—",
 "A step every tutorial skips.", "", "", "user 2026-08-04"),

("F5", "RULE", "Asked twice, build it", "YOU", "—",
 "A repeated question is a validated topic. A single question is an anecdote.",
 "The count is worth recording in the feeder table — it is the only demand signal available before anything is made.",
 "ASKED × column on the canvas.", "user 2026-08-04"),

"FORMAT SPEC — a format is not specified until all nine of these exist for it. Values live in the canvas FORMATS table; visual examples are NOT duplicated, they point at reference rows in Format Research.",

("FS1", "SPEC", "Definition", "CLAUDE", "—", "One line — what the format is.", "", "", "user 2026-08-04"),
("FS2", "SPEC", "The one driver", "CLAUDE", "—",
 "The single variable that decides the outcome, plus its observed control.",
 "Every format in the corpus has one. Showcase: is the system on screen — 316,405 vs 2,455 against 12 explainer controls. Silent: the artifact itself — 47× on an identical rig, white template vs dark editorial. Affiliate: the gate is load-bearing — 4 controls with the gate removed were all bottom-quartile.",
 "", "Format Research findings"),
("FS3", "SPEC", "Script shape", "CLAUDE", "—", "The beats in order, with timings.", "", "", "Script Rules"),
("FS4", "SPEC", "Hook examples", "CLAUDE", "—",
 "Three minimum, verbatim, with provenance and baseline multiple.",
 "Live in the character's SCRIPTS tab as HK rows, not here.", "HK01–HK17 today.", "Format Research"),
("FS5", "SPEC", "Text on screen", "CLAUDE", "—",
 "Verbatim overlay strings — not descriptions of them.",
 "\"SEE THAT BROWN\" is a spec. \"a punchy overlay\" is not.", "", "Research Rules AP2"),
("FS6", "SPEC", "Frame pattern", "CLAUDE", "—",
 "Scene count, scene length, what the storyboard looks like.",
 "Read off the frame columns of the Gold reference rows.", "", "Format Research"),
("FS7", "SPEC", "Face", "YOU", "—", "On camera / voice only / faceless.",
 "Unresolved at brand level where the highest-ceiling format is deliberately faceless and the operator has committed to face content. Recorded per format, not assumed.", "", "user"),
("FS8", "SPEC", "CTA style", "CLAUDE", "—",
 "Placement, spoken vs text, and which rungs the format can carry.", "", "", "canvas/pipeline.md"),
("FS9", "SPEC", "References", "CLAUDE", "—",
 "Gold rows to steal from, Bronze controls to avoid.",
 "Point at Format Research row numbers. Column A there is =ROW() so the address never drifts.",
 "e.g. \"Gold 104–105 · Bronze 109–120\".", "Format Research"),

"THE RUNGS — ordered by what the viewer is asked to invest. Rungs at DIFFERENT depths do not compete; rungs at the same depth do.",

("R0", "RUNG", "Mid-roll internal link", "YOU", "—",
 "\"…which I show you how to make in my last video — go to my page.\"",
 "NOT a rung. Fires around the 40% mark, asks for no comment, and therefore costs no comment volume — it stacks with any rung below for free. Its job is making the back catalogue work as a library rather than a feed.",
 "Ask: none. Money: none. Routes the back catalogue.", "user 2026-08-04"),

("R1", "RUNG", "Give me the thing you used", "YOU", "—",
 "The prompt / template gate. Lowest friction ask there is.",
 "Fulfilment is usually FT1 or FT2. No money attached directly — it buys trust and a DM list, and the list is the asset. Highest comment volume of any rung, which is also its algorithmic value.",
 "Keyword + prompt pack or guide.", "user 2026-08-04"),

("R2", "RUNG", "Show me the full breakdown", "YOU", "—",
 "Medium friction — the viewer has to click out and watch long-form.",
 "Fulfilment is FT3. The selling happens INSIDE the long-form, not in the DM. Most expensive rung to stand up, because the fulfilment asset is itself a full production.",
 "Keyword + a long-form video.", "user 2026-08-04"),

("R3", "RUNG", "How do I get access", "YOU", "—",
 "Highest friction. The viewer self-identifies as a buyer by commenting.",
 "Usually reached through a DISQUALIFIER rather than an offer: \"this only works if you actually have a product\" converts better than \"here's how to get a product\", because it filters before it asks. Fulfilment is FT2 into FT4 — a written guide that ends at a booking.",
 "Keyword + guide + DM sequence + a booking link.", "user 2026-08-04"),

"FULFILMENT TYPES — what actually gets delivered. Every one of these is work; none of them is free.",

("FT1", "TYPE", "DM TEXT", "CLAUDE", "—",
 "The deliverable pasted straight into the DM.",
 "Lowest build cost and instant delivery — no external page to host, nothing to load. Best fit for prompts, templates and short lists.", "", "user 2026-08-04"),

("FT2", "TYPE", "DOC", "CLAUDE", "—",
 "A written guide; the DM carries the link.",
 "Low build cost. Buys the right to be longer than a DM and to be updated after the fact without re-wiring anything.", "", "user 2026-08-04"),

("FT3", "TYPE", "LONG-FORM", "YOU", "—",
 "A video the DM links to. The selling happens inside it.",
 "High build cost — the fulfilment asset is a full production in its own right. Do not promise this rung until the video exists.", "", "user 2026-08-04"),

("FT4", "TYPE", "LINK ONLY", "CLAUDE", "—",
 "Routes to a page, a booking or an affiliate link.",
 "No artifact — and still NOT free. The DM sequence carrying the link is written work and it is where the pitch actually lives. Treat the copy as an asset with its own status, or the rung ships as a bare link and converts like one.",
 "The DM monologue IS the deliverable.", "user 2026-08-04"),

"GATES — the vetoes. These fire regardless of format, rung or character.",

("G1", "GATE", "No keyword ships without fulfilment", "YOU", STOP,
 "A comment that lands on a dead keyword is a burned lead and a spent hook.",
 "The single most expensive failure in the pipeline, because it costs the thing that is hardest to make: a viewer who was willing to act. Blocks posting, not drafting — write the script first, wire the keyword before it goes up.",
 "", "user 2026-08-04"),

("G2", "GATE", "One gate per video. Two only at different depths.", "YOU", CHECK,
 "Two asks at the same depth split the comment section and neither trips the threshold.",
 "R1 and R3 can coexist because they serve different people — the cold viewer takes R1, the warm one takes R3. R1 and R2 cannot, because they are the same viewer offered the same thing at two prices. R0 always stacks free.",
 "", "user 2026-08-04"),

("G3", "GATE", "A keyword must be a word nobody types by accident", "YOU", CHECK,
 "Organic comments will fire a common word and poison the list.",
 "YES · OK · HOW · THIS all appear unprompted in any healthy comment section, and every false fire costs a DM send and pollutes the segment. Prefer a NOUN tied to the ask — the word should be unusable in a normal sentence about the video.",
 "PROMPT · BRAND · MAP  —  not  YES · OK · HOW", "user 2026-08-04"),

("G4", "GATE", "Name the job or the outcome, never the technology", "CLAUDE", "—",
 "Hooks and overlays naming the tech lost to ones naming a job by ~33× on an identical rig.",
 "\"Did the work of an entire marketing team\" is the shape that wins. The name of the system is the shape that loses. Applies to the HOOK and the OVERLAY — naming tools in the BODY of a tutorial is the value and is not covered by this gate.",
 "", "Format Research"),

("G5", "GATE", "Format sets the ceiling, rung sets the depth", "CLAUDE", "—",
 "They are independent dials. Never pick a rung to fix a format problem.",
 "A tutorial carrying an R3 gate is still a tutorial and will still land near the tutorial median. If the problem is reach, change the format. If the problem is revenue per view, change the rung. Mixing them up produces videos that do neither.",
 "", "canvas/pipeline.md"),

("G6", "GATE", "An A/B split changes exactly one thing", "YOU", CHECK,
 "Same body, one differing close — or the result reads nothing.",
 "This is the same single-variable discipline the research protocol uses to isolate drivers. Two videos differing in hook AND close produce a number nobody can act on.",
 "", "Research Rules"),
]


def cell(v, bold=False, size=9, color=None, bg=None, wrap="WRAP", va="TOP", ha="LEFT"):
    s = "" if v is None else str(v)
    return {"userEnteredValue": {"stringValue": s},
            "userEnteredFormat": {"backgroundColor": bg or PAPER, "horizontalAlignment": ha,
                                  "verticalAlignment": va, "wrapStrategy": wrap,
                                  "textFormat": {"bold": bold, "fontSize": size,
                                                 "foregroundColor": color or TEXT}}}


def height(r):
    """Content-aware, capped — a flat height made Research Rules unreadable."""
    longest = max((len(str(x)) for x in r[5:8]), default=0)
    return max(34, min(104, 20 + 20 * (longest // 78 + 1)))


def build():
    rows, heights, merges = [], [], []

    def add(vals, h, merge_full=False):
        rows.append({"values": vals + [cell("") for _ in range(NCOLS - len(vals))]})
        heights.append(h)
        if merge_full:
            merges.append(len(rows) - 1)

    add([cell(x, bold=True, size=9, bg=HEADROW) for x in HEADERS], 30)
    for r in ROWS:
        if isinstance(r, str):
            add([cell(r, bold=True, size=10, color=PAPER, bg=INK)], 26, merge_full=True)
            continue
        tint = TINT.get(r[1], PAPER)
        gate = r[4] not in ("—", "")
        add([cell(r[0], bold=True, bg=tint, ha="CENTER", va="MIDDLE"),
             cell(r[1], size=8, bg=tint, ha="CENTER", va="MIDDLE"),
             cell(r[2], bold=True),
             cell(r[3], size=8, ha="CENTER", va="MIDDLE", color=MUTE),
             cell(r[4], bold=gate, size=8, ha="CENTER", va="MIDDLE",
                  bg=TINT["GATE"] if gate else None),
             cell(r[5]), cell(r[6], color=MUTE), cell(r[7]), cell(r[8], size=8, color=MUTE)],
            height(r))
    return rows, heights, merges


def main():
    ap = argparse.ArgumentParser(description="Build the Pipeline Rules tab")
    ap.add_argument("--rebuild", action="store_true", help="replace the tab (DISCARDS edits)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows, heights, merges = build()
    banners = sum(1 for r in ROWS if isinstance(r, str))
    if a.dry_run:
        print(f"[dry-run] {TAB}: {len(rows)} rows · {len(ROWS) - banners} entries · "
              f"{banners} sections")
        for r in ROWS:
            print(f"    §  {r}" if isinstance(r, str) else
                  f"  {r[0]:<5} {r[1]:<8} {r[2][:58]}")
        return

    svc = gs.get_sheets_service()
    info = svc.spreadsheets().get(spreadsheetId=MASTER_DB_ID).execute()
    ex = {s["properties"]["title"]: s["properties"]["sheetId"] for s in info["sheets"]}
    if TAB in ex:
        if not a.rebuild:
            sys.exit(f"'{TAB}' exists — pass --rebuild (DISCARDS any edits made in the tab).")
        svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={
            "requests": [{"deleteSheet": {"sheetId": ex[TAB]}}]}).execute()

    # Append after whatever tabs already exist, rather than a hardcoded index —
    # a fresh Master DB with only "Database" doesn't have the same tab layout
    # this script's original spreadsheet did, and a fixed index fails with
    # "index too high" as soon as the spreadsheet has fewer tabs than that.
    index = len(info["sheets"]) - (1 if TAB in ex else 0)

    res = svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={"requests": [
        {"addSheet": {"properties": {"title": TAB, "index": index, "gridProperties": {
            "rowCount": len(rows) + 120, "columnCount": NCOLS,
            "frozenRowCount": 1}}}}]}).execute()
    gid = res["replies"][0]["addSheet"]["properties"]["sheetId"]

    svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={"requests": [
        {"updateCells": {"rows": rows, "fields": "userEnteredValue,userEnteredFormat",
                         "start": {"sheetId": gid, "rowIndex": 0, "columnIndex": 0}}}]}).execute()

    reqs = [{"mergeCells": {"range": {"sheetId": gid, "startRowIndex": i, "endRowIndex": i + 1,
                                     "startColumnIndex": 0, "endColumnIndex": NCOLS},
                            "mergeType": "MERGE_ALL"}} for i in merges]
    reqs += [{"updateDimensionProperties": {
        "range": {"sheetId": gid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}} for i, px in enumerate(WIDTHS)]
    reqs += [{"updateDimensionProperties": {
        "range": {"sheetId": gid, "dimension": "ROWS", "startIndex": i, "endIndex": i + 1},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}} for i, px in enumerate(heights)]
    svc.spreadsheets().batchUpdate(spreadsheetId=MASTER_DB_ID, body={"requests": reqs}).execute()

    print(f"✅ {TAB} — {len(rows)} rows · {len(ROWS) - banners} entries · {banners} sections")


if __name__ == "__main__":
    main()
