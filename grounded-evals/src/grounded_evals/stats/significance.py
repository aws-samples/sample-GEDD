"""Paired, cluster-aware significance tests for comparing two systems on the same cases.

GEDD's bar for "this version is better": an exact McNemar test on the paired outcomes AND a
cluster bootstrap interval that excludes zero. Clusters are the unit that shares mistakes
(customer, template, layout); treating cases inside one cluster as independent is overconfident.

References:
  McNemar (1947); Dietterich (1998) Neural Computation 10(7).
  Cameron, Gelbach & Miller (2008) REStat 90(3) — cluster-robust inference.
  Miller (2024) "Adding Error Bars to Evals", arXiv:2411.00640.
  Holm (1979) Scand. J. Statistics 6(2) — step-down multiple-comparison correction.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Hashable, Sequence
from dataclasses import dataclass
from statistics import NormalDist

_Z = NormalDist()


@dataclass(frozen=True)
class McNemarResult:
    only_a: int
    only_b: int
    p_value: float


@dataclass(frozen=True)
class BootstrapResult:
    delta: float
    lo: float
    hi: float
    clusters: int
    reps: int

    @property
    def excludes_zero(self) -> bool:
        return self.lo > 0 or self.hi < 0


@dataclass(frozen=True)
class Comparison:
    n: int
    acc_a: float
    acc_b: float
    mcnemar: McNemarResult
    bootstrap: BootstrapResult
    cluster_se: float
    alpha: float

    @property
    def delta(self) -> float:
        return self.acc_a - self.acc_b

    @property
    def significant(self) -> bool:
        return self.mcnemar.p_value < self.alpha and self.bootstrap.excludes_zero


def _check_paired(a: Sequence[bool], b: Sequence[bool], groups: Sequence[Hashable] | None) -> None:
    if len(a) != len(b):
        raise ValueError(f"paired outcomes differ in length: {len(a)} vs {len(b)}")
    if groups is not None and len(groups) != len(a):
        raise ValueError(f"groups has length {len(groups)}, outcomes have {len(a)}")
    if not a:
        raise ValueError("no cases to compare")


def mcnemar_exact(a: Sequence[bool], b: Sequence[bool]) -> McNemarResult:
    """Two-sided exact McNemar test on paired binary outcomes."""
    _check_paired(a, b, None)
    only_a = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
    only_b = sum(1 for x, y in zip(a, b, strict=True) if y and not x)
    n = only_a + only_b
    if n == 0:
        return McNemarResult(only_a, only_b, 1.0)
    k = min(only_a, only_b)
    tail = sum(math.comb(n, i) for i in range(k + 1))
    return McNemarResult(only_a, only_b, min(1.0, 2 * tail / 2**n))


def _cluster_sums(
    groups: Sequence[Hashable], a: Sequence[bool], b: Sequence[bool]
) -> list[tuple[int, int, int]]:
    by: dict[Hashable, list[int]] = defaultdict(lambda: [0, 0, 0])
    for g, x, y in zip(groups, a, b, strict=True):
        cell = by[g]
        cell[0] += int(x)
        cell[1] += int(y)
        cell[2] += 1
    return [(v[0], v[1], v[2]) for v in by.values()]


def cluster_bootstrap(
    a: Sequence[bool],
    b: Sequence[bool],
    groups: Sequence[Hashable],
    reps: int = 5000,
    seed: int = 42,
    level: float = 0.95,
) -> BootstrapResult:
    """Percentile interval for acc(a) - acc(b), resampling whole clusters with replacement."""
    _check_paired(a, b, groups)
    cells = _cluster_sums(groups, a, b)
    rng = random.Random(seed)
    g = len(cells)
    deltas = []
    for _ in range(reps):
        sa = sb = n = 0
        for _ in range(g):
            ca, cb, cn = cells[rng.randrange(g)]
            sa += ca
            sb += cb
            n += cn
        deltas.append((sa - sb) / n)
    deltas.sort()
    tail = (1 - level) / 2
    lo = deltas[int(tail * reps)]
    hi = deltas[min(reps - 1, int((1 - tail) * reps))]
    delta = (sum(a) - sum(b)) / len(a)
    return BootstrapResult(delta, lo, hi, g, reps)


def cluster_robust_se(a: Sequence[bool], b: Sequence[bool], groups: Sequence[Hashable]) -> float:
    """CR1 cluster-robust standard error of the paired accuracy difference."""
    _check_paired(a, b, groups)
    cells = _cluster_sums(groups, a, b)
    n = sum(c[2] for c in cells)
    g = len(cells)
    if g < 2:
        return float("nan")
    dbar = sum(c[0] - c[1] for c in cells) / n
    ss = sum(((ca - cb) - dbar * cn) ** 2 for ca, cb, cn in cells)
    return math.sqrt(g / (g - 1) * ss) / n


def minimum_detectable_effect(se: float, alpha: float = 0.05, power: float = 0.8) -> float:
    """Smallest true gap a two-sided test at `alpha` detects with probability `power`."""
    return (_Z.inv_cdf(1 - alpha / 2) + _Z.inv_cdf(power)) * se


def holm(p_values: Sequence[float]) -> list[float]:
    """Holm step-down adjusted p-values (family-wise error control), in input order."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[i]))
        adjusted[i] = running
    return adjusted


def compare(
    a: Sequence[bool],
    b: Sequence[bool],
    groups: Sequence[Hashable],
    alpha: float = 0.05,
    reps: int = 5000,
    seed: int = 42,
) -> Comparison:
    """Full GEDD comparison of system A vs system B on the same paired cases."""
    _check_paired(a, b, groups)
    n = len(a)
    return Comparison(
        n=n,
        acc_a=sum(a) / n,
        acc_b=sum(b) / n,
        mcnemar=mcnemar_exact(a, b),
        bootstrap=cluster_bootstrap(a, b, groups, reps=reps, seed=seed, level=1 - alpha),
        cluster_se=cluster_robust_se(a, b, groups),
        alpha=alpha,
    )
