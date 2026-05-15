from __future__ import annotations

from grounded_evals.axial_coding.mapper import STANDARD_ERROR_CATEGORIES, ErrorMapping
from grounded_evals.models.core import Category, JudgeCriterion, JudgeRubric, ParadigmModel


def generate_rubric(
    error_mappings: list[ErrorMapping],
    paradigm_model: ParadigmModel | None = None,
    categories: list[Category] | None = None,
) -> JudgeRubric:
    category_errors: dict[str, list[ErrorMapping]] = {}
    for mapping in error_mappings:
        key = mapping.primary_category
        if key not in category_errors:
            category_errors[key] = []
        category_errors[key].append(mapping)

    criteria = []
    for cat_key, mappings in category_errors.items():
        cat_description = STANDARD_ERROR_CATEGORIES.get(cat_key, cat_key)
        error_details = "; ".join(m.error_code for m in mappings)

        criterion = JudgeCriterion(
            name=cat_key.replace("_", " ").title(),
            description=f"{cat_description}. Observed issues: {error_details}",
            scoring_rubric={
                5: "Excellent — no issues observed in this dimension",
                4: "Good — minor issues that don't impact core value",
                3: "Acceptable — noticeable issues but functional",
                2: "Poor — significant issues impacting usefulness",
                1: "Failing — critical failures in this dimension",
            },
            weight=1.0,
        )
        criteria.append(criterion)

    return JudgeRubric(
        name="Auto-generated Evaluation Rubric",
        description="Derived from Open Coding + Axial Coding error analysis",
        criteria=criteria,
        paradigm_model=paradigm_model,
    )
