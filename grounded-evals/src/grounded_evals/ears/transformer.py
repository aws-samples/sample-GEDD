"""Transform GEDD session artifacts into EARS requirements."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from grounded_evals.guide.session import Session
from grounded_evals.models.core import (
    EARSDocument,
    EARSPattern,
    EARSRequirement,
    GlossaryEntry,
    TraceabilityLink,
    TraceabilityLinkType,
)


@dataclass(frozen=True)
class CodeMetrics:
    """Operational metadata used to prioritize a failure-code requirement."""

    severity: int = 3
    frequency: int = 1
    dimension: str = "quality"
    dimension_weight: float = 1.0


class EARSTransformer:
    """Build an EARS document from observed GEDD failure codes."""

    def transform(
        self,
        session: Session,
        code_metrics: dict[UUID, CodeMetrics],
        paradigm: object | None = None,
    ) -> EARSDocument:
        """Return a deterministic EARS document for the current session."""
        del paradigm
        agent_name = session.agent_spec.name or "AI Agent"
        requirements: list[EARSRequirement] = []
        glossary: list[GlossaryEntry] = []

        for index, code in enumerate(session.codes, start=1):
            metrics = code_metrics.get(code.id, CodeMetrics())
            definition = code.definition or code.agent_behavior_tested or code.label
            linked_prompts = [
                prompt
                for prompt in session.golden_prompts
                if getattr(prompt, "code_id", None) == code.id
            ]
            frequency = max(metrics.frequency, len(linked_prompts), 1)
            priority = (
                float(metrics.severity)
                * max(float(frequency), 1.0)
                * max(float(metrics.dimension_weight), 0.1)
            )
            req_name = f"REQ-{index}: Prevent {code.label}"
            statement = (
                f"WHEN {agent_name} produces a candidate customer-facing response "
                f"matching '{code.label}'\n"
                "THE JUDGE SUBAGENT SHALL classify the response as a "
                "release-blocking domain failure before it is shown to a customer."
            )
            criteria = [
                (
                    f"WHEN {agent_name} produces a candidate customer-facing response "
                    f"matching '{code.label}'\n"
                    "THE JUDGE SUBAGENT SHALL classify the response as a "
                    "release-blocking domain failure before it is shown to a customer."
                ),
                (
                    f"WHEN the LLM-as-Judge evaluates a candidate response for "
                    f"'{code.label}'\n"
                    "THE JUDGE SUBAGENT SHALL return pass_fail, failure_code, severity, "
                    "rationale, evidence_references, recommended_action, and customer_visible_block."
                ),
                (
                    f"IF the LLM-as-Judge returns fail for '{code.label}'\n"
                    "THEN THE JUDGE SUBAGENT SHALL block the customer-visible response until it is "
                    "corrected or explicitly approved by a human reviewer."
                ),
                (
                    f"WHILE the finding for '{code.label}' remains unresolved\n"
                    "THE JUDGE SUBAGENT SHALL retain traceability to the source annotation, "
                    "code definition, golden prompt evidence, and reviewer rationale."
                ),
            ]
            traceability_links = [
                TraceabilityLink(
                    link_type=TraceabilityLinkType.FAILURE_CODE,
                    target_id=code.id,
                    target_label=code.label,
                    description=definition,
                )
            ]
            traceability_links.extend(
                TraceabilityLink(
                    link_type=TraceabilityLinkType.GOLDEN_QUERY,
                    target_id=prompt.id,
                    target_label=prompt.prompt_text[:120],
                    description=prompt.expected_behavior or prompt.rationale,
                )
                for prompt in linked_prompts[:3]
            )
            requirements.append(
                EARSRequirement(
                    name=req_name,
                    pattern=EARSPattern.UNWANTED,
                    user_story=(
                        f"As a domain expert or product manager, I want '{code.label}' "
                        "failures to be blocked by a Kiro LLM-as-Judge subagent, so "
                        "customer-facing agent responses cannot bypass SME quality gates."
                    ),
                    acceptance_criteria=criteria,
                    ears_statement=statement,
                    priority_score=priority,
                    severity=metrics.severity,
                    frequency=frequency,
                    dimension=metrics.dimension,
                    dimension_weight=metrics.dimension_weight,
                    traceability_links=traceability_links,
                    source_failure_code_id=code.id,
                )
            )
            glossary.append(
                GlossaryEntry(
                    term=code.label,
                    definition=definition,
                    severity=metrics.severity,
                    frequency=metrics.frequency,
                )
            )

        if requirements:
            requirements.append(self._judge_release_gate(agent_name, requirements))
        else:
            requirements.append(
                EARSRequirement(
                    name="REQ-1: Maintain Evaluation Traceability",
                    pattern=EARSPattern.UBIQUITOUS,
                    user_story=(
                        "As a product owner, I need judge-subagent requirements to stay "
                        "connected to SME evaluation evidence."
                    ),
                    acceptance_criteria=[
                        (
                            "Given an evaluation dataset, every judge-subagent requirement "
                            "references the evidence that motivated it."
                        ),
                        (
                            "Given no failure codes exist, the system reports that "
                            "additional SME or PM annotation is required before a customer-response gate is generated."
                        ),
                    ],
                    ears_statement=(
                        f"The {agent_name} response-gating process shall retain traceability "
                        "between judge-subagent requirements, golden prompts, SME annotations, and judge criteria."
                    ),
                    priority_score=1.0,
                    dimension="traceability",
                )
            )
            requirements.append(self._judge_release_gate(agent_name, requirements))

        return EARSDocument(
            title=f"Kiro LLM-as-Judge Subagent Requirements for {agent_name}",
            agent_name=agent_name,
            introduction=(
                "Generated from GEDD error analysis and SME/PM annotations. This "
                "Kiro-ready requirements.md specifies the LLM-as-Judge subagent "
                "that evaluates candidate customer-facing responses before customers "
                "see them. Requirements use EARS acceptance criteria and are "
                "prioritized by observed severity, frequency, and product-risk dimension."
            ),
            glossary=glossary,
            requirements=requirements,
            non_functional_requirements=[
                (
                    "Before design starts, Kiro Analyze Requirements should be "
                    "used to check logical inconsistencies, ambiguities, conflicting "
                    "constraints, and gaps."
                ),
                (
                    "The LLM-as-Judge prompt shall be regenerated whenever failure "
                    "codes, severity, domain definitions, or acceptance criteria change."
                ),
                (
                    "The response-gating workflow shall make unresolved critical findings "
                    "visible before customer display and preserve human override rationale."
                ),
            ],
            session_stats={
                "codes": len(session.codes),
                "golden_prompts": len(session.golden_prompts),
                "memos": len(session.memos),
            },
        )

    def _judge_release_gate(
        self,
        agent_name: str,
        requirements: list[EARSRequirement],
    ) -> EARSRequirement:
        failure_links = [
            link
            for requirement in requirements
            for link in requirement.traceability_links
            if link.link_type == TraceabilityLinkType.FAILURE_CODE
        ]
        max_priority = max(
            (requirement.priority_score for requirement in requirements),
            default=1.0,
        )
        max_severity = max((requirement.severity for requirement in requirements), default=0)
        total_frequency = sum(requirement.frequency for requirement in requirements)

        criteria = [
            (
                "WHEN a candidate customer-facing response is submitted for evaluation\n"
                "THE JUDGE SUBAGENT SHALL run an LLM-as-Judge prompt derived from annotated "
                "failure modes, EARS requirements, and domain definitions."
            ),
            (
                "WHEN the LLM-as-Judge completes evaluation\n"
                "THE JUDGE SUBAGENT SHALL return pass_fail, failure_code, severity, rationale, "
                "evidence_references, recommended_action, and customer_visible_block."
            ),
            (
                "IF any critical or unresolved domain failure is detected\n"
                "THEN THE JUDGE SUBAGENT SHALL block the response from customer visibility "
                "until remediation or documented human override."
            ),
            (
                "WHILE requirements, annotations, or failure code definitions change\n"
                "THE JUDGE SUBAGENT SHALL refresh the judge prompt and calibration examples "
                "before promotion."
            ),
        ]

        return EARSRequirement(
            name="LLM-as-Judge Release Gate",
            pattern=EARSPattern.COMPLEX,
            user_story=(
                "As a release owner, I want Kiro requirements to define the "
                "LLM-as-Judge subagent gate, so candidate customer-facing responses "
                "have an executable SME acceptance signal before they are shown."
            ),
            acceptance_criteria=criteria,
            ears_statement=criteria[0],
            priority_score=max_priority + 1.0,
            severity=max_severity,
            frequency=total_frequency,
            dimension="release_gate",
            dimension_weight=1.0,
            traceability_links=failure_links,
        )
