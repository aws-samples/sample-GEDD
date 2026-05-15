"""Eval agent — runs golden queries against multiple Bedrock models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import boto3
from anthropic import AnthropicBedrock

ANTHROPIC_MODELS = {
    "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "us.anthropic.claude-sonnet-4-5-20241022-v2:0",
    "us.anthropic.claude-opus-4-5-20250115-v1:0",
}


@dataclass
class EvalResult:
    query: str
    responses: dict[str, str] = field(default_factory=dict)


def _call_anthropic(client: AnthropicBedrock, model_id: str, system_prompt: str, query: str) -> str:
    response = client.messages.create(
        model=model_id,
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": query}],
    )
    return response.content[0].text


def _call_converse(bedrock_client, model_id: str, system_prompt: str, query: str) -> str:
    response = bedrock_client.converse(
        modelId=model_id,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": query}]}],
        inferenceConfig={"maxTokens": 512},
    )
    return response["output"]["message"]["content"][0]["text"]


def run_eval(
    queries: list[str],
    model_ids: list[str],
    system_prompt: str,
    region: str = "us-east-1",
) -> list[EvalResult]:
    """Run queries against multiple models and return responses."""
    anthropic_client = AnthropicBedrock(aws_region=region)
    bedrock_client = boto3.client("bedrock-runtime", region_name=region)

    results: list[EvalResult] = []
    for query in queries:
        result = EvalResult(query=query)
        for model_id in model_ids:
            try:
                if model_id in ANTHROPIC_MODELS:
                    result.responses[model_id] = _call_anthropic(
                        anthropic_client, model_id, system_prompt, query
                    )
                else:
                    result.responses[model_id] = _call_converse(
                        bedrock_client, model_id, system_prompt, query
                    )
            except Exception as e:
                result.responses[model_id] = f"[Error: {e}]"
        results.append(result)

    return results


def run_eval_json(
    queries: list[str],
    model_ids: list[str],
    system_prompt: str,
    region: str = "us-east-1",
) -> str:
    """Run eval and return JSON-serializable result."""
    results = run_eval(queries, model_ids, system_prompt, region)
    return json.dumps([{"query": r.query, "responses": r.responses} for r in results])
