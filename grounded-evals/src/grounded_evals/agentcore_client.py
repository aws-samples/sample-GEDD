"""Client for invoking the Agent Playground agent deployed on AgentCore Runtime.

Used by the NiceGUI UI to call the remote agent instead of running the LLM loop locally.
Falls back to local mode when AGENTCORE_AGENT_ID is not set.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import boto3


@dataclass
class CoachResponse:
    """Response from the coach agent."""

    text: str
    tool_executions: list[dict] = field(default_factory=list)
    updated_state: dict = field(default_factory=dict)
    messages: list[dict] = field(default_factory=list)


@dataclass
class EvalResponse:
    """Response from the eval agent."""

    results: list[dict] = field(default_factory=list)
    error: str = ""


class AgentCoreClient:
    """Client for invoking AgentCore-hosted agents."""

    def __init__(
        self,
        agent_runtime_arn: str | None = None,
        region: str | None = None,
    ):
        self.agent_runtime_arn = agent_runtime_arn or os.environ.get("AGENTCORE_AGENT_ARN", "")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "bedrock-agent-runtime",
                region_name=self.region,
            )
        return self._client

    def invoke_coach(
        self,
        user_message: str,
        session_id: str,
        session_state: dict,
        messages: list[dict],
    ) -> CoachResponse:
        """Invoke the coach agent for a conversation turn."""
        payload = json.dumps({
            "request_type": "coach",
            "user_message": user_message,
            "session_state": session_state,
            "messages": messages,
        })

        response = self.client.invoke_agent(
            agentId=self._extract_agent_id(),
            agentAliasId=os.environ.get("AGENTCORE_ALIAS_ID", "TSTALIASID"),
            sessionId=session_id,
            inputText=payload,
        )

        result_text = self._read_completion_stream(response)

        try:
            result = json.loads(result_text)
            return CoachResponse(
                text=result.get("text", ""),
                tool_executions=result.get("tool_executions", []),
                updated_state=result.get("updated_state", {}),
                messages=result.get("messages", []),
            )
        except (json.JSONDecodeError, KeyError):
            return CoachResponse(text=result_text)

    def invoke_eval(
        self,
        queries: list[str],
        model_ids: list[str],
        system_prompt: str,
        session_id: str,
    ) -> EvalResponse:
        """Invoke the eval agent for multi-model comparison."""
        payload = json.dumps({
            "request_type": "eval",
            "queries": queries,
            "model_ids": model_ids,
            "system_prompt": system_prompt,
        })

        response = self.client.invoke_agent(
            agentId=self._extract_agent_id(),
            agentAliasId=os.environ.get("AGENTCORE_ALIAS_ID", "TSTALIASID"),
            sessionId=session_id,
            inputText=payload,
        )

        result_text = self._read_completion_stream(response)

        try:
            result = json.loads(result_text)
            if result.get("error"):
                return EvalResponse(error=result["error"])
            return EvalResponse(results=result.get("results", []))
        except (json.JSONDecodeError, KeyError):
            return EvalResponse(error=f"Failed to parse response: {result_text[:200]}")

    def _extract_agent_id(self) -> str:
        """Extract agent ID from ARN or env var."""
        agent_id = os.environ.get("AGENTCORE_AGENT_ID", "")
        if agent_id:
            return agent_id
        if self.agent_runtime_arn:
            parts = self.agent_runtime_arn.split("/")
            return parts[-1] if parts else ""
        raise ValueError("AGENTCORE_AGENT_ID or AGENTCORE_AGENT_ARN must be set")

    def _read_completion_stream(self, response: dict) -> str:
        """Read the streaming completion from an invoke_agent response."""
        chunks: list[str] = []
        completion = response.get("completion", [])
        for event in completion:
            if "chunk" in event:
                chunk_bytes = event["chunk"].get("bytes", b"")
                if isinstance(chunk_bytes, bytes):
                    chunks.append(chunk_bytes.decode("utf-8"))
                else:
                    chunks.append(str(chunk_bytes))
        return "".join(chunks)


def get_agentcore_client() -> AgentCoreClient | None:
    """Return an AgentCoreClient if configured, else None (local mode)."""
    if os.environ.get("AGENTCORE_AGENT_ID") or os.environ.get("AGENTCORE_AGENT_ARN"):
        return AgentCoreClient()
    return None
