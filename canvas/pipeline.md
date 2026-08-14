# The video pipeline — five stages

User spec, 2026-08-04. Mechanism only. Every value this describes lives in a canvas or a
rules tab, never here.

Before this, the engine could recreate a reference video (`canvas/SPEC.md`) but had no
account of where an idea comes from, what a format actually *is*, what the video asks for,
or what the viewer receives afterwards. Those four things are the pipeline. Recreation is
one implementation of stage 5.

```
1 FEEDER      an observed demand            → a line in the idea table
2 FORMAT      the shape that carries it     → a format ID + its spec
3 CTA         what the video asks for       → a rung + a keyword
4 FULFILMENT  what the viewer receives      → a LIVE keyword
5 ASSET       what appears on screen        → a file
```

**A stage with no output blocks the next one.** The common failure is running 1-2-3-5 and
skipping 4 — a video ships, comments land on a keyword wired to nothing, and the leads are
gone. Stage 4 is the only stage with a hard gate on posting.

---

## The distinction that this whole doc exists to make

There are **two asset classes** and they are routinely collapsed into one:

| | ON-SCREEN asset (stage 5) | FULFILMENT asset (stage 4) |
|---|---|---|
| What it is | what appears *in* the video | what the viewer *receives* after commenting |
| Built by | the engine | the engine + the user |
| Deadline | before recording | before **posting** |
| Failure mode | video has nothing to look at | burned lead, spent hook |
| Example | a system diagram, a screen recording | a prompt pack, a guide, a long-form video |

They are produced by different work, on different deadlines, and a video needs both.

---

## Stage 1 — FEEDER

**A video is written from a demand that was observed, not from an idea someone had.**

Sources, in descending signal:

1. **Questions asked live** — stream questions, DMs, comments. Highest signal because the
   asker is real and the wording is theirs.
2. **The operator's own SOP** — what they actually did that day. Whatever is routine to the
   operator is usually opaque to the audience.
3. **Competitor gap** — a format present in the research corpus that nobody in the niche runs.
4. **Tutorial / long-form gaps** — a step everyone skips.

**Rule: asked twice, build it.** A repeated question is a validated topic; a single question
is an anecdote.

The feeder table records the question **in the asker's words**. Rewriting it into a topic
loses the hook — the phrasing of the question is frequently the phrasing of the hook.

## Stage 2 — FORMAT

Format sets the **ceiling**. It does not set the depth of the ask. On identical subject
matter, from one operator in one month, format choice moved outcomes by ~485×.

A format is not specified until every one of these exists for it:

| | what it must carry |
|---|---|
| DEFINITION | one line — what it is |
| THE ONE DRIVER | the single variable that decides the outcome, plus its observed control |
| SCRIPT SHAPE | the beats in order, with timings |
| HOOK EXAMPLES | ≥3, verbatim, with provenance and baseline multiple |
| TEXT ON SCREEN | verbatim overlay strings, not descriptions of them |
| FRAME PATTERN | scene count, scene length, what the storyboard looks like |
| FACE | on camera / voice only / faceless |
| CTA STYLE | placement, spoken vs text, which rungs it can carry |
| REFERENCES | Gold rows to steal from, Bronze controls to avoid |

A format described in one line is not specified — it is named. Naming is what produces
"we have no direction."

Visual examples are **not duplicated** into the spec. The spec points at reference rows in
the research corpus, which already hold thumbnails, transcripts and frames.

## Stage 3 — CTA

A video does not have *a* CTA. It has a **slot map** — asks can land at different timecodes,
and asks at different depths do not compete.

**The rungs**, ordered by what the viewer is asked to invest:

| Rung | The ask | Friction | Where the money is |
|---|---|---|---|
| **R0** | mid-roll internal link — "which I show you how to make in my last video" | none | none — routes the back catalogue |
| **R1** | give me the thing you used | lowest | none — builds trust and the DM list |
| **R2** | show me the full breakdown | medium — clicks out to long-form | inside the long-form |
| **R3** | how do I get access | highest — self-identifies as a buyer | the close |

R0 is **not a rung**. It costs no comment volume, so it stacks with any rung for free.

**R3 is usually reached through a disqualifier, not an offer.** "This only works if you
actually have a product" converts better than "here's how to get a product," because it
filters before it asks.

## Stage 4 — FULFILMENT

**The hard gate. Nothing posts with a keyword that is not wired end to end.**

Four fulfilment types:

| | what it is | cost to build |
|---|---|---|
| **DM TEXT** | the deliverable pasted straight into the DM | lowest |
| **DOC** | a written guide, link delivered in the DM | low |
| **LONG-FORM** | a video the DM links to; the selling happens inside it | high |
| **LINK ONLY** | routes to a page or an affiliate link | none — **but the DM copy is still the asset** |

LINK ONLY has no artifact and is still not free: the DM sequence that carries the link is
written work, and it is where the pitch lives. Treat it as an asset with a status.

A keyword is **LIVE** only when the trigger fires, the copy is written, and the destination
resolves. Anything less is DEAD and blocks posting.

## Stage 5 — ON-SCREEN ASSET

What appears in the video. Three kinds:

- **Built artifact** — a diagram, map, or graph made for the video. Durable, reusable, and
  the only kind that survives into later videos.
- **Live capture** — screen recording of the real work. Most credible, least reusable.
- **Evidence** — analytics, dashboards, receipts. Cheapest, and the only kind that
  substantiates a numeric claim made in the hook.

Registered in the canvas with a path and a rebuild command, so a later video can reuse it
rather than rebuild it.

---

## Gates — the vetoes

| | rule | why |
|---|---|---|
| **G1** | No keyword ships without fulfilment | a comment on a dead keyword is a burned lead and a spent hook |
| **G2** | One gate per video; two only at **different depths** | two asks at the same depth split the comment section and neither trips the engagement threshold |
| **G3** | A keyword must be a word nobody types by accident | `YES` / `OK` / `HOW` fire on organic comments and poison the list — prefer a noun tied to the ask |
| **G4** | Name the job or the outcome, never the technology | ~33× on an otherwise identical rig |
| **G5** | Format sets the ceiling, rung sets the depth | they are independent dials — never pick a rung to fix a format problem |
| **G6** | An A/B split changes **one** thing | same body, one differing close, or the result reads nothing |
