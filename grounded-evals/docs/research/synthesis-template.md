# Synthesis — 5 PM interviews

**Date:** YYYY-MM-DD
**Author:** {your name}
**Calls covered:** 5 PMs at {brief segment description}

---

## TL;DR (write this LAST, after the rest of the doc)

In 3 sentences max. The decision, the evidence behind it, the next step.

> Example: *Solo-PM thesis is mostly intact (3.6/5 average) but every PM had a story where their analysis stalled at the engineer handoff. Paste-in is the right front door (4/5 trace portability) but we underbuilt the engineer-handoff side. Next step: build engineer-ready exports (Linear ticket batch + LangSmith dataset) before paste-in v0.1.*

---

## Methodology (1 paragraph)

5 calls, 30 minutes each, conducted {date range}. Recruited via {channels}. Profile: PMs at companies shipping AI agents in production, not ML engineers. Recordings + transcripts archived in {location}. Scoring rubric in `scoring-sheet.md`. This synthesis was written {N} days after the last call.

---

## What I learned

### Top 3 patterns (showed up in 3+ calls)

**Pattern 1 — {one-line headline}**

What it is: 1-3 sentences describing the pattern.

Evidence (3 calls minimum):
- Call {N1} ({name}): {1-line specific evidence + verbatim quote if possible}
- Call {N2} ({name}): {evidence}
- Call {N3} ({name}): {evidence}

Implication for GEDD:
- {1-2 sentences on what this means for the product}

---

**Pattern 2 — {headline}**

What it is:

Evidence:
- Call {N}:
- Call {N}:
- Call {N}:

Implication:

---

**Pattern 3 — {headline}**

What it is:

Evidence:
- Call {N}:
- Call {N}:
- Call {N}:

Implication:

---

### Top 3 contradictions (where calls disagreed)

**Contradiction 1 — {topic}**

What one camp said:
- Call {N} ({name}):

What the other camp said:
- Call {N} ({name}):

What this likely means: 1-2 sentences. Often contradictions reveal hidden segmentation (e.g., "PMs at <Series B" vs "PMs at >Series C") rather than truth/falsity.

---

**Contradiction 2 — {topic}**

Camp A:
Camp B:
Likely meaning:

---

**Contradiction 3 — {topic}**

Camp A:
Camp B:
Likely meaning:

---

### The one surprise

Something you couldn't have written down before the calls. Often the highest-leverage finding because it's something the team didn't already believe.

> "{verbatim quote that captures it}"

What it changes:

---

## Riskiest-assumption verdict

The bet was: *PMs do error analysis solo, and the output is trusted enough by engineering to drive code changes.*

**Drove-eng-change average:** {X.X} / 5
**Solo-work average:** {X.X} / 5

Verdict: ☐ thesis intact ☐ thesis broken ☐ thesis partially intact (specify segment)

If partially intact: {one sentence on which segment it holds for}

---

## Decisions

Apply the rubric averages to the gates in `scoring-sheet.md`. Re-state the decisions taken here so the synthesis is self-contained.

1. {decision} — {1 sentence rationale}
2. {decision} — {1 sentence rationale}
3. {decision} — {1 sentence rationale}

---

## What changes for GEDD next

Concrete, scoped, owned. Three items max. Each maps to an existing or new doc in `docs/`.

- **Build:** {feature, doc reference, owner, ETA}
- **Stop building:** {feature, why}
- **Validate next:** {next assumption to test, how, by when}

---

## Quotes worth saving

3-5 verbatim quotes that compress an entire pattern into one sentence. These are the slides for an exec readout, the screenshots for a future blog post, the gut-check when scope drifts.

> "{quote}" — Call {N}, {anonymized identifier like "Series C SaaS PM"}

> "{quote}" — Call {N}, {identifier}

> "{quote}" — Call {N}, {identifier}

---

## What I'd do differently next round

Honest reflection. The point is to get better at this, not to look good.

- Recruiting: {what to fix}
- Questions: {what to drop, what to add}
- Note-taking: {what got lost}
- Scoring: {where the rubric was ambiguous}

---

## Distribution

Where this doc goes after it's written:

- ☐ Shared with engineering lead
- ☐ Posted in {Slack channel / shared doc folder}
- ☐ Summary thread for the 5 interviewees (per consent script wrap-up)
- ☐ Linked from the next sprint plan or design doc

If this stays in your local copy of the repo, it didn't actually inform anyone's decisions.
