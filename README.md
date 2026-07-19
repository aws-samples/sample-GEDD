# GEDD

Grounded Evidence Driven Development for systematic LLM-as-Judge curation.

[![CI](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml/badge.svg)](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT-0](https://img.shields.io/badge/License-MIT--0-green.svg)](LICENSE)

GEDD helps domain experts, SMEs, and product managers curate the evidence needed to build a domain-specific LLM-as-Judge. It turns baseline agent behavior into a guardrail calibration set, a structured judge spec, a reusable judge prompt, and a measurable response gate.

The core idea is simple: the judge should come from grounded evidence, not generic assumptions. Domain owners define the query set, review baseline responses, name the failure modes, and decide which failures should block customer-facing answers.

```text
Domain context
  -> curated query set
  -> baseline responses
  -> SME annotations
  -> failure codebook
  -> guardrail calibration scenarios
  -> systematic LLM-as-Judge
  -> response gate before customers see answers
```

![GEDD Coach and annotation workflow](grounded-evals/docs/GEDD_optimized.gif)

## What GEDD Produces

| Artifact | Purpose |
|---|---|
| `SME_error_analysis.md` | Evidence handoff with domain context, query coverage, baseline responses, annotations, failure codes, memos, and traceability |
| Guardrail calibration set | Scenario rows with conversation turns, input/output side, expected pass/fail or tier, category labels, SME rationale, and corrective feedback |
| Judge spec | A structured description of what the LLM-as-Judge must detect, block, escalate, and explain |
| LLM-as-Judge prompt | A domain-specific judge prompt grounded in SME-defined failure modes |
| Response gate | A pass/fail decision contract that runs before an answer becomes customer-visible |
| Measurement report | A before/after quality view across specificity, traceability, testability, domain coverage, and response accuracy |

GEDD is not a model leaderboard. It is the evidence pipeline for building a judge that understands a specific domain.

## Workflow

Coach guides the SME through six steps:

| Step | What happens | Output |
|---|---|---|
| 1. Define the domain | Capture users, risks, constraints, permissions, vocabulary, and known edge cases | Domain expert profile |
| 2. Capture baseline evidence | Upload, paste, or describe the current agent behavior contract, prompt, policy, or traces | Baseline context |
| 3. Curate queries | Build happy path, edge, adversarial, ambiguous, recovery, persona, and red-flag prompts | SME-owned query set |
| 4. Test the baseline | Run or paste baseline responses for the curated queries | Response evidence |
| 5. Annotate failures | Label verdicts, failure codes, severity, confidence, missing rules, and memos | Failure codebook |
| 6. Generate the judge | Produce the evidence handoff, judge spec, LLM-as-Judge prompt, and measurement | Systematic judge package |

The result is a judge that reflects observed behavior and SME judgment. A fluent answer can still fail if it violates the domain evidence.

## Guardrail Calibration Pattern

GEDD is inspired by framework-agnostic guardrail evaluation datasets: simple scenario files that make safety and quality expectations explicit enough to run as regression tests.

In GEDD, a useful scenario has:

- Conversation turns for the user request and, when evaluating outputs, the candidate assistant response
- An evaluation side: input guardrail, output guardrail, or response gate
- An expected result or tier such as allow, continue with resources, block, or human review
- Domain category labels for per-category coverage analysis
- SME rationale explaining why the scenario should pass or fail
- Corrective feedback or an example safer response when the baseline fails

The same scenario set can calibrate a judge, run regression tests on every model or prompt change, and expose category coverage gaps. It is still only a starting point: GEDD expects SME review, production annotation, red-teaming, and ongoing calibration before a judge becomes a blocking gate.

## Quick Start

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

Local runs start in guest mode unless you configure `ADMIN_PASSWORD` or Cognito. If port `8080` is busy, use `--port 8081`.

For full environment setup, Bedrock or Anthropic configuration, AWS deployment, and troubleshooting, use [SETUP.md](SETUP.md).

## App Surfaces

| Route | UI label | Purpose |
|---|---|---|
| `/` | Home | Product entry point |
| `/coach` | Coach | Guided evidence curation workflow |
| `/aaa-game-localization-demo` | AAA Game Localization | An anonymized localization scenario showing the full evidence-to-judge flow |
| `/coding` | Annotations | SME verdicts, failure codes, severity, confidence, and memos |
| `/report` | Evidence | Export and inspect `SME_error_analysis.md` |
| `/requirements` | Judge Spec | Generate the structured judge specification |
| `/judge` | Judge | Generate the LLM-as-Judge response gate |
| `/improvement` | Measurement | Compare baseline and GEDD-generated judge quality |
| `/demos` | Reference seeds | Load example evidence sessions |

The core path is Coach. Other pages appear when enough evidence exists for them.

## Example Scenario

The first-class demo is an anonymized AAA Game Localization Agent.

It shows how a localization SME turns LQA evidence into judge gates for:

- Franchise terminology and lore glossary drift
- Runtime placeholders, tags, controller glyphs, and choice-state markup
- Subtitle meaning, timing, and VO/text parity
- RTL layout and input direction issues
- Storefront, rating, product-scope, and regional compliance copy
- Character voice and canon-role flattening

The demo produces the same artifacts as a real project: `SME_error_analysis.md`, judge spec, LLM-as-Judge prompt, response gate, and measurement report.

## Bring Your Own Agent

Use GEDD when you have a customer-facing assistant and need a grounded judge for its responses.

You can start from:

- A system prompt or product brief
- A policy, rubric, SOP, or current behavior contract
- A set of production or synthetic traces
- A SME-owned golden query set
- A demo seed adapted to your domain

If you already have traces, paste or import them and use GEDD as an annotation and judge-generation surface. See [Paste In Traces](grounded-evals/docs/paste-in-traces.md).

## Judge Gate Contract

GEDD-generated judges are expected to return a structured gate decision before an answer becomes customer-visible:

```json
{
  "pass_fail": "pass | fail",
  "failure_code": "domain failure label or null",
  "severity": "low | medium | high | critical | catastrophic",
  "rationale": "why the response passes or fails",
  "evidence_references": ["query id", "failure code", "judge criterion"],
  "recommended_action": "allow | revise_response | request_human_review",
  "customer_visible_block": true
}
```

The judge should prioritize SME-defined failure modes over generic helpfulness. It should explain what evidence drove the decision and whether a customer-visible response should be blocked.

## Development

Run the test suite:

```bash
cd grounded-evals
python3 -m pytest tests
```

Compile-check the app:

```bash
cd grounded-evals
python3 -m compileall src
```

Deploy the UI after AWS infrastructure is configured:

```bash
cd grounded-evals
./scripts/deploy-ui.sh
```

Local authentication behavior:

| Configuration | Behavior |
|---|---|
| No `ADMIN_PASSWORD`, no Cognito | Guest mode for local development |
| `ADMIN_PASSWORD` set | Simple password login |
| Cognito environment variables set | Cognito OAuth flow for protected routes |

See [SETUP.md](SETUP.md) for AWS, Bedrock, Cognito, AgentCore, and deployment details.

## Repository Layout

```text
.
|-- grounded-evals/          # Python package, NiceGUI app, CLI, tests, infra scripts
|-- METHODOLOGY.md           # Grounded-theory and evaluation methodology
|-- SETUP.md                 # Engineering setup and deployment guide
`-- README.md                # Product and contributor entry point
```

Key app modules:

```text
grounded-evals/src/grounded_evals/
|-- agent/                   # Coach prompt and agent turn handling
|-- ears/                    # EARS-style judge spec generation and measurement
|-- guide/                   # Session model, markdown export, session I/O
|-- judge_builder/           # Judge prompt and rubric generation
|-- open_coding/             # Failure-code discovery helpers
|-- axial_coding/            # Pattern and root-cause mapping
`-- ui/                      # NiceGUI pages and demo datasets
```

## More Detail

- [SETUP.md](SETUP.md): local setup, model provider configuration, auth, AWS deployment, troubleshooting
- [METHODOLOGY.md](METHODOLOGY.md): grounded theory, coding workflow, judge spec generation, judge calibration
- [CONTRIBUTING.md](CONTRIBUTING.md): contribution and security reporting guidance

## License

MIT-0. See [LICENSE](LICENSE).
