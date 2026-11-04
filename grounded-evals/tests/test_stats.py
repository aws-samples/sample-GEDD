"""Tests for grounded_evals.stats: known values, invariants and simulation checks."""

from __future__ import annotations

import itertools
import math
import random

import pytest

from grounded_evals.stats import (
    best_of_n_curve,
    brier_score,
    classical_mean,
    cluster_bootstrap,
    cluster_robust_se,
    compare,
    expected_calibration_error,
    holm,
    kl_best_of_n,
    krippendorff_alpha_nominal,
    mcnemar_exact,
    minimum_detectable_effect,
    overoptimization_gap,
    pairwise_accuracy,
    ppi_mean,
)

# ── significance ──────────────────────────────────────────────────────────────


def _pairs(only_a: int, only_b: int, both: int = 0, neither: int = 0):
    a = [True] * only_a + [False] * only_b + [True] * both + [False] * neither
    b = [False] * only_a + [True] * only_b + [True] * both + [False] * neither
    return a, b


def test_mcnemar_small_exact_value():
    a, b = _pairs(0, 5, both=10)
    r = mcnemar_exact(a, b)
    assert (r.only_a, r.only_b) == (0, 5)
    assert r.p_value == pytest.approx(2 / 32)


def test_mcnemar_no_discordant_pairs():
    a, b = _pairs(0, 0, both=3, neither=2)
    assert mcnemar_exact(a, b).p_value == 1.0


def test_mcnemar_reproduces_docile_headline():
    # experiments/docile-invoices README: fine-tune vs baseline, 625 / 134 discordant pairs, p = 1e-76.
    a, b = _pairs(625, 134, both=3800, neither=441)
    p = mcnemar_exact(a, b).p_value
    assert 1e-77 < p < 1e-75


def test_mcnemar_symmetric():
    a, b = _pairs(7, 3, both=4)
    assert mcnemar_exact(a, b).p_value == mcnemar_exact(b, a).p_value


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        mcnemar_exact([True], [True, False])


def test_holm_known_values():
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_holm_is_monotone_and_capped():
    p = [0.2, 0.001, 0.5, 0.04]
    adj = holm(p)
    assert all(x >= y for x, y in zip(adj, p, strict=True))
    assert max(adj) <= 1.0
    order = sorted(range(4), key=lambda i: p[i])
    assert [adj[i] for i in order] == sorted(adj)


def test_cluster_bootstrap_excludes_zero_for_clear_gain():
    rng = random.Random(0)
    groups = [i // 10 for i in range(400)]
    a = [rng.random() < 0.9 for _ in groups]
    b = [rng.random() < 0.6 for _ in groups]
    bs = cluster_bootstrap(a, b, groups, reps=1000)
    assert bs.excludes_zero and bs.lo > 0
    assert bs.lo <= bs.delta <= bs.hi
    assert bs.clusters == 40


def test_cluster_bootstrap_is_seeded():
    groups = [i % 7 for i in range(70)]
    a = [i % 3 == 0 for i in range(70)]
    b = [i % 2 == 0 for i in range(70)]
    assert cluster_bootstrap(a, b, groups, reps=200, seed=1) == cluster_bootstrap(
        a, b, groups, reps=200, seed=1
    )


def test_cluster_se_wider_when_errors_are_clustered():
    # Same marginal accuracies, but in the clustered design whole clusters win or lose together.
    n_clusters, size = 40, 20
    groups = [g for g in range(n_clusters) for _ in range(size)]
    a_clustered = [g % 2 == 0 for g in groups]
    a_spread = [i % 2 == 0 for i in range(len(groups))]
    b = [False] * len(groups)
    assert cluster_robust_se(a_clustered, b, groups) > 3 * cluster_robust_se(a_spread, b, groups)


def test_mde_matches_normal_formula():
    assert minimum_detectable_effect(0.01) == pytest.approx((1.959964 + 0.841621) * 0.01, rel=1e-5)


def test_compare_requires_both_tests():
    rng = random.Random(3)
    groups = [i // 25 for i in range(1000)]
    a = [rng.random() < 0.8 for _ in groups]
    b = [rng.random() < 0.7 for _ in groups]
    c = compare(a, b, groups, reps=1000)
    assert c.significant
    assert c.delta == pytest.approx(c.acc_a - c.acc_b)
    same = compare(a, a, groups, reps=200)
    assert not same.significant and same.delta == 0


# ── agreement & calibration ───────────────────────────────────────────────────


def test_krippendorff_perfect_agreement():
    units = [{"x": "a", "y": "a"}, {"x": "b", "y": "b"}, {"x": "a", "y": "a"}]
    assert krippendorff_alpha_nominal(units) == pytest.approx(1.0)


def test_krippendorff_hand_computed():
    # o_aa=2, o_ab=o_ba=1, o_bb=4; n_a=3, n_b=5, n=8 -> alpha = 1 - 7*2/30 = 8/15
    units = [
        {"x": "a", "y": "a"},
        {"x": "a", "y": "b"},
        {"x": "b", "y": "b"},
        {"x": "b", "y": "b"},
    ]
    assert krippendorff_alpha_nominal(units) == pytest.approx(8 / 15)


def test_krippendorff_ignores_singly_labelled_units():
    units = [{"x": "a", "y": "a"}, {"x": "b", "y": "b"}, {"x": "a", "y": None}, {"z": "b"}]
    assert krippendorff_alpha_nominal(units) == pytest.approx(1.0)


def test_krippendorff_needs_pairable_data():
    with pytest.raises(ValueError):
        krippendorff_alpha_nominal([{"x": "a"}])


def test_ece_and_brier():
    assert expected_calibration_error([0.0, 1.0, 1.0], [False, True, True]) == 0.0
    # Always says 0.9 but is right half the time: ECE = 0.4
    assert expected_calibration_error([0.9] * 4, [True, False, True, False]) == pytest.approx(0.4)
    assert brier_score([1.0, 0.0], [True, True]) == pytest.approx(0.5)


def test_pairwise_accuracy_ties_count_half():
    assert pairwise_accuracy([1.0, 0.5, 0.2], [0.0, 0.5, 0.9]) == pytest.approx(0.5)


# ── PPI ───────────────────────────────────────────────────────────────────────


def _simulate(rng: random.Random, big_n: int, n: int, flip: float, rate: float = 0.3):
    y = [float(rng.random() < rate) for _ in range(big_n + n)]
    f = [1 - v if rng.random() < flip else v for v in y]  # a judge that is wrong `flip` of the time
    idx = list(range(big_n + n))
    rng.shuffle(idx)
    lab, unl = idx[:n], idx[n:]
    return [y[i] for i in lab], [f[i] for i in lab], [f[i] for i in unl], sum(y) / len(y)


def test_ppi_coverage_and_unbiasedness():
    rng = random.Random(7)
    covered, errors = 0, []
    trials = 400
    for _ in range(trials):
        yl, fl, fu, truth = _simulate(rng, big_n=2000, n=100, flip=0.15)
        est = ppi_mean(yl, fl, fu)
        covered += est.lo <= truth <= est.hi
        errors.append(est.estimate - truth)
    assert covered / trials > 0.91
    assert abs(sum(errors) / trials) < 0.01


def test_ppi_tighter_than_expert_only_with_a_good_judge():
    rng = random.Random(11)
    yl, fl, fu, _ = _simulate(rng, big_n=5000, n=100, flip=0.05)
    assert ppi_mean(yl, fl, fu).width < 0.6 * classical_mean(yl).width


def test_ppi_lambda_zero_is_expert_only():
    rng = random.Random(5)
    yl, fl, fu, _ = _simulate(rng, big_n=500, n=50, flip=0.2)
    est = ppi_mean(yl, fl, fu, lam=0.0)
    assert est.estimate == pytest.approx(sum(yl) / len(yl))
    assert est.se == pytest.approx(classical_mean(yl).se)


def test_ppi_useless_judge_falls_back_to_expert_only():
    rng = random.Random(9)
    yl = [float(rng.random() < 0.4) for _ in range(80)]
    fl = [float(rng.random() < 0.5) for _ in range(80)]
    fu = [float(rng.random() < 0.5) for _ in range(800)]
    est = ppi_mean(yl, fl, fu)
    assert est.lam < 0.3
    assert est.width <= classical_mean(yl).width * 1.05


# ── best-of-N overoptimization ────────────────────────────────────────────────


def test_kl_best_of_n():
    assert kl_best_of_n(1) == 0.0
    assert kl_best_of_n(4) == pytest.approx(math.log(4) - 0.75)


def test_bon_anti_correlated_proxy_shows_overoptimization():
    curve = best_of_n_curve([[0.0, 1.0]], [[1.0, 0.0]])
    assert [p.gold for p in curve] == pytest.approx([0.5, 0.0])
    assert [p.proxy for p in curve] == pytest.approx([0.5, 1.0])
    assert overoptimization_gap(curve) == pytest.approx(0.5)


def test_bon_ties_average_gold():
    curve = best_of_n_curve([[1.0, 1.0]], [[1.0, 0.0]], ns=[2])
    assert curve[0].gold == pytest.approx(0.5)


def test_bon_matches_brute_force_enumeration():
    rng = random.Random(2)
    k = 6
    proxy = [[round(rng.random(), 1) for _ in range(k)] for _ in range(5)]
    gold = [[rng.random() for _ in range(k)] for _ in range(5)]
    curve = best_of_n_curve(proxy, gold)
    for point in curve:
        total = 0.0
        for p, g in zip(proxy, gold, strict=True):
            subsets = list(itertools.combinations(range(k), point.n))
            acc = 0.0
            for s in subsets:
                best = max(p[i] for i in s)
                tied = [i for i in s if p[i] == best]
                acc += sum(g[i] for i in tied) / len(tied)
            total += acc / len(subsets)
        assert point.gold == pytest.approx(total / len(proxy))


def test_bon_rejects_ragged_input():
    with pytest.raises(ValueError):
        best_of_n_curve([[0.1, 0.2], [0.3]], [[1, 0], [1]])
