from __future__ import annotations

from pathlib import Path

import yaml

from grounded_evals.ingest.models import AgentSpec, Capability, Persona


def parse_agent_spec(path: Path | str) -> AgentSpec:
    path = Path(path)
    with path.open() as f:
        raw = yaml.safe_load(f)

    agent_data = raw.get("agent", raw)

    capabilities = [
        Capability(name=c) if isinstance(c, str) else Capability(**c)
        for c in agent_data.get("capabilities", [])
    ]

    target_users = []
    for u in agent_data.get("target_users", []):
        if isinstance(u, dict):
            name = u.get("name") or u.get("persona", "")
            target_users.append(Persona(name=name, description=u.get("description", "")))
        else:
            target_users.append(Persona(name=str(u)))

    return AgentSpec(
        name=agent_data.get("name", ""),
        description=agent_data.get("description", ""),
        capabilities=capabilities,
        target_users=target_users,
        known_edge_cases=agent_data.get("known_edge_cases", []),
        constraints=agent_data.get("constraints", []),
        domain_context=agent_data.get("domain_context", ""),
        system_prompt=agent_data.get("system_prompt", ""),
    )
