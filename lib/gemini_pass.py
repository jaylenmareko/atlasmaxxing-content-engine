#!/usr/bin/env python3
"""Gemini video pass — Step 1 of the Performance Driver Analysis Protocol.

Fetches a research video from the Drive assets folder (API fetch — never the
Drive web UI, which blocks direct downloads), uploads it to the Gemini files
API, runs the 7-section analyst prompt, and appends the output to the row's
Notes column in the working tab.

Usage:
  python3 gemini_pass.py --creator iceman.healer --tag g03 --row 4
  python3 gemini_pass.py --creator iceman.healer --all          # every tagged row
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import requests

import engine_config as cfg
import drive_utils as du

sys.path.insert(0, str(cfg.CONTENT_ENGINE_EXEC))
from google_sheets import read_sheet, write_range  # noqa: E402
from dotenv import load_dotenv                      # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# "gemini-2.5-flash" (the original pinned version) returns 404 "no longer
# available to new users" as of 2026-08 — confirmed live against this key.
# "gemini-flash-latest" (the non-lite alias) is accepted but was hitting
# sustained 503 "high demand" — 4/4 retries failed live. "-lite" answered
# cleanly on the first try. Worth revisiting if demand eases or output
# quality on the labeling/transcription tasks turns out to need the
# heavier model — this was a "what actually works right now" call, not a
# permanent judgment that lite is the better choice long-term.
MODEL = "gemini-flash-lite-latest"

PROMPT = """You are a viral short-form video analyst. Watch this video as a viewer would, then report with timestamps:
1. VIEWER EXPERIENCE — describe the video beat by beat as it's experienced: what happens, what you notice first, where your attention spikes or drifts, the moment you'd scroll away (or why you wouldn't)
2. DELIVERY — vocal tone, cadence, inflection shifts, where energy rises and falls
3. SOUND — music choice, sound design moments, silence usage, audio hooks
4. PACING — real-time rhythm: where it's fast, where it breathes, how cuts feel
5. ON-SCREEN TEXT — timing and interplay with speech (does text lead, lag, or echo the voice?)
6. MOTION — camera movement and subject movement, beat by beat, phrased so it could be reused as a video-generation motion prompt (e.g., "static camera, hands grate seed rhythmically at chest height, slow push-in on bottle at 0:10")
7. ANOMALIES — anything notable that wouldn't show up in static frames or a transcript
Redundancy with a transcript is fine — describe freely. Specific observations with timestamps beat general summaries."""


def upload_to_gemini(file_path: Path) -> str | None:
    size = file_path.stat().st_size
    init = requests.post(
        f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={GEMINI_API_KEY}",
        headers={"X-Goog-Upload-Protocol": "resumable",
                 "X-Goog-Upload-Command": "start",
                 "X-Goog-Upload-Header-Content-Length": str(size),
                 "X-Goog-Upload-Header-Content-Type": "video/mp4",
                 "Content-Type": "application/json"},
        json={"file": {"display_name": file_path.name}})
    upload_url = init.headers.get("X-Goog-Upload-URL")
    if not upload_url:
        print(f"  ⚠️ upload init failed: {init.status_code} {init.text[:200]}")
        return None
    up = requests.post(upload_url,
                       headers={"Content-Length": str(size),
                                "X-Goog-Upload-Offset": "0",
                                "X-Goog-Upload-Command": "upload, finalize"},
                       data=file_path.read_bytes())
    info = up.json().get("file", {})
    uri, name = info.get("uri"), info.get("name")
    if not uri:
        print(f"  ⚠️ upload failed: {up.text[:200]}")
        return None
    for _ in range(45):
        st = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/{name}?key={GEMINI_API_KEY}"
        ).json().get("state")
        if st == "ACTIVE":
            return uri
        if st == "FAILED":
            print("  ⚠️ Gemini file processing failed")
            return None
        time.sleep(2)
    print("  ⚠️ timed out waiting for Gemini file")
    return None


MAX_ATTEMPTS = 4
RETRY_BASE_DELAY = 3.0


def analyze(uri: str, prompt: str = PROMPT) -> str | None:
    # 503 "high demand" is common and genuinely transient — confirmed live,
    # 2 of 3 back-to-back calls hit it before the 3rd succeeded. clip_map.py
    # makes several of these calls per run (transcribe, missed-shot
    # detection, labeling, realign); with no retry, one unlucky 503 anywhere
    # in that chain kills the whole run.
    r = None
    for attempt in range(MAX_ATTEMPTS):
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [
                      {"fileData": {"mimeType": "video/mp4", "fileUri": uri}},
                      {"text": prompt}]}],
                  "generationConfig": {"temperature": 0.3, "maxOutputTokens": 16384}},
            timeout=300)
        if r.status_code == 200:
            break
        if r.status_code in (429, 500, 503) and attempt < MAX_ATTEMPTS - 1:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            print(f"  ⚠️ generateContent {r.status_code} — retrying in {delay:.0f}s "
                  f"(attempt {attempt + 2}/{MAX_ATTEMPTS})")
            time.sleep(delay)
            continue
        break
    if r.status_code != 200:
        print(f"  ⚠️ generateContent failed: {r.status_code} {r.text[:200]}")
        return None
    try:
        parts = r.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError):
        print(f"  ⚠️ unexpected response: {json.dumps(r.json())[:300]}")
        return None


def fetch_video(drive, creator: str, tag: str) -> Path | None:
    assets = du.folder_path(drive, "Format Research", creator, "assets",
                            root=cfg.IM_FOLDER_ID)
    q = (f"name='{tag}' and '{assets}' in parents "
         f"and mimeType='{du.FOLDER_MIME}' and trashed=false")
    hits = drive.files().list(q=q, fields="files(id)").execute().get("files", [])
    if not hits:
        print(f"  ⚠️ no assets folder for {tag}")
        return None
    q2 = f"name='reference.mp4' and '{hits[0]['id']}' in parents and trashed=false"
    vids = drive.files().list(q=q2, fields="files(id)").execute().get("files", [])
    if not vids:
        print(f"  ⚠️ no reference.mp4 in {tag}")
        return None
    dest = Path(tempfile.mkdtemp(prefix=f"gpass_{tag}_")) / "reference.mp4"
    du.download_file(vids[0]["id"], str(dest))
    return dest if dest.exists() else None


def run_one(drive, tab: str, creator: str, tag: str, row: int) -> bool:
    print(f"[{tag}] row {row}", flush=True)
    video = fetch_video(drive, creator, tag)
    if not video:
        return False
    try:
        uri = upload_to_gemini(video)
        if not uri:
            return False
        out = analyze(uri)
        if not out:
            return False
        existing = read_sheet(cfg.MASTER_DB_ID, f"'{tab}'!L{row}")
        prior = existing[0][0] if existing and existing[0] else ""
        text = (prior + "\n\n" if prior.strip() else "") + f"GEMINI PASS ({tag}):\n" + out
        write_range(cfg.MASTER_DB_ID, f"'{tab}'!L{row}", [[text[:48000]]])
        print(f"  ✅ {tag}: {len(out)} chars → Notes", flush=True)
        return True
    finally:
        video.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser(description="Gemini video pass → Notes column")
    ap.add_argument("--creator", required=True)
    ap.add_argument("--tag", help="asset tag, e.g. g03")
    ap.add_argument("--row", type=int, help="tab row number")
    ap.add_argument("--all", action="store_true",
                    help="run every tier row (g01-g10→2-11, s01-s10→12-21, b01-b10→22-31)")
    ap.add_argument("--skip", default="", help="comma-separated tags to skip (already done)")
    args = ap.parse_args()

    if not GEMINI_API_KEY:
        sys.exit("GEMINI_API_KEY not set. Put it in .env at the repo root, or export it.")

    tab = f"R: {args.creator}"
    drive = du.get_drive_service()

    if args.all:
        skip = set(t.strip() for t in args.skip.split(",") if t.strip())
        ok = 0
        jobs = []
        for t_i, prefix in enumerate(("g", "s", "b")):
            for i in range(10):
                jobs.append((f"{prefix}{i+1:02d}", 2 + t_i * 10 + i))
        for tag, row in jobs:
            if tag in skip:
                print(f"[{tag}] skipped", flush=True)
                continue
            if run_one(drive, tab, args.creator, tag, row):
                ok += 1
        print(f"DONE: {ok} passes written", flush=True)
    else:
        if not (args.tag and args.row):
            sys.exit("need --tag and --row (or --all)")
        run_one(drive, tab, args.creator, args.tag, args.row)


if __name__ == "__main__":
    main()
