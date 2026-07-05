"""Quality measurement for baseline vs GEDD-generated EARS documents."""

from __future__ import annotations

from grounded_evals.guide.session import Session
from grounded_evals.models.core import (
    EARSDocument,
    ImprovementReport,
    MetricComparison,
    QualityMetrics,
)


class MeasurementEngine:
    """Compute lightweight quality metrics for requirement documents."""

    def measure(
        self,
        baseline_doc: EARSDocument,
        gedd_doc: EARSDocument,
        session: Session,
    ) -> ImprovementReport:
        baseline_metrics = self._score_document(baseline_doc, session)
        gedd_metrics = self._score_document(gedd_doc, session)
        comparisons: list[MetricComparison] = []
        for metric_name in QualityMetrics.model_fields:
            baseline_score = getattr(baseline_metrics, metric_name)
            gedd_score = getattr(gedd_metrics, metric_name)
            delta = gedd_score - baseline_score
            comparisons.append(
                MetricComparison(
                    metric_name=metric_name,
                    baseline_score=baseline_score,
                    gedd_score=gedd_score,
                    absolute_improvement=delta,
                    percentage_improvement=(delta / baseline_score * 100.0)
                    if baseline_score
                    else 0.0,
                )
            )

        warnings: list[str] = []
        if not session.codes:
            warnings.append("No failure codes were present, so domain coverage is limited.")
        if len(gedd_doc.requirements) < len(session.codes):
            warnings.append("Some failure codes did not produce dedicated requirements.")

        return ImprovementReport(
            agent_name=gedd_doc.agent_name or baseline_doc.agent_name,
            baseline_metrics=baseline_metrics,
            gedd_metrics=gedd_metrics,
            comparisons=comparisons,
            overall_improvement=gedd_metrics.overall_score()
            - baseline_metrics.overall_score(),
            qualitative_examples=self._examples(baseline_doc, gedd_doc),
            warnings=warnings,
        )

    def _score_document(self, document: EARSDocument, session: Session) -> QualityMetrics:
        requirements = document.requirements
        if not requirements:
            return QualityMetrics()

        statements = [req.ears_statement for req in requirements]
        criteria_count = sum(len(req.acceptance_criteria) for req in requirements)
        trace_count = sum(len(req.traceability_links) for req in requirements)
        dimensions = {req.dimension for req in requirements if req.dimension}
        source_codes = {
            req.source_failure_code_id
            for req in requirements
            if req.source_failure_code_id is not None
        }
        failure_code_links = sum(
            1
            for req in requirements
            for link in req.traceability_links
            if link.link_type.value == "failure_code"
        )

        specificity = min(
            100.0,
            35.0 + sum(len(statement.split()) for statement in statements) / len(statements) * 2.0,
        )
        testability = min(100.0, 25.0 + criteria_count / len(requirements) * 22.0)
        traceability = min(100.0, 20.0 + trace_count / len(requirements) * 35.0)
        if session.codes:
            evidence_hits = max(len(source_codes), failure_code_links)
            domain_coverage = min(100.0, evidence_hits / len(session.codes) * 100.0)
        else:
            domain_coverage = min(100.0, len(dimensions) * 20.0)
        completeness = min(
            100.0,
            30.0
            + len(requirements) * 8.0
            + len(document.glossary) * 4.0
            + len(document.non_functional_requirements) * 4.0,
        )

        return QualityMetrics(
            specificity=specificity,
            testability=testability,
            traceability=traceability,
            domain_coverage=domain_coverage,
            completeness=completeness,
        )

    def _examples(
        self,
        baseline_doc: EARSDocument,
        gedd_doc: EARSDocument,
    ) -> list[dict[str, str]]:
        if not baseline_doc.requirements or not gedd_doc.requirements:
            return []
        return [
            {
                "baseline": baseline_doc.requirements[0].ears_statement,
                "gedd_driven": gedd_doc.requirements[0].ears_statement,
                "improvement_note": (
                    "GEDD output ties the requirement to observed PM failure-code "
                    "evidence and release gating behavior."
                ),
            }
        ]
