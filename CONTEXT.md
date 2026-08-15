# Engine — Stage Contract

Shared, brand-agnostic video-recreation pipeline. **Not scoped to one business** — any brand
registers its own character in it. Currently: SwipeMaxx / Ace.

Read this first. Then `CLAUDE.md` (the operating contract that shipped with the template) and
`STATUS.md` (what the template's own authors say does and doesn't work).

---

## Stage: first full recreation, image generation not yet built

The pipeline runs end to end from a URL to a labeled clip map in a character's canvas sheet.
What it cannot yet do is produce the actual new images — the "Our Image" column is still empty
by design, because no script in this repo calls an image model.

## Done criteria for this stage

- [x] Google auth + Master DB + Drive pool wired (`config/engine.json`, `config/characters.json`)
- [x] Doctrine tabs built (`Pipeline Rules`, `Research Rules`)
- [x] First character scaffolded with real assets (Ace — face/body lock, 6 wardrobe, 5 environments)
- [x] `pull_video.py` written (was missing from the template) — URL → local `reference.mp4` + scene frames → Drive pool + manifest
- [x] `clip_map.py` run end to end on a real reference video (Master DB row 2)
- [x] Image Prompts + References In written by hand for every row of that clip map
- [ ] **`generate_images.py` — read a row's Image Prompt + reference cells, call an image model, write the result into `Our Image`**
- [ ] One real generated image reviewed against its source frame

## Next stage

**Write-back loop.** Per `canvas/SPEC.md`, the point of the canvas is bidirectional: the engine
writes a prompt, the operator adjusts it while actually building, then hands the final working
prompt back so it sits beside the delivered one. The delivered-vs-final diff is the learning
signal, and over time the canvas becomes the library of prompts that actually worked. Nothing
captures that today.

After that: video prompts (`Video Prompt` column), then the `recreate <row>` CLI wrapper that
chains pull → clip map → prompts in one command instead of script-by-script.

---

## What moves the needle

Generating one real image from one real prompt and looking at it next to its source frame.
Everything upstream of that is now proven; everything downstream is unverified until an image
actually comes out the other end.

## File map

| Path | What it is |
|---|---|
| `CLAUDE.md` | The template's operating contract — routing, the "no brand data in this repo" rule, the 5-stage mechanism |
| `STATUS.md` | The template authors' own honest account of what runs vs what is scaffolding. Read before trusting any script |
| `canvas/` | Spec + layout for a character canvas; `pipeline.md` for the five stages |
| `rules/` | `base.md` (universal), `styles/` (green screen · ai avatar · transformation · skits), `types/` (product · growth) |
| `execution/` | The scripts you actually run — see STATUS.md for which are proven |
| `lib/` | Vendored Google auth/Sheets/Drive/Docs + the Gemini pass |
| `config/` | **Gitignored.** Your real pointers: `engine.json`, `characters.json`, `creator_spec.json` |
| `artifacts/` | Working outputs that belong to this repo rather than to Drive or the sheet |
| `.env` | **Gitignored.** `GEMINI_API_KEY` |

## Where the real data lives — NOT in this repo

| Thing | Where |
|---|---|
| Master DB + every character canvas | Google Sheet `1cvtkPpK5GhLqweuIFFoGUmKuN3JzrhjJ0tSSTqdvLnU` |
| Reference video frames, character assets | Drive folder `1vp724uuLL_TvaIVMENcxqR2Mj5XneGZw` |
| Downloaded reference videos + local frames | `~/Desktop/Ace/V<n>/` (per `config/engine.json`'s creator folder) |

## Known rough edges

The template shipped with real bugs, several fixed this session (see git log): a hardcoded
spreadsheet tab index that broke on any fresh sheet, `Path.read_text()` without an encoding
(silently corrupts em-dashes on Windows), a deprecated Gemini model hardcoded in two places,
and no retry on any Gemini call. Assume more exist in the scripts not yet run —
`wheel.py` is documented as outright broken, and gen-group labeling needs a human pass
(confirmed: it marked a subject switch as `CONTINUATION` when it should have re-anchored).
