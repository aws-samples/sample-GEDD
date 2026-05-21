"""Tag Failures (Open Coding) Annotation Workbench page."""

from datetime import datetime
from uuid import uuid4

from nicegui import app, ui

from grounded_evals.ui.layout import page_layout


def _build_responses(storage: dict) -> list[dict]:
    """Merge eval_results + annotations into a unified response list for coding.

    This removes the hard dependency on the Eval tab annotation step: unannotated
    model responses from eval_results are surfaced for coding even if the user
    skipped the ✓/⚠/✗ step in the Eval tab.
    """
    seen: set[tuple[str, str]] = set()
    result: list[dict] = []

    for a in storage.get('annotations', []):
        key = (a.get('query', ''), a.get('response', ''))
        if key not in seen:
            seen.add(key)
            result.append(a)

    for er in storage.get('eval_results', []):
        for model_id, resp_text in er.get('responses', {}).items():
            if not resp_text or resp_text.startswith('[Error:'):
                continue
            key = (er.get('query', ''), resp_text)
            if key not in seen:
                seen.add(key)
                result.append({
                    'query': er.get('query', ''),
                    'response': resp_text,
                    'annotation': er.get('annotations', {}).get(model_id, ''),
                    'model': model_id,
                    'error_code': '',
                    'notes': er.get('notes', ''),
                })

    return result


CODING_CSS = """
.coding-nav { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.coding-query-card {
  background: var(--bg-surface-2); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl); padding: 14px; margin-bottom: 8px;
}
.coding-response-card {
  background: var(--bg-surface-1); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl); padding: 14px; margin-bottom: 10px;
}
.codebook-entry {
  background: var(--bg-surface-2); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg); padding: 10px 12px; margin-bottom: 6px;
  transition: border-color 150ms ease;
}
.codebook-entry:hover { border-color: var(--border-strong); }
"""


@ui.page('/coding')
def coding_page():
    page_layout("Tag Failures")
    ui.add_head_html(f"<style>{CODING_CSS}</style>")

    # Inline coaching
    with ui.expansion("💡 What should I do here?", icon="help_outline").classes("w-full max-w-5xl mx-auto").style(
        "background: var(--yellow-tint); border: 1px solid rgba(240,191,0,0.15); "
        "border-radius: var(--radius-xl); margin-bottom: 1rem; color: var(--text-primary)"
    ):
        ui.label("Look at each agent response. Ask yourself: what's the FIRST thing that feels wrong?").style(
            "font-size: 0.82rem; font-weight: 500; color: var(--text-primary)"
        )
        ui.label("Name it in 2-3 words (e.g. 'hallucinated price', 'wrong tone'). "
                 "Don't use a predefined list — let codes emerge from what YOU observe. "
                 "If a new failure looks similar to one you've already tagged, use the same code.").style(
            "font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px"
        )

    # Initialize storage
    storage = app.storage.user
    storage.setdefault('codebook', [])
    storage.setdefault('coding_annotations', [])
    storage.setdefault('memos', [])
    storage.setdefault('annotations', [])

    responses = _build_responses(storage)
    current_idx = {'value': 0}
    selected_codes = {'value': []}

    def get_annotation_for(idx):
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
        saturation_pct = min(100, int((n_annotated / max(1, len(responses))) * 100))
        with stats_container:
            for label, value in [('Codes', n_codes), ('Annotated', n_annotated),
                                 ('Pending', n_pending), ('Memos', n_memos)]:
                with ui.card().classes('stat-card'):
                    ui.label(str(value)).classes('stat-value')
                    ui.label(label).classes('stat-label')
            with ui.card().classes('stat-card'):
                ui.linear_progress(value=saturation_pct / 100, show_value=False).props('color=green size=6px')
                ui.label(f'{saturation_pct}% Coverage').classes('stat-label').style("margin-top: 6px")

    with ui.row().classes('w-full justify-around q-mb-md max-w-5xl mx-auto') as stats_container:
        pass

    # Saturation Discovery Curve
    def render_saturation_curve():
        curve_container.clear()
        with curve_container:
            annotations_list = storage.get('coding_annotations', [])
            if len(annotations_list) < 2:
                ui.label("Complete 2+ annotations to see the saturation curve.").style("font-size: 0.78rem; color: var(--text-muted)")
                return

            seen_codes = set()
            discovery_points = []
            for i, ann in enumerate(annotations_list):
                for c in ann.get('codes', []):
                    seen_codes.add(c)
                discovery_points.append({"x": i + 1, "y": len(seen_codes)})

            recent_new = 0
            if len(annotations_list) >= 3:
                codes_before_last3 = set()
                for ann in annotations_list[:-3]:
                    for c in ann.get('codes', []):
                        codes_before_last3.add(c)
                for ann in annotations_list[-3:]:
                    for c in ann.get('codes', []):
                        if c not in codes_before_last3:
                            recent_new += 1

            chart_options = {
                "xAxis": {"type": "category", "data": [p["x"] for p in discovery_points], "name": "Annotations", "axisLine": {"lineStyle": {"color": "#4a4e55"}}},
                "yAxis": {"type": "value", "name": "Codes", "axisLine": {"lineStyle": {"color": "#4a4e55"}}, "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.05)"}}},
                "series": [{"data": [p["y"] for p in discovery_points], "type": "line", "smooth": True, "lineStyle": {"color": "#5e6ad2", "width": 2}, "itemStyle": {"color": "#828fff"}, "areaStyle": {"color": "rgba(94,106,210,0.1)"}}],
                "grid": {"top": 20, "bottom": 30, "left": 40, "right": 20},
                "tooltip": {"trigger": "axis"},
            }
            ui.echart(chart_options).style("height: 140px; width: 100%")

            if len(annotations_list) >= 3 and recent_new == 0:
                ui.label("🎯 Saturation reached — last 3 annotations revealed no new codes.").style(
                    "font-size: 0.75rem; color: var(--green-bright); font-weight: 500; margin-top: 6px"
                )
            else:
                ui.label(f"📈 Still discovering — {len(seen_codes)} codes from {len(annotations_list)} annotations.").style(
                    "font-size: 0.75rem; color: var(--yellow); margin-top: 6px"
                )

    with ui.column().classes('w-full max-w-5xl mx-auto q-mb-md') as curve_container:
        pass

    def render_left():
        left_panel.clear()
        with left_panel:
            if not responses:
                ui.label('No responses to code yet. Run an evaluation in the Eval tab first.').style("color: var(--text-tertiary)")
                return

            idx = current_idx['value']
            item = responses[idx]
            existing = get_annotation_for(idx)

            # Navigation
            with ui.element("div").classes("coding-nav"):
                ui.button(icon='chevron_left', on_click=lambda: nav(-1)).props('flat round size=sm').style("color: var(--text-tertiary)")
                ui.label(f'{idx + 1} / {len(responses)}').style("font-weight: 600; font-size: 0.85rem; color: var(--text-primary)")
                ui.button(icon='chevron_right', on_click=lambda: nav(1)).props('flat round size=sm').style("color: var(--text-tertiary)")
                if existing:
                    ui.badge('Annotated', color='green').props('outline')

            # Query
            with ui.element("div").classes("coding-query-card"):
                ui.label('QUERY').style("font-size: 0.6rem; font-weight: 600; color: var(--accent-bright); letter-spacing: 0.05em; margin-bottom: 4px")
                ui.label(item.get('query', '')).style("color: var(--text-primary); font-size: 0.85rem")

            # Response
            with ui.element("div").classes("coding-response-card"):
                ui.label('RESPONSE').style("font-size: 0.6rem; font-weight: 600; color: var(--text-tertiary); letter-spacing: 0.05em; margin-bottom: 4px")
                ui.markdown(item.get('response', '')).style("color: var(--text-secondary); font-size: 0.82rem")

            # Code chips
            ui.label('Apply Codes').style("font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-top: 8px")
            selected_codes['value'] = list(existing['codes']) if existing else []

            def toggle_code(name):
                if name in selected_codes['value']:
                    selected_codes['value'].remove(name)
                else:
                    selected_codes['value'].append(name)
                render_left()

            with ui.row().classes('w-full flex-wrap').style("margin-top: 6px"):
                for code in storage['codebook']:
                    is_selected = code['name'] in selected_codes['value']
                    cls = 'code-chip selected' if is_selected else 'code-chip'
                    ui.html(f'<span class="{cls}">{code["name"]}</span>').on('click', lambda _, n=code['name']: toggle_code(n))

            # New code
            with ui.row().classes('w-full items-center q-mt-sm gap-2'):
                new_code_input = ui.input(placeholder='New code name...').classes('flex-grow').props("dense outlined dark")
                ui.button(icon='add', on_click=lambda: add_code(new_code_input.value)).props('flat round size=sm').style("color: var(--accent-bright)")

            # Memo
            memo_input = ui.textarea(placeholder='Memo / analytic note...').classes('w-full q-mt-sm').props("dense outlined dark")

            # Save
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
                render_saturation_curve()
                render_right()
                render_left()

            ui.button('Save Annotation', icon='save', on_click=save_annotation).props('color=primary size=sm').style("margin-top: 10px")

    def render_right():
        right_panel.clear()
        with right_panel:
            ui.label('Codebook').style("font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em")
            if not storage['codebook']:
                ui.label('No codes yet. Add from the left panel.').style("font-size: 0.78rem; color: var(--text-muted); margin-top: 6px")
            for code in storage['codebook']:
                usage = sum(1 for a in storage['coding_annotations'] if code['name'] in a.get('codes', []))
                with ui.element("div").classes("codebook-entry"):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(code['name']).style("font-weight: 500; font-size: 0.82rem; color: var(--text-primary)")
                        ui.label(f'×{usage}').style("font-size: 0.7rem; color: var(--text-muted)")

                    def update_def(e, cid=code['id']):
                        for c in storage['codebook']:
                            if c['id'] == cid:
                                c['definition'] = e.value
                                break

                    ui.input(value=code.get('definition', ''), placeholder='Definition...',
                             on_change=update_def).classes('w-full').props('dense borderless dark').style("font-size: 0.75rem")

            # Memos
            ui.label('Recent Memos').style("font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-top: 16px")
            memos = storage['memos'][-5:]
            if not memos:
                ui.label('No memos yet.').style("font-size: 0.78rem; color: var(--text-muted); margin-top: 4px")
            for m in reversed(memos):
                with ui.element('div').classes('memo-box').style("margin-top: 6px"):
                    ui.label(m.get('text', '')).style("font-size: 0.78rem; color: var(--text-secondary)")

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
        """Similarity check using character n-gram overlap."""
        def _ngrams(s, n=3):
            s = s.lower().strip()
            return set(s[i:i+n] for i in range(max(0, len(s) - n + 1)))

        ng_a = _ngrams(a)
        ng_b = _ngrams(b)
        if not ng_a or not ng_b:
            return False
        jaccard = len(ng_a & ng_b) / len(ng_a | ng_b)
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        word_overlap = len(words_a & words_b) / min(len(words_a), len(words_b)) if min(len(words_a), len(words_b)) > 0 else 0
        return jaccard > 0.35 or word_overlap > 0.5

    # Main split layout
    with ui.splitter(value=60).classes('w-full max-w-5xl mx-auto').style("margin-top: 0.5rem") as splitter:
        with splitter.before:
            with ui.element('div').classes('w-full').style("padding: 12px") as left_panel:
                pass
        with splitter.after:
            with ui.element('div').classes('w-full').style("padding: 12px") as right_panel:
                pass

    # Initial render
    render_stats()
    render_saturation_curve()
    render_left()
    render_right()
