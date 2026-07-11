"""Client for invoking the Agent Playground agent deployed on AgentCore Runtime.

Used by the NiceGUI UI to call the remote agent instead of running the LLM loop locally.
Falls back to local mode when AGENTCORE_AGENT_ID or AGENTCORE_AGENT_ARN is not set.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


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
        self.agent_runtime_id = os.environ.get("AGENTCORE_AGENT_ID", "")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self._client = None
        self._control = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client("bedrock-agentcore", region_name=self.region)
        return self._client

    @property
    def control(self):
        if self._control is None:
            self._control = boto3.client("bedrock-agentcore-control", region_name=self.region)
        return self._control

    def invoke_coach(
        self,
        user_message: str,
        session_id: str,
        session_state: dict,
        messages: list[dict],
    ) -> CoachResponse:
        """Invoke the coach agent for a conversation turn."""
        payload = {
            "request_type": "coach",
            "user_message": user_message,
            "session_state": session_state,
            "messages": messages,
        }

        result_text = self._invoke_runtime(payload, session_id)

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
        payload = {
            "request_type": "eval",
            "queries": queries,
            "model_ids": model_ids,
            "system_prompt": system_prompt,
        }

        result_text = self._invoke_runtime(payload, session_id)

        try:
            result = json.loads(result_text)
            if result.get("error"):
                return EvalResponse(error=result["error"])
            return EvalResponse(results=result.get("results", []))
        except (json.JSONDecodeError, KeyError):
            return EvalResponse(error=f"Failed to parse response: {result_text[:200]}")

    def _invoke_runtime(self, payload: dict, session_id: str) -> str:
        """Invoke the AgentCore runtime and return the raw response text."""
        args = {
            "agentRuntimeArn": self._get_agent_runtime_arn(),
            "runtimeSessionId": session_id,
            "contentType": "application/json",
            "accept": "application/json",
            "payload": json.dumps(payload).encode("utf-8"),
        }
        qualifier = os.environ.get("AGENTCORE_QUALIFIER") or os.environ.get(
            "AGENTCORE_ENDPOINT_NAME"
        )
        if qualifier:
            args["qualifier"] = qualifier

        try:
            response = self.client.invoke_agent_runtime(**args)
        except KeyError as exc:
            raise RuntimeError(
                "AgentCore runtime configuration is invalid. Set AGENTCORE_AGENT_ARN "
                "to the full runtime ARN, or set AGENTCORE_AGENT_ID to a valid runtime id."
            ) from exc
        except NoCredentialsError as exc:
            raise RuntimeError(
                "AWS credentials not found. Configure AWS credentials for AgentCore."
            ) from exc
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            msg = exc.response["Error"]["Message"]
            raise RuntimeError(f"AgentCore invoke failed ({code}): {msg}") from exc

        return self._read_runtime_response(response)

    def _get_agent_runtime_arn(self) -> str:
        """Return the full AgentCore runtime ARN, resolving a short id if needed."""
        configured = (self.agent_runtime_arn or self.agent_runtime_id).strip()
        if not configured:
            raise ValueError("AGENTCORE_AGENT_ID or AGENTCORE_AGENT_ARN must be set")
        if configured.startswith("arn:"):
            self.agent_runtime_arn = configured
            return configured

        try:
            response = self.control.get_agent_runtime(agentRuntimeId=configured)
        except NoCredentialsError as exc:
            raise RuntimeError(
                "AWS credentials not found. Configure AWS credentials for AgentCore."
            ) from exc
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            msg = exc.response["Error"]["Message"]
            raise RuntimeError(f"Unable to resolve AgentCore runtime id ({code}): {msg}") from exc

        arn = response.get("agentRuntimeArn", "")
        if not arn:
            raise RuntimeError(f"Unable to resolve AgentCore runtime ARN for id: {configured}")
        self.agent_runtime_arn = arn
        return arn

    def _read_runtime_response(self, response: dict) -> str:
        """Read the streaming response body from invoke_agent_runtime."""
        body = response.get("response", b"")
        if hasattr(body, "read"):
            data = body.read()
        else:
            data = body

        if isinstance(data, bytes):
            text = data.decode("utf-8")
        else:
            text = str(data)

        stripped = text.strip()
        if stripped.startswith("data:"):
            chunks = []
            for line in stripped.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    chunks.append(line.removeprefix("data:").strip())
            return "".join(chunks)
        return stripped


def get_agentcore_client() -> AgentCoreClient | None:
    """Return an AgentCoreClient if configured, else None (local mode)."""
    if os.environ.get("AGENTCORE_AGENT_ID") or os.environ.get("AGENTCORE_AGENT_ARN"):
        return AgentCoreClient()
    return None
