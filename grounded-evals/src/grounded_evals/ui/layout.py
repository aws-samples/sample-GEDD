"""Shared layout and navigation for Agent Playground multi-page app."""

import json

from nicegui import app, ui

NAV_ITEMS = [
    {"path": "/", "label": "Home", "icon": "dashboard"},
    {"path": "/demos", "label": "Scenarios", "icon": "collections_bookmark", "featured": True},
    {"path": "/coding", "label": "Annotate", "icon": "label", "core": True},
    {"path": "/analysis", "label": "Patterns", "icon": "hub", "core": True},
    {"path": "/judge", "label": "Judge", "icon": "gavel", "core": True},
    {"path": "/report", "label": "Report", "icon": "assessment", "core": True},
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
.brand-stack { display: flex; flex-direction: column; gap: 0; line-height: 1.05; }
.brand-context {
  font-size: 0.62rem; color: var(--text-tertiary);
  letter-spacing: 0.05em; text-transform: uppercase;
}

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

.app-header {
  min-height: 48px;
}
.app-nav-row {
  flex: 1;
  justify-content: center;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.app-nav-row::-webkit-scrollbar { display: none; }
.app-action-row {
  flex-shrink: 0;
}
.scenario-nav-btn {
  color: var(--accent-bright) !important;
  background: var(--accent-tint) !important;
  border: 1px solid rgba(94,106,210,0.22) !important;
}
.scenario-nav-btn:hover {
  background: rgba(94,106,210,0.2) !important;
  border-color: var(--accent) !important;
}
.core-nav-btn {
  color: var(--text-secondary) !important;
}

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

@media (max-width: 900px) {
  .app-header {
    height: auto !important;
    min-height: 48px;
    padding: 0.35rem 0.75rem !important;
    gap: 0.35rem;
    flex-wrap: wrap;
  }
  .app-nav-row {
    order: 3;
    width: 100%;
    justify-content: flex-start;
    padding-bottom: 0.1rem;
  }
  .app-nav-row .q-btn {
    flex-shrink: 0;
  }
}

/* ── Coach page ──────────────────────────────────────────────────────── */
.chat-card { background: var(--bg-surface-2); border-radius: 12px; border: 1px solid var(--border-subtle); }
.msg-user { background: var(--accent-tint); border: 1px solid rgba(94,106,210,0.2); border-radius: 10px; padding: 12px 16px; margin: 6px 0; color: var(--text-primary); }
.msg-ai { background: var(--bg-surface-1); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 12px 16px; margin: 6px 0; border-left: 3px solid var(--accent); color: var(--text-secondary); }
.msg-ai strong { color: var(--text-primary); }
.msg-error { background: var(--red-tint); border: 1px solid rgba(235,87,87,0.2); border-radius: 10px; padding: 12px 16px; margin: 6px 0; border-left: 3px solid var(--red); color: var(--text-secondary); }
.input-box { border-radius: 10px !important; background: var(--bg-surface-1) !important; border: 1px solid var(--border-default) !important; font-size: 0.88rem !important; color: var(--text-primary) !important; transition: border-color 150ms ease !important; }
.input-box:focus-within { border-color: var(--accent) !important; }
.send-btn { background: var(--accent) !important; color: white !important; transition: opacity 150ms ease !important; }
.send-btn:hover { opacity: 0.85 !important; }

/* Progress tracker */
.progress-track { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; margin-bottom: 1rem; background: var(--bg-surface-2); border-radius: 10px; border: 1px solid var(--border-subtle); }
.progress-dot { display: flex; flex-direction: column; align-items: center; flex: 1; }
.dot-circle { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.72rem; font-weight: 600; background: var(--bg-hover); color: var(--text-muted); transition: all 0.3s ease; }
.progress-dot.active .dot-circle { background: var(--green-tint); color: var(--green-bright); }
.progress-dot.current .dot-circle { background: var(--accent); color: white; box-shadow: 0 0 12px rgba(94,106,210,0.4); }
.dot-label { font-size: 0.6rem; color: var(--text-muted); margin-top: 4px; font-weight: 500; }
.progress-dot.active .dot-label { color: var(--green-bright); }
.progress-dot.current .dot-label { color: var(--accent-bright); font-weight: 600; }

/* Sidebar */
.sidebar-panel { width: 320px; min-width: 320px; padding: 1.25rem 1rem; background: var(--bg-surface-2); border-radius: 12px; border: 1px solid var(--border-subtle); height: fit-content; position: sticky; top: 1rem; max-height: 90vh; overflow-y: auto; }
.sidebar-section { margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid var(--border-subtle); }
.sidebar-section:last-child { border-bottom: none; }
.sidebar-title { font-size: 0.65rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; }
.sidebar-value { font-size: 0.85rem; font-weight: 600; color: var(--text-primary); }
.sidebar-detail { font-size: 0.75rem; color: var(--text-secondary); line-height: 1.4; }
.sidebar-empty { font-size: 0.75rem; color: var(--text-muted); }

/* Annotation labels */
.annotation-correct { color: var(--green-bright); }
.annotation-partial { color: var(--yellow); }
.annotation-incorrect { color: var(--red); }
"""


def page_layout(title: str = ""):
    """Apply shared page layout with navigation header."""
    ui.add_head_html(f"<style>{BRAND_CSS}</style>")

    with ui.header().classes("app-header items-center justify-between").style(
        "background: rgba(8,9,10,0.85); backdrop-filter: blur(20px); "
        "border-bottom: 1px solid rgba(255,255,255,0.06); "
        "padding: 0 1.5rem; height: 48px; "
    ):
        with ui.row().classes("items-center gap-sm"):
            ui.icon("rate_review").style("color: var(--accent-bright); font-size: 1.1rem")
            ui.html(
                '<span class="brand-stack">'
                '<span class="brand-title">GEDD</span>'
                '<span class="brand-context">AI PM Eval Workbench</span>'
                '</span>'
            )

        with ui.row().classes("app-nav-row items-center gap-none"):
            for item in NAV_ITEMS:
                button = ui.button(
                    item["label"], icon=item["icon"],
                    on_click=lambda p=item["path"]: ui.navigate.to(p),
                ).props("flat no-caps size=sm")
                if item.get("featured"):
                    button.classes("scenario-nav-btn").tooltip("Open the scenario library")
                elif item.get("core"):
                    button.classes("core-nav-btn")
                button.style(
                    "color: var(--text-tertiary); font-weight: 500; font-size: 0.8rem; "
                    "border-radius: 6px; padding: 4px 10px;"
                )

        def logout():
            app.storage.user["authenticated"] = False
            ui.navigate.to("/login")

        def confirm_new_project():
            with ui.dialog() as dlg:
                dlg.open()
                with ui.card().style(
                    "min-width:320px; padding:1.5rem; background:var(--bg-surface-2); "
                    "border:1px solid var(--border-default); border-radius:12px"
                ):
                    ui.label("Start a New Project?").style(
                        "font-size:1rem; font-weight:600; color:var(--text-primary); margin-bottom:8px"
                    )
                    ui.label(
                        "This will clear your current session — agent definition, golden queries, "
                        "annotations, codebook, and all analysis. This cannot be undone."
                    ).style("font-size:0.82rem; color:var(--text-secondary); margin-bottom:16px")
                    with ui.row().classes("gap-2 justify-end"):
                        ui.button("Cancel", on_click=dlg.close).props("flat size=sm dark").style(
                            "color:var(--text-tertiary)"
                        )
                        def do_reset():
                            keys_to_clear = [
                                "session_data", "current_step", "annotations", "messages",
                                "prompt_variants", "codebook", "coding_annotations", "memos",
                                "paradigm_model", "failure_patterns", "eval_results",
                                "eval_selected_models", "_eval_judge_results",
                                "_generated_judge_prompt", "custom_annotation_labels",
                                "shared_eval_results", "shared_annotator",
                            ]
                            for key in keys_to_clear:
                                app.storage.user.pop(key, None)
                            dlg.close()
                            ui.navigate.to("/")
                        ui.button("Start Fresh", icon="refresh", on_click=do_reset).props(
                            "size=sm color=negative"
                        )

        def open_session_dialog():
            with ui.dialog() as dlg:
                dlg.open()
                with ui.card().style(
                    "min-width:380px; padding:1.5rem; background:var(--bg-surface-2); "
                    "border:1px solid var(--border-default); border-radius:12px"
                ):
                    ui.label("Report Handoff").style(
                        "font-size:1rem; font-weight:600; color:var(--text-primary); "
                        "margin-bottom:8px"
                    )
                    ui.label(
                        "Export the evidence bundle behind the release report, or import a saved PM review session."
                    ).style("font-size:0.82rem; color:var(--text-secondary); margin-bottom:16px")

                    def export_session():
                        from grounded_evals.agent.tools import StateBundle
                        from grounded_evals.guide.session import Session
                        from grounded_evals.guide.session_io import (
                            build_session_payload,
                            validate_session_handoff,
                        )

                        storage = app.storage.user
                        session = Session.model_validate(storage.get("session_data", {}))
                        state = StateBundle(
                            session=session,
                            annotations=storage.get("annotations", []),
                            current_step=storage.get("current_step", session.current_step),
                            prompt_variants=storage.get("prompt_variants", []),
                        )
                        payload = build_session_payload(state, storage.get("messages", []))
                        validation = validate_session_handoff(state)
                        payload["handoff_validation"] = {
                            "errors": validation.errors,
                            "warnings": validation.warnings,
                        }
                        agent_name = (
                            session.agent_spec.name or "agent"
                        ).lower().replace(" ", "_")
                        ui.download(
                            json.dumps(payload, indent=2).encode(),
                            f"{agent_name}_handoff_session.json",
                        )

                    def import_session(e):
                        from grounded_evals.guide.session import Session

                        try:
                            payload = json.loads(e.content.read().decode())
                            session = Session.model_validate(payload["session"])
                        except Exception as exc:
                            ui.notify(f"Import failed: {exc}", type="negative")
                            return

                        storage = app.storage.user
                        storage["session_data"] = session.model_dump(mode="json")
                        storage["current_step"] = payload.get(
                            "current_step", session.current_step
                        )
                        storage["annotations"] = payload.get("annotations", [])
                        storage["messages"] = payload.get("messages", [])
                        storage["prompt_variants"] = payload.get("prompt_variants", [])
                        ui.notify("Session imported", type="positive")
                        dlg.close()
                        ui.navigate.to("/")

                    with ui.row().classes("gap-2 items-center"):
                        ui.button("Export", icon="download", on_click=export_session).props(
                            "size=sm outline dark"
                        )
                        ui.upload(
                            label="Import",
                            on_upload=import_session,
                            auto_upload=True,
                        ).props("accept=.json dense color=primary")

        with ui.row().classes("app-action-row items-center gap-none"):
            ui.button(icon="add_circle_outline", on_click=confirm_new_project).props(
                "flat round size=sm"
            ).style("color: var(--text-muted)").tooltip("New Project")

            ui.button(icon="ios_share", on_click=open_session_dialog).props(
                "flat round size=sm"
            ).style("color: var(--text-muted)").tooltip("Report Handoff")

            ui.button(icon="logout", on_click=logout).props("flat round size=sm").style(
                "color: var(--text-muted)"
            ).tooltip("Logout")
