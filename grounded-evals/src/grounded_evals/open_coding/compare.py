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
    try:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start == -1 or json_end <= json_start:
            raise ValueError("No JSON object found in response")
        data = json.loads(response_text[json_start:json_end])
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"constant_comparison: failed to parse LLM response — {e}") from e

    return ComparisonResult(**data)


class CodeComparisonResult(BaseModel):
    is_duplicate: bool = False
    similar_codes: list[str] = Field(default_factory=list)
    merge_suggestion: str = ""
    explanation: str = ""


CODE_COMPARE_PROMPT = """You are helping a researcher organize error codes from qualitative coding of AI agent failures.

New code being added: "{new_code}"

Existing codes in the codebook:
{existing_codes}

Determine:
1. Is the new code essentially a duplicate or very similar in meaning to an existing one?
2. Which existing codes overlap with it (if any)?
3. If similar codes exist, suggest a single unified label that captures the meaning of both.

Respond in JSON only:
{{
  "is_duplicate": true or false,
  "similar_codes": ["list of existing codes that overlap"],
  "merge_suggestion": "unified label if merging makes sense, empty string otherwise",
  "explanation": "one sentence"
}}"""


def compare_codes(new_code: str, existing_codes: list[str]) -> CodeComparisonResult:
    """Check if a new error code overlaps semantically with existing codebook entries."""
    if not existing_codes:
        return CodeComparisonResult(explanation="First code — unique by definition.")

    client = get_default_client()
    model_id = get_model_id()

    prompt = CODE_COMPARE_PROMPT.format(
        new_code=new_code,
        existing_codes="\n".join(f"- {c}" for c in existing_codes),
    )
    message = client.messages.create(
        model=model_id,
        max_tokens=256,
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
        raise RuntimeError(f"compare_codes: failed to parse LLM response — {e}") from e
    return CodeComparisonResult(**data)
