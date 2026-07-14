"""GEDD — generate Kiro requirements.md and an LLM Judge from annotations."""

import asyncio
import html as _html
import json
import os
import secrets
import urllib.parse
import urllib.request

from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app, ui
from starlette.middleware.base import BaseHTTPMiddleware

import grounded_evals.ui.analysis_page  # noqa: F401
import grounded_evals.ui.coding_page  # noqa: F401
import grounded_evals.ui.demos_page  # noqa: F401
import grounded_evals.ui.ears_page  # noqa: F401
import grounded_evals.ui.eval_page  # noqa: F401
import grounded_evals.ui.gdpr_demo_page  # noqa: F401
import grounded_evals.ui.mass_effect_demo_page  # noqa: F401

# Import new pages (registers their @ui.page routes)
import grounded_evals.ui.home_page  # noqa: F401
import grounded_evals.ui.improvement_page  # noqa: F401
import grounded_evals.ui.judge_builder_page  # noqa: F401
import grounded_evals.ui.report_page  # noqa: F401
from grounded_evals.agent import StateBundle, run_agent_turn
from grounded_evals.agentcore_client import get_agentcore_client
from grounded_evals.guide.session import Session
from grounded_evals.ui.baseline_requirements import render_baseline_requirements_upload
from grounded_evals.ui.layout import BRAND_CSS, page_layout

# --- Authentication via Cognito ---
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")
COGNITO_DOMAIN = os.environ.get("COGNITO_DOMAIN", "")
COGNITO_REGION = os.environ.get("AWS_REGION", "us-east-1")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
# Fallback password if Cognito not configured — must be set explicitly; no hardcoded default
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
# Guest mode: no auth required when neither Cognito nor ADMIN_PASSWORD is configured.
# This is the default for local dev / demo runs with `grounded-evals serve`.
GUEST_MODE = not ADMIN_PASSWORD and not COGNITO_USER_POOL_ID
UNRESTRICTED_PATHS = {"/login", "/auth/callback", "/_nicegui", "/favicon.ico", "/health"}
APP_RELEASE = "2026-06-12-localization-50"


def _cognito_hosted_domain() -> str:
    if "." in COGNITO_DOMAIN:
        return COGNITO_DOMAIN
    return f"{COGNITO_DOMAIN}.auth.{COGNITO_REGION}.amazoncognito.com"


def _public_base_url(request: Request | None = None) -> str:
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    if request is None:
        return ""
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    forwarded_host = request.headers.get("x-forwarded-host", request.headers.get("host", ""))
    return f"{forwarded_proto}://{forwarded_host}".rstrip("/")


def _cognito_login_redirect(request: Request) -> RedirectResponse:
    base_url = _public_base_url(request)
    redirect_uri = f"{base_url}/auth/callback"
    state = secrets.token_urlsafe(24)
    app.storage.user["oauth_state"] = state
    params = urllib.parse.urlencode({
        "client_id": COGNITO_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect_uri,
        "state": state,
    })
    return RedirectResponse(f"https://{_cognito_hosted_domain()}/login?{params}")


def _exchange_cognito_code(code: str, redirect_uri: str) -> dict:
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": COGNITO_CLIENT_ID,
        "code": code,
        "redirect_uri": redirect_uri,
    }).encode()
    request = urllib.request.Request(
        f"https://{_cognito_hosted_domain()}/oauth2/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _cognito_auth(email: str, password: str) -> bool:
    """Authenticate user against Cognito User Pool via SRP."""
    if not COGNITO_USER_POOL_ID or not COGNITO_CLIENT_ID:
        if not ADMIN_PASSWORD:
            return False
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
        return bool(ADMIN_PASSWORD and password == ADMIN_PASSWORD)
    except client.exceptions.UserNotFoundException:
        return bool(ADMIN_PASSWORD and password == ADMIN_PASSWORD)
    except Exception as e:
        import warnings
        warnings.warn(f"Cognito auth error (non-credential): {e}", stacklevel=2)
        return False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in UNRESTRICTED_PATHS):
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store, max-age=0"
            return response
        if GUEST_MODE:
            app.storage.user["authenticated"] = True
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["X-GEDD-Release"] = APP_RELEASE
            return response
        if not app.storage.user.get("authenticated", False):
            if COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID and COGNITO_DOMAIN:
                return _cognito_login_redirect(request)
            return RedirectResponse("/login")
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["X-GEDD-Release"] = APP_RELEASE
        return response


@app.get("/health")
def health():
    return {"status": "ok", "release": APP_RELEASE}


app.add_middleware(AuthMiddleware)

# Serve docs directory for demo gif and static assets
from pathlib import Path as _Path
_docs_dir = _Path(__file__).parent.parent.parent / "docs"
if not _docs_dir.exists():
    _docs_dir = _Path("/app/docs")
if _docs_dir.exists():
    app.add_static_files("/docs", str(_docs_dir))


@ui.page("/login")
def login_page():
    ui.add_head_html(f"<style>{BRAND_CSS}</style>")

    # In guest mode, skip the login wall entirely
    if GUEST_MODE:
        app.storage.user["authenticated"] = True
        ui.navigate.to("/")
        return
    if COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID and COGNITO_DOMAIN:
        ui.navigate.to("/")
        return

    def try_login():
        if _cognito_auth(email.value, password.value):
            app.storage.user["authenticated"] = True
            app.storage.user["email"] = email.value
            ui.navigate.to("/")
        else:
            ui.notify("Invalid credentials", type="negative")

    with ui.column().classes("absolute-center items-center").style("gap: 1.5rem"):
        ui.html('<div class="brand-title" style="font-size:1.4rem; color:#f7f8f8; font-weight:700">GEDD</div>')
        ui.html(
            '<div style="font-size:0.8rem; color:#6e737b">'
            "SME Error Analysis → Annotations → Domain Driven Specs Development"
            "</div>"
        )
        with ui.card().style("width: 320px; padding: 2rem; border-radius: 12px; background: #141516; border: 1px solid rgba(255,255,255,0.09)"):
            ui.label("Sign in").style("font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: #f7f8f8")
            email = ui.input("Email").classes("w-full").props("dark outlined dense")
            password = ui.input("Password", password=True, password_toggle_button=True).classes("w-full").props("dark outlined dense").on("keydown.enter", try_login)
            ui.button("Login", on_click=try_login).classes("w-full").style(
                "margin-top: 1rem; background: #5e6ad2; color: white; border-radius: 6px"
            )


@app.get("/auth/callback")
def auth_callback(request: Request, code: str = "", state: str = ""):
    expected_state = app.storage.user.get("oauth_state", "")
    if not code or not state or state != expected_state:
        return RedirectResponse("/login")
    base_url = _public_base_url(request)
    try:
        tokens = _exchange_cognito_code(code, f"{base_url}/auth/callback")
    except Exception as exc:
        import warnings
        warnings.warn(f"Cognito OAuth callback failed: {exc}", stacklevel=2)
        return RedirectResponse("/login")
    app.storage.user["authenticated"] = True
    app.storage.user["oauth_tokens"] = tokens
    app.storage.user.pop("oauth_state", None)
    return RedirectResponse("/")

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
    s['user_needs'] = [
        {
            'description': item.get('description') or item.get('need') or str(item),
            'importance': item.get('importance', 'medium'),
            'satisfaction': item.get('satisfaction', 'ok'),
        }
        if isinstance(item, dict)
        else {'description': str(item), 'importance': 'medium', 'satisfaction': 'ok'}
        for item in s.get('user_needs', [])
    ]
    s['hypotheses'] = [
        {
            'text': item.get('text') or item.get('hypothesis') or str(item),
            'status': item.get('status', 'active'),
        }
        if isinstance(item, dict)
        else {'text': str(item), 'status': 'active'}
        for item in s.get('hypotheses', [])
    ]
    return s


def _user_session() -> Session:
    """Reconstruct Session from stored user data."""
    s = _user_state()
    return Session.model_validate(s["session_data"])


def _save_user_session(session: Session) -> None:
    """Persist Session back to user storage."""
    app.storage.user["session_data"] = session.model_dump(mode="json")



USE_AGENTCORE = bool(os.environ.get("AGENTCORE_AGENT_ID") or os.environ.get("AGENTCORE_AGENT_ARN"))
_agentcore = None  # lazily initialized on first use to avoid startup failures


def _get_agentcore():
    global _agentcore
    if USE_AGENTCORE and _agentcore is None:
        _agentcore = get_agentcore_client()
    return _agentcore


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
    if agent_data.get("domain_context"):
        session.agent_spec.domain_context = agent_data["domain_context"]
    if agent_data.get("known_edge_cases"):
        session.agent_spec.known_edge_cases = agent_data["known_edge_cases"]
    if agent_data.get("constraints"):
        session.agent_spec.constraints = agent_data["constraints"]
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
    page_layout("Coach", current_path="/coach")

    s = _user_state()
    messages = s["messages"]

    def coach_status(done: bool, current: bool) -> str:
        if done:
            return "done"
        return "current" if current else "next"

    coach_prompts = {
        1: "Use the chat: what domain are you the expert in, who uses this agent, and what can go wrong?",
        2: "Attach the baseline Kiro requirements.md, or describe the baseline requirements if the file is not available.",
        3: "Ask Coach to draft the first query batch, then approve, edit, or add SME-owned queries.",
        4: "Run the approved queries against the baseline Kiro agent, then paste the responses here.",
        5: "Open Annotations and label each baseline response with SME vocabulary and missing domain rules.",
        6: "Open Evidence and use SME_error_analysis.md as the source for requirements.md and the LLM Judge.",
    }

    def current_coach_view() -> tuple[int, tuple[str, str, str, str, str]]:
        cur_s = _user_state()
        cur_session = _user_session()
        has_domain = bool(cur_session.agent_spec.domain_context or cur_session.agent_spec.name)
        has_baseline_spec = bool(
            cur_s.get("baseline_requirements_md") or cur_session.agent_spec.system_prompt
        )
        has_queries = bool(cur_session.golden_prompts)
        has_baseline_evidence = bool(cur_s.get("eval_results") or cur_s.get("coding_annotations"))
        has_annotations = bool(cur_s.get("coding_annotations"))
        has_evidence_handoff = bool(cur_s.get("codebook") or has_annotations)
        coach_workbench_steps = [
            (
                "1",
                "SME domain",
                "Tell Coach the domain, users, risks, permissions, constraints, and known edge cases.",
                "Domain expert profile",
                coach_status(has_domain, not has_domain),
            ),
            (
                "2",
                "Baseline requirements",
                "Upload the existing Kiro requirements.md or capture the baseline spec context in chat.",
                "Baseline Kiro requirements",
                coach_status(has_baseline_spec, has_domain and not has_baseline_spec),
            ),
            (
                "3",
                "Curated queries",
                "Approve happy path, edge, adversarial, ambiguous, multi-turn, recovery, persona, and red-flag queries.",
                "Coverage-backed query set",
                coach_status(has_queries, has_domain and has_baseline_spec and not has_queries),
            ),
            (
                "4",
                "Baseline test",
                "Run or paste responses from the Kiro baseline agent created from the initial requirements.md.",
                "Baseline response traces",
                coach_status(has_baseline_evidence, has_queries and not has_baseline_evidence),
            ),
            (
                "5",
                "SME annotations",
                "Label verdict, failure code, severity, confidence, missing rule, and memo.",
                "SME error analysis",
                coach_status(has_evidence_handoff, has_baseline_evidence and not has_evidence_handoff),
            ),
            (
                "6",
                "Outputs",
                "Export SME_error_analysis.md, then generate requirements.md and the LLM Judge.",
                "Specs + judge + measurement",
                coach_status(bool(cur_s.get("_generated_judge_prompt")), has_evidence_handoff),
            ),
        ]
        current_coach_step = next(
            (step for step in coach_workbench_steps if step[4] == "current"),
            next((step for step in coach_workbench_steps if step[4] != "done"), coach_workbench_steps[-1]),
        )
        return int(current_coach_step[0]), current_coach_step

    def render_coach_action(current_step_number: int) -> None:
        if current_step_number == 1:
            ui.html(
                '<div class="coach-action-note">'
                '<span class="material-icons">chat</span>'
                '<strong>Current action:</strong> answer the Coach in the chat below.'
                '</div>'
            )
        elif current_step_number == 2:
            render_baseline_requirements_upload()
        elif current_step_number == 3:
            ui.html(
                '<div class="coach-action-note">'
                '<span class="material-icons">edit_note</span>'
                '<strong>Current action:</strong> ask Coach to draft the first query batch.'
                '</div>'
            )
        elif current_step_number == 4:
            ui.html(
                '<div class="coach-action-note">'
                '<span class="material-icons">science</span>'
                '<strong>Current action:</strong> paste baseline agent responses in the chat.'
                '</div>'
            )
        elif current_step_number == 5:
            ui.button(
                "Open Annotations",
                icon="rate_review",
                on_click=lambda: ui.navigate.to("/coding"),
            ).props("color=primary size=sm no-caps")
        elif current_step_number == 6:
            ui.button(
                "Open Evidence",
                icon="fact_check",
                on_click=lambda: ui.navigate.to("/report"),
            ).props("color=primary size=sm no-caps")

    with ui.column().classes("w-full items-center").style("max-width: 1120px; margin: 0.75rem auto 0; padding: 0 1rem"):
        with ui.element("div").classes("coach-product-panel"):
            ui.html(
                '<div class="coach-product-kicker">'
                '<span class="material-icons" style="font-size:0.9rem">auto_awesome</span>'
                "Coach"
                "</div>"
            )
            ui.html('<div class="coach-product-title">Curate evidence for Kiro specs</div>')
            ui.html(
                '<div class="coach-product-copy">'
                "Coach controls the sequence. Finish the current prompt, then the next step appears. "
                "The path ends in "
                "SME_error_analysis.md, requirements.md, and the LLM Judge."
                "</div>"
            )
            coach_stage_container = ui.element("div")
            coach_actions_container = ui.element("div").classes("coach-quick-actions")

            def render_coach_stage() -> None:
                current_step_number, current_coach_step = current_coach_view()
                coach_stage_container.clear()
                with coach_stage_container:
                    ui.html(
                        '<div class="coach-led-stage coach-led-single">'
                        '<div class="coach-led-current">'
                        f'<div class="coach-led-label">Step {current_step_number} of 6</div>'
                        f'<div class="coach-led-title">{current_coach_step[1]}</div>'
                        f'<div class="coach-led-copy">{current_coach_step[2]}</div>'
                        '<div class="coach-led-outcome">'
                        '<span>Current handoff</span>'
                        f'<strong>{current_coach_step[3]}</strong>'
                        '</div>'
                        f'<div class="coach-led-prompt">{coach_prompts[current_step_number]}</div>'
                        '</div>'
                        '</div>'
                    )
                coach_actions_container.clear()
                with coach_actions_container:
                    render_coach_action(current_step_number)

            render_coach_stage()

        # Chat card
        with ui.card().classes("w-full chat-card").style("padding: 1.25rem; margin-top: 0.75rem"):
            with ui.row().classes("coach-chat-header"):
                with ui.column().style("gap:2px; min-width:240px"):
                    ui.html(
                        '<div class="coach-chat-title">'
                        '<span class="material-icons">forum</span>'
                        "Coach workbench"
                        "</div>"
                    )
                    ui.html(
                        '<div class="coach-chat-copy">'
                        "Use the chat to curate domain evidence before generating specs and the judge."
                        "</div>"
                    )
                ui.html(
                    '<div class="dynamic-kicker">'
                    '<span class="material-icons" style="font-size:0.9rem">verified</span>'
                    "SME curated"
                    "</div>"
                )
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
                    step = current_coach_view()[0]
                    if step == 1:
                        welcome = (
                            '<div class="msg-ai"><strong>I am your GEDD Coach for Kiro Domain Specs.</strong><br><br>'
                            'First we anchor the work in your domain before discussing specs or outputs.<br><br>'
                            '<strong>What domain are you the expert in, who uses this agent, and what can go wrong if it answers badly?</strong></div>'
                        )
                    elif step == 2:
                        welcome = (
                            '<div class="msg-ai"><strong>The domain is set.</strong><br><br>'
                            'Now attach the baseline Kiro requirements.md that created the current agent. '
                            'If the file is not available, describe the baseline spec or prompt in the chat.</div>'
                        )
                    elif step == 3:
                        welcome = (
                            '<div class="msg-ai"><strong>Baseline context is ready.</strong><br><br>'
                            'Next we curate SME-owned queries before trusting any baseline result. '
                            'Say <strong>draft the first query batch</strong> to begin with happy-path coverage.</div>'
                        )
                    elif step == 4:
                        welcome = (
                            '<div class="msg-ai"><strong>The query set is ready.</strong><br><br>'
                            'Run those queries against the Kiro baseline agent created from the initial requirements.md, '
                            'then paste the baseline responses here.</div>'
                        )
                    elif step == 5:
                        welcome = (
                            '<div class="msg-ai"><strong>Baseline responses are ready for SME annotation.</strong><br><br>'
                            'Open Annotations and label what only a domain expert would catch: verdict, failure code, '
                            'severity, confidence, missing rule, and memo.</div>'
                        )
                    else:
                        welcome = (
                            '<div class="msg-ai"><strong>Annotated evidence is ready.</strong><br><br>'
                            'Open Evidence to export SME_error_analysis.md, then use it for Kiro requirements.md, '
                            'the LLM Judge, and measurement.</div>'
                        )
                    ui.html(welcome)

            ui.separator().style("opacity: 0.1; margin: 12px 0")
            with ui.row().classes("w-full items-center gap-sm coach-input-row"):
                user_input = ui.input(placeholder="Start with your domain expertise...").classes("flex-grow input-box").props("borderless dense")
                send_btn = ui.button(icon="arrow_upward").classes("send-btn").props("round size=md")

    # Send message handler
    async def send_message():
        text = user_input.value.strip()
        if not text:
            return
        user_input.set_value("")
        with chat_container:
            ui.html(f'<div class="msg-user">{_html.escape(text)}</div>')
        send_btn.props("loading")

        try:
            _agc = _get_agentcore()
            if USE_AGENTCORE and _agc:
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
                    _agc.invoke_coach, text, session_id, state_dict, messages
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
            render_coach_stage()
            ui.run_javascript("document.querySelector('[style*=\"overflow-y: auto\"]').scrollTop=999999")

    send_btn.on_click(send_message)
    user_input.on("keydown.enter", send_message)


def run() -> None:
    ui.run(
        title="GEDD — SME Error Analysis → Annotations → Domain Driven Specs Development",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8080")),
        reload=os.environ.get("NICEGUI_RELOAD", "true").lower() == "true",
        storage_secret=os.environ.get("STORAGE_SECRET") or secrets.token_hex(32),
    )


if __name__ in {"__main__", "__mp_main__"}:
    run()
