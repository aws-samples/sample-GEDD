"""Tests for the codebook-grounded reward model and response gate."""

from __future__ import annotations

import random

import pytest

from grounded_evals.reward import (
    CodebookRewardModel,
    FailureCode,
    GateAction,
    GatePolicy,
    PlattCalibrator,
    scalar_reward,
)

CODEBOOK = [
    FailureCode("invented_value", "critical", blocking=True),
    FailureCode("wrong_order_number", "high"),
    FailureCode("format_drift", "low"),
]


def test_reward_is_one_minus_weighted_cost():
    rm = CodebookRewardModel([FailureCode("x", weight=1.0)])
    assert rm.score([{"x": 0.5}]).reward == pytest.approx(0.5)


def test_weights_normalised_so_reward_stays_in_unit_interval():
    rm = CodebookRewardModel(CODEBOOK)
    worst = rm.score([{c.code: 1.0 for c in CODEBOOK}])
    best = rm.score([{}])
    assert worst.reward == pytest.approx(0.0)
    assert best.reward == pytest.approx(1.0)


def test_conservative_ensemble_penalises_disagreement():
    rm = CodebookRewardModel([FailureCode("x", weight=1.0)], k=1.0)
    r = rm.score([{"x": 0.0}, {"x": 1.0}])
    assert r.mean == pytest.approx(0.5)
    assert r.std == pytest.approx(0.5)
    assert r.reward == pytest.approx(0.0)


def test_top_code_names_the_most_costly_failure():
    rm = CodebookRewardModel(CODEBOOK)
    r = rm.score([{"format_drift": 0.9, "wrong_order_number": 0.4}])
    # 0.5 * 0.4 = 0.2 beats 0.1 * 0.9 = 0.09
    assert r.top_code == "wrong_order_number"
    assert rm.score([{}]).top_code is None


def test_duplicate_or_empty_codebook_rejected():
    with pytest.raises(ValueError):
        CodebookRewardModel([FailureCode("a"), FailureCode("a")])
    with pytest.raises(ValueError):
        CodebookRewardModel([])
    with pytest.raises(ValueError):
        _ = FailureCode("a", severity="spicy").w


def test_platt_fit_improves_log_loss_on_miscalibrated_judge():
    rng = random.Random(4)
    # A judge that is overconfident: says 0.95 / 0.05 but is right only 75% of the time.
    labels = [rng.random() < 0.5 for _ in range(600)]
    raw = [(0.95 if y else 0.05) if rng.random() < 0.75 else (0.05 if y else 0.95) for y in labels]
    cal = PlattCalibrator().fit(raw, labels)

    def nll(ps):
        import math

        return -sum(math.log(p if y else 1 - p) for p, y in zip(ps, labels, strict=True)) / len(
            labels
        )

    assert nll([cal(p) for p in raw]) < nll(raw)
    assert cal(0.95) == pytest.approx(0.75, abs=0.05)


def test_platt_degenerate_labels_use_base_rate():
    cal = PlattCalibrator().fit([0.2, 0.9, 0.5], [False, False, False])
    assert cal(0.99) < 0.01


def test_fit_calibration_per_code():
    rm = CodebookRewardModel([FailureCode("x", weight=1.0)])
    raw = [{"x": 0.9}] * 50 + [{"x": 0.1}] * 50
    expert = [{"x"}] * 25 + [set()] * 25 + [set()] * 50
    rm.fit_calibration(raw, expert)
    assert rm.score([{"x": 0.9}]).code_probs["x"] == pytest.approx(0.5, abs=0.05)


def test_scalar_reward_baseline():
    assert scalar_reward([{"pass": 0.2}, {"pass": 0.6}]) == pytest.approx(0.4)


# ── gate ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("members", "expected"),
    [
        ([{}], GateAction.ALLOW),
        ([{"invented_value": 0.7}], GateAction.BLOCK),
        ([{"wrong_order_number": 0.6}], GateAction.REVISE),
        ([{"wrong_order_number": 0.0}, {"wrong_order_number": 1.0}], GateAction.REVIEW),
        (
            [{"wrong_order_number": 1.0, "format_drift": 1.0, "invented_value": 0.3}],
            GateAction.REVIEW,
        ),
    ],
)
def test_gate_routing(members, expected):
    rm = CodebookRewardModel(CODEBOOK, k=0.0)
    decision = GatePolicy().decide(rm.score(members))
    assert decision.action is expected
    assert decision.customer_visible_block is (expected is not GateAction.ALLOW)


def test_gate_block_takes_precedence_over_uncertainty():
    rm = CodebookRewardModel(CODEBOOK)
    r = rm.score([{"invented_value": 0.9}, {"invented_value": 0.6, "format_drift": 1.0}])
    assert GatePolicy().decide(r).action is GateAction.BLOCK


def test_gate_rejects_inverted_thresholds():
    with pytest.raises(ValueError):
        GatePolicy(allow_threshold=0.5, revise_threshold=0.7)
