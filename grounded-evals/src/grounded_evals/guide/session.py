from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from grounded_evals.ingest.models import AgentSpec
from grounded_evals.models.core import (
    Category,
    Code,
    CoverageReport,
    GoldenDataset,
    GoldenPrompt,
    Memo,
)


class Session(BaseModel):
    agent_spec: AgentSpec = Field(default_factory=AgentSpec)
    categories: list[Category] = Field(default_factory=list)
    codes: list[Code] = Field(default_factory=list)
    golden_prompts: list[GoldenPrompt] = Field(default_factory=list)
    memos: list[Memo] = Field(default_factory=list)
    current_step: int = 1
    created_at: datetime = Field(default_factory=datetime.now)

    def update_agent(self, **kwargs: str) -> None:
        for key, value in kwargs.items():
            if hasattr(self.agent_spec, key):
                setattr(self.agent_spec, key, value)

    def add_golden_prompt(self, prompt: GoldenPrompt) -> None:
        self.golden_prompts.append(prompt)

    def add_category(self, category: Category) -> None:
        self.categories.append(category)

    def add_code(self, code: Code) -> None:
        self.codes.append(code)

    def get_category(self, category_id: UUID) -> Category | None:
        for cat in self.categories:
            if cat.id == category_id:
                return cat
        return None

    def prompts_for_category(self, category_id: UUID) -> list[GoldenPrompt]:
        return [p for p in self.golden_prompts if p.category_id == category_id]

    def coverage(self) -> CoverageReport:
        categories_with_prompts = {
            p.category_id for p in self.golden_prompts
        }
        saturated = [c for c in self.categories if c.saturation.value == "saturated"]
        gaps = [
            f"No prompts for: {c.name}"
            for c in self.categories
            if c.id not in categories_with_prompts
        ]
        total_cats = len(self.categories)
        return CoverageReport(
            total_prompts=len(self.golden_prompts),
            categories_covered=len(categories_with_prompts),
            categories_total=total_cats,
            saturated_categories=len(saturated),
            gaps=gaps,
            saturation_score=(len(saturated) / total_cats) if total_cats > 0 else 0.0,
        )

    def to_golden_dataset(self) -> GoldenDataset:
        return GoldenDataset(
            agent_name=self.agent_spec.name,
            agent_description=self.agent_spec.description,
            prompts=self.golden_prompts,
            categories=self.categories,
            codes=self.codes,
            memos=self.memos,
        )
