"""Constitutional LLM-as-a-Judge evaluation.

Inspired by Constitutional AI (Bai et al., 2022, Anthropic) and adapted for
structured error-mode detection. Instead of a single monolithic rubric, the agent
evaluates each error principle in sequence — a "chain of checks" approach.

Why this matters vs a plain rubric:
  - Forces the judge to reason about each failure mode independently.
  - Prevents anchoring: the judge can't assign a mediocre overall score and stop.
  - Produces per-principle verdicts traceable back to specific error codes.
  - Mirrors how a human expert actually reviews (checking a mental checklist).

Data sources used:
  - codebook: each entry becomes one Constitutional Principle.
  - paradigm_model: causal conditions provide the "why" for each principle.
  - coding_annotations: discriminating examples make each principle concrete.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from grounded_evals.llm.client import get_default_client, get_model_id


@dataclass
class ConstitutionalPrinciple:
    """One check derived from a qualitative error code."""
    code_name: str
    definition: str
    causal_trigger: str            # why the agent fails this way
    discriminating_example: str    # real annotated example (positive)
    dimension: str = ""            # standard eval dimension (accuracy, completeness…)


@dataclass
class ConstitutionalVerdict:
    """Result of applying constitutional evaluation to one response."""
    query: str
    response: str
    principle_verdicts: list[dict]   # [{code, violated, reasoning, severity}]
    violated_codes: list[str]
    overall_pass: bool
    confidence: str                  # "high" | "medium" | "low"
    summary: str


_CONSTITUTIONAL_PROMPT = """\
You are a meticulous AI evaluator applying a structured checklist to assess an agent response. \
For each principle below, determine whether the response VIOLATES it. Think step by step for each check.

## Constitutional Principles (derived from qualitative error analysis)

{principles_block}

## Response to Evaluate

<query>{query}</query>
<response>{response}</response>

## Instructions

For EACH principle, output:
1. A brief analysis (1-2 sentences of reasoning)
2. VIOLATED or CLEAR
3. Severity if violated: cosmetic | functional | critical | catastrophic

Then give an overall verdict.

Respond in JSON:
{{
  "principle_verdicts": [
    {{
      "code": "...",
      "reasoning": "...",
      "violated": true/false,
      "severity": "critical|functional|cosmetic|null"
    }}
  ],
  "violated_codes": ["...", "..."],
  "overall_pass": true/false,
  "confidence": "high|medium|low",
  "summary": "One sentence overall assessment."
}}"""


def build_constitutional_principles(
    codebook: list[dict],
    paradigm: dict,
    coding_annotations: list[dict],
    error_mappings: list[dict] | None = None,
) -> list[ConstitutionalPrinciple]:
    """Convert Open Coding artifacts into constitutional principles.

    Each error code in the codebook becomes one principle. The principle is
    enriched with:
      - A causal trigger from the Paradigm Model
      - A discriminating example from coding annotations (highest severity)
      - The evaluation dimension from the error mappings (if available)
    """
    causal = paradigm.get("causal_conditions", [])
    causal_text = "; ".join(c if isinstance(c, str) else c.get("name", "") for c in causal)

    # Build a code→dimension map from error mappings
    code_to_dim: dict[str, str] = {}
    if error_mappings:
        for m in error_mappings:
            code_to_dim[m.get("error_code", "")] = m.get("primary_category", "")

    # Find best positive example per code (highest severity + confidence)
    _sev = {"catastrophic": 4, "critical": 3, "functional": 2, "cosmetic": 1, "": 0}
    _conf = {"high": 3, "medium": 2, "low": 1, "": 0}

    code_to_example: dict[str, str] = {}
    for ann in sorted(
        coding_annotations,
        key=lambda a: (_sev.get(a.get("severity", ""), 0), _conf.get(a.get("confidence", ""), 0)),
        reverse=True,
    ):
        for code in ann.get("codes", []):
            if code not in code_to_example:
                q = ann.get("query", "")[:120]
                r = ann.get("response", "")[:200]
                note = ann.get("memo", "")[:120]
                code_to_example[code] = f'Query: "{q}" → Response: "{r}". Annotator note: {note}' if note else f'Query: "{q}" → Response: "{r}"'

    principles: list[ConstitutionalPrinciple] = []
    for code_entry in codebook:
        name = code_entry.get("name", "")
        defn = code_entry.get("definition", "")
        principles.append(ConstitutionalPrinciple(
            code_name=name,
            definition=defn,
            causal_trigger=causal_text or "Unknown trigger",
            discriminating_example=code_to_example.get(name, "No example available yet."),
            dimension=code_to_dim.get(name, ""),
        ))
    return principles


def _format_principles_block(principles: list[ConstitutionalPrinciple]) -> str:
    lines: list[str] = []
    for i, p in enumerate(principles, 1):
        dim_note = f" [{p.dimension.replace('_', ' ').title()}]" if p.dimension else ""
        lines += [
            f"### Principle {i}: NO {p.code_name.upper()}{dim_note}",
            f"**Definition:** {p.definition}",
            f"**Why agents fail this way:** {p.causal_trigger}",
            f"**Real example of this violation:** {p.discriminating_example}",
            "",
        ]
    return "\n".join(lines)


def constitutional_judge(
    query: str,
    response: str,
    principles: list[ConstitutionalPrinciple],
    client=None,
    model_id: str | None = None,
) -> ConstitutionalVerdict:
    """Apply constitutional evaluation to a single query-response pair."""
    if client is None:
        client = get_default_client()
    if model_id is None:
        model_id = get_model_id()

    principles_block = _format_principles_block(principles)
    prompt = _CONSTITUTIONAL_PROMPT.format(
        principles_block=principles_block,
        query=query[:500],
        response=response[:800],
    )

    message = client.messages.create(
        model=model_id,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text

    try:
        j_start = text.find("{")
        j_end = text.rfind("}") + 1
        data = json.loads(text[j_start:j_end])
    except (json.JSONDecodeError, ValueError):
        return ConstitutionalVerdict(
            query=query, response=response,
            principle_verdicts=[], violated_codes=[],
            overall_pass=False, confidence="low",
            summary="Parse error — could not extract verdict from LLM response.",
        )

    return ConstitutionalVerdict(
        query=query,
        response=response,
        principle_verdicts=data.get("principle_verdicts", []),
        violated_codes=data.get("violated_codes", []),
        overall_pass=data.get("overall_pass", True),
        confidence=data.get("confidence", "medium"),
        summary=data.get("summary", ""),
    )


def build_constitutional_judge_prompt(
    principles: list[ConstitutionalPrinciple],
    agent_name: str = "",
    agent_description: str = "",
) -> str:
    """Generate a static constitutional judge prompt (no LLM call — for export)."""
    principles_block = _format_principles_block(principles)
    header = (
        f"You are evaluating responses from {agent_name or 'an AI agent'}"
        + (f" ({agent_description})" if agent_description else "")
        + ". Apply each principle below as an independent check."
    )
    return (
        f"{header}\n\n"
        f"{principles_block}\n"
        "<query>{query}</query>\n"
        "<response>{response}</response>\n\n"
        "For each principle: briefly reason, then state VIOLATED or CLEAR and severity.\n"
        "Output JSON with principle_verdicts, violated_codes, overall_pass, confidence, summary."
    )
