"""NiceGUI page for Kiro-ready domain requirements."""

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
    return EARSParser().kiro_requirements_md(document)


@ui.page("/requirements")
def ears_requirements_page() -> None:
    page_layout("Kiro requirements.md", current_path="/requirements")
    storage = app.storage.user
    session = _session_from_storage(storage)

    with ui.column().classes("w-full").style(
        "max-width: 980px; margin: 1rem auto; padding: 0 1rem"
    ):
        ui.label("Kiro requirements.md").style(
            "font-size:1.25rem; font-weight:700; color:var(--text-primary)"
        )
        ui.label(
            "The first GEDD output: a Kiro-ready domain driven spec generated from "
            "error analysis, expert annotations, EARS criteria, and judge gates."
        ).style("font-size:0.82rem; color:var(--text-tertiary)")

        if not session.codes:
            ui.label(
                "No failure codes are available yet. Complete coach and PM "
                "annotation work before generating requirements."
            ).style("margin-top:1rem; color:var(--text-secondary)")
            return

        markdown = _build_requirements_markdown(session, storage.get("codebook", []) or [])
        with ui.row().classes("gap-2").style("margin-top:1rem"):
            ui.button(
                "Download requirements.md",
                icon="download",
                on_click=lambda: ui.download(markdown.encode(), "requirements.md"),
            ).props("color=primary no-caps")
            ui.button(
                "Open LLM Judge",
                icon="gavel",
                on_click=lambda: ui.navigate.to("/judge"),
            ).props("outline no-caps").style(
                "color:var(--accent-bright); border-color:var(--border-subtle)"
            )
        with ui.card().classes("w-full").style("margin-top:1rem; padding:1rem"):
            ui.markdown(markdown)
