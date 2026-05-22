"""Self-consistency ensemble judging.

Based on Wang et al. (2023) "Self-Consistency Improves Chain of Thought Reasoning"
and applied to LLM-as-a-Judge evaluation.

Core insight: LLM judges are stochastic. At temperature > 0, the same judge prompt
produces different verdicts on borderline cases. By sampling K responses and
aggregating, you get:
  - A more reliable score (lower variance for clear-cut cases)
  - A calibrated confidence estimate (high variance = the judge is uncertain)
  - Identification of hard cases that warrant human review (high disagreement)

Aggregation strategies:
  - Binary (pass/fail): majority vote, report minority fraction as uncertainty
  - Scored (1–5 rubric): median score, report IQR as uncertainty
  - Verbal ratings: mode; ties broken by recency

Usage in GEDD:
  The ensemble is especially valuable post-calibration to identify which responses
  are in the "uncertain zone" (judge disagrees with itself) — these should be
  routed to the Active Learning recommender for human review.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field


@dataclass
class EnsembleResult:
    query: str
    response: str
    n_samples: int
    # Binary verdict aggregation
    pass_votes: int = 0
    fail_votes: int = 0
    majority_pass: bool = True
    pass_fraction: float = 1.0
    # Scored aggregation (per criterion)
    median_scores: dict[str, float] = field(default_factory=dict)
    score_variance: dict[str, float] = field(default_factory=dict)
    # Confidence derived from agreement
    confidence: str = "high"    # "high" | "medium" | "low"
    is_uncertain: bool = False   # True if judge disagreed with itself
    summaries: list[str] = field(default_factory=list)
    error: str = ""


def _parse_judge_response(text: str) -> dict:
    """Extract JSON from a judge response, tolerating markdown fences."""
    # Try JSON fence first
    for fence in ("```json", "```"):
        if fence in text:
            try:
                start = text.index(fence) + len(fence)
                end = text.index("```", start)
                return json.loads(text[start:end].strip())
            except (ValueError, json.JSONDecodeError):
                pass
    # Fallback: raw JSON
    try:
        j_start = text.find("{")
        j_end = text.rfind("}") + 1
        if j_start >= 0 and j_end > j_start:
            return json.loads(text[j_start:j_end])
    except (json.JSONDecodeError, ValueError):
        pass
    return {}


def _infer_confidence(pass_fraction: float, n: int) -> tuple[str, bool]:
    """Map agreement level → confidence label and uncertainty flag."""
    agreement = max(pass_fraction, 1 - pass_fraction)
    if agreement >= (1.0 if n == 1 else 0.9):
        return "high", False
    elif agreement >= 0.67:
        return "medium", False
    else:
        return "low", True


def ensemble_judge(
    judge_prompt_template: str,
    query: str,
    response: str,
    client,
    model_id: str,
    n_samples: int = 3,
    temperature: float = 0.7,
) -> EnsembleResult:
    """Run the judge N times and aggregate via majority vote + median scoring.

    Parameters
    ----------
    judge_prompt_template:
        The full judge prompt with {query} and {response} placeholders.
    n_samples:
        Number of independent samples. 3 is a good default (odd → no tie).
    temperature:
        Sampling temperature. 0.7 introduces enough variance to detect
        disagreement on borderline cases without being too noisy.
    """
    full_prompt = judge_prompt_template.replace("{query}", query[:500]).replace("{response}", response[:800])

    raw_responses: list[dict] = []
    for _ in range(n_samples):
        try:
            msg = client.messages.create(
                model=model_id,
                max_tokens=1024,
                temperature=temperature,
                messages=[{"role": "user", "content": full_prompt}],
            )
            parsed = _parse_judge_response(msg.content[0].text)
            raw_responses.append(parsed)
        except Exception as e:
            raw_responses.append({"_error": str(e)})

    valid = [r for r in raw_responses if "_error" not in r]
    if not valid:
        errors = [r.get("_error", "unknown") for r in raw_responses]
        return EnsembleResult(
            query=query, response=response, n_samples=n_samples,
            error=f"All {n_samples} samples failed: {errors[0]}"
        )

    # Aggregate binary pass/fail
    passes = sum(1 for r in valid if r.get("pass", True))
    fails = len(valid) - passes
    pass_frac = passes / len(valid)
    majority = passes >= len(valid) / 2

    # Aggregate scores per criterion
    all_criteria: set[str] = set()
    for r in valid:
        all_criteria.update((r.get("scores") or {}).keys())

    median_scores: dict[str, float] = {}
    score_variance: dict[str, float] = {}
    for crit in all_criteria:
        vals = [r["scores"][crit] for r in valid if "scores" in r and crit in r["scores"]]
        if vals:
            median_scores[crit] = statistics.median(vals)
            score_variance[crit] = statistics.variance(vals) if len(vals) > 1 else 0.0

    summaries = [r.get("summary", "") for r in valid if r.get("summary")]
    confidence, is_uncertain = _infer_confidence(pass_frac, len(valid))

    return EnsembleResult(
        query=query,
        response=response,
        n_samples=n_samples,
        pass_votes=passes,
        fail_votes=fails,
        majority_pass=majority,
        pass_fraction=pass_frac,
        median_scores=median_scores,
        score_variance=score_variance,
        confidence=confidence,
        is_uncertain=is_uncertain,
        summaries=summaries,
    )


def aggregate_ensemble_results(results: list[EnsembleResult]) -> dict:
    """Summarise a batch of ensemble results into a dataset-level report."""
    if not results:
        return {}

    total = len(results)
    passing = sum(1 for r in results if r.majority_pass)
    uncertain = [r for r in results if r.is_uncertain]

    # Overall score per criterion (median of medians)
    all_criteria: set[str] = set()
    for r in results:
        all_criteria.update(r.median_scores.keys())

    criterion_scores: dict[str, list[float]] = {c: [] for c in all_criteria}
    for r in results:
        for c, score in r.median_scores.items():
            criterion_scores[c].append(score)

    avg_criterion_scores = {
        c: round(statistics.mean(scores), 2)
        for c, scores in criterion_scores.items()
        if scores
    }

    return {
        "total_evaluated": total,
        "pass_count": passing,
        "fail_count": total - passing,
        "overall_pass_rate": f"{passing / total * 100:.1f}%",
        "uncertain_count": len(uncertain),
        "uncertain_queries": [r.query[:80] for r in uncertain[:5]],
        "avg_criterion_scores": avg_criterion_scores,
        "confidence_distribution": {
            "high": sum(1 for r in results if r.confidence == "high"),
            "medium": sum(1 for r in results if r.confidence == "medium"),
            "low": sum(1 for r in results if r.confidence == "low"),
        },
    }
