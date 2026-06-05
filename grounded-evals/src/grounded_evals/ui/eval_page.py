"""Eval page — Run golden queries against models and annotate."""

from nicegui import app, ui

from grounded_evals.guide.session import Session
from grounded_evals.ui.eval_tab import render as render_eval_tab
from grounded_evals.ui.layout import page_layout


@ui.page("/eval")
def eval_page():
    page_layout("Review Queue")

    s = app.storage.user
    session_data = s.get("session_data", {})
    session = Session.model_validate(session_data) if session_data else Session()
    annotations = s.get("annotations", [])
    prompt_variants = s.get("prompt_variants", [])

    with ui.column().classes("w-full").style("max-width: 1200px; margin: 1rem auto; padding: 0 1.5rem"):
        with ui.element("div").style(
            "background:var(--bg-surface-1); border:1px solid var(--border-subtle); "
            "border-radius:var(--radius-xl); padding:16px; margin-bottom:12px"
        ):
            with ui.row().classes("items-center justify-between gap-3 flex-wrap"):
                with ui.column().style("gap:3px; max-width:760px"):
                    ui.label("Review Queue").style(
                        "font-size:1.05rem; font-weight:700; color:var(--text-primary); "
                        "letter-spacing:-0.01em"
                    )
                    ui.label(
                        "First-pass annotation happens here: inspect each user-visible response, "
                        "apply a quick verdict, and keep enough notes for the deeper codebook pass."
                    ).style("font-size:0.82rem; color:var(--text-secondary); line-height:1.5")
                with ui.row().classes("items-center gap-2 flex-wrap"):
                    for label, icon in [
                        ("←/→ navigate", "keyboard_arrow_right"),
                        ("1/2/3 verdicts", "looks_one"),
                        ("filter unreviewed", "filter_alt"),
                    ]:
                        with ui.element("div").style(
                            "display:flex; align-items:center; gap:6px; padding:6px 9px; "
                            "border-radius:6px; background:var(--bg-surface-2); "
                            "border:1px solid var(--border-subtle)"
                        ):
                            ui.icon(icon).style("font-size:0.95rem; color:var(--accent-bright)")
                            ui.label(label).style(
                                "font-size:0.7rem; color:var(--text-tertiary); white-space:nowrap"
                            )

        # Feature 2: Prompt Diff Viewer
        prompt_history = s.get("prompt_history", [])
        current_prompt = session.agent_spec.system_prompt if session.agent_spec else ""
        if current_prompt and (not prompt_history or prompt_history[-1] != current_prompt):
            prompt_history.append(current_prompt)
            s["prompt_history"] = prompt_history

        if len(prompt_history) >= 2:
            with ui.expansion("📝 Prompt Diff Viewer", icon="compare").classes("w-full").style(
                "background: var(--bg-surface-2); border: 1px solid var(--border-subtle); "
                "border-radius: 12px; margin-bottom: 1rem; color: var(--text-primary)"
            ):
                ui.label(f"Comparing version {len(prompt_history)-1} → {len(prompt_history)}").style(
                    "font-size: 0.75rem; color: var(--text-tertiary); margin-bottom: 8px"
                )
                old_prompt = prompt_history[-2]
                new_prompt = prompt_history[-1]

                with ui.row().classes("w-full gap-2"):
                    with ui.element("div").style(
                        "flex: 1; background: var(--red-tint); border: 1px solid rgba(235,87,87,0.2); "
                        "border-radius: 8px; padding: 10px; max-height: 150px; overflow-y: auto"
                    ):
                        ui.label("PREVIOUS").style("font-size: 0.6rem; font-weight: 600; color: var(--red); letter-spacing: 0.05em; margin-bottom: 4px")
                        ui.label(old_prompt[:500]).style("font-size: 0.72rem; color: var(--text-secondary); white-space: pre-wrap; font-family: monospace")

                    with ui.element("div").style(
                        "flex: 1; background: var(--green-tint); border: 1px solid rgba(39,166,68,0.2); "
                        "border-radius: 8px; padding: 10px; max-height: 150px; overflow-y: auto"
                    ):
                        ui.label("CURRENT").style("font-size: 0.6rem; font-weight: 600; color: var(--green-bright); letter-spacing: 0.05em; margin-bottom: 4px")
                        ui.label(new_prompt[:500]).style("font-size: 0.72rem; color: var(--text-secondary); white-space: pre-wrap; font-family: monospace")

                # Show what changed
                old_words = set(old_prompt.lower().split())
                new_words = set(new_prompt.lower().split())
                added = new_words - old_words
                removed = old_words - new_words
                if added or removed:
                    with ui.row().classes("gap-3").style("margin-top: 8px"):
                        if added:
                            ui.label(f"+{len(added)} words added").style("font-size: 0.72rem; color: var(--green-bright)")
                        if removed:
                            ui.label(f"-{len(removed)} words removed").style("font-size: 0.72rem; color: var(--red)")

        render_eval_tab(session, annotations, prompt_variants)
