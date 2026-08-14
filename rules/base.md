# BASE — true for every video, every brand, every character

If a rule here needs an "if [character]" or "if [style]" inside it, it is filed one layer too high.
Move it to `rules/styles/` or into the character's canvas sheet.

## Prompt base

- iPhone/phone-camera look. Natural available light. Not cinematic, not a professional photoshoot.
- No bokeh, no blurred background — everything in focus.
- **Never re-describe a locked face.** The lock image carries it; describing it fights the lock.
- Props must already exist in the frame. Never name an object that is absent — naming a thing that
  isn't there can conjure it.
- Never put an invented product in a prompt. Product frames use the real product reference image.

## Chaining ⚠️ HARD

- **Never chain more than 2–3 images deep.** Generating off a previously generated image compounds
  artifacts every hop; by hop 4+ it visibly degrades.
- Past the limit: re-anchor to the original base image, or generate fresh and accept the break.
- Chain every edit off the MASTER plate, never off a previous edit.
- Restate cumulative state explicitly (e.g. liquid colour) — the master can't carry it.
- Continuity is a **dial**, declared per video: chained · standalone · mixed. Not a law.

## Frames ≠ images ≠ clips

Three different counts. The storyboard extractor emits **frames** at scene changes; that is not
how many **images** to generate, which is not how many **clips** to render. Every frame carries a
generation group: `NEW` · `SAME` · `CONTINUATION`. Same background + same wardrobe + same props ⇒
same base image.

Intake already encodes partial grouping in the filenames (`04a` / `04b` share a scene).

## Storyboard is a draft

The frame extractor misses scenes. Do a safety pass against the actual video before trusting a
clip map.

## Caption base

- Growth = no links, ever. Product = links, always.
- Max 5 hashtags per platform.
- Disclosure tags on AI-generated content.

## Compliance base

- No medical professionals, no disease claims, no banned terms.
- On-label only — a claim the product's label does not support cannot ship, regardless of how well
  it would perform.

*(Character-specific compliance and the exact banned list belong in the canvas sheet.)*
