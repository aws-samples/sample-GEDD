"""CLI for grounded-evals — Open Coding guided workflow for AI agent evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click


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


if __name__ == "__main__":
    main()
