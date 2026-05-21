from __future__ import annotations

import json

from grounded_evals.llm.client import get_default_client, get_model_id
from grounded_evals.models.core import Code

STANDARD_ERROR_CATEGORIES = {
    "quality": "Quality of Response — coherence, helpfulness, depth, structure",
    "accuracy": "Accuracy — factual correctness, no hallucinations, verifiable claims",
    "brand_relevance": "Brand Relevance — alignment with company voice, values, guidelines",
    "bias": "Bias — fairness, stereotyping, discrimination, equitable treatment",
    "safety": "Safety — refusal of harmful requests, no dangerous information",
    "completeness": "Completeness — addresses all parts of the query, no missing info",
    "tone": "Tone — appropriate emotional register, empathy, professionalism",
    "instruction_following": "Instruction Following — adherence to system prompt constraints",
}

MAP_PROMPT = """You are mapping error codes from an AI Agent evaluation to standard evaluation categories.

Error codes found during Open Coding:
{error_codes}

Standard evaluation categories:
{standard_categories}

For each error code, assign it to ONE primary standard category and optionally one secondary category. Explain the mapping.

Respond in JSON:
{{
  "mappings": [
    {{
      "error_code": "...",
      "primary_category": "quality|accuracy|brand_relevance|bias|safety|completeness|tone|instruction_following",
      "secondary_category": null or "...",
      "rationale": "..."
    }}
  ]
}}"""


class ErrorMapping:
    def __init__(
        self,
        error_code: str,
        primary_category: str,
        secondary_category: str | None = None,
        rationale: str = "",
    ):
        self.error_code = error_code
        self.primary_category = primary_category
        self.secondary_category = secondary_category
        self.rationale = rationale


def map_errors_to_categories(
    error_codes: list[Code],
) -> list[ErrorMapping]:
    if not error_codes:
        return []

    client = get_default_client()
    model_id = get_model_id()

    codes_text = "\n".join(f"- {c.label}: {c.definition}" for c in error_codes)
    cats_text = "\n".join(f"- {k}: {v}" for k, v in STANDARD_ERROR_CATEGORIES.items())

    prompt = MAP_PROMPT.format(error_codes=codes_text, standard_categories=cats_text)

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
        raise RuntimeError(f"map_errors_to_categories: failed to parse LLM response — {e}") from e

    return [
        ErrorMapping(
            error_code=m["error_code"],
            primary_category=m["primary_category"],
            secondary_category=m.get("secondary_category"),
            rationale=m.get("rationale", ""),
        )
        for m in data.get("mappings", [])
    ]
