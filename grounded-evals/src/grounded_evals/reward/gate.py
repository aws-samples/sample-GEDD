"""Response gate: turn a codebook reward into allow / revise / human review / block.

Order of precedence, most cautious first:
  1. block   — P(any blocking code) >= block_threshold
  2. review  — the judge members disagree (std >= uncertainty_threshold)
  3. allow   — conservative reward >= allow_threshold
  4. revise  — conservative reward >= revise_threshold
  5. review  — everything else (low reward but nothing the codebook says to block)

Thresholds are product decisions; calibrate them on expert-labelled cases before the gate blocks
live traffic, and run in shadow mode first.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from grounded_evals.reward.model import RewardResult


class GateAction(str, Enum):
    ALLOW = "allow"
    REVISE = "revise_response"
    REVIEW = "request_human_review"
    BLOCK = "block"


@dataclass(frozen=True)
class GateDecision:
    action: GateAction
    reward: float
    failure_code: str | None
    reason: str

    @property
    def customer_visible_block(self) -> bool:
        return self.action is not GateAction.ALLOW


@dataclass(frozen=True)
class GatePolicy:
    allow_threshold: float = 0.85
    revise_threshold: float = 0.6
    block_threshold: float = 0.5
    uncertainty_threshold: float = 0.15

    def __post_init__(self) -> None:
        if not 0 <= self.revise_threshold <= self.allow_threshold <= 1:
            raise ValueError("need 0 <= revise_threshold <= allow_threshold <= 1")

    def decide(self, r: RewardResult) -> GateDecision:
        if r.blocking_prob >= self.block_threshold:
            return GateDecision(
                GateAction.BLOCK, r.reward, r.top_code, f"blocking code p={r.blocking_prob:.2f}"
            )
        if r.std >= self.uncertainty_threshold:
            return GateDecision(
                GateAction.REVIEW, r.reward, r.top_code, f"judges disagree (std={r.std:.2f})"
            )
        if r.reward >= self.allow_threshold:
            return GateDecision(GateAction.ALLOW, r.reward, None, "reward above allow threshold")
        if r.reward >= self.revise_threshold:
            return GateDecision(GateAction.REVISE, r.reward, r.top_code, "fixable failure")
        return GateDecision(GateAction.REVIEW, r.reward, r.top_code, "low reward, no blocking code")
