"""Guided GDPR specialist demo for GEDD outputs."""

from __future__ import annotations

import copy
import html as _html

from nicegui import app, ui

from grounded_evals.guide.session import Session
from grounded_evals.ui.ears_page import (
    _build_requirements_markdown,
    _codes_from_codebook,
    _link_annotations_to_prompts,
)
from grounded_evals.ui.gdpr_auditor_demo import (
    GDPR_AUDITOR_CODEBOOK,
    GDPR_AUDITOR_CODING_ANNOTATIONS,
    GDPR_AUDITOR_JUDGE_PROMPT,
    GDPR_AUDITOR_METHODOLOGY,
    GDPR_AUDITOR_PARADIGM_MODEL,
    GDPR_AUDITOR_SAMPLE_QUERIES,
    GDPR_AUDITOR_SESSION,
    GDPR_AUDITOR_TRACES,
    load_gdpr_auditor_demo,
)
from grounded_evals.ui.layout import page_layout


GDPR_DEMO_CSS = """
.gdpr-demo-tabs {
  margin-top: 18px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface-1);
  padding: 6px;
}
.gdpr-demo-tab-panels {
  margin-top: 12px;
  background: transparent !important;
}
.gdpr-demo-panel {
  padding: 0 !important;
  background: transparent !important;
}
.gdpr-flow-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}
.gdpr-flow-step,
.gdpr-artifact-panel,
.gdpr-query-row,
.gdpr-code-row {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface-1);
}
.gdpr-flow-step {
  padding: 13px;
  min-height: 126px;
}
.gdpr-step-num {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--accent-tint);
  color: var(--accent-bright);
  font-size: 0.72rem;
  font-weight: 780;
}
.gdpr-step-title {
  margin-top: 9px;
  color: var(--text-primary);
  font-size: 0.82rem;
  font-weight: 740;
}
.gdpr-step-copy {
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 0.72rem;
  line-height: 1.46;
}
.gdpr-workflow-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}
.gdpr-artifact-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  margin-top: 14px;
}
.gdpr-artifact-panel {
  padding: 14px;
  min-width: 0;
}
.gdpr-panel-label {
  color: var(--text-tertiary);
  font-size: 0.64rem;
  font-weight: 760;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.gdpr-panel-title {
  margin-top: 6px;
  color: var(--text-primary);
  font-size: 0.92rem;
  font-weight: 740;
}
.gdpr-panel-copy,
.gdpr-code-def,
.gdpr-query-note {
  color: var(--text-secondary);
  font-size: 0.74rem;
  line-height: 1.5;
}
.gdpr-query-list,
.gdpr-code-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}
.gdpr-query-row {
  padding: 11px 12px;
}
.gdpr-query-text {
  color: var(--text-primary);
  font-size: 0.78rem;
  line-height: 1.45;
  font-weight: 590;
}
.gdpr-query-note {
  margin-top: 5px;
}
.gdpr-code-row {
  padding: 11px 12px;
}
.gdpr-code-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
}
.gdpr-code-name {
  color: var(--text-primary);
  font-size: 0.78rem;
  font-weight: 720;
}
.gdpr-severity {
  flex-shrink: 0;
  padding: 3px 7px;
  border: 1px solid var(--border-subtle);
  border-radius: 99px;
  color: var(--red);
  background: var(--red-tint);
  font-size: 0.58rem;
  font-weight: 760;
  text-transform: uppercase;
}
.gdpr-preview {
  max-height: 430px;
  overflow: auto;
  margin-top: 12px;
  padding: 13px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: #0b0f14;
}
.gdpr-preview pre,
.gdpr-preview code {
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-secondary);
  font-size: 0.72rem;
  line-height: 1.48;
}
@media (max-width: 1000px) {
  .gdpr-flow-grid,
  .gdpr-artifact-grid {
    grid-template-columns: 1fr;
  }
}
"""


def _requirements_preview() -> str:
    session = Session.model_validate(copy.deepcopy(GDPR_AUDITOR_SESSION))
    if not session.codes:
        session.codes = _codes_from_codebook(GDPR_AUDITOR_CODEBOOK)
    _link_annotations_to_prompts(session, GDPR_AUDITOR_CODING_ANNOTATIONS)
    markdown = _build_requirements_markdown(session, GDPR_AUDITOR_CODEBOOK)
    return markdown[:4800] + ("\n\n..." if len(markdown) > 4800 else "")


def _load_demo() -> None:
    load_gdpr_auditor_demo(app.storage.user)
    ui.notify("GDPR specialist demo loaded.", type="positive")


def _load_and_open(path: str) -> None:
    _load_demo()
    ui.navigate.to(path)


def _render_workflow() -> None:
    steps = [
        (
            "01",
            "Specialist frame",
            "Cloud privacy lead reviews an AWS GDPR assistant that gives plausible cloud answers.",
        ),
        (
            "02",
            "SME annotations",
            "The specialist labels 50 traces across legal basis, sensitive data, DSARs, transfers, and breach handling.",
        ),
        (
            "03",
            "Domain specs",
            "Observed failures become EARS acceptance criteria for a judge-spec handoff.",
        ),
        (
            "04",
            "LLM judge",
            "The same failure modes become hard gates for release evaluation.",
        ),
    ]
    with ui.element("div").classes("gdpr-flow-grid"):
        for number, title, copy_text in steps:
            with ui.element("div").classes("gdpr-flow-step"):
                ui.html(f'<div class="gdpr-step-num">{number}</div>')
                ui.html(f'<div class="gdpr-step-title">{_html.escape(title)}</div>')
                ui.html(f'<div class="gdpr-step-copy">{_html.escape(copy_text)}</div>')


def _render_scenario_tab() -> None:
    with ui.element("section").classes("dynamic-panel accent-teal"):
        ui.html('<div class="dynamic-panel-title">GDPR Compliance Specialist Assistant</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            "CloudAuditGate reviews AWS workload decisions for GDPR risk across S3, "
            "CloudWatch, CloudTrail, DynamoDB, Redshift, Rekognition, Bedrock, DSAR workflows, "
            "cross-region movement, vendor roles, and breach escalation."
            "</div>"
        )
        _render_workflow()
        with ui.element("div").classes("gdpr-workflow-actions"):
            ui.button(
                "Load demo workspace",
                icon="input",
                on_click=_load_demo,
            ).props("color=primary no-caps")
            ui.button(
                "Open Annotations",
                icon="rate_review",
                on_click=lambda: _load_and_open("/coding"),
            ).props("outline no-caps")
            ui.button(
                "Open Judge Spec",
                icon="description",
                on_click=lambda: _load_and_open("/requirements"),
            ).props("outline no-caps")
            ui.button(
                "Open Judge",
                icon="gavel",
                on_click=lambda: _load_and_open("/judge"),
            ).props("outline no-caps")

    with ui.element("div").classes("gdpr-artifact-grid"):
        with ui.element("div").classes("gdpr-artifact-panel"):
            ui.html('<div class="gdpr-panel-label">Specialist outcome</div>')
            ui.html('<div class="gdpr-panel-title">Domain-driven specs</div>')
            ui.html(
                '<div class="gdpr-panel-copy">'
                "The handoff is not a generic privacy checklist. It encodes audit rules such as "
                "wrong-purpose reuse, special-category data handling, one-month DSAR defaults, "
                "DPIA escalation, transfer checks, and breach notification clocks."
                "</div>"
            )
        with ui.element("div").classes("gdpr-artifact-panel"):
            ui.html('<div class="gdpr-panel-label">Judge outcome</div>')
            ui.html('<div class="gdpr-panel-title">Release gates from evidence</div>')
            ui.html(
                '<div class="gdpr-panel-copy">'
                "The judge fails responses that sound cloud-safe but approve GDPR-breaking "
                "designs, including wrong legal basis, unsafe Bedrock or Rekognition use, "
                "unreviewed third-country access, and delay tactics."
                "</div>"
            )


def _render_evidence_tab() -> None:
    with ui.element("section").classes("dynamic-panel accent-blue"):
        ui.html('<div class="dynamic-panel-title">Specialist evidence set</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            f'{GDPR_AUDITOR_METHODOLOGY["synthetic_query_count"]} AWS GDPR traces, '
            f'{GDPR_AUDITOR_METHODOLOGY["open_code_count"]} open codes, final saturation window '
            f'with {GDPR_AUDITOR_METHODOLOGY["new_codes_in_final_window"]} new codes.'
            "</div>"
        )
        with ui.element("div").classes("gdpr-query-list"):
            for query in GDPR_AUDITOR_SAMPLE_QUERIES:
                with ui.element("div").classes("gdpr-query-row"):
                    ui.html(f'<div class="gdpr-query-text">{_html.escape(query["q"])}</div>')
                    ui.html(f'<div class="gdpr-query-note">{_html.escape(query["note"])}</div>')

    with ui.element("div").classes("gdpr-artifact-grid"):
        with ui.element("div").classes("gdpr-artifact-panel"):
            ui.html('<div class="gdpr-panel-label">Axial coding</div>')
            ui.html('<div class="gdpr-panel-title">Core phenomenon</div>')
            for item in GDPR_AUDITOR_PARADIGM_MODEL["phenomenon"]:
                ui.html(f'<div class="gdpr-panel-copy">- {_html.escape(item)}</div>')
        with ui.element("div").classes("gdpr-artifact-panel"):
            ui.html('<div class="gdpr-panel-label">Consequences</div>')
            ui.html('<div class="gdpr-panel-title">What the gates prevent</div>')
            for item in GDPR_AUDITOR_PARADIGM_MODEL["consequences"][:4]:
                ui.html(f'<div class="gdpr-panel-copy">- {_html.escape(item)}</div>')


def _render_requirements_tab() -> None:
    with ui.element("section").classes("dynamic-panel accent-violet"):
        ui.html('<div class="dynamic-panel-title">Output 1: Judge spec</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            "The judge spec is generated from the GDPR codebook and linked query evidence. "
            "Loading the workspace makes the full document available in the Judge Spec view."
            "</div>"
        )
        with ui.element("div").classes("gdpr-code-list"):
            for code in GDPR_AUDITOR_CODEBOOK[:5]:
                with ui.element("div").classes("gdpr-code-row"):
                    with ui.element("div").classes("gdpr-code-top"):
                        ui.html(f'<div class="gdpr-code-name">{_html.escape(code["name"])}</div>')
                        ui.html(
                            '<div class="gdpr-severity">'
                            f'{_html.escape(code["severity_label"])}</div>'
                        )
                    ui.html(f'<div class="gdpr-code-def">{_html.escape(code["release_gate"])}</div>')
        with ui.element("div").classes("gdpr-preview"):
            ui.markdown(f"```markdown\n{_requirements_preview()}\n```")


def _render_judge_tab() -> None:
    with ui.element("section").classes("dynamic-panel accent-orange"):
        ui.html('<div class="dynamic-panel-title">Output 2: LLM-as-a-Judge prompt</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            "The judge uses the specialist codebook as release gates and returns structured JSON "
            "with verdict, blocker status, matched failure modes, severity, and rationale."
            "</div>"
        )
        with ui.element("div").classes("gdpr-preview"):
            ui.markdown(f"```text\n{GDPR_AUDITOR_JUDGE_PROMPT}\n```")


@ui.page("/gdpr-demo")
def gdpr_demo_page() -> None:
    page_layout("GDPR Demo", current_path="/gdpr-demo")
    ui.add_head_html(f"<style>{GDPR_DEMO_CSS}</style>")

    with ui.element("main").classes("dynamic-page"):
        with ui.element("section").classes("dynamic-hero"):
            with ui.element("div"):
                ui.html(
                    '<div class="dynamic-kicker">'
                    '<span class="material-icons" style="font-size:0.95rem">policy</span>'
                    "GDPR specialist demo"
                    "</div>"
                )
                ui.html('<div class="dynamic-title">AWS GDPR assistant to specs and judge</div>')
                ui.html(
                    '<div class="dynamic-copy">'
                    "A GDPR compliance specialist reviews a cloud assistant, names the domain "
                    "failure modes, and turns that evidence into a judge spec plus an "
                    "LLM-as-a-judge release gate."
                    "</div>"
                )
            with ui.element("aside").classes("dynamic-side-panel"):
                ui.html('<div class="dynamic-side-label">Scenario</div>')
                ui.html('<div class="dynamic-side-value">50</div>')
                ui.html('<div class="dynamic-side-copy">AWS GDPR traces with 10 specialist failure modes.</div>')

        with ui.element("section").classes("metric-strip"):
            for value, label in [
                ("GDPR", "Domain"),
                ("AWS", "Workload context"),
                ("10", "Failure modes"),
                ("2", "Generated outputs"),
            ]:
                with ui.element("div").classes("metric-tile"):
                    ui.html(f'<div class="metric-tile-value">{value}</div>')
                    ui.html(f'<div class="metric-tile-label">{label}</div>')

        with ui.tabs().classes("gdpr-demo-tabs") as tabs:
            scenario = ui.tab("Scenario")
            evidence = ui.tab("Evidence")
            requirements = ui.tab("Judge Spec")
            judge = ui.tab("LLM Judge")

        with ui.tab_panels(tabs, value=scenario).classes("gdpr-demo-tab-panels"):
            with ui.tab_panel(scenario).classes("gdpr-demo-panel"):
                _render_scenario_tab()
            with ui.tab_panel(evidence).classes("gdpr-demo-panel"):
                _render_evidence_tab()
            with ui.tab_panel(requirements).classes("gdpr-demo-panel"):
                _render_requirements_tab()
            with ui.tab_panel(judge).classes("gdpr-demo-panel"):
                _render_judge_tab()
