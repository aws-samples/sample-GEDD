"""Few-shot calibration for LLM-as-a-Judge.

Implements the Prometheus approach (Kim et al., 2023 / 2024): inject scored reference
examples directly into the judge prompt so the LLM sees WHAT a failure looks like
before it evaluates the candidate response.

Key insight: a judge shown 3-5 annotated examples per error code is substantially
more calibrated than a zero-shot judge, even with a detailed rubric. The examples
ground abstract criteria in concrete observations from *your* domain.

Selection strategy:
  - For each error code, pick the highest-confidence POSITIVE example (exhibits error)
    and the highest-confidence NEGATIVE example (does not exhibit this error).
  - Prefer critical/catastrophic severity for positives (clearest signal).
  - Prefer diverse queries (avoid near-duplicates).
  - Cap at max_per_code exemplars to stay within context budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FewShotExample:
    query: str
    response: str
    error_codes: list[str]          # codes assigned by human annotator
    verdict: str                    # "correct" | "partial" | "incorrect"
    severity: str                   # "cosmetic" | "functional" | "critical" | "catastrophic"
    confidence: str                 # "low" | "medium" | "high"
    memo: str                       # annotator rationale
    is_positive: bool               # True = exhibits target error, False = clean example
    target_error_code: str = ""     # which code this example is selected for


@dataclass
class FewShotExemplarSet:
    """Ready-to-inject exemplars grouped by error code."""
    exemplars: list[FewShotExample] = field(default_factory=list)
    n_positive: int = 0
    n_negative: int = 0
    coverage: list[str] = field(default_factory=list)   # error codes with at least 1 exemplar


_SEVERITY_RANK = {"catastrophic": 4, "critical": 3, "functional": 2, "cosmetic": 1, "": 0}
_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1, "": 0}


def select_exemplars(
    coding_annotations: list[dict],
    codebook: list[dict],
    max_per_code: int = 2,
    max_total: int = 10,
) -> FewShotExemplarSet:
    """Select the most informative annotated examples as few-shot demonstrations.

    Parameters
    ----------
    coding_annotations:
        Human-coded annotations from the Tag Failures step. Each dict has:
        query, response, codes, verdict (optional), severity, confidence, memo.
    codebook:
        Error code definitions from Open Coding.
    max_per_code:
        Max exemplars to select for each error code (split between + and -).
    max_total:
        Hard cap on total exemplars to avoid context overflow.
    """
    if not coding_annotations or not codebook:
        return FewShotExemplarSet()

    code_names = [c["name"] for c in codebook]
    exemplars: list[FewShotExample] = []
    seen_queries: set[str] = set()

    # Prioritise: catastrophic > critical > functional > cosmetic; high confidence first
    def _rank(ann: dict) -> tuple:
        return (
            _SEVERITY_RANK.get(ann.get("severity", ""), 0),
            _CONFIDENCE_RANK.get(ann.get("confidence", ""), 0),
        )

    sorted_anns = sorted(coding_annotations, key=_rank, reverse=True)

    for code_name in code_names:
        if len(exemplars) >= max_total:
            break

        positives: list[FewShotExample] = []
        negatives: list[FewShotExample] = []

        for ann in sorted_anns:
            q = ann.get("query", "")
            if q in seen_queries:
                continue
            codes = ann.get("codes", [])
            exhibits = code_name in codes

            ex = FewShotExample(
                query=q[:300],
                response=ann.get("response", "")[:400],
                error_codes=codes,
                verdict=ann.get("verdict", ann.get("annotation", "incorrect") if exhibits else "correct"),
                severity=ann.get("severity", "functional"),
                confidence=ann.get("confidence", "medium"),
                memo=ann.get("memo", ""),
                is_positive=exhibits,
                target_error_code=code_name,
            )

            if exhibits and len(positives) < max(1, max_per_code - 1):
                positives.append(ex)
            elif not exhibits and len(negatives) < 1:
                negatives.append(ex)

            if len(positives) >= max(1, max_per_code - 1) and len(negatives) >= 1:
                break

        selected = positives + negatives
        for ex in selected:
            seen_queries.add(ex.query)
            exemplars.append(ex)

        if len(exemplars) >= max_total:
            break

    covered = list({e.target_error_code for e in exemplars if e.is_positive})
    return FewShotExemplarSet(
        exemplars=exemplars[:max_total],
        n_positive=sum(1 for e in exemplars if e.is_positive),
        n_negative=sum(1 for e in exemplars if not e.is_positive),
        coverage=covered,
    )


def format_exemplars_for_prompt(exemplar_set: FewShotExemplarSet) -> str:
    """Render exemplars as a prompt block (Prometheus reference-answer style)."""
    if not exemplar_set.exemplars:
        return ""

    lines: list[str] = [
        "## Reference Examples",
        "",
        "The following annotated examples show how to apply the evaluation criteria. "
        "They were collected by a human domain expert during qualitative error analysis.",
        "",
    ]

    for i, ex in enumerate(exemplar_set.exemplars, 1):
        verdict_label = "FAIL" if ex.is_positive else "PASS"
        severity_note = f" [{ex.severity.upper()} severity]" if ex.is_positive else ""
        lines += [
            f"### Example {i} — {verdict_label}{severity_note}",
            f"**Query:** {ex.query}",
            f"**Response:** {ex.response}",
        ]
        if ex.is_positive:
            codes_str = ", ".join(ex.error_codes) if ex.error_codes else ex.target_error_code
            lines.append(f"**Error pattern detected:** {codes_str}")
            if ex.memo:
                lines.append(f"**Annotator rationale:** {ex.memo}")
            lines.append(f"**Verdict:** FAIL — This response exhibits {ex.target_error_code}.")
        else:
            lines.append("**Error patterns detected:** None")
            if ex.memo:
                lines.append(f"**Annotator rationale:** {ex.memo}")
            lines.append("**Verdict:** PASS — No failure patterns detected.")
        lines.append("")

    return "\n".join(lines)
