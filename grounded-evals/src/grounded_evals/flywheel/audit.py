"""Reward audit: before any training, check that the reward can't be won without the product's taste.

Score the base policy and a set of degenerate policies (do nothing, always the fastest action,
refuse everything, ...) under the reward. Any degenerate policy that scores at or above the base
policy is a loophole RL will find, because RL climbs whatever the reward pays for (finding F8).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import fmean
from typing import Any

from grounded_evals.flywheel.harness import AuditFn, Policy, RewardFn


@dataclass(frozen=True)
class AuditRow:
    policy: str
    reward: float
    audit: float | None
    scorer_failures: int
    degenerate: bool
    loophole: bool  # degenerate and reward >= base reward


@dataclass(frozen=True)
class AuditReport:
    base: str
    rows: list[AuditRow]

    @property
    def loopholes(self) -> list[str]:
        return [r.policy for r in self.rows if r.loophole]

    @property
    def passed(self) -> bool:
        return not self.loopholes

    @property
    def margin(self) -> float:
        """Base reward minus the best degenerate reward (> 0 means no degenerate policy wins)."""
        base = next(r.reward for r in self.rows if r.policy == self.base)
        degen = [r.reward for r in self.rows if r.degenerate]
        return base - max(degen) if degen else float("inf")


def audit_reward(
    reward: RewardFn,
    tasks: Sequence[Mapping[str, Any]],
    policies: Mapping[str, Policy],
    *,
    base: str,
    degenerate: Sequence[str],
    n: int = 4,
    audit: AuditFn | None = None,
) -> AuditReport:
    if base not in policies:
        raise ValueError(f"base policy {base!r} not in policies")
    rows, base_reward = [], None
    for name in [base, *[p for p in policies if p != base]]:
        rs, audits, failed = [], [], 0
        for task in tasks:
            for trace in policies[name].sample(task, n):
                r = reward(task, trace)
                if r is None:
                    failed += 1
                else:
                    rs.append(r)
                if audit:
                    audits.append(audit(task, trace))
        mean = fmean(rs) if rs else 0.0
        if name == base:
            base_reward = mean
        is_degen = name in degenerate
        rows.append(
            AuditRow(
                name,
                mean,
                fmean(audits) if audits else None,
                failed,
                is_degen,
                is_degen and base_reward is not None and mean >= base_reward,
            )
        )
    return AuditReport(base, rows)
