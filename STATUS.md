# STATUS — what actually runs

This is a **template under construction**, packaged from a working install. Read this before
assuming anything works end to end. The mechanism is real; the polish is not finished.

## Runs today

| Script | What it does | Needs |
|---|---|---|
| `pipeline_rules_tab.py` | builds the `Pipeline Rules` tab | config + auth |
| `research_rules_tab.py` | builds the `Research Rules` tab | config + auth |
| `creator_tabs.py` | scaffolds a character's CANVAS + SCRIPTS tab pair | a spec JSON |
| `character_assets.py` | uploads a reference image to Drive, drops `=IMAGE()` in the canvas cell | config + auth |
| `character_scripts.py` | inserts a video block into a SCRIPTS tab, non-destructively | a payload JSON |
| `research_tab.py` | creates an `R: [creator]` research working tab | config + auth |
| `gsb_tier.py` | Gold/Silver/Bronze tiering of a SortFeed CSV export | a CSV — no auth, pure local |
| `clip_map.py` | **the core** — labels a reference video frame by frame, renders the block into a canvas | `GEMINI_API_KEY`, ffmpeg |

Every one of these takes `--dry-run`. Use it first, always.

## Needs an input you have to produce

These are proven code but they consume a hand-built JSON, not a config file. Read the docstring
at the top of each — the spec shape is documented there.

- `hq_tabs.py` — CANVAS + FORMATS reference tables, from a spec
- `format_sheets.py` — regroups scraped research rows by format, from a map JSON
- `research_consolidate.py` — merges the `F:` format sheets into one `Format Research` tab

## Known gaps

**`wheel.py` will not run out of the box.** It reads a `Script Rules` tab from your Master DB,
and no script in this repo builds that tab. You have to create it yourself — one row per
framework / hook / structure / technique / psychology entry. The axes and how they combine are
documented in the file's docstring. Until then, the wheel has nothing to spin.

**`research_assets.py` has heavy optional deps.** It wants `yt-dlp`, `ffmpeg`, and
`openai-whisper` for local transcription (commented out of `requirements.txt` — install it
only if you want that). It also looks for `ig_cookies.txt` at the repo root for Instagram
downloads; you supply your own, and it is gitignored.

**Gen-group labelling in `clip_map.py` is not settled.** This is the one real open problem, and
it is worth understanding before you trust the output.

The model labels each frame `NEW IMAGE` · `CONTINUATION` · `SAME IMAGE` — a judgement about
whether one still can serve two moments:

- `SAME IMAGE` — the picture is unchanged. Different words over the same shot still counts.
- `CONTINUATION` — same scene and wardrobe, but movement changed the picture enough that one
  still cannot serve both.
- `NEW IMAGE` — a different setup entirely.

**It is decided by LOOK, not by reasoning.** An earlier prompt that said "default to NEW IMAGE"
over-corrected and labelled an entire video NEW.

The unresolved case: a video shot on one fixed camera, one set, one outfit, where only the
*subject* being demonstrated changes. Under "NEW IMAGE = a scene you would build from scratch"
the right answer is one NEW IMAGE for the whole video, which is useless. In practice each new
subject should be a NEW IMAGE even though the set never changed — so `NEW IMAGE` is keyed to
**the subject being demonstrated, not the location**. No prompt in the file says that yet.
Two fixes were tried and both failed:

1. Sharpening the prompt wording — no change at all.
2. Sending the frames themselves as ordered images instead of the video plus timestamps —
   fixed some frames, broke others, and the model stopped using `SAME IMAGE` entirely.

Expect to correct labels by hand for now. Chain depth *is* enforced in code: overflow past 3 is
re-anchored to NEW IMAGE, so the structure holds even when a label is wrong.

**Also worth knowing:** correcting gen groups does not reduce cost — `CONTINUATION` still needs
a generation. What it fixes is *where chains anchor*, which is what makes the prompts reusable.

**Dialogue on the wrong frame is almost always a missing frame, not a bad alignment.** With no
frame to carry it, ten seconds of speech piles onto whatever frame precedes the gap. The second
pass exists to catch those; `--no-second-pass` turns it off if it is misfiring. Fix the frames
and the dialogue follows.

## Not built

- No `recreate` CLI wrapper. The steps in `CLAUDE.md` are run script by script.
- No prompt-emission step (step 4 of the core mechanism) — the clip map is rendered, the image
  and video prompt columns are yours to fill, and the write-back loop is manual.
- No tests.
