---
inclusion: fileMatch
fileMatchPattern: "tests/**"
---

# GEDD Testing Conventions

## Test Runner & Config
- pytest with `asyncio_mode = "auto"`
- Test directory: `grounded-evals/tests/`
- Run: `cd grounded-evals && python -m pytest tests/ -q --tb=short`

## File Organization
- One test file per source module: `tests/test_<module>.py`
- Test function naming: `test_<function>_<scenario>()`
- Use `_make_*()` helper functions for test data construction

## Test Data Helpers
```python
def _make_category(name: str = "Test") -> Category:
    return Category(name=name, definition="Test definition")

def _make_code(label: str = "test_code") -> Code:
    return Code(label=label, code_type=CodeType.IN_VIVO, definition="Test")
```

## LLM Mocking Pattern
Always mock LLM calls at the module boundary using monkeypatch:
```python
def test_with_llm_mock(monkeypatch):
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps({"data": "response"}))]
    mock_client.messages.create.return_value = msg

    monkeypatch.setattr(
        "grounded_evals.module_under_test.get_default_client",
        lambda: mock_client
    )
    # exercise function under test
```

## Key Test Files
| File | Tests |
|------|-------|
| test_open_coding.py | fracture, compare, saturation |
| test_axial_coding.py | error mapping, paradigm model |
| test_judge_builder.py | rubric generation, judge prompts |
| test_calibrate.py | Cohen's κ calibration |
| test_few_shot.py | exemplar selection |
| test_constitutional.py | constitutional AI judge |
| test_ensemble.py | self-consistency ensemble |
| test_active_learning.py | margin sampling |
| test_cli.py | CLI commands via CliRunner |
| test_integration.py | end-to-end pipelines |
| test_models_core.py | Pydantic model validation |
| test_ui_logic.py | UI state and interactions |

## Principles
- Mock external services (LLM, AWS), test business logic fully
- One assertion per test is ideal; multiple related assertions acceptable
- Integration tests cover happy paths; unit tests cover edge cases
- Use `pytest.raises()` for expected exceptions
- No network calls in tests — all LLM interactions mocked

## Running Tests
```bash
pytest                                  # all tests
pytest tests/test_open_coding.py        # single file
pytest tests/test_open_coding.py::test_empty_category  # single test
pytest -v                               # verbose
pytest --cov=src/grounded_evals         # coverage
```

## CI Behavior
- GitHub Actions runs: `python -m pytest tests/ -q --tb=short`
- Ruff lint check on tests (E501, E741, F401 ignored)
- Format check (non-blocking)
