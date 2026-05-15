from __future__ import annotations

import asyncio
import json

from nicegui import ui

from grounded_evals.guide.session import Session
from grounded_evals.ingest.models import Capability, Persona
from grounded_evals.llm.client import get_default_client, get_model_id

SUGGEST_CAPABILITIES_PROMPT = """Given this AI Agent description, suggest 3-5 additional capabilities that would be important to test. Only suggest capabilities NOT already listed.

Agent: {name}
Description: {description}
Existing capabilities: {capabilities}

Respond in JSON: {{"suggestions": ["capability 1", "capability 2", ...]}}"""


def render(session: Session) -> None:
    ui.label("What AI Agent are you building?").classes("text-h6 q-mb-md")
    ui.label(
        "Tell us about your agent so we can help you create a thorough evaluation dataset."
    ).classes("text-body1 text-grey-8 q-mb-lg")

    with ui.card().classes("w-full q-pa-md"):
        ui.label("Agent Name").classes("text-subtitle2")
        name_input = ui.input(
            placeholder="e.g., Customer Support Agent, Code Review Bot...",
            value=session.agent_spec.name,
        ).classes("w-full")
        name_input.on_value_change(lambda e: session.update_agent(name=e.value))

        ui.separator().classes("q-my-md")

        ui.label("What does your agent do?").classes("text-subtitle2")
        desc_input = ui.textarea(
            placeholder="Describe your agent's purpose in 2-3 sentences. "
            "What problems does it solve? Who uses it?",
            value=session.agent_spec.description,
        ).classes("w-full")
        desc_input.on_value_change(lambda e: session.update_agent(description=e.value))

    ui.separator().classes("q-my-lg")

    with ui.card().classes("w-full q-pa-md"):
        ui.label("Capabilities").classes("text-subtitle2")
        ui.label(
            "What can your agent do? List its main skills and functions."
        ).classes("text-caption text-grey-7")

        capabilities_container = ui.column().classes("w-full q-mt-sm")

        def rebuild_capabilities():
            capabilities_container.clear()
            with capabilities_container:
                for i, cap in enumerate(session.agent_spec.capabilities):
                    with ui.row().classes("w-full items-center"):
                        inp = ui.input(value=cap.name).classes("flex-grow")
                        idx = i

                        def on_cap_change(e, _idx=idx):
                            if _idx < len(session.agent_spec.capabilities):
                                session.agent_spec.capabilities[_idx].name = e.value

                        inp.on_value_change(on_cap_change)

                        def remove_cap(_idx=idx):
                            session.agent_spec.capabilities.pop(_idx)
                            rebuild_capabilities()

                        ui.button(icon="close", on_click=remove_cap).props("flat dense")

        rebuild_capabilities()

        with ui.row().classes("gap-sm q-mt-sm"):

            def add_capability():
                session.agent_spec.capabilities.append(Capability(name=""))
                rebuild_capabilities()

            ui.button("+ Add capability", on_click=add_capability).props(
                "flat color=primary"
            )

            async def suggest_capabilities():
                if not session.agent_spec.name and not session.agent_spec.description:
                    ui.notify("Please fill in agent name and description first.", type="warning")
                    return
                suggest_btn.props("loading")
                try:
                    client = get_default_client()
                    model_id = get_model_id()
                    prompt = SUGGEST_CAPABILITIES_PROMPT.format(
                        name=session.agent_spec.name,
                        description=session.agent_spec.description,
                        capabilities=", ".join(
                            c.name for c in session.agent_spec.capabilities if c.name
                        ),
                    )
                    message = await asyncio.to_thread(
                        client.messages.create,
                        model=model_id,
                        max_tokens=512,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    text = message.content[0].text
                    json_start = text.find("{")
                    json_end = text.rfind("}") + 1
                    data = json.loads(text[json_start:json_end])
                    for s in data.get("suggestions", []):
                        session.agent_spec.capabilities.append(Capability(name=s))
                    rebuild_capabilities()
                    ui.notify(
                        f"Added {len(data.get('suggestions', []))} suggested capabilities!",
                        type="positive",
                    )
                except Exception as e:
                    ui.notify(f"Error: {e}", type="negative")
                finally:
                    suggest_btn.props(remove="loading")

            suggest_btn = ui.button(
                "AI Suggest", icon="auto_awesome", on_click=suggest_capabilities
            ).props("outlined color=primary")

    ui.separator().classes("q-my-lg")

    with ui.card().classes("w-full q-pa-md"):
        ui.label("Target Users").classes("text-subtitle2")
        ui.label(
            "Who will interact with your agent? Describe their personas."
        ).classes("text-caption text-grey-7")

        users_container = ui.column().classes("w-full q-mt-sm")

        def rebuild_personas():
            users_container.clear()
            with users_container:
                for i, user in enumerate(session.agent_spec.target_users):
                    with ui.card().classes("w-full q-pa-sm q-mb-sm").props("bordered"):
                        idx = i
                        name_inp = ui.input(
                            value=user.name,
                            placeholder="Persona name (e.g., Frustrated Customer)",
                        ).classes("w-full")
                        desc_inp = ui.input(
                            value=user.description,
                            placeholder="Brief description",
                        ).classes("w-full")

                        def on_name(e, _idx=idx):
                            if _idx < len(session.agent_spec.target_users):
                                session.agent_spec.target_users[_idx].name = e.value

                        def on_desc(e, _idx=idx):
                            if _idx < len(session.agent_spec.target_users):
                                session.agent_spec.target_users[_idx].description = e.value

                        name_inp.on_value_change(on_name)
                        desc_inp.on_value_change(on_desc)

        rebuild_personas()

        def add_persona():
            session.agent_spec.target_users.append(Persona(name="", description=""))
            rebuild_personas()

        ui.button("+ Add persona", on_click=add_persona).props("flat color=primary")

    ui.separator().classes("q-my-lg")

    with ui.expansion("Known Edge Cases & Constraints", icon="warning").classes("w-full"):
        ui.label(
            "Any tricky scenarios or rules your agent must follow? (optional for now)"
        ).classes("text-caption text-grey-7 q-mb-sm")

        edge_input = ui.textarea(
            placeholder="One edge case per line...\n"
            "e.g., Multi-item orders with mixed return eligibility\n"
            "Requests outside agent scope",
            value="\n".join(session.agent_spec.known_edge_cases),
        ).classes("w-full")

        def on_edge_change(e):
            session.agent_spec.known_edge_cases = [
                line.strip() for line in e.value.split("\n") if line.strip()
            ]

        edge_input.on_value_change(on_edge_change)

        constraints_input = ui.textarea(
            placeholder="Constraints (one per line)...\n"
            "e.g., Must not reveal internal policies\n"
            "Must escalate after 3 failed attempts",
            value="\n".join(session.agent_spec.constraints),
        ).classes("w-full q-mt-sm")

        def on_constraints_change(e):
            session.agent_spec.constraints = [
                line.strip() for line in e.value.split("\n") if line.strip()
            ]

        constraints_input.on_value_change(on_constraints_change)
