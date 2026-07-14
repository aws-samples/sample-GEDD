# Annotation Workflow

Guide the domain expert through domain intake, curated query generation, Kiro baseline testing, and systematic annotation so GEDD can generate Kiro judge-subagent `requirements.md` and an LLM-as-Judge response gate.

## Prerequisites
- An AI agent with a defined system prompt and task boundary
- A baseline Kiro `requirements.md` file or an initial behavior contract to test
- Curated domain queries or existing baseline agent traces
- The domain expert's time and vocabulary

## Phase 1: Domain Expert Intake

Start with the SME's domain before generic agent setup. Capture these fields before annotation begins:

| Field | Description | Example |
|-------|-------------|---------|
| Domain Context | SME's domain, regulatory context, risk posture, and vocabulary | "AWS cloud GDPR audit for product teams" |
| Agent Name | Short identifier | "CloudAuditGate" |
| Description | What the agent does | "Reviews AWS configurations for GDPR compliance" |
| Capabilities | What it can do | ["Analyze S3 policies", "Check retention rules"] |
| Target Users | Who uses it | ["Security engineers", "Compliance officers"] |
| Known Edge Cases | Domain exceptions and boundary scenarios | ["Cross-region transfer without DPA", "DSAR deletion blocked by backups"] |
| Constraints | What it must NOT do | ["Never recommend disabling logging"] |
| Baseline requirements.md | Initial Kiro requirements before GEDD evidence | (existing file or generated baseline) |
| System Prompt | Baseline agent instruction set if available | (full prompt text) |

## Phase 2: Curate Domain Queries

This is the most important first product step. Create representative test cases that cover:

| Category | Purpose | Count Target |
|----------|---------|--------------|
| Happy path | Normal successful interactions | 3-5 per capability |
| Edge cases | Boundary conditions, unusual inputs | 2-3 per capability |
| Adversarial | Attempts to break, manipulate, or bypass rules | 3-5 total |
| Multi-turn | Conversations requiring context | 2-3 total |
| Recovery | Error handling and graceful degradation | 2-3 total |
| Ambiguous | Unclear intent requiring clarification | 2-3 total |
| Persona variation | Different roles, expertise levels, permissions, or incentives | 2-3 total |
| Domain red flags | High-risk signals only an SME would know to test | 3-5 total |

### Constant Comparison
For each new query, check:
1. Is it unique compared to existing queries? (not redundant)
2. Does it test a distinct behavior? (not a rephrasing)
3. Does it cover a gap in the current set? (adds coverage)

If redundant, revise or skip. If unique, add to dataset.

## Phase 3: Test the Kiro Baseline Agent

Run the curated queries against the baseline Kiro agent created from the initial `requirements.md` file, or paste existing baseline traces. For each response, record:

- Query category and expected behavior
- The full response text
- Model/version used
- Baseline requirements version
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
- Domain expert profile (domain, agent, target users, constraints, edge cases)
- Curated domain queries with category assignments
- Baseline response evidence
- Annotations with verdicts, codes, severity, confidence, memos
- Saturation status per category

This feeds into:
- Pattern Discovery (`pattern-discovery.md`) when codes need consolidation
- Requirements Generation (`requirements-generation.md`) for Kiro judge-subagent `requirements.md`
- Judge Generation (`judge-generation.md`) for the LLM-as-Judge response gate
