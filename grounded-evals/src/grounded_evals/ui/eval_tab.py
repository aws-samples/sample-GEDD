"""Eval Tab — Run golden queries against multiple Bedrock models and annotate."""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import string
from datetime import datetime

import boto3
from nicegui import app, ui

from grounded_evals.feedback_loop import (
    QualityReport,
    build_coach_briefing,
    compute_eval_health,
    run_quality_analysis,
)
from grounded_evals.guide.session import Session
from grounded_evals.harness_client import HARNESS_REGIONS, HarnessClient
from grounded_evals.llm.client import get_default_client, get_model_id, traced_eval_call

AVAILABLE_MODELS = [
    {"id": "us.anthropic.claude-haiku-4-5-20251001-v1:0", "label": "Claude Haiku 4.5", "api": "anthropic"},
    {"id": "us.anthropic.claude-sonnet-4-5-20241022-v2:0", "label": "Claude Sonnet 4.5", "api": "anthropic"},
    {"id": "us.anthropic.claude-opus-4-5-20250115-v1:0", "label": "Claude Opus 4.5", "api": "anthropic"},
    {"id": "us.amazon.nova-pro-v1:0", "label": "Amazon Nova Pro", "api": "converse"},
    {"id": "us.amazon.nova-lite-v1:0", "label": "Amazon Nova Lite", "api": "converse"},
    {"id": "us.amazon.nova-micro-v1:0", "label": "Amazon Nova Micro", "api": "converse"},
    {"id": "us.meta.llama3-3-70b-instruct-v1:0", "label": "Llama 3.3 70B", "api": "converse"},
    {"id": "us.mistral.mistral-large-2411-v1:0", "label": "Mistral Large 24.11", "api": "converse"},
]

# ── Annotation Labels ─────────────────────────────────────────────────────────

DEFAULT_LABELS: list[dict] = [
    {"key": "correct", "label": "✓ Correct", "color": "green"},
    {"key": "partial", "label": "⚠ Partial", "color": "orange"},
    {"key": "incorrect", "label": "✗ Incorrect", "color": "red"},
]

LABEL_COLORS: dict[str, str] = {
    "green": "var(--green)",
    "orange": "var(--yellow)",
    "red": "var(--red)",
    "purple": "#a855f7",
    "blue": "var(--blue)",
    "teal": "#14b8a6",
    "pink": "#ec4899",
    "indigo": "#6366f1",
}

COLOR_OPTIONS = {
    "green": "Green",
    "orange": "Orange",
    "red": "Red",
    "purple": "Purple",
    "blue": "Blue",
    "teal": "Teal",
    "pink": "Pink",
    "indigo": "Indigo",
}


def _get_all_labels() -> list[dict]:
    """Return default labels + user-defined custom labels."""
    custom = app.storage.user.get("custom_annotation_labels", [])
    return DEFAULT_LABELS + custom


def _label_css_color(key: str) -> str:
    for lbl in _get_all_labels():
        if lbl["key"] == key:
            return LABEL_COLORS.get(lbl["color"], "var(--border-default)")
    return "var(--border-default)"


def _get_model_api(model_id: str) -> str:
    for m in AVAILABLE_MODELS:
        if m["id"] == model_id:
            return m.get("api", "converse")
    return "converse"


def _call_converse(system_prompt: str, query: str, model_id: str) -> str:
    """Call Bedrock Converse API for non-Anthropic models."""
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    client = boto3.client("bedrock-runtime", region_name=region)
    response = client.converse(
        modelId=model_id,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": query}]}],
        inferenceConfig={"maxTokens": 512},
    )
    return response["output"]["message"]["content"][0]["text"]


async def run_query_against_model(
    system_prompt: str, query: str, model_id: str
) -> str:
    try:
        api = _get_model_api(model_id)
        if api == "anthropic":
            client = get_default_client()
            response = await asyncio.to_thread(
                traced_eval_call, client, model_id, system_prompt, query
            )
            return response.content[0].text
        else:
            return await asyncio.to_thread(
                _call_converse, system_prompt, query, model_id
            )
    except Exception as e:
        return f"[Error: {e}]"


async def run_harness_query(
    harness_arn: str, model_id: str, system_prompt: str, query: str, region: str
) -> str:
    """Invoke one query through an AgentCore Harness instead of direct Bedrock."""
    client = HarnessClient(region)
    return await asyncio.to_thread(
        client.invoke_query, harness_arn, model_id, system_prompt, query
    )


def _get_eval_results() -> list[dict]:
    return app.storage.user.setdefault("eval_results", [])


def _get_selected_models() -> list[str]:
    return app.storage.user.setdefault("eval_selected_models", [])


def _get_judge_results() -> dict:
    return app.storage.user.setdefault("_eval_judge_results", {})


def _save_eval_snapshot(selected_models: list[str], eval_results: list[dict]) -> None:
    """Persist a summary of this run to eval_history (capped at 10 entries)."""
    history = app.storage.user.setdefault("eval_history", [])
    all_ann = [r.get("annotations", {}) for r in eval_results]
    total_ann = sum(len(a) for a in all_ann)
    correct = sum(1 for a in all_ann for v in a.values() if v == "correct")
    history.append({
        "timestamp": datetime.now().isoformat(),
        "models": selected_models,
        "query_count": len(eval_results),
        "total_annotated": total_ann,
        "correct": correct,
        "pass_rate": f"{correct / total_ann * 100:.0f}%" if total_ann else "—",
        "query_verdicts": [
            {"query": r.get("query", ""), "annotations": dict(r.get("annotations", {}))}
            for r in eval_results
        ],
    })
    app.storage.user["eval_history"] = history[-10:]


async def _score_with_judge(judge_prompt: str, query: str, response: str) -> bool | None:
    """Score one response with the stored judge prompt. Returns True=PASS, False=FAIL, None=error."""
    try:
        client = get_default_client()
        model_id = get_model_id()
        full_prompt = (
            f"{judge_prompt}\n\n<query>{query}</query>\n<response>{response}</response>"
        )
        resp = await asyncio.to_thread(
            client.messages.create,
            model=model_id,
            max_tokens=512,
            messages=[{"role": "user", "content": full_prompt}],
        )
        text = resp.content[0].text
        m = re.search(r'"pass"\s*:\s*(true|false)', text, re.IGNORECASE)
        if m:
            return m.group(1).lower() == "true"
        text_lower = text.lower()
        if "true" in text_lower or ("pass" in text_lower and "fail" not in text_lower):
            return True
        return False
    except Exception:
        return None


def render(session: Session, annotations_list: list[dict], prompt_variants: list[dict] | None = None) -> None:
    """Render the eval tab content."""

    if not session.golden_prompts:
        with ui.card().classes("w-full q-pa-lg").style(
            "text-align:center; background:var(--bg-surface-2); border-radius:12px; border:1px solid var(--border-subtle)"
        ):
            ui.icon("science", size="xl").style("color: var(--text-muted)")
            ui.label("No golden queries yet").style(
                "font-size:1.1rem; font-weight:600; color:var(--text-primary); margin-top:12px"
            )
            ui.label(
                "Go to the Coach tab and generate golden queries first."
            ).style("font-size:0.85rem; color:var(--text-tertiary); margin-top:4px")
            ui.button("Open Coach", icon="chat",
                      on_click=lambda: ui.navigate.to("/coach")).props(
                "color=primary"
            ).style("margin-top:12px")
        return

    if not session.agent_spec.system_prompt:
        with ui.card().classes("w-full q-pa-lg").style(
            "text-align:center; background:var(--bg-surface-2); border-radius:12px; border:1px solid var(--border-subtle)"
        ):
            ui.icon("warning", size="xl").style("color: var(--yellow)")
            ui.label("No system prompt defined").style(
                "font-size:1.1rem; font-weight:600; color:var(--text-primary); margin-top:12px"
            )
            ui.label(
                "Go to the Coach tab and create a system prompt first."
            ).style("font-size:0.85rem; color:var(--text-tertiary); margin-top:4px")
            ui.button("Open Coach", icon="chat",
                      on_click=lambda: ui.navigate.to("/coach")).props(
                "color=primary"
            ).style("margin-top:12px")
        return

    variants = prompt_variants or []

    # Shared state dict so keyboard handler can reach render_results' inner functions
    kb_state: dict = {"go": None, "annotate": None}

    # ── Annotation Labels Manager ─────────────────────────────────────────────
    labels_panel_container = ui.column().classes("w-full")

    def render_labels_panel():
        labels_panel_container.clear()
        with labels_panel_container:
            with ui.expansion("Annotation Labels", icon="label").classes("w-full").style(
                "background:var(--bg-surface-2); border-radius:12px; border:1px solid var(--border-subtle); margin-bottom:1rem"
            ):
                ui.label("Customize the labels annotators can apply to model responses.").style(
                    "font-size:0.78rem; color:var(--text-tertiary); margin-bottom:10px"
                )
                # Current labels display
                with ui.row().classes("gap-1 flex-wrap").style("margin-bottom:12px"):
                    for lbl in _get_all_labels():
                        css_color = LABEL_COLORS.get(lbl["color"], "var(--border-default)")
                        ui.html(
                            f'<span style="background:{css_color}22; color:{css_color}; '
                            f'border:1px solid {css_color}55; border-radius:4px; '
                            f'padding:3px 10px; font-size:0.75rem; font-weight:500">'
                            f'{lbl["label"]}</span>'
                        )

                ui.separator().style("opacity:0.15; margin:8px 0")
                ui.label("Add Custom Label").style(
                    "font-size:0.7rem; font-weight:600; color:var(--text-tertiary); "
                    "text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px"
                )
                with ui.row().classes("gap-2 items-end flex-wrap"):
                    label_name_input = ui.input(
                        "Label name", placeholder="e.g. Tone Issue"
                    ).props("dense outlined dark").style("width:180px")
                    color_select = ui.select(
                        options=COLOR_OPTIONS, value="purple", label="Color"
                    ).props("dense outlined dark").style("width:120px")

                    def add_custom_label():
                        name = label_name_input.value.strip()
                        if not name:
                            ui.notify("Enter a label name", type="warning")
                            return
                        key = name.lower().replace(" ", "_")
                        custom = app.storage.user.setdefault("custom_annotation_labels", [])
                        if any(l["key"] == key for l in custom) or any(l["key"] == key for l in DEFAULT_LABELS):
                            ui.notify("Label already exists", type="warning")
                            return
                        custom.append({"key": key, "label": name, "color": color_select.value})
                        ui.notify(f"Label '{name}' added — will appear on next eval run", type="positive")
                        label_name_input.value = ""
                        render_labels_panel()

                    ui.button("Add", icon="add", on_click=add_custom_label).props(
                        "size=sm color=primary dense"
                    )

                custom_labels = app.storage.user.get("custom_annotation_labels", [])
                if custom_labels:
                    ui.label("Your custom labels:").style(
                        "font-size:0.7rem; color:var(--text-tertiary); margin-top:10px; margin-bottom:4px"
                    )
                    with ui.row().classes("gap-1 flex-wrap"):
                        for lbl in custom_labels:
                            css_color = LABEL_COLORS.get(lbl["color"], "var(--border-default)")

                            def delete_label(key=lbl["key"]):
                                app.storage.user["custom_annotation_labels"] = [
                                    l for l in app.storage.user.get("custom_annotation_labels", [])
                                    if l["key"] != key
                                ]
                                ui.notify("Label removed", type="info")
                                render_labels_panel()

                            with ui.element("div").style(
                                f"display:inline-flex; align-items:center; gap:4px; "
                                f"background:{css_color}22; border:1px solid {css_color}55; "
                                f"border-radius:4px; padding:3px 8px; font-size:0.75rem; color:{css_color}"
                            ):
                                ui.html(f"<span>{lbl['label']}</span>")
                                ui.button(
                                    icon="close", on_click=delete_label
                                ).props("flat round size=xs").style(f"color:{css_color}; padding:0")

    render_labels_panel()

    # ── System Prompt Variant Selection ───────────────────────────────────────
    selected_variant_ref: dict = {"value": variants[0]["name"] if variants else ""}
    if variants and len(variants) > 1:
        with ui.card().classes("w-full q-pa-md").style(
            "background:var(--bg-surface-2); border-radius:12px; border:1px solid var(--border-subtle); margin-bottom:1rem"
        ):
            ui.label("System Prompt Variant").style(
                "font-size:0.85rem; font-weight:700; color:var(--text-primary); margin-bottom:8px"
            )
            ui.label("Select which prompt variant to test (A/B testing)").style(
                "font-size:0.75rem; color:var(--text-tertiary); margin-bottom:8px"
            )
            variant_options = {v["name"]: v["name"] + f" ({len(v['prompt'])} chars)" for v in variants}
            selected_variant = ui.select(
                options=variant_options,
                value=variants[0]["name"],
                label="Prompt Variant",
            ).style("width:200px")
            selected_variant.on_value_change(lambda e: selected_variant_ref.update({"value": e.value}))

    # ── Agent Target (Direct Bedrock vs AgentCore Harness) ───────────────────
    agent_target_ctr = ui.column().classes("w-full")

    _at_expanded: dict = {"open": False}

    def render_agent_target(keep_open: bool = False):
        agent_target_ctr.clear()
        mode = app.storage.user.get("harness_mode", "direct")
        if keep_open:
            _at_expanded["open"] = True
        with agent_target_ctr:
            exp = ui.expansion("Agent Target", icon="track_changes").classes("w-full").style(
                "background:var(--bg-surface-2); border-radius:12px; "
                "border:1px solid var(--border-subtle); margin-bottom:1rem"
            )
            if _at_expanded["open"]:
                exp.open()
            exp.on_value_change(lambda e: _at_expanded.update({"open": e.value}))
            with exp:
                ui.label(
                    "Route eval queries directly through Bedrock or through an Amazon Bedrock "
                    "AgentCore Harness (your deployed agent endpoint)."
                ).style("font-size:0.78rem; color:var(--text-tertiary); margin-bottom:12px")

                # Mode toggle pills
                with ui.row().classes("gap-2 items-center").style("margin-bottom:14px"):
                    def _mode_pill_style(active: bool) -> str:
                        if active:
                            return (
                                "padding:5px 16px; border-radius:20px; cursor:pointer; "
                                "font-size:0.78rem; font-weight:600; background:var(--accent); "
                                "color:#fff; border:1.5px solid var(--accent)"
                            )
                        return (
                            "padding:5px 16px; border-radius:20px; cursor:pointer; "
                            "font-size:0.78rem; font-weight:500; background:transparent; "
                            "color:var(--text-secondary); border:1.5px solid var(--border-subtle)"
                        )

                    direct_pill = ui.html(
                        f'<div style="{_mode_pill_style(mode == "direct")}">Direct Bedrock</div>'
                    )
                    harness_pill = ui.html(
                        f'<div style="{_mode_pill_style(mode == "harness")}">AgentCore Harness</div>'
                    )

                    def set_direct():
                        app.storage.user["harness_mode"] = "direct"
                        render_agent_target(keep_open=True)

                    def set_harness():
                        app.storage.user["harness_mode"] = "harness"
                        render_agent_target(keep_open=True)

                    direct_pill.on("click", set_direct)
                    harness_pill.on("click", set_harness)

                if mode == "direct":
                    ui.html(
                        '<div style="display:flex;align-items:center;gap:6px;'
                        'font-size:0.78rem;color:var(--green-bright)">'
                        '&#9679; Queries will be sent directly to the selected Bedrock models.'
                        '</div>'
                    )
                else:
                    # Harness configuration
                    harness_status = app.storage.user.get("harness_status", "")
                    harness_arn_val = app.storage.user.get("harness_arn", "")
                    harness_name_val = app.storage.user.get("harness_name", "")
                    harness_region_val = app.storage.user.get("harness_region", "us-east-1")

                    if harness_arn_val and harness_status == "READY":
                        # Active harness summary
                        ui.html(
                            f'<div style="display:flex;align-items:center;gap:8px;'
                            f'background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.3);'
                            f'border-radius:8px;padding:10px 14px;font-size:0.8rem;margin-bottom:12px">'
                            f'<span style="color:var(--green-bright);font-size:1rem">&#9679;</span>'
                            f'<div><div style="color:var(--green-bright);font-weight:600">'
                            f'Harness READY — {harness_name_val}</div>'
                            f'<div style="color:var(--text-tertiary);font-size:0.72rem;margin-top:2px">'
                            f'{harness_arn_val[:60]}{"…" if len(harness_arn_val) > 60 else ""}'
                            f'</div></div></div>'
                        )
                        with ui.row().classes("gap-2 items-center").style("margin-bottom:10px"):
                            def clear_harness():
                                app.storage.user.pop("harness_arn", None)
                                app.storage.user.pop("harness_status", None)
                                app.storage.user.pop("harness_name", None)
                                render_agent_target(keep_open=True)
                            ui.button("Remove", icon="delete_outline", on_click=clear_harness).props(
                                "flat size=sm dark"
                            ).style("color:var(--text-muted)")

                    else:
                        # Region selector
                        ui.label("Region").style(
                            "font-size:0.7rem; font-weight:600; color:var(--text-tertiary); "
                            "text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px"
                        )
                        region_opts = {r: r for r in sorted(HARNESS_REGIONS)}
                        region_sel = ui.select(
                            options=region_opts,
                            value=harness_region_val if harness_region_val in HARNESS_REGIONS else "us-east-1",
                            label="Harness region",
                        ).props("dense outlined dark").style("width:200px; margin-bottom:12px")
                        region_sel.on_value_change(
                            lambda e: app.storage.user.update({"harness_region": e.value})
                        )

                        ui.separator().style("opacity:0.15; margin:10px 0")

                        # Option A — use existing ARN
                        with ui.element("div").style("margin-bottom:12px"):
                            ui.label("Use an existing Harness ARN").style(
                                "font-size:0.78rem; font-weight:600; color:var(--text-primary); margin-bottom:6px"
                            )
                            arn_status_ctr = ui.column().classes("w-full")
                            with ui.row().classes("gap-2 items-center").style("flex-wrap:wrap"):
                                arn_input = ui.input(
                                    "Harness ARN",
                                    value=harness_arn_val,
                                    placeholder="arn:aws:bedrock-agentcore:us-east-1:123456789012:harness/...",
                                ).props("dense outlined dark").style("flex:1; min-width:300px")

                                async def verify_harness_arn():
                                    arn = arn_input.value.strip()
                                    if not arn.startswith("arn:"):
                                        ui.notify("Enter a valid ARN", type="warning")
                                        return
                                    verify_btn.props("loading")
                                    region = app.storage.user.get("harness_region", "us-east-1")
                                    hc = HarnessClient(region)
                                    status = await asyncio.to_thread(hc.get_harness_status, arn)
                                    verify_btn.props(remove="loading")
                                    if status == "READY":
                                        app.storage.user["harness_arn"] = arn
                                        app.storage.user["harness_status"] = "READY"
                                        app.storage.user["harness_name"] = arn.split("/")[-1]
                                        ui.notify("Harness verified and ready", type="positive")
                                        render_agent_target()
                                    elif status == "CREATING":
                                        ui.notify("Harness is still being created — wait a moment", type="warning")
                                    elif status == "NOT_FOUND":
                                        ui.notify("Harness not found — check ARN and region", type="negative")
                                    else:
                                        ui.notify(f"Harness status: {status}", type="warning")

                                verify_btn = ui.button("Verify", icon="check_circle", on_click=verify_harness_arn).props(
                                    "size=sm color=primary"
                                )

                        ui.separator().style("opacity:0.15; margin:10px 0")

                        # Option B — create a new Harness
                        with ui.element("div"):
                            ui.label("Or create a new Harness").style(
                                "font-size:0.78rem; font-weight:600; color:var(--text-primary); margin-bottom:6px"
                            )

                            _hc_tmp = HarnessClient()
                            default_role = _hc_tmp.discover_execution_role_arn()
                            role_input = ui.input(
                                "Execution role ARN",
                                value=default_role,
                                placeholder="arn:aws:iam::123456789012:role/GEDDHarnessExecutionRole",
                            ).props("dense outlined dark").style("width:100%; margin-bottom:8px")
                            create_status_ctr = ui.column().classes("w-full")

                            async def create_harness():
                                role_arn = role_input.value.strip()
                                if not role_arn.startswith("arn:aws:iam::"):
                                    ui.notify("Enter a valid IAM role ARN", type="warning")
                                    return
                                agent_name = session.agent_spec.name if session.agent_spec else "my-agent"
                                system_prompt_text = session.agent_spec.system_prompt or "You are a helpful assistant."
                                region = app.storage.user.get("harness_region", "us-east-1")
                                hc = HarnessClient(region)
                                create_btn.props("loading")
                                create_status_ctr.clear()
                                with create_status_ctr:
                                    ui.html(
                                        '<div style="font-size:0.78rem;color:var(--text-tertiary)">'
                                        '&#9675; Creating harness…</div>'
                                    )
                                try:
                                    result = await asyncio.to_thread(
                                        hc.create_harness, agent_name, system_prompt_text, role_arn
                                    )
                                except RuntimeError as exc:
                                    create_btn.props(remove="loading")
                                    create_status_ctr.clear()
                                    with create_status_ctr:
                                        ui.html(
                                            f'<div style="font-size:0.78rem;color:var(--red)">'
                                            f'&#10060; {exc}</div>'
                                        )
                                    return

                                created_arn = result["arn"]
                                app.storage.user["harness_arn"] = created_arn
                                app.storage.user["harness_name"] = result["name"]
                                app.storage.user["harness_status"] = "CREATING"
                                create_btn.props(remove="loading")

                                async def poll_harness_ready():
                                    hc2 = HarnessClient(region)
                                    final = await asyncio.to_thread(hc2.wait_for_ready, created_arn, 120)
                                    app.storage.user["harness_status"] = final
                                    if final == "READY":
                                        ui.notify("Harness is ready!", type="positive")
                                        render_agent_target(keep_open=True)
                                    else:
                                        ui.notify(f"Harness ended with status: {final}", type="negative")
                                        render_agent_target(keep_open=True)

                                asyncio.create_task(poll_harness_ready())
                                create_status_ctr.clear()
                                with create_status_ctr:
                                    ui.html(
                                        '<div style="font-size:0.78rem;color:var(--text-tertiary)">'
                                        '&#9675; Harness provisioning… this takes ~60 s. '
                                        'Eval will be available once status shows READY.</div>'
                                    )

                            create_btn = ui.button(
                                "Create Harness", icon="add_circle", on_click=create_harness
                            ).props("size=sm color=primary").style("margin-bottom:8px")

                        # Setup guide link
                        ui.separator().style("opacity:0.15; margin:10px 0")

                        async def show_setup_guide():
                            with ui.dialog() as dlg:
                                dlg.open()
                                with ui.card().style(
                                    "min-width:540px; max-width:620px; padding:1.5rem; "
                                    "background:var(--bg-surface-2)"
                                ):
                                    ui.label("AgentCore Harness Setup").style(
                                        "font-size:1rem; font-weight:700; color:var(--text-primary); margin-bottom:4px"
                                    )
                                    ui.label(
                                        "Create the IAM execution role your Harness needs:"
                                    ).style("font-size:0.8rem; color:var(--text-tertiary); margin-bottom:12px")
                                    _setup_cmd = (
                                        "aws iam create-role \\\n"
                                        "  --role-name GEDDHarnessExecutionRole \\\n"
                                        "  --assume-role-policy-document "
                                        '\'{"Version":"2012-10-17","Statement":[{"Effect":"Allow",'
                                        '"Principal":{"Service":"bedrock-agentcore.amazonaws.com"},'
                                        '"Action":"sts:AssumeRole"}]}\'\n\n'
                                        "aws iam attach-role-policy \\\n"
                                        "  --role-name GEDDHarnessExecutionRole \\\n"
                                        "  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
                                    )
                                    ui.code(_setup_cmd, language="bash").style("font-size:0.72rem")
                                    ui.label(
                                        "Harness is available in: us-east-1 · us-west-2 · eu-central-1 · ap-southeast-2"
                                    ).style("font-size:0.72rem; color:var(--text-muted); margin-top:10px")
                                    ui.button("Close", on_click=dlg.close).props(
                                        "flat size=sm dark"
                                    ).style("margin-top:12px; color:var(--text-muted)")

                        ui.button(
                            "Setup Guide", icon="help_outline", on_click=show_setup_guide
                        ).props("flat size=sm no-caps dark").style("color:var(--text-muted)")

    render_agent_target()

    # ── Model Selection + Run ─────────────────────────────────────────────────
    results_container = ui.column().classes("w-full")

    with ui.card().classes("w-full q-pa-md").style(
        "background:var(--bg-surface-2); border-radius:12px; border:1px solid var(--border-subtle); margin-bottom:1rem"
    ):
        with ui.row().classes("items-center justify-between w-full").style("margin-bottom:4px"):
            ui.label("Select Models to Compare").style(
                "font-size:0.85rem; font-weight:700; color:var(--text-primary)"
            )
            ui.label(f"{len(session.golden_prompts)} queries · pick up to 3").style(
                "font-size:0.72rem; color:var(--text-muted)"
            )

        # Group models by provider for visual clarity
        MODEL_GROUPS = [
            ("Claude", [m for m in AVAILABLE_MODELS if "claude" in m["id"]]),
            ("Amazon Nova", [m for m in AVAILABLE_MODELS if "nova" in m["id"]]),
            ("Other", [m for m in AVAILABLE_MODELS if "claude" not in m["id"] and "nova" not in m["id"]]),
        ]

        existing_selected = _get_selected_models()
        selected_state: dict[str, bool] = {m["id"]: m["id"] in existing_selected for m in AVAILABLE_MODELS}
        pill_buttons: dict[str, object] = {}

        def _pill_style(selected: bool) -> str:
            if selected:
                return (
                    "padding:6px 14px; border-radius:20px; cursor:pointer; font-size:0.78rem; font-weight:600; "
                    "background:var(--accent); color:#fff; border:1.5px solid var(--accent); transition:all 0.15s"
                )
            return (
                "padding:6px 14px; border-radius:20px; cursor:pointer; font-size:0.78rem; font-weight:500; "
                "background:transparent; color:var(--text-secondary); border:1.5px solid var(--border-subtle); transition:all 0.15s"
            )

        for group_name, group_models in MODEL_GROUPS:
            if not group_models:
                continue
            ui.label(group_name).style(
                "font-size:0.65rem; font-weight:700; color:var(--text-muted); letter-spacing:0.08em; "
                "text-transform:uppercase; margin-top:12px; margin-bottom:6px"
            )
            with ui.row().classes("gap-2 flex-wrap"):
                for model in group_models:
                    mid = model["id"]
                    btn = ui.html(
                        f'<div style="{_pill_style(selected_state[mid])}">{model["label"]}</div>'
                    )

                    def make_toggle(model_id=mid, pill=btn):
                        def toggle():
                            selected_state[model_id] = not selected_state[model_id]
                            pill.set_content(
                                f'<div style="{_pill_style(selected_state[model_id])}">'
                                f'{next(m["label"] for m in AVAILABLE_MODELS if m["id"] == model_id)}'
                                f'</div>'
                            )
                        return toggle

                    btn.on("click", make_toggle())
                    pill_buttons[mid] = btn

        # Expose the same interface run_eval expects
        checkboxes = []
        for model in AVAILABLE_MODELS:
            class _FakeCb:
                def __init__(self, mid): self._mid = mid
                @property
                def value(self): return selected_state[self._mid]
            checkboxes.append((_FakeCb(model["id"]), model["id"]))

        ui.separator().style("opacity:0.2; margin:14px 0 10px")

        progress_bar = ui.linear_progress(value=0, show_value=False).props("color=primary size=4px").style("margin-bottom:6px; opacity:0")
        progress_label = ui.label("").style("font-size:0.8rem; color:var(--text-tertiary)")

        async def run_eval():
            sel = [mid for cb, mid in checkboxes if cb.value]
            if not sel:
                ui.notify("Select at least one model", type="warning")
                return
            if len(sel) > 3:
                ui.notify("Select up to 3 models", type="warning")
                return

            active_prompt = session.agent_spec.system_prompt
            if variants and len(variants) > 1:
                variant_name = selected_variant_ref["value"]
                for v in variants:
                    if v["name"] == variant_name:
                        active_prompt = v["prompt"]
                        break

            selected_models_store = _get_selected_models()
            selected_models_store.clear()
            selected_models_store.extend(sel)

            eval_results_store = _get_eval_results()
            eval_results_store.clear()

            run_btn.props("loading")
            progress_bar.style("opacity:1")
            progress_bar.set_value(0)
            progress_label.set_text("Running queries...")

            harness_mode = app.storage.user.get("harness_mode", "direct")
            harness_arn = app.storage.user.get("harness_arn", "")
            harness_region = app.storage.user.get("harness_region", "us-east-1")

            total = len(session.golden_prompts)
            for idx, gp in enumerate(session.golden_prompts):
                progress_bar.set_value(idx / total)
                progress_label.set_text(f"Running query {idx + 1}/{total}...")
                responses = {}
                for model_id in sel:
                    if harness_mode == "harness" and harness_arn:
                        resp = await run_harness_query(
                            harness_arn, model_id, active_prompt, gp.prompt_text, harness_region
                        )
                    else:
                        resp = await run_query_against_model(active_prompt, gp.prompt_text, model_id)
                    responses[model_id] = resp

                eval_results_store.append({
                    "query_idx": idx,
                    "query": gp.prompt_text,
                    "category": gp.rationale,
                    "responses": responses,
                    "annotations": {},
                    "notes": "",
                })

            progress_bar.set_value(1.0)
            progress_label.set_text(
                f"Done! {total} queries × {len(sel)} models = {total * len(sel)} responses"
            )
            run_btn.props(remove="loading")
            render_results(results_container, sel, annotations_list, kb_state)
            _save_eval_snapshot(sel, eval_results_store)

        run_btn = ui.button(
            "Run Evaluation", icon="play_arrow", on_click=run_eval
        ).props("color=primary")

    # Re-render existing results when navigating back
    existing_results = _get_eval_results()
    existing_sel = _get_selected_models()
    if existing_results and existing_sel:
        render_results(results_container, existing_sel, annotations_list, kb_state)

    # ── Run History ───────────────────────────────────────────────────────────
    with ui.expansion("Run History", icon="history").classes("w-full").style(
        "background:var(--bg-surface-2); border-radius:12px; border:1px solid var(--border-subtle); margin-top:1rem"
    ):
        history = app.storage.user.get("eval_history", [])
        if not history:
            ui.label("No previous runs yet. Complete an evaluation to start tracking history.").style(
                "font-size:0.78rem; color:var(--text-muted)"
            )
        else:
            ui.label(f"Last {len(history)} evaluation run(s):").style(
                "font-size:0.78rem; color:var(--text-tertiary); margin-bottom:8px"
            )
            for i, run in enumerate(reversed(history)):
                ts = run.get("timestamp", "")[:16].replace("T", " ")
                pass_rate = run.get("pass_rate", "—")
                pr_color = (
                    "var(--green-bright)"
                    if "%" in pass_rate and int(pass_rate[:-1]) >= 70
                    else ("var(--yellow)" if "%" in pass_rate and int(pass_rate[:-1]) >= 40 else "var(--red)")
                    if "%" in pass_rate else "var(--text-muted)"
                )
                model_names = [
                    next((m["label"] for m in AVAILABLE_MODELS if m["id"] == mid), mid.split(".")[-1])
                    for mid in run.get("models", [])
                ]
                with ui.element("div").style(
                    "background:var(--bg-surface-1); border-radius:8px; padding:10px 14px; "
                    "margin-bottom:6px; border:1px solid var(--border-subtle)"
                ):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label(f"Run #{len(history) - i}  ·  {ts}").style(
                            "font-size:0.78rem; font-weight:600; color:var(--text-primary)"
                        )
                        ui.label(f"Pass rate: {pass_rate}").style(
                            f"font-size:0.78rem; font-weight:600; color:{pr_color}"
                        )
                    n_models = len(run.get("models", []))
                    q_count = run.get("query_count", 0)
                    ui.label(
                        f"{q_count} queries · {', '.join(model_names)} · "
                        f"{run.get('total_annotated', 0)}/{q_count * n_models} annotated"
                    ).style("font-size:0.72rem; color:var(--text-tertiary); margin-top:2px")

    # ── A/B Compare Runs ─────────────────────────────────────────────────────
    _ab_history = app.storage.user.get("eval_history", [])
    if len(_ab_history) >= 2:
        with ui.expansion("Compare Runs", icon="compare_arrows").classes("w-full").style(
            "background:var(--bg-surface-2); border-radius:12px; border:1px solid var(--border-subtle); margin-top:1rem"
        ):
            ui.label(
                "Select two runs to see which queries improved or regressed between them."
            ).style("font-size:0.78rem; color:var(--text-tertiary); margin-bottom:10px")

            _run_labels = {
                i: f"Run #{i + 1}  ·  {run['timestamp'][:16].replace('T', ' ')}  ·  {run.get('pass_rate', '—')}"
                for i, run in enumerate(_ab_history)
            }
            compare_container = ui.column().classes("w-full")

            with ui.row().classes("gap-2 items-end flex-wrap").style("margin-bottom:8px"):
                sel_a = ui.select(
                    options=_run_labels, value=len(_ab_history) - 2, label="Run A (baseline)"
                ).props("dense outlined dark").style("width:280px")
                sel_b = ui.select(
                    options=_run_labels, value=len(_ab_history) - 1, label="Run B (compare)"
                ).props("dense outlined dark").style("width:280px")

                def show_comparison():
                    run_a = _ab_history[sel_a.value]
                    run_b = _ab_history[sel_b.value]
                    verdicts_a = {v["query"]: v["annotations"] for v in run_a.get("query_verdicts", [])}
                    verdicts_b = {v["query"]: v["annotations"] for v in run_b.get("query_verdicts", [])}

                    all_queries = list(dict.fromkeys(list(verdicts_a) + list(verdicts_b)))
                    improved = regressed = unchanged = changed = 0
                    rows: list[dict] = []
                    for q in all_queries:
                        ann_a = verdicts_a.get(q, {})
                        ann_b = verdicts_b.get(q, {})
                        all_models = list(dict.fromkeys(list(ann_a) + list(ann_b)))
                        for m in all_models:
                            v_a = ann_a.get(m, "—")
                            v_b = ann_b.get(m, "—")
                            if v_a == "incorrect" and v_b == "correct":
                                delta, delta_color = "↑ improved", "var(--green-bright)"
                                improved += 1
                            elif v_a == "correct" and v_b == "incorrect":
                                delta, delta_color = "↓ regressed", "var(--red)"
                                regressed += 1
                            elif v_a == v_b:
                                delta, delta_color = "= same", "var(--text-muted)"
                                unchanged += 1
                            else:
                                delta = f"{v_a} → {v_b}"
                                delta_color = "var(--yellow)"
                                changed += 1
                            rows.append({
                                "query": q[:65],
                                "model": m.split(".")[-1][:18],
                                "v_a": v_a, "v_b": v_b,
                                "delta": delta, "color": delta_color,
                            })

                    compare_container.clear()
                    with compare_container:
                        if not rows:
                            ui.label(
                                "No per-query verdicts in these runs — runs must be from v9+ to compare."
                            ).style("font-size:0.78rem; color:var(--text-muted)")
                            return
                        with ui.row().classes("gap-4 items-center").style("margin-bottom:10px"):
                            for label, val, col in [
                                (f"↑ Improved", improved, "var(--green-bright)"),
                                (f"↓ Regressed", regressed, "var(--red)"),
                                (f"~ Changed", changed, "var(--yellow)"),
                                (f"= Same", unchanged, "var(--text-muted)"),
                            ]:
                                ui.html(
                                    f'<span style="font-size:1rem; font-weight:700; color:{col}">{val}</span>'
                                    f'<span style="font-size:0.7rem; color:var(--text-tertiary); margin-left:3px">{label}</span>'
                                )
                        for row in rows:
                            a_col = _label_css_color(row["v_a"]) if row["v_a"] != "—" else "var(--text-muted)"
                            b_col = _label_css_color(row["v_b"]) if row["v_b"] != "—" else "var(--text-muted)"
                            with ui.element("div").style(
                                "display:flex; align-items:baseline; gap:10px; padding:5px 0; "
                                "border-bottom:1px solid var(--border-subtle)"
                            ):
                                ui.label(row["query"]).style(
                                    "font-size:0.74rem; color:var(--text-secondary); flex:1; "
                                    "overflow:hidden; text-overflow:ellipsis; white-space:nowrap"
                                )
                                ui.label(row["model"]).style(
                                    "font-size:0.64rem; color:var(--text-tertiary); white-space:nowrap"
                                )
                                ui.html(f'<span style="font-size:0.68rem; color:{a_col}; white-space:nowrap">A: {row["v_a"]}</span>')
                                ui.html(f'<span style="font-size:0.68rem; color:{b_col}; white-space:nowrap">B: {row["v_b"]}</span>')
                                ui.html(
                                    f'<span style="font-size:0.68rem; color:{row["color"]}; '
                                    f'font-weight:600; white-space:nowrap">{row["delta"]}</span>'
                                )

                ui.button("Compare", icon="compare_arrows", on_click=show_comparison).props("size=sm color=primary")

    # ── Quality Loop (Uber-inspired feedback loop) ────────────────────────────
    quality_ctr = ui.column().classes("w-full")

    def render_quality_loop(report: QualityReport | None = None):
        quality_ctr.clear()
        with quality_ctr:
            with ui.expansion("Quality Loop", icon="loop").classes("w-full").style(
                "background:var(--bg-surface-2); border-radius:12px; "
                "border:1px solid var(--border-subtle); margin-top:1rem"
            ):
                ui.label(
                    "Measure eval quality and close the feedback loop — "
                    "IAA, failure breakdown, judge-human disagreements, and "
                    "LLM-generated improvement suggestions."
                ).style("font-size:0.78rem; color:var(--text-tertiary); margin-bottom:10px")

                # ── Health Score Widget ───────────────────────────────────────
                health = compute_eval_health(dict(app.storage.user))

                def _score_color(score: int, max_s: int = 25) -> str:
                    pct = score / max_s if max_s else 0
                    if pct >= 0.8:
                        return "var(--green-bright)"
                    if pct >= 0.5:
                        return "var(--yellow)"
                    return "var(--red)"

                total_color = _score_color(health.total, 100)
                with ui.element("div").style(
                    "background:var(--bg-surface-1); border-radius:10px; "
                    "padding:14px 18px; margin-bottom:14px; "
                    "border:1px solid var(--border-subtle)"
                ):
                    with ui.row().classes("items-center justify-between w-full").style("margin-bottom:10px"):
                        ui.label("Eval Health Score").style(
                            "font-size:0.7rem; font-weight:700; color:var(--text-tertiary); "
                            "text-transform:uppercase; letter-spacing:0.05em"
                        )
                        ui.html(
                            f'<span style="font-size:1.4rem; font-weight:800; color:{total_color}">'
                            f'{health.total}</span>'
                            f'<span style="font-size:0.8rem; color:var(--text-muted)">/100</span>'
                        )

                    _indicators = [
                        ("Rubric Freshness", health.rubric_freshness,
                         f"{health.rubric_age_days}d old" if health.rubric_age_days is not None
                         else ("Generated" if health.rubric_freshness > 0 else "No judge prompt")),
                        ("Eval Staleness", health.eval_staleness,
                         f"{health.eval_age_days}d ago" if health.eval_age_days is not None else "Never run"),
                        ("Annotation Coverage", health.annotation_coverage,
                         f"{health.annotation_pct:.0%} annotated"),
                        ("Judge-Human κ", health.judge_human_agreement,
                         f"κ={health.kappa:.2f}" if health.kappa is not None else "Run Judge first"),
                    ]
                    for label, score, detail in _indicators:
                        bar_pct = score / 25 * 100
                        bar_color = _score_color(score, 25)
                        detail_color = "var(--text-muted)" if score >= 10 else "#eb5757"
                        with ui.element("div").style("margin-bottom:8px"):
                            with ui.row().classes("items-center justify-between w-full").style("margin-bottom:3px"):
                                ui.label(label).style("font-size:0.72rem; color:var(--text-secondary); font-weight:600")
                                ui.label(detail).style(f"font-size:0.68rem; color:{detail_color}")
                            if score == 0:
                                ui.html(
                                    '<div style="height:5px; border-radius:3px; background:var(--border-subtle); '
                                    'outline:1px dashed #3a3d45; outline-offset:-1px"></div>'
                                )
                            else:
                                ui.html(
                                    f'<div style="height:5px; border-radius:3px; background:var(--border-subtle)">'
                                    f'<div style="height:100%; width:{bar_pct:.0f}%; border-radius:3px; '
                                    f'background:{bar_color}; min-width:5px; transition:width 0.4s ease"></div></div>'
                                )

                    if health.gaps:
                        ui.separator().style("opacity:0.15; margin:10px 0")
                        for gap in health.gaps[:3]:
                            ui.html(
                                f'<div style="font-size:0.7rem; color:var(--yellow); '
                                f'margin-bottom:3px">⚠ {gap}</div>'
                            )

                ui.separator().style("opacity:0.15; margin:10px 0")

                # ── Run Quality Analysis button ───────────────────────────────
                analysis_result_ctr = ui.column().classes("w-full")

                async def run_analysis():
                    eval_res = _get_eval_results()
                    if not eval_res:
                        ui.notify("Run an evaluation first", type="warning")
                        return
                    run_btn.props("loading")
                    analysis_result_ctr.clear()
                    with analysis_result_ctr:
                        ui.label("Analyzing…").style("font-size:0.78rem; color:var(--text-muted)")
                    try:
                        client = get_default_client()
                        model_id = get_model_id()
                        sp = session.agent_spec.system_prompt or ""
                        name = session.agent_spec.name or "agent"
                        report = await run_quality_analysis(
                            state=dict(app.storage.user),
                            agent_name=name,
                            system_prompt=sp,
                            client=client,
                            model_id=model_id,
                        )
                        app.storage.user["_quality_report"] = {
                            "generated_at": report.generated_at,
                            "health_total": report.health.total,
                            "n_disagreements": report.n_disagreements,
                        }
                        render_quality_loop(report)
                    except Exception as exc:
                        analysis_result_ctr.clear()
                        with analysis_result_ctr:
                            ui.label(f"Analysis failed: {exc}").style("font-size:0.78rem; color:var(--red)")
                    finally:
                        run_btn.props(remove="loading")

                with ui.row().classes("gap-2 items-center").style("margin-bottom:12px"):
                    run_btn = ui.button(
                        "Run Quality Analysis", icon="analytics", on_click=run_analysis
                    ).props("color=primary size=sm")
                    if app.storage.user.get("_quality_report"):
                        rpt = app.storage.user["_quality_report"]
                        ui.label(
                            f"Last run: {rpt['generated_at'][:16]} · "
                            f"Score {rpt['health_total']}/100 · "
                            f"{rpt['n_disagreements']} disagreements"
                        ).style("font-size:0.68rem; color:var(--text-muted)")

                # ── Report body (shown after analysis) ────────────────────────
                if report is not None:
                    # Category failure breakdown (Uber: slice-first)
                    if report.category_insights:
                        ui.label("Failure Breakdown by Category").style(
                            "font-size:0.7rem; font-weight:700; color:var(--text-tertiary); "
                            "text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px"
                        )
                        for ci in report.category_insights[:6]:
                            bar_w = int(ci.pass_rate * 100)
                            bar_col = (
                                "var(--green-bright)" if ci.pass_rate >= 0.7
                                else ("var(--yellow)" if ci.pass_rate >= 0.4 else "var(--red)")
                            )
                            with ui.element("div").style(
                                "background:var(--bg-surface-1); border-radius:8px; "
                                "padding:8px 12px; margin-bottom:5px; "
                                "border:1px solid var(--border-subtle)"
                            ):
                                with ui.row().classes("items-center justify-between w-full").style("margin-bottom:4px"):
                                    ui.label(ci.category[:55]).style(
                                        "font-size:0.75rem; color:var(--text-primary); font-weight:500"
                                    )
                                    ui.html(
                                        f'<span style="font-size:0.72rem; font-weight:700; color:{bar_col}">'
                                        f'{ci.pass_rate:.0%}</span>'
                                        f'<span style="font-size:0.65rem; color:var(--text-muted); margin-left:4px">'
                                        f'{ci.passed}/{ci.total}</span>'
                                    )
                                ui.html(
                                    f'<div style="height:4px; border-radius:2px; background:var(--border-subtle)">'
                                    f'<div style="height:100%; width:{bar_w}%; border-radius:2px; '
                                    f'background:{bar_col}"></div></div>'
                                )

                        ui.separator().style("opacity:0.15; margin:12px 0")

                    # Disagreement queue (Uber: escalate low-confidence to human review)
                    if report.disagreements:
                        ui.label(
                            f"Judge-Human Disagreements — {report.n_disagreements} cases requiring review"
                        ).style(
                            "font-size:0.7rem; font-weight:700; color:var(--text-tertiary); "
                            "text-transform:uppercase; letter-spacing:0.04em; margin-bottom:6px"
                        )
                        for d in report.disagreements[:5]:
                            dir_color = "var(--red)" if d.direction == "false_positive" else "var(--yellow)"
                            dir_label = "Judge=PASS, Human=FAIL" if d.direction == "false_positive" else "Judge=FAIL, Human=PASS"
                            with ui.element("div").style(
                                "background:var(--bg-surface-1); border-radius:8px; "
                                "padding:8px 12px; margin-bottom:5px; "
                                f"border:1px solid var(--border-subtle); "
                                f"border-left:3px solid {dir_color}"
                            ):
                                ui.html(
                                    f'<div style="font-size:0.72rem; color:{dir_color}; '
                                    f'font-weight:600; margin-bottom:3px">{dir_label}</div>'
                                    f'<div style="font-size:0.74rem; color:var(--text-secondary)">'
                                    f'{d.query[:100]}{"…" if len(d.query) > 100 else ""}</div>'
                                )

                        ui.separator().style("opacity:0.15; margin:12px 0")

                    # Improvement suggestions (LLM-generated)
                    if report.suggestions:
                        ui.label("Improvement Suggestions").style(
                            "font-size:0.7rem; font-weight:700; color:var(--text-tertiary); "
                            "text-transform:uppercase; letter-spacing:0.04em; margin-bottom:8px"
                        )
                        _type_icons = {
                            "golden_query": "quiz",
                            "rubric_refinement": "tune",
                            "system_prompt": "edit_note",
                            "coverage_gap": "search_off",
                        }
                        _priority_colors = {
                            "high": "var(--red)",
                            "medium": "var(--yellow)",
                            "low": "var(--text-muted)",
                        }
                        for sug in report.suggestions:
                            icon = _type_icons.get(sug.type, "lightbulb")
                            p_color = _priority_colors.get(sug.priority, "var(--text-muted)")
                            with ui.element("div").style(
                                "background:var(--bg-surface-1); border-radius:10px; "
                                "padding:12px 14px; margin-bottom:8px; "
                                "border:1px solid var(--border-subtle)"
                            ):
                                with ui.row().classes("items-start gap-3"):
                                    ui.icon(icon, size="sm").style("color:var(--accent); margin-top:2px; flex-shrink:0")
                                    with ui.column().classes("gap-1").style("flex:1; min-width:0"):
                                        with ui.row().classes("items-center gap-2"):
                                            ui.label(sug.title).style(
                                                "font-size:0.8rem; font-weight:600; color:var(--text-primary)"
                                            )
                                            ui.html(
                                                f'<span style="font-size:0.62rem; font-weight:700; '
                                                f'color:{p_color}; text-transform:uppercase; '
                                                f'letter-spacing:0.06em; padding:1px 5px; '
                                                f'border:1px solid {p_color}; border-radius:3px">'
                                                f'{sug.priority}</span>'
                                            )
                                        ui.label(sug.description).style(
                                            "font-size:0.74rem; color:var(--text-secondary)"
                                        )
                                        if sug.action_text:
                                            ui.html(
                                                f'<div style="font-size:0.72rem; color:var(--accent-bright); '
                                                f'background:rgba(99,102,241,0.08); border-radius:6px; '
                                                f'padding:6px 10px; margin-top:4px; '
                                                f'font-family:monospace; white-space:pre-wrap">'
                                                f'{sug.action_text[:300]}</div>'
                                            )

                    ui.separator().style("opacity:0.15; margin:12px 0")

                    # Brief Coach CTA
                    def brief_coach():
                        if report is None:
                            return
                        sp = session.agent_spec.system_prompt or ""
                        name = session.agent_spec.name or "agent"
                        briefing = build_coach_briefing(report, name, sp)
                        msgs = app.storage.user.setdefault("coach_messages", [])
                        msgs.append({"role": "user", "content": briefing})
                        app.storage.user["coach_messages"] = msgs
                        ui.navigate.to("/coach")

                    with ui.row().classes("gap-2 items-center flex-wrap"):
                        ui.button(
                            "Brief Coach →", icon="chat", on_click=brief_coach
                        ).props("color=primary size=sm").style("font-weight:600")
                        ui.button(
                            "Refine Rubric →", icon="tune",
                            on_click=lambda: ui.navigate.to("/judge"),
                        ).props("outline size=sm dark").style("color:var(--accent-bright)")
                        ui.label(
                            "Brief Coach injects the quality report into your Coach conversation."
                        ).style("font-size:0.68rem; color:var(--text-muted)")

    render_quality_loop()

    # ── Keyboard shortcuts ────────────────────────────────────────────────────
    ui.html(
        '<div style="font-size:0.62rem; color:var(--text-muted); margin-top:6px; text-align:center">'
        '← → navigate &nbsp;·&nbsp; 1 / 2 / 3 quick-annotate all models with first / second / third label'
        '</div>'
    )

    def _handle_eval_kb(e):
        key = e.key
        if key == "ArrowLeft" and kb_state.get("go"):
            kb_state["go"](-1)
        elif key == "ArrowRight" and kb_state.get("go"):
            kb_state["go"](1)
        elif key in ("1", "2", "3") and kb_state.get("annotate"):
            label_idx = int(key) - 1
            labels = _get_all_labels()
            if label_idx < len(labels):
                kb_state["annotate"](labels[label_idx]["key"])

    ui.keyboard(on_key=_handle_eval_kb, ignore=["input", "select", "textarea", "button"])

    # ── Import / Share Panel ──────────────────────────────────────────────────
    with ui.expansion("Import or Share Annotations", icon="share").classes("w-full").style(
        "background:var(--bg-surface-2); border-radius:12px; border:1px solid var(--border-subtle); margin-top:1rem"
    ):
        ui.label("Share your annotations with teammates or import theirs for comparison.").style(
            "font-size:0.78rem; color:var(--text-tertiary); margin-bottom:12px"
        )

        with ui.row().classes("gap-3 flex-wrap"):
            # Export my annotations
            def export_annotations():
                results = _get_eval_results()
                if not results:
                    ui.notify("No eval results to export yet", type="warning")
                    return
                data = {
                    "annotator": app.storage.user.get("email", "anonymous"),
                    "agent": session.agent_spec.name if session.agent_spec else "unknown",
                    "exported_at": datetime.now().isoformat(),
                    "custom_labels": app.storage.user.get("custom_annotation_labels", []),
                    "eval_results": results,
                }
                ui.download(json.dumps(data, indent=2).encode(), "annotations_export.json")

            ui.button("Export My Annotations", icon="download", on_click=export_annotations).props(
                "outline size=sm dark"
            ).style("color:var(--accent-bright)")

            # Share by code
            share_code_ref: dict = {"code": None}

            def generate_share_code():
                results = _get_eval_results()
                if not results:
                    ui.notify("Run an evaluation first", type="warning")
                    return
                code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                data = {
                    "annotator": app.storage.user.get("email", "anonymous"),
                    "agent": session.agent_spec.name if session.agent_spec else "unknown",
                    "shared_at": datetime.now().isoformat(),
                    "custom_labels": app.storage.user.get("custom_annotation_labels", []),
                    "eval_results": results,
                }
                app.storage.general[f"share_{code}"] = data
                share_code_ref["code"] = code
                with ui.dialog() as dlg:
                    dlg.open()
                    with ui.card().style("min-width:300px; padding:1.5rem; background:var(--bg-surface-2)"):
                        ui.label("Share Code").style(
                            "font-size:0.7rem; font-weight:600; color:var(--text-tertiary); "
                            "text-transform:uppercase; letter-spacing:0.04em"
                        )
                        ui.label(code).style(
                            "font-size:2rem; font-weight:700; color:var(--accent-bright); "
                            "letter-spacing:0.15em; margin:8px 0"
                        )
                        ui.label("Share this code with your teammates. They can import it below.").style(
                            "font-size:0.78rem; color:var(--text-secondary)"
                        )
                        ui.button(
                            "Copy Code",
                            on_click=lambda: ui.run_javascript(f"navigator.clipboard.writeText('{code}')")
                        ).props("size=sm color=primary").style("margin-top:12px")

            ui.button("Share by Code", icon="share", on_click=generate_share_code).props(
                "outline size=sm dark"
            ).style("color:var(--green-bright)")

        ui.separator().style("opacity:0.15; margin:12px 0")

        # Import panel
        with ui.row().classes("gap-3 items-end flex-wrap"):
            # Import by share code
            code_input = ui.input(
                "Enter share code", placeholder="e.g. ABC123"
            ).props("dense outlined dark").style("width:150px")

            imported_container = ui.column().classes("w-full")

            def import_by_code():
                code = code_input.value.strip().upper()
                if len(code) != 6:
                    ui.notify("Enter a valid 6-character code", type="warning")
                    return
                data = app.storage.general.get(f"share_{code}")
                if not data:
                    ui.notify("Code not found or expired", type="negative")
                    return
                _render_imported_annotations(imported_container, data)

            ui.button("Load", icon="input", on_click=import_by_code).props(
                "dense size=sm color=primary"
            )

            # Import by file upload
            def handle_upload(e):
                try:
                    data = json.loads(e.content.read())
                    _render_imported_annotations(imported_container, data)
                except Exception as ex:
                    ui.notify(f"Failed to parse file: {ex}", type="negative")

            ui.upload(
                label="Import JSON file",
                on_upload=handle_upload,
                auto_upload=True,
            ).props("accept=.json flat dense dark").style(
                "color:var(--text-tertiary); font-size:0.78rem"
            )


def _render_imported_annotations(container, data: dict) -> None:
    """Show imported annotations from another annotator for comparison."""
    container.clear()
    with container:
        annotator = data.get("annotator", "Unknown")
        agent = data.get("agent", "Unknown")
        shared_at = data.get("shared_at") or data.get("exported_at", "")[:10]
        external_results: list[dict] = data.get("eval_results", [])
        external_labels: list[dict] = data.get("custom_labels", [])

        if not external_results:
            ui.notify("No annotations found in imported data", type="warning")
            return

        app.storage.user["shared_eval_results"] = external_results
        app.storage.user["shared_annotator"] = annotator

        ui.notify(
            f"Loaded {len(external_results)} annotations from {annotator}",
            type="positive",
        )

        with ui.card().classes("w-full").style(
            "background:var(--bg-surface-2); border-radius:10px; border:1px solid var(--accent); margin-top:12px"
        ):
            with ui.row().classes("items-center justify-between w-full").style("margin-bottom:8px"):
                ui.label(f"External Annotations — {annotator}").style(
                    "font-size:0.8rem; font-weight:600; color:var(--accent-bright)"
                )
                ui.label(f"Agent: {agent} · {shared_at}").style(
                    "font-size:0.72rem; color:var(--text-tertiary)"
                )

            # Custom labels used
            all_ext_labels = DEFAULT_LABELS + external_labels
            label_map = {l["key"]: l for l in all_ext_labels}

            # Agreement statistics
            my_results = _get_eval_results()
            if my_results:
                agree = 0
                total_compared = 0
                for my_r, ext_r in zip(my_results, external_results):
                    for model_id in my_r.get("responses", {}):
                        my_ann = my_r.get("annotations", {}).get(model_id, "")
                        ext_ann = ext_r.get("annotations", {}).get(model_id, "")
                        if my_ann and ext_ann:
                            total_compared += 1
                            if my_ann == ext_ann:
                                agree += 1
                if total_compared:
                    pct = agree / total_compared * 100
                    color = "var(--green-bright)" if pct >= 70 else ("var(--yellow)" if pct >= 50 else "var(--red)")
                    with ui.row().classes("items-center gap-2").style("margin-bottom:8px"):
                        ui.label(f"Agreement: {pct:.0f}%").style(
                            f"font-size:0.85rem; font-weight:700; color:{color}"
                        )
                        ui.label(f"({agree}/{total_compared} responses match)").style(
                            "font-size:0.75rem; color:var(--text-tertiary)"
                        )

            # Show first 5 as preview
            preview = external_results[:5]
            for ext_r in preview:
                with ui.element("div").style(
                    "background:var(--bg-surface-1); border-radius:8px; padding:10px 12px; margin-bottom:6px"
                ):
                    ui.label(ext_r.get("query", "")[:80] + "...").style(
                        "font-size:0.78rem; color:var(--text-secondary); margin-bottom:4px"
                    )
                    with ui.row().classes("gap-1 flex-wrap"):
                        for model_id, ann_key in ext_r.get("annotations", {}).items():
                            lbl_info = label_map.get(ann_key, {"label": ann_key, "color": "blue"})
                            css_color = LABEL_COLORS.get(lbl_info.get("color", "blue"), "var(--blue)")
                            ui.html(
                                f'<span style="background:{css_color}22; color:{css_color}; '
                                f'border:1px solid {css_color}44; border-radius:3px; '
                                f'padding:2px 6px; font-size:0.7rem">'
                                f'{model_id.split(".")[-1][:20]}: {lbl_info["label"]}</span>'
                            )

            if len(external_results) > 5:
                ui.label(f"... and {len(external_results) - 5} more annotations").style(
                    "font-size:0.72rem; color:var(--text-muted)"
                )


def render_results(
    container, selected_models: list[str], annotations_list: list[dict],
    kb_state: dict | None = None,
) -> None:
    """Render the eval results with annotation controls."""
    container.clear()

    eval_results = _get_eval_results()
    if not eval_results:
        return

    model_labels = {m["id"]: m["label"] for m in AVAILABLE_MODELS}

    judge_prompt = app.storage.user.get("_generated_judge_prompt", "")
    judge_results = _get_judge_results()
    shared_results = app.storage.user.get("shared_eval_results", [])
    shared_annotator = app.storage.user.get("shared_annotator", "")

    with container:
        with ui.row().classes("w-full items-center justify-between").style("margin-bottom:12px"):
            ui.label(
                f"Results: {len(eval_results)} queries × {len(selected_models)} models"
            ).style("font-size:0.9rem; font-weight:700; color:var(--text-primary)")

            with ui.row().classes("items-center gap-2"):
                summary_parts = []
                for model_id in selected_models:
                    label = model_labels.get(model_id, model_id)
                    correct = sum(
                        1 for r in eval_results if r["annotations"].get(model_id) == "correct"
                    )
                    total_ann = sum(1 for r in eval_results if model_id in r["annotations"])
                    if total_ann:
                        summary_parts.append(f"{label}: {correct}/{total_ann} ✓")
                if summary_parts:
                    ui.label(" · ".join(summary_parts)).style(
                        "font-size:0.75rem; color:var(--text-tertiary)"
                    )

                if judge_prompt:
                    judge_status = ui.label("").style("font-size:0.72rem; color:var(--text-muted)")
                    judge_btn_ref: dict = {}

                    async def run_all_judges():
                        judge_btn_ref["btn"].props("loading")
                        scored = 0
                        for idx, result in enumerate(eval_results):
                            for mid in selected_models:
                                resp = result["responses"].get(mid, "")
                                if not resp or resp.startswith("[Error:"):
                                    continue
                                key = f"{idx}_{mid}"
                                verdict = await _score_with_judge(judge_prompt, result["query"], resp)
                                judge_results[key] = {"pass": verdict}
                                scored += 1
                        judge_btn_ref["btn"].props(remove="loading")
                        passed = sum(1 for v in judge_results.values() if v.get("pass") is True)
                        judge_status.set_text(f"Judge: {passed}/{scored} PASS")
                        render_current()

                    judge_btn = ui.button("Run Judge", icon="gavel", on_click=run_all_judges).props("size=sm outline dark")
                    judge_btn_ref["btn"] = judge_btn

                    if judge_results:
                        passed = sum(1 for v in judge_results.values() if v.get("pass") is True)
                        judge_status.set_text(f"Judge: {passed}/{len(judge_results)} PASS")

        # ── Filter bar ────────────────────────────────────────────────────────
        filter_state = {"key": "all"}
        position = {"value": 0}

        def get_filtered_indices() -> list[int]:
            key = filter_state["key"]
            if key == "all":
                return list(range(len(eval_results)))
            if key == "unannotated":
                return [
                    i for i, r in enumerate(eval_results)
                    if not any(r["annotations"].get(m) for m in selected_models)
                ]
            return [
                i for i, r in enumerate(eval_results)
                if any(r["annotations"].get(m) == key for m in selected_models)
            ]

        filter_bar_container = ui.row().classes("gap-1 flex-wrap items-center").style(
            "margin-bottom:10px"
        )

        def render_filter_bar():
            filter_bar_container.clear()
            with filter_bar_container:
                ui.label("Filter:").style(
                    "font-size:0.72rem; color:var(--text-tertiary); margin-right:4px"
                )
                filter_options = [("all", "All"), ("unannotated", "Unannotated")] + [
                    (l["key"], l["label"]) for l in _get_all_labels()
                ]
                for fkey, flabel in filter_options:
                    if fkey == "all":
                        count = len(eval_results)
                    elif fkey == "unannotated":
                        count = sum(
                            1 for r in eval_results
                            if not any(r["annotations"].get(m) for m in selected_models)
                        )
                    else:
                        count = sum(
                            1 for r in eval_results
                            if any(r["annotations"].get(m) == fkey for m in selected_models)
                        )
                    is_active = filter_state["key"] == fkey

                    def make_filter(k=fkey):
                        def apply():
                            filter_state["key"] = k
                            position["value"] = 0
                            render_filter_bar()
                            render_current()
                        return apply

                    ui.button(
                        f"{flabel} ({count})", on_click=make_filter()
                    ).props("size=xs dense no-caps").style(
                        f"{'background:var(--accent); color:white' if is_active else 'background:var(--bg-hover); color:var(--text-secondary)'}; "
                        "border-radius:4px; padding:2px 8px; font-size:0.72rem"
                    )

        render_filter_bar()

        # ── Category saturation ───────────────────────────────────────────────
        sat_container = ui.column().classes("w-full")

        def render_sat_indicator():
            sat_container.clear()
            cats: dict[str, dict] = {}
            for r in eval_results:
                cat = r.get("category", "") or "general"
                if cat not in cats:
                    cats[cat] = {"total": 0, "annotated": 0}
                cats[cat]["total"] += 1
                if any(r["annotations"].get(m) for m in selected_models):
                    cats[cat]["annotated"] += 1
            if len(cats) <= 1:
                return
            with sat_container:
                with ui.element("div").style(
                    "background:var(--bg-surface-1); border-radius:8px; padding:8px 12px; "
                    "margin-bottom:8px; border:1px solid var(--border-subtle)"
                ):
                    ui.label("Category Coverage").style(
                        "font-size:0.65rem; font-weight:600; color:var(--text-tertiary); "
                        "text-transform:uppercase; letter-spacing:0.04em; margin-bottom:5px"
                    )
                    for cat, stats in sorted(cats.items()):
                        pct = stats["annotated"] / max(stats["total"], 1)
                        color = (
                            "var(--green-bright)" if pct >= 0.8
                            else "var(--yellow)" if pct >= 0.4
                            else "var(--text-muted)"
                        )
                        with ui.row().classes("items-center gap-2").style("margin-bottom:3px"):
                            ui.label(cat[:22]).style(
                                "font-size:0.67rem; color:var(--text-secondary); "
                                "width:130px; overflow:hidden; text-overflow:ellipsis; "
                                "white-space:nowrap; flex-shrink:0"
                            )
                            ui.linear_progress(value=pct).props("size=3px").style("flex:1")
                            ui.label(f"{stats['annotated']}/{stats['total']}").style(
                                f"font-size:0.65rem; color:{color}; white-space:nowrap"
                            )

        render_sat_indicator()

        # System prompt from storage (needed for retry)
        _session_data = app.storage.user.get("session_data", {})
        _stored_system_prompt = (
            (_session_data.get("agent_spec") or {}).get("system_prompt", "")
            if isinstance(_session_data, dict) else ""
        )

        # Step-through navigation
        card_container = ui.column().classes("w-full")

        def render_current():
            card_container.clear()
            fi = get_filtered_indices()
            if not fi:
                with card_container:
                    ui.label("No results match this filter.").style(
                        "font-size:0.85rem; color:var(--text-muted); text-align:center; padding:24px 0"
                    )
                return

            pos = min(position["value"], len(fi) - 1)
            position["value"] = pos
            idx = fi[pos]
            result = eval_results[idx]
            ext_result = shared_results[idx] if shared_results and idx < len(shared_results) else None
            all_labels = _get_all_labels()

            with card_container:
                # Navigation
                with ui.row().classes("w-full items-center justify-between").style(
                    "margin-bottom:12px"
                ):
                    ui.button(
                        icon="chevron_left",
                        on_click=lambda: go(-1),
                    ).props("flat round" + (" disable" if pos == 0 else ""))
                    ui.label(
                        f"Query {pos + 1} of {len(fi)}"
                        + (f"  (#{idx + 1} overall)" if filter_state["key"] != "all" else "")
                    ).style("font-size:0.85rem; font-weight:600; color:var(--text-primary)")
                    ui.button(
                        icon="chevron_right",
                        on_click=lambda: go(1),
                    ).props("flat round" + (" disable" if pos >= len(fi) - 1 else ""))

                # Query card
                with ui.card().classes("w-full").style(
                    "background:var(--accent-tint); border-radius:10px; padding:16px; margin-bottom:12px; border:1px solid rgba(94,106,210,0.2)"
                ):
                    if result["category"]:
                        ui.html(
                            f'<span style="font-size:0.65rem; font-weight:600; color:var(--accent-bright); '
                            f'text-transform:uppercase; letter-spacing:0.04em">'
                            f'{result["category"]}</span>'
                        )
                    ui.label(result["query"]).style(
                        "font-size:0.9rem; font-weight:500; color:var(--text-primary); margin-top:4px"
                    )

                # Model responses side by side
                with ui.row().classes("w-full gap-sm"):
                    for model_id in selected_models:
                        resp = result["responses"].get(model_id, "")
                        annotation = result["annotations"].get(model_id, "")
                        is_error = resp.startswith("[Error:")

                        border_color = _label_css_color(annotation) if annotation else (
                            "var(--red)" if is_error else "var(--border-default)"
                        )
                        ext_ann = ext_result.get("annotations", {}).get(model_id, "") if ext_result else ""

                        with ui.card().classes("flex-1").style(
                            f"border-radius:10px; padding:12px; border:2px solid {border_color}; "
                            f"min-width:0; background:var(--bg-surface-1)"
                        ):
                            ui.label(model_labels.get(model_id, model_id)).style(
                                "font-size:0.7rem; font-weight:600; color:var(--accent-bright); "
                                "text-transform:uppercase; margin-bottom:6px"
                            )

                            if is_error:
                                ui.label(resp).style(
                                    "font-size:0.75rem; color:var(--red); font-style:italic"
                                )

                                async def retry_query(m_id=model_id, r=result):
                                    r["responses"][m_id] = "Retrying…"
                                    render_current()
                                    new_resp = await run_query_against_model(
                                        _stored_system_prompt, r["query"], m_id
                                    )
                                    r["responses"][m_id] = new_resp
                                    render_current()

                                ui.button(
                                    "Retry", icon="refresh", on_click=retry_query
                                ).props("size=xs outline").style(
                                    "color:var(--yellow); border-color:var(--yellow)44; margin-top:6px"
                                )
                            else:
                                with ui.scroll_area().style("max-height:250px; width:100%"):
                                    ui.markdown(resp).style(
                                        "font-size:0.75rem; color:var(--text-secondary); line-height:1.5"
                                    )

                            ui.separator().style("opacity:0.2; margin:8px 0")

                            ui.label("My verdict:").style(
                                "font-size:0.65rem; color:var(--text-tertiary); margin-bottom:4px"
                            )
                            with ui.row().classes("gap-xs items-center flex-wrap"):
                                def make_annotate(m_id, label_key):
                                    def annotate():
                                        result["annotations"][m_id] = label_key
                                        annotations_list.append({
                                            "query": result["query"],
                                            "response": result["responses"][m_id],
                                            "annotation": label_key,
                                            "model": model_labels.get(m_id, m_id),
                                            "error_code": "",
                                            "notes": result.get("notes", ""),
                                        })
                                        render_current()
                                        render_filter_bar()
                                        render_sat_indicator()
                                    return annotate

                                for lbl in all_labels:
                                    is_active = annotation == lbl["key"]
                                    css_color = LABEL_COLORS.get(lbl["color"], "var(--border-default)")
                                    btn_style = (
                                        f"background:{css_color}; color:white; border-radius:4px; margin:1px; font-size:0.72rem"
                                        if is_active else
                                        f"color:{css_color}; border:1px solid {css_color}44; background:{css_color}11; border-radius:4px; margin:1px; font-size:0.72rem"
                                    )
                                    ui.button(
                                        lbl["label"],
                                        on_click=make_annotate(model_id, lbl["key"])
                                    ).props("dense size=sm" + ("" if is_active else " flat")).style(btn_style)

                            if ext_ann and shared_annotator:
                                ext_css = _label_css_color(ext_ann)
                                ui.html(
                                    f'<div style="margin-top:6px; font-size:0.65rem; color:var(--text-tertiary)">'
                                    f'{shared_annotator}: '
                                    f'<span style="color:{ext_css}; font-weight:600">{ext_ann}</span>'
                                    f'{"  ✓ agree" if ext_ann == annotation and annotation else ("  ✗ disagree" if annotation else "")}</div>'
                                )

                # Judge result row
                judge_row_parts = []
                for mid in selected_models:
                    key = f"{idx}_{mid}"
                    if key in judge_results:
                        v = judge_results[key]
                        status = "PASS" if v.get("pass") else "FAIL"
                        color = "var(--green)" if v.get("pass") else "var(--red)"
                        label_short = model_labels.get(mid, mid).split()[-1]
                        judge_row_parts.append(f'<span style="color:{color}; font-weight:600">{label_short}: {status}</span>')
                if judge_row_parts:
                    ui.html(
                        '<div style="font-size:0.72rem; color:var(--text-tertiary); margin-top:6px">Judge: '
                        + " · ".join(judge_row_parts)
                        + "</div>"
                    )

                # Notes input
                notes_input = ui.input(
                    placeholder="Add notes for this query (error code, why it failed...)",
                    value=result.get("notes", ""),
                ).classes("w-full").style("margin-top:12px; font-size:0.8rem").props("dense outlined")

                def save_notes(e, r=result):
                    r["notes"] = e.value

                notes_input.on_value_change(save_notes)

                # Annotation progress
                total_annotated = sum(1 for r in eval_results for _ in r["annotations"].values())
                total_possible = len(eval_results) * len(selected_models)
                ui.label(f"Annotated: {total_annotated}/{total_possible}").style(
                    "font-size:0.75rem; color:var(--text-tertiary); margin-top:12px"
                )

        def go(delta: int):
            fi = get_filtered_indices()
            if not fi:
                return
            position["value"] = max(0, min(len(fi) - 1, position["value"] + delta))
            render_current()

        def annotate_current(label_key: str) -> None:
            """Bulk-apply label_key to all selected models on the current query (keyboard shortcut)."""
            fi = get_filtered_indices()
            if not fi:
                return
            pos = min(position["value"], len(fi) - 1)
            idx = fi[pos]
            result = eval_results[idx]
            for m_id in selected_models:
                result["annotations"][m_id] = label_key
                annotations_list.append({
                    "query": result["query"],
                    "response": result["responses"].get(m_id, ""),
                    "annotation": label_key,
                    "model": model_labels.get(m_id, m_id),
                    "error_code": "",
                    "notes": result.get("notes", ""),
                })
            render_current()
            render_filter_bar()
            render_sat_indicator()

        if kb_state is not None:
            kb_state["go"] = go
            kb_state["annotate"] = annotate_current

        render_current()
