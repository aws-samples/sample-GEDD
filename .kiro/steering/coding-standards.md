---
inclusion: always
---

# GEDD Coding Standards

## Language & Stack
- Python 3.11+ with strict mypy type checking
- NiceGUI 3.12+ (web framework on FastAPI)
- Pydantic 2.13+ (data models and validation)
- Click 8.4+ (CLI)
- Anthropic SDK with Bedrock (LLM client)
- AWS CDK (infrastructure)

## Type Hints (Mandatory)
- All function parameters and return types must be annotated
- Use `X | None` instead of `Optional[X]`
- Use `list[T]`, `dict[K, V]` (Python 3.11 builtins, not typing module)
- Pydantic fields: always annotated with explicit `Field()` for mutable defaults

```python
def check_saturation(category: Category, prompts: list[GoldenPrompt]) -> SaturationStatus:
    ...
```

## Imports
- Always absolute: `from grounded_evals.models.core import Code`
- Never relative imports within the package
- Group order: stdlib → third-party → local
- Import specific symbols, no wildcards

## Naming
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Enums: `class MyEnum(str, Enum):`
- Private: `_leading_underscore`
- Tests: `test_<function>_<scenario>()`

## Line Length & Formatting
- Max 100 characters (ruff enforced)
- 4 spaces indentation, no tabs
- Per-file E501 ignores in pyproject.toml for long prompts/strings

## Pydantic Models
All domain models live in `src/grounded_evals/models/core.py`:
```python
class MyEntity(BaseModel):
    """Brief docstring."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    items: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
```

Rules:
- `Field(default_factory=list)` for mutable defaults
- UUID `id` and `created_at` on all entities
- Enums for fixed state sets
- `@field_validator` for domain validation, not `__init__` logic

## Docstrings
- Module: one-line summary at top
- Functions: brief description; Google-style for complex functions
- Classes: describe purpose and key invariants

## Error Handling
- Catch specific exceptions, never bare `except:`
- Log with `logger.error()` or `logger.exception()`
- UI errors: `ui.notify("message", type="negative")`
- Agent tool failures: return error string (agent retries)

## Security
- No hardcoded credentials — use `os.environ.get()`
- Never log or echo secrets back to users
- Input validation via Pydantic at boundaries
- Use Cognito or ADMIN_PASSWORD for auth, never disable in prod

## Anti-Patterns to Avoid
- Relative imports
- `Optional[X]` (use `X | None`)
- `List[T]`, `Dict[K,V]` from typing (use builtins)
- Mutable default arguments
- Circular imports (follow: models → domain → ui)
- Global mutable state (use DI or per-request storage)
