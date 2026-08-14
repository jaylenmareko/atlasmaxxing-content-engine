# Character schema — the SHAPE of the frozen header

The repo defines the **shape**. The canvas sheet holds the **values**. This file must never
contain a real character's data.

Every character canvas opens with this block, frozen so it stays visible however far the clip maps
scroll.

| Field | What it is | Used at stage |
|---|---|---|
| `slug` | short id, also the key in `config/characters.json` | routing |
| `name` | display name | all |
| `page` | the one page she posts to (Meta) | packaging |
| `platforms` | which platforms this character actually posts on | packaging |
| `product` | the product this avatar sells | scripting, packaging |
| `links` | the selling links, one per platform | packaging |
| `face_lock` | reference image(s) that lock the face | production |
| `body_lock` | reference image(s) that lock the body | production |
| `wardrobe` | the named wardrobe styles available | production |
| `environments` | the named environments available | production |
| `voice` | voice id/settings, or `none` for no-VO characters | production |
| `styles` | which of the four styles this character runs | scripting, production |
| `type_defaults` | CTA/hashtag defaults for product vs growth | packaging |
| `compliance` | character/product-specific restrictions on top of `rules/base.md` | all |

## Notes

- `face_lock` / `body_lock` / `wardrobe` / `environments` are **image cells** — addressable, so
  "recreate using this cell image" resolves to a real Drive file ID.
- A character with no voice (`voice: none`) is not an exception to be coded around — it is a value.
  Same for a character that posts to two platforms instead of three. **If the engine needs an
  `if [character]` anywhere, a field is missing from this schema.**
- Stage loading applies: production fields must not load at scripting time.
