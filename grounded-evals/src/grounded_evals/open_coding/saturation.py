from __future__ import annotations

from grounded_evals.models.core import Category, CoverageReport, GoldenPrompt, SaturationStatus

MIN_PROMPTS_PER_CATEGORY = 3
APPROACHING_THRESHOLD = 2
SATURATED_THRESHOLD = 3


def check_category_saturation(
    category: Category, prompts: list[GoldenPrompt]
) -> SaturationStatus:
    category_prompts = [p for p in prompts if p.category_id == category.id]
    count = len(category_prompts)

    if count >= SATURATED_THRESHOLD:
        return SaturationStatus.SATURATED
    elif count >= APPROACHING_THRESHOLD:
        return SaturationStatus.APPROACHING
    return SaturationStatus.UNSATURATED


def check_overall_saturation(
    categories: list[Category], prompts: list[GoldenPrompt]
) -> CoverageReport:
    if not categories:
        return CoverageReport()

    categories_with_prompts = set()
    saturated_count = 0
    gaps: list[str] = []
    redundancies: list[str] = []

    for cat in categories:
        cat_prompts = [p for p in prompts if p.category_id == cat.id]
        count = len(cat_prompts)

        if count > 0:
            categories_with_prompts.add(cat.id)

        status = check_category_saturation(cat, prompts)
        if status == SaturationStatus.SATURATED:
            saturated_count += 1
        elif count == 0:
            gaps.append(f"No prompts for: {cat.name}")

        if count > SATURATED_THRESHOLD * 2:
            redundancies.append(
                f"'{cat.name}' has {count} prompts — consider focusing elsewhere"
            )

    return CoverageReport(
        total_prompts=len(prompts),
        categories_covered=len(categories_with_prompts),
        categories_total=len(categories),
        saturated_categories=saturated_count,
        gaps=gaps,
        redundancies=redundancies,
        saturation_score=saturated_count / len(categories),
    )


def saturation_recommendation(report: CoverageReport) -> str:
    if report.saturation_score >= 0.8:
        return (
            "Great coverage! Most categories are well-tested. "
            "Consider moving to the next step."
        )
    elif report.saturation_score >= 0.5:
        return (
            f"Good progress — {report.saturated_categories}/{report.categories_total} "
            f"categories saturated. Focus on the gaps: "
            + "; ".join(report.gaps[:3])
        )
    elif report.categories_covered > 0:
        return (
            f"Early stage — {report.categories_covered}/{report.categories_total} "
            f"categories started. Keep writing prompts across different categories."
        )
    return "No prompts yet. Start by selecting a category and writing your first test query."
