# GEDD Architecture & Design Patterns

## System Overview

GEDD implements a grounded-theory-first workflow for building LLM-as-a-Judge evaluation criteria:

```
User Input          → Agent Annotation Loop → Failure Codebook → Judge Prompt → CI/ML Pipeline
(agent + queries)     (PM review, feedback)    (open + axial)    (generation)   (automated eval)
```

The system is organized into three layers:

1. **Workflow Layer** (UI + CLI)
   - NiceGUI web pages for PM interaction
   - Click CLI for ML engineer automation
   - Session state management in `guide/session.py`

2. **Core Logic Layer** (Open Coding → Axial Coding → Judge Building)
   - `open_coding/`: Fracture categories, check saturation, compare exemplars
   - `axial_coding/`: Map errors to paradigm model (conditions, context, strategies, consequences)
   - `judge_builder/`: Generate rubrics, prompts, and calibrate judge vs. human labels

3. **Infrastructure Layer** (Models, LLM, Data Ingestion)
   - `models/`: Pydantic data classes (immutable domain entities)
   - `llm/`: Anthropic + Bedrock client abstraction
   - `agent/`: Agentic tool loop for interactive annotation
   - `ingest/`: Import traces and queries

## Module Responsibilities

### models/
**Responsibility**: Define all domain entities as Pydantic models

Core models:
- `Code`, `Category`: Open coding concepts
- `ParadigmModel`: Axial coding structure (phenomenon, conditions, strategies, consequences)
- `Memo`: PM annotations and design rationale
- `GoldenPrompt`, `GoldenDataset`: Query provenance and golden dataset
- `JudgeCriterion`, `JudgeRubric`: Judge specification
- `CoverageReport`: Dataset quality metrics

**Invariants**:
- All entities have UUID id and created_at timestamp
- Enums for fixed states (CodeType, MemoType, SaturationStatus)
- No business logic in models (only validation via @field_validator)

### open_coding/
**Responsibility**: Structured discovery of failure patterns

Functions:
- `fracture_domain(agent_spec: AgentSpec) → list[Category]`: Generate candidate categories via LLM
- `check_category_saturation(category, prompts) → SaturationStatus`: Evidence of saturation (3+ examples)
- `check_overall_saturation(categories, prompts) → CoverageReport`: Dataset-wide coverage analysis
- `compare_codes(new_code, existing_codes) → CodeComparisonResult`: Check for duplicates and merges

**Key insight**: Saturation is binary per category (approaching at 2, saturated at 3+ prompts).

### axial_coding/
**Responsibility**: Relate categories via grounded-theory relationships

Functions:
- `map_errors_to_categories(codes: list[Code]) → list[ErrorMapping]`: Assign to standard dimensions (accuracy, safety, tone, etc.)
- `build_paradigm_model(phenomenon, conditions, strategies, consequences) → ParadigmModel`: Construct the causal/strategic model

**Key insight**: Paradigm model feeds into rubric, rubric feeds into judge prompt. The model captures *why* failures happen and *how* they manifest, not just surface-level labels.

### judge_builder/
**Responsibility**: Convert observed failures into executable judge criteria

Modules:
- `rubric.py`: Generate JudgeRubric from error mappings (enriched with paradigm context)
- `prompt_gen.py`: Render rubric into LLM judge prompt (Anthropic or G-Eval style)
- `calibrate.py`: Compare judge scores vs. human labels (Cohen's kappa, agreement analysis)
- `few_shot.py`: Select exemplar prompts for few-shot learning in judge prompt
- `ensemble.py`: Run multiple judges, aggregate results
- `constitutional.py`: Build judge from constitutional AI principles
- `active_learning.py`: Recommend next prompts to maximize coverage

**Key insight**: Judge is not a generic LLM scorer. It is domain-specific, calibrated against ground truth, and grounded in observed failure modes.

### ui/
**Responsibility**: NiceGUI workflow pages and components

Pages (in `ui/*_page.py`):
- `home_page.py`: Workflow entry, demo loader, progress tracking
- `eval_page.py`: Run agent and collect responses
- `coding_page.py`: PM annotation workbench (verdict, code, severity, memo)
- `judge_builder_page.py`: Interactive judge prompt generation and testing
- `report_page.py`: Quality signals, CI gates, ML engineer handoff
- `analysis_page.py`: Saturation, coverage, and axial coding review
- `demos_page.py`: Load seeded 50-query demos

Steps (`ui/steps/`):
- Reusable workflow components (define agent, system prompt, query ingestion, etc.)
- Composed into pages via context managers or direct UI element building

**Storage**: Per-session state in `ui.context.client.storage`, keyed by data type (session_data, coding_annotations, eval_results, etc.).

### agent/
**Responsibility**: Agentic tool loop for interactive PM guidance during annotation

Structure:
- `prompt.py`: System prompt template for the annotation coach (an AI agent)
- `tools.py`: Tool definitions (save_code, update_memo, check_saturation, etc.)
- `handler.py`: Main turn loop (user message → tool calls → state mutations)

**Workflow**:
1. User sends chat message (e.g., "suggest codes for this failure")
2. Agent receives state block (current categories, memos, saturation)
3. Agent calls tools to mutate session state
4. Tool results + response returned to user
5. Repeat until user closes conversation

### llm/
**Responsibility**: Unified interface to LLM providers (Anthropic, Bedrock, etc.)

Functions:
- `get_default_client()`: Returns configured Anthropic or Bedrock client
- `get_model_id()`: Returns active model ID from environment or config
- `traced_coach_call()`: Wraps LLM calls with LangSmith tracing for observability

**Configuration**: Via environment variables or hardcoded fallbacks.

### guide/
**Responsibility**: Session lifecycle and state mutation

Classes:
- `Session`: In-memory representation of a GEDD session (agent spec, queries, annotations, codebook)
- Session methods: `load_from_file()`, `save_to_file()`, `add_annotation()`, etc.

**Invariant**: Session is the single source of truth; all mutations go through session methods.

### cli.py
**Responsibility**: Command-line orchestration for ML engineers

Main commands:
- `serve`: Start NiceGUI web app
- `fracture`: Run open coding on agent spec
- `check_saturation`: Analyze coverage
- `judge`: Generate judge prompt from session
- `run_eval`: Execute agent against golden queries
- `annotate`: Ingest human labels into session
- `export`: Write session to JSON/CSV
- `handoff`: Create ML engineer package (queries, codebook, judge, calibration)

**Pattern**: Each command loads session, calls core logic, outputs result (file or stdout).

## Data Flow Examples

### Example 1: PM Workbench Annotation
```
1. User opens /coding page
2. Page loads session_data from storage → Session object
3. For each response, user: sets verdict, creates/selects code, sets severity, writes memo
4. On save, mutations are stored in storage['coding_annotations']
5. UI refreshes to show updated counts and saturation status
6. (Optional) User opens agent chat for guidance
7. Agent queries state, suggests codes or validates coverage
8. Agent calls tools to mutate session and storage
```

### Example 2: Judge Generation
```
1. User clicks "Generate Judge" on /judge page
2. Page calls `generate_judge_prompt()` with:
   - session (golden queries, categories, annotations)
   - paradigm model (from axial coding analysis)
   - error mappings (domain → standard categories)
3. Function returns rubric → rendered prompt template
4. UI displays prompt, allows editing
5. User can test prompt on sample responses (ensemble judge)
6. On save, prompt stored in storage['_generated_judge_prompt']
7. /report page offers prompt for download
```

### Example 3: CLI Export for ML Engineer
```
$ grounded-evals export session.json --output report.csv

1. cli.py::export() loads session.json
2. Calls Session.to_csv() or similar export method
3. Writes to report.csv
4. Stdout: "Exported 50 queries, 12 codes, 4 categories"
```

## State Management

### Session State (`ui.context.client.storage`)
Stored as JSON, per-user, per-browser-session (no authentication in guest mode):
```
storage = {
    "session_data": {
        "agent_spec": {...},
        "golden_prompts": [...],
        "queries": [...],
    },
    "eval_results": [...],  # Agent responses
    "coding_annotations": [  # PM labels
        {
            "prompt_id": "...",
            "verdict": "correct|partial|incorrect",
            "codes": ["code1", "code2"],
            "severity": 1-5,
            "memo": "...",
        }
    ],
    "codebook": {...},  # Category/code definitions
    "paradigm_model": {...},  # Axial coding output
    "_generated_judge_prompt": "...",
}
```

### File-Based Session (CLI & Export)
Saved as `session.json`:
```json
{
    "agent_spec": {...},
    "golden_prompts": [...],
    "eval_results": [...],
    "annotations": [...],
    "codebook": {...},
    "judge_prompt": "...",
    "created_at": "2024-01-15T...",
    "version": "0.1.0"
}
```

## Async & Concurrency

### NiceGUI Event Loop
- NiceGUI runs on FastAPI event loop
- All page handlers are `async def`
- Long-running operations (LLM calls) yield to event loop via `await`

### CLI Concurrency
- CLI commands are synchronous
- For batch operations (e.g., evaluate 50 queries), use simple loops or `asyncio.run()` if needed
- No background jobs / queues in current implementation

## Error Handling

### Patterns
1. **Validation errors**: Pydantic raises `ValidationError`, caught at page/CLI boundary
2. **LLM errors**: Caught, logged, returned as user message or error indicator
3. **File I/O**: Wrapped in try/except, user shown friendly error message
4. **Tool failures**: Caught in agent tool dispatcher, returned as tool error (agent retries)

### Best Practice
```python
try:
    result = some_operation()
except ValueError as e:
    logger.error(f"Validation failed: {e}")
    ui.notify(f"Error: {e}", type="negative")
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    ui.notify("An unexpected error occurred. Please try again.", type="negative")
```

## Extension Points

### Adding a New Judge Style
1. Add function to `judge_builder/prompt_gen.py` (e.g., `generate_constitutional_judge()`)
2. Register in UI dropdown on `/judge` page
3. Add corresponding test in `tests/test_prompt_gen.py`

### Adding a New CLI Command
1. Add function to `cli.py` with Click decorators
2. Add corresponding test in `tests/test_cli.py`
3. Update CLI help in README

### Adding a New Data Source
1. Add importer function to `ingest/`
2. Add test in `tests/test_ingest.py`
3. Update Session.load_* methods

## Performance & Scalability

### Current Limitations
- Session state is in-memory (ui.context.client.storage)
- No persistent database (file-based for CLI)
- No caching of LLM outputs (each call re-invokes model)
- No background job queue (blocking operations)

### Future Improvements
- Persistent session store (DynamoDB / RDS)
- LLM result caching with semantic deduplication
- Background eval worker (SQS / Step Functions)
- Horizontal scaling via load balancer + session affinity

