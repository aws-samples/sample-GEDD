from __future__ import annotations

import json

from pydantic import BaseModel, Field

from grounded_evals.llm.client import get_default_client, get_model_id
from grounded_evals.models.core import Category, GoldenPrompt


class ComparisonResult(BaseModel):
    is_unique: bool = True
    similar_existing: list[str] = Field(default_factory=list)
    gaps_filled: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    explanation: str = ""


COMPARE_PROMPT = """You are applying the Constant Comparison method from qualitative research. Given an existing set of golden evaluation prompts and a new candidate prompt, determine:

1. Is this new prompt UNIQUE — does it test something not already covered?
2. Which existing prompts (if any) are SIMILAR to it?
3. What GAPS does this new prompt fill in the evaluation coverage?
4. What SUGGESTIONS would you make for better prompts to fill remaining gaps?

Existing prompts:
{existing_prompts}

Categories being tested:
{categories}

New candidate prompt: "{new_prompt}"

Respond in JSON:
{{
  "is_unique": true/false,
  "similar_existing": ["list of similar existing prompts if any"],
  "gaps_filled": ["what new coverage this prompt adds"],
  "suggestions": ["suggestions for other prompts to try"],
  "explanation": "brief explanation of your comparison"
}}"""


def constant_comparison(
    new_prompt: str,
    existing_prompts: list[GoldenPrompt],
    categories: list[Category],
) -> ComparisonResult:
    if not existing_prompts:
        return ComparisonResult(
            is_unique=True,
            explanation="First prompt in the dataset — unique by definition.",
            gaps_filled=["Initial coverage"],
        )

    client = get_default_client()
    model_id = get_model_id()

    existing_text = "\n".join(
        f"- {p.prompt_text}" for p in existing_prompts[:50]
    )
    categories_text = "\n".join(
        f"- {c.name}: {c.definition}" for c in categories
    )

    prompt = COMPARE_PROMPT.format(
        existing_prompts=existing_text,
        categories=categories_text,
        new_prompt=new_prompt,
    )

    message = client.messages.create(
        model=model_id,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    json_start = response_text.find("{")
    json_end = response_text.rfind("}") + 1
    data = json.loads(response_text[json_start:json_end])

    return ComparisonResult(**data)
