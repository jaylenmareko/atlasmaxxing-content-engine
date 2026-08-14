# Asset demo rules

How a visual asset gets built, rendered and published into a canvas cell.

Every value here was read out of a shipped file, not remembered. The four that define the
system — and the only ones worth copying from — are:

| File | What it proves |
|---|---|
| `V1 — Recreation Map` | the full stage: four stations, measured wires, IG chrome |
| `V2 — Recreation Comparison` | the two-row grid: reference over recreated, one connector each |
| `V2 — Recreation Canvas` | stage + rails: source in, frames across, one output |
| `Content Library` | the ledger: one row per item, thumbnail → strip → meta |

**Nothing brand- or character-specific belongs in an asset's *structure*.** Colour, geometry
and wiring are the system. What goes in the frames is the character's, and comes from the
sheet.

---

## 1 · The two layouts. Pick one before writing a line of CSS.

**STAGE** — a fixed composition that never scrolls. Everything visible at once, sized to the
viewport on both axes. Use it when the point is a *relationship*: this became that, this feeds
that. Recreation maps, comparisons, canvases, pipeline diagrams.

**LEDGER** — a scrolling column of rows, one row per item. Use it when the point is *volume*:
here is everything we have. Libraries, registers, indexes.

Getting this wrong is the most expensive mistake available. A relationship rendered as a ledger
scrolls and the relationship disappears; a library forced onto a stage shrinks until nothing
reads. When in doubt: **is the viewer comparing, or browsing?**

---

## 2 · Tokens

Identical in all four files. Do not invent new ones — extend this list instead.

```
--canvas      #F1F0EA      the paper
--dot         rgba(20,25,40,.06)
--node        #FFFFFF      anything sitting on the paper
--node-line   #E4E2DA      its border
--ink         #1B2027      text
--muted       #7A8291      secondary text
--faint       #A8AEB8      labels, column heads
--blue        #2F80ED      the wire. flow, connection, "this becomes that"
--blue-2      #63A4F7      wire gradient end
--coral       #FF6A43      rebuilt / new / ours          (V1, Siphon)
--coral-deep  #DC4318      coral on light backgrounds
--green       #2E9E6B      script, shipped, go
--violet      #7B5EE0      motion
--pink        #E0417E      the reference, when it needs its own colour  (V2)
```

Dark mode: every file ships `@media (prefers-color-scheme:dark)` plus
`:root[data-theme="light"|"dark"]` overrides.

```
--canvas #171A1F · --dot rgba(255,255,255,.05) · --node #20252D · --node-line #2E353F
--ink #EDF0F4 · --muted #98A1AD · --faint #66707C · --blue #4F97FF · --blue-2 #7FB6FF
```

The published PNG renders **light** — headless Chrome defaults to it and dark was rejected for
V1. Ship the dark block anyway; it costs nothing and the HTML gets opened directly too.

Type:

```
--sans  -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif
--mono  ui-monospace, "SF Mono", Menlo, Consolas, monospace
```

Mono is for anything machine-ish: timestamps, IDs, counts, column labels, chips. Sans for
everything a person wrote.

---

## 3 · Geometry

**Paper.** Dot grid on every asset, both layouts:

```css
background-image: radial-gradient(var(--dot) 1.3px, transparent 1.3px);
background-size: 26px 26px;   /* 24px on the ledger */
```

**Stage sizing — CSS only, no JavaScript:**

```css
.fit   { position:fixed; inset:0; display:grid; place-items:center; overflow:hidden; }
.stage { position:relative; width:min(100vw, 177.78vh); aspect-ratio:1200/720;
         container-type:inline-size; }
body   { overflow:hidden; }
```

`177.78vh` is `1200/720 × 100`. Change the stage ratio and that number changes with it.
Then **every dimension inside is `cqw`** — 1cqw = 1% of stage width — so the whole composition
scales as one object. Absolute nodes get `%` positions computed in the 1200×720 space.

V1 does the same job with a fixed 1240px stage and a JS `transform: scale()` fitter. It works
and it shipped, but the CSS version has no scripts, no resize handler, and no flash before
first paint. **Use the CSS version for anything new.**

**Cards.** Vertical video is `aspect-ratio: 9/16`, `object-fit: cover`, always. Never letterbox
a frame, never distort one.

```
radius       .55cqw on frames · .9–1cqw on hero/video nodes
border       .17cqw solid, in the colour that classifies it
shadow       0 1cqw 2.2cqw -1cqw rgba(30,30,25,.28)
hero shadow  0 2cqw 4cqw -1.4cqw <accent at .45 alpha>
chip         top/left .32cqw · mono .6cqw · 700 · white on the border colour · radius .28cqw
```

**Colour classifies. Position does not.** A reader must be able to tell a reference frame from
a rebuilt one with the file zoomed out to a thumbnail — which is exactly how it appears in a
sheet cell. Border colour does that work; row position does not survive the shrink.

**Two known-good compositions:**

*Comparison grid* — `grid-template-columns: repeat(N, 1fr)`, `column-gap: 1.05cqw`, three
implicit rows: frames, connectors (`height: 6.4cqw`), frames. Pairs align because they are
literally in the same grid column. 8 across is the tested maximum at 1200×720.

*Canvas* — in the 1200×720 space: frame block starts at x=140, columns 98 wide with a 10.86
gutter (8 columns land exactly on x=1000); rows at y=198 and y=438; rails at y=176 and y=634;
source reel 78 wide on the left, output node 132 wide on the right, both centred on
y=405 — the mid-line of the two frame rows.

**Centre the hero on the composition's own mid-line, not the stage's**, and give the left and
right margins the same weight. The first Siphon canvas put its final video at x=66% with 20% of
empty stage to its right; it reads as an accident.

---

## 4 · Wires

The wire is what makes it a canvas instead of a mood board. Rules:

- One colour: the blue gradient, left to right.
- Two passes over the **same** path set — a soft halo then the line itself:
  `stroke-width:7 opacity:.11`, then `stroke-width:2.2`.
- `stroke-linecap: round`. Curves are cubic; straight runs are `L`.
- A `<circle r="3–4">` at every junction and at each connector's midpoint.
- SVG is `position:absolute; inset:0; z-index:1; pointer-events:none` with
  `viewBox="0 0 1200 720" preserveAspectRatio="none"`. Nodes sit at `z-index:2` so wires pass
  behind them.

**The gradient trap — this will cost you an hour.** A `linearGradient` defaults to
`gradientUnits="objectBoundingBox"`. A perfectly vertical or horizontal stroke has a
zero-width or zero-height bounding box, the gradient is degenerate, and **the stroke does not
render at all** — silently. Every straight connector vanishes while the curves paint fine.

```html
<linearGradient id="bl" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="1200" y2="0">
```

`userSpaceOnUse` over the stage width paints every case. Use it always.

**Rails.** When one source feeds many frames, do not fan N curves out of it — run a horizontal
rail above the row and drop a short line into each frame's top centre. Same on the way out:
drop from each frame's bottom into a lower rail, then one curve to the output node. Two curves
total instead of sixteen.

---

## 5 · Weight

Assets are self-contained — every image inlined as base64, no external requests. That makes
file size a real constraint, and oversized source images are always the cause.

**Downscale before encoding.** A frame that renders ~130px wide does not need a 1080px source.

```
frames in a strip or grid   →  340px wide       (~25KB each)
hero / single large node    →  520px wide
sips -Z 340 in.jpg --out out.jpg
```

Measured: the same 8-pair comparison went 771KB → 385KB on downscaling alone, with no visible
difference at render size. V1 went 5.79MB → 2.81MB by inlining each image **once** as a CSS
custom property (`--i-<key>`) and drawing it via a class rather than repeating the base64 in
every `<img>`. Do that whenever an image appears more than once.

Target: **under 500KB** for a stage, under 2MB for a ledger.

---

## 6 · Render and publish

Four artefacts per asset. All four go to Drive; two get referenced by the sheet.

```
<name>.html      the source, editable, opens standalone
<name>.png       what the sheet shows            ← must be anyone-with-link
<name>.pdf       what a click opens
build_<name>.py  the builder, kept in the project folder
```

**Render** with headless Chrome. Always `--force-device-scale-factor=2` — the PNG is viewed
full-screen and 1x looks soft.

```bash
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

"$CH" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
      --window-size=1600,960 --screenshot=out.png "file://$SRC"

"$CH" --headless --disable-gpu --no-pdf-header-footer \
      --print-to-pdf=out.pdf "file://$SRC"
```

Window size sets the crop:

- **Stage** — match the stage ratio. A 1200×720 stage wants 5:3, e.g. `1600,960`. Any other
  ratio letterboxes with dead paper.
- **Ledger** — width comfortably over the wrap's `max-width`, height tall enough for the last
  row. Too short truncates *silently* and the PNG looks finished. **Always open the render and
  count the rows** before uploading.

**Upload** to `IM / Brands / <brand> / Assets / V<n>/` via `drive_utils.upload_public()` —
`upload_file()` alone leaves the PNG private and the sheet renders a broken image.

**Publish** into the canvas cell. One formula, thumbnail links to the PDF:

```
=HYPERLINK("https://drive.google.com/file/d/<PDF_ID>/view",
           IMAGE("https://drive.google.com/thumbnail?id=<PNG_ID>&sz=w1000"))
```

Then confirm the thumbnail is actually public before calling it done:

```bash
curl -sIL -o /dev/null -w "%{http_code} %{content_type}\n" \
  "https://drive.google.com/thumbnail?id=<PNG_ID>&sz=w1000"     # want: 200 image/…
```

**Cell geometry:** demo columns are **404px wide**, demo rows **280px tall**. A new demo column
is made by `copyPaste` with `pasteType: PASTE_FORMAT` from an existing one — header styling and
row heights come along, and nothing has to be re-specified.

**Column order in the canvas:** the main demo sits in the first demo column; additional demos
extend to the right of `REFERENCE VIDEO`. Sheets do not grow columns on their own — a tab
created with 8 columns *stops* at H and writes past it fail. Widen the grid first:

```python
{"updateSheetProperties": {"properties": {"sheetId": GID,
  "gridProperties": {"columnCount": 12}}, "fields": "gridProperties.columnCount"}}
```

---

## 7 · Laws

1. **Read the reference files before designing.** The system already exists. Reinventing it
   produces a fifth style and costs a rebuild.
2. **Match the layout to the question** — comparing or browsing. Decide first.
3. **No copy on a visual asset unless it carries information a picture cannot.** Titles,
   column labels, chips and legends stay. Descriptive captions under images are noise.
4. **A stage never scrolls.** If it scrolls it is not a stage; either cut items or switch to a
   ledger.
5. **4–5 rows maximum on a stage; 8 frames maximum across.** Past that nothing reads at
   thumbnail size.
6. **Colour is classification, never decoration.**
7. **Never chain a derived asset off another derived asset.** Rebuild from the source folder,
   or drift compounds.
8. **Look at the render before uploading.** Truncation, missing wires and clipped rows all
   produce files that look finished.
