"""Shared layout and navigation for Agent Playground multi-page app."""

from nicegui import app, ui


NAV_ITEMS = [
    {"path": "/", "label": "Home", "icon": "home"},
    {"path": "/coach", "label": "1. Coach", "icon": "chat"},
    {"path": "/eval", "label": "2. Eval", "icon": "science"},
    {"path": "/coding", "label": "3. Tag", "icon": "label"},
    {"path": "/analysis", "label": "4. Root Causes", "icon": "hub"},
    {"path": "/report", "label": "5. Report", "icon": "assessment"},
]

BRAND_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg-base: #08090a;
  --bg-surface-1: #0f1011;
  --bg-surface-2: #141516;
  --bg-surface-3: #191a1b;
  --bg-hover: #232326;
  --border-subtle: rgba(255,255,255,0.06);
  --border-default: rgba(255,255,255,0.09);
  --border-strong: rgba(255,255,255,0.14);
  --text-primary: #f7f8f8;
  --text-secondary: #b4b8c0;
  --text-tertiary: #6e737b;
  --text-muted: #4a4e55;
  --accent: #5e6ad2;
  --accent-bright: #828fff;
  --accent-tint: rgba(94,106,210,0.12);
  --green: #27a644;
  --green-tint: rgba(39,166,68,0.12);
  --green-bright: #4ade80;
  --yellow: #f0bf00;
  --yellow-tint: rgba(240,191,0,0.1);
  --red: #eb5757;
  --red-tint: rgba(235,87,87,0.1);
  --blue: #4ea7fc;
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-xl: 12px;
}

* { box-sizing: border-box; }

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
  background: var(--bg-base) !important;
  color: var(--text-primary) !important;
  font-size: 0.875rem;
  letter-spacing: -0.011em;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

/* Override NiceGUI/Quasar defaults */
.q-page, .q-layout, .q-page-container, .nicegui-content {
  background: var(--bg-base) !important;
  color: var(--text-primary) !important;
}
.q-card {
  background: var(--bg-surface-2) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-subtle) !important;
  box-shadow: none !important;
}
.q-field__control {
  background: var(--bg-surface-1) !important;
  color: var(--text-primary) !important;
}
.q-field__label, .q-field__native, .q-field__input {
  color: var(--text-primary) !important;
}
.q-table { background: var(--bg-surface-2) !important; color: var(--text-primary) !important; }
.q-table th { color: var(--text-tertiary) !important; border-color: var(--border-subtle) !important; }
.q-table td { color: var(--text-secondary) !important; border-color: var(--border-subtle) !important; }
.q-linear-progress__track { background: var(--bg-hover) !important; }
.q-badge { font-weight: 500; }
.q-expansion-item { background: var(--bg-surface-2) !important; border-radius: var(--radius-xl) !important; }
.q-expansion-item__container { color: var(--text-primary) !important; }
.q-item__label { color: var(--text-primary) !important; }
.q-splitter__separator { background: var(--border-subtle) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.15); }

/* Brand */
.brand-title {
  font-size: 0.9rem; font-weight: 600; color: var(--text-primary);
  letter-spacing: -0.02em;
}
.brand-subtitle { font-size: 0.75rem; color: var(--text-tertiary); }

/* Cards */
.page-card {
  background: var(--bg-surface-2);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-subtle);
  padding: 1.25rem;
  transition: border-color 150ms ease;
}
.page-card:hover { border-color: var(--border-default); }

/* Section titles */
.section-title {
  font-size: 0.7rem; font-weight: 600; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.04em;
}

/* Code chips */
.code-chip {
  background: var(--accent-tint); color: var(--accent-bright);
  border-radius: var(--radius-sm); padding: 3px 9px;
  font-size: 0.75rem; font-weight: 500;
  display: inline-block; margin: 2px; cursor: pointer;
  border: 1px solid transparent;
  transition: all 150ms ease;
}
.code-chip:hover { background: rgba(94,106,210,0.2); border-color: var(--accent); }
.code-chip.selected { background: var(--accent); color: white; }

/* Paradigm slots */
.paradigm-slot {
  border: 1px dashed var(--border-default); border-radius: var(--radius-xl);
  min-height: 90px; padding: 12px; transition: border-color 200ms ease;
  background: var(--bg-surface-1);
}
.paradigm-slot:hover { border-color: var(--accent); }
.paradigm-slot.has-items { border-style: solid; border-color: var(--green); background: var(--green-tint); }

/* Pattern cards */
.pattern-card {
  background: var(--bg-surface-2); border-radius: var(--radius-xl);
  border-left: 3px solid var(--green); padding: 14px;
  border: 1px solid var(--border-subtle); border-left: 3px solid var(--green);
  margin-bottom: 10px;
}
.severity-high { border-left-color: var(--red); }
.severity-medium { border-left-color: var(--yellow); }
.severity-low { border-left-color: var(--green); }

/* Memo box */
.memo-box {
  background: var(--yellow-tint); border: 1px solid rgba(240,191,0,0.2);
  border-radius: var(--radius-lg); padding: 10px; font-size: 0.8rem;
}

/* Stat cards */
.stat-card {
  background: var(--bg-surface-2); border-radius: var(--radius-xl);
  padding: 16px; text-align: center; border: 1px solid var(--border-subtle);
}
.stat-value { font-size: 1.6rem; font-weight: 700; color: var(--text-primary); font-variant-numeric: tabular-nums; }
.stat-label { font-size: 0.65rem; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.03em; margin-top: 2px; }

/* Buttons */
.q-btn { letter-spacing: -0.01em !important; }

/* Animations */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.animate-in { animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
.stagger-1 { animation-delay: 0s; }
.stagger-2 { animation-delay: 0.1s; opacity: 0; }
.stagger-3 { animation-delay: 0.2s; opacity: 0; }
.stagger-4 { animation-delay: 0.3s; opacity: 0; }
.stagger-5 { animation-delay: 0.4s; opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
"""


def page_layout(title: str = ""):
    """Apply shared page layout with navigation header."""
    ui.add_head_html(f"<style>{BRAND_CSS}</style>")

    with ui.header().classes("items-center justify-between").style(
        "background: rgba(8,9,10,0.85); backdrop-filter: blur(20px); "
        "border-bottom: 1px solid rgba(255,255,255,0.06); "
        "padding: 0 1.5rem; height: 48px; "
    ):
        with ui.row().classes("items-center gap-sm"):
            ui.icon("auto_awesome").style("color: var(--accent-bright); font-size: 1.1rem")
            ui.html('<span class="brand-title">GEDD</span>')

        with ui.row().classes("items-center gap-none"):
            for item in NAV_ITEMS:
                ui.button(
                    item["label"], icon=item["icon"],
                    on_click=lambda p=item["path"]: ui.navigate.to(p),
                ).props("flat no-caps size=sm").style(
                    "color: var(--text-tertiary); font-weight: 500; font-size: 0.8rem; "
                    "border-radius: 6px; padding: 4px 10px;"
                )

        def logout():
            app.storage.user["authenticated"] = False
            ui.navigate.to("/login")

        ui.button(icon="logout", on_click=logout).props("flat round size=sm").style(
            "color: var(--text-muted)"
        ).tooltip("Logout")
