"""Map Root Causes (Axial Coding) — Paradigm Model Canvas page."""

from nicegui import app, ui

from grounded_evals.ui.layout import page_layout

SLOTS = ['phenomenon', 'causal_conditions', 'context', 'intervening_conditions', 'strategies', 'consequences']
SLOT_LABELS = {
    'phenomenon': 'Phenomenon',
    'causal_conditions': 'Triggered By',
    'context': 'Occurs When',
    'intervening_conditions': 'Gets Worse If',
    'strategies': 'Manifests As',
    'consequences': 'User Impact',
}
SLOT_COLORS = {
    'phenomenon': 'var(--accent-bright)',
    'causal_conditions': 'var(--red)',
    'context': 'var(--blue)',
    'intervening_conditions': 'var(--yellow)',
    'strategies': 'var(--text-secondary)',
    'consequences': 'var(--red)',
}

SEVERITY_WEIGHTS = {'cosmetic': 1, 'functional': 2, 'critical': 3, 'catastrophic': 4}

# Keywords that map codes to EVAL_DIMENSIONS
_DIM_KEYWORDS = {
    'accuracy':     ['accurate', 'accuracy', 'fact', 'factual', 'wrong', 'incorrect', 'hallucin', 'misinform'],
    'completeness': ['complet', 'missing', 'partial', 'incomplete', 'omit', 'left out', 'forgot'],
    'safety':       ['safe', 'safety', 'harm', 'toxic', 'danger', 'abuse', 'violat', 'policy'],
    'scope':        ['scope', 'role', 'off-topic', 'irrelevant', 'boundary', 'outside', 'off topic'],
    'tone':         ['tone', 'style', 'rude', 'inappropriate', 'formal', 'informal', 'cold', 'harsh'],
    'instructions': ['instruct', 'follow', 'rule', 'system prompt', 'ignore', 'contradict', 'format'],
    'completeness2': ['concis', 'verbose', 'pad', 'rambl', 'lengthy', 'too long', 'too short'],
    'bias':         ['bias', 'fair', 'discriminat', 'stereotyp', 'prejudic', 'unfair'],
}

EVAL_DIMENSIONS = [
    ("accuracy",       "Accuracy",          "Are facts, figures, and claims correct?"),
    ("completeness",   "Completeness",       "Does the response address all parts of the query?"),
    ("safety",         "Safety",             "Does it avoid harmful, dangerous, or toxic output?"),
    ("scope",          "Scope Adherence",    "Does it stay within the agent's intended role?"),
    ("tone",           "Tone / Style",       "Is the tone appropriate for the target audience?"),
    ("instructions",   "Instruction Follow", "Does it follow the system-prompt rules?"),
    ("completeness2",  "Conciseness",        "Is the response appropriately concise (not padded)?"),
    ("bias",           "Bias / Fairness",    "Does it avoid discrimination or unfair framing?"),
]

_VAGUE = {'bad', 'wrong', 'issue', 'error', 'problem', 'fail', 'failed', 'poor', 'incorrect',
          'broken', 'not', 'fix', 'failure', 'fault', 'defect', 'mistake', 'bug'}


def _ensure_state():
    if 'codebook' not in app.storage.user:
        app.storage.user['codebook'] = []
    if 'paradigm_model' not in app.storage.user:
        app.storage.user['paradigm_model'] = {s: [] for s in SLOTS}
    if 'failure_patterns' not in app.storage.user:
        app.storage.user['failure_patterns'] = []
    if 'coding_annotations' not in app.storage.user:
        app.storage.user['coding_annotations'] = []


def _all_code_names():
    return [c['name'] for c in app.storage.user['codebook']]


def _assigned_codes():
    all_names = set(_all_code_names())
    assigned = set()
    for items in app.storage.user['paradigm_model'].values():
        for item in items:
            if item in all_names:
                assigned.add(item)
    return assigned


def _unassigned_codes():
    return [n for n in _all_code_names() if n not in _assigned_codes()]


def _saturation_pct():
    total = len(_all_code_names())
    if total == 0:
        return 0
    return min(1.0, len(_assigned_codes()) / total)


def _code_evidence(code_name: str) -> list[dict]:
    """Return all annotations that include this code name."""
    return [
        a for a in app.storage.user.get('coding_annotations', [])
        if code_name in a.get('codes', [])
    ]


def _code_frequency() -> dict[str, int]:
    freq: dict[str, int] = {}
    for a in app.storage.user.get('coding_annotations', []):
        for c in a.get('codes', []):
            freq[c] = freq.get(c, 0) + 1
    return freq


def _code_avg_severity(code_name: str) -> float:
    weights = [
        SEVERITY_WEIGHTS.get(a.get('severity', 'functional'), 2)
        for a in app.storage.user.get('coding_annotations', [])
        if code_name in a.get('codes', [])
    ]
    return sum(weights) / len(weights) if weights else 2.0


def _infer_dimensions() -> list[str]:
    """Return EVAL_DIMENSION ids hinted at by paradigm model codes."""
    all_codes = []
    for codes in app.storage.user['paradigm_model'].values():
        all_codes.extend(codes)
    text = ' '.join(all_codes).lower()
    matched = []
    for dim_id, kws in _DIM_KEYWORDS.items():
        if any(kw in text for kw in kws):
            matched.append(dim_id)
    # Always suggest accuracy and completeness when there are any codes
    if all_codes and not matched:
        matched = ['accuracy', 'completeness']
    return matched


def _code_quality(name: str) -> tuple[str, str]:
    """Return (status, message) for a code name. status: 'good'|'vague'|'long'|'short'."""
    stripped = (name or '').strip()
    if not stripped:
        return ('empty', '')
    words = stripped.lower().split()
    if len(words) == 1 and words[0] in _VAGUE:
        return ('vague', 'Too vague — describe failure TYPE')
    if all(w in _VAGUE for w in words):
        return ('vague', 'Describes symptom, not type — be more specific')
    if len(stripped) > 60:
        return ('long', 'Too long — aim for 2–4 words')
    if len(words) == 1:
        return ('short', 'Single word — add context')
    return ('good', '')


def _show_evidence_dialog(code_name: str):
    annotations = _code_evidence(code_name)
    with ui.dialog() as dlg, ui.card().style(
        "min-width: 520px; max-width: 720px; max-height: 80vh; overflow-y: auto; "
        "background: var(--surface-2); border: 1px solid var(--border)"
    ):
        with ui.row().classes("items-center justify-between w-full").style("margin-bottom: 12px"):
            ui.label(f'Evidence for "{code_name}"').style(
                "font-weight: 700; font-size: 1rem; color: var(--text-primary)"
            )
            ui.label(f'{len(annotations)} annotation(s)').style(
                "font-size: 0.75rem; color: var(--text-tertiary)"
            )
        if not annotations:
            ui.label('No annotations yet for this code.').style("color: var(--text-secondary); font-style: italic")
        for ann in annotations:
            sev = ann.get('severity', 'functional')
            sev_color = {'cosmetic': 'var(--green-bright)', 'functional': 'var(--yellow)',
                         'critical': 'var(--red)', 'catastrophic': 'var(--red)'}.get(sev, 'var(--yellow)')
            with ui.element("div").style(
                "border: 1px solid var(--border); border-radius: var(--radius-xl); "
                "padding: 10px 12px; margin-bottom: 8px; background: var(--surface-1)"
            ):
                # Severity badge
                ui.html(
                    f'<span style="display:inline-block;padding:1px 7px;border-radius:8px;'
                    f'font-size:0.68rem;font-weight:600;background:{sev_color}20;'
                    f'color:{sev_color};margin-bottom:6px">{sev.upper()}</span>'
                )
                ui.label('Query').style("font-size: 0.65rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase")
                ui.label(ann.get('query', '—')).style(
                    "font-size: 0.8rem; color: var(--text-primary); margin-bottom: 6px; "
                    "white-space: pre-wrap; word-break: break-word"
                )
                ui.label('Response').style("font-size: 0.65rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase")
                resp = ann.get('response', '—')
                ui.label(resp[:400] + ('…' if len(resp) > 400 else '')).style(
                    "font-size: 0.78rem; color: var(--text-secondary); white-space: pre-wrap; word-break: break-word"
                )
                if ann.get('memo'):
                    ui.label(f'Note: {ann["memo"]}').style("font-size: 0.72rem; color: var(--accent-bright); margin-top: 4px; font-style: italic")
        with ui.row().classes("justify-end w-full").style("margin-top: 8px"):
            ui.button('Close', on_click=dlg.close).props('flat size=sm').style("color: var(--text-secondary)")
    dlg.open()


def _show_audit_dialog():
    codebook = app.storage.user.get('codebook', [])
    issues = [(c['name'], *_code_quality(c['name'])) for c in codebook]
    bad = [(name, status, msg) for name, status, msg in issues if status != 'good' and status != 'empty']

    with ui.dialog() as dlg, ui.card().style(
        "min-width: 480px; max-width: 680px; max-height: 75vh; overflow-y: auto; "
        "background: var(--surface-2); border: 1px solid var(--border)"
    ):
        ui.label('Codebook Quality Audit').style("font-weight: 700; font-size: 1rem; color: var(--text-primary); margin-bottom: 12px")
        if not bad:
            with ui.row().classes("items-center gap-2"):
                ui.icon('check_circle').style("color: var(--green-bright); font-size: 1.4rem")
                ui.label('All codes look good!').style("color: var(--green-bright); font-weight: 600")
        else:
            ui.label(f'{len(bad)} code(s) need attention:').style("font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 8px")
            for name, status, msg in bad:
                color_map = {'vague': 'var(--red)', 'long': 'var(--yellow)', 'short': 'var(--yellow)'}
                c = color_map.get(status, 'var(--text-secondary)')
                with ui.element("div").style(
                    f"border-left: 3px solid {c}; padding: 6px 10px; margin-bottom: 6px; "
                    "background: var(--surface-1); border-radius: 0 var(--radius-md) var(--radius-md) 0"
                ):
                    ui.label(name).style(f"font-weight: 600; font-size: 0.82rem; color: {c}")
                    ui.label(msg).style("font-size: 0.75rem; color: var(--text-tertiary)")
        # Check for low-frequency codes (appear in 0-1 annotations)
        freq = _code_frequency()
        lonely = [c['name'] for c in codebook if freq.get(c['name'], 0) <= 1]
        if lonely:
            ui.separator().style("margin: 10px 0")
            ui.label('Low-evidence codes (≤1 annotation) — consider merging or removing:').style(
                "font-size: 0.78rem; color: var(--text-tertiary); margin-bottom: 6px"
            )
            with ui.row().classes("flex-wrap gap-1"):
                for name in lonely:
                    ui.html(f'<span class="code-chip" style="opacity:0.6">{name}</span>')
        with ui.row().classes("justify-end w-full").style("margin-top: 12px"):
            ui.button('Close', on_click=dlg.close).props('flat size=sm').style("color: var(--text-secondary)")
    dlg.open()


@ui.page('/analysis')
def analysis_page():
    _ensure_state()
    page_layout('Pattern Map', current_path="/analysis")

    if not app.storage.user.get('codebook') and not app.storage.user.get('coding_annotations'):
        with ui.column().classes('w-full items-center justify-center').style("min-height: 60vh"):
            with ui.element("div").style(
                "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                "border-radius: var(--radius-xl); padding: 3rem; text-align: center; max-width: 420px"
            ):
                ui.icon("hub").style("font-size: 3rem; color: var(--accent-bright); margin-bottom: 1rem")
                ui.label("Pattern Map").style("font-size: 1.1rem; font-weight: 700; color: var(--text-primary)")
                ui.label("Map failure codes into root causes and user impacts. Annotate responses first to create codes.").style(
                    "font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.5rem; line-height: 1.5"
                )
                ui.button("Annotate responses first", icon="label",
                          on_click=lambda: ui.navigate.to("/coding")).style(
                    "margin-top: 1.5rem; background: var(--accent); color: white; border-radius: 6px"
                )
        return

    view_mode = {'value': 'canvas'}  # 'canvas' | 'table'

    with ui.column().classes('w-full max-w-5xl mx-auto').style("padding: 1.5rem"):
        # Coaching
        with ui.expansion("💡 What should I do here?", icon="help_outline").classes("w-full").style(
            "background: var(--yellow-tint); border: 1px solid rgba(240,191,0,0.15); "
            "border-radius: var(--radius-xl); margin-bottom: 1rem; color: var(--text-primary)"
        ):
            ui.label("Turn expert labels into a PM-ready risk map:").style("font-size: 0.82rem; font-weight: 500; color: var(--text-primary)")
            ui.label("• What TRIGGERS it? → Triggered By\n"
                     "• WHEN does it happen? → Occurs When\n"
                     "• What makes it WORSE? → Gets Worse If\n"
                     "• HOW does the agent fail? → Manifests As\n"
                     "• What's the USER IMPACT? → User Impact\n\n"
                     "Click any chip to inspect the evidence behind that product risk.").style(
                "font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px; white-space: pre-line"
            )

        # Unassigned codes
        with ui.row().classes("items-center gap-2").style("margin-bottom: 8px"):
            ui.label('Unassigned Codes').style("font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em")
        codes_container = ui.row().classes('flex-wrap gap-1')

        def refresh_all():
            refresh_codes()
            refresh_canvas()
            refresh_saturation()

        def refresh_codes():
            codes_container.clear()
            with codes_container:
                unassigned = _unassigned_codes()
                if not unassigned:
                    ui.label('All codes assigned ✓').style("font-size: 0.78rem; color: var(--green-bright)")
                for name in unassigned:
                    freq = _code_frequency().get(name, 0)
                    label = f'{name} ({freq})' if freq else name
                    ui.html(f'<span class="code-chip">{label}</span>')

        # Saturation
        saturation_container = ui.row().classes('w-full items-center gap-3').style("margin: 10px 0")

        def refresh_saturation():
            saturation_container.clear()
            with saturation_container:
                pct = _saturation_pct()
                ui.linear_progress(value=pct).props('size=6px color=green').style("flex: 1")
                ui.label(f'{pct:.0%} assigned').style("font-size: 0.72rem; color: var(--text-tertiary)")

        # View toggle row
        with ui.row().classes("items-center justify-between w-full").style("margin-top: 12px; margin-bottom: 8px"):
            ui.label('Paradigm Model').style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em"
            )
            with ui.row().classes("gap-1 items-center"):
                view_btn_canvas = ui.button('Canvas', icon='dashboard', on_click=lambda: switch_view('canvas')).props('size=sm flat')
                view_btn_table = ui.button('Priority Table', icon='table_rows', on_click=lambda: switch_view('table')).props('size=sm flat')

        canvas_container = ui.column().classes('w-full gap-2')

        def switch_view(mode: str):
            view_mode['value'] = mode
            if mode == 'canvas':
                view_btn_canvas.props('unelevated color=primary')
                view_btn_table.props(remove='unelevated color')
            else:
                view_btn_table.props('unelevated color=primary')
                view_btn_canvas.props(remove='unelevated color')
            refresh_canvas()

        def make_slot_ui(slot_key, parent):
            model = app.storage.user['paradigm_model']
            codes_in_slot = model.get(slot_key, [])
            has = 'has-items' if codes_in_slot else ''
            color = SLOT_COLORS.get(slot_key, 'var(--text-tertiary)')
            freq_map = _code_frequency()
            with parent:
                with ui.column().classes(f'paradigm-slot {has} w-full'):
                    ui.label(SLOT_LABELS[slot_key]).style(
                        f"font-weight: 600; font-size: 0.72rem; color: {color}; text-transform: uppercase; letter-spacing: 0.04em"
                    )
                    with ui.row().classes('flex-wrap gap-1').style("margin-top: 6px"):
                        for name in codes_in_slot:
                            freq = freq_map.get(name, 0)
                            chip_label = f'{name}  ({freq})' if freq else name

                            def open_evidence(n=name):
                                _show_evidence_dialog(n)

                            def remove(n=name, s=slot_key):
                                app.storage.user['paradigm_model'][s].remove(n)
                                refresh_all()

                            with ui.element("div").style("display:inline-flex;align-items:center;gap:4px"):
                                ui.chip(chip_label, color='primary', on_click=open_evidence).props("size=sm dark clickable").style("cursor:pointer")
                                ui.button(icon='close', on_click=remove).props("flat round size=xs").style(
                                    "color: var(--text-tertiary); width: 20px; height: 20px; min-width: 20px; padding: 0"
                                )
                    options = _unassigned_codes()
                    if options:
                        def assign(e, s=slot_key):
                            if e.value:
                                app.storage.user['paradigm_model'][s].append(e.value)
                                refresh_all()
                        ui.select(options, label='+ Assign code', on_change=assign).props('dense outlined dark').style("max-width: 200px; margin-top: 6px")

        def render_priority_table():
            codebook = app.storage.user.get('codebook', [])
            freq_map = _code_frequency()
            rows = []
            for c in codebook:
                name = c['name']
                freq = freq_map.get(name, 0)
                avg_sev = _code_avg_severity(name)
                impact = round(freq * avg_sev, 1)
                rows.append({'name': name, 'freq': freq, 'avg_sev': avg_sev, 'impact': impact})
            rows.sort(key=lambda r: r['impact'], reverse=True)

            if not rows:
                ui.label('No codes yet. Go to Tag Failures first.').style("color: var(--text-secondary); font-style: italic")
                return

            # Table header
            with ui.element("div").style(
                "border: 1px solid var(--border); border-radius: var(--radius-xl); overflow: hidden"
            ):
                with ui.row().style(
                    "background: var(--surface-2); padding: 8px 12px; gap: 0; border-bottom: 1px solid var(--border)"
                ):
                    for label, flex in [('Code', '3'), ('Freq', '1'), ('Avg Severity', '1.5'), ('Impact Score', '1.5')]:
                        ui.label(label).style(
                            f"flex:{flex}; font-size: 0.68rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase"
                        )
                for i, row in enumerate(rows):
                    bg = 'var(--surface-1)' if i % 2 == 0 else 'var(--surface-2)'
                    sev_label = {1: 'Cosmetic', 2: 'Functional', 3: 'Critical', 4: 'Catastrophic'}.get(round(row['avg_sev']), 'Functional')
                    sev_color = {1: 'var(--green-bright)', 2: 'var(--yellow)', 3: 'var(--red)', 4: 'var(--red)'}.get(round(row['avg_sev']), 'var(--yellow)')
                    impact_color = 'var(--red)' if row['impact'] >= 6 else 'var(--yellow)' if row['impact'] >= 3 else 'var(--text-secondary)'
                    with ui.row().style(f"background:{bg}; padding:8px 12px; gap:0; align-items:center"):
                        with ui.element("div").style("flex:3"):
                            def ev_click(n=row['name']):
                                _show_evidence_dialog(n)
                            ui.link(row['name'], target='#').on('click', ev_click).style(
                                "font-size: 0.82rem; color: var(--accent-bright); cursor: pointer"
                            )
                        ui.label(str(row['freq'])).style(f"flex:1; font-size:0.82rem; color:var(--text-primary)")
                        ui.html(
                            f'<span style="flex:1.5;font-size:0.75rem;font-weight:600;color:{sev_color}">'
                            f'{sev_label}</span>'
                        ).style("flex:1.5")
                        ui.html(
                            f'<span style="flex:1.5;font-size:0.85rem;font-weight:700;color:{impact_color}">'
                            f'{row["impact"]}</span>'
                        ).style("flex:1.5")

            ui.label('Impact = Frequency × Avg Severity Weight (Cosmetic=1, Functional=2, Critical=3, Catastrophic=4)').style(
                "font-size: 0.68rem; color: var(--text-tertiary); margin-top: 6px"
            )

        def refresh_canvas():
            canvas_container.clear()
            with canvas_container:
                if view_mode['value'] == 'table':
                    render_priority_table()
                    return

                # Phenomenon (full width, highlighted)
                with ui.element("div").style(
                    "padding: 12px 14px; border-radius: var(--radius-xl); "
                    "background: var(--accent-tint); border: 1px solid var(--accent); margin-bottom: 4px"
                ):
                    make_slot_ui('phenomenon', ui.column().classes("w-full"))

                # Grid: 2 columns
                with ui.row().classes('w-full gap-2'):
                    for slot in ['causal_conditions', 'context']:
                        col = ui.column().classes('flex-1')
                        make_slot_ui(slot, col)
                with ui.row().classes('w-full gap-2'):
                    for slot in ['intervening_conditions', 'strategies']:
                        col = ui.column().classes('flex-1')
                        make_slot_ui(slot, col)
                # Consequences full width
                make_slot_ui('consequences', ui.column().classes("w-full"))

        # ── Action buttons ────────────────────────────────────────────────────
        async def generate_analysis():
            codebook = app.storage.user.get('codebook', [])
            if not codebook:
                ui.notify('Add codes in Tag Failures first', type='warning')
                return
            try:
                import asyncio

                from grounded_evals.axial_coding.paradigm import build_paradigm_model
                from grounded_evals.models.core import Code, CodeType

                codes = [Code(label=c['name'], definition=c.get('definition', ''), code_type=CodeType.DESCRIPTIVE) for c in codebook]
                ui.notify('Analyzing patterns...', type='info')
                session_data = app.storage.user.get('session_data', {})
                try:
                    from grounded_evals.guide.session import Session as _Session
                    session_categories = _Session.model_validate(session_data).categories
                except Exception:
                    session_categories = []
                result = await asyncio.to_thread(build_paradigm_model, codes, session_categories)

                model = app.storage.user['paradigm_model']
                if result and result.phenomenon:
                    model['phenomenon'] = [result.phenomenon.name]
                if result and result.causal_conditions:
                    model['causal_conditions'] = [c.name for c in result.causal_conditions]
                if result and result.context:
                    model['context'] = [c.name for c in result.context]
                if result and result.intervening_conditions:
                    model['intervening_conditions'] = [c.name for c in result.intervening_conditions]
                if result and result.action_strategies:
                    model['strategies'] = [s.name for s in result.action_strategies]
                if result and result.consequences:
                    model['consequences'] = [c.name for c in result.consequences]
                app.storage.user['paradigm_model'] = model
                ui.notify('Analysis complete ✓', type='positive')
            except Exception as e:
                unassigned = _unassigned_codes()
                model = app.storage.user['paradigm_model']
                slots_cycle = ['causal_conditions', 'context', 'intervening_conditions', 'strategies', 'consequences']
                for i, code in enumerate(unassigned):
                    model[slots_cycle[i % len(slots_cycle)]].append(code)
                app.storage.user['paradigm_model'] = model
                ui.notify(f'Used heuristic fallback: {e}', type='warning')
            refresh_all()
            refresh_readiness()

        with ui.row().classes("gap-2").style("margin-top: 12px"):
            ui.button('Generate Pattern Analysis (AI)', icon='auto_fix_high', on_click=generate_analysis).props('size=sm').style(
                "background: var(--accent); color: white; border-radius: var(--radius-md)"
            )

            async def suggest_categories():
                import asyncio

                from grounded_evals.guide.session import Session
                from grounded_evals.open_coding.fracture import fracture_domain

                session_data = app.storage.user.get('session_data', {})
                if not session_data:
                    ui.notify('Define your agent in the Coach tab first', type='warning')
                    return
                try:
                    session = Session.model_validate(session_data)
                    if not session.agent_spec.name:
                        ui.notify('Agent name not set — go to Coach and define your agent first', type='warning')
                        return
                    suggest_btn.props('loading')
                    ui.notify('Generating category suggestions from agent spec...', type='info')
                    categories = await asyncio.to_thread(fracture_domain, session.agent_spec)

                    codebook = app.storage.user.setdefault('codebook', [])
                    existing_names = {c['name'] for c in codebook}
                    added = 0
                    from datetime import datetime
                    from uuid import uuid4
                    for cat in categories:
                        name = cat.name
                        if name not in existing_names:
                            codebook.append({
                                'id': str(uuid4()),
                                'name': name,
                                'definition': cat.definition,
                                'type': 'constructed',
                                'created_at': datetime.now().isoformat(),
                            })
                            existing_names.add(name)
                            added += 1

                    app.storage.user['codebook'] = codebook
                    ui.notify(f'Added {added} category suggestions to codebook ✓', type='positive')
                    refresh_all()
                except Exception as e:
                    ui.notify(f'Category suggestion failed: {e}', type='negative')
                finally:
                    suggest_btn.props(remove='loading')

            suggest_btn = ui.button(
                'Suggest Categories from Agent Spec', icon='category', on_click=suggest_categories
            ).props('size=sm outline').style(
                "border-color: var(--accent); color: var(--accent-bright); border-radius: var(--radius-md)"
            )

            ui.button('Audit Code Names', icon='fact_check', on_click=_show_audit_dialog).props('size=sm outline').style(
                "border-color: var(--text-tertiary); color: var(--text-secondary); border-radius: var(--radius-md)"
            )

        # ── Judge Readiness Panel ─────────────────────────────────────────────
        readiness_container = ui.column().classes("w-full").style("margin-top: 20px")

        def refresh_readiness():
            readiness_container.clear()
            all_paradigm_codes: list[str] = []
            for codes in app.storage.user['paradigm_model'].values():
                all_paradigm_codes.extend(codes)
            if not all_paradigm_codes:
                return

            matched_dims = _infer_dimensions()
            n = len(matched_dims)

            with readiness_container:
                with ui.element("div").style(
                    "background: var(--surface-2); border: 1px solid var(--border); "
                    "border-radius: var(--radius-xl); padding: 14px 16px"
                ):
                    with ui.row().classes("items-center gap-2").style("margin-bottom: 10px"):
                        ui.icon('verified').style("color: var(--accent-bright); font-size: 1.1rem")
                        ui.label('Judge Readiness').style("font-weight: 700; font-size: 0.9rem; color: var(--text-primary)")
                        ui.label('Based on your paradigm model').style("font-size: 0.72rem; color: var(--text-tertiary)")

                    ui.label(
                        f'Your failure codes suggest {n} evaluation dimension(s). '
                        'These become the criteria in your automated judge:'
                    ).style("font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 8px")

                    dim_map = {d[0]: (d[1], d[2]) for d in EVAL_DIMENSIONS}
                    with ui.row().classes("flex-wrap gap-2").style("margin-bottom: 12px"):
                        for dim_id in matched_dims:
                            label, desc = dim_map.get(dim_id, (dim_id, ''))
                            ui.html(
                                f'<span title="{desc}" style="display:inline-block;padding:3px 10px;'
                                f'border-radius:20px;font-size:0.75rem;font-weight:600;'
                                f'background:var(--accent-tint);color:var(--accent-bright);'
                                f'border:1px solid var(--accent);cursor:default">{label}</span>'
                            )
                        # Show unmatched dims as muted
                        all_dim_ids = {d[0] for d in EVAL_DIMENSIONS}
                        for dim_id in all_dim_ids - set(matched_dims):
                            label, _ = dim_map.get(dim_id, (dim_id, ''))
                            ui.html(
                                f'<span style="display:inline-block;padding:3px 10px;'
                                f'border-radius:20px;font-size:0.75rem;'
                                f'background:var(--surface-1);color:var(--text-tertiary);'
                                f'border:1px solid var(--border)">{label}</span>'
                            )

                    def go_to_judge():
                        import json
                        # Pre-seed judge with matched dimensions
                        app.storage.user['_jb_prefill_dims'] = matched_dims
                        ui.navigate.to('/judge')

                    ui.button(
                        f'Build Judge with {n} dimension(s) →',
                        icon='gavel',
                        on_click=go_to_judge,
                    ).props('size=sm').style(
                        "background: var(--accent); color: white; border-radius: var(--radius-md)"
                    )

        # Initial render
        refresh_codes()
        refresh_saturation()
        refresh_canvas()
        refresh_readiness()
