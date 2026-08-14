# The Recreation Canvas — spec

User spec, 2026-07-29. The first thing this engine builds.

## What it is

One canvas per **character/avatar**, not per brand. Working assumption: one avatar = one page =
one product, Meta only. A brand may hold several canvases.

It is a **tool, not a document** — the same reason the Master Video DB is a real asset. It is
also the **source of truth for that character**: face lock, body lock, wardrobe, environments,
links, page, product all live here, not in the repo.

## Trigger

`recreate <row>` on a locked character. Row = Master DB row number. The mechanism is
**repo-agnostic** — the same call works in any brand engine. The end goal is an app; the sheet is
one rendering of the underlying function, not the product. Design every piece as a function that
returns data, with the sheet as a view.

## On trigger

1. Assets materialize locally + Drive mirror (`pull_video.py` — already works).
2. The reference video is **labeled**: style · script · clip map (which dialogue maps to which
   frame).
3. A **new clip-map block appends to the character's existing canvas**. Never a new file — the
   canvas grows forever and is the archive.
4. Prompts get written into the rows.
5. It becomes editable — swap references, upload new ones, change beats.

## Structure

**Frozen header** (always visible however far you scroll): name · page · selling links · face lock ·
body lock · wardrobe styles · environments.

**Below it:** clip-map blocks stacked vertically, newest last. **One row = one frame.**

## Each row must encode the REFERENCE CHAIN, not just the frame

This is the point of the whole thing. Each row answers *what are the steps and what are the
references*:

- Default: `base image = storyboard frame + the character's image lock` (+ environment) → regenerate.
- Where continuity is needed: **two-step regeneration** — generate image 1 from frame + lock, then
  **chain image 2 off image 1**, so image 1 is the reference.
- Inherits the hard chain-depth limit of 2–3 from `rules/base.md`.

## The write-back loop — the whole point

The canvas is **bidirectional**:

1. Engine writes the image prompt + video prompt into the row.
2. User builds the video, **adjusting prompts as he goes**.
3. User hands the **final adjusted prompts back**; they sit beside the delivered ones.

⇒ The canvas becomes **the library of prompts that actually worked**. The delivered-vs-final diff
is the learning signal.

## Store images, never videos

The video output is **not stored — deliberately.** "That's overkill." The **image is the durable
asset**: from a saved image you can always regenerate video. Rebuilding a past video needs no
generation from scratch — the plumbing and the hard assets are already in the row.

## Cells are addressable inputs

"Recreate a video using **this** cell image" must be a valid instruction. Every asset cell carries
a stable handle (the Drive file ID behind the `=IMAGE()`), so a cell reference resolves to a real
input, not just a picture.

## Proven plumbing this rides on

`sheet_frames.py`: Drive upload → public read → `https://drive.google.com/thumbnail?id=…&sz=w1000`
→ `=IMAGE(url, 1)` → row height 220px. Already working in the Master DB today.

## Open

See `STATUS.md`. Layout is in `layout.md` and is **co-designed — never finalized unilaterally**.
