# GEDD — find what your AI agent gets wrong

[![CI](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml/badge.svg)](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT-0](https://img.shields.io/badge/License-MIT--0-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/aws-samples/sample-GEDD?style=social)](https://github.com/aws-samples/sample-GEDD/stargazers)

You shipped an AI agent. Now you need to prove it works — to your CEO, to compliance, to the team that inherits it. The agent fails in ways no rubric anticipated, and the eval tools expect you to know what to measure before you've seen what breaks.

GEDD is the tool for *before* you have a rubric. A domain expert has a conversation, and 90 minutes later you have a production eval pipeline.

> **The eval pipeline is the product. The agent is just the thing it produces.**

<img width="4644" height="5854" alt="Quality Metrics Pipeline-2026-05-31-074649" src="https://github.com/user-attachments/assets/c2b6c3b4-8b56-4eea-a221-c0287a56fb7d" />


📖 **Read the why:** [Why Grounded Theory? for reliable AI Agents](https://balachanderkeelapudi.substack.com/p/why-grounded-theory-for-reliable)

---

## The Pipeline

Two personas. Six steps. One `session.json` connects them.

```
╔══════════════════════════════════════════════════════════════════════════╗
║  DOMAIN EXPERT (PM / SME)                                              ║
║  Tool: /gedd in Claude Code                                            ║
║                                                                         ║
║  Step 1  Define Agent       "RxBot helps patients with medications"     ║
║  Step 2  System Prompt      "Never prescribe. Always escalate."         ║
║  Step 3  Deploy             → live on Amazon Bedrock AgentCore          ║
║  Step 4  Golden Queries     20 test cases via Open Coding methodology   ║
║  Step 5  Annotate & Judge   ✓/⚠/✗ → error codes → G-Eval rubric       ║
║                                                                         ║
╠══════════════════════════════════════════════════════════════════════════╣
║  ML ENGINEER                                                           ║
║  Tool: grounded-evals mlflow                                           ║
║                                                                         ║
║  Step 6  MLflow Pipeline    → SageMaker experiment + CI/CD gates       ║
║                                                                         ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**Why deploy before testing?** The agent only needs the system prompt to function. By deploying at Step 3, all golden queries run against the *real endpoint* — latency, IAM, cold starts included. If the prompt changes, redeployment is one command.

**Why two personas?** The domain expert knows what "correct" means. The ML engineer knows how to run it at scale. GEDD gives each the right tool and connects them with one file.

---

## Quick start

### For Domain Experts: Claude Code skill

```bash
cd grounded-evals
pip install -e .
claude          # opens Claude Code
```
```
/gedd
```

The skill guides you through all 5 steps conversationally. No code. No YAML. Just answer questions about your agent and mark responses correct or incorrect.

### For ML Engineers: SageMaker MLflow bridge

```bash
pip install sagemaker-mlflow

grounded-evals mlflow \
  --session session.json \
  --results eval_results.json \
  --tracking-uri arn:aws:sagemaker:us-east-1:ACCOUNT:mlflow-tracking-server/SERVER
```

Creates custom judges, eval dataset, and metrics in your SageMaker MLflow server. Add `--run-eval` to score the agent through all judges.

### For everyone: Web UI

```bash
pip install -e ".[dev]"
grounded-evals serve
```

Open `http://localhost:8080` — 17 pre-loaded demo scenarios, no LLM calls needed.

---

## What each step produces

| Step | Who | Input | Output |
|------|-----|-------|--------|
| 1. Define | Domain Expert | "It's a pharmacy assistant for patients" | Bounded context in `session.json` |
| 2. Prompt | Domain Expert | Collaborative drafting | System prompt + safety rules |
| 3. Deploy | Domain Expert | One command | Live agent on AgentCore |
| 4. Test | Domain Expert | Coach proposes queries | 20 golden queries + agent responses |
| 5. Judge | Domain Expert | ✓/⚠/✗ per response | Error codes + G-Eval rubric |
| 6. Ship | ML Engineer | `grounded-evals mlflow` | SageMaker experiment + CI/CD gates |

The domain expert never touches MLflow. The ML engineer never touches the golden dataset. Each works in their tool, connected by `session.json`.

---

## What the domain expert discovers

We tested across 4 domains. In every case, the expert caught failures an engineer would miss:

| Domain | Error Code | What Happened | Why Only an Expert Catches It |
|--------|-----------|---------------|-------------------------------|
| Pharmacy | `dosage_unit_confusion` | Agent said "mg" when context suggests "mcg" | 1000x dosage error — potentially fatal |
| Insurance | `coverage_hallucination` | Assumed policy exists without checking | Could lead policyholder to believe they're covered |
| Tax | `incomplete_guidance` | Didn't recommend CPA for $200K scenario | Liability issue in tax advice |
| Immigration | `bar_misapplication` | Said 3-year bar applies to 90-day overstay | Bar only triggers at 180+ days (INA §212(a)(9)(B)) |

These aren't generic "hallucination" labels. They're domain-specific failure modes in the expert's own vocabulary — and they become the criteria in the deployed judge.

---

## The AWS-native stack

```
Claude Code (/gedd skill)
  └── Domain Expert conversation → session.json
                    │
                    │  grounded-evals mlflow --tracking-uri ARN
                    ▼
Amazon SageMaker MLflow (managed tracking server)
  ├── Custom judges (make_judge from error codes)
  ├── Eval datasets (golden queries + expectations)
  ├── Metrics (human_tsr, error_code_count)
  └── Auth: IAM SigV4 (via sagemaker-mlflow plugin)
                    │
                    ▼
Amazon Bedrock
  ├── AgentCore (deployed agent runtime)
  └── Claude Haiku 4.5 (inference for agent + judges)
```

No external services. No API keys to rotate. All IAM.

---

## CI/CD integration

```yaml
# .github/workflows/agent-eval.yml
- run: |
    grounded-evals mlflow \
      --session session.json \
      --tracking-uri ${{ secrets.SAGEMAKER_MLFLOW_ARN }} \
      --run-eval
```

Every push that changes the agent triggers the eval pipeline. If TSR drops below 95%, the deploy is blocked.

---

## 17 demo scenarios

No LLM calls needed. Each is pre-loaded with golden queries, annotations, error codes, and a generated judge.

| Demo | Domain | Key failure modes |
|------|--------|------------------|
| **TravelBot** | Flight booking | Hallucinated entities, fabricated booking data |
| **ClinicalBot** | Clinical triage | Missed escalation, contraindication miss |
| **LexBot** | Legal assistant | Jurisdiction error, unauthorized legal advice |
| **WealthBot** | Financial planning | Unlicensed advice, projection hallucination |
| **HRBot** | HR policy Q&A | Policy misquote, confidentiality breach |
| **EduBot** | Student learning | Answer reveal, grade inflation |
| **VaultEx AI** | Crypto exchange | Regulatory misguidance, fee hallucination |
| **PixelGuard** | Gaming moderation | False positive bans, harassment miss |
| **InsureBot** | Insurance claims | Bad-faith denial, coverage hallucination |
| **PropBot** | Real estate | Fair Housing steering, fabricated comps |
| **RxBot** | Pharmacy | Drug interaction miss, dosage unit confusion |
| **TaxBot** | Tax/accounting | Deduction hallucination, Circular 230 violation |
| **ClaimsBot** | Defense contracting | ITAR violation, CUI spillage |
| **FoodBot** | Food safety | Allergen cross-contact, HACCP temp error |
| **AutoBot** | Automotive | Lemon law omission, CARS Rule violation |
| **MigrateBot** | Immigration | Asylum deadline miss, bar misapplication |
| **EnergyBot** | Energy/utilities | Solar ITC outdated, NEM 3.0 confusion |

---

## CLI reference

| Command | What it does |
|---------|-------------|
| `chat` | Conversational coaching (Steps 1-5) |
| `eval` | Run golden queries against a model |
| `annotate` | Mark responses ✓/⚠/✗ with error codes |
| `judge` | Generate G-Eval judge prompt |
| `mlflow` | Export to SageMaker MLflow (Step 6) |
| `export` | Write golden dataset as JSONL/CSV/JSON |
| `status` | Session dashboard |
| `analyze` | Map error codes to eval dimensions |
| `serve` | Start the web UI |
| `fracture` | Fracture domain into test categories |
| `check-saturation` | Check dataset coverage |
| `coverage` | Bar-chart breakdown by category |
| `compare` | Check if a new prompt adds unique coverage |

```bash
grounded-evals --help
```

---

## Why this works

Most eval tools ask: *what should we measure?* GEDD asks: *what is actually happening?*

- **You can't evaluate what you haven't observed.** Pre-baked rubrics miss your agent's unique failures.
- **Criteria should be weighted by evidence.** A dosage unit confusion isn't the same severity as a tone slip.
- **Your evaluation evolves with the agent.** New failure modes surface; the methodology absorbs them.
- **Your work becomes load-bearing.** The judge is in *your* domain vocabulary, not generic "helpfulness 1-5."

The methodology is grounded theory — the same discipline social scientists use to find patterns in human data. We use it to find patterns in agent failures.

---

## Guides

| Guide | For |
|-------|-----|
| [Pipeline Guide](grounded-evals/docs/pipeline-guide.md) | Full two-persona workflow with CI/CD YAML |
| [Domain Expert Guide](grounded-evals/docs/domain-expert-guide.md) | End-to-end walkthrough for PMs |
| [PM → Production Judge](grounded-evals/docs/pm-to-ml-llm-judge.md) | ML engineer: turn annotations into CI judge |
| [Cohen's Kappa](grounded-evals/docs/cohens-kappa-for-llm-judges.md) | Calibrate judge-human agreement (κ ≥ 0.80) |
| [Building an LLM Judge](grounded-evals/docs/building-llm-as-a-judge.md) | Rubric design, weighting, few-shot calibration |

---

## ⭐ Found this useful?

If GEDD helped you find what your agent gets wrong, **[a star](https://github.com/aws-samples/sample-GEDD)** helps others find it too.

---

## License

MIT-0. See [LICENSE](LICENSE).

Security issues: see [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications).
