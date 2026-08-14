# Engine

A brand-agnostic engine for researching and recreating short-form videos. **A template — it
contains mechanism, not content.** You supply the brand, the character, and the data.

New here? **`START-HERE.md`** — hand it to Claude Code and it runs the setup for you.
Doing it by hand instead? `SETUP.md`. Then read `CLAUDE.md`.

## The one rule that defines this repo

**Nothing character-specific or brand-specific is ever written into these files.**

Character data — face lock, body lock, wardrobe, environments, links, page, product — lives in
that character's **canvas sheet** in Google Sheets. The sheet is the source of truth. This repo
holds the *logic that reads it*. If you are about to type a character's name into a file here,
stop: it belongs in the sheet.

The test: if a rule needs an "if [character] / if [brand]" inside it, it does not live here.

## Topology

```
engine/              THIS REPO — the agnostic mechanism
  lib/               Google auth + Sheets/Docs/Drive helpers, vendored so it runs standalone
  execution/         engine logic — the scripts you actually run
  config/            YOUR pointers (gitignored). Copy the .example.json files.
[your sheet]         per-character source of truth — face lock, wardrobe, links, clip maps
[your Drive folder]  durable assets — images, storyboards, research
```

The repo holds logic. The sheet holds data. Adding a character is filling in a sheet, not
editing code — that is what makes this an app rather than a repo.

## Layers

```
BASE            true for every video, every brand, every character   → rules/base.md
  ↓ two independent dials
STYLE           how it looks     → rules/styles/    green screen · ai avatar · transformation · skits
TYPE            what it's for    → rules/types/     product · growth
  ↓
CHARACTER       fills in the values                → the canvas sheet, NOT this repo
```

## Layout

```
START-HERE.md             the agent bootstrap — give this to Claude Code
SETUP.md                  the by-hand version — Google auth, config, first run
CLAUDE.md                 the operating contract
STATUS.md                 what actually runs vs what is scaffolding
rules/
  base.md                 true for every video, every brand, every character
  styles/                 how it looks — green screen · ai avatar · transformation · skits
  types/                  what it's for — product · growth
canvas/
  SPEC.md                 the recreation canvas
  layout.md               rows/columns/cells
  pipeline.md             the five stages a video passes through
  character_schema.md     the SHAPE of a character record (values live in the sheet)
execution/                engine code — see STATUS.md for what is proven
lib/                      vendored Google plumbing
config/*.example.json     copy these, fill them in, they are gitignored
design/decisions.md       why it is shaped this way
```

## The core mechanism

`recreate <row>` on a locked character:

1. Pull the reference video's assets from the Master DB row (local + Drive).
2. Label it — style, script, clip map (which dialogue maps to which frame).
3. Append a clip-map block to that character's canvas sheet.
4. Emit image + video prompts into the rows.
5. **Write-back:** you build, adjust the prompts, hand the final ones back. Those are stored.
   Over time the canvas becomes the library of prompts that actually worked.

**Store images, never videos.** The image is the durable asset — video regenerates from it.

## Adding a character

Create a canvas tab in your spreadsheet and register it in `config/characters.json`. That is
the whole setup — no code changes.
