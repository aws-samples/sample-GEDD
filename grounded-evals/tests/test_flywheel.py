"""Tests for the GEDD RL eval flywheel (grounded_evals.flywheel)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from grounded_evals.flywheel import (
    Code,
    Codebook,
    LLMJudgeDetector,
    RuleDetector,
    TasteReward,
    Tripwire,
    audit_reward,
    grpo_advantages,
    parse_detection,
    run,
)
from grounded_evals.flywheel import sim_travel as sim
from grounded_evals.flywheel.reward import fit_calibrators

CB = Codebook(
    (
        Code("leak", "leaks data", "catastrophic", blocking=True),
        Code("made_up", "invents facts", "high"),
    )
)


def fixed(name, probs, exact=False):
    return RuleDetector(name, lambda t, tr: probs, exact=exact)


def reward(*detectors, goal=1.0):
    return TasteReward(CB, list(detectors), goal_fn=lambda t, tr: goal, k=0.0)


# ---------- codebook ----------


def test_codebook_add_bumps_version_and_keeps_history(tmp_path):
    cb2 = CB.add(Code("rude", severity="low"), "seen 4 times")
    assert (CB.version, cb2.version) == (1, 2)
    assert "rude" in cb2 and "rude" not in CB
    assert cb2.history[-1].startswith("v2: +rude")
    cb2.save(tmp_path / "cb.yaml")
    assert Codebook.load(tmp_path / "cb.yaml") == cb2


def test_codebook_rejects_duplicates_and_bad_severity():
    with pytest.raises(ValueError):
        Codebook((Code("a"), Code("a")))
    with pytest.raises(ValueError):
        Codebook((Code("a", severity="spicy"),))
    with pytest.raises(ValueError):
        CB.add(Code("leak"), "again")


# ---------- reward ----------


def test_blocking_code_zeroes_the_reward():
    assert reward(fixed("j", {"leak": 0.9, "made_up": 0.0}))({}, {}) == 0.0


def test_pay_for_the_goal_charge_for_the_cost():
    clean = reward(fixed("j", {"leak": 0.0, "made_up": 0.0}))({}, {})
    flawed = reward(fixed("j", {"leak": 0.0, "made_up": 1.0}))({}, {})
    idle = reward(fixed("j", {"leak": 0.0, "made_up": 0.0}), goal=0.1)({}, {})
    assert clean == 1.0
    assert flawed == pytest.approx(0.5)
    assert idle < flawed < clean  # doing nothing is not free


def test_failed_detector_or_uncovered_code_is_missing_not_zero():
    failing = RuleDetector("j", lambda t, tr: None)
    assert reward(fixed("a", {"leak": 0.0, "made_up": 0.0}), failing)({}, {}) is None
    assert reward(fixed("a", {"leak": 0.0}))({}, {}) is None  # made_up uncovered


def test_exact_rule_check_overrides_judges():
    r = reward(
        fixed("rule", {"leak": 0.0}, exact=True), fixed("judge", {"leak": 0.9, "made_up": 0.0})
    )
    assert r({}, {}) == 1.0


def test_efficiency_discounts_excess_calls_with_a_cap():
    r = reward(fixed("j", {"leak": 0.0, "made_up": 0.0}))
    assert r({"ideal_calls": 3}, {"tool_calls": 5}) == pytest.approx(0.88)
    assert r({"ideal_calls": 3}, {"tool_calls": 50}) == pytest.approx(0.75)


def test_conservative_ensemble_charges_disagreement():
    r = TasteReward(
        CB,
        [fixed("a", {"leak": 0.0, "made_up": 0.0}), fixed("b", {"leak": 0.0, "made_up": 0.6})],
        goal_fn=lambda t, tr: 1.0,
        k=1.0,
    )
    b = r.breakdown({}, {})
    assert b.code_probs["made_up"] == pytest.approx(0.6)  # mean 0.3 + std 0.3
    assert b.code_mean["made_up"] == pytest.approx(0.3)


def test_parse_detection():
    assert parse_detection('ok {"leak": 0.2, "made_up": {"p": 0.7}}', CB.names) == {
        "leak": 0.2,
        "made_up": 0.7,
    }
    assert parse_detection('{"leak": 0.2}', CB.names) is None
    assert parse_detection('{"leak": 1.5, "made_up": 0}', CB.names) is None
    assert parse_detection("no json", CB.names) is None


def test_llm_judge_detector_hides_private_fields_and_fails_soft():
    sent = {}

    def create(**kw):
        sent.update(kw)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"leak":0.1,"made_up":0.2}'))]
        )

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    det = LLMJudgeDetector("j", client, "m", CB)
    assert det.detect({"q": 1}, {"reply": "hi", "_truth": {"leak"}}) == {
        "leak": 0.1,
        "made_up": 0.2,
    }
    assert "_truth" not in sent["messages"][0]["content"]

    def boom(**kw):
        raise TimeoutError

    det.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=boom)))
    assert det.detect({}, {}) is None


def test_fit_calibrators_skips_single_class_codes():
    r = reward(fixed("judge", {"leak": 0.0, "made_up": 0.0}))
    bds = [r.breakdown({}, {}) for _ in range(10)]
    for i, b in enumerate(bds):
        b.raw["judge"] = {"leak": 0.1, "made_up": 0.9 if i < 5 else 0.1}
    labels = [({"made_up"} if i < 5 else set()) for i in range(10)]
    cal = fit_calibrators(r, bds, labels)
    assert "judge:made_up" in cal and "judge:leak" not in cal
    assert cal["judge:made_up"](0.9) > 0.5 > cal["judge:made_up"](0.1)


# ---------- harness ----------


def test_grpo_advantages():
    assert grpo_advantages([0.5, 0.5, 0.5]) is None
    assert grpo_advantages([1.0, None]) is None
    adv = grpo_advantages([1.0, 0.0, 0.0, 0.0])
    assert adv[0] > 0 > adv[1] and abs(sum(adv)) < 1e-9


def test_tripwire_fires_only_when_reward_rises_and_taste_falls():
    up_down = Tripwire(window=2)
    assert [up_down.update(r, a) for r, a in [(0.5, 0.9), (0.5, 0.9), (0.7, 0.6), (0.8, 0.5)]][-1]
    both_up = Tripwire(window=2)
    assert not any(
        both_up.update(r, a) for r, a in [(0.5, 0.5), (0.5, 0.5), (0.7, 0.7), (0.8, 0.8)]
    )


def test_run_drops_scorer_failed_groups():
    class P:
        def sample(self, task, n):
            return [{"tool_calls": 1, "ok": i % 2 == 0} for i in range(n)]

    def r(task, trace):
        return None if task["id"] == "bad" else float(trace["ok"])

    res = run(P(), [{"id": "good"}, {"id": "bad"}], reward=r, steps=1, tasks_per_step=2, group=4)
    assert res.history[0]["scorer_failed_groups"] == 1
    assert res.history[0]["flat_groups"] == 0


# ---------- the simulated agent app, end to end ----------


def test_reward_audit_flags_the_generic_reward_not_the_codebook():
    app = sim.make_app()
    pols = {"base": sim.TabularPolicy.start(), **app.degenerate}
    generic = audit_reward(
        sim.helpfulness_reward, app.train_tasks, pols, base="base", degenerate=list(app.degenerate)
    )
    gedd = audit_reward(
        sim.make_reward(sim.starting_codebook()),
        app.train_tasks,
        pols,
        base="base",
        degenerate=list(app.degenerate),
    )
    assert generic.loopholes == [sim.SKIP]
    assert gedd.passed and gedd.margin > 0


def test_demo_runs_the_whole_flywheel_deterministically():
    from grounded_evals.flywheel.demo import render, run_demo

    a, b = run_demo(seed=0), run_demo(seed=0)
    assert a == b
    assert a["generic_arm"]["tripped"]
    r1, r2, r3 = a["rounds"]
    assert (
        r1["found_by_tripwire"] == ["missed_passenger_rights"] and r1["next_codebook_version"] == 2
    )
    assert r2["promoted"] and r2["locked"]["significant"]
    assert not r3["promoted"]  # converged: no significant gain, nothing shipped
    assert "missed_passenger_rights" in [c["code"] for c in a["codebook"]["codes"]]
    assert "not a GEDD finding" in render(a)
