#!/usr/bin/env python3
"""Pull a reference video — step 1 of `recreate <row>`.

Referenced by canvas/SPEC.md ("Assets materialize locally + Drive mirror —
pull_video.py — already works") and execution/clip_map.py ("Row {row} is not
in the pool — run pull_video.py first."), but missing from this packaged
export. This fills that gap.

What it does, given a Master DB row that already has a Link:

  1. Read the Link from the Database tab (never take a URL on the CLI — the
     row is the address, per canvas/SPEC.md: "recreate <row> on a locked
     character... the sheet row is how everything addresses a video").
  2. Download the video with yt-dlp to <v_folder>/reference.mp4 — the exact
     path clip_map.py's build_clip_map() requires.
  3. Extract frames at SCENE CHANGES (not fixed fps — rules/base.md: "the
     storyboard extractor emits frames at scene changes"), named
     scene_{seq:04d}_{time:.1f}s.jpg. clip_map.py's frame_time() parses the
     trailing `_<seconds>s` for ordering; label_frames() reads them back from
     <v_folder>/frames/ by that same name.
  4. Mirror the frames to Drive under `Video Pool/Row {row:04d}/`, public-read
     (needed for the =IMAGE() cells clip_map.py writes later), and write a
     manifest.json there — {"link", "frames": [{"name", "id"}, ...]} — which
     is exactly what clip_map.py's pool_frames()/pool_folder() read back.

Scene detection threshold is a judgment call, not a law — rules/base.md is
explicit that "the storyboard is a draft" and expects a safety pass. This is
also why clip_map.py has its own second pass (missed-shot detection): a
missed cut here isn't a dead end, it gets caught and added later.

Usage:
  python3 pull_video.py --row 2 --character ace
  python3 pull_video.py --row 2 --character ace --v 2         # second pull for the same row
  python3 pull_video.py --row 2 --character ace --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
LIB = ENGINE_ROOT / "lib"
sys.path.insert(0, str(LIB))

import engine_config as cfg           # noqa: E402
import drive_utils as du              # noqa: E402
from google_sheets import get_sheets_service  # noqa: E402

# Windows consoles default stdout/stderr to the system codepage (e.g. cp1252),
# which raises UnicodeEncodeError on characters like "→"/"✅" — see the same
# fix already applied in lib/google_sheets.py.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

SCENE_THRESHOLD = 0.3  # ffmpeg scene-change score, 0-1 — a tuning knob, not a law
PTS_TIME_RE = re.compile(r"pts_time:([\d.]+)")


def _require(binary: str) -> None:
    if shutil.which(binary) is None:
        raise SystemExit(f"{binary} is not installed on this machine")


def read_row_link(row: int) -> str:
    svc = get_sheets_service()
    col = chr(ord("A") + cfg.COL_LINK)
    res = svc.spreadsheets().values().get(
        spreadsheetId=cfg.MASTER_DB_ID,
        range=f"'{cfg.MASTER_DB_TAB}'!{col}{row}").execute()
    values = res.get("values", [[]])
    link = (values[0][0] if values and values[0] else "").strip()
    if not link:
        raise SystemExit(
            f"No link in '{cfg.MASTER_DB_TAB}'!{col}{row} — add the video to the "
            f"Database tab first, recreate addresses a row, not a bare URL."
        )
    return link


def download_video(url: str, out_path: Path) -> None:
    _require("yt-dlp")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "-o", str(out_path),
        url,
    ]
    result = subprocess.run(cmd, stdout=sys.stderr, stderr=sys.stderr)
    if result.returncode != 0 or not out_path.exists():
        raise SystemExit(f"yt-dlp could not download {url} (exit {result.returncode})")


def extract_scenes(video: Path, out_dir: Path, threshold: float = SCENE_THRESHOLD) -> list[dict]:
    """Scene-change frame extraction. ffmpeg's `select` filter both picks the
    frames AND numbers the output files in order; `showinfo` on the same
    filter chain prints each selected frame's real timestamp to stderr, in
    the same order the files get written — that's what ties a numbered
    output file back to a real time in the source video.
    """
    _require("ffmpeg")
    out_dir.mkdir(parents=True, exist_ok=True)
    # Clear both the pre-rename and post-rename patterns — a re-run (retry,
    # different --threshold) leaves scene_*.jpg from last time, and Windows'
    # os.rename (unlike POSIX) refuses to overwrite an existing destination.
    for pattern in ("frame_*.jpg", "scene_*.jpg"):
        for existing in out_dir.glob(pattern):
            existing.unlink()

    pattern = str(out_dir / "frame_%04d.jpg")
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "info", "-y",
        "-i", str(video),
        "-filter:v", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr", "-q:v", "4",
        pattern,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    timestamps = [float(m) for m in PTS_TIME_RE.findall(result.stderr)]
    files = sorted(out_dir.glob("frame_*.jpg"))

    if not files:
        raise SystemExit(
            f"No scene changes detected at threshold {threshold} — ffmpeg stderr:\n"
            f"{result.stderr[-800:]}"
        )
    if len(timestamps) != len(files):
        # showinfo should emit exactly one pts_time per selected frame; if this
        # ever drifts, fail loudly rather than silently mislabel timestamps.
        raise RuntimeError(
            f"{len(files)} frame(s) written but {len(timestamps)} timestamp(s) parsed — "
            f"ffmpeg output format may have changed."
        )

    named: list[dict] = []
    for i, (f, ts) in enumerate(zip(files, timestamps), start=1):
        name = f"scene_{i:04d}_{ts:.1f}s.jpg"
        dest = out_dir / name
        f.rename(dest)
        named.append({"name": name, "path": dest})
    return named


def mirror_to_pool(row: int, link: str, local_frames: list[dict]) -> dict:
    drive = du.get_drive_service()
    root = du.folder_path(drive, cfg.POOL_FOLDER_NAME, root=cfg.IM_FOLDER_ID)
    folder = du.find_or_create_folder(drive, f"Row {row:04d}", root)

    frames = []
    for f in local_frames:
        meta = du.upload_public(f["path"], f["name"], folder, "image/jpeg")
        if not meta:
            raise RuntimeError(f"upload failed for {f['name']}")
        frames.append({"name": f["name"], "id": meta["id"]})
        print(f"  ↑ {f['name']}", file=sys.stderr)

    manifest = {"link": link, "frames": frames}
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "manifest.json"
        p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        # Replace any existing manifest rather than leaving two behind — a
        # re-pull (--v bumped) still addresses the same Drive row folder.
        old = drive.files().list(
            q=f"name='manifest.json' and '{folder}' in parents and trashed=false",
            fields="files(id)").execute().get("files", [])
        du.upload_file(str(p), "manifest.json", folder, "application/json")
        for f in old:
            drive.files().delete(fileId=f["id"]).execute()

    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description="Pull a reference video into the local V-folder + Drive pool")
    ap.add_argument("--row", type=int, required=True, help="Master DB row number")
    ap.add_argument("--character", required=True, help="slug from config/characters.json — resolves the local V-folder")
    ap.add_argument("--v", type=int, default=1, help="V number (local folder V<n>, default 1)")
    ap.add_argument("--threshold", type=float, default=SCENE_THRESHOLD, help="scene-change sensitivity, 0-1")
    ap.add_argument("--dry-run", action="store_true", help="download + detect scenes, skip the Drive mirror")
    args = ap.parse_args()

    link = read_row_link(args.row)
    print(f"[pull_video] row {args.row}: {link}", file=sys.stderr)

    cc = cfg.creator(args.character)
    v_folder = cc["folder"] / f"V{args.v}"
    v_folder.mkdir(parents=True, exist_ok=True)
    video_path = v_folder / "reference.mp4"

    print("[pull_video] downloading…", file=sys.stderr)
    download_video(link, video_path)
    size_mb = video_path.stat().st_size / (1024 * 1024)
    print(f"[pull_video] downloaded: {size_mb:.1f} MB -> {video_path}", file=sys.stderr)

    print(f"[pull_video] detecting scene changes (threshold {args.threshold})…", file=sys.stderr)
    frames = extract_scenes(video_path, v_folder / "frames", args.threshold)
    print(f"[pull_video] {len(frames)} frame(s): "
          f"{', '.join(f['name'] for f in frames[:5])}{' …' if len(frames) > 5 else ''}",
          file=sys.stderr)

    if args.dry_run:
        print(f"[pull_video] dry run — Drive pool untouched. Row {args.row} not registered.", file=sys.stderr)
        return 0

    print(f"[pull_video] mirroring to Drive (Video Pool/Row {args.row:04d})…", file=sys.stderr)
    manifest = mirror_to_pool(args.row, link, frames)
    print(f"✅ row {args.row}: {len(manifest['frames'])} frame(s) in the pool, "
          f"reference.mp4 at {video_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
