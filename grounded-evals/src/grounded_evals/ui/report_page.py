"""Release report page — summary, failure patterns, judge pipeline, calibration, exports."""

import asyncio
import csv
import io
import json
from collections import Counter
from datetime import date

from nicegui import app, ui

from grounded_evals.feedback_loop import compute_eval_health

from grounded_evals.ui.layout import page_layout

REPORT_CSS = """
.rr-hero {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  background: var(--bg-surface-1);
  padding: 18px;
}
.rr-eyebrow {
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}
.rr-title {
  font-size: 1.35rem;
  font-weight: 750;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin-top: 4px;
}
.rr-subtitle {
  font-size: 0.82rem;
  color: var(--text-secondary);
  line-height: 1.55;
  max-width: 680px;
  margin-top: 6px;
}
.rr-decision {
  border-radius: var(--radius-lg);
  padding: 12px 14px;
  min-width: 190px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface-2);
}
.rr-decision-label {
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}
.rr-decision-value {
  font-size: 1.05rem;
  font-weight: 750;
  margin-top: 4px;
}
.rr-metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.rr-metric {
  background: var(--bg-surface-2);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 13px 14px;
}
.rr-metric-value {
  font-size: 1.35rem;
  font-weight: 750;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.rr-metric-label {
  font-size: 0.66rem;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 2px;
}
.rr-action-card {
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius-xl);
  background: var(--bg-surface-2);
  padding: 14px 16px;
}
.rr-action-title {
  font-size: 0.86rem;
  font-weight: 700;
  color: var(--text-primary);
}
.rr-action-copy {
  font-size: 0.78rem;
  color: var(--text-secondary);
  line-height: 1.55;
  margin-top: 3px;
}
.rr-section-title {
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.rr-handoff-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.rr-handoff-stat {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface-1);
  padding: 11px 12px;
}
.rr-handoff-value {
  font-size: 0.95rem;
  font-weight: 750;
  color: var(--text-primary);
}
.rr-handoff-label {
  font-size: 0.62rem;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 3px;
}
.rr-priority-row {
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--red);
  border-radius: var(--radius-lg);
  background: var(--bg-surface-1);
  padding: 12px 14px;
  margin-top: 8px;
}
.rr-runbook {
  background: var(--bg-base);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 11px 12px;
  color: var(--text-secondary);
  font-size: 0.72rem;
  line-height: 1.55;
  white-space: pre-wrap;
  font-family: monospace;
}
@media (max-width: 760px) {
  .rr-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .rr-handoff-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 520px) {
  .rr-metric-grid { grid-template-columns: 1fr; }
  .rr-handoff-grid { grid-template-columns: 1fr; }
}
"""


def _build_failure_patterns(codebook: list[dict], coding_annotations: list[dict]) -> list[dict]:
    """Derive failure_patterns from codebook usage across coding annotations."""
    code_counter: Counter = Counter()
    for ann in coding_annotations:
        for code_name in ann.get("codes", []):
            code_counter[code_name] += 1

    patterns = []
    for code in codebook:
        name = code["name"]
        freq = code_counter.get(name, 0)
        if freq == 0:
            continue
        total = max(1, sum(code_counter.values()))
        pct = freq / total
        severity = "high" if pct >= 0.4 else ("medium" if pct >= 0.2 else "low")
        patterns.append({"name": name, "frequency": freq, "severity": severity, "definition": code.get("definition", "")})

    return sorted(patterns, key=lambda p: p["frequency"], reverse=True)


_RUBRIC_PIE_COLORS = [
    "#5e6ad2",
    "#4ade80",
    "#f0bf00",
    "#eb5757",
    "#6ed6cf",
    "#f28a35",
    "#60a5fa",
    "#f472b6",
]


def _build_rubric_error_mode_mix(
    codebook: list[dict],
    coding_annotations: list[dict],
    limit: int = 6,
) -> dict:
    """Aggregate PM-coded failures into a rubric pie chart payload."""
    counts: Counter = Counter()
    known_names = {
        str(entry.get("name", "")).strip()
        for entry in codebook or []
        if isinstance(entry, dict) and str(entry.get("name", "")).strip()
    }

    for ann in coding_annotations or []:
        if not isinstance(ann, dict):
            continue
        raw_codes = ann.get("codes", [])
        if isinstance(raw_codes, str):
            codes = [raw_codes]
        elif isinstance(raw_codes, list):
            codes = raw_codes[:]
        else:
            codes = []
        error_code = ann.get("error_code")
        if error_code:
            codes.append(error_code)
        for code in codes:
            name = str(code).strip()
            if name and (not known_names or name in known_names):
                counts[name] += 1

    ordered = sorted(
        (
            {"name": name, "value": count}
            for name, count in counts.items()
            if count > 0
        ),
        key=lambda item: (-item["value"], item["name"]),
    )
    if not ordered:
        return {
            "total_instances": 0,
            "distinct_modes": 0,
            "top_mode": "",
            "top_count": 0,
            "slices": [],
        }

    slices = []
    for idx, item in enumerate(ordered[:limit]):
        slices.append({
            "name": item["name"],
            "value": item["value"],
            "itemStyle": {"color": _RUBRIC_PIE_COLORS[idx % len(_RUBRIC_PIE_COLORS)]},
        })
    if len(ordered) > limit:
        slices.append({
            "name": "Other identified modes",
            "value": sum(item["value"] for item in ordered[limit:]),
            "itemStyle": {"color": "#5a5d66"},
        })

    return {
        "total_instances": sum(item["value"] for item in ordered),
        "distinct_modes": len(ordered),
        "top_mode": ordered[0]["name"],
        "top_count": ordered[0]["value"],
        "slices": slices,
    }


_SEVERITY_RANK = {"cosmetic": 1, "functional": 2, "critical": 3, "catastrophic": 4}
_SEVERITY_WEIGHT = {"cosmetic": 1, "functional": 2, "critical": 4, "catastrophic": 8}


def _truncate(text: str, limit: int = 140) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def _build_fix_queue(
    codebook: list[dict],
    coding_annotations: list[dict],
    limit: int = 7,
) -> list[dict]:
    """Build the ML engineer's prioritized implementation queue from PM codes."""
    definitions = {
        c.get("name", ""): c.get("definition", "")
        for c in codebook
        if c.get("name")
    }
    stats: dict[str, dict] = {}
    for ann in coding_annotations:
        severity = ann.get("severity") or "functional"
        severity = severity if severity in _SEVERITY_RANK else "functional"
        for code_name in ann.get("codes", []):
            if not code_name:
                continue
            item = stats.setdefault(
                code_name,
                {
                    "code": code_name,
                    "count": 0,
                    "max_severity": severity,
                    "severity_rank": _SEVERITY_RANK[severity],
                    "definition": definitions.get(code_name, ""),
                    "examples": [],
                },
            )
            item["count"] += 1
            if _SEVERITY_RANK[severity] > item["severity_rank"]:
                item["max_severity"] = severity
                item["severity_rank"] = _SEVERITY_RANK[severity]
            if len(item["examples"]) < 2:
                item["examples"].append({
                    "query": _truncate(ann.get("query", ""), 160),
                    "response": _truncate(ann.get("response", ""), 160),
                    "memo": _truncate(ann.get("memo", ""), 180),
                })

    queue = []
    for item in stats.values():
        severity = item["max_severity"]
        priority = item["count"] * _SEVERITY_WEIGHT.get(severity, 2)
        queue.append({
            "priority": "P0" if severity in {"critical", "catastrophic"} else "P1",
            "code": item["code"],
            "count": item["count"],
            "max_severity": severity,
            "priority_score": priority,
            "definition": item["definition"],
            "engineering_change": (
                f"Patch prompt, retrieval, tool policy, or runtime guardrails so "
                f"{item['code']} is no longer produced on the tagged examples."
            ),
            "definition_of_done": (
                "Add tagged examples to the regression suite, verify the old response fails, "
                "verify the fixed response passes, and rerun judge calibration."
            ),
            "examples": item["examples"],
        })
    return sorted(queue, key=lambda q: (-q["priority_score"], q["code"]))[:limit]


def _build_judge_coverage_queue(
    codebook: list[dict],
    coding_annotations: list[dict],
    limit: int = 7,
) -> list[dict]:
    """Prioritize which failure modes must become explicit judge rules."""
    definitions = {
        c.get("name", ""): c.get("definition", "")
        for c in codebook
        if c.get("name")
    }
    stats: dict[str, dict] = {}
    for ann in coding_annotations:
        severity = ann.get("severity") or "functional"
        severity = severity if severity in _SEVERITY_RANK else "functional"
        for code_name in ann.get("codes", []):
            if not code_name:
                continue
            item = stats.setdefault(
                code_name,
                {
                    "code": code_name,
                    "count": 0,
                    "max_severity": severity,
                    "severity_rank": _SEVERITY_RANK[severity],
                    "definition": definitions.get(code_name, ""),
                    "examples": [],
                },
            )
            item["count"] += 1
            if _SEVERITY_RANK[severity] > item["severity_rank"]:
                item["max_severity"] = severity
                item["severity_rank"] = _SEVERITY_RANK[severity]
            if len(item["examples"]) < 2:
                item["examples"].append({
                    "query": _truncate(ann.get("query", ""), 160),
                    "response": _truncate(ann.get("response", ""), 160),
                    "memo": _truncate(ann.get("memo", ""), 180),
                })

    queue = []
    for item in stats.values():
        severity = item["max_severity"]
        priority = item["count"] * _SEVERITY_WEIGHT.get(severity, 2)
        queue.append({
            "priority": "P0" if severity in {"critical", "catastrophic"} else "P1",
            "code": item["code"],
            "count": item["count"],
            "max_severity": severity,
            "priority_score": priority,
            "definition": item["definition"],
            "engineering_change": (
                f"Encode {item['code']} as an explicit fail condition in the judge, "
                f"return this exact code name when it fires, and calibrate against a clean near-neighbor negative."
            ),
            "definition_of_done": (
                "Judge fails the tagged positive examples for this code, passes the near-neighbor negatives, "
                "returns valid structured output, and shows no false negatives on the tagged critical set."
            ),
            "examples": item["examples"],
        })
    return sorted(queue, key=lambda q: (-q["priority_score"], q["code"]))[:limit]


def _build_engineering_handoff(
    *,
    agent_name: str,
    total: int,
    correct: int,
    partial: int,
    incorrect: int,
    pass_rate_pct: float,
    golden_count: int,
    n_blockers: int,
    codebook: list[dict],
    coding_annotations: list[dict],
    judge_prompt: str,
    health_total: int,
    health_gaps: list[str],
    kappa: float | None,
    reference_examples: int = 0,
) -> dict:
    """Create an actionable handoff contract for the ML engineer building the judge."""
    fix_queue = _build_judge_coverage_queue(codebook, coding_annotations)
    p0_count = sum(1 for item in fix_queue if item["priority"] == "P0")
    pass_examples = max(correct, 0)
    borderline_examples = max(partial, 0)
    fail_examples = sum(1 for ann in coding_annotations if ann.get("codes"))
    code_example_counts: Counter = Counter()
    p0_example_count = 0
    for ann in coding_annotations:
        severity = ann.get("severity") or "functional"
        severity = severity if severity in _SEVERITY_RANK else "functional"
        if ann.get("codes") and severity in {"critical", "catastrophic"}:
            p0_example_count += 1
        for code_name in ann.get("codes", []):
            if code_name:
                code_example_counts[code_name] += 1

    codes_with_two_examples = sum(1 for count in code_example_counts.values() if count >= 2)
    coverage_gaps = [
        code.get("name", "")
        for code in codebook
        if code.get("name") and code_example_counts.get(code["name"], 0) < 2
    ]
    strategy = {
        "primary_mode": "single_answer_pass_fail",
        "secondary_mode": "diagnostic_failure_codes",
        "starter_model": "gpt-5.5",
        "reasoning_policy": "Run structured rubric checks before returning the final verdict.",
        "reference_mode": (
            "Use expected behavior as reference-guided context when scoring."
            if reference_examples
            else "No reference answers available; rely on the PM rubric and tagged examples."
        ),
        "why": (
            "Release gates are more reliable as pass/fail checks than open-ended scoring, "
            "and the judge should be calibrated against human labels before cost optimization."
        ),
    }
    output_contract = {
        "pass": "boolean",
        "triggered_failure_modes": "list[str] using exact codebook names only",
        "max_severity": "cosmetic|functional|critical|catastrophic|null",
        "reasoning_summary": "short justification grounded in the rubric and evidence",
        "needs_human_review": "boolean for borderline or low-confidence cases",
    }
    bias_checks = [
        {
            "risk": "Verbosity bias",
            "mitigation": (
                "Calibrate on short clean pass cases and long wrong answers so the judge does not reward length."
            ),
        },
        {
            "risk": "Borderline ambiguity",
            "mitigation": (
                "Keep partial examples as a separate review set and require needs_human_review when the verdict is unclear."
            ),
        },
        {
            "risk": "Reference leakage",
            "mitigation": (
                "If expected behavior exists, use it as scoring guidance rather than a string-match target."
            ),
        },
    ]

    if not judge_prompt:
        status = "missing_judge"
        status_label = "Missing judge prompt"
    elif not codebook or pass_examples == 0 or fail_examples == 0:
        status = "missing_judge_dataset"
        status_label = "Missing judge calibration set"
    elif kappa is None or health_total < 75:
        status = "needs_calibration"
        status_label = "Needs calibration"
    else:
        status = "shadow_ready"
        status_label = "Ready for shadow eval"

    artifact_status = [
        {"artifact": "session.json handoff", "status": "ready" if golden_count else "missing", "detail": f"{golden_count} golden queries"},
        {"artifact": "golden_dataset.jsonl", "status": "ready" if golden_count or total else "missing", "detail": f"{golden_count} queries, {total} labels"},
        {"artifact": "codebook.json", "status": "ready" if codebook else "missing", "detail": f"{len(codebook)} failure codes"},
        {"artifact": "judge_prompt.txt", "status": "ready" if judge_prompt else "missing", "detail": "generated" if judge_prompt else "generate judge first"},
        {"artifact": "pass_set", "status": "ready" if pass_examples else "missing", "detail": f"{pass_examples} clean pass examples"},
        {"artifact": "fail_set", "status": "ready" if fail_examples else "missing", "detail": f"{fail_examples} coded fail examples"},
        {"artifact": "borderline_set", "status": "ready" if borderline_examples else "needed", "detail": f"{borderline_examples} partial examples"},
        {"artifact": "reference_hints", "status": "ready" if reference_examples else "needed", "detail": f"{reference_examples} expected-behavior references"},
        {"artifact": "calibration", "status": "ready" if kappa is not None else "needed", "detail": f"kappa {kappa:.2f}" if kappa is not None else "target kappa >= 0.80"},
    ]
    ci_gates = [
        {"gate": "Judge-human agreement", "target": "kappa >= 0.80 on labeled calibration set", "current": f"{kappa:.2f}" if kappa is not None else "not measured"},
        {"gate": "False positives on pass set", "target": "<= 5% on clean pass examples", "current": f"not measured across {pass_examples} pass examples"},
        {"gate": "False negatives on P0 fail set", "target": "0 misses on critical/catastrophic tagged examples", "current": f"not measured across {p0_example_count} P0 examples"},
        {"gate": "Output schema validity", "target": "100% valid JSON with exact code names", "current": "not measured"},
    ]
    commands = [
        "grounded-evals validate-session --session session.json",
        "grounded-evals export --session session.json --format jsonl --output golden_dataset.jsonl",
        "grounded-evals judge --session session.json --output judge_prompt.md",
        "grounded-evals mlflow --session session.json --tracking-uri $MLFLOW_TRACKING_URI --run-eval",
    ]
    next_steps = [
        "Export the session handoff and judge-builder JSON from this page.",
        "Start with a strong judge model, keep the task single-answer pass/fail, and only optimize cost after agreement is acceptable.",
        "Build a calibration set that includes clean passes, coded fails, and partial borderline cases.",
        "Instrument false positives, false negatives, and schema-validity before promoting the judge from shadow mode to blocking mode.",
    ]
    if not fix_queue:
        next_steps[2] = "Add coded failure annotations before treating this as a judge-building packet."

    return {
        "agent": agent_name,
        "status": status,
        "status_label": status_label,
        "metrics": {
            "total_annotations": total,
            "correct": correct,
            "partial": partial,
            "incorrect": incorrect,
            "pass_rate_pct": round(pass_rate_pct, 1),
            "golden_queries": golden_count,
            "release_blockers": n_blockers,
            "readiness_score": health_total,
            "kappa": kappa,
        },
        "judge_strategy": strategy,
        "dataset_profile": {
            "pass_examples": pass_examples,
            "borderline_examples": borderline_examples,
            "fail_examples": fail_examples,
            "reference_examples": reference_examples,
            "codes_with_two_examples": codes_with_two_examples,
            "coverage_gaps": coverage_gaps,
            "p0_queue_items": p0_count,
        },
        "output_contract": output_contract,
        "bias_checks": bias_checks,
        "artifact_status": artifact_status,
        "ci_gates": ci_gates,
        "implementation_queue": fix_queue,
        "health_gaps": health_gaps,
        "commands": commands,
        "next_steps": next_steps,
    }


def _build_engineering_clipboard_text(handoff: dict) -> str:
    lines = [
        f"LLM Judge Builder Handoff: {handoff.get('agent', 'agent')}",
        f"Status: {handoff.get('status_label', 'unknown')}",
        "",
        "Judge strategy:",
    ]
    strategy = handoff.get("judge_strategy", {})
    if strategy:
        lines.append(f"- Primary mode: {strategy.get('primary_mode', 'unknown')}")
        lines.append(f"- Secondary mode: {strategy.get('secondary_mode', 'unknown')}")
        lines.append(f"- Starter model: {strategy.get('starter_model', 'unknown')}")
        lines.append(f"- Reference mode: {strategy.get('reference_mode', 'unknown')}")
    profile = handoff.get("dataset_profile", {})
    if profile:
        lines.extend([
            "",
            "Calibration set:",
            f"- Pass examples: {profile.get('pass_examples', 0)}",
            f"- Borderline examples: {profile.get('borderline_examples', 0)}",
            f"- Fail examples: {profile.get('fail_examples', 0)}",
            f"- Reference examples: {profile.get('reference_examples', 0)}",
        ])
    lines.extend(["", "Promotion gates:"])
    for gate in handoff.get("ci_gates", []):
        lines.append(f"- {gate['gate']}: target {gate['target']} (current: {gate['current']})")
    lines.extend(["", "Judge coverage queue:"])
    queue = handoff.get("implementation_queue", [])
    if queue:
        for item in queue[:5]:
            lines.append(
                f"- {item['priority']} {item['code']} "
                f"({item['max_severity']}, {item['count']} examples): "
                f"{item['engineering_change']}"
            )
    else:
        lines.append("- No coded failures yet.")
    output_contract = handoff.get("output_contract", {})
    if output_contract:
        lines.extend(["", "Output contract:"])
        for key, value in output_contract.items():
            lines.append(f"- {key}: {value}")
    lines.extend(["", "Commands:"])
    lines.extend(handoff.get("commands", []))
    return "\n".join(lines)


def _build_judge_builder_handoff_export(
    *,
    agent_name: str,
    agent_description: str,
    handoff: dict,
    judge_prompt: str,
) -> dict:
    """Build the exported judge-builder packet with a stable artifact shape."""
    return {
        "artifact": "judge_builder_handoff",
        "schema_version": "2026-06-13",
        "exported_on": date.today().isoformat(),
        "agent": {
            "name": agent_name,
            "description": agent_description,
        },
        "handoff": {
            "status": handoff.get("status"),
            "status_label": handoff.get("status_label"),
            "metrics": handoff.get("metrics", {}),
            "judge_strategy": handoff.get("judge_strategy", {}),
            "dataset_profile": handoff.get("dataset_profile", {}),
            "output_contract": handoff.get("output_contract", {}),
            "bias_checks": handoff.get("bias_checks", []),
            "artifact_status": handoff.get("artifact_status", []),
            "promotion_gates": handoff.get("ci_gates", []),
            "judge_coverage_queue": handoff.get("implementation_queue", []),
            "health_gaps": handoff.get("health_gaps", []),
            "commands": handoff.get("commands", []),
            "next_steps": handoff.get("next_steps", []),
        },
        "judge_prompt": {
            "available": bool(judge_prompt.strip()),
            "text": judge_prompt,
        },
    }


def _build_html_report(
    agent_name: str,
    date_str: str,
    total: int,
    correct: int,
    partial: int,
    incorrect: int,
    patterns: list[dict],
    codebook: list[dict],
    system_prompt: str,
    judge_prompt: str,
    exec_summary: str,
    annotations: list[dict],
    engineering_handoff: dict | None = None,
) -> str:
    """Build a self-contained HTML report suitable for stakeholder sharing."""
    pass_rate = f"{correct / total * 100:.0f}%" if total else "0%"

    patterns_rows = "".join(
        f"<tr><td>{p['name']}</td>"
        f"<td class='sev-{p['severity']}'>{p['severity'].upper()}</td>"
        f"<td>{p['frequency']}</td>"
        f"<td>{p.get('definition', '')[:120]}</td></tr>"
        for p in patterns
    )
    ann_rows = "".join(
        f"<tr><td>{a.get('query', '')[:70]}</td>"
        f"<td>{a.get('model', '')}</td>"
        f"<td class='v-{a.get('annotation', '')}'>{a.get('annotation', '')}</td>"
        f"<td>{a.get('error_code', '')}</td></tr>"
        for a in annotations[:50]
    )
    codebook_items = "".join(
        f"<li><strong>{c['name']}</strong>: {c.get('definition', '')}</li>"
        for c in codebook
    )
    summary_html = (
        f"<p class='summary'>{exec_summary}</p>" if exec_summary
        else f"<p>{pass_rate} pass rate ({correct}/{total} correct).</p>"
    )
    handoff_html = ""
    if engineering_handoff:
        queue_rows = "".join(
            f"<tr><td>{item['priority']}</td><td>{item['code']}</td>"
            f"<td>{item['max_severity']}</td><td>{item['count']}</td>"
            f"<td>{item['definition_of_done']}</td></tr>"
            for item in engineering_handoff.get("implementation_queue", [])[:7]
        )
        gates_rows = "".join(
            f"<tr><td>{gate['gate']}</td><td>{gate['target']}</td><td>{gate['current']}</td></tr>"
            for gate in engineering_handoff.get("ci_gates", [])
        )
        strategy = engineering_handoff.get("judge_strategy", {})
        strategy_items = "".join(
            f"<li><strong>{label}:</strong> {value}</li>"
            for label, value in [
                ("Primary mode", strategy.get("primary_mode", "")),
                ("Secondary mode", strategy.get("secondary_mode", "")),
                ("Starter model", strategy.get("starter_model", "")),
                ("Reasoning policy", strategy.get("reasoning_policy", "")),
                ("Reference mode", strategy.get("reference_mode", "")),
            ]
            if value
        )
        dataset_profile = engineering_handoff.get("dataset_profile", {})
        dataset_items = "".join(
            f"<li><strong>{label}:</strong> {value}</li>"
            for label, value in [
                ("Pass examples", dataset_profile.get("pass_examples")),
                ("Borderline examples", dataset_profile.get("borderline_examples")),
                ("Fail examples", dataset_profile.get("fail_examples")),
                ("Reference examples", dataset_profile.get("reference_examples")),
                ("Codes with >=2 examples", dataset_profile.get("codes_with_two_examples")),
            ]
            if value is not None
        )
        output_contract = json.dumps(engineering_handoff.get("output_contract", {}), indent=2)
        commands = "\n".join(engineering_handoff.get("commands", []))
        handoff_html = f"""
<h2>LLM Judge Builder Handoff</h2>
<p><strong>Status:</strong> {engineering_handoff.get('status_label', 'Unknown')}</p>
{"<h2>Judge Strategy</h2><ul>" + strategy_items + "</ul>" if strategy_items else ""}
{"<h2>Calibration Set</h2><ul>" + dataset_items + "</ul>" if dataset_items else ""}
{"<h2>Output Contract</h2><pre>" + output_contract + "</pre>" if output_contract and output_contract != "{}" else ""}
{"<table><thead><tr><th>Gate</th><th>Target</th><th>Current</th></tr></thead><tbody>" + gates_rows + "</tbody></table>" if gates_rows else ""}
<h2>Judge Coverage Queue</h2>
{"<table><thead><tr><th>Priority</th><th>Failure</th><th>Severity</th><th>Examples</th><th>Definition of Done</th></tr></thead><tbody>" + queue_rows + "</tbody></table>" if queue_rows else "<p>No coded failure queue yet.</p>"}
<h2>Runbook</h2>
<pre>{commands}</pre>
"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>GEDD Release Readiness Report — {agent_name}</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:960px;margin:0 auto;padding:2rem;color:#1a1a1a;line-height:1.6}}
  h1{{font-size:1.6rem;font-weight:700;border-bottom:2px solid #e2e8f0;padding-bottom:.5rem}}
  h2{{font-size:.75rem;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:.04em;margin-top:2rem}}
  .meta{{color:#64748b;font-size:.85rem;margin-bottom:1.5rem}}
  .stats{{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}}
  .stat{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:1rem 1.5rem;text-align:center;flex:1;min-width:100px}}
  .sv{{font-size:1.8rem;font-weight:700}}.sl{{font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;color:#64748b}}
  .correct{{color:#16a34a}}.partial{{color:#d97706}}.incorrect{{color:#dc2626}}
  .summary{{background:#f0f9ff;border-left:4px solid #0ea5e9;padding:1rem 1.25rem;border-radius:0 8px 8px 0;font-size:.95rem;color:#0c4a6e}}
  table{{width:100%;border-collapse:collapse;margin:1rem 0;font-size:.85rem}}
  th{{background:#f1f5f9;text-align:left;padding:8px 12px;color:#475569;font-weight:600;font-size:.75rem;text-transform:uppercase}}
  td{{padding:8px 12px;border-bottom:1px solid #e2e8f0;vertical-align:top}}
  tr:hover td{{background:#f8fafc}}
  .v-correct{{color:#16a34a;font-weight:600}}.v-partial{{color:#d97706;font-weight:600}}.v-incorrect{{color:#dc2626;font-weight:600}}
  .sev-high{{color:#dc2626;font-weight:600}}.sev-medium{{color:#d97706;font-weight:600}}.sev-low{{color:#16a34a;font-weight:600}}
  pre{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:1rem;font-size:.78rem;white-space:pre-wrap;word-break:break-word;max-height:400px;overflow-y:auto}}
  ul{{padding-left:1.5rem}}li{{margin-bottom:.3rem}}
  .footer{{margin-top:3rem;padding-top:1rem;border-top:1px solid #e2e8f0;font-size:.75rem;color:#94a3b8;text-align:center}}
</style>
</head>
<body>
<h1>Release Readiness Report — {agent_name}</h1>
<p class="meta">Generated {date_str} &nbsp;·&nbsp; {total} total annotations</p>
<h2>Readiness Snapshot</h2>
<div class="stats">
  <div class="stat"><div class="sv">{total}</div><div class="sl">Total</div></div>
  <div class="stat"><div class="sv correct">{correct}</div><div class="sl">Correct</div></div>
  <div class="stat"><div class="sv partial">{partial}</div><div class="sl">Partial</div></div>
  <div class="stat"><div class="sv incorrect">{incorrect}</div><div class="sl">Incorrect</div></div>
  <div class="stat"><div class="sv">{pass_rate}</div><div class="sl">Pass Rate</div></div>
</div>
<h2>Executive Summary</h2>
{summary_html}
{handoff_html}
<h2>Release-Blocking Failure Patterns</h2>
{"<table><thead><tr><th>Pattern</th><th>Severity</th><th>Freq</th><th>Definition</th></tr></thead><tbody>" + patterns_rows + "</tbody></table>" if patterns else "<p>No failure patterns recorded yet.</p>"}
<h2>Error Codebook</h2>
{"<ul>" + codebook_items + "</ul>" if codebook else "<p>No error codes defined yet.</p>"}
<h2>Sample Annotations (first 50)</h2>
{"<table><thead><tr><th>Query</th><th>Model</th><th>Verdict</th><th>Error Code</th></tr></thead><tbody>" + ann_rows + "</tbody></table>" if annotations else "<p>No annotations yet.</p>"}
<h2>System Prompt</h2>
{"<pre>" + system_prompt[:3000] + "</pre>" if system_prompt else "<p>Not available.</p>"}
<h2>Judge Prompt</h2>
{"<pre>" + judge_prompt[:3000] + "</pre>" if judge_prompt else "<p>Not generated yet.</p>"}
<div class="footer">Generated by GEDD (Grounded Eval-Driven Development)</div>
</body>
</html>"""


@ui.page("/report")
def report_page():
    page_layout("Release Report", current_path="/report")
    ui.add_head_html(f"<style>{REPORT_CSS}</style>")
    storage = app.storage.user

    if not storage.get("_generated_judge_prompt"):
        with ui.column().classes("w-full items-center justify-center").style("min-height: 60vh"):
            with ui.element("div").style(
                "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                "border-radius: var(--radius-xl); padding: 3rem; text-align: center; max-width: 420px"
            ):
                ui.icon("assessment").style("font-size: 3rem; color: var(--accent-bright); margin-bottom: 1rem")
                ui.label("Release Report").style("font-size: 1.1rem; font-weight: 700; color: var(--text-primary)")
                ui.label("Review release readiness and export evidence. Build a judge first to generate the report.").style(
                    "font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.5rem; line-height: 1.5"
                )
                ui.button("Build a judge first", icon="gavel",
                          on_click=lambda: ui.navigate.to("/judge")).style(
                    "margin-top: 1.5rem; background: var(--accent); color: white; border-radius: 6px"
                )
        return

    session = storage.get("session_data", {})
    annotations = storage.get("annotations", [])
    codebook = storage.get("codebook", [])
    coding_annotations = storage.get("coding_annotations", [])
    paradigm = storage.get("paradigm_model", {})

    # Derive failure_patterns from actual coding data and persist
    patterns = _build_failure_patterns(codebook, coding_annotations)
    storage["failure_patterns"] = patterns

    agent_spec = session.get("agent_spec", {}) if isinstance(session, dict) else {}
    agent_name = agent_spec.get("name", "Unknown Agent") if isinstance(agent_spec, dict) else "Unknown Agent"
    agent_description = agent_spec.get("description", "") if isinstance(agent_spec, dict) else ""
    system_prompt = agent_spec.get("system_prompt", "") if isinstance(agent_spec, dict) else ""
    golden_prompts = session.get("golden_prompts", []) if isinstance(session, dict) else []
    reference_examples = sum(
        1
        for prompt in golden_prompts
        if isinstance(prompt, dict) and str(prompt.get("expected_behavior", "")).strip()
    )

    total = len(annotations)
    correct = sum(1 for a in annotations if a.get("annotation") == "correct")
    partial = sum(1 for a in annotations if a.get("annotation") == "partial")
    incorrect = sum(1 for a in annotations if a.get("annotation") == "incorrect")

    # Error code tallies from eval annotations
    error_counts: dict[str, int] = {}
    for a in annotations:
        code = a.get("error_code", "")
        if code:
            error_counts[code] = error_counts.get(code, 0) + 1

    pass_rate_pct = (correct / total * 100) if total else 0
    blocking_annotations = [
        ann for ann in coding_annotations
        if ann.get("severity") in ("critical", "catastrophic")
    ]
    n_blockers = len(blocking_annotations)
    n_codes = len(codebook)
    top_pattern = patterns[0]["name"] if patterns else "No dominant pattern yet"
    _health = compute_eval_health(dict(app.storage.user))
    _total_color = (
        "#4ade80" if _health.total >= 75
        else ("#f0bf00" if _health.total >= 40 else "#eb5757")
    )
    if n_blockers:
        decision_label = "Do not ship"
        decision_color = "var(--red)"
        next_action = (
            f"Resolve {n_blockers} critical/catastrophic annotation"
            f"{'s' if n_blockers != 1 else ''} before release."
        )
    elif _health.total < 40 or not total:
        decision_label = "Not ready"
        decision_color = "var(--red)"
        next_action = "Add enough annotated evidence to support a defensible launch decision."
    elif _health.total < 75 or pass_rate_pct < 80:
        decision_label = "Fix before GA"
        decision_color = "var(--yellow)"
        next_action = "Use the top failure patterns below to prioritize fixes, then re-run the judge."
    else:
        decision_label = "Pilot ready"
        decision_color = "var(--green-bright)"
        next_action = "Proceed with gated rollout and keep these judge criteria in CI."

    engineering_handoff = _build_engineering_handoff(
        agent_name=agent_name,
        total=total,
        correct=correct,
        partial=partial,
        incorrect=incorrect,
        pass_rate_pct=pass_rate_pct,
        golden_count=len(golden_prompts),
        n_blockers=n_blockers,
        codebook=codebook,
        coding_annotations=coding_annotations,
        judge_prompt=storage.get("_generated_judge_prompt", ""),
        health_total=_health.total,
        health_gaps=_health.gaps,
        kappa=_health.kappa,
        reference_examples=reference_examples,
    )
    engineering_clipboard = _build_engineering_clipboard_text(engineering_handoff)
    judge_builder_packet = _build_judge_builder_handoff_export(
        agent_name=agent_name,
        agent_description=agent_description,
        handoff=engineering_handoff,
        judge_prompt=storage.get("_generated_judge_prompt", ""),
    )

    def download_judge_builder_packet():
        ui.download(
            json.dumps(judge_builder_packet, indent=2).encode(),
            "judge_builder_handoff.json",
        )

    def copy_engineering_plan():
        ui.run_javascript(
            f"navigator.clipboard.writeText({json.dumps(engineering_clipboard)})"
        )
        ui.notify("Judge builder packet copied", type="positive")

    def download_html_report():
        html = _build_html_report(
            agent_name=agent_name,
            date_str=date.today().isoformat(),
            total=total,
            correct=correct,
            partial=partial,
            incorrect=incorrect,
            patterns=patterns,
            codebook=codebook,
            system_prompt=system_prompt,
            judge_prompt=storage.get("_generated_judge_prompt", ""),
            exec_summary=storage.get("_exec_summary", ""),
            annotations=annotations,
            engineering_handoff=engineering_handoff,
        )
        safe_name = agent_name.replace(" ", "_").replace("/", "-")
        ui.download(html.encode(), f"release_readiness_report_{safe_name}.html")

    def download_golden_dataset():
        lines = []
        for p in golden_prompts:
            if isinstance(p, dict):
                lines.append(json.dumps({
                    "prompt": p.get("prompt_text", ""),
                    "system_prompt": system_prompt,
                    "category": p.get("rationale", ""),
                    "expected_behavior": p.get("expected_behavior", ""),
                }))
        for a in annotations:
            lines.append(json.dumps({
                "prompt": a.get("query", ""),
                "response": a.get("response", ""),
                "annotation": a.get("annotation", ""),
                "model": a.get("model", ""),
                "error_code": a.get("error_code", ""),
            }))
        if not lines:
            ui.notify("No data to export yet", type="warning")
            return
        ui.download("\n".join(lines).encode(), "golden_dataset.jsonl")

    def download_codebook():
        ui.download(json.dumps(codebook, indent=2).encode(), "codebook.json")

    def copy_judge_prompt():
        prompt = storage.get("_generated_judge_prompt", "")
        if not prompt.strip():
            ui.notify("Generate a judge first", type="warning")
            return
        ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(prompt)})")
        ui.notify("Judge prompt copied", type="positive")

    def download_judge_prompt():
        prompt = storage.get("_generated_judge_prompt", "")
        if not prompt.strip():
            ui.notify("Generate a judge first", type="warning")
            return
        ui.download(prompt.encode(), "judge_prompt.txt")

    def download_error_analysis_md():
        from grounded_evals.guide.markdown_export import export_error_analysis_md

        md = export_error_analysis_md(storage)
        safe_name = agent_name.replace(" ", "_").replace("/", "-").lower()
        ui.download(md.encode(), f"{safe_name}_error_analysis.md")

    recent_memos = storage.get("memos", [])
    judge_prompt_text = storage.get("_generated_judge_prompt", "")
    handoff_status_color = (
        "var(--red)" if engineering_handoff["status"] in {"missing_judge", "missing_judge_dataset"}
        else ("var(--yellow)" if engineering_handoff["status"] == "needs_calibration" else "var(--green-bright)")
    )
    artifact_ready_count = sum(
        1 for artifact in engineering_handoff["artifact_status"]
        if artifact["status"] == "ready"
    )
    verdict_summary = [
        ("Correct", correct, "var(--green-bright)"),
        ("Partial", partial, "var(--yellow)"),
        ("Incorrect", incorrect, "var(--red)"),
    ]
    severity_colors = {"high": "var(--red)", "medium": "var(--yellow)", "low": "var(--green-bright)"}
    rubric_mix = _build_rubric_error_mode_mix(codebook, coding_annotations)

    with ui.column().classes("w-full max-w-5xl mx-auto").style("padding: 1.5rem; gap: 16px"):

        with ui.element("div").classes("rr-hero"):
            with ui.row().classes("items-start justify-between gap-4 flex-wrap"):
                with ui.column().style("gap: 0; flex: 1; min-width: 260px"):
                    ui.html('<div class="rr-eyebrow">AI PM Release Readiness</div>')
                    ui.html(f'<div class="rr-title">{agent_name}</div>')
                    ui.html(
                        '<div class="rr-subtitle">'
                        'Decision, main failure modes, and the judge-builder handoff needed to turn PM evidence into an LLM-as-a-judge.'
                        '</div>'
                    )
                with ui.element("div").classes("rr-decision").style(
                    f"border-left:3px solid {decision_color}"
                ):
                    ui.html('<div class="rr-decision-label">Decision</div>')
                    ui.html(
                        f'<div class="rr-decision-value" style="color:{decision_color}">{decision_label}</div>'
                    )
                    ui.label(date.today().isoformat()).style(
                        "font-size:0.68rem; color:var(--text-muted); margin-top:4px"
                    )

            with ui.element("div").classes("rr-metric-grid").style("margin-top: 16px"):
                for value, label, color in [
                    (f"{_health.total}/100", "Readiness score", _total_color),
                    (f"{pass_rate_pct:.0f}%", "Pass rate", "var(--green-bright)" if pass_rate_pct >= 80 else "var(--yellow)"),
                    (str(n_blockers), "Release blockers", "var(--red)" if n_blockers else "var(--green-bright)"),
                    (str(n_codes), "Expert failure codes", "var(--accent-bright)"),
                ]:
                    with ui.element("div").classes("rr-metric"):
                        ui.html(f'<div class="rr-metric-value" style="color:{color}">{value}</div>')
                        ui.html(f'<div class="rr-metric-label">{label}</div>')

            with ui.element("div").classes("rr-action-card").style("margin-top: 14px"):
                with ui.row().classes("items-center justify-between gap-3 flex-wrap"):
                    with ui.column().style("gap:0; flex:1; min-width:260px"):
                        ui.html('<div class="rr-action-title">Next release action</div>')
                        ui.html(
                            f'<div class="rr-action-copy">{next_action} '
                            f'Top observed pattern: <strong>{top_pattern}</strong>.</div>'
                        )
                    with ui.row().classes("gap-2 flex-wrap"):
                        ui.button(
                            "Export HTML", icon="download", on_click=download_html_report
                        ).props("size=sm color=primary no-caps")
                        ui.button(
                            "Open judge", icon="gavel", on_click=lambda: ui.navigate.to("/judge")
                        ).props("size=sm outline no-caps").style("color:var(--accent-bright); border-color:var(--accent)")

        with ui.element("div").classes("page-card"):
            with ui.row().classes("items-start justify-between gap-3 flex-wrap").style("margin-bottom: 10px"):
                with ui.column().style("gap: 2px; flex: 1; min-width: 260px"):
                    ui.label("Observed Failure Modes").classes("rr-section-title")
                    ui.label(
                        "The main patterns the expert found. This is the shortest useful view of what is going wrong."
                    ).style("font-size: 0.78rem; color: var(--text-muted); line-height: 1.5")
                with ui.row().classes("gap-2 flex-wrap"):
                    for label, count, color in verdict_summary:
                        ui.html(
                            f'<span style="font-size:0.68rem;padding:4px 10px;border-radius:999px;'
                            f'background:rgba(255,255,255,0.04);border:1px solid var(--border-subtle);'
                            f'color:{color};font-weight:650">{label}: {count}</span>'
                        )

            if patterns:
                for pattern in patterns[:5]:
                    sev_color = severity_colors.get(pattern["severity"], "var(--text-tertiary)")
                    with ui.element("div").style(
                        "background:var(--bg-surface-1); border:1px solid var(--border-subtle); "
                        "border-radius:10px; padding:10px 12px; margin-bottom:8px"
                    ):
                        with ui.row().classes("items-center justify-between gap-2 flex-wrap"):
                            with ui.row().classes("items-center gap-2 flex-wrap"):
                                ui.html(
                                    f'<span style="font-size:0.62rem;font-weight:800;color:{sev_color};'
                                    f'background:rgba(0,0,0,0.18);border:1px solid {sev_color};'
                                    f'border-radius:4px;padding:2px 7px">{pattern["severity"].upper()}</span>'
                                )
                                ui.label(pattern["name"]).style(
                                    "font-size:0.84rem; font-weight:700; color:var(--text-primary)"
                                )
                            ui.label(f'{pattern["frequency"]} tagged').style(
                                "font-size:0.7rem; color:var(--text-tertiary)"
                            )
                        if pattern.get("definition"):
                            ui.label(pattern["definition"]).style(
                                "font-size:0.74rem; color:var(--text-secondary); line-height:1.45; margin-top:4px"
                            )
            else:
                ui.label("No coded failure patterns yet.").style(
                    "font-size: 0.78rem; color: var(--text-muted)"
                )

            if recent_memos:
                with ui.expansion("Recent expert memos", icon="notes").classes("w-full").style("margin-top: 8px"):
                    for memo in reversed(recent_memos[-3:]):
                        with ui.element("div").style(
                            "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                            "border-radius: 8px; padding: 10px 12px; margin-bottom: 8px"
                        ):
                            if memo.get("codes"):
                                ui.label(", ".join(memo.get("codes", [])[:3])).style(
                                    "font-size:0.66rem; color:var(--accent-bright); margin-bottom:4px"
                                )
                            ui.label(memo.get("text", "")).style(
                                "font-size:0.76rem; color:var(--text-secondary); line-height:1.5"
                            )

        if rubric_mix["slices"]:
            with ui.element("div").classes("page-card").style(
                "border:1px solid rgba(94,106,210,0.34); "
                "background:linear-gradient(180deg, rgba(94,106,210,0.10), var(--bg-surface-1))"
            ):
                with ui.row().classes("items-start justify-between gap-4 flex-wrap"):
                    with ui.column().style("gap: 2px; flex: 1; min-width: 240px"):
                        ui.label("Rubric Error-Mode Pie").classes("rr-section-title")
                        ui.label(
                            "This is the visual summary of what the judge rubric is mainly enforcing."
                        ).style("font-size: 0.78rem; color: var(--text-muted); line-height: 1.5")
                        ui.label(
                            f"{rubric_mix['distinct_modes']} identified modes across "
                            f"{rubric_mix['total_instances']} tagged failures."
                        ).style("font-size:0.76rem; color:var(--text-secondary); margin-top:4px")
                        ui.label(
                            f"Most common: {rubric_mix['top_mode']} ({rubric_mix['top_count']} examples)"
                        ).style("font-size:0.74rem; color:var(--accent-bright); margin-top:2px")

                    ui.html(
                        '<span style="font-size:0.68rem;padding:4px 10px;border-radius:999px;'
                        'background:rgba(94,106,210,0.14);border:1px solid rgba(94,106,210,0.28);'
                        'color:var(--accent-bright);font-weight:650">Highlighted judge coverage</span>'
                    )

                ui.echart({
                    "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
                    "legend": {
                        "orient": "vertical",
                        "right": "1%",
                        "top": "center",
                        "textStyle": {"color": "#b4b8c0", "fontSize": 11},
                        "icon": "circle",
                        "itemWidth": 8,
                        "itemHeight": 8,
                        ":formatter": "function(name){return name.length > 24 ? name.slice(0, 24) + '...' : name;}",
                    },
                    "series": [{
                        "type": "pie",
                        "radius": ["43%", "70%"],
                        "center": ["34%", "54%"],
                        "data": rubric_mix["slices"],
                        "label": {"show": False},
                        "labelLine": {"show": False},
                        "emphasis": {"itemStyle": {"shadowBlur": 12}},
                    }],
                    "backgroundColor": "transparent",
                }).style("height:250px; width:100%; margin-top: 8px")

        with ui.element("div").classes("page-card").style("border-left:3px solid var(--accent)"):
            judge_strategy = engineering_handoff["judge_strategy"]
            dataset_profile = engineering_handoff["dataset_profile"]

            with ui.row().classes("items-start justify-between gap-3 flex-wrap").style("margin-bottom: 10px"):
                with ui.column().style("gap: 2px; flex: 1; min-width: 260px"):
                    ui.label("LLM Judge Builder Handoff").classes("rr-section-title")
                    ui.label(
                        "This packet is for the engineer building and calibrating the judge, not patching the runtime."
                    ).style("font-size: 0.78rem; color: var(--text-muted); line-height: 1.5")
                with ui.row().classes("gap-2 flex-wrap"):
                    ui.button(
                        "Copy plan", icon="content_copy", on_click=copy_engineering_plan
                    ).props("size=sm outline no-caps").style("color:var(--accent-bright); border-color:var(--accent)")
                    ui.button(
                        "Download Packet", icon="download", on_click=download_judge_builder_packet
                    ).props("size=sm color=primary no-caps")

            with ui.element("div").classes("rr-handoff-grid"):
                for value, label, color in [
                    (engineering_handoff["status_label"], "Judge build status", handoff_status_color),
                    (judge_strategy["primary_mode"].replace("_", " "), "Primary judge", "var(--accent-bright)"),
                    (f"{artifact_ready_count}/{len(engineering_handoff['artifact_status'])}", "Artifacts ready", "var(--green-bright)"),
                    (f"{_health.kappa:.2f}" if _health.kappa is not None else "Not measured", "Judge agreement", "var(--yellow)" if _health.kappa is None else "var(--green-bright)"),
                ]:
                    with ui.element("div").classes("rr-handoff-stat"):
                        ui.html(f'<div class="rr-handoff-value" style="color:{color}">{value}</div>')
                        ui.html(f'<div class="rr-handoff-label">{label}</div>')

            with ui.row().classes("gap-2 flex-wrap").style("margin-top: 14px"):
                for text, color in [
                    (f"Start model: {judge_strategy['starter_model']}", "var(--accent-bright)"),
                    ("Use pass/fail as the gate", "var(--green-bright)"),
                    (f"Reference hints: {dataset_profile['reference_examples']}", "var(--text-secondary)"),
                    (f"P0 codes: {dataset_profile['p0_queue_items']}", "var(--red)" if dataset_profile["p0_queue_items"] else "var(--text-secondary)"),
                ]:
                    ui.html(
                        f'<span style="font-size:0.68rem;padding:4px 10px;border-radius:999px;'
                        f'background:rgba(255,255,255,0.04);border:1px solid var(--border-subtle);'
                        f'color:{color};font-weight:650">{text}</span>'
                    )

            ui.label("Judge strategy").style(
                "font-size: 0.68rem; font-weight: 700; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.05em; margin-top: 16px"
            )
            ui.label(judge_strategy["why"]).style(
                "font-size: 0.75rem; color: var(--text-secondary); line-height: 1.5"
            )
            ui.label(judge_strategy["reference_mode"]).style(
                "font-size: 0.72rem; color: var(--accent-bright); line-height: 1.45; margin-top: 4px"
            )

            ui.label("Calibration set").style(
                "font-size: 0.68rem; font-weight: 700; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.05em; margin-top: 16px"
            )
            with ui.element("div").classes("rr-handoff-grid"):
                for value, label, color in [
                    (str(dataset_profile["pass_examples"]), "Clean pass examples", "var(--green-bright)"),
                    (str(dataset_profile["borderline_examples"]), "Borderline examples", "var(--yellow)"),
                    (str(dataset_profile["fail_examples"]), "Coded fail examples", "var(--red)"),
                    (str(dataset_profile["codes_with_two_examples"]), "Codes with >=2 examples", "var(--accent-bright)"),
                ]:
                    with ui.element("div").classes("rr-handoff-stat"):
                        ui.html(f'<div class="rr-handoff-value" style="color:{color}">{value}</div>')
                        ui.html(f'<div class="rr-handoff-label">{label}</div>')

            ui.label("Judge output contract").style(
                "font-size: 0.68rem; font-weight: 700; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.05em; margin-top: 16px"
            )
            ui.html(
                '<pre class="rr-runbook">'
                + json.dumps(engineering_handoff["output_contract"], indent=2)
                + "</pre>"
            )

            if engineering_handoff["implementation_queue"]:
                ui.label("Judge coverage queue").style(
                    "font-size: 0.68rem; font-weight: 700; color: var(--text-tertiary); "
                    "text-transform: uppercase; letter-spacing: 0.05em; margin-top: 16px"
                )
                for item in engineering_handoff["implementation_queue"][:4]:
                    row_color = "var(--red)" if item["priority"] == "P0" else "var(--yellow)"
                    with ui.element("div").classes("rr-priority-row").style(f"border-left-color:{row_color}"):
                        with ui.row().classes("items-center justify-between gap-2 flex-wrap"):
                            with ui.row().classes("items-center gap-2 flex-wrap"):
                                ui.html(
                                    f'<span style="font-size:0.62rem;font-weight:800;color:{row_color};'
                                    f'background:rgba(0,0,0,0.18);border:1px solid {row_color};'
                                    f'border-radius:4px;padding:2px 7px">{item["priority"]}</span>'
                                )
                                ui.label(item["code"]).style(
                                    "font-size:0.84rem; font-weight:700; color:var(--text-primary)"
                                )
                            ui.label(
                                f'{item["max_severity"]} · {item["count"]} tagged'
                            ).style("font-size:0.7rem; color:var(--text-tertiary)")
                        if item.get("definition"):
                            ui.label(item["definition"]).style(
                                "font-size:0.74rem; color:var(--text-secondary); line-height:1.45; margin-top:4px"
                            )
                        ui.label(item["engineering_change"]).style(
                            "font-size:0.75rem; color:var(--text-secondary); line-height:1.5; margin-top:4px"
                        )
                        if item["examples"]:
                            ui.label(f'Example: {item["examples"][0].get("query", "")}').style(
                                "font-size:0.7rem; color:var(--text-muted); margin-top:4px"
                            )

            ui.label("Bias checks").style(
                "font-size: 0.68rem; font-weight: 700; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.05em; margin-top: 16px"
            )
            for check in engineering_handoff["bias_checks"]:
                with ui.element("div").style(
                    "background:var(--bg-surface-1); border:1px solid var(--border-subtle); "
                    "border-radius:8px; padding:10px 12px; margin-top:8px"
                ):
                    ui.label(check["risk"]).style("font-size:0.76rem; font-weight:650; color:var(--text-primary)")
                    ui.label(check["mitigation"]).style(
                        "font-size:0.73rem; color:var(--text-secondary); line-height:1.45; margin-top:3px"
                    )

            if dataset_profile["coverage_gaps"] or _health.gaps:
                ui.label("Watchouts").style(
                    "font-size: 0.68rem; font-weight: 700; color: var(--text-tertiary); "
                    "text-transform: uppercase; letter-spacing: 0.05em; margin-top: 16px"
                )
                for gap in dataset_profile["coverage_gaps"][:3]:
                    ui.label(f"• Add one more tagged example for {gap}.").style(
                        "font-size:0.74rem; color:var(--yellow); line-height:1.5"
                    )
                for gap in _health.gaps[:2]:
                    ui.label(f"• {gap}").style(
                        "font-size:0.74rem; color:var(--yellow); line-height:1.5"
                    )

            with ui.expansion("Show judge promotion gates", icon="rule").classes("w-full").style("margin-top: 10px"):
                for gate in engineering_handoff["ci_gates"]:
                    with ui.row().classes("items-baseline gap-2 flex-wrap").style(
                        "padding: 6px 0; border-bottom: 1px solid var(--border-subtle)"
                    ):
                        ui.label(gate["gate"]).style(
                            "font-size: 0.76rem; font-weight: 650; color: var(--text-primary); min-width: 170px"
                        )
                        ui.label(f"Target: {gate['target']}").style(
                            "font-size: 0.72rem; color: var(--text-secondary); flex: 1; min-width: 220px"
                        )
                        ui.label(f"Current: {gate['current']}").style(
                            "font-size: 0.7rem; color: var(--text-tertiary)"
                        )

            with ui.expansion("Show runbook commands", icon="terminal").classes("w-full").style("margin-top: 8px"):
                ui.html(
                    '<pre class="rr-runbook">'
                    + "\n".join(engineering_handoff["commands"])
                    + "</pre>"
                )

        with ui.element("div").classes("page-card"):
            with ui.row().classes("items-start justify-between gap-3 flex-wrap").style("margin-bottom: 10px"):
                with ui.column().style("gap: 2px; flex: 1; min-width: 260px"):
                    ui.label("Judge Prompt").classes("rr-section-title")
                    ui.label(
                        "The current release gate prompt grounded in your PM annotations and codebook."
                    ).style("font-size: 0.78rem; color: var(--text-muted); line-height: 1.5")
                with ui.row().classes("gap-2 flex-wrap"):
                    ui.button(
                        "Copy prompt", icon="content_copy", on_click=copy_judge_prompt
                    ).props("size=sm outline no-caps").style("color:var(--accent-bright); border-color:var(--accent)")
                    ui.button(
                        "Download prompt", icon="download", on_click=download_judge_prompt
                    ).props("size=sm color=primary no-caps")

            with ui.row().classes("gap-2 flex-wrap").style("margin-bottom: 10px"):
                for text, color in [
                    (f"{len(codebook)} failure codes", "var(--accent-bright)"),
                    (f"{len(coding_annotations)} coded examples", "var(--text-secondary)"),
                    ("Prompt ready", "var(--green-bright)"),
                ]:
                    ui.html(
                        f'<span style="font-size:0.68rem;padding:4px 10px;border-radius:999px;'
                        f'background:rgba(255,255,255,0.04);border:1px solid var(--border-subtle);'
                        f'color:{color};font-weight:650">{text}</span>'
                    )

            if patterns:
                ui.label(
                    "Grounded in: " + ", ".join(pattern["name"] for pattern in patterns[:4])
                ).style("font-size:0.74rem; color:var(--text-secondary); line-height:1.5")

            with ui.expansion("Show judge prompt", icon="article").classes("w-full").style("margin-top: 10px"):
                with ui.scroll_area().style("max-height: 300px; width: 100%"):
                    with ui.element("pre").style(
                        "background: var(--bg-base); border: 1px solid var(--border-subtle); "
                        "border-radius: var(--radius-md); padding: 10px; "
                        "font-size: 0.7rem; color: var(--text-secondary); white-space: pre-wrap; "
                        "line-height: 1.5; font-family: monospace"
                    ):
                        ui.label(judge_prompt_text)

        with ui.element("div").classes("page-card"):
            ui.label("Export").classes("rr-section-title")
            ui.label(
                "Core artifacts only: report, judge-builder packet, dataset, codebook, and judge prompt."
            ).style("font-size: 0.78rem; color: var(--text-muted); margin-top: 6px")
            with ui.row().classes("gap-2 flex-wrap").style("margin-top: 12px"):
                ui.button("Error Analysis (MD)", on_click=download_error_analysis_md, icon="description").props("size=sm dark").style("background: var(--accent); color: white")
                ui.button("HTML Report", on_click=download_html_report, icon="download").props("outline size=sm dark")
                ui.button("Judge Builder Packet", on_click=download_judge_builder_packet, icon="integration_instructions").props("outline size=sm dark")
                ui.button("Golden Dataset", on_click=download_golden_dataset, icon="download").props("outline size=sm dark")
                ui.button("Codebook", on_click=download_codebook, icon="download").props("outline size=sm dark")
                ui.button("Judge Prompt", on_click=download_judge_prompt, icon="download").props("outline size=sm dark")

    return
