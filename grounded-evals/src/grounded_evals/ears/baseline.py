"""Generic baseline requirements for comparison with GEDD-driven output."""

from __future__ import annotations

from grounded_evals.ingest.models import AgentSpec
from grounded_evals.models.core import (
    EARSDocument,
    EARSPattern,
    EARSRequirement,
)


class BaselineGenerator:
    """Generate non-GEDD baseline requirements from an agent definition."""

    def generate(self, agent_spec: AgentSpec) -> EARSDocument:
        agent_name = agent_spec.name or "AI Agent"
        capabilities = agent_spec.capabilities or []
        requirements: list[EARSRequirement] = []

        if capabilities:
            for index, capability in enumerate(capabilities, start=1):
                cap_name = capability.name or f"Capability {index}"
                requirements.append(
                    EARSRequirement(
                        name=f"BASE-{index}: Support {cap_name}",
                        pattern=EARSPattern.UBIQUITOUS,
                        user_story=(
                            "As a user, I need the agent to perform its documented "
                            "capabilities reliably."
                        ),
                        acceptance_criteria=[
                            (
                                f"Given a user requests {cap_name}, the agent "
                                "provides a relevant response."
                            ),
                            "Given the request is unclear, the agent asks a clarifying question.",
                        ],
                        ears_statement=(
                            f"The {agent_name} system shall support {cap_name} "
                            "for in-scope users."
                        ),
                        priority_score=1.0,
                        dimension="quality",
                    )
                )
        else:
            requirements.append(
                EARSRequirement(
                    name="BASE-1: Provide Helpful Responses",
                    pattern=EARSPattern.UBIQUITOUS,
                    user_story="As a user, I need helpful and relevant responses.",
                    acceptance_criteria=[
                        "Given an in-scope request, the agent provides a relevant answer.",
                        "Given an out-of-scope request, the agent explains the limitation.",
                    ],
                    ears_statement=(
                        f"The {agent_name} system shall provide helpful, relevant, "
                        "and policy-compliant responses."
                    ),
                    priority_score=1.0,
                    dimension="quality",
                )
            )

        return EARSDocument(
            title=f"Baseline Requirements for {agent_name}",
            agent_name=agent_name,
            introduction=(
                "Generic baseline requirements generated from the agent definition, "
                "without PM failure-code evidence."
            ),
            requirements=requirements,
            non_functional_requirements=[
                "The agent should provide clear, relevant, and concise responses.",
            ],
            session_stats={"capabilities": len(capabilities)},
        )
