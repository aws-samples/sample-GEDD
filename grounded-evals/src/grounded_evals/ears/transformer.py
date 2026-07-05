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
                f"WHEN {agent_name} produces or is evaluated against a response "
                f"matching '{code.label}'\n"
                "THE SYSTEM SHALL classify the response as a release-blocking "
                "domain failure."
            )
            criteria = [
                (
                    f"WHEN {agent_name} produces or is evaluated against a response "
                    f"matching '{code.label}'\n"
                    "THE SYSTEM SHALL classify the response as a release-blocking "
                    "domain failure."
                ),
                (
                    f"WHEN the LLM-as-Judge evaluates a candidate response for "
                    f"'{code.label}'\n"
                    "THE SYSTEM SHALL return pass_fail, failure_code, severity, "
                    "rationale, evidence_references, and recommended_action."
                ),
                (
                    f"IF the LLM-as-Judge returns fail for '{code.label}'\n"
                    "THEN THE SYSTEM SHALL block promotion until the response is "
                    "corrected or explicitly approved by a human reviewer."
                ),
                (
                    f"WHILE the finding for '{code.label}' remains unresolved\n"
                    "THE SYSTEM SHALL retain traceability to the source annotation, "
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
                        f"As a domain owner, I want '{code.label}' failures to "
                        "be blocked by domain requirements and judge checks, so "
                        "that annotated release risks cannot silently ship."
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
                        "As a product owner, I need generated requirements to stay "
                        "connected to evaluation evidence."
                    ),
                    acceptance_criteria=[
                        (
                            "Given an evaluation dataset, every release requirement "
                            "references the evidence that motivated it."
                        ),
                        (
                            "Given no failure codes exist, the system reports that "
                            "additional PM annotation is required."
                        ),
                    ],
                    ears_statement=(
                        f"The {agent_name} release process shall retain traceability "
                        "between requirements, golden prompts, PM annotations, and judge criteria."
                    ),
                    priority_score=1.0,
                    dimension="traceability",
                )
            )
            requirements.append(self._judge_release_gate(agent_name, requirements))

        return EARSDocument(
            title=f"Kiro Domain Requirements for {agent_name}",
            agent_name=agent_name,
            introduction=(
                "Generated from GEDD error analysis and domain annotations. This "
                "Kiro-ready requirements.md uses EARS acceptance criteria so teams "
                "can move from requirements to design with traceable judge gates. "
                "Requirements are prioritized by observed severity, frequency, "
                "and product-risk dimension."
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
                    "The release workflow shall make unresolved critical findings "
                    "visible before promotion and preserve human override rationale."
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
                "WHEN a candidate response is submitted for release evaluation\n"
                "THE SYSTEM SHALL run an LLM-as-Judge prompt derived from annotated "
                "failure modes, EARS requirements, and domain definitions."
            ),
            (
                "WHEN the LLM-as-Judge completes evaluation\n"
                "THE SYSTEM SHALL return pass_fail, failure_code, severity, rationale, "
                "evidence_references, and recommended_action."
            ),
            (
                "IF any critical or unresolved domain failure is detected\n"
                "THEN THE SYSTEM SHALL block release until remediation or documented "
                "human override."
            ),
            (
                "WHILE requirements, annotations, or failure code definitions change\n"
                "THE SYSTEM SHALL refresh the judge prompt and calibration examples "
                "before promotion."
            ),
        ]

        return EARSRequirement(
            name="LLM-as-Judge Release Gate",
            pattern=EARSPattern.COMPLEX,
            user_story=(
                "As a release owner, I want domain requirements to define the "
                "LLM-as-Judge gate, so that Kiro implementation work has an "
                "executable acceptance signal."
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
