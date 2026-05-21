from __future__ import annotations

import json

from grounded_evals.llm.client import get_default_client, get_model_id
from grounded_evals.models.core import Category, Code, ParadigmModel

PARADIGM_PROMPT = """You are an expert qualitative researcher applying Axial Coding to organize error patterns from an AI Agent evaluation.

Axial Coding uses the Paradigm Model to relate categories:
- Causal Conditions: What causes this error pattern?
- Phenomenon: The central error pattern being analyzed
- Context: The specific conditions under which this error occurs
- Intervening Conditions: Broader factors that influence the error
- Action/Interaction Strategies: How the agent responds (correctly or incorrectly)
- Consequences: What happens as a result of this error

Given these error codes discovered during Open Coding:
{error_codes}

And these evaluation dimensions:
{dimensions}

Build a Paradigm Model that explains the relationships between these error patterns. Group related errors and identify the central phenomenon.

Respond in JSON:
{{
  "phenomenon": {{"name": "...", "definition": "..."}},
  "causal_conditions": [{{"name": "...", "definition": "..."}}],
  "context": [{{"name": "...", "definition": "..."}}],
  "intervening_conditions": [{{"name": "...", "definition": "..."}}],
  "action_strategies": [{{"name": "...", "definition": "..."}}],
  "consequences": [{{"name": "...", "definition": "..."}}]
}}"""

STANDARD_DIMENSIONS = [
    "Quality of Response",
    "Accuracy",
    "Brand Relevance",
    "Bias",
    "Safety",
    "Completeness",
    "Tone Appropriateness",
    "Instruction Following",
]


def build_paradigm_model(
    error_codes: list[Code],
    categories: list[Category],
) -> ParadigmModel:
    client = get_default_client()
    model_id = get_model_id()

    codes_text = "\n".join(
        f"- {c.label}: {c.definition}" for c in error_codes
    )
    dims_text = "\n".join(f"- {d}" for d in STANDARD_DIMENSIONS)

    prompt = PARADIGM_PROMPT.format(error_codes=codes_text, dimensions=dims_text)

    message = client.messages.create(
        model=model_id,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    try:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start == -1 or json_end <= json_start:
            raise ValueError("No JSON object found in response")
        data = json.loads(response_text[json_start:json_end])
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"build_paradigm_model: failed to parse LLM response — {e}") from e

    def make_category(d: dict) -> Category:  # type: ignore[type-arg]
        return Category(name=d["name"], definition=d.get("definition", ""))

    return ParadigmModel(
        phenomenon=make_category(data["phenomenon"]),
        causal_conditions=[make_category(c) for c in data.get("causal_conditions", [])],
        context=[make_category(c) for c in data.get("context", [])],
        intervening_conditions=[make_category(c) for c in data.get("intervening_conditions", [])],
        action_strategies=[make_category(c) for c in data.get("action_strategies", [])],
        consequences=[make_category(c) for c in data.get("consequences", [])],
    )
