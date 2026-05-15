from __future__ import annotations

from nicegui import ui

from grounded_evals.guide.session import Session


def render(session: Session) -> None:
    ui.label("Deploy & Monitor").classes("text-h6 q-mb-md")
    ui.label(
        "Your LLM-as-a-Judge is ready for production. "
        "Export the configuration and set up automated monitoring."
    ).classes("text-body1 text-grey-8 q-mb-lg")

    with ui.card().classes("w-full q-pa-md"):
        ui.label("Export Options").classes("text-subtitle2 q-mb-sm")

        with ui.row().classes("gap-md"):
            with ui.card().classes("q-pa-md cursor-pointer").props("bordered"):
                ui.icon("description", size="lg", color="primary")
                ui.label("Judge Prompt").classes("text-body2 text-weight-medium")
                ui.label("System prompt + rubric as text").classes("text-caption text-grey-7")

            with ui.card().classes("q-pa-md cursor-pointer").props("bordered"):
                ui.icon("data_object", size="lg", color="primary")
                ui.label("JSON Config").classes("text-body2 text-weight-medium")
                ui.label("Machine-readable rubric").classes("text-caption text-grey-7")

            with ui.card().classes("q-pa-md cursor-pointer").props("bordered"):
                ui.icon("inventory", size="lg", color="primary")
                ui.label("Full Dataset").classes("text-body2 text-weight-medium")
                ui.label("Golden + synthetic + eval results").classes("text-caption text-grey-7")

    with ui.card().classes("w-full q-pa-md q-mt-md").props("bordered"):
        ui.label("Next: Set up monitoring").classes("text-subtitle2")
        ui.label(
            "Once deployed, your judge will run automatically on new agent interactions. "
            "Track quality scores over time to catch regressions early."
        ).classes("text-body2 text-grey-7")
