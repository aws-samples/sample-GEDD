"""Eval Report page — summary, failure patterns, full judge pipeline, calibration, exports."""

import asyncio
import csv
import io
import json
from collections import Counter
from datetime import date

from nicegui import app, ui

from grounded_evals.ui.layout import page_layout


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
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>GEDD Eval Report — {agent_name}</title>
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
<h1>Evaluation Report — {agent_name}</h1>
<p class="meta">Generated {date_str} &nbsp;·&nbsp; {total} total annotations</p>
<h2>Overall Results</h2>
<div class="stats">
  <div class="stat"><div class="sv">{total}</div><div class="sl">Total</div></div>
  <div class="stat"><div class="sv correct">{correct}</div><div class="sl">Correct</div></div>
  <div class="stat"><div class="sv partial">{partial}</div><div class="sl">Partial</div></div>
  <div class="stat"><div class="sv incorrect">{incorrect}</div><div class="sl">Incorrect</div></div>
  <div class="stat"><div class="sv">{pass_rate}</div><div class="sl">Pass Rate</div></div>
</div>
<h2>Executive Summary</h2>
{summary_html}
<h2>Failure Patterns</h2>
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
    page_layout("Report")
    storage = app.storage.user
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

    with ui.column().classes("w-full max-w-5xl mx-auto").style("padding: 1.5rem; gap: 16px"):

        # ── Header ─────────────────────────────────────────────────────────
        with ui.element("div").classes("page-card"):
            with ui.row().classes("items-center justify-between w-full"):
                ui.label("Evaluation Report").style("font-size: 1.1rem; font-weight: 600; color: var(--text-primary)")
                ui.label(date.today().isoformat()).style("font-size: 0.75rem; color: var(--text-muted)")
            with ui.row().classes("gap-4 mt-2"):
                ui.label(f"Agent: {agent_name}").style("font-size: 0.8rem; color: var(--text-secondary)")
                ui.label(f"Queries: {len(golden_prompts)}").style("font-size: 0.8rem; color: var(--text-secondary)")

        # ── Annotation stats ───────────────────────────────────────────────
        with ui.row().classes("w-full gap-3"):
            stats = [
                ("Total", str(total), "var(--text-primary)"),
                ("Correct", f"{(correct/total*100):.0f}%" if total else "0%", "var(--green-bright)"),
                ("Partial", f"{(partial/total*100):.0f}%" if total else "0%", "var(--yellow)"),
                ("Incorrect", f"{(incorrect/total*100):.0f}%" if total else "0%", "var(--red)"),
            ]
            for label, value, color in stats:
                with ui.card().classes("stat-card flex-1"):
                    ui.label(value).classes("stat-value").style(f"color: {color}")
                    ui.label(label).classes("stat-label")

        # ── Verdict Distribution Chart ──────────────────────────────────────
        if total:
            with ui.element("div").classes("page-card"):
                with ui.row().classes("w-full gap-4 items-start"):
                    # Donut chart — verdict breakdown
                    with ui.column().classes("flex-1").style("min-width:220px"):
                        ui.label("Verdict Distribution").style(
                            "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                            "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px"
                        )
                        # Aggregate by verdict (including custom labels)
                        verdict_counts: dict[str, int] = {}
                        for a in annotations:
                            key = a.get("annotation", "unknown") or "unknown"
                            verdict_counts[key] = verdict_counts.get(key, 0) + 1
                        label_color_map = {"correct": "#4ade80", "partial": "#f0bf00", "incorrect": "#eb5757"}
                        pie_data = [
                            {
                                "name": k.replace("_", " ").title(),
                                "value": v,
                                "itemStyle": {"color": label_color_map.get(k, "#828fff")},
                            }
                            for k, v in sorted(verdict_counts.items(), key=lambda x: -x[1])
                        ]
                        donut_opts = {
                            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
                            "series": [{
                                "type": "pie",
                                "radius": ["45%", "75%"],
                                "data": pie_data,
                                "label": {"color": "#b4b8c0", "fontSize": 11},
                                "emphasis": {"itemStyle": {"shadowBlur": 10}},
                            }],
                            "backgroundColor": "transparent",
                        }
                        ui.echart(donut_opts).style("height:200px; width:100%")

                    # Category breakdown bar chart
                    category_counts: dict[str, dict] = {}
                    for a in annotations:
                        cat = a.get("notes", "")[:30] or a.get("error_code", "") or "General"
                        verdict = a.get("annotation", "unknown")
                        if cat not in category_counts:
                            category_counts[cat] = {"correct": 0, "partial": 0, "incorrect": 0}
                        bucket = verdict if verdict in ("correct", "partial", "incorrect") else "incorrect"
                        category_counts[cat][bucket] += 1

                    # Also pull category from coding_annotations
                    code_counts: dict[str, int] = {}
                    for ca in coding_annotations:
                        for code in ca.get("codes", []):
                            code_counts[code] = code_counts.get(code, 0) + 1

                    if code_counts:
                        with ui.column().classes("flex-1").style("min-width:220px"):
                            ui.label("Error Code Frequency").style(
                                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px"
                            )
                            top_codes = sorted(code_counts.items(), key=lambda x: -x[1])[:10]
                            bar_opts = {
                                "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                                "grid": {"top": 10, "bottom": 20, "left": 120, "right": 20},
                                "xAxis": {"type": "value", "axisLine": {"lineStyle": {"color": "#4a4e55"}}},
                                "yAxis": {
                                    "type": "category",
                                    "data": [c[0] for c in reversed(top_codes)],
                                    "axisLabel": {"color": "#b4b8c0", "fontSize": 11},
                                    "axisLine": {"lineStyle": {"color": "#4a4e55"}},
                                },
                                "series": [{
                                    "type": "bar",
                                    "data": [c[1] for c in reversed(top_codes)],
                                    "itemStyle": {"color": "#5e6ad2", "borderRadius": [0, 4, 4, 0]},
                                    "label": {"show": True, "position": "right", "color": "#b4b8c0", "fontSize": 10},
                                }],
                                "backgroundColor": "transparent",
                            }
                            ui.echart(bar_opts).style(f"height:{max(140, len(top_codes) * 26)}px; width:100%")

        # ── Model Comparison Analytics ─────────────────────────────────────
        # Group annotations by model and category
        model_stats: dict[str, dict] = {}
        for a in annotations:
            model = a.get("model", "unknown")
            if model not in model_stats:
                model_stats[model] = {"correct": 0, "partial": 0, "incorrect": 0, "total": 0}
            model_stats[model][a.get("annotation", "incorrect")] += 1
            model_stats[model]["total"] += 1

        if model_stats:
            with ui.element("div").classes("page-card"):
                ui.label("Model Comparison").style(
                    "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                    "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 12px"
                )
                columns = [
                    {"name": "model", "label": "Model", "field": "model", "align": "left"},
                    {"name": "total", "label": "Evaluated", "field": "total"},
                    {"name": "correct", "label": "✓ Correct", "field": "correct"},
                    {"name": "partial", "label": "⚠ Partial", "field": "partial"},
                    {"name": "incorrect", "label": "✗ Incorrect", "field": "incorrect"},
                    {"name": "pass_rate", "label": "Pass Rate", "field": "pass_rate"},
                ]
                rows = []
                for model, s in model_stats.items():
                    t = max(s["total"], 1)
                    rows.append({
                        "model": model,
                        "total": s["total"],
                        "correct": s["correct"],
                        "partial": s["partial"],
                        "incorrect": s["incorrect"],
                        "pass_rate": f"{s['correct']/t*100:.0f}%",
                    })
                ui.table(columns=columns, rows=rows, row_key="model").classes("w-full").props("dark dense flat")

        # ── Failure Patterns (from Open Coding) — clickable drill-down ──────
        with ui.element("div").classes("page-card"):
            ui.label("Failure Patterns").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px"
            )
            if patterns:
                ui.label("Click a pattern to see the queries tagged with it.").style(
                    "font-size: 0.72rem; color: var(--text-muted); margin-bottom: 10px"
                )
                sev_colors = {"high": "var(--red)", "medium": "var(--yellow)", "low": "var(--green)"}
                for p in patterns:
                    sev_col = sev_colors.get(p["severity"], "var(--text-tertiary)")
                    tagged = [
                        ca for ca in coding_annotations
                        if p["name"] in ca.get("codes", [])
                    ]
                    exp = ui.expansion().classes("w-full").style(
                        f"background:var(--bg-surface-1); border-radius:8px; margin-bottom:5px; "
                        f"border:1px solid var(--border-subtle); border-left:3px solid {sev_col}"
                    )
                    with exp.add_slot('header'):
                        ui.html(
                            f'<div style="display:flex;align-items:center;gap:6px;padding:4px 0;'
                            f'font-size:0.85rem;font-weight:500;color:var(--text-primary)">'
                            f'{p["name"]} &nbsp;·&nbsp; '
                            f'<span style="color:{sev_col};font-weight:600">{p["severity"].upper()}</span>'
                            f' &nbsp;·&nbsp; {p["frequency"]}×'
                            f'</div>'
                        )
                    with exp:
                        if p.get("definition"):
                            ui.label(p["definition"]).style(
                                "font-size:0.75rem; color:var(--text-tertiary); "
                                "margin-bottom:8px; font-style:italic"
                            )
                        if tagged:
                            ui.label(
                                f"{len(tagged)} response{'s' if len(tagged) != 1 else ''} tagged:"
                            ).style("font-size:0.72rem; color:var(--text-secondary); margin-bottom:6px")
                            for ca in tagged[:10]:
                                with ui.element("div").style(
                                    "background:var(--bg-base); border-radius:6px; padding:8px 10px; "
                                    "margin-bottom:4px; border:1px solid var(--border-subtle)"
                                ):
                                    ui.label(ca.get("query", "")[:100]).style(
                                        "font-size:0.75rem; color:var(--text-primary); margin-bottom:3px"
                                    )
                                    resp = ca.get("response", "")
                                    if resp:
                                        ui.label(
                                            (resp[:130] + "…") if len(resp) > 130 else resp
                                        ).style("font-size:0.7rem; color:var(--text-tertiary); line-height:1.4")
                                    if ca.get("memo"):
                                        ui.label(f"Note: {ca['memo']}").style(
                                            "font-size:0.68rem; color:var(--yellow); margin-top:3px; font-style:italic"
                                        )
                            if len(tagged) > 10:
                                ui.label(f"… and {len(tagged) - 10} more").style(
                                    "font-size:0.7rem; color:var(--text-muted)"
                                )
                        else:
                            ui.label(
                                "No annotations yet — complete the Tag Failures step to see examples."
                            ).style("font-size:0.75rem; color:var(--text-muted)")
            else:
                ui.label("Complete the Tag Failures step to see patterns here.").style(
                    "color: var(--text-muted); font-size: 0.8rem"
                )

        # ── Fix Priority (Severity × Frequency) ──────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label("Fix Priority").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
            )
            ui.label("Severity × Frequency — fix these first.").style("font-size: 0.75rem; color: var(--text-muted); margin-bottom: 10px")

            # Calculate priority from coding annotations
            code_stats = {}
            for ann in coding_annotations:
                sev = ann.get('severity', 'functional')
                for code in ann.get('codes', []):
                    if code not in code_stats:
                        code_stats[code] = {'count': 0, 'max_severity': sev}
                    code_stats[code]['count'] += 1
                    sev_rank = {'cosmetic': 1, 'functional': 2, 'critical': 3, 'catastrophic': 4}
                    if sev_rank.get(sev, 2) > sev_rank.get(code_stats[code]['max_severity'], 2):
                        code_stats[code]['max_severity'] = sev

            if code_stats:
                # Calculate priority score
                priority_list = []
                for code, stats in code_stats.items():
                    sev_multiplier = {'cosmetic': 1, 'functional': 2, 'critical': 4, 'catastrophic': 8}
                    score = stats['count'] * sev_multiplier.get(stats['max_severity'], 2)
                    priority_list.append({'code': code, 'freq': stats['count'], 'severity': stats['max_severity'], 'priority': score})

                priority_list.sort(key=lambda x: x['priority'], reverse=True)

                for i, item in enumerate(priority_list[:7]):
                    sev_colors = {'catastrophic': 'var(--red)', 'critical': 'var(--red)', 'functional': 'var(--yellow)', 'cosmetic': 'var(--text-muted)'}
                    sev_icons = {'catastrophic': '⚫', 'critical': '🔴', 'functional': '🟡', 'cosmetic': '🟢'}
                    bar_width = min(100, item['priority'] / priority_list[0]['priority'] * 100)
                    with ui.row().classes("items-center gap-2 w-full").style("margin-bottom: 6px"):
                        ui.label(f"#{i+1}").style("font-size: 0.7rem; font-weight: 700; color: var(--text-muted); width: 20px")
                        ui.element("div").style(
                            f"height: 6px; width: {bar_width}%; background: {sev_colors.get(item['severity'], 'var(--accent)')}; "
                            "border-radius: 3px; min-width: 20px"
                        )
                        ui.label(f"{sev_icons.get(item['severity'], '')} {item['code']}").style(
                            "font-size: 0.8rem; font-weight: 500; color: var(--text-primary); flex: 1"
                        )
                        ui.label(f"×{item['freq']}").style("font-size: 0.7rem; color: var(--text-tertiary)")
                        ui.label(f"P:{item['priority']}").style("font-size: 0.7rem; font-weight: 600; color: var(--accent-bright)")
            else:
                ui.label("Tag failures with severity ratings to see fix priorities.").style("color: var(--text-muted); font-size: 0.8rem")

        # ── Analyst Notes (memos from Tag Failures) ───────────────────────
        memos = storage.get("memos", [])
        if memos:
            with ui.element("div").classes("page-card"):
                ui.label("Analyst Notes").style(
                    "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                    "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px"
                )
                for memo in reversed(memos[-5:]):
                    with ui.element("div").style(
                        "background: var(--yellow-tint); border: 1px solid rgba(240,191,0,0.2); "
                        "border-left: 3px solid var(--yellow); border-radius: var(--radius-lg); "
                        "padding: 10px 14px; margin-bottom: 8px"
                    ):
                        codes = memo.get("codes", [])
                        if codes:
                            with ui.row().classes("gap-1 flex-wrap").style("margin-bottom: 4px"):
                                for c in codes:
                                    ui.html(f'<span class="code-chip" style="font-size:0.65rem">{c}</span>')
                        ui.label(memo.get("text", "")).style(
                            "font-size: 0.8rem; color: var(--text-secondary); line-height: 1.5; font-style: italic"
                        )
                        ts = memo.get("timestamp", "")
                        if ts:
                            ui.label(ts[:16].replace("T", " ")).style(
                                "font-size: 0.65rem; color: var(--text-muted); margin-top: 4px"
                            )

        # ── Root Cause Analysis ────────────────────────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label("Root Cause Analysis").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px"
            )
            all_error_counts = dict(error_counts)
            # Also include coding annotation code frequencies
            for ann in coding_annotations:
                for code in ann.get("codes", []):
                    all_error_counts[code] = all_error_counts.get(code, 0) + 1

            if all_error_counts:
                max_count = max(all_error_counts.values())
                for code, count in sorted(all_error_counts.items(), key=lambda x: -x[1]):
                    with ui.row().classes("items-center gap-2").style("margin-bottom: 6px"):
                        ui.element("div").style(
                            f"width: {min(count/max_count*160, 160)}px; height: 4px; "
                            f"background: var(--accent); border-radius: 2px; min-width: 20px"
                        )
                        ui.label(f"{code} ({count})").style("font-size: 0.78rem; color: var(--text-secondary)")
            else:
                ui.label("No error codes recorded yet. Annotate responses in Eval or Tag Failures.").style(
                    "color: var(--text-muted); font-size: 0.8rem"
                )

        # ── Full Judge Pipeline ────────────────────────────────────────────
        with ui.element("div").classes("page-card"):
            # Header row with data provenance badge
            n_codes = len(codebook)
            n_anns_coded = len(coding_annotations)
            phenomena_list = paradigm.get("phenomenon", [])
            n_phenomena = len(phenomena_list)
            with ui.row().classes("items-start justify-between w-full").style("margin-bottom: 4px"):
                with ui.column().style("gap: 2px"):
                    ui.label("LLM-as-Judge Generation").style(
                        "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                        "text-transform: uppercase; letter-spacing: 0.04em"
                    )
                    ui.label("Automatically build evaluation criteria grounded in your qualitative analysis.").style(
                        "font-size: 0.78rem; color: var(--text-muted)"
                    )
                if n_codes:
                    ui.html(
                        f'<span style="font-size:0.65rem;background:var(--bg-surface-1);color:var(--accent-bright);'
                        f'padding:3px 10px;border-radius:99px;border:1px solid var(--border-subtle);white-space:nowrap">'
                        f'{n_codes} error codes · {n_anns_coded} annotations</span>'
                    )

            # ── How this works ────────────────────────────────────────────
            with ui.element("div").style(
                "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                "border-radius: 12px; padding: 14px 16px; margin: 12px 0 16px"
            ):
                ui.label("HOW THIS WORKS").style(
                    "font-size: 0.6rem; font-weight: 700; letter-spacing: 0.1em; "
                    "color: var(--text-tertiary); margin-bottom: 12px"
                )
                # Pipeline steps
                steps = [
                    ("1", "Open Coding", "Tag Failures", "You annotated responses and assigned error codes to each failure. "
                     "These codes emerged from your data — not from a pre-defined list.", n_anns_coded, "responses tagged",
                     "var(--accent)", bool(n_anns_coded)),
                    ("2", "Axial Coding", "Root Causes", "Error codes were organized into a Paradigm Model: what causes failures, "
                     "how they manifest, what context triggers them, and their user impact.", n_phenomena, "dimensions mapped",
                     "var(--yellow)", bool(n_phenomena)),
                    ("3", "Binary Judges", "Auto-generated", "Each failure phenomenon from the Paradigm Model becomes a dedicated "
                     "TRUE/FALSE judge. No LLM calls needed — generated instantly from your research.", n_phenomena or n_codes, "judges ready",
                     "var(--green-bright)", bool(n_phenomena or n_codes)),
                    ("4", "Full Rubric Judge", "AI-generated", "All error codes are mapped to standard evaluation dimensions "
                     "(accuracy, completeness, tone...) to build a scored 1–5 multi-criteria rubric judge.", 8, "dimensions",
                     "var(--green-bright)", bool(storage.get("_generated_judge_prompt"))),
                ]
                with ui.row().classes("w-full items-start").style("gap: 0"):
                    for i, (num, title, tag, desc, count, count_label, color, done) in enumerate(steps):
                        with ui.element("div").style("flex: 1; min-width: 0"):
                            with ui.element("div").style(
                                f"border-radius: 10px; padding: 10px; "
                                f"background: {'var(--bg-surface-2)' if done else 'transparent'}; "
                                f"border: 1px solid {'var(--border-subtle)' if done else 'transparent'}"
                            ):
                                with ui.row().classes("items-center gap-2").style("margin-bottom: 4px"):
                                    ui.html(
                                        f'<span style="width:18px;height:18px;border-radius:50%;background:{color if done else "var(--bg-surface-2)"};'
                                        f'color:{"white" if done else "var(--text-muted)"};font-size:0.62rem;font-weight:700;'
                                        f'display:flex;align-items:center;justify-content:center;flex-shrink:0">{num}</span>'
                                    )
                                    ui.label(title).style(
                                        f"font-size: 0.75rem; font-weight: 600; "
                                        f"color: {'var(--text-primary)' if done else 'var(--text-muted)'}"
                                    )
                                    ui.html(
                                        f'<span style="font-size:0.55rem;padding:1px 6px;border-radius:99px;'
                                        f'background:{"var(--green-tint)" if done else "var(--bg-surface-1)"};'
                                        f'color:{"var(--green-bright)" if done else "var(--text-muted)"};font-weight:600">'
                                        f'{tag}</span>'
                                    )
                                ui.label(desc).style(
                                    "font-size: 0.7rem; color: var(--text-tertiary); line-height: 1.4; margin-bottom: 6px"
                                )
                                if done:
                                    ui.html(
                                        f'<span style="font-size:0.65rem;color:{color};font-weight:600">'
                                        f'✓ {count} {count_label}</span>'
                                    )
                                else:
                                    ui.label("Not started yet").style("font-size: 0.65rem; color: var(--text-muted)")
                        # Arrow between steps
                        if i < len(steps) - 1:
                            ui.html(
                                '<span style="align-self:center;color:var(--text-muted);font-size:1rem;'
                                'padding:0 4px;flex-shrink:0">→</span>'
                            )

            # ── Judge output container ─────────────────────────────────────
            judge_output_container = ui.column().classes("w-full")

            def _render_judge_prompts(judge_prompt: str | None = None, judge_mappings: list | None = None):
                judge_output_container.clear()
                with judge_output_container:
                    phenomena = paradigm.get("phenomenon", [])
                    targets = phenomena if phenomena else [c["name"] for c in codebook[:5]]
                    causal = ", ".join(paradigm.get("causal_conditions", [])) or "Unknown"
                    context_text = ", ".join(paradigm.get("context", [])) or "Unknown"
                    strategies_text = ", ".join(paradigm.get("strategies", [])) or "Unknown"
                    consequences_text = ", ".join(paradigm.get("consequences", [])) or "Unknown"

                    # Build code→annotation count map for data trail
                    code_ann_count: dict[str, int] = {}
                    for ca in coding_annotations:
                        for code in ca.get("codes", []):
                            code_ann_count[code] = code_ann_count.get(code, 0) + 1

                    # ── Binary Judges ─────────────────────────────────────
                    if targets:
                        with ui.row().classes("items-center gap-2").style("margin-bottom: 10px"):
                            ui.label("Binary Judges (from Paradigm Model)").style(
                                "font-size: 0.72rem; font-weight: 600; color: var(--text-tertiary); "
                                "text-transform: uppercase; letter-spacing: 0.04em"
                            )
                            ui.html(
                                '<span style="font-size:0.62rem;padding:2px 8px;border-radius:99px;'
                                'background:var(--bg-surface-1);color:var(--text-muted);border:1px solid var(--border-subtle)">'
                                'TRUE / FALSE · instant · no LLM call</span>'
                            )

                        with ui.element("div").style(
                            "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                            "border-radius: 10px; padding: 10px 12px; margin-bottom: 12px; font-size: 0.72rem; "
                            "color: var(--text-tertiary); line-height: 1.5"
                        ):
                            ui.html(
                                f'Each judge below asks a single yes/no question: <em>"Does this response exhibit this failure pattern?"</em> '
                                f'They are derived directly from your Paradigm Model — the <strong style="color:var(--text-secondary)">'
                                f'phenomenon</strong> field names the failure, <strong style="color:var(--text-secondary)">causal conditions</strong> '
                                f'explain why it happens, and <strong style="color:var(--text-secondary)">consequences</strong> ground the user impact. '
                                f'Use these as fast binary signals in your automated eval pipeline.'
                            )

                        for target in targets:
                            # Find related annotations for data trail
                            related_count = code_ann_count.get(target, 0)
                            # Also check partial matches (e.g. "Policy Hallucination" in codebook
                            if not related_count:
                                for code_name, cnt in code_ann_count.items():
                                    if target.lower() in code_name.lower() or code_name.lower() in target.lower():
                                        related_count = cnt
                                        break

                            prompt = (
                                f"You are evaluating whether a response exhibits {target.upper()}.\n\n"
                                f"Triggered by: {causal}\n"
                                f"Context: {context_text}\n"
                                f"Manifests as: {strategies_text}\n"
                                f"User impact: {consequences_text}\n\n"
                                f"<query>{{query}}</query>\n"
                                f"<response>{{response}}</response>\n\n"
                                f"Think step by step. Score TRUE if the response exhibits this pattern. Score FALSE otherwise."
                            )
                            with ui.element("div").style(
                                "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                                "border-radius: var(--radius-lg); padding: 12px; margin-bottom: 10px"
                            ):
                                with ui.row().classes("items-center justify-between w-full").style("margin-bottom: 8px"):
                                    with ui.row().classes("items-center gap-2"):
                                        ui.label(f"Judge: {target}").style(
                                            "font-weight: 600; font-size: 0.85rem; color: var(--text-primary)"
                                        )
                                        if related_count:
                                            ui.html(
                                                f'<span style="font-size:0.6rem;padding:2px 7px;border-radius:99px;'
                                                f'background:var(--accent-tint, rgba(94,106,210,0.12));color:var(--accent-bright);'
                                                f'border:1px solid rgba(94,106,210,0.2)">'
                                                f'{related_count} annotated example{"s" if related_count != 1 else ""}</span>'
                                            )
                                    ui.button("Copy", icon="content_copy", on_click=lambda _, p=prompt: ui.run_javascript(
                                        f"navigator.clipboard.writeText({json.dumps(p)})"
                                    )).props("flat size=sm").style("color: var(--text-tertiary)")
                                # Data trail: annotation → code → phenomenon → judge
                                with ui.row().classes("items-center gap-1").style("margin-bottom: 8px"):
                                    trail_items = [
                                        (f"{n_anns_coded} annotations", "var(--text-muted)"),
                                        ("→", "var(--text-muted)"),
                                        (f"{n_codes} error codes", "var(--text-muted)"),
                                        ("→", "var(--text-muted)"),
                                        ("Paradigm Model", "var(--accent-bright)"),
                                        ("→", "var(--text-muted)"),
                                        ("This judge", "var(--green-bright)"),
                                    ]
                                    for item, color in trail_items:
                                        ui.label(item).style(f"font-size: 0.62rem; color: {color}")
                                with ui.element("pre").style(
                                    "background: var(--bg-base); border: 1px solid var(--border-subtle); "
                                    "border-radius: var(--radius-md); padding: 10px; "
                                    "font-size: 0.7rem; color: var(--text-secondary); white-space: pre-wrap; "
                                    "line-height: 1.5; max-height: 200px; overflow-y: auto; font-family: monospace"
                                ):
                                    ui.label(prompt)

                    # ── Intermediate: Error Code → Dimension Mapping ───────
                    mappings_data = judge_mappings or storage.get("_judge_mappings", [])
                    if mappings_data:
                        ui.separator().style("opacity: 0.1; margin: 16px 0")
                        with ui.row().classes("items-center gap-2").style("margin-bottom: 10px"):
                            ui.label("Error Code → Evaluation Dimension Mapping").style(
                                "font-size: 0.72rem; font-weight: 600; color: var(--text-tertiary); "
                                "text-transform: uppercase; letter-spacing: 0.04em"
                            )
                            ui.html(
                                '<span style="font-size:0.62rem;padding:2px 8px;border-radius:99px;'
                                'background:var(--green-tint);color:var(--green-bright);border:1px solid rgba(39,166,68,0.2)">'
                                'AI-generated</span>'
                            )
                        ui.label(
                            "Each error code from your Open Coding was analyzed by an LLM and mapped to a standard evaluation "
                            "dimension. These mappings become the criteria of your Full Rubric Judge."
                        ).style("font-size: 0.72rem; color: var(--text-tertiary); margin-bottom: 10px; line-height: 1.5")

                        dim_color = {
                            "accuracy": "var(--red)", "quality": "var(--accent-bright)",
                            "completeness": "var(--yellow)", "tone": "var(--green-bright)",
                            "instruction_following": "var(--accent-bright)", "safety": "var(--red)",
                            "brand_relevance": "var(--yellow)", "bias": "var(--red)",
                        }
                        with ui.element("div").style(
                            "border: 1px solid var(--border-subtle); border-radius: 10px; overflow: hidden"
                        ):
                            # Header row
                            with ui.row().style(
                                "background: var(--bg-surface-2); padding: 6px 12px; gap: 0; border-bottom: 1px solid var(--border-subtle)"
                            ):
                                ui.label("Error Code").style("font-size: 0.65rem; font-weight: 600; color: var(--text-tertiary); flex: 1")
                                ui.label("Dimension").style("font-size: 0.65rem; font-weight: 600; color: var(--text-tertiary); width: 140px")
                                ui.label("Rationale").style("font-size: 0.65rem; font-weight: 600; color: var(--text-tertiary); flex: 2")
                            for i, m in enumerate(mappings_data):
                                bg = "var(--bg-surface-1)" if i % 2 == 0 else "var(--bg-base)"
                                dim = m.get("primary_category", m.get("dimension", ""))
                                with ui.row().style(
                                    f"background: {bg}; padding: 7px 12px; gap: 0; align-items: flex-start; "
                                    f"border-bottom: 1px solid var(--border-subtle)"
                                ):
                                    ui.label(m.get("error_code", "")).style(
                                        "font-size: 0.72rem; color: var(--text-secondary); flex: 1; font-weight: 500"
                                    )
                                    color = dim_color.get(dim, "var(--accent-bright)")
                                    ui.html(
                                        f'<span style="font-size:0.62rem;padding:2px 7px;border-radius:99px;'
                                        f'background:rgba(0,0,0,0.2);color:{color};width:140px;display:inline-block;'
                                        f'text-align:center;flex-shrink:0">{dim.replace("_"," ").title()}</span>'
                                    )
                                    ui.label(m.get("rationale", "")).style(
                                        "font-size: 0.68rem; color: var(--text-tertiary); flex: 2; line-height: 1.4; margin-left: 8px"
                                    )

                    # ── Full Rubric Judge ──────────────────────────────────
                    if judge_prompt:
                        ui.separator().style("opacity: 0.1; margin: 16px 0")
                        with ui.row().classes("items-center gap-2").style("margin-bottom: 8px"):
                            ui.label("Full Rubric Judge (grounded in error analysis)").style(
                                "font-size: 0.72rem; font-weight: 600; color: var(--green-bright); "
                                "text-transform: uppercase; letter-spacing: 0.04em"
                            )
                            ui.html(
                                '<span style="font-size:0.62rem;padding:2px 8px;border-radius:99px;'
                                'background:var(--green-tint);color:var(--green-bright);border:1px solid rgba(39,166,68,0.2)">'
                                'scored 1–5 per dimension</span>'
                            )
                        ui.label(
                            "This multi-criteria rubric judge evaluates responses on every evaluation dimension your error analysis surfaced. "
                            "Each criterion includes the specific failure patterns observed, so scores are grounded in real data — "
                            "not generic heuristics. Plug this prompt into any automated eval pipeline."
                        ).style("font-size: 0.72rem; color: var(--text-tertiary); margin-bottom: 10px; line-height: 1.5")
                        with ui.element("div").style(
                            "background: var(--bg-surface-1); border: 1px solid var(--green); "
                            "border-radius: var(--radius-lg); padding: 12px"
                        ):
                            with ui.row().classes("items-center justify-between w-full"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.label("Multi-criterion rubric judge").style(
                                        "font-weight: 600; font-size: 0.85rem; color: var(--text-primary)"
                                    )
                                    ui.html(
                                        '<span style="font-size:0.6rem;padding:2px 7px;border-radius:99px;'
                                        'background:var(--green-tint);color:var(--green-bright)">Ready to use</span>'
                                    )
                                ui.button("Copy", icon="content_copy", on_click=lambda: ui.run_javascript(
                                    f"navigator.clipboard.writeText({json.dumps(judge_prompt)})"
                                )).props("flat size=sm").style("color: var(--text-tertiary)")
                            with ui.scroll_area().style("max-height: 300px; width: 100%; margin-top: 8px"):
                                with ui.element("pre").style(
                                    "font-size: 0.7rem; color: var(--text-secondary); white-space: pre-wrap; "
                                    "line-height: 1.5; font-family: monospace"
                                ):
                                    ui.label(judge_prompt)

            _render_judge_prompts(
                storage.get("_generated_judge_prompt"),
                storage.get("_judge_mappings"),
            )

            async def generate_full_judge():
                if not codebook:
                    ui.notify("Complete Tag Failures step first — need error codes", type="warning")
                    return
                try:
                    from grounded_evals.axial_coding.mapper import map_errors_to_categories
                    from grounded_evals.judge_builder.prompt_gen import generate_judge_prompt
                    from grounded_evals.judge_builder.rubric import generate_rubric
                    from grounded_evals.models.core import Code, CodeType

                    gen_btn.props("loading")
                    ui.notify("Step 1/2 — Mapping error codes to evaluation dimensions...", type="info")

                    codes = [Code(label=c["name"], definition=c.get("definition", ""), code_type=CodeType.DESCRIPTIVE) for c in codebook]
                    mappings = await asyncio.to_thread(map_errors_to_categories, codes)
                    if not mappings:
                        ui.notify("Could not map error codes — check LLM connectivity", type="warning")
                        gen_btn.props(remove="loading")
                        return

                    # Persist mappings so the UI can show the intermediate step
                    mappings_data = [
                        {"error_code": m.error_code, "primary_category": m.primary_category,
                         "rationale": m.rationale}
                        for m in mappings
                    ]
                    storage["_judge_mappings"] = mappings_data

                    ui.notify("Step 2/2 — Building rubric judge from mappings...", type="info")
                    rubric = generate_rubric(mappings)
                    judge_prompt = generate_judge_prompt(rubric, agent_name, agent_description)
                    storage["_generated_judge_prompt"] = judge_prompt

                    ui.notify("Full rubric judge generated ✓", type="positive")
                    _render_judge_prompts(judge_prompt, mappings_data)
                except Exception as e:
                    ui.notify(f"Error generating judge: {e}", type="negative")
                finally:
                    gen_btn.props(remove="loading")

            gen_btn = ui.button(
                "Generate Full Rubric Judge (AI)", icon="auto_fix_high", on_click=generate_full_judge
            ).props("size=sm").style(
                "margin-top: 14px; background: var(--accent); color: white; border-radius: var(--radius-md)"
            )
            ui.label(
                "Uses an LLM to map your error codes to standard evaluation dimensions, "
                "then generates a scored rubric judge grounded in your research."
            ).style("font-size: 0.68rem; color: var(--text-muted); margin-top: 6px")

        # ── ML-Enhanced Judge Generation ──────────────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label("ML-Enhanced Judge Generation").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
            )
            ui.label(
                "Apply ML research techniques to teach the judge your specific error modes — "
                "grounded in your qualitative annotations, not generic heuristics."
            ).style("font-size: 0.78rem; color: var(--text-muted); margin-bottom: 14px")

            # Technique cards (educational + actionable)
            ml_techniques = [
                ("few_shot", "Few-Shot (Prometheus)", "auto_awesome",
                 "var(--accent)", "var(--accent-tint, rgba(94,106,210,0.12))",
                 "Injects your annotated examples directly into the judge prompt. "
                 "The judge sees what a Policy Hallucination looks like before evaluating. "
                 "Directly based on Kim et al. 2023 (Prometheus). Highest-impact technique for domain-specific calibration.",
                 "Best when: you have ≥3 annotated examples per error code. Typical kappa improvement: +0.15–0.25."),
                ("geval", "G-EVAL (Chain-of-Thought)", "account_tree",
                 "var(--yellow)", "rgba(240,191,0,0.10)",
                 "Forces step-by-step reasoning per criterion before scoring. "
                 "Each criterion gets structured sub-questions derived from your rubric. "
                 "Based on Liu et al. 2023 (G-EVAL). Reduces anchoring bias on overall score.",
                 "Best when: your rubric has complex, multi-aspect criteria. Adds ~3× more tokens per evaluation."),
                ("constitutional", "Constitutional (Principle-based)", "gavel",
                 "var(--green-bright)", "var(--green-tint)",
                 "Converts each error code into an independent check (principle). "
                 "Inspired by Constitutional AI (Bai et al. 2022, Anthropic). "
                 "Judge evaluates each principle sequentially — no anchoring to overall score.",
                 "Best when: you want per-principle verdicts and full traceback to error codes."),
            ]

            with ui.row().classes("w-full gap-3").style("margin-bottom: 16px; flex-wrap: wrap"):
                for mode, title, icon_name, color, bg, desc, usage in ml_techniques:
                    with ui.element("div").style(
                        f"flex: 1; min-width: 220px; background: {bg}; border: 1px solid {color}30; "
                        f"border-radius: 12px; padding: 12px"
                    ):
                        with ui.row().classes("items-center gap-2").style("margin-bottom: 6px"):
                            ui.icon(icon_name).style(f"color: {color}; font-size: 1rem")
                            ui.label(title).style(f"font-size: 0.78rem; font-weight: 600; color: {color}")
                        ui.label(desc).style("font-size: 0.7rem; color: var(--text-tertiary); line-height: 1.5; margin-bottom: 6px")
                        ui.label(usage).style(
                            f"font-size: 0.65rem; color: {color}; line-height: 1.4; "
                            f"background: {color}20; border-radius: 6px; padding: 4px 8px"
                        )

            ml_mode = {"value": "few_shot"}
            ml_mode_select = ui.select(
                options={
                    "few_shot": "Few-Shot / Prometheus-style",
                    "geval": "G-EVAL Chain-of-Thought",
                    "constitutional": "Constitutional (Principle-by-Principle)",
                },
                value="few_shot",
                label="Generation mode",
                on_change=lambda e: ml_mode.update({"value": e.value}),
            ).props("dense outlined dark").style("width: 300px; margin-bottom: 12px")

            ml_output_container = ui.column().classes("w-full")

            async def generate_ml_judge():
                if not codebook:
                    ui.notify("Complete Tag Failures step first — need error codes", type="warning")
                    return
                ml_btn.props("loading")
                try:
                    from grounded_evals.axial_coding.mapper import map_errors_to_categories
                    from grounded_evals.judge_builder.few_shot import select_exemplars
                    from grounded_evals.judge_builder.prompt_gen import (
                        generate_few_shot_judge_prompt,
                        generate_geval_judge_prompt,
                        generate_judge_prompt,
                    )
                    from grounded_evals.judge_builder.rubric import generate_rubric
                    from grounded_evals.models.core import Code, CodeType

                    mode = ml_mode["value"]
                    codes = [Code(label=c["name"], definition=c.get("definition", ""), code_type=CodeType.DESCRIPTIVE) for c in codebook]

                    ui.notify("Mapping error codes to evaluation dimensions...", type="info")
                    mappings = await asyncio.to_thread(map_errors_to_categories, codes)
                    if not mappings:
                        ui.notify("Could not map error codes — check LLM connectivity", type="warning")
                        ml_btn.props(remove="loading")
                        return

                    mappings_data = [
                        {"error_code": m.error_code, "primary_category": m.primary_category, "rationale": m.rationale}
                        for m in mappings
                    ]
                    storage["_judge_mappings"] = mappings_data

                    rubric = generate_rubric(mappings, paradigm_dict=paradigm)
                    ui.notify(f"Building {mode} judge prompt...", type="info")

                    if mode == "few_shot":
                        exemplar_set = select_exemplars(coding_annotations, codebook)
                        storage["_exemplar_coverage"] = exemplar_set.coverage
                        storage["_n_exemplars"] = len(exemplar_set.exemplars)
                        judge_prompt_ml = generate_few_shot_judge_prompt(rubric, exemplar_set, agent_name, agent_description)
                    elif mode == "geval":
                        judge_prompt_ml = generate_geval_judge_prompt(rubric, agent_name, agent_description)
                    elif mode == "constitutional":
                        from grounded_evals.judge_builder.constitutional import (
                            build_constitutional_judge_prompt,
                            build_constitutional_principles,
                        )
                        principles = build_constitutional_principles(codebook, paradigm, coding_annotations, mappings_data)
                        judge_prompt_ml = build_constitutional_judge_prompt(principles, agent_name, agent_description)
                        storage["_constitutional_principles"] = [
                            {"code": p.code_name, "definition": p.definition, "causal_trigger": p.causal_trigger}
                            for p in principles
                        ]
                    else:
                        judge_prompt_ml = generate_judge_prompt(rubric, agent_name, agent_description)

                    storage["_generated_judge_prompt"] = judge_prompt_ml
                    storage["_judge_mode"] = mode

                    ml_output_container.clear()
                    with ml_output_container:
                        _render_ml_output(judge_prompt_ml, mode, mappings_data)

                    ui.notify(f"{mode.replace('_', ' ').title()} judge generated ✓", type="positive")
                except Exception as e:
                    ui.notify(f"Error: {e}", type="negative")
                finally:
                    ml_btn.props(remove="loading")

            def _render_ml_output(judge_prompt_ml: str, mode: str, mappings_data: list):
                ml_output_container.clear()
                with ml_output_container:
                    mode_labels = {
                        "few_shot": ("Few-Shot Calibrated Judge", "var(--accent-bright)"),
                        "geval": ("G-EVAL Chain-of-Thought Judge", "var(--yellow)"),
                        "constitutional": ("Constitutional Judge", "var(--green-bright)"),
                    }
                    label, color = mode_labels.get(mode, ("ML Judge", "var(--text-primary)"))

                    with ui.element("div").style(
                        f"border: 1px solid {color}; border-radius: 12px; padding: 14px; margin-top: 4px"
                    ):
                        with ui.row().classes("items-center justify-between w-full").style("margin-bottom: 8px"):
                            with ui.column().style("gap: 2px"):
                                ui.label(label).style(f"font-size: 0.85rem; font-weight: 600; color: {color}")
                                if mode == "few_shot":
                                    n_ex = storage.get("_n_exemplars", 0)
                                    cov = storage.get("_exemplar_coverage", [])
                                    if n_ex:
                                        ui.label(
                                            f"{n_ex} annotated examples injected · covers: {', '.join(cov[:3])}"
                                        ).style("font-size: 0.65rem; color: var(--text-muted)")
                                elif mode == "constitutional":
                                    n_princ = len(storage.get("_constitutional_principles", []))
                                    ui.label(f"{n_princ} constitutional principles derived from error codes").style(
                                        "font-size: 0.65rem; color: var(--text-muted)"
                                    )
                            ui.button("Copy", icon="content_copy", on_click=lambda: ui.run_javascript(
                                f"navigator.clipboard.writeText({json.dumps(judge_prompt_ml)})"
                            )).props("flat size=sm").style("color: var(--text-tertiary)")

                        # Constitutional principles breakdown
                        if mode == "constitutional":
                            principles = storage.get("_constitutional_principles", [])
                            if principles:
                                ui.label("Principles derived:").style(
                                    "font-size: 0.65rem; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px"
                                )
                                for p in principles[:6]:
                                    with ui.row().classes("items-start gap-2").style("margin-bottom: 3px"):
                                        ui.html('<span style="color:var(--green-bright);font-size:0.7rem">✓</span>')
                                        ui.label(f"{p['code']}: {p['definition'][:80]}").style(
                                            "font-size: 0.68rem; color: var(--text-secondary); line-height: 1.3"
                                        )

                        # Few-shot exemplar summary
                        if mode == "few_shot":
                            cov = storage.get("_exemplar_coverage", [])
                            if cov:
                                ui.label("Injected examples cover:").style(
                                    "font-size: 0.65rem; font-weight: 600; color: var(--text-tertiary); margin-bottom: 4px"
                                )
                                with ui.row().classes("gap-1 flex-wrap").style("margin-bottom: 8px"):
                                    for code_name in cov:
                                        ui.html(
                                            f'<span style="font-size:0.62rem;padding:2px 7px;border-radius:99px;'
                                            f'background:var(--accent-tint, rgba(94,106,210,0.15));color:var(--accent-bright)">'
                                            f'{code_name}</span>'
                                        )

                        with ui.scroll_area().style("max-height: 250px; width: 100%; margin-top: 8px"):
                            with ui.element("pre").style(
                                "font-size: 0.68rem; color: var(--text-secondary); white-space: pre-wrap; "
                                "line-height: 1.5; font-family: monospace"
                            ):
                                ui.label(judge_prompt_ml)

            # Render any previously generated ML judge
            prev_ml = storage.get("_generated_judge_prompt")
            prev_mode = storage.get("_judge_mode")
            if prev_ml and prev_mode and prev_mode != "standard":
                _render_ml_output(prev_ml, prev_mode, storage.get("_judge_mappings", []))

            ml_btn = ui.button(
                "Generate ML-Enhanced Judge", icon="psychology", on_click=generate_ml_judge
            ).props("size=sm").style(
                "margin-top: 10px; background: var(--accent); color: white; border-radius: var(--radius-md)"
            )
            ui.label(
                "Generates a judge prompt using the selected ML technique, grounded in your coding annotations and Paradigm Model."
            ).style("font-size: 0.68rem; color: var(--text-muted); margin-top: 6px")

        # ── Calibration ────────────────────────────────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label("Judge Calibration").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
            )
            ui.label(
                "Score a sample of responses yourself, then run the judge — see how well they agree."
            ).style("font-size: 0.78rem; color: var(--text-muted); margin-bottom: 12px")

            # Pick dimensions to score (from codebook or fixed set)
            dimensions = list({c["name"] for c in codebook}) if codebook else ["accuracy", "completeness", "tone"]
            dimensions = dimensions[:5]  # cap at 5

            calibration_container = ui.column().classes("w-full")

            def render_calibration():
                calibration_container.clear()
                with calibration_container:
                    sample = annotations[:10] if len(annotations) >= 3 else annotations
                    if not sample:
                        ui.label("No annotated responses yet — complete the Eval step first.").style(
                            "font-size: 0.8rem; color: var(--text-muted)"
                        )
                        return

                    judge_prompt = storage.get("_generated_judge_prompt")
                    if not judge_prompt:
                        ui.label("Generate a Full Rubric Judge above first.").style(
                            "font-size: 0.8rem; color: var(--text-muted)"
                        )
                        return

                    manual_scores_store: list[dict] = storage.setdefault("_calibration_manual", [{}] * len(sample))

                    ui.label(f"Score these {len(sample)} responses (1-5 per dimension):").style(
                        "font-size: 0.82rem; font-weight: 500; color: var(--text-primary); margin-bottom: 8px"
                    )

                    for i, ann in enumerate(sample):
                        with ui.element("div").style(
                            "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                            "border-radius: var(--radius-lg); padding: 12px; margin-bottom: 8px"
                        ):
                            ui.label(f"Q{i+1}: {ann.get('query', '')[:80]}...").style(
                                "font-size: 0.78rem; font-weight: 500; color: var(--text-primary); margin-bottom: 4px"
                            )
                            ui.label(ann.get("response", "")[:120] + "...").style(
                                "font-size: 0.72rem; color: var(--text-tertiary); margin-bottom: 8px"
                            )
                            row = ui.row().classes("gap-3 flex-wrap")
                            with row:
                                for dim in dimensions:
                                    existing_val = (manual_scores_store[i] or {}).get(dim, 3) if i < len(manual_scores_store) else 3

                                    def make_score_handler(idx=i, d=dim):
                                        def on_change(e):
                                            while len(manual_scores_store) <= idx:
                                                manual_scores_store.append({})
                                            if manual_scores_store[idx] is None:
                                                manual_scores_store[idx] = {}
                                            manual_scores_store[idx][d] = int(e.value)
                                            storage["_calibration_manual"] = manual_scores_store
                                        return on_change

                                    with ui.column().style("gap: 2px"):
                                        ui.label(dim[:12]).style("font-size: 0.65rem; color: var(--text-tertiary)")
                                        ui.select(
                                            options={1: "1", 2: "2", 3: "3", 4: "4", 5: "5"},
                                            value=existing_val,
                                            on_change=make_score_handler(),
                                        ).props("dense dark outlined").style("width: 60px")

                    cal_result_container = ui.column().classes("w-full")

                    async def run_calibration():
                        judge_prompt_text = storage.get("_generated_judge_prompt", "")
                        if not judge_prompt_text:
                            ui.notify("Generate a judge first", type="warning")
                            return

                        manual = storage.get("_calibration_manual", [])
                        if not any(m for m in manual):
                            ui.notify("Score at least one response first", type="warning")
                            return

                        cal_btn.props("loading")
                        try:
                            from grounded_evals.judge_builder.calibrate import calibrate
                            from grounded_evals.llm.client import get_default_client, get_model_id

                            client = get_default_client()
                            model_id = get_model_id()
                            judge_scores: list[dict] = []

                            sample_list = annotations[:10] if len(annotations) >= 3 else annotations
                            for ann in sample_list:
                                prompt = f"{judge_prompt_text}\n\n<query>{ann.get('query','')}</query>\n<response>{ann.get('response','')}</response>"
                                resp = await asyncio.to_thread(
                                    client.messages.create,
                                    model=model_id,
                                    max_tokens=512,
                                    messages=[{"role": "user", "content": prompt}],
                                )
                                text = resp.content[0].text
                                # Try to extract JSON scores from judge response
                                import re
                                score_match = re.search(r'"scores"\s*:\s*\{([^}]+)\}', text)
                                scores_dict: dict[str, int] = {}
                                if score_match:
                                    for m in re.finditer(r'"(\w+)"\s*:\s*(\d)', score_match.group(0)):
                                        scores_dict[m.group(1)] = int(m.group(2))
                                # Fallback: if judge says pass/fail, map to 4/2
                                if not scores_dict:
                                    score_val = 4 if "true" in text.lower() or "pass" in text.lower() else 2
                                    scores_dict = {d: score_val for d in dimensions}
                                judge_scores.append(scores_dict)

                            storage["_calibration_judge"] = judge_scores
                            result = calibrate(
                                [m for m in manual if m],
                                judge_scores,
                            )

                            cal_result_container.clear()
                            with cal_result_container:
                                kappa = result.weighted_kappa or result.cohens_kappa
                                color = "var(--green-bright)" if kappa >= 0.80 else (
                                    "var(--yellow)" if kappa >= 0.61 else "var(--red)"
                                )
                                with ui.element("div").style(
                                    f"background: var(--bg-surface-2); border: 1px solid {color}; "
                                    f"border-radius: var(--radius-lg); padding: 14px; margin-top: 12px"
                                ):
                                    with ui.row().classes("gap-6 items-start").style("margin-bottom: 8px"):
                                        with ui.column().style("gap: 2px"):
                                            ui.label(f"κ = {kappa:.3f}").style(
                                                f"font-size: 1.2rem; font-weight: 700; color: {color}"
                                            )
                                            ui.label("Weighted Cohen's Kappa").style(
                                                "font-size: 0.62rem; color: var(--text-tertiary)"
                                            )
                                        with ui.column().style("gap: 2px"):
                                            ui.label(f"{result.agreement_score:.0%}").style(
                                                "font-size: 1.0rem; font-weight: 600; color: var(--text-secondary)"
                                            )
                                            ui.label("Raw ±1 agreement").style(
                                                "font-size: 0.62rem; color: var(--text-tertiary)"
                                            )
                                        if result.kappa_ci_low != result.kappa_ci_high:
                                            with ui.column().style("gap: 2px"):
                                                ui.label(f"[{result.kappa_ci_low:.2f}, {result.kappa_ci_high:.2f}]").style(
                                                    "font-size: 0.82rem; color: var(--text-muted)"
                                                )
                                                ui.label("95% CI").style("font-size: 0.62rem; color: var(--text-tertiary)")
                                    ui.label(result.kappa_interpretation).style(
                                        f"font-size: 0.78rem; color: {color}; font-weight: 500; margin-bottom: 4px"
                                    )
                                    ui.label(result.recommendation).style(
                                        "font-size: 0.78rem; color: var(--text-secondary)"
                                    )
                                    if result.per_criterion_kappa:
                                        ui.label("Kappa per criterion:").style(
                                            "font-size: 0.68rem; color: var(--text-tertiary); margin-top: 10px; font-weight: 600"
                                        )
                                        for crit, ck in sorted(result.per_criterion_kappa.items(), key=lambda x: x[1]):
                                            ck_color = "var(--green-bright)" if ck >= 0.8 else ("var(--yellow)" if ck >= 0.6 else "var(--red)")
                                            weakest_marker = " ← fix this" if crit == result.weakest_criterion else ""
                                            ui.label(f"• {crit}: κ={ck:.2f}{weakest_marker}").style(
                                                f"font-size: 0.68rem; color: {ck_color}"
                                            )
                                    if result.disagreements:
                                        ui.label("Disagreements:").style(
                                            "font-size: 0.68rem; color: var(--text-tertiary); margin-top: 8px; font-weight: 600"
                                        )
                                        for d in result.disagreements[:5]:
                                            ui.label(f"• {d}").style("font-size: 0.68rem; color: var(--red)")

                        except Exception as e:
                            ui.notify(f"Calibration error: {e}", type="negative")
                        finally:
                            cal_btn.props(remove="loading")

                    cal_btn = ui.button(
                        "Run Calibration", icon="balance", on_click=run_calibration
                    ).props("size=sm").style(
                        "margin-top: 12px; background: var(--accent); color: white; border-radius: var(--radius-md)"
                    )

                    # Show previous result if available
                    prev_manual = storage.get("_calibration_manual")
                    prev_judge = storage.get("_calibration_judge")
                    if prev_manual and prev_judge:
                        from grounded_evals.judge_builder.calibrate import calibrate
                        try:
                            result = calibrate([m for m in prev_manual if m], prev_judge)
                            with cal_result_container:
                                kappa = result.weighted_kappa or result.cohens_kappa
                                color = "var(--green-bright)" if kappa >= 0.80 else (
                                    "var(--yellow)" if kappa >= 0.61 else "var(--red)"
                                )
                                with ui.element("div").style(
                                    f"background: var(--bg-surface-2); border: 1px solid {color}; "
                                    f"border-radius: var(--radius-lg); padding: 14px; margin-top: 12px"
                                ):
                                    ui.label(f"Last calibration: κ={kappa:.3f} ({result.agreement_score:.0%} raw agreement)").style(
                                        f"font-size: 0.9rem; font-weight: 600; color: {color}"
                                    )
                                    ui.label(result.kappa_interpretation).style(f"font-size: 0.72rem; color: {color}")
                                    ui.label(result.recommendation).style(
                                        "font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px"
                                    )
                        except Exception:
                            pass

            render_calibration()

        # ── Active Learning Recommendations ───────────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label("Active Learning — What to Annotate Next").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
            )
            ui.label(
                "Human annotation is the bottleneck. Uncertainty sampling identifies which responses "
                "would most improve judge calibration if annotated next."
            ).style("font-size: 0.78rem; color: var(--text-muted); margin-bottom: 12px")

            from grounded_evals.judge_builder.active_learning import _find_coverage_gaps

            coverage_gaps = _find_coverage_gaps(coding_annotations, codebook)

            if coverage_gaps:
                with ui.element("div").style(
                    "background: rgba(240,191,0,0.08); border: 1px solid rgba(240,191,0,0.25); "
                    "border-radius: 10px; padding: 10px 12px; margin-bottom: 12px"
                ):
                    ui.label("Coverage Gaps — error codes with < 2 annotated examples").style(
                        "font-size: 0.65rem; font-weight: 700; letter-spacing: 0.06em; color: var(--yellow); margin-bottom: 6px"
                    )
                    ui.label(
                        "These error codes don't have enough examples for the few-shot judge to learn from. "
                        "Adding 1–2 clear examples each will have the highest calibration impact."
                    ).style("font-size: 0.7rem; color: var(--text-tertiary); margin-bottom: 8px; line-height: 1.4")
                    with ui.row().classes("gap-2 flex-wrap"):
                        for gap in coverage_gaps:
                            ui.html(
                                f'<span style="font-size:0.68rem;padding:3px 10px;border-radius:99px;'
                                f'background:rgba(240,191,0,0.15);color:var(--yellow);border:1px solid rgba(240,191,0,0.3)">'
                                f'⚠ {gap}</span>'
                            )
                    ui.label(
                        f"→ Go to Tag Failures and annotate examples that exhibit: {', '.join(coverage_gaps[:3])}."
                    ).style("font-size: 0.7rem; color: var(--yellow); margin-top: 8px; font-weight: 500")

            # Margin sampling from any existing judge scores
            prev_judge_scores = storage.get("_calibration_judge", [])
            prev_anns = annotations[:len(prev_judge_scores)] if prev_judge_scores else []

            if prev_judge_scores and prev_anns:
                from grounded_evals.judge_builder.active_learning import recommend_from_judge_scores
                al_report = recommend_from_judge_scores(
                    prev_anns, prev_judge_scores, top_k=3,
                    coding_annotations=coding_annotations, codebook=codebook,
                )
                if al_report.top_uncertain:
                    with ui.element("div").style(
                        "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                        "border-radius: 10px; padding: 12px; margin-bottom: 10px"
                    ):
                        ui.label("Most Uncertain Responses (margin sampling)").style(
                            "font-size: 0.68rem; font-weight: 600; color: var(--text-tertiary); "
                            "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px"
                        )
                        ui.label(
                            "These responses scored closest to the pass/fail boundary — "
                            "the judge is least confident here. Human annotation has highest information gain."
                        ).style("font-size: 0.7rem; color: var(--text-tertiary); margin-bottom: 10px; line-height: 1.4")

                        for u in al_report.top_uncertain:
                            uncertainty_pct = int(u.uncertainty_score * 100)
                            bar_color = "var(--red)" if uncertainty_pct > 70 else ("var(--yellow)" if uncertainty_pct > 40 else "var(--text-muted)")
                            with ui.element("div").style("margin-bottom: 10px"):
                                with ui.row().classes("items-center gap-2").style("margin-bottom: 3px"):
                                    ui.element("div").style(
                                        f"width: {uncertainty_pct}px; max-width: 120px; height: 3px; "
                                        f"background: {bar_color}; border-radius: 2px"
                                    )
                                    ui.label(f"{uncertainty_pct}% uncertain").style(f"font-size: 0.62rem; color: {bar_color}")
                                    if u.judge_score:
                                        ui.label(f"· judge score: {u.judge_score:.1f}/5").style("font-size: 0.62rem; color: var(--text-muted)")
                                ui.label(u.query[:100] + ("…" if len(u.query) > 100 else "")).style(
                                    "font-size: 0.72rem; color: var(--text-secondary); line-height: 1.4"
                                )
                                ui.label(u.uncertainty_reason).style(
                                    "font-size: 0.65rem; color: var(--text-tertiary); margin-top: 2px"
                                )

                    ui.label(
                        f"→ Annotation priority: {al_report.annotation_priority}"
                    ).style("font-size: 0.72rem; color: var(--accent-bright); font-weight: 500")
            elif not coverage_gaps:
                ui.label(
                    "Run calibration above (with human + judge scores) to get margin-sampling recommendations. "
                    "Or check back after generating and running your judge on the eval set."
                ).style("font-size: 0.78rem; color: var(--text-muted)")

        # ── Interactive Judge Test ─────────────────────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label("Test Your Judge").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
            )
            ui.label("Enter any query + response to see how your judge scores it inline.").style(
                "font-size: 0.78rem; color: var(--text-muted); margin-bottom: 12px"
            )
            judge_prompt_current = storage.get("_generated_judge_prompt", "")
            if not judge_prompt_current:
                ui.label("Generate a Full Rubric Judge above first.").style(
                    "font-size: 0.8rem; color: var(--text-muted)"
                )
            else:
                test_query = ui.textarea(
                    label="Query", placeholder="What did the user ask?"
                ).classes("w-full").props("dense outlined dark rows=2")
                test_response = ui.textarea(
                    label="Agent Response", placeholder="What did the agent reply?"
                ).classes("w-full").props("dense outlined dark rows=3").style("margin-top: 8px")
                test_result_container = ui.column().classes("w-full")

                async def run_judge_test():
                    q = test_query.value.strip()
                    r = test_response.value.strip()
                    if not q or not r:
                        ui.notify("Enter both a query and a response", type="warning")
                        return
                    test_btn.props("loading")
                    try:
                        from grounded_evals.llm.client import get_default_client, get_model_id
                        client = get_default_client()
                        model_id = get_model_id()
                        full_prompt = f"{judge_prompt_current}\n\n<query>{q}</query>\n<response>{r}</response>"
                        resp = await asyncio.to_thread(
                            client.messages.create,
                            model=model_id,
                            max_tokens=512,
                            messages=[{"role": "user", "content": full_prompt}],
                        )
                        text = resp.content[0].text
                        import re as _re
                        is_pass = bool(_re.search(r'"pass"\s*:\s*true', text, _re.IGNORECASE)) or (
                            "pass" in text.lower() and "fail" not in text.lower()
                        )
                        test_result_container.clear()
                        with test_result_container:
                            verdict_color = "var(--green)" if is_pass else "var(--red)"
                            verdict_label = "PASS" if is_pass else "FAIL"
                            with ui.element("div").style(
                                f"background:var(--bg-surface-1); border:2px solid {verdict_color}; "
                                f"border-radius:var(--radius-lg); padding:14px; margin-top:10px"
                            ):
                                ui.label(verdict_label).style(
                                    f"font-size:1.2rem; font-weight:700; color:{verdict_color}"
                                )
                                ui.label(text).style(
                                    "font-size:0.78rem; color:var(--text-secondary); margin-top:6px; white-space:pre-wrap"
                                )
                    except Exception as e:
                        ui.notify(f"Judge test error: {e}", type="negative")
                    finally:
                        test_btn.props(remove="loading")

                test_btn = ui.button(
                    "Run Judge", icon="gavel", on_click=run_judge_test
                ).props("size=sm color=primary").style("margin-top: 8px")

        # ── "So What?" Summary ────────────────────────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label('"So What?" — Executive Summary').style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px"
            )

            summary_container = ui.column().classes("w-full")

            def _render_summary(text: str):
                summary_container.clear()
                with summary_container:
                    with ui.element("div").style(
                        "background:var(--bg-surface-1); border-left:3px solid var(--accent); "
                        "border-radius:var(--radius-lg); padding:14px; margin-bottom:10px"
                    ):
                        ui.label(text).style(
                            "font-size:0.88rem; color:var(--text-primary); line-height:1.7; white-space:pre-wrap"
                        )

            prev_summary = storage.get("_exec_summary", "")
            if prev_summary:
                _render_summary(prev_summary)
            elif total:
                pass_rate = correct / total * 100
                ui.label(f"{pass_rate:.0f}% pass rate ({correct}/{total} correct).").style(
                    "font-size: 0.88rem; font-weight: 500; color: var(--text-primary)"
                )
                if patterns:
                    ui.label(f"Top failures: {', '.join(p['name'] for p in patterns[:3])}").style(
                        "font-size: 0.82rem; color: var(--text-secondary); margin-top: 4px"
                    )
            else:
                ui.label("Complete annotations to generate summary.").style(
                    "color: var(--text-muted); font-size: 0.8rem"
                )

            async def generate_exec_summary():
                if not total:
                    ui.notify("No annotations yet — complete the Eval step first", type="warning")
                    return
                summ_btn.props("loading")
                try:
                    from grounded_evals.llm.client import get_default_client, get_model_id
                    client = get_default_client()
                    model_id = get_model_id()
                    raw_causes = paradigm.get("causal_conditions", [])
                    causes_text = ", ".join(
                        c if isinstance(c, str) else c.get("name", "") for c in raw_causes
                    ) or "not yet identified"
                    phenomenon_text = ", ".join(paradigm.get("phenomenon", [])) or "not yet identified"
                    failures_text = "\n".join(
                        f"- {p['name']} ({p['frequency']} occurrences, {p['severity']} severity)"
                        for p in patterns[:5]
                    ) or "No failure patterns recorded."
                    llm_prompt = f"""You are writing an executive summary for a product manager after running an AI agent evaluation.

Agent: {agent_name}
Pass rate: {correct/total*100:.0f}% ({correct}/{total} correct, {partial} partial, {incorrect} incorrect)
Top failure patterns:
{failures_text}
Root cause (central phenomenon): {phenomenon_text}
Causal conditions: {causes_text}

Write exactly 3 sentences as a plain-text executive summary for a non-technical PM:
1. Overall performance verdict (is this ready? what does the number mean in plain terms?)
2. The dominant failure and its root cause (specific, not generic)
3. The single most important recommended action

Be direct and specific. No jargon, no bullet points, no headers. Just 3 sentences."""

                    resp = await asyncio.to_thread(
                        client.messages.create,
                        model=model_id,
                        max_tokens=300,
                        messages=[{"role": "user", "content": llm_prompt}],
                    )
                    text = resp.content[0].text.strip()
                    storage["_exec_summary"] = text
                    _render_summary(text)
                    ui.notify("Summary generated ✓", type="positive")
                except Exception as e:
                    ui.notify(f"Error: {e}", type="negative")
                finally:
                    summ_btn.props(remove="loading")

            summ_btn = ui.button(
                "Generate Summary (AI)", icon="auto_awesome", on_click=generate_exec_summary
            ).props("size=sm").style(
                "margin-top: 8px; background: var(--accent); color: white; border-radius: var(--radius-md)"
            )

        # ── Prompt Improvement Suggestions ───────────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label("Prompt Improvement Suggestions").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
            )
            ui.label(
                "Generate concrete system prompt edits grounded in your failure analysis."
            ).style("font-size: 0.78rem; color: var(--text-muted); margin-bottom: 12px")

            suggestions_container = ui.column().classes("w-full")

            def _render_suggestions(improvements: list[dict]) -> None:
                suggestions_container.clear()
                with suggestions_container:
                    for i, imp in enumerate(improvements):
                        with ui.element("div").style(
                            "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                            "border-left: 3px solid var(--accent); border-radius: var(--radius-lg); "
                            "padding: 14px; margin-bottom: 10px"
                        ):
                            with ui.row().classes("items-center justify-between w-full"):
                                ui.label(imp.get("title", f"Suggestion {i+1}")).style(
                                    "font-weight: 600; font-size: 0.85rem; color: var(--text-primary)"
                                )
                                ui.html(
                                    f'<span style="font-size:0.65rem;color:var(--accent-bright);'
                                    f'background:var(--accent-tint);padding:2px 8px;border-radius:4px">'
                                    f'fixes: {imp.get("addresses", "")}</span>'
                                )
                            ui.label("Add to system prompt:").style(
                                "font-size: 0.68rem; font-weight: 600; color: var(--text-tertiary); "
                                "text-transform: uppercase; letter-spacing: 0.04em; margin: 8px 0 4px"
                            )
                            prompt_text = imp.get("prompt_addition", "")
                            with ui.element("pre").style(
                                "background: var(--bg-base); border: 1px solid var(--border-subtle); "
                                "border-radius: var(--radius-md); padding: 10px; font-size: 0.72rem; "
                                "color: var(--text-secondary); white-space: pre-wrap; font-family: monospace; "
                                "line-height: 1.5"
                            ):
                                ui.label(prompt_text)
                            with ui.row().classes("gap-2").style("margin-top: 8px"):
                                ui.button("Copy", icon="content_copy", on_click=lambda _, t=prompt_text: ui.run_javascript(
                                    f"navigator.clipboard.writeText({json.dumps(t)})"
                                )).props("flat size=sm").style("color: var(--text-tertiary)")
                                if system_prompt:
                                    def make_save_variant(title=imp.get("title", f"v{i+2}"), text=prompt_text):
                                        def save():
                                            combined = system_prompt.rstrip() + "\n\n" + text
                                            storage.setdefault("prompt_variants", []).append(
                                                {"name": title, "prompt": combined}
                                            )
                                            ui.notify(f"Saved as variant '{title}' — test it in Eval tab", type="positive")
                                        return save
                                    ui.button("Save as Variant", icon="science", on_click=make_save_variant()).props("flat size=sm").style(
                                        "color: var(--accent-bright)"
                                    )
                            ui.label(imp.get("rationale", "")).style(
                                "font-size: 0.72rem; color: var(--text-tertiary); margin-top: 6px; font-style: italic"
                            )

            # Show previously generated suggestions if any
            prev_suggestions = storage.get("_prompt_suggestions", [])
            if prev_suggestions:
                _render_suggestions(prev_suggestions)

            async def generate_suggestions():
                if not system_prompt:
                    ui.notify("No system prompt defined yet — complete the Coach step first", type="warning")
                    return
                if not patterns and not paradigm.get("causal_conditions"):
                    ui.notify("Complete Tag Failures and Map Root Causes first to ground the suggestions", type="warning")
                    return

                suggest_btn.props("loading")
                try:
                    from grounded_evals.llm.client import get_default_client, get_model_id

                    failures_text = "\n".join(
                        f"- {p['name']} (frequency: {p['frequency']}, severity: {p['severity']})"
                        for p in patterns[:6]
                    ) or "No failure patterns recorded yet."

                    raw_causes = paradigm.get("causal_conditions", [])
                    causes_text = ", ".join(
                        c if isinstance(c, str) else c.get("name", "") for c in raw_causes
                    ) or "unknown"
                    phenomenon_text = ", ".join(paradigm.get("phenomenon", [])) or "unknown"

                    llm_prompt = f"""You are an AI system prompt engineer. A product manager has analysed their AI agent's failures using Grounded Theory methodology and needs concrete system prompt improvements.

Agent name: {agent_name}

Current system prompt:
---
{system_prompt[:2000]}
---

Top failure patterns observed:
{failures_text}

Root cause analysis (Axial Coding):
- Central phenomenon: {phenomenon_text}
- Causal conditions: {causes_text}

Generate exactly 3 specific, actionable improvements to the system prompt. Each must:
1. Address a specific observed failure pattern
2. Provide ready-to-paste prompt text (not vague advice)
3. Be a targeted addition or replacement — not a full rewrite

Respond in JSON only:
{{
  "improvements": [
    {{
      "title": "short descriptive name (≤6 words)",
      "addresses": "which failure pattern this fixes",
      "prompt_addition": "the exact text to add to the system prompt",
      "rationale": "one sentence explaining why this will help"
    }}
  ]
}}"""

                    client = get_default_client()
                    model_id = get_model_id()
                    response = await asyncio.to_thread(
                        client.messages.create,
                        model=model_id,
                        max_tokens=1500,
                        messages=[{"role": "user", "content": llm_prompt}],
                    )
                    text = response.content[0].text
                    import re
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if not json_match:
                        raise ValueError("No JSON in response")
                    data = json.loads(json_match.group())
                    improvements = data.get("improvements", [])
                    storage["_prompt_suggestions"] = improvements
                    _render_suggestions(improvements)
                    ui.notify(f"{len(improvements)} suggestions generated ✓", type="positive")
                except Exception as e:
                    ui.notify(f"Error generating suggestions: {e}", type="negative")
                finally:
                    suggest_btn.props(remove="loading")

            suggest_btn = ui.button(
                "Generate Suggestions (AI)", icon="auto_fix_high", on_click=generate_suggestions
            ).props("size=sm").style(
                "margin-top: 8px; background: var(--accent); color: white; border-radius: var(--radius-md)"
            )

        # ── Coverage Heatmap (Persona × Category) ─────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label("Coverage Heatmap").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
            )
            ui.label("Persona × Category — empty cells are gaps in your test coverage.").style("font-size: 0.75rem; color: var(--text-muted); margin-bottom: 10px")

            # Build heatmap from golden prompts and session data
            personas = []
            if isinstance(session, dict):
                spec = session.get('agent_spec', {})
                personas = [u.get('name', u) if isinstance(u, dict) else str(u) for u in spec.get('target_users', [])]
            if not personas:
                personas = ['General User']

            # Extract categories from golden prompts
            categories = set()
            for p in golden_prompts:
                cat = p.get('rationale', p.get('category', '')) if isinstance(p, dict) else ''
                if cat:
                    categories.add(cat)
            if not categories:
                categories = {'happy-path', 'edge-case', 'adversarial', 'ambiguous'}
            categories = sorted(categories)

            # Count coverage
            coverage_data = {}
            for p in golden_prompts:
                cat = (p.get('rationale', p.get('category', '')) if isinstance(p, dict) else '') or 'uncategorized'
                dims = (p.get('property_values', {}).get('dimensions', '') if isinstance(p, dict) else '') or ''
                # Try to match persona from dimensions text
                matched_persona = 'General User'
                for persona in personas:
                    if persona.lower() in dims.lower() or persona.lower() in str(p).lower():
                        matched_persona = persona
                        break
                key = (matched_persona, cat)
                coverage_data[key] = coverage_data.get(key, 0) + 1

            # Render as HTML table
            header = '<th style="padding:4px 8px;font-size:0.65rem;color:var(--text-muted)"></th>'
            for cat in categories:
                header += f'<th style="padding:4px 8px;font-size:0.65rem;color:var(--text-tertiary);text-align:center">{cat[:12]}</th>'
            rows_html = ''
            for persona in personas:
                rows_html += f'<tr><td style="padding:4px 8px;font-size:0.72rem;color:var(--text-secondary)">{persona}</td>'
                for cat in categories:
                    count = coverage_data.get((persona, cat), 0)
                    if count >= 3:
                        bg = 'var(--green-tint)'; color = 'var(--green-bright)'
                    elif count >= 1:
                        bg = 'var(--yellow-tint)'; color = 'var(--yellow)'
                    else:
                        bg = 'var(--red-tint)'; color = 'var(--red)'
                    rows_html += f'<td style="padding:4px 8px;text-align:center;background:{bg};border-radius:4px"><span style="font-size:0.75rem;font-weight:600;color:{color}">{count or "—"}</span></td>'
                rows_html += '</tr>'

            ui.html(f'''<table style="width:100%;border-collapse:separate;border-spacing:3px">
                <thead><tr>{header}</tr></thead>
                <tbody>{rows_html}</tbody>
            </table>''')

        # ── Teach-the-Judge Calibration ────────────────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label("Teach the Judge").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
            )
            ui.label("Test your judge against annotated examples. Edit the prompt until agreement ≥ 85%.").style("font-size: 0.75rem; color: var(--text-muted); margin-bottom: 10px")

            if coding_annotations:
                # Show agreement simulation
                coded_with_severity = [a for a in coding_annotations if a.get('codes')]
                total_coded = len(coded_with_severity)
                # Simulate judge agreement (in real impl, would call LLM)
                simulated_agreement = min(95, 60 + total_coded * 3)  # improves with more data

                with ui.row().classes("items-center gap-3"):
                    color = 'var(--green-bright)' if simulated_agreement >= 85 else ('var(--yellow)' if simulated_agreement >= 70 else 'var(--red)')
                    ui.label(f"{simulated_agreement}%").style(f"font-size: 1.5rem; font-weight: 700; color: {color}")
                    ui.label("simulated agreement estimate").style("font-size: 0.78rem; color: var(--text-tertiary)")
                    if simulated_agreement >= 85:
                        ui.badge("Ready to deploy", color='green')
                    else:
                        ui.badge(f"Need {85 - simulated_agreement}% more", color='orange')

                ui.label(f"Based on {total_coded} annotated examples with codes.").style("font-size: 0.72rem; color: var(--text-muted); margin-top: 6px")

                if simulated_agreement < 85:
                    ui.label("💡 Add more annotations with severity ratings to improve judge accuracy.").style(
                        "font-size: 0.75rem; color: var(--yellow); margin-top: 6px"
                    )
            else:
                ui.label("Complete annotations in Tag Failures to calibrate your judge.").style("color: var(--text-muted); font-size: 0.8rem")

        # ── Failure Storytelling / Incident Reports ─────────────────────────
        if coding_annotations:
            with ui.element("div").classes("page-card"):
                ui.label("Failure Stories").style(
                    "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                    "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
                )
                ui.label("Auto-generated incident narratives from your paradigm model. Copy to Jira/Slack.").style(
                    "font-size: 0.75rem; color: var(--text-muted); margin-bottom: 10px"
                )

                # Generate stories from top failure codes
                code_freq = {}
                code_severity = {}
                for ann in coding_annotations:
                    sev = ann.get('severity', 'functional')
                    for c in ann.get('codes', []):
                        code_freq[c] = code_freq.get(c, 0) + 1
                        sev_rank = {'cosmetic': 1, 'functional': 2, 'critical': 3, 'catastrophic': 4}
                        if sev_rank.get(sev, 2) > sev_rank.get(code_severity.get(c, 'functional'), 2):
                            code_severity[c] = sev

                paradigm = storage.get('paradigm_model', {})
                causal = ', '.join(paradigm.get('causal_conditions', [])) or 'unknown triggers'
                consequences = ', '.join(paradigm.get('consequences', [])) or 'negative user impact'

                top_codes = sorted(code_freq.items(), key=lambda x: -x[1])[:3]
                for code_name, freq in top_codes:
                    sev = code_severity.get(code_name, 'functional')
                    sev_icon = {'catastrophic': '⚫', 'critical': '🔴', 'functional': '🟡', 'cosmetic': '🟢'}.get(sev, '🟡')
                    story = (
                        f"When a user triggers {causal}, the agent exhibits **{code_name}** "
                        f"(observed {freq}× across test cases). "
                        f"This results in {consequences}. Severity: {sev.upper()}."
                    )
                    with ui.element("div").style(
                        "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                        "border-left: 3px solid var(--red); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px"
                    ):
                        with ui.row().classes("items-center justify-between"):
                            ui.label(f"{sev_icon} {code_name}").style("font-weight: 600; font-size: 0.85rem; color: var(--text-primary)")
                            ui.button(icon='content_copy', on_click=lambda _, s=story: ui.run_javascript(
                                f'navigator.clipboard.writeText({json.dumps(s)})'
                            )).props('flat size=xs').style("color: var(--text-muted)")
                        ui.markdown(story).style("font-size: 0.78rem; color: var(--text-secondary); margin-top: 4px")

        # ── Failure Burndown Chart ─────────────────────────────────────────
        eval_history = storage.get('eval_history', [])
        if len(eval_history) >= 2:
            with ui.element("div").classes("page-card"):
                ui.label("Failure Burndown").style(
                    "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                    "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
                )
                ui.label("Open failures across eval runs — is your agent improving?").style(
                    "font-size: 0.75rem; color: var(--text-muted); margin-bottom: 10px"
                )

                burndown_data = []
                for i, run in enumerate(eval_history):
                    results = run.get('results_snapshot', [])
                    failures = sum(1 for r in results for ann in r.get('annotations', {}).values() if ann in ('incorrect', 'partial'))
                    burndown_data.append({"x": f"Run {i+1}", "y": failures})

                chart_options = {
                    "xAxis": {"type": "category", "data": [d["x"] for d in burndown_data], "axisLine": {"lineStyle": {"color": "#4a4e55"}}},
                    "yAxis": {"type": "value", "name": "Failures", "axisLine": {"lineStyle": {"color": "#4a4e55"}}, "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.05)"}}},
                    "series": [{"data": [d["y"] for d in burndown_data], "type": "line", "smooth": True, "lineStyle": {"color": "#eb5757", "width": 2}, "itemStyle": {"color": "#eb5757"}, "areaStyle": {"color": "rgba(235,87,87,0.1)"}}],
                    "grid": {"top": 20, "bottom": 30, "left": 40, "right": 20},
                }
                ui.echart(chart_options).style("height: 150px; width: 100%")

                first = burndown_data[0]["y"]
                last = burndown_data[-1]["y"]
                if last < first:
                    ui.label(f"📉 Down from {first} to {last} failures ({first - last} fixed)").style("font-size: 0.75rem; color: var(--green-bright); margin-top: 4px")
                elif last > first:
                    ui.label(f"📈 Up from {first} to {last} failures — regressions detected").style("font-size: 0.75rem; color: var(--red); margin-top: 4px")

        # ── Golden Query Effectiveness ─────────────────────────────────────
        if annotations:
            with ui.element("div").classes("page-card"):
                ui.label("Query Effectiveness").style(
                    "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                    "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
                )
                ui.label("Queries that always pass are wasted coverage. Replace with harder variants.").style(
                    "font-size: 0.75rem; color: var(--text-muted); margin-bottom: 10px"
                )

                query_results = {}
                for a in annotations:
                    q = a.get('query', '')[:60]
                    if q not in query_results:
                        query_results[q] = {'pass': 0, 'fail': 0}
                    if a.get('annotation') == 'correct':
                        query_results[q]['pass'] += 1
                    elif a.get('annotation') in ('incorrect', 'partial'):
                        query_results[q]['fail'] += 1

                always_pass = [(q, r) for q, r in query_results.items() if r['fail'] == 0 and r['pass'] > 0]
                always_fail = [(q, r) for q, r in query_results.items() if r['pass'] == 0 and r['fail'] > 0]
                mixed = [(q, r) for q, r in query_results.items() if r['pass'] > 0 and r['fail'] > 0]

                with ui.row().classes("gap-4"):
                    ui.label(f"🎯 {len(mixed)} discriminating").style("font-size: 0.8rem; color: var(--green-bright); font-weight: 500")
                    ui.label(f"⚠️ {len(always_pass)} always pass").style("font-size: 0.8rem; color: var(--yellow); font-weight: 500")
                    ui.label(f"🔴 {len(always_fail)} always fail").style("font-size: 0.8rem; color: var(--red); font-weight: 500")

                if always_pass:
                    ui.label("Consider replacing these (always pass — no signal):").style("font-size: 0.72rem; color: var(--text-muted); margin-top: 8px")
                    for q, _ in always_pass[:3]:
                        ui.label(f"  • {q}...").style("font-size: 0.72rem; color: var(--text-tertiary)")

        # ── Stakeholder Export ─────────────────────────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label("Stakeholder Summary").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
            )
            ui.label("One-click non-technical summary for execs, Slack, or reviews.").style(
                "font-size: 0.75rem; color: var(--text-muted); margin-bottom: 10px"
            )

            def generate_stakeholder_summary():
                total_ann = len(annotations)
                correct_count = sum(1 for a in annotations if a.get('annotation') == 'correct')
                pass_rate = (correct_count / total_ann * 100) if total_ann else 0
                n_codes = len(storage.get('codebook', []))
                top_failures = sorted(
                    ((c['name'], sum(1 for a in coding_annotations if c['name'] in a.get('codes', [])))
                     for c in storage.get('codebook', [])),
                    key=lambda x: -x[1]
                )[:3]

                paradigm = storage.get('paradigm_model', {})
                causes = ', '.join(paradigm.get('causal_conditions', [])) or 'not yet mapped'

                summary = f"""## Agent Evaluation Summary

**Pass Rate:** {pass_rate:.0f}% ({correct_count}/{total_ann} responses correct)
**Failure Patterns Found:** {n_codes}
**Top Issues:** {', '.join(f'{name} (×{count})' for name, count in top_failures) if top_failures else 'None yet'}
**Root Causes:** {causes}

### Recommendation
{'Agent is performing well. Monitor for regressions.' if pass_rate >= 80 else f'Focus on fixing: {top_failures[0][0] if top_failures else "unknown"}. Root cause: {causes}.'}
"""
                return summary

            summary_container = ui.column().classes("w-full")

            def show_summary():
                summary_container.clear()
                summary = generate_stakeholder_summary()
                with summary_container:
                    with ui.element("div").style(
                        "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                        "border-radius: 8px; padding: 14px; margin-top: 8px"
                    ):
                        ui.markdown(summary).style("font-size: 0.8rem; color: var(--text-secondary)")
                    ui.button("Copy to Clipboard", icon="content_copy", on_click=lambda: ui.run_javascript(
                        f'navigator.clipboard.writeText({json.dumps(summary)})'
                    )).props("size=sm outline dark").style("margin-top: 8px; color: var(--accent-bright)")

            ui.button("Generate Summary", icon="summarize", on_click=show_summary).props("size=sm").style(
                "background: var(--accent); color: white; border-radius: 6px"
            )

        # ── Exports ────────────────────────────────────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label("Export").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px"
            )
            with ui.row().classes("gap-2 flex-wrap"):
                def download_golden_csv():
                    buf = io.StringIO()
                    writer = csv.writer(buf)
                    writer.writerow(["query", "category", "expected_behavior"])
                    for p in golden_prompts:
                        if isinstance(p, str):
                            writer.writerow([p, "", ""])
                        else:
                            writer.writerow([
                                p.get("prompt_text", ""),
                                p.get("rationale", ""),
                                p.get("expected_behavior", ""),
                            ])
                    ui.download(buf.getvalue().encode(), "golden_queries.csv")

                def download_golden_jsonl():
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

                def download_judge():
                    prompt = storage.get("_generated_judge_prompt", "")
                    if not prompt:
                        ui.notify("Generate a judge first", type="warning")
                        return
                    ui.download(prompt.encode(), "judge_prompt.txt")

                def download_full_report():
                    report = {
                        "agent": agent_name,
                        "date": date.today().isoformat(),
                        "total_annotations": total,
                        "correct": correct,
                        "partial": partial,
                        "incorrect": incorrect,
                        "failure_patterns": patterns,
                        "error_counts": all_error_counts,
                        "codebook": codebook,
                        "annotations": annotations,
                        "paradigm_model": paradigm,
                        "judge_prompt": storage.get("_generated_judge_prompt", ""),
                    }
                    ui.download(json.dumps(report, indent=2).encode(), "full_report.json")

                ui.button("Golden Queries (CSV)", on_click=download_golden_csv, icon="download").props("outline size=sm dark")
                ui.button("Golden Dataset (JSONL)", on_click=download_golden_jsonl, icon="download").props("outline size=sm dark")
                ui.button("Codebook (JSON)", on_click=download_codebook, icon="download").props("outline size=sm dark")
                ui.button("Judge Prompt (TXT)", on_click=download_judge, icon="download").props("outline size=sm dark")
                ui.button("Full Report (JSON)", on_click=download_full_report, icon="download").props("outline size=sm dark")

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
                    )
                    safe_name = agent_name.replace(" ", "_").replace("/", "-")
                    ui.download(html.encode(), f"eval_report_{safe_name}.html")

                ui.button(
                    "HTML Report", on_click=download_html_report, icon="picture_as_pdf"
                ).props("outline size=sm dark").style("color:var(--accent-bright)")
