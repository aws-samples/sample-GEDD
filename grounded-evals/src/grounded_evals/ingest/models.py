from __future__ import annotations

from pydantic import BaseModel, Field


class Persona(BaseModel):
    name: str
    description: str = ""


class Capability(BaseModel):
    name: str
    description: str = ""


class AgentSpec(BaseModel):
    name: str = ""
    description: str = ""
    capabilities: list[Capability] = Field(default_factory=list)
    target_users: list[Persona] = Field(default_factory=list)
    known_edge_cases: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    domain_context: str = ""
    system_prompt: str = ""
