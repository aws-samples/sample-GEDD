# Annotation Workflow

Guide the domain expert through systematic annotation of AI agent responses so GEDD can generate Kiro `requirements.md` and an LLM Judge.

## Prerequisites
- An AI agent with a defined system prompt and task boundary
- Representative queries (golden prompts) or existing agent traces
- The domain expert's time and vocabulary

## Phase 1: Define the Agent

Capture these fields before annotation begins:

| Field | Description | Example |
|-------|-------------|---------|
| Agent Name | Short identifier | "CloudAuditGate" |
| Description | What the agent does | "Reviews AWS configurations for GDPR compliance" |
| Capabilities | What it can do | ["Analyze S3 policies", "Check retention rules"] |
| Target Users | Who uses it | ["Security engineers", "Compliance officers"] |
| Constraints | What it must NOT do | ["Never recommend disabling logging"] |
| System Prompt | The agent's instruction set | (full prompt text) |

## Phase 2: Build Golden Queries

Create representative test cases that cover:

| Category | Purpose | Count Target |
|----------|---------|--------------|
| Happy path | Normal successful interactions | 3-5 per capability |
| Edge cases | Boundary conditions, unusual inputs | 2-3 per capability |
| Adversarial | Attempts to break or confuse | 3-5 total |
| Multi-turn | Conversations requiring context | 2-3 total |
| Recovery | Error handling and graceful degradation | 2-3 total |
| Ambiguous | Unclear intent requiring clarification | 2-3 total |

### Constant Comparison
For each new query, check:
1. Is it unique compared to existing queries? (not redundant)
2. Does it test a distinct behavior? (not a rephrasing)
3. Does it cover a gap in the current set? (adds coverage)

If redundant, revise or skip. If unique, add to dataset.

## Phase 3: Collect Responses

Run the golden queries against the agent (or paste existing traces). For each response, record:
- The full response text
- Model/version used
- Timestamp
- Any system context provided

## Phase 4: Annotate

For each agent response, the domain expert provides:

### Verdict
- ✓ **Correct** — Response fully satisfies the query intent
- ⚠ **Partial** — Some value delivered but issues present
- ✗ **Incorrect** — Response fails or is harmful

### Failure Code (for Partial/Incorrect)
Name the failure in your own words. Use domain-specific language:
- GOOD: "Hallucinated Pricing", "Rating Disclosure Softening"
- BAD: "error_type_1", "quality_issue", "incorrect"

### Severity (1-5)
| Score | Meaning |
|-------|---------|
| 5 | Release blocker — cannot ship with this failure |
| 4 | Critical — significant user impact |
| 3 | Major — noticeable but workaround exists |
| 2 | Minor — cosmetic or edge-case only |
| 1 | Trivial — noted but acceptable |

### Confidence
How certain is the annotation?
- **High** — Clear-cut, no ambiguity
- **Medium** — Reasonable judgment call
- **Low** — Edge case, could go either way

### Memo
Brief rationale: why is this a failure? What should the agent have done instead?

## Phase 5: Check Saturation

After each annotation round, check:
- Are any categories still UNSATURATED (< 2 examples)?
- Are we seeing NEW failure codes, or repeating existing ones?
- Has the domain expert confirmed "nothing new is emerging"?

### Saturation States
```
UNSATURATED → < 2 prompts in category → Keep annotating
APPROACHING → 2 prompts → Almost there
SATURATED   → ≥ 3 prompts, no new codes → Category complete
```

When all categories are saturated and no new codes emerge in the last annotation window, the dataset is ready for pattern discovery.

## Output

After annotation, you should have:
- Agent spec (name, description, capabilities, constraints, system prompt)
- Golden queries with category assignments
- Annotations with verdicts, codes, severity, confidence, memos
- Saturation status per category

This feeds into:
- Pattern Discovery (`pattern-discovery.md`) when codes need consolidation
- Requirements Generation (`requirements-generation.md`) for Kiro `requirements.md`
- Judge Generation (`judge-generation.md`) for the LLM-as-a-Judge release gate
