#!/usr/bin/env python3
"""Research pilot — fill a working tab with picks + assets.

Ported from pc-engine-v2 2026-08-02. Same two changes as research_tab.py: IDs come
from config/characters.json -> workspace, and the shared plumbing (drive_utils,
storyboard) is imported from where it already lives rather than copied. This repo
adds no brand values of its own.

For each pick (top/mid/bottom N from the SortFeed CSV):
  1. Write link/views/likes into the tab row immediately (cheap data first)
  2. Download the video (H.264)
  3. Storyboard (scene frames + contact sheet)
  4. Whisper transcript (medium model by default, loaded once)
  5. Upload to Drive: [drive root] → Format Research → [creator]/assets/[g01|s05|b10]/
  6. Write into the row: thumbnail (scene 1), transcript, storyboard, frames →

This is PH4 in the `Research Rules` tab. It stops there — the analysis does not
start until the user's kill #2 at PH5.

Usage:
  python3 research_assets.py --creator <handle> \
      --csv ~/Desktop/Dirty/creator_306_reels.csv --picks 10
"""

import argparse
import os
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE_EXEC = Path(__file__).resolve().parent
CONFIG = ENGINE_EXEC.parent / "config" / "characters.json"
WS = json.loads(CONFIG.read_text(encoding="utf-8"))["workspace"]
MASTER_DB_ID = WS["master_db_id"]
DRIVE_ROOT_ID = WS["drive_root_id"]
RESEARCH_FOLDER = WS.get("research_folder", "Format Research")
TAB_PREFIX = WS.get("research_tab_prefix", "R: ")

LIB = Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(LIB))

import drive_utils as du                                    # noqa: E402
from google_sheets import write_range                       # noqa: E402
from gsb_tier import load_csv, pick_tiers                   # noqa: E402

STORYBOARD = LIB / "storyboard.py"
IG_COOKIES = ENGINE_EXEC.parent / "ig_cookies.txt"   # you supply this; gitignored
DATA_START = 2          # first data row in the tab
MAX_FRAMES = 40
_whisper_model = None


def whisper_transcribe(video: Path) -> str:
    global _whisper_model
    if _whisper_model is None:
        import whisper
        # 'base' is too small for non-English and fails silently — see the note in
        # Content-Engine/execution/process_thumbnails.py. 'medium' is the first size
        # that holds up on Spanish. WHISPER_MODEL=base to go back to fast.
        model = os.environ.get("WHISPER_MODEL", "medium")
        print(f"  loading whisper ({model})…", flush=True)
        _whisper_model = whisper.load_model(model)
    try:
        result = _whisper_model.transcribe(str(video), fp16=False)
        return result.get("text", "").strip()
    except Exception as e:
        print(f"  ⚠️ whisper failed: {e}", flush=True)
        return ""


def download_h264(link: str, dest_dir: Path) -> Path | None:
    out = dest_dir / "reference.%(ext)s"
    cmd = ["yt-dlp", "-S", "vcodec:h264,acodec:m4a", "--merge-output-format", "mp4",
           "-o", str(out), link]
    if IG_COOKIES.exists():
        cmd[1:1] = ["--cookies", str(IG_COOKIES)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
    except Exception as e:
        print(f"  ⚠️ download failed: {e}", flush=True)
        return None
    vids = list(dest_dir.glob("reference.*"))
    return vids[0] if vids else None


def img_formula(file_id: str) -> str:
    return f'=IMAGE("https://drive.google.com/thumbnail?id={file_id}&sz=w1000", 1)'


def process_one(drive, tab: str, assets_root: str, row_num: int, tag: str, video: dict):
    """One pick: download → storyboard → transcribe → upload → write row."""
    folder = du.find_or_create_folder(drive, tag, assets_root)
    work = Path(tempfile.mkdtemp(prefix=f"research_{tag}_"))
    try:
        vid = download_h264(video["link"], work)
        if not vid:
            write_range(MASTER_DB_ID, f"'{tab}'!F{row_num}",
                        [["⚠️ download failed — likely removed/private"]])
            return False

        subprocess.run([sys.executable, str(STORYBOARD),
                        "--video", str(vid), "--out", str(work)],
                       check=True, capture_output=True, text=True)
        frames = sorted((work / "frames").glob("scene_*.jpg"))[:MAX_FRAMES]
        contact = work / "storyboard.jpg"

        transcript = whisper_transcribe(vid)
        (work / "transcript.txt").write_text(transcript, encoding="utf-8")

        du.upload_file(str(vid), "reference.mp4", folder, "video/mp4")
        du.upload_file(str(work / "transcript.txt"), "transcript.txt", folder, "text/plain")

        thumb_f = contact_f = None
        frame_fs = []
        if frames:
            up = du.upload_public(frames[0], "thumb.jpg", folder, "image/jpeg")
            thumb_f = img_formula(up["id"]) if up else None
        if contact.exists():
            up = du.upload_public(contact, "storyboard.jpg", folder, "image/jpeg")
            contact_f = img_formula(up["id"]) if up else None
        for f in frames:
            up = du.upload_public(f, f.name, folder, "image/jpeg")
            if up:
                frame_fs.append(img_formula(up["id"]))

        # B thumb | G transcript | H storyboard | I+ frames
        write_range(MASTER_DB_ID, f"'{tab}'!B{row_num}", [[thumb_f or ""]])
        write_range(MASTER_DB_ID, f"'{tab}'!G{row_num}", [[transcript[:4000]]])
        if contact_f or frame_fs:
            vals = [contact_f or ""] + frame_fs
            end_col = 8 + len(vals)   # H is col 8 (1-based)

            def cl(n):
                s = ""
                while n:
                    n, r = divmod(n - 1, 26)
                    s = chr(65 + r) + s
                return s

            write_range(MASTER_DB_ID,
                        f"'{tab}'!H{row_num}:{cl(end_col)}{row_num}", [vals])
        print(f"  ✅ {tag}: {len(frames)} frames, {len(transcript)} chars transcript",
              flush=True)
        return True
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Fill a research tab with picks + assets")
    ap.add_argument("--creator", required=True)
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--picks", type=int, default=10)
    ap.add_argument("--no-kill", action="store_true",
                    help="tier by views only — skip the likes/views engagement "
                         "kill (use when the export's likes column is corrupt)")
    args = ap.parse_args()

    tab = f"{TAB_PREFIX}{args.creator}"
    videos = load_csv(args.csv)
    sel = pick_tiers(videos, args.picks, kill_engagement=not args.no_kill)
    print(f"{args.creator}: {sel['killed_engagement']} engagement-killed, "
          f"{sel['survivors']} survive → {3*args.picks} picks", flush=True)

    drive = du.get_drive_service()
    fr_root = du.folder_path(drive, RESEARCH_FOLDER, args.creator, "assets",
                             root=DRIVE_ROOT_ID)
    # archive the raw CSV alongside (paper trail)
    creator_folder = du.folder_path(drive, RESEARCH_FOLDER, args.creator,
                                    root=DRIVE_ROOT_ID)
    du.upload_file(str(args.csv), args.csv.name, creator_folder, "text/csv")

    # cheap data first: links/views/likes for all 30 rows
    plan = []
    for t_i, (tier, prefix) in enumerate((("GOLD", "g"), ("SILVER", "s"), ("BRONZE", "b"))):
        for i, v in enumerate(sel[tier]):
            row_num = DATA_START + t_i * args.picks + i
            tag = f"{prefix}{i+1:02d}"
            plan.append((row_num, tag, v))
            write_range(MASTER_DB_ID, f"'{tab}'!C{row_num}:E{row_num}",
                        [[v["link"], int(v["views"]), int(v["likes"] or 0)]])
    print(f"wrote {len(plan)} rows of cheap data — starting asset intake", flush=True)

    alts = {t: list(sel.get("ALT", {}).get(t, [])) for t in ("GOLD", "SILVER", "BRONZE")}
    tier_of = lambda tag: {"g": "GOLD", "s": "SILVER", "b": "BRONZE"}[tag[0]]
    ok = 0
    for row_num, tag, v in plan:
        print(f"[{tag}] row {row_num} — {v['link']}", flush=True)
        while True:
            if process_one(drive, tab, fr_root, row_num, tag, v):
                ok += 1
                break
            # dead/blocked video → remove and backfill with the next candidate
            pool = alts[tier_of(tag)]
            if not pool:
                write_range(MASTER_DB_ID, f"'{tab}'!F{row_num}",
                            [["⚠️ video unavailable — no alternates left"]])
                break
            v = pool.pop(0)
            print(f"  ↻ backfilling {tag} with alternate: {v['link']}", flush=True)
            write_range(MASTER_DB_ID, f"'{tab}'!C{row_num}:F{row_num}",
                        [[v["link"], int(v["views"]), int(v["likes"] or 0), ""]])
    print(f"DONE: {ok}/{len(plan)} picks fully processed", flush=True)


if __name__ == "__main__":
    main()
