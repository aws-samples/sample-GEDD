"""Unit tests for axial_coding/ — mapper and paradigm model building."""

import json
from unittest.mock import MagicMock

from grounded_evals.axial_coding.mapper import (
    STANDARD_ERROR_CATEGORIES,
    ErrorMapping,
    map_errors_to_categories,
)
from grounded_evals.axial_coding.paradigm import (
    STANDARD_DIMENSIONS,
    build_paradigm_model,
)
from grounded_evals.models.core import Category, Code, CodeType

# ── ErrorMapping ──────────────────────────────────────────────────────────────


def test_error_mapping_creation():
    m = ErrorMapping(error_code="hallucination", primary_category="accuracy")
    assert m.error_code == "hallucination"
    assert m.primary_category == "accuracy"
    assert m.secondary_category is None
    assert m.rationale == ""


def test_error_mapping_with_secondary():
    m = ErrorMapping(
        error_code="policy_fabrication",
        primary_category="accuracy",
        secondary_category="instruction_following",
        rationale="Invents policies not in system prompt",
    )
    assert m.secondary_category == "instruction_following"


# ── STANDARD_ERROR_CATEGORIES ─────────────────────────────────────────────────


def test_standard_categories_complete():
    expected = {
        "quality",
        "accuracy",
        "brand_relevance",
        "bias",
        "safety",
        "completeness",
        "tone",
        "instruction_following",
    }
    assert set(STANDARD_ERROR_CATEGORIES.keys()) == expected


# ── map_errors_to_categories (mocked LLM) ────────────────────────────────────


def test_map_errors_empty():
    result = map_errors_to_categories([])
    assert result == []


def test_map_errors_with_mock_llm(monkeypatch):
    mock_response = json.dumps(
        {
            "mappings": [
                {
                    "error_code": "hallucination",
                    "primary_category": "accuracy",
                    "secondary_category": None,
                    "rationale": "Factual error",
                },
                {
                    "error_code": "rude_tone",
                    "primary_category": "tone",
                    "secondary_category": "brand_relevance",
                    "rationale": "Tone issue",
                },
            ]
        }
    )
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=mock_response)]
    mock_client.messages.create.return_value = msg

    monkeypatch.setattr(
        "grounded_evals.axial_coding.mapper.get_default_client", lambda: mock_client
    )
    monkeypatch.setattr("grounded_evals.axial_coding.mapper.get_model_id", lambda: "test-model")

    codes = [
        Code(label="hallucination", code_type=CodeType.IN_VIVO, definition="Made up facts"),
        Code(label="rude_tone", code_type=CodeType.DESCRIPTIVE, definition="Rude response"),
    ]
    result = map_errors_to_categories(codes)
    assert len(result) == 2
    assert result[0].error_code == "hallucination"
    assert result[0].primary_category == "accuracy"
    assert result[1].secondary_category == "brand_relevance"


def test_map_errors_parse_failure(monkeypatch):
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text="Not valid JSON at all")]
    mock_client.messages.create.return_value = msg

    monkeypatch.setattr(
        "grounded_evals.axial_coding.mapper.get_default_client", lambda: mock_client
    )
    monkeypatch.setattr("grounded_evals.axial_coding.mapper.get_model_id", lambda: "test-model")

    codes = [Code(label="test", code_type=CodeType.IN_VIVO)]
    import pytest

    with pytest.raises(RuntimeError, match="failed to parse"):
        map_errors_to_categories(codes)


# ── STANDARD_DIMENSIONS ───────────────────────────────────────────────────────


def test_standard_dimensions_not_empty():
    assert len(STANDARD_DIMENSIONS) >= 5
    assert "Accuracy" in STANDARD_DIMENSIONS
    assert "Safety" in STANDARD_DIMENSIONS


# ── build_paradigm_model (mocked LLM) ────────────────────────────────────────


def test_build_paradigm_model_success(monkeypatch):
    mock_response = json.dumps(
        {
            "phenomenon": {"name": "Agent Hallucination", "definition": "Core failure"},
            "causal_conditions": [{"name": "Missing context", "definition": "No grounding data"}],
            "context": [{"name": "Long conversation", "definition": "Multi-turn"}],
            "intervening_conditions": [{"name": "Model limitations", "definition": "Capacity"}],
            "action_strategies": [{"name": "Fabrication", "definition": "Makes up facts"}],
            "consequences": [{"name": "User distrust", "definition": "Loss of confidence"}],
        }
    )
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=mock_response)]
    mock_client.messages.create.return_value = msg

    monkeypatch.setattr(
        "grounded_evals.axial_coding.paradigm.get_default_client", lambda: mock_client
    )
    monkeypatch.setattr("grounded_evals.axial_coding.paradigm.get_model_id", lambda: "test-model")

    codes = [Code(label="hallucination", code_type=CodeType.IN_VIVO, definition="Invents facts")]
    categories = [Category(name="Accuracy")]

    pm = build_paradigm_model(codes, categories)
    assert pm.phenomenon.name == "Agent Hallucination"
    assert len(pm.causal_conditions) == 1
    assert pm.causal_conditions[0].name == "Missing context"
    assert len(pm.consequences) == 1


def test_build_paradigm_model_parse_failure(monkeypatch):
    mock_client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text="No JSON here")]
    mock_client.messages.create.return_value = msg

    monkeypatch.setattr(
        "grounded_evals.axial_coding.paradigm.get_default_client", lambda: mock_client
    )
    monkeypatch.setattr("grounded_evals.axial_coding.paradigm.get_model_id", lambda: "test-model")

    import pytest

    with pytest.raises(RuntimeError, match="failed to parse"):
        build_paradigm_model([], [])
