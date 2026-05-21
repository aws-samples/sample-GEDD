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
        ui.html('<div class="brand-title" style="font-size:1.4rem; color:#f7f8f8; font-weight:700">GEDD</div>')
        ui.html('<div style="font-size:0.8rem; color:#6e737b">Grounded Eval-Driven Development</div>')
        with ui.card().style("width: 320px; padding: 2rem; border-radius: 12px; background: #141516; border: 1px solid rgba(255,255,255,0.09)"):
            ui.label("Sign in").style("font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: #f7f8f8")
            email = ui.input("Email").classes("w-full").props("dark outlined dense")
            password = ui.input("Password", password=True, password_toggle_button=True).classes("w-full").props("dark outlined dense").on("keydown.enter", try_login)
            ui.button("Login", on_click=try_login).classes("w-full").style(
                "margin-top: 1rem; background: #5e6ad2; color: white; border-radius: 6px"
            )

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
:root {
  --bg-base: #08090a; --bg-surface-1: #0f1011; --bg-surface-2: #141516; --bg-surface-3: #191a1b; --bg-hover: #232326;
  --border-subtle: rgba(255,255,255,0.06); --border-default: rgba(255,255,255,0.09); --border-strong: rgba(255,255,255,0.14);
  --text-primary: #f7f8f8; --text-secondary: #b4b8c0; --text-tertiary: #6e737b; --text-muted: #4a4e55;
  --accent: #5e6ad2; --accent-bright: #828fff; --accent-tint: rgba(94,106,210,0.12);
  --green: #27a644; --green-bright: #4ade80; --green-tint: rgba(39,166,68,0.12);
  --yellow: #f0bf00; --yellow-tint: rgba(240,191,0,0.1);
  --red: #eb5757; --red-tint: rgba(235,87,87,0.1);
}
body { font-family: 'Inter', -apple-system, sans-serif !important; background: var(--bg-base) !important; color: var(--text-primary) !important; font-size: 0.875rem; letter-spacing: -0.011em; -webkit-font-smoothing: antialiased; }
.q-page, .q-layout, .q-page-container, .nicegui-content { background: var(--bg-base) !important; color: var(--text-primary) !important; }
.q-card { background: var(--bg-surface-2) !important; color: var(--text-primary) !important; border: 1px solid var(--border-subtle) !important; box-shadow: none !important; }
.q-tab { color: var(--text-tertiary) !important; }
.q-tab--active { color: var(--accent-bright) !important; }
.q-tab-panel { background: transparent !important; }
.q-separator { background: var(--border-subtle) !important; }
.q-field__control { background: var(--bg-surface-1) !important; color: var(--text-primary) !important; }
.q-field__label, .q-field__native, .q-field__input { color: var(--text-primary) !important; }
::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: transparent; } ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 99px; }
.brand-title { font-size: 1.2rem; font-weight: 700; color: var(--text-primary); }
.brand-subtitle { font-size: 0.78rem; color: var(--text-tertiary); }
.chat-card { background: var(--bg-surface-2); border-radius: 12px; border: 1px solid var(--border-subtle); }
.msg-user { background: var(--accent-tint); border: 1px solid rgba(94,106,210,0.2); border-radius: 10px; padding: 12px 16px; margin: 6px 0; color: var(--text-primary); }
.msg-ai { background: var(--bg-surface-1); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 12px 16px; margin: 6px 0; border-left: 3px solid var(--accent); color: var(--text-secondary); }
.msg-ai strong { color: var(--text-primary); }
.msg-error { background: var(--red-tint); border: 1px solid rgba(235,87,87,0.2); border-radius: 10px; padding: 12px 16px; margin: 6px 0; border-left: 3px solid var(--red); color: var(--text-secondary); }
.input-box { border-radius: 10px !important; background: var(--bg-surface-1) !important; border: 1px solid var(--border-default) !important; font-size: 0.88rem !important; color: var(--text-primary) !important; transition: border-color 150ms ease !important; }
.input-box:focus-within { border-color: var(--accent) !important; }
.send-btn { background: var(--accent) !important; color: white !important; transition: opacity 150ms ease !important; }
.send-btn:hover { opacity: 0.85 !important; }
.progress-track { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; margin-bottom: 1rem; background: var(--bg-surface-2); border-radius: 10px; border: 1px solid var(--border-subtle); }
.progress-dot { display: flex; flex-direction: column; align-items: center; flex: 1; }
.dot-circle { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.72rem; font-weight: 600; background: var(--bg-hover); color: var(--text-muted); transition: all 0.3s ease; }
.progress-dot.active .dot-circle { background: var(--green-tint); color: var(--green-bright); }
.progress-dot.current .dot-circle { background: var(--accent); color: white; box-shadow: 0 0 12px rgba(94,106,210,0.4); }
.dot-label { font-size: 0.6rem; color: var(--text-muted); margin-top: 4px; font-weight: 500; }
.progress-dot.active .dot-label { color: var(--green-bright); }
.progress-dot.current .dot-label { color: var(--accent-bright); font-weight: 600; }
.sidebar-panel { width: 320px; min-width: 320px; padding: 1.25rem 1rem; background: var(--bg-surface-2); border-radius: 12px; border: 1px solid var(--border-subtle); height: fit-content; position: sticky; top: 1rem; max-height: 90vh; overflow-y: auto; }
.sidebar-section { margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid var(--border-subtle); }
.sidebar-section:last-child { border-bottom: none; }
.sidebar-title { font-size: 0.65rem; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; }
.sidebar-value { font-size: 0.85rem; font-weight: 600; color: var(--text-primary); }
.sidebar-detail { font-size: 0.75rem; color: var(--text-secondary); line-height: 1.4; }
.sidebar-empty { font-size: 0.75rem; color: var(--text-muted); }
.annotation-correct { color: var(--green-bright); } .annotation-partial { color: var(--yellow); } .annotation-incorrect { color: var(--red); }
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
    ui.add_head_html(f"<style>{CUSTOM_CSS}</style>")

    s = _user_state()
    session = _user_session()
    messages = s["messages"]

    # Header
    def logout():
        app.storage.user["authenticated"] = False
        ui.navigate.to("/login")

    def new_agent():
        s = _user_state()
        s["session_data"] = Session().model_dump(mode="json")
        s["current_step"] = 1
        s["annotations"] = []
        s["messages"] = []
        s["prompt_variants"] = []
        ui.navigate.to("/coach")

    with ui.row().classes("w-full items-center").style("padding: 0.5rem 1rem 0"):
        ui.button("New Agent", icon="restart_alt", on_click=new_agent).props("flat dense size=sm").style("color: var(--text-tertiary)").tooltip("Start over")
        ui.html(
            '<div style="text-align:center; flex:1">'
            '<div class="brand-title">GEDD Coach</div>'
            '<div class="brand-subtitle">Define your agent & system prompt</div></div>'
        )
        ui.button(icon="logout", on_click=logout).props("flat round size=sm").style("color: var(--text-muted)").tooltip("Logout")

    # Progress: 3 steps
    with ui.column().classes("w-full items-center").style("max-width: 720px; margin: 0.75rem auto 0"):
        progress_container = ui.element("div").classes("w-full")

        def refresh_progress():
            progress_container.clear()
            step = min(_user_state()["current_step"], 3)
            steps = ["Define Agent", "System Prompt", "Golden Queries"]
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

        # Chat card
        with ui.card().classes("w-full chat-card").style("padding: 1.5rem; margin-top: 0.75rem"):
            chat_container = ui.column().classes("w-full").style(
                "max-height: 62vh; overflow-y: auto; padding-right: 8px"
            )
            with chat_container:
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
                            'I\'ll guide you through 3 steps:<br>'
                            '1. <strong>Define your agent</strong> — name, capabilities, users<br>'
                            '2. <strong>Craft a system prompt</strong><br>'
                            '3. <strong>Generate golden test queries</strong> using Open Coding<br><br>'
                            'Then you\'ll move to Eval to run them. <strong>What AI agent are you building?</strong></div>'
                        )
                    elif step == 2:
                        welcome = (
                            f'<div class="msg-ai"><strong>Welcome back!</strong> Your agent '
                            f'<strong>{session.agent_spec.name}</strong> is defined.<br><br>'
                            f'Let\'s work on the <strong>system prompt</strong>. What should your agent\'s personality and rules be?</div>'
                        )
                    else:
                        welcome = (
                            f'<div class="msg-ai"><strong>Welcome back!</strong> '
                            f'Agent and system prompt are set for <strong>{session.agent_spec.name}</strong>.<br><br>'
                            f'Ready to generate <strong>golden test queries</strong> using Open Coding. '
                            f'Say "generate queries" to start!</div>'
                        )
                    ui.html(welcome)

            ui.separator().style("opacity: 0.1; margin: 12px 0")
            with ui.row().classes("w-full items-center gap-sm"):
                user_input = ui.input(placeholder="Tell me about your AI agent...").classes("flex-grow input-box").props("borderless dense")
                send_btn = ui.button(icon="arrow_upward").classes("send-btn").props("round size=md")

            # Downloads
            def _download_system_prompt():
                cur = _user_session()
                if not cur.agent_spec.system_prompt:
                    ui.notify("No system prompt yet", type="warning")
                    return
                ui.download(cur.agent_spec.system_prompt.encode(), "system_prompt.txt")

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

            with ui.row().classes("w-full justify-center gap-sm").style("margin-top: 8px"):
                ui.button("System Prompt", icon="download", on_click=_download_system_prompt).props("flat size=sm").style("text-transform: none; color: var(--text-tertiary)")
                ui.button("Golden Queries (CSV)", icon="download", on_click=_download_queries_csv).props("flat size=sm").style("text-transform: none; color: var(--text-tertiary)")

        # "Next step" nudge when ready
        if session.golden_prompts:
            with ui.element("div").style(
                "margin-top: 12px; padding: 12px 16px; border-radius: 10px; "
                "background: var(--green-tint); border: 1px solid rgba(39,166,68,0.2); text-align: center"
            ):
                ui.label(f"✓ {len(session.golden_prompts)} golden queries generated. Ready to evaluate →").style("font-size: 0.82rem; color: var(--green-bright); font-weight: 500")
                ui.button("Go to Eval", icon="arrow_forward", on_click=lambda: ui.navigate.to("/eval")).props("size=sm").style(
                    "margin-top: 6px; background: var(--accent); color: white; border-radius: 6px"
                )

    # Send message handler
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
            ui.run_javascript("document.querySelector('[style*=\"overflow-y: auto\"]').scrollTop=999999")

    send_btn.on_click(send_message)
    user_input.on("keydown.enter", send_message)


def run() -> None:
    ui.run(
        title="GEDD — Grounded Eval Driven Development",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8080")),
        reload=os.environ.get("NICEGUI_RELOAD", "true").lower() == "true",
        storage_secret=os.environ.get("STORAGE_SECRET", "dev-secret-change-me"),
    )


if __name__ in {"__main__", "__mp_main__"}:
    run()
