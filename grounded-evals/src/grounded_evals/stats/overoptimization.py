"""Reward-model overoptimization curves for best-of-N selection.

Given K sampled candidates per prompt, each with a proxy score (reward model) and a gold score
(expert label or verifiable scorer), compute the expected gold and proxy score of best-of-N
selection for N = 1..K, plotted against the analytic KL of best-of-N:

  KL_bon(N) = log N - (N - 1) / N        (Stiennon et al. 2020; Gao, Schulman & Hilton 2022)

When proxy keeps rising while gold flattens or falls, the policy is exploiting the reward model.
The expectation over random size-N subsets of the K candidates is computed exactly from order
statistics, so no resampling noise enters the curve.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class BonPoint:
    n: int
    kl: float
    proxy: float
    gold: float


def kl_best_of_n(n: int) -> float:
    if n < 1:
        raise ValueError("n must be >= 1")
    return math.log(n) - (n - 1) / n


def _expected_bon(proxy: Sequence[float], gold: Sequence[float], n: int) -> tuple[float, float]:
    """Exact E[proxy, gold of argmax-proxy] over uniformly random size-n subsets of K candidates.

    Ties in proxy are broken by averaging gold within the tied block, which is the expectation
    under uniformly random tie-breaking.
    """
    k = len(proxy)
    order = sorted(range(k), key=lambda i: proxy[i])  # ascending
    total = math.comb(k, n)
    exp_p = exp_g = 0.0
    i = 0
    while i < k:
        j = i
        while j + 1 < k and proxy[order[j + 1]] == proxy[order[i]]:
            j += 1
        # block order[i..j] shares one proxy value; subsets whose max lies in this block:
        below, block = i, j - i + 1
        ways = math.comb(below + block, n) - math.comb(below, n)
        if ways:
            w = ways / total
            exp_p += w * proxy[order[i]]
            exp_g += w * sum(gold[order[t]] for t in range(i, j + 1)) / block
        i = j + 1
    return exp_p, exp_g


def best_of_n_curve(
    proxy_scores: Sequence[Sequence[float]],
    gold_scores: Sequence[Sequence[float]],
    ns: Sequence[int] | None = None,
) -> list[BonPoint]:
    """Average best-of-N curve across prompts. Every prompt must have the same K candidates."""
    if len(proxy_scores) != len(gold_scores) or not proxy_scores:
        raise ValueError("proxy and gold must be non-empty and aligned per prompt")
    k = len(proxy_scores[0])
    for p, g in zip(proxy_scores, gold_scores, strict=True):
        if len(p) != k or len(g) != k:
            raise ValueError("every prompt needs the same number of candidates")
    ns = list(ns) if ns else list(range(1, k + 1))
    points = []
    for n in ns:
        if not 1 <= n <= k:
            raise ValueError(f"n={n} outside 1..{k}")
        sp = sg = 0.0
        for p, g in zip(proxy_scores, gold_scores, strict=True):
            ep, eg = _expected_bon(p, g, n)
            sp += ep
            sg += eg
        m = len(proxy_scores)
        points.append(BonPoint(n, kl_best_of_n(n), sp / m, sg / m))
    return points


def overoptimization_gap(curve: Sequence[BonPoint]) -> float:
    """Gold lost from the curve's peak to its final point (0 = no overoptimization observed)."""
    peak = max(p.gold for p in curve)
    return peak - curve[-1].gold
