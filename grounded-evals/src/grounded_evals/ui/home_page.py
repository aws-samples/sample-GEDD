"""Home page — Problem Space → Solution Space workflow."""

from nicegui import app, ui

from grounded_evals.ui.layout import BRAND_CSS


PROBLEM_STEPS = [
    {"num": 1, "title": "Define the Job", "desc": "What is your agent trying to accomplish? For whom? Under what constraints?", "path": "/coach", "icon": "chat"},
    {"num": 2, "title": "Observe Behavior", "desc": "Run golden queries against your agent — see what actually happens", "path": "/eval", "icon": "science"},
    {"num": 3, "title": "Discover Failures", "desc": "Inductively code failure patterns from real outputs — no assumptions", "path": "/coding", "icon": "label"},
    {"num": 4, "title": "Understand Why", "desc": "Map causal relationships — what triggers failures, under what conditions?", "path": "/analysis", "icon": "hub"},
]

SOLUTION_STEPS = [
    {"num": 5, "title": "Build the Eval", "desc": "Generate rubrics, automated judges, and export — grounded in what you discovered", "path": "/report", "icon": "assessment"},
]


@ui.page("/")
def home_page():
    ui.add_head_html(f"<style>{BRAND_CSS}</style>")

    with ui.column().classes("w-full items-center").style("max-width: 820px; margin: 2.5rem auto; padding: 0 1.5rem"):

        # Header
        with ui.column().classes("items-center").style("text-align: center; margin-bottom: 2rem"):
            ui.label("GEDD").style(
                "font-size: 0.7rem; font-weight: 700; letter-spacing: 0.15em; "
                "color: #16a34a; background: #dcfce7; padding: 4px 14px; border-radius: 20px"
            )
            ui.label("Grounded Eval-Driven Development").style(
                "font-size: 1.7rem; font-weight: 700; color: #14532d; margin-top: 0.6rem"
            )
            ui.label("Build AI agent evaluations the right way — problem first, solution second").style(
                "font-size: 0.9rem; color: #6b7280; margin-top: 0.4rem"
            )

        # Problem Space section
        with ui.column().classes("w-full").style("margin-bottom: 0.5rem"):
            with ui.row().classes("items-center gap-sm").style("margin-bottom: 0.75rem"):
                ui.label("PROBLEM SPACE").style(
                    "font-size: 0.65rem; font-weight: 700; letter-spacing: 0.12em; "
                    "color: #7c3aed; background: #ede9fe; padding: 3px 10px; border-radius: 4px"
                )
                ui.label("Understand what your agent fails at — and why").style(
                    "font-size: 0.8rem; color: #6b7280; font-style: italic"
                )

            for step in PROBLEM_STEPS:
                with ui.card().classes("w-full").style(
                    "padding: 1rem 1.2rem; margin-bottom: 0.6rem; border-radius: 12px; "
                    "border-left: 4px solid #7c3aed; cursor: pointer; transition: transform 0.1s"
                ).on("click", lambda p=step["path"]: ui.navigate.to(p)):
                    with ui.row().classes("items-center gap-md"):
                        ui.icon(step["icon"]).style("font-size: 1.4rem; color: #7c3aed")
                        with ui.column().style("gap: 1px"):
                            with ui.row().classes("items-center gap-sm"):
                                ui.label(f"{step['num']}").style(
                                    "font-size: 0.65rem; font-weight: 700; color: #7c3aed; "
                                    "background: #ede9fe; width: 18px; height: 18px; border-radius: 50%; "
                                    "display: flex; align-items: center; justify-content: center"
                                )
                                ui.label(step["title"]).style("font-size: 1rem; font-weight: 600; color: #1a1a1a")
                            ui.label(step["desc"]).style("font-size: 0.82rem; color: #6b7280")

        # Divider
        with ui.row().classes("w-full items-center").style("margin: 1rem 0"):
            ui.element("div").style("flex: 1; height: 1px; background: #e5e7eb")
            ui.label("then").style("font-size: 0.75rem; color: #9ca3af; padding: 0 12px; font-style: italic")
            ui.element("div").style("flex: 1; height: 1px; background: #e5e7eb")

        # Solution Space section
        with ui.column().classes("w-full"):
            with ui.row().classes("items-center gap-sm").style("margin-bottom: 0.75rem"):
                ui.label("SOLUTION SPACE").style(
                    "font-size: 0.65rem; font-weight: 700; letter-spacing: 0.12em; "
                    "color: #16a34a; background: #dcfce7; padding: 3px 10px; border-radius: 4px"
                )
                ui.label("Build evaluation criteria grounded in what you discovered").style(
                    "font-size: 0.8rem; color: #6b7280; font-style: italic"
                )

            for step in SOLUTION_STEPS:
                with ui.card().classes("w-full").style(
                    "padding: 1rem 1.2rem; margin-bottom: 0.6rem; border-radius: 12px; "
                    "border-left: 4px solid #16a34a; cursor: pointer; transition: transform 0.1s"
                ).on("click", lambda p=step["path"]: ui.navigate.to(p)):
                    with ui.row().classes("items-center gap-md"):
                        ui.icon(step["icon"]).style("font-size: 1.4rem; color: #16a34a")
                        with ui.column().style("gap: 1px"):
                            with ui.row().classes("items-center gap-sm"):
                                ui.label(f"{step['num']}").style(
                                    "font-size: 0.65rem; font-weight: 700; color: #16a34a; "
                                    "background: #dcfce7; width: 18px; height: 18px; border-radius: 50%; "
                                    "display: flex; align-items: center; justify-content: center"
                                )
                                ui.label(step["title"]).style("font-size: 1rem; font-weight: 600; color: #1a1a1a")
                            ui.label(step["desc"]).style("font-size: 0.82rem; color: #6b7280")

        # Footer principle
        with ui.card().classes("w-full").style(
            "margin-top: 1.5rem; padding: 1rem 1.2rem; border-radius: 12px; "
            "background: #fefce8; border: 1px solid #fde68a; text-align: center"
        ):
            ui.label("Most eval tools skip straight to rubrics. GEDD makes you earn the right to build one.").style(
                "font-size: 0.85rem; color: #92400e; font-weight: 500"
            )
            ui.label("A rubric grounded in observed failures beats one grounded in assumptions — every time.").style(
                "font-size: 0.78rem; color: #a16207; margin-top: 4px"
            )

        # Logout
        def logout():
            app.storage.user["authenticated"] = False
            ui.navigate.to("/login")

        ui.button("Logout", icon="logout", on_click=logout).props("flat color=grey").style("margin-top: 1rem")
