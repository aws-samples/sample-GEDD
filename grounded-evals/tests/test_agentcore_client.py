from __future__ import annotations

import io
import json
from uuid import uuid4

from grounded_evals.agentcore_client import AgentCoreClient

RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/coach-runtime"


class FakeRuntimeClient:
    def __init__(self, body: dict) -> None:
        self.body = body
        self.calls: list[dict] = []

    def invoke_agent_runtime(self, **kwargs):
        self.calls.append(kwargs)
        return {"response": io.BytesIO(json.dumps(self.body).encode("utf-8"))}


class FakeControlClient:
    def __init__(self, arn: str) -> None:
        self.arn = arn
        self.calls: list[dict] = []

    def get_agent_runtime(self, **kwargs):
        self.calls.append(kwargs)
        return {"agentRuntimeArn": self.arn}


def test_invoke_coach_uses_agentcore_runtime_payload() -> None:
    client = AgentCoreClient(agent_runtime_arn=RUNTIME_ARN, region="us-east-1")
    runtime = FakeRuntimeClient(
        {
            "text": "Coach reply",
            "updated_state": {"current_step": 2},
            "messages": [{"role": "assistant", "content": "Coach reply"}],
        }
    )
    client._client = runtime

    response = client.invoke_coach(
        user_message="hello",
        session_id=str(uuid4()),
        session_state={"agent_spec": {"name": "RxBot"}},
        messages=[],
    )

    assert response.text == "Coach reply"
    assert response.updated_state == {"current_step": 2}
    call = runtime.calls[0]
    assert call["agentRuntimeArn"] == RUNTIME_ARN
    assert call["contentType"] == "application/json"
    assert call["accept"] == "application/json"
    payload = json.loads(call["payload"].decode("utf-8"))
    assert payload["request_type"] == "coach"
    assert payload["user_message"] == "hello"
    assert payload["session_state"]["agent_spec"]["name"] == "RxBot"


def test_short_runtime_id_resolves_to_agentcore_runtime_arn() -> None:
    client = AgentCoreClient(region="us-east-1")
    client.agent_runtime_id = "coach-runtime-id"
    control = FakeControlClient(RUNTIME_ARN)
    client._control = control

    assert client._get_agent_runtime_arn() == RUNTIME_ARN
    assert control.calls == [{"agentRuntimeId": "coach-runtime-id"}]
    assert client.agent_runtime_arn == RUNTIME_ARN


def test_read_runtime_response_accepts_sse_data_lines() -> None:
    client = AgentCoreClient(agent_runtime_arn=RUNTIME_ARN, region="us-east-1")

    text = client._read_runtime_response(
        {"response": io.BytesIO(b'data: {"text":"hello"}\n\n')}
    )

    assert text == '{"text":"hello"}'
