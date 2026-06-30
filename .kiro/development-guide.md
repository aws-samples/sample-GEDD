# Development Guide for GEDD

## Getting Started

### Prerequisites
- Python 3.11+
- pip or pip-tools
- Optional: AWS credentials and Docker (for deployment)

### Setup
```bash
cd grounded-evals
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Running Locally
```bash
# Start the web app (default: http://localhost:8080)
grounded-evals serve --host 127.0.0.1 --port 8080

# Run tests
pytest

# Linting & type checking
ruff check src/
mypy src/grounded_evals/
```

## Common Development Tasks

### Adding a New Domain Model
1. Define in `src/grounded_evals/models/core.py`:
   ```python
   class MyEntity(BaseModel):
       id: UUID = Field(default_factory=uuid4)
       name: str
       # ... other fields
       created_at: datetime = Field(default_factory=datetime.now)
   ```
2. Export from `models/__init__.py`
3. Use in other modules as `from grounded_evals.models.core import MyEntity`

### Adding a New UI Page
1. Create `src/grounded_evals/ui/my_page.py`:
   ```python
   """Page description."""
   from nicegui import ui
   from grounded_evals.ui.layout import page_layout
   
   @ui.page("/my-path")
   async def my_page() -> None:
       """Page handler."""
       with page_layout():
           ui.label("Hello")
           # Page content
   ```
2. Import in `src/grounded_evals/app.py` (auto-registers route):
   ```python
   import grounded_evals.ui.my_page  # noqa: F401
   ```
3. Add to navigation in appropriate page (e.g., `home_page.py`)

### Adding a New CLI Command
1. Add function to `src/grounded_evals/cli.py`:
   ```python
   @click.command()
   @click.argument("input_path", type=click.Path(exists=True))
   @click.option("--output", "-o", type=click.Path(), help="Output path")
   def my_command(input_path: str, output: str | None) -> None:
       """Perform my operation."""
       # Implementation
       click.echo("Done!")
   ```
2. Add test in `tests/test_cli.py`
3. Document in README.md CLI section

### Adding a Test
1. Create file `tests/test_<module>.py` if needed
2. Write test function:
   ```python
   def test_my_feature():
       """Test description."""
       result = my_function()
       assert result == expected
   ```
3. For LLM mocks:
   ```python
   def test_with_llm_mock(monkeypatch):
       mock_client = MagicMock()
       monkeypatch.setattr(
           "grounded_evals.module.get_default_client",
           lambda: mock_client
       )
       # Test code
   ```

### Modifying Data Models
1. Update model in `src/grounded_evals/models/core.py`
2. Update serialization if needed (Pydantic handles JSON automatically)
3. For file format changes, add migration logic to `Session.load_from_file()`
4. Update tests in `tests/test_models_core.py`

### Debugging Agent Turns
1. Add logging to `src/grounded_evals/agent/handler.py`:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.debug(f"Agent response: {response}")
   ```
2. Check LangSmith traces (if configured) for tool calls
3. Review state block in system prompt (via `get_state_block()`)

### Working with Environment Variables
1. Add to documentation in comment
2. Use in code with fallback:
   ```python
   MY_VAR = os.environ.get("MY_VAR", "default_value")
   ```
3. For secrets, never log or echo to user
4. For local dev, create `.env` file (not committed) and load via `python-dotenv`

## Testing Best Practices

### Unit Tests
- Test single functions in isolation
- Mock external dependencies (LLM, AWS)
- Use descriptive names: `test_<function>_<scenario>()`
- One assertion per test is ideal, multiple related assertions okay

### Integration Tests
- Test module interactions (e.g., `open_coding` → `judge_builder`)
- Use real data fixtures from `tests/conftest.py` if available
- Keep integration tests focused on happy path

### Test Fixtures
Create helper functions in test file:
```python
def _make_category(name: str = "Test") -> Category:
    return Category(name=name, definition="Definition")

def test_my_feature():
    cat = _make_category()
    assert check_saturation(cat, []) == SaturationStatus.UNSATURATED
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_open_coding.py

# Run specific test
pytest tests/test_open_coding.py::test_empty_category_is_unsaturated

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src/grounded_evals --cov-report=html
```

## Type Checking & Linting

### mypy
```bash
# Check entire codebase
mypy src/

# Check specific file
mypy src/grounded_evals/models/core.py

# Fix common issues
mypy src/ --show-traceback
```

### ruff
```bash
# Check all issues
ruff check src/

# Auto-fix (when possible)
ruff check src/ --fix

# Sort imports only
ruff check src/ --select I

# Check line length
ruff check src/ --line-length 100
```

## Performance Profiling

### Timing LLM Calls
Use `traced_coach_call()` with LangSmith (if configured):
```python
from grounded_evals.llm.client import traced_coach_call

response = traced_coach_call(client, model, system, messages, tools, max_tokens)
# Trace is sent to LangSmith (visible in dashboard)
```

### Memory Profiling
```bash
pip install memory-profiler

python -m memory_profiler my_script.py
```

## Deployment & Infrastructure

### Local Docker Build
```bash
cd grounded-evals
docker build -t grounded-evals:latest .
docker run -p 8080:8080 grounded-evals:latest
```

### AWS CDK Deployment
```bash
cd grounded-evals/infra
cdk bootstrap  # One-time setup
cdk deploy --context region=us-east-1 --context enable_app_auth=true
```

### Environment Configuration
Set via AWS Systems Manager Parameter Store or environment variables at container runtime:
```bash
export COGNITO_USER_POOL_ID="us-east-1_xxx"
export COGNITO_CLIENT_ID="abc123"
export COGNITO_DOMAIN="my-domain"
export AWS_REGION="us-east-1"
grounded-evals serve
```

## Troubleshooting

### Common Issues

**Issue: mypy errors about missing type hints**
- Solution: Add `: Type` annotations to function parameters and return types
- Example: `def my_func(x: str) -> int:` instead of `def my_func(x):`

**Issue: Tests fail with "ModuleNotFoundError"**
- Solution: Ensure `PYTHONPATH` includes `src/`: `export PYTHONPATH=src:$PYTHONPATH`
- Or run from project root: `pytest` (not `cd tests && pytest`)

**Issue: LLM calls timeout**
- Solution: Check Anthropic/AWS credentials, network connectivity
- Add timeout in config: `ANTHROPIC_TIMEOUT_SECONDS=30`

**Issue: NiceGUI page shows 500 error**
- Solution: Check browser console for error, check server logs for traceback
- Enable debug mode: `grounded-evals serve --debug`

**Issue: Session state is lost after page refresh**
- Solution: State is only in-memory. Save to file via CLI or /report download
- For persistent state, implement Session storage (e.g., DynamoDB)

## Contributing

### Code Review Checklist
- [ ] Passes `pytest`
- [ ] Passes `ruff check src/`
- [ ] Passes `mypy src/`
- [ ] New functions have type hints
- [ ] New module functions have tests
- [ ] Docstrings added or updated
- [ ] No hardcoded credentials or sensitive data
- [ ] No new warnings from linters

### Pull Request Process
1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes, commit with clear messages
3. Push to fork, open PR against `main`
4. Wait for CI to pass (GitHub Actions)
5. Request review, address feedback
6. Merge when approved

### Commit Message Format
Use descriptive messages:
```
feat: Add saturation check for categories
fix: Handle empty code list in paradigm model
refactor: Extract validation into helper function
test: Add tests for ensemble judge
docs: Update development guide
```

