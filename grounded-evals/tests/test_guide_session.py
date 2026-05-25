"""Unit tests for guide/session.py — Session management and state tracking."""

from uuid import uuid4

from grounded_evals.guide.session import Session
from grounded_evals.ingest.models import AgentSpec, Capability
from grounded_evals.models.core import (
    Category,
    Code,
    CodeType,
    GoldenPrompt,
    SaturationStatus,
)


def test_session_defaults():
    s = Session()
    assert s.agent_spec.name == ""
    assert s.categories == []
    assert s.golden_prompts == []
    assert s.current_step == 1


def test_update_agent():
    s = Session()
    s.update_agent(name="TestBot", description="A test bot")
    assert s.agent_spec.name == "TestBot"
    assert s.agent_spec.description == "A test bot"


def test_update_agent_ignores_unknown_fields():
    s = Session()
    s.update_agent(name="Bot", nonexistent_field="ignored")
    assert s.agent_spec.name == "Bot"


def test_add_golden_prompt():
    s = Session()
    cat = Category(name="Happy")
    s.add_category(cat)
    gp = GoldenPrompt(prompt_text="Hello", category_id=cat.id)
    s.add_golden_prompt(gp)
    assert len(s.golden_prompts) == 1
    assert s.golden_prompts[0].prompt_text == "Hello"


def test_add_category():
    s = Session()
    cat = Category(name="Edge Case", definition="Boundary")
    s.add_category(cat)
    assert len(s.categories) == 1
    assert s.categories[0].name == "Edge Case"


def test_add_code():
    s = Session()
    code = Code(label="hallucination", code_type=CodeType.IN_VIVO)
    s.add_code(code)
    assert len(s.codes) == 1


def test_get_category_found():
    s = Session()
    cat = Category(name="Test")
    s.add_category(cat)
    found = s.get_category(cat.id)
    assert found is not None
    assert found.name == "Test"


def test_get_category_not_found():
    s = Session()
    assert s.get_category(uuid4()) is None


def test_prompts_for_category():
    s = Session()
    cat1 = Category(name="A")
    cat2 = Category(name="B")
    s.add_category(cat1)
    s.add_category(cat2)
    s.add_golden_prompt(GoldenPrompt(prompt_text="p1", category_id=cat1.id))
    s.add_golden_prompt(GoldenPrompt(prompt_text="p2", category_id=cat1.id))
    s.add_golden_prompt(GoldenPrompt(prompt_text="p3", category_id=cat2.id))

    assert len(s.prompts_for_category(cat1.id)) == 2
    assert len(s.prompts_for_category(cat2.id)) == 1


def test_coverage_empty():
    s = Session()
    report = s.coverage()
    assert report.total_prompts == 0
    assert report.saturation_score == 0.0


def test_coverage_with_data():
    s = Session()
    cat1 = Category(name="A", saturation=SaturationStatus.SATURATED)
    cat2 = Category(name="B")
    s.add_category(cat1)
    s.add_category(cat2)
    s.add_golden_prompt(GoldenPrompt(prompt_text="p1", category_id=cat1.id))

    report = s.coverage()
    assert report.total_prompts == 1
    assert report.categories_covered == 1
    assert report.categories_total == 2
    assert report.saturated_categories == 1
    assert report.saturation_score == 0.5
    assert len(report.gaps) == 1


def test_to_golden_dataset():
    s = Session()
    s.update_agent(name="Bot", description="Test bot")
    cat = Category(name="Happy")
    s.add_category(cat)
    s.add_golden_prompt(GoldenPrompt(prompt_text="Hi", category_id=cat.id))

    ds = s.to_golden_dataset()
    assert ds.agent_name == "Bot"
    assert ds.agent_description == "Test bot"
    assert len(ds.prompts) == 1
    assert len(ds.categories) == 1


def test_session_serialization():
    s = Session()
    s.update_agent(name="SerBot")
    data = s.model_dump()
    restored = Session(**data)
    assert restored.agent_spec.name == "SerBot"
