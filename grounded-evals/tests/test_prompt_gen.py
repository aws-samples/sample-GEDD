"""Unit tests for judge_builder/prompt_gen.py — judge prompt generation modes."""

from grounded_evals.axial_coding.mapper import ErrorMapping
from grounded_evals.judge_builder.few_shot import FewShotExample, FewShotExemplarSet
from grounded_evals.judge_builder.prompt_gen import (
    _build_criteria_section,
    _build_geval_criteria_section,
    _build_score_keys,
    generate_few_shot_judge_prompt,
    generate_geval_judge_prompt,
    generate_judge_prompt,
)
from grounded_evals.judge_builder.rubric import generate_rubric
from grounded_evals.models.core import JudgeCriterion, JudgeRubric


def _make_rubric():
    mappings = [
        ErrorMapping(error_code="Hallucination", primary_category="accuracy"),
        ErrorMapping(error_code="Rude tone", primary_category="tone"),
    ]
    return generate_rubric(mappings)


# ── _build_criteria_section ───────────────────────────────────────────────────


def test_build_criteria_section():
    rubric = _make_rubric()
    section = _build_criteria_section(rubric)
    assert "### Accuracy" in section or "### accuracy" in section.lower()
    assert "### Tone" in section or "### tone" in section.lower()
    assert "5/5" in section
    assert "1/5" in section


# ── _build_score_keys ─────────────────────────────────────────────────────────


def test_build_score_keys():
    rubric = _make_rubric()
    score_keys, justification_keys = _build_score_keys(rubric)
    assert "<1-5>" in score_keys
    assert "<reason>" in justification_keys


# ── generate_judge_prompt (standard) ──────────────────────────────────────────


def test_generate_judge_prompt_basic():
    rubric = _make_rubric()
    prompt = generate_judge_prompt(rubric, agent_name="TestBot")
    assert "TestBot" in prompt
    assert "1-5" in prompt
    assert "pass" in prompt.lower()


def test_generate_judge_prompt_default_agent():
    rubric = _make_rubric()
    prompt = generate_judge_prompt(rubric)
    assert "AI Agent" in prompt


def test_generate_judge_prompt_contains_criteria():
    rubric = _make_rubric()
    prompt = generate_judge_prompt(rubric, agent_name="Bot")
    assert "Hallucination" in prompt
    assert "Rude tone" in prompt


# ── generate_geval_judge_prompt ───────────────────────────────────────────────


def test_generate_geval_prompt():
    rubric = _make_rubric()
    prompt = generate_geval_judge_prompt(rubric, agent_name="GBot")
    assert "GBot" in prompt
    assert "Step-by-Step" in prompt
    assert "{query}" in prompt
    assert "{response}" in prompt


def test_geval_criteria_section_has_questions():
    rubric = _make_rubric()
    section = _build_geval_criteria_section(rubric)
    # Should contain guiding questions
    assert "?" in section
    assert "Step-by-step questions" in section


# ── generate_few_shot_judge_prompt ────────────────────────────────────────────


def test_generate_few_shot_prompt():
    rubric = _make_rubric()
    exemplar_set = FewShotExemplarSet(
        exemplars=[
            FewShotExample(
                query="What's the policy?",
                response="Our policy is 30 days.",
                error_codes=["Hallucination"],
                verdict="incorrect",
                severity="critical",
                confidence="high",
                memo="No such policy",
                is_positive=True,
                target_error_code="Hallucination",
            ),
        ],
        n_positive=1,
        n_negative=0,
        coverage=["Hallucination"],
    )
    prompt = generate_few_shot_judge_prompt(
        rubric, exemplar_set, agent_name="FewBot", agent_description="A test bot"
    )
    assert "FewBot" in prompt
    assert "Reference Examples" in prompt
    assert "FAIL" in prompt
    assert "{query}" in prompt


def test_generate_few_shot_prompt_empty_exemplars():
    rubric = _make_rubric()
    exemplar_set = FewShotExemplarSet()
    prompt = generate_few_shot_judge_prompt(rubric, exemplar_set, agent_name="Bot")
    assert "Bot" in prompt
    # Should still produce a valid prompt even without exemplars
    assert "Evaluation Rubric" in prompt


# ── Rubric with paradigm model enrichment ────────────────────────────────────


def test_rubric_with_paradigm_dict():
    mappings = [ErrorMapping(error_code="hallucination", primary_category="accuracy")]
    paradigm_dict = {
        "causal_conditions": ["Missing context", "No grounding"],
        "strategies": ["Fabrication"],
        "consequences": ["User distrust"],
        "context": ["Long conversations"],
    }
    rubric = generate_rubric(mappings, paradigm_dict=paradigm_dict)
    desc = rubric.criteria[0].description
    assert "Missing context" in desc
    assert "Fabrication" in desc
    assert "User distrust" in desc


def test_rubric_dimension_weights():
    mappings = [
        ErrorMapping(error_code="x", primary_category="safety"),
        ErrorMapping(error_code="y", primary_category="tone"),
    ]
    rubric = generate_rubric(mappings)
    weights = {c.name.lower(): c.weight for c in rubric.criteria}
    assert weights["safety"] == 2.0
    assert weights["tone"] == 0.8
