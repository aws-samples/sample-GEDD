import click


@click.group()
def main() -> None:
    """grounded-evals: Open Coding guided workflow for AI Agent golden dataset generation."""


@main.command()
@click.option("--agent-spec", "-a", required=True, type=click.Path(exists=True),
              help="Agent specification YAML file")
def guide(agent_spec: str) -> None:
    """Start interactive session guiding PM through Open Coding workflow."""
    click.echo(f"Starting guided session for agent spec: {agent_spec}")


@main.command()
@click.option("--dataset", "-d", required=True, type=click.Path(exists=True),
              help="Golden dataset JSONL file")
def check_saturation(dataset: str) -> None:
    """Analyze whether the golden dataset has reached theoretical saturation."""
    click.echo(f"Checking saturation for: {dataset}")


@main.command()
@click.option("--dataset", "-d", required=True, type=click.Path(exists=True),
              help="Golden dataset JSONL file")
def coverage(dataset: str) -> None:
    """Generate coverage report showing gaps and redundancies."""
    click.echo(f"Coverage report for: {dataset}")


@main.command()
@click.option("--input", "-i", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", required=True, type=click.Path())
def fracture(input: str, output: str) -> None:
    """Fracture agent domain into prompt categories with properties/dimensions."""
    click.echo(f"Fracturing domain: {input}")


@main.command()
@click.option("--dataset", "-d", required=True, type=click.Path(exists=True))
@click.option("--new-prompt", "-p", required=True)
def compare(dataset: str, new_prompt: str) -> None:
    """Run constant comparison on a new prompt against existing dataset."""
    click.echo(f"Comparing new prompt against: {dataset}")


if __name__ == "__main__":
    main()
