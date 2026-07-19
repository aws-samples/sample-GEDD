"""NiceGUI page for systematic LLM-as-Judge specifications."""

from __future__ import annotations

from collections import Counter
from uuid import NAMESPACE_URL, UUID, uuid5

from nicegui import app, ui

from grounded_evals.ears.parser import EARSParser
from grounded_evals.ears.transformer import CodeMetrics, EARSTransformer
from grounded_evals.guide.session import Session
from grounded_evals.models.core import Code, CodeType
from grounded_evals.ui.layout import page_layout


def _session_from_storage(storage: dict | None = None) -> Session:
    storage = app.storage.user if storage is None else storage
    session = Session.model_validate(storage.get("session_data", {}))
    if not session.codes:
        session.codes = _codes_from_codebook(storage.get("codebook", []) or [])
    _link_annotations_to_prompts(session, storage.get("coding_annotations", []) or [])
    return session


def _codes_from_codebook(codebook: list[dict]) -> list[Code]:
    codes: list[Code] = []
    for entry in codebook:
        label = entry.get("name") or entry.get("label")
        if not label:
            continue
        codes.append(
            Code(
                id=uuid5(NAMESPACE_URL, f"gedd-code:{label}"),
                label=label,
                code_type=CodeType.DESCRIPTIVE,
                definition=entry.get("definition", ""),
                agent_behavior_tested=entry.get("release_gate", ""),
            )
        )
    return codes


def _link_annotations_to_prompts(session: Session, annotations: list[dict]) -> None:
    code_by_label = {code.label: code for code in session.codes}
    for index, annotation in enumerate(annotations):
        if index >= len(session.golden_prompts):
            break
        code_names = annotation.get("codes") or []
        if isinstance(code_names, str):
            code_names = [code_names]
        for code_name in code_names:
            code = code_by_label.get(code_name)
            if code:
                session.golden_prompts[index].code_id = code.id
                break


def _dimension_for(label: str) -> str:
    lower = label.lower()
    if "safety" in lower or "harm" in lower or "unsafe" in lower:
        return "safety"
    if "hallucin" in lower or "fact" in lower or "accuracy" in lower:
        return "accuracy"
    if "incomplete" in lower or "missing" in lower:
        return "completeness"
    return "quality"


def _severity_for(label: str, codebook_by_name: dict[str, dict]) -> int:
    severity = (codebook_by_name.get(label, {}).get("severity_label") or "").lower()
    if severity in {"catastrophic", "critical"}:
        return 5
    if severity in {"high", "major"}:
        return 4
    if severity in {"medium", "moderate"}:
        return 3
    if severity in {"low", "minor"}:
        return 2
    return 3


def _build_requirements_markdown(session: Session, codebook: list[dict] | None = None) -> str:
    codebook_by_name = {
        (entry.get("name") or entry.get("label")): entry
        for entry in codebook or []
        if entry.get("name") or entry.get("label")
    }
    prompt_counts = Counter(prompt.code_id for prompt in session.golden_prompts if prompt.code_id)
    metrics: dict[UUID, CodeMetrics] = {
        code.id: CodeMetrics(
            severity=_severity_for(code.label, codebook_by_name),
            frequency=max(prompt_counts.get(code.id, 0), 1),
            dimension=_dimension_for(code.label),
        )
        for code in session.codes
    }
    document = EARSTransformer().transform(session, metrics, paradigm=None)
    return EARSParser().judge_spec_md(document)


@ui.page("/requirements")
def ears_requirements_page() -> None:
    page_layout("Judge Spec", current_path="/requirements")
    storage = app.storage.user
    session = _session_from_storage(storage)
    codebook = storage.get("codebook", []) or []
    annotations = storage.get("coding_annotations", []) or []
    golden = session.golden_prompts or []

    with ui.element("main").classes("dynamic-page"):
        with ui.element("section").classes("dynamic-hero"):
            with ui.element("div"):
                ui.html(
                    '<div class="dynamic-kicker">'
                    '<span class="material-icons" style="font-size:0.95rem">description</span>'
                    "Judge output"
                    "</div>"
                )
                ui.html('<div class="dynamic-title">Systematic LLM-as-Judge spec from grounded evidence</div>')
                ui.html(
                    '<div class="dynamic-copy">'
                    "GEDD converts annotated baseline failures into evidence-backed user stories "
                    "and EARS acceptance criteria for the LLM-as-Judge gate that checks "
                    "customer-facing responses. Every requirement traces back to SME evidence."
                    "</div>"
                )
            with ui.element("aside").classes("dynamic-side-panel"):
                ui.html('<div class="dynamic-side-label">Requirement source</div>')
                ui.html(f'<div class="dynamic-side-value">{len(session.codes)}</div>')
                ui.html('<div class="dynamic-side-copy">SME-derived failure modes available for judge specification.</div>')

        with ui.element("section").classes("metric-strip"):
            for value, label in [
                (len(golden), "Curated queries"),
                (len(annotations), "Annotated examples"),
                (len(codebook), "Codebook entries"),
                (len(session.codes), "Requirements drivers"),
            ]:
                with ui.element("div").classes("metric-tile"):
                    ui.html(f'<div class="metric-tile-value">{value}</div>')
                    ui.html(f'<div class="metric-tile-label">{label}</div>')

        if not session.codes:
            with ui.element("div").classes("empty-state-panel"):
                ui.icon("description")
                ui.html('<div class="empty-state-title">No requirements evidence yet</div>')
                ui.html(
                    '<div class="empty-state-copy">'
                    "Complete Coach and SME annotations first. The judge spec is generated "
                    "from failure codes, severity, memos, and curated baseline evidence."
                    "</div>"
                )
                ui.button("Open Coach", icon="auto_awesome", on_click=lambda: ui.navigate.to("/coach")).props(
                    "color=primary no-caps"
                ).style("margin-top:16px")
            return

        markdown = _build_requirements_markdown(session, codebook)
        with ui.element("section").classes("dynamic-grid"):
            with ui.element("div").classes("dynamic-panel accent-teal"):
                with ui.row().classes("items-center justify-between gap-3 flex-wrap"):
                    with ui.column().style("gap:2px"):
                        ui.html('<div class="dynamic-panel-title">Generated judge spec</div>')
                        ui.html('<div class="dynamic-panel-copy">Evidence-backed markdown preview for the LLM-as-Judge gate.</div>')
                    ui.button(
                        "Download",
                        icon="download",
                        on_click=lambda: ui.download(markdown.encode(), "judge-spec.md"),
                    ).props("color=primary no-caps")
                with ui.element("div").classes("document-preview").style("margin-top:12px"):
                    ui.markdown(markdown)

            with ui.element("aside").classes("dynamic-panel accent-violet"):
                ui.html('<div class="dynamic-panel-title">Next outputs</div>')
                ui.html(
                    '<div class="dynamic-panel-copy">'
                    "Use the same SME evidence to generate the LLM-as-Judge gate and measure the judge spec."
                    "</div>"
                )
                with ui.column().style("gap:8px; margin-top:12px"):
                    ui.button("Open Response Gate", icon="gavel", on_click=lambda: ui.navigate.to("/judge")).props(
                        "outline no-caps"
                    ).style("color:var(--violet); border-color:rgba(177,140,255,0.35)")
                    ui.button("Measure Improvement", icon="monitoring", on_click=lambda: ui.navigate.to("/improvement")).props(
                        "outline no-caps"
                    ).style("color:var(--blue); border-color:rgba(106,169,255,0.35)")
