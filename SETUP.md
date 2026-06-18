# GEDD setup — for engineers

Everything you need to get GEDD running locally and deployed. The PM-facing tour lives in [README.md](README.md); this doc is the engineer's reference.

Before a public beta or production launch, run the [launch checklist](grounded-evals/docs/launch-checklist.md). It covers fresh install, browser E2E, auth, AWS deployment, web-app and CLI validation, MLflow handoff, rollback, and no-go criteria.

---

## Prerequisites

- Python 3.12+
- AWS account with [Amazon Bedrock model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) enabled
- AWS credentials configured (`aws configure` or environment variables)

---

## Quick start

```bash
cd grounded-evals

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run the app
grounded-evals serve
```

The app runs at `http://localhost:8080`. Local demo mode does not require a password unless you set `ADMIN_PASSWORD` or Cognito environment variables.
If port 8080 is already in use, run `grounded-evals serve --port 8081`.

---

## LLM provider configuration

GEDD supports two LLM providers. Choose one.

### Option A: Amazon Bedrock (default — recommended for workshops)

Uses IAM credentials via boto3. No API key needed — just ensure your AWS account has Bedrock model access enabled.

```bash
# Set your region (must match where you enabled Bedrock models)
export AWS_REGION=us-east-1

# Optionally override the default model for the coaching agent
export BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
```

### Option B: Direct Anthropic API (local dev, no AWS)

If you don't have Bedrock access, use a direct Anthropic API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
export BEDROCK_MODEL_ID=claude-sonnet-4-6-20250514   # uses Anthropic model names
```

> **Note:** When `ANTHROPIC_API_KEY` is set, it takes priority over Bedrock.

---

## Available models for evaluation

The eval runner supports these Bedrock models out of the box (select up to 3 for side-by-side comparison):

| Model | ID | API |
|---|---|---|
| Claude Haiku 4.5 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Anthropic Messages |
| Claude Sonnet 4.5 | `us.anthropic.claude-sonnet-4-5-20241022-v2:0` | Anthropic Messages |
| Claude Opus 4.5 | `us.anthropic.claude-opus-4-5-20250115-v1:0` | Anthropic Messages |
| Amazon Nova Pro | `us.amazon.nova-pro-v1:0` | Bedrock Converse |
| Amazon Nova Lite | `us.amazon.nova-lite-v1:0` | Bedrock Converse |
| Amazon Nova Micro | `us.amazon.nova-micro-v1:0` | Bedrock Converse |
| Llama 3.3 70B | `us.meta.llama3-3-70b-instruct-v1:0` | Bedrock Converse |
| Mistral Large 24.11 | `us.mistral.mistral-large-2411-v1:0` | Bedrock Converse |

> **Workshop tip:** Ensure you have [requested access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) to the models you want to use in the AWS Console under **Amazon Bedrock → Model access**.

---

## Authentication

For local exploration, the app starts in guest mode when neither Cognito nor `ADMIN_PASSWORD` is configured.

For workshop use, set a simple password login:

```bash
export ADMIN_PASSWORD=your-workshop-password
```

For production, configure Cognito:

```bash
export COGNITO_USER_POOL_ID=us-east-1_xxxxxxx
export COGNITO_CLIENT_ID=your-client-id
```

---

## All environment variables

| Variable | Purpose | Default |
|---|---|---|
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `BEDROCK_MODEL_ID` | Model ID for coaching agent | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| `ANTHROPIC_API_KEY` | Direct Anthropic API key (bypasses Bedrock) | — |
| `ADMIN_PASSWORD` | Enables simple password login when set | — (guest mode when Cognito is also unset) |
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8080` |
| `COGNITO_USER_POOL_ID` | Cognito User Pool (production auth) | — |
| `COGNITO_CLIENT_ID` | Cognito App Client ID | — |
| `STORAGE_SECRET` | Secret key for session persistence (set a strong random string in production) | auto-generated random 32-byte hex per startup |
| `AGENTCORE_AGENT_ID` | Remote AgentCore agent ID | — |
| `LANGSMITH_API_KEY` | LangSmith tracing key (optional) | — |
| `LANGSMITH_PROJECT` | LangSmith project name | `agent-playground` |

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `AccessDeniedException` on Bedrock calls | Enable model access in AWS Console → Bedrock → Model access |
| `NoCredentialProviders` | Run `aws configure` or set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` |
| Wrong region error | Ensure `AWS_REGION` matches where you enabled Bedrock models |
| Models not responding | Check that the specific model ID is available in your region |
| Login not working | If you intended password auth, set `ADMIN_PASSWORD` before starting the app |

---

## Architecture

```
NiceGUI Web App (Dark Mode)
  ├── Home — interactive demo + saved sessions
  ├── Coach — define agent, system prompt, golden queries
  ├── Eval — run queries against up to 3 Bedrock models side-by-side
  ├── Tag Failures — Open Coding annotation workbench
  ├── Map Root Causes — Paradigm Model canvas
  └── Report — judge generation + calibration
       ↓
Core Engine
  ├── open_coding/     # fracture, compare, saturation
  ├── axial_coding/    # mapper, paradigm
  ├── judge_builder/   # rubric, prompt_gen, calibrate, few_shot,
  │                    # constitutional, ensemble, active_learning
  └── llm/client       # Bedrock + Anthropic
       ↓
AWS Infrastructure (optional)
  ├── CloudFront (public HTTPS domain)
  ├── ALB (origin)
  ├── ECS Fargate (UI deployment)
  ├── Cognito (authentication)
  ├── ECR (container registry)
  └── AgentCore (agent runtime)
```

---

## Project structure

```
grounded-evals/
├── src/grounded_evals/
│   ├── open_coding/        # Phase 1: discover patterns
│   │   ├── fracture.py     #   domain → categories + codes
│   │   ├── compare.py      #   constant comparison method
│   │   └── saturation.py   #   theoretical saturation checks
│   ├── axial_coding/       # Phase 2: relate patterns
│   │   ├── mapper.py       #   errors → 8 standard dimensions
│   │   └── paradigm.py     #   build Paradigm Model
│   ├── judge_builder/      # Phase 3: build judge (ML-enhanced)
│   │   ├── rubric.py       #   generate rubric (paradigm-enriched, severity-weighted)
│   │   ├── prompt_gen.py   #   3 modes: standard / few-shot / G-EVAL CoT
│   │   ├── calibrate.py    #   Cohen's weighted κ + per-criterion breakdown
│   │   ├── few_shot.py     #   Prometheus-style exemplar selection + injection
│   │   ├── constitutional.py # principle-by-principle evaluation (Const. AI)
│   │   ├── ensemble.py     #   self-consistency judging
│   │   └── active_learning.py # margin sampling + coverage gap detection
│   ├── agent/              # conversational coach
│   │   ├── handler.py      #   tool-use loop
│   │   ├── tools.py        #   coaching tools
│   │   └── prompt.py       #   coach system prompt
│   ├── ui/                 # NiceGUI pages (dark mode)
│   │   ├── home_page.py
│   │   ├── coding_page.py
│   │   ├── analysis_page.py
│   │   ├── report_page.py
│   │   ├── eval_page.py
│   │   ├── eval_tab.py
│   │   └── layout.py       # design system + nav
│   ├── ingest/             # input parsing
│   ├── models/core.py      # Pydantic data models
│   ├── llm/client.py       # Bedrock + Anthropic client
│   └── app.py              # entry point + Coach page
├── agentcore/              # AWS AgentCore runtime
├── infra/                  # CDK infrastructure
├── configs/                # example YAML specs
├── docs/research/          # PM interview kit
└── tests/
```

---

## Deployment

Infrastructure is defined with AWS CDK:

```bash
cd grounded-evals/infra
pip install -r requirements.txt
cdk deploy --all
```

Stacks: Network (VPC, ALB, CloudFront) → ECR → ECS Fargate (UI) → Cognito (auth) → AgentCore (agent runtime).

The Network stack outputs `CloudFrontUrl`, for example `https://dxxxxx.cloudfront.net`. Use that as the public web app URL.

For a custom CloudFront hostname, provide a certificate from `us-east-1`:

```bash
./scripts/deploy-infra.sh \
  --cloudfront-domain gedd.example.com \
  --cloudfront-cert arn:aws:acm:us-east-1:123456789012:certificate/abc123
```

Then create a DNS `CNAME` or Route 53 alias from your hostname to the emitted `CloudFrontDomainName`.

The `--cert` flag configures an HTTPS listener on the ALB for direct-origin deployments. For the default CloudFront URL, you don't need an ALB certificate because CloudFront terminates public HTTPS.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: [CONTRIBUTING#security-issue-notifications](CONTRIBUTING.md#security-issue-notifications).

License: MIT-0. See [LICENSE](LICENSE).
