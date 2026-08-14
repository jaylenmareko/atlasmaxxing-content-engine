"""Engine configuration — reads config/engine.json, exposes it as module attributes.

The shared plumbing (drive_utils, gemini_pass) imports this module by name and reads
constants off it. Nothing brand-specific is written here: every value comes from
config/engine.json, which is yours and is gitignored. Copy config/engine.example.json
to config/engine.json and fill it in.
"""

from pathlib import Path
import json
import sys

ENGINE_ROOT = Path(__file__).resolve().parent.parent
LIB = ENGINE_ROOT / "lib"
CONFIG_PATH = ENGINE_ROOT / "config" / "engine.json"

if not CONFIG_PATH.exists():
    sys.exit(
        f"Missing {CONFIG_PATH}.\n"
        f"Copy config/engine.example.json to config/engine.json and fill it in — see SETUP.md."
    )

_cfg = json.loads(CONFIG_PATH.read_text())

# ── Brand ────────────────────────────────────────────────────────────────
BRAND_NAME = _cfg["brand_name"]

# ── Creators ─────────────────────────────────────────────────────────────
# One brand, N creators. Each has its own local working folder and captions tab.
CREATORS = {
    key: {**value, "folder": Path(value["folder"]).expanduser()}
    for key, value in _cfg["creators"].items()
}
DEFAULT_CREATOR = _cfg["default_creator"]
BRAND_FOLDER = CREATORS[DEFAULT_CREATOR]["folder"]


def creator(name=None):
    """Config for a creator. Defaults to DEFAULT_CREATOR so bare callers work."""
    key = (name or DEFAULT_CREATOR).strip().lower()
    if key not in CREATORS:
        raise KeyError(f"Unknown creator {name!r}. Known: {', '.join(CREATORS)}")
    return CREATORS[key]


# ── Master Video DB ──────────────────────────────────────────────────────
MASTER_DB_ID = _cfg["master_db_id"]
MASTER_DB_TAB = _cfg.get("master_db_tab", "Database")

# Column indexes (0-based) into the Database tab.
_cols = _cfg.get("columns", {})
COL_LINK = _cols.get("link", 1)
COL_TRANSCRIPT = _cols.get("transcript", 4)
COL_TYPE = _cols.get("type", 5)
COL_STYLE = _cols.get("style")          # None unless your schema has one
COL_CREATOR = _cols.get("creator", 6)

# ── Captions ─────────────────────────────────────────────────────────────
CAPTIONS_SHEET_ID = _cfg.get("captions_sheet_id") or MASTER_DB_ID
CAPTIONS_TAB = _cfg.get("captions_tab", "Captions")

# ── Google Drive filing ──────────────────────────────────────────────────
# Folder chain for working docs. {year} and {month} are filled at call time.
DRIVE_PATH = _cfg.get("drive_path", ["{year}", "Scripts", "{month}"])

# Drive root — the anchor folder everything is created under.
IM_FOLDER_ID = _cfg["drive_root_id"]
DRIVE_ROOT_ID = IM_FOLDER_ID            # clearer alias for new code
POOL_FOLDER_NAME = _cfg.get("pool_folder_name", "Video Pool")
BRANDS_FOLDER_NAME = _cfg.get("brands_folder_name", "Brands")

# ── Auth / shared helpers ────────────────────────────────────────────────
# Vendored into lib/. OAuth credentials and tokens live at the repo root.
CONTENT_ENGINE_EXEC = LIB

# Instagram cookies for yt-dlp. Optional — only research_assets.py wants it.
IG_COOKIES = ENGINE_ROOT / "ig_cookies.txt"
