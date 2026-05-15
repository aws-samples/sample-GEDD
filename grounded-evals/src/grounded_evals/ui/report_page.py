"""Eval Report page — summary, failure patterns, root cause, rubric, and exports."""

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

    with ui.column().classes('w-full max-w-5xl mx-auto p-4 gap-4'):
        # 1. Report Header
        with ui.card().classes('page-card w-full'):
            ui.label('Evaluation Report').classes('section-title')
            with ui.row().classes('items-center gap-8 mt-2'):
                ui.label(f'Agent: {agent_name}').style('font-weight:600')
                ui.label(f'Date: {date.today().isoformat()}')
                ui.label('Annotators: 1')
                ui.label(f'Total Queries: {len(golden_prompts)}')
                ui.label('Inter-Annotator Agreement: N/A (single annotator)')

        # 2. Summary Stats
        with ui.row().classes('w-full gap-4'):
            for label, value, color in [
                ('Total Annotations', str(total), '#14532d'),
                ('Correct', f'{(correct/total*100):.0f}%' if total else '0%', '#16a34a'),
                ('Partial', f'{(partial/total*100):.0f}%' if total else '0%', '#d97706'),
                ('Incorrect', f'{(incorrect/total*100):.0f}%' if total else '0%', '#dc2626'),
            ]:
                with ui.card().classes('stat-card flex-1'):
                    ui.label(value).classes('stat-value').style(f'color:{color}')
                    ui.label(label).classes('stat-label')

        # 3. Top Failure Patterns
        with ui.card().classes('page-card w-full'):
            ui.label('Top Failure Patterns').classes('section-title')
            sorted_patterns = sorted(patterns, key=lambda p: p.get('frequency', 0), reverse=True)
            columns = [
                {'name': 'name', 'label': 'Pattern', 'field': 'name', 'align': 'left'},
                {'name': 'frequency', 'label': 'Frequency', 'field': 'frequency'},
                {'name': 'severity', 'label': 'Severity', 'field': 'severity'},
                {'name': 'dimension', 'label': 'Primary Dimension', 'field': 'dimension', 'align': 'left'},
            ]
            rows = [
                {'name': p.get('name', ''), 'frequency': p.get('frequency', 0),
                 'severity': p.get('severity', ''), 'dimension': p.get('dimension', '')}
                for p in sorted_patterns
            ]
            ui.table(columns=columns, rows=rows, row_key='name').classes('w-full')

        # 4. Root Cause Analysis
        with ui.card().classes('page-card w-full'):
            ui.label('Root Cause Analysis').classes('section-title')
            error_counts = {}
            for a in annotations:
                code = a.get('error_code', '')
                if code:
                    error_counts[code] = error_counts.get(code, 0) + 1

            causal_conditions = paradigm.get('causal_conditions', [])
            condition_map = {}
            for cond in causal_conditions if isinstance(causal_conditions, list) else []:
                name = cond.get('name', '') if isinstance(cond, dict) else str(cond)
                codes = cond.get('error_codes', []) if isinstance(cond, dict) else []
                count = sum(error_counts.get(c, 0) for c in codes)
                if count > 0:
                    condition_map[name] = count

            if error_counts:
                ui.label('Error Code Distribution').style('font-weight:500; margin-top:8px')
                ec_cols = [
                    {'name': 'code', 'label': 'Error Code', 'field': 'code', 'align': 'left'},
                    {'name': 'count', 'label': 'Count', 'field': 'count'},
                ]
                ec_rows = [{'code': k, 'count': v} for k, v in sorted(error_counts.items(), key=lambda x: -x[1])]
                ui.table(columns=ec_cols, rows=ec_rows, row_key='code').classes('w-full')

            if condition_map:
                ui.label('Causal Conditions Mapping').style('font-weight:500; margin-top:12px')
                for name, count in sorted(condition_map.items(), key=lambda x: -x[1]):
                    with ui.row().classes('items-center gap-2'):
                        ui.label(f'{name}:').style('font-weight:500')
                        ui.label(f'{count} failure(s)')
            elif not error_counts:
                ui.label('No annotations with error codes yet.').style('color:#6b7280')

        # 5. Generated Rubric
        with ui.card().classes('page-card w-full'):
            ui.label('Generated Rubric').classes('section-title')
            unique_codes = sorted(set(a.get('error_code', '') for a in annotations if a.get('error_code')))
            if unique_codes:
                for code in unique_codes:
                    with ui.card().classes('pattern-card'):
                        ui.label(code).style('font-weight:600')
                        ui.label(f'Pass: Response avoids {code} entirely').style('color:#16a34a; font-size:0.85rem')
                        ui.label(f'Partial: Response shows minor instances of {code}').style('color:#d97706; font-size:0.85rem')
                        ui.label(f'Fail: Response clearly exhibits {code}').style('color:#dc2626; font-size:0.85rem')
            else:
                ui.label('No error codes recorded yet.').style('color:#6b7280')

        # 6. Export Buttons
        with ui.card().classes('page-card w-full'):
            ui.label('Export').classes('section-title')
            with ui.row().classes('gap-2 mt-2'):
                def download_golden_csv():
                    buf = io.StringIO()
                    writer = csv.writer(buf)
                    writer.writerow(['query'])
                    for p in golden_prompts:
                        writer.writerow([p if isinstance(p, str) else p.get('query', '')])
                    ui.download(buf.getvalue().encode(), 'golden_queries.csv')

                def download_codebook():
                    ui.download(json.dumps(codebook, indent=2).encode(), 'codebook.json')

                def download_rubric():
                    rubric = []
                    for code in unique_codes:
                        rubric.append({
                            'criterion': code,
                            'pass': f'Response avoids {code} entirely',
                            'partial': f'Response shows minor instances of {code}',
                            'fail': f'Response clearly exhibits {code}',
                        })
                    ui.download(json.dumps(rubric, indent=2).encode(), 'rubric.yaml')

                def download_full_report():
                    report = {
                        'agent': agent_name,
                        'date': date.today().isoformat(),
                        'total_annotations': total,
                        'correct': correct, 'partial': partial, 'incorrect': incorrect,
                        'error_counts': error_counts,
                        'failure_patterns': sorted_patterns,
                        'codebook': codebook,
                        'annotations': annotations,
                    }
                    ui.download(json.dumps(report, indent=2).encode(), 'full_report.json')

                ui.button('Download Golden Queries (CSV)', on_click=download_golden_csv, icon='download').props('outline')
                ui.button('Download Codebook (JSON)', on_click=download_codebook, icon='download').props('outline')
                ui.button('Download Rubric (YAML)', on_click=download_rubric, icon='download').props('outline')
                ui.button('Download Full Report (JSON)', on_click=download_full_report, icon='download').props('outline')

        # 7. Recommendations
        with ui.card().classes('page-card w-full'):
            ui.label('Recommendations').classes('section-title')
            if condition_map:
                top_cond = max(condition_map, key=condition_map.get)
                top_pct = (condition_map[top_cond] / total * 100) if total else 0
                ui.label(f'• {top_pct:.0f}% of failures trace to "{top_cond}". Prioritize addressing this causal condition.')
            if sorted_patterns:
                top_p = sorted_patterns[0]
                ui.label(f'• Most frequent failure pattern: "{top_p.get("name", "")}" (count: {top_p.get("frequency", 0)}). Consider targeted prompt engineering.')
            if incorrect and total:
                ui.label(f'• {(incorrect/total*100):.0f}% of responses are incorrect. Review error codes for systematic issues.')
            if not annotations:
                ui.label('Complete annotations to generate recommendations.').style('color:#6b7280')
