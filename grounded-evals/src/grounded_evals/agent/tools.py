"""Tool definitions and execution for the coaching agent."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from uuid import uuid4

from grounded_evals.guide.session import Session
from grounded_evals.ingest.models import Capability, Persona
from grounded_evals.llm.client import get_default_client, get_model_id, traced_eval_call
from grounded_evals.models.core import GoldenPrompt


@dataclass
class StateBundle:
    """Mutable state passed to tool handlers."""

    session: Session
    annotations: list[dict] = field(default_factory=list)
    current_step: int = 1
    prompt_variants: list[dict] = field(default_factory=list)


TOOLS = [
    {
        "name": "save_agent_info",
        "description": "Save/update agent details. Call when user provides agent info or approves a system prompt.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "capabilities": {"type": "array", "items": {"type": "string"}},
                "target_users": {"type": "array", "items": {"type": "string"}},
                "system_prompt": {"type": "string", "description": "Full system prompt text when approved"},
            },
            "required": [],
        },
    },
    {
        "name": "save_golden_query",
        "description": "Save ONE golden query to the dataset. Call once per approved query. Include category and expected behavior.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The test query text"},
                "category": {"type": "string", "description": "happy_path|edge_case|adversarial|ambiguous|multi_turn|error_recovery|persona_variation"},
                "expected_behavior": {"type": "string", "description": "Brief description of correct agent behavior"},
                "dimensions": {"type": "string", "description": "Which dimensions this varies: e.g. 'complex, frustrated tone, expert user'"},
            },
            "required": ["query", "category"],
        },
    },
    {
        "name": "run_agent_query",
        "description": "Simulate the agent responding to a golden query using the saved system prompt. Call during error analysis to generate responses for PM to annotate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The user query to send to the agent"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "save_annotation",
        "description": "Save PM's annotation of an agent response. Call after PM gives feedback on a response.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The original query"},
                "response": {"type": "string", "description": "The agent's response"},
                "annotation": {"type": "string", "description": "correct|partial|incorrect"},
                "error_code": {"type": "string", "description": "Error label if partial/incorrect (e.g. hallucination, wrong_tone, incomplete)"},
                "notes": {"type": "string", "description": "PM's explanation of why it failed"},
            },
            "required": ["query", "response", "annotation"],
        },
    },
    {
        "name": "set_current_step",
        "description": "Update the progress tracker. Call when moving to a new step.",
        "input_schema": {
            "type": "object",
            "properties": {
                "step": {"type": "integer", "description": "1=Define, 2=System Prompt, 3=Golden Queries, 4=Error Analysis"},
            },
            "required": ["step"],
        },
    },
    {
        "name": "save_prompt_variant",
        "description": "Save a system prompt variant for A/B testing. Call when PM wants to save a prompt version (e.g., 'save this as variant A'). Also call save_agent_info with system_prompt to set the active prompt.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Variant name (e.g., 'A', 'B', 'Concise', 'Detailed')"},
                "prompt": {"type": "string", "description": "Full system prompt text"},
            },
            "required": ["name", "prompt"],
        },
    },
]


def handle_tool_call(tool_name: str, tool_input: dict, state: StateBundle) -> str:
    """Execute a tool call and mutate state accordingly. Returns JSON result."""
    if tool_name == "save_agent_info":
        if tool_input.get("name"):
            state.session.agent_spec.name = tool_input["name"]
        if tool_input.get("description"):
            state.session.agent_spec.description = tool_input["description"]
        if tool_input.get("capabilities"):
            state.session.agent_spec.capabilities = [Capability(name=c) for c in tool_input["capabilities"]]
        if tool_input.get("target_users"):
            state.session.agent_spec.target_users = [Persona(name=u) for u in tool_input["target_users"]]
        if tool_input.get("system_prompt"):
            state.session.agent_spec.system_prompt = tool_input["system_prompt"]
        return json.dumps({"status": "saved"})

    elif tool_name == "save_golden_query":
        prompt = GoldenPrompt(
            prompt_text=tool_input["query"],
            category_id=uuid4(),
            expected_behavior=tool_input.get("expected_behavior", ""),
            rationale=tool_input.get("category", ""),
            property_values={"dimensions": tool_input.get("dimensions", "")},
        )
        state.session.add_golden_prompt(prompt)
        return json.dumps({"saved": True, "total": len(state.session.golden_prompts)})

    elif tool_name == "run_agent_query":
        if not state.session.agent_spec.system_prompt:
            return json.dumps({"error": "No system prompt defined. Complete step 2 first."})
        client = get_default_client()
        model_id = get_model_id()
        resp = traced_eval_call(client, model_id, state.session.agent_spec.system_prompt, tool_input["query"])
        agent_response = resp.content[0].text
        return json.dumps({"query": tool_input["query"], "agent_response": agent_response})

    elif tool_name == "save_annotation":
        state.annotations.append({
            "query": tool_input["query"],
            "response": tool_input["response"],
            "annotation": tool_input["annotation"],
            "error_code": tool_input.get("error_code", ""),
            "notes": tool_input.get("notes", ""),
        })
        return json.dumps({"saved": True, "total_annotations": len(state.annotations)})

    elif tool_name == "set_current_step":
        state.current_step = max(1, min(4, tool_input.get("step", 1)))
        return json.dumps({"step": state.current_step})

    elif tool_name == "save_prompt_variant":
        name = tool_input["name"]
        prompt = tool_input["prompt"]
        for v in state.prompt_variants:
            if v["name"] == name:
                v["prompt"] = prompt
                break
        else:
            state.prompt_variants.append({"name": name, "prompt": prompt})
        return json.dumps({"saved": True, "variants": len(state.prompt_variants)})

    return json.dumps({"error": "unknown tool"})
