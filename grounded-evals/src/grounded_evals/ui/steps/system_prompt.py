from __future__ import annotations

import asyncio
import json

from nicegui import ui

from grounded_evals.guide.session import Session
from grounded_evals.llm.client import get_default_client, get_model_id

REVIEW_PROMPT = """You are an expert AI system prompt reviewer. Analyze this system prompt for an AI Agent and provide feedback.

Agent: {name}
Description: {description}
Capabilities: {capabilities}
Constraints: {constraints}

System Prompt:
---
{system_prompt}
---

Review for:
1. Clarity of role definition
2. Coverage of declared capabilities
3. Clear boundaries (what to refuse)
4. Tone and personality guidance
5. Escalation rules
6. Missing elements based on the agent's description

Respond in JSON:
{{
  "score": <1-10>,
  "strengths": ["...", "..."],
  "gaps": ["...", "..."],
  "suggestions": ["specific improvement 1", "specific improvement 2"]
}}"""


def render(session: Session) -> None:
    ui.label("Craft Your System Prompt").classes("text-h6 q-mb-md")
    ui.label(
        "Write or paste the system prompt that defines your agent's behavior. "
        "We'll help you evaluate and improve it."
    ).classes("text-body1 text-grey-8 q-mb-lg")

    with ui.row().classes("w-full gap-md"):
        with ui.column().classes("flex-grow"):
            ui.label("System Prompt").classes("text-subtitle2")
            prompt_input = ui.textarea(
                placeholder="You are a helpful customer support agent for...\n\n"
                "Your responsibilities include:\n- ...\n- ...\n\n"
                "Rules:\n- Never reveal internal policies\n- Always be empathetic...",
                value=session.agent_spec.system_prompt,
            ).classes("w-full").props("rows=16")

            def on_prompt_change(e):
                session.agent_spec.system_prompt = e.value

            prompt_input.on_value_change(on_prompt_change)

        with ui.column().classes("w-96"):
            ui.label("AI Review").classes("text-subtitle2")

            review_container = ui.column().classes("w-full")
            with review_container:
                ui.label(
                    "Click 'Review Prompt' after writing your system prompt."
                ).classes("text-caption text-grey-7")

            async def on_review():
                text = prompt_input.value.strip()
                if not text:
                    ui.notify("Write a system prompt first.", type="warning")
                    return

                review_btn.props("loading")
                try:
                    client = get_default_client()
                    model_id = get_model_id()
                    prompt = REVIEW_PROMPT.format(
                        name=session.agent_spec.name,
                        description=session.agent_spec.description,
                        capabilities=", ".join(
                            c.name for c in session.agent_spec.capabilities
                        ),
                        constraints=", ".join(session.agent_spec.constraints),
                        system_prompt=text,
                    )
                    message = await asyncio.to_thread(
                        client.messages.create,
                        model=model_id,
                        max_tokens=1024,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    response_text = message.content[0].text
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    data = json.loads(response_text[json_start:json_end])

                    review_container.clear()
                    with review_container:
                        score = data.get("score", 0)
                        score_color = (
                            "green" if score >= 7 else "orange" if score >= 5 else "red"
                        )
                        with ui.row().classes("items-center gap-sm"):
                            ui.label(f"Score: {score}/10").classes(
                                f"text-h6 text-{score_color}"
                            )

                        if data.get("strengths"):
                            ui.label("Strengths").classes(
                                "text-subtitle2 text-green q-mt-sm"
                            )
                            for s in data["strengths"]:
                                ui.label(f"  ✓ {s}").classes("text-caption")

                        if data.get("gaps"):
                            ui.label("Gaps").classes(
                                "text-subtitle2 text-orange q-mt-sm"
                            )
                            for g in data["gaps"]:
                                ui.label(f"  ⚠ {g}").classes("text-caption")

                        if data.get("suggestions"):
                            ui.label("Suggestions").classes(
                                "text-subtitle2 text-blue q-mt-sm"
                            )
                            for s in data["suggestions"]:
                                ui.label(f"  → {s}").classes("text-caption")

                except Exception as e:
                    review_container.clear()
                    with review_container:
                        ui.label(f"Review failed: {e}").classes("text-caption text-red")
                finally:
                    review_btn.props(remove="loading")

            review_btn = ui.button(
                "Review Prompt", icon="rate_review", on_click=on_review
            ).props("color=primary outlined").classes("q-mt-sm")

            with ui.expansion("What makes a good system prompt?", icon="help").classes(
                "w-full q-mt-sm"
            ):
                ui.markdown(
                    "- **Clear role definition** — who is the agent?\n"
                    "- **Explicit capabilities** — what can it do?\n"
                    "- **Boundaries** — what should it refuse?\n"
                    "- **Tone guidance** — how should it sound?\n"
                    "- **Escalation rules** — when to hand off?"
                )
