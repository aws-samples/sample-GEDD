# Building the Best LLM-as-a-Judge with GEDD
### A Step-by-Step Guide for Domain Experts

---

## What You're Building — and Why It's Different

Most LLM eval tools ask you to write criteria from scratch. GEDD does the opposite: it extracts evaluation criteria **from evidence you already have** — real failure modes observed while testing your agent, organized into a causal map through qualitative research methodology (Grounded Theory). The judge you build at the end is grounded in data, not gut feel.

The workflow is:

```
Real agent failures  →  Open Coding  →  Axial Coding  →  Judge Builder  →  Automated eval
(Tag Failures tab)     (error codes)   (Paradigm Model)  (Build Judge)    (Eval tab)
```

Each step feeds the next. By the time you click "Generate Judge Prompt," the LLM already knows your specific failure modes, why they happen, how they manifest, and what the user impact is. That context makes the difference between a generic rubric and a precise instrument.

---

## Part 1: Foundations — Before You Touch the Judge Builder

The quality of your judge is determined almost entirely by the quality of what you feed it. Invest here first.

### Step 1.1 — Annotate with Precision in the Tag Failures Tab

When you mark a response in the **Tag** tab, the annotations become the raw material for everything downstream. Three practices separate mediocre from excellent annotation:

**Use severity honestly.** The four levels have specific meanings in GEDD's calibration math:
- **Catastrophic** — patient harm, legal liability, safety violation. Hard-fail candidate.
- **Critical** — response is wrong in a way the user will act on. High weight in the rubric.
- **Functional** — response fails but the user can recover. Medium weight.
- **Cosmetic** — wrong tone, minor omission, no harm done. Low weight.

Overusing "critical" breaks calibration. If everything is critical, nothing is.

**Write memos for every incorrect annotation.** The memo field feeds directly into constitutional principles and few-shot exemplars. A memo like *"Agent confirmed warfarin + ibuprofen was safe without checking DDI database — user could have internal bleeding"* is worth 10 generic annotations. Be specific about the mechanism of failure, not just the label.

**Assign confidence levels.** Mark "high" only when you are certain a reasonable domain expert would agree. Low-confidence annotations introduce noise into your calibration set. It is better to have 8 high-confidence annotations than 20 uncertain ones.

**Aim for minimum coverage before building the judge:**
- At least 2 annotated examples per error code in your codebook
- At least 1 each of correct, partial, and incorrect verdicts in the set
- At least 3 examples for any error code you plan to make a hard-fail rule

### Step 1.2 — Build a Clean Codebook

In the **Tag** tab, your codebook is your vocabulary of failure. A good codebook has:

- **Specific names**, not categories. "Missed Drug-Drug Interaction" is better than "Accuracy Failure." The name should be readable in a judge prompt.
- **A one-sentence definition** that a colleague with no context could apply correctly. Test it: can you apply it consistently yourself?
- **No overlapping codes.** If two codes fire on the same response most of the time, merge them. Overlap creates ambiguity in the judge and dilutes per-criterion kappa.
- **6–12 codes.** Below 4 is too coarse. Above 15 creates a judge with too many checks to be reliable. If you have 15+, use the **axial coding** step to group them under fewer phenomena.

### Step 1.3 — Complete the Paradigm Model (Root Causes Tab)

The Paradigm Model is what separates GEDD judges from generic rubric judges. It tells the judge not just *what* to look for but *why* failures happen and *how* they manifest. The rubric generator in `rubric.py` embeds this context directly into each criterion.

Fill in all six slots. The ones most people skip — and most hurt the judge:

**Causal Conditions (Triggered By):** What in the system prompt or agent design creates the conditions for this failure? Example: *"System prompt lists escalation triggers as prose instructions rather than structured if-then rules."* This tells the judge what architectural context to reason about.

**Intervening Conditions (Gets Worse If):** What makes the failure more likely in practice? Example: *"User frames urgency themselves — agent defers to user framing."* Helps the judge understand why some queries at the same risk level fail and others don't.

**Consequences (User Impact):** The stakes. *"Delayed emergency care; medication harm; regulatory exposure."* Higher-consequence phenomena should get higher weight in the rubric — and the judge needs to know this.

Use **Generate Pattern Analysis (AI)** to fill the model automatically, then edit for accuracy. The AI-generated model is a starting point, not a final answer.

---

## Part 2: Building the Judge — Step by Step

### Step 2.1 — Map Failure Codes to Evaluation Dimensions

In the **Build Judge** wizard, Step 2 asks you to assign your error codes to standard evaluation dimensions. This is not just taxonomy — it determines how GEDD's rubric generator writes scoring criteria.

The eight standard dimensions and when to select them:

| Dimension | Select when your codebook has codes about… |
|---|---|
| **Accuracy** | Hallucinations, wrong facts, stale data, fabricated citations |
| **Safety** | Harmful instructions, refusal failures, dangerous information |
| **Scope Adherence** | Out-of-scope responses, agent acting outside its intended role |
| **Instruction Following** | System prompt violations, ignored constraints, unauthorized escalation |
| **Completeness** | Missing answers, unanswered sub-questions, partial responses |
| **Tone / Style** | Wrong register, inappropriate empathy level, condescension |
| **Conciseness** | Padding, unnecessary caveats, excessive hedging |
| **Bias / Fairness** | Demographic assumptions, inequitable treatment |

**Rules for mapping:**

1. Every error code should map to exactly one primary dimension. If a code could go to two dimensions, pick the one where the user harm originates (not where it surfaces).
2. Don't select a dimension if you have zero error codes for it. An empty dimension produces noise in the rubric.
3. Safety and Accuracy almost always belong. If your agent can be wrong or harmful, include both.

Use **Auto-Map with AI** after you have a clean codebook. It will suggest assignments based on code definitions and paradigm model context. Review every suggestion — it's right ~85% of the time and occasionally maps conceptual codes to the wrong dimension.

### Step 2.2 — Define the Rubric: Score 1 vs Score 5

Step 3 asks for concrete descriptions of what a failing (1/5) and excellent (5/5) response looks like per dimension. This is the highest-leverage prompt engineering you will do in the entire process.

**What makes a good rubric anchor:**

A bad anchor: *"Score 1: The response has accuracy problems."*
A good anchor: *"Score 1: The response states a fact the user is likely to act on that is factually wrong — wrong dosage, wrong jurisdiction, wrong date — or fabricates a source."*

Rules for writing anchors:
- Be **specific to your domain**. "Incorrect fact" is generic. "Wrong medication interaction status" is specific and directly applies your codebook.
- **Include observable signals** the judge can detect without external knowledge. "States a drug is safe when the interaction is listed in the codebook" gives the judge something to check.
- For Score 5: describe absence of failure, not presence of excellence. "No evidence of Missed Escalation, Contraindication Miss, or Drug Interaction Error" is more reliable than "perfectly comprehensive medical response."
- **Levels 2–4 don't need explicit text** (GEDD generates them from the rubric template). But if you find the judge scoring 3 too often in calibration, add an explicit 3 anchor to break the middle bias.

**Setting weights:**

| Weight | When to use |
|---|---|
| 3 (Critical) | Safety, Accuracy in high-stakes domains — a 1 here should fail the response regardless of other scores |
| 2 (Important) | Instruction Following, Scope Adherence, Completeness |
| 1 (Standard) | Tone, Conciseness, Bias when not central to the use case |

Use **Auto-Fill with AI** to generate initial anchors, then edit. The AI-generated anchors for domain-specific criteria (clinical, legal, financial) tend to be generic. Replace generic medical language with your specific observed failure examples from the codebook.

### Step 2.3 — Set Hard-Fail Rules

Hard-fail rules are the most important part of a production judge for high-stakes domains. They are evaluated before the rubric — if any hard-fail condition is met, the response gets an automatic FAIL regardless of its scores on Tone or Completeness.

**When to create a hard-fail rule:**

- Any error code rated "catastrophic" in your codebook
- Any failure with a direct safety, legal, or regulatory consequence
- Any behavior the agent should *never* exhibit — regardless of context

**Writing a hard-fail condition that a judge can reliably detect:**

Bad: *"Response is harmful."* (too abstract — the judge will under-trigger)
Good: *"Response provides specific medication dosage or treatment recommendation to a non-clinician without a required disclaimer and recommendation to consult a physician."* (observable, specific)

Bad: *"Response mentions competitor."* (might miss paraphrase)
Good: *"Response names a competing product by name or URL in a way that could direct the user away from our service."*

**GEDD's hard-fail → prompt structure:** Hard-fail conditions appear at the top of the generated judge prompt, before any rubric scoring. The judge evaluates them first, in sequence. A single VIOLATED result ends the evaluation with FAIL and the name of the triggered condition. This means your hard-fail descriptions must be written so the judge can answer a binary VIOLATED / CLEAR question — not assign a score.

Use the **Suggested Hard-Fails** button to see which of your error codes are high-severity candidates. Add one hard-fail per catastrophic/critical code. Aim for 3–7 total. More than 10 hard-fail rules degrades precision (the judge starts over-triggering on benign responses).

### Step 2.4 — Generate the Judge Prompt

Click **Generate Judge Prompt** in Step 5. GEDD synthesizes:
- Your rubric (dimensions, score anchors, weights)
- Hard-fail conditions
- Agent context (name, description, system prompt excerpt)
- Error codebook definitions

into a structured judge prompt using the G-EVAL chain-of-thought format by default: the judge answers sub-questions per criterion before assigning a score. This is the Liu et al. (2023) approach shown to significantly improve inter-rater reliability vs direct scoring.

**Read the generated prompt before using it.** Check:
- Does the role description correctly describe your agent's purpose?
- Are the hard-fail conditions precise enough that a false trigger is unlikely?
- Do the rubric anchors use your domain vocabulary?
- Is the output format JSON with per-criterion scores, a weighted total, and a pass/fail verdict?

Edit directly in the textarea. The most common edits:
- Make the agent description more specific ("clinical triage assistant for emergency nurses in the US" not just "medical AI")
- Replace generic Score 1 descriptions with your specific observed failure examples
- Add "Unless the system prompt explicitly permits this" to scope-related hard-fails

---

## Part 3: Calibration — Before You Deploy

### Step 3.1 — Run the Judge on Annotated Examples First

Before using the judge on new responses, test it against your annotated ground truth. In Step 5's Calibration section, GEDD shows your human-annotated examples. For each one, run the generated judge prompt and compare its verdict to your label.

**Target metrics (from `calibrate.py`):**

| Weighted Kappa (κ) | Interpretation | Action |
|---|---|---|
| κ ≥ 0.80 | Almost perfect agreement | Deploy with confidence |
| 0.61–0.79 | Substantial | Minor prompt tuning; add 1–2 examples |
| 0.41–0.60 | Moderate | Revise criterion definitions; inject few-shot examples |
| 0.21–0.40 | Fair | Use Constitutional or Few-Shot mode |
| < 0.21 | Slight / Poor | Redesign rubric; criteria are ambiguous or overlapping |

**Minimum calibration set:** 10–15 annotated examples before trusting kappa. With N < 10, the 95% confidence interval on kappa is wider than ±0.3 — meaningless for deployment decisions. With N = 20–30, you can trust the number.

### Step 3.2 — Use the Right Judge Mode for Your Situation

GEDD implements three judge modes (in `judge_builder/prompt_gen.py`). Use the right one:

**Standard (zero-shot rubric):** Good baseline. Use when you have a clean rubric, ≥ 6 annotated examples, and kappa ≥ 0.61 before deployment. Fast and cheap to run.

**G-EVAL Chain-of-Thought:** Best for complex multi-aspect responses where the agent can fail in multiple ways simultaneously. Forces the judge to answer sub-questions per criterion before scoring. Slower (more tokens), but substantially more reliable — especially on criteria like Completeness and Instruction Following where a quick read misses violations. **This is the default mode in GEDD's generated prompt.**

**Few-Shot / Prometheus-style:** Best when you have ≥ 3 annotated examples per error code. Injects your best annotated FAIL and PASS examples directly into the judge prompt as demonstrations. Reduces the judge's reliance on its training priors and grounds it in your specific domain. Critical for niche domains where the LLM's prior knowledge is unreliable (specialty medicine, financial regulation, jurisdiction-specific law). Use when kappa in Standard mode is 0.41–0.60 and adding examples brings it above 0.61.

**Constitutional Checklist:** Best for safety-critical agents where you need per-principle verdicts, not a composite score. Each error code becomes an independent check. Produces the most auditable output — you can see exactly which principle was violated and why. Slower and more expensive, but the trace is invaluable for debugging.

### Step 3.3 — Debug Per-Criterion Disagreements

When calibration kappa is below target, `calibrate.py` identifies the **weakest criterion** — the evaluation dimension where judge and human disagree most. Fix that one first.

**Common causes and fixes:**

*Judge consistently scores too high (false PASS):*
- Your Score 1 anchor is too specific — the judge doesn't recognize variants of the failure
- Fix: add an explicit "Or any response that..." clause covering the failure variants you've observed

*Judge consistently scores too low (false FAIL):*
- Your Score 5 anchor doesn't cover the range of good responses
- Fix: add domain-specific examples of correct responses to the Score 5 anchor

*High variance (sometimes right, sometimes wrong):*
- The criterion definition is ambiguous — judge is guessing
- Fix: rewrite the dimension description to be more specific; add a few-shot example

*Particular error code never detected:*
- The error code definition is too abstract in the judge prompt
- Fix: add a "Real example of this violation" (constitutional format) or inject a few-shot FAIL example

### Step 3.4 — Active Learning: Which Responses to Annotate Next

Once you have an initial judge deployed, GEDD's active learning module (`active_learning.py`) tells you which unannotated responses are most worth a human review.

The two signals:

**Margin sampling** (default): responses where the judge's overall score is closest to the pass/fail threshold (3.5/5). These are the cases where the judge is genuinely uncertain — a human verdict here provides the most calibration information per annotation hour.

**Coverage gaps**: error codes with fewer than 2 annotated examples. Each gap means the judge has no concrete reference for that failure mode. Adding even one clean positive example per gap typically raises per-criterion kappa by 0.1–0.2.

**The active learning loop:**
1. Tag initial batch (10–20 responses) → build first judge → calibrate
2. Get active learning recommendations → annotate those 5 responses
3. Rebuild judge with new exemplars → re-calibrate
4. Repeat until kappa plateau (typically 3–4 rounds, 30–40 total annotations)

This is dramatically more efficient than random annotation. Random annotation to reach κ = 0.80 typically requires 60–80 examples. Active learning reaches the same threshold with 25–35.

---

## Part 4: Common Failure Modes and How to Avoid Them

### Position Bias
The LLM judge scores responses that appear first in a comparison higher, regardless of quality. **Mitigation:** GEDD's generated prompt doesn't do pairwise comparison — it evaluates one response at a time against the rubric. Single-response evaluation eliminates position bias.

### Verbosity Bias
Longer responses score higher even when the extra length is padding. **Mitigation:** Include a Conciseness dimension with a Score 1 anchor that explicitly penalizes padding. If your agent tends toward verbosity, weight it 2.

### Self-Preference / Same-Model Bias
Using the same model as your agent to judge it produces inflated scores. **Mitigation:** Use a different judge model than your agent. If your agent is Claude Haiku, judge with Claude Sonnet. If your agent is GPT-4o, judge with Claude.

### Middle Score Inflation
Judges default to 3/5 when uncertain. This inflates pass rates. **Mitigation:** Write explicit anchors for 3/5 that make it unambiguous when 3 is and isn't appropriate. Alternatively, use a 3-point scale (1, 3, 5) if binary pass/fail suits your use case — it forces the judge off the fence.

### Sycophancy in the Judge
The judge agrees with the response's own confidence even when it's wrong. **Mitigation:** G-EVAL sub-questions force the judge to check specific facts before assigning a score, breaking the confidence-following pattern. Include explicit questions like "Can any specific fact in this response be verified?" in your criteria.

### Criterion Overload
More than 6 active dimensions degrades consistency. The judge tries to apply all criteria simultaneously and anchoring effects cause errors. **Mitigation:** Use the Paradigm Model to identify 3–4 core phenomena and weight those highest. Demote less-critical dimensions to a secondary pass-only check.

---

## Part 5: Production Checklist

Before deploying your judge to run automatically on new responses:

- [ ] **Codebook:** 6–12 codes, each with a specific 1-sentence definition. No overlapping codes.
- [ ] **Annotations:** ≥ 2 examples per error code. ≥ 10 total. Severity ratings applied honestly.
- [ ] **Paradigm Model:** All 6 slots filled, especially Causal Conditions and Consequences.
- [ ] **Dimensions:** 3–6 selected. Every selected dimension has ≥ 1 error code assigned.
- [ ] **Rubric anchors:** Score 1 and Score 5 are domain-specific and observable. Not generic.
- [ ] **Hard-fail rules:** 3–7 rules. Each is a binary VIOLATED/CLEAR question, not a score. Catastrophic codes have a rule.
- [ ] **Calibration:** Weighted kappa ≥ 0.61 on annotated set before deployment. Know your weakest criterion.
- [ ] **Judge mode:** G-EVAL for complex responses. Few-shot if you have ≥ 3 examples per code. Constitutional for safety-critical audit trails.
- [ ] **Model choice:** Judge model is different from agent model.
- [ ] **Output format:** JSON with per-criterion scores, hard-fail flag, weighted total (0–100), pass/fail verdict, and reasoning. The Eval tab can parse this automatically.

---

## Quick Reference: What Each GEDD Step Contributes to the Judge

| GEDD Tab | Output | Feeds Into |
|---|---|---|
| **1. Coach** | Agent spec, system prompt, golden queries | Agent context in judge prompt; queries as calibration inputs |
| **2. Eval** | Model responses to golden queries | Raw material for annotation and calibration |
| **3. Tag** | Error codes, severity, memos, confidence | Codebook → dimensions → rubric anchors; few-shot exemplars; constitutional principles |
| **4. Root Causes** | Paradigm Model (causal map) | Rubric criterion descriptions; hard-fail suggestions; constitutional trigger explanations |
| **5. Build Judge** | Rubric, hard-fails, judge prompt | Deployed as the automated judge in the Eval tab |
| **6. Report** | Calibration metrics, failure pattern analysis | Identifies which criteria to improve; drives active learning recommendations |

---

## The Single Highest-Leverage Action

If you do one thing after reading this guide: **write better memos when annotating failures.**

Every memo you write becomes either a few-shot FAIL example (showing the judge what this error looks like in your domain) or a constitutional principle discriminating example (showing the judge exactly where the agent crossed a line). A judge with 10 high-quality annotated examples with detailed memos will consistently outperform a judge with 50 annotations that say "wrong answer."

Specificity compounds. Every specific annotation improves the rubric, the few-shot examples, the constitutional principles, and the active learning signal simultaneously. That is the core insight behind GEDD's Grounded Theory approach: quality of observation beats quantity of labels.
