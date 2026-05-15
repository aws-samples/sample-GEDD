from __future__ import annotations

from pydantic import BaseModel, Field


class CalibrationResult(BaseModel):
    agreement_score: float = 0.0
    total_compared: int = 0
    exact_matches: int = 0
    within_one: int = 0
    disagreements: list[str] = Field(default_factory=list)
    recommendation: str = ""


def calibrate(
    manual_scores: list[dict[str, int]],
    judge_scores: list[dict[str, int]],
) -> CalibrationResult:
    if not manual_scores or not judge_scores:
        return CalibrationResult(recommendation="No scores to compare yet.")

    total = 0
    exact = 0
    within_one = 0
    disagreements = []

    for manual, judge in zip(manual_scores, judge_scores):
        for key in manual:
            if key in judge:
                total += 1
                diff = abs(manual[key] - judge[key])
                if diff == 0:
                    exact += 1
                    within_one += 1
                elif diff == 1:
                    within_one += 1
                else:
                    disagreements.append(
                        f"{key}: manual={manual[key]}, judge={judge[key]} (diff={diff})"
                    )

    agreement = within_one / total if total > 0 else 0.0

    if agreement >= 0.85:
        rec = "Excellent alignment. Your judge is ready for production use."
    elif agreement >= 0.7:
        rec = "Good alignment. Review the disagreements and consider tuning the judge prompt."
    elif agreement >= 0.5:
        rec = "Moderate alignment. The judge needs tuning — review criteria definitions and examples."
    else:
        rec = "Low alignment. Consider adding more examples to the judge prompt or revising criteria."

    return CalibrationResult(
        agreement_score=agreement,
        total_compared=total,
        exact_matches=exact,
        within_one=within_one,
        disagreements=disagreements[:10],
        recommendation=rec,
    )
