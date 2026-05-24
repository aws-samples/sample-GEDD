# PM interview script — testing the riskiest assumption

**Status:** ready to run · **Owner:** TBD · **Last updated:** 2026-05-23

## Why this interview

GEDD is built on a stack of bets. The riskiest is:

> **PMs do error analysis solo, and the output is trusted enough by engineering to drive code changes.**

If <2 of 5 PMs say their analysis directly drove an engineering change, the solo-PM thesis is broken and we should pivot toward a **collaborative-first** product (shared workspace, comments, threaded discussion with the AI engineer) before anything else.

Cheap to test. 30 minutes per call. Five calls.

## Recruiting (5 PMs)

**Profile:**
- Product manager at a company shipping a customer-facing AI feature (chatbot, agent, copilot) — must be in production, not prototype.
- Has personally reviewed agent output in the last 30 days.
- Not an ML engineer. Doesn't ship code as part of their day job.

**Channels:**
- Lenny's Newsletter Slack (#ai-product-management)
- Reforge AI Community
- LinkedIn outreach to "AI Product Manager" titles at Series B-D companies
- Personal network — start here, fastest

**Incentive:** $75 Amazon gift card. Half-promise: "we'll share what we learn from the 5 calls."

**Outreach DM:**
> Hi [name] — I'm researching how PMs at AI-shipping companies actually review agent output (vs. how the eval-tools market thinks they do). 30 min call, $75 gift card. Looking for 5 people. Interested?

## Format

- 30 minutes
- Recorded with consent (Zoom + transcript)
- One interviewer, one note-taker if possible
- No demo of GEDD. Pure observation. Do not pitch.

## Questions (ordered)

### Frame (2 min)
> "I'm not selling anything. I'm trying to understand how you actually work, not how the tools market thinks you do. There are no wrong answers. Walk me through the *last specific time* you reviewed AI agent output — not in general, the actual last time."

### Q1 — The trigger (4 min)
> "What kicked off that review session? Were you looking for something specific, or just looking?"

**Listen for:** Bug report from CX? Pre-release QA? Exec asked? Curiosity? *Triggers reveal the underlying job.*

### Q2 — The artifact (5 min)
> "Show me where the traces lived. Walk me through what you opened. If you can share screen, even better."

**Listen for:** Spreadsheet? LangSmith dashboard? Slack thread? Internal tool? PDF export? *This tests the paste-in assumption directly. If they say "internal tool I can't export from," paste-in is half-dead.*

### Q3 — The action (5 min)
> "What did you actually do — like, click by click? Did you label anything? Categorize? Make notes? Send anything to anyone?"

**Listen for:** Solo or pair? Did they tag/label? Did they invent categories or use predefined ones? Did they write a doc/Slack message at the end? *This tests the methodology fit.*

### Q4 — The handoff (5 min) ← **the critical question**
> "What happened after? Who saw your analysis? Did anything change in the product as a result?"

**Listen for:**
- Did the engineer change a prompt / model / RAG config based on the analysis?
- Was the analysis discussed in standup / sprint planning / a doc?
- Did the PM run this solo or with the AI engineer in the room?
- *This is the entire riskiest-assumption test.*

### Q5 — The frustration (5 min)
> "What was the most annoying part? If a magic genie could fix one thing about that workflow, what would you ask for?"

**Listen for:** Tooling friction (paste-in wedge), social friction (collaboration wedge), methodology gap (does GEDD's frame even resonate?), output gap (their analysis didn't matter — collab wedge confirmed).

### Q6 — The team shape (3 min)
> "Who do you usually do this work with? Are you alone, paired with an engineer, in a working session with multiple people?"

**Listen for:** Direct test of the solo-PM assumption.

### Wrap (1 min)
> "If I built a tool that did [paraphrase their #1 frustration], would you actually try it? What would make you say no?"

## Scoring rubric

After each call, score on a fresh sheet (don't cross-reference until all 5 done — avoid anchoring).

| Dimension | Score 1 | Score 3 | Score 5 |
|---|---|---|---|
| **Drove eng change** (Q4) | Analysis ignored / shelved | Mentioned, no clear action | Engineer changed code/prompt directly |
| **Solo work** (Q3, Q6) | Always paired with engineer | Sometimes solo, sometimes paired | Always solo, hands result over |
| **Trace portability** (Q2) | Traces locked in tool, can't export | CSV available with effort | Traces routinely pasted/shared |
| **Methodology fit** (Q3) | Pure vibes, no labeling | Some categorization | Already doing open-coding by another name |
| **Pain acuity** (Q5) | "It's fine" | Mild frustration | "I waste hours on this" |

## Decision criteria

After 5 calls, tally:

- **"Drove eng change" average ≥ 3.5:** Solo-PM thesis intact. Continue building GEDD as designed.
- **"Drove eng change" average < 3.5:** Solo-PM thesis broken. Pivot toward collab-first features (shared workspace, traces with comments, @-mention engineer, status workflow on each failure pattern). Block paste-in build until collab basics ship.
- **"Trace portability" average ≥ 3:** Build paste-in (proposal in `paste-in-traces.md`).
- **"Trace portability" average < 3:** Build LangSmith importer instead. Paste-in is wrong front door.
- **"Methodology fit" average < 2:** Strip "grounded theory" / "open coding" from the user-facing UI entirely. The PM doesn't recognize the frame; they need outcomes language.
- **"Pain acuity" average < 3 across all 5:** Reconsider whether this is a tool problem at all. May be a courseware problem (Hamel + Shreya already do that).

## What NOT to ask

- Do NOT ask "would you use a tool that..." — Steve Blank's rule. The data is in past behavior, not stated preference.
- Do NOT pitch GEDD or grounded theory. If they ask what we're building, defer: "I'll share once I've talked to a few more people."
- Do NOT ask leading questions ("how frustrating is the LangSmith UI?"). Use neutral phrasings ("how does that part feel?").

## After all 5 calls

- 1-page synthesis: top 3 patterns, top 3 contradictions, 1 surprise.
- Update this doc with the actual scores.
- Decide: build paste-in / build collab features / build LangSmith importer / pause and rethink.

Run the calls before any of the v0.2 paste-in work. The point of the test is to *not* build the wrong thing.
