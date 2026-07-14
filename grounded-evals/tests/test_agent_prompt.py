from __future__ import annotations

from grounded_evals.agent.prompt import SYSTEM_PROMPT, get_state_block
from grounded_evals.guide.session import Session


def test_system_prompt_format_escapes_documentation_placeholders() -> None:
    state = get_state_block(Session(), annotations=[], current_step=1)

    prompt = SYSTEM_PROMPT.format(state=state)

    assert ".kiro/specs/{agent-name}/requirements.md" in prompt
    assert "LLM-as-a-Judge subagent" in prompt
    assert "before customers see them" in prompt
    assert "Current step: 1" in prompt
