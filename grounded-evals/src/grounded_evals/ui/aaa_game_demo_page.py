"""Guided AAA game localization specialist demo for GEDD outputs."""

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
from grounded_evals.ui.aaa_game_localization_demo import (
    AAA_GAME_BASELINE_REQUIREMENTS_MD,
    AAA_GAME_LOCALIZATION_ANNOTATIONS,
    AAA_GAME_LOCALIZATION_CODEBOOK,
    AAA_GAME_LOCALIZATION_CODING_ANNOTATIONS,
    AAA_GAME_LOCALIZATION_EVAL_HISTORY,
    AAA_GAME_LOCALIZATION_JUDGE_PROMPT,
    AAA_GAME_LOCALIZATION_PARADIGM_MODEL,
    AAA_GAME_LOCALIZATION_SESSION,
    load_aaa_game_localization_demo,
)


AAA_GAME_DEMO_CSS = """
.aaa-game-demo-tabs {
  margin-top: 18px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface-1);
  padding: 6px;
}
.aaa-game-demo-tab-panels {
  margin-top: 12px;
  background: transparent !important;
}
.aaa-game-demo-panel {
  padding: 0 !important;
  background: transparent !important;
}
.aaa-game-flow-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}
.aaa-game-flow-step,
.aaa-game-artifact-panel,
.aaa-game-query-row,
.aaa-game-code-row {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface-1);
}
.aaa-game-flow-step {
  padding: 13px;
  min-height: 126px;
}
.aaa-game-step-num {
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
.aaa-game-step-title {
  margin-top: 9px;
  color: var(--text-primary);
  font-size: 0.82rem;
  font-weight: 740;
}
.aaa-game-step-copy {
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 0.72rem;
  line-height: 1.46;
}
.aaa-game-workflow-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}
.aaa-game-artifact-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  margin-top: 14px;
}
.aaa-game-artifact-panel {
  padding: 14px;
  min-width: 0;
}
.aaa-game-panel-label {
  color: var(--text-tertiary);
  font-size: 0.64rem;
  font-weight: 760;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.aaa-game-panel-title {
  margin-top: 6px;
  color: var(--text-primary);
  font-size: 0.92rem;
  font-weight: 740;
}
.aaa-game-panel-copy,
.aaa-game-code-def,
.aaa-game-query-note {
  color: var(--text-secondary);
  font-size: 0.74rem;
  line-height: 1.5;
}
.aaa-game-query-list,
.aaa-game-code-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}
.aaa-game-query-row {
  padding: 11px 12px;
}
.aaa-game-query-text {
  color: var(--text-primary);
  font-size: 0.78rem;
  line-height: 1.45;
  font-weight: 590;
}
.aaa-game-query-note {
  margin-top: 5px;
}
.aaa-game-code-row {
  padding: 11px 12px;
}
.aaa-game-code-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
}
.aaa-game-code-name {
  color: var(--text-primary);
  font-size: 0.78rem;
  font-weight: 720;
}
.aaa-game-severity {
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
.aaa-game-preview {
  max-height: 430px;
  overflow: auto;
  margin-top: 12px;
  padding: 13px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: #0b0f14;
}
.aaa-game-preview pre,
.aaa-game-preview code {
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-secondary);
  font-size: 0.72rem;
  line-height: 1.48;
}
@media (max-width: 1000px) {
  .aaa-game-flow-grid,
  .aaa-game-artifact-grid {
    grid-template-columns: 1fr;
  }
}
"""


def _requirements_preview() -> str:
    session = Session.model_validate(copy.deepcopy(AAA_GAME_LOCALIZATION_SESSION))
    if not session.codes:
        session.codes = _codes_from_codebook(AAA_GAME_LOCALIZATION_CODEBOOK)
    _link_annotations_to_prompts(session, AAA_GAME_LOCALIZATION_CODING_ANNOTATIONS)
    markdown = _build_requirements_markdown(session, AAA_GAME_LOCALIZATION_CODEBOOK)
    return markdown[:4800] + ("\n\n..." if len(markdown) > 4800 else "")


def _load_demo() -> None:
    load_aaa_game_localization_demo(app.storage.user)
    ui.notify("AAA game localization demo loaded.", type="positive")


def _load_and_open(path: str) -> None:
    _load_demo()
    ui.navigate.to(path)


def _render_workflow() -> None:
    steps = [
        (
            "01",
            "Franchise frame",
            "LQA lead reviews a AAA game localization assistant for lore, UI, subtitles, and store copy.",
        ),
        (
            "02",
            "Specialist coding",
            "The specialist labels failures around lore terms, runtime tokens, controls, and rating copy.",
        ),
        (
            "03",
            "Judge-subagent spec",
            "Observed defects become EARS requirements for the Kiro LLM-as-Judge subagent.",
        ),
        (
            "04",
            "Response gate",
            "The same failure modes become AAA game localization gates before assistant answers reach users.",
        ),
    ]
    with ui.element("div").classes("aaa-game-flow-grid"):
        for number, title, copy_text in steps:
            with ui.element("div").classes("aaa-game-flow-step"):
                ui.html(f'<div class="aaa-game-step-num">{number}</div>')
                ui.html(f'<div class="aaa-game-step-title">{_html.escape(title)}</div>')
                ui.html(f'<div class="aaa-game-step-copy">{_html.escape(copy_text)}</div>')


def _render_scenario_tab() -> None:
    with ui.element("section").classes("dynamic-panel accent-blue"):
        ui.html('<div class="dynamic-panel-title">AAA Game Localization Agent judge scenario</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            "AAAGameLocaleGate reviews localization risks for an anonymized AAA game setting "
            "with franchise-specific lore, party combat, branching choices, runtime tokens, "
            "and region-specific storefront requirements."
            "</div>"
        )
        _render_workflow()
        with ui.element("div").classes("aaa-game-workflow-actions"):
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

    with ui.element("div").classes("aaa-game-artifact-grid"):
        with ui.element("div").classes("aaa-game-artifact-panel"):
            ui.html('<div class="aaa-game-panel-label">Specialist outcome</div>')
            ui.html('<div class="aaa-game-panel-title">Kiro judge-subagent requirements</div>')
            ui.html(
                '<div class="aaa-game-panel-copy">'
                "The requirements specify how the judge subagent evaluates assistant answers. They encode AAA game "
                "lore glossary fidelity, runtime token preservation, ability-system terminology, "
                "choice-state safety, RTL controller validation, and store copy boundaries."
                "</div>"
            )
        with ui.element("div").classes("aaa-game-artifact-panel"):
            ui.html('<div class="aaa-game-panel-label">Judge outcome</div>')
            ui.html('<div class="aaa-game-panel-title">Response gates from LQA evidence</div>')
            ui.html(
                '<div class="aaa-game-panel-copy">'
                "The judge blocks assistant answers that approve fluent but unsafe localization, including "
                "lost placeholders, wrong party controls, product-scope drift, ratings softening, "
                "and canon role flattening."
                "</div>"
            )


def _render_evidence_tab() -> None:
    with ui.element("section").classes("dynamic-panel accent-teal"):
        ui.html('<div class="dynamic-panel-title">Specialist evidence set</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            f'{len(AAA_GAME_LOCALIZATION_SESSION["golden_prompts"])} AAA Game localization prompts, '
            f'{len(AAA_GAME_LOCALIZATION_CODEBOOK)} failure modes, '
            f'{len(AAA_GAME_LOCALIZATION_CODING_ANNOTATIONS)} coded specialist observations.'
            "</div>"
        )
        with ui.element("div").classes("aaa-game-query-list"):
            for annotation in AAA_GAME_LOCALIZATION_ANNOTATIONS[:4]:
                with ui.element("div").classes("aaa-game-query-row"):
                    ui.html(f'<div class="aaa-game-query-text">{_html.escape(annotation["query"])}</div>')
                    ui.html(f'<div class="aaa-game-query-note">{_html.escape(annotation["notes"])}</div>')

    with ui.element("div").classes("aaa-game-artifact-grid"):
        with ui.element("div").classes("aaa-game-artifact-panel"):
            ui.html('<div class="aaa-game-panel-label">Axial coding</div>')
            ui.html('<div class="aaa-game-panel-title">Core phenomenon</div>')
            for item in AAA_GAME_LOCALIZATION_PARADIGM_MODEL["phenomenon"]:
                ui.html(f'<div class="aaa-game-panel-copy">- {_html.escape(item)}</div>')
        with ui.element("div").classes("aaa-game-artifact-panel"):
            ui.html('<div class="aaa-game-panel-label">Observed consequence</div>')
            ui.html('<div class="aaa-game-panel-title">What the gates prevent</div>')
            for item in AAA_GAME_LOCALIZATION_PARADIGM_MODEL["consequences"][:4]:
                ui.html(f'<div class="aaa-game-panel-copy">- {_html.escape(item)}</div>')


def _render_requirements_tab() -> None:
    with ui.element("section").classes("dynamic-panel accent-violet"):
        ui.html('<div class="dynamic-panel-title">Output 1: Kiro judge-subagent requirements.md</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            "The requirements define the LLM-as-Judge subagent using the AAA game localization codebook "
            "and linked LQA evidence. Loading the workspace makes the full document available in requirements.md."
            "</div>"
        )
        with ui.element("div").classes("aaa-game-code-list"):
            for code in AAA_GAME_LOCALIZATION_CODEBOOK[:5]:
                with ui.element("div").classes("aaa-game-code-row"):
                    with ui.element("div").classes("aaa-game-code-top"):
                        ui.html(f'<div class="aaa-game-code-name">{_html.escape(code["name"])}</div>')
                        ui.html(
                            '<div class="aaa-game-severity">'
                            f'{_html.escape(code["severity_label"])}</div>'
                        )
                    ui.html(
                        f'<div class="aaa-game-code-def">{_html.escape(code.get("release_gate", code["definition"]))}</div>'
                    )
        with ui.element("div").classes("aaa-game-preview"):
            ui.markdown(f"```markdown\n{_requirements_preview()}\n```")


def _render_baseline_tab() -> None:
    preview = AAA_GAME_BASELINE_REQUIREMENTS_MD[:5200]
    if len(AAA_GAME_BASELINE_REQUIREMENTS_MD) > len(preview):
        preview += "\n\n..."
    with ui.element("section").classes("dynamic-panel accent-blue"):
        ui.html('<div class="dynamic-panel-title">Baseline requirements.md</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            "This is the starting Kiro-style requirements file for the AAA game localization "
            "assistant under test. GEDD uses SME annotations to create the separate judge-subagent "
            "requirements.md and response gates for lore drift, runtime tokens, controller prompts, product-scope copy, "
            "and regional compliance."
            "</div>"
        )
        with ui.element("div").classes("aaa-game-preview"):
            ui.markdown(f"```markdown\n{preview}\n```")


def _render_judge_tab() -> None:
    with ui.element("section").classes("dynamic-panel accent-orange"):
        ui.html('<div class="dynamic-panel-title">Output 2: LLM-as-Judge response gate</div>')
        ui.html(
            '<div class="dynamic-panel-copy">'
            "The judge uses AAA game-specific localization failure modes as hard gates and returns "
            "a structured verdict before each candidate assistant answer can become customer-visible."
            "</div>"
        )
        with ui.element("div").classes("aaa-game-preview"):
            ui.markdown(f"```text\n{AAA_GAME_LOCALIZATION_JUDGE_PROMPT}\n```")


@ui.page("/aaa-game-localization-demo")
def aaa_game_demo_page() -> None:
    page_layout("AAA Game Localization", current_path="/aaa-game-localization-demo")
    ui.add_head_html(f"<style>{AAA_GAME_DEMO_CSS}</style>")

    with ui.element("main").classes("dynamic-page"):
        with ui.element("section").classes("dynamic-hero"):
            with ui.element("div"):
                ui.html(
                    '<div class="dynamic-kicker">'
                    '<span class="material-icons" style="font-size:0.95rem">translate</span>'
                    "AAA game localization demo"
                    "</div>"
                )
                ui.html('<div class="dynamic-title">AAA game SME evidence to LLM-as-Judge response gates</div>')
                ui.html(
                    '<div class="dynamic-copy">'
                    "A localization specialist reviews baseline assistant responses, names the "
                    "AAA game-specific risks, and turns that evidence into a Kiro judge-subagent "
                    "requirements.md plus an LLM-as-Judge gate before customer-facing answers are shown."
                    "</div>"
                )
            with ui.element("aside").classes("dynamic-side-panel"):
                ui.html('<div class="dynamic-side-label">Scenario</div>')
                ui.html('<div class="dynamic-side-value">8</div>')
                ui.html('<div class="dynamic-side-copy">LQA prompts with 7 specialist failure modes.</div>')

        with ui.element("section").classes("metric-strip"):
            for value, label in [
                ("AAA game", "Franchise context"),
                ("LQA", "Specialist role"),
                ("7", "Failure modes"),
                ("2", "Judge artifacts"),
            ]:
                with ui.element("div").classes("metric-tile"):
                    ui.html(f'<div class="metric-tile-value">{value}</div>')
                    ui.html(f'<div class="metric-tile-label">{label}</div>')

        with ui.tabs().classes("aaa-game-demo-tabs") as tabs:
            scenario = ui.tab("Scenario")
            evidence = ui.tab("Evidence")
            baseline = ui.tab("Baseline")
            requirements = ui.tab("Judge Spec")
            judge = ui.tab("Response Gate")

        with ui.tab_panels(tabs, value=scenario).classes("aaa-game-demo-tab-panels"):
            with ui.tab_panel(scenario).classes("aaa-game-demo-panel"):
                _render_scenario_tab()
            with ui.tab_panel(evidence).classes("aaa-game-demo-panel"):
                _render_evidence_tab()
            with ui.tab_panel(baseline).classes("aaa-game-demo-panel"):
                _render_baseline_tab()
            with ui.tab_panel(requirements).classes("aaa-game-demo-panel"):
                _render_requirements_tab()
            with ui.tab_panel(judge).classes("aaa-game-demo-panel"):
                _render_judge_tab()
