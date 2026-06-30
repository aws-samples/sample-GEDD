# GEDD Steering Files

This directory contains comprehensive steering files for the GEDD project. Use these documents to understand the codebase structure, conventions, and development patterns.

## Files Overview

### 1. **coding-conventions.md** (336 lines)
Complete Python coding standards and conventions for GEDD.

**Contains:**
- Import organization and type hinting standards
- Naming conventions (snake_case functions, PascalCase classes)
- Pydantic model patterns and validation
- Test patterns with fixtures and mocking
- CLI and UI conventions
- Security best practices

**Use when:** Writing new code, reviewing PRs, setting up IDE linters

---

### 2. **architecture.md** (291 lines)
High-level system design and module responsibilities.

**Contains:**
- System overview (workflow layer, core logic layer, infrastructure layer)
- Module responsibilities (models, open_coding, axial_coding, judge_builder, ui, agent, etc.)
- Data flow examples (annotation workflow, judge generation, CLI export)
- State management patterns (session state, file-based sessions)
- Performance and scalability considerations
- Extension points for adding new features

**Use when:** Understanding system design, adding new modules, planning large features

---

### 3. **development-guide.md** (292 lines)
Practical guide for developing GEDD locally.

**Contains:**
- Setup instructions (venv, pip install, dependencies)
- Common development tasks (adding models, pages, CLI commands, tests)
- Testing best practices and running tests
- Type checking and linting workflows
- Performance profiling techniques
- Deployment to Docker and AWS CDK
- Troubleshooting common issues
- Contributing process and PR checklist

**Use when:** Setting up dev environment, implementing features, debugging

---

### 4. **project-structure.md** (297 lines)
Detailed directory map and file organization.

**Contains:**
- Complete directory tree with descriptions
- Key files reference by purpose (config, entry points, core logic, UI, testing, data)
- File naming conventions for different types (modules, pages, tests, stacks)
- Import paths for common operations
- Dependencies between modules

**Use when:** Locating files, understanding module organization, navigating codebase

---

### 5. **quick-reference.md** (246 lines)
Cheat sheet for commands, patterns, and common tasks.

**Contains:**
- Key commands (run app, tests, linting, CLI examples)
- Core data models (Enums, classes)
- Module quick links with main functions
- Test patterns (fixtures, LLM mocks)
- File locations for common tasks
- UI route map
- Storage keys reference
- Environment variables
- Performance tips
- Security checklist
- Common errors & fixes
- Deployment quick start

**Use when:** Needing quick answers, looking up command syntax, debugging

---

## Quick Start

1. **New to GEDD?** Start with:
   - `quick-reference.md` → Get oriented with commands and key concepts
   - `architecture.md` → Understand the system design
   - `project-structure.md` → See how files are organized

2. **Writing code?** Reference:
   - `coding-conventions.md` → Style, type hints, patterns
   - `development-guide.md` → How to add features and run tests

3. **Specific task?** Use:
   - `quick-reference.md` → Quick lookup of commands/files
   - `development-guide.md` → Step-by-step guide for common tasks
   - `project-structure.md` → Find file locations

4. **Understanding existing code?** Refer to:
   - `architecture.md` → Data flow and module responsibilities
   - `project-structure.md` → How modules relate to each other

## Key Conventions at a Glance

### Imports
- Always absolute: `from grounded_evals.models.core import Code`
- Group: stdlib, third-party, local

### Type Hints (MANDATORY)
```python
def check_saturation(category: Category, prompts: list[GoldenPrompt]) -> SaturationStatus:
    pass
```

### Naming
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

### Pydantic Models
- All domain entities in `models/core.py`
- Include `id: UUID = Field(default_factory=uuid4)`
- Include `created_at: datetime = Field(default_factory=datetime.now)`
- Use `Field(default_factory=list)` for mutable defaults

### Testing
- One test file per module: `tests/test_<module>.py`
- Use `_make_*()` helpers for fixtures
- Mock LLM with `monkeypatch`
- Pattern: `test_<function>_<scenario>()`

### CLI Commands
- Click decorators for args/options
- Return None or call `sys.exit()`
- Provide `-X` short flags for common options

### UI Pages
- Use `@ui.page()` decorator
- Import in `app.py` to auto-register
- Store state in `ui.context.client.storage`
- Use `page_layout()` context manager

## Project at a Glance

```
GEDD = Grounded-theory-driven LLM-as-a-Judge evaluation framework

Core Workflow:
  1. Define agent (system prompt, task boundary)
  2. Collect/generate golden queries
  3. Run agent → collect responses
  4. PM annotates (verdict, failure codes, severity, memos)
  5. Extract failure patterns (Open Coding → Axial Coding)
  6. Generate judge prompt from patterns
  7. Export for ML engineer (automated eval, regression gates)

Core Modules:
  - open_coding/: Discover & categorize failures
  - axial_coding/: Map failures to root causes & consequences
  - judge_builder/: Convert patterns → executable judge criteria
  - ui/: NiceGUI web app for PM collaboration
  - cli.py: ML engineer automation
  - agent/: Interactive annotation assistant
```

## Tools & Stack

- **Language**: Python 3.11+
- **Web**: NiceGUI 3.12+ (FastAPI)
- **Data**: Pydantic 2.13+
- **CLI**: Click 8.4+
- **LLM**: Anthropic Claude (with Bedrock support)
- **Testing**: pytest, pytest-asyncio
- **Linting**: ruff, mypy
- **Infrastructure**: AWS CDK
- **Observability**: LangSmith (optional)

## File Sizes & Scope

| File | Lines | Purpose |
|------|-------|---------|
| coding-conventions.md | 336 | Python style, patterns, standards |
| architecture.md | 291 | System design, data flow |
| development-guide.md | 292 | Setup, tasks, debugging |
| project-structure.md | 297 | Directory map, file locations |
| quick-reference.md | 246 | Commands, cheat sheet |
| **Total** | **1,462** | Complete developer guide |

## Keeping These Updated

As the project evolves, update steering files when:
- Adding a new major module or page
- Changing code organization or import patterns
- Adding new CLI commands or UI pages
- Updating dependencies or tools
- Establishing new conventions or patterns

The steering files are living documentation. Keep them synchronized with actual code.

## For AI Agents & Development Tools

These steering files are optimized for use with:
- Kiro (development environment)
- Claude or other AI coding assistants
- Linters and type checkers (mypy, ruff)
- IDE configuration tools

Use the `architecture.md` and `project-structure.md` for context about the codebase.
Use `coding-conventions.md` and `quick-reference.md` for implementation patterns.

