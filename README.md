# GEDD - SME evidence to LLM-as-Judge response gates

<img width="1370" height="667" alt="Screenshot 2026-07-09 at 10 08 17 PM" src="https://github.com/user-attachments/assets/eeee4959-3189-4913-9e3f-d4384c59a440" />


[![CI](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml/badge.svg)](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT-0](https://img.shields.io/badge/License-MIT--0-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/aws-samples/sample-GEDD?style=social)](https://github.com/aws-samples/sample-GEDD/stargazers)

Coach leads SMEs and product managers from baseline evidence to a judge-subagent `requirements.md`, and an LLM-as-Judge gate that checks customer-facing responses before customers see them.

The product has one main path:

```text
Domain Expert Intake -> Baseline Kiro requirements.md -> Curated Query Set -> Kiro Baseline Test -> SME Annotations -> SME_error_analysis.md -> Kiro Judge-Subagent requirements.md + LLM-as-Judge Gate + Measurement
```

Start in `Coach`. The app uses progressive disclosure: the SME sees one current step, one Coach prompt, and one allowed action. Coach first asks for the SME's domain, then asks for the baseline Kiro `requirements.md`, then leads query curation, baseline testing, annotations, and output generation in order.

| Output | File | Why it matters |
|---|---|---|
| SME Evidence Handoff | `SME_error_analysis.md` | The domain-expert-curated source artifact for Kiro and the judge subagent |
| Kiro Judge-Subagent Spec | `requirements.md` | Converts SME-annotated baseline failures into Kiro-ready user stories and EARS acceptance criteria for the LLM-as-Judge subagent |
| LLM-as-Judge Gate | `llm-judge.md` or judge prompt markdown | Converts the same failure modes into a pre-customer response gate |
| Measurement Report | app view or markdown export | Compares generic baseline requirements against the GEDD judge-subagent spec for coverage, traceability, testability, and response-quality signals |

GEDD is not a generic model leaderboard or demo gallery. Its first job is domain query curation. Its second job is SME-guided error analysis of the Kiro baseline agent. GEDD packages that work as `SME_error_analysis.md`; Kiro then uses the file to create the judge-subagent `requirements.md` and judge rules that gate customer-facing responses.

The current UI is intentionally simple: the homepage has one action, `Open Coach`. The Coach is the product surface. Demos, generated outputs, and reference seeds stay secondary until Coach makes them relevant.

![GEDD Coach and annotation workflow](grounded-evals/docs/GEDD_optimized.gif)

The longer methodology essay is in [METHODOLOGY.md](METHODOLOGY.md). This README is the practical product and engineering guide.

## Product Shape

GEDD works in two places:

| Surface | Use it when | Output |
|---|---|---|
| Web UI Coach | SMEs need a guided step-by-step workflow for domain intake, query curation, baseline testing, error analysis, and annotations | Curated evidence plus downloadable Kiro judge-subagent `requirements.md`, LLM-as-Judge gate, and improvement measurement |
| Kiro Power | You want Kiro to consume GEDD's curated evidence inside the IDE | Generated `.kiro/specs/{agent-name}/requirements.md` for the judge subagent and `.kiro/specs/{agent-name}/llm-judge.md` |

GEDD provides the evidence layer. The domain expert curates that evidence through:

- Agent purpose, target users, capabilities, and task boundary
- Curated domain queries or imported baseline traces
- SME verdicts: correct, partial, incorrect
- Failure codes in the SME's own domain vocabulary
- Severity, confidence, and memos
- Optional saturation and axial-coding evidence

The core idea is simple: Kiro should not invent judge rules from generic assumptions. GEDD provides SME-curated evidence from baseline behavior, and every important SME annotation should become a Kiro judge-subagent requirement, a judge rule, or both.

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
http://127.0.0.1:8080/
```

The homepage intentionally shows only `Open Coach`. You can also go directly to `http://127.0.0.1:8080/coach`.

Local runs start in guest mode unless `ADMIN_PASSWORD` or Cognito environment variables are configured. If port `8080` is busy, use `--port 8081`.

To use an existing Kiro baseline, click `Open Coach`, answer the domain prompt, then use the baseline step to upload the current `.kiro/specs/{agent-name}/requirements.md` file. GEDD stores it as baseline evidence and embeds it in `SME_error_analysis.md` under `Baseline Kiro Requirements`.

## First Run For A Domain Expert

Open the app and click `Open Coach`. Coach leads the SME through six small decisions. Downstream pages appear only when the current project state makes them relevant.

| Step | What the SME does | Why it exists | App output |
|---|---|---|---|
| 1. Identify the SME domain | Tell Coach the domain, users, risks, permissions, constraints, and known edge cases | Prevents Kiro from inventing generic requirements without domain context | Domain expert profile |
| 2. Upload the baseline Kiro spec | Upload `.kiro/specs/{agent-name}/requirements.md`, or capture the baseline prompt/spec context | Establishes what the baseline agent was built from before GEDD evidence is added | Baseline Kiro Requirements section in `SME_error_analysis.md` |
| 3. Curate the query set | Approve happy path, edge, adversarial, ambiguous, multi-turn, recovery, persona, and red-flag queries | Creates the SME-owned test set that exposes real domain behavior | Coverage-backed query set |
| 4. Test the Kiro baseline agent | Run or paste baseline responses for those queries | Converts the initial Kiro spec into observable behavior that can be reviewed | Baseline response traces |
| 5. Annotate with SME judgment | Label verdict, failure code, severity, confidence, missing domain rule, and memo | Turns SME expertise into structured error analysis instead of loose feedback | Codebook and annotated failures |
| 6. Generate the handoff and outputs | Export `SME_error_analysis.md`, then create the Kiro judge-subagent `requirements.md`, LLM-as-Judge gate, and measurement | Gives Kiro and the judge one shared source of truth before customer-facing responses are shown | `SME_error_analysis.md`, Kiro judge `requirements.md`, LLM-as-Judge gate, measurement report |

The product rule is: no judge-subagent requirements before SME evidence. Kiro's requirements-first workflow and EARS acceptance criteria work best when every gate traces back to an observed baseline failure, an SME-approved query, or a domain rule the SME explicitly named.

## Web UI Workflow

The application is organized around Coach, not demo browsing. `Home` and `Coach` are always visible. `Annotations`, `Evidence`, `Judge Spec`, and `Judge` appear only after Coach has enough evidence for that surface.

| Route | UI label | Purpose |
|---|---|---|
| `/` | Home | Minimal entry screen with one action: `Open Coach` |
| `/coach` | Coach | One current step, one Coach prompt, and one allowed action for domain intake, baseline upload, query curation, and SME-guided evidence collection |
| `/coding` | Annotations | Review baseline responses and label verdict, failure code, severity, confidence, missing rule, and memo |
| `/report` | Evidence | Export `SME_error_analysis.md` and inspect the curated evidence handoff |
| `/requirements` | Judge Spec | Generate the Kiro judge-subagent `requirements.md` from SME evidence using EARS-style acceptance criteria |
| `/judge` | Judge | Generate the LLM-as-Judge response gate from the same failure modes |
| `/improvement` | Measurement | Compare baseline requirements against the GEDD judge-subagent requirements |
| `/demos` | Reference seeds | Load example evidence sessions; not the primary product path |

The app navigation intentionally keeps this narrow. The SME does not need to choose a workflow page up front. Coach sends them to Annotations only after baseline responses exist, and sends them to Evidence only after SME annotations exist. Demos are available separately at `/demos`, but they are reference seed sessions, not the product workflow.

## SME_error_analysis.md

The primary GEDD handoff is `SME_error_analysis.md`. It contains the domain profile, curated query set, baseline response evidence, SME annotations, failure codebook, memos, saturation evidence, and any generated judge prompt. Kiro can use this single file to build the judge-subagent `requirements.md` file and the runnable response gate.

## Kiro Judge-Subagent requirements.md

The Kiro requirements output follows Kiro's requirements-first spec format and is generated from `SME_error_analysis.md`. It specifies the LLM-as-Judge subagent, not the customer-facing assistant itself:

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

Most high-value judge requirements come from unwanted behavior: an SME saw the agent fail, named the failure, and GEDD turns that customer-response risk into an acceptance criterion.

## LLM-as-Judge Gate

The second GEDD output is an LLM-as-Judge prompt that enforces the same domain-expert-curated failures captured in the judge-subagent `requirements.md`.

The judge should return a structured response-gating decision before the answer is shown to a customer:

```json
{
  "pass_fail": "pass | fail",
  "failure_code": "domain failure label or null",
  "severity": "low | medium | high | critical | catastrophic",
  "rationale": "why the response passes or fails",
  "evidence_references": ["query id", "requirement id"],
  "recommended_action": "allow | revise_response | request_human_review",
  "customer_visible_block": true
}
```

The judge is intentionally domain-specific. It should not start with generic helpfulness; it should check the failure modes SMEs actually observed.

## Kiro Power

The repository includes a Kiro Power in [`power-gedd/`](power-gedd/). It brings the GEDD workflow into Kiro by treating GEDD evidence as the source of truth.

Install it in Kiro:

```text
Powers panel → Add Custom Power → Import from folder → power-gedd/
```

Use it when you want Kiro to create judge-subagent specs from GEDD's domain-expert-curated baseline evidence:

```text
Use GEDD to create the LLM-as-Judge subagent requirements.md from SME-curated evidence and generate the response gate.
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
    ├── judge-generation.md
    ├── design-generation.md
    └── tasks-generation.md
```

Optional Kiro follow-ons such as `design.md` and `tasks.md` can come later, but they are not the core GEDD product. The core product is `SME_error_analysis.md` feeding the judge-subagent `requirements.md` plus the LLM-as-Judge gate.

## Bring Your Own Agent

Use GEDD when you have a real or proposed agent and need a domain expert to turn baseline behavior into measured judge-subagent requirements.

| Step | What to do | Output |
|---|---|---|
| 1. Domain intake | Tell Coach which domain the SME owns, who uses the agent, what risks matter, and what constraints cannot be violated | Domain expert profile |
| 2. Upload baseline spec | Upload the existing `.kiro/specs/{agent-name}/requirements.md`, or capture baseline prompt/spec context | Baseline Kiro requirements evidence |
| 3. Curate queries | Generate or paste happy path, edge, ambiguous, adversarial, multi-turn, recovery, persona, and red-flag queries | Curated query set |
| 4. Test baseline | Run the Kiro baseline agent created from the initial `requirements.md`, or paste existing baseline traces | Baseline response queue |
| 5. Annotate | Review each baseline response in `Annotations` and capture verdict, code, severity, confidence, missing rule, and memo | Human labels and codebook |
| 6. Generate outputs | Export `SME_error_analysis.md`, generate judge-subagent `requirements.md`, generate the response gate, and measure uplift | Evidence handoff, judge spec, judge prompt, improvement report |

If you already have production traces, use the app as an annotation surface rather than generating new responses. See [Paste In Traces](grounded-evals/docs/paste-in-traces.md).

## Reference Seeds

Reference seeds live at `/demos`. They exist to show what good evidence looks like before teams bring their own traces.

| Reference seed | What it demonstrates |
|---|---|
| AAA game localization | Runtime strings, storefront copy, subtitles, RTL input prompts, region rules, culturalization, paid-currency copy, live-event dates, and glossary consistency |
| AWS Cloud GDPR auditor | S3 and CloudWatch retention, CloudTrail logging, Bedrock prompt reuse, Rekognition review, DSAR deletion, shared responsibility, transfer risk, and breach escalation |

They produce the same evidence handoff and downstream outputs as any custom project: `SME_error_analysis.md`, Kiro judge-subagent `requirements.md`, and an LLM-as-Judge gate. They are intentionally separate from the main Coach product path.

## License And Security

License: MIT-0. See [LICENSE](LICENSE).

Security issue reporting: see [CONTRIBUTING.md](CONTRIBUTING.md#security-issue-notifications).
