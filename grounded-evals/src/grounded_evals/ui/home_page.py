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

/* ── Marketing hero ─────────────────────────────────────────────────── */
.mkt-hero { text-align: center; padding: 3.25rem 0 1.5rem; }
.mkt-eyebrow {
  display: inline-block; font-size: 0.7rem; font-weight: 600;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--accent-bright); background: var(--accent-tint);
  padding: 4px 10px; border-radius: 99px; margin-bottom: 1rem;
}
.mkt-headline {
  font-size: 2.4rem; font-weight: 700; color: var(--text-primary);
  letter-spacing: -0.03em; line-height: 1.15; margin: 0 0 0.6rem;
}
.mkt-headline em { font-style: italic; color: var(--accent-bright); font-weight: 700; }
.mkt-subhead {
  font-size: 1rem; color: var(--text-secondary); margin: 0 auto;
  max-width: 580px; line-height: 1.55;
}
.mkt-cta-row { display: flex; gap: 10px; justify-content: center; margin-top: 1.5rem; }

/* ── Domain demo grid ──────────────────────────────────────────────── */
.mkt-section-head {
  display: flex; align-items: baseline; justify-content: space-between;
  margin: 2.5rem 0 0.85rem;
}
.mkt-section-title {
  font-size: 1.05rem; font-weight: 600; color: var(--text-primary);
  letter-spacing: -0.01em;
}
.mkt-section-sub { font-size: 0.78rem; color: var(--text-tertiary); }

.domain-grid {
  display: grid; grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.domain-card {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 14px; border-radius: var(--radius-xl);
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface-2);
  cursor: pointer; transition: all 150ms ease;
  position: relative; overflow: hidden;
}
.domain-card:hover {
  border-color: var(--accent);
  background: var(--bg-surface-3);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(94,106,210,0.08);
}
.domain-card .icon-wrap {
  width: 36px; height: 36px; border-radius: 8px;
  background: var(--accent-tint); display: flex;
  align-items: center; justify-content: center; flex-shrink: 0;
}
.domain-card .body { flex: 1; min-width: 0; }
.domain-card .name {
  font-size: 0.88rem; font-weight: 600; color: var(--text-primary);
  margin-bottom: 2px; line-height: 1.3;
}
.domain-card .desc {
  font-size: 0.75rem; color: var(--text-tertiary);
  line-height: 1.45;
}
.domain-card .arrow {
  position: absolute; top: 14px; right: 14px;
  color: var(--text-muted); font-size: 0.95rem;
  transition: transform 150ms ease, color 150ms ease;
}
.domain-card:hover .arrow {
  color: var(--accent-bright); transform: translateX(3px);
}

/* ── Outcome strip ─────────────────────────────────────────────────── */
.outcome-strip {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 1px; background: var(--border-subtle);
  border: 1px solid var(--border-subtle); border-radius: var(--radius-xl);
  margin-top: 1.5rem; overflow: hidden;
}
.outcome-cell {
  background: var(--bg-surface-2); padding: 16px 14px;
  text-align: center;
}
.outcome-cell .num {
  font-size: 1.6rem; font-weight: 700; color: var(--green-bright);
  font-variant-numeric: tabular-nums; line-height: 1;
}
.outcome-cell .label {
  font-size: 0.72rem; color: var(--text-tertiary);
  margin-top: 6px; letter-spacing: 0.01em;
}

/* ── Continue card ─────────────────────────────────────────────────── */
.continue-card {
  background: linear-gradient(135deg, var(--accent-tint), transparent);
  border: 1px solid var(--accent);
  border-radius: var(--radius-xl);
  padding: 14px 16px; margin-bottom: 1.5rem;
}

/* ── Methodology fold ──────────────────────────────────────────────── */
.method-fold {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  margin-top: 1.5rem;
  background: var(--bg-surface-1);
}
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

    storage = app.storage.user

    # Guest mode: auto-load TravelBot on first visit so newcomers land in a
    # fully-populated session rather than a blank slate.
    import os as _os
    _guest_mode = not _os.environ.get("ADMIN_PASSWORD") and not _os.environ.get("COGNITO_USER_POOL_ID")
    if _guest_mode and not storage.get("_guest_demo_loaded"):
        from grounded_evals.ui.demo_data import load_demo_data
        load_demo_data(storage)
        storage["_guest_demo_loaded"] = True

    progress = _get_progress(storage)
    session = storage.get("session_data") or {}
    agent_spec = session.get("agent_spec", {}) if isinstance(session, dict) else {}
    agent_name_home = agent_spec.get("name", "") if isinstance(agent_spec, dict) else ""
    n_queries = len(session.get("golden_prompts", []) if isinstance(session, dict) else [])
    n_annotations = len(storage.get("coding_annotations", []))
    done_count = sum(1 for s in progress.values() if s == "done")

    # Demo loaders — kept identical to previous implementation
    def load_demo():
        from grounded_evals.ui.demo_data import load_demo_data
        load_demo_data(app.storage.user)
        ui.notify("TravelBot demo loaded! Explore each page to see it in action.", type="positive")
        ui.navigate.to("/coach")

    def load_support_demo():
        from grounded_evals.ui.support_bot_demo import load_support_bot_demo
        load_support_bot_demo(app.storage.user)
        ui.notify("SupportBot demo loaded!", type="positive")
        ui.navigate.to("/coach")

    def load_clinical_demo():
        from grounded_evals.ui.domain_demos import load_clinical_demo
        load_clinical_demo(app.storage.user)
        ui.notify("ClinicalBot demo loaded!", type="positive")
        ui.navigate.to("/coach")

    def load_lex_demo():
        from grounded_evals.ui.domain_demos import load_lex_demo
        load_lex_demo(app.storage.user)
        ui.notify("LexBot demo loaded!", type="positive")
        ui.navigate.to("/coach")

    def load_wealth_demo():
        from grounded_evals.ui.domain_demos import load_wealth_demo
        load_wealth_demo(app.storage.user)
        ui.notify("WealthBot demo loaded!", type="positive")
        ui.navigate.to("/coach")

    def load_hr_demo():
        try:
            from grounded_evals.ui.domain_demos import load_hr_demo
            load_hr_demo(app.storage.user)
            ui.notify("HRBot demo loaded!", type="positive")
            ui.navigate.to("/coach")
        except (ImportError, AttributeError):
            ui.notify("HRBot demo not available", type="warning")

    def load_edu_demo():
        try:
            from grounded_evals.ui.domain_demos import load_edu_demo
            load_edu_demo(app.storage.user)
            ui.notify("EduBot demo loaded!", type="positive")
            ui.navigate.to("/coach")
        except (ImportError, AttributeError):
            ui.notify("EduBot demo not available", type="warning")

    def load_game_demo():
        try:
            from grounded_evals.ui.domain_demos import load_game_demo
            load_game_demo(app.storage.user)
            ui.notify("PixelGuard demo loaded!", type="positive")
            ui.navigate.to("/coach")
        except (ImportError, AttributeError):
            ui.notify("PixelGuard demo not available", type="warning")

    def load_crypto_demo():
        try:
            from grounded_evals.ui.domain_demos import load_crypto_demo
            load_crypto_demo(app.storage.user)
            ui.notify("VaultEx AI demo loaded!", type="positive")
            ui.navigate.to("/coach")
        except (ImportError, AttributeError):
            ui.notify("VaultEx demo not available", type="warning")

    def logout():
        app.storage.user["authenticated"] = False
        ui.navigate.to("/login")

    DOMAIN_CARDS = [
        ("ClinicalBot", "local_hospital", load_clinical_demo,
         "Surfaces missed escalation triggers and dangerous drug-interaction blindspots."),
        ("LexBot", "gavel", load_lex_demo,
         "Exposes phantom citations and unauthorized-practice-of-law boundary crossings."),
        ("WealthBot", "trending_up", load_wealth_demo,
         "Finds suitability failures and responses edging toward unregistered investment advice."),
        ("VaultEx AI", "currency_bitcoin", load_crypto_demo,
         "Uncovers securities-law overreach, seed-phrase scam vulnerability, and sanctions blindspots."),
        ("HRBot", "people", load_hr_demo,
         "Identifies disparate-impact patterns and ADA boundary violations in candidate screening."),
        ("EduBot", "school", load_edu_demo,
         "Catches academic-integrity violations and age-gate failures under COPPA."),
        ("PixelGuard", "sports_esports", load_game_demo,
         "Surfaces COPPA failures, loot-box law exposure, and anti-cheat policy violations."),
        ("TravelBot", "flight", load_demo,
         "Catches hallucinated airlines, fabricated booking IDs, and confident confabulation."),
    ]

    with ui.column().classes("w-full items-center").style(
        "max-width: 820px; margin: 0 auto; padding: 1.25rem 1.5rem 2.5rem"
    ):

        # ── Resume bar (returning users only) ────────────────────────────
        if agent_name_home:
            with ui.element("div").classes("continue-card animate-in stagger-1"):
                with ui.row().classes("items-center justify-between w-full"):
                    with ui.column().style("gap: 2px"):
                        ui.label(f"Continuing: {agent_name_home}").style(
                            "font-size: 0.88rem; font-weight: 600; color: var(--text-primary)"
                        )
                        ui.label(
                            f"{n_queries} queries · {n_annotations} annotations · {done_count}/5 steps done"
                        ).style("font-size: 0.74rem; color: var(--text-tertiary)")
                    ui.button(
                        "Continue", icon="arrow_forward",
                        on_click=lambda: ui.navigate.to(
                            next((p for p, s in progress.items() if s == "current"), "/coach")
                        ),
                    ).props("size=sm color=primary")

        # ── Hero ────────────────────────────────────────────────────────
        with ui.element("div").classes("mkt-hero animate-in stagger-1"):
            ui.html('<div class="mkt-eyebrow">Qualitative Eval Framework</div>')
            ui.html(
                '<h1 class="mkt-headline">'
                "Find what your AI gets wrong. <em>Before your customers do.</em>"
                "</h1>"
            )
            ui.html(
                '<p class="mkt-subhead">'
                "GEDD helps product managers and domain experts systematically discover "
                "failure modes, then turn them into a deployable LLM-as-judge — in your "
                "own vocabulary, not generic 'helpfulness 1–5'."
                "</p>"
            )
            with ui.row().classes("mkt-cta-row"):
                ui.button(
                    "Try a 90-second demo",
                    icon="play_arrow",
                    on_click=lambda: ui.run_javascript(
                        "document.getElementById('domain-section')?.scrollIntoView({behavior:'smooth'})"
                    ),
                ).props("color=primary size=md unelevated").style(
                    "font-weight: 600; letter-spacing: -0.01em; padding: 8px 18px"
                )
                ui.button(
                    "Start your own agent",
                    icon="chat",
                    on_click=lambda: ui.navigate.to("/coach"),
                ).props("flat size=md").style(
                    "color: var(--text-secondary); font-weight: 500"
                )

        # ── Outcome strip (social-proof shaped) ──────────────────────────
        with ui.element("div").classes("outcome-strip animate-in stagger-2"):
            with ui.element("div").classes("outcome-cell"):
                ui.html('<div class="num">8</div>')
                ui.html('<div class="label">domain personas, pre-loaded</div>')
            with ui.element("div").classes("outcome-cell"):
                ui.html('<div class="num">~90 min</div>')
                ui.html('<div class="label">to your first deployable judge</div>')
            with ui.element("div").classes("outcome-cell"):
                ui.html('<div class="num">κ ≥ 0.80</div>')
                ui.html('<div class="label">judge-vs-human calibration target</div>')
                ui.html(
                    '<div style="font-size:0.68rem;color:#6e737b;margin-top:4px;line-height:1.4">'
                    'κ (Cohen\'s Kappa) measures how closely your LLM judge agrees with human verdicts. '
                    '0.80 = strong agreement — the threshold where the judge can run autonomously in CI.'
                    '</div>'
                )

        # ── Domain demo grid (the hero asset) ────────────────────────────
        ui.html('<div id="domain-section"></div>')
        with ui.element("div").classes("mkt-section-head animate-in stagger-3"):
            with ui.column().style("gap: 2px"):
                ui.html('<div class="mkt-section-title">Load a pre-built eval scenario</div>')
                ui.html(
                    '<div class="mkt-section-sub">'
                    "Each scenario runs all 5 steps: golden queries, failure annotations, "
                    "paradigm model, and a generated judge — ready to explore."
                    "</div>"
                )
            ui.button(
                "View all →", icon="open_in_new",
                on_click=lambda: ui.navigate.to("/demos"),
            ).props("flat size=sm no-caps").style(
                "color: var(--accent-bright); font-size: 0.78rem"
            )

        with ui.element("div").classes("domain-grid animate-in stagger-3"):
            for name, icon, handler, desc in DOMAIN_CARDS:
                with ui.element("div").classes("domain-card").on("click", handler):
                    with ui.element("div").classes("icon-wrap"):
                        ui.icon(icon).style("color: var(--accent-bright); font-size: 1.05rem")
                    with ui.element("div").classes("body"):
                        ui.html(f'<div class="name">{name}</div>')
                        ui.html(f'<div class="desc">{desc}</div>')
                    ui.html('<span class="arrow material-icons">arrow_forward</span>')

        # ── Evaluate your own agent (demoted CTA) ────────────────────────
        ui.button(
            "Evaluate your own agent →", icon="chat",
            on_click=lambda: ui.navigate.to("/coach"),
        ).props("flat size=sm no-caps").style(
            "color: var(--text-secondary); margin-top: 1rem; align-self: center"
        )

        # ── Methodology fold (deprioritized; for the curious buyer) ──────
        with ui.expansion(
            "How GEDD works under the hood — grounded theory for AI eval",
            icon="psychology",
        ).classes("w-full animate-in stagger-5").style(
            "background: var(--bg-surface-1); border: 1px solid var(--border-subtle); "
            "border-radius: var(--radius-xl); margin-top: 1.5rem; "
            "color: var(--text-primary)"
        ):
            ui.html(
                '<div style="font-size:0.84rem;color:var(--text-secondary);'
                'line-height:1.6;margin-bottom:0.85rem">'
                "GEDD applies <strong>Strauss & Corbin's grounded theory</strong> "
                "(open coding → axial coding → selective coding) to AI evaluation. "
                "Instead of guessing what to measure, you observe what fails, name "
                "the patterns in your domain's vocabulary, and build a judge "
                "calibrated against your own scoring."
                "</div>"
            )
            _render_demo()
            ui.html(
                '<div style="font-size:0.74rem;color:var(--text-muted);'
                'margin-top:0.85rem;text-align:center">'
                "Walk through the full TravelBot example — Define → Observe → "
                "Tag → Root Cause → Judge."
                "</div>"
            )

        # ── Closing positioning line ─────────────────────────────────────
        with ui.element("div").style(
            "margin-top: 2rem; padding: 14px 18px; border-radius: var(--radius-xl); "
            "background: var(--bg-surface-2); border: 1px solid var(--border-subtle); "
            "text-align: center"
        ):
            ui.label(
                "Most eval tools skip straight to rubrics. "
                "GEDD makes you earn the right to build one."
            ).style(
                "font-size: 0.84rem; color: var(--text-secondary); "
                "font-weight: 500; letter-spacing: -0.005em"
            )

        ui.button("Logout", icon="logout", on_click=logout).props("flat size=sm").style(
            "color: var(--text-muted); margin-top: 1rem"
        )
