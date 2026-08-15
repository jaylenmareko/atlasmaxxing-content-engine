#!/usr/bin/env python3
"""Clip map — label a reference video frame by frame, then render it into a canvas.

The mechanism is character-agnostic. It reads the character -> canvas pointer from
config/characters.json and never contains character or brand values itself.

Three model passes, then arithmetic:

  1. TRANSCRIBE   speech with timestamps, independent of frames
  2. SECOND PASS  the shots the scene detector missed (rules/base.md: the storyboard is a
                  draft). Missing frames are extracted with ffmpeg and registered in the
                  pool, so the fix is permanent rather than per-run.
  3. LABEL        gen_group per frame — a visual judgement, the only one left to the model

  then ALIGN      speech onto frames by timestamp overlap, in code, not by model judgement

Dialogue drifting onto the wrong frame is almost always a MISSING FRAME, not a bad
alignment: with no frame to carry it, ten seconds of speech piles onto whatever frame
precedes the gap. Fix the frames and the dialogue follows.

  NEW IMAGE     a fresh generation. The default.
  CONTINUATION  chained off the frame above — only when it cannot be described from
                scratch. Capped at MAX_CHAIN; overflow is re-anchored automatically.
  SAME IMAGE    one still, animated. No generation at all.

Usage:
  python3 clip_map.py --row 818 --character example --v 127
  python3 clip_map.py --row 818 --character example --v 127 --dry-run
  python3 clip_map.py --row 818 --character example --v 127 --no-second-pass
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
LIB = Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(LIB))

import engine_config as cfg          # noqa: E402
import drive_utils as du             # noqa: E402
from gemini_pass import upload_to_gemini, analyze   # noqa: E402
from google_sheets import get_sheets_service        # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character_assets import col_letter             # noqa: E402

CHARACTERS = ENGINE_ROOT / "config" / "characters.json"
MAX_CHAIN = 3          # rules/base.md, HARD. Hop 4+ visibly degrades.
NEAR_DUPLICATE_S = 1.0 # a "missed" shot this close to a frame we hold is the same shot

TRANSCRIBE_PROMPT = """Transcribe this video's speech with timestamps. One entry per natural
clause or sentence — split where a speaker would draw breath, not into paragraphs.

Return ONLY a JSON array, no markdown fence:
[{"start": 0.8, "end": 3.4, "text": "...", "text_en": "..."}]

start/end are seconds. `text` is as spoken, in its own language. `text_en` is an English
translation — repeat `text` verbatim if it is already English. Be precise on start times;
they are used to map speech onto frames."""

MISSED_PROMPT = """This video's scene-change detector produced frames at these timestamps
only:
{stamps}
The video is {duration:.1f}s long.

The detector is known to miss shots. Find every DISTINCT SHOT it missed — a moment where
the framing, the action, or what is on screen changes enough that recreating this video
would need its own generated image for it.

Check EVERY interval between consecutive timestamps, not just the long ones. A 3-second gap
covering two separate actions is a miss just as much as a 10-second gap is.

Do NOT report a timestamp that merely re-describes a frame already in the list above. If a
shot is already represented, skip it. Only genuinely absent shots.

Return ONLY a JSON array, no fence:
[{{"timestamp": 20.4, "note": "what is on screen", "why_distinct": "what changed"}}]
Return [] if nothing was missed."""

REALIGN_PROMPT = """Speech has been mapped onto this video's frames by timestamp alone. That
gets boundaries wrong in two ways, and you are fixing both by WATCHING the video.

1. A line is spoken slightly BEFORE the shot that shows it. "Add the juice of two lemons"
   may start while the previous shot is still on screen, but it belongs to the frame where
   the lemons are actually squeezed. Put each line on the frame that SHOWS what it describes.
2. One sentence can span a cut. "and one glass of water and blend for one minute" is two
   beats across two shots — SPLIT it at the cut and give each frame its half.

Current mapping (frame · timestamp · what is on screen · dialogue as assigned now):
{proposed}

The full transcript, in order:
{transcript}

HARD CONSTRAINT: every word of the transcript must appear exactly once across your output,
in the same order. Do not reword, translate, add or drop anything. A frame with no speech
over it gets "". Splitting is allowed; duplicating is not.

Return ONLY a JSON array, one object per frame in the same order, no fence:
[{{"frame": "scene_01_0.8s.jpg", "dialogue": "...", "dialogue_en": "..."}}]"""

LABEL_PROMPT = """You are shown {n} still frames from one video, IN ORDER. Image 1 is frame
1, image 2 is frame 2, and so on. Classify EVERY frame by comparing it to the image
IMMEDIATELY BEFORE it. Frame 1 has nothing before it, so it is always NEW IMAGE.

Judge only from the images in front of you. Do not reason from timestamps or from the script.

The ONLY question is: how different does this frame LOOK from the frame immediately above it?

  SAME IMAGE    It looks essentially identical to the frame above — same framing, same pose,
                same props, same position in the room. Nothing moved enough to see. One
                generation, animated, produces both frames. NO new generation at all.
                Two talking-head frames of the same person in the same chair are SAME IMAGE
                even if different words are spoken over them.

  CONTINUATION  The SAME physical setup as the frame above — same table, same room, same
                props, same wardrobe — but the picture has changed. Hands moved, an object
                is now cut open, a blender that was still is now running, water that was
                clear has gone cloudy. **A tighter or wider framing on that same setup is
                CONTINUATION too** — zooming in on the jar does not make it a new scene.
                One still cannot serve both, so it needs its own generation, chained off the
                frame above.

                Reveal shots are almost always CONTINUATION: the payoff of a demonstration
                is the same set with a changed result in it.

  NEW IMAGE     A scene you would have to BUILD FROM SCRATCH. Different location, different
                furniture, different wardrobe, or the subject has moved somewhere else.
                Nothing in the frame above helps produce it.

The test for NEW IMAGE is not "does this look different" — it is "would I have to construct
a different scene." If the camera could have stayed where it was and the set is the same,
it is NOT a NEW IMAGE, however much the contents changed.

Also give a short `note` on what is on screen.

Return ONLY a JSON array of exactly {n} objects, one per image, in the same order, no fence:
[{{"i": 1, "gen_group": "NEW IMAGE", "note": "..."}}]"""


# ── data in ────────────────────────────────────────────────────────────────────

def load_character(slug: str) -> dict:
    chars = json.loads(CHARACTERS.read_text(encoding="utf-8"))["characters"]
    if slug not in chars:
        raise KeyError(f"Unknown character {slug!r}. Known: {', '.join(chars) or '(none)'}")
    return chars[slug]


def frame_time(name: str) -> float:
    """scene_07a_25.2s.jpg -> 25.2. The timestamp is the only reliable ordering key."""
    m = re.search(r"_([\d.]+)s", name)
    return float(m.group(1)) if m else 0.0


def pool_folder(row: int) -> tuple[object, str]:
    drive = du.get_drive_service()
    root = du.folder_path(drive, cfg.POOL_FOLDER_NAME, root=cfg.IM_FOLDER_ID)
    q = (f"name='Row {row:04d}' and '{root}' in parents "
         f"and mimeType='{du.FOLDER_MIME}' and trashed=false")
    hits = drive.files().list(q=q, fields="files(id)").execute().get("files", [])
    if not hits:
        raise RuntimeError(f"Row {row} is not in the pool — run pull_video.py first.")
    return drive, hits[0]["id"]


def pool_frames(row: int) -> tuple[list[dict], str, dict, str]:
    drive, folder = pool_folder(row)
    manifest = du.read_manifest(drive, folder)
    frames = sorted(manifest["frames"], key=lambda f: frame_time(f["name"]))
    return frames, manifest.get("link", ""), manifest, folder


def video_duration(video: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


def ask_json(uri: str, prompt: str, what: str) -> list:
    for attempt in (1, 2):
        out = analyze(uri, prompt)
        if not out:
            raise RuntimeError(f"Gemini returned nothing for {what}.")
        try:
            return parse_entries(out)
        except ValueError as e:
            print(f"  ⚠️ unparseable {what} (attempt {attempt}): {e}", file=sys.stderr)
    raise RuntimeError(f"Gemini would not return valid JSON for {what}.")


def parse_entries(out: str) -> list:
    out = re.sub(r"^```(?:json)?\s*|\s*```$", "", out.strip(), flags=re.M).strip()
    start, end = out.find("["), out.rfind("]")
    if start == -1 or end <= start:
        raise ValueError("no JSON array in response")
    try:
        entries = json.loads(out[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(str(e)) from e
    if not isinstance(entries, list):
        raise ValueError("response was not an array")
    return entries


# ── second pass ───────────────────────────────────────────────────────────────

def extract_and_register(row: int, video: Path, missed: list[dict],
                         frames: list[dict], manifest: dict, folder: str) -> list[dict]:
    """Cut the missing shots out of the video, park them in the pool beside the frames
    intake produced, and record them in the manifest so the fix outlives this run."""
    if not missed:
        return frames
    drive = du.get_drive_service()
    added = []
    have = [frame_time(f["name"]) for f in frames]
    with tempfile.TemporaryDirectory() as tmp:
        for m in missed:
            ts = float(m["timestamp"])
            # the detector is stochastic; never re-add a shot we already hold
            if any(abs(ts - t) < NEAR_DUPLICATE_S for t in have):
                print(f"  · {ts:.1f}s already covered — skipped", file=sys.stderr)
                continue
            have.append(ts)
            name = f"scene_2p_{ts:.1f}s.jpg"      # timestamp keys the name, so re-runs
            if any(f["name"] == name for f in frames):   # cannot collide or duplicate
                continue
            local = Path(tmp) / name
            r = subprocess.run(["ffmpeg", "-y", "-ss", str(ts), "-i", str(video),
                                "-frames:v", "1", "-q:v", "2", str(local)],
                               capture_output=True)
            if r.returncode != 0 or not local.exists():
                print(f"  ⚠️ ffmpeg failed at {ts}s", file=sys.stderr)
                continue
            meta = du.upload_public(local, name, folder, "image/jpeg")
            if not meta:
                continue
            added.append({"name": name, "id": meta["id"]})
            print(f"  ＋ {name}  {m.get('note', '')[:56]}", file=sys.stderr)

    if added:
        manifest["frames"] = sorted(manifest["frames"] + added,
                                    key=lambda f: frame_time(f["name"]))
        old = drive.files().list(
            q=f"name='manifest.json' and '{folder}' in parents and trashed=false",
            fields="files(id)").execute().get("files", [])
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "manifest.json"
            p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            du.upload_file(str(p), "manifest.json", folder, "application/json")
        for f in old:
            drive.files().delete(fileId=f["id"]).execute()
        frames = manifest["frames"]
    return frames


# ── alignment, in code ────────────────────────────────────────────────────────

def assign_dialogue(frames: list[dict], utterances: list[dict],
                    duration: float) -> dict[str, list[dict]]:
    """Each frame owns [its timestamp, the next frame's timestamp). An utterance goes to the
    frame it OVERLAPS MOST, which survives the half-second jitter between a cut and the
    speech around it. No model judgement involved."""
    stamps = [frame_time(f["name"]) for f in frames]
    bounds = [(stamps[i], stamps[i + 1] if i + 1 < len(stamps) else max(duration, stamps[-1] + 1))
              for i in range(len(stamps))]
    out: dict[str, list[dict]] = {f["name"]: [] for f in frames}
    for u in utterances:
        s, e = float(u.get("start", 0)), float(u.get("end", 0))
        if e <= s:
            e = s + 0.1
        best, best_overlap = 0, -1.0
        for i, (a, b) in enumerate(bounds):
            overlap = min(e, b) - max(s, a)
            if overlap > best_overlap:
                best, best_overlap = i, overlap
        out[frames[best]["name"]].append(u)
    return out


def label_frames(frames: list[dict], v_folder: Path) -> list[dict]:
    """Classify gen_group from the FRAMES THEMSELVES, sent in order as images.

    Asking the model to judge a frame from the video plus a timestamp fails: on 821 every
    NEW IMAGE landed one frame early, on the last shot of the old scene rather than the
    first of the new one. It was inferring the moment instead of looking at it. Sending the
    stills removes the inference, and positional indexing removes the filename matching."""
    import base64
    import os
    import requests

    key = os.getenv("GEMINI_API_KEY")
    parts: list[dict] = []
    for f in frames:
        local = v_folder / "frames" / f["name"]
        if not local.exists():                       # second-pass frames live in the pool
            local = Path(tempfile.gettempdir()) / f["name"]
            du.download_file(f["id"], str(local))
        parts.append({"inlineData": {"mimeType": "image/jpeg",
                                     "data": base64.b64encode(local.read_bytes()).decode()}})
    parts.append({"text": LABEL_PROMPT.format(n=len(frames))})

    # Same model/retry fix as lib/gemini_pass.py's analyze() — this call is
    # a separate direct request, not routed through that function, so it
    # needed the identical fix applied a second time. See that file's MODEL
    # comment: gemini-2.5-flash 404s for this key as of 2026-08, and 503
    # "high demand" is common enough to need a retry, not just a raise.
    r = None
    for attempt in range(4):
        r = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-flash-latest:generateContent?key={key}",
            json={"contents": [{"parts": parts}],
                  "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}},
            timeout=300)
        if r.status_code == 200:
            break
        if r.status_code in (429, 500, 503) and attempt < 3:
            delay = 3.0 * (2 ** attempt)
            print(f"  ⚠️ label pass {r.status_code} — retrying in {delay:.0f}s "
                  f"(attempt {attempt + 2}/4)", file=sys.stderr)
            time.sleep(delay)
            continue
        break
    if r.status_code != 200:
        raise RuntimeError(f"label pass failed: {r.status_code} {r.text[:200]}")
    text = "".join(p.get("text", "")
                   for p in r.json()["candidates"][0]["content"]["parts"])
    labels = parse_entries(text)
    if len(labels) != len(frames):
        raise RuntimeError(f"got {len(labels)} labels for {len(frames)} frames")
    for i, (f, l) in enumerate(zip(frames, labels), 1):
        l["frame"] = f["name"]                        # positional, never name-matched
        l["i"] = i
    return labels


def words(s: str) -> list[str]:
    return re.findall(r"[^\W_]+", (s or "").lower(), flags=re.UNICODE)


def covers_transcript(utterances: list[dict], assigned: list[str]) -> bool:
    """Every word of the transcript, exactly once, in order. This is what makes it safe to
    let the model move dialogue around: it can re-cut the boundaries but cannot invent,
    drop or duplicate a word. 820's repeated-tail bug would fail this check."""
    want = [w for u in utterances for w in words(u.get("text", ""))]
    got = [w for a in assigned for w in words(a)]
    return want == got


def realign(uri: str, frames: list[dict], entries: list[dict],
            utterances: list[dict]) -> list[dict]:
    """Code proposes by timestamp; the model corrects by what is on screen. Alignment is
    partly semantic — a line is often spoken a beat before the shot it describes — so pure
    arithmetic gets it wrong. Rejected if it fails the coverage check."""
    proposed = "\n".join(
        f"  {e['frame']} · {e['timestamp']:.1f}s · {e.get('note', '')[:70]} · "
        f"\"{e.get('dialogue', '')}\"" for e in entries)
    transcript = "\n".join(f"  {u['start']:.1f}-{u['end']:.1f}  {u.get('text', '')}"
                           for u in utterances)
    try:
        fixed = ask_json(uri, REALIGN_PROMPT.format(proposed=proposed,
                                                    transcript=transcript), "realignment")
    except RuntimeError as e:
        print(f"  ⚠️ realign failed ({e}) — keeping timestamp alignment", file=sys.stderr)
        return entries

    by_frame = {f.get("frame"): f for f in fixed}
    candidate = [by_frame.get(e["frame"], {}).get("dialogue", "") for e in entries]
    if not covers_transcript(utterances, candidate):
        print("  ⚠️ realignment lost or duplicated words — keeping timestamp alignment",
              file=sys.stderr)
        return entries

    moved = 0
    for e, new in zip(entries, candidate):
        if (e.get("dialogue") or "").strip() != (new or "").strip():
            moved += 1
        e["dialogue"] = new or ""
        e["dialogue_en"] = by_frame.get(e["frame"], {}).get("dialogue_en", "") or ""
    print(f"  ↔ realigned: {moved} frame(s) re-cut against the visuals", file=sys.stderr)
    return entries


def enforce_chain_cap(entries: list[dict]) -> list[dict]:
    """No chain deeper than MAX_CHAIN survives. Overflow is re-anchored to a fresh
    generation — rules/base.md calls this hard, so it is applied, not warned about."""
    depth = 0
    for e in entries:
        g = (e.get("gen_group") or "").upper()
        if g == "NEW IMAGE":
            depth = 0
        elif g == "CONTINUATION":
            depth += 1
            if depth > MAX_CHAIN:
                e["gen_group"] = "NEW IMAGE"
                e["re_anchored"] = True
                depth = 0
        e["chain_depth"] = depth
    return entries


# ── the function ──────────────────────────────────────────────────────────────

def build_clip_map(row: int, v_folder: Path, second_pass: bool = True,
                   dry_run: bool = False) -> list[dict]:
    """Label a reference video frame by frame. Returns data — the sheet is one rendering."""
    video = v_folder / "reference.mp4"
    if not video.exists():
        raise RuntimeError(f"No reference.mp4 in {v_folder} — run pull_video.py first.")

    frames, link, manifest, folder = pool_frames(row)
    duration = video_duration(video)
    uri = upload_to_gemini(video)
    if not uri:
        raise RuntimeError("Gemini upload failed.")

    utterances = ask_json(uri, TRANSCRIBE_PROMPT, "transcript")
    utterances.sort(key=lambda u: float(u.get("start", 0)))
    print(f"  🎙  {len(utterances)} utterances", file=sys.stderr)

    if second_pass:
        stamps = ", ".join(f"{frame_time(f['name']):.1f}" for f in frames)
        missed = ask_json(uri, MISSED_PROMPT.format(stamps=stamps, duration=duration),
                          "missed shots")
        if dry_run:
            # extraction mutates the pool manifest — a dry run must not touch it
            print(f"  🔍 second pass: {len(missed)} shot(s) would be added "
                  f"(dry run — pool untouched)", file=sys.stderr)
        else:
            before = len(frames)
            frames = extract_and_register(row, video, missed, frames, manifest, folder)
            print(f"  🔍 second pass: {len(frames) - before} frame(s) added "
                  f"({before} → {len(frames)})", file=sys.stderr)

    labels = label_frames(frames, v_folder)
    by_frame = {l["frame"]: l for l in labels}

    spoken = assign_dialogue(frames, utterances, duration)
    entries = []
    for f in frames:
        lines = spoken[f["name"]]
        lab = by_frame.get(f["name"], {})
        entries.append({
            "frame": f["name"],
            "timestamp": frame_time(f["name"]),
            "file_id": f["id"],
            "dialogue": " ".join(u.get("text", "").strip() for u in lines).strip(),
            "dialogue_en": " ".join(u.get("text_en", "").strip() for u in lines).strip(),
            "gen_group": lab.get("gen_group", "NEW IMAGE"),
            "note": lab.get("note", ""),
        })
    entries = realign(uri, frames, entries, utterances)
    return enforce_chain_cap(entries), link


# ── the view ──────────────────────────────────────────────────────────────────

def dialogue_cell(e: dict) -> str:
    src, en = (e.get("dialogue") or "").strip(), (e.get("dialogue_en") or "").strip()
    if not src:
        return ""
    return src if not en or en == src else f"{src}\n({en})"


def image_formula(file_id: str) -> str:
    return (f'=IMAGE("https://drive.google.com/thumbnail?id={file_id}&sz=w1000", 1)'
            if file_id else "")


def write_block(char: dict, row: int, entries: list[dict], link: str,
                v: int | None = None, row_height: int = 110) -> int:
    """Render the clip map into the character's canvas. Fills an existing stub for this row
    if there is one, otherwise appends a fresh block below everything."""
    svc = get_sheets_service()
    sid, tab = char["spreadsheet_id"], char["tab"]
    info = svc.spreadsheets().get(spreadsheetId=sid).execute()
    gid = next(s["properties"]["sheetId"] for s in info["sheets"]
               if s["properties"]["title"] == tab)

    # the block's left edge is wherever the CLIP MAPS banner sits — the header band above
    # gains and loses columns as the character fills in, so never assume column A
    grid = svc.spreadsheets().values().get(
        spreadsheetId=sid, range=f"'{tab}'!A:D").execute().get("values", [])
    col0 = next((j for r in grid for j, c in enumerate(r)
                 if str(c).strip().upper().startswith("CLIP MAPS")), 0)
    stub = next((i + 1 for i, r in enumerate(grid)
                 if len(r) > col0 and str(r[col0]).startswith(f"ROW {row}")), None)
    banner = next((i + 1 for i, r in enumerate(grid)
                   if len(r) > col0 and str(r[col0]).strip().upper().startswith("CLIP MAPS")), None)

    if stub:
        header_row = stub
    elif banner:
        # NEWEST FIRST (user, 2026-07-30). Open a gap directly under the CLIP MAPS banner and
        # write the new block there, so the most recent video is the one you land on rather
        # than the one you have to scroll past everything to reach.
        need = len(entries) + 3                        # header + column row + rows + spacer
        svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": [
            {"insertDimension": {"range": {"sheetId": gid, "dimension": "ROWS",
                                           "startIndex": banner, "endIndex": banner + need},
                                 "inheritFromBefore": False}}]}).execute()
        header_row = banner + 1
    else:
        header_row = len(grid) + 3                     # no banner yet, fall back to appending
    first_col = col_letter(col0)

    label = f"ROW {row}" + (f"   ·   V{v}" if v else "") + (f"   —   {link}" if link else "")
    values = [
        [label],
        ["Frame", "Source Dialogue", "Gen Group", "References In",
         "Image Prompt", "Our Image", "Video Prompt", "Approved"],
    ] + [
        # gen group carries the frame's position and timestamp underneath it, so a beat can
        # be checked against the video without opening the V-folder
        [image_formula(e.get("file_id")), dialogue_cell(e),
         f"{e.get('gen_group', '')}\n{n:02d} · {e.get('timestamp', 0):.1f}s",
         "", "", "", "", ""]
        for n, e in enumerate(entries, 1)
    ]
    svc.spreadsheets().values().update(
        spreadsheetId=sid, range=f"'{tab}'!{first_col}{header_row}",
        valueInputOption="USER_ENTERED", body={"values": values}).execute()

    first, last = header_row + 2, header_row + 1 + len(entries)
    blue = {"red": 0.812, "green": 0.886, "blue": 0.953}
    grey = {"red": 0.851, "green": 0.851, "blue": 0.851}
    svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": [
        # blue block header, grey column header — the break that separates one video
        # from the next when the canvas is hundreds of rows long
        {"mergeCells": {
            "range": {"sheetId": gid, "startRowIndex": header_row - 1, "endRowIndex": header_row,
                      "startColumnIndex": col0, "endColumnIndex": col0 + 8},
            "mergeType": "MERGE_ALL"}},
        {"repeatCell": {
            "range": {"sheetId": gid, "startRowIndex": header_row - 1, "endRowIndex": header_row,
                      "startColumnIndex": col0, "endColumnIndex": col0 + 8},
            "cell": {"userEnteredFormat": {"backgroundColor": blue,
                     "textFormat": {"bold": True, "fontSize": 11},
                     "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)"}},
        {"repeatCell": {
            "range": {"sheetId": gid, "startRowIndex": header_row, "endRowIndex": header_row + 1,
                      "startColumnIndex": col0, "endColumnIndex": col0 + 8},
            "cell": {"userEnteredFormat": {"backgroundColor": grey,
                     "textFormat": {"bold": True, "fontSize": 10},
                     "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": gid, "dimension": "ROWS",
                      "startIndex": header_row - 1, "endIndex": header_row},
            "properties": {"pixelSize": 26}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": gid, "dimension": "ROWS",
                      "startIndex": header_row, "endIndex": header_row + 1},
            "properties": {"pixelSize": 22}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": gid, "dimension": "ROWS",
                      "startIndex": first - 1, "endIndex": last},
            "properties": {"pixelSize": row_height}, "fields": "pixelSize"}},
        # Data rows must be reset to white and not-bold, not just wrapped. The rows are opened
        # with insertDimension inheritFromBefore=False, so they inherit the format of the row
        # BELOW — which is the previous block's blue bold banner. Without this the whole new
        # block comes out banner-coloured. Runs to +13 because the five hand-added columns
        # (Final Script · Reference 2 · Reference 3 · Notes · Captions) inherit it too.
        {"repeatCell": {
            "range": {"sheetId": gid, "startRowIndex": first - 1, "endRowIndex": last,
                      "startColumnIndex": col0, "endColumnIndex": col0 + 13},
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP",
                                           "verticalAlignment": "TOP",
                                           "backgroundColor": {"red": 1, "green": 1, "blue": 1},
                                           "textFormat": {"bold": False}}},
            "fields": "userEnteredFormat(wrapStrategy,verticalAlignment,backgroundColor,"
                      "textFormat.bold)"}},
    ]}).execute()
    return header_row


def relabel(row: int, v_folder: Path) -> list[dict]:
    """Re-run ONLY the gen_group pass and rewrite that column. Dialogue the user has already
    reviewed is never touched — gen_group is the part that gets refined as the rules sharpen."""
    video = v_folder / "reference.mp4"
    frames, link, _, _ = pool_frames(row)
    uri = upload_to_gemini(video)
    if not uri:
        raise RuntimeError("Gemini upload failed.")
    labels = label_frames(frames, v_folder)
    by_frame = {l["frame"]: l for l in labels}
    entries = [{"frame": f["name"], "timestamp": frame_time(f["name"]),
                "gen_group": by_frame.get(f["name"], {}).get("gen_group", "NEW IMAGE"),
                "note": by_frame.get(f["name"], {}).get("note", "")} for f in frames]
    return enforce_chain_cap(entries)


def write_gen_groups(char: dict, row: int, entries: list[dict]) -> int:
    """Rewrite only the Gen Group column of an existing block."""
    svc = get_sheets_service()
    sid, tab = char["spreadsheet_id"], char["tab"]
    grid = svc.spreadsheets().values().get(
        spreadsheetId=sid, range=f"'{tab}'!A:D").execute().get("values", [])
    col0 = next((j for r in grid for j, c in enumerate(r)
                 if str(c).strip().upper().startswith("CLIP MAPS")), 0)
    stub = next((i + 1 for i, r in enumerate(grid)
                 if len(r) > col0 and str(r[col0]).startswith(f"ROW {row}")), None)
    if not stub:
        raise RuntimeError(f"No block for row {row} in '{tab}'")
    first = stub + 2
    col = col_letter(col0 + 2)
    svc.spreadsheets().values().update(
        spreadsheetId=sid, range=f"'{tab}'!{col}{first}",
        valueInputOption="USER_ENTERED",
        body={"values": [[f"{e['gen_group']}\n{n:02d} · {e['timestamp']:.1f}s"]
                         for n, e in enumerate(entries, 1)]}).execute()
    return first


def main():
    ap = argparse.ArgumentParser(description="Label a reference video and render its clip map")
    ap.add_argument("--row", type=int, required=True)
    ap.add_argument("--character", required=True, help="slug from config/characters.json")
    ap.add_argument("--v", type=int, help="V number, for the block label")
    ap.add_argument("--v-folder", help="override the local V-folder path")
    ap.add_argument("--no-second-pass", action="store_true",
                    help="skip missed-shot detection and frame extraction")
    ap.add_argument("--dry-run", action="store_true", help="print the data, write nothing")
    ap.add_argument("--relabel", action="store_true",
                    help="re-run gen_group only, leaving reviewed dialogue untouched")
    args = ap.parse_args()

    char = load_character(args.character)
    if args.v_folder:
        v_folder = Path(args.v_folder)
    else:
        cc = cfg.creator(args.character)
        v_folder = cc["folder"] / f"V{args.v}" if args.v else cc["folder"]

    if args.relabel:
        entries = relabel(args.row, v_folder)
        counts: dict[str, int] = {}
        for e in entries:
            counts[e["gen_group"]] = counts.get(e["gen_group"], 0) + 1
        base = counts.get("NEW IMAGE", 0) + counts.get("CONTINUATION", 0)
        print(json.dumps([{k: e[k] for k in ("frame", "gen_group", "note")}
                          for e in entries], indent=2))
        print(f"\n{len(entries)} frames → {base} base images   {counts}", file=sys.stderr)
        if not args.dry_run:
            at = write_gen_groups(char, args.row, entries)
            print(f"gen groups rewritten from row {at}", file=sys.stderr)
        return

    entries, link = build_clip_map(args.row, v_folder,
                                   second_pass=not args.no_second_pass,
                                   dry_run=args.dry_run)
    print(json.dumps(entries, indent=2, ensure_ascii=False))

    counts: dict[str, int] = {}
    for e in entries:
        counts[e.get("gen_group", "?")] = counts.get(e.get("gen_group", "?"), 0) + 1
    base = counts.get("NEW IMAGE", 0) + counts.get("CONTINUATION", 0)
    re_anchored = sum(1 for e in entries if e.get("re_anchored"))
    print(f"\n{len(entries)} frames → {base} base images   {counts}", file=sys.stderr)
    if re_anchored:
        print(f"  ↩ {re_anchored} frame(s) re-anchored — chain hit the "
              f"{MAX_CHAIN}-deep limit", file=sys.stderr)

    if not args.dry_run:
        at = write_block(char, args.row, entries, link, v=args.v)
        print(f"written to '{char['tab']}' at row {at}", file=sys.stderr)


if __name__ == "__main__":
    main()
