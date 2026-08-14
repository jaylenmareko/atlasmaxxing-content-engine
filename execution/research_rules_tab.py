#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the `Research Rules` tab — the research protocol, visible in the sheet.

Same idiom as `Script Rules` and `Prompting Rules`: one row per thing, flat and
cell-addressable, tinted by KIND, section banners in ink. Row 1 frozen.

Two columns exist here that the other rules tabs don't need:
  WHO   — who acts on this step: YOU / ENGINE / CLAUDE
  GATE  — where the flow stops for the user. This is the whole reason the protocol
          is in the sheet instead of a repo file: the intervention points have to be
          visible, so a change can be called out mid-run ("from phase 5, do X").

Nothing character-specific or brand-specific is in this file. Content categories are
niche-specific by nature and are deliberately NOT enumerated here — see CAT01.

Usage:
  python3 research_rules_tab.py                 # create (refuses if it exists)
  python3 research_rules_tab.py --rebuild       # replace the tab in place
  python3 research_rules_tab.py --dry-run       # print the row plan, touch nothing
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import google_sheets as gs  # noqa: E402

CONFIG = Path(__file__).resolve().parent.parent / "config" / "characters.json"
TAB = "Research Rules"

NCOLS = 9
HEADERS = ["ID", "KIND", "NAME", "WHO", "GATE",
           "WHAT IT IS (one line)", "DETAIL", "OUTPUT / EXAMPLE", "SOURCE"]
WIDTHS = [64, 118, 300, 92, 122, 380, 470, 380, 190]

INK = {"red": 0.169, "green": 0.188, "blue": 0.220}
PAPER = {"red": 1, "green": 1, "blue": 1}
TEXT = {"red": 0.11, "green": 0.12, "blue": 0.13}

TINT = {
    "PHASE":        {"red": 0.867, "green": 0.910, "blue": 0.988},
    "QUALIFY":      {"red": 0.898, "green": 0.957, "blue": 0.910},
    "RED FLAG":     {"red": 0.988, "green": 0.878, "blue": 0.878},
    "MATH":         {"red": 0.988, "green": 0.969, "blue": 0.847},
    "TIER":         {"red": 0.988, "green": 0.867, "blue": 0.600},
    "FILTER":       {"red": 0.988, "green": 0.929, "blue": 0.847},
    "PRINCIPLE":    {"red": 0.949, "green": 0.910, "blue": 0.976},
    "SYSTEM":       {"red": 0.988, "green": 0.867, "blue": 0.600},
    "DRIVER":       {"red": 0.859, "green": 0.957, "blue": 0.969},
    "PRIORITY":     {"red": 0.988, "green": 0.969, "blue": 0.847},
    "HOOK":         {"red": 0.988, "green": 0.929, "blue": 0.847},
    "CATEGORY":     {"red": 0.988, "green": 0.929, "blue": 0.847},
    "STEP":         {"red": 0.949, "green": 0.918, "blue": 0.988},
    "OUTPUT":       {"red": 0.898, "green": 0.957, "blue": 0.910},
    "TOOL":         {"red": 0.988, "green": 0.847, "blue": 0.820},
    "LOOP":         {"red": 0.949, "green": 0.910, "blue": 0.976},
}

CHECK = "✋ YOU"
PING = "📣 PING"

# --------------------------------------------------------------------------------------
# The protocol. One tuple per row: (ID, KIND, NAME, WHO, GATE, WHAT, DETAIL, OUTPUT, SOURCE)
# A bare string is a section banner.
# --------------------------------------------------------------------------------------
ROWS = [

"FLOW — the nine steps, in order. WHO says who acts. GATE is where it stops for you. Everything else runs without asking.",

("PH1", "PHASE", "SPOT the creator", "YOU", "—",
 "Find a creator whose content stops you, then sanity-check them before spending anything.",
 "Feed, keyword search, or competitor. Keyword combos that surface formats: topic + Challenge / Hacks / Tutorial / Review / Reaction / Storytime / Day in the Life / Before-After / Comparison / Debunking / Explaining / Behind the Scenes. Run them past Q01–Q05 and RF1–RF3 first — a creator who fails those wastes the whole pipeline.",
 "A handle worth scraping.", "workflow Phase 1"),

("PH2", "PHASE", "SCRAPE the page", "YOU", "—",
 "SortFeed the creator, sort reels most-viewed to least, export.",
 "Export CSV / Excel / Sheets. Upload to Discord tagged `research`, or just hand over the file path. The Discord routing is specced but NOT wired — the manual path is the live one today.",
 "One CSV: every reel with views and likes.", "workflow Phase 2 · research_intake.md"),

("PH3", "PHASE", "TIER — the math kill", "ENGINE", "—",
 "The export is split into Gold / Silver / Bronze by arithmetic, not by opinion.",
 "gsb_tier.py applies M01–M07: kill sub-1% engagement, find tier boundaries at natural 2× gaps, centre Silver on the MODE, warn on 10× variance inside a tier, cap at 10 per tier. Also picks 3 alternates per tier for backfill when a video turns out dead or private.",
 "30 picks + 9 alternates.", "gsb_tier.py"),

("PH4", "PHASE", "BUILD the tab + pull the assets", "ENGINE", PING,
 "Create `R: [creator]` and fill every row with the thing you actually look at.",
 "research_tab.py lays out the tab (DATA region tinted by tier, FINDINGS region below). research_assets.py writes cheap data — link, views, likes — for all 30 rows FIRST so the tab is readable in seconds, then per pick: download H.264 → storyboard frames → Whisper transcript → upload to Drive → write thumbnail, transcript, contact sheet and frames back in as =IMAGE(). A dead video is replaced from the alternates pool automatically.",
 "A visual tab: thumbnail · transcript · storyboard · up to 40 frames per row.", "research_tab.py · research_assets.py"),

("PH5", "PHASE", "KILL #2 — your format cut", "YOU", CHECK,
 "You cut rows by eye off the storyboards. This is the first place you steer.",
 "Read across the tab and call it — \"1–6 gold, 12–18 silver, kill the rest.\" Off-format videos come out HERE (FF1): every tier must be the same format or the Gold-vs-Bronze comparison compares nothing. Then say \"go\" and analysis starts. This is also where you change the run — any adjustment to a later phase gets stated now.",
 "A trimmed tab, one format only.", "workflow orchestration"),

("PH6", "PHASE", "EVIDENCE — Gemini pass + read", "CLAUDE", "—",
 "The video pass runs FIRST, before any judgement, on every surviving video.",
 "AP1 then AP2. Gemini watches each video as a viewer and reports viewer experience, delivery, sound, pacing, on-screen text, motion and anomalies with timestamps — output lands in that row's Notes. Then the storyboard read and the transcript read per video. Observations are logged specific and citable (\"scene 3: brown-spot close-up + 'SEE THAT BROWN' overlay\"), never vague.",
 "Notes column filled per row.", "protocol AP1–AP2"),

("PH7", "PHASE", "SCREEN + VALIDATE", "CLAUDE", PING,
 "Every driver is screened Gold vs Bronze, then actively attacked before it is accepted.",
 "AP3–AP5. 19 drivers plus any format-specific candidates that emerge; strength 1–10 per video. Present in both tiers with no quality difference = discarded on the spot. Silver has to show the gradient in between. Anomalies get investigated explicitly, not skipped. No finding leaves this step as a bare tactic — the EOV bridge is mandatory.",
 "FINDINGS rows written, uncertainties flagged.", "protocol AP3–AP5"),

("PH8", "PHASE", "CONFIRM the findings", "YOU", CHECK,
 "You correct, kill or confirm. Nothing proceeds unconfirmed.",
 "Presented to you: the findings, the scoring grid, the flagged uncertainties and the anomalies. This is the ~10% of the evidence base that is your judgement — format intuition and niche knowledge that neither the frames nor the transcript carry. Second and last place the flow stops for you.",
 "Approved findings.", "protocol AP7"),

("PH9", "PHASE", "DOCUMENT + archive", "CLAUDE", "—",
 "The hypothesis doc is written, then the whole paper trail is filed and the working tab removed.",
 "AP8 writes hypothesis.md to the OUTPUT shape below. Then: copy the working tab into its OWN spreadsheet named for the creator/format → upload to Format Research / [creator]/ beside the raw CSV and assets → copy DATA + FINDINGS into the master library tab → delete the working tab from this workbook. A validated script formula graduates into the scripting library only when you adopt it.",
 "hypothesis.md + a standalone archived sheet.", "workflow Phase 7"),

("PH0", "LOOP", "Findings are never final", "BOTH", "—",
 "After videos ship on a findings doc, the results come back here.",
 "Note which drivers held on contact, downgrade the ones that didn't survive, add new findings from later analyses. FB1 governs the verdict when something flops.",
 "An updated findings doc, versioned not replaced.", "workflow — Living Documentation"),

# ---------------------------------------------------------------------------------
"QUALIFY — does this creator deserve the pipeline at all? Fires at PH1, before anything is spent.",

("Q01", "QUALIFY", "Consistent high views", "YOU", "—",
 "Hundreds of thousands to millions, regularly — not a one-hit wonder.",
 "One breakout inside an otherwise flat account tells you about that video, not about a format.",
 "", "rules.md"),
("Q02", "QUALIFY", "Success is NOT status-based", "YOU", "—",
 "No celebrities, no major brands whose identity is what drives the views.",
 "If fame is the mechanism, the mechanism is not reproducible by us.",
 "", "rules.md"),
("Q03", "QUALIFY", "Organic performance", "YOU", "—",
 "Likes-to-views above 1%. Below 1% usually means paid or boosted.",
 "Boosted content teaches you what money does, not what the format does.",
 "", "rules.md"),
("Q04", "QUALIFY", "Content age", "YOU", "—",
 "1–3 years old is ideal. 4–5 years is the hard ceiling.",
 "Older than that and the platform, the audience and the editing conventions have all moved.",
 "", "rules.md"),
("Q05", "QUALIFY", "Format, not trend", "YOU", "—",
 "A format is a reusable storytelling structure. A trend is a fleeting pattern. Research formats only.",
 "The test: the creator has 5–10+ successful videos using the SAME structure. Below that there is nothing to generalise from.",
 "", "rules.md"),

("RF1", "RED FLAG", "One viral video, otherwise flat", "YOU", "—",
 "Skip the creator.", "", "", "rules.md"),
("RF2", "RED FLAG", "Celebrity / brand account", "YOU", "—",
 "Skip the creator — fame drives the follows.", "", "", "rules.md"),
("RF3", "RED FLAG", "Heavily boosted content", "YOU", "—",
 "Skip the creator — engagement is low relative to views.", "", "", "rules.md"),

# ---------------------------------------------------------------------------------
"MATH — the tiering rules. Applied by gsb_tier.py at PH3. These exist so taste never touches the split.",

("M01", "MATH", "Clustering rule", "ENGINE", "—",
 "Tier by natural gaps, not by rank.",
 "If (video A views) ÷ (video B views) > 2 between consecutive videos, that is a tier boundary. Videos inside a tier must sit closer to each other than to the adjacent tier.",
 "", "rules.md · gsb_tier.tier()"),
("M02", "MATH", "10× variance rule", "ENGINE", "—",
 "Inside one tier, the highest video must be ≤ 10× the lowest.",
 "Exceeded means the tier is really two tiers — re-split. The tool warns rather than silently accepting it.",
 "", "rules.md · gsb_tier.tier()"),
("M03", "MATH", "Likes-to-views filter", "ENGINE", "—",
 "Below 1% likes/views is flagged and killed as likely ad-driven.",
 "YouTube ≥1%. TikTok 5–10% is typical. Use --no-kill when the export's likes column is unreliable (some SortFeed exports return a constant) so tiers form on views alone.",
 "", "rules.md · gsb_tier.pick_tiers()"),
("M04", "MATH", "Follower-to-view expectation", "CLAUDE", "—",
 "On Instagram, expect roughly 10% of followers to see a given post.",
 "Use it to judge whether a number is over- or under-performing for that account, rather than reading raw views.",
 "", "rules.md"),
("M05", "MATH", "Reference minimum", "YOU", "—",
 "5–10 successful videos in the format before it is worth analysing.", "", "", "rules.md"),
("M06", "MATH", "Content age rule", "ENGINE", "—",
 "1–2 years ideal, 3 max, 4–5 absolute ceiling.", "", "", "rules.md"),
("M07", "MATH", "100-to-1 ideation rule", "BOTH", "—",
 "Generate roughly 100 ideas for every 1 that gets finalised.",
 "Sits downstream in ideation, but it is the reason research volume matters: the funnel is wide by design.",
 "", "rules.md"),

("T1", "TIER", "GOLD", "ENGINE", "—",
 "Breakout top performers, significantly above the creator's baseline.", "", "", "rules.md"),
("T2", "TIER", "SILVER — the baseline", "ENGINE", "—",
 "The MODE, not the mean. The most frequent view level.",
 "Continuous view counts have no literal mode, so the tool finds the densest bin in log space and returns its centre. Silver is then the N videos closest to that centre.",
 "", "rules.md · gsb_tier.mode_center()"),
("T3", "TIER", "BRONZE", "ENGINE", "—",
 "Underperformers, below the median. Disappointing for THAT creator.",
 "Bronze is not 'bad content' in the abstract — it is the same creator, same audience, worse outcome. That control is what makes the contrast mean anything.",
 "", "rules.md"),
("T4", "TIER", "Tier size", "ENGINE", "—",
 "Minimum 5 per tier for analysis, cap around 10, sorted by views.", "", "", "rules.md"),
("T5", "TIER", "Per-creator baseline when pooling creators", "CLAUDE", "—",
 "Multi-creator studies tier on baseline multiple (views ÷ that creator's median), never on absolute views.",
 "Learned, not inherited from the book: pooling 7 creators on raw views tiers by audience size instead of by performance. The identical hook landed Gold at 3.1M and Bronze at 6.3k for the same creator — a 44× spread on the same structure.",
 "", "MEASURED — transformation findings, 174 videos"),

("FF1", "FILTER", "Format filter — all tiers, one format", "YOU", CHECK,
 "Before any driver analysis, every off-format video is eliminated.",
 "If the scrape mixes formats (a few green screens inside a talking-head page), they come out. Compare like with like, always. Runs at PH5 off thumbnails, storyboards and transcripts — and whatever gets removed is stated with the reason.",
 "", "rules.md"),

("K1", "PRINCIPLE", "Leave personal taste at the door", "BOTH", "—",
 "Judge by performance, not by preference.", "", "", "rules.md"),
("K2", "PRINCIPLE", "Observations are hypotheses, not facts", "CLAUDE", "—",
 "Until validated across multiple videos, a pattern is a guess with evidence attached.", "", "", "rules.md"),
("K3", "PRINCIPLE", "Focus on EOV", "CLAUDE", "—",
 "Don't copy tactics. Copy the effect the tactic creates.", "", "", "rules.md · E01"),
("K4", "PRINCIPLE", "Try to disprove your first assumption", "CLAUDE", "—",
 "Don't stop at the first pattern that fits. The first pattern that fits is the one most likely to be confirmation.", "", "", "rules.md"),
("K5", "PRINCIPLE", "Patterns need majority, not unanimity", "CLAUDE", "—",
 "Not every Gold video carries every driver. Look across the majority.", "", "", "rules.md"),

# ---------------------------------------------------------------------------------
"DRIVERS — the screen, run at PH7. For each: present in Gold? present in Bronze? strength 1–10. Present in BOTH with no quality difference = discard immediately.",

("E01", "SYSTEM", "Tactic vs EOV — the core distinction", "CLAUDE", "—",
 "Tactic = what you can see and hear. EOV = the effect it creates in the viewer.",
 "Text on screen → curiosity, clarity, intrigue. Dramatic pause → tension, anticipation. Fast cuts → energy, urgency. Slow zoom on a face → intimacy, emotional weight. Multiple tactics can serve one EOV; the EOV is the thing to replicate, in our own style.",
 "", "drivers.md"),

("D01", "DRIVER", "Perspective Shift", "CLAUDE", "—",
 "A revelation that challenges how the viewer thinks about the topic.",
 "Debunking a misconception, a new idea, a different point of view.", "", "drivers.md"),
("D02", "DRIVER", "Absurdity", "CLAUDE", "—",
 "Unexpected, ridiculous or illogical elements that are hard to look away from.",
 "Novelty peaks interest; weirdness holds it; the viewer stays for the resolution.", "", "drivers.md"),
("D03", "DRIVER", "Cleverness", "CLAUDE", "—",
 "Unexpected AND smart — unrelated ideas connected logically.",
 "The reaction to aim for: \"why didn't I think of that?\"", "", "drivers.md"),
("D04", "DRIVER", "Tension", "CLAUDE", "—",
 "Making the viewer need to know what happens next.",
 "The Jenga effect: one main problem plus multiple obstacles building toward it.", "", "drivers.md"),
("D05", "DRIVER", "Viewer Connection", "CLAUDE", "—",
 "A personal relationship with the viewer.",
 "Eye contact, calling them \"you\", framing to the average viewer's POV, predicting what they're thinking.", "", "drivers.md"),
("D06", "DRIVER", "Dynamics", "CLAUDE", "—",
 "Intentional changes in energy across storylines, visuals or audio.",
 "Prevents any single energy from going monotonous.", "", "drivers.md"),
("D07", "DRIVER", "Delivery", "CLAUDE", "—",
 "Vocal tone, inflection, pacing, expression and body language supporting the words.",
 "Largely invisible in frames — this is what the Gemini pass at AP1 exists to capture.", "", "drivers.md"),
("D08", "DRIVER", "Reactivity", "CLAUDE", "—",
 "Genuine, strong responses from strangers or characters on screen.",
 "Authentic reactions create emotional resonance and social proof.", "", "drivers.md"),
("D09", "DRIVER", "Drama", "CLAUDE", "—",
 "Storytelling tropes, conflict, music and delivery used to heighten emotional intensity.", "", "", "drivers.md"),
("D10", "DRIVER", "Contrast", "CLAUDE", "—",
 "Juxtaposition of two or more items to direct attention or create curiosity.",
 "Lives in storyline, visuals, delivery, thumbnails and titles.", "", "drivers.md"),
("D11", "DRIVER", "Promise of Value", "CLAUDE", "—",
 "An implicit signal the viewer will be rewarded for their time.",
 "Entertainment, education, advice, emotional validation, a unique experience. Usually at the start — a type of hook.", "", "drivers.md"),
("D12", "DRIVER", "Work-to-Wow Ratio", "CLAUDE", "—",
 "Effort the viewer spends vs value received. LOW ratio wins.",
 "High effort for little return kills retention outright.", "", "drivers.md"),
("D13", "DRIVER", "Extra Layer", "CLAUDE", "—",
 "Elements that amplify the main idea — props, costumes, skits, challenges.",
 "Multiple avenues holding attention at once.", "", "drivers.md"),
("D14", "DRIVER", "Generalist Principle", "CLAUDE", "—",
 "Framing a niche topic for a general audience.",
 "Treat the audience as unfamiliar: broad relatable subjects, no jargon, stories with conflict.", "", "drivers.md"),
("D15", "DRIVER", "Hook", "CLAUDE", "—",
 "The initial moment that decides whether the audience continues.",
 "Conveys the premise and builds expectation of value. Visual, text, audio, curiosity gap, promise of value or potential energy. Hook TYPE taxonomy is HK01–HK16 below.", "", "drivers.md · hooks.md"),
("D16", "DRIVER", "Pacing", "CLAUDE", "—",
 "The rate at which ideas arrive — not the shot count.",
 "Highlight what matters, fast-forward through repetition.", "", "drivers.md"),
("D17", "DRIVER", "Storytelling", "CLAUDE", "—",
 "A message conveyed through a narrative sequence of events.",
 "Creates context and builds a world, which forms a stronger connection than assertion does.", "", "drivers.md"),
("D18", "DRIVER", "Satisfying", "CLAUDE", "—",
 "Caters to the senses, or delivers fulfilment through order, pattern or task completion.", "", "", "drivers.md"),
("D19", "DRIVER", "Setup and Payoff", "CLAUDE", "—",
 "Setup gives a reason to stay; payoff fulfils the promise.",
 "All viral content has setup. Not all has a clear payoff — that gap is where videos die.", "", "drivers.md"),

("PR1", "PRIORITY", "P1 Critical", "CLAUDE", "—",
 "Present in 90%+ of Gold, absent in 90%+ of Bronze. Production effort goes here first.", "", "", "drivers.md"),
("PR2", "PRIORITY", "P2 Important", "CLAUDE", "—",
 "Present in 70–90% of Gold, mostly absent in Bronze.", "", "", "drivers.md"),
("PR3", "PRIORITY", "P3 Helpful", "CLAUDE", "—",
 "Noticeable correlation, less consistent.", "", "", "drivers.md"),
("PR4", "PRIORITY", "P4 Minor", "CLAUDE", "—",
 "Small effect, context-dependent.", "", "", "drivers.md"),

# ---------------------------------------------------------------------------------
"HOOKS — tag every video with one hook type. Patterns across the tags become format intelligence over time.",

("HK01", "HOOK", "Conditional Trigger", "CLAUDE", "—",
 "\"If you [have this], then [do this].\" Instant personal relevance by matching the viewer's situation.", "", "", "hooks.md"),
("HK02", "HOOK", "Body Indicator", "CLAUDE", "—",
 "Opens on a physical sign the viewer might recognise in themselves. Triggers self-diagnosis curiosity.", "", "", "hooks.md"),
("HK03", "HOOK", "Demographic Target", "CLAUDE", "—",
 "Calls out a specific group directly. Stops the scroll for exactly that audience.", "", "", "hooks.md"),
("HK04", "HOOK", "Secret Reveal", "CLAUDE", "—",
 "Promises hidden or suppressed information. Information-gap curiosity.", "", "", "hooks.md"),
("HK05", "HOOK", "Fear Symptom", "CLAUDE", "—",
 "Leads with a scary symptom or consequence. Urgency-driven attention grab.", "", "", "hooks.md"),
("HK06", "HOOK", "Question Hook", "CLAUDE", "—",
 "Opens with a direct question. Engages the brain to seek an answer.", "", "", "hooks.md"),
("HK07", "HOOK", "Authority Claim", "CLAUDE", "—",
 "Establishes credibility immediately. Instant trust.", "", "", "hooks.md"),
("HK08", "HOOK", "Contrarian Take", "CLAUDE", "—",
 "Challenges a common belief. Pattern interrupt that demands explanation.", "", "", "hooks.md"),
("HK09", "HOOK", "Action Ritual", "CLAUDE", "—",
 "Prescribes a specific routine. A concrete step the viewer can take immediately.", "", "", "hooks.md"),
("HK10", "HOOK", "Time Urgency", "CLAUDE", "—",
 "Creates a time constraint. Pressures immediate attention.", "", "", "hooks.md"),
("HK11", "HOOK", "Social Proof", "CLAUDE", "—",
 "References what others are doing. FOMO and herd mentality.", "", "", "hooks.md"),
("HK12", "HOOK", "Transformation Tease", "CLAUDE", "—",
 "Hints at a dramatic before/after. Promise of visible results.", "", "", "hooks.md"),
("HK13", "HOOK", "List Format", "CLAUDE", "—",
 "Structures content as a numbered list. Clear expectation of what's coming.", "", "", "hooks.md"),
("HK14", "HOOK", "Myth Buster", "CLAUDE", "—",
 "Challenges a widely held belief. Disrupts the viewer's existing mental model.", "", "", "hooks.md"),
("HK15", "HOOK", "Emotional Story", "CLAUDE", "—",
 "Opens with a personal or emotional narrative. Connects on a human level.", "", "", "hooks.md"),
("HK16", "HOOK", "Unclassified", "CLAUDE", "—",
 "Doesn't fit the existing categories — flag it.",
 "A hybrid or genuinely new approach is worth studying. This row is how new hook types get discovered instead of being forced into an old label.", "", "hooks.md"),

("CAT01", "CATEGORY", "Content categories are niche-specific — they do NOT live here", "BOTH", "—",
 "Every video also gets one content category, and that list belongs to the brand, not to the engine.",
 "The category set is the one part of this protocol that changes per niche. It stays with the brand or character it describes, so this tab holds only the instruction. A health set would read Skin & Hair / Blood Sugar / Gut Health / Inflammation …; an AI-creator set reads nothing like it.",
 "One category per video, from the brand's own list.", "hooks.md — kept deliberately empty"),

# ---------------------------------------------------------------------------------
"PROTOCOL — the analysis itself, step by step. Runs inside PH6–PH9. This is the part that runs solo, no question sequence.",

("EV1", "SYSTEM", "Evidence split — 80 / 10 / 10", "BOTH", "—",
 "Where the evidence actually comes from, declared up front.",
 "~80% Claude on storyboards, frames and transcripts — visual structure, script structure, hooks, pacing by scene, overlays, settings, props, characters. ~10% the Gemini video pass — what frames cannot show. ~10% your judgement at PH8 — format intuition, niche knowledge, corrections.",
 "", "protocol"),

("AP1", "STEP", "Gemini video pass — evidence FIRST", "CLAUDE", "—",
 "Runs on every surviving video before any judgement is formed. Output goes into that row's Notes.",
 "One prompt, one output per video (≤2 min): \"You are a viral short-form video analyst. Watch this video as a viewer would, then report with timestamps: 1 VIEWER EXPERIENCE — beat by beat as experienced, what you notice first, where attention spikes or drifts, the moment you'd scroll away or why you wouldn't. 2 DELIVERY — vocal tone, cadence, inflection shifts, where energy rises and falls. 3 SOUND — music, sound design, silence, audio hooks. 4 PACING — real-time rhythm, where it's fast, where it breathes, how cuts feel. 5 ON-SCREEN TEXT — timing and interplay with speech; does text lead, lag or echo. 6 MOTION — camera and subject movement beat by beat, phrased so it could be reused as a video-generation motion prompt. 7 ANOMALIES — anything that wouldn't show up in static frames or a transcript. Redundancy with a transcript is fine. Specific observations with timestamps beat general summaries.\"",
 "MOTION does double duty — analysis evidence here, and motion-prompt source material for the recreation pipeline.", "protocol AP1"),

("AP1b", "STEP", "Upload the FILE, not a Drive link", "ENGINE", "—",
 "The Gemini pass takes a local copy through the files API.",
 "Drive blocks direct downloads of folders and sometimes flags multi-file fetches. Observed failure, 2026-06-03. Pull the video locally first, then upload.",
 "", "MEASURED"),

("AP2", "STEP", "Per-video evidence read", "CLAUDE", "—",
 "Storyboard read plus transcript read, logged into Notes, for every surviving video.",
 "Storyboard: scene count, scene lengths as a pacing map, settings, characters, props, on-screen text per scene, the visual hook in the first frames, overlay patterns. Transcript: verbal hook, structure and beats, question density, reveal timing, CTA placement and wording. Log it citable — \"scene 3: brown-spot close-up + 'SEE THAT BROWN' overlay\" — never \"good visuals\".",
 "", "protocol AP2"),

("AP3", "STEP", "Driver screen", "CLAUDE", "—",
 "Every driver, against every tier, scored.",
 "For each of the 19 (plus format-specific candidates that emerge): present in Gold and how, citing videos; present in Bronze and how it differs; strength 1–10 per video into the grid. Present in both with no quality difference → discarded immediately, no further work.",
 "", "protocol AP3"),

("AP4", "STEP", "Validation", "CLAUDE", "—",
 "Four outcomes, and only two of them are findings.",
 "In Gold, absent or weak in Bronze → validated UPWARD driver. Only in Bronze → validated DOWNWARD driver, an avoid-this. In both at the same quality → not a driver, discard. Inconsistent → flag as needs-more-data or context-dependent. Cross-checks: Silver should show the gradient; anomalies get investigated explicitly; majority not unanimity; actively try to DISPROVE each candidate before accepting it.",
 "", "protocol AP4"),

("AP5", "STEP", "Tactic → EOV bridge — MANDATORY", "CLAUDE", "—",
 "No finding ships as a bare tactic.",
 "Every finding states the tactic (what is seen or heard) + the EOV (what the viewer feels) + why that effect drives retention or engagement. Several tactics can serve one EOV — the EOV is what gets replicated, not the tactic.",
 "", "protocol AP5"),

("AP6", "STEP", "Write findings into the tab", "CLAUDE", "—",
 "Four columns per finding, in the FINDINGS region below the data.",
 "Driver (from the master list, or newly named) · Takeaway & Explanation (the NAMED takeaway in caps, then how it manifests in this format and why it works) · Gold Evidence (specific video, specific moment) · Bronze Evidence (specific video, how it is absent, weak or different). Prioritised P1–P4.",
 "", "protocol AP6"),

("AP7", "STEP", "User checkpoint", "YOU", CHECK,
 "Findings, scoring grid, flagged uncertainties and anomalies — presented for correction.",
 "You correct, kill or confirm. Nothing proceeds to the hypothesis doc unconfirmed.",
 "", "protocol AP7"),

("AP8", "STEP", "Hypothesis doc", "CLAUDE", "—",
 "The actual product of research — the scripting instrument, not a report.",
 "Written to the OUTPUT shape below and filed to Format Research / [creator]/.",
 "hypothesis.md", "protocol AP8"),

("FB1", "LOOP", "Feedback rule — closes the loop", "BOTH", "—",
 "When a video built on a hypothesis flops, compare it against the Gold reference.",
 "Matches the standard and still flopped → the research was wrong; revisit and form new hypotheses. Doesn't match the standard → an execution problem, not a research problem. Log either verdict in the hypothesis doc. Without this the findings never get corrected by reality.",
 "", "protocol · the book"),

("DOC1", "SYSTEM", "The book governs the ANALYSIS, not the EXECUTION", "BOTH", "—",
 "Analyse orthodox; apply however you decide.",
 "Kane's model governs GSB contrast, tactic→EOV and hypothesis validation. It does NOT govern branding levels, posting cadence or batching — deviating there is your call and is not a protocol violation.",
 "", "Kane, Guide to Going Viral"),

# ---------------------------------------------------------------------------------
"OUTPUT — the findings doc shape. Every section earns its place: a driver with nothing under Evidence is not validated yet.",

("O01", "OUTPUT", "Header", "CLAUDE", "—",
 "FORMAT · CREATOR(S) ANALYZED · DATE · SAMPLE (# Gold / # Silver / # Bronze).", "", "", "findings_template.md"),
("O02", "OUTPUT", "Primary hypothesis", "CLAUDE", "—",
 "ONE testable sentence about what drives performance in this format.",
 "If it can't be written as one sentence that could be proven wrong, the analysis isn't finished.", "", "findings_template.md"),
("O03", "OUTPUT", "Driver blocks", "CLAUDE", "—",
 "One block per validated driver, each with eight fields.",
 "Hypothesis (specific, with thresholds where possible) · Reasoning (the EOV) · Function (stop scroll / commitment / retention / persuasion / conversion) · Timeframe (where in the video it lives) · Failure Mode (what happens when it's missing) · Relationships (how it differs from neighbouring drivers) · Gold evidence · Bronze evidence. Tagged P1–P4.",
 "", "findings_template.md"),
("O04", "OUTPUT", "Quick reference table", "CLAUDE", "—",
 "Driver | high-performer pattern | low-performer pattern. The at-a-glance version.", "", "", "findings_template.md"),
("O05", "OUTPUT", "Script formula", "CLAUDE", "—",
 "The structural blueprint, mapped section by section to the drivers.",
 "[HOOK — PD1] [SETUP — PD2] … [CTA — PD9]. This is what graduates into the scripting library once you adopt it — and it is the handoff point from research into the wheel.",
 "", "findings_template.md"),
("O06", "OUTPUT", "Hook templates", "CLAUDE", "—",
 "Extracted from the Gold hooks with the topic words stripped out.",
 "What's left is the reusable shape. Feeds hook-only respins directly.", "", "findings_template.md"),
("O07", "OUTPUT", "Scorecard", "CLAUDE", "—",
 "Every script written in this format gets scored against the drivers BEFORE production.",
 "Driver | target | score 1–10 | total out of max. This is what makes the research bind on the output instead of being read once and forgotten.",
 "", "findings_template.md"),
("O08", "OUTPUT", "Validated downward drivers", "CLAUDE", "—",
 "The avoid-this list, with why each one hurts.", "", "", "findings_template.md"),
("O09", "OUTPUT", "Inconclusive", "CLAUDE", "—",
 "Elements that needed more data. Kept visible rather than quietly dropped.", "", "", "findings_template.md"),
("O10", "OUTPUT", "Anomalies", "CLAUDE", "—",
 "Videos that break the pattern, and the best available explanation.",
 "Good structure that flopped, bad structure that hit. Never skipped.", "", "findings_template.md"),
("O11", "OUTPUT", "Null hypothesis", "CLAUDE", "—",
 "\"There is no performance difference between [the mechanism] and [the alternative].\" Status: rejected or standing, based on what.",
 "Forces the analysis to state what would have proven it wrong.", "", "findings_template.md"),
("O12", "OUTPUT", "Evidence log", "CLAUDE", "—",
 "Finding · pattern · Gold evidence · Bronze evidence · COUNTER-EVIDENCE · conclusion · application.",
 "The counter-evidence line is the important one — it is the proof the finding was actually tested rather than merely noticed.",
 "", "findings_template.md"),

# ---------------------------------------------------------------------------------
"TOOLS — what runs at each phase. These live in the repo as executables; everything above lives here in the sheet.",

("TL1", "TOOL", "gsb_tier.py", "ENGINE", "—",
 "Applies the math to a SortFeed CSV. PH3.",
 "python3 gsb_tier.py --csv <file>              full tiering table\npython3 gsb_tier.py --csv <file> --pick 10    research selection, 10 per tier + alternates\n--no-kill skips the engagement filter when the export's likes column is unreliable.\nColumns are auto-detected (views/plays, likes, url/link, title/caption); 1.5M and 340K parse.",
 "Gold / Silver / Bronze with view ranges, warnings and flags.", "engine/execution"),
("TL2", "TOOL", "research_tab.py", "ENGINE", "—",
 "Creates the `R: [creator]` working tab. PH4.",
 "python3 research_tab.py --creator <handle> [--picks 10]\nDATA region tinted by tier, 220px rows so storyboards are readable; FINDINGS region scaffolded below with the four columns from AP6.",
 "An empty, correctly-shaped working tab.", "engine/execution"),
("TL3", "TOOL", "research_assets.py", "ENGINE", "—",
 "Fills the tab with picks and assets. PH4.",
 "python3 research_assets.py --creator <handle> --csv <file> [--picks 10] [--no-kill]\nWrites cheap data for all 30 rows first, then per pick: yt-dlp H.264 download → storyboard frames → Whisper transcript (medium — base fails silently on non-English) → Drive upload → =IMAGE() write-back. Dead or private videos are replaced from the alternates pool automatically.",
 "A filled, visual working tab + the paper trail in Drive.", "engine/execution"),
("TL4", "TOOL", "Archive destination", "ENGINE", "—",
 "Where a finished research lands. PH9.",
 "Format Research / [creator]/ holds the raw CSV, hypothesis.md, assets/ and the standalone copy of the working tab — the complete paper trail in one folder. The working tab is then deleted from this workbook so the master doesn't accumulate.",
 "", "workflow Phase 7"),
("TL5", "TOOL", "Not wired yet — Discord `research` tag", "ENGINE", "—",
 "The bot does not yet route a CSV tagged `research` into a research tab.",
 "Specced in research_intake.md piece 4. Until it is built, hand over the CSV path and PH3 runs manually. This is the only gap between the protocol as written and the protocol as running.",
 "", "OPEN"),
]


def cell(v, bold=False, size=9, color=None, bg=None, wrap="CLIP", va="MIDDLE"):
    s = "" if v is None else str(v)
    return {
        "userEnteredValue": {"stringValue": s},
        "userEnteredFormat": {
            "backgroundColor": bg or PAPER,
            "horizontalAlignment": "LEFT",
            "verticalAlignment": va,
            "wrapStrategy": wrap,
            "textFormat": {"bold": bold, "fontSize": size, "foregroundColor": color or TEXT},
        },
    }


# Row height is computed from the content, not fixed, and then capped. Uncapped
# auto-fit is what makes a long row unreadable — the user's read of `Prompting
# Rules`: P03 is a good size, PX08 is too tall. MAX_H is ~7 wrapped lines, which
# lands between them. Anything longer clips and is read by clicking the cell.
CHAR_PX = 5.1        # average glyph width at font size 9
LINE_PX = 13
MIN_H, MAX_H = 36, 104
WRAP_COLS = {2, 5, 6, 7, 8}   # NAME · WHAT IT IS · DETAIL · OUTPUT · SOURCE


def est_lines(text: str, width_px: int) -> int:
    if not text:
        return 1
    cpl = max(int(width_px / CHAR_PX), 10)
    return sum(max(1, -(-len(p) // cpl)) for p in str(text).split("\n"))


def row_height(values: list[str]) -> int:
    lines = max(est_lines(values[i], WIDTHS[i]) for i in WRAP_COLS)
    return max(MIN_H, min(MAX_H, lines * LINE_PX + 8))


def build():
    """Return (rows, banner_row_indexes, heights) — indexes 0-based in the block."""
    rows, banners, heights = [], [], []
    rows.append({"values": [cell(h, bold=True, size=10, color=PAPER, bg=INK) for h in HEADERS]})
    heights.append(26)

    for item in ROWS:
        if isinstance(item, str):
            banners.append(len(rows))
            vals = [cell(item, bold=True, size=10, color=PAPER, bg=INK)]
            vals += [cell("", bg=INK) for _ in range(NCOLS - 1)]
            rows.append({"values": vals})
            heights.append(28)
            continue

        rid, kind, name, who, gate, what, detail, out, src = item
        tint = TINT.get(kind, PAPER)
        gated = gate not in ("", "—")
        rows.append({"values": [
            cell(rid, bold=True, bg=tint, va="TOP"),
            cell(kind, bold=True, bg=tint, va="TOP"),
            cell(name, bold=kind == "PHASE", wrap="WRAP", va="TOP"),
            cell(who, bold=True, va="TOP"),
            cell(gate, bold=gated, bg=TINT["TIER"] if gated else PAPER, wrap="WRAP", va="TOP"),
            cell(what, wrap="WRAP", va="TOP"),
            cell(detail, wrap="WRAP", va="TOP"),
            cell(out, wrap="WRAP", va="TOP"),
            cell(src, color={"red": 0.42, "green": 0.45, "blue": 0.50}, wrap="WRAP", va="TOP"),
        ]})
        heights.append(row_height([rid, kind, name, who, gate, what, detail, out, src]))
    return rows, banners, heights


def main():
    ap = argparse.ArgumentParser(description="Build the Research Rules tab")
    ap.add_argument("--rebuild", action="store_true", help="replace the tab if it exists")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cfg = json.loads(CONFIG.read_text())
    ssid = cfg["workspace"]["master_db_id"]

    rows, banners, heights = build()
    n = len(rows)
    if a.dry_run:
        entry_h = [h for i, h in enumerate(heights) if i and i not in banners]
        print(f"[dry-run] {TAB}: {n} rows ({len(banners)} section banners, "
              f"{n - 1 - len(banners)} entries), {NCOLS} columns.")
        print(f"          row heights {min(entry_h)}-{max(entry_h)}px "
              f"(median {sorted(entry_h)[len(entry_h)//2]}, capped at {MAX_H}), "
              f"{sum(1 for h in entry_h if h == MAX_H)} rows at the cap.")
        i = 0
        for r in ROWS:
            if isinstance(r, str):
                print(f"  §  {r}")
                continue
            i += 1
            print(f"     {r[0]:<6} {r[1]:<10} {r[2][:46]:<48} {entry_h[i-1]:>3}px")
        return

    svc = gs.get_sheets_service()
    info = svc.spreadsheets().get(spreadsheetId=ssid).execute()
    existing = {s["properties"]["title"]: s["properties"]["sheetId"] for s in info["sheets"]}

    if TAB in existing and not a.rebuild:
        sys.exit(f"'{TAB}' already exists. Re-run with --rebuild to replace it "
                 f"(this discards anything edited in the tab).")
    if TAB in existing:
        svc.spreadsheets().batchUpdate(spreadsheetId=ssid, body={
            "requests": [{"deleteSheet": {"sheetId": existing[TAB]}}]}).execute()

    # Append after whatever tabs already exist, rather than a hardcoded index
    # — a fresh Master DB with only "Database" doesn't have the same tab
    # layout this script's original spreadsheet did, and a fixed index fails
    # with "index too high" as soon as the spreadsheet has fewer tabs than that.
    index = len(info["sheets"]) - (1 if TAB in existing else 0)

    r = svc.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": [
        {"addSheet": {"properties": {
            "title": TAB, "index": index,
            "gridProperties": {"rowCount": n + 20, "columnCount": NCOLS,
                               "frozenRowCount": 1}}}}]}).execute()
    gid = r["replies"][0]["addSheet"]["properties"]["sheetId"]

    svc.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": [
        {"updateCells": {"rows": rows, "fields": "userEnteredValue,userEnteredFormat",
                         "start": {"sheetId": gid, "rowIndex": 0, "columnIndex": 0}}}]}).execute()

    reqs = [{"mergeCells": {"range": {"sheetId": gid, "startRowIndex": i, "endRowIndex": i + 1,
                                      "startColumnIndex": 0, "endColumnIndex": NCOLS},
                            "mergeType": "MERGE_ALL"}} for i in banners]
    reqs += [{"updateDimensionProperties": {
        "range": {"sheetId": gid, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}} for i, px in enumerate(WIDTHS)]
    # per-row heights, runs of equal height collapsed into one request
    start = 0
    for i in range(1, n + 1):
        if i < n and heights[i] == heights[start]:
            continue
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": gid, "dimension": "ROWS",
                      "startIndex": start, "endIndex": i},
            "properties": {"pixelSize": heights[start]}, "fields": "pixelSize"}})
        start = i
    svc.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": reqs}).execute()

    print(f"✅ '{TAB}' built — {n} rows, {len(banners)} sections, "
          f"{n - 1 - len(banners)} entries. Tab index 5, after Prompting Rules.")


if __name__ == "__main__":
    main()
