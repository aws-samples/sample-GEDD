"""Uber-inspired Eval Quality Feedback Loop for GEDD.

Four-layer quality measurement framework adapted from Uber's production ML
validation systems (Human-in-the-Loop Validation, Oct 2025 + ML Deployment
Safety, Oct 2025) for LLM evaluation:

  1. Eval Health Score (0–100) — 4-indicator composite readiness metric
     mirrors Uber's Composite Deployment Readiness Score
  2. Category-Level Failure Analysis — where does the agent fail most?
     mirrors Uber's "slice-first" backtesting that catches invisible regressions
  3. Judge-Human Agreement (Cohen's Kappa) — where is the rubric ambiguous?
     mirrors Uber's IAA threshold (70%) and real-time Kappa measurement
  4. LLM-Assisted Improvement Suggestions — specific, grounded recommendations
     closes the loop: eval failures → suggestions → coach/rubric/queries

Design principles from Uber research:
  - Human attention is rationed: surface only low-confidence cases for review
  - Aggregate metrics hide regressions: always break down by category
  - Platform-enforced minimums: health score shows non-negotiable gaps
  - Feedback must be explicit: suggestions carry direct action payloads
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from grounded_evals.judge_builder.calibrate import _cohens_kappa_binary


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class EvalHealthScore:
    """4-indicator composite score (0–100) mirroring Uber's deployment readiness score.

    Indicators (each 0–25):
      rubric_freshness      — days since judge prompt generated (30-day window)
      eval_staleness        — days since last eval run (staleness penalty)
      annotation_coverage   — % of responses human-annotated
      judge_human_agreement — Cohen's Kappa mapped to 0–25
    """
    rubric_freshness: int = 0
    eval_staleness: int = 0
    annotation_coverage: int = 0
    judge_human_agreement: int = 0
    total: int = 0
    rubric_age_days: int | None = None
    eval_age_days: int | None = None
    annotation_pct: float = 0.0
    kappa: float | None = None
    kappa_interpretation: str = ""
    gaps: list[str] = field(default_factory=list)


@dataclass
class CategoryInsight:
    """Pass-rate breakdown for a single query category (Uber: slice-level analysis)."""
    category: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    sample_failures: list[str] = field(default_factory=list)


@dataclass
class DisagreementCase:
    """A judge-human disagreement case requiring human escalation.

    Mirrors Uber's multi-judge escalation: when confidence is low,
    escalate to additional human review rather than forcing a verdict.
    """
    query_idx: int
    model_id: str
    query: str
    response_excerpt: str
    human_verdict: str
    judge_pass: bool
    direction: str  # "false_positive" | "false_negative"


@dataclass
class ImprovementSuggestion:
    """Specific, actionable improvement grounded in eval data.

    Each suggestion has a type that maps to a concrete GEDD workflow action:
      golden_query    — add this query to the golden set
      rubric_refinement — update a specific rubric criterion
      system_prompt   — append/replace text in the agent system prompt
      coverage_gap    — a failure category with no golden queries
    """
    type: str
    priority: str  # "high" | "medium" | "low"
    title: str
    description: str
    action_text: str
    category: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReport:
    """Full quality analysis report produced by run_quality_analysis()."""
    health: EvalHealthScore
    category_insights: list[CategoryInsight]
    disagreements: list[DisagreementCase]
    suggestions: list[ImprovementSuggestion]
    n_queries: int
    n_annotated: int
    n_disagreements: int
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ── Health score computation ──────────────────────────────────────────────────

def compute_eval_health(state: dict) -> EvalHealthScore:
    """Compute 4-indicator composite health score from app.storage.user state dict."""
    eval_results: list[dict] = state.get("eval_results", [])
    eval_history: list[dict] = state.get("eval_history", [])
    judge_results: dict = state.get("_eval_judge_results", {})
    judge_prompt: str = state.get("_generated_judge_prompt", "")
    jb_generated_at: str = state.get("_jb_generated_at", "")

    gaps: list[str] = []

    # ── Indicator 1: Eval staleness (0–25) ───────────────────────────────────
    # Full score if run today; loses 3 pts/day; 0 after ~8 days
    eval_age_days: int | None = None
    if eval_history:
        last_ts = eval_history[-1].get("timestamp", "")
        if last_ts:
            try:
                dt = datetime.fromisoformat(last_ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                eval_age_days = (datetime.now(timezone.utc) - dt).days
            except Exception:
                pass
    if eval_age_days is None:
        staleness_score = 0
        gaps.append("No eval runs yet — run an evaluation to start tracking quality.")
    else:
        staleness_score = max(0, 25 - eval_age_days * 3)
        if staleness_score < 10:
            gaps.append(f"Last eval run {eval_age_days}d ago — re-run to get fresh signal.")

    # ── Indicator 2: Annotation coverage (0–25) ───────────────────────────────
    total_responses = sum(len(r.get("responses", {})) for r in eval_results)
    annotated = sum(
        1 for r in eval_results
        for mid in r.get("responses", {})
        if r.get("annotations", {}).get(mid)
    )
    annotation_pct = annotated / total_responses if total_responses > 0 else 0.0
    coverage_score = int(annotation_pct * 25)
    if annotation_pct < 0.5 and total_responses > 0:
        gaps.append(
            f"Only {annotation_pct:.0%} of responses annotated "
            f"({annotated}/{total_responses}) — annotate more to enable quality analysis."
        )
    elif total_responses == 0:
        gaps.append("No eval results — run an evaluation first.")

    # ── Indicator 3: Rubric freshness (0–25) ──────────────────────────────────
    # No prompt = 0. Generated today = 25. Loses 2 pts/day over 30-day window.
    rubric_age_days: int | None = None
    if jb_generated_at:
        try:
            dt = datetime.fromisoformat(jb_generated_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            rubric_age_days = (datetime.now(timezone.utc) - dt).days
        except Exception:
            pass
    if not judge_prompt:
        freshness_score = 0
        gaps.append("No judge prompt generated — complete Step 5 in Build Judge.")
    elif rubric_age_days is None:
        freshness_score = 20
    else:
        freshness_score = max(0, 25 - rubric_age_days * 2)
        if freshness_score < 10:
            gaps.append(
                f"Judge prompt is {rubric_age_days}d old — regenerate after adding new failure codes."
            )

    # ── Indicator 4: Judge-human agreement (0–25) — Cohen's Kappa ────────────
    kappa: float | None = None
    kappa_score = 0
    kappa_interp = ""
    if judge_results and eval_results:
        human_verdicts: list[bool] = []
        judge_verdicts: list[bool] = []
        for idx, r in enumerate(eval_results):
            for mid in r.get("annotations", {}):
                key = f"{idx}_{mid}"
                if key in judge_results:
                    human_pass = r["annotations"][mid] == "correct"
                    judge_pass = bool(judge_results[key].get("pass", False))
                    human_verdicts.append(human_pass)
                    judge_verdicts.append(judge_pass)
        if len(human_verdicts) >= 3:
            kappa, _, _ = _cohens_kappa_binary(human_verdicts, judge_verdicts)
            # Map kappa (-1 to 1) → score (0–25)
            # κ ≥ 0.8 → 25, κ = 0 → 12, κ < 0 → 0
            kappa_score = int(max(0, min(25, (kappa + 1) / 2 * 25)))
            if kappa >= 0.80:
                kappa_interp = "Almost perfect — judge is production-ready"
            elif kappa >= 0.61:
                kappa_interp = "Substantial — minor rubric tuning recommended"
            elif kappa >= 0.41:
                kappa_interp = "Moderate — review criteria definitions"
            elif kappa >= 0.21:
                kappa_interp = "Fair — significant rubric revision needed"
            else:
                kappa_interp = "Poor — rubric may be ambiguous or inverted"
            if kappa < 0.61:
                gaps.append(
                    f"Judge-human agreement κ={kappa:.2f} is below the 0.61 threshold "
                    "(Uber's IAA standard). Run quality analysis for specific rubric fixes."
                )
    elif judge_prompt and annotated >= 3:
        gaps.append(
            "Run Judge (in eval results) to enable judge-human agreement measurement."
        )

    total = staleness_score + coverage_score + freshness_score + kappa_score
    return EvalHealthScore(
        rubric_freshness=freshness_score,
        eval_staleness=staleness_score,
        annotation_coverage=coverage_score,
        judge_human_agreement=kappa_score,
        total=total,
        rubric_age_days=rubric_age_days,
        eval_age_days=eval_age_days,
        annotation_pct=annotation_pct,
        kappa=kappa,
        kappa_interpretation=kappa_interp,
        gaps=gaps,
    )


# ── Category-level failure analysis ──────────────────────────────────────────

def analyze_category_failures(eval_results: list[dict]) -> list[CategoryInsight]:
    """Group eval results by category and compute pass rates.

    Mirrors Uber's backtesting insight: aggregate pass rates hide category-level
    regressions. A 70% overall pass rate can mask a 20% pass rate on safety queries.
    """
    cat_data: dict[str, dict] = {}
    for r in eval_results:
        cat = (r.get("category") or "Uncategorized").strip()[:60]
        if cat not in cat_data:
            cat_data[cat] = {"total": 0, "passed": 0, "failed": 0, "failure_queries": []}
        for mid, verdict in r.get("annotations", {}).items():
            cat_data[cat]["total"] += 1
            if verdict == "correct":
                cat_data[cat]["passed"] += 1
            else:
                cat_data[cat]["failed"] += 1
                q = r.get("query", "")
                if q and q not in cat_data[cat]["failure_queries"]:
                    cat_data[cat]["failure_queries"].append(q)

    insights: list[CategoryInsight] = []
    for cat, d in cat_data.items():
        if d["total"] == 0:
            continue
        rate = d["passed"] / d["total"]
        insights.append(CategoryInsight(
            category=cat,
            total=d["total"],
            passed=d["passed"],
            failed=d["failed"],
            pass_rate=rate,
            sample_failures=d["failure_queries"][:3],
        ))

    return sorted(insights, key=lambda x: x.pass_rate)


# ── Judge-human disagreement detection ───────────────────────────────────────

def detect_disagreements(
    eval_results: list[dict],
    judge_results: dict,
) -> list[DisagreementCase]:
    """Identify cases where judge and human annotator disagree.

    These cases should be escalated for human review (Uber's multi-judge escalation
    pattern: when confidence is low, don't force a verdict — escalate to review).
    """
    cases: list[DisagreementCase] = []
    for idx, r in enumerate(eval_results):
        for mid, human_verdict in r.get("annotations", {}).items():
            key = f"{idx}_{mid}"
            if key not in judge_results:
                continue
            judge_pass = bool(judge_results[key].get("pass", False))
            human_pass = human_verdict == "correct"
            if judge_pass == human_pass:
                continue
            direction = "false_positive" if judge_pass and not human_pass else "false_negative"
            response_text = r.get("responses", {}).get(mid, "")
            cases.append(DisagreementCase(
                query_idx=idx,
                model_id=mid,
                query=r.get("query", "")[:200],
                response_excerpt=response_text[:300],
                human_verdict=human_verdict,
                judge_pass=judge_pass,
                direction=direction,
            ))
    return cases


# ── LLM-assisted improvement suggestions ─────────────────────────────────────

_SUGGESTION_PROMPT = """\
You are an AI evaluation quality expert reviewing eval results for an AI agent.

AGENT NAME: {agent_name}
SYSTEM PROMPT (excerpt): {system_prompt_excerpt}

EVAL HEALTH SUMMARY:
- Annotation coverage: {annotation_pct}% ({annotated}/{total_responses} responses annotated)
- Judge-human agreement: {kappa_str}
- Days since last eval run: {eval_age_days}

FAILURE BREAKDOWN BY CATEGORY (worst first):
{category_breakdown}

FAILURE MODES IN CODEBOOK ({n_codes} codes):
{codebook_summary}

JUDGE-HUMAN DISAGREEMENTS ({n_disagreements} cases):
{disagreements_summary}

CURRENT JUDGE PROMPT EXISTS: {has_judge}

Your task: Generate exactly 4 specific, actionable improvement suggestions.
Each suggestion must be GROUNDED IN THE DATA above — not generic advice.

Types:
  "golden_query"      — an exact new query to add to the golden set
  "rubric_refinement" — a specific criterion change (name the criterion and write new score1/score5)
  "system_prompt"     — a specific addition or clarification to the agent system prompt
  "coverage_gap"      — a failure pattern that has no golden queries yet

Priority: "high" if it addresses a category with <40% pass rate or κ<0.41, else "medium" or "low".

Output ONLY valid JSON (no markdown, no explanation):
[
  {{
    "type": "golden_query",
    "priority": "high",
    "title": "Short title (max 8 words)",
    "description": "1-2 sentences on WHY this matters based on the data above.",
    "action_text": "The exact query text, rubric criterion, or prompt addition.",
    "category": "which category this addresses"
  }}
]
"""


async def generate_suggestions(
    *,
    agent_name: str,
    system_prompt: str,
    eval_results: list[dict],
    codebook: list[dict],
    category_insights: list[CategoryInsight],
    disagreements: list[DisagreementCase],
    health: EvalHealthScore,
    client,
    model_id: str,
) -> list[ImprovementSuggestion]:
    """Call the LLM to generate grounded improvement suggestions."""

    total_responses = sum(len(r.get("responses", {})) for r in eval_results)
    annotated = sum(
        1 for r in eval_results for mid in r.get("responses", {})
        if r.get("annotations", {}).get(mid)
    )

    cat_lines = "\n".join(
        f"  {i+1}. '{ci.category}': {ci.pass_rate:.0%} pass rate "
        f"({ci.passed}/{ci.total}) — failures: {', '.join(ci.sample_failures[:2]) or 'none annotated'}"
        for i, ci in enumerate(category_insights[:6])
    ) or "  No annotated categories yet."

    codebook_lines = "\n".join(
        f"  - {c['name']}: {c.get('definition', '')[:80]}"
        for c in codebook[:8]
    ) or "  No failure codes yet."

    if disagreements:
        dis_lines = "\n".join(
            f"  - Q: '{d.query[:80]}' → human={d.human_verdict}, judge={'PASS' if d.judge_pass else 'FAIL'} ({d.direction})"
            for d in disagreements[:4]
        )
    else:
        dis_lines = "  None detected yet."

    kappa_str = (
        f"κ={health.kappa:.2f} ({health.kappa_interpretation})"
        if health.kappa is not None else "Not yet measured"
    )

    prompt = _SUGGESTION_PROMPT.format(
        agent_name=agent_name,
        system_prompt_excerpt=system_prompt[:250],
        annotation_pct=f"{health.annotation_pct:.0%}",
        annotated=annotated,
        total_responses=total_responses,
        kappa_str=kappa_str,
        eval_age_days=health.eval_age_days if health.eval_age_days is not None else "unknown",
        category_breakdown=cat_lines,
        n_codes=len(codebook),
        codebook_summary=codebook_lines,
        n_disagreements=len(disagreements),
        disagreements_summary=dis_lines,
        has_judge="Yes" if health.rubric_age_days is not None or health.rubric_freshness > 0 else "No",
    )

    try:
        response = await asyncio.to_thread(
            client.messages.create,
            model=model_id,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Extract JSON array even if model adds preamble
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if not m:
            return _fallback_suggestions(category_insights, health)
        items = json.loads(m.group(0))
        suggestions = []
        for item in items[:5]:
            suggestions.append(ImprovementSuggestion(
                type=item.get("type", "coverage_gap"),
                priority=item.get("priority", "medium"),
                title=item.get("title", "Improvement"),
                description=item.get("description", ""),
                action_text=item.get("action_text", ""),
                category=item.get("category", ""),
            ))
        return suggestions
    except Exception:
        return _fallback_suggestions(category_insights, health)


def _fallback_suggestions(
    category_insights: list[CategoryInsight],
    health: EvalHealthScore,
) -> list[ImprovementSuggestion]:
    """Rule-based fallback suggestions when LLM call fails."""
    suggestions: list[ImprovementSuggestion] = []

    worst = [ci for ci in category_insights if ci.pass_rate < 0.5]
    if worst:
        ci = worst[0]
        suggestions.append(ImprovementSuggestion(
            type="golden_query",
            priority="high",
            title=f"More coverage for '{ci.category}'",
            description=(
                f"'{ci.category}' has only {ci.pass_rate:.0%} pass rate "
                f"({ci.failed} failures). Adding targeted queries will surface the failure mode."
            ),
            action_text=f"Query targeting the '{ci.category}' failure pattern",
            category=ci.category,
        ))

    if health.kappa is not None and health.kappa < 0.61:
        suggestions.append(ImprovementSuggestion(
            type="rubric_refinement",
            priority="high",
            title="Improve rubric calibration",
            description=(
                f"Judge-human agreement is κ={health.kappa:.2f} "
                "(below the 0.61 substantial-agreement threshold). "
                "Add concrete examples to your score1/score5 rubric criteria."
            ),
            action_text="Add 1–2 concrete examples to the lowest-scoring rubric criterion.",
            category="",
        ))

    if health.annotation_pct < 0.5:
        suggestions.append(ImprovementSuggestion(
            type="coverage_gap",
            priority="medium",
            title="Increase annotation coverage",
            description=(
                f"Only {health.annotation_pct:.0%} of eval responses are annotated. "
                "Quality analysis improves significantly above 70% coverage."
            ),
            action_text="Annotate all responses in the Eval Harness tab.",
            category="",
        ))

    return suggestions


# ── Main entry point ──────────────────────────────────────────────────────────

async def run_quality_analysis(
    *,
    state: dict,
    agent_name: str,
    system_prompt: str,
    client,
    model_id: str,
) -> QualityReport:
    """Run the full quality analysis pipeline and return a QualityReport.

    This is the top-level entry point called by the UI when the user clicks
    'Run Quality Analysis'. All sub-analyses are run and the LLM generates
    grounded improvement suggestions.
    """
    eval_results: list[dict] = state.get("eval_results", [])
    judge_results: dict = state.get("_eval_judge_results", {})
    codebook: list[dict] = state.get("codebook", [])

    health = compute_eval_health(state)
    category_insights = analyze_category_failures(eval_results)
    disagreements = detect_disagreements(eval_results, judge_results)

    n_annotated = sum(
        1 for r in eval_results for mid in r.get("responses", {})
        if r.get("annotations", {}).get(mid)
    )

    suggestions = await generate_suggestions(
        agent_name=agent_name,
        system_prompt=system_prompt,
        eval_results=eval_results,
        codebook=codebook,
        category_insights=category_insights,
        disagreements=disagreements,
        health=health,
        client=client,
        model_id=model_id,
    )

    return QualityReport(
        health=health,
        category_insights=category_insights,
        disagreements=disagreements,
        suggestions=suggestions,
        n_queries=len(eval_results),
        n_annotated=n_annotated,
        n_disagreements=len(disagreements),
    )


# ── Coach briefing text generator ────────────────────────────────────────────

def build_coach_briefing(report: QualityReport, agent_name: str, system_prompt: str) -> str:
    """Build a pre-formatted coach briefing message from a quality report.

    This is injected into the coach conversation so the PM can immediately
    ask for help with the most urgent failures (closes the feedback loop).
    """
    health = report.health
    worst_cats = [ci for ci in report.category_insights if ci.pass_rate < 0.6][:3]
    high_sug = [s for s in report.suggestions if s.priority == "high"][:2]

    cat_lines = "\n".join(
        f"  • '{ci.category}': {ci.pass_rate:.0%} pass rate ({ci.failed}/{ci.total} failed)"
        for ci in worst_cats
    ) or "  • No categories with <60% pass rate yet."

    sug_lines = "\n".join(
        f"  {i+1}. [{s.type.upper()}] {s.title} — {s.description}"
        for i, s in enumerate(high_sug)
    ) or "  • No high-priority suggestions yet — annotate more responses."

    kappa_str = (
        f"κ={health.kappa:.2f} ({health.kappa_interpretation})"
        if health.kappa is not None else "Not yet measured (run Judge first)"
    )

    return (
        f"I've completed an evaluation run on **{agent_name}** and need your help "
        f"interpreting the results and improving the agent.\n\n"
        f"**Eval Health Score: {health.total}/100**\n"
        f"- Annotation coverage: {health.annotation_pct:.0%}\n"
        f"- Judge-human agreement: {kappa_str}\n"
        f"- Eval freshness: {'Today' if health.eval_age_days == 0 else f'{health.eval_age_days}d ago'}\n\n"
        f"**Worst-performing query categories:**\n{cat_lines}\n\n"
        f"**Top improvement suggestions from quality analysis:**\n{sug_lines}\n\n"
        f"Can you help me with:\n"
        f"1. Generate 3 new golden queries targeting the "
        f"'{worst_cats[0].category if worst_cats else 'failing'}' category?\n"
        f"2. Review and improve the agent system prompt to address these failure patterns?\n"
        f"3. Suggest what rubric criterion is most likely causing the judge-human disagreements?"
    )
