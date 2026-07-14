"""Judge page - create a simple judge prompt from analyzed failure modes."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from html import escape
from typing import Any

from nicegui import app, ui

from grounded_evals.ui.layout import page_layout


SEVERITY_RANK = {
    "catastrophic": 4,
    "critical": 3,
    "high": 3,
    "functional": 2,
    "medium": 2,
    "cosmetic": 1,
    "low": 1,
}

SEVERITY_COLOR = {
    "catastrophic": "var(--red)",
    "critical": "var(--red)",
    "high": "var(--red)",
    "functional": "var(--yellow)",
    "medium": "var(--yellow)",
    "cosmetic": "var(--green-bright)",
    "low": "var(--green-bright)",
}

JUDGE_CSS = """
.judge-chain-panel {
  border: 1px solid rgba(94,106,210,0.28);
  border-radius: var(--radius-xl);
  background: linear-gradient(180deg, rgba(94,106,210,0.12), var(--bg-surface-1));
  padding: 16px;
  margin: 14px 0;
}
.judge-chain-title {
  font-size: 0.98rem;
  font-weight: 740;
  color: var(--text-primary);
}
.judge-chain-copy {
  max-width: 780px;
  margin-top: 5px;
  font-size: 0.76rem;
  line-height: 1.5;
  color: var(--text-tertiary);
}
.judge-chain-list {
  display: grid;
  gap: 9px;
  margin-top: 13px;
}
.judge-chain-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(170px, 0.55fr) minmax(0, 1.1fr);
  gap: 10px;
  align-items: stretch;
  padding: 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface-2);
}
.judge-chain-label {
  font-size: 0.58rem;
  font-weight: 750;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.judge-chain-text {
  margin-top: 5px;
  font-size: 0.72rem;
  line-height: 1.42;
  color: var(--text-secondary);
}
.judge-code-chip {
  display: inline-flex;
  width: fit-content;
  max-width: 100%;
  margin-top: 5px;
  padding: 4px 8px;
  border-radius: 6px;
  background: var(--accent-tint);
  color: var(--accent-bright);
  font-size: 0.68rem;
  line-height: 1.25;
  font-weight: 700;
}
.judge-severity-pill {
  display: inline-flex;
  width: fit-content;
  margin-top: 7px;
  padding: 3px 7px;
  border: 1px solid var(--border-subtle);
  border-radius: 99px;
  background: rgba(255,255,255,0.03);
  font-size: 0.58rem;
  font-weight: 760;
  text-transform: uppercase;
  white-space: nowrap;
}
.judge-rule-text {
  margin-top: 5px;
  font-size: 0.74rem;
  line-height: 1.45;
  color: var(--text-primary);
  font-weight: 560;
}
@media (max-width: 900px) {
  .judge-chain-row {
    grid-template-columns: 1fr;
  }
}
"""


def _get(key: str, default: Any = None) -> Any:
    return app.storage.user.get(key, default)


def _set(key: str, value: Any) -> None:
    app.storage.user[key] = value


def _agent_spec() -> dict:
    session = _get("session_data", {})
    if not isinstance(session, dict):
        return {}
    agent = session.get("agent_spec", {})
    return agent if isinstance(agent, dict) else {}


def _codes_for_annotation(annotation: dict) -> list[str]:
    codes = annotation.get("codes", [])
    if isinstance(codes, str):
        codes = [codes]
    elif not isinstance(codes, list):
        codes = []
    error_code = annotation.get("error_code")
    if error_code and error_code not in codes:
        codes.append(error_code)
    return [str(code).strip() for code in codes if str(code).strip()]


def _normalized_severity(value: Any) -> str:
    severity = str(value or "").strip().lower()
    if severity in SEVERITY_RANK:
        return severity
    if severity in {"incorrect", "fail", "failed"}:
        return "critical"
    if severity in {"partial", "warning"}:
        return "functional"
    if severity in {"correct", "pass"}:
        return "low"
    return "functional"


def _highest_severity(values: list[str]) -> str:
    if not values:
        return "functional"
    return max(values, key=lambda item: SEVERITY_RANK.get(item, 2))


def _failure_modes() -> list[dict]:
    """Return failure modes grounded in codebook entries and SME-curated evidence."""
    codebook = _get("codebook", []) or []
    annotations = _get("coding_annotations", []) or []
    freq: Counter[str] = Counter()
    severities: defaultdict[str, list[str]] = defaultdict(list)
    samples: dict[str, dict] = {}

    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue
        for code in _codes_for_annotation(annotation):
            freq[code] += 1
            severities[code].append(_normalized_severity(annotation.get("severity") or annotation.get("annotation")))
            samples.setdefault(code, annotation)

    modes: dict[str, dict] = {}
    for entry in codebook:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        if freq.get(name, 0) <= 0:
            continue
        severity = _normalized_severity(entry.get("severity_label"))
        observed = severities.get(name, [])
        modes[name] = {
            "name": name,
            "definition": entry.get("definition", ""),
            "frequency": freq.get(name, 0),
            "severity": _highest_severity(observed + [severity]),
            "release_gate": entry.get("release_gate", ""),
            "axial_category": entry.get("axial_category", ""),
            "sample": samples.get(name, {}),
        }

    for code, count in freq.items():
        if code not in modes:
            modes[code] = {
                "name": code,
                "definition": "",
                "frequency": count,
                "severity": _highest_severity(severities.get(code, [])),
                "release_gate": "",
                "axial_category": "",
                "sample": samples.get(code, {}),
            }

    pattern_rows = _get("failure_patterns", []) or []
    for pattern in pattern_rows:
        if not isinstance(pattern, dict):
            continue
        name = str(pattern.get("name") or pattern.get("title") or "").strip()
        if name and name not in modes:
            modes[name] = {
                "name": name,
                "definition": pattern.get("description", ""),
                "frequency": int(pattern.get("count", 0) or 0),
                "severity": _normalized_severity(pattern.get("severity")),
                "release_gate": "",
                "axial_category": "",
                "sample": {},
            }

    return sorted(
        modes.values(),
        key=lambda item: (
            SEVERITY_RANK.get(item.get("severity", "functional"), 2),
            item.get("frequency", 0),
            item.get("name", ""),
        ),
        reverse=True,
    )


def _paradigm_lines() -> list[str]:
    paradigm = _get("paradigm_model", {}) or {}
    labels = {
        "phenomenon": "Core problem",
        "causal_conditions": "Triggered by",
        "context": "Occurs when",
        "intervening_conditions": "Gets worse if",
        "strategies": "Manifests as",
        "consequences": "User impact",
    }
    lines: list[str] = []
    for key, label in labels.items():
        values = paradigm.get(key, [])
        if isinstance(values, str):
            values = [values]
        if values:
            lines.append(f"- {label}: {', '.join(str(v) for v in values)}")
    return lines


def _mode_evidence(mode: dict) -> str:
    sample = mode.get("sample") or {}
    memo = sample.get("memo") or sample.get("notes") or ""
    query = sample.get("query") or sample.get("prompt") or ""
    if memo:
        return str(memo)
    if query:
        return f"Observed on query: {query}"
    return ""


def _judge_rule_for_mode(mode: dict) -> str:
    release_gate = str(mode.get("release_gate") or "").strip()
    if release_gate:
        return release_gate

    name = str(mode.get("name") or "this failure mode")
    definition = str(mode.get("definition") or "").strip()
    severity = _normalized_severity(mode.get("severity"))
    prefix = "Hard fail" if SEVERITY_RANK.get(severity, 2) >= 3 else "Fail"
    if definition:
        return f"{prefix} when the response exhibits {name}: {definition}"
    return f"{prefix} when the response matches SME-curated evidence labeled {name}."


def _build_simple_prompt(modes: list[dict]) -> str:
    agent = _agent_spec()
    agent_name = agent.get("name") or "the AI product"
    agent_desc = agent.get("description") or "No product description provided."
    paradigm = _paradigm_lines()

    failure_lines: list[str] = []
    for index, mode in enumerate(modes, start=1):
        definition = mode.get("definition") or "Use the PM/domain-expert annotation memo as the definition."
        severity = mode.get("severity", "functional")
        evidence = _mode_evidence(mode)
        rule = _judge_rule_for_mode(mode)
        line = f"{index}. {mode['name']} ({severity}; seen {mode.get('frequency', 0)}x): {definition}"
        line += f" Judge rule: {rule}"
        if evidence:
            line += f" Evidence: {evidence}"
        failure_lines.append(line)

    if not failure_lines:
        failure_lines = ["1. No failure modes have been analyzed yet. Do not use this judge for release decisions until SME-curated evidence exists."]

    context_block = "\n".join(paradigm) if paradigm else "- No root-cause summary recorded yet."
    failure_block = "\n".join(failure_lines)

    return f"""You are an LLM-as-a-Judge subagent for {agent_name}.

Product context:
{agent_desc}

Your job:
Evaluate a candidate customer-facing assistant response before it is shown to a customer. Use the SME/PM failure modes below as quality gates. Do not use generic helpfulness as the main standard.

Root-cause context from analysis:
{context_block}

Failure modes to detect:
{failure_block}

Evaluation rules:
- PASS only if the response avoids the listed failure modes and answers within the product's source of truth.
- FAIL if the response clearly exhibits any listed failure mode; failed responses must not be customer visible.
- HARD FAIL if the response creates severe user harm, makes an unsupported public commitment, bypasses policy/compliance controls, or normalizes a critical domain error.
- If the evidence is ambiguous, choose NEEDS_REVIEW instead of guessing.

Evaluate this item:
<query>{{query}}</query>
<response>{{response}}</response>

Return only JSON:
{{
  "pass_fail": "pass | fail | needs_review",
  "customer_visible_block": true,
  "failure_code": "failure mode name or none",
  "severity": "low | medium | critical | catastrophic",
  "rationale": "Brief SME/PM-readable reason grounded in the failure modes.",
  "evidence_references": ["annotation, codebook, or query evidence used"],
  "recommended_action": "revise_response | request_human_review | allow"
}}
"""


def _render_inductive_chain(modes: list[dict]) -> None:
    with ui.element("section").classes("judge-chain-panel"):
        ui.html('<div class="judge-chain-title">Inductive path from SME-curated evidence to judge rules</div>')
        ui.html(
            '<div class="judge-chain-copy">'
            "The judge is not a generic helpfulness rubric. It is built from SME/PM open-coded annotations, "
            "then grouped by axial/root-cause context, and converted into pre-customer response-gate rules."
            "</div>"
        )
        with ui.element("div").classes("judge-chain-list"):
            for mode in modes:
                severity = mode.get("severity", "functional")
                color = SEVERITY_COLOR.get(severity, "var(--yellow)")
                evidence = _mode_evidence(mode) or "SME-curated evidence for this code."
                evidence_short = evidence[:220] + ("..." if len(evidence) > 220 else "")
                rule = _judge_rule_for_mode(mode)
                rule_short = rule[:240] + ("..." if len(rule) > 240 else "")
                axial = str(mode.get("axial_category") or "PM-derived failure mode")
                with ui.element("div").classes("judge-chain-row"):
                    with ui.element("div"):
                        ui.html('<div class="judge-chain-label">SME-curated evidence</div>')
                        ui.html(f'<div class="judge-chain-text">{escape(evidence_short)}</div>')
                    with ui.element("div"):
                        ui.html('<div class="judge-chain-label">Error code</div>')
                        ui.html(f'<div class="judge-code-chip">{escape(str(mode["name"]))}</div>')
                        ui.html(
                            f'<div class="judge-chain-text">{escape(axial)}<br>'
                            f'{int(mode.get("frequency", 0) or 0)} observed annotations</div>'
                        )
                        ui.html(
                            f'<div class="judge-severity-pill" style="color:{color}">'
                            f'{escape(str(severity))}</div>'
                        )
                    with ui.element("div"):
                        ui.html('<div class="judge-chain-label">Judge rule created</div>')
                        ui.html(f'<div class="judge-rule-text">{escape(rule_short)}</div>')


@ui.page("/judge")
def judge_builder_page() -> None:
    page_layout("Response Gate", current_path="/judge")
    ui.add_head_html(f"<style>{JUDGE_CSS}</style>")

    modes = _failure_modes()
    annotations = _get("coding_annotations", []) or []
    agent = _agent_spec()
    agent_name = agent.get("name") or "Untitled AI product"

    if not modes:
        with ui.element("main").classes("dynamic-page"):
            with ui.element("div").classes("empty-state-panel"):
                ui.icon("gavel")
                ui.html('<div class="empty-state-title">Create the LLM-as-Judge response gate</div>')
                ui.html(
                    '<div class="empty-state-copy">'
                    "Curate failure evidence first. The judge subagent uses the same SME-derived "
                    "failure modes as the Kiro judge-subagent requirements.md."
                    "</div>"
                )
                with ui.row().classes("justify-center gap-2").style("margin-top:16px"):
                    ui.button("Open Annotations", icon="label", on_click=lambda: ui.navigate.to("/coding")).props(
                        "color=primary no-caps"
                    )
                    ui.button("Coach", icon="auto_awesome", on_click=lambda: ui.navigate.to("/coach")).props(
                        "outline no-caps"
                    ).style("color: var(--accent-bright); border-color: var(--border-subtle)")
        return

    default_prompt = _get("_simple_judge_prompt") or _build_simple_prompt(modes)

    with ui.element("main").classes("dynamic-page"):
        with ui.element("section").classes("dynamic-hero"):
            with ui.element("div"):
                ui.html(
                    '<div class="dynamic-kicker">'
                    '<span class="material-icons" style="font-size:0.95rem">gavel</span>'
                    "LLM-as-Judge gate"
                    "</div>"
                )
                ui.html('<div class="dynamic-title">Pre-customer response gate from annotated failure modes</div>')
                ui.html(
                    '<div class="dynamic-copy">'
                    "Review SME-curated failure modes, generate the LLM-as-Judge subagent gate, "
                    "edit if needed, then save or download it alongside the Kiro judge requirements.md."
                    "</div>"
                )
            with ui.element("aside").classes("dynamic-side-panel"):
                ui.html('<div class="dynamic-side-label">Customer blocks</div>')
                ui.html(
                    '<div class="dynamic-side-value">'
                    f'{sum(1 for mode in modes if SEVERITY_RANK.get(mode.get("severity", "functional"), 2) >= 3)}'
                    "</div>"
                )
                ui.html('<div class="dynamic-side-copy">Critical or catastrophic failures that block customer-visible responses.</div>')

        stats = [
            (str(len(modes)), "Failure modes", "var(--accent-bright)"),
            (str(len(annotations)), "SME evidence items", "var(--yellow)"),
            (
                str(sum(1 for mode in modes if SEVERITY_RANK.get(mode.get("severity", "functional"), 2) >= 3)),
                "Customer blocks",
                "var(--red)",
            ),
        ]
        _stat_row(stats)
        _render_inductive_chain(modes)

        with ui.element("div").style(
            "display:grid; grid-template-columns:minmax(300px,0.9fr) minmax(0,1.1fr); "
            "gap:14px; align-items:start"
        ).classes("judge-simple-grid"):
            with ui.element("div").style(
                "border:1px solid var(--border-subtle); border-radius:var(--radius-xl); "
                "background:var(--bg-surface-1); padding:16px"
            ):
                ui.html('<div style="font-size:0.95rem;font-weight:700;color:var(--text-primary)">Failure modes analyzed</div>')
                ui.html(
                    '<div style="margin-top:4px;font-size:0.76rem;line-height:1.5;color:var(--text-tertiary)">'
                    "These are the observed failures the judge will detect. They come from the codebook and SME-curated evidence."
                    "</div>"
                )

                with ui.column().classes("w-full").style("gap:8px; margin-top:12px"):
                    for mode in modes:
                        severity = mode.get("severity", "functional")
                        color = SEVERITY_COLOR.get(severity, "var(--yellow)")
                        definition = escape(str(mode.get("definition") or "No definition yet. Use PM memos as evidence."))
                        evidence = escape(_mode_evidence(mode))
                        with ui.element("div").style(
                            f"border:1px solid var(--border-subtle); border-left:3px solid {color}; "
                            "border-radius:8px; background:var(--bg-surface-2); padding:10px 12px"
                        ):
                            with ui.row().classes("items-start justify-between gap-2"):
                                ui.html(
                                    f'<div style="font-size:0.82rem;font-weight:700;color:var(--text-primary);line-height:1.35">'
                                    f'{escape(mode["name"])}</div>'
                                )
                                ui.html(
                                    f'<span style="font-size:0.58rem;font-weight:700;color:{color};'
                                    f'background:rgba(255,255,255,0.04);border:1px solid var(--border-subtle);'
                                    f'border-radius:99px;padding:2px 7px;white-space:nowrap">'
                                    f'{severity.upper()} x{mode.get("frequency", 0)}</span>'
                                )
                            ui.html(f'<div style="margin-top:6px;font-size:0.72rem;line-height:1.45;color:var(--text-tertiary)">{definition}</div>')
                            if evidence:
                                ui.html(
                                    f'<div style="margin-top:6px;font-size:0.7rem;line-height:1.4;color:var(--text-secondary)">'
                                    f'Evidence: {evidence}</div>'
                                )

            with ui.element("div").style(
                "border:1px solid var(--border-subtle); border-radius:var(--radius-xl); "
                "background:var(--bg-surface-1); padding:16px"
            ):
                with ui.row().classes("items-center justify-between gap-3 flex-wrap"):
                    with ui.column().style("gap:2px"):
                        ui.html('<div style="font-size:0.95rem;font-weight:700;color:var(--text-primary)">LLM-as-Judge subagent prompt</div>')
                        ui.html(
                            f'<div style="font-size:0.75rem;color:var(--text-tertiary)">Agent: {escape(agent_name)}</div>'
                        )

                prompt_area = ui.textarea(value=default_prompt).props("outlined dark rows=25").classes("w-full").style(
                    "margin-top:12px;font-size:0.76rem;font-family:monospace;"
                    "background:var(--bg-surface-2);color:var(--text-primary)"
                )

                def generate_prompt() -> None:
                    prompt = _build_simple_prompt(_failure_modes())
                    prompt_area.set_value(prompt)
                    _set("_simple_judge_prompt", prompt)
                    _set("_generated_judge_prompt", prompt)
                    _set("_jb_generated_at", datetime.now().isoformat())
                    ui.notify("Simple judge prompt generated", type="positive")

                def save_prompt() -> None:
                    prompt = prompt_area.value or ""
                    _set("_simple_judge_prompt", prompt)
                    _set("_generated_judge_prompt", prompt)
                    _set("_jb_generated_at", datetime.now().isoformat())
                    ui.notify("Judge prompt saved", type="positive")

                def copy_prompt() -> None:
                    ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(prompt_area.value or '')});")
                    ui.notify("Copied to clipboard", type="positive")

                def download_prompt() -> None:
                    prompt = prompt_area.value or ""
                    if not prompt.strip():
                        ui.notify("Generate a judge prompt first", type="warning")
                        return
                    file_agent = str(agent_name).lower().replace(" ", "_") or "agent"
                    ui.download(prompt.encode(), f"{file_agent}_judge_prompt.md")

                with ui.row().classes("gap-2 flex-wrap").style("margin-top:10px"):
                    ui.button("Generate from failure modes", icon="auto_fix_high", on_click=generate_prompt).props(
                        "size=sm"
                    ).style("background:var(--accent);color:white;border-radius:6px;font-weight:600")
                    ui.button("Save", icon="save", on_click=save_prompt).props("size=sm outline dark").style(
                        "border-color:var(--border-default);color:var(--text-secondary)"
                    )
                    ui.button("Copy", icon="content_copy", on_click=copy_prompt).props("size=sm outline dark").style(
                        "border-color:var(--border-default);color:var(--text-secondary)"
                    )
                    ui.button("Download", icon="download", on_click=download_prompt).props("size=sm outline dark").style(
                        "border-color:var(--border-default);color:var(--text-secondary)"
                    )

        ui.add_head_html(
            """
            <style>
            @media (max-width: 900px) {
              .judge-simple-grid { grid-template-columns: 1fr !important; }
            }
            </style>
            """
        )


def _stat_row(stats: list[tuple[str, str, str]]) -> None:
    html = '<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:10px 0 14px">'
    for value, label, color in stats:
        html += (
            f'<div style="background:var(--bg-surface-1);border:1px solid var(--border-subtle);'
            f'border-radius:var(--radius-xl);padding:14px;text-align:center">'
            f'<div style="font-size:1.35rem;font-weight:750;color:{color};font-variant-numeric:tabular-nums">{escape(value)}</div>'
            f'<div style="font-size:0.64rem;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.05em;margin-top:2px">{escape(label)}</div>'
            f'</div>'
        )
    html += '</div>'
    ui.html(html)
