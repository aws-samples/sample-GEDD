"""Codebook-grounded reward model.

The reward is decomposed by failure code instead of being a single opaque scalar:

  r(x, y) = 1 - sum_c w_c * P(code c present in y | x)

where the codes and their severity weights w_c come from the expert-built GEDD failure codebook
and P(.) comes from one or more judge members (prompted LLM judges or trained classifiers),
optionally Platt-calibrated per code against expert labels.

With several members the model returns a conservative score, mean - k * std, which is the
uncertainty-penalised objective shown to mitigate overoptimization (Coste et al., 2023,
arXiv:2310.02743). The decomposition is what makes the reward auditable: every low score names
the failure code that caused it.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from statistics import fmean, pstdev

# Default mapping from GEDD severity labels to reward weights. Experts own these numbers.
SEVERITY_WEIGHTS: dict[str, float] = {
    "low": 0.1,
    "medium": 0.25,
    "high": 0.5,
    "critical": 0.8,
    "catastrophic": 1.0,
}


@dataclass(frozen=True)
class FailureCode:
    code: str
    severity: str = "medium"
    blocking: bool = False
    weight: float | None = None  # overrides the severity mapping when set

    @property
    def w(self) -> float:
        if self.weight is not None:
            return self.weight
        try:
            return SEVERITY_WEIGHTS[self.severity]
        except KeyError as exc:
            raise ValueError(f"unknown severity {self.severity!r} for {self.code}") from exc


@dataclass
class PlattCalibrator:
    """p_cal = sigmoid(a * logit(p_raw) + b), fitted by Newton's method on expert labels.

    Uses Platt's (1999) smoothed targets, (N+ + 1) / (N+ + 2) and 1 / (N- + 2), so the fit stays
    finite when a judge separates the labels perfectly on part of the range.
    """

    a: float = 1.0
    b: float = 0.0

    @staticmethod
    def _logit(p: float) -> float:
        p = min(1 - 1e-6, max(1e-6, p))
        return math.log(p / (1 - p))

    def __call__(self, p: float) -> float:
        z = self.a * self._logit(p) + self.b
        return 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))

    def fit(self, raw: Sequence[float], labels: Sequence[bool], iters: int = 50) -> PlattCalibrator:
        if len(raw) != len(labels) or not raw:
            raise ValueError("raw and labels must be non-empty and aligned")
        if all(labels) or not any(labels):
            # Degenerate: no information about the slope; shift to the base rate only.
            rate = min(1 - 1e-3, max(1e-3, sum(labels) / len(labels)))
            self.a, self.b = 0.0, math.log(rate / (1 - rate))
            return self
        xs = [self._logit(p) for p in raw]
        n_pos = sum(labels)
        n_neg = len(labels) - n_pos
        t_pos, t_neg = (n_pos + 1) / (n_pos + 2), 1 / (n_neg + 2)
        targets = [t_pos if y else t_neg for y in labels]
        a, b, ridge = self.a, self.b, 1e-6

        def loss(a_: float, b_: float) -> float:
            total = 0.0
            for x, t in zip(xs, targets, strict=True):
                z = a_ * x + b_
                # log(1 + e^z) - t * z, computed stably
                total += (z if z > 0 else 0.0) + math.log1p(math.exp(-abs(z))) - t * z
            return total

        current = loss(a, b)
        for _ in range(iters):
            ga = gb = haa = hab = hbb = 0.0
            for x, t in zip(xs, targets, strict=True):
                z = a * x + b
                p = 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))
                r = p - t
                s = p * (1 - p)
                ga += r * x
                gb += r
                haa += s * x * x
                hab += s * x
                hbb += s
            haa += ridge
            hbb += ridge
            det = haa * hbb - hab * hab
            if det <= 0:
                break
            da = (hbb * ga - hab * gb) / det
            db = (haa * gb - hab * ga) / det
            step = 1.0  # backtracking line search keeps Newton from overshooting
            while step > 1e-8:
                cand = loss(a - step * da, b - step * db)
                if cand <= current:
                    break
                step /= 2
            else:
                break
            a, b, current = a - step * da, b - step * db, cand
            if abs(step * da) < 1e-9 and abs(step * db) < 1e-9:
                break
        self.a, self.b = a, b
        return self


@dataclass(frozen=True)
class RewardResult:
    reward: float  # conservative score: mean - k * std across members
    mean: float
    std: float
    code_probs: dict[str, float]  # ensemble-mean P(code) after calibration
    top_code: str | None  # code contributing most expected cost
    blocking_prob: float  # P(any blocking code), max over blocking codes


@dataclass
class CodebookRewardModel:
    codebook: Sequence[FailureCode]
    k: float = 1.0
    calibrators: dict[str, PlattCalibrator] = field(default_factory=dict)

    def __post_init__(self) -> None:
        codes = [c.code for c in self.codebook]
        if len(set(codes)) != len(codes):
            raise ValueError("duplicate failure codes in codebook")
        if not codes:
            raise ValueError("codebook is empty")
        total = sum(c.w for c in self.codebook)
        self._norm = total if total > 1 else 1.0

    def _calibrated(self, member: Mapping[str, float]) -> dict[str, float]:
        out = {}
        for c in self.codebook:
            p = float(member.get(c.code, 0.0))
            cal = self.calibrators.get(c.code)
            out[c.code] = cal(p) if cal else p
        return out

    def _member_reward(self, probs: Mapping[str, float]) -> float:
        return 1.0 - sum(c.w * probs[c.code] for c in self.codebook) / self._norm

    def score(self, members: Sequence[Mapping[str, float]]) -> RewardResult:
        """Score one response from one or more judge members' per-code probabilities."""
        if not members:
            raise ValueError("need at least one judge member")
        cal = [self._calibrated(m) for m in members]
        rewards = [self._member_reward(p) for p in cal]
        mean = fmean(rewards)
        std = pstdev(rewards) if len(rewards) > 1 else 0.0
        probs = {c.code: fmean(p[c.code] for p in cal) for c in self.codebook}
        costs = {c.code: c.w * probs[c.code] for c in self.codebook}
        top = max(costs, key=lambda k: costs[k])
        blocking = [probs[c.code] for c in self.codebook if c.blocking]
        return RewardResult(
            reward=mean - self.k * std,
            mean=mean,
            std=std,
            code_probs=probs,
            top_code=top if costs[top] > 0 else None,
            blocking_prob=max(blocking) if blocking else 0.0,
        )

    def fit_calibration(
        self, raw_members: Sequence[Mapping[str, float]], expert_codes: Sequence[set[str]]
    ) -> CodebookRewardModel:
        """Fit one Platt calibrator per code on (judge P(code), expert says code present) pairs."""
        if len(raw_members) != len(expert_codes):
            raise ValueError("raw_members and expert_codes must align")
        for c in self.codebook:
            raw = [float(m.get(c.code, 0.0)) for m in raw_members]
            labels = [c.code in codes for codes in expert_codes]
            self.calibrators[c.code] = PlattCalibrator().fit(raw, labels)
        return self


def scalar_reward(members: Sequence[Mapping[str, float]], key: str = "pass") -> float:
    """Baseline: a single undecomposed pass probability, averaged over members."""
    return fmean(float(m[key]) for m in members)
