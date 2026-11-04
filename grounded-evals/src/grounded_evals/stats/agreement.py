"""Label-quality and calibration metrics for expert annotators, judges and reward models.

- Krippendorff's alpha (nominal): agreement for any number of annotators, tolerates missing labels.
  Krippendorff (2004/2011), "Computing Krippendorff's Alpha-Reliability".
- Expected calibration error and Brier score: is a judge's or reward model's probability honest?
  Guo et al. (2017) "On Calibration of Modern Neural Networks", ICML; Brier (1950).
- Pairwise accuracy: does the reward model rank the expert-preferred response higher?
  (as in RewardBench, Lambert et al. 2024, arXiv:2403.13787).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Mapping, Sequence
from itertools import permutations


def krippendorff_alpha_nominal(units: Sequence[Mapping[str, Hashable | None]]) -> float:
    """Nominal Krippendorff's alpha.

    `units` is one mapping per item, annotator -> label (None or absent = not labelled).
    Items with fewer than two labels are ignored, as the coefficient requires.
    """
    coincidence: defaultdict[tuple[Hashable, Hashable], float] = defaultdict(float)
    for unit in units:
        values = [v for v in unit.values() if v is not None]
        m = len(values)
        if m < 2:
            continue
        for x, y in permutations(values, 2):
            coincidence[(x, y)] += 1.0 / (m - 1)
    n_c: defaultdict[Hashable, float] = defaultdict(float)
    for (x, _), w in coincidence.items():
        n_c[x] += w
    n = sum(n_c.values())
    if n <= 1:
        raise ValueError("need at least one item labelled by two or more annotators")
    observed = sum(w for (x, y), w in coincidence.items() if x != y)
    expected_pairs = n * n - sum(v * v for v in n_c.values())
    if expected_pairs == 0:
        return 1.0
    return 1.0 - (n - 1) * observed / expected_pairs


def expected_calibration_error(
    probs: Sequence[float], labels: Sequence[bool], bins: int = 10
) -> float:
    """Equal-width-bin ECE for binary predictions: sum_b |acc_b - conf_b| * n_b / n."""
    if len(probs) != len(labels) or not probs:
        raise ValueError("probs and labels must be non-empty and the same length")
    buckets: list[list[tuple[float, bool]]] = [[] for _ in range(bins)]
    for p, y in zip(probs, labels, strict=True):
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"probability out of range: {p}")
        buckets[min(bins - 1, int(p * bins))].append((p, y))
    n = len(probs)
    ece = 0.0
    for bucket in buckets:
        if bucket:
            conf = sum(p for p, _ in bucket) / len(bucket)
            acc = sum(y for _, y in bucket) / len(bucket)
            ece += abs(acc - conf) * len(bucket) / n
    return ece


def brier_score(probs: Sequence[float], labels: Sequence[bool]) -> float:
    if len(probs) != len(labels) or not probs:
        raise ValueError("probs and labels must be non-empty and the same length")
    return sum((p - float(y)) ** 2 for p, y in zip(probs, labels, strict=True)) / len(probs)


def pairwise_accuracy(chosen_scores: Sequence[float], rejected_scores: Sequence[float]) -> float:
    """Share of expert preference pairs the scorer ranks correctly (ties count half)."""
    if len(chosen_scores) != len(rejected_scores) or not chosen_scores:
        raise ValueError("score lists must be non-empty and the same length")
    total = 0.0
    for c, r in zip(chosen_scores, rejected_scores, strict=True):
        total += 1.0 if c > r else 0.5 if c == r else 0.0
    return total / len(chosen_scores)
