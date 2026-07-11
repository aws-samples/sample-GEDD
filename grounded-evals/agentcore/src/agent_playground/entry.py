"""AgentCore Runtime entry point for Agent Playground.

This is the handler that AgentCore invokes when a request arrives.
It routes between the coach agent (guided conversation) and the eval agent
(multi-model comparison) based on the request type.
"""

from __future__ import annotations

import json
import os

from bedrock_agentcore import BedrockAgentCoreApp

from agent_playground.coach import CoachState, run_coach_turn
from agent_playground.evaluator import run_eval_json

app = BedrockAgentCoreApp()

REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")


@app.entrypoint
async def handler(request):
    """Route requests to coach or eval agent based on request_type field."""
    payload = request.get("payload", request)
    request_type = payload.get("request_type", "coach")

    if request_type == "eval":
        return await _handle_eval(payload)
    else:
        return await _handle_coach(request, payload)


async def _handle_coach(request, payload):
    """Handle a coaching conversation turn."""
    user_message = payload.get("user_message", request.get("prompt", ""))
    session_state = payload.get("session_state", {})
    messages = payload.get("messages", [])

    state = CoachState.from_dict(session_state)

    response = run_coach_turn(
        user_message=user_message,
        messages=messages,
        state=state,
        region=REGION,
        model_id=MODEL_ID,
    )

    yield json.dumps({
        "type": "coach_response",
        "text": response.text,
        "tool_executions": response.tool_executions,
        "updated_state": response.updated_state,
        "messages": messages,
    })


async def _handle_eval(payload):
    """Handle a multi-model evaluation request."""
    queries = payload.get("queries", [])
    model_ids = payload.get("model_ids", [])
    system_prompt = payload.get("system_prompt", "")

    if not queries or not model_ids or not system_prompt:
        yield json.dumps({
            "type": "eval_response",
            "error": "Missing required fields: queries, model_ids, system_prompt",
        })
        return

    results_json = run_eval_json(queries, model_ids, system_prompt, REGION)

    yield json.dumps({
        "type": "eval_response",
        "results": json.loads(results_json),
    })


if __name__ == "__main__":
    app.run()
