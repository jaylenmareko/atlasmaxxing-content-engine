#!/usr/bin/env python3
"""Character assets — put a durable image behind a canvas cell.

Every identity/wardrobe/environment/product image a character owns lives in one place
on Drive and is surfaced in the canvas header as an =IMAGE() with a stable Drive file id.
That id is the handle: "recreate this frame using THIS cell" resolves to a real input.

Drive tree (created on demand, character-agnostic):

    [your Drive root]/
      Characters/
        [Character]/
          identity/        face lock, body lock, and their alts
          wardrobe/        outfit swaps      -> header wardrobe strip
          environments/    setting swaps     -> header environment strip
          product/         product reference images

Usage:
  python3 character_assets.py --character example --slot face_lock --file path/to.jpg
  python3 character_assets.py --character example --strip wardrobe --label "Grey Hoodie" --file path/to.jpg
  python3 character_assets.py --character example --list
"""

import argparse
import json
import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
LIB = Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(LIB))

import engine_config as cfg           # noqa: E402
import drive_utils as du              # noqa: E402
from google_sheets import get_sheets_service   # noqa: E402

CHARACTERS = ENGINE_ROOT / "config" / "characters.json"
CHARACTERS_FOLDER = "Characters"

# slot -> (label in the IDENTITY label row, drive subfolder). Row AND column are both
# looked up from that label, so the block can be reordered without touching this file.
SLOTS = {
    "face_lock":     ("Face Lock", "identity"),
    "face_lock_alt": ("Face Lock — alt", "identity"),
    "body_lock":     ("Body Lock", "identity"),
    "body_lock_alt": ("Body Lock — alt", "identity"),
}
# strip -> (section banner in column A, drive subfolder). One image per column, extends
# right forever. Rows are LOOKED UP from the banner, never hardcoded — the header band
# gets reshaped as the character fills in, and hardcoded rows go stale silently.
STRIPS = {
    "wardrobe":    ("WARDROBE", "wardrobe"),
    "environment": ("ENVIRONMENTS", "environments"),
}
IDENTITY_BANNER = "IDENTITY"
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp"}


def col_letter(i: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA"""
    s = ""
    while True:
        s = chr(65 + i % 26) + s
        i = i // 26 - 1
        if i < 0:
            return s


def load_characters() -> dict:
    return json.loads(CHARACTERS.read_text(encoding="utf-8"))


def save_characters(data: dict) -> None:
    CHARACTERS.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def find_banner(char: dict, banner: str) -> tuple[int, int]:
    """(row, col0) of a section banner. Its label row is +1, its content row +2, and the
    banner's own column is the left edge of that section. Both are looked up, never
    assumed — the header band gets columns and rows inserted as the character fills in."""
    svc = get_sheets_service()
    grid = svc.spreadsheets().values().get(
        spreadsheetId=char["spreadsheet_id"],
        range=f"'{char['tab']}'!A:D").execute().get("values", [])
    for i, row in enumerate(grid, 1):
        for j, cell in enumerate(row):
            if str(cell).strip().upper().startswith(banner):
                return i, j
    raise RuntimeError(f"No {banner!r} section in '{char['tab']}'")


def banner_row(char: dict, banner: str) -> int:
    return find_banner(char, banner)[0]


def label_column(char: dict, banner: str, label: str) -> int:
    """0-indexed column of a label in a section's label row (banner row + 1)."""
    row, _ = find_banner(char, banner)
    svc = get_sheets_service()
    vals = svc.spreadsheets().values().get(
        spreadsheetId=char["spreadsheet_id"],
        range=f"'{char['tab']}'!{row + 1}:{row + 1}").execute().get("values", [[]])
    for j, cell in enumerate(vals[0] if vals else []):
        if str(cell).strip().lower() == label.lower():
            return j
    raise RuntimeError(f"No {label!r} column under {banner!r} in '{char['tab']}'")


def assets_folder(drive, display_name: str, subfolder: str) -> str:
    """IM / Characters / [Character] / [subfolder] — created if absent."""
    return du.folder_path(drive, CHARACTERS_FOLDER, display_name, subfolder,
                          root=cfg.IM_FOLDER_ID)


def image_formula(file_id: str) -> str:
    return f'=IMAGE("https://drive.google.com/thumbnail?id={file_id}&sz=w1000", 1)'


def place(slug: str, slot: str, local: Path) -> dict:
    """Upload one image, park it in the character's Drive tree, surface it in the canvas."""
    if slot not in SLOTS:
        raise KeyError(f"Unknown slot {slot!r}. Known: {', '.join(SLOTS)}")
    if not local.exists():
        raise FileNotFoundError(local)

    data = load_characters()
    char = data["characters"][slug]
    label, subfolder = SLOTS[slot]
    cell = (f"{col_letter(label_column(char, IDENTITY_BANNER, label))}"
            f"{banner_row(char, IDENTITY_BANNER) + 2}")
    display = char.get("display") or slug.title()

    drive = du.get_drive_service()
    folder_id = assets_folder(drive, display, subfolder)
    name = f"{slug}_{slot}{local.suffix.lower()}"
    meta = du.upload_public(local, name, folder_id, MIME.get(local.suffix.lower(), "image/jpeg"))
    if not meta:
        raise RuntimeError(f"upload failed for {local}")
    fid = meta["id"]

    svc = get_sheets_service()
    svc.spreadsheets().values().update(
        spreadsheetId=char["spreadsheet_id"],
        range=f"'{char['tab']}'!{cell}",
        valueInputOption="USER_ENTERED",
        body={"values": [[image_formula(fid)]]}).execute()

    # remember the handle so later stages can reference the cell without a Drive lookup
    char.setdefault("assets", {})[slot] = {"file_id": fid, "cell": cell,
                                           "source": local.name}
    save_characters(data)
    return {"slot": slot, "cell": cell, "file_id": fid, "drive_folder": folder_id}


def place_strip_item(slug: str, strip: str, local: Path, label: str) -> dict:
    """Upload ONE local image directly into the next open column of a wardrobe/
    environment strip. Companion to fill_strip() below, which instead copies
    images already on Drive (bulk case) — this is for the common onboarding
    case: a brand-new character with nothing on Drive yet, filling one
    named slot at a time from local reference photos. Was previously only
    reachable by importing this module and calling it directly — no CLI path
    existed despite fill_strip() being fully wired into --list's output.
    """
    if strip not in STRIPS:
        raise KeyError(f"Unknown strip {strip!r}. Known: {', '.join(STRIPS)}")
    if not local.exists():
        raise FileNotFoundError(local)

    data = load_characters()
    char = data["characters"][slug]
    banner, subfolder = STRIPS[strip]
    banner_r, banner_c = find_banner(char, banner)
    existing = char.get("strips", {}).get(strip, [])
    col = banner_c + len(existing)
    row = banner_r + 2
    display = char.get("display") or slug.title()

    drive = du.get_drive_service()
    folder_id = assets_folder(drive, display, subfolder)
    n = len(existing) + 1
    name = f"{slug}_{strip}_{n:02d}_{label}{local.suffix.lower()}"
    meta = du.upload_public(local, name, folder_id, MIME.get(local.suffix.lower(), "image/jpeg"))
    if not meta:
        raise RuntimeError(f"upload failed for {local}")
    fid = meta["id"]

    cell_col = col_letter(col)
    svc = get_sheets_service()
    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=char["spreadsheet_id"],
        body={"valueInputOption": "USER_ENTERED", "data": [
            {"range": f"'{char['tab']}'!{cell_col}{row}", "values": [[image_formula(fid)]]},
            {"range": f"'{char['tab']}'!{cell_col}{row - 1}", "values": [[label]]},
        ]}).execute()

    placed = {"cell": f"{cell_col}{row}", "file_id": fid, "label": label, "source": local.name}
    char.setdefault("strips", {}).setdefault(strip, [])
    char["strips"][strip].append(placed)
    save_characters(data)
    return placed


def fill_strip(slug: str, strip: str, items: list[dict], start: int = 0) -> list[dict]:
    """Populate a header strip from images ALREADY on Drive.

    items: [{"file_id": ..., "name": ..., "label": ...}]  — copied server-side into the
    character's tree, so the canvas never points at a folder someone might reorganise.
    """
    if strip not in STRIPS:
        raise KeyError(f"Unknown strip {strip!r}. Known: {', '.join(STRIPS)}")

    data = load_characters()
    char = data["characters"][slug]
    banner, subfolder = STRIPS[strip]
    banner_r, banner_c = find_banner(char, banner)
    row, start = banner_r + 2, start + banner_c
    display = char.get("display") or slug.title()

    drive = du.get_drive_service()
    folder_id = assets_folder(drive, display, subfolder)

    placed, formulas, labels = [], [], []
    for n, item in enumerate(items):
        cell_col = col_letter(start + n)
        name = f"{slug}_{strip}_{start + n + 1:02d}_{item.get('label', 'ref')}.jpeg"
        new_id = du.copy_into(drive, item["file_id"], name, folder_id)
        if not new_id:
            continue
        try:
            drive.permissions().create(fileId=new_id,
                                       body={"type": "anyone", "role": "reader"}).execute()
        except Exception as e:
            print(f"⚠️  permission failed on {name}: {e}", file=sys.stderr)
        formulas.append(image_formula(new_id))
        labels.append(item.get("label", ""))
        placed.append({"cell": f"{cell_col}{row}", "file_id": new_id,
                       "label": item.get("label", ""), "source": item.get("name", "")})

    if not placed:
        return placed

    svc = get_sheets_service()
    first = col_letter(start)
    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=char["spreadsheet_id"],
        body={"valueInputOption": "USER_ENTERED", "data": [
            {"range": f"'{char['tab']}'!{first}{row}", "values": [formulas]},
            {"range": f"'{char['tab']}'!{first}{row - 1}", "values": [labels]},
        ]}).execute()

    char.setdefault("strips", {}).setdefault(strip, [])
    char["strips"][strip] = char["strips"][strip][:start] + placed
    save_characters(data)
    return placed


def main():
    ap = argparse.ArgumentParser(description="Upload a character reference image into its canvas cell")
    ap.add_argument("--character", required=True, help="slug from config/characters.json")
    ap.add_argument("--slot", choices=list(SLOTS))
    ap.add_argument("--strip", choices=list(STRIPS), help="append one local image to a wardrobe/environment strip")
    ap.add_argument("--label", help="name for this strip entry (required with --strip)")
    ap.add_argument("--file")
    ap.add_argument("--list", action="store_true", help="show what is already placed")
    args = ap.parse_args()

    if args.list:
        char = load_characters()["characters"][args.character]
        ident = banner_row(char, IDENTITY_BANNER) + 2
        for slot, (label, sub) in SLOTS.items():
            got = char.get("assets", {}).get(slot)
            cell = f"{col_letter(label_column(char, IDENTITY_BANNER, label))}{ident}"
            print(f"  {slot:<16} {cell:<5} {sub:<13} {got['file_id'] if got else '—'}")
        for strip, (bannr, sub) in STRIPS.items():
            placed = char.get("strips", {}).get(strip, [])
            r, c = find_banner(char, bannr)
            print(f"  {strip:<16} {col_letter(c)}{r + 2:<4} {sub:<13} {len(placed)} placed: "
                  f"{', '.join(p['label'] for p in placed) or '—'}")
        return

    if args.slot and args.file:
        print(json.dumps(place(args.character, args.slot, Path(args.file)), indent=2))
    elif args.strip and args.file:
        if not args.label:
            ap.error("--label is required with --strip")
        print(json.dumps(place_strip_item(args.character, args.strip, Path(args.file), args.label), indent=2))
    else:
        ap.error("--slot+--file, or --strip+--label+--file, are required unless --list")


if __name__ == "__main__":
    main()
