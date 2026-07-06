"""NiceGUI page for EARS quality comparison."""

from __future__ import annotations

from uuid import UUID

from nicegui import app, ui

from grounded_evals.ears.baseline import BaselineGenerator
from grounded_evals.ears.measurement import MeasurementEngine
from grounded_evals.ears.transformer import CodeMetrics, EARSTransformer
from grounded_evals.guide.session import Session
from grounded_evals.ui.ears_page import _session_from_storage
from grounded_evals.ui.layout import page_layout


def _build_report(session: Session):
    metrics: dict[UUID, CodeMetrics] = {
        code.id: CodeMetrics(severity=3, frequency=1, dimension="quality")
        for code in session.codes
    }
    gedd_doc = EARSTransformer().transform(session, metrics, paradigm=None)
    baseline_doc = BaselineGenerator().generate(session.agent_spec)
    return MeasurementEngine().measure(baseline_doc, gedd_doc, session)


@ui.page("/improvement")
def improvement_page() -> None:
    page_layout("requirements.md Quality", current_path="/improvement")
    session = _session_from_storage(app.storage.user)

    with ui.element("main").classes("dynamic-page"):
        with ui.element("section").classes("dynamic-hero"):
            with ui.element("div"):
                ui.html(
                    '<div class="dynamic-kicker">'
                    '<span class="material-icons" style="font-size:0.95rem">monitoring</span>'
                    "Measurement"
                    "</div>"
                )
                ui.html('<div class="dynamic-title">requirements.md quality uplift</div>')
                ui.html(
                    '<div class="dynamic-copy">'
                    "Compare the baseline Kiro requirements against the GEDD-improved spec "
                    "created from SME-curated query results and annotations."
                    "</div>"
                )
            with ui.element("aside").classes("dynamic-side-panel"):
                ui.html('<div class="dynamic-side-label">Evidence drivers</div>')
                ui.html(f'<div class="dynamic-side-value">{len(session.codes)}</div>')
                ui.html('<div class="dynamic-side-copy">Failure modes available for measuring requirements quality.</div>')

        if not session.codes:
            with ui.element("div").classes("empty-state-panel"):
                ui.icon("monitoring")
                ui.html('<div class="empty-state-title">No measurement evidence yet</div>')
                ui.html(
                    '<div class="empty-state-copy">'
                    "Test the Kiro baseline agent with curated domain queries, then annotate "
                    "failures before measuring requirements uplift."
                    "</div>"
                )
                ui.button("Open Coach", icon="auto_awesome", on_click=lambda: ui.navigate.to("/coach")).props(
                    "color=primary no-caps"
                ).style("margin-top:16px")
            return

        report = _build_report(session)
        with ui.element("section").classes("metric-strip"):
            for value, label in [
                (f"{report.overall_improvement:+.1f}%", "Overall delta"),
                (len(report.comparisons), "Quality metrics"),
                (len(session.codes), "Failure modes"),
                ("EARS", "Criteria style"),
            ]:
                with ui.element("div").classes("metric-tile"):
                    ui.html(f'<div class="metric-tile-value">{value}</div>')
                    ui.html(f'<div class="metric-tile-label">{label}</div>')

        with ui.element("section").classes("dynamic-panel accent-blue").style("margin-top:16px"):
            ui.html('<div class="dynamic-panel-title">Quality comparison</div>')
            ui.html(
                '<div class="dynamic-panel-copy">'
                "Baseline vs GEDD-improved requirements across specificity, traceability, "
                "testability, and domain coverage."
                "</div>"
            )
            rows = [
                {
                    "metric": comp.metric_name,
                    "baseline": f"{comp.baseline_score:.1f}%",
                    "gedd": f"{comp.gedd_score:.1f}%",
                    "delta": f"{comp.absolute_improvement:+.1f}%",
                }
                for comp in report.comparisons
            ]
            ui.table(
                columns=[
                    {"name": "metric", "label": "Metric", "field": "metric"},
                    {"name": "baseline", "label": "Baseline", "field": "baseline"},
                    {"name": "gedd", "label": "GEDD", "field": "gedd"},
                    {"name": "delta", "label": "Delta", "field": "delta"},
                ],
                rows=rows,
                row_key="metric",
            ).classes("w-full").style("margin-top:12px")
