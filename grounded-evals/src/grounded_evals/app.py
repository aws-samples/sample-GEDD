"""Agent Playground v1.0 — Golden Queries + Error Analysis with Open Coding."""

import asyncio
import csv
import io
import json
import os

from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app, ui
from starlette.middleware.base import BaseHTTPMiddleware

from grounded_evals.agent import StateBundle, run_agent_turn
from grounded_evals.agentcore_client import get_agentcore_client
from grounded_evals.guide.session import Session

# Import new pages (registers their @ui.page routes)
import grounded_evals.ui.home_page  # noqa: F401
import grounded_evals.ui.eval_page  # noqa: F401
import grounded_evals.ui.coding_page  # noqa: F401
import grounded_evals.ui.analysis_page  # noqa: F401
import grounded_evals.ui.report_page  # noqa: F401

# --- Authentication via Cognito ---
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")
COGNITO_REGION = os.environ.get("AWS_REGION", "us-east-1")
# Fallback password if Cognito not configured
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "playground2024")
UNRESTRICTED_PATHS = {"/login", "/_nicegui", "/favicon.ico", "/health"}


def _cognito_auth(email: str, password: str) -> bool:
    """Authenticate user against Cognito User Pool via SRP."""
    if not COGNITO_USER_POOL_ID or not COGNITO_CLIENT_ID:
        return password == ADMIN_PASSWORD
    import boto3
    client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
    try:
        client.initiate_auth(
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )
        return True
    except client.exceptions.NotAuthorizedException:
        return False
    except client.exceptions.UserNotFoundException:
        return False
    except Exception:
        return False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in UNRESTRICTED_PATHS):
            return await call_next(request)
        if not app.storage.user.get("authenticated", False):
            return RedirectResponse("/login")
        return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


app.add_middleware(AuthMiddleware)


@ui.page("/login")
def login_page():
    ui.add_head_html(f"<style>{CUSTOM_CSS}</style>")

    def try_login():
        if _cognito_auth(email.value, password.value):
            app.storage.user["authenticated"] = True
            app.storage.user["email"] = email.value
            ui.navigate.to("/")
        else:
            ui.notify("Invalid credentials", type="negative")

    with ui.column().classes("absolute-center items-center").style("gap: 1.5rem"):
        ui.html('<div class="brand-title">Agent Playground</div>')
        ui.html('<div class="brand-subtitle">Powered by Grounded Eval Driven Development</div>')
        with ui.card().style("width: 320px; padding: 2rem; border-radius: 16px"):
            ui.label("Sign in").style("font-size: 1.2rem; font-weight: 600; margin-bottom: 0.5rem")
            email = ui.input("Email").classes("w-full")
            password = ui.input("Password", password=True, password_toggle_button=True).classes("w-full").on("keydown.enter", try_login)
            ui.button("Login", on_click=try_login).classes("w-full send-btn").style("margin-top: 1rem; color: white; border-radius: 8px")

def _user_state() -> dict:
    """Get or initialize per-user state from app.storage.user."""
    s = app.storage.user
    if "session_data" not in s:
        s["session_data"] = Session().model_dump(mode="json")
        s["current_step"] = 1
        s["annotations"] = []
        s["messages"] = []
        s["prompt_variants"] = []
    if 'codebook' not in s:
        s['codebook'] = []
    if 'coding_annotations' not in s:
        s['coding_annotations'] = []
    if 'memos' not in s:
        s['memos'] = []
    if 'paradigm_model' not in s:
        s['paradigm_model'] = {'phenomenon': [], 'causal_conditions': [], 'context': [], 'intervening_conditions': [], 'strategies': [], 'consequences': []}
    if 'failure_patterns' not in s:
        s['failure_patterns'] = []
    return s


def _user_session() -> Session:
    """Reconstruct Session from stored user data."""
    s = _user_state()
    return Session.model_validate(s["session_data"])


def _save_user_session(session: Session) -> None:
    """Persist Session back to user storage."""
    app.storage.user["session_data"] = session.model_dump(mode="json")


CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root { --brand-green: #16a34a; --brand-dark: #14532d; --brand-accent: #4ade80; --text-secondary: #6b7280; --text-muted: #9ca3af; }
body { font-family: 'Inter', sans-serif !important; background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 50%, #f0f9ff 100%) !important; }
.brand-title { font-size: 1.8rem; font-weight: 700; background: linear-gradient(135deg, #14532d, #16a34a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.brand-subtitle { font-size: 0.85rem; color: var(--text-secondary); }
.chat-card { background: white; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.06); border: 1px solid #e5e7eb; }
.msg-user { background: linear-gradient(135deg, #dcfce7, #d1fae5); border-radius: 12px; padding: 12px 16px; margin: 6px 0; }
.msg-ai { background: white; border-radius: 12px; padding: 12px 16px; margin: 6px 0; border-left: 3px solid var(--brand-accent); box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.msg-error { background: #fff7ed; border-radius: 12px; padding: 12px 16px; margin: 6px 0; border-left: 3px solid #fb923c; }
.input-box { border-radius: 24px !important; background: white !important; box-shadow: 0 2px 12px rgba(0,0,0,0.08) !important; border: 1.5px solid #e5e7eb !important; font-size: 0.95rem !important; transition: border-color 0.2s, box-shadow 0.2s !important; }
.input-box:focus-within { border-color: var(--brand-accent) !important; box-shadow: 0 2px 16px rgba(74,222,128,0.2) !important; }
.send-btn { background: linear-gradient(135deg, #16a34a, #15803d) !important; box-shadow: 0 2px 8px rgba(22,163,74,0.3) !important; transition: transform 0.1s !important; }
.send-btn:hover { transform: scale(1.05) !important; }
.send-btn:active { transform: scale(0.95) !important; }
.progress-track { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; margin-bottom: 1rem; background: white; border-radius: 12px; box-shadow: 0 1px 8px rgba(0,0,0,0.04); }
.progress-dot { display: flex; flex-direction: column; align-items: center; flex: 1; }
.dot-circle { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 600; background: #f3f4f6; color: #9ca3af; transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); }
.progress-dot.active .dot-circle { background: #dcfce7; color: #16a34a; }
.progress-dot.current .dot-circle { background: linear-gradient(135deg, #16a34a, #15803d); color: white; box-shadow: 0 2px 8px rgba(22,163,74,0.3); transform: scale(1.15); animation: dot-pulse 2s ease-in-out infinite; }
.dot-label { font-size: 0.65rem; color: #9ca3af; margin-top: 4px; font-weight: 500; }
.progress-dot.active .dot-label { color: #16a34a; }
.progress-dot.current .dot-label { color: #14532d; font-weight: 700; }
@keyframes dot-pulse { 0%, 100% { box-shadow: 0 2px 8px rgba(22,163,74,0.3); } 50% { box-shadow: 0 2px 16px rgba(22,163,74,0.6), 0 0 24px rgba(74,222,128,0.2); } }
.sidebar-panel { width: 320px; min-width: 320px; padding: 1.5rem 1rem; background: white; border-radius: 16px; border: 1px solid #e5e7eb; box-shadow: 0 2px 12px rgba(0,0,0,0.04); height: fit-content; position: sticky; top: 1rem; max-height: 90vh; overflow-y: auto; }
.sidebar-section { margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #f3f4f6; }
.sidebar-section:last-child { border-bottom: none; }
.sidebar-title { font-size: 0.7rem; font-weight: 600; color: #16a34a; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; }
.sidebar-value { font-size: 0.85rem; font-weight: 600; color: #1a1a1a; }
.sidebar-detail { font-size: 0.75rem; color: #6b7280; line-height: 1.4; }
.sidebar-empty { font-size: 0.75rem; color: #d1d5db; }
.annotation-correct { color: #16a34a; } .annotation-partial { color: #d97706; } .annotation-incorrect { color: #dc2626; }
"""

USE_AGENTCORE = bool(os.environ.get("AGENTCORE_AGENT_ID") or os.environ.get("AGENTCORE_AGENT_ARN"))
_agentcore = get_agentcore_client()


def _get_state_bundle() -> StateBundle:
    """Build a StateBundle from per-user storage."""
    s = _user_state()
    session = _user_session()
    return StateBundle(
        session=session,
        annotations=s["annotations"],
        current_step=s["current_step"],
        prompt_variants=s["prompt_variants"],
    )


def _sync_state_from_bundle(state: StateBundle) -> None:
    """Sync per-user storage after agent turn mutates the bundle."""
    s = _user_state()
    s["current_step"] = state.current_step
    s["annotations"] = state.annotations
    s["prompt_variants"] = state.prompt_variants
    _save_user_session(state.session)


def _apply_agentcore_state(updated_state: dict) -> None:
    """Apply state mutations returned by AgentCore back to per-user storage."""
    if not updated_state:
        return
    s = _user_state()
    session = _user_session()

    agent_data = updated_state.get("agent_spec", {})
    if agent_data.get("name"):
        session.agent_spec.name = agent_data["name"]
    if agent_data.get("description"):
        session.agent_spec.description = agent_data["description"]
    if agent_data.get("capabilities"):
        from grounded_evals.ingest.models import Capability
        session.agent_spec.capabilities = [Capability(name=c["name"] if isinstance(c, dict) else c) for c in agent_data["capabilities"]]
    if agent_data.get("target_users"):
        from grounded_evals.ingest.models import Persona
        session.agent_spec.target_users = [Persona(name=u["name"] if isinstance(u, dict) else u) for u in agent_data["target_users"]]
    if agent_data.get("system_prompt"):
        session.agent_spec.system_prompt = agent_data["system_prompt"]

    if "golden_prompts" in updated_state:
        from uuid import uuid4

        from grounded_evals.models.core import GoldenPrompt
        session.golden_prompts = [
            GoldenPrompt(
                prompt_text=p.get("prompt_text", ""),
                category_id=uuid4(),
                expected_behavior=p.get("expected_behavior", ""),
                rationale=p.get("category", ""),
                property_values={"dimensions": p.get("dimensions", "")},
            )
            for p in updated_state["golden_prompts"]
        ]

    _save_user_session(session)

    if "annotations" in updated_state:
        s["annotations"] = updated_state["annotations"]

    if "current_step" in updated_state:
        s["current_step"] = updated_state["current_step"]

    if "prompt_variants" in updated_state:
        s["prompt_variants"] = updated_state["prompt_variants"]


@ui.page("/coach")
def main_page() -> None:
    from grounded_evals.ui.eval_tab import render as render_eval_tab

    ui.add_head_html(f"<style>{CUSTOM_CSS}</style>")
    ui.add_head_html('<script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.3/dist/confetti.browser.min.js"></script>')

    s = _user_state()
    session = _user_session()
    messages = s["messages"]
    annotations = s["annotations"]
    system_prompt_variants = s["prompt_variants"]

    # Header
    def logout():
        app.storage.user["authenticated"] = False
        ui.navigate.to("/login")

    with ui.row().classes("w-full items-center").style("padding: 0.5rem 1rem 0"):
        ui.html(
            '<div style="text-align:center; flex:1">'
            '<div class="brand-title">Agent Playground</div>'
            '<div class="brand-subtitle">Powered by Grounded Eval Driven Development</div></div>'
        )
        ui.button(icon="logout", on_click=logout).props("flat round size=sm").tooltip("Logout")

    # Tabs
    with ui.tabs().classes("w-full").style(
        "max-width:500px; margin:0 auto 1rem"
    ) as tabs:
        coach_tab = ui.tab("Coach", icon="chat")
        eval_tab_btn = ui.tab("Eval", icon="science")

    with ui.tab_panels(tabs, value=coach_tab).classes("w-full").style(
        "background:transparent"
    ):
        # === COACH TAB ===
        with ui.tab_panel(coach_tab).style("padding:0"):
            with ui.row().classes("w-full").style("padding: 0 1rem"):

                # Chat area
                with ui.column().classes("flex-grow items-center").style("max-width: 720px; margin: 0 auto"):

                    progress_container = ui.element("div").classes("w-full")

            progress_container = ui.element("div").classes("w-full")

            def refresh_progress():
                progress_container.clear()
                step = _user_state()["current_step"]
                steps = ["Define Agent", "System Prompt", "Golden Queries", "Error Analysis"]
                with progress_container:
                    ui.html(
                        '<div class="progress-track">'
                        + "".join(
                            f'<div class="progress-dot {"active" if i + 1 <= step else ""} {"current" if i + 1 == step else ""}">'
                            f'<div class="dot-circle">{"✓" if i + 1 < step else i + 1}</div>'
                            f'<div class="dot-label">{s}</div></div>'
                            for i, s in enumerate(steps)
                        )
                        + "</div>"
                    )

            refresh_progress()

            with ui.card().classes("w-full chat-card").style("padding: 1.5rem"):
                chat_container = ui.column().classes("w-full").style(
                    "max-height: 62vh; overflow-y: auto; padding-right: 8px"
                )
                with chat_container:
                    # Show conversation history if resuming, otherwise welcome
                    if messages:
                        for msg in messages:
                            if msg["role"] == "user" and isinstance(msg["content"], str):
                                ui.html(f'<div class="msg-user">{msg["content"]}</div>')
                            elif msg["role"] == "assistant" and isinstance(msg["content"], str):
                                with ui.element("div").classes("msg-ai"):
                                    ui.markdown(msg["content"])
                    else:
                        step = s["current_step"]
                        if step == 1:
                            welcome = (
                                '<div class="msg-ai"><strong>Hey! 👋 I\'m your eval coach.</strong><br><br>'
                                'I\'ll help you:<br>'
                                '1. Define your agent & system prompt<br>'
                                '2. <strong>Generate golden test queries</strong> using Open Coding<br>'
                                '3. <strong>Analyze errors</strong> by running queries and annotating failures<br><br>'
                                '<strong>What AI agent are you building?</strong></div>'
                            )
                        elif step == 2:
                            welcome = (
                                f'<div class="msg-ai"><strong>Welcome back!</strong> Your agent '
                                f'<strong>{session.agent_spec.name}</strong> is defined.<br><br>'
                                f'Let\'s work on the <strong>system prompt</strong>. What should your agent\'s personality and rules be?</div>'
                            )
                        elif step == 3:
                            welcome = (
                                f'<div class="msg-ai"><strong>Welcome back!</strong> '
                                f'Agent and system prompt are set for <strong>{session.agent_spec.name}</strong>.<br><br>'
                                f'Ready to generate <strong>golden test queries</strong> using Open Coding. '
                                f'Say "let\'s write queries" to start!</div>'
                            )
                        else:
                            welcome = (
                                f'<div class="msg-ai"><strong>Welcome back!</strong> '
                                f'You have <strong>{len(session.golden_prompts)} golden queries</strong>.<br><br>'
                                f'Ready for <strong>error analysis</strong> — I\'ll run each query against your agent '
                                f'and you\'ll annotate the responses. Say "start error analysis" to begin!</div>'
                            )
                        ui.html(welcome)

                ui.separator().style("opacity: 0.2; margin: 12px 0")
                with ui.row().classes("w-full items-center gap-sm"):
                    user_input = ui.input(placeholder="Tell me about your AI agent...").classes("flex-grow input-box").props("borderless dense")
                    send_btn = ui.button(icon="arrow_upward").classes("send-btn").props("round size=md")

                # Download button (visible when golden queries exist)
                def _download_queries_csv():
                    cur = _user_session()
                    if not cur.golden_prompts:
                        ui.notify("No golden queries yet", type="warning")
                        return
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow(["query", "category", "expected_behavior", "dimensions"])
                    for p in cur.golden_prompts:
                        writer.writerow([p.prompt_text, p.rationale, p.expected_behavior, p.property_values.get("dimensions", "")])
                    ui.download(output.getvalue().encode(), "golden_queries.csv")

                def _download_system_prompt():
                    cur = _user_session()
                    if not cur.agent_spec.system_prompt:
                        ui.notify("No system prompt yet", type="warning")
                        return
                    ui.download(cur.agent_spec.system_prompt.encode(), "system_prompt.txt")

                with ui.row().classes("w-full justify-center gap-sm").style("margin-top: 8px"):
                    ui.button("System Prompt", icon="download", on_click=_download_system_prompt).props("flat color=green").style("text-transform: none")
                    ui.button("Golden Queries (CSV)", icon="download", on_click=_download_queries_csv).props("flat color=green").style("text-transform: none")

        # === SIDEBAR ===
        sidebar_container = ui.column().classes("sidebar-panel")

        def _download_agent():
            data = {"name": session.agent_spec.name, "description": session.agent_spec.description, "capabilities": [c.name for c in session.agent_spec.capabilities], "target_users": [u.name for u in session.agent_spec.target_users]}
            ui.download(json.dumps(data, indent=2).encode(), "agent_definition.json")

        def _download_prompt():
            ui.download(session.agent_spec.system_prompt.encode(), "system_prompt.txt")

        def _download_queries():
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["query", "category", "expected_behavior", "dimensions"])
            for p in session.golden_prompts:
                writer.writerow([p.prompt_text, p.rationale, p.expected_behavior, p.property_values.get("dimensions", "")])
            ui.download(output.getvalue().encode(), "golden_queries.csv")

        def _download_annotations():
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["query", "response", "annotation", "model", "error_code", "notes"])
            for a in annotations:
                writer.writerow([a["query"], a["response"], a["annotation"], a.get("model", ""), a.get("error_code", ""), a.get("notes", "")])
            ui.download(output.getvalue().encode(), "error_analysis.csv")

        def refresh_sidebar():
            sidebar_container.clear()
            with sidebar_container:
                ui.label("Outputs").style("font-size:0.95rem; font-weight:700; color:#14532d; margin-bottom:14px")

                # Agent
                with ui.element("div").classes("sidebar-section"):
                    with ui.row().classes("items-center justify-between"):
                        ui.label("Agent Definition").classes("sidebar-title")
                        if session.agent_spec.name:
                            ui.button(icon="download", on_click=_download_agent).props("flat dense round size=xs color=primary").tooltip("JSON")
                    if session.agent_spec.name:
                        ui.label(session.agent_spec.name).classes("sidebar-value")
                        if session.agent_spec.capabilities:
                            ui.label(", ".join(c.name for c in session.agent_spec.capabilities)).classes("sidebar-detail")
                    else:
                        ui.label("—").classes("sidebar-empty")

                # System Prompt
                with ui.element("div").classes("sidebar-section"):
                    with ui.row().classes("items-center justify-between"):
                        ui.label("System Prompt").classes("sidebar-title")
                        if session.agent_spec.system_prompt:
                            ui.button(icon="download", on_click=_download_prompt).props("flat dense round size=xs color=primary").tooltip("TXT")
                    if session.agent_spec.system_prompt:
                        ui.label(session.agent_spec.system_prompt[:100] + "...").classes("sidebar-detail")
                    else:
                        ui.label("—").classes("sidebar-empty")

                # Golden Queries
                with ui.element("div").classes("sidebar-section"):
                    with ui.row().classes("items-center justify-between"):
                        ui.label(f"Golden Queries ({len(session.golden_prompts)})").classes("sidebar-title")
                        if session.golden_prompts:
                            ui.button(icon="download", on_click=_download_queries).props("flat dense round size=xs color=primary").tooltip("CSV")
                    if session.golden_prompts:
                        cats = {}
                        for p in session.golden_prompts:
                            cat = p.rationale or "uncategorized"
                            cats[cat] = cats.get(cat, 0) + 1
                        for cat, count in cats.items():
                            ui.label(f"• {cat}: {count}").classes("sidebar-detail")
                    else:
                        ui.label("—").classes("sidebar-empty")

                # Error Analysis
                with ui.element("div").classes("sidebar-section"):
                    with ui.row().classes("items-center justify-between"):
                        ui.label(f"Error Analysis ({len(annotations)})").classes("sidebar-title")
                        if annotations:
                            ui.button(icon="download", on_click=_download_annotations).props("flat dense round size=xs color=primary").tooltip("CSV")
                    if annotations:
                        correct = sum(1 for a in annotations if a["annotation"] == "correct")
                        partial = sum(1 for a in annotations if a["annotation"] == "partial")
                        incorrect = sum(1 for a in annotations if a["annotation"] == "incorrect")
                        ui.html(
                            f'<span class="sidebar-detail">'
                            f'<span class="annotation-correct">✓ {correct}</span> &nbsp; '
                            f'<span class="annotation-partial">⚠ {partial}</span> &nbsp; '
                            f'<span class="annotation-incorrect">✗ {incorrect}</span>'
                            f'</span>'
                        )
                        error_codes = list({a["error_code"] for a in annotations if a.get("error_code")})
                        if error_codes:
                            ui.label("Error codes:").classes("sidebar-detail").style("margin-top:4px; font-weight:600")
                            for code in error_codes:
                                count = sum(1 for a in annotations if a.get("error_code") == code)
                                ui.label(f"  • {code} ({count})").classes("sidebar-detail")
                    else:
                        ui.label("—").classes("sidebar-empty")

        refresh_sidebar()

        # === SEND MESSAGE ===
        async def send_message():
            text = user_input.value.strip()
            if not text:
                return
            user_input.set_value("")
            with chat_container:
                ui.html(f'<div class="msg-user">{text}</div>')
            send_btn.props("loading")

            try:
                if USE_AGENTCORE and _agentcore:
                    from uuid import uuid4
                    session_id = str(uuid4())
                    cur_session = _user_session()
                    cur_s = _user_state()
                    state_dict = {
                        "agent_spec": cur_session.agent_spec.model_dump(mode="json") if hasattr(cur_session.agent_spec, "model_dump") else {},
                        "golden_prompts": [{"prompt_text": p.prompt_text, "category": p.rationale, "expected_behavior": p.expected_behavior, "dimensions": p.property_values.get("dimensions", "")} for p in cur_session.golden_prompts],
                        "annotations": cur_s["annotations"],
                        "current_step": cur_s["current_step"],
                        "prompt_variants": cur_s["prompt_variants"],
                    }
                    coach_resp = await asyncio.to_thread(
                        _agentcore.invoke_coach, text, session_id, state_dict, messages
                    )
                    _apply_agentcore_state(coach_resp.updated_state)
                    reply = coach_resp.text
                    if coach_resp.messages:
                        messages.clear()
                        messages.extend(coach_resp.messages)
                else:
                    state = _get_state_bundle()
                    response = await asyncio.to_thread(
                        run_agent_turn, text, messages, state
                    )
                    _sync_state_from_bundle(state)
                    reply = response.text

                if reply:
                    with chat_container:
                        with ui.element("div").classes("msg-ai"):
                            ui.markdown(reply)

            except Exception as e:
                import traceback
                traceback.print_exc()
                with chat_container:
                    ui.html(f'<div class="msg-error"><strong>Error</strong><br><small>{e}</small></div>')
            finally:
                send_btn.props(remove="loading")
                refresh_progress()
                # Re-read state for sidebar
                session = _user_session()
                annotations = _user_state()["annotations"]
                refresh_sidebar()
                ui.run_javascript("document.querySelector('[style*=\"overflow-y: auto\"]').scrollTop=999999")

        send_btn.on_click(send_message)
        user_input.on("keydown.enter", send_message)

        # === EVAL TAB ===
        with ui.tab_panel(eval_tab_btn).style("padding:0 1rem"):
            eval_panel_container = ui.column().classes("w-full")

    def on_tab_change(e):
        if e.value == "Eval":
            eval_panel_container.clear()
            with eval_panel_container:
                render_eval_tab(_user_session(), _user_state()["annotations"], _user_state()["prompt_variants"])

    tabs.on_value_change(on_tab_change)


def run() -> None:
    ui.run(
        title="Agent Playground — Grounded Eval Driven Development",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8080")),
        reload=os.environ.get("NICEGUI_RELOAD", "true").lower() == "true",
        storage_secret=os.environ.get("STORAGE_SECRET", "dev-secret-change-me"),
    )


if __name__ in {"__main__", "__mp_main__"}:
    run()
