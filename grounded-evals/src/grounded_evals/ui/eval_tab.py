"""Eval Tab — Run golden queries against multiple Bedrock models and annotate."""

from __future__ import annotations

import asyncio
import os

import boto3
from nicegui import app, ui

from grounded_evals.guide.session import Session
from grounded_evals.llm.client import get_default_client, traced_eval_call

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

    # System Prompt Variant Selection
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

    # Model selection
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

        results_container = ui.column().classes("w-full")
        progress_label = ui.label("").style("font-size:0.8rem; color:var(--text-tertiary)")

        async def run_eval():
            sel = [mid for cb, mid in checkboxes if cb.value]
            if not sel:
                ui.notify("Select at least one model", type="warning")
                return
            if len(sel) > 3:
                ui.notify("Select up to 3 models", type="warning")
                return

            # Determine active system prompt
            active_prompt = session.agent_spec.system_prompt
            if variants and len(variants) > 1:
                variant_name = selected_variant_ref["value"]
                for v in variants:
                    if v["name"] == variant_name:
                        active_prompt = v["prompt"]
                        break

            # Store per-user
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

        run_btn = ui.button(
            "Run Evaluation", icon="play_arrow", on_click=run_eval
        ).props("color=primary")

    # Re-render existing results when navigating back to this tab
    existing_results = _get_eval_results()
    existing_sel = _get_selected_models()
    if existing_results and existing_sel:
        render_results(results_container, existing_sel, annotations_list)


def render_results(
    container, selected_models: list[str], annotations_list: list[dict]
) -> None:
    """Render the eval results with annotation controls."""
    container.clear()

    eval_results = _get_eval_results()
    if not eval_results:
        return

    model_labels = {m["id"]: m["label"] for m in AVAILABLE_MODELS}

    with container:
        with ui.row().classes("w-full items-center justify-between").style("margin-bottom:12px"):
            ui.label(
                f"Results: {len(eval_results)} queries × {len(selected_models)} models"
            ).style("font-size:0.9rem; font-weight:700; color:var(--text-primary)")

            # Model comparison summary
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

        # Step-through navigation
        current_idx = {"value": 0}
        card_container = ui.column().classes("w-full")

        def render_current():
            card_container.clear()
            idx = current_idx["value"]
            result = eval_results[idx]

            with card_container:
                # Navigation
                with ui.row().classes("w-full items-center justify-between").style(
                    "margin-bottom:12px"
                ):
                    ui.button(
                        icon="chevron_left",
                        on_click=lambda: go(-1),
                    ).props("flat round" + (" disable" if idx == 0 else ""))
                    ui.label(f"Query {idx + 1} of {len(eval_results)}").style(
                        "font-size:0.85rem; font-weight:600; color:var(--text-primary)"
                    )
                    ui.button(
                        icon="chevron_right",
                        on_click=lambda: go(1),
                    ).props(
                        "flat round"
                        + (" disable" if idx == len(eval_results) - 1 else "")
                    )

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

                        border_color = {
                            "correct": "var(--green)",
                            "partial": "var(--yellow)",
                            "incorrect": "var(--red)",
                        }.get(annotation, "var(--red)" if is_error else "var(--border-default)")

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
                            else:
                                with ui.scroll_area().style("max-height:250px; width:100%"):
                                    ui.markdown(resp).style(
                                        "font-size:0.75rem; color:var(--text-secondary); line-height:1.5"
                                    )

                            ui.separator().style("opacity:0.2; margin:8px 0")
                            with ui.row().classes("gap-xs items-center"):

                                def make_annotate(m_id, label):
                                    def annotate():
                                        result["annotations"][m_id] = label
                                        annotations_list.append({
                                            "query": result["query"],
                                            "response": result["responses"][m_id],
                                            "annotation": label,
                                            "model": model_labels.get(m_id, m_id),
                                            "error_code": "",
                                            "notes": result.get("notes", ""),
                                        })
                                        render_current()
                                    return annotate

                                ui.button(
                                    "✓", on_click=make_annotate(model_id, "correct")
                                ).props(
                                    "dense size=sm"
                                    + (" color=green" if annotation == "correct" else " flat")
                                ).tooltip("Correct")
                                ui.button(
                                    "⚠", on_click=make_annotate(model_id, "partial")
                                ).props(
                                    "dense size=sm"
                                    + (" color=orange" if annotation == "partial" else " flat")
                                ).tooltip("Partially correct")
                                ui.button(
                                    "✗", on_click=make_annotate(model_id, "incorrect")
                                ).props(
                                    "dense size=sm"
                                    + (" color=red" if annotation == "incorrect" else " flat")
                                ).tooltip("Incorrect")

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
            current_idx["value"] = max(
                0, min(len(eval_results) - 1, current_idx["value"] + delta)
            )
            render_current()

        render_current()
