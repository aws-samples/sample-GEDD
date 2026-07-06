# Session Import Workflow

Guide for importing a GEDD error-analysis markdown file into the baseline-to-improved generation pipeline.

## What is SME_error_analysis.md?

The `SME_error_analysis.md` file is the canonical handoff artifact from the GEDD web app or CLI.
It contains structured domain profile, curated query, baseline response, and annotation evidence in a human-readable, LLM-optimized markdown format.

Export it from:
- **Web app:** Outputs page or session export
- **CLI:** `grounded-evals export-md --session session.json`

## Expected Structure

```markdown
# SME Error Analysis — {Agent Name}

## Domain Expert Profile
- **Domain Context:** SME domain, regulatory context, and risk posture
- **Name:** AgentName
- **Description:** What the agent does
- **Capabilities:** cap1, cap2, ...
- **Target Users:** user1, user2, ...
- **Known Edge Cases:** edge1, edge2, ...
- **Constraints:** hard rule1, hard rule2, ...

### System Prompt
(the agent's system prompt)

## Curated Domain Queries ({n} total, {saturation}% saturated)
| # | Query | Category | Expected Behavior |
|---|-------|----------|-------------------|

## Baseline Responses
| # | Query | Baseline Response | Baseline Requirement Version |
|---|-------|-------------------|------------------------------|

## Annotations Summary
- **Total:** N | Correct: X | Partial: Y | Incorrect: Z

## Failure Codebook
| Code | Severity | Freq | Definition |
|------|----------|------|------------|

## Paradigm Model
### Phenomenon
### Causal Conditions
### Context
### Intervening Conditions
### Action Strategies
### Consequences

## Annotated Failures ({n} examples)
### Example N [verdict]
**Query:** ...
**Response:** ...
**Codes:** ...
**Severity: X | Confidence: Y**
**Memo:** ...

## Saturation Evidence
| Category | Queries | Status |
|----------|---------|--------|

## Memos
- [Code] memo text...

## Judge Prompt
(generated judge prompt text)
```

## Import Steps

### Step 1: Locate the error analysis file

Search for the markdown file in common locations:
- `./SME_error_analysis.md`
- `./*_SME_error_analysis.md`
- `./*_error_analysis.md`
- `./error-analysis.md`
- `./outputs/*_error_analysis.md`
- Any path the user specifies

Also check for legacy `session.json` files. If only a session.json exists,
suggest the user run `grounded-evals export-md` to generate the markdown.

### Step 2: Parse and validate completeness

Extract each section and report status:

| Section | Required For | Status |
|---------|-------------|--------|
| Domain Expert Profile | Both outputs | ✓/✗ |
| Curated Domain Queries | Requirements, Judge | ✓/✗ |
| Baseline Responses | Requirements, Judge, Measurement | ✓/✗ |
| Failure Codebook | Requirements, Judge | ✓/✗ |
| Annotated Failures | Requirements, Judge | ✓/✗ |
| Paradigm Model | Requirement rationale | ✓/✗ |
| Saturation Evidence | Output confidence | ✓/✗ |
| Memos | Context enrichment | ✓/✗ |

### Step 3: Assess readiness for each output

| Output | Minimum Required |
|--------|-----------------|
| requirements.md | Domain Expert Profile + Curated Queries + Baseline Responses + Codebook + Annotated Failures (severity ≥ critical) |
| llm-judge.md | Domain Expert Profile + Codebook + Annotated Failures + release-gate memos |

### Step 4: Report gaps

If the file is incomplete, guide the user:

- **Missing annotations:** "Your file has curated queries but no annotated failures.
  Use the annotation workflow to review baseline agent responses."
- **Missing paradigm model:** "Your annotations are complete but root cause analysis
  hasn't been done. Let's build paradigm models for your high-severity failures."
- **Low saturation:** "Some categories show missing coverage. Consider adding more
  curated domain queries to reach saturation before generating specs."
- **No codebook:** "No failure codes found. The domain expert needs to annotate
  agent responses and name the failure patterns first."

### Step 5: Extract and transform

Parse the markdown sections and prepare data for spec generation:

1. **Build codebook** — Extract from the Failure Codebook table (Code, Severity, Freq, Definition)
2. **Build priority queue** — Score each code: severity × frequency × dimension_weight
3. **Extract paradigm models** — Parse the Paradigm Model section lists
4. **Map curated queries** — Parse the Curated Domain Queries table for categories and expected behavior
5. **Map baseline responses** — Parse baseline responses and link them to curated queries
6. **Compute saturation** — Read the Saturation Evidence table

### Step 6: Proceed to generation

Once validated, proceed through:
1. `requirements-generation.md` — Improve Kiro requirements from curated queries, baseline responses, codebook, and annotated failures
2. `judge-generation.md` — Generate the LLM Judge from the same failure modes

Only run `design-generation.md` or `tasks-generation.md` if the user explicitly asks for Kiro follow-on docs after the two GEDD outputs are complete.

---

## Handling Partial Files

### No paradigm model section
Proceed with requirements.md and llm-judge.md. Flag that root-cause rationale is weaker without paradigm model evidence.

### No severity in codebook
Default all codes to severity "functional". Warn the user that prioritization
will be flat without severity data.

### No memos
Proceed without contextual rationale. Requirements will be less detailed
in their justification sections.

### Multiple error analysis files
If multiple files exist (e.g., different annotation rounds), merge by:
- Taking the file with more annotated failures
- Unioning all failure codes from both codebooks
- Using the most complete paradigm model

### Legacy session.json found
If only a `session.json` exists (no markdown), instruct:
```
grounded-evals export-md --session session.json --output SME_error_analysis.md
```
Then proceed with the markdown file.
