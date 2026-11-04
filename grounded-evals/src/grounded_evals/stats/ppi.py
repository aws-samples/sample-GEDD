"""Prediction-powered inference for the online half of the GEDD flywheel.

A judge or reward model scores every production trace, but its scores are biased by its own
errors. Experts label a small *random* sample. PPI combines both into an unbiased estimate of the
true rate (for example, the share of responses that should have been blocked) with a valid
confidence interval, usually far tighter than the expert sample alone.

  theta_hat = lambda * mean(f(X_unlabelled)) - (lambda * mean(f(X_labelled)) - mean(Y_labelled))

lambda = 1 is classic PPI (Angelopoulos et al., 2023, Science, arXiv:2301.09633); the variance-
minimising lambda is PPI++ (Angelopoulos, Duchi & Zrnic, 2023, arXiv:2311.01453), which is never
worse than the expert-only estimate asymptotically.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist, fmean


@dataclass(frozen=True)
class MeanEstimate:
    estimate: float
    lo: float
    hi: float
    se: float
    lam: float
    n_labelled: int
    n_unlabelled: int

    @property
    def width(self) -> float:
        return self.hi - self.lo


def _var(xs: Sequence[float]) -> float:
    m = fmean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def _cov(xs: Sequence[float], ys: Sequence[float]) -> float:
    mx, my = fmean(xs), fmean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / (len(xs) - 1)


def classical_mean(y_labelled: Sequence[float], alpha: float = 0.05) -> MeanEstimate:
    """Expert-only estimate with a normal-approximation interval (the baseline PPI must beat)."""
    n = len(y_labelled)
    if n < 2:
        raise ValueError("need at least two labelled examples")
    est = fmean(y_labelled)
    se = math.sqrt(_var(y_labelled) / n)
    z = NormalDist().inv_cdf(1 - alpha / 2)
    return MeanEstimate(est, est - z * se, est + z * se, se, 0.0, n, 0)


def ppi_mean(
    y_labelled: Sequence[float],
    f_labelled: Sequence[float],
    f_unlabelled: Sequence[float],
    alpha: float = 0.05,
    lam: float | None = None,
) -> MeanEstimate:
    """PPI / PPI++ estimate of E[Y].

    y_labelled: expert labels on the random labelled sample.
    f_labelled: the judge's predictions on those same examples.
    f_unlabelled: the judge's predictions on the remaining (unlabelled) examples.
    lam: None = power-tuned (PPI++), 1.0 = classic PPI, 0.0 = expert-only.
    """
    n, big_n = len(y_labelled), len(f_unlabelled)
    if n != len(f_labelled):
        raise ValueError("y_labelled and f_labelled must align")
    if n < 2 or big_n < 2:
        raise ValueError("need at least two labelled and two unlabelled examples")
    var_f_l, var_f_u = _var(f_labelled), _var(f_unlabelled)
    if lam is None:
        denom = (1 + n / big_n) * var_f_l
        lam = 0.0 if denom == 0 else _cov(y_labelled, f_labelled) / denom
        lam = min(1.0, max(0.0, lam))
    est = lam * fmean(f_unlabelled) - (lam * fmean(f_labelled) - fmean(y_labelled))
    rectifier = [y - lam * f for y, f in zip(y_labelled, f_labelled, strict=True)]
    se = math.sqrt(lam * lam * var_f_u / big_n + _var(rectifier) / n)
    z = NormalDist().inv_cdf(1 - alpha / 2)
    return MeanEstimate(est, est - z * se, est + z * se, se, lam, n, big_n)
