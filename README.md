# GEDD - SME Error Analysis → Annotations → Domain Driven Specs Development

[![CI](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml/badge.svg)](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT-0](https://img.shields.io/badge/License-MIT--0-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/aws-samples/sample-GEDD?style=social)](https://github.com/aws-samples/sample-GEDD/stargazers)

GEDD is an SME Error Analysis → Annotations → Domain Driven Specs Development workflow that generates two AI-agent artifacts: Kiro `requirements.md` and an LLM-as-a-Judge prompt.

It turns domain-owner review of AI agent behavior into evidence-backed specs and release gates engineering can run.

The web app gives product managers, domain experts, and ML engineers one shared path to two generated outputs:

1. Run error analysis on representative queries and responses.
2. Capture expert annotations: verdicts, failure codes, severity, and memos.
3. Convert observed failures into `requirements.md` for Kiro and an LLM-as-a-Judge prompt.

The main product surface is `Coach`: define the agent, generate or refine test cases, guide SME error analysis, and produce the two outputs for Kiro and release evaluation.

![GEDD PM annotation walkthrough](grounded-evals/docs/GEDD_optimized.gif)

The longer methodology essay is in [METHODOLOGY.md](METHODOLOGY.md). This README is the practical product and engineering guide.

## What GEDD Produces

| Output | Who creates it | Who uses it | Why it matters |
|---|---|---|---|
| Kiro `requirements.md` | GEDD from annotations | Kiro, product, engineering | Turns observed failure modes into EARS acceptance criteria |
| LLM-as-a-Judge prompt | GEDD from annotations | CI, eval owner, release owner | Turns the same failure modes into an automated release gate |

Golden queries, human labels, failure codes, memos, and severity are inputs. They exist to make those two outputs precise, traceable, and testable.

GEDD is not a generic model leaderboard. It is a way to preserve expert judgment and make it executable.

## Quick Start

Start the web app:

```bash
cd grounded-evals
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
grounded-evals serve --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080`.

No Codex skill or plugin is required.

Local runs start in guest mode unless `ADMIN_PASSWORD` or Cognito environment variables are configured. If port `8080` is busy, use `--port 8081`.

For the product workflow:

1. Open `Coach`.
2. Define the agent, users, task boundary, system prompt, and test-case plan.
3. Continue to `Annotations` to capture verdicts, failure codes, severity, confidence, and memos.
4. Open `Kiro requirements.md` to inspect or download the generated domain spec.
5. Open `LLM Judge` or `Outputs` to inspect or download the judge prompt.

To reset a project, use the top-right refresh action. Confirm `Start Fresh` to clear loaded project data while keeping the current login session.

## Current Web App

`grounded-evals serve` runs a NiceGUI app with a short primary navigation:

| Page | Purpose | Main actions |
|---|---|---|
| `Coach` | Product front door | Define the agent, generate test cases, guide SME error analysis, and route to the two outputs |
| `Error Analysis` | Evidence view | Continue active work and inspect query/response evidence |
| `Annotations` | Annotation surface | Review responses, assign verdicts, create failure codes, set severity, write memos, and monitor saturation |
| `Kiro requirements.md` | Domain driven spec output | Generate Kiro-ready `requirements.md` from observed failure evidence |
| `LLM Judge` | Judge output | Generate and edit an LLM-as-a-Judge prompt from the observed failure modes |
| `Outputs` | Download surface | Download `requirements.md` and the LLM Judge prompt |

Reference demos remain available at `/demos`. They are not the product workflow; they are seed sessions for teams that want example evidence before bringing their own traces.

## Reference Demo: 50-Query Localization

This reference seed is a synthetic but complete localization QA session for an AAA game agent called `LocaleGate`.

It includes:

| Asset | Contents |
|---|---|
| 50 golden queries | Runtime strings, storefront copy, subtitles, RTL input prompts, region rules, culturalization, paid-currency copy, live-event dates, and glossary consistency |
| Synthetic responses | Baseline agent answers with realistic localization failures |
| PM annotations | Correct, partial, and incorrect verdicts with severity and confidence |
| Open codes | Localization-specific failure labels rather than generic quality tags |
| Axial coding | Root causes, context, intervening conditions, action strategy, and consequence mapping |
| Saturation evidence | Final-window evidence that new annotations repeat existing codes |
| Kiro `requirements.md` | EARS requirements generated from the localization failure modes |
| LLM Judge | A release-gate judge built from the same localization failure modes |

Example failure codes in the reference seed include:

| Code | What it catches |
|---|---|
| Placeholder And Markup Corruption | The response approves a translation that drops variables, tags, markup, or runtime-safe formatting |
| Gameplay Meaning Reversal | The localized text reverses the gameplay instruction or player action |
| Rating Or Disclosure Softening | Marketing or regional copy weakens required rating, privacy, paid-currency, or platform disclosures |
| RTL Input Direction Drift | Right-to-left layout or controller input language changes the intended interaction |
| Locale Format Ambiguity | Dates, times, numbers, or currencies remain ambiguous for the target locale |
| Entitlement Copy Mistranslation | Storefront text changes what the buyer receives or what content is included |
| Culturalization Risk Dismissal | The response treats regional content risk as a translation-only issue |

Those labels are the point of the workflow. The judge is not asked to score generic helpfulness first. It is asked to enforce the domain owner's observed release blockers.

## Reference Demo: 50-Query AWS Cloud GDPR

This reference seed is a synthetic AWS cloud GDPR audit session for `CloudAuditGate`.

It includes 50 golden queries covering S3 and CloudWatch retention, CloudTrail and centralized logging, Bedrock prompt reuse, Rekognition and high-risk review, DSAR and deletion handling across backups and data lakes, shared responsibility, cross-region transfers, and breach escalation from AWS security incidents. The outputs are the same as the localization seed: Kiro `requirements.md` and an audit-ready LLM Judge prompt.

The AWS Cloud GDPR seed uses plain-language tags on purpose, for example `Data Used For The Wrong Job`, `Collecting Or Keeping Too Much Data`, `EU Data Moved The Wrong Way`, and `Trying To Work Around GDPR`. The point is to make the GEDD loop easy to follow: annotate the failure in human language first, then turn that observed pattern into the judge gate.

## Bring Your Own Agent

Use the app when you have a real or proposed agent and need review evidence before you automate evaluation.

| Step | What to do | Output |
|---|---|---|
| 1. Define | Describe the agent, user, task boundary, and system prompt in `Coach` | Agent spec and prompt |
| 2. Build queries | Generate or paste golden queries that cover normal, edge, ambiguous, adversarial, multi-turn, and recovery cases | Query set |
| 3. Get responses | Run the saved prompt against Bedrock, Anthropic, or a configured runtime, or paste existing traces | Response queue |
| 4. Annotate | Review each response in `Annotations` and capture verdict, code, severity, confidence, and memo | Human labels and codebook |
| 5. Pattern | Use open coding and axial coding to group repeated failures and root causes | Release-risk model |
| 6. Specs | Generate Kiro-ready requirements with EARS acceptance criteria and judge gates | `requirements.md` |
| 7. Judge | Generate the LLM-as-a-Judge prompt from the same failure modes | Judge prompt |

If you already have production traces, use the app as an annotation surface rather than generating new responses. See [Paste In Traces](grounded-evals/docs/paste-in-traces.md).

## Outputs

The Outputs page is intentionally narrow:

| Output | File | Source |
|---|---|---|
| Domain driven spec | `requirements.md` | Error analysis, annotations, failure codebook, severity, and memos |
| LLM-as-a-Judge | `judge_prompt.txt` or `<agent>_judge_prompt.md` | The same annotated failure modes and release gates |

## GEDD Power for Kiro

The repository includes a **Kiro Power** (`power-gedd/`) that converts GEDD annotations directly into structured engineering specs inside Kiro.

### What it does

The Power packages the GEDD methodology into an on-demand workflow. When activated, it guides domain experts from error analysis to a complete Kiro spec:

```
Agent Failures → Annotate → Codebook → requirements.md + LLM Judge
```

| GEDD Artifact | Becomes | Output |
|---------------|---------|--------|
| Failure codes + severity | User stories + acceptance criteria | requirements.md |
| Golden queries + annotations | Verification test cases | requirements.md |
| Judge output contract | Release-blocking criteria | LLM Judge prompt |
| Memos and release gates | Judge rules and rationale | LLM Judge prompt |

### Install

In Kiro: **Powers panel → Add Custom Power → Import from folder** → select `power-gedd/`.

The Power activates automatically when you mention keywords like "annotation", "failure codes", "error analysis", "codebook", or "agent evaluation".

### Usage

Two entry points:

1. **Import existing session** — Load a `session.json` exported from the GEDD web app or CLI. The Power validates completeness and generates specs from the evidence.

2. **Start fresh** — The Power guides you through: define agent → build golden queries → annotate responses → discover patterns → generate specs.

### Quick test

```
You: "I want to analyze my agent's failure patterns and create requirements"
Kiro: [activates GEDD Power, checks for session.json, walks through pipeline]
```

### Power structure

```
power-gedd/
├── POWER.md                         # Lifecycle metadata, onboarding, steering
└── steering/
    ├── annotation-workflow.md       # Guide annotation from scratch
    ├── session-import.md            # Import error-analysis.md
    ├── pattern-discovery.md         # Open coding → axial coding
    ├── requirements-generation.md   # EARS requirements (baseline + evidence-backed)
    └── judge-generation.md          # Failure modes → LLM Judge
```

The Power uses **EARS notation** (Easy Approach to Requirements Syntax, Mavin et al. 2009) — the same constrained natural language format used by Kiro's spec-driven development. Failure codes map to EARS Unwanted Behaviour patterns; paradigm model conditions map to State-driven patterns; golden queries map to Event-driven patterns.

For the full story behind the Power, see [blog-gedd-power.md](blog-gedd-power.md).

## License And Security

License: MIT-0. See [LICENSE](LICENSE).

Security issue reporting: see [CONTRIBUTING.md](CONTRIBUTING.md#security-issue-notifications).
