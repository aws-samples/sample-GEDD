"""Edge case and error handling tests — boundary conditions, invalid inputs, error paths."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from click.testing import CliRunner

from grounded_evals.axial_coding.mapper import ErrorMapping
from grounded_evals.cli import main
from grounded_evals.guide.session import Session
from grounded_evals.ingest.models import AgentSpec
from grounded_evals.ingest.parser import parse_agent_spec
from grounded_evals.judge_builder.calibrate import calibrate
from grounded_evals.judge_builder.ensemble import (
    EnsembleResult,
    _parse_judge_response,
    ensemble_judge,
)
from grounded_evals.judge_builder.few_shot import select_exemplars
from grounded_evals.judge_builder.rubric import generate_rubric
from grounded_evals.models.core import (
    Category,
    Code,
    CodeType,
    CoverageReport,
    GoldenPrompt,
    SaturationStatus,
)
from grounded_evals.open_coding.saturation import (
    check_category_saturation,
    check_overall_saturation,
    saturation_recommendation,
)

# ── Models edge cases ─────────────────────────────────────────────────────────


def test_golden_prompt_empty_text():
    """Empty prompt text is technically valid (no min_length constraint)."""
    gp = GoldenPrompt(prompt_text="", category_id=uuid4())
    assert gp.prompt_text == ""


def test_golden_prompt_very_long_text():
    gp = GoldenPrompt(prompt_text="x" * 10000, category_id=uuid4())
    assert len(gp.prompt_text) == 10000


def test_category_duplicate_code_ids():
    """Category can have duplicate code_ids (no uniqueness constraint)."""
    uid = uuid4()
    cat = Category(name="Test", code_ids=[uid, uid])
    assert len(cat.code_ids) == 2


def test_coverage_report_zero_division():
    """CoverageReport with 0 categories should not crash."""
    cr = CoverageReport(categories_total=0, saturation_score=0.0)
    assert cr.saturation_score == 0.0


# ── Saturation edge cases ────────────────────────────────────────────────────


def test_saturation_single_category_many_prompts():
    cat = Category(name="Only")
    prompts = [GoldenPrompt(prompt_text=f"p{i}", category_id=cat.id) for i in range(100)]
    status = check_category_saturation(cat, prompts)
    assert status == SaturationStatus.SATURATED


def test_saturation_prompts_for_wrong_category():
    cat = Category(name="Target")
    other_id = uuid4()
    prompts = [GoldenPrompt(prompt_text=f"p{i}", category_id=other_id) for i in range(10)]
    status = check_category_saturation(cat, prompts)
    assert status == SaturationStatus.UNSATURATED


def test_overall_saturation_redundancy_detection():
    cat = Category(name="Overloaded")
    # More than SATURATED_THRESHOLD * 2 = 6 prompts → redundancy
    prompts = [GoldenPrompt(prompt_text=f"p{i}", category_id=cat.id) for i in range(7)]
    report = check_overall_saturation([cat], prompts)
    assert len(report.redundancies) == 1
    assert "Overloaded" in report.redundancies[0]


def test_saturation_recommendation_partial():
    cats = [Category(name=f"C{i}") for i in range(4)]
    prompts = []
    for cat in cats[:2]:
        prompts.extend([GoldenPrompt(prompt_text=f"p{i}", category_id=cat.id) for i in range(3)])
    report = check_overall_saturation(cats, prompts)
    rec = saturation_recommendation(report)
    assert "Good progress" in rec


# ── Calibration edge cases ────────────────────────────────────────────────────


def test_calibrate_single_score():
    manual = [{"accuracy": 3}]
    judge = [{"accuracy": 3}]
    result = calibrate(manual, judge)
    assert result.exact_matches == 1
    assert result.agreement_score == 1.0


def test_calibrate_mismatched_keys():
    """Judge missing a key that manual has → skip that key."""
    manual = [{"accuracy": 5, "tone": 4}]
    judge = [{"accuracy": 5}]  # missing tone
    result = calibrate(manual, judge)
    assert result.total_compared == 1  # only accuracy compared


def test_calibrate_extreme_disagreement():
    manual = [{"accuracy": 5}] * 10
    judge = [{"accuracy": 1}] * 10
    result = calibrate(manual, judge)
    assert result.agreement_score == 0.0
    assert len(result.disagreements) > 0
    assert result.weighted_kappa < 0.5


def test_calibrate_all_same_scores():
    """When all scores are identical, kappa may be undefined (p_e = 1)."""
    manual = [{"accuracy": 5}] * 5
    judge = [{"accuracy": 5}] * 5
    result = calibrate(manual, judge)
    assert result.exact_matches == 5
    assert result.agreement_score == 1.0


# ── Ensemble edge cases ───────────────────────────────────────────────────────


def test_parse_judge_response_nested_json():
    """JSON embedded in prose with extra text."""
    text = 'Let me analyze this.\n\nBased on my review:\n{"pass": true, "scores": {"x": 4}}\n\nThat is my verdict.'
    result = _parse_judge_response(text)
    assert result["pass"] is True


def test_parse_judge_response_multiple_json_objects():
    """Should find the outermost JSON object."""
    text = 'Here: {"inner": {"nested": true}, "pass": false}'
    result = _parse_judge_response(text)
    assert result["pass"] is False


def test_ensemble_judge_partial_failures():
    """Some samples fail, others succeed → still produces result."""
    responses = [
        json.dumps({"scores": {"accuracy": 4}, "pass": True, "summary": "OK"}),
    ]
    client = MagicMock()
    call_count = [0]

    def side_effect(**kwargs):
        call_count[0] += 1
        if call_count[0] <= 2:
            raise RuntimeError("API error")
        msg = MagicMock()
        msg.content = [MagicMock(text=responses[0])]
        return msg

    client.messages.create.side_effect = side_effect
    result = ensemble_judge("{query} {response}", "q", "r", client, "model", n_samples=3)
    # 2 failures + 1 success → should still produce a result
    assert result.pass_votes == 1


# ── Few-shot edge cases ───────────────────────────────────────────────────────


def test_select_exemplars_all_same_code():
    codebook = [{"name": "hallucination"}]
    annotations = [
        {
            "query": f"q{i}",
            "response": f"r{i}",
            "codes": ["hallucination"],
            "severity": "critical",
            "confidence": "high",
            "memo": "",
        }
        for i in range(10)
    ]
    result = select_exemplars(annotations, codebook, max_per_code=2, max_total=5)
    assert len(result.exemplars) <= 5


def test_select_exemplars_truncates_long_text():
    codebook = [{"name": "x"}]
    annotations = [
        {
            "query": "q" * 500,
            "response": "r" * 600,
            "codes": ["x"],
            "severity": "critical",
            "confidence": "high",
            "memo": "",
        },
    ]
    result = select_exemplars(annotations, codebook)
    for ex in result.exemplars:
        assert len(ex.query) <= 300
        assert len(ex.response) <= 400


# ── Parser edge cases ─────────────────────────────────────────────────────────


def test_parse_agent_spec_empty_file(tmp_path):
    f = tmp_path / "empty.yaml"
    f.write_text("")
    # yaml.safe_load returns None for empty file
    with pytest.raises((TypeError, AttributeError)):
        parse_agent_spec(f)


def test_parse_agent_spec_no_agent_key(tmp_path):
    f = tmp_path / "flat.yaml"
    f.write_text("name: DirectBot\ndescription: Direct format\n")
    spec = parse_agent_spec(f)
    assert spec.name == "DirectBot"


def test_parse_agent_spec_capabilities_as_strings(tmp_path):
    f = tmp_path / "strings.yaml"
    f.write_text("agent:\n  name: Bot\n  capabilities:\n    - Search\n    - Navigate\n")
    spec = parse_agent_spec(f)
    assert len(spec.capabilities) == 2
    assert spec.capabilities[0].name == "Search"


# ── CLI edge cases ────────────────────────────────────────────────────────────


def test_cli_coverage_empty_file(tmp_path):
    dataset = tmp_path / "empty.jsonl"
    dataset.write_text("")
    runner = CliRunner()
    result = runner.invoke(main, ["coverage", "-d", str(dataset)])
    assert result.exit_code == 0


def test_cli_coverage_blank_lines(tmp_path):
    dataset = tmp_path / "blanks.jsonl"
    dataset.write_text('\n\n{"prompt": "p1", "category": "a"}\n\n')
    runner = CliRunner()
    result = runner.invoke(main, ["coverage", "-d", str(dataset)])
    assert result.exit_code == 0
    assert "a" in result.output


def test_cli_saturation_single_prompt(tmp_path):
    dataset = tmp_path / "single.jsonl"
    dataset.write_text(json.dumps({"prompt": "p1", "category": "only"}))
    runner = CliRunner()
    result = runner.invoke(main, ["check-saturation", "-d", str(dataset)])
    assert result.exit_code == 1  # not saturated
    assert "NOT YET SATURATED" in result.output


# ── Rubric edge cases ─────────────────────────────────────────────────────────


def test_rubric_single_mapping():
    mappings = [ErrorMapping(error_code="x", primary_category="quality")]
    rubric = generate_rubric(mappings)
    assert len(rubric.criteria) == 1
    assert rubric.criteria[0].name == "Quality"


def test_rubric_many_errors_same_category():
    mappings = [
        ErrorMapping(error_code=f"error_{i}", primary_category="accuracy") for i in range(10)
    ]
    rubric = generate_rubric(mappings)
    assert len(rubric.criteria) == 1  # all grouped under accuracy
    assert "error_0" in rubric.criteria[0].description


def test_rubric_unknown_category_weight():
    mappings = [ErrorMapping(error_code="x", primary_category="unknown_dimension")]
    rubric = generate_rubric(mappings)
    assert rubric.criteria[0].weight == 1.0  # default weight


# ── Session edge cases ────────────────────────────────────────────────────────


def test_session_prompts_for_nonexistent_category():
    s = Session()
    result = s.prompts_for_category(uuid4())
    assert result == []


def test_session_coverage_no_categories():
    s = Session()
    s.add_golden_prompt(GoldenPrompt(prompt_text="orphan", category_id=uuid4()))
    report = s.coverage()
    assert report.total_prompts == 1
    assert report.categories_total == 0
    assert report.saturation_score == 0.0


# ── LLM config edge cases ────────────────────────────────────────────────────


def test_llm_config_both_env_vars(monkeypatch):
    """When both ANTHROPIC_API_KEY and AWS_REGION are set, Anthropic wins."""
    from grounded_evals.llm.client import LLMConfig

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    cfg = LLMConfig.from_env()
    assert cfg.provider == "anthropic"


def test_llm_config_yaml_overrides_env(tmp_path, monkeypatch):
    from grounded_evals.llm.client import LLMConfig

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "llm:\n  provider: bedrock\n  region: ap-southeast-1\n  model_id: custom-model\n"
    )
    cfg = LLMConfig.from_yaml(config_file)
    assert cfg.region == "ap-southeast-1"
    assert cfg.model_id == "custom-model"
