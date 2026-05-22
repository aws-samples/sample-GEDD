"""Active learning: recommend which responses to annotate next.

Motivation (from Settles 2009, "Active Learning Literature Survey"):
  Human annotation is the bottleneck. Given N unannotated responses and a judge
  that is already calibrated on some examples, uncertainty sampling tells you
  which N' << N examples would yield the most calibration improvement if annotated.

In GEDD, this drives the workflow:
  1. Human annotates initial batch (Tag Failures step)
  2. Judge is generated and calibrated on that batch
  3. Active learning identifies the most uncertain responses in the eval set
  4. Human annotates those next → judge becomes dramatically more accurate
  5. Repeat until calibration plateau

Uncertainty metrics used:
  - **Margin sampling**: |score - threshold| is smallest → most uncertain.
    For binary judges: responses closest to 50/50 pass/fail.
    For scored judges: responses with overall_score closest to 3.5.
  - **Ensemble disagreement**: high score_variance across ensemble samples.
  - **Error code coverage gap**: responses that may contain an error code not
    yet in the annotated set (novelty signal, inspired by Core-Set / BADGE).

Both signals can be combined into a single uncertainty rank.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UncertainExample:
    """A response the judge is least certain about — recommend for human review."""
    query: str
    response: str
    uncertainty_score: float      # 0–1, higher = more uncertain
    uncertainty_reason: str       # human-readable explanation
    judge_score: float | None     # raw score or pass_fraction
    suggested_codes: list[str]    # codes the judge suspects but isn't sure


@dataclass
class ActiveLearningReport:
    top_uncertain: list[UncertainExample]
    uncertainty_method: str
    n_evaluated: int
    n_recommended: int
    coverage_gaps: list[str]      # error codes with < min_examples annotations
    annotation_priority: str      # "focus on X" guidance for the PM


# Pass/fail threshold for binary judges
_BINARY_THRESHOLD = 0.5
# Score threshold for rubric judges (pass ≥ 3.5 out of 5)
_RUBRIC_THRESHOLD = 3.5


def recommend_from_ensemble_results(
    responses: list[dict],
    ensemble_results: list,       # list[EnsembleResult] from ensemble.py
    top_k: int = 5,
    coding_annotations: list[dict] | None = None,
    codebook: list[dict] | None = None,
) -> ActiveLearningReport:
    """Select responses where the ensemble judge disagreed most with itself.

    This is the most principled uncertainty signal: if running the same judge
    3 times gives 2 PASS and 1 FAIL, the model is genuinely on the fence.
    These are the examples most worth a human look.
    """
    if not responses or not ensemble_results:
        return ActiveLearningReport(
            top_uncertain=[], uncertainty_method="ensemble_disagreement",
            n_evaluated=0, n_recommended=0,
            coverage_gaps=[], annotation_priority="Run an evaluation first.",
        )

    uncertain: list[UncertainExample] = []
    for r in ensemble_results:
        if hasattr(r, "is_uncertain"):
            # Binary: uncertainty = distance from 50/50
            score = 1.0 - abs(r.pass_fraction - _BINARY_THRESHOLD) * 2
            score = max(0.0, min(1.0, score))
            reason = (
                f"Judge voted {r.pass_votes} PASS / {r.fail_votes} FAIL across "
                f"{r.n_samples} samples — genuine disagreement."
            )
        else:
            score = 0.0
            reason = "No ensemble data available."

        uncertain.append(UncertainExample(
            query=r.query if hasattr(r, "query") else "",
            response=r.response if hasattr(r, "response") else "",
            uncertainty_score=score,
            uncertainty_reason=reason,
            judge_score=getattr(r, "pass_fraction", None),
            suggested_codes=[],
        ))

    uncertain.sort(key=lambda u: u.uncertainty_score, reverse=True)
    top = uncertain[:top_k]

    coverage_gaps = _find_coverage_gaps(coding_annotations or [], codebook or [])
    priority = _build_priority_guidance(top, coverage_gaps)

    return ActiveLearningReport(
        top_uncertain=top,
        uncertainty_method="ensemble_disagreement",
        n_evaluated=len(ensemble_results),
        n_recommended=len(top),
        coverage_gaps=coverage_gaps,
        annotation_priority=priority,
    )


def recommend_from_judge_scores(
    responses: list[dict],
    judge_scores: list[dict],
    top_k: int = 5,
    threshold: float = _RUBRIC_THRESHOLD,
    coding_annotations: list[dict] | None = None,
    codebook: list[dict] | None = None,
) -> ActiveLearningReport:
    """Margin sampling: responses whose judge score is closest to the pass threshold.

    When you don't have ensemble results, this is the next-best signal:
    a response scored 3.5 out of 5 (exactly on the pass/fail boundary) is the
    most informative example to annotate. Human verdict on it provides the most
    information gain for recalibrating the judge.
    """
    if not responses or not judge_scores:
        return ActiveLearningReport(
            top_uncertain=[], uncertainty_method="margin_sampling",
            n_evaluated=0, n_recommended=0,
            coverage_gaps=[], annotation_priority="No judge scores available yet.",
        )

    uncertain: list[UncertainExample] = []
    for resp, scores in zip(responses, judge_scores):
        overall = scores.get("overall_score")
        if overall is None:
            # Infer from pass/fail
            overall = 4.0 if scores.get("pass") else 1.5

        margin = abs(overall - threshold)
        # Normalize: margin of 0 → uncertainty 1.0, margin of 2+ → 0.0
        uncertainty = max(0.0, 1.0 - margin / 2.0)

        reason = (
            f"Judge scored {overall:.1f}/5 — within {margin:.1f} points of the "
            f"pass/fail boundary ({threshold}). A human check here has high calibration value."
        )
        uncertain.append(UncertainExample(
            query=resp.get("query", "")[:200],
            response=resp.get("response", "")[:300],
            uncertainty_score=uncertainty,
            uncertainty_reason=reason,
            judge_score=overall,
            suggested_codes=[],
        ))

    uncertain.sort(key=lambda u: u.uncertainty_score, reverse=True)
    top = uncertain[:top_k]

    coverage_gaps = _find_coverage_gaps(coding_annotations or [], codebook or [])
    priority = _build_priority_guidance(top, coverage_gaps)

    return ActiveLearningReport(
        top_uncertain=top,
        uncertainty_method="margin_sampling",
        n_evaluated=len(judge_scores),
        n_recommended=len(top),
        coverage_gaps=coverage_gaps,
        annotation_priority=priority,
    )


def _find_coverage_gaps(
    coding_annotations: list[dict],
    codebook: list[dict],
    min_examples: int = 2,
) -> list[str]:
    """Find error codes with fewer than min_examples annotated examples."""
    code_counts: dict[str, int] = {}
    for ann in coding_annotations:
        for code in ann.get("codes", []):
            code_counts[code] = code_counts.get(code, 0) + 1

    gaps = []
    for entry in codebook:
        name = entry.get("name", "")
        if code_counts.get(name, 0) < min_examples:
            gaps.append(name)
    return gaps


def _build_priority_guidance(
    top_uncertain: list[UncertainExample],
    coverage_gaps: list[str],
) -> str:
    parts = []
    if top_uncertain:
        parts.append(
            f"Annotate the {len(top_uncertain)} highlighted response(s) — "
            f"the judge is least confident here."
        )
    if coverage_gaps:
        gaps_str = ", ".join(coverage_gaps[:3])
        parts.append(
            f"Error codes with sparse examples: {gaps_str}. "
            f"Adding 1–2 clear examples per code will most improve judge accuracy."
        )
    if not parts:
        return "Your annotation coverage looks good. Consider running the ensemble judge to find remaining edge cases."
    return " ".join(parts)
