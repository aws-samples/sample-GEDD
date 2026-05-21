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

from grounded_evals.guide.session import Session
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
        return

    variants = prompt_variants or []

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

    # ── Model Selection + Run ─────────────────────────────────────────────────
    results_container = ui.column().classes("w-full")

    with ui.card().classes("w-full q-pa-md").style(
        "background:var(--bg-surface-2); border-radius:12px; border:1px solid var(--border-subtle); margin-bottom:1rem"
    ):
        ui.label("Select Models to Compare").style(
            "font-size:0.85rem; font-weight:700; color:var(--text-primary); margin-bottom:8px"
        )
        ui.label(
            f"Running {len(session.golden_prompts)} golden queries against selected models"
        ).style("font-size:0.75rem; color:var(--text-tertiary); margin-bottom:12px")

        checkboxes = []
        existing_selected = _get_selected_models()
        with ui.row().classes("gap-md"):
            for model in AVAILABLE_MODELS:
                cb = ui.checkbox(model["label"], value=model["id"] in existing_selected)
                checkboxes.append((cb, model["id"]))

        ui.separator().style("opacity:0.2; margin:12px 0")

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
            progress_label.set_text("Running queries...")

            total = len(session.golden_prompts)
            for idx, gp in enumerate(session.golden_prompts):
                progress_label.set_text(f"Running query {idx + 1}/{total}...")
                responses = {}
                for model_id in sel:
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

            progress_label.set_text(
                f"Done! {total} queries × {len(sel)} models = {total * len(sel)} responses"
            )
            run_btn.props(remove="loading")
            render_results(results_container, sel, annotations_list)
            _save_eval_snapshot(sel, eval_results_store)

        run_btn = ui.button(
            "Run Evaluation", icon="play_arrow", on_click=run_eval
        ).props("color=primary")

    # Re-render existing results when navigating back
    existing_results = _get_eval_results()
    existing_sel = _get_selected_models()
    if existing_results and existing_sel:
        render_results(results_container, existing_sel, annotations_list)

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
    container, selected_models: list[str], annotations_list: list[dict]
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

        render_current()
