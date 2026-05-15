"""Coach agent — runs the guided conversation with tool loop."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from uuid import uuid4

from anthropic import AnthropicBedrock
from pydantic import BaseModel, Field


class Capability(BaseModel):
    name: str
    description: str = ""


class Persona(BaseModel):
    name: str
    description: str = ""


class AgentSpec(BaseModel):
    name: str = ""
    description: str = ""
    capabilities: list[Capability] = Field(default_factory=list)
    target_users: list[Persona] = Field(default_factory=list)
    system_prompt: str = ""


class GoldenPrompt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    prompt_text: str = ""
    category: str = ""
    expected_behavior: str = ""
    dimensions: str = ""


@dataclass
class CoachState:
    """Deserialized session state passed from the UI."""

    agent_spec: AgentSpec = field(default_factory=AgentSpec)
    golden_prompts: list[GoldenPrompt] = field(default_factory=list)
    annotations: list[dict] = field(default_factory=list)
    current_step: int = 1
    prompt_variants: list[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> CoachState:
        agent_data = data.get("agent_spec", {})
        return cls(
            agent_spec=AgentSpec(**agent_data) if agent_data else AgentSpec(),
            golden_prompts=[GoldenPrompt(**p) for p in data.get("golden_prompts", [])],
            annotations=data.get("annotations", []),
            current_step=data.get("current_step", 1),
            prompt_variants=data.get("prompt_variants", []),
        )

    def to_dict(self) -> dict:
        return {
            "agent_spec": self.agent_spec.model_dump(),
            "golden_prompts": [p.model_dump() for p in self.golden_prompts],
            "annotations": self.annotations,
            "current_step": self.current_step,
            "prompt_variants": self.prompt_variants,
        }


@dataclass
class CoachResponse:
    text: str
    tool_executions: list[dict] = field(default_factory=list)
    updated_state: dict = field(default_factory=dict)


SYSTEM_PROMPT = """\
<role>
You are an expert AI Agent evaluation coach. You help Product Managers create golden evaluation datasets using Open Coding methodology and perform systematic error analysis on AI agent responses.
</role>

<personality>
- Warm, collaborative — use "we" language
- Concise: 2-4 sentences unless presenting structured output
- One question per turn — never ask multiple questions
- Always acknowledge what the user said before moving forward
- Use markdown: **bold** for key terms, numbered/bulleted lists for structured info
</personality>

<workflow>
Guide the PM through 4 steps:

**Step 1: Define Agent** — Gather name, purpose, capabilities, target users.

**Step 2: System Prompt** — Collaboratively draft the agent's system prompt. When approved, save it.

**Step 3: Golden Queries (Open Coding)** — THIS IS THE CORE FEATURE. Apply Open Coding methodology:
1. FRACTURE the domain into 6-8 test categories:
   - Happy path (straightforward, should work perfectly)
   - Edge cases (boundary conditions, unusual combinations)
   - Adversarial (jailbreaks, manipulation, off-topic)
   - Ambiguous (vague, underspecified, could be interpreted multiple ways)
   - Multi-turn (requires context from prior messages)
   - Error recovery (agent failed, user retries differently)
   - Persona variation (same request from different user types)
2. For each category, VARY DIMENSIONS:
   - Complexity: simple → compound
   - Tone: polite → frustrated → hostile
   - Specificity: vague → highly detailed
   - User expertise: novice → expert
   - Length: terse (3 words) → verbose (paragraph)
3. Apply CONSTANT COMPARISON — after suggesting each query, note what coverage it adds that previous queries don't
4. Track SATURATION — when categories are well-covered, tell the PM

Generate queries in batches of 3-5, grouped by category. After each batch, ask PM to approve, modify, or add their own. Save each approved query via save_golden_query.

**Step 4: Error Analysis (Open Coding + Axial Coding)** — THIS IS THE SECOND CORE FEATURE.
1. Take each golden query and use run_agent_query to simulate the agent's response
2. Present the query + response to the PM
3. Ask them to annotate: Correct | Partial | Incorrect
4. For incorrect responses, apply OPEN CODING:
   - Ask PM to describe the failure
   - Suggest an error code label (or let PM create one)
   - Save the annotation via save_annotation
5. After annotating 5+ responses, apply AXIAL CODING:
   - Group error codes into patterns
   - Identify: what CAUSES these failures? Under what CONDITIONS? What are the CONSEQUENCES?
   - Map to standard dimensions: Quality, Accuracy, Relevance, Safety, Completeness, Tone
6. Summarize findings and suggest system prompt improvements
</workflow>

<behavior>
- Call set_current_step when transitioning between steps
- Call save_agent_info when user provides agent details
- When PM approves a system prompt, call save_agent_info with the full system_prompt text AND call save_prompt_variant with name="A"
- Call save_golden_query for EACH approved query (one tool call per query)
- Call run_agent_query to simulate agent responses during error analysis
- Call save_annotation when PM provides feedback on a response
- Generate at least 15-20 golden queries across all categories before moving to step 4
- During error analysis, be systematic — go through queries one by one
</behavior>

<current_state>
{state}
</current_state>"""

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
        "description": "Save ONE golden query to the dataset. Call once per approved query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "category": {"type": "string"},
                "expected_behavior": {"type": "string"},
                "dimensions": {"type": "string"},
            },
            "required": ["query", "category"],
        },
    },
    {
        "name": "run_agent_query",
        "description": "Simulate the agent responding to a golden query using the saved system prompt.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "save_annotation",
        "description": "Save PM's annotation of an agent response.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "response": {"type": "string"},
                "annotation": {"type": "string", "description": "correct|partial|incorrect"},
                "error_code": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["query", "response", "annotation"],
        },
    },
    {
        "name": "set_current_step",
        "description": "Update the progress tracker.",
        "input_schema": {
            "type": "object",
            "properties": {"step": {"type": "integer"}},
            "required": ["step"],
        },
    },
    {
        "name": "save_prompt_variant",
        "description": "Save a system prompt variant for A/B testing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "prompt": {"type": "string"},
            },
            "required": ["name", "prompt"],
        },
    },
]


def _get_state_block(state: CoachState) -> str:
    caps = ", ".join(c.name for c in state.agent_spec.capabilities) or "not yet defined"
    users = ", ".join(u.name for u in state.agent_spec.target_users) or "not yet defined"
    correct = sum(1 for a in state.annotations if a.get("annotation") == "correct")
    partial = sum(1 for a in state.annotations if a.get("annotation") == "partial")
    incorrect = sum(1 for a in state.annotations if a.get("annotation") == "incorrect")
    error_codes = list({a["error_code"] for a in state.annotations if a.get("error_code")})
    return (
        f"Agent: {state.agent_spec.name or 'not defined'}\n"
        f"Capabilities: {caps}\n"
        f"Target users: {users}\n"
        f"System prompt: {f'YES ({len(state.agent_spec.system_prompt)} chars)' if state.agent_spec.system_prompt else 'not defined'}\n"
        f"Golden queries: {len(state.golden_prompts)}\n"
        f"Annotations: {len(state.annotations)} total ({correct} correct, {partial} partial, {incorrect} incorrect)\n"
        f"Error codes discovered: {', '.join(error_codes) if error_codes else 'none yet'}\n"
        f"Current step: {state.current_step}"
    )


def _handle_tool(tool_name: str, tool_input: dict, state: CoachState, client: AnthropicBedrock, model_id: str) -> str:
    """Execute a tool and mutate state. Returns JSON result."""
    if tool_name == "save_agent_info":
        if tool_input.get("name"):
            state.agent_spec.name = tool_input["name"]
        if tool_input.get("description"):
            state.agent_spec.description = tool_input["description"]
        if tool_input.get("capabilities"):
            state.agent_spec.capabilities = [Capability(name=c) for c in tool_input["capabilities"]]
        if tool_input.get("target_users"):
            state.agent_spec.target_users = [Persona(name=u) for u in tool_input["target_users"]]
        if tool_input.get("system_prompt"):
            state.agent_spec.system_prompt = tool_input["system_prompt"]
        return json.dumps({"status": "saved"})

    elif tool_name == "save_golden_query":
        state.golden_prompts.append(GoldenPrompt(
            prompt_text=tool_input["query"],
            category=tool_input.get("category", ""),
            expected_behavior=tool_input.get("expected_behavior", ""),
            dimensions=tool_input.get("dimensions", ""),
        ))
        return json.dumps({"saved": True, "total": len(state.golden_prompts)})

    elif tool_name == "run_agent_query":
        if not state.agent_spec.system_prompt:
            return json.dumps({"error": "No system prompt defined. Complete step 2 first."})
        resp = client.messages.create(
            model=model_id,
            max_tokens=512,
            system=state.agent_spec.system_prompt,
            messages=[{"role": "user", "content": tool_input["query"]}],
        )
        return json.dumps({"query": tool_input["query"], "agent_response": resp.content[0].text})

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


def run_coach_turn(
    user_message: str,
    messages: list[dict],
    state: CoachState,
    region: str = "us-east-1",
    model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0",
) -> CoachResponse:
    """Run a full coach turn with tool loop. Returns text + tool executions + updated state."""
    client = AnthropicBedrock(aws_region=region)

    messages.append({"role": "user", "content": user_message})
    system = SYSTEM_PROMPT.format(state=_get_state_block(state))

    response = client.messages.create(
        model=model_id, max_tokens=2048, system=system, messages=messages, tools=TOOLS
    )

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
            result = _handle_tool(block.name, block.input, state, client, model_id)
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            all_tool_executions.append({
                "tool_name": block.name,
                "tool_input": block.input,
                "tool_result": result,
            })
        messages.append({"role": "user", "content": tool_results})

        system = SYSTEM_PROMPT.format(state=_get_state_block(state))
        response = client.messages.create(
            model=model_id, max_tokens=2048, system=system, messages=messages, tools=TOOLS
        )

    for block in response.content:
        if hasattr(block, "text") and block.text.strip():
            all_text_parts.append(block.text)

    if not all_text_parts and response.stop_reason == "tool_use":
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
                result = _handle_tool(block.name, block.input, state, client, model_id)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
                all_tool_executions.append({"tool_name": block.name, "tool_input": block.input, "tool_result": result})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model=model_id, max_tokens=2048, system=system, messages=messages
        )
        for block in response.content:
            if hasattr(block, "text") and block.text.strip():
                all_text_parts.append(block.text)

    return CoachResponse(
        text="\n".join(all_text_parts),
        tool_executions=all_tool_executions,
        updated_state=state.to_dict(),
    )
