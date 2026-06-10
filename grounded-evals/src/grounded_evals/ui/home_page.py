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


def _has_session_content(storage: dict) -> bool:
    """Return whether the user has started or loaded meaningful eval work."""
    session = storage.get("session_data") or {}
    if not isinstance(session, dict):
        return False
    agent_spec = session.get("agent_spec", {})
    if not isinstance(agent_spec, dict):
        agent_spec = {}
    return bool(
        agent_spec.get("name")
        or agent_spec.get("system_prompt")
        or session.get("golden_prompts")
        or storage.get("eval_results")
        or storage.get("coding_annotations")
        or storage.get("codebook")
    )


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

EXPERT_DISCOVERIES = [
    {
        "domain": "Pharmacy",
        "error_code": "dosage_unit_confusion",
        "what_happened": 'Said "mg" when context suggests "mcg"',
        "expert_signal": "1000x dose error, potentially fatal",
    },
    {
        "domain": "Insurance",
        "error_code": "coverage_hallucination",
        "what_happened": "Assumed policy exists without checking",
        "expert_signal": "Policyholder believes they are covered",
    },
    {
        "domain": "Tax",
        "error_code": "incomplete_guidance",
        "what_happened": "Did not recommend a CPA for a $200K scenario",
        "expert_signal": "Liability issue in tax advice",
    },
    {
        "domain": "Immigration",
        "error_code": "bar_misapplication",
        "what_happened": "Said 3-year bar applies to 90-day overstay",
        "expert_signal": "Bar triggers at 180+ days under INA Section 212(a)(9)(B)",
    },
    {
        "domain": "AdTech",
        "error_code": "consent_bypass_for_targeting",
        "what_happened": "Helped justify targeted advertising without valid consent",
        "expert_signal": "Growth pressure does not override privacy law or platform policy",
    },
]

ANNOTATION_SURFACES = [
    {
        "title": "Chat",
        "icon": "forum",
        "copy": "Render the full conversation, prior turns, model variants, and user-visible answer together.",
    },
    {
        "title": "Email",
        "icon": "mail",
        "copy": "Show the message as an inbox thread with sender, recipients, subject, attachments, and reply context.",
    },
    {
        "title": "Calendar",
        "icon": "event_available",
        "copy": "Review the proposed event as a booking confirmation, not a raw tool-call payload.",
    },
    {
        "title": "AdTech",
        "icon": "campaign",
        "copy": "Put campaign objective, audience, consent basis, policy flags, and recommendation in one view.",
    },
]

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

/* ── Coach-first homepage ───────────────────────────────────────────── */
.coach-first-hero {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
  gap: 14px;
  margin-top: 1.35rem;
}
.coach-main-panel,
.coach-brief-panel {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  background: var(--bg-surface-1);
}
.coach-main-panel {
  padding: 24px;
  min-height: 360px;
}
.coach-brief-panel {
  padding: 18px;
}
.coach-kicker {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-bright);
  background: var(--accent-tint);
  border: 1px solid rgba(94,106,210,0.2);
  border-radius: 99px;
  padding: 5px 10px;
}
.coach-headline {
  max-width: 680px;
  margin: 16px 0 0;
  font-size: 2.2rem;
  line-height: 1.12;
  letter-spacing: 0;
  font-weight: 720;
  color: var(--text-primary);
}
.coach-subhead {
  max-width: 650px;
  margin-top: 12px;
  font-size: 0.98rem;
  line-height: 1.6;
  color: var(--text-secondary);
}
.coach-action-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 22px;
}
.coach-flow {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 22px;
}
.coach-flow-step {
  min-height: 92px;
  padding: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-surface-2);
}
.coach-flow-num {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 99px;
  background: var(--accent-tint);
  color: var(--accent-bright);
  font-size: 0.68rem;
  font-weight: 700;
}
.coach-flow-title {
  margin-top: 9px;
  font-size: 0.77rem;
  color: var(--text-primary);
  font-weight: 650;
}
.coach-flow-copy {
  margin-top: 4px;
  font-size: 0.7rem;
  line-height: 1.42;
  color: var(--text-tertiary);
}
.brief-title {
  font-size: 0.9rem;
  font-weight: 680;
  color: var(--text-primary);
}
.brief-copy {
  margin-top: 6px;
  font-size: 0.76rem;
  line-height: 1.5;
  color: var(--text-tertiary);
}
.brief-list {
  display: grid;
  gap: 8px;
  margin-top: 14px;
}
.brief-item {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 8px;
  padding: 10px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface-2);
}
.brief-item .material-icons {
  color: var(--accent-bright);
  font-size: 1rem;
  line-height: 1.2;
}
.brief-item-title {
  font-size: 0.74rem;
  font-weight: 650;
  color: var(--text-primary);
}
.brief-item-copy {
  margin-top: 2px;
  font-size: 0.69rem;
  line-height: 1.38;
  color: var(--text-tertiary);
}
.coach-reference-note {
  margin-top: 14px;
  padding: 11px 12px;
  border-radius: var(--radius-lg);
  background: var(--yellow-tint);
  border: 1px solid rgba(240,191,0,0.16);
  color: var(--text-secondary);
  font-size: 0.72rem;
  line-height: 1.45;
}

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

/* ── Annotation product section ─────────────────────────────────────── */
.annotation-panel {
  width: 100%;
  margin-top: 1.5rem;
  padding: 16px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  background: var(--bg-surface-1);
}
.annotation-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}
.annotation-surface {
  padding: 13px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface-2);
}
.annotation-surface-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.annotation-surface-title {
  font-size: 0.82rem;
  font-weight: 650;
  color: var(--text-primary);
}
.annotation-surface-copy {
  font-size: 0.74rem;
  line-height: 1.45;
  color: var(--text-tertiary);
}
.principle-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}
.principle-card {
  padding: 12px;
  border-radius: var(--radius-lg);
  background: var(--accent-tint);
  border: 1px solid rgba(94,106,210,0.18);
}
.principle-title {
  font-size: 0.76rem;
  font-weight: 650;
  color: var(--accent-bright);
}
.principle-copy {
  margin-top: 4px;
  font-size: 0.72rem;
  line-height: 1.45;
  color: var(--text-secondary);
}

/* ── Evidence section ───────────────────────────────────────────────── */
.evidence-panel {
  width: 100%;
  margin-top: 1.5rem;
  padding: 16px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  background: var(--bg-surface-1);
}
.evidence-kicker {
  font-size: 0.64rem; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--accent-bright);
}
.evidence-title {
  margin-top: 4px; font-size: 1rem; font-weight: 650;
  color: var(--text-primary); letter-spacing: -0.01em;
}
.evidence-copy {
  margin-top: 6px; font-size: 0.78rem; line-height: 1.55;
  color: var(--text-tertiary);
}
.evidence-grid {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px; margin-top: 14px;
}
.evidence-card {
  padding: 12px; border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle); background: var(--bg-surface-2);
}
.evidence-card-top {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px; margin-bottom: 8px;
}
.evidence-domain {
  font-size: 0.78rem; font-weight: 650; color: var(--text-primary);
}
.evidence-code {
  font-family: 'SF Mono', 'Menlo', monospace; font-size: 0.62rem;
  color: var(--accent-bright); background: var(--accent-tint);
  padding: 3px 6px; border-radius: 6px; overflow-wrap: anywhere;
}
.evidence-label {
  font-size: 0.6rem; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase; color: var(--text-muted); margin-top: 8px;
}
.evidence-value {
  font-size: 0.74rem; line-height: 1.45; color: var(--text-secondary);
  margin-top: 2px;
}

/* ── Continue card ─────────────────────────────────────────────────── */
.continue-card {
  background: linear-gradient(135deg, var(--accent-tint), transparent);
  border: 1px solid var(--accent);
  border-radius: var(--radius-xl);
  padding: 14px 16px; margin-bottom: 1.5rem;
}

.custom-agent-card {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 1.25rem;
  padding: 15px 16px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  background: var(--bg-surface-1);
}
.custom-agent-card .title {
  font-size: 0.86rem;
  font-weight: 600;
  color: var(--text-primary);
}
.custom-agent-card .copy {
  font-size: 0.76rem;
  color: var(--text-tertiary);
  line-height: 1.45;
  margin-top: 2px;
}

/* ── Methodology fold ──────────────────────────────────────────────── */
.method-fold {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  margin-top: 1.5rem;
  background: var(--bg-surface-1);
}

@media (max-width: 720px) {
  .mkt-hero { padding-top: 2rem; }
  .mkt-headline { font-size: 1.65rem; line-height: 1.2; }
  .mkt-subhead { font-size: 0.9rem; }
  .mkt-cta-row { flex-direction: column; align-items: stretch; }
  .coach-first-hero { grid-template-columns: 1fr; }
  .coach-main-panel { padding: 18px; min-height: auto; }
  .coach-headline { font-size: 1.55rem; }
  .coach-action-row { flex-direction: column; align-items: stretch; }
  .coach-flow { grid-template-columns: 1fr; }
  .outcome-strip { grid-template-columns: 1fr; }
  .annotation-grid { grid-template-columns: 1fr; }
  .principle-row { grid-template-columns: 1fr; }
  .domain-grid { grid-template-columns: 1fr; }
  .evidence-grid { grid-template-columns: 1fr; }
  .mkt-section-head {
    align-items: flex-start; flex-direction: column; gap: 0.6rem;
  }
  .custom-agent-card { flex-direction: column; align-items: flex-start; }
  .paradigm-grid { grid-template-columns: 1fr; }
  .demo-nav { overflow-x: auto; }
  .demo-nav-btn { min-width: 88px; }
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
    is_returning = _has_session_content(storage)

    progress = _get_progress(storage)
    session = storage.get("session_data") or {}
    agent_spec = session.get("agent_spec", {}) if isinstance(session, dict) else {}
    agent_name_home = agent_spec.get("name", "") if isinstance(agent_spec, dict) else ""
    n_queries = len(session.get("golden_prompts", []) if isinstance(session, dict) else [])
    n_annotations = len(storage.get("coding_annotations", []))
    done_count = sum(1 for s in progress.values() if s == "done")

    def next_annotation_path() -> str:
        if storage.get("coding_annotations") or storage.get("codebook"):
            return "/coding"
        if storage.get("eval_results"):
            return "/coding"
        session_obj = storage.get("session_data") or {}
        if isinstance(session_obj, dict) and session_obj.get("golden_prompts"):
            return "/eval"
        return "/coach"

    from grounded_evals.ui.demos_page import _build_domain_registry
    domain_cards = _build_domain_registry()
    domain_priority = {"game_producer": 0, "game_operator": 1, "adtech": 2}
    domain_cards = sorted(
        domain_cards,
        key=lambda domain: domain_priority.get(domain.get("id", ""), 99),
    )

    with ui.column().classes("w-full items-center").style(
        "max-width: 820px; margin: 0 auto; padding: 1.25rem 1.5rem 2.5rem"
    ):

        # ── Resume bar (returning users only) ────────────────────────────
        if _has_session_content(storage):
            display_name = agent_name_home or "Untitled agent"
            with ui.element("div").classes("continue-card animate-in stagger-1"):
                with ui.row().classes("items-center justify-between w-full"):
                    with ui.column().style("gap: 2px"):
                        ui.label(f"Continuing: {display_name}").style(
                            "font-size: 0.88rem; font-weight: 600; color: var(--text-primary)"
                        )
                        ui.label(
                            f"{n_queries} queries · {n_annotations} annotations · {done_count}/5 steps done"
                        ).style("font-size: 0.74rem; color: var(--text-tertiary)")
                    ui.button(
                        "Continue", icon="arrow_forward",
                        on_click=lambda: ui.navigate.to(next_annotation_path()),
                    ).props("size=sm color=primary")

        # ── Hero: headline + single CTA + demo gif ────────────────────────
        with ui.element("div").classes("animate-in stagger-1").style(
            "text-align: center; margin-top: 1.5rem"
        ):
            ui.html(
                '<div class="coach-kicker" style="margin: 0 auto; width: fit-content">'
                '<span class="material-icons" style="font-size:0.95rem">auto_awesome</span>'
                "AI PM Release Readiness"
                "</div>"
            )
            ui.html(
                '<h1 class="coach-headline" style="text-align:center; margin: 16px auto 0">'
                "Find the failures that decide whether your agent is shippable."
                "</h1>"
            )
            ui.html(
                '<div class="coach-subhead" style="text-align:center; margin: 12px auto 0; max-width: 600px">'
                "Offline eval techniques for AI PMs. Observe agent behavior, "
                "name failures in domain language, and leave with a release report "
                "engineering can act on."
                "</div>"
            )
            with ui.row().classes("justify-center gap-2").style("margin-top: 22px"):
                ui.button(
                    "Open GEDD Coach",
                    icon="auto_awesome",
                    on_click=lambda: ui.navigate.to("/coach"),
                ).props("color=primary size=md unelevated").style(
                    "font-weight: 600; letter-spacing: 0; padding: 8px 22px"
                )
                ui.button(
                    "Load a demo",
                    icon="collections_bookmark",
                    on_click=lambda: ui.run_javascript(
                        "document.getElementById('domain-section')?.scrollIntoView({behavior:'smooth'})"
                    ),
                ).props("outline size=md no-caps").style(
                    "color: var(--accent-bright); border-color: var(--border-subtle)"
                )

        # ── Demo gif ─────────────────────────────────────────────────────
        with ui.element("div").style(
            "margin-top: 1.5rem; border-radius: var(--radius-xl); overflow: hidden; "
            "border: 1px solid var(--border-subtle); background: var(--bg-surface-1)"
        ):
            ui.image("/docs/GEDD_optimized.gif").style(
                "width: 100%; border-radius: var(--radius-xl)"
            )
            ui.html(
                '<div style="padding: 10px 14px; font-size: 0.72rem; color: var(--text-tertiary); text-align: center">'
                "Query → Responses → Annotate → Codes emerge → Judge"
                "</div>"
            )

        # ── Stats strip ──────────────────────────────────────────────────
        with ui.element("div").classes("outcome-strip animate-in stagger-2"):
            with ui.element("div").classes("outcome-cell"):
                ui.html(f'<div class="num">{len(domain_cards)}</div>')
                ui.html('<div class="label">launch-risk scenarios</div>')
            with ui.element("div").classes("outcome-cell"):
                ui.html('<div class="num">8</div>')
                ui.html('<div class="label">rubric dimensions</div>')
            with ui.element("div").classes("outcome-cell"):
                ui.html('<div class="num">Evidence handoff</div>')
                ui.html('<div class="label">session.json for engineering</div>')

        # ── Before / After contrast card ─────────────────────────────────
        with ui.element("div").classes("animate-in stagger-2").style(
            "display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 1.25rem; "
            "width: 100%"
        ):
            # Before
            with ui.element("div").style(
                "padding: 18px; border-radius: var(--radius-xl); "
                "background: var(--bg-surface-1); border: 1px solid var(--border-subtle)"
            ):
                ui.html(
                    '<div style="font-size:0.68rem; text-transform:uppercase; letter-spacing:0.08em; '
                    'font-weight:700; color: var(--text-muted); margin-bottom:10px">Before</div>'
                )
                ui.html(
                    '<div style="font-size:0.82rem; color:var(--text-secondary); line-height:1.6">'
                    '<div style="margin-bottom:6px">Label: <span style="color:var(--text-muted)">"hallucination"</span></div>'
                    '<div style="margin-bottom:6px">Score: <span style="color:var(--text-muted)">Quality 3/5</span></div>'
                    '<div>Rubric: <span style="color:var(--text-muted)">generic helpfulness</span></div>'
                    "</div>"
                )
            # After
            with ui.element("div").style(
                "padding: 18px; border-radius: var(--radius-xl); "
                "background: var(--bg-surface-1); border: 1px solid rgba(94,106,210,0.3)"
            ):
                ui.html(
                    '<div style="font-size:0.68rem; text-transform:uppercase; letter-spacing:0.08em; '
                    'font-weight:700; color: var(--accent-bright); margin-bottom:10px">After GEDD</div>'
                )
                ui.html(
                    '<div style="font-size:0.82rem; color:var(--text-primary); line-height:1.6">'
                    '<div style="margin-bottom:6px">Code: <code style="background:var(--accent-tint);'
                    'padding:2px 6px;border-radius:4px;font-size:0.75rem;color:var(--accent-bright)">'
                    'dosage_unit_confusion</code></div>'
                    '<div style="margin-bottom:6px">Severity: <span style="color:#ef5350; font-weight:600">Catastrophic</span></div>'
                    '<div>Memo: <span style="color:var(--text-secondary)">1000× unit error, potentially fatal</span></div>'
                    "</div>"
                )

        # ── Annotation interface proof (hidden for returning users) ─────
        if not is_returning:
          with ui.element("div").classes("annotation-panel animate-in stagger-2"):
            ui.html('<div class="evidence-kicker">Purpose-built annotation</div>')
            ui.html('<div class="evidence-title">Give experts the context needed to make a product call.</div>')
            ui.html(
                '<div class="evidence-copy">'
                "AI PMs need labels that explain user impact, not just pass/fail scores. "
                "The workbench keeps the user request, model response, expected behavior, "
                "risk, memo, and codebook in one review path."
                "</div>"
            )
            with ui.element("div").classes("annotation-grid"):
                for surface in ANNOTATION_SURFACES:
                    with ui.element("div").classes("annotation-surface"):
                        with ui.element("div").classes("annotation-surface-top"):
                            ui.icon(surface["icon"]).style(
                                "color: var(--accent-bright); font-size: 1rem"
                            )
                            ui.html(f'<div class="annotation-surface-title">{surface["title"]}</div>')
                        ui.html(f'<div class="annotation-surface-copy">{surface["copy"]}</div>')
            with ui.element("div").classes("principle-row"):
                for title, copy in [
                    ("See the user impact", "Review the scenario as the customer experiences it, with expected behavior and risk in the same frame."),
                    ("Prioritize release blockers", "Use severity, frequency, and confidence to separate must-fix failures from product polish."),
                    ("Create engineering-ready gates", "Convert expert codes, memos, and examples into judge criteria and hard-fail rules."),
                ]:
                    with ui.element("div").classes("principle-card"):
                        ui.html(f'<div class="principle-title">{title}</div>')
                        ui.html(f'<div class="principle-copy">{copy}</div>')

        # ── Domain expertise proof (3 examples) ───────────────────────────
        with ui.element("div").classes("evidence-panel animate-in stagger-3"):
            ui.html('<div class="evidence-kicker">What the domain expert discovers</div>')
            ui.html(
                '<div class="evidence-title">'
                "These are not generic hallucination labels."
                "</div>"
            )
            ui.html(
                '<div class="evidence-copy">'
                "Domain experts catch the failures that generic eval labels flatten away."
                "</div>"
            )
            with ui.element("div").classes("evidence-grid"):
                for item in EXPERT_DISCOVERIES[:3]:
                    with ui.element("div").classes("evidence-card"):
                        with ui.element("div").classes("evidence-card-top"):
                            ui.html(f'<div class="evidence-domain">{item["domain"]}</div>')
                            ui.html(f'<div class="evidence-code">{item["error_code"]}</div>')
                        ui.html('<div class="evidence-label">What happened</div>')
                        ui.html(f'<div class="evidence-value">{item["what_happened"]}</div>')
                        ui.html('<div class="evidence-label">Why only an expert catches it</div>')
                        ui.html(f'<div class="evidence-value">{item["expert_signal"]}</div>')

        # ── Compact domain badge grid ─────────────────────────────────────
        ui.html('<div id="domain-section"></div>')
        with ui.element("div").classes("mkt-section-head animate-in stagger-3"):
            with ui.column().style("gap: 2px"):
                ui.html(f'<div class="mkt-section-title">{len(domain_cards)} domains tested</div>')
                ui.html(
                    '<div class="mkt-section-sub">'
                    "Load any scenario to see how expert observations become failure codes and judges."
                    "</div>"
                )
            ui.button(
                "View all →", icon="open_in_new",
                on_click=lambda: ui.navigate.to("/demos"),
            ).props("flat size=sm no-caps").style(
                "color: var(--accent-bright); font-size: 0.78rem"
            )

        with ui.element("div").style(
            "display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); "
            "gap: 8px; width: 100%"
        ).classes("animate-in stagger-3"):
            for domain in domain_cards:
                def make_loader(d=domain):
                    def _load():
                        d["loader"](app.storage.user)
                        ui.notify(f'{d["name"]} loaded into the annotation workbench.', type="positive")
                        ui.navigate.to("/coding")
                    return _load

                with ui.element("div").style(
                    "display: flex; align-items: center; gap: 8px; padding: 10px 12px; "
                    "border-radius: var(--radius-lg); border: 1px solid var(--border-subtle); "
                    "background: var(--bg-surface-1); cursor: pointer; transition: border-color 0.15s"
                ).on("click", make_loader()):
                    ui.icon(domain["icon"]).style("color: var(--accent-bright); font-size: 0.95rem")
                    ui.label(domain["name"]).style(
                        "font-size: 0.75rem; font-weight: 600; color: var(--text-primary); "
                        "white-space: nowrap; overflow: hidden; text-overflow: ellipsis"
                    )

        # ── Final CTA ────────────────────────────────────────────────────
        with ui.element("div").style(
            "margin-top: 1.5rem; text-align: center; padding: 18px; "
            "border-radius: var(--radius-xl); background: var(--bg-surface-1); "
            "border: 1px solid var(--border-subtle)"
        ).classes("animate-in stagger-4"):
            ui.html(
                '<div style="font-size:0.88rem; font-weight:600; color:var(--text-primary); margin-bottom:6px">'
                "Ready to find what your agent gets wrong?"
                "</div>"
            )
            with ui.row().classes("justify-center gap-2").style("margin-top: 10px"):
                ui.button(
                    "Open Coach",
                    icon="auto_awesome",
                    on_click=lambda: ui.navigate.to("/coach"),
                ).props("color=primary size=sm unelevated").style("font-weight: 600")
                ui.button(
                    "Load a demo",
                    icon="collections_bookmark",
                    on_click=lambda: (domain_cards[0]["loader"](app.storage.user), ui.navigate.to("/coding")),
                ).props("outline size=sm no-caps").style(
                    "color: var(--accent-bright); border-color: var(--border-subtle)"
                )

        # ── (Methodology and closing removed — see /demos for details) ──
