# Canvas layout — BUILT, iterated with the user 2026-07-29

Was a strawman. Now it is the shape of a live canvas the user has reviewed and approved
("this looks really good"). Still co-designed — do not restructure it alone.

His constraint, unchanged: *"If it's a little bit clunky, or if it's not cleanly visible to
the eye, then it's not going to work too well."*

## The shape

One tab per character, inside the Master Video DB spreadsheet.

| Rows | Block | Starts at |
|---|---|---|
| 1 | Character banner | A |
| 2–4 | **IDENTITY** — face lock · face lock alt · body lock · body lock alt | A |
| 6–8 | **ACCOUNT & LINKS** — platform · handle · page URL | A |
| 9–15 | Links table — product image · product · placement · short link · Amazon link | A |
| 16–18 | Hashtag rules — post type · hashtags · rule | A |
| 19–21 | **WARDROBE** — one outfit per column, extends right forever | A |
| 23–25 | **ENVIRONMENTS** — one environment per column, same | A |
| 27+ | **CLIP MAPS** — blocks append below, newest last | A |

Each clip-map block: a label row (`ROW n · V# — link`), a column header row, then one row
per frame.

| Col | Width | Holds |
|---|---|---|
| A | 105 | Frame (`=IMAGE()` from intake) |
| B | 300 | Source Dialogue — as spoken, English underneath |
| C | 110 | Gen Group — `NEW IMAGE` · `CONTINUATION` · `SAME IMAGE` |
| D | 210 | References In — cell handles from the header band |
| E | 330 | Image Prompt |
| F | 115 | Our Image — the generated still. The durable asset. |
| G | 330 | Video Prompt |
| H | 115 | Approved |

## Rules that fell out of building it

- **The links table is the one block that indents.** Column A there is the product image,
  merged across that product's three placement rows. Everywhere else starts at A.
- **Column widths are global, so the widest values decide.** Amazon links are ~195 chars and
  must sit in a 330px column; that is why the links table is ordered the way it is.
- **Never hardcode a row or column in code.** The band gains and loses both. `character_assets.py`
  and `clip_map.py` locate everything from section banners and label text.
- Only row 1 is frozen. Freezing the whole band leaves nothing visible on a laptop.
- Images use `=IMAGE(url, 1)`, so row height alone controls size and a wide column costs
  nothing but whitespace. Frames run at 110px — half the Master DB's 220.

## Still open

- Move the ACCOUNT & LINKS block (rows 6–15) up beside IDENTITY. User: *"for now it's not that
  big of a deal, I don't mind it the way it looks."* Deferred, not rejected.
- Column A is unused in the clip-map rows. Frame ID + timestamp would fit.
