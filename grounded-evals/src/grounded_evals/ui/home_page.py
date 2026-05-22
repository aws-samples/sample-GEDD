"""Home page — GEDD workflow with interactive product demo."""

from nicegui import app, ui

from grounded_evals.ui.layout import BRAND_CSS


def _get_progress(storage: dict) -> dict[str, str]:
    """Return done/current/todo for each workflow path based on real session state."""
    session = storage.get("session_data") or {}
    agent_spec = session.get("agent_spec", {}) if isinstance(session, dict) else {}
    if not isinstance(agent_spec, dict):
        agent_spec = {}

    has_agent = bool(agent_spec.get("name"))
    has_prompt = bool(agent_spec.get("system_prompt"))
    has_queries = bool(session.get("golden_prompts") if isinstance(session, dict) else False)
    has_eval = bool(storage.get("eval_results"))
    has_annotations = bool(storage.get("coding_annotations"))
    has_paradigm = any(v for v in storage.get("paradigm_model", {}).values())

    coach_done = has_agent and has_prompt and has_queries

    return {
        "/coach": "done" if coach_done else ("current" if has_agent else "todo"),
        "/eval": "done" if has_eval else ("current" if coach_done else "todo"),
        "/coding": "done" if has_annotations else ("current" if has_eval else "todo"),
        "/analysis": "done" if has_paradigm else ("current" if has_annotations else "todo"),
        "/report": "current" if has_paradigm else ("todo" if not has_annotations else "current"),
    }

PROBLEM_STEPS = [
    {"num": 1, "title": "Define the Job", "desc": "What is your agent trying to accomplish? For whom?", "path": "/coach", "icon": "chat"},
    {"num": 2, "title": "Observe Behavior", "desc": "Run golden queries — see what actually happens", "path": "/eval", "icon": "science"},
    {"num": 3, "title": "Tag Failures", "desc": "Name failure patterns from real outputs", "path": "/coding", "icon": "label"},
    {"num": 4, "title": "Map Root Causes", "desc": "Understand WHY failures happen", "path": "/analysis", "icon": "hub"},
]

SOLUTION_STEPS = [
    {"num": 5, "title": "Build the Eval", "desc": "Generate judges grounded in what you discovered", "path": "/report", "icon": "assessment"},
]

# --- Demo data ---
DEMO_TRACES = [
    {"query": "Book me a flight from NYC to London next Tuesday", "response": "I found a great flight on United Airlines departing at 8:30 PM for $450.", "verdict": "correct", "icon": "check_circle"},
    {"query": "I need the cheapest option, I'm allergic to peanuts", "response": "The cheapest is $320 on BudgetAir. I've noted your peanut allergy.", "verdict": "incorrect", "icon": "cancel", "why": "BudgetAir doesn't exist — hallucinated airline"},
    {"query": "Cancel my booking from last week", "response": "I've cancelled booking #TRV-4821 and initiated a refund to card ending 3291.", "verdict": "incorrect", "icon": "cancel", "why": "Fabricated booking number and card details"},
    {"query": "What's the baggage policy?", "response": "You're allowed one carry-on. Checked bags are $35 each.", "verdict": "partial", "icon": "warning", "why": "Guessed pricing without verification"},
]

DEMO_CODES = [
    {"name": "Hallucinated Entity", "count": 2, "color": "var(--red)"},
    {"name": "Fabricated User Data", "count": 1, "color": "var(--yellow)"},
    {"name": "Unverified Claim", "count": 1, "color": "var(--yellow)"},
    {"name": "Confident Confabulation", "count": 3, "color": "var(--red)"},
]

DEMO_PARADIGM = {
    "phenomenon": "Confident Confabulation",
    "causal": "No tool call to verify data",
    "context": "User asks about specific details (prices, IDs)",
    "intervening": "Worse with urgency; better when user asks 'are you sure?'",
    "strategies": "States fabricated details as fact without disclaimers",
    "consequences": "User trusts false info → wrong booking or missed refund",
}

DEMO_JUDGE = """You are evaluating whether a response exhibits CONFIDENT CONFABULATION.

Triggered by: Agent has no tool access to verify details but responds as if it does.
Manifests as: Stating specific numbers/names/IDs without hedging or disclaimers.

<response>{response}</response>

Score TRUE if the response states unverifiable details as fact.
Score FALSE if it hedges, asks for clarification, or only states verifiable info."""

HOME_CSS = """
.home-hero { text-align: center; padding: 3rem 0 2rem; }
.home-hero h1 {
  font-size: 2.2rem; font-weight: 700; color: var(--text-primary);
  letter-spacing: -0.03em; line-height: 1.2; margin: 0;
}
.home-hero p { font-size: 0.95rem; color: var(--text-tertiary); margin-top: 0.5rem; }

.demo-box {
  background: var(--bg-surface-1); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl); padding: 1.5rem; margin-top: 1.5rem;
}
.demo-nav {
  display: flex; gap: 4px; padding: 4px; background: var(--bg-surface-2);
  border-radius: var(--radius-lg); border: 1px solid var(--border-subtle);
  margin-bottom: 1.25rem;
}
.demo-nav-btn {
  flex: 1; padding: 8px 12px; border-radius: var(--radius-md);
  font-size: 0.75rem; font-weight: 500; cursor: pointer;
  transition: all 150ms ease; border: none; text-align: center;
  color: var(--text-tertiary); background: transparent;
}
.demo-nav-btn:hover { color: var(--text-secondary); background: var(--bg-hover); }
.demo-nav-btn.active {
  background: var(--accent); color: white;
  box-shadow: 0 2px 8px rgba(94,106,210,0.3);
}

.demo-content { min-height: 280px; }

.trace-row {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 10px 12px; border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle); margin-bottom: 6px;
  background: var(--bg-surface-2); transition: border-color 150ms ease;
}
.trace-row:hover { border-color: var(--border-strong); }
.trace-icon-ok { color: var(--green); }
.trace-icon-err { color: var(--red); }
.trace-icon-warn { color: var(--yellow); }

.code-tag {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 10px; border-radius: var(--radius-md);
  background: var(--bg-surface-2); border: 1px solid var(--border-subtle);
  font-size: 0.78rem; margin: 3px;
}
.code-tag .dot { width: 7px; height: 7px; border-radius: 50%; }

.paradigm-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
}
.paradigm-cell {
  padding: 10px 12px; border-radius: var(--radius-lg);
  background: var(--bg-surface-2); border: 1px solid var(--border-subtle);
}
.paradigm-cell-label {
  font-size: 0.65rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.04em; margin-bottom: 4px;
}
.paradigm-cell-value { font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4; }

.judge-block {
  background: var(--bg-surface-2); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg); padding: 14px;
  font-family: 'SF Mono', 'Menlo', monospace; font-size: 0.72rem;
  color: var(--text-secondary); line-height: 1.6; white-space: pre-wrap;
}

.workflow-card {
  padding: 14px 16px; border-radius: var(--radius-xl);
  border: 1px solid var(--border-subtle); background: var(--bg-surface-2);
  cursor: pointer; transition: all 150ms ease; margin-bottom: 8px;
}
.workflow-card:hover { border-color: var(--border-strong); background: var(--bg-surface-3); transform: translateX(4px); }

.section-badge {
  font-size: 0.6rem; font-weight: 600; letter-spacing: 0.1em;
  padding: 3px 9px; border-radius: 99px; display: inline-block;
}

.insight-box {
  background: var(--yellow-tint); border: 1px solid rgba(240,191,0,0.15);
  border-radius: var(--radius-lg); padding: 12px 14px; margin-top: 12px;
  font-size: 0.78rem; color: var(--yellow);
}

.metric-row { display: flex; align-items: baseline; gap: 8px; margin-top: 10px; }
.metric-big { font-size: 1.5rem; font-weight: 700; color: var(--green-bright); font-variant-numeric: tabular-nums; }
.metric-label { font-size: 0.78rem; color: var(--text-tertiary); }
"""


def _render_demo():
    """Interactive end-to-end demo with step navigation."""
    demo_step = {"value": 0}

    with ui.element("div").classes("demo-box"):
        # Header
        with ui.row().classes("items-center justify-between w-full").style("margin-bottom: 12px"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("play_circle").style("color: var(--accent-bright); font-size: 1.1rem")
                ui.label("See GEDD in Action").style("font-weight: 600; font-size: 0.95rem; color: var(--text-primary)")
            ui.label("TravelBot — flight booking assistant").style("font-size: 0.78rem; color: var(--text-tertiary)")

        # Step nav
        step_labels = ["Define", "Observe", "Tag", "Root Cause", "Judge"]
        nav_row = ui.element("div").classes("demo-nav")
        content = ui.element("div").classes("demo-content")

        def render_step(idx):
            demo_step["value"] = idx
            nav_row.clear()
            with nav_row:
                for i, label in enumerate(step_labels):
                    cls = "demo-nav-btn active" if i == idx else "demo-nav-btn"
                    ui.html(f'<button class="{cls}" onclick="void(0)">{i+1}. {label}</button>').on("click", lambda _, si=i: render_step(si))

            content.clear()
            with content:
                [_step_define, _step_observe, _step_tag, _step_root_cause, _step_judge][idx]()

        def _step_define():
            ui.label("What are we evaluating?").style("font-weight: 600; color: var(--text-primary); margin-bottom: 10px")
            fields = [
                ("Agent", "TravelBot — flight booking assistant", "smart_toy"),
                ("Users", "Consumers booking personal travel", "people"),
                ("Tools", "Flight search API, booking API, user profile DB", "build"),
                ("Risk", "Users trust agent with real money and travel plans", "warning"),
            ]
            for label, value, icon in fields:
                with ui.row().classes("items-center gap-3").style("margin-bottom: 8px"):
                    ui.icon(icon).style("color: var(--accent-bright); font-size: 1rem")
                    ui.label(f"{label}:").style("font-weight: 600; font-size: 0.8rem; color: var(--text-tertiary); min-width: 45px")
                    ui.label(value).style("font-size: 0.82rem; color: var(--text-secondary)")
            with ui.element("div").classes("insight-box"):
                ui.label("💡 This grounds everything. You can't evaluate what you haven't defined.")

        def _step_observe():
            ui.label("Run queries. See what happens.").style("font-weight: 600; color: var(--text-primary); margin-bottom: 10px")
            for t in DEMO_TRACES:
                icon_cls = {"correct": "trace-icon-ok", "incorrect": "trace-icon-err", "partial": "trace-icon-warn"}[t["verdict"]]
                with ui.element("div").classes("trace-row"):
                    ui.icon(t["icon"]).classes(icon_cls).style("font-size: 1.1rem; margin-top: 2px")
                    with ui.column().style("gap: 2px; flex: 1"):
                        ui.label(t["query"]).style("font-size: 0.8rem; font-weight: 500; color: var(--text-primary)")
                        ui.label(t["response"]).style("font-size: 0.75rem; color: var(--text-tertiary)")
                        if t.get("why"):
                            ui.label(f"↳ {t['why']}").style("font-size: 0.72rem; color: var(--red)")
            with ui.element("div").classes("insight-box"):
                ui.label("💡 3/4 responses have issues. Without systematic observation, you'd miss the pattern.")

        def _step_tag():
            ui.label("Name what you see. Let codes emerge.").style("font-weight: 600; color: var(--text-primary); margin-bottom: 10px")
            with ui.row().classes("flex-wrap"):
                for code in DEMO_CODES:
                    with ui.element("span").classes("code-tag"):
                        ui.html(f'<span class="dot" style="background:{code["color"]}"></span>')
                        ui.label(f'{code["name"]} ×{code["count"]}').style("color: var(--text-secondary)")

            # Mini saturation curve
            with ui.element("div").style("margin-top: 16px; padding: 12px; background: var(--bg-surface-2); border-radius: var(--radius-lg); border: 1px solid var(--border-subtle)"):
                ui.label("Saturation Curve").style("font-size: 0.65rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em")
                with ui.row().classes("items-end gap-1").style("height: 50px; margin-top: 8px; align-items: flex-end"):
                    heights = [20, 35, 42, 48]
                    for i, h in enumerate(heights):
                        ui.element("div").style(
                            f"width: 32px; height: {h}px; background: var(--accent); border-radius: 3px 3px 0 0; opacity: {0.5 + i*0.15}"
                        )
                    # Projected (dashed)
                    ui.element("div").style(
                        "width: 32px; height: 50px; border: 1px dashed var(--text-muted); border-radius: 3px 3px 0 0; background: transparent"
                    )
                ui.label("Still discovering — 4 codes from 4 traces. Keep going.").style("font-size: 0.72rem; color: var(--yellow); margin-top: 6px")

            with ui.element("div").classes("insight-box"):
                ui.label("💡 Codes emerge from YOUR data, not a generic taxonomy. That's what makes them actionable.")

        def _step_root_cause():
            ui.label("Don't just list failures — understand WHY.").style("font-weight: 600; color: var(--text-primary); margin-bottom: 10px")
            # Phenomenon highlight
            with ui.element("div").style(
                "padding: 10px 14px; border-radius: var(--radius-lg); "
                "background: var(--accent-tint); border: 1px solid var(--accent); margin-bottom: 10px"
            ):
                ui.label("PHENOMENON").style("font-size: 0.6rem; font-weight: 600; color: var(--accent-bright); letter-spacing: 0.06em")
                ui.label(DEMO_PARADIGM["phenomenon"]).style("font-size: 0.95rem; font-weight: 600; color: var(--text-primary); margin-top: 2px")

            grid_items = [
                ("Triggered by", DEMO_PARADIGM["causal"], "var(--red)"),
                ("Occurs when", DEMO_PARADIGM["context"], "var(--blue)"),
                ("Gets worse if", DEMO_PARADIGM["intervening"], "var(--yellow)"),
                ("Manifests as", DEMO_PARADIGM["strategies"], "var(--text-secondary)"),
                ("User impact", DEMO_PARADIGM["consequences"], "var(--red)"),
            ]
            with ui.element("div").classes("paradigm-grid"):
                for label, value, color in grid_items:
                    with ui.element("div").classes("paradigm-cell"):
                        ui.label(label).classes("paradigm-cell-label").style(f"color: {color}")
                        ui.label(value).classes("paradigm-cell-value")

            with ui.element("div").classes("insight-box"):
                ui.label("💡 The fix is adding tool-call verification — not rewriting the whole prompt.")

        def _step_judge():
            ui.label("Paradigm model → binary judge prompt.").style("font-weight: 600; color: var(--text-primary); margin-bottom: 10px")
            with ui.element("div").classes("judge-block"):
                ui.label(DEMO_JUDGE)

            with ui.element("div").classes("metric-row"):
                ui.label("87%").classes("metric-big")
                ui.label("agreement with human labels (3/4 traces match)").classes("metric-label")

            with ui.element("div").classes("insight-box"):
                ui.label("💡 A judge grounded in observed failures beats a generic 'is this response good?' — every time.")

        render_step(0)


@ui.page("/")
def home_page():
    ui.add_head_html(f"<style>{BRAND_CSS}</style>")
    ui.add_head_html(f"<style>{HOME_CSS}</style>")

    with ui.column().classes("w-full items-center").style("max-width: 780px; margin: 0 auto; padding: 1.5rem"):

        # Hero
        with ui.element("div").classes("home-hero animate-in stagger-1"):
            ui.html('<h1>Grounded Eval-Driven<br>Development</h1>')
            ui.html('<p>Build AI agent evaluations the right way — problem first, solution second</p>')

        # Demo
        with ui.element("div").classes("w-full animate-in stagger-2"):
            _render_demo()

        # Workflow steps
        storage = app.storage.user
        progress = _get_progress(storage)

        # Progress summary bar (if user has started)
        session = storage.get("session_data") or {}
        agent_spec = session.get("agent_spec", {}) if isinstance(session, dict) else {}
        agent_name_home = agent_spec.get("name", "") if isinstance(agent_spec, dict) else ""
        n_queries = len(session.get("golden_prompts", []) if isinstance(session, dict) else [])
        n_annotations = len(storage.get("coding_annotations", []))
        done_count = sum(1 for s in progress.values() if s == "done")

        if agent_name_home:
            with ui.element("div").style(
                "background: var(--bg-surface-2); border: 1px solid var(--border-subtle); "
                "border-radius: var(--radius-xl); padding: 14px 16px; margin-bottom: 1.5rem"
            ):
                with ui.row().classes("items-center justify-between w-full"):
                    with ui.column().style("gap: 2px"):
                        ui.label(f"Continuing: {agent_name_home}").style(
                            "font-size: 0.85rem; font-weight: 600; color: var(--text-primary)"
                        )
                        ui.label(
                            f"{n_queries} queries · {n_annotations} annotations · {done_count}/5 steps done"
                        ).style("font-size: 0.75rem; color: var(--text-tertiary)")
                    ui.button("Continue", icon="arrow_forward", on_click=lambda: ui.navigate.to(
                        next((p for p, s in progress.items() if s == "current"), "/coach")
                    )).props("size=sm color=primary")

        with ui.column().classes("w-full").style("margin-top: 1rem"):
            # Problem space
            with ui.row().classes("items-center gap-2").style("margin-bottom: 10px"):
                ui.html('<span class="section-badge" style="background: var(--accent-tint); color: var(--accent-bright)">PROBLEM SPACE</span>')
                ui.label("Understand what fails — and why").style("font-size: 0.78rem; color: var(--text-tertiary)")

            for step in PROBLEM_STEPS:
                status = progress.get(step["path"], "todo")
                is_done = status == "done"
                is_current = status == "current"
                icon_color = "var(--green-bright)" if is_done else ("var(--accent-bright)" if is_current else "var(--text-muted)")
                text_color = "var(--text-primary)" if not status == "todo" else "var(--text-muted)"
                with ui.element("div").classes("workflow-card").on("click", lambda _, p=step["path"]: ui.navigate.to(p)):
                    with ui.row().classes("items-center gap-3 w-full"):
                        ui.icon("check_circle" if is_done else step["icon"]).style(f"color: {icon_color}; font-size: 1.2rem")
                        with ui.column().style("gap: 1px; flex: 1"):
                            ui.label(step["title"]).style(f"font-size: 0.9rem; font-weight: 600; color: {text_color}")
                            ui.label(step["desc"]).style("font-size: 0.78rem; color: var(--text-tertiary)")
                        if is_done:
                            ui.html('<span style="font-size:0.65rem;background:var(--green-tint);color:var(--green-bright);padding:2px 9px;border-radius:99px;font-weight:600;white-space:nowrap">Done</span>')
                        elif is_current:
                            ui.html('<span style="font-size:0.65rem;background:var(--accent-tint);color:var(--accent-bright);padding:2px 9px;border-radius:99px;font-weight:600;white-space:nowrap">→ Next</span>')

            # Divider
            with ui.row().classes("w-full items-center").style("margin: 14px 0"):
                ui.element("div").style("flex: 1; height: 1px; background: var(--border-subtle)")
                ui.label("then").style("font-size: 0.7rem; color: var(--text-muted); padding: 0 10px")
                ui.element("div").style("flex: 1; height: 1px; background: var(--border-subtle)")

            # Solution space
            with ui.row().classes("items-center gap-2").style("margin-bottom: 10px"):
                ui.html('<span class="section-badge" style="background: var(--green-tint); color: var(--green-bright)">SOLUTION SPACE</span>')
                ui.label("Build evaluation grounded in discovery").style("font-size: 0.78rem; color: var(--text-tertiary)")

            for step in SOLUTION_STEPS:
                status = progress.get(step["path"], "todo")
                is_done = status == "done"
                is_current = status == "current"
                with ui.element("div").classes("workflow-card").on("click", lambda _, p=step["path"]: ui.navigate.to(p)):
                    with ui.row().classes("items-center gap-3 w-full"):
                        ui.icon("check_circle" if is_done else step["icon"]).style(
                            f"color: {'var(--green-bright)' if is_done else 'var(--accent-bright)'}; font-size: 1.2rem"
                        )
                        with ui.column().style("gap: 1px; flex: 1"):
                            ui.label(step["title"]).style("font-size: 0.9rem; font-weight: 600; color: var(--text-primary)")
                            ui.label(step["desc"]).style("font-size: 0.78rem; color: var(--text-tertiary)")
                        if is_done:
                            ui.html('<span style="font-size:0.65rem;background:var(--green-tint);color:var(--green-bright);padding:2px 9px;border-radius:99px;font-weight:600">Done</span>')
                        elif is_current:
                            ui.html('<span style="font-size:0.65rem;background:var(--green-tint);color:var(--green-bright);padding:2px 9px;border-radius:99px;font-weight:600">→ Next</span>')

        # Footer
        with ui.element("div").style(
            "margin-top: 2rem; padding: 14px; border-radius: var(--radius-xl); "
            "background: var(--bg-surface-2); border: 1px solid var(--border-subtle); text-align: center"
        ):
            ui.label("Most eval tools skip straight to rubrics. GEDD makes you earn the right to build one.").style(
                "font-size: 0.82rem; color: var(--text-secondary); font-weight: 500"
            )

        # Load Demo Data
        def load_demo():
            from grounded_evals.ui.demo_data import load_demo_data
            load_demo_data(app.storage.user)
            ui.notify("Demo data loaded! Explore each page to see it in action.", type="positive")
            ui.navigate.to("/coach")

        with ui.row().classes("items-center gap-2").style("margin-top: 1.5rem"):
            ui.button("Load Demo Data (TravelBot)", icon="science", on_click=load_demo).props("size=sm").style(
                "background: var(--accent); color: white; border-radius: 6px"
            )
            ui.label("Pre-populates all pages with realistic sample data").style("font-size: 0.72rem; color: var(--text-muted)")

        # Logout
        def logout():
            app.storage.user["authenticated"] = False
            ui.navigate.to("/login")

        ui.button("Logout", icon="logout", on_click=logout).props("flat size=sm").style(
            "color: var(--text-muted); margin-top: 0.5rem"
        )
