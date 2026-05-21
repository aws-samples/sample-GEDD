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


def _ensure_state():
    if 'codebook' not in app.storage.user:
        app.storage.user['codebook'] = []
    if 'paradigm_model' not in app.storage.user:
        app.storage.user['paradigm_model'] = {s: [] for s in SLOTS}
    if 'failure_patterns' not in app.storage.user:
        app.storage.user['failure_patterns'] = []


def _all_code_names():
    return [c['name'] for c in app.storage.user['codebook']]


def _assigned_codes():
    assigned = set()
    for codes in app.storage.user['paradigm_model'].values():
        assigned.update(codes)
    return assigned


def _unassigned_codes():
    return [n for n in _all_code_names() if n not in _assigned_codes()]


def _saturation_pct():
    total = len(_all_code_names())
    if total == 0:
        return 0
    return len(_assigned_codes()) / total


@ui.page('/analysis')
def analysis_page():
    _ensure_state()
    page_layout('Map Root Causes')

    with ui.column().classes('w-full max-w-5xl mx-auto').style("padding: 1.5rem"):
        # Coaching
        with ui.expansion("💡 What should I do here?", icon="help_outline").classes("w-full").style(
            "background: var(--yellow-tint); border: 1px solid rgba(240,191,0,0.15); "
            "border-radius: var(--radius-xl); margin-bottom: 1rem; color: var(--text-primary)"
        ):
            ui.label("Organize your failure codes into a causal map:").style("font-size: 0.82rem; font-weight: 500; color: var(--text-primary)")
            ui.label("• What TRIGGERS it? → Triggered By\n"
                     "• WHEN does it happen? → Occurs When\n"
                     "• What makes it WORSE? → Gets Worse If\n"
                     "• HOW does the agent fail? → Manifests As\n"
                     "• What's the USER IMPACT? → User Impact").style(
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
                    ui.html(f'<span class="code-chip">{name}</span>')

        # Saturation
        saturation_container = ui.row().classes('w-full items-center gap-3').style("margin: 10px 0")

        def refresh_saturation():
            saturation_container.clear()
            with saturation_container:
                pct = _saturation_pct()
                ui.linear_progress(value=pct).props('size=6px color=green').style("flex: 1")
                ui.label(f'{pct:.0%} assigned').style("font-size: 0.72rem; color: var(--text-tertiary)")

        # Paradigm Model Canvas
        ui.label('Paradigm Model').style("font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-top: 12px; margin-bottom: 8px")
        canvas_container = ui.column().classes('w-full gap-2')

        def make_slot_ui(slot_key, parent):
            model = app.storage.user['paradigm_model']
            codes_in_slot = model.get(slot_key, [])
            has = 'has-items' if codes_in_slot else ''
            color = SLOT_COLORS.get(slot_key, 'var(--text-tertiary)')
            with parent:
                with ui.column().classes(f'paradigm-slot {has} w-full'):
                    ui.label(SLOT_LABELS[slot_key]).style(f"font-weight: 600; font-size: 0.72rem; color: {color}; text-transform: uppercase; letter-spacing: 0.04em")
                    with ui.row().classes('flex-wrap gap-1').style("margin-top: 6px"):
                        for name in codes_in_slot:
                            def remove(n=name, s=slot_key):
                                app.storage.user['paradigm_model'][s].remove(n)
                                refresh_all()
                            ui.chip(name, color='primary', removable=True, on_click=remove).props("size=sm dark")
                    options = _unassigned_codes()
                    if options:
                        def assign(e, s=slot_key):
                            if e.value:
                                app.storage.user['paradigm_model'][s].append(e.value)
                                refresh_all()
                        ui.select(options, label='+ Assign code', on_change=assign).props('dense outlined dark').style("max-width: 200px; margin-top: 6px")

        def refresh_canvas():
            canvas_container.clear()
            with canvas_container:
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

        # AI Analysis button
        async def generate_analysis():
            codebook = app.storage.user.get('codebook', [])
            if not codebook:
                ui.notify('Add codes in Tag Failures first', type='warning')
                return
            try:
                import asyncio
                from grounded_evals.models.core import Code, CodeType
                from grounded_evals.axial_coding.paradigm import build_paradigm_model

                codes = [Code(name=c['name'], definition=c.get('definition', ''), code_type=CodeType.DESCRIPTIVE) for c in codebook]
                ui.notify('Analyzing patterns...', type='info')
                result = await asyncio.to_thread(build_paradigm_model, codes, [])

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

        ui.button('Generate Pattern Analysis (AI)', icon='auto_fix_high', on_click=generate_analysis).props('size=sm').style(
            "margin-top: 12px; background: var(--accent); color: white; border-radius: var(--radius-md)"
        )

        # Initial render
        refresh_codes()
        refresh_saturation()
        refresh_canvas()
