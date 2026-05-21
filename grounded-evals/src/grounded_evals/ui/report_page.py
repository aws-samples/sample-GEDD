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

        # ── Failure Patterns (from Open Coding) ───────────────────────────
        with ui.element("div").classes("page-card"):
            ui.label("Failure Patterns").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px"
            )
            if patterns:
                columns = [
                    {"name": "name", "label": "Pattern", "field": "name", "align": "left"},
                    {"name": "frequency", "label": "Freq", "field": "frequency"},
                    {"name": "severity", "label": "Severity", "field": "severity"},
                    {"name": "definition", "label": "Definition", "field": "definition", "align": "left"},
                ]
                ui.table(columns=columns, rows=patterns, row_key="name").classes("w-full").props("dark dense flat")
            else:
                ui.label("Complete the Tag Failures step to see patterns here.").style(
                    "color: var(--text-muted); font-size: 0.8rem"
                )

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
            ui.label("LLM-as-Judge Generation").style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px"
            )
            ui.label("Generate a grounded judge prompt from your error analysis.").style(
                "font-size: 0.78rem; color: var(--text-muted); margin-bottom: 12px"
            )

            judge_output_container = ui.column().classes("w-full")

            def _render_judge_prompts(judge_prompt: str | None = None):
                judge_output_container.clear()
                with judge_output_container:
                    # Binary judges from paradigm model (always shown)
                    phenomena = paradigm.get("phenomenon", [])
                    targets = phenomena if phenomena else [c["name"] for c in codebook[:5]]
                    causal = ", ".join(paradigm.get("causal_conditions", [])) or "Unknown"
                    strategies_text = ", ".join(paradigm.get("strategies", [])) or "Unknown"
                    consequences_text = ", ".join(paradigm.get("consequences", [])) or "Unknown"

                    if targets:
                        ui.label("Binary Judges (from Paradigm Model)").style(
                            "font-size: 0.72rem; font-weight: 600; color: var(--text-tertiary); "
                            "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px"
                        )
                        for target in targets:
                            prompt = (
                                f"You are evaluating whether a response exhibits {target.upper()}.\n\n"
                                f"Triggered by: {causal}\n"
                                f"Manifests as: {strategies_text}\n"
                                f"User impact: {consequences_text}\n\n"
                                f"<response>{{response}}</response>\n\n"
                                f"Think step by step. Score TRUE if the response exhibits this pattern. Score FALSE otherwise."
                            )
                            with ui.element("div").style(
                                "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                                "border-radius: var(--radius-lg); padding: 12px; margin-bottom: 10px"
                            ):
                                with ui.row().classes("items-center justify-between w-full"):
                                    ui.label(f"Judge: {target}").style(
                                        "font-weight: 600; font-size: 0.85rem; color: var(--text-primary)"
                                    )
                                    ui.button("Copy", icon="content_copy", on_click=lambda _, p=prompt: ui.run_javascript(
                                        f"navigator.clipboard.writeText({json.dumps(p)})"
                                    )).props("flat size=sm").style("color: var(--text-tertiary)")
                                with ui.element("pre").style(
                                    "background: var(--bg-base); border: 1px solid var(--border-subtle); "
                                    "border-radius: var(--radius-md); padding: 10px; margin-top: 8px; "
                                    "font-size: 0.7rem; color: var(--text-secondary); white-space: pre-wrap; "
                                    "line-height: 1.5; max-height: 180px; overflow-y: auto; font-family: monospace"
                                ):
                                    ui.label(prompt)

                    # Full rubric-based judge (if generated)
                    if judge_prompt:
                        ui.separator().style("opacity: 0.1; margin: 16px 0")
                        ui.label("Full Rubric Judge (grounded in error analysis)").style(
                            "font-size: 0.72rem; font-weight: 600; color: var(--green-bright); "
                            "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px"
                        )
                        with ui.element("div").style(
                            "background: var(--bg-surface-1); border: 1px solid var(--green); "
                            "border-radius: var(--radius-lg); padding: 12px"
                        ):
                            with ui.row().classes("items-center justify-between w-full"):
                                ui.label("Multi-criterion rubric judge").style(
                                    "font-weight: 600; font-size: 0.85rem; color: var(--text-primary)"
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

            _render_judge_prompts(storage.get("_generated_judge_prompt"))

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
                    ui.notify("Mapping errors to dimensions...", type="info")

                    codes = [Code(label=c["name"], definition=c.get("definition", ""), code_type=CodeType.DESCRIPTIVE) for c in codebook]
                    mappings = await asyncio.to_thread(map_errors_to_categories, codes)
                    if not mappings:
                        ui.notify("Could not map error codes — check LLM connectivity", type="warning")
                        gen_btn.props(remove="loading")
                        return

                    rubric = generate_rubric(mappings)
                    judge_prompt = generate_judge_prompt(rubric, agent_name, agent_description)
                    storage["_generated_judge_prompt"] = judge_prompt

                    ui.notify("Full judge prompt generated ✓", type="positive")
                    _render_judge_prompts(judge_prompt)
                except Exception as e:
                    ui.notify(f"Error generating judge: {e}", type="negative")
                finally:
                    gen_btn.props(remove="loading")

            gen_btn = ui.button(
                "Generate Full Rubric Judge (AI)", icon="auto_fix_high", on_click=generate_full_judge
            ).props("size=sm").style(
                "margin-top: 12px; background: var(--accent); color: white; border-radius: var(--radius-md)"
            )

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
                                color = "var(--green-bright)" if result.agreement_score >= 0.85 else (
                                    "var(--yellow)" if result.agreement_score >= 0.7 else "var(--red)"
                                )
                                with ui.element("div").style(
                                    f"background: var(--bg-surface-2); border: 1px solid {color}; "
                                    f"border-radius: var(--radius-lg); padding: 14px; margin-top: 12px"
                                ):
                                    ui.label(f"Agreement: {result.agreement_score:.0%}").style(
                                        f"font-size: 1.1rem; font-weight: 700; color: {color}"
                                    )
                                    ui.label(result.recommendation).style(
                                        "font-size: 0.82rem; color: var(--text-secondary); margin-top: 4px"
                                    )
                                    if result.disagreements:
                                        ui.label("Disagreements:").style(
                                            "font-size: 0.72rem; color: var(--text-tertiary); margin-top: 8px; font-weight: 600"
                                        )
                                        for d in result.disagreements[:5]:
                                            ui.label(f"• {d}").style("font-size: 0.72rem; color: var(--red)")

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
                                color = "var(--green-bright)" if result.agreement_score >= 0.85 else (
                                    "var(--yellow)" if result.agreement_score >= 0.7 else "var(--red)"
                                )
                                with ui.element("div").style(
                                    f"background: var(--bg-surface-2); border: 1px solid {color}; "
                                    f"border-radius: var(--radius-lg); padding: 14px; margin-top: 12px"
                                ):
                                    ui.label(f"Last calibration: {result.agreement_score:.0%} agreement").style(
                                        f"font-size: 0.9rem; font-weight: 600; color: {color}"
                                    )
                                    ui.label(result.recommendation).style(
                                        "font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px"
                                    )
                        except Exception:
                            pass

            render_calibration()

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
                        "error_counts": all_error_counts if "all_error_counts" in dir() else error_counts,
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
