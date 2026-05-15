"""Shared layout and navigation for Agent Playground multi-page app."""

from nicegui import app, ui


NAV_ITEMS = [
    {"path": "/", "label": "Coach", "icon": "chat"},
    {"path": "/coding", "label": "Open Coding", "icon": "label"},
    {"path": "/analysis", "label": "Axial Coding", "icon": "hub"},
    {"path": "/report", "label": "Report", "icon": "assessment"},
]

BRAND_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root { --brand-green: #16a34a; --brand-dark: #14532d; --brand-accent: #4ade80; }
body { font-family: 'Inter', sans-serif !important; background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 50%, #f0f9ff 100%) !important; }
.brand-title { font-size: 1.4rem; font-weight: 700; background: linear-gradient(135deg, #14532d, #16a34a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.brand-subtitle { font-size: 0.75rem; color: #6b7280; }
.page-card { background: white; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.06); border: 1px solid #e5e7eb; padding: 1.5rem; }
.section-title { font-size: 0.7rem; font-weight: 600; color: #16a34a; text-transform: uppercase; letter-spacing: 0.04em; }
.code-chip { background: #dcfce7; color: #14532d; border-radius: 6px; padding: 4px 10px; font-size: 0.8rem; font-weight: 500; display: inline-block; margin: 2px; cursor: pointer; }
.code-chip:hover { background: #bbf7d0; }
.code-chip.selected { background: #16a34a; color: white; }
.paradigm-slot { border: 2px dashed #d1d5db; border-radius: 12px; min-height: 100px; padding: 12px; transition: border-color 0.2s; }
.paradigm-slot:hover { border-color: #4ade80; }
.paradigm-slot.has-items { border-style: solid; border-color: #16a34a; background: #f0fdf4; }
.pattern-card { background: white; border-radius: 12px; border-left: 4px solid #16a34a; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); margin-bottom: 12px; }
.severity-high { border-left-color: #dc2626; }
.severity-medium { border-left-color: #d97706; }
.severity-low { border-left-color: #16a34a; }
.memo-box { background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px; font-size: 0.8rem; }
.stat-card { background: white; border-radius: 12px; padding: 16px; text-align: center; border: 1px solid #e5e7eb; }
.stat-value { font-size: 1.8rem; font-weight: 700; color: #14532d; }
.stat-label { font-size: 0.7rem; color: #6b7280; text-transform: uppercase; }
"""


def page_layout(title: str = ""):
    """Apply shared page layout with navigation header."""
    ui.add_head_html(f"<style>{BRAND_CSS}</style>")

    # Top navigation bar
    with ui.header().classes("items-center justify-between").style(
        "background: white; border-bottom: 1px solid #e5e7eb; padding: 0.5rem 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,0.04)"
    ):
        with ui.row().classes("items-center gap-sm"):
            ui.html('<div class="brand-title">AI Agent Grounded Eval-Driven Development</div>')

        with ui.row().classes("items-center gap-none"):
            for item in NAV_ITEMS:
                ui.button(
                    item["label"], icon=item["icon"],
                    on_click=lambda p=item["path"]: ui.navigate.to(p),
                ).props("flat no-caps").style("color: #374151; font-weight: 500")

        def logout():
            app.storage.user["authenticated"] = False
            ui.navigate.to("/login")

        ui.button(icon="logout", on_click=logout).props("flat round size=sm").tooltip("Logout")
