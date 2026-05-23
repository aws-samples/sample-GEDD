# PM interview kit — riskiest assumption test

**Goal:** in 5 calls × 30 min, decide whether GEDD's solo-PM thesis is intact, and answer 4 other product questions blocked on user evidence.

**The thesis under test:** PMs do error analysis solo, and the output is trusted enough by engineering to drive code changes. If <2 of 5 say their analysis directly drove an engineering change, the thesis is broken and GEDD pivots to collab-first.

---

## Files in this kit

Read top to bottom, in order. The order matters — `interview-script.md` defines the questions; everything else operationalizes them.

1. **`interview-script.md`** — the playbook. Recruiting profile, outreach DM, the 6 questions, what to listen for, decision criteria.
2. **`consent-intro.md`** — verbatim script for the first 3 minutes of every call. Recording consent, gift-card timing, anonymity, the "this isn't a pitch" framing.
3. **`notes-template.md`** — copy this once per call. Quotes column + observations column kept separate. Fill during/right after the call.
4. **`scoring-sheet.md`** — fill out **after all 5 calls**, in one sitting. Decision gates apply averages to the 5-dimension rubric.
5. **`synthesis-template.md`** — the 1-page write-up. Top 3 patterns, top 3 contradictions, 1 surprise, decisions taken. Distribute outside this folder.

---

## Workflow

```
recruit (week 1)  →  schedule (week 1-2)  →  5 calls (week 2-3)
                                                ↓
                                       notes-template.md × 5
                                                ↓
                                  read all 5 notes (no scoring)
                                                ↓
                                       scoring-sheet.md
                                                ↓
                                       synthesis-template.md
                                                ↓
                                  decision → next sprint plan
```

Total elapsed time: ~3 weeks. Total active hours: ~15. Cost: $375 in gift cards + your time.

---

## Hard rules (don't skip)

1. **Send the gift card same-day, every time.** Not after all 5 calls. Not "when I have time." Same day. Even if the call was bad.
2. **Don't pitch GEDD during the calls.** This is observation research, not a sales call. If they ask, defer to wrap-up.
3. **Don't score until all 5 calls are done.** Scoring early anchors you to the first interviewee.
4. **Don't paraphrase quotes into observations during the call.** Quotes go in the QUOTES column, your interpretation in the OBSERVATIONS column. Frozen as captured.
5. **Run all 5 before deciding.** Three calls is not enough; the patterns and contradictions only show with 5.

---

## What "done" looks like

- 5 filled `notes-{N}-{date}-{name}.md` files
- 1 completed `scoring-sheet.md` with all gates checked
- 1 written `synthesis-{date}.md` (using `synthesis-template.md`)
- A clear decision recorded somewhere outside this folder (sprint plan, design doc, exec update)
- Gift cards sent

If the synthesis doc is written but never read by anyone else, the research didn't change anyone's decisions. Distribute it.

---

## When to redo this

Re-run a 5-call cycle when:

- You ship a major flow change and want to know if the JTBD shifted
- You're about to invest >2 weeks in a new feature whose value depends on a user behavior you don't have evidence for
- The market changes (new competitor launches, new methodology gets traction)

Don't run it as a quarterly ritual. Run it when a decision is at stake.
