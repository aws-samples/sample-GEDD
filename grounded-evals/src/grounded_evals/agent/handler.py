"""Agent turn handler — runs the LLM tool loop and returns structured results."""

from __future__ import annotations

from dataclasses import dataclass, field

from grounded_evals.agent.prompt import SYSTEM_PROMPT, get_state_block
from grounded_evals.agent.tools import TOOLS, StateBundle, handle_tool_call
from grounded_evals.llm.client import get_default_client, get_model_id, traced_coach_call


@dataclass
class AgentResponse:
    """Result of a single agent turn (may involve multiple LLM calls)."""

    text: str
    tool_executions: list[dict] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)


def run_agent_turn(
    user_message: str,
    messages: list[dict],
    state: StateBundle,
) -> AgentResponse:
    """Run a full agent turn with tool loop. Mutates state and messages in place."""
    messages.append({"role": "user", "content": user_message})

    client = get_default_client()
    model_id = get_model_id()
    system = SYSTEM_PROMPT.format(state=get_state_block(state.session, state.annotations, state.current_step))

    response = traced_coach_call(client, model_id, system, messages, TOOLS, 2048)

    all_text_parts: list[str] = []
    all_tool_executions: list[dict] = []

    for _ in range(8):
        if response.stop_reason != "tool_use":
            break

        for block in response.content:
            if block.type == "text" and block.text.strip():
                all_text_parts.append(block.text)

        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = handle_tool_call(block.name, block.input, state)
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            all_tool_executions.append({
                "tool_name": block.name,
                "tool_input": block.input,
                "tool_result": result,
            })
        messages.append({"role": "user", "content": tool_results})

        system = SYSTEM_PROMPT.format(state=get_state_block(state.session, state.annotations, state.current_step))
        response = traced_coach_call(client, model_id, system, messages, TOOLS, 2048)

    for block in response.content:
        if hasattr(block, "text") and block.text.strip():
            all_text_parts.append(block.text)

    # If no text was produced, force one more call without tools
    if not all_text_parts:
        if response.stop_reason == "tool_use":
            assistant_content = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
            messages.append({"role": "assistant", "content": assistant_content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = handle_tool_call(block.name, block.input, state)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
                    all_tool_executions.append({
                        "tool_name": block.name,
                        "tool_input": block.input,
                        "tool_result": result,
                    })
            messages.append({"role": "user", "content": tool_results})

        system = SYSTEM_PROMPT.format(state=get_state_block(state.session, state.annotations, state.current_step))
        response = traced_coach_call(client, model_id, system, messages, None, 2048)
        for block in response.content:
            if hasattr(block, "text") and block.text.strip():
                all_text_parts.append(block.text)

    text = "\n".join(all_text_parts)

    if text:
        messages.append({"role": "assistant", "content": text})

    return AgentResponse(
        text=text,
        tool_executions=all_tool_executions,
        messages=messages,
    )
