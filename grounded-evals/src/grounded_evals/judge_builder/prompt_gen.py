from __future__ import annotations

from grounded_evals.models.core import JudgeRubric

JUDGE_TEMPLATE = """You are an expert evaluator assessing AI Agent responses. Score each response on the following criteria, using the 1-5 scale defined for each.

## Evaluation Criteria

{criteria_section}

## Scoring Instructions

For each criterion:
1. Read the user query and agent response carefully
2. Consider the specific failure patterns identified for each criterion
3. Assign a score from 1-5 using the rubric
4. Provide a brief justification (1-2 sentences)

## Output Format

For each query-response pair, output:
```json
{{
  "scores": {{
    {score_keys}
  }},
  "justifications": {{
    {justification_keys}
  }},
  "overall_score": <weighted average>,
  "pass": <true if overall >= 3.5, false otherwise>,
  "summary": "<one sentence overall assessment>"
}}
```

## Context
Agent Name: {agent_name}
Agent Description: {agent_description}
"""


def generate_judge_prompt(rubric: JudgeRubric, agent_name: str = "", agent_description: str = "") -> str:
    criteria_lines = []
    for criterion in rubric.criteria:
        criteria_lines.append(f"### {criterion.name}")
        criteria_lines.append(f"**What it measures:** {criterion.description}")
        criteria_lines.append(f"**Weight:** {criterion.weight}")
        criteria_lines.append("**Scoring:**")
        for score, desc in sorted(criterion.scoring_rubric.items(), reverse=True):
            criteria_lines.append(f"  - {score}/5: {desc}")
        criteria_lines.append("")

    score_keys = ",\n    ".join(
        f'"{c.name.lower().replace(" ", "_")}": <1-5>' for c in rubric.criteria
    )
    justification_keys = ",\n    ".join(
        f'"{c.name.lower().replace(" ", "_")}": "<reason>"' for c in rubric.criteria
    )

    return JUDGE_TEMPLATE.format(
        criteria_section="\n".join(criteria_lines),
        score_keys=score_keys,
        justification_keys=justification_keys,
        agent_name=agent_name or "AI Agent",
        agent_description=agent_description or "An AI assistant",
    )
