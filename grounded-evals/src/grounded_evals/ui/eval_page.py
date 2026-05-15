"""Eval page — Run golden queries against models and annotate."""

from nicegui import app, ui

from grounded_evals.guide.session import Session
from grounded_evals.ui.eval_tab import render as render_eval_tab
from grounded_evals.ui.layout import page_layout


@ui.page("/eval")
def eval_page():
    page_layout("Evaluation")

    s = app.storage.user
    session_data = s.get("session_data", {})
    session = Session.model_validate(session_data) if session_data else Session()
    annotations = s.get("annotations", [])
    prompt_variants = s.get("prompt_variants", [])

    with ui.column().classes("w-full").style("max-width: 1200px; margin: 1rem auto; padding: 0 1.5rem"):
        render_eval_tab(session, annotations, prompt_variants)
