"""Production half of the flywheel: gate every trace, estimate true taste, let experts grow the codebook.

1. **Gate** every production trace with the taste reward (allow / revise / review / block).
2. **Estimate** the real clean rate with PPI++: judge scores on every trace plus expert labels on a
   small *random* sample give an unbiased estimate with a valid interval. If it disagrees with
   the judge's own estimate, the judge (and any reward built on it) is drifting.
3. **Review** a second, *targeted* sample: the traces the judge is least sure about. These are
   for learning, not for estimation, so they never enter the PPI sample.
4. **Recalibrate**: every expert label also refits the judge members' Platt calibrators for the
   next round's reward and gate.
5. **Grow**: failures experts name that the codebook doesn't have become proposals; once a
   proposal recurs, experts define it (severity, blocking) and it enters the next codebook version.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from grounded_evals.flywheel.codebook import Code, Codebook
from grounded_evals.flywheel.harness import Trace
from grounded_evals.flywheel.reward import TasteReward, fit_calibrators
from grounded_evals.reward.gate import GatePolicy
from grounded_evals.reward.model import PlattCalibrator
from grounded_evals.stats.ppi import MeanEstimate, classical_mean, ppi_mean


class Expert(Protocol):
    def label(self, task: Mapping[str, Any], trace: Mapping[str, Any]) -> set[str]:
        """Failure codes present in the trace; may name codes the codebook doesn't have yet."""
        ...

    def define(self, code: str) -> Code:
        """Turn a recurring new failure into a codebook entry (description, severity, blocking)."""
        ...


@dataclass(frozen=True)
class CodeProposal:
    code: str
    count: int
    examples: list[str]


@dataclass
class ProductionReport:
    traces: int
    gate: dict[str, int]
    judge_clean_rate: float
    clean_rate: MeanEstimate  # PPI++ on the random expert sample
    expert_only: MeanEstimate  # the same sample without the judge, for comparison
    expert_labels: int
    proposals: list[CodeProposal]
    review_queue: list[str] = field(default_factory=list)
    calibrators: dict[str, PlattCalibrator] = field(default_factory=dict)  # for the next round
    exact_codes: list[str] = field(
        default_factory=list
    )  # decided by exact rule checks, need no calibration

    @property
    def judge_drift(self) -> float:
        """Judge's clean-rate estimate minus the PPI++ estimate (> 0: the judge is too lenient)."""
        return self.judge_clean_rate - self.clean_rate.estimate


def production_round(
    traffic: Sequence[tuple[Mapping[str, Any], Trace]],
    reward: TasteReward,
    expert: Expert,
    *,
    random_labels: int = 40,
    targeted_labels: int = 20,
    propose_at: int = 3,
    gate: GatePolicy | None = None,
    seed: int = 0,
) -> ProductionReport:
    if len(traffic) < random_labels + 2:
        raise ValueError("need more traffic than the random expert sample")
    gate = gate or GatePolicy()
    blocking = [c.code for c in reward.codebook.codes if c.blocking]
    scored = [(task, trace, reward.breakdown(task, trace)) for task, trace in traffic]
    decisions = Counter(
        gate.decide(b.as_reward_result(blocking)).action.value for _, _, b in scored
    )

    rng = random.Random(seed)
    idx = list(range(len(scored)))
    rng.shuffle(idx)
    rand, rest = idx[:random_labels], idx[random_labels:]
    labels = {i: expert.label(scored[i][0], scored[i][1]) for i in rand}

    f = [scored[i][2].p_clean for i in idx]
    y_l = [float(not labels[i]) for i in rand]
    f_l = [scored[i][2].p_clean for i in rand]
    f_u = [scored[i][2].p_clean for i in rest]

    by_uncertainty = sorted(rest, key=lambda i: abs(scored[i][2].p_clean - 0.5))[:targeted_labels]
    for i in by_uncertainty:
        labels[i] = expert.label(scored[i][0], scored[i][1])

    unknown: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    for i, codes in labels.items():
        for c in codes - set(reward.codebook.names):
            unknown[c] += 1
            examples.setdefault(c, []).append(str(scored[i][1].get("id", i)))
    proposals = [
        CodeProposal(c, n, examples[c][:5]) for c, n in unknown.most_common() if n >= propose_at
    ]
    exact_names = {getattr(d, "name", "") for d in reward.detectors if getattr(d, "exact", False)}
    exact_codes = sorted(
        {c for _, _, b in scored for n, det in b.raw.items() if n in exact_names for c in det}
    )
    labelled = list(labels)
    calibrators = fit_calibrators(
        reward, [scored[i][2] for i in labelled], [labels[i] for i in labelled]
    )

    return ProductionReport(
        traces=len(scored),
        gate=dict(decisions),
        judge_clean_rate=sum(f) / len(f),
        clean_rate=ppi_mean(y_l, f_l, f_u),
        expert_only=classical_mean(y_l),
        expert_labels=len(labels),
        proposals=proposals,
        review_queue=[str(scored[i][1].get("id", i)) for i in by_uncertainty],
        calibrators=calibrators,
        exact_codes=exact_codes,
    )


def propose_from(
    items: Sequence[tuple[Mapping[str, Any], Trace]],
    codebook: Codebook,
    expert: Expert,
    propose_at: int = 3,
) -> list[CodeProposal]:
    """Expert-label a set of traces (e.g. the tripwire's review queue) and propose recurring new codes."""
    unknown: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    for i, (task, trace) in enumerate(items):
        for c in expert.label(task, trace) - set(codebook.names):
            unknown[c] += 1
            examples.setdefault(c, []).append(str(trace.get("id", i)))
    return [
        CodeProposal(c, n, examples[c][:5]) for c, n in unknown.most_common() if n >= propose_at
    ]


def merge_proposals(*groups: Sequence[CodeProposal]) -> list[CodeProposal]:
    count: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    for g in groups:
        for p in g:
            count[p.code] += p.count
            examples.setdefault(p.code, []).extend(p.examples)
    return [CodeProposal(c, n, examples[c][:5]) for c, n in count.most_common()]


def grow_codebook(
    codebook: Codebook, proposals: Sequence[CodeProposal], expert: Expert
) -> Codebook:
    for p in proposals:
        if p.code not in codebook:
            codebook = codebook.add(
                expert.define(p.code), f"named by experts in {p.count} reviewed traces"
            )
    return codebook
