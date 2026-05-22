from grounded_evals.axial_coding.mapper import ErrorMapping
from grounded_evals.judge_builder.calibrate import calibrate
from grounded_evals.judge_builder.prompt_gen import generate_judge_prompt
from grounded_evals.judge_builder.rubric import generate_rubric


def test_generate_rubric_from_mappings():
    mappings = [
        ErrorMapping(error_code="Hallucination", primary_category="accuracy"),
        ErrorMapping(error_code="Safety violation", primary_category="safety"),
        ErrorMapping(error_code="Wrong facts", primary_category="accuracy"),
    ]

    rubric = generate_rubric(mappings)

    assert "Rubric" in rubric.name
    assert len(rubric.criteria) == 2  # accuracy and safety
    criterion_names = {c.name for c in rubric.criteria}
    assert "Accuracy" in criterion_names
    assert "Safety" in criterion_names


def test_generate_judge_prompt():
    mappings = [
        ErrorMapping(error_code="Hallucination", primary_category="accuracy"),
    ]
    rubric = generate_rubric(mappings)
    prompt = generate_judge_prompt(rubric, agent_name="Test Agent")

    assert "Test Agent" in prompt
    assert "Accuracy" in prompt
    assert "1-5" in prompt


def test_calibrate_perfect_agreement():
    manual = [{"accuracy": 5, "safety": 4}]
    judge = [{"accuracy": 5, "safety": 4}]
    result = calibrate(manual, judge)

    assert result.agreement_score == 1.0
    assert result.exact_matches == 2
    assert len(result.disagreements) == 0


def test_calibrate_within_one():
    manual = [{"accuracy": 5, "safety": 4}]
    judge = [{"accuracy": 4, "safety": 3}]
    result = calibrate(manual, judge)

    assert result.agreement_score == 1.0
    assert result.exact_matches == 0
    assert result.within_one == 2


def test_calibrate_disagreements():
    manual = [{"accuracy": 5, "safety": 5}]
    judge = [{"accuracy": 2, "safety": 1}]
    result = calibrate(manual, judge)

    assert result.agreement_score == 0.0
    assert len(result.disagreements) == 2


def test_calibrate_empty():
    result = calibrate([], [])
    assert result.recommendation == "No scores to compare yet."
