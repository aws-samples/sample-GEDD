# GEDD Quick Reference

## Key Commands

### Development
```bash
# Install and setup
cd grounded-evals
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run web app
grounded-evals serve --host 127.0.0.1 --port 8080

# Run tests
pytest                              # all tests
pytest tests/test_open_coding.py    # single file
pytest -v                           # verbose
pytest --cov=src/grounded_evals     # with coverage

# Linting
ruff check src/
ruff check src/ --fix               # auto-fix
mypy src/                           # type check
```

### CLI Examples
```bash
# Load 50-query demo
grounded-evals chat session.json
# Choose: Load 50-query localization demo OR Load 50-query AWS Cloud GDPR demo

# Export session to JSON
grounded-evals export session.json --output report.json

# Check saturation
grounded-evals check-saturation dataset.json

# Generate judge
grounded-evals judge session.json --output judge.txt

# Run evaluation
grounded-evals run-eval session.json --output results.json

# Full ML engineer handoff
grounded-evals handoff session.json --output handoff/

# View status
grounded-evals status session.json
```

## Core Data Models

### Enums
```python
CodeType: IN_VIVO, CONSTRUCTED, PROCESS, DESCRIPTIVE, ANALYTIC
MemoType: CODE, THEORETICAL, OPERATIONAL, REFLECTIVE
SaturationStatus: UNSATURATED, APPROACHING, SATURATED
```

### Key Classes
```python
Code          # Failure label (in_vivo or constructed)
Category      # Higher-order grouping of codes
Memo          # PM annotation & rationale
GoldenPrompt  # Single query in golden dataset
GoldenDataset # Complete query + annotation set
ParadigmModel # Axial coding: phenomenon → conditions → strategies → consequences
JudgeRubric   # Scoring criteria for judge
JudgeCriterion# Single criterion in rubric
CoverageReport# Dataset quality metrics
```

## Module Quick Links

### Discovery: Open Coding
**Module**: `src/grounded_evals/open_coding/`
- `fracture_domain()` → Generate initial categories from agent spec
- `check_category_saturation()` → Check if category has enough examples (3+ = saturated)
- `check_overall_saturation()` → Analyze dataset coverage, find gaps
- `saturation_recommendation()` → Human-readable saturation report

### Analysis: Axial Coding
**Module**: `src/grounded_evals/axial_coding/`
- `map_errors_to_categories()` → Assign codes to standard dimensions (accuracy, safety, tone, etc.)
- `build_paradigm_model()` → Construct causal model (conditions → phenomenon → consequences)

### Automation: Judge Building
**Module**: `src/grounded_evals/judge_builder/`
- `generate_rubric()` → Convert error mappings → scoring rubric
- `generate_judge_prompt()` → Rubric → LLM judge prompt
- `calibrate()` → Compare judge scores vs. human labels (Cohen's kappa)
- `ensemble_judge()` → Run multiple judges, aggregate votes
- `select_exemplars()` → Choose best few-shot examples for judge prompt
- `build_constitutional_principles()` → Constitutional AI judge variant

### Workflow: Agent & Session
**Module**: `src/grounded_evals/agent/` + `src/grounded_evals/guide/`
- `run_agent_turn()` → Agent annotation loop (user message → tool calls → state mutations)
- `Session` class → Load/save session, manage state lifecycle

### Web App: UI Pages
**Module**: `src/grounded_evals/ui/`
- `home_page.py` → Entry point, progress tracking, demo loader
- `eval_page.py` → Run agent, collect responses
- `coding_page.py` → PM annotation workbench (verdict, code, severity, memo)
- `judge_builder_page.py` → Interactive judge prompt generation
- `report_page.py` → Quality signals, ML engineer handoff
- `analysis_page.py` → Saturation & coverage analysis

## Test Patterns

### Fixture Helper
```python
def _make_category(name: str = "Test") -> Category:
    return Category(name=name, definition="Test")

def test_saturation():
    cat = _make_category()
    status = check_category_saturation(cat, [])
    assert status == SaturationStatus.UNSATURATED
```

### LLM Mock
```python
def test_with_llm(monkeypatch):
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps({"data": "..."})]
    mock_client.messages.create.return_value = msg
    
    monkeypatch.setattr(
        "grounded_evals.module.get_default_client",
        lambda: mock_client
    )
    # Test code
```

## File Locations (Most Common)

| Task | File |
|------|------|
| Add domain model | `src/grounded_evals/models/core.py` |
| Add new page | `src/grounded_evals/ui/<name>_page.py` |
| Add CLI command | `src/grounded_evals/cli.py` |
| Update saturation logic | `src/grounded_evals/open_coding/saturation.py` |
| Update judge generation | `src/grounded_evals/judge_builder/prompt_gen.py` |
| Update agent loop | `src/grounded_evals/agent/handler.py` |
| Add test | `tests/test_<module>.py` |
| Update infrastructure | `infra/stacks/<component>_stack.py` |

## Workflow Paths (UI Routes)

| Path | Purpose | Key Actions |
|------|---------|-------------|
| `/` | Home | Load demo, start custom session, view progress |
| `/coach` | Define agent | Set name, description, system prompt, query plan |
| `/eval` | Collect responses | Run agent on golden queries |
| `/coding` | Annotate failures | Mark verdict, create codes, set severity |
| `/judge` | Build judge | Generate & test judge prompt |
| `/report` | Quality gates & handoff | View saturation, coverage, export for ML engineer |
| `/analysis` | Deep dive | Inspect saturation, paradigm model, exemplars |
| `/demos` | Gallery | Load 50-query localization or GDPR demo |

## Storage Keys (UI State)

```python
storage = {
    "session_data": {...},              # Agent spec, queries
    "eval_results": [...],              # Agent responses
    "coding_annotations": [...],        # PM labels (verdict, code, severity)
    "codebook": {...},                  # Category/code definitions
    "paradigm_model": {...},            # Axial coding output
    "_generated_judge_prompt": "...",   # Generated judge prompt
}
```

## Environment Variables

```bash
# LLM Configuration
ANTHROPIC_API_KEY          # Anthropic API key
AWS_REGION                 # AWS region (default: us-east-1)
BEDROCK_ENDPOINT           # Optional Bedrock endpoint

# Authentication (optional, local dev uses guest mode if unset)
ADMIN_PASSWORD             # Simple password for local dev
COGNITO_USER_POOL_ID       # Cognito user pool ID
COGNITO_CLIENT_ID          # Cognito app client ID
COGNITO_DOMAIN             # Cognito domain
PUBLIC_BASE_URL            # CloudFront domain (for OAuth callbacks)

# Observability
LANGSMITH_API_KEY          # Optional LangSmith tracing
```

## Performance Tips

1. **LLM calls are instrumented** → Check LangSmith traces for latency
2. **Session state is in-memory** → Save explicitly via CLI or /report download for persistence
3. **Batch operations** → Use simple for-loops for 50-100 item operations; no async needed
4. **UI responsiveness** → Long operations use `async/await` to avoid blocking

## Security Checklist

- ✅ Type hints enforced by mypy (strict mode)
- ✅ Input validation via Pydantic models
- ✅ No hardcoded credentials (use environment variables)
- ✅ No SQL (Pydantic models handle data)
- ✅ Authentication optional (Cognito or local password)
- ✅ Session isolation per browser client

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError` | Wrong import or PYTHONPATH | Use absolute imports, run from project root |
| mypy errors | Missing type hints | Add `: Type` annotations to all parameters/returns |
| LLM timeout | Credential or network issue | Check API key, network connectivity, timeout config |
| NiceGUI 500 error | Page handler error | Check browser console and server logs |
| Test mock not working | Import path mismatch | Ensure patch path matches `from ... import ...` statement |

## Deployment

### Local Docker
```bash
docker build -t grounded-evals:latest .
docker run -p 8080:8080 grounded-evals:latest
```

### AWS CDK
```bash
cd infra
cdk bootstrap
cdk deploy
```

### Environment at Runtime
```bash
export COGNITO_USER_POOL_ID="..."
export COGNITO_CLIENT_ID="..."
export COGNITO_DOMAIN="..."
grounded-evals serve --host 0.0.0.0 --port 8080
```

