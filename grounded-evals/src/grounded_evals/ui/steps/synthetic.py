from __future__ import annotations

from nicegui import ui

from grounded_evals.guide.session import Session


def render(session: Session) -> None:
    ui.label("Expand to 100+ (Synthetic Generation)").classes("text-h6 q-mb-md")
    ui.label(
        "From your golden queries, we'll generate synthetic variations that test "
        "the same categories but with different phrasing, complexity, and tone."
    ).classes("text-body1 text-grey-8 q-mb-lg")

    golden_count = len(session.golden_prompts)

    with ui.card().classes("w-full q-pa-md"):
        with ui.row().classes("items-center gap-md"):
            ui.icon("edit_note", size="lg", color="primary")
            ui.label(f"You have {golden_count} golden queries").classes("text-subtitle1")

        ui.separator().classes("q-my-md")

        ui.label("Generation Settings").classes("text-subtitle2")
        with ui.row().classes("gap-md items-center q-mt-sm"):
            ui.label("Target count:").classes("text-body2")
            ui.number(value=100, min=50, max=500, step=10).classes("w-32")
            ui.label("queries").classes("text-body2")

        with ui.row().classes("gap-md items-center q-mt-sm"):
            ui.label("Variation strategy:").classes("text-body2")
            ui.select(
                options=[
                    "Vary along all dimensions equally",
                    "Focus on edge cases",
                    "Focus on under-covered categories",
                    "Mix of all strategies",
                ],
                value="Mix of all strategies",
            ).classes("w-64")

        ui.button("Generate Synthetic Queries", icon="auto_awesome").props(
            "color=primary size=lg"
        ).classes("q-mt-lg")

    with ui.card().classes("w-full q-pa-md q-mt-md").props("bordered"):
        ui.label("Generated queries will appear here for your review.").classes(
            "text-body2 text-grey-7"
        )
        ui.label(
            "You can accept, edit, or reject each one before adding to your dataset."
        ).classes("text-caption text-grey-6")
