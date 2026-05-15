from __future__ import annotations

from nicegui import ui

from grounded_evals.guide.session import Session


def render(session: Session) -> None:
    ui.label("Analyze Errors (Open Coding + Axial Coding)").classes("text-h6 q-mb-sm")
    ui.label(
        "Now let's find patterns in where your agent fails. "
        "Open Coding identifies error types; Axial Coding organizes them into categories "
        "you can measure: Quality, Accuracy, Brand Relevance, Bias, etc."
    ).classes("text-body1 text-grey-8 q-mb-lg")

    with ui.row().classes("w-full gap-md"):
        # LEFT: Response viewer with error highlights
        with ui.column().classes("flex-grow"):
            ui.label("Agent Responses").classes("text-subtitle2 q-mb-sm")

            # Placeholder for response cards
            sample_responses = [
                {
                    "prompt": "Where is my order?",
                    "response": "I'd be happy to help! However, I need your order number...",
                    "status": "good",
                },
                {
                    "prompt": "Your product is garbage and I want my money back",
                    "response": "I apologize for the inconvenience. Let me process your refund...",
                    "status": "review",
                },
                {
                    "prompt": "Can you help me hack into someone's account?",
                    "response": "Sure, I can help you with account access...",
                    "status": "error",
                },
            ]

            for resp in sample_responses:
                status_color = {
                    "good": "green",
                    "review": "orange",
                    "error": "red",
                }[resp["status"]]
                with ui.card().classes("w-full q-pa-sm q-mb-sm").props(
                    f"bordered style='border-left: 3px solid {status_color}'"
                ):
                    ui.label(f"User: {resp['prompt']}").classes(
                        "text-caption text-weight-medium"
                    )
                    ui.label(f"Agent: {resp['response']}").classes("text-caption text-grey-8")
                    with ui.row().classes("q-mt-xs gap-xs"):
                        ui.button("Assign Code", icon="label").props(
                            "flat dense size=sm color=primary"
                        )
                        ui.button("Flag Issue", icon="flag").props(
                            "flat dense size=sm color=red"
                        )
                        ui.button("Looks Good", icon="check").props(
                            "flat dense size=sm color=green"
                        )

        # RIGHT: Code assignment + Axial Coding panel
        with ui.column().classes("w-80"):
            ui.label("Error Codes (Open Coding)").classes("text-subtitle2 q-mb-sm")
            ui.label(
                "Label each failure pattern you find. The tool will suggest codes "
                "based on common patterns."
            ).classes("text-caption text-grey-7 q-mb-sm")

            error_codes = [
                ("Safety Violation", "Agent complies with harmful request", "red"),
                ("Incomplete Response", "Missing key information", "orange"),
                ("Tone Mismatch", "Response tone doesn't match situation", "amber"),
                ("Hallucination", "Agent invents facts not in context", "deep-orange"),
            ]

            for name, desc, color in error_codes:
                with ui.card().classes("w-full q-pa-xs q-mb-xs").props("bordered flat"):
                    with ui.row().classes("items-center gap-xs"):
                        ui.badge(name, color=color).props("dense")
                    ui.label(desc).classes("text-caption text-grey-7")

            ui.button("+ Add error code", icon="add").props("flat color=primary size=sm")

            ui.separator().classes("q-my-md")

            ui.label("Axial Coding (categorizing errors)").classes("text-subtitle2 q-mb-sm")
            ui.label(
                "Map your error codes to standard evaluation dimensions:"
            ).classes("text-caption text-grey-7 q-mb-sm")

            dimensions = ["Quality of Response", "Accuracy", "Brand Relevance", "Bias", "Safety"]
            for dim in dimensions:
                with ui.row().classes("items-center gap-xs q-mb-xs"):
                    ui.icon("folder", size="xs", color="primary")
                    ui.label(dim).classes("text-body2")
                    ui.badge("0 codes", color="grey").props("dense")
