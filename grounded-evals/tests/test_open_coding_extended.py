"""Unit tests for open_coding/compare.py and open_coding/fracture.py."""

import json
from unittest.mock import MagicMock

import pytest

from grounded_evals.models.core import Category, GoldenPrompt
from grounded_evals.open_coding.compare import (
    CodeComparisonResult,
    ComparisonResult,
    compare_codes,
    constant_comparison,
)
from grounded_evals.open_coding.fracture import fracture_domain
from grounded_evals.ingest.models import AgentSpec, Capability


# ── ComparisonResult model ────────────────────────────────────────────────────

def test_comparison_result_defaults():
    r = ComparisonResult()
    assert r.is_unique is True
    assert r.similar_existing == []
    assert r.explanation == ""


# ── constant_comparison ───────────────────────────────────────────────────────

def test_constant_comparison_first_prompt():
    """First prompt is always unique."""
    result = constant_comparison("Hello world", [], [])
    assert result.is_unique is True
    assert "First prompt" in result.explanation


def test_constant_comparison_with_existing(monkeypatch):
    mock_response = json.dumps({
        "is_unique": False,
        "similar_existing": ["Find me a flight"],
        "gaps_filled": [],
        "suggestions": ["Try a cancellation query"],
        "explanation": "Very similar to existing flight query",
    })
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=mock_response)]
    mock_client.messages.create.return_value = msg

    monkeypatch.setattr("grounded_evals.open_coding.compare.get_default_client", lambda: mock_client)
    monkeypatch.setattr("grounded_evals.open_coding.compare.get_model_id", lambda: "test")

    from uuid import uuid4
    existing = [GoldenPrompt(prompt_text="Find me a flight", category_id=uuid4())]
    result = constant_comparison("Book a flight for me", existing, [])
    assert result.is_unique is False
    assert "Find me a flight" in result.similar_existing


def test_constant_comparison_parse_error(monkeypatch):
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text="Not JSON")]
    mock_client.messages.create.return_value = msg

    monkeypatch.setattr("grounded_evals.open_coding.compare.get_default_client", lambda: mock_client)
    monkeypatch.setattr("grounded_evals.open_coding.compare.get_model_id", lambda: "test")

    from uuid import uuid4
    existing = [GoldenPrompt(prompt_text="test", category_id=uuid4())]
    with pytest.raises(RuntimeError, match="failed to parse"):
        constant_comparison("new prompt", existing, [])


# ── CodeComparisonResult ──────────────────────────────────────────────────────

def test_code_comparison_result_defaults():
    r = CodeComparisonResult()
    assert r.is_duplicate is False
    assert r.similar_codes == []


# ── compare_codes ─────────────────────────────────────────────────────────────

def test_compare_codes_first_code():
    result = compare_codes("hallucination", [])
    assert result.is_duplicate is False
    assert "First code" in result.explanation


def test_compare_codes_with_existing(monkeypatch):
    mock_response = json.dumps({
        "is_duplicate": True,
        "similar_codes": ["fabrication"],
        "merge_suggestion": "hallucination/fabrication",
        "explanation": "Same concept",
    })
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=mock_response)]
    mock_client.messages.create.return_value = msg

    monkeypatch.setattr("grounded_evals.open_coding.compare.get_default_client", lambda: mock_client)
    monkeypatch.setattr("grounded_evals.open_coding.compare.get_model_id", lambda: "test")

    result = compare_codes("hallucination", ["fabrication", "tone_issue"])
    assert result.is_duplicate is True
    assert "fabrication" in result.similar_codes


# ── fracture_domain (mocked LLM) ─────────────────────────────────────────────

def test_fracture_domain_success(monkeypatch):
    mock_response = json.dumps({
        "categories": [
            {
                "name": "Happy Path",
                "definition": "Standard successful interactions",
                "properties": [
                    {"name": "complexity", "dimensions": [
                        {"name": "complexity", "low_anchor": "simple", "high_anchor": "complex"}
                    ]}
                ],
                "exemplar_prompts": ["Book a flight", "Check status"],
            },
            {
                "name": "Edge Case",
                "definition": "Boundary conditions",
                "properties": [],
                "exemplar_prompts": ["Empty input"],
            },
        ]
    })
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=mock_response)]
    mock_client.messages.create.return_value = msg

    monkeypatch.setattr("grounded_evals.open_coding.fracture.get_default_client", lambda: mock_client)
    monkeypatch.setattr("grounded_evals.open_coding.fracture.get_model_id", lambda: "test")

    spec = AgentSpec(
        name="TravelBot",
        description="Books flights",
        capabilities=[Capability(name="Flight booking")],
    )
    categories = fracture_domain(spec)
    assert len(categories) == 2
    assert categories[0].name == "Happy Path"
    assert len(categories[0].properties) == 1
    assert categories[0].properties[0].dimensions[0].low_anchor == "simple"
    # Exemplar prompts create code_ids
    assert len(categories[0].code_ids) == 2


def test_fracture_domain_no_json(monkeypatch):
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text="I cannot help with that.")]
    mock_client.messages.create.return_value = msg

    monkeypatch.setattr("grounded_evals.open_coding.fracture.get_default_client", lambda: mock_client)
    monkeypatch.setattr("grounded_evals.open_coding.fracture.get_model_id", lambda: "test")

    spec = AgentSpec(name="Bot")
    with pytest.raises(RuntimeError, match="failed to parse"):
        fracture_domain(spec)


def test_fracture_domain_empty_categories(monkeypatch):
    mock_response = json.dumps({"categories": []})
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=mock_response)]
    mock_client.messages.create.return_value = msg

    monkeypatch.setattr("grounded_evals.open_coding.fracture.get_default_client", lambda: mock_client)
    monkeypatch.setattr("grounded_evals.open_coding.fracture.get_model_id", lambda: "test")

    spec = AgentSpec(name="Bot")
    categories = fracture_domain(spec)
    assert categories == []
