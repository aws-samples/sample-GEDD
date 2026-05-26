"""CLI for grounded-evals — Open Coding guided workflow for AI agent evaluation."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import click


# ── Session persistence helpers ──────────────────────────────────────────────

def _load_state(session_file: str):
    from grounded_evals.agent.tools import StateBundle
    from grounded_evals.guide.session import Session

    path = Path(session_file)
    if path.exists():
        data = json.loads(path.read_text())
        session = Session.model_validate(data["session"])
        state = StateBundle(
            session=session,
            annotations=data.get("annotations", []),
            current_step=data.get("current_step", 1),
            prompt_variants=data.get("prompt_variants", []),
        )
        return state, data.get("messages", [])

    from grounded_evals.guide.session import Session
    return StateBundle(session=Session()), []


def _save_state(session_file: str, state, messages: list[dict]) -> None:
    data = {
        "session": state.session.model_dump(mode="json"),
        "annotations": state.annotations,
        "current_step": state.current_step,
        "prompt_variants": state.prompt_variants,
        "messages": messages,
    }
    Path(session_file).write_text(json.dumps(data, indent=2, default=str))


@click.group()
def main() -> None:
    """grounded-evals: Build golden eval datasets and analyse AI agent failures."""


@main.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind")
@click.option("--port", default=8080, show_default=True, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Reload on code changes (dev mode)")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the GEDD web UI."""
    import grounded_evals.app  # noqa: F401 — registers all pages

    import os
    import secrets

    from nicegui import ui
    ui.run(
        host=host,
        port=port,
        reload=reload,
        title="GEDD",
        storage_secret=os.environ.get("STORAGE_SECRET") or secrets.token_hex(32),
    )


@main.command()
@click.option("--spec", "-s", required=True, type=click.Path(exists=True),
              help="Agent spec YAML or JSON file")
@click.option("--output", "-o", default="-", help="Output file (default: stdout)")
def fracture(spec: str, output: str) -> None:
    """Fracture an agent domain into testable prompt categories (Open Coding)."""
    from grounded_evals.ingest.parser import parse_agent_spec
    from grounded_evals.open_coding.fracture import fracture_domain

    agent_spec = parse_agent_spec(spec)

    click.echo(f"Fracturing domain for: {agent_spec.name}", err=True)
    categories = fracture_domain(agent_spec)

    result = [
        {
            "name": c.name,
            "definition": c.definition,
            "properties": [
                {
                    "name": p.name,
                    "dimensions": [d.model_dump() for d in p.dimensions],
                }
                for p in c.properties
            ],
        }
        for c in categories
    ]

    out_text = json.dumps(result, indent=2)
    if output == "-":
        click.echo(out_text)
    else:
        Path(output).write_text(out_text)
        click.echo(f"Wrote {len(categories)} categories to {output}", err=True)


@main.command("check-saturation")
@click.option("--dataset", "-d", required=True, type=click.Path(exists=True),
              help="Golden dataset JSONL file")
@click.option("--categories", "-c", type=click.Path(exists=True),
              help="Categories JSON (output of fracture). If omitted, inferred from dataset.")
def check_saturation(dataset: str, categories: str | None) -> None:
    """Check whether a golden dataset has reached theoretical saturation."""
    from uuid import uuid4

    from grounded_evals.models.core import Category, GoldenPrompt
    from grounded_evals.open_coding.saturation import check_overall_saturation

    raw_rows: list[dict] = []
    with Path(dataset).open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw_rows.append(json.loads(line))

    if categories:
        cats_data = json.loads(Path(categories).read_text())
        cats = [Category(name=c["name"], definition=c.get("definition", "")) for c in cats_data]
        cat_by_name = {c.name: c for c in cats}
        prompts = [
            GoldenPrompt(
                prompt_text=r.get("prompt_text") or r.get("prompt") or r.get("query", ""),
                category_id=cat_by_name[r["category"]].id if r.get("category") in cat_by_name else uuid4(),
                rationale=r.get("category") or r.get("rationale", ""),
            )
            for r in raw_rows
        ]
    else:
        # Infer categories from dataset rationale fields
        seen: dict[str, Category] = {}
        prompts = []
        for r in raw_rows:
            key = r.get("category") or r.get("rationale") or "uncategorized"
            if key not in seen:
                seen[key] = Category(name=key, definition="")
            prompts.append(GoldenPrompt(
                prompt_text=r.get("prompt_text") or r.get("prompt") or r.get("query", ""),
                category_id=seen[key].id,
                rationale=key,
            ))
        cats = list(seen.values())

    from grounded_evals.models.core import SaturationStatus
    from grounded_evals.open_coding.saturation import check_category_saturation

    report = check_overall_saturation(cats, prompts)
    statuses = [check_category_saturation(c, prompts) for c in cats]
    approaching = sum(1 for s in statuses if s == SaturationStatus.APPROACHING)
    unsaturated = sum(1 for s in statuses if s == SaturationStatus.UNSATURATED)

    click.echo(f"\nSaturation Report — {Path(dataset).name}")
    click.echo(f"  Total prompts  : {len(prompts)}")
    click.echo(f"  Categories     : {len(cats)}")
    click.echo(f"  Saturated      : {report.saturated_categories}")
    click.echo(f"  Approaching    : {approaching}")
    click.echo(f"  Unsaturated    : {unsaturated}")
    click.echo(f"  Coverage       : {report.saturation_score:.0%}")
    if report.gaps:
        click.echo("\n  Gaps (need more prompts):")
        for gap in report.gaps:
            click.echo(f"    • {gap}")
    saturated = report.saturation_score >= 0.8
    status = "SATURATED" if saturated else "NOT YET SATURATED"
    click.echo(f"\n  Status: {status}\n")
    sys.exit(0 if saturated else 1)


@main.command()
@click.option("--dataset", "-d", required=True, type=click.Path(exists=True),
              help="Golden dataset JSONL file")
def coverage(dataset: str) -> None:
    """Show a coverage breakdown of a golden dataset by category."""
    from collections import Counter

    prompts = []
    with Path(dataset).open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            cat = obj.get("category") or obj.get("rationale") or "uncategorized"
            prompts.append(cat)

    counts = Counter(prompts)
    total = len(prompts)
    click.echo(f"\nCoverage — {Path(dataset).name}  ({total} prompts)\n")
    max_name = max((len(c) for c in counts), default=10)
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "█" * n + "░" * max(0, 5 - n)
        status = "✓ saturated" if n >= 3 else ("~ approaching" if n >= 2 else "✗ thin")
        click.echo(f"  {cat:<{max_name}}  {bar}  {n:>2}  {status}")
    click.echo()


@main.command()
@click.option("--dataset", "-d", required=True, type=click.Path(exists=True),
              help="Golden dataset JSONL file")
@click.option("--new-prompt", "-p", required=True, help="New candidate prompt text")
def compare(dataset: str, new_prompt: str) -> None:
    """Run constant comparison on a new prompt against an existing golden dataset."""
    from uuid import uuid4

    from grounded_evals.models.core import GoldenPrompt
    from grounded_evals.open_coding.compare import constant_comparison

    prompts: list[GoldenPrompt] = []
    with Path(dataset).open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            prompts.append(GoldenPrompt(
                prompt_text=obj.get("prompt_text") or obj.get("prompt") or obj.get("query", ""),
                category_id=uuid4(),
                rationale=obj.get("category") or obj.get("rationale", ""),
            ))

    click.echo(f"Comparing against {len(prompts)} existing prompts...", err=True)
    result = constant_comparison(new_prompt, prompts, [])

    click.echo(f"\nIs unique    : {'YES' if result.is_unique else 'NO'}")
    click.echo(f"Explanation  : {result.explanation}")
    if result.similar_existing:
        click.echo("\nSimilar existing prompts:")
        for s in result.similar_existing:
            click.echo(f"  • {s}")
    if result.gaps_filled:
        click.echo("\nGaps this prompt fills:")
        for g in result.gaps_filled:
            click.echo(f"  + {g}")
    if result.suggestions:
        click.echo("\nSuggested prompts to try next:")
        for s in result.suggestions:
            click.echo(f"  → {s}")
    click.echo()
    sys.exit(0 if result.is_unique else 1)


@main.command()
@click.option("--session", "-s", default="session.json", show_default=True,
              help="Session file to load/save state between runs")
def chat(session: str) -> None:
    """Interactive coaching session — guided through all 4 steps.

    Starts fresh or resumes from a saved session file. Type 'quit' to exit.

    Steps:\n
      1. Define your agent (name, capabilities, users)\n
      2. Write a system prompt collaboratively\n
      3. Generate golden test queries via Open Coding\n
      4. Run queries + annotate responses (error analysis)
    """
    from grounded_evals.agent.handler import run_agent_turn

    state, messages = _load_state(session)

    step_names = {1: "Define Agent", 2: "System Prompt", 3: "Golden Queries", 4: "Error Analysis"}

    if messages:
        n_queries = len(state.session.golden_prompts)
        click.echo(f"Resumed session from {session}")
        click.echo(f"  Step {state.current_step}/4: {step_names[state.current_step]}  |  {n_queries} queries saved")
        click.echo("Type 'quit' to exit.\n")
    else:
        click.echo(f"New GEDD session. State will be saved to: {session}")
        click.echo("Type 'quit' to exit.\n")
        # Send a silent opener so the coach greets the user first
        resp = run_agent_turn("Hello, I'm ready to start.", messages, state)
        click.echo(f"Coach: {resp.text}\n")
        _save_state(session, state, messages)

    while True:
        try:
            user_input = click.prompt("You")
        except (EOFError, KeyboardInterrupt):
            click.echo("\nSession saved.")
            break

        if user_input.strip().lower() in ("quit", "exit", "q"):
            click.echo("Session saved.")
            break

        resp = run_agent_turn(user_input, messages, state)

        for te in resp.tool_executions:
            name = te["tool_name"]
            result = json.loads(te["tool_result"])
            if name == "save_golden_query":
                click.echo(f"  [query #{result.get('total')} saved]", err=True)
            elif name == "set_current_step":
                s = result.get("step", 1)
                click.echo(f"  [→ step {s}: {step_names.get(s, '')}]", err=True)
            elif name == "save_agent_info":
                click.echo("  [agent info saved]", err=True)
            elif name == "save_annotation":
                click.echo(f"  [annotation #{result.get('total_annotations')} saved]", err=True)

        click.echo(f"\nCoach: {resp.text}\n")
        _save_state(session, state, messages)


@main.command("eval")
@click.option("--session", "-s", default="session.json", show_default=True,
              help="Session file with golden queries + system prompt")
@click.option("--output", "-o", default="eval_results.json", show_default=True,
              help="File to write results to")
@click.option("--model", "-m", default=None,
              help="Model ID to run against (default: same model as coach)")
def run_eval(session: str, output: str, model: str | None) -> None:
    """Run golden queries from a session against the agent and save results.

    Results are written to --output as JSON, ready for `annotate`.
    """
    from grounded_evals.llm.client import get_default_client, get_model_id, traced_eval_call

    state, _ = _load_state(session)
    prompts = state.session.golden_prompts
    system_prompt = state.session.agent_spec.system_prompt

    if not prompts:
        click.echo("No golden queries found. Run `chat` first to generate them.", err=True)
        sys.exit(1)
    if not system_prompt:
        click.echo("No system prompt found. Complete step 2 in `chat` first.", err=True)
        sys.exit(1)

    client = get_default_client()
    model_id = model or get_model_id()

    click.echo(f"Model  : {model_id}")
    click.echo(f"Queries: {len(prompts)}")
    click.echo(f"Output : {output}\n")

    results = []
    for i, prompt in enumerate(prompts, 1):
        click.echo(f"[{i}/{len(prompts)}] {prompt.prompt_text[:70]}", err=True)
        try:
            resp = traced_eval_call(client, model_id, system_prompt, prompt.prompt_text)
            agent_response = resp.content[0].text
        except Exception as exc:
            agent_response = f"[Error: {exc}]"

        results.append({
            "query": prompt.prompt_text,
            "category": prompt.rationale,
            "expected_behavior": prompt.expected_behavior,
            "agent_response": agent_response,
            "annotation": None,
            "error_code": None,
            "notes": None,
        })

        click.echo(f"\nQ: {prompt.prompt_text}")
        preview = agent_response[:300] + ("..." if len(agent_response) > 300 else "")
        click.echo(f"A: {preview}\n")

    Path(output).write_text(json.dumps(results, indent=2))
    click.echo(f"Saved {len(results)} results → {output}")


@main.command()
@click.option("--results", "-r", default="eval_results.json", show_default=True,
              help="Eval results file (output of `eval`)")
@click.option("--session", "-s", default="session.json", show_default=True,
              help="Session file to persist annotations into")
def annotate(results: str, session: str) -> None:
    """Annotate eval results interactively.

    For each response: mark correct / partial / incorrect, add an error code
    and notes for failures. Annotations are saved to both the results file and
    the session file.

    Keys: [c] correct   [p] partial   [i] incorrect   [s] skip
    """
    state, messages = _load_state(session)

    results_data: list[dict] = json.loads(Path(results).read_text())
    unannotated = [r for r in results_data if r.get("annotation") is None]

    if not unannotated:
        click.echo("All results are already annotated.")
        return

    click.echo(f"{len(unannotated)} unannotated responses.")
    click.echo("Keys: [c] correct  [p] partial  [i] incorrect  [s] skip\n")

    annotation_map = {"c": "correct", "p": "partial", "i": "incorrect"}

    for i, result in enumerate(unannotated, 1):
        click.echo(f"──── [{i}/{len(unannotated)}] ────────────────────────────────")
        click.echo(f"Category : {result.get('category', 'n/a')}")
        click.echo(f"Query    : {result['query']}")
        click.echo(f"Expected : {result.get('expected_behavior', 'n/a')}")
        response_preview = result["agent_response"][:400]
        if len(result["agent_response"]) > 400:
            response_preview += "..."
        click.echo(f"Response : {response_preview}\n")

        key = click.prompt("Annotation", default="c").strip().lower()
        if key == "s":
            click.echo()
            continue

        annotation = annotation_map.get(key, "correct")
        error_code = ""
        notes = ""
        if annotation in ("partial", "incorrect"):
            error_code = click.prompt("Error code (e.g. hallucination, wrong_tone, incomplete)", default="")
            notes = click.prompt("Notes — why did it fail?", default="")

        result["annotation"] = annotation
        result["error_code"] = error_code
        result["notes"] = notes

        state.annotations.append({
            "query": result["query"],
            "response": result["agent_response"],
            "annotation": annotation,
            "error_code": error_code,
            "notes": notes,
        })
        click.echo()

    Path(results).write_text(json.dumps(results_data, indent=2))
    _save_state(session, state, messages)

    total = len(results_data)
    annotated = sum(1 for r in results_data if r.get("annotation"))
    correct = sum(1 for r in results_data if r.get("annotation") == "correct")
    partial = sum(1 for r in results_data if r.get("annotation") == "partial")
    incorrect = sum(1 for r in results_data if r.get("annotation") == "incorrect")

    click.echo(f"Done. {annotated}/{total} annotated — {correct} correct, {partial} partial, {incorrect} incorrect")


@main.command()
@click.option("--session", "-s", default="session.json", show_default=True,
              help="Session file to export from")
@click.option("--format", "-f", "fmt",
              type=click.Choice(["jsonl", "csv", "json"]), default="jsonl", show_default=True,
              help="Output format")
@click.option("--output", "-o", default=None,
              help="Output file (default: <agent_name>_golden_dataset.<fmt>)")
def export(session: str, fmt: str, output: str | None) -> None:
    """Export the golden dataset from a session to JSONL, CSV, or JSON.

    \b
    Formats:
      jsonl  One query per line — best for feeding into eval pipelines
      csv    Spreadsheet-friendly for sharing with non-engineers
      json   Full Pydantic model dump with all metadata
    """
    state, _ = _load_state(session)
    prompts = state.session.golden_prompts

    if not prompts:
        click.echo("No golden queries in session.", err=True)
        sys.exit(1)

    agent_name = (state.session.agent_spec.name or "agent").lower().replace(" ", "_")
    out_path = output or f"{agent_name}_golden_dataset.{fmt}"

    if fmt == "jsonl":
        lines = [
            json.dumps({
                "query": p.prompt_text,
                "category": p.rationale,
                "expected_behavior": p.expected_behavior,
                "dimensions": p.property_values.get("dimensions", ""),
                "is_edge_case": p.is_edge_case,
                "is_adversarial": p.is_adversarial,
            })
            for p in prompts
        ]
        Path(out_path).write_text("\n".join(lines) + "\n")

    elif fmt == "json":
        dataset = state.session.to_golden_dataset()
        Path(out_path).write_text(dataset.model_dump_json(indent=2))

    elif fmt == "csv":
        rows = [
            {
                "query": p.prompt_text,
                "category": p.rationale,
                "expected_behavior": p.expected_behavior,
                "dimensions": p.property_values.get("dimensions", ""),
                "is_edge_case": p.is_edge_case,
                "is_adversarial": p.is_adversarial,
            }
            for p in prompts
        ]
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    click.echo(f"Exported {len(prompts)} queries → {out_path}")


if __name__ == "__main__":
    main()
