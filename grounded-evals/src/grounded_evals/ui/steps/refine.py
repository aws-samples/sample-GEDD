from __future__ import annotations

from nicegui import ui

from grounded_evals.guide.session import Session


def render(session: Session) -> None:
    ui.label("Refine & Iterate").classes("text-h6 q-mb-md")
    ui.label(
        "Use what you learned from error analysis to improve your agent's system prompt. "
        "This closes the loop: better prompt -> better agent -> better eval scores."
    ).classes("text-body1 text-grey-8 q-mb-lg")

    with ui.row().classes("w-full gap-md"):
        with ui.column().classes("flex-grow"):
            ui.label("Identified Gaps").classes("text-subtitle2 q-mb-sm")
            ui.label(
                "Based on your error analysis, here are areas where your agent's "
                "system prompt could be strengthened:"
            ).classes("text-caption text-grey-7 q-mb-sm")

            gaps = [
                ("Safety boundaries", "Agent doesn't clearly refuse harmful requests"),
                ("Edge case handling", "No guidance for multi-item return scenarios"),
                ("Escalation triggers", "Unclear when to hand off to human"),
            ]
            for title, desc in gaps:
                with ui.card().classes("w-full q-pa-sm q-mb-sm").props("bordered"):
                    ui.label(title).classes("text-body2 text-weight-medium")
                    ui.label(desc).classes("text-caption text-grey-7")
                    ui.button("Suggest fix", icon="auto_fix_high").props(
                        "flat dense size=sm color=primary"
                    )

        with ui.column().classes("w-96"):
            ui.label("Updated System Prompt").classes("text-subtitle2 q-mb-sm")
            ui.textarea(
                placeholder="Your refined system prompt will appear here...",
                value=session.agent_spec.system_prompt,
            ).classes("w-full").props("rows=12")
            ui.button("Save & Re-evaluate", icon="replay").props("color=primary").classes(
                "q-mt-sm"
            )

    with ui.card().classes("w-full q-pa-md q-mt-lg").props("bordered flat"):
        with ui.row().classes("items-center gap-sm"):
            ui.icon("loop", color="primary")
            ui.label("The Eval Loop").classes("text-subtitle2")
        ui.label(
            "After refining, go back to Step 6 to re-run your agent and compare scores. "
            "Iterate until your judge shows consistent improvement."
        ).classes("text-body2 text-grey-7")
