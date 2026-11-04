"""Codebook-grounded reward model and response gate (the centre of the GEDD flywheel)."""

from grounded_evals.reward.gate import GateAction, GateDecision, GatePolicy
from grounded_evals.reward.model import (
    SEVERITY_WEIGHTS,
    CodebookRewardModel,
    FailureCode,
    PlattCalibrator,
    RewardResult,
    scalar_reward,
)

__all__ = [
    "SEVERITY_WEIGHTS",
    "CodebookRewardModel",
    "FailureCode",
    "GateAction",
    "GateDecision",
    "GatePolicy",
    "PlattCalibrator",
    "RewardResult",
    "scalar_reward",
]
