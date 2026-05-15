from __future__ import annotations

from nicegui import ui

from grounded_evals.guide.session import Session


def render(session: Session) -> None:
    ui.label("Build Context for Your Agent").classes("text-h6 q-mb-md")
    ui.label(
        "Provide domain knowledge that helps us understand your agent's world. "
        "This context helps generate better evaluation scenarios."
    ).classes("text-body1 text-grey-8 q-mb-lg")

    with ui.card().classes("w-full q-pa-md"):
        ui.label("Domain Context").classes("text-subtitle2")
        ui.label(
            "Paste relevant documentation, FAQs, or describe the domain your agent operates in."
        ).classes("text-caption text-grey-7")
        ui.textarea(
            placeholder="e.g., Our e-commerce platform sells electronics and home goods. "
            "We have a 30-day return policy for most items, except final sale items...",
            value=session.agent_spec.domain_context,
        ).classes("w-full").props("rows=8")

    ui.separator().classes("q-my-lg")

    with ui.card().classes("w-full q-pa-md"):
        ui.label("Example Conversations (optional)").classes("text-subtitle2")
        ui.label(
            "Paste 2-3 example conversations showing how your agent should behave."
        ).classes("text-caption text-grey-7")
        ui.textarea(
            placeholder="User: Where is my order #12345?\n"
            "Agent: Let me look that up for you. Your order #12345 shipped on...",
        ).classes("w-full").props("rows=8")

    with ui.card().classes("w-full q-pa-md q-mt-md") as hint_card:
        hint_card.props("bordered")
        with ui.row().classes("items-center"):
            ui.icon("lightbulb", color="amber").classes("text-h6")
            ui.label("Tip").classes("text-subtitle2")
        ui.label(
            "The more context you provide here, the better the tool can suggest "
            "diverse test scenarios in the next step. Think about: product categories, "
            "policies, common customer issues, seasonal patterns."
        ).classes("text-body2 text-grey-8")
