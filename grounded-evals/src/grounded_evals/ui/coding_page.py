"""Tag Failures (Open Coding) Annotation Workbench page."""

import asyncio
import json
import random
import string as _string
from collections import Counter
from datetime import datetime
from uuid import uuid4

from nicegui import app, ui

from grounded_evals.ui.layout import page_layout

# ── Module-level helpers ──────────────────────────────────────────────────────

SEVERITY_WEIGHTS: dict[str, int] = {
    'cosmetic': 1, 'functional': 2, 'critical': 3, 'catastrophic': 4,
}
_VAGUE = {
    'bad', 'wrong', 'issue', 'error', 'problem', 'fail', 'failed',
    'poor', 'incorrect', 'broken', 'not', 'fix', 'failure', 'fault',
    'defect', 'mistake', 'bug',
}


def _code_quality(name: str) -> tuple[str, str, str]:
    """Return (status, message, css-color) for inline code-name validation."""
    stripped = (name or '').strip()
    if not stripped:
        return ('empty', '', 'var(--text-muted)')
    words = stripped.lower().split()
    if len(words) == 1 and words[0] in _VAGUE:
        return ('vague', 'Too vague — describe failure TYPE, e.g. "Missed escalation"', 'var(--red)')
    if all(w in _VAGUE for w in words):
        return ('vague', 'Describes symptom, not type — be more specific', 'var(--red)')
    if len(stripped) > 60:
        return ('long', 'Too long — aim for 2–4 words', 'var(--yellow)')
    if len(words) == 1:
        return ('short', 'Add one more word for context', 'var(--yellow)')
    return ('good', '✓ Good code name', 'var(--green-bright)')


def _build_responses(storage: dict) -> list[dict]:
    """Merge eval_results + annotations into a unified response list for coding."""
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


def _is_similar(a: str, b: str) -> bool:
    """Jaccard n-gram + word overlap similarity check."""
    def _ngrams(s: str, n: int = 3) -> set[str]:
        s = s.lower().strip()
        return set(s[i:i + n] for i in range(max(0, len(s) - n + 1)))
    ng_a, ng_b = _ngrams(a), _ngrams(b)
    if not ng_a or not ng_b:
        return False
    jaccard = len(ng_a & ng_b) / len(ng_a | ng_b)
    wa, wb = set(a.lower().split()), set(b.lower().split())
    word_overlap = len(wa & wb) / min(len(wa), len(wb)) if min(len(wa), len(wb)) > 0 else 0
    return jaccard > 0.35 or word_overlap > 0.5


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
.triage-card {
  background: var(--bg-surface-2); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl); padding: 12px; flex: 1; min-width: 0;
}
"""


@ui.page('/coding')
def coding_page():
    page_layout("Tag Failures")
    ui.add_head_html(f"<style>{CODING_CSS}</style>")

    with ui.expansion("💡 What should I do here?", icon="help_outline").classes("w-full max-w-5xl mx-auto").style(
        "background: var(--yellow-tint); border: 1px solid rgba(240,191,0,0.15); "
        "border-radius: var(--radius-xl); margin-bottom: 0.5rem; color: var(--text-primary)"
    ):
        ui.html(
            '<div style="font-size:0.82rem;font-weight:500;color:var(--text-primary);margin-bottom:4px">'
            "You're discovering WHY your AI fails — not just that it fails."
            '</div>'
            '<div style="font-size:0.8rem;color:var(--text-secondary);line-height:1.6">'
            "Look at each response. Ask: <em>what type of failure is this?</em> Name it in 2–3 words "
            "(e.g. 'Missed escalation', 'Wrong medication dose'). Don't use a predefined list — let codes "
            "emerge from what YOU observe. Keep going until the last 3 annotations reveal no new code types. "
            "<strong>Each code you create becomes an evaluation criterion in your automated judge.</strong>"
            '</div>'
        )

    storage = app.storage.user
    storage.setdefault('codebook', [])
    storage.setdefault('coding_annotations', [])
    storage.setdefault('memos', [])
    storage.setdefault('annotations', [])

    responses = _build_responses(storage)
    current_idx: dict = {'value': 0}
    selected_codes: dict = {'value': []}
    kb_refs: dict = {'save': None}
    filter_state: dict = {'mode': 'all', 'model': None}
    view_mode: dict = {'value': 'detailed'}

    # ── Filtering helpers ─────────────────────────────────────────────────

    def _get_filtered_responses() -> list[dict]:
        mode = filter_state['mode']
        coded_keys = {(a['query'], a['response']) for a in storage['coding_annotations']}
        danger_keys = {
            (a['query'], a['response'])
            for a in storage['coding_annotations']
            if a.get('severity') in ('critical', 'catastrophic')
        }
        if mode == 'uncoded':
            return [r for r in responses if (r.get('query', ''), r.get('response', '')) not in coded_keys]
        if mode == 'danger':
            return [r for r in responses if (r.get('query', ''), r.get('response', '')) in danger_keys]
        if mode == 'model' and filter_state.get('model'):
            return [r for r in responses if r.get('model') == filter_state['model']]
        return responses

    def get_annotation_for(idx: int):
        filtered = _get_filtered_responses()
        if not filtered or idx >= len(filtered):
            return None
        r = filtered[idx]
        for a in storage['coding_annotations']:
            if a['query'] == r.get('query') and a['response'] == r.get('response'):
                return a
        return None

    # ── Stats bar ─────────────────────────────────────────────────────────

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

    # ── Filter bar ────────────────────────────────────────────────────────

    filter_bar_el = ui.row().classes('w-full max-w-5xl mx-auto items-center flex-wrap gap-2').style(
        "margin-bottom: 8px; padding: 0 2px"
    )

    def render_filter_bar():
        filter_bar_el.clear()
        with filter_bar_el:
            coded_keys = {(a['query'], a['response']) for a in storage['coding_annotations']}
            n_uncoded = len([r for r in responses
                             if (r.get('query', ''), r.get('response', '')) not in coded_keys])
            ann_map = {(a['query'], a['response']): a for a in storage['coding_annotations']}
            n_danger = len([r for r in responses
                            if ann_map.get((r.get('query', ''), r.get('response', '')), {})
                            .get('severity', '') in ('critical', 'catastrophic')])
            cur = filter_state['mode']

            def _filter_btn(label: str, mode: str, count: int, color: str = 'var(--accent)'):
                is_active = (cur == mode) and (mode != 'model')
                bg = f"background:{color};color:white;border-color:{color}" if is_active \
                    else "background:transparent;color:var(--text-muted);border:1px solid var(--border-subtle)"
                def click(m=mode):
                    filter_state['mode'] = m
                    filter_state['model'] = None
                    current_idx['value'] = 0
                    render_filter_bar()
                    render_left()
                ui.button(f"{label} ({count})", on_click=click).props("size=xs").style(
                    f"border-radius:99px;padding:2px 12px;font-size:0.7rem;font-weight:600;{bg}"
                )

            _filter_btn('All', 'all', len(responses))
            _filter_btn('Uncoded', 'uncoded', n_uncoded, 'var(--yellow)')
            _filter_btn('🔴 Danger', 'danger', n_danger, 'var(--red)')

            models = sorted({r.get('model', '') for r in responses if r.get('model')})
            if len(models) > 1:
                ui.html('<span style="color:var(--border-default);font-size:0.8rem;margin:0 4px">|</span>')
                for m in models[:3]:
                    short = (m.split('/')[-1] if '/' in m else m)[:16]
                    is_active = filter_state.get('model') == m
                    def click_model(model=m):
                        if filter_state.get('model') == model:
                            filter_state['model'] = None
                            filter_state['mode'] = 'all'
                        else:
                            filter_state['model'] = model
                            filter_state['mode'] = 'model'
                        current_idx['value'] = 0
                        render_filter_bar()
                        render_left()
                    bg = "background:var(--blue);color:white" if is_active \
                        else "background:transparent;color:var(--text-muted);border:1px solid var(--border-subtle)"
                    ui.button(short, on_click=click_model).props("size=xs").style(
                        f"border-radius:99px;padding:2px 10px;font-size:0.7rem;{bg}"
                    )

            ui.html('<div style="flex:1"></div>')

            is_triage = view_mode['value'] == 'triage'
            def toggle_view():
                view_mode['value'] = 'triage' if view_mode['value'] == 'detailed' else 'detailed'
                render_filter_bar()
                render_left()
            style = "background:var(--accent);color:white" if is_triage \
                else "border:1px solid var(--accent);color:var(--accent-bright);background:transparent"
            ui.button(
                "⚡ Triage Mode" if not is_triage else "✎ Detailed Mode",
                on_click=toggle_view,
            ).props("size=xs").style(f"border-radius:6px;font-size:0.7rem;{style}")

    # ── Saturation curve ──────────────────────────────────────────────────

    def render_saturation_curve():
        curve_container.clear()
        with curve_container:
            annotations_list = storage.get('coding_annotations', [])
            if len(annotations_list) < 2:
                ui.label("Complete 2+ annotations to see the saturation curve.").style(
                    "font-size: 0.78rem; color: var(--text-muted)"
                )
                return

            seen_codes: set = set()
            discovery_points = []
            for i, ann in enumerate(annotations_list):
                for c in ann.get('codes', []):
                    seen_codes.add(c)
                discovery_points.append({"x": i + 1, "y": len(seen_codes)})

            sev_thresh = {'catastrophic': 6, 'critical': 5, 'functional': 3, 'cosmetic': 2}
            code_sev: dict = {}
            for ann in annotations_list:
                sev = ann.get('severity', 'functional')
                for c in ann.get('codes', []):
                    if c not in code_sev or sev_thresh.get(sev, 3) > sev_thresh.get(code_sev[c], 3):
                        code_sev[c] = sev

            total_w = saturated_w = 0.0
            for code in seen_codes:
                sev = code_sev.get(code, 'functional')
                thresh = sev_thresh.get(sev, 3)
                total_w += thresh
                count = sum(1 for a in annotations_list if code in a.get('codes', []))
                saturated_w += min(thresh, thresh * count / thresh)
            weighted_pct = (saturated_w / total_w * 100) if total_w > 0 else 0

            recent_new = 0
            if len(annotations_list) >= 3:
                prev: set = set()
                for ann in annotations_list[:-3]:
                    prev.update(ann.get('codes', []))
                for ann in annotations_list[-3:]:
                    for c in ann.get('codes', []):
                        if c not in prev:
                            recent_new += 1

            ui.echart({
                "xAxis": {"type": "category", "data": [p["x"] for p in discovery_points],
                           "name": "Annotations", "axisLine": {"lineStyle": {"color": "#4a4e55"}}},
                "yAxis": {"type": "value", "name": "Codes",
                           "axisLine": {"lineStyle": {"color": "#4a4e55"}},
                           "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.05)"}}},
                "series": [{"data": [p["y"] for p in discovery_points], "type": "line",
                             "smooth": True, "lineStyle": {"color": "#5e6ad2", "width": 2},
                             "itemStyle": {"color": "#828fff"},
                             "areaStyle": {"color": "rgba(94,106,210,0.1)"}}],
                "grid": {"top": 20, "bottom": 30, "left": 40, "right": 20},
                "tooltip": {"trigger": "axis"},
            }).style("height: 140px; width: 100%")

            with ui.row().classes("items-center gap-3").style("margin-top: 6px"):
                ui.linear_progress(value=weighted_pct / 100).props("size=6px color=green").style("flex: 1")
                ui.label(f"{weighted_pct:.0f}% weighted").style("font-size: 0.72rem; color: var(--text-tertiary)")

            if len(annotations_list) >= 3 and recent_new == 0:
                with ui.row().classes("items-center gap-3 flex-wrap").style("margin-top: 6px"):
                    ui.label("🎯 Saturation reached — last 3 annotations revealed no new codes.").style(
                        "font-size: 0.75rem; color: var(--green-bright); font-weight: 500"
                    )
                    ui.button("Map Root Causes →", icon="hub",
                              on_click=lambda: ui.navigate.to("/analysis")).props("size=xs").style(
                        "background:var(--accent);color:white;border-radius:6px;font-size:0.7rem"
                    )
            elif weighted_pct < 50:
                ui.label(f"⚠️ Critical failures need deeper exploration ({weighted_pct:.0f}% weighted coverage).").style(
                    "font-size: 0.75rem; color: var(--yellow); margin-top: 4px"
                )
            else:
                ui.label(f"📈 Still discovering — {len(seen_codes)} codes from {len(annotations_list)} annotations.").style(
                    "font-size: 0.75rem; color: var(--yellow); margin-top: 4px"
                )

            if len(discovery_points) >= 4:
                import math
                n = len(discovery_points)
                y_last = discovery_points[-1]["y"]
                y_half = discovery_points[n // 2]["y"]
                n_last = discovery_points[-1]["x"]
                n_half = discovery_points[n // 2]["x"]
                if y_half > 0 and n_half > 0 and y_last > y_half:
                    alpha = math.log(y_last / max(y_half, 1)) / math.log(n_last / max(n_half, 1))
                    alpha = min(alpha, 0.9)
                    if 0 < alpha < 1:
                        k = y_last / (n_last ** alpha) if n_last > 0 else 1
                        try:
                            n_needed = max(1, min(50, int(((y_last + 1) / k) ** (1 / alpha)) - n_last))
                            ui.label(
                                f"🔮 Forecast: ~{n_needed} more annotation(s) until next new code (α={alpha:.2f})"
                            ).style("font-size: 0.72rem; color: var(--accent-bright); margin-top: 4px")
                        except (ValueError, ZeroDivisionError, OverflowError):
                            pass

    with ui.column().classes('w-full max-w-5xl mx-auto q-mb-md') as curve_container:
        pass

    # ── Triage mode ───────────────────────────────────────────────────────

    def render_triage():
        filtered = _get_filtered_responses()
        coded_keys = {(a['query'], a['response']) for a in storage['coding_annotations']}
        uncoded = [r for r in filtered if (r.get('query', ''), r.get('response', '')) not in coded_keys]

        if not uncoded:
            with ui.column().classes("items-center gap-2").style("padding: 32px; text-align:center"):
                ui.html('<div style="font-size:2rem">🎉</div>')
                ui.html('<div style="font-size:0.88rem;color:var(--green-bright);font-weight:600">All responses in this filter are coded!</div>')
                ui.html('<div style="font-size:0.78rem;color:var(--text-muted);margin-top:4px">Switch to Detailed mode to review existing annotations.</div>')
            return

        batch = uncoded[:3]
        codebook_names = [c['name'] for c in storage['codebook']]

        ui.html(
            f'<div style="font-size:0.7rem;font-weight:600;color:var(--text-tertiary);'
            f'text-transform:uppercase;letter-spacing:0.04em;margin-bottom:10px">'
            f'⚡ Triage — {len(uncoded)} uncoded remaining — annotating {len(batch)} at once'
            f'</div>'
        )

        # Each triage card gets its own closed-over state
        triage_states: list[dict] = [{'codes': [], 'sev_ref': None} for _ in batch]

        with ui.row().classes("w-full gap-2").style("align-items: flex-start"):
            for card_i, item in enumerate(batch):
                state = triage_states[card_i]

                def make_card(it=item, st=state, ci=card_i):
                    with ui.element("div").classes("triage-card"):
                        q = it.get('query', '')
                        ui.html(
                            f'<div style="font-size:0.62rem;font-weight:600;color:var(--accent-bright);'
                            f'letter-spacing:0.04em;margin-bottom:3px">QUERY</div>'
                            f'<div style="font-size:0.78rem;color:var(--text-primary);margin-bottom:8px">'
                            f'{q[:120]}{"…" if len(q)>120 else ""}</div>'
                        )
                        r_text = it.get('response', '')
                        ui.html(
                            f'<div style="font-size:0.62rem;font-weight:600;color:var(--text-tertiary);'
                            f'letter-spacing:0.04em;margin-bottom:3px">RESPONSE</div>'
                            f'<div style="font-size:0.75rem;color:var(--text-secondary);margin-bottom:8px;line-height:1.5">'
                            f'{r_text[:300]}{"…" if len(r_text)>300 else ""}</div>'
                        )

                        if codebook_names:
                            ui.html('<div style="font-size:0.62rem;font-weight:600;color:var(--text-tertiary);margin-bottom:4px">CODES</div>')
                            with ui.row().classes("flex-wrap gap-1").style("margin-bottom:8px"):
                                for cn in codebook_names:
                                    def make_toggle(name=cn, s=st):
                                        def toggle():
                                            if name in s['codes']:
                                                s['codes'].remove(name)
                                            else:
                                                s['codes'].append(name)
                                            render_left()
                                        return toggle
                                    is_sel = cn in st['codes']
                                    cls = 'code-chip selected' if is_sel else 'code-chip'
                                    ui.html(f'<span class="{cls}" style="font-size:0.65rem;padding:2px 7px;cursor:pointer">{cn}</span>').on('click', make_toggle())
                        else:
                            ui.html('<div style="font-size:0.72rem;color:var(--text-muted);margin-bottom:8px">Add codes in Detailed mode first.</div>')

                        sev_sel = ui.select(
                            {'cosmetic': '🟢 Cosmetic', 'functional': '🟡 Functional',
                             'critical': '🔴 Critical', 'catastrophic': '⚫ Catastrophic'},
                            value='functional', label='Severity',
                        ).props("dense outlined dark").style("font-size:0.72rem;margin-bottom:6px")
                        st['sev_ref'] = sev_sel

                        def make_save(it2=it, st2=st):
                            def do_save():
                                if not st2['codes']:
                                    ui.notify('Select at least one code', type='warning')
                                    return
                                ann = {
                                    'id': str(uuid4()),
                                    'query': it2.get('query', ''),
                                    'response': it2.get('response', ''),
                                    'codes': list(st2['codes']),
                                    'memo': '',
                                    'severity': st2['sev_ref'].value if st2['sev_ref'] else 'functional',
                                    'confidence': 'medium',
                                    'annotator': storage.get('username', 'anonymous'),
                                    'timestamp': datetime.now().isoformat(),
                                }
                                storage['coding_annotations'] = [
                                    a for a in storage['coding_annotations']
                                    if not (a['query'] == ann['query'] and a['response'] == ann['response'])
                                ]
                                storage['coding_annotations'].append(ann)
                                ui.notify('Saved ✓', type='positive')
                                render_stats()
                                render_saturation_curve()
                                render_filter_bar()
                                render_right()
                                render_left()
                            return do_save

                        ui.button('Save', icon='save', on_click=make_save()).props('size=xs color=primary')

                make_card()

    # ── Left panel (detailed mode) ────────────────────────────────────────

    def render_left():
        left_panel.clear()
        with left_panel:
            if view_mode['value'] == 'triage':
                render_triage()
                return

            filtered = _get_filtered_responses()

            if not responses:
                with ui.column().classes("items-start gap-2"):
                    ui.label('No responses to code yet. Run an evaluation first.').style("color: var(--text-tertiary)")
                    ui.button("Go to Eval", icon="arrow_forward",
                              on_click=lambda: ui.navigate.to("/eval")).props("size=sm color=primary")
                return

            if not filtered:
                with ui.column().classes("items-start gap-2"):
                    ui.label('No responses match this filter.').style("color: var(--text-tertiary)")
                    ui.button("Show All", on_click=lambda: [
                        filter_state.update({'mode': 'all', 'model': None}),
                        current_idx.update({'value': 0}),
                        render_filter_bar(), render_left(),
                    ]).props("size=sm color=primary")
                return

            if current_idx['value'] >= len(filtered):
                current_idx['value'] = max(0, len(filtered) - 1)

            idx = current_idx['value']
            item = filtered[idx]
            existing = get_annotation_for(idx)

            # Navigation
            with ui.element("div").classes("coding-nav"):
                ui.button(icon='chevron_left', on_click=lambda: nav(-1)).props('flat round size=sm').style("color: var(--text-tertiary)")
                ui.label(f'{idx + 1} / {len(filtered)}').style("font-weight: 600; font-size: 0.85rem; color: var(--text-primary)")
                ui.button(icon='chevron_right', on_click=lambda: nav(1)).props('flat round size=sm').style("color: var(--text-tertiary)")
                if existing:
                    annotator = existing.get('annotator', '')
                    ts = existing.get('timestamp', '')[:10]
                    label_text = f'By {annotator}' if annotator and annotator != 'anonymous' else 'Annotated'
                    ui.badge(label_text, color='green').props('outline').tooltip(ts)
                if filter_state['mode'] != 'all':
                    mode_labels = {'uncoded': 'Uncoded', 'danger': '🔴 Danger',
                                   'model': (filter_state.get('model') or '')[:14]}
                    tag = mode_labels.get(filter_state['mode'], '')
                    if tag:
                        ui.html(f'<span style="font-size:0.62rem;padding:2px 7px;border-radius:99px;background:var(--accent-tint);color:var(--accent-bright)">{tag}</span>')

            ui.html(
                '<div style="font-size:0.62rem;color:var(--text-muted);margin-bottom:6px">'
                '← → navigate &nbsp;·&nbsp; S save &nbsp;·&nbsp; 1/2/3 quick code'
                '</div>'
            )

            with ui.element("div").classes("coding-query-card"):
                ui.label('QUERY').style("font-size: 0.6rem; font-weight: 600; color: var(--accent-bright); letter-spacing: 0.05em; margin-bottom: 4px")
                ui.label(item.get('query', '')).style("color: var(--text-primary); font-size: 0.85rem")

            with ui.element("div").classes("coding-response-card"):
                ui.label('RESPONSE').style("font-size: 0.6rem; font-weight: 600; color: var(--text-tertiary); letter-spacing: 0.05em; margin-bottom: 4px")
                ui.markdown(item.get('response', '')).style("color: var(--text-secondary); font-size: 0.82rem")

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

            # New code input with quality guardrail
            quality_label = ui.html('').style("font-size:0.68rem;margin-left:2px;height:16px;margin-top:2px")
            with ui.row().classes('w-full items-center q-mt-sm gap-2'):
                new_code_input = ui.input(placeholder='New code name…').classes('flex-grow').props("dense outlined dark")
                ui.button(icon='add', on_click=lambda: add_code(new_code_input.value)).props('flat round size=sm').style("color: var(--accent-bright)")

            def on_code_input(e):
                name = e.value or ''
                status, msg, color = _code_quality(name)
                quality_label.set_content(
                    f'<span style="color:{color}">{msg}</span>' if status != 'empty' else ''
                )
            new_code_input.on('input', on_code_input)

            memo_input = ui.textarea(placeholder='Memo / analytic note…').classes('w-full q-mt-sm').props("dense outlined dark")

            ui.label('Impact Severity').style("font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-top: 8px")
            severity_options = {
                'cosmetic':     '🟢 Cosmetic — user notices but isn\'t blocked',
                'functional':   '🟡 Functional — user has to retry or work around',
                'critical':     '🔴 Critical — wrong info, loses money/trust',
                'catastrophic': '⚫ Catastrophic — safety, legal, data breach',
            }
            existing_severity = existing.get('severity', 'functional') if existing else 'functional'
            severity_select = ui.select(
                options=severity_options, value=existing_severity, label='How bad if this reaches a user?'
            ).props("dense outlined dark").classes("w-full").style("margin-top: 4px")

            confidence_options = {
                'high': '✓ High — clearly a failure',
                'medium': '~ Medium — probably a failure',
                'low': '? Low — not sure',
            }
            existing_confidence = existing.get('confidence', 'high') if existing else 'high'
            confidence_select = ui.select(
                options=confidence_options, value=existing_confidence, label='How confident are you?'
            ).props("dense outlined dark").classes("w-full").style("margin-top: 4px")

            def save_annotation():
                ann = {
                    'id': str(uuid4()),
                    'query': item.get('query', ''),
                    'response': item.get('response', ''),
                    'codes': list(selected_codes['value']),
                    'memo': memo_input.value or '',
                    'severity': severity_select.value,
                    'confidence': confidence_select.value,
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
                render_filter_bar()
                render_right()
                render_left()

                n_anns = len(storage['coding_annotations'])
                if n_anns > 0 and n_anns % 5 == 0:
                    with ui.dialog() as reflection_dlg:
                        reflection_dlg.open()
                        with ui.card().style(
                            "min-width: 400px; padding: 1.5rem; background: var(--bg-surface-2); "
                            "border: 1px solid var(--border-subtle); border-radius: 12px"
                        ):
                            ui.label("🪞 Quick Reflection").style("font-size: 1rem; font-weight: 600; color: var(--text-primary)")
                            ui.label(f"You've completed {n_anns} annotations. Take 30 seconds:").style(
                                "font-size: 0.8rem; color: var(--text-tertiary); margin: 6px 0 12px"
                            )
                            r_input1 = ui.input(placeholder="What pattern is emerging that you didn't expect?").classes("w-full").props("dense outlined dark")
                            r_input2 = ui.input(placeholder="Any failure you expected to see but haven't?").classes("w-full").props("dense outlined dark")

                            def save_reflection():
                                texts = [r_input1.value, r_input2.value]
                                combined = ' | '.join(t for t in texts if t.strip())
                                if combined:
                                    storage['memos'].append({
                                        'id': str(uuid4()),
                                        'text': f"[Reflection @{n_anns}] {combined}",
                                        'codes': [],
                                        'timestamp': datetime.now().isoformat(),
                                    })
                                reflection_dlg.close()
                                ui.notify("Reflection saved ✓", type="positive")
                                render_right()

                            with ui.row().classes("gap-2").style("margin-top: 12px"):
                                ui.button("Save & Continue", on_click=save_reflection).props("size=sm").style("background: var(--accent); color: white")
                                ui.button("Skip", on_click=reflection_dlg.close).props("flat size=sm").style("color: var(--text-muted)")

            kb_refs['save'] = save_annotation

            with ui.row().classes("gap-2 items-center").style("margin-top: 10px"):
                ui.button('Save', icon='save', on_click=save_annotation).props('color=primary size=sm')

                async def apply_to_similar():
                    codes = list(selected_codes['value'])
                    if not codes:
                        ui.notify('Select codes first', type='warning')
                        return
                    current_text = item.get('response', '')
                    applied = 0
                    for i2, r2 in enumerate(responses):
                        if _is_similar(current_text[:80], r2.get('response', '')[:80]):
                            existing2 = None
                            for a in storage['coding_annotations']:
                                if a['query'] == r2.get('query') and a['response'] == r2.get('response'):
                                    existing2 = a
                                    break
                            merged = list(set((existing2.get('codes', []) if existing2 else []) + codes))
                            ann2 = {
                                'id': str(uuid4()),
                                'query': r2.get('query', ''),
                                'response': r2.get('response', ''),
                                'codes': merged,
                                'memo': 'Bulk-applied from similar response',
                                'annotator': storage.get('username', 'anonymous'),
                                'timestamp': datetime.now().isoformat(),
                            }
                            storage['coding_annotations'] = [
                                a for a in storage['coding_annotations']
                                if not (a['query'] == ann2['query'] and a['response'] == ann2['response'])
                            ]
                            storage['coding_annotations'].append(ann2)
                            applied += 1
                    if applied:
                        ui.notify(f'Applied to {applied} similar response(s)', type='positive')
                        render_stats()
                    else:
                        ui.notify('No similar responses found', type='info')

                ui.button('Apply to Similar', icon='auto_fix_normal', on_click=apply_to_similar).props(
                    'outline size=sm dark'
                ).style('color:var(--accent-bright); font-size:0.75rem')

    # ── Right panel ───────────────────────────────────────────────────────

    def render_right():
        right_panel.clear()
        with right_panel:

            # ── Priority Matrix ───────────────────────────────────────────
            ann_list = storage.get('coding_annotations', [])
            codebook_now = storage.get('codebook', [])
            if len(codebook_now) >= 2 and ann_list:
                code_freq: Counter = Counter()
                code_max_sev: dict = {}
                for ann in ann_list:
                    sw = SEVERITY_WEIGHTS.get(ann.get('severity', 'functional'), 2)
                    for c in ann.get('codes', []):
                        code_freq[c] += 1
                        code_max_sev[c] = max(code_max_sev.get(c, 0), sw)

                scatter_data = [
                    {'value': [code_freq.get(c['name'], 0), code_max_sev.get(c['name'], 1)],
                     'name': c['name'],
                     'symbolSize': max(8, min(28, 6 + code_freq.get(c['name'], 0) * 3))}
                    for c in codebook_now
                ]
                if any(d['value'][0] > 0 for d in scatter_data):
                    max_freq = max(d['value'][0] for d in scatter_data)
                    mid_x = max(1.0, max_freq / 2)
                    color_fn = (
                        f"function(p){{var x=p.data.value[0],y=p.data.value[1],mx={mid_x},my=2.5;"
                        "if(x>=mx&&y>=my)return'#eb5757';"
                        "if(x<mx&&y>=my)return'#f2c94c';"
                        "if(x>=mx&&y<my)return'#5e6ad2';"
                        "return'#4a4e55';}}"
                    )
                    ui.html(
                        '<div style="font-size:0.7rem;font-weight:600;color:var(--text-tertiary);'
                        'text-transform:uppercase;letter-spacing:0.04em;margin-bottom:2px">Priority Matrix</div>'
                        '<div style="font-size:0.63rem;color:var(--text-muted);margin-bottom:4px">'
                        'X = frequency · Y = severity · hover for name</div>'
                    )
                    ui.echart({
                        "tooltip": {"formatter": "function(p){return'<b>'+p.data.name+'</b><br/>Freq: '+p.data.value[0]+'&nbsp; Sev: '+['','Cosmetic','Functional','Critical','Catastrophic'][p.data.value[1]]}"},
                        "xAxis": {"type": "value", "name": "Frequency", "min": 0, "max": max_freq + 1,
                                  "splitLine": {"show": False}, "axisLine": {"lineStyle": {"color": "#4a4e55"}},
                                  "axisLabel": {"color": "#666", "fontSize": 9}},
                        "yAxis": {"type": "value", "min": 0, "max": 5, "splitLine": {"show": False},
                                  "axisLine": {"lineStyle": {"color": "#4a4e55"}},
                                  "axisLabel": {"formatter": "function(v){return['','C','F','!','!!'][v]||''}", "color": "#666", "fontSize": 9}},
                        "series": [{"type": "scatter", "data": scatter_data,
                                    "label": {"show": len(scatter_data) <= 7,
                                              "formatter": "function(p){return p.data.name.split(' ').slice(0,2).join(' ')}",
                                              "color": "#999", "fontSize": 8, "position": "top"},
                                    "itemStyle": {"color": color_fn, "opacity": 0.85}}],
                        "markLine": {"silent": True, "lineStyle": {"color": "rgba(255,255,255,0.08)", "type": "dashed"},
                                     "data": [{"xAxis": mid_x}, {"yAxis": 2.5}]},
                        "grid": {"top": 10, "bottom": 28, "left": 28, "right": 8},
                        "backgroundColor": "transparent",
                    }).style("height: 155px; width: 100%")
                    ui.html(
                        '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:2px;margin-bottom:2px">'
                        '<span style="font-size:0.6rem;color:#eb5757">■ Fix Now</span>'
                        '<span style="font-size:0.6rem;color:#f2c94c">■ Investigate</span>'
                        '<span style="font-size:0.6rem;color:#5e6ad2">■ Easy Wins</span>'
                        '<span style="font-size:0.6rem;color:#4a4e55">■ Noise</span>'
                        '</div>'
                    )
                    ui.separator().style("opacity:0.1;margin:10px 0")

            # ── Codebook ──────────────────────────────────────────────────
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

                    ui.input(value=code.get('definition', ''), placeholder='Definition…',
                             on_change=update_def).classes('w-full').props('dense borderless dark').style("font-size: 0.75rem")

            # ── Memos ─────────────────────────────────────────────────────
            ui.label('Recent Memos').style("font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-top: 16px")
            memos = storage['memos'][-5:]
            if not memos:
                ui.label('No memos yet.').style("font-size: 0.78rem; color: var(--text-muted); margin-top: 4px")
            for m in reversed(memos):
                with ui.element('div').classes('memo-box').style("margin-top: 6px"):
                    ui.label(m.get('text', '')).style("font-size: 0.78rem; color: var(--text-secondary)")

            # ── Merge suggestions with action buttons ─────────────────────
            if len(storage['codebook']) >= 4:
                ui.separator().style("opacity:0.12; margin:14px 0")
                ui.label('Suggested Merges').style(
                    "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                    "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px"
                )
                codes_list = storage['codebook']
                merge_suggestions: list[tuple[str, str]] = []
                for i2 in range(len(codes_list)):
                    for j in range(i2 + 1, len(codes_list)):
                        if _is_similar(codes_list[i2]['name'], codes_list[j]['name']):
                            merge_suggestions.append((codes_list[i2]['name'], codes_list[j]['name']))
                co_occur: dict = {}
                for ann in storage['coding_annotations']:
                    ac = ann.get('codes', [])
                    for c1 in ac:
                        for c2 in ac:
                            if c1 < c2:
                                co_occur[(c1, c2)] = co_occur.get((c1, c2), 0) + 1
                for pair, cnt in co_occur.items():
                    if cnt >= 2 and pair not in merge_suggestions:
                        merge_suggestions.append(pair)

                if merge_suggestions:
                    for c1, c2 in merge_suggestions[:3]:
                        with ui.element("div").style(
                            "background:var(--accent-tint);border:1px solid rgba(94,106,210,0.2);"
                            "border-radius:6px;padding:6px 10px;margin-bottom:6px"
                        ):
                            with ui.row().classes("items-center justify-between gap-2"):
                                ui.label(f'🔗 "{c1}" ↔ "{c2}"').style("font-size:0.72rem;color:var(--accent-bright);flex:1")

                                def do_merge(a=c1, b=c2):
                                    n_affected = sum(1 for ann in storage['coding_annotations'] if a in ann.get('codes', []))
                                    with ui.dialog() as d:
                                        d.open()
                                        with ui.card().style("min-width:280px;padding:1.2rem;background:var(--bg-surface-2)"):
                                            ui.label(f'Merge "{a}" → "{b}"?').style(
                                                "font-size:0.85rem;font-weight:600;color:var(--text-primary)"
                                            )
                                            ui.label(
                                                f'{n_affected} annotation(s) tagged "{a}" will be relabeled to "{b}". '
                                                f'"{a}" will be removed from the codebook.'
                                            ).style("font-size:0.75rem;color:var(--text-muted);margin:6px 0")

                                            def confirm_merge(d=d, a=a, b=b):
                                                storage['codebook'] = [c for c in storage['codebook'] if c['name'] != a]
                                                for ann in storage['coding_annotations']:
                                                    if a in ann.get('codes', []):
                                                        ann['codes'] = list(dict.fromkeys(
                                                            b if c == a else c for c in ann['codes']
                                                        ))
                                                storage['coding_annotations'] = list(storage['coding_annotations'])
                                                d.close()
                                                ui.notify(f'Merged "{a}" → "{b}" ✓', type='positive')
                                                render_right()
                                                render_left()
                                                render_stats()

                                            with ui.row().classes("gap-2").style("margin-top:12px"):
                                                ui.button("Merge", on_click=confirm_merge).props("size=sm").style("background:var(--accent);color:white")
                                                ui.button("Cancel", on_click=d.close).props("flat size=sm").style("color:var(--text-muted)")

                                ui.button("Merge", icon="merge", on_click=do_merge).props("size=xs flat").style(
                                    "color:var(--accent-bright);padding:0 4px;min-width:unset"
                                )
                else:
                    ui.label("No merge suggestions yet. Keep coding!").style("font-size: 0.72rem; color: var(--text-muted)")

            # ── AI Pre-labeling ───────────────────────────────────────────
            ui.separator().style("opacity:0.12; margin:14px 0")
            pre_label_result = ui.column().classes("w-full")

            async def pre_label_uncoded():
                codebook_data = storage.get('codebook', [])
                if len(codebook_data) < 3:
                    ui.notify('Add at least 3 codes first', type='warning')
                    return
                coded_keys = {(a['query'], a['response']) for a in storage['coding_annotations']}
                uncoded = [r for r in responses if (r.get('query', ''), r.get('response', '')) not in coded_keys]
                if not uncoded:
                    ui.notify('All responses are already coded ✓', type='info')
                    return
                pre_label_btn.props('loading')
                pre_label_result.clear()
                with pre_label_result:
                    ui.html('<div style="font-size:0.75rem;color:var(--text-muted)">Running AI pre-labeling…</div>')
                try:
                    from grounded_evals.llm.client import get_default_client, get_model_id
                    import json as _json
                    client = get_default_client()
                    model_id = get_model_id()
                    code_list = "\n".join(f"- {c['name']}: {c.get('definition','')}" for c in codebook_data)
                    suggestions: list[dict] = []
                    for it in uncoded[:8]:
                        prompt = (
                            f"Annotate this AI agent response with failure codes from the codebook.\n\n"
                            f"Codebook:\n{code_list}\n\n"
                            f"Query: {it.get('query','')[:300]}\n"
                            f"Response: {it.get('response','')[:500]}\n\n"
                            f"Which codes apply? Return only JSON: "
                            f'{{\"codes\": [\"...\"], \"confidence\": \"high|medium|low\", \"severity\": \"cosmetic|functional|critical|catastrophic\"}}'
                            f" Use only exact code names from the codebook. If none apply, return {{\"codes\": []}}."
                        )
                        try:
                            msg = await asyncio.to_thread(
                                client.messages.create, model=model_id, max_tokens=256,
                                messages=[{"role": "user", "content": prompt}],
                            )
                            raw = msg.content[0].text
                            js = raw.find('{'); je = raw.rfind('}') + 1
                            data = _json.loads(raw[js:je]) if js >= 0 and je > js else {}
                            valid = [c for c in data.get('codes', []) if any(cb['name'] == c for cb in codebook_data)]
                            if valid:
                                suggestions.append({
                                    'item': it, 'codes': valid,
                                    'confidence': data.get('confidence', 'medium'),
                                    'severity': data.get('severity', 'functional'),
                                })
                        except Exception:
                            pass

                    pre_label_result.clear()
                    with pre_label_result:
                        if not suggestions:
                            ui.html('<div style="font-size:0.75rem;color:var(--text-muted)">No suggestions generated — check credentials or add more defined codes.</div>')
                        else:
                            ui.html(
                                f'<div style="font-size:0.7rem;font-weight:600;color:var(--text-tertiary);'
                                f'text-transform:uppercase;margin-bottom:6px">AI Suggestions ({len(suggestions)} of {len(uncoded)} uncoded)</div>'
                            )
                            for s in suggestions[:5]:
                                with ui.element("div").style(
                                    "background:var(--bg-surface-1);border:1px solid var(--border-subtle);"
                                    "border-radius:8px;padding:8px 10px;margin-bottom:6px"
                                ):
                                    q_trunc = s['item'].get('query', '')[:70]
                                    ui.html(f'<div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:4px">{q_trunc}…</div>')
                                    conf_color = 'var(--green-bright)' if s['confidence'] == 'high' else 'var(--yellow)'
                                    with ui.row().classes("items-center gap-2 flex-wrap"):
                                        for cn in s['codes']:
                                            ui.html(f'<span class="code-chip" style="font-size:0.65rem;padding:2px 7px">{cn}</span>')
                                        ui.html(f'<span style="font-size:0.62rem;color:{conf_color}">{s["confidence"]}</span>')

                                    def accept(sug=s):
                                        ann = {
                                            'id': str(uuid4()),
                                            'query': sug['item'].get('query', ''),
                                            'response': sug['item'].get('response', ''),
                                            'codes': sug['codes'],
                                            'memo': '[AI pre-labeled]',
                                            'severity': sug['severity'],
                                            'confidence': sug['confidence'],
                                            'annotator': 'ai',
                                            'timestamp': datetime.now().isoformat(),
                                        }
                                        storage['coding_annotations'] = [
                                            a for a in storage['coding_annotations']
                                            if not (a['query'] == ann['query'] and a['response'] == ann['response'])
                                        ]
                                        storage['coding_annotations'].append(ann)
                                        ui.notify('Accepted ✓', type='positive')
                                        render_stats()
                                        render_saturation_curve()
                                        render_filter_bar()
                                        render_right()
                                        render_left()

                                    ui.button('Accept', icon='check', on_click=accept).props('size=xs color=positive').style("margin-top:4px")

                except Exception as e:
                    pre_label_result.clear()
                    with pre_label_result:
                        ui.html(f'<div style="font-size:0.75rem;color:var(--red)">Pre-labeling failed: {e}<br><span style="font-size:0.68rem;color:var(--text-muted)">Check ANTHROPIC_API_KEY or AWS credentials.</span></div>')
                finally:
                    pre_label_btn.props(remove='loading')

            pre_label_btn = ui.button(
                'Pre-Label Uncoded (AI)', icon='smart_toy', on_click=pre_label_uncoded,
            ).props('size=sm outline dark').style(
                'color:var(--accent-bright);width:100%;font-size:0.75rem'
            )

            # ── Export / Share / Import ───────────────────────────────────
            ui.separator().style("opacity:0.12; margin:14px 0")
            ui.label('Share Annotations').style(
                "font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); "
                "text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px"
            )

            def export_coding():
                data = {
                    'annotator': storage.get('email', 'anonymous'),
                    'exported_at': datetime.now().isoformat(),
                    'codebook': storage['codebook'],
                    'coding_annotations': storage['coding_annotations'],
                }
                ui.download(json.dumps(data, indent=2).encode(), 'coding_annotations.json')

            ui.button('Export Annotations', icon='download', on_click=export_coding).props(
                'size=sm outline dark'
            ).style('color:var(--accent-bright); width:100%; margin-bottom:6px')

            def generate_share():
                if not storage['coding_annotations']:
                    ui.notify('No annotations to share yet', type='warning')
                    return
                code = ''.join(random.choices(_string.ascii_uppercase + _string.digits, k=6))
                data = {
                    'annotator': storage.get('email', 'anonymous'),
                    'shared_at': datetime.now().isoformat(),
                    'codebook': storage['codebook'],
                    'coding_annotations': storage['coding_annotations'],
                }
                app.storage.general[f'coding_share_{code}'] = data
                with ui.dialog() as dlg:
                    dlg.open()
                    with ui.card().style('min-width:280px; padding:1.5rem; background:var(--bg-surface-2)'):
                        ui.label('Coding Share Code').style('font-size:0.7rem; color:var(--text-tertiary); text-transform:uppercase')
                        ui.label(code).style('font-size:2rem; font-weight:700; color:var(--accent-bright); letter-spacing:0.12em; margin:6px 0')
                        ui.label('Teammates can import using this code below.').style('font-size:0.78rem; color:var(--text-secondary)')
                        ui.button('Copy', on_click=lambda: ui.run_javascript(f"navigator.clipboard.writeText('{code}')")).props('size=sm color=primary')

            ui.button('Share by Code', icon='share', on_click=generate_share).props(
                'size=sm outline dark'
            ).style('color:var(--green-bright); width:100%; margin-bottom:10px')

            ui.label('Import from Teammate').style(
                "font-size: 0.65rem; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom:6px"
            )
            shared_container = ui.column().classes('w-full')

            def render_shared_comparison():
                shared = storage.get('shared_coding_annotations')
                if not shared:
                    return
                shared_container.clear()
                with shared_container:
                    annotator = shared.get('annotator', 'Unknown')
                    ext_anns = shared.get('coding_annotations', [])
                    my_anns = {(a['query'], a['response']): a.get('codes', []) for a in storage['coding_annotations']}
                    agree = total_cmp = 0
                    for ext in ext_anns:
                        key = (ext.get('query', ''), ext.get('response', ''))
                        if key in my_anns:
                            total_cmp += 1
                            if set(ext.get('codes', [])) & set(my_anns[key]):
                                agree += 1
                    with ui.card().style('background:var(--accent-tint); border:1px solid var(--accent); border-radius:8px; padding:10px; margin-top:6px'):
                        ui.label(f"Loaded from {annotator}").style("font-size:0.75rem; font-weight:600; color:var(--accent-bright)")
                        ui.label(f"{len(ext_anns)} annotations · {len(shared.get('codebook',[]))} codes").style("font-size:0.7rem; color:var(--text-tertiary)")
                        if total_cmp:
                            pct = agree / total_cmp * 100
                            color = 'var(--green-bright)' if pct >= 70 else ('var(--yellow)' if pct >= 50 else 'var(--red)')
                            ui.label(f"Code overlap: {pct:.0f}% ({agree}/{total_cmp})").style(f"font-size:0.78rem; font-weight:600; color:{color}; margin-top:4px")

            with ui.row().classes('w-full items-center gap-1').style("margin-bottom:4px"):
                code_in = ui.input(placeholder='6-char code').props('dense outlined dark').style('flex:1; font-size:0.8rem')

                def load_by_code():
                    code = code_in.value.strip().upper()
                    data = app.storage.general.get(f'coding_share_{code}')
                    if not data:
                        ui.notify('Code not found', type='negative')
                        return
                    storage['shared_coding_annotations'] = data
                    render_shared_comparison()
                    ui.notify(f"Loaded annotations from {data.get('annotator','?')}", type='positive')

                ui.button(icon='input', on_click=load_by_code).props('flat round size=sm').style('color:var(--accent-bright)')

            def handle_coding_upload(e):
                try:
                    data = json.loads(e.content.read())
                    storage['shared_coding_annotations'] = data
                    render_shared_comparison()
                    ui.notify(f"Imported annotations from {data.get('annotator','?')}", type='positive')
                except Exception as ex:
                    ui.notify(f'Parse error: {ex}', type='negative')

            ui.upload(
                label='Upload JSON', on_upload=handle_coding_upload, auto_upload=True,
            ).props('accept=.json flat dense dark').style('font-size:0.75rem; color:var(--text-tertiary)')

            render_shared_comparison()

    # ── Nav + keyboard ────────────────────────────────────────────────────

    def nav(delta):
        filtered = _get_filtered_responses()
        current_idx['value'] = max(0, min(len(filtered) - 1, current_idx['value'] + delta))
        render_left()

    async def add_code(name):
        if not name or not name.strip():
            return
        name = name.strip()
        if any(c['name'] == name for c in storage['codebook']):
            ui.notify('Code already exists', type='warning')
            return
        status, msg, _ = _code_quality(name)
        if status == 'vague':
            ui.notify(f'Code quality: {msg}', type='warning', timeout=5000)
        existing_names = [c['name'] for c in storage['codebook']]
        similar = [n for n in existing_names if _is_similar(name, n)]
        if similar:
            ui.notify(f'Similar codes exist: {", ".join(similar)}. Adding anyway.', type='info')
        storage['codebook'].append({
            'id': str(uuid4()),
            'name': name,
            'definition': '',
            'type': 'in_vivo' if name.startswith(('"', "'")) else 'descriptive',
            'created_at': datetime.now().isoformat(),
        })
        selected_codes['value'].append(name)
        render_left()
        render_right()
        render_stats()
        if len(existing_names) >= 2:
            try:
                from grounded_evals.open_coding.compare import compare_codes
                result = await asyncio.to_thread(compare_codes, name, existing_names)
                if result.similar_codes:
                    note = f"'{name}' may overlap with: {', '.join(result.similar_codes)}"
                    if result.merge_suggestion:
                        note += f" — consider merging as '{result.merge_suggestion}'"
                    ui.notify(note, type='warning', timeout=10000)
            except Exception:
                pass

    # Main split layout
    with ui.splitter(value=60).classes('w-full max-w-5xl mx-auto').style("margin-top: 0.5rem") as splitter:
        with splitter.before:
            with ui.element('div').classes('w-full').style("padding: 12px") as left_panel:
                pass
        with splitter.after:
            with ui.element('div').classes('w-full').style("padding: 12px") as right_panel:
                pass

    def handle_key(e):
        key = e.key
        if key == 'ArrowRight':
            nav(1)
        elif key == 'ArrowLeft':
            nav(-1)
        elif key.lower() == 's':
            if kb_refs.get('save'):
                kb_refs['save']()
        elif key in ('1', '2', '3'):
            codebook = storage.get('codebook', [])
            try:
                code_idx = int(key) - 1
                if code_idx < len(codebook):
                    n = codebook[code_idx]['name']
                    if n in selected_codes['value']:
                        selected_codes['value'].remove(n)
                    else:
                        selected_codes['value'].append(n)
                    render_left()
            except (ValueError, IndexError):
                pass

    ui.keyboard(on_key=handle_key, ignore=['input', 'select', 'textarea', 'button'])

    render_stats()
    render_filter_bar()
    render_saturation_curve()
    render_left()
    render_right()
