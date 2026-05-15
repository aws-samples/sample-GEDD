"""Centralized LLM client for Amazon Bedrock with LangSmith tracing.

Uses AnthropicBedrock with IAM credentials (boto3 credential chain).
All LLM calls are traced to LangSmith for observability.

Configuration via environment variables:
  AWS_REGION             - AWS region (default: us-east-1)
  BEDROCK_MODEL_ID       - Override model ID
  ANTHROPIC_API_KEY      - Fallback: direct Anthropic API (local dev)

LangSmith tracing (optional — works without it):
  LANGSMITH_API_KEY      - LangSmith API key
  LANGSMITH_PROJECT      - Project name (default: "agent-playground")
  LANGSMITH_TRACING      - Set to "true" to enable (auto-enabled if API key set)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from anthropic import Anthropic, AnthropicBedrock

try:
    from langsmith import traceable
except ImportError:
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        if args and callable(args[0]):
            return args[0]
        return decorator

DEFAULT_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
DEFAULT_REGION = "us-east-1"


def _langsmith_enabled() -> bool:
    return bool(os.environ.get("LANGSMITH_API_KEY"))


@dataclass
class LLMConfig:
    api_key: str = ""
    region: str = DEFAULT_REGION
    model_id: str = DEFAULT_MODEL_ID
    provider: str = "bedrock"

    @classmethod
    def from_env(cls) -> LLMConfig:
        # Direct Anthropic API (highest priority — simple and always works)
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if anthropic_key:
            return cls(
                api_key=anthropic_key,
                model_id=os.environ.get("BEDROCK_MODEL_ID", "claude-sonnet-4-6-20250514"),
                provider="anthropic",
            )

        # Standard Bedrock (IAM via boto3 credential chain)
        region = (
            os.environ.get("AWS_REGION", "")
            or os.environ.get("AWS_DEFAULT_REGION", DEFAULT_REGION)
        )
        return cls(
            region=region,
            model_id=os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID),
            provider="bedrock",
        )

    @classmethod
    def from_yaml(cls, path: Path | str) -> LLMConfig:
        path = Path(path)
        if not path.exists():
            return cls.from_env()
        with path.open() as f:
            data = yaml.safe_load(f) or {}
        llm_data = data.get("llm", data)
        return cls(
            api_key=llm_data.get("api_key", ""),
            region=llm_data.get("region", DEFAULT_REGION),
            model_id=llm_data.get("model_id", DEFAULT_MODEL_ID),
            provider=llm_data.get("provider", "bedrock"),
        )


def get_client(config: LLMConfig | None = None) -> Anthropic | AnthropicBedrock:
    if config is None:
        config = LLMConfig.from_env()

    if config.provider == "anthropic" and config.api_key:
        return Anthropic(api_key=config.api_key)

    return AnthropicBedrock(aws_region=config.region)


_config: LLMConfig | None = None
_client: Anthropic | AnthropicBedrock | None = None


def get_default_client() -> Anthropic | AnthropicBedrock:
    global _config, _client
    if _client is None:
        _config = LLMConfig.from_env()
        _client = get_client(_config)
    return _client


def get_model_id(config: LLMConfig | None = None) -> str:
    if config is None:
        global _config
        if _config is None:
            _config = LLMConfig.from_env()
        return _config.model_id
    return config.model_id


# === LangSmith-traced wrappers for all LLM calls ===


@traceable(run_type="llm", name="coach_conversation")
def traced_coach_call(
    client: Anthropic | AnthropicBedrock,
    model: str,
    system: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    max_tokens: int = 2048,
):
    """Traced LLM call for the coaching conversation."""
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
    return client.messages.create(**kwargs)


@traceable(run_type="llm", name="eval_agent_query")
def traced_eval_call(
    client: Anthropic | AnthropicBedrock,
    model: str,
    system_prompt: str,
    query: str,
):
    """Traced LLM call for running a golden query against an agent model."""
    return client.messages.create(
        model=model,
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": query}],
    )


@traceable(name="run_golden_eval_batch")
def traced_eval_batch(
    client: Anthropic | AnthropicBedrock,
    system_prompt: str,
    queries: list[str],
    model_ids: list[str],
) -> list[dict]:
    """Traced batch evaluation — runs all golden queries against multiple models."""
    results = []
    for query in queries:
        responses = {}
        for model_id in model_ids:
            try:
                response = traced_eval_call(client, model_id, system_prompt, query)
                responses[model_id] = response.content[0].text
            except Exception as e:
                responses[model_id] = f"[Error: {e}]"
        results.append({"query": query, "responses": responses})
    return results
