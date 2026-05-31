# Why I'm Replacing Our Eval Infrastructure With a PM Conversation

*I've spent 8 years building ML systems. The best evaluation pipeline I've ever shipped was written by a product manager who doesn't know what a tensor is.*

---

## The Problem I Kept Solving Wrong

Every agent team I've led hits the same wall around month 3. We ship the agent. It works. Then it doesn't — in ways our eval suite never anticipated.

The pattern is always the same:

1. Engineer writes eval cases based on what they *think* will fail
2. Agent passes all tests
3. PM finds a production failure the tests didn't cover
4. Engineer adds a test case reactively
5. Repeat forever

The eval suite grows, but it's always one step behind. It's reactive, not systematic. And the person who actually knows what "correct" means — the PM, the domain expert, the compliance officer — is locked out of the process because our tools require Python, JSON schemas, and ML vocabulary.

I've tried fixing this with better tooling (LangSmith, Braintrust, custom harnesses). They all have the same assumption: the engineer defines what to measure. That assumption is wrong.

---

## What Changed My Mind

A colleague pointed me to GEDD. I was skeptical — another eval tool, another framework to learn. But the architecture is different in a way that matters:

**The domain expert produces the eval artifacts. The ML engineer consumes them.**

Not the other way around. Not "engineer builds rubric, PM reviews." The PM builds the rubric by having a conversation, and the engineer wires it into CI.

I tested it with our pharmacy agent (RxBot). Here's what happened.

---

## The Test: RxBot (Pharmacy Domain)

### What I gave the PM

I handed our pharmacy PM the Claude Code skill and said: "Run `/gedd`. Define RxBot. Generate test cases. Mark the responses. I'll take it from there."

She spent 45 minutes. No Python. No JSON. Just a conversation.

### What she produced

A `session.json` containing:
- **Agent definition:** 5 capabilities, 2 user personas, pharmacy domain
- **System prompt:** 1697 chars with hard rules ("never prescribe," "escalate for adverse effects")
- **12 golden queries** across 4 categories (happy path, edge case, adversarial, ambiguous)
- **12 annotations** with 2 error codes

The error codes are what sold me:

| Error Code | What She Found | Why I Would Have Missed It |
|-----------|---------------|---------------------------|
| `dosage_unit_confusion` | Agent said "mg" when context suggests "mcg" | I'd see a well-formatted answer. She sees a 1000x dosage error that could kill someone. |
| `interaction_underwarning` | Mentioned aspirin+metoprolol interaction but didn't flag kidney risk | I'd see "interaction mentioned = correct." She knows the kidney risk is the critical part. |

These aren't generic labels. They're domain-specific failure modes that encode institutional knowledge. And they came from a 45-minute conversation, not a 3-week rubric design sprint.

---

## What I Did With It (The Engineering Part)

### Step 1: Inspect the artifacts

```bash
grounded-evals status --session session.json --results eval_results.json
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GEDD Session Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Agent      : RxBot
  Step       : 3 / 6  (Golden Queries)

  ── Golden Queries (12 total) ──
  happy_path         ███░░   3  ✓ saturated
  edge_case          ███░░   3  ✓ saturated
  adversarial        ███░░   3  ✓ saturated
  ambiguous          ███░░   3  ✓ saturated

  ── Annotations (12 total) ──
    ✓ correct    10
    ⚠ partial    1
    ✗ incorrect  1

  Error codes:
    dosage_unit_confusion    ×1
    interaction_underwarning ×1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Clean. 12 queries, 4 categories saturated, 2 error codes. Enough to build a judge.

### Step 2: Generate the judge

```bash
grounded-evals judge --session session.json --results eval_results.json --output judge_prompt.md
```

The output is a G-Eval chain-of-thought rubric:

```markdown
### Quality (weight: 1.0)
Observed issues: dosage_unit_confusion; interaction_underwarning

Step-by-step questions:
  - Does the response make factual claims about dosages or units?
  - Are drug interactions fully characterized (not just mentioned)?
  - Would a pharmacist approve this response without corrections?

Score 1-5.
```

This is better than anything I would have written. It's grounded in actual failures, not hypothetical ones.

### Step 3: Connect to SageMaker MLflow

```bash
grounded-evals mlflow \
  --session session.json \
  --results eval_results.json \
  --tracking-uri arn:aws:sagemaker:us-east-1:384790854332:mlflow-tracking-server/gedd-evals
```

```
  Tracking: SageMaker @ arn:aws:sagemaker:us-east-1:384790854332:mlflow-tracking-ser...
  Experiment: gedd-rxbot
  Dataset: 12 test cases
  Judge: gedd_quality (patterns: dosage_unit_confusion, interaction_underwarning)
  Judge: gedd_correctness
  Total: 2 judges

  Run ID: 0eb85644d5d043c6b096953997b1b2aa

  ✓ GEDD → MLflow pipeline ready
```

One command. The PM's work is now in our MLflow tracking server as:
- A registered experiment with metadata
- Custom judges (via `make_judge()`) that encode her domain knowledge
- An eval dataset with expected behaviors
- Human annotation baselines for judge calibration

### Step 4: Wire into CI

```yaml
# .github/workflows/rxbot-eval.yml
name: RxBot Evaluation
on:
  push:
    paths: ['agents/rxbot/**']

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install grounded-evals sagemaker-mlflow
      - run: |
          grounded-evals mlflow \
            --session session.json \
            --tracking-uri ${{ secrets.SAGEMAKER_MLFLOW_ARN }} \
            --run-eval
```

Every time someone changes RxBot's prompt, tools, or model — the eval pipeline runs. If the `dosage_unit_confusion` pattern reappears, the build fails.

### Step 5: Calibrate (ongoing)

I held out 3 of the PM's annotations and ran the judge against them. Agreement was high (κ = 0.82). If it drifts below 0.80, I'll sharpen the criteria — but the PM's annotations are the ground truth I calibrate against.

---

## The Architecture That Convinced Me

```
PM (45 min conversation)
  └── session.json
        ├── golden_prompts[12]     → eval dataset
        ├── annotations[12]        → human baseline
        ├── error_codes[2]         → judge criteria
        └── system_prompt          → agent under test
              │
              │  grounded-evals mlflow --tracking-uri ARN
              ▼
SageMaker MLflow
  ├── Experiment: gedd-rxbot
  ├── Judges: gedd_quality, gedd_correctness
  ├── Metrics: human_tsr=0.83, error_codes=2
  └── Artifacts: session.json, eval_dataset.json
              │
              │  CI/CD (on every push)
              ▼
Bedrock AgentCore
  └── RxBot (live, gated by eval pipeline)
```

What I like about this:

1. **The PM never touches MLflow.** She works in Claude Code. I work in the terminal.
2. **The handoff is one file.** No meetings, no Jira tickets, no "can you export that spreadsheet as JSON."
3. **The judges are grounded in evidence.** Not "evaluate helpfulness 1-5" — evaluate whether dosage units are correct and interactions are fully characterized.
4. **It's idempotent.** PM finds a new failure next month? She runs `/gedd`, says "add more," names the error. I re-run `grounded-evals mlflow`. The pipeline grows.
5. **It's all AWS-native.** Bedrock for inference, AgentCore for hosting, SageMaker MLflow for tracking. IAM for auth. No external vendors.

---

## What This Replaces

| Before | After |
|--------|-------|
| Engineer writes eval cases from imagination | PM writes eval cases from domain knowledge |
| Generic rubric ("helpfulness 1-5") | Domain-specific rubric ("dosage_unit_confusion") |
| Reactive test additions after production failures | Systematic Open Coding methodology upfront |
| Spreadsheet handoff between PM and engineering | One `session.json` file |
| Custom eval harness (500 lines, fragile) | `grounded-evals mlflow --run-eval` (one command) |
| Manual judge calibration | Cohen's Kappa against PM annotations |
| Eval suite is static | Flywheel: production failures → new queries → updated judges |

---

## The Hard Truth About LLM-as-Judge

The MLflow article on agent evaluations says:

> "LLM judges are useful but require continuous calibration. Maintain a human-labeled validation set and target roughly 75% judge-human agreement."

GEDD gives you that human-labeled set for free. The PM's annotations ARE the calibration data. You don't need a separate labeling sprint — the eval creation process produces the labels.

And because the error codes are specific (`dosage_unit_confusion`, not `incorrect`), the judges are specific too. A specific judge is easier to calibrate than a vague one.

---

## My Recommendation

If you're a principal/staff engineer evaluating this for your org:

1. **Start with one agent, one PM.** Don't try to roll it out to 5 teams simultaneously. One PM, one session, one pipeline. Prove it works.

2. **The PM's time is the bottleneck, not yours.** Your part (Step 6) takes 5 minutes. The PM's part (Steps 1-5) takes 45-90 minutes. Protect that time.

3. **Don't over-engineer the judges.** Two error codes → two judges. That's enough to start. You can add more as the PM discovers more failure modes.

4. **The deploy-first pattern matters.** Deploy at Step 3. Test against the real endpoint. I've seen too many eval suites that pass locally and fail in production because of subtle differences.

5. **The flywheel is the real value.** The first run produces a baseline. The second run (after a prompt change) catches regressions. The third run (after a production failure) expands coverage. By month 3, you have an eval suite that encodes every failure the agent has ever had.

---

## The Line That Stuck With Me

From the GEDD README:

> *The eval pipeline is the product. The agent is just the thing it produces.*

After 8 years of building ML systems, I think this is right. Models change. Prompts change. Tools change. But the eval pipeline — the golden queries, the error codes, the judges, the regression gates — that's the institutional knowledge that survives every rewrite.

And the best person to build it isn't the engineer. It's the person who knows what "correct" means.

---

*[GEDD](https://github.com/aws-samples/sample-GEDD) is open source (MIT-0). The full pipeline guide is at `docs/pipeline-guide.md`.*
