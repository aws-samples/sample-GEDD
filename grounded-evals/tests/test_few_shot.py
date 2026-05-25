"""Unit tests for judge_builder/few_shot.py — exemplar selection and formatting."""

from grounded_evals.judge_builder.few_shot import (
    FewShotExample,
    FewShotExemplarSet,
    format_exemplars_for_prompt,
    select_exemplars,
)


def _make_annotation(query, response, codes, severity="functional", confidence="high", memo=""):
    return {
        "query": query,
        "response": response,
        "codes": codes,
        "severity": severity,
        "confidence": confidence,
        "memo": memo,
    }


def _make_codebook(*names):
    return [{"name": n, "definition": f"def of {n}"} for n in names]


def test_select_exemplars_empty():
    result = select_exemplars([], [])
    assert result.exemplars == []
    assert result.n_positive == 0


def test_select_exemplars_no_annotations():
    codebook = _make_codebook("hallucination")
    result = select_exemplars([], codebook)
    assert result.exemplars == []


def test_select_exemplars_basic():
    codebook = _make_codebook("hallucination", "tone_issue")
    annotations = [
        _make_annotation("q1", "r1", ["hallucination"], severity="critical"),
        _make_annotation("q2", "r2", ["tone_issue"], severity="functional"),
        _make_annotation("q3", "r3", [], severity="cosmetic"),
    ]
    result = select_exemplars(annotations, codebook)
    assert result.n_positive >= 1
    assert len(result.coverage) >= 1


def test_select_exemplars_respects_max_total():
    codebook = _make_codebook("a", "b", "c", "d", "e")
    annotations = [
        _make_annotation(f"q{i}", f"r{i}", [c["name"]], severity="critical")
        for i, c in enumerate(codebook)
    ] + [_make_annotation(f"clean{i}", f"ok{i}", []) for i in range(5)]
    result = select_exemplars(annotations, codebook, max_total=4)
    assert len(result.exemplars) <= 4


def test_select_exemplars_prefers_high_severity():
    codebook = _make_codebook("error")
    annotations = [
        _make_annotation("q1", "r1", ["error"], severity="cosmetic", confidence="low"),
        _make_annotation("q2", "r2", ["error"], severity="catastrophic", confidence="high"),
    ]
    result = select_exemplars(annotations, codebook, max_per_code=2)
    positives = [e for e in result.exemplars if e.is_positive]
    assert positives[0].query == "q2"


def test_select_exemplars_includes_negatives():
    codebook = _make_codebook("hallucination")
    annotations = [
        _make_annotation("q1", "r1", ["hallucination"], severity="critical"),
        _make_annotation("q2", "r2", [], severity="cosmetic"),
    ]
    result = select_exemplars(annotations, codebook)
    assert result.n_negative >= 1


def test_select_exemplars_deduplicates_queries():
    codebook = _make_codebook("a", "b")
    annotations = [
        _make_annotation("same_q", "r1", ["a", "b"], severity="critical"),
    ]
    result = select_exemplars(annotations, codebook)
    queries = [e.query for e in result.exemplars]
    # same_q should only appear once
    assert queries.count("same_q") == 1


def test_format_exemplars_empty():
    empty_set = FewShotExemplarSet()
    assert format_exemplars_for_prompt(empty_set) == ""


def test_format_exemplars_produces_markdown():
    ex = FewShotExample(
        query="What's the refund policy?",
        response="You can get a refund within 30 days.",
        error_codes=["hallucination"],
        verdict="incorrect",
        severity="critical",
        confidence="high",
        memo="Agent invented a policy",
        is_positive=True,
        target_error_code="hallucination",
    )
    exemplar_set = FewShotExemplarSet(
        exemplars=[ex], n_positive=1, n_negative=0, coverage=["hallucination"]
    )
    output = format_exemplars_for_prompt(exemplar_set)
    assert "## Reference Examples" in output
    assert "FAIL" in output
    assert "hallucination" in output
    assert "Agent invented a policy" in output


def test_format_exemplars_pass_example():
    ex = FewShotExample(
        query="Hello",
        response="Hi there!",
        error_codes=[],
        verdict="correct",
        severity="cosmetic",
        confidence="high",
        memo="",
        is_positive=False,
        target_error_code="hallucination",
    )
    exemplar_set = FewShotExemplarSet(exemplars=[ex], n_positive=0, n_negative=1, coverage=[])
    output = format_exemplars_for_prompt(exemplar_set)
    assert "PASS" in output
    assert "No failure patterns detected" in output
