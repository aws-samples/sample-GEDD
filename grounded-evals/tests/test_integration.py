"""Functional/integration tests — end-to-end pipeline workflows.

Tests the full flow from agent spec → fracture → compare → saturation → rubric → judge prompt,
with LLM calls mocked at the boundary.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from grounded_evals.axial_coding.mapper import ErrorMapping
from grounded_evals.cli import main
from grounded_evals.guide.session import Session
from grounded_evals.ingest.models import AgentSpec, Capability, Persona
from grounded_evals.ingest.parser import parse_agent_spec
from grounded_evals.judge_builder.calibrate import CalibrationResult, calibrate
from grounded_evals.judge_builder.few_shot import select_exemplars
from grounded_evals.judge_builder.prompt_gen import (
    generate_few_shot_judge_prompt,
    generate_geval_judge_prompt,
    generate_judge_prompt,
)
from grounded_evals.judge_builder.rubric import generate_rubric
from grounded_evals.models.core import (
    Category,
    Code,
    CodeType,
    GoldenDataset,
    GoldenPrompt,
    SaturationStatus,
)
from grounded_evals.open_coding.saturation import (
    check_category_saturation,
    check_overall_saturation,
)

# ── Full pipeline: spec → session → coverage ──────────────────────────────────


def test_full_session_workflow():
    """Integration: create session, add categories/prompts, check coverage."""
    session = Session()
    session.update_agent(name="SupportBot", description="Customer support")

    # Add categories
    cats = [
        Category(name="Happy Path", definition="Normal queries"),
        Category(name="Edge Case", definition="Boundary conditions"),
        Category(name="Adversarial", definition="Attack attempts"),
    ]
    for cat in cats:
        session.add_category(cat)

    # Add prompts to saturate first category
    for i in range(3):
        session.add_golden_prompt(
            GoldenPrompt(prompt_text=f"Normal query {i}", category_id=cats[0].id)
        )
    # Add one prompt to second category
    session.add_golden_prompt(GoldenPrompt(prompt_text="Edge query", category_id=cats[1].id))

    # Check coverage
    report = session.coverage()
    assert report.total_prompts == 4
    assert report.categories_covered == 2
    assert report.categories_total == 3
    assert len(report.gaps) == 1  # Adversarial has no prompts

    # Export to golden dataset
    ds = session.to_golden_dataset()
    assert ds.agent_name == "SupportBot"
    assert len(ds.prompts) == 4


# ── Pipeline: error mappings → rubric → judge prompt ──────────────────────────


def test_rubric_to_judge_prompt_pipeline():
    """Integration: error mappings → rubric → all 3 judge prompt modes."""
    mappings = [
        ErrorMapping(error_code="hallucination", primary_category="accuracy"),
        ErrorMapping(error_code="policy_fabrication", primary_category="accuracy"),
        ErrorMapping(error_code="rude_tone", primary_category="tone"),
        ErrorMapping(error_code="unsafe_content", primary_category="safety"),
    ]
    rubric = generate_rubric(mappings)

    # Standard prompt
    standard = generate_judge_prompt(rubric, agent_name="TestBot")
    assert "TestBot" in standard
    assert "accuracy" in standard.lower()

    # G-EVAL prompt
    geval = generate_geval_judge_prompt(rubric, agent_name="TestBot")
    assert "Step-by-Step" in geval

    # Few-shot prompt (with exemplars)
    codebook = [{"name": "hallucination"}, {"name": "rude_tone"}]
    annotations = [
        {
            "query": "q1",
            "response": "r1",
            "codes": ["hallucination"],
            "severity": "critical",
            "confidence": "high",
            "memo": "Invented policy",
        },
        {
            "query": "q2",
            "response": "r2",
            "codes": [],
            "severity": "cosmetic",
            "confidence": "high",
            "memo": "",
        },
    ]
    exemplars = select_exemplars(annotations, codebook)
    few_shot = generate_few_shot_judge_prompt(rubric, exemplars, agent_name="TestBot")
    assert "Reference Examples" in few_shot


# ── Pipeline: saturation check with real data ─────────────────────────────────


def test_saturation_pipeline():
    """Integration: categories + prompts → saturation analysis."""
    cats = [Category(name=f"Cat{i}") for i in range(4)]
    prompts = []
    # Saturate first 2 categories
    for cat in cats[:2]:
        for j in range(3):
            prompts.append(GoldenPrompt(prompt_text=f"p{j}", category_id=cat.id))
    # Partially fill third
    prompts.append(GoldenPrompt(prompt_text="p", category_id=cats[2].id))

    report = check_overall_saturation(cats, prompts)
    assert report.saturated_categories == 2
    assert report.categories_covered == 3
    assert report.saturation_score == 0.5
    assert len(report.gaps) == 1  # Cat3 has no prompts


# ── Pipeline: calibration with realistic scores ───────────────────────────────


def test_calibration_pipeline_multi_criterion():
    """Integration: multi-criterion calibration with kappa metrics."""
    manual = [
        {"accuracy": 5, "tone": 4, "safety": 5},
        {"accuracy": 3, "tone": 5, "safety": 4},
        {"accuracy": 2, "tone": 3, "safety": 5},
        {"accuracy": 4, "tone": 4, "safety": 5},
    ]
    judge = [
        {"accuracy": 5, "tone": 4, "safety": 5},  # perfect
        {"accuracy": 4, "tone": 5, "safety": 4},  # within 1
        {"accuracy": 4, "tone": 3, "safety": 5},  # accuracy off by 2
        {"accuracy": 4, "tone": 4, "safety": 5},  # perfect
    ]
    result = calibrate(manual, judge)
    assert result.total_compared == 12
    assert result.exact_matches >= 8
    assert result.weighted_kappa > 0.0
    assert result.weakest_criterion != ""
    assert result.recommendation != ""


# ── CLI integration: coverage command with varied data ────────────────────────


def test_cli_coverage_multiple_categories(tmp_path):
    dataset = tmp_path / "ds.jsonl"
    rows = (
        [{"prompt": f"p{i}", "category": "happy"} for i in range(5)]
        + [{"prompt": f"e{i}", "category": "edge"} for i in range(2)]
        + [
            {"prompt": "a1", "category": "adversarial"},
        ]
    )
    dataset.write_text("\n".join(json.dumps(r) for r in rows))

    runner = CliRunner()
    result = runner.invoke(main, ["coverage", "-d", str(dataset)])
    assert result.exit_code == 0
    assert "happy" in result.output
    assert "edge" in result.output
    assert "adversarial" in result.output
    assert "saturated" in result.output


# ── CLI integration: check-saturation with threshold behavior ─────────────────


def test_cli_saturation_threshold_behavior(tmp_path):
    """80% saturation → exit 0, below → exit 1."""
    dataset = tmp_path / "ds.jsonl"
    # 4 categories, 3 saturated (75%) → not saturated
    rows = []
    for cat in ["a", "b", "c"]:
        rows.extend([{"prompt": f"{cat}{i}", "category": cat} for i in range(3)])
    rows.append({"prompt": "d1", "category": "d"})
    dataset.write_text("\n".join(json.dumps(r) for r in rows))

    runner = CliRunner()
    result = runner.invoke(main, ["check-saturation", "-d", str(dataset)])
    assert result.exit_code == 1  # 75% < 80%


# ── Agent spec parsing integration ───────────────────────────────────────────


def test_parse_complex_agent_spec(tmp_path):
    spec_yaml = tmp_path / "spec.yaml"
    spec_yaml.write_text("""
agent:
  name: FinanceBot
  description: Handles financial queries
  capabilities:
    - name: Balance inquiry
      description: Check account balance
    - name: Transfer funds
      description: Move money between accounts
  target_users:
    - name: Retail customer
      description: Individual account holder
    - name: Business customer
      description: Corporate account manager
  known_edge_cases:
    - Negative balance
    - International transfer
    - Closed account
  constraints:
    - Never reveal full account numbers
    - Always verify identity first
  domain_context: Banking and finance
  system_prompt: You are a helpful banking assistant.
""")
    spec = parse_agent_spec(spec_yaml)
    assert spec.name == "FinanceBot"
    assert len(spec.capabilities) == 2
    assert spec.capabilities[0].description == "Check account balance"
    assert len(spec.target_users) == 2
    assert len(spec.known_edge_cases) == 3
    assert len(spec.constraints) == 2
    assert spec.system_prompt == "You are a helpful banking assistant."


# ── Golden dataset serialization roundtrip ────────────────────────────────────


def test_golden_dataset_json_roundtrip():
    cat = Category(name="Test", definition="Testing")
    gp = GoldenPrompt(prompt_text="Hello", category_id=cat.id, is_edge_case=True)
    ds = GoldenDataset(
        agent_name="Bot",
        agent_description="A bot",
        prompts=[gp],
        categories=[cat],
    )
    # Serialize to JSON and back
    json_str = ds.model_dump_json()
    restored = GoldenDataset.model_validate_json(json_str)
    assert restored.agent_name == "Bot"
    assert restored.prompts[0].prompt_text == "Hello"
    assert restored.prompts[0].is_edge_case is True
    assert restored.categories[0].id == cat.id
