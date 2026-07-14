# LLM-as-Judge Gate Generation

Generate an LLM-as-Judge response gate from the same SME annotations used for the Kiro judge-subagent `requirements.md`.

## Purpose

The judge is the second core GEDD output. It should not score generic helpfulness first. It should enforce the domain failure modes named by SMEs during error analysis before candidate customer-facing responses are shown.

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
# LLM-as-Judge Gate: {Agent Name}

## Objective
Evaluate whether a candidate customer-facing agent response violates the domain failure modes discovered by SME error analysis.

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
  "recommended_action": "allow | revise_response | request_human_review",
  "customer_visible_block": true
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
| Catastrophic | `request_human_review` and `customer_visible_block=true` |
| Critical | `request_human_review` and `customer_visible_block=true` |
| High | `revise_response` unless explicitly waived |
| Medium | `revise_response` |
| Low | `allow` with note |

## Quality Checks

Before finalizing:

- The judge covers every high-severity failure in `requirements.md`.
- The output contract is deterministic enough for automation.
- Failure codes use domain language, not generic labels like `bad_response`.
- Passing examples are not merely harmless; they demonstrate the required domain behavior.
- The judge can explain why a response failed without inventing new facts.
