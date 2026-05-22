"""Judge calibration — agreement metrics and calibration analysis.

Extends the original naive agreement metric with statistically principled measures:

Cohen's Kappa (Cohen 1960):
  κ = (p_o - p_e) / (1 - p_e)
  Corrects for chance agreement. κ ≥ 0.8 = almost perfect, 0.6–0.8 = substantial.
  Used for binary (pass/fail) judge vs human agreement.

Weighted Kappa (Cohen 1968):
  Uses a weight matrix so near-disagreements (score diff = 1) count less than
  far disagreements (score diff = 4). Appropriate for ordinal 1–5 rubric scores.
  Quadratic weights are standard for Likert-scale inter-rater reliability.

Calibration analysis:
  Beyond a single agreement number, we want to know WHERE the judge disagrees.
  The per-criterion analysis shows which evaluation dimension is least calibrated
  so you know exactly what to improve in the judge prompt.

Confidence intervals:
  For small calibration sets (N < 30), the raw kappa estimate has high variance.
  We report a simple ±95% CI using the asymptotic normal approximation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class CalibrationResult:
    agreement_score: float = 0.0      # raw observed agreement (legacy)
    cohens_kappa: float = 0.0         # chance-corrected agreement (binary)
    weighted_kappa: float = 0.0       # ordinal agreement (rubric scores)
    kappa_ci_low: float = 0.0         # 95% CI lower bound
    kappa_ci_high: float = 0.0        # 95% CI upper bound
    total_compared: int = 0
    exact_matches: int = 0
    within_one: int = 0
    disagreements: list[str] = field(default_factory=list)
    per_criterion_kappa: dict[str, float] = field(default_factory=dict)
    weakest_criterion: str = ""        # lowest kappa criterion — fix this first
    recommendation: str = ""
    kappa_interpretation: str = ""


# Fleiss / Landis & Koch kappa interpretation thresholds
_KAPPA_LEVELS = [
    (0.80, "Almost perfect agreement — judge is production-ready."),
    (0.61, "Substantial agreement — minor prompt tuning recommended."),
    (0.41, "Moderate agreement — review criteria definitions and add examples."),
    (0.21, "Fair agreement — significant prompt revision needed."),
    (0.00, "Slight agreement — consider redesigning the rubric."),
    (-1.0, "Poor agreement (worse than chance) — rubric is likely inverted or ambiguous."),
]


def _kappa_interpretation(kappa: float) -> str:
    for threshold, label in _KAPPA_LEVELS:
        if kappa >= threshold:
            return label
    return "Poor agreement."


def _cohens_kappa_binary(
    human: list[bool],
    judge: list[bool],
) -> tuple[float, float, float]:
    """Compute Cohen's Kappa for binary classification + 95% CI."""
    n = len(human)
    if n == 0:
        return 0.0, 0.0, 0.0

    p_o = sum(h == j for h, j in zip(human, judge)) / n
    p_h_pos = sum(human) / n
    p_j_pos = sum(judge) / n
    p_e = p_h_pos * p_j_pos + (1 - p_h_pos) * (1 - p_j_pos)

    if p_e >= 1.0:
        return 1.0, 1.0, 1.0

    kappa = (p_o - p_e) / (1 - p_e)

    # Asymptotic standard error for κ (Fleiss et al., 1969)
    if n > 1:
        se = math.sqrt(p_e / ((1 - p_e) * n))
        z = 1.96  # 95% CI
        ci_low = kappa - z * se
        ci_high = kappa + z * se
    else:
        ci_low = ci_high = kappa

    return kappa, ci_low, ci_high


def _weighted_kappa_ordinal(
    human: list[int],
    judge: list[int],
    min_score: int = 1,
    max_score: int = 5,
) -> float:
    """Weighted Cohen's Kappa with quadratic weights for ordinal scores."""
    n = len(human)
    if n == 0:
        return 0.0

    k = max_score - min_score + 1

    # Frequency matrix
    mat = [[0] * k for _ in range(k)]
    for h, j in zip(human, judge):
        i = max(0, min(h - min_score, k - 1))
        ji = max(0, min(j - min_score, k - 1))
        mat[i][ji] += 1

    # Quadratic weight matrix
    weights = [
        [1.0 - ((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)]
        for i in range(k)
    ]

    row_sums = [sum(mat[i]) for i in range(k)]
    col_sums = [sum(mat[i][j] for i in range(k)) for j in range(k)]

    p_o = sum(weights[i][j] * mat[i][j] for i in range(k) for j in range(k)) / n
    p_e = sum(
        weights[i][j] * row_sums[i] * col_sums[j]
        for i in range(k) for j in range(k)
    ) / (n * n)

    if p_e >= 1.0:
        return 1.0
    return (p_o - p_e) / (1 - p_e)


def calibrate(
    manual_scores: list[dict[str, int]],
    judge_scores: list[dict[str, int]],
) -> CalibrationResult:
    """Full calibration analysis with Cohen's Kappa metrics.

    Parameters
    ----------
    manual_scores:
        Human expert scores. Each dict maps criterion name → integer score (1–5).
    judge_scores:
        LLM judge scores in the same format.
    """
    if not manual_scores or not judge_scores:
        return CalibrationResult(recommendation="No scores to compare yet.")

    total = 0
    exact = 0
    within_one = 0
    disagreements: list[str] = []

    # Collect all scores for Kappa computation
    all_human_flat: list[int] = []
    all_judge_flat: list[int] = []
    per_criterion_human: dict[str, list[int]] = {}
    per_criterion_judge: dict[str, list[int]] = {}

    for manual, judge in zip(manual_scores, judge_scores):
        for key in manual:
            if key not in judge:
                continue
            h_score = int(manual[key])
            j_score = int(judge[key])
            all_human_flat.append(h_score)
            all_judge_flat.append(j_score)
            per_criterion_human.setdefault(key, []).append(h_score)
            per_criterion_judge.setdefault(key, []).append(j_score)

            total += 1
            diff = abs(h_score - j_score)
            if diff == 0:
                exact += 1
                within_one += 1
            elif diff == 1:
                within_one += 1
            else:
                disagreements.append(
                    f"{key}: human={h_score}, judge={j_score} (diff={diff})"
                )

    raw_agreement = within_one / total if total > 0 else 0.0

    # Cohen's Kappa (binary: pass if score >= 3.5)
    human_binary = [s >= 4 for s in all_human_flat]
    judge_binary = [s >= 4 for s in all_judge_flat]
    kappa, ci_low, ci_high = _cohens_kappa_binary(human_binary, judge_binary)

    # Weighted Kappa (ordinal 1–5)
    w_kappa = _weighted_kappa_ordinal(all_human_flat, all_judge_flat)

    # Per-criterion weighted kappa
    per_criterion_kappa: dict[str, float] = {}
    for crit in per_criterion_human:
        h = per_criterion_human[crit]
        j = per_criterion_judge[crit]
        if len(h) >= 2:
            per_criterion_kappa[crit] = round(_weighted_kappa_ordinal(h, j), 3)

    weakest = min(per_criterion_kappa, key=per_criterion_kappa.get) if per_criterion_kappa else ""

    # Recommendation based on weighted kappa (most relevant for rubric scoring)
    target_kappa = w_kappa if all_human_flat else kappa
    if target_kappa >= 0.80:
        rec = "Excellent. Judge is production-ready — deploy with confidence."
    elif target_kappa >= 0.61:
        rec = f"Substantial agreement. Review disagreements{f' — {weakest} is weakest criterion' if weakest else ''} and add 1–2 examples."
    elif target_kappa >= 0.41:
        rec = f"Moderate agreement. Revise criteria definitions{f' for {weakest}' if weakest else ''} and inject few-shot examples."
    elif target_kappa >= 0.21:
        rec = "Fair agreement. Use Constitutional Judge or Few-Shot mode for better calibration."
    else:
        rec = "Low agreement. Reconsider rubric structure — criteria may be ambiguous or overlapping."

    return CalibrationResult(
        agreement_score=round(raw_agreement, 3),
        cohens_kappa=round(kappa, 3),
        weighted_kappa=round(w_kappa, 3),
        kappa_ci_low=round(ci_low, 3),
        kappa_ci_high=round(ci_high, 3),
        total_compared=total,
        exact_matches=exact,
        within_one=within_one,
        disagreements=disagreements[:10],
        per_criterion_kappa=per_criterion_kappa,
        weakest_criterion=weakest,
        recommendation=rec,
        kappa_interpretation=_kappa_interpretation(target_kappa),
    )
