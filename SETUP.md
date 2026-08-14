# Setup

This is the by-hand version. If you have Claude Code, use `START-HERE.md` instead — it runs
these steps for you and stops at the four points that need you.

About 20 minutes, most of it in the Google Cloud console. Everything runs locally on your
machine and talks to **your** Google account — nothing is shared with anyone else's.

---

## 1. Prerequisites

```bash
python3 --version      # need 3.11 or newer
ffmpeg -version         # frame extraction — clip_map.py needs it
yt-dlp --version        # video download — only research_assets.py needs it
```

On macOS:
```bash
brew install python@3.12 ffmpeg yt-dlp
```

## 2. Install

```bash
cd engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Re-run `source .venv/bin/activate` in each new terminal before running anything.

## 3. Google credentials

The engine reads and writes your Sheets and Drive through the Google API. You create your own
OAuth client — takes five minutes and is free.

1. Go to **console.cloud.google.com** → create a project (any name).
2. **APIs & Services → Library** → enable all three:
   - Google Sheets API
   - Google Drive API
   - Google Docs API
3. **APIs & Services → OAuth consent screen** → User type **External** → fill in app name and
   your email → on the **Test users** step, **add your own Google address**. Leave it in
   Testing; you never need to publish it.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID** → Application type
   **Desktop app** → Create → **Download JSON**.
5. Rename that file to **`credentials.json`** and put it in the repo root (next to `README.md`).

> `credentials.json` and the tokens are gitignored. Never commit them.

## 4. Create your spreadsheet and Drive folder

1. New Google Sheet. Name it whatever you like — this is your **Master DB**.
   Copy its id from the URL: `docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`
2. Rename the first tab to **`Database`** and give it this header row:

   | A | B | C | D | E | F | G | H+ |
   |---|---|---|---|---|---|---|---|
   | Thumbnail | Link | Brand | Platform | Transcript | Type | Creator | frames → |

   One reference video per row. The row number is how you address a video everywhere else
   (`--row 42`).
3. New folder in Google Drive — your **Drive root**. Everything the engine uploads is created
   under it. Copy its id from the URL: `drive.google.com/drive/folders/`**`THIS_PART`**

## 5. Fill in your config

```bash
cp config/engine.example.json     config/engine.json
cp config/characters.example.json config/characters.json
cp .env.example .env
```

Open each and replace the `PASTE_YOUR_...` placeholders with the two ids from step 4.
Both files are gitignored — they are yours.

In `.env`, set `GEMINI_API_KEY` from **aistudio.google.com/apikey**. Only the video-labelling
scripts (`clip_map.py`, `lib/gemini_pass.py`) use it; skip it if you are not using those yet.

## 6. First run — authorise

```bash
python3 execution/pipeline_rules_tab.py --dry-run
```

A browser window opens asking you to grant access. Google will warn that the app is
unverified — that is expected, it is your own unpublished client. Click **Advanced → Go to
[app name] (unsafe)** and allow.

Two token files appear in the repo root (`token.json`, `token_sheets.json`). You will not be
asked again.

If it fails with `Missing config/engine.json`, go back to step 5.

## 7. Build your tabs

Drop `--dry-run` to actually write. These create the doctrine tabs in your spreadsheet — the
rules you are meant to see and edit on the page rather than in code:

```bash
python3 execution/pipeline_rules_tab.py     # Pipeline Rules — how a video gets built
python3 execution/research_rules_tab.py     # Research Rules — how a format gets discovered
```

Each refuses to overwrite an existing tab; pass `--rebuild` if you mean to replace it.

## 8. Add a character

```bash
cp config/creator_spec.example.json config/creator_spec.json
# edit it — name, tabs, wardrobe and environment slots
python3 execution/creator_tabs.py --spec config/creator_spec.json --dry-run
python3 execution/creator_tabs.py --spec config/creator_spec.json
```

Then register the character in `config/characters.json` under `characters` — the slug, the
display name, and the tab names you just created.

Now fill the header band with real images. Each one uploads to Drive, is made link-readable,
and lands in the right canvas cell as an `=IMAGE()`:

```bash
python3 execution/character_assets.py --character example --slot face_lock --file ~/face.jpg
python3 execution/character_assets.py --character example --list
```

## 9. Recreate a video

Put a reference video in row 42 of your `Database` tab (link in column B), then:

```bash
python3 execution/clip_map.py --row 42 --character example --v 1 --dry-run
python3 execution/clip_map.py --row 42 --character example --v 1
```

That labels the video frame by frame and appends a clip-map block to the character's canvas.
Read `canvas/SPEC.md` for what the block means and `STATUS.md` for what is still rough.

---

## Where things live

| | |
|---|---|
| `credentials.json`, `token*.json` | repo root — yours, gitignored |
| `.env` | repo root — `GEMINI_API_KEY` |
| `config/engine.json` | brand wiring: name, creators, Drive filing |
| `config/characters.json` | slug → canvas tab pointers |
| `lib/` | vendored Google plumbing — you should not need to touch it |
| `execution/` | the scripts you run |

## Common problems

**`Missing config/engine.json`** — step 5.

**`credentials.json not found`** — step 3.5; the file must be at the repo root, not in a
subfolder.

**`403 accessNotConfigured`** — one of the three APIs is not enabled. Step 3.2.

**Browser says "access blocked / has not completed verification"** — you are not on the test
user list. OAuth consent screen → Test users → add your address.

**Token errors after changing scopes** — delete `token.json` and `token_sheets.json` and run
again to re-authorise.

**`ModuleNotFoundError: engine_config`** — you are running from the wrong directory. Run from
the repo root: `python3 execution/<script>.py`.
