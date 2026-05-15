"""Agent Journey Map — clean ECharts node-graph visualization."""

from __future__ import annotations

from nicegui import ui

from grounded_evals.guide.session import Session

STAGES = [
    {"id": "define", "name": "Define\nAgent", "step": 1, "x": 80, "y": 150},
    {"id": "context", "name": "Build\nContext", "step": 2, "x": 220, "y": 150},
    {"id": "system_prompt", "name": "System\nPrompt", "step": 3, "x": 360, "y": 150},
    {"id": "golden", "name": "Golden\nQueries", "step": 4, "x": 500, "y": 150},
    {"id": "synthetic", "name": "Expand\nto 100+", "step": 5, "x": 640, "y": 150},
    {"id": "eval_run", "name": "Run\nEval", "step": 6, "x": 780, "y": 150},
    {"id": "error_analysis", "name": "Error\nAnalysis", "step": 7, "x": 920, "y": 150},
    {"id": "judge", "name": "Build\nJudge", "step": 8, "x": 1060, "y": 150},
    {"id": "deploy", "name": "Deploy", "step": 9, "x": 1200, "y": 150},
    {"id": "refine", "name": "Refine", "step": 10, "x": 1340, "y": 150},
]

EDGES = [
    {"source": "define", "target": "context"},
    {"source": "context", "target": "system_prompt"},
    {"source": "system_prompt", "target": "golden"},
    {"source": "golden", "target": "synthetic"},
    {"source": "synthetic", "target": "eval_run"},
    {"source": "eval_run", "target": "error_analysis"},
    {"source": "error_analysis", "target": "judge"},
    {"source": "judge", "target": "deploy"},
    {"source": "deploy", "target": "refine"},
    {"source": "refine", "target": "system_prompt"},
]


def get_node_color(stage_id: str, session: Session) -> str:
    if stage_id == "define" and session.agent_spec.name:
        return "#43A047"
    if stage_id == "context" and session.agent_spec.domain_context:
        return "#43A047"
    if stage_id == "system_prompt" and session.agent_spec.system_prompt:
        return "#43A047"
    if stage_id == "golden" and session.golden_prompts:
        return "#FB8C00" if len(session.golden_prompts) < 10 else "#43A047"
    if stage_id in ("define", "context", "system_prompt", "golden"):
        return "#2E7D32"
    return "#9E9E9E"


def build_chart_options(session: Session) -> dict:
    nodes = []
    for stage in STAGES:
        color = get_node_color(stage["id"], session)
        nodes.append({
            "name": stage["id"],
            "value": stage["id"],
            "x": stage["x"],
            "y": stage["y"],
            "symbolSize": [90, 45],
            "symbol": "roundRect",
            "label": {
                "show": True,
                "formatter": stage["name"],
                "fontSize": 12,
                "fontWeight": "bold",
                "color": "#fff",
            },
            "itemStyle": {
                "color": color,
                "borderRadius": 8,
            },
        })

    links = []
    for edge in EDGES:
        is_loop = edge["source"] == "refine"
        links.append({
            "source": edge["source"],
            "target": edge["target"],
            "lineStyle": {
                "color": "#FB8C00" if is_loop else "#4CAF50",
                "width": 2,
                "curveness": 0.4 if is_loop else 0,
                "type": "dashed" if is_loop else "solid",
            },
        })

    return {
        "series": [{
            "type": "graph",
            "layout": "none",
            "roam": True,
            "data": nodes,
            "links": links,
            "edgeSymbol": ["none", "arrow"],
            "edgeSymbolSize": [0, 8],
            "lineStyle": {"opacity": 0.8},
            "emphasis": {"focus": "adjacency"},
        }],
    }


def render(session: Session, on_stage_click=None) -> None:
    chart_options = build_chart_options(session)
    stage_ids = [s["id"] for s in STAGES]

    def handle_click(e):
        if on_stage_click and e.name in stage_ids:
            on_stage_click(e.name)

    chart = ui.echart(chart_options).classes("w-full").style("height: 200px")
    chart.on_point_click(handle_click)
