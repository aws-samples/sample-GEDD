"""Build Judge — step-by-step LLM-as-a-Judge wizard grounded in root cause analysis."""

import asyncio
import json

from nicegui import app, ui

from grounded_evals.ui.layout import page_layout

EVAL_DIMENSIONS = [
    ("accuracy",       "Accuracy",          "Are facts, figures, and claims correct?",          "var(--red)"),
    ("completeness",   "Completeness",       "Does the response address all parts of the query?","var(--yellow)"),
    ("safety",         "Safety",             "Does it avoid harmful, dangerous, or toxic output?","var(--red)"),
    ("scope",          "Scope Adherence",    "Does it stay within the agent's intended role?",   "var(--blue)"),
    ("tone",           "Tone / Style",       "Is the tone appropriate for the target audience?", "var(--text-secondary)"),
    ("instructions",   "Instruction Follow", "Does it follow the system-prompt rules?",          "var(--accent-bright)"),
    ("completeness2",  "Conciseness",        "Is the response appropriately concise (not padded)?","var(--text-secondary)"),
    ("bias",           "Bias / Fairness",    "Does it avoid discrimination or unfair framing?",  "var(--yellow)"),
]

SEVERITY_LEVELS = {
    "catastrophic": {"label": "Catastrophic", "color": "var(--red)",       "score": 4},
    "critical":     {"label": "Critical",     "color": "var(--red)",       "score": 3},
    "functional":   {"label": "Functional",   "color": "var(--yellow)",    "score": 2},
    "cosmetic":     {"label": "Cosmetic",     "color": "var(--green-bright)", "score": 1},
}


def _get(key, default=None):
    return app.storage.user.get(key, default)


def _set(key, value):
    app.storage.user[key] = value


def _init_state():
    if "_jb_step" not in app.storage.user:
        app.storage.user["_jb_step"] = 1
    if "_jb_mappings" not in app.storage.user:
        app.storage.user["_jb_mappings"] = {}
    if "_jb_rubrics" not in app.storage.user:
        app.storage.user["_jb_rubrics"] = {}
    if "_jb_hard_fails" not in app.storage.user:
        app.storage.user["_jb_hard_fails"] = []
    if "_jb_selected_dims" not in app.storage.user:
        app.storage.user["_jb_selected_dims"] = []
    if "_jb_mode" not in app.storage.user:
        app.storage.user["_jb_mode"] = "geval"


def _failure_summary():
    codebook = _get("codebook", [])
    coding_annotations = _get("coding_annotations", [])
    from collections import Counter
    freq: Counter = Counter()
    for ann in coding_annotations:
        for c in ann.get("codes", []):
            freq[c] += 1
    result = []
    for code in codebook:
        name = code["name"]
        count = freq.get(name, 0)
        total = max(1, sum(freq.values()))
        pct = count / total
        severity = "high" if pct >= 0.4 else ("medium" if pct >= 0.2 else "low")
        result.append({"name": name, "definition": code.get("definition", ""), "frequency": count, "severity": severity})
    return sorted(result, key=lambda x: x["frequency"], reverse=True)


@ui.page("/judge")
def judge_builder_page():
    _init_state()
    page_layout("Build Judge")

    with ui.column().classes("w-full max-w-4xl mx-auto").style("padding: 1.5rem; gap: 1rem"):

        # ── Page header ──────────────────────────────────────────────────────
        ui.html(
            '<div style="margin-bottom: 4px">'
            '<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;color:var(--text-tertiary);text-transform:uppercase;margin-bottom:4px">5. BUILD JUDGE</div>'
            '<div style="font-size:1.1rem;font-weight:700;color:var(--text-primary);margin-bottom:2px">LLM-as-a-Judge Builder</div>'
            '<div style="font-size:0.82rem;color:var(--text-secondary)">Turn your root cause findings into a production-ready evaluation rubric — step by step.</div>'
            '</div>'
        )

        # ── Stepper dots ─────────────────────────────────────────────────────
        STEPS = ["Review Failures", "Map Dimensions", "Rubric & Weights", "Hard-Fail Rules", "Generate & Export"]
        step_container = ui.element("div")

        def refresh_stepper():
            step_container.clear()
            cur = _get("_jb_step", 1)
            with step_container:
                ui.html(
                    '<div style="display:flex;justify-content:space-between;align-items:center;'
                    'background:var(--bg-surface-2);border:1px solid var(--border-subtle);'
                    'border-radius:10px;padding:10px 16px;margin-bottom:1rem">'
                    + "".join(
                        f'<div style="display:flex;flex-direction:column;align-items:center;flex:1">'
                        f'<div style="width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;'
                        f'font-size:0.68rem;font-weight:700;'
                        f'background:{"var(--accent)" if i+1==cur else ("var(--green-tint)" if i+1<cur else "var(--bg-hover)")};'
                        f'color:{"white" if i+1==cur else ("var(--green-bright)" if i+1<cur else "var(--text-muted)")};'
                        f'box-shadow:{"0 0 10px rgba(94,106,210,0.4)" if i+1==cur else "none"}">'
                        f'{"✓" if i+1<cur else str(i+1)}</div>'
                        f'<div style="font-size:0.58rem;color:{"var(--accent-bright)" if i+1==cur else ("var(--green-bright)" if i+1<cur else "var(--text-muted)")};'
                        f'margin-top:4px;font-weight:{"600" if i+1==cur else "400"};text-align:center">{s}</div>'
                        f'</div>'
                        for i, s in enumerate(STEPS)
                    )
                    + '</div>'
                )

        refresh_stepper()

        # ── Step panels ──────────────────────────────────────────────────────
        panel = ui.column().classes("w-full")

        def render_step():
            panel.clear()
            cur = _get("_jb_step", 1)
            with panel:
                if cur == 1:
                    _step1_review()
                elif cur == 2:
                    _step2_dimensions()
                elif cur == 3:
                    _step3_rubrics()
                elif cur == 4:
                    _step4_hard_fails()
                elif cur == 5:
                    _step5_generate()

        def go_to(step: int):
            _set("_jb_step", step)
            refresh_stepper()
            render_step()

        # ── Step 1: Review Failures ──────────────────────────────────────────
        def _step1_review():
            patterns = _failure_summary()
            paradigm = _get("paradigm_model", {})
            codebook = _get("codebook", [])
            coding_annotations = _get("coding_annotations", [])

            _card_header(
                "Step 1 of 5 — Review Failure Patterns",
                "These are the failure patterns discovered during Open Coding and Axial Coding. "
                "Review them before mapping to evaluation dimensions.",
            )

            if not codebook:
                ui.html(
                    '<div style="padding:16px;background:var(--yellow-tint);border:1px solid rgba(240,191,0,0.2);'
                    'border-radius:10px;font-size:0.82rem;color:var(--text-secondary)">'
                    '⚠️ No failure codes found. Complete the <strong>Tag</strong> and <strong>Root Causes</strong> steps first to build your codebook.'
                    '</div>'
                )
            else:
                # Quick stats bar
                n_codes = len(codebook)
                n_anns = len(coding_annotations)
                phen = paradigm.get("phenomenon", [])
                _stat_row([
                    (str(n_codes), "Error Codes", "var(--accent-bright)"),
                    (str(n_anns), "Tagged Responses", "var(--yellow)"),
                    (str(len(phen)), "Core Phenomena", "var(--green-bright)"),
                ])

                # Paradigm model summary
                if any(paradigm.values()):
                    ui.html('<div style="font-size:0.7rem;font-weight:600;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.04em;margin:12px 0 6px">Paradigm Model</div>')
                    slot_labels = {
                        "phenomenon": ("Core Problem", "var(--accent-bright)"),
                        "causal_conditions": ("Triggered By", "var(--red)"),
                        "context": ("Occurs When", "var(--blue)"),
                        "intervening_conditions": ("Gets Worse If", "var(--yellow)"),
                        "strategies": ("Manifests As", "var(--text-secondary)"),
                        "consequences": ("User Impact", "var(--red)"),
                    }
                    with ui.row().classes("flex-wrap gap-2"):
                        for slot, (label, color) in slot_labels.items():
                            codes = paradigm.get(slot, [])
                            if codes:
                                with ui.element("div").style(
                                    f"background:var(--bg-surface-1);border:1px solid var(--border-subtle);"
                                    f"border-left:3px solid {color};border-radius:8px;padding:8px 12px;min-width:160px"
                                ):
                                    ui.html(f'<div style="font-size:0.6rem;font-weight:700;color:{color};text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px">{label}</div>')
                                    for c in codes:
                                        ui.html(f'<span style="font-size:0.72rem;color:var(--text-primary)">{c}</span><br>')

                # Failure frequency table
                ui.html('<div style="font-size:0.7rem;font-weight:600;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.04em;margin:14px 0 6px">Failure Frequency</div>')
                if patterns:
                    for p in patterns[:10]:
                        sev_color = {"high": "var(--red)", "medium": "var(--yellow)", "low": "var(--green-bright)"}[p["severity"]]
                        width = min(100, p["frequency"] / max(1, patterns[0]["frequency"]) * 100)
                        with ui.element("div").style("margin-bottom:8px"):
                            with ui.row().classes("items-center gap-2").style("margin-bottom:3px"):
                                ui.html(
                                    f'<span style="font-size:0.78rem;font-weight:500;color:var(--text-primary);flex:1">{p["name"]}</span>'
                                    f'<span style="font-size:0.65rem;font-weight:600;color:{sev_color}">{p["severity"].upper()} · ×{p["frequency"]}</span>'
                                )
                            ui.element("div").style(
                                f"height:4px;width:{width}%;background:{sev_color};border-radius:2px;min-width:12px"
                            )
                            if p["definition"]:
                                ui.html(f'<div style="font-size:0.7rem;color:var(--text-muted);margin-top:2px">{p["definition"][:100]}</div>')
                else:
                    ui.label("No failures tagged yet.").style("color: var(--text-muted); font-size: 0.8rem")

            _nav_row(back=None, forward=lambda: go_to(2), forward_label="Map Dimensions →")

        # ── Step 2: Map Dimensions ───────────────────────────────────────────
        def _step2_dimensions():
            codebook = _get("codebook", [])
            code_names = [c["name"] for c in codebook]
            mappings: dict = _get("_jb_mappings", {})
            selected_dims: list = _get("_jb_selected_dims", [])

            _card_header(
                "Step 2 of 5 — Map Failure Codes to Evaluation Dimensions",
                "Select which evaluation dimensions apply to this agent, then assign your failure codes to each. "
                "This grounds your judge in real observed failures — not generic criteria.",
            )

            dim_checkboxes: dict[str, object] = {}
            dim_selects: dict[str, object] = {}

            with ui.column().classes("w-full gap-3"):
                for dim_id, dim_label, dim_desc, dim_color in EVAL_DIMENSIONS:
                    is_selected = dim_id in selected_dims
                    with ui.element("div").style(
                        f"border:1px solid {'var(--accent)' if is_selected else 'var(--border-subtle)'};"
                        "border-radius:10px;padding:12px 14px;background:var(--bg-surface-2);transition:border-color 200ms"
                    ) as dim_card:
                        with ui.row().classes("items-start gap-3 w-full"):
                            cb = ui.checkbox(value=is_selected).props("color=primary dark size=sm")
                            dim_checkboxes[dim_id] = cb
                            with ui.column().classes("flex-grow gap-1"):
                                ui.html(
                                    f'<div style="font-size:0.82rem;font-weight:600;color:var(--text-primary)">{dim_label}</div>'
                                    f'<div style="font-size:0.72rem;color:var(--text-muted)">{dim_desc}</div>'
                                )
                                if code_names:
                                    current_codes = mappings.get(dim_id, [])
                                    sel = ui.select(
                                        options=code_names,
                                        multiple=True,
                                        value=current_codes,
                                        label="Failure codes that belong here",
                                    ).props("dense outlined dark use-chips").style("font-size:0.78rem;margin-top:4px")
                                    dim_selects[dim_id] = sel
                                else:
                                    ui.label("Add failure codes in the Tag step first.").style(
                                        "font-size:0.72rem;color:var(--text-muted)"
                                    )

            def save_mappings():
                new_selected = []
                new_mappings = dict(mappings)
                for dim_id, cb in dim_checkboxes.items():
                    if cb.value:
                        new_selected.append(dim_id)
                    if dim_id in dim_selects:
                        codes = dim_selects[dim_id].value or []
                        new_mappings[dim_id] = codes if isinstance(codes, list) else [codes]
                _set("_jb_selected_dims", new_selected)
                _set("_jb_mappings", new_mappings)
                ui.notify("Mappings saved ✓", type="positive")
                go_to(3)

            async def auto_map():
                if not code_names:
                    ui.notify("No failure codes to map", type="warning")
                    return
                codebook_data = _get("codebook", [])
                paradigm = _get("paradigm_model", {})
                try:
                    from grounded_evals.llm.client import get_default_client, get_model_id
                    client = get_default_client()
                    model_id = get_model_id()
                    dims_desc = "\n".join(f"- {did}: {dlabel} — {ddesc}" for did, dlabel, ddesc, _ in EVAL_DIMENSIONS)
                    codes_desc = "\n".join(f"- {c['name']}: {c.get('definition','')}" for c in codebook_data)
                    prompt = (
                        f"You are mapping AI agent failure codes to evaluation dimensions.\n\n"
                        f"EVALUATION DIMENSIONS:\n{dims_desc}\n\n"
                        f"FAILURE CODES FROM ANALYSIS:\n{codes_desc}\n\n"
                        f"PARADIGM MODEL PHENOMENA: {', '.join(paradigm.get('phenomenon', []))}\n\n"
                        f"Task: For each dimension that applies to this agent, list which failure codes belong to it. "
                        f"Return ONLY a JSON object like: {{\"accuracy\": [\"Code A\", \"Code B\"], \"safety\": [\"Code C\"]}}. "
                        f"Include only dimensions where at least one code clearly belongs. "
                        f"Use the exact dimension IDs: accuracy, completeness, safety, scope, tone, instructions, completeness2, bias."
                    )
                    msg = await asyncio.to_thread(
                        client.messages.create,
                        model=model_id,
                        max_tokens=1024,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    raw = msg.content[0].text.strip()
                    start = raw.find("{")
                    end = raw.rfind("}") + 1
                    result = json.loads(raw[start:end])
                    new_mappings = {}
                    new_selected = []
                    for dim_id, codes in result.items():
                        if isinstance(codes, list) and codes:
                            valid = [c for c in codes if c in code_names]
                            if valid:
                                new_mappings[dim_id] = valid
                                new_selected.append(dim_id)
                    _set("_jb_mappings", new_mappings)
                    _set("_jb_selected_dims", new_selected)
                    ui.notify(f"Auto-mapped {len(new_selected)} dimensions ✓ — refreshing", type="positive")
                    go_to(2)
                except Exception as e:
                    ui.notify(f"Auto-map failed: {e}", type="negative")

            _nav_row(
                back=lambda: go_to(1),
                forward=save_mappings,
                forward_label="Save & Continue →",
                extra_btn=("Auto-Map with AI", "auto_fix_high", auto_map),
            )

        # ── Step 3: Rubrics & Weights ────────────────────────────────────────
        def _step3_rubrics():
            selected_dims = _get("_jb_selected_dims", [])
            rubrics: dict = _get("_jb_rubrics", {})
            mappings: dict = _get("_jb_mappings", {})

            _card_header(
                "Step 3 of 5 — Define Scoring Rubric",
                "For each selected dimension, define what a 1 (failing) vs 5 (excellent) response looks like. "
                "Also set the weight — dimensions tied to severe failures should be weighted higher.",
            )

            if not selected_dims:
                ui.html(
                    '<div style="padding:16px;background:var(--yellow-tint);border:1px solid rgba(240,191,0,0.2);'
                    'border-radius:10px;font-size:0.82rem;color:var(--text-secondary)">'
                    '⚠️ No dimensions selected. Go back and select at least one dimension.'
                    '</div>'
                )
                _nav_row(back=lambda: go_to(2), forward=None)
                return

            dim_map = {d[0]: d for d in EVAL_DIMENSIONS}
            weight_inputs: dict[str, object] = {}
            score1_inputs: dict[str, object] = {}
            score5_inputs: dict[str, object] = {}

            with ui.column().classes("w-full gap-4"):
                for dim_id in selected_dims:
                    if dim_id not in dim_map:
                        continue
                    _, dim_label, dim_desc, dim_color = dim_map[dim_id]
                    cur_rubric = rubrics.get(dim_id, {})
                    codes_for_dim = mappings.get(dim_id, [])

                    with ui.element("div").style(
                        f"border:1px solid var(--border-subtle);border-left:3px solid {dim_color};"
                        "border-radius:10px;padding:14px 16px;background:var(--bg-surface-2)"
                    ):
                        with ui.row().classes("items-center gap-2").style("margin-bottom:8px"):
                            ui.html(f'<span style="font-size:0.82rem;font-weight:700;color:var(--text-primary)">{dim_label}</span>')
                            if codes_for_dim:
                                for c in codes_for_dim[:3]:
                                    ui.html(f'<span style="font-size:0.6rem;padding:2px 7px;border-radius:99px;background:var(--accent-tint);color:var(--accent-bright)">{c}</span>')

                        with ui.row().classes("items-center gap-4 w-full").style("margin-bottom:10px"):
                            ui.html('<span style="font-size:0.72rem;color:var(--text-muted)">Weight (1–3):</span>')
                            w_inp = ui.number(
                                value=cur_rubric.get("weight", 2),
                                min=1, max=3, step=1,
                            ).props("dense outlined dark").style("width:70px")
                            weight_inputs[dim_id] = w_inp
                            ui.html('<span style="font-size:0.68rem;color:var(--text-muted)">1=standard · 2=important · 3=critical</span>')

                        with ui.row().classes("w-full gap-3"):
                            with ui.column().classes("flex-1"):
                                ui.html('<span style="font-size:0.65rem;font-weight:600;color:var(--red);text-transform:uppercase">Score 1 — Failing</span>')
                                s1 = ui.textarea(
                                    value=cur_rubric.get("score1", ""),
                                    placeholder=f"What does a 1/5 {dim_label.lower()} response look like?",
                                ).props("dense outlined dark rows=3").style("font-size:0.78rem")
                                score1_inputs[dim_id] = s1
                            with ui.column().classes("flex-1"):
                                ui.html('<span style="font-size:0.65rem;font-weight:600;color:var(--green-bright);text-transform:uppercase">Score 5 — Excellent</span>')
                                s5 = ui.textarea(
                                    value=cur_rubric.get("score5", ""),
                                    placeholder=f"What does a 5/5 {dim_label.lower()} response look like?",
                                ).props("dense outlined dark rows=3").style("font-size:0.78rem")
                                score5_inputs[dim_id] = s5

            async def auto_fill_rubrics():
                dim_map2 = {d[0]: d for d in EVAL_DIMENSIONS}
                try:
                    from grounded_evals.llm.client import get_default_client, get_model_id
                    client = get_default_client()
                    model_id = get_model_id()
                    codebook = _get("codebook", [])
                    session_data = _get("session_data", {})
                    agent_name = session_data.get("agent_spec", {}).get("name", "the agent")
                    dims_info = "\n".join(
                        f"- {did}: {dim_map2[did][1]} — codes: {', '.join(mappings.get(did, []))}"
                        for did in selected_dims if did in dim_map2
                    )
                    prompt = (
                        f"You are writing evaluation rubrics for an LLM-as-a-Judge for agent: {agent_name}\n\n"
                        f"DIMENSIONS AND THEIR FAILURE CODES:\n{dims_info}\n\n"
                        f"For each dimension, write:\n"
                        f"- score1: concrete description of a FAILING (1/5) response\n"
                        f"- score5: concrete description of an EXCELLENT (5/5) response\n"
                        f"- weight: 1, 2, or 3 (based on severity of associated failure codes)\n\n"
                        f"Return ONLY JSON: {{\"accuracy\": {{\"score1\": \"...\", \"score5\": \"...\", \"weight\": 2}}, ...}}"
                    )
                    msg = await asyncio.to_thread(
                        client.messages.create,
                        model=model_id,
                        max_tokens=2048,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    raw = msg.content[0].text.strip()
                    start = raw.find("{")
                    end = raw.rfind("}") + 1
                    result = json.loads(raw[start:end])
                    new_rubrics = dict(rubrics)
                    for did, val in result.items():
                        if did in selected_dims:
                            new_rubrics[did] = val
                    _set("_jb_rubrics", new_rubrics)
                    ui.notify("Rubrics auto-filled ✓ — refreshing", type="positive")
                    go_to(3)
                except Exception as e:
                    ui.notify(f"Auto-fill failed: {e}", type="negative")

            def save_rubrics():
                new_rubrics = {}
                for dim_id in selected_dims:
                    new_rubrics[dim_id] = {
                        "weight": int(weight_inputs[dim_id].value or 2),
                        "score1": score1_inputs[dim_id].value or "",
                        "score5": score5_inputs[dim_id].value or "",
                    }
                _set("_jb_rubrics", new_rubrics)
                ui.notify("Rubrics saved ✓", type="positive")
                go_to(4)

            _nav_row(
                back=lambda: go_to(2),
                forward=save_rubrics,
                forward_label="Save & Continue →",
                extra_btn=("Auto-Fill with AI", "auto_fix_high", auto_fill_rubrics),
            )

        # ── Step 4: Hard-Fail Rules ──────────────────────────────────────────
        def _step4_hard_fails():
            hard_fails: list = list(_get("_jb_hard_fails", []))
            codebook = _get("codebook", [])
            code_names = [c["name"] for c in codebook]
            paradigm = _get("paradigm_model", {})
            consequences = paradigm.get("consequences", [])

            _card_header(
                "Step 4 of 5 — Hard-Fail Rules",
                "Hard-fail rules override the rubric score — if ANY hard-fail condition is met, "
                "the entire evaluation fails regardless of other scores. Use these for safety violations, "
                "legal/regulatory breaches, or any response that should never reach a user.",
            )

            # Suggested hard-fails from high-severity codes
            high_codes = [p for p in _failure_summary() if p["severity"] == "high"]
            if high_codes:
                ui.html(
                    '<div style="font-size:0.7rem;font-weight:600;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.04em;margin-bottom:6px">'
                    'Suggested from High-Severity Failures</div>'
                )
                with ui.row().classes("flex-wrap gap-2").style("margin-bottom:12px"):
                    for p in high_codes[:5]:
                        def add_suggestion(name=p["name"]):
                            existing = _get("_jb_hard_fails", [])
                            if not any(hf["condition"].startswith(name) for hf in existing):
                                existing.append({"condition": f"{name} occurs in the response", "code": name})
                                _set("_jb_hard_fails", existing)
                                ui.notify(f"Added hard-fail for '{name}'", type="positive")
                                go_to(4)
                        ui.button(f"+ {p['name']}", on_click=add_suggestion).props("size=sm outline").style(
                            "border-color:var(--red);color:var(--red);font-size:0.72rem"
                        )

            # Existing hard-fails
            hf_container = ui.column().classes("w-full gap-2")

            def refresh_hf():
                hf_container.clear()
                current = _get("_jb_hard_fails", [])
                with hf_container:
                    if not current:
                        ui.html(
                            '<div style="padding:12px;background:var(--bg-surface-1);border:1px dashed var(--border-default);'
                            'border-radius:8px;font-size:0.78rem;color:var(--text-muted);text-align:center">'
                            'No hard-fail rules yet. Add one below or use the suggestions above.'
                            '</div>'
                        )
                    else:
                        for i, hf in enumerate(current):
                            with ui.element("div").style(
                                "background:var(--red-tint);border:1px solid rgba(235,87,87,0.2);"
                                "border-left:3px solid var(--red);border-radius:8px;padding:10px 14px"
                            ):
                                with ui.row().classes("items-center gap-2 w-full"):
                                    ui.html('<span style="font-size:0.75rem;font-weight:700;color:var(--red)">HARD-FAIL:</span>')
                                    ui.html(f'<span style="flex:1;font-size:0.8rem;color:var(--text-primary)">{hf["condition"]}</span>')
                                    if hf.get("code"):
                                        ui.html(f'<span style="font-size:0.65rem;padding:2px 7px;border-radius:99px;background:var(--red-tint);color:var(--red);border:1px solid rgba(235,87,87,0.3)">{hf["code"]}</span>')

                                    def remove_hf(idx=i):
                                        current2 = _get("_jb_hard_fails", [])
                                        if idx < len(current2):
                                            current2.pop(idx)
                                            _set("_jb_hard_fails", current2)
                                            refresh_hf()
                                    ui.button(icon="close", on_click=remove_hf).props("flat round size=xs").style("color:var(--text-muted)")

            refresh_hf()

            # Add new hard-fail
            ui.separator().style("opacity:0.1;margin:12px 0")
            ui.html('<div style="font-size:0.7rem;font-weight:600;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.04em;margin-bottom:8px">Add Hard-Fail Rule</div>')
            with ui.row().classes("w-full gap-2 items-end"):
                cond_input = ui.input(
                    placeholder="e.g. Response contains patient-specific medication dosage instructions",
                    label="Condition",
                ).props("dense outlined dark").classes("flex-grow")
                code_sel = ui.select(
                    options=["(none)"] + code_names,
                    value="(none)",
                    label="Linked Code",
                ).props("dense outlined dark").style("width:160px")

                def add_hf():
                    cond = cond_input.value.strip()
                    if not cond:
                        ui.notify("Enter a condition", type="warning")
                        return
                    code = code_sel.value if code_sel.value != "(none)" else ""
                    existing = _get("_jb_hard_fails", [])
                    existing.append({"condition": cond, "code": code})
                    _set("_jb_hard_fails", existing)
                    cond_input.set_value("")
                    code_sel.set_value("(none)")
                    refresh_hf()
                    ui.notify("Hard-fail rule added ✓", type="positive")

                ui.button(icon="add", on_click=add_hf).props("size=sm color=negative round")

            _nav_row(back=lambda: go_to(3), forward=lambda: go_to(5), forward_label="Generate Judge →")

        # ── Step 5: Generate & Export ────────────────────────────────────────
        def _step5_generate():
            _card_header(
                "Step 5 of 5 — Generate Judge Prompt & Export",
                "Choose a judge mode, generate your prompt, then calibrate against your annotated examples.",
            )

            selected_dims = _get("_jb_selected_dims", [])
            rubrics      = _get("_jb_rubrics", {})
            hard_fails   = _get("_jb_hard_fails", [])
            mappings     = _get("_jb_mappings", {})
            codebook     = _get("codebook", [])
            coding_annotations = _get("coding_annotations", [])
            session_data = _get("session_data", {})
            agent_name   = session_data.get("agent_spec", {}).get("name", "the agent")
            agent_desc   = session_data.get("agent_spec", {}).get("description", "")
            paradigm     = _get("paradigm_model", {})
            existing_prompt = _get("_generated_judge_prompt", "")
            dim_map = {d[0]: d for d in EVAL_DIMENSIONS}

            _stat_row([
                (str(len(selected_dims)), "Dimensions", "var(--accent-bright)"),
                (str(len(hard_fails)),    "Hard-Fail Rules", "var(--red)"),
                (str(len(coding_annotations)), "Annotated Examples", "var(--yellow)"),
            ])

            # ── Mode picker ───────────────────────────────────────────────────
            MODES = [
                ("standard",      "Standard",       "ballot",
                 "Zero-shot rubric. Fast, good baseline. No warm-up needed.",
                 "var(--text-secondary)"),
                ("geval",         "G-EVAL",          "psychology",
                 "Chain-of-thought per criterion (Liu et al. 2023). Most reliable for complex responses.",
                 "var(--accent-bright)"),
                ("fewshot",       "Few-Shot",        "format_list_bulleted",
                 "Injects your annotated PASS/FAIL examples (Prometheus). Best for niche domains.",
                 "var(--yellow)"),
                ("constitutional","Constitutional",  "security",
                 "Per-principle checklist from each error code. Best for safety-critical agents.",
                 "var(--red)"),
            ]

            mode_state = {"current": _get("_jb_mode", "geval")}
            mode_card_els: dict[str, object] = {}

            ui.html('<div style="font-size:0.7rem;font-weight:600;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.04em;margin-bottom:8px">Judge Mode</div>')
            with ui.row().classes("w-full gap-2 flex-wrap").style("margin-bottom:14px"):
                for mid, mlabel, micon, mdesc, mcolor in MODES:
                    is_sel = mode_state["current"] == mid
                    card_el = ui.element("div").style(
                        f"flex:1;min-width:160px;border:2px solid {'var(--accent)' if is_sel else 'var(--border-subtle)'};"
                        f"border-radius:10px;padding:10px 12px;background:var(--bg-surface-2);"
                        f"cursor:pointer;transition:border-color 150ms"
                    )
                    mode_card_els[mid] = card_el
                    with card_el:
                        with ui.row().classes("items-center gap-2").style("margin-bottom:4px"):
                            ui.icon(micon).style(f"color:{mcolor};font-size:1rem")
                            ui.html(f'<span style="font-size:0.82rem;font-weight:700;color:{"var(--text-primary)" if is_sel else "var(--text-secondary)"}">{mlabel}</span>')
                            if is_sel:
                                ui.html('<span style="font-size:0.58rem;padding:1px 6px;border-radius:99px;background:var(--accent-tint);color:var(--accent-bright);font-weight:600">SELECTED</span>')
                        ui.html(f'<div style="font-size:0.7rem;color:var(--text-muted);line-height:1.4">{mdesc}</div>')

                    def make_select(m=mid):
                        def on_click():
                            mode_state["current"] = m
                            _set("_jb_mode", m)
                            go_to(5)
                        return on_click
                    card_el.on("click", make_select())

            # ── Prompt textarea ───────────────────────────────────────────────
            prompt_area = ui.textarea(
                value=existing_prompt,
                placeholder="Click 'Generate' to build your judge prompt instantly from your rubric...",
            ).props("outlined dark rows=16").classes("w-full").style(
                "font-size:0.78rem;font-family:monospace;background:var(--bg-surface-1);color:var(--text-primary)"
            )

            # ── Generation (uses backend functions — no LLM call) ─────────────
            def generate_judge():
                try:
                    from grounded_evals.models.core import JudgeCriterion, JudgeRubric
                    from grounded_evals.judge_builder.prompt_gen import (
                        generate_judge_prompt,
                        generate_geval_judge_prompt,
                        generate_few_shot_judge_prompt,
                    )
                    from grounded_evals.judge_builder.constitutional import (
                        build_constitutional_principles,
                        build_constitutional_judge_prompt,
                    )

                    # Build JudgeRubric from UI state
                    criteria = []
                    for did in selected_dims:
                        if did not in dim_map:
                            continue
                        _, dim_label, dim_desc, _ = dim_map[did]
                        r = rubrics.get(did, {})
                        weight = float(r.get("weight", 2))
                        s1 = r.get("score1", "") or f"Response critically fails on {dim_label.lower()}"
                        s5 = r.get("score5", "") or f"Response excellently demonstrates {dim_label.lower()}"
                        codes = mappings.get(did, [])
                        parts = [dim_desc]
                        if codes:
                            parts.append(f"Observed failures: {', '.join(codes)}.")
                        causal = paradigm.get("causal_conditions", [])
                        if causal:
                            cs = "; ".join(c if isinstance(c, str) else c.get("name", "") for c in causal)
                            parts.append(f"Root causes: {cs}.")
                        criteria.append(JudgeCriterion(
                            name=dim_label,
                            description=" ".join(parts),
                            scoring_rubric={
                                5: s5,
                                4: f"Good — minor {dim_label.lower()} issues, core value delivered",
                                3: f"Acceptable — noticeable {dim_label.lower()} issues but response is functional",
                                2: f"Poor — significant issues: {', '.join(codes[:3]) if codes else 'see criteria'}",
                                1: s1,
                            },
                            weight=weight,
                        ))

                    rubric = JudgeRubric(
                        name="Grounded Evaluation Rubric (GEDD)",
                        description="Auto-generated from Open Coding + Axial Coding qualitative analysis.",
                        criteria=criteria,
                    )

                    mode = mode_state["current"]
                    if mode == "geval":
                        base_prompt = generate_geval_judge_prompt(rubric, agent_name, agent_desc)
                    elif mode == "fewshot":
                        from grounded_evals.judge_builder.few_shot import select_exemplars
                        exemplar_set = select_exemplars(coding_annotations, codebook)
                        base_prompt = generate_few_shot_judge_prompt(rubric, exemplar_set, agent_name, agent_desc)
                        if exemplar_set.n_positive == 0:
                            ui.notify("No annotated examples found — using standard rubric for few-shot. Add annotations in the Tag tab.", type="warning")
                    elif mode == "constitutional":
                        principles = build_constitutional_principles(codebook, paradigm, coding_annotations)
                        base_prompt = build_constitutional_judge_prompt(principles, agent_name, agent_desc)
                    else:  # standard
                        base_prompt = generate_judge_prompt(rubric, agent_name, agent_desc)

                    # Inject hard-fail rules before the rubric
                    final_prompt = _inject_hard_fails(base_prompt, hard_fails)
                    _set("_generated_judge_prompt", final_prompt)
                    prompt_area.set_value(final_prompt)
                    mode_label = next(m[1] for m in MODES if m[0] == mode)
                    ui.notify(f"{mode_label} judge prompt generated ✓", type="positive")
                except Exception as e:
                    ui.notify(f"Generation failed: {e}", type="negative")

            def save_edits():
                _set("_generated_judge_prompt", prompt_area.value)
                ui.notify("Prompt saved ✓", type="positive")

            def copy_prompt():
                ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(prompt_area.value or "")});')
                ui.notify("Copied to clipboard ✓", type="positive")

            def download_prompt():
                content = prompt_area.value or ""
                if not content:
                    ui.notify("Generate the prompt first", type="warning")
                    return
                mode = _get("_jb_mode", "geval")
                ui.download(content.encode(), f"judge_{mode}_{agent_name.lower().replace(' ', '_')}.txt")

            def download_full_spec():
                spec = {
                    "agent": agent_name,
                    "judge_mode": _get("_jb_mode", "geval"),
                    "dimensions": [
                        {
                            "id": did,
                            "label": dim_map[did][1] if did in dim_map else did,
                            "weight": rubrics.get(did, {}).get("weight", 2),
                            "score1": rubrics.get(did, {}).get("score1", ""),
                            "score5": rubrics.get(did, {}).get("score5", ""),
                            "failure_codes": mappings.get(did, []),
                        }
                        for did in selected_dims if did in dim_map
                    ],
                    "hard_fail_rules": hard_fails,
                    "judge_prompt": prompt_area.value or "",
                    "error_codebook": [{"name": c["name"], "definition": c.get("definition", "")} for c in codebook],
                }
                ui.download(json.dumps(spec, indent=2).encode(), f"judge_spec_{agent_name.lower().replace(' ', '_')}.json")

            with ui.row().classes("gap-2 flex-wrap").style("margin: 10px 0"):
                ui.button("Generate", icon="auto_fix_high", on_click=generate_judge).style(
                    "background:var(--accent);color:white;border-radius:6px"
                ).props("size=sm")
                ui.button("Save Edits", icon="save", on_click=save_edits).props("size=sm outline dark").style(
                    "border-color:var(--border-default);color:var(--text-secondary)"
                )
                ui.button("Copy", icon="content_copy", on_click=copy_prompt).props("size=sm outline dark").style(
                    "border-color:var(--border-default);color:var(--text-secondary)"
                )
                ui.button("Download .txt", icon="download", on_click=download_prompt).props("size=sm outline dark").style(
                    "border-color:var(--border-default);color:var(--text-secondary)"
                )
                ui.button("Download Spec", icon="download", on_click=download_full_spec).props("size=sm outline dark").style(
                    "border-color:var(--accent);color:var(--accent-bright)"
                )

            # ── Calibration panel ─────────────────────────────────────────────
            ui.separator().style("opacity:0.1;margin:18px 0")
            with ui.row().classes("items-center justify-between w-full").style("margin-bottom:10px"):
                with ui.column().style("gap:2px"):
                    ui.html('<div style="font-size:0.7rem;font-weight:600;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.04em">Calibrate Judge</div>')
                    n_anns = len(coding_annotations)
                    ann_color = "var(--green-bright)" if n_anns >= 10 else ("var(--yellow)" if n_anns >= 5 else "var(--red)")
                    ui.html(
                        f'<div style="font-size:0.75rem;color:var(--text-muted)">'
                        f'Run judge against your <span style="color:{ann_color};font-weight:600">{n_anns} annotated examples</span> '
                        f'and measure Cohen\'s κ agreement with human labels.'
                        f'{"" if n_anns >= 5 else " <span style=\'color:var(--yellow)\'>Add at least 5 annotations in the Tag tab for meaningful results.</span>"}'
                        f'</div>'
                    )

            calibration_result_container = ui.column().classes("w-full")

            async def run_calibration():
                prompt = prompt_area.value or _get("_generated_judge_prompt", "")
                if not prompt.strip():
                    ui.notify("Generate a judge prompt first", type="warning")
                    return
                if not coding_annotations:
                    ui.notify("No annotated examples found. Tag some responses first.", type="warning")
                    return

                calibrate_btn.props("loading")
                calibration_result_container.clear()
                with calibration_result_container:
                    ui.html('<div style="font-size:0.78rem;color:var(--text-muted);padding:8px 0">Running judge on annotated examples…</div>')

                try:
                    from grounded_evals.llm.client import get_default_client, get_model_id
                    from grounded_evals.judge_builder.calibrate import calibrate
                    import json as _json

                    client = get_default_client()
                    model_id = get_model_id()

                    manual_scores: list[dict] = []
                    judge_scores: list[dict] = []
                    disagreements_raw: list[dict] = []

                    for ann in coding_annotations:
                        query    = ann.get("query", "")
                        response = ann.get("response", "")
                        verdict  = ann.get("annotation", ann.get("verdict", ""))
                        if not query or not response or not verdict:
                            continue

                        # Human: map verdict → score 1–5
                        h_score = {"correct": 5, "partial": 3, "incorrect": 1}.get(verdict, 3)
                        manual_scores.append({"overall": h_score})

                        # Run judge
                        filled = prompt.replace("{query}", query[:500]).replace("{response}", response[:800])
                        msg = await asyncio.to_thread(
                            client.messages.create,
                            model=model_id,
                            max_tokens=1024,
                            messages=[{"role": "user", "content": filled}],
                        )
                        raw = msg.content[0].text
                        parsed: dict = {}
                        for fence in ("```json", "```"):
                            if fence in raw:
                                try:
                                    s = raw.index(fence) + len(fence)
                                    e2 = raw.index("```", s)
                                    parsed = _json.loads(raw[s:e2].strip())
                                    break
                                except Exception:
                                    pass
                        if not parsed:
                            try:
                                js = raw.find("{"); je = raw.rfind("}") + 1
                                if js >= 0 and je > js:
                                    parsed = _json.loads(raw[js:je])
                            except Exception:
                                pass

                        # Extract overall score from judge output
                        j_score = None
                        if "overall_score" in parsed:
                            j_score = float(parsed["overall_score"])
                        elif "pass" in parsed:
                            j_score = 5.0 if parsed["pass"] else 1.0
                        elif "weighted_total" in parsed:
                            j_score = float(parsed["weighted_total"]) / 20  # 0-100 → 1-5
                        else:
                            j_score = 3.0  # fallback

                        judge_scores.append({"overall": round(j_score)})

                        # Collect disagreements for display
                        j_pass = j_score >= 3.5
                        h_pass = h_score >= 4
                        if j_pass != h_pass:
                            disagreements_raw.append({
                                "query": query[:80],
                                "human": verdict,
                                "judge": "PASS" if j_pass else "FAIL",
                                "j_score": j_score,
                                "summary": parsed.get("summary", parsed.get("reasoning_summary", "")),
                            })

                    result = calibrate(manual_scores, judge_scores)

                    calibration_result_container.clear()
                    with calibration_result_container:
                        _render_calibration_result(result, disagreements_raw, len(manual_scores))

                    ui.notify(f"Calibration complete — κ = {result.weighted_kappa:.2f}", type="positive")

                except Exception as e:
                    calibration_result_container.clear()
                    with calibration_result_container:
                        ui.html(
                            f'<div style="padding:12px;background:var(--red-tint);border:1px solid rgba(235,87,87,0.2);'
                            f'border-radius:8px;font-size:0.8rem;color:var(--text-secondary)">'
                            f'⚠️ Calibration failed: {e}<br>'
                            f'<span style="font-size:0.72rem;color:var(--text-muted)">Check that ANTHROPIC_API_KEY or AWS credentials are configured.</span>'
                            f'</div>'
                        )
                finally:
                    calibrate_btn.props(remove="loading")

            calibrate_btn = ui.button(
                "Calibrate Judge", icon="analytics", on_click=run_calibration
            ).props("size=sm outline").style(
                "border-color:var(--green);color:var(--green-bright);border-radius:6px"
            )

            _nav_row(back=lambda: go_to(4), forward=None)

        # ── Initial render ────────────────────────────────────────────────────
        render_step()


# ── Shared helpers ────────────────────────────────────────────────────────────

def _card_header(title: str, subtitle: str):
    ui.html(
        f'<div style="margin-bottom:14px">'
        f'<div style="font-size:0.88rem;font-weight:700;color:var(--text-primary);margin-bottom:3px">{title}</div>'
        f'<div style="font-size:0.78rem;color:var(--text-muted);line-height:1.5">{subtitle}</div>'
        f'</div>'
    )


def _stat_row(stats: list[tuple[str, str, str]]):
    html = '<div style="display:flex;gap:10px;margin-bottom:14px">'
    for val, label, color in stats:
        html += (
            f'<div style="flex:1;background:var(--bg-surface-1);border:1px solid var(--border-subtle);'
            f'border-radius:8px;padding:10px;text-align:center">'
            f'<div style="font-size:1.4rem;font-weight:700;color:{color};font-variant-numeric:tabular-nums">{val}</div>'
            f'<div style="font-size:0.62rem;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.04em;margin-top:2px">{label}</div>'
            f'</div>'
        )
    html += '</div>'
    ui.html(html)


def _nav_row(back, forward, forward_label: str = "Continue →", extra_btn=None):
    with ui.row().classes("w-full justify-between items-center").style("margin-top:18px;padding-top:14px;border-top:1px solid var(--border-subtle)"):
        if back:
            ui.button("← Back", on_click=back).props("flat size=sm").style("color:var(--text-muted)")
        else:
            ui.element("div")

        with ui.row().classes("gap-2"):
            if extra_btn:
                label, icon, handler = extra_btn
                ui.button(label, icon=icon, on_click=handler).props("size=sm outline dark").style(
                    "border-color:var(--accent);color:var(--accent-bright)"
                )
            if forward:
                ui.button(forward_label, on_click=forward).props("size=sm").style(
                    "background:var(--accent);color:white;border-radius:6px"
                )


def _inject_hard_fails(base_prompt: str, hard_fails: list[dict]) -> str:
    """Prepend hard-fail rules block into the generated judge prompt."""
    if not hard_fails:
        return base_prompt
    lines = ["## Hard-Fail Rules (Binary Override)", ""]
    lines.append("If ANY of the following conditions is met, the overall verdict MUST be FAIL (score 1) regardless of other scores:")
    lines.append("")
    for i, hf in enumerate(hard_fails, 1):
        cond = hf.get("condition", "")
        code = hf.get("code", "")
        tag = f" [{code}]" if code else ""
        lines.append(f"{i}. VIOLATED if: {cond}{tag}")
    lines.append("")
    block = "\n".join(lines)
    # Insert after first double-newline (after system context / role definition)
    split_idx = base_prompt.find("\n\n")
    if split_idx != -1:
        return base_prompt[:split_idx + 2] + block + base_prompt[split_idx + 2:]
    return block + "\n\n" + base_prompt


def _render_calibration_result(result, disagreements_raw: list[dict], n: int):
    """Render Cohen's κ calibration result with traffic-light color coding."""
    kappa = result.weighted_kappa
    interp = result.kappa_interpretation

    # Traffic-light color
    if kappa >= 0.80:
        kappa_color = "var(--green-bright)"
        badge_bg    = "rgba(39,174,96,0.12)"
        verdict_icon = "✅"
    elif kappa >= 0.61:
        kappa_color = "var(--accent-bright)"
        badge_bg    = "var(--accent-tint)"
        verdict_icon = "🟡"
    elif kappa >= 0.41:
        kappa_color = "var(--yellow)"
        badge_bg    = "rgba(242,201,76,0.12)"
        verdict_icon = "⚠️"
    else:
        kappa_color = "var(--red)"
        badge_bg    = "var(--red-tint)"
        verdict_icon = "❌"

    ci_lo = getattr(result, "kappa_ci_low", None)
    ci_hi = getattr(result, "kappa_ci_high", None)
    ci_str = f" (95% CI: {ci_lo:.2f}–{ci_hi:.2f})" if ci_lo is not None and ci_hi is not None else ""

    ui.html(
        f'<div style="padding:14px 16px;background:{badge_bg};border:1px solid {kappa_color}33;'
        f'border-radius:10px;margin-bottom:12px">'
        f'<div style="display:flex;align-items:center;gap:12px">'
        f'<div style="font-size:2.2rem;font-weight:800;color:{kappa_color};font-variant-numeric:tabular-nums">'
        f'κ = {kappa:.2f}</div>'
        f'<div>'
        f'<div style="font-size:0.85rem;font-weight:600;color:var(--text-primary)">{verdict_icon} {interp}</div>'
        f'<div style="font-size:0.72rem;color:var(--text-muted)">'
        f'{n} examples evaluated{ci_str}'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    # Recommendation
    rec = getattr(result, "recommendation", "")
    if rec:
        ui.html(
            f'<div style="font-size:0.78rem;color:var(--text-secondary);'
            f'background:var(--bg-surface-1);border-radius:8px;padding:10px 12px;'
            f'border-left:3px solid {kappa_color};margin-bottom:12px">'
            f'<strong>Recommendation:</strong> {rec}'
            f'</div>'
        )

    # Per-criterion kappa table
    per_crit = getattr(result, "per_criterion_kappa", {})
    weakest  = getattr(result, "weakest_criterion", "")
    if per_crit:
        rows_html = ""
        for crit, ck in per_crit.items():
            crit_color = "var(--green-bright)" if ck >= 0.80 else ("var(--yellow)" if ck >= 0.41 else "var(--red)")
            weak_mark  = " ⚠️" if crit == weakest else ""
            rows_html += (
                f'<tr>'
                f'<td style="padding:5px 8px;font-size:0.75rem;color:var(--text-secondary)">{crit}{weak_mark}</td>'
                f'<td style="padding:5px 8px;text-align:right;font-weight:700;color:{crit_color};'
                f'font-variant-numeric:tabular-nums;font-size:0.75rem">{ck:.2f}</td>'
                f'</tr>'
            )
        ui.html(
            f'<div style="margin-bottom:12px">'
            f'<div style="font-size:0.68rem;font-weight:600;color:var(--text-tertiary);'
            f'text-transform:uppercase;letter-spacing:0.04em;margin-bottom:6px">Per-Criterion Agreement</div>'
            f'<table style="width:100%;border-collapse:collapse;background:var(--bg-surface-1);border-radius:8px;overflow:hidden">'
            f'{rows_html}'
            f'</table>'
            f'</div>'
        )

    # Disagreement examples
    if disagreements_raw:
        ui.html(
            f'<div style="font-size:0.68rem;font-weight:600;color:var(--text-tertiary);'
            f'text-transform:uppercase;letter-spacing:0.04em;margin-bottom:6px">'
            f'Disagreements ({len(disagreements_raw)} of {n})'
            f'</div>'
        )
        for d in disagreements_raw[:5]:
            h_col = "var(--green-bright)" if d["human"] == "correct" else ("var(--yellow)" if d["human"] == "partial" else "var(--red)")
            j_col = "var(--green-bright)" if d["judge"] == "PASS" else "var(--red)"
            summary_html = f'<div style="font-size:0.68rem;color:var(--text-muted);margin-top:3px">{d["summary"][:120]}…</div>' if d.get("summary") else ""
            ui.html(
                f'<div style="background:var(--bg-surface-1);border:1px solid var(--border-subtle);'
                f'border-radius:8px;padding:10px 12px;margin-bottom:6px">'
                f'<div style="font-size:0.76rem;color:var(--text-secondary);margin-bottom:4px">{d["query"]}</div>'
                f'<div style="display:flex;gap:8px;align-items:center">'
                f'<span style="font-size:0.68rem;padding:2px 8px;border-radius:99px;'
                f'background:{h_col}22;color:{h_col};font-weight:600">Human: {d["human"].upper()}</span>'
                f'<span style="font-size:0.68rem;padding:2px 8px;border-radius:99px;'
                f'background:{j_col}22;color:{j_col};font-weight:600">Judge: {d["judge"]}</span>'
                f'<span style="font-size:0.68rem;color:var(--text-muted)">score {d["j_score"]:.1f}</span>'
                f'</div>'
                f'{summary_html}'
                f'</div>'
            )
