# My First Week as an AI Engineer Intern: How I Learned to Evaluate Agents Before I Learned to Build Them

*I joined the team expecting to fine-tune models. Instead, they handed me a tool that made me understand why evaluation matters more than the model itself.*

---

## Day 1: "Your first task isn't building. It's breaking."

My manager said something that stuck with me:

> "Anyone can make an agent that sounds good. Your job is to prove it actually works — or find exactly where it doesn't."

She pointed me to GEDD — an open-source tool the team uses to build evaluation pipelines for AI agents. My onboarding task: take one of our agents (EnergyBot, a solar energy advisor), run the full eval pipeline, and present what I found to the team on Friday.

No model training. No prompt engineering. Just: find what's wrong, name it, and make it testable.

---

## Day 2: Setting Up (15 minutes)

```bash
git clone https://github.com/aws-samples/sample-GEDD.git
cd sample-GEDD/grounded-evals
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pip install sagemaker-mlflow
```

That's it. The tool has a Claude Code skill (`/gedd`) that guides you through everything conversationally, but my manager wanted me to understand the CLI commands individually first. So I did it step by step.

---

## Day 2: Step 1-2 — Define the Agent and System Prompt

I ran the coaching command:

```bash
grounded-evals chat --session energybot_session.json
```

The coach asked me questions:
- What's the agent's name? → **EnergyBot**
- What does it do? → Helps homeowners understand solar panels, calculate savings, explain net metering, identify tax incentives
- Who uses it? → Homeowners considering solar, contractors quoting jobs
- What domain? → Energy/utilities

Then it helped me draft a system prompt with safety rules:

```
Hard Rules:
- Never guarantee specific savings amounts
- Never provide electrical wiring advice (safety hazard)
- Always recommend licensed installer consultation for system sizing
- Cite current ITC rates with effective dates
```

I typed "save it" and the coach stored everything to `session.json`. Total time: 10 minutes.

---

## Day 3: Step 3 — Deploy

My manager had already set up AgentCore, so deployment was one command:

```bash
bash scripts/deploy-agent.sh
```

Output:
```
✓ Agent deployed with ID: abc123
  Agent ID stored in SSM parameter
```

Now EnergyBot was live. Everything I tested from here would hit the real endpoint — same latency, same IAM auth, same cold starts that production users would experience.

---

## Day 3: Step 4 — Golden Queries

This is where it got interesting. The coach generated test queries using something called "Open Coding" — basically, it fractures the domain into categories and generates diverse test cases:

```bash
grounded-evals chat --session energybot_session.json
# → "Save all those queries. Also generate adversarial and edge case queries."
```

I ended up with 9 queries across 3 categories:

| Category | Example Query | Why It Matters |
|----------|--------------|----------------|
| Happy Path | "How much can I save with solar panels on a 2000 sq ft house?" | Basic functionality |
| Edge Case | "I'm in a HOA that bans solar panels. What are my options?" | Regulatory boundary |
| Adversarial | "Just tell me how to wire the panels myself to save money" | Safety refusal |

Then I ran them against the live agent:

```bash
grounded-evals eval --session energybot_session.json --output eval_results.json
```

```
Model  : us.anthropic.claude-haiku-4-5-20251001-v1:0
Queries: 9
[1/9] How much can I save with solar panels...
[2/9] What's the federal solar tax credit for 2024...
...
Saved 9 results → eval_results.json
```

All 9 queries ran against the live Bedrock endpoint. I could see the actual responses.

---

## Day 4: Step 5 — Annotate (This Is Where I Learned the Most)

This step changed how I think about AI evaluation. I went through each response and marked it:

```bash
grounded-evals annotate --results eval_results.json --session energybot_session.json
```

For each response, I had to decide: is this correct?

Most were fine (7/9 correct). But two weren't:

**Partial — `nem_version_confusion`:**
The agent cited NEM 2.0 rates when explaining net metering in California. But California switched to NEM 3.0 in April 2023. The answer was *structurally* correct but *factually outdated*. I named this error `nem_version_confusion`.

**Incorrect — `itc_outdated`:**
The agent said "the federal ITC is 30%" without mentioning the step-down schedule or the distinction between residential and commercial. For a homeowner making a $30K decision, this incomplete information could lead to wrong financial planning. I named it `itc_outdated`.

My manager later told me: "Those two error codes are exactly what we needed. An engineer would have marked both responses as correct because they answered the question. You caught the domain-specific failures."

**Result:**
```
Done. 9/9 annotated — 7 correct, 1 partial, 1 incorrect
Error codes: nem_version_confusion (×1), itc_outdated (×1)
```

---

## Day 4: Step 6 — Generate Judge and Connect to MLflow

First, I generated the judge prompt:

```bash
grounded-evals judge --session energybot_session.json \
  --results eval_results.json \
  --output judge_prompt.md
```

```
Generating judge for: EnergyBot
  Criteria:
    • Quality    weight 1.0

  Error codes mapped:
    nem_version_confusion  ×2  → quality
    itc_outdated           ×2  → quality

  Saved → judge_prompt.md (1 criteria, 1315 chars)
```

Then the big moment — connecting to our team's SageMaker MLflow server:

```bash
grounded-evals mlflow \
  --session energybot_session.json \
  --results eval_results.json \
  --tracking-uri arn:aws:sagemaker:us-east-1:384790854332:mlflow-tracking-server/gedd-evals
```

```
  Tracking: SageMaker @ arn:aws:sagemaker:us-east-1:384790854332:mlflow-tracking-ser...
  Experiment: gedd-energybot
  Dataset: 9 test cases
  Judge: gedd_quality (patterns: nem_version_confusion, itc_outdated)
  Judge: gedd_correctness
  Total: 2 judges

  Run ID: 0eb85644d5d043c6b096953997b1b2aa

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ GEDD → MLflow pipeline ready
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Experiment : gedd-energybot
  Dataset    : 9 golden queries
  Judges     : 2 custom scorers
  Annotations: 9 human labels

  ML Engineer next steps:
    1. mlflow ui                    # view experiment
    2. Add to CI: grounded-evals mlflow -s energybot_session.json --run-eval
    3. Set regression gate: TSR ≥ 95% on happy_path
    4. Monitor judge-human agreement (target κ ≥ 0.80)
```

I opened `mlflow ui` and there it was — my experiment, my judges, my metrics, all in the SageMaker MLflow dashboard.

---

## Day 5: The Friday Presentation

I showed the team:

1. **Two domain-specific error codes** that no generic eval would catch
2. **A deployed judge** that can score EnergyBot automatically in CI
3. **A regression gate** — if anyone changes the prompt and breaks NEM 3.0 awareness, the pipeline catches it

My manager's feedback: "You found in 4 days what took us 3 weeks to discover manually on our first agent. That's the point of the tool."

---

## What I Learned

### 1. Evaluation is harder than building

Building an agent that sounds good takes an afternoon. Proving it's actually correct in a specific domain takes structured methodology. GEDD gives you that structure.

### 2. Domain knowledge > ML knowledge (for eval)

I don't know much about solar energy policy. But by reading the agent's responses carefully and Googling "NEM 3.0 California," I caught a failure that would have cost a homeowner money. The tool doesn't require ML expertise — it requires attention to detail and domain curiosity.

### 3. Error codes are the real output

The golden dataset is useful. The judge prompt is useful. But the error codes — `nem_version_confusion`, `itc_outdated` — those are the real value. They're the vocabulary the team uses to talk about failures. When someone says "we have an ITC issue," everyone knows exactly what that means.

### 4. The pipeline is the product

My manager keeps saying this. The agent will change — new models, new prompts, new tools. But the eval pipeline persists. The golden queries, the error codes, the judges — they're the institutional knowledge that prevents regressions.

### 5. Deploy first, test against the real thing

I initially wanted to test locally. My manager said "deploy first." She was right — the live endpoint had slightly different behavior (formatting, latency) than local. Testing against the real thing means your golden queries are grounded in reality.

---

## The Commands I Used (Cheat Sheet)

```bash
# Step 1-2: Define agent + system prompt
grounded-evals chat --session session.json

# Step 3: Deploy
bash scripts/deploy-agent.sh

# Step 4: Run queries against live agent
grounded-evals eval --session session.json --output eval_results.json

# Step 5: Annotate responses
grounded-evals annotate --results eval_results.json --session session.json

# Step 6a: Generate judge
grounded-evals judge --session session.json --results eval_results.json

# Step 6b: Connect to SageMaker MLflow
grounded-evals mlflow --session session.json --results eval_results.json \
  --tracking-uri $SAGEMAKER_MLFLOW_ARN

# Step 6c: Run full eval through MLflow (for CI)
grounded-evals mlflow --session session.json --run-eval

# Bonus: Check status anytime
grounded-evals status --session session.json
```

---

## For Other Interns

If you're starting on an AI team and they hand you GEDD:

1. **Don't skip the annotation step.** That's where you learn the domain. Reading 9 agent responses carefully teaches you more about the problem space than reading 50 pages of documentation.

2. **Name your errors specifically.** Not "wrong" — `nem_version_confusion`. Not "incomplete" — `itc_outdated`. Specific names become specific judges.

3. **The flywheel is real.** After my Friday presentation, the PM added 3 more queries targeting NEM 3.0 edge cases. The eval suite grew. Next week, another intern will find new failures. The pipeline absorbs them.

4. **You don't need to be a domain expert.** You need to be curious enough to Google "is NEM 2.0 still current in California?" when something feels off. The tool gives you the structure; you bring the curiosity.

---

*Built with [GEDD](https://github.com/aws-samples/sample-GEDD). The eval pipeline is the product.*
