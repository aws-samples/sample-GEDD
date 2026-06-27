---
inclusion: fileMatch
fileMatchPattern: "**/ui/**"
---

# GEDD UI Development Guide

## Framework
NiceGUI 3.12+ running on FastAPI. Dark-mode UI with responsive design.

## Page Pattern
All pages go in `src/grounded_evals/ui/*_page.py`:
```python
"""Page title — one-line description."""

from nicegui import app, ui
from grounded_evals.ui.layout import page_layout

@ui.page("/my-route")
async def my_page() -> None:
    """Page handler — async for LLM calls."""
    with page_layout():
        ui.label("Content")
        # Build page here
```

## Registration
Import the page module in `src/grounded_evals/app.py` to auto-register the route:
```python
import grounded_evals.ui.my_page  # noqa: F401
```

## Layout & Styling
- Always use `page_layout()` context manager for header/sidebar consistency
- Theme defined in `ui/theme.py` and `ui/layout.py`
- Component styling via `.classes()` or `.style()`
- Dark mode is default and required

## State Management
Use `ui.context.client.storage` for per-session browser state:
```python
storage = app.storage.user  # or ui.context.client.storage

# Read state
session_data = storage.get("session_data", {})

# Write state
storage["coding_annotations"] = annotations
```

### Storage Keys
| Key | Contents |
|-----|----------|
| `session_data` | Agent spec, golden prompts, queries |
| `eval_results` | Agent responses from eval runs |
| `coding_annotations` | PM labels (verdict, code, severity, memo) |
| `codebook` | Category/code definitions |
| `paradigm_model` | Axial coding output |
| `_generated_judge_prompt` | Generated judge prompt text |

## Reusable Components
Step components live in `ui/steps/`:
- `define_agent.py` — Agent name, description, capabilities
- `system_prompt.py` — System prompt editor
- `ingestion_step.py` — Query import
- `judge_builder_step.py` — Judge generation UI
- `evaluation_step.py` — Eval runner

## Async Pattern
Use `async def` for page handlers. Long operations (LLM calls) must use `await`:
```python
@ui.page("/eval")
async def eval_page() -> None:
    async def run_eval():
        result = await asyncio.to_thread(traced_eval_call, client, model, prompt, query)
        # update UI
    ui.button("Run", on_click=run_eval)
```

## Error Display
```python
try:
    result = some_operation()
except Exception as e:
    ui.notify(f"Error: {e}", type="negative")
```

## Demo Data
- 50-query demos in `ui/demo_data.py` and dedicated `*_demo.py` files
- Demos load into storage without requiring model calls
- Used for onboarding and showcasing the workflow
