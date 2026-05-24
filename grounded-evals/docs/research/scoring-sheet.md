# Scoring sheet — fill out AFTER all 5 calls in one sitting

**When to use:** after all 5 calls are complete and notes are written. Not before. Not between calls.

**Why batch:** scoring during/between calls anchors you to the first interviewee. Batched scoring forces you to compare across the full set, which is the point.

**How long:** 60 minutes for 5 calls. Read all 5 notes first (no scoring), then score in one pass.

---

## The rubric (from `interview-script.md`)

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| **Drove eng change** (Q4) | Analysis ignored / shelved | Mentioned, no clear action | Engineer changed code/prompt directly |
| **Solo work** (Q3, Q6) | Always paired with engineer | Sometimes solo, sometimes paired | Always solo, hands result over |
| **Trace portability** (Q2) | Traces locked in tool, can't export | CSV available with effort | Traces routinely pasted/shared |
| **Methodology fit** (Q3) | Pure vibes, no labeling | Some categorization | Already doing open-coding by another name |
| **Pain acuity** (Q5) | "It's fine" | Mild frustration | "I waste hours on this" |

---

## Scoring grid

Fill in 1-5 for each cell. **Use the actual rubric anchors above** — don't ad-lib midpoints unless the data clearly says 2 or 4.

| | Drove eng change | Solo work | Trace portability | Methodology fit | Pain acuity |
|---|---|---|---|---|---|
| **Call 1** ({name}) | | | | | |
| **Call 2** ({name}) | | | | | |
| **Call 3** ({name}) | | | | | |
| **Call 4** ({name}) | | | | | |
| **Call 5** ({name}) | | | | | |
| **Average** | | | | | |

---

## Decision gates (apply averages to the rules)

After filling the grid, check each gate. The decision is the *averages*, not your gut.

### Gate A — Solo-PM thesis

- **Drove eng change avg ≥ 3.5:** Solo-PM thesis intact. Continue building GEDD as designed. → ☐
- **Drove eng change avg < 3.5:** Solo-PM thesis broken. Pivot toward collab-first features (shared workspace, threaded comments on traces, @-mention engineer, status workflow per failure pattern). Block paste-in build until collab basics ship. → ☐

### Gate B — Paste-in front door

- **Trace portability avg ≥ 3:** Build paste-in entry point per `paste-in-traces.md` v0.1. → ☐
- **Trace portability avg < 3:** Skip paste-in. Build a LangSmith CSV importer first instead — paste-in is the wrong front door if traces are locked in tools. → ☐

### Gate C — Methodology vocabulary

- **Methodology fit avg ≥ 3:** Keep grounded-theory framing in user-facing UI; PMs recognize the shape. → ☐
- **Methodology fit avg < 2:** Strip "grounded theory," "open coding," "axial coding," "paradigm model" from the user-facing UI entirely. Use outcomes language instead. Keep the academic frame in marketing for the buyer. → ☐
- **Methodology fit avg between 2 and 3:** Soften but don't strip. Replace section headers with plain language; keep methodology in tooltips/docs. → ☐

### Gate D — Is this a tool problem at all?

- **Pain acuity avg ≥ 3:** Tool-shaped problem, continue. → ☐
- **Pain acuity avg < 3 across all 5:** Reconsider — may be a courseware problem (Hamel + Shreya already do that). Pause feature work; spend a week reading more posts before committing more. → ☐

### Gate E — Wrong segment

- **3+ calls scored "no" on recruiting fit** (in their notes-template metadata): the recruiting screen is broken. Re-segment. The 5 calls don't count toward the decision. → ☐

---

## Aggregate findings (write after gates are checked)

**Top 3 patterns** (things that showed up in 3+ calls):

1.
2.
3.

**Top 3 contradictions** (things where 2 calls said opposite things):

1.
2.
3.

**1 surprise** (one thing you didn't expect, that you couldn't have written down before the calls):

-

**Verbatim quotes worth keeping** (3-5 max — the ones that compress an entire pattern into one sentence):

> ""

> ""

> ""

---

## Decisions taken

Based on the gates above, the next 2 weeks will:

- ☐ Continue building paste-in (per `paste-in-traces.md`)
- ☐ Pause paste-in, build LangSmith importer instead
- ☐ Build collab-first features (define scope in a new doc)
- ☐ Strip methodology vocabulary from the UI
- ☐ Re-recruit and re-run the 5 calls
- ☐ Pause feature work entirely; reconsider thesis
- ☐ Other: ___________________________

**Owner:** {name} · **Decision date:** YYYY-MM-DD

Move the decision into the next sprint plan or a new design doc. Don't leave it in this scoring sheet — this file is the *record*, not the *plan*.
