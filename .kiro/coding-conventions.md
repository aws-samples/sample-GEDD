# GEDD Coding Conventions & Standards

## Project Overview
GEDD is a systematic, evidence-driven LLM-as-a-Judge framework built with Python 3.11+. It combines grounded theory methodology (open coding, axial coding) with web-based UI (NiceGUI), CLI tools, and AWS CDK infrastructure.

## Core Languages & Frameworks
- **Python 3.11+**: Primary language, strict type hints required (mypy strict mode)
- **NiceGUI 3.12+**: Web framework for UI pages (runs on top of FastAPI)
- **Pydantic 2.13+**: Data validation and serialization
- **Click 8.4+**: CLI framework with decorators
- **AWS CDK**: Infrastructure-as-Code for deployment
- **Anthropic SDK + Bedrock**: LLM client support

## Code Organization

### Directory Structure
```
grounded-evals/
├── src/grounded_evals/          # Main source code
│   ├── __init__.py
│   ├── app.py                   # NiceGUI FastAPI app
│   ├── cli.py                   # Click CLI entry point
│   ├── agent/                   # Agent turn loop and tool handlers
│   ├── models/                  # Pydantic data models (core.py)
│   ├── ui/                      # NiceGUI pages and components
│   │   ├── *_page.py            # @ui.page decorated route handlers
│   │   ├── steps/               # Reusable workflow step components
│   │   └── layout.py            # Shared layout and styling
│   ├── open_coding/             # Fracture, saturation, comparison
│   ├── axial_coding/            # Paradigm model, error mapping
│   ├── judge_builder/           # Rubric, prompt generation, calibration
│   ├── llm/                     # LLM client abstraction
│   ├── ingest/                  # Data import utilities
│   └── guide/                   # Session and workflow state
├── tests/                       # pytest test suite
├── infra/                       # AWS CDK infrastructure
│   └── stacks/                  # Individual CDK stacks
├── configs/                     # Configuration templates
└── data/                        # Seed data (50-query demos)
```

### Module Dependencies
- **models/** → foundation, used by all modules
- **ui/** → imports from agent/, guide/, open_coding/, judge_builder/
- **cli.py** → orchestrates all modules
- **agent/** → uses models/, llm/
- **open_coding/, axial_coding/, judge_builder/** → use models/

## Python Style & Conventions

### Imports
- Group in standard order: stdlib, third-party, local imports
- Always use absolute imports: `from grounded_evals.models.core import Code`
- Never use relative imports within the package
- Import specific symbols, not wildcard imports
```python
from grounded_evals.models.core import Category, Code, SaturationStatus
from grounded_evals.llm.client import get_default_client, traced_coach_call
```

### Type Hints
- **Mandatory** for all function parameters and return types (mypy strict)
- Use union syntax for nullable types: `UUID | None` (not `Optional[UUID]`)
- Use `list[T]` and `dict[K, V]` instead of `List[T]` (Python 3.11+ style)
- Annotate dataclass fields and Pydantic model fields
```python
def fracture_domain(agent_spec: AgentSpec) -> list[Category]:
    """Generate categories from agent specification."""
    categories: list[Category] = []
    # ...
    return categories
```

### Documentation
- Module docstring: one-line summary at top
- Function/class docstring: brief description, parameters, return type
- Use Google-style docstrings for complex functions
```python
"""Saturation analysis module — checks category coverage."""

def check_category_saturation(
    category: Category,
    prompts: list[GoldenPrompt],
) -> SaturationStatus:
    """Check whether a category has saturation evidence.
    
    Parameters
    ----------
    category: The category to evaluate
    prompts: Golden prompts assigned to this category
    
    Returns
    -------
    SaturationStatus enum indicating saturation level
    """
```

### Naming Conventions
- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Enums**: Use `class NameEnum(str, Enum):` for string-backed enums
- **Private functions**: Prefix with `_`, e.g., `_load_state()`
- **Test functions**: Prefix with `test_`, follow convention: `test_<function>_<scenario>()`

### Line Length & Formatting
- **Max line length**: 100 characters (enforced by ruff)
- **Exceptions**: Per-file ignores in pyproject.toml for generated/long prompts
- **Indentation**: 4 spaces, no tabs

### Code Quality Tools
- **Ruff**: Linting and import sorting (line-length=100, select E,F,I,N,W,UP)
- **mypy**: Strict type checking enabled
- **pytest**: Test runner with asyncio support
- **Black-compatible**: Code follows Black style (via ruff)

Configuration in `pyproject.toml`:
```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["UP042"]

[tool.mypy]
python_version = "3.11"
strict = true
```

## Pydantic Models

### Core Model Patterns
All domain models inherit from `BaseModel` and live in `models/core.py`:

- Use `Field(default_factory=list)` for mutable defaults
- Include `id: UUID = Field(default_factory=uuid4)` for entities
- Include `created_at: datetime = Field(default_factory=datetime.now)` for tracking
- Use enums for fixed set of values (CodeType, MemoType, SaturationStatus)
- Add descriptive docstrings for complex models

```python
class Code(BaseModel):
    """A conceptual label for a prompt category discovered during fracturing."""
    id: UUID = Field(default_factory=uuid4)
    label: str
    code_type: CodeType
    definition: str = ""
    exemplar_prompts: list[str] = Field(default_factory=list)
    properties: list[Property] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
```

### Validation Pattern
Use Pydantic validators for domain logic (post_init patterns):
```python
from pydantic import BaseModel, field_validator

class MyModel(BaseModel):
    name: str
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('name cannot be empty')
        return v.strip()
```

## Testing Patterns

### Test File Organization
- Test files mirror source structure: `tests/test_<module>.py`
- Use descriptive test names: `test_<function>_<scenario>()`
- Group related tests with setup helpers

### Test Fixtures & Helpers
```python
def _make_category(name: str = "Test Category") -> Category:
    """Helper to construct test Category."""
    return Category(name=name, definition="Test definition")

def test_empty_category_is_unsaturated():
    cat = _make_category()
    status = check_category_saturation(cat, [])
    assert status == SaturationStatus.UNSATURATED
```

### Mocking Pattern
Use `unittest.mock` with `monkeypatch` for LLM and external service mocks:
```python
def test_map_errors_with_mock_llm(monkeypatch):
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps({"mappings": [...]})]
    mock_client.messages.create.return_value = msg
    
    monkeypatch.setattr(
        "grounded_evals.axial_coding.mapper.get_default_client",
        lambda: mock_client
    )
    # Test code here
```

### Test Configuration
From `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

## CLI Conventions

### Entry Point
Click-based CLI in `cli.py`, configured in pyproject.toml:
```toml
[project.scripts]
grounded-evals = "grounded_evals.cli:main"
```

### Command Patterns
```python
@click.command()
@click.argument("session", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output path")
def export(session: str, output: str | None) -> None:
    """Export session data in specified format."""
    # Implementation
```

### Conventions
- Use `click.argument()` for required positional parameters
- Use `click.option()` for optional flags/parameters
- Provide short `-X` aliases for common options
- Docstring is help text
- Return None or call `sys.exit()` on error

## UI Conventions (NiceGUI)

### Page Pattern
Pages use `@ui.page()` decorator and go in `ui/*_page.py`:
```python
"""Page title and one-line description."""

from nicegui import app, ui
from grounded_evals.ui.layout import page_layout

@ui.page("/my-page")
async def my_page() -> None:
    """Page handler — sets up layout and event bindings."""
    with page_layout():
        ui.label("Welcome")
        # Page content here
```

### Layout & Styling
- Use `page_layout()` context manager for consistent header/sidebar
- Theme CSS in `ui/theme.py` and `ui/layout.py`
- Component styles inline with `ui.element().classes()`
- Responsive design assumes mobile-first

### State Management
- Use `ui.context.client.storage` for per-session state
- Structured data in `storage['session_data']`, `storage['coding_annotations']`, etc.
- Session state lives in `guide/session.py` (Session class)

## Agent & Tool Patterns

### Agent Turn Loop
From `agent/handler.py`:
- One turn = user message + tool loop (up to 8 iterations)
- Returns `AgentResponse` with text, tool_executions list, and updated messages
- Mutates state and messages in place (side effects)

### Tool Definition
Tools in `agent/tools.py` as Pydantic models with a `handle_tool_call()` dispatcher:
```python
from grounded_evals.agent.tools import TOOLS, StateBundle, handle_tool_call

# Each tool is a Pydantic model describing its interface
class SaveCodeTool(BaseModel):
    name: str = "save_code"
    description: str = "Save a failure code..."
    # ... tool-specific fields
```

## Infrastructure & Deployment

### CDK Patterns
Stacks in `infra/stacks/`:
- Each stack is a self-contained CDK Construct
- Stacks are composed in `infra/app.py` (the CDK App)
- Configuration via `cdk.json` context values
- Standard stacks: Network, ECR, ECS, Cognito, AgentCore

```python
# Example stack composition
network = NetworkStack(app, "Network", env=env)
ecs = EcsStack(app, "ECS", vpc=network.vpc, env=env)
```

### Environment Variables
Loaded via `os.environ.get()` at runtime:
- `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_DOMAIN`: Auth config
- `AWS_REGION`: Deployment region
- `ADMIN_PASSWORD`: Local guest-mode auth (no Cognito)
- `PUBLIC_BASE_URL`: Cloudfront domain for OAuth callbacks

## Common Anti-Patterns to Avoid

1. **Relative imports** → Always use absolute imports
2. **Missing type hints** → Add full annotations, mypy catches violations
3. **Mutable defaults** → Use `Field(default_factory=list)` in Pydantic
4. **Hardcoded credentials** → Use environment variables, never commit secrets
5. **Bare except clauses** → Catch specific exceptions, log properly
6. **Logic in __init__** → Keep model initialization minimal, use validators
7. **Circular imports** → Organize by dependency tree (models → domain → ui)
8. **Global state** → Use dependency injection or per-request state (storage)

## Performance Considerations

1. **LLM calls** → Instrument with `traced_coach_call()` for observability
2. **Database queries** → Minimize I/O in loops, batch when possible
3. **Session state** → Keep in-memory, persist to file only on explicit save
4. **UI responsiveness** → Use async/await for long operations, show progress

## Security Best Practices

1. **Authentication** → Use Cognito or local password, never disable entirely in production
2. **CORS** → NiceGUI handles CORS automatically
3. **Input validation** → Pydantic models validate at boundary, use validators for domain logic
4. **Secrets** → Load from environment, never log or echo back to user
5. **SQL/Injection** → No SQL in this project, but if queries added, use parameterized queries

