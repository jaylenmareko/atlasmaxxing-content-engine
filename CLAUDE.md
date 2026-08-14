# Engine — brand-agnostic video recreation engine

**Read `STATUS.md` before doing anything.** This is a template, and it says so. It contains
mechanism only. It contains no brand, no character, no product.

New install? `START-HERE.md` first (agent-driven), or `SETUP.md` to do it by hand.

## The one rule that defines this repo

**Nothing character-specific or brand-specific is ever written into these files.**

Character data — face lock, body lock, wardrobe, environments, links, page, product — lives in
that character's **canvas sheet**. The sheet is the source of truth. This repo holds the *logic
that reads it*. If you are about to type a character's name into a file here, stop: it belongs
in the sheet.

The test: if a rule needs an "if [character] / if [brand]" inside it, it does not live here.

The two escape hatches: `config/engine.json` and `config/characters.json`. Both are gitignored,
both hold pointers rather than values. Everything brand-shaped goes in one of them or in the
sheet — never in a `.py` or `.md` file.

## Layers

```
BASE            true for every video, every brand, every character   → rules/base.md
  ↓ two independent dials
STYLE           how it looks     → rules/styles/    green screen · ai avatar · transformation · skits
TYPE            what it's for    → rules/types/     product · growth
  ↓
CHARACTER       fills in the values                → the canvas sheet, NOT this repo
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

Full spec: `canvas/SPEC.md`. Layout: `canvas/layout.md` — that one is co-designed with whoever
owns the account; never restructure it unilaterally.

## Routing

| You say | I read |
|---|---|
| "new video" / "what's the CTA" / "what do I owe people" | the **`Pipeline Rules`** tab + that character's canvas |
| "why five stages" / "what's an on-screen vs fulfilment asset" | `canvas/pipeline.md` |
| "recreate row X" | `canvas/SPEC.md` + the character's canvas sheet |
| "research this creator" / a SortFeed export | the **`Research Rules`** tab in the Master DB — NOT a repo file |
| "run driver analysis" / "what's driving performance" | `Research Rules` → PROTOCOL section (AP1–AP8) |
| "what's built / where are we" | `STATUS.md` |
| anything about layout, columns, rows, cells | `canvas/layout.md` — and ask, don't decide |
| "build an asset" / colours, wires, sizing, rendering | `design/asset-rules.md` |
| "why is it like this" | `design/decisions.md` |
| "it won't run" / auth / credentials | `SETUP.md` |

## Where rules live

Doctrine that a human needs to *see and change* lives in the Sheet, as a tab. The repo holds
the executables that build and read it. The reasoning: an MD file in a repo is invisible — when
something changes, nobody notices. A tab is on the page, next to the work.

`Research Rules` and `Pipeline Rules` are built this way, by
`execution/research_rules_tab.py` and `execution/pipeline_rules_tab.py`. `rules/base.md` and
`rules/styles/*` predate that decision and have not been migrated — don't migrate them
unilaterally.

A rules tab is flat and cell-addressable — one row per thing, tinted by KIND, section banners
in ink, row 1 frozen. A protocol tab additionally carries **WHO** and **GATE** columns, so
every point where the flow stops for a human is visible on the page.

## The two protocols

`Research Rules` covers how a format is **discovered**. `Pipeline Rules` covers how a video is
**built** — feeder → format → cta → fulfilment → on-screen asset (mechanism in
`canvas/pipeline.md`). Recreation is one implementation of stage 5, not the whole flow.

The distinction that tab exists to make: an **on-screen asset** is what appears *in* the video
and is due before recording; a **fulfilment asset** is what the viewer *receives* after
commenting and is due before **posting**. Different work, different clocks. Gate G1 — no
keyword ships without fulfilment — is the only thing in this repo that blocks a post.

## Plumbing

Google auth, Sheets, Docs and Drive live in `lib/`, vendored so the repo runs standalone.
`lib/engine_config.py` reads `config/engine.json` and exposes it to the rest — that is the only
place brand values enter the code path. Scripts put `lib/` on `sys.path` and import by name.

## Conventions

- Deliverables are the FINAL message of a turn — all tool calls first, zero tool calls after.
- Intermediate files go in `.tmp/`, never kept.
- No character/brand names in this repo. See the one rule above.
- Never hardcode a spreadsheet row or column in code. Locate cells from section banners and
  label text — the canvas band gains and loses rows.
