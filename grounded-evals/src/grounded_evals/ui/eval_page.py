"""Deprecated Eval page route."""

from nicegui import ui


@ui.page("/eval")
def eval_page():
    ui.navigate.to("/coding")
