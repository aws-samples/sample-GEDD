from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CodeType(str, Enum):
    IN_VIVO = "in_vivo"
    CONSTRUCTED = "constructed"
    PROCESS = "process"
    DESCRIPTIVE = "descriptive"
    ANALYTIC = "analytic"


class MemoType(str, Enum):
    CODE = "code"
    THEORETICAL = "theoretical"
    OPERATIONAL = "operational"
    REFLECTIVE = "reflective"


class SaturationStatus(str, Enum):
    UNSATURATED = "unsaturated"
    APPROACHING = "approaching"
    SATURATED = "saturated"


class Dimension(BaseModel):
    name: str
    low_anchor: str
    high_anchor: str
    description: str = ""


class Property(BaseModel):
    name: str
    dimensions: list[Dimension] = Field(default_factory=list)
    description: str = ""


class Code(BaseModel):
    """A conceptual label for a prompt category discovered during fracturing."""

    id: UUID = Field(default_factory=uuid4)
    label: str
    code_type: CodeType
    definition: str = ""
    exemplar_prompts: list[str] = Field(default_factory=list)
    properties: list[Property] = Field(default_factory=list)
    agent_behavior_tested: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Category(BaseModel):
    """Higher-order grouping of related codes (prompt categories)."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    definition: str = ""
    properties: list[Property] = Field(default_factory=list)
    code_ids: list[UUID] = Field(default_factory=list)
    subcategory_ids: list[UUID] = Field(default_factory=list)
    saturation: SaturationStatus = SaturationStatus.UNSATURATED
    created_at: datetime = Field(default_factory=datetime.now)


class ParadigmModel(BaseModel):
    """Axial coding: relates categories via conditions, strategies, consequences."""

    phenomenon: Category
    causal_conditions: list[Category] = Field(default_factory=list)
    context: list[Category] = Field(default_factory=list)
    intervening_conditions: list[Category] = Field(default_factory=list)
    action_strategies: list[Category] = Field(default_factory=list)
    consequences: list[Category] = Field(default_factory=list)


class Memo(BaseModel):
    """PM's documented rationale for prompt categories and design decisions."""

    id: UUID = Field(default_factory=uuid4)
    memo_type: MemoType
    title: str
    content: str
    related_code_ids: list[UUID] = Field(default_factory=list)
    related_category_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class GoldenPrompt(BaseModel):
    """A single prompt in the golden dataset with full provenance."""

    id: UUID = Field(default_factory=uuid4)
    prompt_text: str
    category_id: UUID
    code_id: UUID | None = None
    property_values: dict[str, str] = Field(default_factory=dict)
    expected_behavior: str = ""
    rationale: str = ""
    is_edge_case: bool = False
    is_adversarial: bool = False
    turn_count: int = 1
    created_at: datetime = Field(default_factory=datetime.now)


class GoldenDataset(BaseModel):
    """The complete golden dataset output with traceability."""

    id: UUID = Field(default_factory=uuid4)
    agent_name: str
    agent_description: str = ""
    prompts: list[GoldenPrompt] = Field(default_factory=list)
    categories: list[Category] = Field(default_factory=list)
    codes: list[Code] = Field(default_factory=list)
    memos: list[Memo] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    version: str = "0.1.0"


class JudgeCriterion(BaseModel):
    name: str
    description: str
    scoring_rubric: dict[int, str] = Field(default_factory=dict)
    source_category_id: UUID | None = None
    weight: float = 1.0


class JudgeRubric(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    criteria: list[JudgeCriterion] = Field(default_factory=list)
    judge_prompt_template: str = ""
    paradigm_model: ParadigmModel | None = None
    version: str = "0.1.0"
    created_at: datetime = Field(default_factory=datetime.now)


class CoverageReport(BaseModel):
    """Analysis of how well the golden dataset covers the agent's domain."""

    total_prompts: int = 0
    categories_covered: int = 0
    categories_total: int = 0
    saturated_categories: int = 0
    gaps: list[str] = Field(default_factory=list)
    redundancies: list[str] = Field(default_factory=list)
    saturation_score: float = 0.0
