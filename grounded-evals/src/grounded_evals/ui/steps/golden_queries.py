from __future__ import annotations

import asyncio
from uuid import uuid4

from nicegui import ui

from grounded_evals.guide.session import Session
from grounded_evals.models.core import GoldenPrompt, SaturationStatus
from grounded_evals.open_coding.compare import constant_comparison
from grounded_evals.open_coding.fracture import fracture_domain
from grounded_evals.open_coding.saturation import (
    check_category_saturation,
    saturation_recommendation,
)


def render(session: Session) -> None:
    ui.label("Write Golden Queries (Open Coding)").classes("text-h6 q-mb-sm")
    ui.label(
        "Open Coding means systematically breaking your agent's domain into categories, "
        "then writing test queries that cover each one. We'll guide you through it."
    ).classes("text-body1 text-grey-8 q-mb-lg")

    # --- Coverage progress bar ---
    coverage_card = ui.card().classes("w-full q-pa-sm q-mb-md").props("bordered")

    def refresh_coverage():
        coverage_card.clear()
        coverage = session.coverage()
        with coverage_card:
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(
                    f"{coverage.total_prompts} prompts across "
                    f"{coverage.categories_covered}/{coverage.categories_total} categories"
                ).classes("text-subtitle2")
                score_pct = int(coverage.saturation_score * 100)
                color = "green" if score_pct > 70 else "orange" if score_pct > 30 else "red"
                ui.label(f"Coverage: {score_pct}%").classes(f"text-subtitle2 text-{color}")
            ui.linear_progress(value=coverage.saturation_score, color=color).classes("q-mt-xs")
            rec = saturation_recommendation(coverage)
            ui.label(rec).classes("text-caption text-grey-7 q-mt-xs")

    refresh_coverage()

    # --- Main layout ---
    with ui.row().classes("w-full gap-md"):

        # ========== LEFT: Category cards ==========
        categories_container = ui.column().classes("w-72")

        def refresh_categories():
            categories_container.clear()
            with categories_container:
                ui.label("Categories").classes("text-subtitle2 q-mb-sm")
                ui.label(
                    "Select a category to write prompts for."
                ).classes("text-caption text-grey-7 q-mb-sm")

                if not session.categories:
                    with ui.card().classes("w-full q-pa-md").props("bordered"):
                        ui.label("No categories yet").classes("text-body2 text-grey-7")
                        ui.label(
                            "Click 'Suggest Categories' to have AI analyze your agent "
                            "and propose test scenario categories."
                        ).classes("text-caption text-grey-6")

                    async def on_suggest():
                        suggest_btn.props("loading")
                        try:
                            categories = await asyncio.to_thread(
                                fracture_domain, session.agent_spec
                            )
                            for cat in categories:
                                session.add_category(cat)
                            refresh_categories()
                            refresh_coverage()
                            refresh_suggestions()
                            ui.notify(
                                f"Generated {len(categories)} categories!",
                                type="positive",
                            )
                        except Exception as e:
                            ui.notify(f"Error: {e}", type="negative")
                        finally:
                            suggest_btn.props(remove="loading")

                    suggest_btn = ui.button(
                        "Suggest Categories", icon="auto_awesome", on_click=on_suggest
                    ).props("color=primary").classes("q-mt-sm w-full")
                else:
                    for cat in session.categories:
                        prompts_count = len(session.prompts_for_category(cat.id))
                        sat = check_category_saturation(cat, session.golden_prompts)
                        cat.saturation = sat

                        if sat == SaturationStatus.SATURATED:
                            border_color = "green"
                            icon_name = "check_circle"
                        elif sat == SaturationStatus.APPROACHING:
                            border_color = "orange"
                            icon_name = "timelapse"
                        else:
                            border_color = "grey"
                            icon_name = "radio_button_unchecked"

                        with ui.card().classes(
                            "w-full q-pa-sm q-mb-xs cursor-pointer"
                        ).props(
                            f"bordered style='border-left: 3px solid {border_color}'"
                        ).on("click", lambda _c=cat: select_category(_c)):
                            with ui.row().classes("items-center justify-between w-full"):
                                ui.label(cat.name).classes("text-body2 text-weight-medium")
                                with ui.row().classes("items-center gap-xs"):
                                    ui.label(str(prompts_count)).classes("text-caption")
                                    ui.icon(icon_name, size="xs", color=border_color)
                            if cat.definition:
                                ui.label(cat.definition).classes(
                                    "text-caption text-grey-7"
                                )

        refresh_categories()

        # ========== CENTER: Prompt input ==========
        with ui.column().classes("flex-grow"):
            selected_cat_label = ui.label(
                "Select a category from the left, or write any query."
            ).classes("text-subtitle2 q-mb-sm")

            selected_category_id = {"value": None}

            def select_category(cat):
                selected_category_id["value"] = cat.id
                selected_cat_label.set_text(f"Writing for: {cat.name}")
                if cat.properties:
                    props_text = ", ".join(
                        f"{p.name} ({p.dimensions[0].low_anchor}...{p.dimensions[0].high_anchor})"
                        if p.dimensions else p.name
                        for p in cat.properties
                    )
                    props_hint.set_text(f"Vary along: {props_text}")
                    props_hint.set_visibility(True)
                else:
                    props_hint.set_visibility(False)

            props_hint = ui.label("").classes("text-caption text-blue-7 q-mb-sm")
            props_hint.set_visibility(False)

            prompt_input = ui.textarea(
                placeholder="Type a user query your agent should handle...\n\n"
                "Examples:\n"
                "- 'Where is my order #12345?'\n"
                "- 'I want to return this broken item but I lost the receipt'\n"
                "- 'Your product ruined my carpet and I want compensation NOW'",
            ).classes("w-full").props("rows=4")

            with ui.row().classes("q-mt-sm gap-sm"):
                edge_case_cb = ui.checkbox("Edge case").tooltip(
                    "Check if this tests an unusual or boundary scenario"
                )
                adversarial_cb = ui.checkbox("Adversarial").tooltip(
                    "Check if this tests malicious or off-topic input"
                )

            expected_input = ui.textarea(
                placeholder="Expected behavior (optional): How should the agent respond?",
            ).classes("w-full q-mt-sm").props("rows=2")

            rationale_input = ui.textarea(
                placeholder="Rationale (optional): Why is this prompt important to test?",
            ).classes("w-full q-mt-sm").props("rows=2")

            # --- Comparison feedback area ---
            ui.separator().classes("q-my-md")
            ui.label("Constant Comparison (checking for gaps)").classes(
                "text-subtitle2 q-mb-xs"
            )
            comparison_card = ui.card().classes("w-full q-pa-sm").props("bordered flat")
            with comparison_card:
                ui.label(
                    "After you add a prompt, we'll compare it against your existing set "
                    "and show whether it adds unique coverage."
                ).classes("text-caption text-grey-7")

            async def on_add_prompt():
                text = prompt_input.value.strip()
                if not text:
                    ui.notify("Please write a prompt first.", type="warning")
                    return

                cat_id = selected_category_id["value"]
                if not cat_id and session.categories:
                    ui.notify("Please select a category.", type="warning")
                    return
                if not cat_id:
                    cat_id = uuid4()

                add_btn.props("loading")

                # Run constant comparison in background
                try:
                    result = await asyncio.to_thread(
                        constant_comparison,
                        text,
                        session.golden_prompts,
                        session.categories,
                    )

                    # Show comparison result
                    comparison_card.clear()
                    with comparison_card:
                        if result.is_unique:
                            with ui.row().classes("items-center gap-xs"):
                                ui.icon("check_circle", color="green", size="sm")
                                ui.label("Unique! This adds new coverage.").classes(
                                    "text-body2 text-green"
                                )
                            if result.gaps_filled:
                                ui.label(
                                    f"Fills: {', '.join(result.gaps_filled)}"
                                ).classes("text-caption text-grey-7")
                        else:
                            with ui.row().classes("items-center gap-xs"):
                                ui.icon("warning", color="orange", size="sm")
                                ui.label("Similar to existing prompts.").classes(
                                    "text-body2 text-orange"
                                )
                            if result.similar_existing:
                                ui.label(
                                    f"Similar to: {', '.join(result.similar_existing[:3])}"
                                ).classes("text-caption text-grey-7")

                        if result.suggestions:
                            ui.separator().classes("q-my-xs")
                            ui.label("Try next:").classes("text-caption text-weight-medium")
                            for s in result.suggestions[:3]:
                                ui.label(f"  • {s}").classes("text-caption text-grey-8")

                except Exception as e:
                    comparison_card.clear()
                    with comparison_card:
                        ui.label(f"Comparison unavailable: {e}").classes(
                            "text-caption text-orange"
                        )

                # Add to golden dataset regardless
                golden_prompt = GoldenPrompt(
                    prompt_text=text,
                    category_id=cat_id,
                    expected_behavior=expected_input.value or "",
                    rationale=rationale_input.value or "",
                    is_edge_case=edge_case_cb.value,
                    is_adversarial=adversarial_cb.value,
                )
                session.add_golden_prompt(golden_prompt)

                # Clear inputs
                prompt_input.set_value("")
                expected_input.set_value("")
                rationale_input.set_value("")
                edge_case_cb.set_value(False)
                adversarial_cb.set_value(False)

                # Refresh UI
                refresh_categories()
                refresh_coverage()
                refresh_suggestions()
                add_btn.props(remove="loading")
                ui.notify("Prompt added to golden dataset!", type="positive")

            add_btn = ui.button(
                "Add to Golden Dataset", icon="add", on_click=on_add_prompt
            ).props("color=primary").classes("q-mt-sm")

        # ========== RIGHT: AI suggestions ==========
        suggestions_container = ui.column().classes("w-72")

        def refresh_suggestions():
            suggestions_container.clear()
            with suggestions_container:
                ui.label("AI Suggestions").classes("text-subtitle2 q-mb-sm")

                if not session.categories:
                    ui.label(
                        "Suggestions will appear after categories are generated."
                    ).classes("text-caption text-grey-7")
                    return

                # Generate suggestions based on gaps
                coverage = session.coverage()
                if coverage.gaps:
                    ui.label("Focus on these gaps:").classes(
                        "text-caption text-weight-medium q-mb-xs"
                    )
                    for gap in coverage.gaps[:5]:
                        with ui.card().classes("w-full q-pa-xs q-mb-xs").props(
                            "bordered flat"
                        ):
                            ui.label(gap).classes("text-caption text-orange")
                else:
                    ui.label(
                        "All categories covered! Try varying dimensions:"
                    ).classes("text-caption text-grey-7 q-mb-xs")

                # Show property-based suggestions
                for cat in session.categories[:5]:
                    if cat.saturation != SaturationStatus.SATURATED and cat.properties:
                        for prop in cat.properties[:1]:
                            if prop.dimensions:
                                dim = prop.dimensions[0]
                                suggestion = (
                                    f"Try '{cat.name}' with {prop.name} "
                                    f"at '{dim.high_anchor}' level"
                                )
                                with ui.card().classes(
                                    "w-full q-pa-xs q-mb-xs"
                                ).props("bordered flat"):
                                    ui.label(suggestion).classes("text-caption")

                ui.separator().classes("q-my-sm")
                ui.label("Saturation (do you have enough?)").classes(
                    "text-subtitle2 q-mb-xs"
                )
                rec = saturation_recommendation(coverage)
                ui.label(rec).classes("text-caption text-grey-8")

        refresh_suggestions()
