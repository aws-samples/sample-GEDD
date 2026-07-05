# GEDD - SME Error Analysis → Annotations → Domain Driven Specs Development

[![CI](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml/badge.svg)](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT-0](https://img.shields.io/badge/License-MIT--0-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/aws-samples/sample-GEDD?style=social)](https://github.com/aws-samples/sample-GEDD/stargazers)

GEDD is a Coach-first product for creating domain-expert-curated evidence from AI-agent failures and turning that evidence into domain-driven specs.

The product has one main path:

```text
Coach → SME Error Analysis → Annotations → Kiro requirements.md + LLM Judge
```

Start in `Coach`. Define the agent, generate or refine test cases, guide SME error analysis, and curate the evidence that drives two concrete outputs:

| Output | File | Why it matters |
|---|---|---|
| Kiro Domain Spec | `requirements.md` | Converts observed failure modes into Kiro-ready user stories and EARS acceptance criteria |
| LLM-as-a-Judge | `llm-judge.md` or judge prompt markdown | Converts the same failure modes into an automated release gate |

GEDD is not a generic model leaderboard or demo gallery. Its job is to capture the domain expert's evidence: what failed, why it matters, what severity it carries, and what requirement or judge rule should prevent it. Kiro then uses that curated evidence to generate executable specs.

![GEDD Coach and annotation workflow](grounded-evals/docs/GEDD_optimized.gif)

The longer methodology essay is in [METHODOLOGY.md](METHODOLOGY.md). This README is the practical product and engineering guide.

## Product Shape

GEDD works in two places:

| Surface | Use it when | Output |
|---|---|---|
| Web UI Coach | SMEs need a guided product workflow for agent definition, test cases, error analysis, and annotations | Curated evidence plus downloadable Kiro `requirements.md` and LLM Judge |
| Kiro Power | You want Kiro to consume GEDD's curated evidence inside the IDE | `.kiro/specs/{agent-name}/requirements.md` and `.kiro/specs/{agent-name}/llm-judge.md` |

GEDD provides the evidence layer. The domain expert curates that evidence through:

- Agent purpose, target users, capabilities, and task boundary
- Golden queries or imported traces
- SME verdicts: correct, partial, incorrect
- Failure codes in the SME's own domain vocabulary
- Severity, confidence, and memos
- Optional saturation and axial-coding evidence

The core idea is simple: Kiro should not invent domain requirements from generic assumptions. GEDD provides curated domain evidence, and every important SME annotation should become either a Kiro requirement, a judge rule, or both.

## Quick Start

Start the web app:

```bash
cd grounded-evals
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
grounded-evals serve --host 127.0.0.1 --port 8080
```

Open:

```text
http://127.0.0.1:8080/coach
```

Local runs start in guest mode unless `ADMIN_PASSWORD` or Cognito environment variables are configured. If port `8080` is busy, use `--port 8081`.

## Web UI Workflow

| Step | Page | What happens | Output |
|---|---|---|---|
| 1 | `Coach` | Define the agent, users, capabilities, task boundary, system prompt, and test-case plan | Agent spec + query plan |
| 2 | `Error Analysis` | Inspect representative queries, traces, and response evidence | Domain-expert-curated failure evidence |
| 3 | `Annotations` | SMEs assign verdicts, failure codes, severity, confidence, and memos | Codebook + annotated failures |
| 4 | `Kiro requirements.md` | Generate a Kiro-ready domain spec using EARS acceptance criteria | `requirements.md` |
| 5 | `LLM Judge` | Generate a release-gate judge from the same failure modes | Judge prompt |
| 6 | `Outputs` | Download the two artifacts | Output bundle |

The app navigation intentionally keeps this narrow. Demos are available separately at `/demos`, but they are reference seed sessions, not the product workflow.

## Kiro requirements.md

The first GEDD output follows Kiro's requirements-first spec format and is generated from GEDD's domain-expert-curated evidence:

```markdown
# Requirements Document

## Introduction

## Requirements

### Requirement 1
**User Story:** As a {target user}, I want {domain-safe behavior}, so that {risk is prevented}.

#### Acceptance Criteria
1. WHEN {trigger}, THE SYSTEM SHALL {expected behavior}.
2. IF {unwanted condition}, THEN THE SYSTEM SHALL {safe response}.
3. WHILE {domain state}, THE SYSTEM SHALL {required invariant}.
```

GEDD uses EARS patterns so requirements stay testable:

| Evidence | EARS pattern | Example shape |
|---|---|---|
| Always-active rule | Ubiquitous | `THE SYSTEM SHALL ...` |
| Triggering user event | Event-driven | `WHEN ..., THE SYSTEM SHALL ...` |
| Domain state | State-driven | `WHILE ..., THE SYSTEM SHALL ...` |
| Observed failure | Unwanted behavior | `IF ..., THEN THE SYSTEM SHALL ...` |
| State plus trigger | Complex | `WHILE ..., WHEN ..., THE SYSTEM SHALL ...` |

Most high-value requirements come from unwanted behavior: an SME saw the agent fail, named the failure, and GEDD turns that release risk into an acceptance criterion.

## LLM Judge

The second GEDD output is an LLM-as-a-Judge prompt that enforces the same domain-expert-curated failures captured in `requirements.md`.

The judge should return a structured release decision:

```json
{
  "pass_fail": "pass | fail",
  "failure_code": "domain failure label or null",
  "severity": "low | medium | high | critical | catastrophic",
  "rationale": "why the response passes or fails",
  "evidence_references": ["query id", "requirement id"],
  "recommended_action": "ship | revise | block release"
}
```

The judge is intentionally domain-specific. It should not start with generic helpfulness; it should check the failure modes SMEs actually observed.

## Kiro Power

The repository includes a Kiro Power in [`power-gedd/`](power-gedd/). It brings the GEDD workflow into Kiro by treating GEDD evidence as the source of truth.

Install it in Kiro:

```text
Powers panel → Add Custom Power → Import from folder → power-gedd/
```

Use it when you want Kiro to generate or upgrade specs from GEDD's domain-expert-curated evidence:

```text
Use GEDD to turn this exported error analysis into Kiro requirements.md and an LLM Judge.
```

Power structure:

```text
power-gedd/
├── POWER.md
└── steering/
    ├── annotation-workflow.md
    ├── session-import.md
    ├── pattern-discovery.md
    ├── requirements-generation.md
    └── judge-generation.md
```

Optional Kiro follow-ons such as `design.md` and `tasks.md` can come later, but they are not the core GEDD product. The core product is `requirements.md` plus the LLM Judge.

## Bring Your Own Agent

Use GEDD when you have a real or proposed agent and need domain-expert-curated evidence before generating requirements or automating evaluation.

| Step | What to do | Output |
|---|---|---|
| 1. Define | Describe the agent, user, task boundary, and system prompt in `Coach` | Agent spec and prompt |
| 2. Build queries | Generate or paste queries that cover normal, edge, ambiguous, adversarial, multi-turn, and recovery cases | Query set |
| 3. Get responses | Run the saved prompt against Bedrock, Anthropic, or a configured runtime, or paste existing traces | Response queue |
| 4. Annotate | Review each response in `Annotations` and capture verdict, code, severity, confidence, and memo | Human labels and codebook |
| 5. Generate specs | Open `Kiro requirements.md` and generate EARS acceptance criteria from the evidence | `requirements.md` |
| 6. Generate judge | Open `LLM Judge` and generate a release gate from the same failure modes | Judge prompt |

If you already have production traces, use the app as an annotation surface rather than generating new responses. See [Paste In Traces](grounded-evals/docs/paste-in-traces.md).

## Reference Seeds

Reference seeds live at `/demos`. They exist to show what good evidence looks like before teams bring their own traces.

| Reference seed | What it demonstrates |
|---|---|
| AAA game localization | Runtime strings, storefront copy, subtitles, RTL input prompts, region rules, culturalization, paid-currency copy, live-event dates, and glossary consistency |
| AWS Cloud GDPR auditor | S3 and CloudWatch retention, CloudTrail logging, Bedrock prompt reuse, Rekognition review, DSAR deletion, shared responsibility, transfer risk, and breach escalation |

They produce the same two outputs as any custom project: Kiro `requirements.md` and an LLM Judge. They are intentionally separate from the main Coach product path.

## License And Security

License: MIT-0. See [LICENSE](LICENSE).

Security issue reporting: see [CONTRIBUTING.md](CONTRIBUTING.md#security-issue-notifications).
