"""Open Coding Annotation Workbench page."""

from datetime import datetime
from uuid import uuid4

from nicegui import app, ui

from grounded_evals.ui.layout import page_layout


@ui.page('/coding')
def coding_page():
    page_layout("Open Coding")

    # Initialize storage
    storage = app.storage.user
    storage.setdefault('codebook', [])
    storage.setdefault('coding_annotations', [])
    storage.setdefault('memos', [])
    storage.setdefault('annotations', [])

    # Get responses to annotate from annotations list
    responses = storage.get('annotations', [])
    current_idx = {'value': 0}
    selected_codes = {'value': []}

    def get_annotation_for(idx):
        """Find existing coding annotation for a response."""
        if not responses:
            return None
        r = responses[idx]
        for a in storage['coding_annotations']:
            if a['query'] == r.get('query') and a['response'] == r.get('response'):
                return a
        return None

    # Stats bar
    def render_stats():
        stats_container.clear()
        n_codes = len(storage['codebook'])
        n_annotated = len(storage['coding_annotations'])
        n_pending = max(0, len(responses) - n_annotated)
        n_memos = len(storage['memos'])
        # Saturation: new codes per last 5 annotations
        recent = storage['coding_annotations'][-5:]
        new_codes_recent = set()
        for a in recent:
            for c in a.get('codes', []):
                new_codes_recent.add(c)
        saturation_pct = min(100, int((n_annotated / max(1, len(responses))) * 100))
        with stats_container:
            for label, value in [('Codes', n_codes), ('Annotated', n_annotated),
                                 ('Pending', n_pending), ('Memos', n_memos)]:
                with ui.card().classes('stat-card'):
                    ui.label(str(value)).classes('stat-value')
                    ui.label(label).classes('stat-label')
            with ui.card().classes('stat-card'):
                ui.linear_progress(value=saturation_pct / 100, show_value=False).props('color=green')
                ui.label(f'{saturation_pct}% Coverage').classes('stat-label')

    with ui.row().classes('w-full justify-around q-mb-md') as stats_container:
        pass

    def render_left():
        left_panel.clear()
        with left_panel:
            if not responses:
                ui.label('No responses to annotate. Complete some evaluations first.')
                return

            idx = current_idx['value']
            item = responses[idx]
            existing = get_annotation_for(idx)

            # Navigation
            with ui.row().classes('w-full items-center justify-between q-mb-sm'):
                ui.button(icon='chevron_left', on_click=lambda: nav(-1)).props('flat round').bind_enabled_from(current_idx, 'value', lambda v: v > 0)
                ui.label(f'{idx + 1} / {len(responses)}').classes('text-bold')
                ui.button(icon='chevron_right', on_click=lambda: nav(1)).props('flat round').bind_enabled_from(current_idx, 'value', lambda v: v < len(responses) - 1)

            # Query card
            with ui.card().classes('w-full q-mb-sm').style('background: #dcfce7; border: 1px solid #86efac'):
                ui.label('Query').classes('section-title')
                ui.label(item.get('query', ''))

            # Response card
            with ui.card().classes('w-full page-card q-mb-sm'):
                ui.label('Response').classes('section-title')
                ui.markdown(item.get('response', ''))

            # Verdict badge
            if existing:
                ui.badge('Annotated', color='green').props('outline')
                ui.label(f"Codes: {', '.join(existing.get('codes', []))}").classes('text-caption')

            # Code chips
            ui.label('Apply Codes').classes('section-title q-mt-md')
            selected_codes['value'] = list(existing['codes']) if existing else []

            def toggle_code(name):
                if name in selected_codes['value']:
                    selected_codes['value'].remove(name)
                else:
                    selected_codes['value'].append(name)
                render_left()

            with ui.row().classes('w-full flex-wrap'):
                for code in storage['codebook']:
                    is_selected = code['name'] in selected_codes['value']
                    cls = 'code-chip selected' if is_selected else 'code-chip'
                    ui.html(f'<span class="{cls}">{code["name"]}</span>').on('click', lambda _, n=code['name']: toggle_code(n))

            # New code input
            with ui.row().classes('w-full items-center q-mt-sm'):
                new_code_input = ui.input(placeholder='New code name').classes('flex-grow')
                ui.button(icon='add', on_click=lambda: add_code(new_code_input.value)).props('flat round')

            # Memo
            memo_input = ui.textarea(placeholder='Memo / analytic note...').classes('w-full q-mt-sm')

            # Save button
            def save_annotation():
                ann = {
                    'id': str(uuid4()),
                    'query': item.get('query', ''),
                    'response': item.get('response', ''),
                    'codes': list(selected_codes['value']),
                    'memo': memo_input.value or '',
                    'annotator': storage.get('username', 'anonymous'),
                    'timestamp': datetime.now().isoformat(),
                }
                # Replace existing or append
                storage['coding_annotations'] = [
                    a for a in storage['coding_annotations']
                    if not (a['query'] == ann['query'] and a['response'] == ann['response'])
                ]
                storage['coding_annotations'].append(ann)
                if memo_input.value:
                    storage['memos'].append({
                        'id': str(uuid4()),
                        'text': memo_input.value,
                        'codes': list(selected_codes['value']),
                        'timestamp': datetime.now().isoformat(),
                    })
                ui.notify('Annotation saved', type='positive')
                render_stats()
                render_right()
                render_left()

            ui.button('Save Annotation', icon='save', on_click=save_annotation).props('color=green').classes('q-mt-sm')

    def render_right():
        right_panel.clear()
        with right_panel:
            ui.label('Codebook').classes('section-title')
            if not storage['codebook']:
                ui.label('No codes yet. Add codes from the left panel.').classes('text-caption')
            for code in storage['codebook']:
                usage = sum(1 for a in storage['coding_annotations'] if code['name'] in a.get('codes', []))
                with ui.card().classes('w-full page-card q-mb-xs'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(code['name']).classes('text-bold')
                        type_colors = {'in_vivo': 'green', 'descriptive': 'blue', 'process': 'orange'}
                        ui.badge(code.get('type', 'in_vivo'), color=type_colors.get(code.get('type', 'in_vivo'), 'grey'))
                        ui.badge(f'×{usage}', color='grey').props('outline')
                    # Inline definition editor
                    def update_def(e, cid=code['id']):
                        for c in storage['codebook']:
                            if c['id'] == cid:
                                c['definition'] = e.value
                                break

                    ui.input(value=code.get('definition', ''), placeholder='Definition...',
                             on_change=update_def).classes('w-full').props('dense')

            # Last 5 memos
            ui.label('Recent Memos').classes('section-title q-mt-md')
            memos = storage['memos'][-5:]
            if not memos:
                ui.label('No memos yet.').classes('text-caption')
            for m in reversed(memos):
                with ui.element('div').classes('memo-box q-mb-xs'):
                    ui.label(m.get('text', '')).classes('text-caption')
                    ui.label(m.get('timestamp', '')[:16]).classes('text-caption text-grey')

    def nav(delta):
        current_idx['value'] = max(0, min(len(responses) - 1, current_idx['value'] + delta))
        render_left()

    def add_code(name):
        if not name or not name.strip():
            return
        name = name.strip()
        if any(c['name'] == name for c in storage['codebook']):
            ui.notify('Code already exists', type='warning')
            return
        # Constant comparison: check similarity to existing codes
        existing_names = [c['name'] for c in storage['codebook']]
        similar = [n for n in existing_names if _is_similar(name, n)]
        if similar:
            ui.notify(f'Similar codes exist: {", ".join(similar)}. Adding anyway.', type='info')
        storage['codebook'].append({
            'id': str(uuid4()),
            'name': name,
            'definition': '',
            'type': 'in_vivo' if name.startswith('"') or name.startswith("'") else 'descriptive',
            'created_at': datetime.now().isoformat(),
        })
        selected_codes['value'].append(name)
        render_left()
        render_right()
        render_stats()

    def _is_similar(a: str, b: str) -> bool:
        """Simple word-overlap similarity check."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return False
        overlap = len(words_a & words_b)
        return overlap / min(len(words_a), len(words_b)) > 0.5

    # Main split layout
    with ui.splitter(value=60).classes('w-full') as splitter:
        with splitter.before:
            with ui.element('div').classes('w-full q-pa-md') as left_panel:
                pass
        with splitter.after:
            with ui.element('div').classes('w-full q-pa-md') as right_panel:
                pass

    # Initial render
    render_stats()
    render_left()
    render_right()
