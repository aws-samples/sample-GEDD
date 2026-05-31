# GEDD → SageMaker MLflow Pipeline Guide

## Two Personas, One Pipeline

GEDD bridges the gap between domain expertise and ML engineering. The domain expert discovers what the agent gets wrong. The ML engineer turns those discoveries into a production eval pipeline.

```
Domain Expert (PM/SME)          ML Engineer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1: Define Agent            │
Step 2: System Prompt           │
Step 3: Deploy to AgentCore     │
Step 4: Golden Queries          │
Step 5: Annotate & Judge        │
         ─── handoff ───────────┤
                                │  Step 6: MLflow Pipeline
                                │    • Create experiment
                                │    • Register judges
                                │    • Wire into CI/CD
                                │    • Set regression gates
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Prerequisites

```bash
# Domain Expert needs:
pip install grounded-evals

# ML Engineer additionally needs:
pip install sagemaker-mlflow mlflow>=3.0
```

---

## Domain Expert Workflow (Steps 1-5)

### Option A: Claude Code skill (recommended)

```bash
cd grounded-evals
claude    # opens Claude Code
```
```
/gedd
```

The skill guides you through all 5 steps conversationally.

### Option B: CLI commands

```bash
# Step 1-2: Interactive coaching
grounded-evals chat --session session.json

# Step 3: Deploy
bash scripts/deploy-agent.sh

# Step 4: Run eval
grounded-evals eval --session session.json --output eval_results.json

# Step 5: Annotate + generate judge
grounded-evals annotate --results eval_results.json --session session.json
grounded-evals judge --session session.json --results eval_results.json
```

### What the Domain Expert produces

| Artifact | Contents |
|----------|----------|
| `session.json` | Agent spec, golden queries, annotations, error codes |
| `eval_results.json` | Agent responses to all golden queries |
| `judge_prompt.md` | G-Eval rubric with weighted criteria |
| `golden_dataset.jsonl` | Exportable test cases (optional) |

---

## ML Engineer Workflow (Step 6)

### Setup: SageMaker MLflow Tracking Server

Create a tracking server in SageMaker Studio or via CLI:

```bash
aws sagemaker create-mlflow-tracking-server \
  --tracking-server-name gedd-evals \
  --artifact-store-uri s3://my-bucket/mlflow-artifacts \
  --tracking-server-size Small
```

Note the ARN: `arn:aws:sagemaker:us-east-1:123456789:mlflow-tracking-server/gedd-evals`

### Connect GEDD to SageMaker MLflow

```bash
# One command bridges the two personas
grounded-evals mlflow \
  --session session.json \
  --results eval_results.json \
  --tracking-uri arn:aws:sagemaker:us-east-1:123456789:mlflow-tracking-server/gedd-evals
```

This creates in your SageMaker MLflow server:
- **Experiment:** `gedd-<agent-name>`
- **Custom judges:** One per error dimension (e.g., `gedd_accuracy`, `gedd_safety`)
- **Eval dataset:** Golden queries with expected behaviors
- **Metrics:** `human_tsr`, `error_code_count`, `categories_covered`
- **Artifacts:** `session.json`, `judge_prompt.md`, `gedd_eval_dataset.json`

### Run the eval pipeline

```bash
# Score the agent through all judges
grounded-evals mlflow \
  --session session.json \
  --tracking-uri arn:aws:sagemaker:us-east-1:123456789:mlflow-tracking-server/gedd-evals \
  --run-eval
```

### Add to CI/CD

```yaml
# .github/workflows/agent-eval.yml
name: Agent Evaluation
on:
  push:
    paths: ['agent/**', 'prompts/**']

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v6
        with:
          python-version: '3.11'
      - run: pip install grounded-evals sagemaker-mlflow
      - run: |
          grounded-evals mlflow \
            --session session.json \
            --tracking-uri ${{ secrets.SAGEMAKER_MLFLOW_ARN }} \
            --run-eval
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-east-1
```

### Set regression gates

In your CI pipeline, fail the build if:
- **Task Success Rate (TSR)** drops below 95% on `happy_path` queries
- **TSR** drops below 80% on `adversarial` queries
- Any **safety** judge scores below 4/5

---

## How the Artifacts Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Domain Expert produces:                                         │
│                                                                   │
│  session.json ─────────────────────────────────────────────┐    │
│    ├── agent_spec (name, domain, system_prompt)             │    │
│    ├── golden_prompts[] (20 test cases)                     │    │
│    ├── annotations[] (✓/⚠/✗ + error codes)                 │    │
│    └── prompt_variants[] (A/B versions)                     │    │
│                                                              │    │
│  eval_results.json ────────────────────────────────────┐    │    │
│    └── [{query, response, category, annotation}]        │    │    │
│                                                          │    │    │
│  judge_prompt.md ─────────────────────────────────┐     │    │    │
│    └── G-Eval rubric with chain-of-thought         │     │    │    │
└────────────────────────────────────────────────────┼─────┼────┼───┘
                                                     │     │    │
                    grounded-evals mlflow             │     │    │
                                                     ▼     ▼    ▼
┌─────────────────────────────────────────────────────────────────┐
│  SageMaker MLflow receives:                                      │
│                                                                   │
│  Experiment: gedd-rxbot                                          │
│    ├── Params: agent_name, domain, error_codes, dimensions       │
│    ├── Metrics: human_tsr, error_code_count, categories_covered  │
│    ├── Artifacts: session.json, judge_prompt.md, eval_dataset    │
│    └── Judges: gedd_accuracy(make_judge), gedd_correctness       │
│                                                                   │
│  When --run-eval:                                                │
│    ├── Calls predict_fn (Bedrock agent) for each test case       │
│    ├── Scores with all judges                                    │
│    └── Logs per-case scores + aggregate metrics                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Production Monitoring

Once the pipeline is in CI, the ML engineer monitors:

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Task Success Rate | `gedd_correctness` judge | < 95% (regression) |
| Accuracy score | `gedd_accuracy` judge | < 4.0 avg |
| Safety score | `gedd_safety` judge | Any < 3 |
| Judge-human agreement | Compare judge vs annotations | κ < 0.80 |
| Eval saturation | Category coverage | < 80% categories |

### Refreshing the eval suite

When the domain expert discovers new failure modes in production:

```bash
# Domain expert adds new queries
grounded-evals chat --session session.json
# → "add more" targeting new failure patterns

# ML engineer re-exports to MLflow
grounded-evals mlflow -s session.json --tracking-uri $ARN --run-eval
```

The eval suite grows with the agent. New error codes become new judges automatically.

---

## Architecture: The Full AWS Stack

```
┌──────────────────────────────────────────────────────────────┐
│  Claude Code (/gedd skill)                                    │
│  └── Domain Expert conversation → session.json               │
└──────────────────────────┬───────────────────────────────────┘
                           │
              grounded-evals mlflow --tracking-uri ARN
                           │
┌──────────────────────────▼───────────────────────────────────┐
│  Amazon SageMaker MLflow (managed tracking server)            │
│  ├── Experiments (one per agent)                              │
│  ├── Custom judges (make_judge from error codes)              │
│  ├── Eval datasets (golden queries)                           │
│  ├── Model Registry (agent versions)                          │
│  └── Auth: IAM SigV4 (via sagemaker-mlflow plugin)           │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│  Amazon Bedrock                                               │
│  ├── AgentCore (deployed agent runtime)                       │
│  ├── Claude Haiku 4.5 (inference for agent + judges)          │
│  └── Model access (IAM-controlled)                            │
└──────────────────────────────────────────────────────────────┘
```

All AWS-native. IAM for auth. S3 for artifacts. No external dependencies.
