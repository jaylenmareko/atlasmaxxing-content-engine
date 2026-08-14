# START HERE

You have been handed a video engine. It is a working template — it holds the *logic*, and you
supply the data. Nothing in it is set up yet.

## If you have Claude Code

Open a terminal in this folder and run `claude`. Then paste this:

> Read START-HERE.md and set this repo up for me. Work through the steps in order. Stop at
> every HUMAN GATE and tell me exactly what to do — don't guess at values I haven't given you.

That's it. It will do the install, the config, the verification and the first tab build, and it
will stop and ask you at the four points where only you can act.

## If you don't have Claude Code

Follow `SETUP.md` by hand. Same steps, written for a human. It takes about 20 minutes.

---

# Setup plan (for the agent)

Work top to bottom. `WHO` is who does the step. `GATE` means stop and wait for the operator —
do not invent a value, do not skip ahead, do not proceed with a placeholder.

| # | Step | WHO | GATE |
|---|---|---|---|
| 1 | Check `python3` ≥ 3.11, `ffmpeg`, `yt-dlp`. Offer the `brew install` line for anything missing. | AGENT | — |
| 2 | `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` | AGENT | — |
| 3 | Google Cloud project + OAuth client → `credentials.json` at the repo root | OPERATOR | **G1** |
| 4 | Create the Master DB spreadsheet and the Drive root folder; collect both ids | OPERATOR | **G2** |
| 5 | `cp` the three `config/*.example.json` and `.env.example`, then write the ids in | AGENT | — |
| 6 | Run `python3 execution/pipeline_rules_tab.py --dry-run` to trigger the OAuth browser flow | AGENT | **G3** |
| 7 | Build the doctrine tabs: `pipeline_rules_tab.py`, `research_rules_tab.py` | AGENT | — |
| 8 | Scaffold the first character from a spec | BOTH | **G4** |
| 9 | Read `STATUS.md` aloud to the operator — two known gaps they need to hear | AGENT | — |

## The four gates, in detail

### G1 — credentials
The operator must create their own Google OAuth client. You cannot do this for them; it is
console clicks in a browser. Give them exactly this and wait:

1. **console.cloud.google.com** → new project (any name)
2. **APIs & Services → Library** → enable **Google Sheets API**, **Google Drive API**,
   **Google Docs API** — all three
3. **OAuth consent screen** → User type **External** → app name + their email → on the
   **Test users** step, **add their own Google address**. Leave it in Testing; never publish.
4. **Credentials → Create credentials → OAuth client ID** → Application type **Desktop app** →
   Create → **Download JSON**
5. Rename it `credentials.json` and drop it in this folder

Verify with `ls credentials.json` before moving on. Do not continue without it.

### G2 — the two ids
The operator creates these in their own Google account:

- **A spreadsheet.** Rename the first tab to exactly `Database`. Header row:
  `Thumbnail | Link | Brand | Platform | Transcript | Type | Creator | frames →` in A–H.
  One reference video per row; the row number is how everything addresses a video.
  The id is the middle of the URL: `docs.google.com/spreadsheets/d/`**`ID`**`/edit`
- **A Drive folder.** Everything uploaded gets created under it.
  `drive.google.com/drive/folders/`**`ID`**

Ask for both. Write them into `config/engine.json` (`master_db_id`, `drive_root_id`) **and**
`config/characters.json` (`workspace.master_db_id`, `workspace.drive_root_id`) — the same two
values go in both files.

Also ask for the brand name and set `brand_name` in `config/engine.json`. If they don't have
one, use their account handle — it is only a label.

### G3 — the browser consent
The first run opens a browser. Google shows a scary "unverified app" screen because it is their
own unpublished client. Tell them to click **Advanced → Go to [app name] (unsafe) → Allow**.

Success looks like `token.json` and `token_sheets.json` appearing at the repo root. If the run
errors instead, check `SETUP.md` → Common problems before improvising.

### G4 — the first character
`cp config/creator_spec.example.json config/creator_spec.json`, then ask the operator for:

- the character's **slug** (lowercase, no spaces) and **display name**
- what the account is *for*, in one line
- their wardrobe and environment slots — how many, and what each one is

Fill the spec, then:
```bash
python3 execution/creator_tabs.py --spec config/creator_spec.json --dry-run
python3 execution/creator_tabs.py --spec config/creator_spec.json
```
Then register the character in `config/characters.json` under `characters`, keyed by slug, with
`display`, `spreadsheet_id`, `tab`, and `scripts_tab` matching what you just built.

Leave `assets`, `strips` and `products` as empty objects — `character_assets.py` fills those in
when the operator uploads real images:
```bash
python3 execution/character_assets.py --character <slug> --slot face_lock --file <path>
python3 execution/character_assets.py --character <slug> --list
```

---

## Rules for the agent doing this setup

**Every script takes `--dry-run`. Use it first, every time.** These write to a live spreadsheet.

**Never invent an id, a key, or a character value.** If you don't have it, you are at a gate —
stop and ask. A placeholder that reaches a config file will fail confusingly three steps later.

**The one rule of this repo: no brand or character names in these files.** Character data lives
in the canvas sheet. Config files hold pointers, never values. If you are about to type a
character's name into a `.py` or `.md` file here, you are doing it wrong — it belongs in the
sheet. See `CLAUDE.md`.

**Don't restructure `canvas/layout.md`.** It is co-designed with whoever owns the account.

**Two things are known-broken. Say so out loud at step 9 rather than letting them find out:**
- `wheel.py` will not run — it reads a `Script Rules` tab that no script in this repo builds.
  The operator has to author that tab themselves.
- Gen-group labelling in `clip_map.py` is unsettled and will need hand-correction.

Full detail in `STATUS.md`. Read it before you make promises about what works.

## After setup

`CLAUDE.md` is the operating contract — routing, layers, the core mechanism. Read it once setup
is green, and work from it after that.
