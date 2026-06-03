"""Unit tests for models/core.py — Pydantic model validation and serialization."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from grounded_evals.models.core import (
    Category,
    Code,
    CodeType,
    CoverageReport,
    Dimension,
    GoldenDataset,
    GoldenPrompt,
    JudgeCriterion,
    JudgeRubric,
    Memo,
    MemoType,
    ParadigmModel,
    Property,
    SaturationStatus,
)

# ── Dimension ─────────────────────────────────────────────────────────────────


def test_dimension_basic():
    d = Dimension(name="complexity", low_anchor="simple", high_anchor="complex")
    assert d.name == "complexity"
    assert d.description == ""


def test_dimension_with_description():
    d = Dimension(name="x", low_anchor="lo", high_anchor="hi", description="desc")
    assert d.description == "desc"


def test_dimension_serialization():
    d = Dimension(name="x", low_anchor="lo", high_anchor="hi")
    data = d.model_dump()
    assert data == {"name": "x", "low_anchor": "lo", "high_anchor": "hi", "description": ""}
    restored = Dimension(**data)
    assert restored == d


# ── Property ──────────────────────────────────────────────────────────────────


def test_property_empty_dimensions():
    p = Property(name="tone")
    assert p.dimensions == []


def test_property_with_dimensions():
    p = Property(
        name="tone",
        dimensions=[
            Dimension(name="formality", low_anchor="casual", high_anchor="formal"),
        ],
    )
    assert len(p.dimensions) == 1


# ── Code ──────────────────────────────────────────────────────────────────────


def test_code_defaults():
    c = Code(label="hallucination", code_type=CodeType.IN_VIVO)
    assert isinstance(c.id, UUID)
    assert c.definition == ""
    assert c.exemplar_prompts == []
    assert c.properties == []
    assert isinstance(c.created_at, datetime)


def test_code_type_enum():
    assert CodeType.IN_VIVO.value == "in_vivo"
    assert CodeType.CONSTRUCTED.value == "constructed"
    assert CodeType.PROCESS.value == "process"
    assert CodeType.DESCRIPTIVE.value == "descriptive"
    assert CodeType.ANALYTIC.value == "analytic"


def test_code_full():
    c = Code(
        label="policy_hallucination",
        code_type=CodeType.ANALYTIC,
        definition="Agent invents policies",
        exemplar_prompts=["What's your refund policy?"],
        agent_behavior_tested="policy retrieval",
    )
    assert c.label == "policy_hallucination"
    assert len(c.exemplar_prompts) == 1


# ── Category ──────────────────────────────────────────────────────────────────


def test_category_defaults():
    cat = Category(name="Happy Path")
    assert cat.saturation == SaturationStatus.UNSATURATED
    assert cat.code_ids == []
    assert cat.subcategory_ids == []


def test_category_with_properties():
    cat = Category(
        name="Edge Case",
        definition="Boundary conditions",
        properties=[Property(name="severity")],
    )
    assert len(cat.properties) == 1


def test_category_serialization_roundtrip():
    cat = Category(name="Test", definition="def")
    data = cat.model_dump()
    restored = Category(**data)
    assert restored.name == cat.name
    assert restored.id == cat.id


# ── GoldenPrompt ──────────────────────────────────────────────────────────────


def test_golden_prompt_requires_category_id():
    gp = GoldenPrompt(prompt_text="Hello", category_id=uuid4())
    assert gp.prompt_text == "Hello"
    assert gp.is_edge_case is False
    assert gp.turn_count == 1


def test_golden_prompt_missing_category_id_raises():
    with pytest.raises(ValidationError):
        GoldenPrompt(prompt_text="Hello")


def test_golden_prompt_edge_case_flags():
    gp = GoldenPrompt(
        prompt_text="Hack me",
        category_id=uuid4(),
        is_edge_case=True,
        is_adversarial=True,
    )
    assert gp.is_edge_case is True
    assert gp.is_adversarial is True


# ── ParadigmModel ─────────────────────────────────────────────────────────────


def test_paradigm_model_minimal():
    phenomenon = Category(name="Core Failure")
    pm = ParadigmModel(phenomenon=phenomenon)
    assert pm.causal_conditions == []
    assert pm.consequences == []


def test_paradigm_model_full():
    pm = ParadigmModel(
        phenomenon=Category(name="Hallucination"),
        causal_conditions=[Category(name="Missing context")],
        context=[Category(name="Long conversation")],
        action_strategies=[Category(name="Fabrication")],
        consequences=[Category(name="User distrust")],
    )
    assert len(pm.causal_conditions) == 1
    assert pm.consequences[0].name == "User distrust"


# ── Memo ──────────────────────────────────────────────────────────────────────


def test_memo_types():
    assert MemoType.CODE.value == "code"
    assert MemoType.THEORETICAL.value == "theoretical"
    assert MemoType.OPERATIONAL.value == "operational"
    assert MemoType.REFLECTIVE.value == "reflective"


def test_memo_creation():
    m = Memo(memo_type=MemoType.THEORETICAL, title="Insight", content="Pattern found")
    assert isinstance(m.id, UUID)
    assert m.related_code_ids == []


# ── GoldenDataset ─────────────────────────────────────────────────────────────


def test_golden_dataset_empty():
    ds = GoldenDataset(agent_name="TestBot")
    assert ds.prompts == []
    assert ds.version == "0.1.0"


def test_golden_dataset_with_prompts():
    cat = Category(name="Test")
    gp = GoldenPrompt(prompt_text="Hi", category_id=cat.id)
    ds = GoldenDataset(agent_name="Bot", prompts=[gp], categories=[cat])
    assert len(ds.prompts) == 1
    assert ds.categories[0].id == cat.id


# ── JudgeCriterion / JudgeRubric ─────────────────────────────────────────────


def test_judge_criterion_defaults():
    jc = JudgeCriterion(name="Accuracy", description="Factual correctness")
    assert jc.weight == 1.0
    assert jc.scoring_rubric == {}


def test_judge_rubric_with_criteria():
    rubric = JudgeRubric(
        name="Test Rubric",
        criteria=[
            JudgeCriterion(name="Safety", description="No harm", weight=2.0),
            JudgeCriterion(name="Quality", description="Good response"),
        ],
    )
    assert len(rubric.criteria) == 2
    assert rubric.criteria[0].weight == 2.0


# ── CoverageReport ───────────────────────────────────────────────────────────


def test_coverage_report_defaults():
    cr = CoverageReport()
    assert cr.total_prompts == 0
    assert cr.saturation_score == 0.0
    assert cr.gaps == []
    assert cr.redundancies == []


def test_coverage_report_with_data():
    cr = CoverageReport(
        total_prompts=10,
        categories_covered=3,
        categories_total=5,
        saturated_categories=2,
        gaps=["No prompts for: Edge Case"],
        saturation_score=0.4,
    )
    assert cr.categories_covered == 3
    assert len(cr.gaps) == 1


# ── SaturationStatus enum ────────────────────────────────────────────────────


def test_saturation_status_values():
    assert SaturationStatus.UNSATURATED.value == "unsaturated"
    assert SaturationStatus.APPROACHING.value == "approaching"
    assert SaturationStatus.SATURATED.value == "saturated"
