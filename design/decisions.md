# Decisions log

> **Note for this copy:** this is the original build log, kept because it explains *why*
> the repo is shaped the way it is. It references repos and files from the machine it was
> written on (`pc-engine-v2`, `rebuild_notes.md`) that are not in this package. The
> reasoning stands on its own; the paths are history.

Append-only. Why the engine is shaped the way it is. Nothing here overrides `CLAUDE.md`.

---

## 2026-07-29 — Build fresh, not inside `pc-engine-v2`

**Decision:** new repo at `~/engine`, sibling to `~/pc-engine-v2`. That repo keeps running
production untouched.

**Why:** `pc-engine-v2` has brand text inside files that are supposed to be generic — 6 of them
(`production/image_rules.md`, `production/gs_product_sop.md`,
`production/transformation_two_shot_style.md`, `production/styles/transformation.md`,
`packaging/caption_rules.md`, `scripting/frameworks/smart_selling_script.md`). Building the
agnostic mechanism inside it means absorbing those assumptions invisibly. In a repo with zero
brand content, contamination is a **visible error** instead of a silent one.

Precedent: the user's standing rule from the earlier redesign — build new next to old, copy don't
move, test before switching.

---

## 2026-07-29 — The canvas sheet is the source of truth for character data

**Decision:** face lock, body lock, wardrobe, environments, links, page, product live in the
character's canvas sheet. The repo holds only the logic that reads it.

**Why (user):** *"That's where the source of truth is, not in the actual repository. So we can
keep it very lean."* It also means adding a character is filling in a sheet, not editing code —
which is what makes this an app rather than a repo.

**Consequence:** the repo ships empty. No characters, no brands. `config/characters.json` is the
only pointer, mapping a character slug to its canvas spreadsheet ID.

---

## 2026-07-29 — Store images, never videos

The image is the durable asset; video regenerates from it. Storing video was called overkill by
the user. Consequence: a rebuild months later costs almost nothing, and the canvas stays light —
which directly helps the layout/visibility problem.

---

## Carried from the `pc-engine-v2` audit (2026-07-27–28)

Full log: `~/pc-engine-v2/design/rebuild_notes.md`. The load-bearing conclusions:

- **The problem in one line:** things written where the model always reads them work (captions,
  links, intake); things that live only in chat break (scripting, prompts, recreation decisions).
  Not a rules problem — a missing-infrastructure problem.
- **Layers:** BASE → STYLE + TYPE (independent dials) → character fills the values.
- **Stage loading:** the user's one line is the routing key. Mechanical work fires silently.
  Face lock/wardrobe/environments/links are PRODUCTION info; they must not load at scripting time.
- **FRAMES ≠ IMAGES ≠ CLIPS**, and continuity is a dial (chained/standalone/mixed).
- **Chain depth 2–3 max.** Hard.
- **Every tool-spec claim carries a source tag:** 🟢 MEASURED · 🔵 USER · 🟡 LIBRARY (tested
  elsewhere, not our stack) · 🔴 GUESS. A wrong Omni word-cap once got adopted straight from
  library intake with no A/B — hence the tags.
- **One chat per video.** The separate-production-chat rule is retired; continuity beats isolation.
- **Deferred until the canvas exists:** the scripting roulette (4 sources × 3 change levels = 12
  scripts, built as a function returning 12, not coupled to Google Docs).
