# Session Import Workflow

Guide for importing an existing GEDD session.json into the spec generation pipeline.

## What is session.json?

A session.json file is the portable handoff artifact from the GEDD web app or CLI.
It contains the complete annotation history needed to generate specs.

## Expected Structure

```json
{
  "agent_spec": {
    "name": "AgentName",
    "description": "What the agent does",
    "capabilities": [...],
    "target_users": [...],
    "constraints": [...],
    "system_prompt": "..."
  },
  "golden_prompts": [...],
  "categories": [...],
  "codes": [...],
  "memos": [...],
  "annotations": [...],
  "paradigm_model": {...},
  "saturation_score": 0.85,
  "version": "0.1.0"
}
```

## Import Steps

### Step 1: Locate the session file

Search for session.json in common locations:
- `./session.json`
- `./outputs/session.json`
- `./grounded-evals/outputs/session.json`
- Any path the user specifies

### Step 2: Validate completeness

Check which fields are present and report status:

| Field | Required For | Status |
|-------|-------------|--------|
| agent_spec | All docs | ✓/✗ |
| golden_prompts | Requirements | ✓/✗ |
| codes (codebook) | Requirements, Design | ✓/✗ |
| annotations | Requirements | ✓/✗ |
| paradigm_model | Design | ✓/✗ |
| categories + saturation | All docs | ✓/✗ |
| memos | Context enrichment | ✓/✗ |


### Step 3: Assess readiness for each document

| Document | Minimum Required |
|----------|-----------------|
| requirements.md | agent_spec + codes + annotations (severity ≥ 3) |
| design.md | Above + paradigm_model with causal conditions |
| tasks.md | Above + requirements.md + design.md already generated |

### Step 4: Report gaps

If the session is incomplete, guide the user:

- **Missing annotations:** "Your session has golden queries but no annotations yet.
  Use the annotation workflow to review agent responses."
- **Missing paradigm model:** "Your annotations are complete but root cause analysis
  hasn't been done. Let's build paradigm models for your high-severity failures."
- **Low saturation:** "Some categories have < 3 examples. Consider adding more
  golden queries to reach saturation before generating specs."

### Step 5: Extract and transform

Parse the session.json and prepare data for spec generation:

1. **Build codebook** — Extract all codes with frequency counts and severity stats
2. **Build priority queue** — Score each code: severity × frequency × dimension_weight
3. **Extract paradigm models** — Pull causal analysis for each major failure
4. **Map golden queries** — Link queries to codes and categories
5. **Compute saturation** — Verify coverage claims

### Step 6: Proceed to generation

Once validated, proceed through:
1. `requirements-generation.md` — Generate requirements from codes + annotations
2. `design-generation.md` — Generate design from paradigm models
3. `tasks-generation.md` — Generate tasks from priority queue

---

## Handling Partial Sessions

### No paradigm model
Skip design.md generation. Generate requirements.md and tasks.md only.
Flag that design requires root cause analysis first.

### No severity scores
Default all codes to severity 3 (major). Warn the user that prioritization
will be flat without severity data.

### No memos
Proceed without contextual rationale. Requirements will be less detailed
in their justification sections.

### Multiple session files
If multiple session.json files exist (e.g., different annotation rounds),
merge by taking the latest annotation for each golden query and unioning
all failure codes.
