# GEDD — A Systematic Evidence Driven LLM As a Judge + SPEC Framework for Continuous Learning

[![CI](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml/badge.svg)](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT-0](https://img.shields.io/badge/License-MIT--0-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/aws-samples/sample-GEDD?style=social)](https://github.com/aws-samples/sample-GEDD/stargazers)

GEDD is a systematic evidence-driven framework that combines **LLM-as-a-Judge evaluation** with **structured SPEC generation** in a continuous learning lifecycle for AI agents.

Kiro generates baseline specs. The agent runs. Domain experts annotate what goes wrong. GEDD converts those observations into an executable judge *and* improved engineering specs — then the cycle repeats.

```
① Baseline Specs → ② Agent Runs → ③ Expert Annotates → ④ Judge + Improved Specs → ⑤ Next Iteration
```

The web app gives product managers, domain experts, and ML engineers one shared path:

1. Define the agent and the work it is supposed to do.
2. Collect or load representative queries and responses.
3. Review the responses in a task-shaped workbench.
4. Name failures in the domain owner's vocabulary.
5. Convert the observed failures into an LLM-as-a-judge prompt.
6. Export improved specs and a validated handoff for CI, MLflow, and model regression work.

The current first-run experience ships with two 50-query PM workbench demos: an AAA game localization session and an AWS cloud GDPR auditor session. They show how a domain owner can move from raw agent traces to open codes, root-cause patterns, saturation evidence, a judge prompt, and an ML engineer implementation queue.

![GEDD PM annotation walkthrough](grounded-evals/docs/GEDD_optimized.gif)

The longer methodology essay is in [METHODOLOGY.md](METHODOLOGY.md). This README is the practical product and engineering guide.

## What GEDD Produces

| Output | Who creates it | Who uses it | Why it matters |
|---|---|---|---|
| Golden queries | PM or domain expert | ML engineer, eval owner | Defines the user situations the agent must handle |
| Human labels | PM or domain expert | Judge builder, release owner | Separates acceptable, partial, and failing behavior |
| Failure codebook | PM or domain expert | ML engineer, prompt owner | Names the exact domain-specific failure modes to fix |
| Memos and severity | PM or domain expert | ML engineer, reviewer | Explains why the failure matters and how bad it is |
| Axial coding | PM or domain expert | Product and engineering leads | Groups repeated failures into root causes and consequences |
| Judge prompt | PM plus ML engineer | CI and model evaluation | Converts observed failures into automated review criteria |
| `session.json` handoff | App or CLI | ML engineer | Carries agent spec, prompt, queries, labels, and validation state |
| MLflow artifacts | ML engineer | Release pipeline | Tracks datasets, judges, evaluation runs, and regression gates |

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

For the fastest product tour, use one of the seeded 50-query demos. They do not require model calls:

1. Open `Home` or `Demos`.
2. Click `Load 50-query localization demo` or `Load 50-query AWS Cloud GDPR demo`.
3. Open `PM Workbench` to review the labeled traces, failure codes, memos, and saturation state.
4. Open `Judge` to inspect or revise the generated judge prompt.
5. Open `Report` to review release readiness and download the ML engineer handoff.

To reset after loading a demo, use the top-right refresh action. Confirm `Start Fresh` to clear the loaded project data while keeping the current login session.

## Current Web App

`grounded-evals serve` runs a NiceGUI app with a short primary navigation:

| Page | Purpose | Main actions |
|---|---|---|
| `Home` | Entry point | Load the 50-query localization or AWS Cloud GDPR demo, continue active work, or start a custom agent |
| `AI PM Coach` | Guided setup | Capture agent definition, system prompt, runtime choice, and golden-query plan |
| `PM Workbench` | Annotation surface | Review responses, assign verdicts, create failure codes, set severity, write memos, and monitor saturation |
| `Judge` | Release gate builder | Generate and edit an LLM-as-a-judge prompt from the observed failure modes |
| `Report` | Engineering handoff | Review quality signals, CI gates, artifact readiness, implementation queue, and export files |

The Demos page remains available for starter data. It is not the main workflow. Demos are seed sessions that help teams understand the annotation loop before they bring their own traces.

## The 50-Query Localization Demo

The main demo is a synthetic but complete localization QA session for an AAA game agent called `LocaleGate`.

It includes:

| Asset | Contents |
|---|---|
| 50 golden queries | Runtime strings, storefront copy, subtitles, RTL input prompts, region rules, culturalization, paid-currency copy, live-event dates, and glossary consistency |
| Synthetic responses | Baseline agent answers with realistic localization failures |
| PM annotations | Correct, partial, and incorrect verdicts with severity and confidence |
| Open codes | Localization-specific failure labels rather than generic quality tags |
| Axial coding | Root causes, context, intervening conditions, action strategy, and consequence mapping |
| Saturation evidence | Final-window evidence that new annotations repeat existing codes |
| Judge prompt | A release-gate judge built from the localization failure modes |
| Report handoff | CI gates, artifact status, implementation queue, and commands for an ML engineer |

Example failure codes in the demo include:

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

## The 50-Query AWS Cloud GDPR Demo

The second main workbench demo is a synthetic AWS cloud GDPR audit session for `CloudAuditGate`.

It includes 50 golden queries covering S3 and CloudWatch retention, CloudTrail and centralized logging, Bedrock prompt reuse, Rekognition and high-risk review, DSAR and deletion handling across backups and data lakes, shared responsibility, cross-region transfers, and breach escalation from AWS security incidents. The output is the same PM-owned package as the localization demo: annotations, open codes, axial coding, saturation evidence, and an audit-ready judge prompt.

The AWS Cloud GDPR demo uses plain-language tags on purpose, for example `Data Used For The Wrong Job`, `Collecting Or Keeping Too Much Data`, `EU Data Moved The Wrong Way`, and `Trying To Work Around GDPR`. The point is to make the GEDD loop easy to follow: annotate the failure in human language first, then turn that observed pattern into the judge gate.

## Bring Your Own Agent

Use the app when you have a real or proposed agent and need review evidence before you automate evaluation.

| Step | What to do | Output |
|---|---|---|
| 1. Define | Describe the agent, user, task boundary, and system prompt in `AI PM Coach` | Agent spec and prompt |
| 2. Build queries | Generate or paste golden queries that cover normal, edge, ambiguous, adversarial, multi-turn, and recovery cases | Query set |
| 3. Get responses | Run the saved prompt against Bedrock, Anthropic, or a configured runtime, or paste existing traces | Response queue |
| 4. Annotate | Review each response in `PM Workbench` and capture verdict, code, severity, confidence, and memo | Human labels and codebook |
| 5. Pattern | Use open coding and axial coding to group repeated failures and root causes | Release-risk model |
| 6. Judge | Build the judge prompt from the observed codes and examples | LLM-as-a-judge prompt |
| 7. Handoff | Export the session and ML handoff from `Report` | Engineering package |

If you already have production traces, use the app as an annotation surface rather than generating new responses. See [Paste In Traces](grounded-evals/docs/paste-in-traces.md).

## ML Engineer Handoff

The Report page contains an `ML Engineer Handoff` section. It is designed to be actionable, not a narrative status update.

It gives engineering:

| Handoff field | Why it exists |
|---|---|
| Engineering status | Indicates whether the session is blocked by P0 failures, missing a judge, needs calibration, or is ready for a CI pilot |
| CI gates | Shows current and target values for P0 failures, regression pass rate, human coverage, and judge-human agreement |
| Artifact status | Confirms whether session handoff, golden dataset, codebook, judge prompt, and calibration evidence are ready |
| Implementation queue | Prioritizes failure codes by severity and count, with tagged examples and definitions of done |
| Runbook | Gives commands the ML engineer can run immediately |

## GEDD Power for Kiro

The repository includes a **Kiro Power** (`power-gedd/`) that implements a continuous learning lifecycle for agent specs. Kiro generates baseline requirements; domain experts annotate what goes wrong; GEDD upgrades the specs with evidence.

### What it does

The Power turns the gap between "what we assumed" and "what we observed" into better engineering specs — every iteration:

```
① Kiro Baseline → ② Agent Runs → ③ Expert Annotates → ④ GEDD Processes → ⑤ Improved Specs
      ↑                                                                          │
      └──────────────────────── next iteration ←─────────────────────────────────┘
```

| Phase | Input | Output |
|-------|-------|--------|
| Baseline | Agent description + system prompt | `requirements.md` v1 (assumed) |
| Annotate | Agent responses + domain expertise | `error-analysis.md` (observed) |
| Improve | Baseline + annotations + paradigm model | `requirements.md` v2+ (evidence-backed) |

| Spec Element | Baseline | After Annotations |
|-------------|----------|-------------------|
| User stories | Generic capabilities | Grounded in observed failures |
| Acceptance criteria | Assumed from system prompt | Actual failed responses as negative tests |
| Priority ordering | Engineer's guess | severity × frequency × dimension_weight |
| Verification | Unit tests | Golden queries + LLM judge (κ ≥ 0.80) |

### Install

In Kiro: **Powers panel → Add Custom Power → Import from folder** → select `power-gedd/`.

The Power activates automatically when you mention keywords like "annotation", "failure codes", "error analysis", "codebook", "requirements", or "agent evaluation".

### Usage

Three entry points depending on where you are in the lifecycle:

1. **Generate baseline** — No annotations yet. Kiro generates initial requirements from the agent spec. These are marked as unvalidated.

2. **Import annotations** — Load an `error-analysis.md` exported from the GEDD web app (Report → "Error Analysis (MD)") or CLI (`grounded-evals export-md`). The Power compares against existing specs and upgrades them.

3. **Start fresh** — No agent spec, no annotations. The Power guides you through the full cycle: define agent → build golden queries → annotate → discover patterns → generate specs.

### Quick test

```
You: "I have an error-analysis.md from my domain expert — upgrade my requirements"
Kiro: [activates GEDD Power, loads annotations, compares to baseline, generates improved specs]
```

Or:

```
You: "Generate baseline requirements for my travel booking agent"
Kiro: [generates v1 specs from agent description, marks them as needing validation]
```

### Power structure

```
power-gedd/
├── POWER.md                         # Lifecycle metadata, onboarding, steering
└── steering/
    ├── annotation-workflow.md       # Guide annotation from scratch
    ├── session-import.md            # Import error-analysis.md
    ├── pattern-discovery.md         # Open coding → axial coding
    ├── requirements-generation.md   # Baseline OR evidence-backed upgrade
    ├── design-generation.md         # Paradigm models → design.md
    └── tasks-generation.md          # Priority queue → tasks.md
```

For the full story behind the Power, see [blog-gedd-power.md](blog-gedd-power.md).

## License And Security

License: MIT-0. See [LICENSE](LICENSE).

Security issue reporting: see [CONTRIBUTING.md](CONTRIBUTING.md#security-issue-notifications).
