"""Guided Mass Effect localization specialist demo for GEDD outputs."""

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
from grounded_evals.ui.layout import page_layout
from grounded_evals.ui.mass_effect_localization_demo import (
    MASS_EFFECT_LOCALIZATION_ANNOTATIONS,
    MASS_EFFECT_LOCALIZATION_CODEBOOK,
    MASS_EFFECT_LOCALIZATION_CODING_ANNOTATIONS,
    MASS_EFFECT_LOCALIZATION_EVAL_HISTORY,
    MASS_EFFECT_LOCALIZATION_JUDGE_PROMPT,
    MASS_EFFECT_LOCALIZATION_PARADIGM_MODEL,
    MASS_EFFECT_LOCALIZATION_SESSION,
    load_mass_effect_localization_demo,
)


MASS_EFFECT_DEMO_CSS = """
.me-demo-tabs {
  margin-top: 18px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface-1);
  padding: 6px;
}
.me-demo-tab-panels {
  margin-top: 12px;
  background: transparent !important;
}
.me-demo-panel {
  padding: 0 !important;
  background: transparent !important;
}
.me-flow-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}
.me-flow-step,
.me-artifact-panel,
.me-query-row,
.me-code-row {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface-1);
}
.me-flow-step {
  padding: 13px;
  min-height: 126px;
}
.me-step-num {
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
.me-step-title {
  margin-top: 9px;
  color: var(--text-primary);
  font-size: 0.82rem;
  font-weight: 740;
}
.me-step-copy {
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 0.72rem;
  line-height: 1.46;
}
.me-workflow-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}
.me-artifact-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  margin-top: 14px;
}
.me-artifact-panel {
  padding: 14px;
  min-width: 0;
}
.me-panel-label {
  color: var(--text-tertiary);
  font-size: 0.64rem;
  font-weight: 760;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.me-panel-title {
  margin-top: 6px;
  color: var(--text-primary);
  font-size: 0.92rem;
  font-weight: 740;
}
.me-panel-copy,
.me-code-def,
.me-query-note {
  color: var(--text-secondary);
  font-size: 0.74rem;
  line-height: 1.5;
}
.me-query-list,
.me-code-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}
.me-query-row {
  padding: 11px 12px;
}
.me-query-text {
  color: var(--text-primary);
  font-size: 0.78rem;
  line-height: 1.45;
  font-weight: 590;
}
.me-query-note {
  margin-top: 5px;
}
.me-code-row {
  padding: 11px 12px;
}
.me-code-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
}
.me-code-name {
  color: var(--text-primary);
  font-size: 0.78rem;
  font-weight: 720;
}
.me-severity {
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
.me-preview {
  max-height: 430px;
  overflow: auto;
  margin-top: 12px;
  padding: 13px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: #0b0f14;
}
.me-preview pre,
.me-preview code {
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-secondary);
  font-size: 0.72rem;
  line-height: 1.48;
}
@media (max-width: 1000px) {
  .me-flow-grid,
  .me-artifact-grid {
    grid-template-columns: 1fr;
  }
}
"""


def _requirements_preview() -> str:
    session = Session.model_validate(copy.deepcopy(MASS_EFFECT_LOCALIZATION_SESSION))
    if not session.codes:
        session.codes = _codes_from_codebook(MASS_EFFECT_LOCALIZATION_CODEBOOK)
    _link_annotations_to_prompts(session, MASS_EFFECT_LOCALIZATION_CODING_ANNOTATIONS)
    markdown = _build_requirements_markdown(session, MASS_EFFECT_LOCALIZATION_CODEBOOK)
    return markdown[:4800] + ("\n\n..." if len(markdown) > 4800 else "")


def _load_demo() -> None:
    load_mass_effect_localization_demo(app.storage.user)
    ui.notify("Mass Effect localization demo loaded.", type="positive")


def _load_and_open(path: str) -> None:
    _load_demo()
    ui.navigate.to(path)


def _render_workflow() -> None:
    steps = [
        (
            "01",
            "Franchise frame",
            "LQA lead reviews a Mass Effect localization assistant for lore, UI, subtitles, and store copy.",
        ),
        (
            "02",
            "Specialist coding",
            "The specialist labels failures around lore terms, runtime tokens, controls, and rating copy.",
        ),
        (
            "03",
            "Domain specs",
            "Observed defects become EARS requirements for a Kiro requirements.md handoff.",
        ),
        (
            "04",
            "LLM judge",
            "The same failure modes become Mass Effect localization release gates.",
        ),
    ]
    with ui.element("div").classes("me-flow-grid"):
        for number, title, copy_text in steps:
            with ui.element("div").classes("me-flow-step"):
                ui.html(f'<div class="me-step-num">{number}</div>')
                ui.html(f'<div class="me-step-title">{_html.escape(title)}</div>')
                ui.html(f'<div class="me-step-copy">{_html.escape(copy_text)}</div>')


def _render_scenario_tab() -> None:
    with ui.element("section").classes("dynamic-panel accent-blue"):
        ui.html('<div class="dynamic-panel-title">Mass Effect Localization Specialist</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            "MassEffectLocaleGate reviews localization risks for a military sci-fi RPG setting "
            "with humanity, alien civilizations, mass relay travel, squad combat, player choices, "
            "and region-specific storefront requirements."
            "</div>"
        )
        _render_workflow()
        with ui.element("div").classes("me-workflow-actions"):
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
                "Open requirements.md",
                icon="description",
                on_click=lambda: _load_and_open("/requirements"),
            ).props("outline no-caps")
            ui.button(
                "Open Judge",
                icon="gavel",
                on_click=lambda: _load_and_open("/judge"),
            ).props("outline no-caps")

    with ui.element("div").classes("me-artifact-grid"):
        with ui.element("div").classes("me-artifact-panel"):
            ui.html('<div class="me-panel-label">Specialist outcome</div>')
            ui.html('<div class="me-panel-title">Domain-driven specs</div>')
            ui.html(
                '<div class="me-panel-copy">'
                "The requirements are not generic translation advice. They encode Mass Effect "
                "lore glossary fidelity, runtime token preservation, biotic/system terminology, "
                "choice-state safety, RTL controller validation, and store copy boundaries."
                "</div>"
            )
        with ui.element("div").classes("me-artifact-panel"):
            ui.html('<div class="me-panel-label">Judge outcome</div>')
            ui.html('<div class="me-panel-title">Release gates from LQA evidence</div>')
            ui.html(
                '<div class="me-panel-copy">'
                "The judge fails answers that approve fluent but unsafe localization, including "
                "lost placeholders, wrong squad controls, product-scope drift, ratings softening, "
                "and canon role flattening."
                "</div>"
            )


def _render_evidence_tab() -> None:
    with ui.element("section").classes("dynamic-panel accent-teal"):
        ui.html('<div class="dynamic-panel-title">Specialist evidence set</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            f'{len(MASS_EFFECT_LOCALIZATION_SESSION["golden_prompts"])} Mass Effect LQA prompts, '
            f'{len(MASS_EFFECT_LOCALIZATION_CODEBOOK)} failure modes, '
            f'{len(MASS_EFFECT_LOCALIZATION_CODING_ANNOTATIONS)} coded specialist observations.'
            "</div>"
        )
        with ui.element("div").classes("me-query-list"):
            for annotation in MASS_EFFECT_LOCALIZATION_ANNOTATIONS[:4]:
                with ui.element("div").classes("me-query-row"):
                    ui.html(f'<div class="me-query-text">{_html.escape(annotation["query"])}</div>')
                    ui.html(f'<div class="me-query-note">{_html.escape(annotation["notes"])}</div>')

    with ui.element("div").classes("me-artifact-grid"):
        with ui.element("div").classes("me-artifact-panel"):
            ui.html('<div class="me-panel-label">Axial coding</div>')
            ui.html('<div class="me-panel-title">Core phenomenon</div>')
            for item in MASS_EFFECT_LOCALIZATION_PARADIGM_MODEL["phenomenon"]:
                ui.html(f'<div class="me-panel-copy">- {_html.escape(item)}</div>')
        with ui.element("div").classes("me-artifact-panel"):
            ui.html('<div class="me-panel-label">Observed consequence</div>')
            ui.html('<div class="me-panel-title">What the gates prevent</div>')
            for item in MASS_EFFECT_LOCALIZATION_PARADIGM_MODEL["consequences"][:4]:
                ui.html(f'<div class="me-panel-copy">- {_html.escape(item)}</div>')


def _render_requirements_tab() -> None:
    with ui.element("section").classes("dynamic-panel accent-violet"):
        ui.html('<div class="dynamic-panel-title">Output 1: Kiro requirements.md</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            "The requirements are generated from the Mass Effect localization codebook and linked "
            "LQA evidence. Loading the workspace makes the full document available in requirements.md."
            "</div>"
        )
        with ui.element("div").classes("me-code-list"):
            for code in MASS_EFFECT_LOCALIZATION_CODEBOOK[:5]:
                with ui.element("div").classes("me-code-row"):
                    with ui.element("div").classes("me-code-top"):
                        ui.html(f'<div class="me-code-name">{_html.escape(code["name"])}</div>')
                        ui.html(
                            '<div class="me-severity">'
                            f'{_html.escape(code["severity_label"])}</div>'
                        )
                    ui.html(
                        f'<div class="me-code-def">{_html.escape(code.get("release_gate", code["definition"]))}</div>'
                    )
        with ui.element("div").classes("me-preview"):
            ui.markdown(f"```markdown\n{_requirements_preview()}\n```")


def _render_judge_tab() -> None:
    with ui.element("section").classes("dynamic-panel accent-orange"):
        ui.html('<div class="dynamic-panel-title">Output 2: LLM-as-a-Judge prompt</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            "The judge uses Mass Effect-specific localization failure modes as hard release gates "
            "and returns a structured verdict for each candidate assistant answer."
            "</div>"
        )
        with ui.element("div").classes("me-preview"):
            ui.markdown(f"```text\n{MASS_EFFECT_LOCALIZATION_JUDGE_PROMPT}\n```")


@ui.page("/mass-effect-localization-demo")
def mass_effect_demo_page() -> None:
    page_layout("Mass Effect LQA", current_path="/mass-effect-localization-demo")
    ui.add_head_html(f"<style>{MASS_EFFECT_DEMO_CSS}</style>")

    with ui.element("main").classes("dynamic-page"):
        with ui.element("section").classes("dynamic-hero"):
            with ui.element("div"):
                ui.html(
                    '<div class="dynamic-kicker">'
                    '<span class="material-icons" style="font-size:0.95rem">translate</span>'
                    "Mass Effect localization demo"
                    "</div>"
                )
                ui.html('<div class="dynamic-title">Mass Effect localization assistant to specs and judge</div>')
                ui.html(
                    '<div class="dynamic-copy">'
                    "A localization specialist reviews an AAA sci-fi RPG assistant, names the "
                    "Mass Effect-specific release risks, and turns that evidence into Kiro "
                    "requirements.md plus an LLM-as-a-judge release gate."
                    "</div>"
                )
            with ui.element("aside").classes("dynamic-side-panel"):
                ui.html('<div class="dynamic-side-label">Scenario</div>')
                ui.html('<div class="dynamic-side-value">8</div>')
                ui.html('<div class="dynamic-side-copy">LQA prompts with 7 specialist failure modes.</div>')

        with ui.element("section").classes("metric-strip"):
            for value, label in [
                ("Mass Effect", "Franchise context"),
                ("LQA", "Specialist role"),
                ("7", "Failure modes"),
                ("2", "Generated outputs"),
            ]:
                with ui.element("div").classes("metric-tile"):
                    ui.html(f'<div class="metric-tile-value">{value}</div>')
                    ui.html(f'<div class="metric-tile-label">{label}</div>')

        with ui.tabs().classes("me-demo-tabs") as tabs:
            scenario = ui.tab("Scenario")
            evidence = ui.tab("Evidence")
            requirements = ui.tab("requirements.md")
            judge = ui.tab("LLM Judge")

        with ui.tab_panels(tabs, value=scenario).classes("me-demo-tab-panels"):
            with ui.tab_panel(scenario).classes("me-demo-panel"):
                _render_scenario_tab()
            with ui.tab_panel(evidence).classes("me-demo-panel"):
                _render_evidence_tab()
            with ui.tab_panel(requirements).classes("me-demo-panel"):
                _render_requirements_tab()
            with ui.tab_panel(judge).classes("me-demo-panel"):
                _render_judge_tab()
