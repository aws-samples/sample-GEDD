# GEDD Project Structure Reference

## Directory Map

```
sample-GEDD/
├── grounded-evals/                    # Main Python package
│   ├── src/grounded_evals/            # Source code
│   │   ├── __init__.py                # Package initialization
│   │   ├── __pycache__/               # Python bytecode cache
│   │   ├── app.py                     # FastAPI app with NiceGUI pages
│   │   ├── cli.py                     # Click CLI entry point
│   │   ├── agentcore_client.py        # AgentCore integration
│   │   ├── harness_client.py          # Test harness integration
│   │   ├── feedback_loop.py           # Feedback loop orchestration
│   │   │
│   │   ├── agent/                     # Agent annotation loop
│   │   │   ├── __init__.py
│   │   │   ├── handler.py             # run_agent_turn() — main turn loop
│   │   │   ├── prompt.py              # SYSTEM_PROMPT, get_state_block()
│   │   │   ├── tools.py               # Tool definitions, StateBundle, handle_tool_call()
│   │   │   └── __pycache__/
│   │   │
│   │   ├── axial_coding/              # Root cause & consequence mapping
│   │   │   ├── __init__.py
│   │   │   ├── mapper.py              # map_errors_to_categories(), ErrorMapping
│   │   │   ├── paradigm.py            # build_paradigm_model()
│   │   │   └── __pycache__/
│   │   │
│   │   ├── guide/                     # Session & workflow state
│   │   │   ├── __init__.py
│   │   │   ├── session.py             # Session class — load/save/mutate
│   │   │   └── __pycache__/
│   │   │
│   │   ├── ingest/                    # Data import utilities
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/
│   │   │   └── (import functions)
│   │   │
│   │   ├── judge_builder/             # Judge creation & evaluation
│   │   │   ├── __init__.py
│   │   │   ├── active_learning.py     # Recommend next prompts
│   │   │   ├── calibrate.py           # Judge vs. human calibration
│   │   │   ├── constitutional.py      # Constitutional AI judge
│   │   │   ├── ensemble.py            # Multiple judges, aggregate results
│   │   │   ├── few_shot.py            # Few-shot exemplar selection
│   │   │   ├── prompt_gen.py          # Rubric → judge prompt
│   │   │   ├── rubric.py              # Error mappings → rubric
│   │   │   └── __pycache__/
│   │   │
│   │   ├── llm/                       # LLM client abstraction
│   │   │   ├── __init__.py
│   │   │   ├── client.py              # get_default_client(), get_model_id(), traced_coach_call()
│   │   │   ├── config.py              # LLM configuration
│   │   │   └── __pycache__/
│   │   │
│   │   ├── models/                    # Pydantic domain models
│   │   │   ├── __init__.py
│   │   │   ├── core.py                # Code, Category, Memo, GoldenPrompt, etc.
│   │   │   └── __pycache__/
│   │   │
│   │   ├── open_coding/               # Failure pattern discovery
│   │   │   ├── __init__.py
│   │   │   ├── saturation.py          # Saturation analysis
│   │   │   ├── fracture.py            # Initial category generation
│   │   │   ├── compare.py             # Code comparison & merging
│   │   │   └── __pycache__/
│   │   │
│   │   └── ui/                        # NiceGUI web interface
│   │       ├── __init__.py
│   │       ├── __pycache__/
│   │       ├── app.py                 # App initialization
│   │       ├── layout.py              # Shared layout & styling
│   │       ├── theme.py               # CSS theming
│   │       │
│   │       ├── *_page.py              # Page handlers (one per page)
│   │       │   ├── home_page.py
│   │       │   ├── eval_page.py       # Run agent, collect responses
│   │       │   ├── coding_page.py     # PM annotation workbench
│   │       │   ├── judge_builder_page.py
│   │       │   ├── report_page.py
│   │       │   ├── analysis_page.py
│   │       │   ├── demos_page.py
│   │       │   ├── inductive_pm_demo.py (deprecated demo)
│   │       │   ├── gdpr_auditor_demo.py
│   │       │   ├── game_release_demos.py
│   │       │   ├── support_bot_demo.py
│   │       │   ├── new_domain_demos.py
│   │       │   └── domain_demos.py
│   │       │
│   │       ├── steps/                 # Reusable workflow components
│   │       │   ├── __init__.py
│   │       │   ├── define_agent.py
│   │       │   ├── system_prompt.py
│   │       │   ├── ingestion_step.py
│   │       │   ├── judge_builder_step.py
│   │       │   ├── evaluation_step.py
│   │       │   └── __pycache__/
│   │       │
│   │       ├── demo_data.py           # Shared demo data
│   │       ├── eval_tab.py            # Evaluation results UI
│   │       ├── journey_map.py         # Workflow visualization
│   │       └── *_demo.py              # Demo session data
│   │
│   ├── tests/                         # pytest test suite
│   │   ├── __init__.py
│   │   ├── __pycache__/
│   │   ├── test_*.py                  # Test files (one per module)
│   │   │   ├── test_active_learning.py
│   │   │   ├── test_axial_coding.py
│   │   │   ├── test_cli.py
│   │   │   ├── test_constitutional.py
│   │   │   ├── test_edge_cases.py
│   │   │   ├── test_ensemble.py
│   │   │   ├── test_few_shot.py
│   │   │   ├── test_guide_session.py
│   │   │   ├── test_ingest.py
│   │   │   ├── test_integration.py
│   │   │   ├── test_judge_builder.py
│   │   │   ├── test_llm_config.py
│   │   │   ├── test_models_core.py
│   │   │   ├── test_open_coding_extended.py
│   │   │   ├── test_open_coding.py
│   │   │   ├── test_prompt_gen.py
│   │   │   └── test_ui_logic.py
│   │   └── conftest.py                # pytest configuration & fixtures (if exists)
│   │
│   ├── infra/                         # AWS CDK infrastructure
│   │   ├── __pycache__/
│   │   ├── .venv/                     # Virtual env for CDK
│   │   ├── app.py                     # CDK App entry point
│   │   ├── cdk.json                   # CDK context values
│   │   ├── requirements.txt           # CDK dependencies
│   │   ├── cdk.out/                   # CDK synthesis output
│   │   └── stacks/                    # CDK stack definitions
│   │       ├── __init__.py
│   │       ├── __pycache__/
│   │       ├── agentcore_stack.py     # AgentCore service integration
│   │       ├── cognito_stack.py       # Cognito authentication
│   │       ├── ecr_stack.py           # ECR container registry
│   │       ├── ecs_stack.py           # ECS Fargate cluster
│   │       └── network_stack.py       # VPC, ALB, CloudFront
│   │
│   ├── scripts/                       # Utility scripts
│   │   └── (build/deploy scripts)
│   │
│   ├── data/                          # Seed data
│   │   ├── demos/                     # 50-query demo datasets
│   │   │   ├── localization_50.json
│   │   │   └── gdpr_auditor_50.json
│   │   └── templates/                 # Config templates
│   │
│   ├── docs/                          # Documentation
│   │   ├── README.md                  # GEDD documentation
│   │   ├── paste-in-traces.md         # Importing existing traces
│   │   ├── GEDD_optimized.gif         # Demo walkthrough animation
│   │   └── (other docs)
│   │
│   ├── configs/                       # Configuration files
│   │   ├── llm_config.yaml            # LLM model selection
│   │   └── agent_config.yaml
│   │
│   ├── agentcore/                     # AgentCore agent impl (optional)
│   │   └── (agent tools & handlers)
│   │
│   ├── agentcore-deploy/              # AgentCore deployment
│   │   └── (deployment configs)
│   │
│   ├── .claude/                       # Claude/Kiro config
│   │   ├── settings.local.json
│   │   └── commands/                  # Custom Kiro commands
│   │       ├── gedd.md
│   │       ├── gedd-chat.md
│   │       └── gedd-status.md
│   │
│   ├── .mypy_cache/                   # mypy cache
│   ├── .nicegui/                      # NiceGUI user storage
│   ├── .pytest_cache/                 # pytest cache
│   ├── .ruff_cache/                   # ruff cache
│   ├── .venv/                         # Python virtual environment
│   ├── .dockerignore
│   ├── .gitignore
│   ├── Dockerfile                     # Docker build image
│   ├── CLAUDE.md                      # Kiro project guide
│   ├── pyproject.toml                 # Python project config (deps, tools)
│   └── ~ .pptx files                  # Presentation files (local only)
│
├── node_modules/                      # NPM packages (if any)
├── outputs/                           # CLI output directory (generated)
├── .agents/                           # Agent definitions
├── .claude/                           # Parent Claude/Kiro config
│   └── settings.local.json
├── .github/                           # GitHub config
│   ├── workflows/
│   │   └── ci.yml                     # Continuous integration
│   ├── CODEOWNERS                     # Code ownership rules
│   ├── SECURITY.md                    # Security policy
│   ├── dependabot.yml                 # Dependency updates
│   └── pull_request_template.md
├── .nicegui/                          # NiceGUI parent storage
├── .git/                              # Git repository
├── .gitignore                         # Root .gitignore
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE                            # MIT-0 license
├── METHODOLOGY.md                     # Grounded theory methodology
├── README.md                          # Main README
├── SETUP.md                           # Setup instructions
├── conference-talk.md                 # Conference presentation notes
└── package.json                       # NPM config (if any)
```

## Key Files Reference

### Configuration
- `pyproject.toml`: Python dependencies, linting, type checking, test config
- `infra/cdk.json`: AWS CDK context values
- `.github/workflows/ci.yml`: GitHub Actions CI/CD
- `Dockerfile`: Container image for deployment

### Entry Points
- `cli.py`: Command-line interface (Click)
- `app.py`: Web interface (FastAPI + NiceGUI)
- `infra/app.py`: CDK App for AWS infrastructure

### Core Logic Modules
- `models/core.py`: All domain entities (one file, ~200 lines each)
- `open_coding/fracture.py`: Category generation via LLM
- `open_coding/saturation.py`: Coverage analysis
- `axial_coding/mapper.py`: Error → category mapping
- `axial_coding/paradigm.py`: Paradigm model construction
- `judge_builder/rubric.py`: Rubric generation
- `judge_builder/prompt_gen.py`: Judge prompt rendering
- `judge_builder/calibrate.py`: Judge vs. human calibration
- `judge_builder/ensemble.py`: Multiple judge aggregation

### UI Pages
All in `ui/*_page.py`, decorated with `@ui.page()`:
- `/`: Home page (entry point, demo loader)
- `/coach`: AI PM Coach (agent definition)
- `/eval`: Evaluation (run agent, collect responses)
- `/coding`: PM Workbench (annotation)
- `/judge`: Judge Builder (prompt generation)
- `/report`: Report (quality signals, ML handoff)
- `/analysis`: Analysis (saturation, coverage)
- `/demos`: Demo gallery (load 50-query demos)

### Testing
- `tests/test_*.py`: One test file per source module
- Test patterns: use `_make_*()` helpers, mock LLM with `monkeypatch`
- Run: `pytest` (all), `pytest tests/test_foo.py` (single file)

### Data
- `data/demos/localization_50.json`: 50-query game localization demo
- `data/demos/gdpr_auditor_50.json`: 50-query AWS GDPR audit demo
- Both include queries, responses, annotations, codes, and paradigm model

## File Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Module | lowercase_with_underscores.py | `open_coding.py` |
| Package | lowercase | `open_coding/` |
| Page handler | `*_page.py` | `home_page.py` |
| Test | `test_<module>.py` | `test_open_coding.py` |
| CDK Stack | `*_stack.py` | `ecs_stack.py` |
| Demo | `*_demo.py` | `gdpr_auditor_demo.py` |
| Class | PascalCase | `Code`, `ParadigmModel` |
| Function | snake_case | `fracture_domain()` |
| Constant | UPPER_SNAKE_CASE | `STANDARD_ERROR_CATEGORIES` |
| Private | _leading_underscore | `_load_state()` |

## Import Paths

```python
# Models (most common)
from grounded_evals.models.core import Code, Category, SaturationStatus

# Open coding
from grounded_evals.open_coding.saturation import check_overall_saturation

# Axial coding
from grounded_evals.axial_coding.mapper import map_errors_to_categories

# Judge builder
from grounded_evals.judge_builder.prompt_gen import generate_judge_prompt

# LLM
from grounded_evals.llm.client import get_default_client

# UI (from within pages)
from grounded_evals.ui.layout import page_layout

# Agent
from grounded_evals.agent import run_agent_turn, StateBundle
```

