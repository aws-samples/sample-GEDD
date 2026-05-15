"""Axial Coding / Paradigm Model Canvas page."""

from nicegui import app, ui

from grounded_evals.ui.layout import page_layout

SLOTS = ['phenomenon', 'causal_conditions', 'context', 'intervening_conditions', 'strategies', 'consequences']
SLOT_LABELS = {
    'phenomenon': 'Phenomenon',
    'causal_conditions': 'Causal Conditions',
    'context': 'Context',
    'intervening_conditions': 'Intervening Conditions',
    'strategies': 'Strategies',
    'consequences': 'Consequences',
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


def _severity_for_code(code_name):
    codebook = app.storage.user['codebook']
    for c in codebook:
        if c['name'] == code_name:
            freq = c.get('frequency', c.get('count', 0))
            if freq >= 5:
                return 'high'
            elif freq >= 2:
                return 'medium'
            return 'low'
    return 'low'


@ui.page('/analysis')
def analysis_page():
    _ensure_state()
    page_layout('Axial Coding')

    with ui.column().classes('w-full max-w-6xl mx-auto p-4 gap-4'):
        # --- Available Codes ---
        ui.label('Available Codes').classes('section-title')
        codes_container = ui.row().classes('flex-wrap gap-1')

        def refresh_all():
            refresh_codes()
            refresh_canvas()
            refresh_saturation()
            refresh_patterns()

        def refresh_codes():
            codes_container.clear()
            with codes_container:
                for name in _unassigned_codes():
                    ui.chip(name, color='green').classes('code-chip')

        # --- Saturation Indicator ---
        ui.label('Saturation').classes('section-title')
        saturation_container = ui.column().classes('w-full')

        def refresh_saturation():
            saturation_container.clear()
            with saturation_container:
                pct = _saturation_pct()
                ui.linear_progress(value=pct).props('size=20px color=green')
                ui.label(f'{pct:.0%} of codes assigned').style('font-size:0.8rem;color:#6b7280')

        # --- Paradigm Model Canvas ---
        ui.label('Paradigm Model Canvas').classes('section-title')
        canvas_container = ui.column().classes('w-full gap-3')

        def make_slot_ui(slot_key, parent):
            model = app.storage.user['paradigm_model']
            codes_in_slot = model.get(slot_key, [])
            has = 'has-items' if codes_in_slot else ''
            with parent:
                with ui.column().classes(f'paradigm-slot {has} w-full'):
                    ui.label(SLOT_LABELS[slot_key]).style('font-weight:600;font-size:0.8rem;color:#374151')
                    with ui.row().classes('flex-wrap gap-1'):
                        for name in codes_in_slot:
                            def remove(n=name, s=slot_key):
                                app.storage.user['paradigm_model'][s].remove(n)
                                refresh_all()
                            ui.chip(name, color='green', removable=True, on_click=remove).classes('code-chip selected')
                    options = _unassigned_codes()
                    if options:
                        def assign(e, s=slot_key):
                            if e.value:
                                app.storage.user['paradigm_model'][s].append(e.value)
                                refresh_all()
                        ui.select(options, label='Assign code...', on_change=assign).props('dense outlined').classes('w-48')

        def refresh_canvas():
            canvas_container.clear()
            with canvas_container:
                # Row 1: Causal Conditions | Phenomenon | Context
                with ui.row().classes('w-full gap-3'):
                    for slot in ['causal_conditions', 'phenomenon', 'context']:
                        col = ui.column().classes('flex-1')
                        make_slot_ui(slot, col)
                # Row 2-4: full width
                for slot in ['intervening_conditions', 'strategies', 'consequences']:
                    row = ui.column().classes('w-full')
                    make_slot_ui(slot, row)

        # --- Generate Pattern Analysis Button ---
        async def generate_analysis():
            """Use LLM-powered axial coding to organize codes into paradigm model."""
            codebook = app.storage.user.get('codebook', [])
            if not codebook:
                ui.notify('Add codes in the Open Coding tab first', type='warning')
                return

            # Try LLM-powered paradigm building
            try:
                import asyncio
                from grounded_evals.models.core import Code, CodeType
                from grounded_evals.axial_coding.paradigm import build_paradigm_model

                codes = [Code(name=c['name'], definition=c.get('definition', ''), code_type=CodeType.DESCRIPTIVE) for c in codebook]
                ui.notify('Analyzing patterns with LLM...', type='info')
                result = await asyncio.to_thread(build_paradigm_model, codes, [])

                # Map result to storage format
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
                ui.notify('Pattern analysis complete ✓', type='positive')
            except Exception as e:
                # Fallback: distribute unassigned codes round-robin
                unassigned = _unassigned_codes()
                model = app.storage.user['paradigm_model']
                slots_cycle = ['causal_conditions', 'context', 'intervening_conditions', 'strategies', 'consequences']
                for i, code in enumerate(unassigned):
                    target = slots_cycle[i % len(slots_cycle)]
                    model[target].append(code)
                app.storage.user['paradigm_model'] = model
                ui.notify(f'Used heuristic fallback: {e}', type='warning')
            refresh_all()

        ui.button('Generate Pattern Analysis (AI)', icon='auto_fix_high', on_click=generate_analysis).props('color=green')

        # --- Failure Pattern Cards ---
        ui.label('Failure Patterns').classes('section-title')
        patterns_container = ui.column().classes('w-full gap-3')

        def refresh_patterns():
            patterns_container.clear()
            model = app.storage.user['paradigm_model']
            with patterns_container:
                for phenom in model.get('phenomenon', []):
                    severity = _severity_for_code(phenom)
                    sev_class = f'severity-{severity}'
                    with ui.card().classes(f'pattern-card {sev_class} w-full'):
                        ui.label(phenom).style('font-weight:700;font-size:1rem')
                        ui.badge(severity.upper(), color={'high': 'red', 'medium': 'orange', 'low': 'green'}[severity])
                        with ui.grid(columns=2).classes('w-full gap-2 mt-2'):
                            ui.label('Triggers').style('font-weight:600;font-size:0.75rem')
                            ui.label(', '.join(model.get('causal_conditions', [])) or '—').style('font-size:0.8rem')
                            ui.label('Context').style('font-weight:600;font-size:0.75rem')
                            ui.label(', '.join(model.get('context', [])) or '—').style('font-size:0.8rem')
                            ui.label('Manifests as').style('font-weight:600;font-size:0.75rem')
                            ui.label(', '.join(model.get('strategies', [])) or '—').style('font-size:0.8rem')
                            ui.label('User Impact').style('font-weight:600;font-size:0.75rem')
                            ui.label(', '.join(model.get('consequences', [])) or '—').style('font-size:0.8rem')

        # Initial render
        refresh_codes()
        refresh_saturation()
        refresh_canvas()
        refresh_patterns()
