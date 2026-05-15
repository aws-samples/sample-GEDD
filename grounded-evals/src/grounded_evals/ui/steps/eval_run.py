from __future__ import annotations

from nicegui import ui

from grounded_evals.guide.session import Session


def render(session: Session) -> None:
    ui.label("Run Agent Evaluation").classes("text-h6 q-mb-md")
    ui.label(
        "Run your AI Agent against the expanded query set and collect its responses. "
        "Upload results or connect to your agent's API."
    ).classes("text-body1 text-grey-8 q-mb-lg")

    with ui.tabs().classes("w-full") as tabs:
        upload_tab = ui.tab("Upload Results")
        api_tab = ui.tab("Connect API")

    with ui.tab_panels(tabs, value=upload_tab).classes("w-full"):
        with ui.tab_panel(upload_tab):
            with ui.card().classes("w-full q-pa-md"):
                ui.label("Upload eval results").classes("text-subtitle2")
                ui.label(
                    "JSONL file with prompt-response pairs. "
                    "Each line: {\"prompt\": \"...\", \"response\": \"...\"}"
                ).classes("text-caption text-grey-7 q-mb-md")
                ui.upload(
                    label="Drop your results file here",
                    auto_upload=True,
                ).classes("w-full").props("accept=.jsonl,.json")

        with ui.tab_panel(api_tab):
            with ui.card().classes("w-full q-pa-md"):
                ui.label("Connect to your agent").classes("text-subtitle2")
                ui.input(placeholder="Agent API endpoint URL").classes("w-full q-mb-sm")
                ui.input(placeholder="API key (optional)").classes("w-full q-mb-sm").props(
                    "type=password"
                )
                ui.button("Test Connection", icon="wifi").props("color=primary")

    with ui.card().classes("w-full q-pa-md q-mt-md").props("bordered"):
        ui.label("Results Summary").classes("text-subtitle2")
        ui.label("Upload or connect your agent to see evaluation results here.").classes(
            "text-body2 text-grey-7"
        )
