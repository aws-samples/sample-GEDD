"""Trainer-agnostic RL harness for agent apps: groups, GRPO advantages, per-step audit, tripwire.

The harness owns everything except the gradient step. A trainer (TRL, verl, OpenRLHF or your own
loop) plugs in through two methods; a policy is anything that can produce traces for a task.

  Policy   sample(task, n) -> list[trace]          trace: dict with at least "tool_calls"
  Trainer  policy() -> Policy                      the current weights
           update(groups) -> dict                  one optimiser step from the scored groups

Every step logs the trained reward *and* an independent audit signal: a verifiable check, a
different-family judge, or expert labels. The tripwire stops the run when the trained reward
rises while the audit signal falls: the moment training starts trading the product's taste away.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from statistics import fmean
from typing import Any, Protocol

Trace = dict[str, Any]
RewardFn = Callable[[Mapping[str, Any], Mapping[str, Any]], float | None]
AuditFn = Callable[[Mapping[str, Any], Mapping[str, Any]], float]


class Policy(Protocol):
    def sample(self, task: Mapping[str, Any], n: int) -> list[Trace]: ...


class Trainer(Protocol):
    def policy(self) -> Policy: ...

    def update(self, groups: list[Group]) -> dict: ...


@dataclass
class Group:
    task: Mapping[str, Any]
    traces: list[Trace]
    rewards: list[float | None]
    advantages: list[float] | None  # None: flat or scorer-failed group, carries no learning signal
    audit: list[float] = field(default_factory=list)

    @property
    def scorer_failed(self) -> bool:
        return any(r is None for r in self.rewards)


def grpo_advantages(rewards: Sequence[float | None], clip: float = 2.0) -> list[float] | None:
    """(r - group mean) / group std, clipped. None if any score is missing or the group is flat."""
    if len(rewards) < 2 or any(r is None for r in rewards):
        return None
    rs = [float(r) for r in rewards]  # type: ignore[arg-type]
    if max(rs) - min(rs) < 1e-9:
        return None
    mean = fmean(rs)
    std = (sum((r - mean) ** 2 for r in rs) / (len(rs) - 1)) ** 0.5
    return [max(-clip, min(clip, (r - mean) / (std + 1e-8))) for r in rs]


@dataclass
class Tripwire:
    """Fires when, over the last `window` steps versus the `window` before, the trained reward
    rose while the audit signal fell by more than `min_drop`. Windows smooth out step noise."""

    window: int = 3
    min_drop: float = 0.05
    _hist: list[tuple[float, float]] = field(default_factory=list)

    def update(self, reward: float, audit: float) -> bool:
        self._hist.append((reward, audit))
        w = self.window
        if len(self._hist) < 2 * w:
            return False
        prev, last = self._hist[-2 * w : -w], self._hist[-w:]
        d_reward = fmean(r for r, _ in last) - fmean(r for r, _ in prev)
        d_audit = fmean(a for _, a in last) - fmean(a for _, a in prev)
        return d_reward > 0 and d_audit < -self.min_drop


def score_group(
    task: Mapping[str, Any],
    traces: list[Trace],
    reward: RewardFn,
    audit: AuditFn | None = None,
    clip: float = 2.0,
) -> Group:
    rewards = [reward(task, t) for t in traces]
    return Group(
        task,
        traces,
        rewards,
        grpo_advantages(rewards, clip),
        [audit(task, t) for t in traces] if audit else [],
    )


@dataclass
class RunResult:
    history: list[dict]
    tripped: bool
    review_queue: list[tuple[Mapping[str, Any], Trace]]  # worst traces of the tripping step


def run(
    source: Policy | Trainer,
    tasks: Sequence[Mapping[str, Any]],
    *,
    reward: RewardFn,
    audit: AuditFn | None = None,
    steps: int,
    tasks_per_step: int,
    group: int,
    window: int = 3,
    clip: float = 2.0,
    on_step: Callable[[dict], None] | None = None,
) -> RunResult:
    """Sample → score → advantages → (if a trainer is given) update, once per step.

    With a plain Policy nothing trains: the run measures headroom (how many groups GRPO could
    learn from) and the reward/audit relationship before any GPU time is spent.
    """
    trainer = source if hasattr(source, "update") else None
    wire, history = Tripwire(window), []
    for step in range(steps):
        policy = trainer.policy() if trainer else source  # type: ignore[union-attr]
        batch = [tasks[(step * tasks_per_step + i) % len(tasks)] for i in range(tasks_per_step)]
        groups = [score_group(t, policy.sample(t, group), reward, audit, clip) for t in batch]
        scored = [r for g in groups for r in g.rewards if r is not None]
        audits = [a for g in groups for a in g.audit]
        m = {
            "step": step,
            "reward": fmean(scored) if scored else 0.0,
            "audit": fmean(audits) if audits else None,
            "tool_calls": fmean(t.get("tool_calls", 0) for g in groups for t in g.traces),
            "groups": len(groups),
            "flat_groups": sum(g.advantages is None and not g.scorer_failed for g in groups),
            "scorer_failed_groups": sum(g.scorer_failed for g in groups),
        }
        if trainer:
            m.update(
                {
                    f"train/{k}": v
                    for k, v in trainer.update([g for g in groups if g.advantages]).items()
                }
            )
        history.append(m)
        if on_step:
            on_step(m)
        if m["audit"] is not None and wire.update(m["reward"], m["audit"]):
            worst = sorted(
                ((a, g.task, t) for g in groups for a, t in zip(g.audit, g.traces, strict=True)),
                key=lambda x: x[0],
            )[:20]
            return RunResult(history, True, [(task, t) for _, task, t in worst])
    return RunResult(history, False, [])
