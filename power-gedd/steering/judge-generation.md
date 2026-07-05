# LLM Judge Generation

Generate an LLM-as-a-Judge release gate from the same SME annotations used for Kiro `requirements.md`.

## Purpose

The judge is the second core GEDD output. It should not score generic helpfulness first. It should enforce the domain failure modes named by SMEs during error analysis.

Generate:

```text
.kiro/specs/{agent-name}/llm-judge.md
```

## Inputs

Required:

- Agent name and task boundary
- Golden queries or representative traces
- SME verdicts
- Failure codes
- Severity labels
- Memos or release-gate notes

Preferred:

- Codebook definitions
- EARS acceptance criteria from `requirements.md`
- Sample passing and failing responses
- Saturation evidence

## Judge Structure

Use this structure:

```markdown
# LLM Judge: {Agent Name}

## Objective
Evaluate whether an agent response violates the domain failure modes discovered by SME error analysis.

## Domain Failure Modes
| Code | Severity | Definition | Release Gate |
|------|----------|------------|--------------|

## Evaluation Instructions
1. Read the user query, agent response, and any available context.
2. Check each failure code before assigning pass.
3. Fail the response if it triggers any critical or catastrophic release gate.
4. Cite the observed evidence and requirement id when possible.

## Output Contract
Return only valid JSON:
{
  "pass_fail": "pass | fail",
  "failure_code": "domain failure label or null",
  "severity": "low | medium | high | critical | catastrophic",
  "rationale": "short explanation tied to evidence",
  "evidence_references": ["query id", "requirement id"],
  "recommended_action": "ship | revise | block release"
}

## Calibration Examples
### Failing Example
...

### Passing Example
...
```

## Mapping Rules

For each failure code:

1. Use the SME's label as the judge category.
2. Use the codebook definition as the detection rule.
3. Use severity to determine release action.
4. Use memos as rationale language.
5. Link back to the matching Kiro requirement when available.

## Release Action Rules

| Severity | Recommended Action |
|----------|--------------------|
| Catastrophic | `block release` |
| Critical | `block release` |
| High | `revise` unless explicitly waived |
| Medium | `revise` |
| Low | `ship` with note |

## Quality Checks

Before finalizing:

- The judge covers every high-severity failure in `requirements.md`.
- The output contract is deterministic enough for automation.
- Failure codes use domain language, not generic labels like `bad_response`.
- Passing examples are not merely harmless; they demonstrate the required domain behavior.
- The judge can explain why a response failed without inventing new facts.
