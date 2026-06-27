---
inclusion: always
---

# GEDD Project Architecture

## What is GEDD
A Systematic Evidence-Driven LLM-as-a-Judge Framework that applies grounded theory (Strauss & Corbin) to AI agent evaluation. PMs annotate agent failures inductively, then the system converts those patterns into automated judge criteria.

## Three-Phase Workflow
1. **Open Coding** (`open_coding/`) — Fracture domain into categories, discover failure codes inductively, check saturation
2. **Axial Coding** (`axial_coding/`) — Map errors to 8 standard dimensions, build paradigm model (cause → phenomenon → consequence)
3. **Selective Coding / Judge** (`judge_builder/`) — Generate rubric, build judge prompt (standard/few-shot/G-EVAL/constitutional), calibrate against humans

## Source Layout
```
grounded-evals/src/grounded_evals/
├── app.py              # NiceGUI entry point
├── cli.py              # Click CLI
├── models/core.py      # All Pydantic domain models
├── open_coding/        # fracture.py, compare.py, saturation.py
├── axial_coding/       # mapper.py, paradigm.py
├── judge_builder/      # rubric.py, prompt_gen.py, calibrate.py, few_shot.py,
│                       # constitutional.py, ensemble.py, active_learning.py
├── agent/              # handler.py (turn loop), tools.py, prompt.py
├── ui/                 # *_page.py (NiceGUI pages), steps/, layout.py, theme.py
├── llm/client.py       # Unified Bedrock + Anthropic client
├── guide/session.py    # Session state management
└── ingest/models.py    # AgentSpec, Capability, Persona
```

## Module Dependency Order
```
models/ → (foundation, no deps)
llm/ → models
open_coding/, axial_coding/, judge_builder/ → models, llm
agent/ → models, llm, open_coding, axial_coding, judge_builder
guide/ → models, ingest
ui/ → agent, guide, open_coding, judge_builder
cli.py → orchestrates all modules
```

## Key Domain Models (models/core.py)
- `Code` — Failure label (in_vivo or constructed)
- `Category` — Higher-order grouping with saturation status
- `ParadigmModel` — Causal relationships (Strauss & Corbin)
- `Memo` — PM's documented reasoning
- `GoldenPrompt` — Test case with full provenance
- `GoldenDataset` — Complete handoff artifact
- `JudgeRubric` / `JudgeCriterion` — Scoring criteria
- `CoverageReport` — Dataset quality metrics

## UI Pages (NiceGUI)
| Route | File | Purpose |
|-------|------|---------|
| `/` | home_page.py | Entry, demo loader |
| `/coach` | app.py | Agent definition, system prompt |
| `/eval` | eval_page.py | Run agent, collect responses |
| `/coding` | coding_page.py | PM annotation workbench |
| `/judge` | judge_builder_page.py | Generate/edit judge prompt |
| `/report` | report_page.py | CI gates, ML engineer handoff |
| `/analysis` | analysis_page.py | Saturation, coverage review |

## State Management
- **Web UI**: `ui.context.client.storage` (per-session, in-memory)
- **CLI/Export**: `session.json` file (portable handoff)
- **Session class** in `guide/session.py` is the single source of truth

## LLM Client (llm/client.py)
- Default: AWS Bedrock via AnthropicBedrock (IAM credentials)
- Fallback: Direct Anthropic API when `ANTHROPIC_API_KEY` is set
- All calls traced to LangSmith when configured
- Wrappers: `traced_coach_call()`, `traced_eval_call()`, `traced_eval_batch()`

## Infrastructure (infra/)
AWS CDK stacks: Network (VPC/ALB/CloudFront) → ECR → ECS Fargate → Cognito → AgentCore
