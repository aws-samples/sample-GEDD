from uuid import uuid4

from grounded_evals.models.core import Category, GoldenPrompt, SaturationStatus
from grounded_evals.open_coding.saturation import (
    check_category_saturation,
    check_overall_saturation,
    saturation_recommendation,
)


def _make_category(name: str = "Test Category") -> Category:
    return Category(name=name, definition="Test definition")


def _make_prompt(category_id=None) -> GoldenPrompt:
    return GoldenPrompt(
        prompt_text="Test prompt",
        category_id=category_id or uuid4(),
    )


def test_empty_category_is_unsaturated():
    cat = _make_category()
    status = check_category_saturation(cat, [])
    assert status == SaturationStatus.UNSATURATED


def test_category_approaching_saturation():
    cat = _make_category()
    prompts = [_make_prompt(cat.id) for _ in range(2)]
    status = check_category_saturation(cat, prompts)
    assert status == SaturationStatus.APPROACHING


def test_category_saturated():
    cat = _make_category()
    prompts = [_make_prompt(cat.id) for _ in range(3)]
    status = check_category_saturation(cat, prompts)
    assert status == SaturationStatus.SATURATED


def test_overall_saturation_no_categories():
    report = check_overall_saturation([], [])
    assert report.total_prompts == 0
    assert report.saturation_score == 0.0


def test_overall_saturation_with_gaps():
    cats = [_make_category("A"), _make_category("B"), _make_category("C")]
    prompts = [_make_prompt(cats[0].id) for _ in range(3)]
    report = check_overall_saturation(cats, prompts)

    assert report.categories_covered == 1
    assert report.categories_total == 3
    assert len(report.gaps) == 2
    assert report.saturated_categories == 1


def test_saturation_recommendation_empty():
    report = check_overall_saturation([_make_category("A")], [])
    rec = saturation_recommendation(report)
    assert "No prompts yet" in rec


def test_saturation_recommendation_good_coverage():
    cats = [_make_category(f"Cat{i}") for i in range(5)]
    prompts = []
    for cat in cats:
        prompts.extend([_make_prompt(cat.id) for _ in range(3)])
    report = check_overall_saturation(cats, prompts)
    rec = saturation_recommendation(report)
    assert "Great coverage" in rec
