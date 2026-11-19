"""One turn of the GEDD RL eval flywheel for an AI agent app.

  codebook vN ─► taste reward ─► 1 AUDIT     degenerate policies must not out-score the base policy
                                 2 TRAIN     RL under the taste reward, tripwire on an independent audit signal
                                 3 MEASURE   locked tasks, scored by expert-standard checks, McNemar + cluster bootstrap
                                 4 SHIP?     promote only if taste rose significantly and the tripwire stayed quiet
                                 5 OPERATE   gate production traffic, PPI++ estimate from a random expert sample
                                 6 GROW      expert labels recalibrate the judges; failures the codebook lacks ─► vN+1

The product team supplies an `AgentApp`: its tasks, a way to build the reward from a codebook, a
trainer, its experts, and the check that defines "kept the product's taste" on the locked set.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from grounded_evals.flywheel.audit import AuditReport, audit_reward
from grounded_evals.flywheel.codebook import Codebook
from grounded_evals.flywheel.harness import AuditFn, Policy, RunResult, Trainer, run
from grounded_evals.flywheel.production import (
    CodeProposal,
    Expert,
    ProductionReport,
    grow_codebook,
    merge_proposals,
    production_round,
    propose_from,
)
from grounded_evals.flywheel.reward import TasteReward
from grounded_evals.reward.gate import GatePolicy
from grounded_evals.reward.model import PlattCalibrator
from grounded_evals.stats.significance import Comparison, compare

Task = Mapping[str, Any]


@dataclass
class AgentApp:
    train_tasks: Sequence[Task]
    locked_tasks: Sequence[Task]  # never trained on, never used to tune the reward
    production_tasks: Sequence[Task]
    make_reward: Callable[[Codebook], TasteReward]
    make_trainer: Callable[[Policy], Trainer]  # starts from the given policy
    degenerate: Mapping[str, Policy]
    expert: Expert
    taste_ok: Callable[
        [Task, Mapping[str, Any]], bool
    ]  # locked-set outcome: no failure by the expert standard
    audit: AuditFn | None = (
        None  # independent signal for the tripwire (verifiable check or other judge)
    )
    group_of: Callable[[Task], Hashable] = lambda t: t["id"]


@dataclass
class RoundConfig:
    steps: int = 30
    tasks_per_step: int = 8
    group: int = 8
    window: int = 3
    audit_samples: int = 4
    random_labels: int = 40
    targeted_labels: int = 20
    propose_at: int = 3
    gate: GatePolicy | None = None  # thresholds are product decisions; default GatePolicy()
    seed: int = 0


@dataclass
class RoundReport:
    round: int
    codebook_version: int
    audit: AuditReport
    training: RunResult | None
    locked: Comparison | None  # trained (a) vs incoming (b)
    promoted: bool
    production: ProductionReport
    next_codebook: Codebook
    notes: list[str] = field(default_factory=list)
    tripwire_proposals: list[CodeProposal] = field(default_factory=list)

    @property
    def uncalibrated(self) -> list[str]:
        """Judge-scored codes with no calibrator yet (too few expert-labelled positives, or new)."""
        have = {k.split(":", 1)[1] for k in self.production.calibrators} | set(
            self.production.exact_codes
        )
        return [c for c in self.next_codebook.names if c not in have]

    @property
    def next_calibrators(self) -> dict[str, PlattCalibrator]:
        valid = set(self.next_codebook.names)
        return {k: v for k, v in self.production.calibrators.items() if k.split(":", 1)[1] in valid}

    def summary(self) -> dict:
        out = {
            "round": self.round,
            "codebook_version": self.codebook_version,
            "audit_passed": self.audit.passed,
            "loopholes": self.audit.loopholes,
            "audit_margin": round(self.audit.margin, 4),
            "tripped": bool(self.training and self.training.tripped),
            "promoted": self.promoted,
            "gate": self.production.gate,
            "judge_clean_rate": round(self.production.judge_clean_rate, 4),
            "ppi_clean_rate": round(self.production.clean_rate.estimate, 4),
            "ppi_ci": [
                round(max(0.0, self.production.clean_rate.lo), 4),
                round(min(1.0, self.production.clean_rate.hi), 4),
            ],
            "expert_labels": self.production.expert_labels,
            "uncalibrated_judge_codes": self.uncalibrated,
            "new_codes": sorted(
                {p.code for p in self.production.proposals + self.tripwire_proposals}
            ),
            "found_by_tripwire": [p.code for p in self.tripwire_proposals],
            "next_codebook_version": self.next_codebook.version,
            "notes": self.notes,
        }
        if self.locked:
            out["locked"] = {
                "n": self.locked.n,
                "trained": round(self.locked.acc_a, 4),
                "incoming": round(self.locked.acc_b, 4),
                "delta": round(self.locked.delta, 4),
                "mcnemar_p": self.locked.mcnemar.p_value,
                "ci": [round(self.locked.bootstrap.lo, 4), round(self.locked.bootstrap.hi, 4)],
                "significant": self.locked.significant,
            }
        return out


def measure(app: AgentApp, a: Policy, b: Policy, seed: int) -> Comparison:
    tasks = list(app.locked_tasks)
    out_a = [app.taste_ok(t, a.sample(t, 1)[0]) for t in tasks]
    out_b = [app.taste_ok(t, b.sample(t, 1)[0]) for t in tasks]
    return compare(out_a, out_b, [app.group_of(t) for t in tasks], seed=seed)


def run_round(
    app: AgentApp,
    codebook: Codebook,
    policy: Policy,
    *,
    round_no: int = 1,
    config: RoundConfig | None = None,
    calibrators: dict[str, PlattCalibrator] | None = None,
    on_step: Callable[[dict], None] | None = None,
) -> tuple[RoundReport, Policy]:
    """One flywheel turn. Returns the report and the policy to carry into the next round."""
    cfg = config or RoundConfig()
    reward = app.make_reward(codebook)
    reward.calibrators = dict(calibrators or {})
    notes: list[str] = []

    report = audit_reward(
        reward,
        app.train_tasks,
        {"incoming": policy, **app.degenerate},
        base="incoming",
        degenerate=list(app.degenerate),
        n=cfg.audit_samples,
        audit=app.audit,
    )
    training, locked, promoted, nxt = None, None, False, policy
    tripwire_props: list[CodeProposal] = []
    if not report.passed:
        notes.append(
            f"reward audit failed ({', '.join(report.loopholes)}): fix the reward before training"
        )
    else:
        trainer = app.make_trainer(policy)
        training = run(
            trainer,
            app.train_tasks,
            reward=reward,
            audit=app.audit,
            steps=cfg.steps,
            tasks_per_step=cfg.tasks_per_step,
            group=cfg.group,
            window=cfg.window,
            on_step=on_step,
        )
        trained = trainer.policy()
        locked = measure(app, trained, policy, cfg.seed + round_no)
        if training.tripped:
            tripwire_props = propose_from(
                training.review_queue, codebook, app.expert, cfg.propose_at
            )
            notes.append(
                f"tripwire at step {training.history[-1]['step']}: reward rose while the audit signal "
                f"fell; experts reviewed the {len(training.review_queue)} worst traces"
            )
        elif locked.significant and locked.delta > 0:
            promoted, nxt = True, trained
        else:
            notes.append("trained policy not promoted: no significant taste gain on the locked set")

    traffic = [(t, nxt.sample(t, 1)[0]) for t in app.production_tasks]
    prod = production_round(
        traffic,
        reward,
        app.expert,
        random_labels=cfg.random_labels,
        targeted_labels=cfg.targeted_labels,
        propose_at=cfg.propose_at,
        gate=cfg.gate,
        seed=cfg.seed + round_no,
    )
    grown = grow_codebook(codebook, merge_proposals(tripwire_props, prod.proposals), app.expert)
    return RoundReport(
        round_no,
        codebook.version,
        report,
        training,
        locked,
        promoted,
        prod,
        grown,
        notes,
        tripwire_props,
    ), nxt


def run_flywheel(
    app: AgentApp,
    codebook: Codebook,
    policy: Policy,
    rounds: int,
    *,
    config: RoundConfig | None = None,
) -> tuple[list[RoundReport], Policy, Codebook]:
    reports, calibrators = [], {}
    for r in range(1, rounds + 1):
        rep, policy = run_round(
            app, codebook, policy, round_no=r, config=config, calibrators=calibrators
        )
        reports.append(rep)
        codebook, calibrators = rep.next_codebook, rep.next_calibrators
    return reports, policy, codebook
