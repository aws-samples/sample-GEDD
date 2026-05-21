"""Eval Report page — summary, failure patterns, judges, and exports."""

import csv
import io
import json
from datetime import date

from nicegui import app, ui

from grounded_evals.ui.layout import page_layout


@ui.page('/report')
def report_page():
    page_layout('Report')
    storage = app.storage.user
    session = storage.get('session_data', {})
    annotations = storage.get('annotations', [])
    codebook = storage.get('codebook', [])
    paradigm = storage.get('paradigm_model', {})
    patterns = storage.get('failure_patterns', [])

    agent_name = session.get('agent_spec', {}).get('name', 'Unknown Agent') if isinstance(session.get('agent_spec'), dict) else 'Unknown Agent'
    golden_prompts = session.get('golden_prompts', [])
    total = len(annotations)
    correct = sum(1 for a in annotations if a.get('annotation') == 'correct')
    partial = sum(1 for a in annotations if a.get('annotation') == 'partial')
    incorrect = sum(1 for a in annotations if a.get('annotation') == 'incorrect')

    with ui.column().classes('w-full max-w-5xl mx-auto').style("padding: 1.5rem; gap: 16px"):
        # Header
        with ui.element("div").classes("page-card"):
            with ui.row().classes("items-center justify-between w-full"):
                ui.label("Evaluation Report").style("font-size: 1.1rem; font-weight: 600; color: var(--text-primary)")
                ui.label(date.today().isoformat()).style("font-size: 0.75rem; color: var(--text-muted)")
            with ui.row().classes("gap-4 mt-2"):
                ui.label(f'Agent: {agent_name}').style("font-size: 0.8rem; color: var(--text-secondary)")
                ui.label(f'Queries: {len(golden_prompts)}').style("font-size: 0.8rem; color: var(--text-secondary)")

        # Stats
        with ui.row().classes('w-full gap-3'):
            stats = [
                ('Total', str(total), 'var(--text-primary)'),
                ('Correct', f'{(correct/total*100):.0f}%' if total else '0%', 'var(--green-bright)'),
                ('Partial', f'{(partial/total*100):.0f}%' if total else '0%', 'var(--yellow)'),
                ('Incorrect', f'{(incorrect/total*100):.0f}%' if total else '0%', 'var(--red)'),
            ]
            for label, value, color in stats:
                with ui.card().classes('stat-card flex-1'):
                    ui.label(value).classes('stat-value').style(f'color: {color}')
                    ui.label(label).classes('stat-label')

        # Failure Patterns
        with ui.element("div").classes("page-card"):
            ui.label('Failure Patterns').style("font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px")
            sorted_patterns = sorted(patterns, key=lambda p: p.get('frequency', 0), reverse=True)
            if sorted_patterns:
                columns = [
                    {'name': 'name', 'label': 'Pattern', 'field': 'name', 'align': 'left'},
                    {'name': 'frequency', 'label': 'Freq', 'field': 'frequency'},
                    {'name': 'severity', 'label': 'Severity', 'field': 'severity'},
                ]
                rows = [{'name': p.get('name', ''), 'frequency': p.get('frequency', 0), 'severity': p.get('severity', '')} for p in sorted_patterns]
                ui.table(columns=columns, rows=rows, row_key='name').classes('w-full').props("dark dense flat")
            else:
                ui.label('No patterns recorded yet.').style("color: var(--text-muted); font-size: 0.8rem")

        # Root Cause
        with ui.element("div").classes("page-card"):
            ui.label('Root Cause Analysis').style("font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px")
            error_counts = {}
            for a in annotations:
                code = a.get('error_code', '')
                if code:
                    error_counts[code] = error_counts.get(code, 0) + 1

            if error_counts:
                for code, count in sorted(error_counts.items(), key=lambda x: -x[1]):
                    with ui.row().classes("items-center gap-2").style("margin-bottom: 4px"):
                        ui.element("div").style(f"width: {min(count/max(error_counts.values())*100, 100)}%; height: 4px; background: var(--accent); border-radius: 2px; min-width: 20px")
                        ui.label(f"{code} ({count})").style("font-size: 0.78rem; color: var(--text-secondary)")
            else:
                ui.label('No error codes recorded yet.').style("color: var(--text-muted); font-size: 0.8rem")

        # Binary Judge Prompts
        with ui.element("div").classes("page-card"):
            ui.label('Binary LLM-as-Judge Prompts').style("font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px")
            ui.label('Auto-generated from your paradigm model.').style("font-size: 0.78rem; color: var(--text-muted); margin-bottom: 12px")

            def _gen_judge(phenomenon, causal, strategies, consequences):
                return f"""You are evaluating whether a response exhibits {phenomenon.upper()}.

Triggered by: {causal}
Manifests as: {strategies}
User impact: {consequences}

<response>{{response}}</response>

Think step by step. Score TRUE if the response exhibits this pattern. Score FALSE otherwise."""

            phenomena = paradigm.get('phenomenon', [])
            targets = phenomena if phenomena else [c['name'] for c in codebook[:5]]
            causal = ', '.join(paradigm.get('causal_conditions', [])) or 'Unknown'
            strategies_text = ', '.join(paradigm.get('strategies', [])) or 'Unknown'
            consequences_text = ', '.join(paradigm.get('consequences', [])) or 'Unknown'

            if not targets and not codebook:
                ui.label('Complete Tag Failures and Map Root Causes first.').style("color: var(--text-muted); font-size: 0.8rem")
            else:
                for target in targets:
                    prompt = _gen_judge(target, causal, strategies_text, consequences_text)
                    with ui.element("div").style(
                        "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
                        "border-radius: var(--radius-lg); padding: 12px; margin-bottom: 10px"
                    ):
                        with ui.row().classes("items-center justify-between w-full"):
                            ui.label(f'Judge: {target}').style("font-weight: 600; font-size: 0.85rem; color: var(--text-primary)")
                            ui.button('Copy', icon='content_copy', on_click=lambda _, p=prompt: ui.run_javascript(
                                f'navigator.clipboard.writeText({json.dumps(p)})'
                            )).props('flat size=sm').style("color: var(--text-tertiary)")
                        with ui.element("pre").style(
                            "background: var(--bg-base); border: 1px solid var(--border-subtle); "
                            "border-radius: var(--radius-md); padding: 10px; margin-top: 8px; "
                            "font-size: 0.7rem; color: var(--text-secondary); white-space: pre-wrap; "
                            "line-height: 1.5; max-height: 180px; overflow-y: auto; font-family: monospace"
                        ):
                            ui.label(prompt)

        # "So What?" Summary
        with ui.element("div").classes("page-card"):
            ui.label('"So What?" — Executive Summary').style("font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px")

            if total:
                pass_rate = correct / total * 100
                ui.label(f'Your agent passes {pass_rate:.0f}% of test cases ({correct}/{total} correct).').style(
                    "font-size: 0.88rem; font-weight: 500; color: var(--text-primary)"
                )
                if incorrect:
                    ui.label(f'⚠️ {incorrect} responses are incorrect ({incorrect/total*100:.0f}%).').style(
                        "font-size: 0.82rem; color: var(--red); margin-top: 4px"
                    )
            if codebook:
                top_codes = sorted(codebook, key=lambda c: c.get('frequency', c.get('count', 0)), reverse=True)[:3]
                if top_codes:
                    names = ', '.join(c['name'] for c in top_codes)
                    ui.label(f'Top failure types: {names}').style("font-size: 0.82rem; color: var(--text-secondary); margin-top: 6px")
            if paradigm.get('causal_conditions'):
                causes = paradigm['causal_conditions']
                cause_text = ', '.join(causes) if isinstance(causes[0], str) else ', '.join(c.get('name', '') for c in causes)
                ui.label(f'Root causes: {cause_text}').style("font-size: 0.82rem; color: var(--text-secondary); margin-top: 4px")
                ui.label('→ Fixing these would address multiple failure patterns.').style(
                    "font-size: 0.8rem; color: var(--green-bright); font-weight: 500; margin-top: 2px"
                )
            if not annotations:
                ui.label('Complete annotations to generate summary.').style("color: var(--text-muted); font-size: 0.8rem")

        # Exports
        with ui.element("div").classes("page-card"):
            ui.label('Export').style("font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px")
            with ui.row().classes('gap-2 flex-wrap'):
                def download_golden_csv():
                    buf = io.StringIO()
                    writer = csv.writer(buf)
                    writer.writerow(['query'])
                    for p in golden_prompts:
                        writer.writerow([p if isinstance(p, str) else p.get('query', '')])
                    ui.download(buf.getvalue().encode(), 'golden_queries.csv')

                def download_codebook():
                    ui.download(json.dumps(codebook, indent=2).encode(), 'codebook.json')

                def download_full_report():
                    report = {
                        'agent': agent_name, 'date': date.today().isoformat(),
                        'total_annotations': total, 'correct': correct, 'partial': partial, 'incorrect': incorrect,
                        'error_counts': error_counts, 'codebook': codebook, 'annotations': annotations,
                    }
                    ui.download(json.dumps(report, indent=2).encode(), 'full_report.json')

                ui.button('Golden Queries (CSV)', on_click=download_golden_csv, icon='download').props('outline size=sm dark')
                ui.button('Codebook (JSON)', on_click=download_codebook, icon='download').props('outline size=sm dark')
                ui.button('Full Report (JSON)', on_click=download_full_report, icon='download').props('outline size=sm dark')
