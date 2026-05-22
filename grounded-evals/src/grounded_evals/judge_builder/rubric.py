"""Rubric generation from error mappings and Paradigm Model.

Enhanced to embed Paradigm Model context into each JudgeCriterion so the rubric
knows not just WHAT to score but WHY failures occur and HOW they manifest.

The Paradigm Model contribution per criterion:
  - causal_conditions → added to criterion description as "Root causes"
  - action_strategies  → "How failures manifest" (observable behaviour)
  - consequences       → "User impact" (informs severity calibration)

This enriched rubric is then used by prompt_gen.py to produce a judge that
understands failure mechanisms, not just surface-level error labels.
"""

from __future__ import annotations

from grounded_evals.axial_coding.mapper import STANDARD_ERROR_CATEGORIES, ErrorMapping
from grounded_evals.models.core import Category, JudgeCriterion, JudgeRubric, ParadigmModel


def generate_rubric(
    error_mappings: list[ErrorMapping],
    paradigm_model: ParadigmModel | None = None,
    paradigm_dict: dict | None = None,
    categories: list[Category] | None = None,
) -> JudgeRubric:
    """Build a JudgeRubric from error mappings, enriched with Paradigm Model context.

    Parameters
    ----------
    error_mappings:
        Output of map_errors_to_categories() — each error code mapped to a dimension.
    paradigm_model:
        Structured ParadigmModel (from axial_coding.paradigm).
    paradigm_dict:
        Raw dict from app.storage.user['paradigm_model'] — used when the structured
        model is not available (common in the UI context).
    """
    # Resolve paradigm context from whichever form is available
    causal_text = ""
    strategies_text = ""
    consequences_text = ""
    context_text = ""

    if paradigm_model is not None:
        causal_text = "; ".join(c.name for c in paradigm_model.causal_conditions)
        strategies_text = "; ".join(c.name for c in paradigm_model.action_strategies)
        consequences_text = "; ".join(c.name for c in paradigm_model.consequences)
        context_text = "; ".join(c.name for c in paradigm_model.context)
    elif paradigm_dict:
        def _join(key: str) -> str:
            items = paradigm_dict.get(key, [])
            return "; ".join(
                (i if isinstance(i, str) else i.get("name", ""))
                for i in items
            )
        causal_text = _join("causal_conditions")
        strategies_text = _join("strategies")
        consequences_text = _join("consequences")
        context_text = _join("context")

    # Group error codes by primary evaluation dimension
    category_errors: dict[str, list[ErrorMapping]] = {}
    for mapping in error_mappings:
        key = mapping.primary_category
        category_errors.setdefault(key, []).append(mapping)

    criteria: list[JudgeCriterion] = []
    for cat_key, mappings in category_errors.items():
        cat_description = STANDARD_ERROR_CATEGORIES.get(cat_key, cat_key)
        error_labels = "; ".join(m.error_code for m in mappings)

        # Build enriched description with Paradigm Model context
        description_parts = [f"{cat_description}. Observed issues: {error_labels}."]
        if causal_text:
            description_parts.append(f"Root causes: {causal_text}.")
        if strategies_text:
            description_parts.append(f"How failures manifest: {strategies_text}.")
        if consequences_text:
            description_parts.append(f"User impact: {consequences_text}.")
        if context_text:
            description_parts.append(f"Conditions that trigger failures: {context_text}.")

        # Tailor scoring anchors to the specific error codes observed
        criterion = JudgeCriterion(
            name=cat_key.replace("_", " ").title(),
            description=" ".join(description_parts),
            scoring_rubric={
                5: f"Excellent — no evidence of {error_labels} or related issues",
                4: f"Good — very minor {cat_key.replace('_', ' ')} issues, core value delivered",
                3: f"Acceptable — noticeable {cat_key.replace('_', ' ')} issues but response is functional",
                2: f"Poor — significant issues: {error_labels[:80]}",
                1: f"Failing — critical {cat_key.replace('_', ' ')} failure: {error_labels[:60]}",
            },
            weight=_dimension_weight(cat_key),
        )
        criteria.append(criterion)

    return JudgeRubric(
        name="Grounded Evaluation Rubric (GEDD)",
        description=(
            "Auto-generated from Open Coding + Axial Coding qualitative analysis. "
            "Criteria are grounded in observed failure patterns, not generic heuristics."
        ),
        criteria=criteria,
        paradigm_model=paradigm_model,
    )


def _dimension_weight(dimension: str) -> float:
    """Assign higher weight to dimensions with direct user-safety implications."""
    _WEIGHTS = {
        "safety": 2.0,
        "accuracy": 1.5,
        "instruction_following": 1.3,
        "completeness": 1.2,
        "quality": 1.0,
        "tone": 0.8,
        "brand_relevance": 0.8,
        "bias": 1.5,
    }
    return _WEIGHTS.get(dimension, 1.0)
