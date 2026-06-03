"""Unit tests for judge_builder/active_learning.py — uncertainty sampling."""

from grounded_evals.judge_builder.active_learning import (
    ActiveLearningReport,
    UncertainExample,
    _build_priority_guidance,
    _find_coverage_gaps,
    recommend_from_ensemble_results,
    recommend_from_judge_scores,
)
from grounded_evals.judge_builder.ensemble import EnsembleResult

# ── _find_coverage_gaps ───────────────────────────────────────────────────────


def test_find_coverage_gaps_empty():
    assert _find_coverage_gaps([], []) == []


def test_find_coverage_gaps_all_covered():
    codebook = [{"name": "hallucination"}, {"name": "tone"}]
    annotations = [
        {"codes": ["hallucination"]},
        {"codes": ["hallucination"]},
        {"codes": ["tone"]},
        {"codes": ["tone"]},
    ]
    gaps = _find_coverage_gaps(annotations, codebook, min_examples=2)
    assert gaps == []


def test_find_coverage_gaps_some_missing():
    codebook = [{"name": "hallucination"}, {"name": "tone"}, {"name": "safety"}]
    annotations = [
        {"codes": ["hallucination"]},
        {"codes": ["hallucination"]},
        {"codes": ["tone"]},
    ]
    gaps = _find_coverage_gaps(annotations, codebook, min_examples=2)
    assert "tone" in gaps
    assert "safety" in gaps
    assert "hallucination" not in gaps


# ── _build_priority_guidance ──────────────────────────────────────────────────


def test_build_priority_guidance_empty():
    result = _build_priority_guidance([], [])
    assert "looks good" in result


def test_build_priority_guidance_with_uncertain():
    uncertain = [
        UncertainExample(
            query="q",
            response="r",
            uncertainty_score=0.9,
            uncertainty_reason="reason",
            judge_score=0.5,
            suggested_codes=[],
        )
    ]
    result = _build_priority_guidance(uncertain, [])
    assert "Annotate" in result


def test_build_priority_guidance_with_gaps():
    result = _build_priority_guidance([], ["safety", "tone"])
    assert "safety" in result


# ── recommend_from_ensemble_results ───────────────────────────────────────────


def test_recommend_from_ensemble_empty():
    report = recommend_from_ensemble_results([], [])
    assert report.n_evaluated == 0
    assert report.top_uncertain == []


def test_recommend_from_ensemble_basic():
    results = [
        EnsembleResult(
            query="q1",
            response="r1",
            n_samples=3,
            pass_votes=2,
            fail_votes=1,
            majority_pass=True,
            pass_fraction=0.67,
            confidence="medium",
            is_uncertain=False,
        ),
        EnsembleResult(
            query="q2",
            response="r2",
            n_samples=3,
            pass_votes=1,
            fail_votes=2,
            majority_pass=False,
            pass_fraction=0.33,
            confidence="low",
            is_uncertain=True,
        ),
        EnsembleResult(
            query="q3",
            response="r3",
            n_samples=3,
            pass_votes=3,
            fail_votes=0,
            majority_pass=True,
            pass_fraction=1.0,
            confidence="high",
            is_uncertain=False,
        ),
    ]
    report = recommend_from_ensemble_results(
        [{"query": f"q{i}"} for i in range(1, 4)], results, top_k=2
    )
    assert report.n_evaluated == 3
    assert report.n_recommended == 2
    # Most uncertain should be first (closest to 50/50)
    assert report.top_uncertain[0].query == "q2"


def test_recommend_from_ensemble_with_coverage_gaps():
    results = [
        EnsembleResult(
            query="q1",
            response="r1",
            n_samples=3,
            pass_votes=1,
            fail_votes=2,
            majority_pass=False,
            pass_fraction=0.33,
            confidence="low",
            is_uncertain=True,
        ),
    ]
    codebook = [{"name": "safety"}, {"name": "tone"}]
    annotations = [{"codes": ["safety"]}]
    report = recommend_from_ensemble_results(
        [{}], results, coding_annotations=annotations, codebook=codebook
    )
    assert "tone" in report.coverage_gaps


# ── recommend_from_judge_scores ───────────────────────────────────────────────


def test_recommend_from_judge_scores_empty():
    report = recommend_from_judge_scores([], [])
    assert report.n_evaluated == 0


def test_recommend_from_judge_scores_margin_sampling():
    responses = [
        {"query": "q1", "response": "r1"},
        {"query": "q2", "response": "r2"},
        {"query": "q3", "response": "r3"},
    ]
    scores = [
        {"overall_score": 3.5},  # exactly on boundary → most uncertain
        {"overall_score": 5.0},  # far from boundary → least uncertain
        {"overall_score": 3.0},  # close to boundary
    ]
    report = recommend_from_judge_scores(responses, scores, top_k=2)
    assert report.n_evaluated == 3
    assert report.n_recommended == 2
    # q1 (score=3.5) should be most uncertain
    assert report.top_uncertain[0].query == "q1"
    assert report.top_uncertain[0].uncertainty_score == 1.0


def test_recommend_from_judge_scores_pass_fail_inferred():
    responses = [{"query": "q1", "response": "r1"}]
    scores = [{"pass": True}]  # no overall_score → inferred as 4.0
    report = recommend_from_judge_scores(responses, scores)
    assert report.n_evaluated == 1
    # 4.0 is 0.5 from threshold 3.5 → uncertainty = 1 - 0.5/2 = 0.75
    assert report.top_uncertain[0].uncertainty_score == 0.75
