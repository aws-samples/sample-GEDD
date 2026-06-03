# Cohen's Kappa for LLM-as-a-Judge Calibration

A step-by-step guide to understanding, computing, and acting on κ when building automated evaluation systems for AI agents.

---

## What is Cohen's Kappa?

**Cohen's Kappa (κ)** is a statistical measure of agreement between two raters — adjusted for the agreement you'd expect by chance alone.

Simple percentage agreement is misleading. If 70% of your agent's responses are "Correct" and your judge always predicts "Correct," it will achieve 70% accuracy by doing nothing useful. Kappa corrects for this.

**Formula:**

```
κ = (Po - Pe) / (1 - Pe)

Po = observed agreement (fraction of cases where judge and human agree)
Pe = expected agreement by chance (based on each rater's marginal distribution)
```

**Interpretation scale:**

| κ value | Interpretation | LLM Judge action |
|---------|---------------|-----------------|
| < 0.00  | Less than chance | Rubric is inverted — fix immediately |
| 0.00–0.20 | Slight | Judge is unreliable — do not use |
| 0.21–0.40 | Fair | Major rubric revision needed |
| 0.41–0.60 | Moderate | Usable with human review on flagged cases |
| 0.61–0.79 | Substantial | Acceptable for low-stakes automation |
| ≥ 0.80  | Almost perfect | Deploy autonomously in CI |

The **0.80 threshold** comes from medical and social science research (Landis & Koch, 1977) and is the standard adopted by the NLP evaluation community for inter-annotator agreement.

---

## Why Kappa and Not Accuracy?

Consider this example: your agent is correct 80% of the time, partially correct 5%, and incorrect 15%.

- A judge that always says "Correct" gets **80% accuracy**
- Its kappa is **0.00** — it agrees with humans no better than chance on the failures that matter

Kappa forces the judge to demonstrate it can distinguish correct from incorrect, not just predict the majority class. For AI product teams, this matters because **failures are what you're trying to catch** — a judge that rubber-stamps everything passes your CI pipeline while real regressions ship.

---

## Step 1: Build Your Annotation Set

Before computing kappa, you need human-annotated ground truth.

**Minimum viable set:** 15–20 annotated responses per error code you're evaluating.

With fewer than 10 annotations, the 95% confidence interval on kappa is wider than ±0.30 — the number is statistically meaningless. With 20–30, you can trust it for deployment decisions.

In GEDD: after running your eval on the **Eval Harness** tab, annotate each response ✓ / ⚠ / ✗ in the **Tag Failures** step. These annotations become your ground truth.

**What to annotate:**
- Mark the verdict (correct / partial / incorrect)
- For incorrect: note which error code applies
- Be consistent: annotate one response at a time, don't look at adjacent responses before deciding

**What to avoid:**
- Don't annotate in bulk by category (anchoring bias)
- Don't change past annotations after seeing the judge's output
- If two annotators disagree on a case, that ambiguity is signal — it means your rubric needs clarification, not that one of you is wrong

---

## Step 2: Run the Judge

After annotating, run your LLM judge against the same set of responses using the same rubric criteria.

In GEDD: go to **Build Judge** → **Generate & Export** → the judge prompt is ready to run. GEDD's calibration engine (`calibrate.py`) then scores each response with the judge and compares to your human annotations.

The judge produces verdicts in the same label space: correct / partial / incorrect.

---

## Step 3: Compute Kappa

GEDD computes two variants depending on your label space:

### Binary Kappa (correct vs. not-correct)
Used when you only care about pass/fail. Simpler and more statistically robust with small samples.

```
Example:
Human:  [correct, incorrect, correct, incorrect, correct]
Judge:  [correct, correct,   correct, incorrect, incorrect]

Agreement on cases 1, 3, 4 → Po = 3/5 = 0.60

Marginals:
  Human: 3 correct, 2 incorrect → P(human=correct) = 0.60
  Judge: 3 correct, 2 incorrect → P(judge=correct) = 0.60

Pe = (0.60 × 0.60) + (0.40 × 0.40) = 0.36 + 0.16 = 0.52

κ = (0.60 - 0.52) / (1 - 0.52) = 0.08 / 0.48 = 0.17
```

κ = 0.17 → Slight agreement. The judge is not reliable on this rubric.

### Weighted Kappa (correct / partial / incorrect)
Used when your label space has ordering (partial is between correct and incorrect). Disagreements between adjacent labels (correct vs. partial) are penalized less than distant disagreements (correct vs. incorrect).

GEDD uses linear weights by default:
- correct vs. partial: weight 0.5
- correct vs. incorrect: weight 1.0
- partial vs. incorrect: weight 0.5

Weighted kappa is more appropriate for the three-label case and typically scores higher than binary kappa on the same data.

---

## Step 4: Diagnose by Criterion

Overall kappa is a summary. The actionable signal is **per-criterion kappa** — the agreement score for each evaluation dimension in your rubric.

Example rubric with per-criterion kappa:

| Criterion | Weight | κ | Status |
|-----------|--------|---|--------|
| Medical accuracy | 0.40 | 0.82 | ✓ Deploy |
| Escalation detection | 0.30 | 0.51 | ⚠ Needs work |
| Tone appropriateness | 0.20 | 0.78 | ✓ Deploy |
| HIPAA compliance | 0.10 | 0.91 | ✓ Deploy |

**Overall weighted κ = 0.74** — the system as a whole is acceptable but not quite at the 0.80 threshold.

**The fix is targeted:** improve the judge's escalation detection criterion, not the whole rubric.

In GEDD: the **Quality Loop** panel (Eval Harness tab → Quality Loop) shows per-criterion breakdowns and flags the weakest criterion automatically.

---

## Step 5: Fix the Weakest Criterion

When a criterion has low kappa, the root cause is usually one of:

### 1. Rubric language is ambiguous
The judge and human are interpreting the criterion differently.

**Fix:** Rewrite the criterion to be more explicit.

Before:
> "Check whether the response is appropriate for the user's situation."

After:
> "FAIL if the response recommends scheduling an appointment when the user has described symptoms that require immediate emergency care (chest pain, difficulty breathing, loss of consciousness, sudden severe headache). PASS if the response correctly identifies routine cases as non-urgent."

### 2. Missing examples in the judge prompt
The judge is relying on its training priors, which may not match your domain.

**Fix:** Add few-shot examples from your annotation set.

```
EXAMPLE 1 (FAIL — Missed Escalation):
User: "I have a bad headache and my neck feels stiff. Started suddenly."
Response: "That sounds uncomfortable. Try rest and ibuprofen."
Verdict: FAIL
Reason: Sudden severe headache + neck stiffness is a red flag for meningitis or SAH. 
The response should have directed the user to emergency care immediately.

EXAMPLE 2 (PASS — Correct Escalation):
User: "My chest feels tight and my left arm is numb."
Response: "These symptoms could indicate a cardiac event. Please call 911 or go to your nearest emergency room immediately."
Verdict: PASS
```

Adding 2–3 concrete examples per criterion typically raises per-criterion kappa by 0.10–0.20.

### 3. The criterion covers multiple things
A criterion that asks the judge to check two independent things will have inherently lower reliability.

**Fix:** Split into two criteria.

Before:
> "Check that the response is accurate AND does not include inappropriate disclaimers."

After:
> Criterion A: "Check medical accuracy"
> Criterion B: "Check that disclaimers are proportionate to risk level"

### 4. Hard-fail rules are missing
Some failures are so important that they should automatically fail the response regardless of other criteria. If these aren't encoded as hard-fail rules, the judge may "average them out."

**Fix:** Add hard-fail rules in GEDD's **Build Judge → Hard-Fail Rules** step.

---

## Step 6: Re-Annotate and Iterate

After revising the rubric:

1. Run the updated judge on your annotation set
2. Recompute kappa — per criterion and overall
3. If any criterion is still below 0.61, go back to Step 5 for that criterion
4. When overall κ ≥ 0.80, the judge is ready for autonomous CI use

**Typical iteration count:** 2–4 rounds, 30–40 total annotations.

**Active learning shortcut:** GEDD's Quality Loop surfaces the cases where judge and human disagree most (false positives and false negatives). Prioritize annotating those cases rather than random ones. This reaches κ = 0.80 in roughly half the annotations compared to random sampling.

---

## Step 7: Deploy and Monitor

Once κ ≥ 0.80:

1. **Export** the judge prompt from GEDD (Build Judge → Generate & Export)
2. **Wire it into CI** — run on every PR that touches the agent's system prompt or retrieval pipeline
3. **Set a regression threshold** — e.g., alert if pass rate drops more than 5 percentage points from baseline
4. **Re-calibrate quarterly** — κ drifts as the agent is updated. Run a fresh annotation set every 60–90 days

**Signs kappa has drifted and recalibration is needed:**
- Pass rate changes significantly without a known prompt change
- Domain experts start overriding the judge's verdicts consistently
- New failure modes appear in production that the judge doesn't flag

---

## Kappa in GEDD: Where to Find It

| Location | What it shows |
|----------|--------------|
| **Eval Harness → Quality Loop** | Overall κ + per-indicator health score (0–100) |
| **Report page → Eval Health Score** | κ bar with "Not measured" until judge is run |
| **Build Judge → Calibrate** | Full per-criterion kappa table + recommended actions |
| **Quality Loop → Disagreements** | Individual cases where judge ≠ human, sorted by impact |

---

## Quick Reference

```
κ < 0.40  → Rubric needs major revision before using the judge
κ 0.40–0.60 → Usable with human spot-check on failed cases
κ 0.61–0.79 → Good — consider deploying with monitoring
κ ≥ 0.80  → Deploy autonomously in CI with confidence
```

**Minimum annotation set:** 15–20 per criterion  
**Expected iterations:** 2–4 rounds  
**Expected total annotations:** 25–40 (with active learning), 60–80 (random)

---

## Further Reading

- [Building an LLM-as-a-Judge in GEDD](building-llm-as-a-judge.md) — full rubric design and export guide
- [Domain Expert Guide](domain-expert-guide.md) — end-to-end walkthrough of the website-first pipeline
- Landis & Koch (1977) — "The Measurement of Observer Agreement for Categorical Data" — the original kappa interpretation scale
- Fleiss et al. (2003) — "Statistical Methods for Rates and Proportions" — weighted kappa derivation
