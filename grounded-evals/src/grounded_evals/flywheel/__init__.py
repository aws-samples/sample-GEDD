"""The GEDD RL eval flywheel for AI agent apps: keep the product's taste while you train.

codebook (the experts' standard) → taste reward → reward audit → RL with a tripwire → locked-set
measurement → gated production with PPI++ → experts grow the codebook → next round.
"""

from grounded_evals.flywheel.audit import AuditReport, AuditRow, audit_reward
from grounded_evals.flywheel.codebook import Code, Codebook
from grounded_evals.flywheel.harness import (
    Group,
    Policy,
    RunResult,
    Trainer,
    Tripwire,
    grpo_advantages,
    run,
)
from grounded_evals.flywheel.loop import (
    AgentApp,
    RoundConfig,
    RoundReport,
    measure,
    run_flywheel,
    run_round,
)
from grounded_evals.flywheel.production import (
    CodeProposal,
    Expert,
    ProductionReport,
    grow_codebook,
    merge_proposals,
    production_round,
    propose_from,
)
from grounded_evals.flywheel.reward import (
    Detector,
    LLMJudgeDetector,
    RewardBreakdown,
    RuleDetector,
    TasteReward,
    parse_detection,
)

__all__ = [
    "AgentApp",
    "AuditReport",
    "AuditRow",
    "Code",
    "CodeProposal",
    "Codebook",
    "Detector",
    "Expert",
    "Group",
    "LLMJudgeDetector",
    "Policy",
    "ProductionReport",
    "RewardBreakdown",
    "RoundConfig",
    "RoundReport",
    "RuleDetector",
    "RunResult",
    "TasteReward",
    "Trainer",
    "Tripwire",
    "audit_reward",
    "grow_codebook",
    "grpo_advantages",
    "measure",
    "merge_proposals",
    "parse_detection",
    "production_round",
    "propose_from",
    "run",
    "run_flywheel",
    "run_round",
]
