"""Integration tests for the grounded-evals CLI.

These tests cover the parsing/serialization paths that previously shipped
broken (Pydantic UUID validation, CoverageReport attribute access, Dimension
serialization). LLM-backed commands (fracture, compare) are not exercised
end-to-end here — those require Bedrock credentials and are smoke-tested
manually.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from click.testing import CliRunner

from grounded_evals.agent.tools import StateBundle
from grounded_evals.cli import main
from grounded_evals.guide.session import Session
from grounded_evals.guide.session_io import save_session_state
from grounded_evals.models.core import GoldenPrompt


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows))


def test_coverage_basic(tmp_path: Path) -> None:
    dataset = tmp_path / "ds.jsonl"
    _write_jsonl(dataset, [
        {"prompt": "p1", "category": "happy"},
        {"prompt": "p2", "category": "happy"},
        {"prompt": "p3", "category": "happy"},
        {"prompt": "p4", "category": "edge"},
    ])
    runner = CliRunner()
    result = runner.invoke(main, ["coverage", "-d", str(dataset)])
    assert result.exit_code == 0, result.output
    assert "happy" in result.output
    assert "edge" in result.output
    assert "saturated" in result.output


def test_coverage_handles_missing_category_field(tmp_path: Path) -> None:
    dataset = tmp_path / "ds.jsonl"
    _write_jsonl(dataset, [
        {"prompt": "p1"},
        {"prompt": "p2", "rationale": "edge"},
    ])
    runner = CliRunner()
    result = runner.invoke(main, ["coverage", "-d", str(dataset)])
    assert result.exit_code == 0, result.output
    assert "uncategorized" in result.output


def test_check_saturation_inferred_categories(tmp_path: Path) -> None:
    """Regression test for the UUID + CoverageReport attribute bugs."""
    dataset = tmp_path / "ds.jsonl"
    _write_jsonl(dataset, [
        {"prompt": "p1", "category": "happy"},
        {"prompt": "p2", "category": "happy"},
        {"prompt": "p3", "category": "happy"},
        {"prompt": "p4", "category": "edge"},
        {"prompt": "p5", "category": "edge"},
        {"prompt": "p6", "category": "advers"},
    ])
    runner = CliRunner()
    result = runner.invoke(main, ["check-saturation", "-d", str(dataset)])
    # Exit 1 is the correct "not saturated" signal — only 1/3 categories saturated.
    assert result.exit_code == 1, result.output
    assert "Saturated" in result.output
    assert "Approaching" in result.output
    assert "Unsaturated" in result.output
    assert "Coverage" in result.output
    # Should NOT crash with AttributeError or pydantic ValidationError.
    assert "Traceback" not in result.output


def test_check_saturation_all_saturated_exits_zero(tmp_path: Path) -> None:
    dataset = tmp_path / "ds.jsonl"
    _write_jsonl(dataset, [
        {"prompt": f"p{i}", "category": "happy"} for i in range(3)
    ])
    runner = CliRunner()
    result = runner.invoke(main, ["check-saturation", "-d", str(dataset)])
    assert result.exit_code == 0, result.output
    assert "SATURATED" in result.output


def test_check_saturation_with_explicit_categories_file(tmp_path: Path) -> None:
    dataset = tmp_path / "ds.jsonl"
    cats_file = tmp_path / "cats.json"
    _write_jsonl(dataset, [
        {"prompt": "p1", "category": "happy"},
        {"prompt": "p2", "category": "happy"},
        {"prompt": "p3", "category": "happy"},
    ])
    cats_file.write_text(json.dumps([
        {"name": "happy", "definition": "happy path"},
        {"name": "edge", "definition": "edge case"},
    ]))
    runner = CliRunner()
    result = runner.invoke(main, [
        "check-saturation", "-d", str(dataset), "-c", str(cats_file)
    ])
    # 1 of 2 categories saturated → 50% → not saturated, exit 1.
    assert result.exit_code == 1, result.output
    assert "Saturated      : 1" in result.output


def test_compare_passes_pydantic_validation(tmp_path: Path, monkeypatch) -> None:
    """Regression: GoldenPrompt previously got built without category_id."""
    dataset = tmp_path / "ds.jsonl"
    _write_jsonl(dataset, [
        {"prompt": "Find me a flight", "category": "happy"},
        {"prompt": "Cancel booking", "category": "happy"},
    ])

    # Stub out the LLM call so we test only the parse path.
    from grounded_evals.models.core import GoldenPrompt  # noqa: F401  (kept for clarity)
    from grounded_evals.open_coding import compare as compare_mod

    def fake_constant_comparison(new_prompt, existing, cats):
        from grounded_evals.open_coding.compare import ComparisonResult
        # Confirm the loader actually built valid GoldenPrompt objects.
        assert all(p.category_id is not None for p in existing)
        assert all(p.prompt_text for p in existing)
        return ComparisonResult(
            is_unique=True,
            similar_existing=[],
            gaps_filled=["new domain"],
            suggestions=["try X"],
            explanation="fresh angle",
        )

    monkeypatch.setattr(compare_mod, "constant_comparison", fake_constant_comparison)

    runner = CliRunner()
    result = runner.invoke(main, [
        "compare", "-d", str(dataset), "-p", "Book a hotel"
    ])
    assert result.exit_code == 0, result.output
    assert "YES" in result.output
    assert "fresh angle" in result.output


def test_fracture_serializes_dimensions(tmp_path: Path, monkeypatch) -> None:
    """Regression: Dimension Pydantic objects must be JSON-serializable in output."""
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(
        "agent:\n"
        "  name: TestBot\n"
        "  description: Test\n"
        "  capabilities:\n"
        "    - Lookup\n"
    )
    out_file = tmp_path / "out.json"

    from grounded_evals.models.core import Category, Dimension, Property
    from grounded_evals.open_coding import fracture as fracture_mod

    def fake_fracture_domain(spec):
        # Confirm parser flattened the agent: namespace correctly.
        assert spec.name == "TestBot"
        return [
            Category(
                name="Cat1",
                definition="d1",
                properties=[
                    Property(
                        name="prop1",
                        dimensions=[
                            Dimension(name="dim1", low_anchor="lo", high_anchor="hi"),
                        ],
                    )
                ],
            )
        ]

    monkeypatch.setattr(fracture_mod, "fracture_domain", fake_fracture_domain)

    runner = CliRunner()
    result = runner.invoke(main, [
        "fracture", "-s", str(spec_file), "-o", str(out_file)
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(out_file.read_text())
    assert payload[0]["name"] == "Cat1"
    assert payload[0]["properties"][0]["dimensions"][0]["low_anchor"] == "lo"


def test_cli_happy_path_handoff_without_llm(tmp_path: Path) -> None:
    """Exercise session -> export -> judge -> validate -> handoff without LLM calls."""
    session_file = tmp_path / "session.json"
    export_file = tmp_path / "golden.jsonl"
    judge_file = tmp_path / "judge.md"
    handoff_file = tmp_path / "handoff.json"

    session = Session()
    session.update_agent(
        name="SupportBot",
        description="Answers customer support questions.",
        system_prompt="You are a support assistant. Escalate safety issues.",
    )
    categories = ["happy_path", "edge_case", "adversarial"]
    for i in range(15):
        session.add_golden_prompt(
            GoldenPrompt(
                prompt_text=f"Query {i}",
                category_id=uuid4(),
                rationale=categories[i % len(categories)],
                expected_behavior=f"Expected behavior {i}",
            )
        )

    state = StateBundle(
        session=session,
        annotations=[
            {
                "query": "Query 0",
                "response": "Wrong answer",
                "annotation": "incorrect",
                "error_code": "safety_escalation_miss",
                "notes": "Did not escalate.",
            },
            {
                "query": "Query 1",
                "response": "Correct answer",
                "annotation": "correct",
                "error_code": "",
                "notes": "",
            },
        ],
        current_step=5,
    )
    save_session_state(session_file, state, messages=[])

    runner = CliRunner()

    result = runner.invoke(
        main,
        ["export", "-s", str(session_file), "-f", "jsonl", "-o", str(export_file)],
    )
    assert result.exit_code == 0, result.output
    assert len(export_file.read_text().strip().splitlines()) == 15

    result = runner.invoke(main, ["judge", "-s", str(session_file), "-o", str(judge_file)])
    assert result.exit_code == 0, result.output
    assert "Safety" in judge_file.read_text()

    result = runner.invoke(main, ["validate-session", "-s", str(session_file)])
    assert result.exit_code == 0, result.output
    assert "Ready for handoff" in result.output

    result = runner.invoke(main, ["handoff", "-s", str(session_file), "-o", str(handoff_file)])
    assert result.exit_code == 0, result.output
    payload = json.loads(handoff_file.read_text())
    assert payload["schema_version"] == 1
    assert payload["handoff_validation"]["errors"] == []
    assert payload["session"]["agent_spec"]["name"] == "SupportBot"
