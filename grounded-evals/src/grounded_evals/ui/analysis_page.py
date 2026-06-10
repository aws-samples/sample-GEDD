"""Deprecated analysis route."""

from nicegui import ui


@ui.page("/analysis")
def analysis_page() -> None:
    ui.navigate.to("/judge")
