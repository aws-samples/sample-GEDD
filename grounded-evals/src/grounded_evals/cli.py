"""CLI for grounded-evals — Open Coding guided workflow for AI agent evaluation."""

from __future__ import annotations

import csv
import json
import os
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


def _infer_dimension(error_code: str) -> str:
    code = error_code.lower()
    if any(k in code for k in ["hallucin", "factual", "confab", "wrong_fact", "fabricat"]):
        return "accuracy"
    if any(k in code for k in ["tone", "hostile", "empathy", "rude", "harsh", "cold"]):
        return "tone"
    if any(k in code for k in ["escalat", "refus", "safety", "harm", "danger", "unsafe"]):
        return "safety"
    if any(k in code for k in ["incomplete", "missing", "partial", "skip", "unanswer"]):
        return "completeness"
    if any(k in code for k in ["instruction", "constraint", "policy", "prompt", "rule"]):
        return "instruction_following"
    if any(k in code for k in ["brand", "voice", "persona", "off_brand", "company"]):
        return "brand_relevance"
    if any(k in code for k in ["bias", "discriminat", "fair", "stereotyp", "inequit"]):
        return "bias"
    return "quality"


def _coverage_table(state, indent: str = "  ") -> str:
    from collections import Counter
    prompts = state.session.golden_prompts
    if not prompts:
        return f"{indent}No queries yet."
    counts = Counter(p.rationale for p in prompts)
    max_name = max(len(c) for c in counts)
    lines = [f"{indent}{'Category':<{max_name}}  Bars   N  Status"]
    lines.append(f"{indent}{'─' * max_name}  ─────  ─  ──────────")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(n, 5) + "░" * (5 - min(n, 5))
        status = "✓ saturated" if n >= 3 else ("~ approx." if n >= 2 else "✗ thin")
        lines.append(f"{indent}{cat:<{max_name}}  {bar}  {n}  {status}")
    saturated = sum(1 for n in counts.values() if n >= 3)
    lines.append(f"\n{indent}Saturation: {saturated}/{len(counts)} categories  ({len(prompts)} queries total)")
    return "\n".join(lines)


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

        saved_query_this_turn = False
        for te in resp.tool_executions:
            name = te["tool_name"]
            result = json.loads(te["tool_result"])
            if name == "save_golden_query":
                click.echo(f"  [query #{result.get('total')} saved]", err=True)
                saved_query_this_turn = True
            elif name == "set_current_step":
                s = result.get("step", 1)
                click.echo(f"  [→ step {s}: {step_names.get(s, '')}]", err=True)
            elif name == "save_agent_info":
                click.echo("  [agent info saved]", err=True)
            elif name == "save_annotation":
                click.echo(f"  [annotation #{result.get('total_annotations')} saved]", err=True)

        if saved_query_this_turn:
            click.echo("\n" + _coverage_table(state) + "\n", err=True)

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
    from collections import Counter

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
            existing = [a["error_code"] for a in state.annotations if a.get("error_code")]
            if existing:
                top = ", ".join(c for c, _ in Counter(existing).most_common(5))
                click.echo(f"  Previously used: {top}")
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

        if i % 5 == 0:
            c = sum(1 for a in state.annotations if a.get("annotation") == "correct")
            p = sum(1 for a in state.annotations if a.get("annotation") == "partial")
            inc = sum(1 for a in state.annotations if a.get("annotation") == "incorrect")
            click.echo(f"  ── Progress: {i}/{len(unannotated)}  ✓ {c}  ⚠ {p}  ✗ {inc} ──\n")

    Path(results).write_text(json.dumps(results_data, indent=2))
    _save_state(session, state, messages)

    total = len(results_data)
    annotated = sum(1 for r in results_data if r.get("annotation"))
    correct = sum(1 for r in results_data if r.get("annotation") == "correct")
    partial = sum(1 for r in results_data if r.get("annotation") == "partial")
    incorrect = sum(1 for r in results_data if r.get("annotation") == "incorrect")

    click.echo(f"Done. {annotated}/{total} annotated — {correct} correct, {partial} partial, {incorrect} incorrect")

    error_codes = Counter(r["error_code"] for r in results_data if r.get("error_code"))
    if error_codes:
        click.echo("\nError codes found:")
        for code, count in error_codes.most_common():
            click.echo(f"  {code:<30} ×{count}  → {_infer_dimension(code)}")
        click.echo("\nRun `grounded-evals analyze` to map these to evaluation dimensions.")
        click.echo("Run `grounded-evals judge` to generate your judge prompt.")


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


@main.command()
@click.option("--session", "-s", default="session.json", show_default=True)
@click.option("--results", "-r", default="eval_results.json", show_default=True)
def status(session: str, results: str) -> None:
    """Show a dashboard of the current GEDD session."""
    from collections import Counter

    path = Path(session)
    if not path.exists():
        click.echo("No session.json found. Run `grounded-evals chat` to start.")
        return

    data = json.loads(path.read_text())
    sess = data.get("session", {})
    agent_name = (sess.get("agent_spec") or {}).get("name", "not defined")
    step = data.get("current_step", 1)
    prompts = sess.get("golden_prompts", [])
    annotations = data.get("annotations", [])
    step_names = {1: "Define Agent", 2: "System Prompt", 3: "Golden Queries",
                  4: "Eval", 5: "Annotation", 6: "Export"}

    click.echo("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    click.echo("  GEDD Session Status")
    click.echo("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    click.echo(f"  Agent      : {agent_name}")
    click.echo(f"  Step       : {step} / 6  ({step_names.get(step, '')})")
    click.echo(f"  Session    : {session}\n")

    if prompts:
        cats = Counter(p.get("rationale", "uncategorized") for p in prompts)
        click.echo(f"  ── Golden Queries ({len(prompts)} total) ──\n")
        for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
            bar = "█" * min(n, 5) + "░" * max(0, 5 - n)
            stat = "✓ saturated" if n >= 3 else ("~ approx." if n >= 2 else "✗ thin")
            click.echo(f"  {cat:<18} {bar}  {n:>2}  {stat}")
        saturated = sum(1 for c in cats.values() if c >= 3)
        click.echo(f"\n  Overall: {saturated}/{len(cats)} saturated ({saturated / len(cats) * 100:.0f}%)\n")

    if annotations:
        correct = sum(1 for a in annotations if a.get("annotation") == "correct")
        partial = sum(1 for a in annotations if a.get("annotation") == "partial")
        incorrect = sum(1 for a in annotations if a.get("annotation") == "incorrect")
        click.echo(f"  ── Annotations ({len(annotations)} total) ──\n")
        click.echo(f"    ✓ correct    {correct}")
        click.echo(f"    ⚠ partial    {partial}")
        click.echo(f"    ✗ incorrect  {incorrect}")
        codes = Counter(a.get("error_code") for a in annotations if a.get("error_code"))
        if codes:
            click.echo("\n  Error codes:")
            for code, count in codes.most_common(5):
                click.echo(f"    {code:<24} ×{count}")
        click.echo()

    rpath = Path(results)
    if rpath.exists():
        rdata = json.loads(rpath.read_text())
        annotated = sum(1 for r in rdata if r.get("annotation"))
        click.echo(f"  Eval results: {len(rdata)} responses ({annotated} annotated)\n")

    # What's next suggestion
    click.echo("  ── What's next ──\n")
    if step == 1:
        click.echo("  Define your agent → grounded-evals chat")
    elif step == 2:
        click.echo("  Write a system prompt → grounded-evals chat")
    elif step == 3:
        n = len(prompts)
        if n < 15:
            click.echo(f"  Generate more queries ({n}/15 minimum) → grounded-evals chat")
        else:
            click.echo("  Queries ready → grounded-evals eval")
    elif step == 4:
        click.echo("  Run evaluation → grounded-evals eval")
    elif step == 5:
        unannotated = len(annotations) < len(prompts)
        if unannotated:
            click.echo("  Keep annotating → grounded-evals annotate")
        else:
            click.echo("  Generate judge → grounded-evals judge")
    else:
        click.echo("  Export dataset → grounded-evals export --format jsonl")

    click.echo("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


@main.command()
@click.option("--session", "-s", default="session.json", show_default=True)
@click.option("--results", "-r", default="eval_results.json", show_default=True)
@click.option("--style", type=click.Choice(["standard", "geval"]), default="geval", show_default=True,
              help="standard: direct rubric scoring | geval: chain-of-thought per criterion (more reliable)")
@click.option("--output", "-o", default="judge_prompt.md", show_default=True)
def judge(session: str, results: str, style: str, output: str) -> None:
    """Generate a deployable LLM-as-a-Judge prompt from annotations.

    \b
    Reads error codes from annotations, maps them to evaluation dimensions,
    builds a weighted rubric, and outputs a ready-to-use judge prompt.

    Styles:
      standard  Direct rubric scoring — fast, good baseline
      geval     Chain-of-thought per criterion (Liu et al. 2023) — more reliable
    """
    from collections import Counter

    from grounded_evals.axial_coding.mapper import ErrorMapping
    from grounded_evals.judge_builder.prompt_gen import generate_geval_judge_prompt, generate_judge_prompt
    from grounded_evals.judge_builder.rubric import generate_rubric

    state, _ = _load_state(session)
    annotations = list(state.annotations)

    rpath = Path(results)
    if rpath.exists():
        for r in json.loads(rpath.read_text()):
            if r.get("error_code"):
                annotations.append(r)

    codes = Counter(a.get("error_code") for a in annotations if a.get("error_code"))
    if not codes:
        click.echo("No error codes found. Run `annotate` first and name the failures.", err=True)
        sys.exit(1)

    mappings = [ErrorMapping(error_code=c, primary_category=_infer_dimension(c)) for c in codes]
    rubric = generate_rubric(mappings)
    agent_name = state.session.agent_spec.name or "AI Agent"
    agent_desc = state.session.agent_spec.description or ""

    if style == "geval":
        prompt_text = generate_geval_judge_prompt(rubric, agent_name=agent_name, agent_description=agent_desc)
    else:
        prompt_text = generate_judge_prompt(rubric, agent_name=agent_name, agent_description=agent_desc)

    Path(output).write_text(f"# Judge Prompt — {agent_name}\n\n{prompt_text}\n")

    click.echo(f"\nGenerating judge for: {agent_name}")
    click.echo(f"  Style : {style}")
    click.echo(f"\n  Criteria:")
    for c in rubric.criteria:
        click.echo(f"    • {c.name:<22} weight {c.weight}")
    click.echo(f"\n  Error codes mapped:")
    for code, count in codes.most_common():
        click.echo(f"    {code:<30} ×{count}  → {_infer_dimension(code)}")
    click.echo(f"\n  Saved → {output}  ({len(rubric.criteria)} criteria, {len(prompt_text)} chars)")
    click.echo("  Next: run `grounded-evals export --format jsonl` to export the dataset.")


@main.command()
@click.option("--session", "-s", default="session.json", show_default=True,
              help="Session file with annotations")
@click.option("--llm", is_flag=True,
              help="Use LLM for richer dimension mapping with rationale (requires credentials)")
@click.option("--output", "-o", default=None,
              help="Save analysis JSON to this file")
def analyze(session: str, llm: bool, output: str | None) -> None:
    """Map error codes from annotations to the 8 standard evaluation dimensions.

    \b
    Dimensions: quality · accuracy · completeness · tone · safety
                instruction_following · brand_relevance · bias

    Run after `annotate`. Results saved to session.json and used by `judge`.
    Use --llm for richer analysis with LLM-generated rationale per code.
    """
    from collections import Counter

    state, messages = _load_state(session)
    annotations = state.annotations

    if not annotations:
        click.echo("No annotations found. Run `grounded-evals annotate` first.", err=True)
        sys.exit(1)

    error_counts = Counter(a["error_code"] for a in annotations if a.get("error_code"))
    if not error_counts:
        click.echo(f"No error codes in {len(annotations)} annotations — all responses were correct.")
        return

    click.echo(f"\nError Analysis — {len(error_counts)} unique codes, {sum(error_counts.values())} failures\n")

    if llm:
        from grounded_evals.axial_coding.mapper import map_errors_to_categories
        from grounded_evals.models.core import Code, CodeType

        click.echo("Running LLM-based mapping...", err=True)
        code_objects = [
            Code(label=code, code_type=CodeType.DESCRIPTIVE,
                 definition=f"Observed {error_counts[code]}× in human annotations")
            for code in error_counts
        ]
        mappings = map_errors_to_categories(code_objects)
        max_w = max(len(m.error_code) for m in mappings)
        click.echo(f"  {'Error Code':<{max_w}}  Count  {'Dimension':<22}  Rationale")
        click.echo(f"  {'─' * max_w}  ─────  {'─' * 22}  {'─' * 30}")
        for m in sorted(mappings, key=lambda x: -error_counts.get(x.error_code, 0)):
            n = error_counts.get(m.error_code, 0)
            click.echo(f"  {m.error_code:<{max_w}}  ×{n:<4}  {m.primary_category:<22}  {m.rationale[:50]}")
        from grounded_evals.models.core import Code, CodeType
        state.session.codes = [
            Code(label=m.error_code, code_type=CodeType.DESCRIPTIVE, definition=m.rationale)
            for m in mappings
        ]
    else:
        max_w = max(len(c) for c in error_counts)
        click.echo(f"  {'Error Code':<{max_w}}  Count  Dimension")
        click.echo(f"  {'─' * max_w}  ─────  ──────────────────────")
        for code, n in error_counts.most_common():
            click.echo(f"  {code:<{max_w}}  ×{n:<4}  {_infer_dimension(code)}")
        click.echo("\n  Tip: use --llm for richer mapping with rationale per code")
        from grounded_evals.models.core import Code, CodeType
        state.session.codes = [
            Code(label=code, code_type=CodeType.DESCRIPTIVE)
            for code in error_counts
        ]

    _save_state(session, state, messages)
    click.echo(f"\n  Saved {len(state.session.codes)} codes to {session}")
    click.echo("  Run `grounded-evals judge` to generate your judge prompt.")

    if output:
        result = {
            "error_codes": dict(error_counts),
            "mappings": [
                {"error_code": c.label, "dimension": _infer_dimension(c.label), "definition": c.definition}
                for c in state.session.codes
            ],
        }
        Path(output).write_text(json.dumps(result, indent=2))
        click.echo(f"  Analysis saved → {output}")


@main.command("mlflow")
@click.option("--session", "-s", default="session.json", show_default=True)
@click.option("--results", "-r", default="eval_results.json", show_default=True)
@click.option("--experiment", "-e", default=None,
              help="MLflow experiment name (default: gedd-<agent_name>)")
@click.option("--tracking-uri", "-t", default=None,
              help="MLflow tracking URI or SageMaker ARN (default: env MLFLOW_TRACKING_URI)")
@click.option("--run-eval", is_flag=True,
              help="Run evaluation against the agent via Bedrock")
def mlflow_export(session: str, results: str, experiment: str | None,
                  tracking_uri: str | None, run_eval: bool) -> None:
    """Export GEDD session to MLflow/SageMaker — judges, dataset, and eval pipeline.

    \b
    Two-persona workflow:
      Domain Expert: runs /gedd skill → produces session.json
      ML Engineer:   runs this command → creates MLflow eval pipeline

    \b
    Creates in MLflow:
      - Experiment with GEDD metadata and agent lineage
      - Custom LLM judges from domain expert's error codes
      - Evaluation dataset from golden queries
      - Human feedback baseline from annotations

    \b
    SageMaker integration:
      pip install sagemaker-mlflow
      grounded-evals mlflow --tracking-uri arn:aws:sagemaker:us-east-1:ACCT:mlflow/SERVER

    Requires: pip install mlflow>=3.0 (+ sagemaker-mlflow for AWS)
    """
    try:
        import mlflow
        from mlflow.genai.judges import make_judge
    except ImportError:
        click.echo("MLflow not installed. Run: pip install 'mlflow>=3.0'", err=True)
        sys.exit(1)

    # ── 0. Connect to tracking server ──
    uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI", "")
    if uri:
        is_sagemaker = uri.startswith("arn:aws:sagemaker")
        if is_sagemaker:
            try:
                import sagemaker_mlflow  # noqa: F401
            except ImportError:
                click.echo(
                    "SageMaker MLflow plugin required for ARN tracking URIs.\n"
                    "  Run: pip install sagemaker-mlflow", err=True)
                sys.exit(1)
        mlflow.set_tracking_uri(uri)
        click.echo(f"\n  Tracking: {'SageMaker' if is_sagemaker else 'MLflow'} @ {uri[:60]}...")
    else:
        click.echo("\n  Tracking: local (set --tracking-uri or MLFLOW_TRACKING_URI for remote)")

    state, _ = _load_state(session)
    agent_name = state.session.agent_spec.name or "agent"
    exp_name = experiment or f"gedd-{agent_name.lower().replace(' ', '-')}"

    # ── 1. Create/set experiment ──
    mlflow.set_experiment(exp_name)
    click.echo(f"  Experiment: {exp_name}")

    # ── 2. Build eval dataset from golden queries ──
    prompts = state.session.golden_prompts
    if not prompts:
        click.echo("  No golden queries. Run the GEDD workflow first.", err=True)
        sys.exit(1)

    eval_dataset = [
        {
            "inputs": {"messages": [{"role": "user", "content": p.prompt_text}]},
            "expectations": {
                "expected_behavior": p.expected_behavior,
                "category": p.rationale,
                "is_adversarial": p.is_adversarial,
            },
        }
        for p in prompts
    ]
    click.echo(f"  Dataset: {len(eval_dataset)} test cases")

    # ── 3. Build custom judges from error codes ──
    from collections import Counter
    annotations = list(state.annotations)

    rpath = Path(results)
    if rpath.exists():
        for r in json.loads(rpath.read_text()):
            if r.get("error_code"):
                annotations.append(r)

    error_counts = Counter(a.get("error_code") for a in annotations if a.get("error_code"))
    dimensions: dict[str, list[str]] = {}
    for code in error_counts:
        dim = _infer_dimension(code)
        dimensions.setdefault(dim, []).append(code)

    judges = []
    for dim, codes in dimensions.items():
        codes_str = ", ".join(codes)
        judge = make_judge(
            name=f"gedd_{dim}",
            instructions=(
                f"You are evaluating an AI agent called {agent_name}.\n\n"
                f"Evaluate the {dim} dimension of the agent's response.\n"
                f"Known failure patterns: {codes_str}\n\n"
                f"User's message: {{{{ inputs }}}}\n"
                f"Agent's response: {{{{ outputs }}}}\n"
                f"Expected behavior: {{{{ expectations }}}}\n\n"
                f"Score 1-5 on {dim}. Deduct points if these failure patterns "
                f"({codes_str}) are present.\n"
                f"5=Excellent, 4=Good, 3=Acceptable, 2=Poor, 1=Failing"
            ),
            feedback_value_type=int,
        )
        judges.append(judge)
        click.echo(f"  Judge: gedd_{dim} (patterns: {codes_str})")

    overall_judge = make_judge(
        name="gedd_correctness",
        instructions=(
            f"You are evaluating {agent_name}.\n\n"
            f"User's message: {{{{ inputs }}}}\n"
            f"Agent's response: {{{{ outputs }}}}\n"
            f"Expected behavior: {{{{ expectations }}}}\n\n"
            f"Is the response correct, partially correct, or incorrect?"
        ),
        feedback_value_type=bool,
    )
    judges.append(overall_judge)
    click.echo(f"  Judge: gedd_correctness")
    click.echo(f"  Total: {len(judges)} judges")

    # ── 4. Log to MLflow ──
    with mlflow.start_run(run_name="gedd-pipeline-export") as run:
        mlflow.log_params({
            "agent_name": agent_name,
            "domain": state.session.agent_spec.domain_context or "general",
            "system_prompt_chars": len(state.session.agent_spec.system_prompt),
            "total_queries": len(prompts),
            "total_annotations": len(state.annotations),
            "error_codes": json.dumps(dict(error_counts)),
            "dimensions": json.dumps(list(dimensions.keys())),
            "source": "gedd",
        })

        # Log metrics from human annotations
        if state.annotations:
            correct = sum(1 for a in state.annotations if a.get("annotation") == "correct")
            total = len(state.annotations)
            mlflow.log_metrics({
                "human_tsr": correct / total if total else 0,
                "human_annotations": total,
                "error_code_count": len(error_counts),
                "categories_covered": len(set(p.rationale for p in prompts)),
            })

        # Log artifacts
        dataset_path = Path("gedd_eval_dataset.json")
        dataset_path.write_text(json.dumps(eval_dataset, indent=2))
        mlflow.log_artifact(str(dataset_path))
        dataset_path.unlink()

        judge_path = Path("judge_prompt.md")
        if judge_path.exists():
            mlflow.log_artifact(str(judge_path))

        session_path = Path(session)
        if session_path.exists():
            mlflow.log_artifact(str(session_path))

        click.echo(f"\n  Run ID: {run.info.run_id}")

    # ── 5. Run evaluation if requested ──
    if run_eval:
        click.echo("\n  Running evaluation pipeline...")
        from grounded_evals.llm.client import get_default_client, get_model_id, traced_eval_call

        system_prompt = state.session.agent_spec.system_prompt
        if not system_prompt:
            click.echo("  No system prompt. Cannot run eval.", err=True)
            sys.exit(1)

        client = get_default_client()
        model_id = get_model_id()

        def predict_fn(inputs: dict) -> dict:
            messages = inputs.get("messages", [])
            query = messages[-1]["content"] if messages else ""
            resp = traced_eval_call(client, model_id, system_prompt, query)
            return {"messages": [{"role": "assistant", "content": resp.content[0].text}]}

        eval_result = mlflow.genai.evaluate(
            data=eval_dataset,
            predict_fn=predict_fn,
            scorers=judges,
        )
        click.echo("  ✓ Evaluation complete — results logged to MLflow")
    else:
        click.echo(f"\n  To run eval: grounded-evals mlflow -s {session} --run-eval")

    # ── 6. Summary ──
    click.echo(f"\n  {'━' * 50}")
    click.echo(f"  ✓ GEDD → MLflow pipeline ready")
    click.echo(f"  {'━' * 50}")
    click.echo(f"  Experiment : {exp_name}")
    click.echo(f"  Dataset    : {len(eval_dataset)} golden queries")
    click.echo(f"  Judges     : {len(judges)} custom scorers")
    click.echo(f"  Annotations: {len(state.annotations)} human labels")
    if uri and uri.startswith("arn:aws:sagemaker"):
        click.echo(f"  Backend    : Amazon SageMaker Managed MLflow")
    click.echo(f"\n  ML Engineer next steps:")
    click.echo(f"    1. mlflow ui                    # view experiment")
    click.echo(f"    2. Add to CI: grounded-evals mlflow -s {session} --run-eval")
    click.echo(f"    3. Set regression gate: TSR ≥ 95% on happy_path")
    click.echo(f"    4. Monitor judge-human agreement (target κ ≥ 0.80)")
    click.echo()


if __name__ == "__main__":
    main()
