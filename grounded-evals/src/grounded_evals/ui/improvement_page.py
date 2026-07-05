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

    with ui.column().classes("w-full").style(
        "max-width: 900px; margin: 1rem auto; padding: 0 1rem"
    ):
        ui.label("requirements.md Quality").style(
            "font-size:1.25rem; font-weight:700; color:var(--text-primary)"
        )
        ui.label(
            "Compares generic baseline requirements against the Kiro-ready requirements.md output."
        ).style("font-size:0.82rem; color:var(--text-tertiary)")

        if not session.codes:
            ui.label(
                "No failure codes are available yet. Spec quality improves once "
                "PM annotations create codes."
            ).style("margin-top:1rem; color:var(--text-secondary)")
            return

        report = _build_report(session)
        with ui.card().classes("w-full").style("margin-top:1rem; padding:1rem"):
            ui.label(f"Overall delta: {report.overall_improvement:.1f}%").style(
                "font-size:1rem; font-weight:700; color:var(--text-primary)"
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
            ).classes("w-full")
