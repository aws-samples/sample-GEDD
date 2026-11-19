"""`grounded-evals flywheel demo`: the whole RL eval flywheel on the simulated TravelBot app.

Two arms from the same starting agent:
  generic   RL on a generic "helpful and quick" judge. The reward audit flags it before training;
            trained anyway, the tripwire stops it once reward rises while the product's taste falls.
  gedd      three flywheel rounds on the experts' codebook: audit → train → measure → ship? →
            gate + PPI++ in production → recalibrate → grow the codebook.

Simulation only: the numbers exercise the loop's mechanics and are not GEDD findings.
"""

from __future__ import annotations

from grounded_evals.flywheel import sim_travel as sim
from grounded_evals.flywheel.audit import audit_reward
from grounded_evals.flywheel.harness import run
from grounded_evals.flywheel.loop import RoundConfig, run_flywheel
from grounded_evals.reward.gate import GatePolicy


def run_demo(seed: int = 0, rounds: int = 3) -> dict:
    app = sim.make_app(seed)
    base = sim.TabularPolicy.start(seed)
    codebook = sim.starting_codebook()
    cfg = RoundConfig(seed=seed, gate=GatePolicy(allow_threshold=0.75, revise_threshold=0.5))
    policies = {"base": base, **app.degenerate}

    def audit_rows(reward):
        rep = audit_reward(
            reward,
            app.train_tasks,
            policies,
            base="base",
            degenerate=list(app.degenerate),
            audit=app.audit,
        )
        return {
            "passed": rep.passed,
            "loopholes": rep.loopholes,
            "rows": [
                {
                    "policy": r.policy,
                    "reward": round(r.reward, 3),
                    "taste": round(r.audit or 0, 3),
                    "loophole": r.loophole,
                }
                for r in rep.rows
            ],
        }

    generic_run = run(
        sim.GRPOTabularTrainer(base.copy(seed=seed + 7)),
        app.train_tasks,
        reward=sim.helpfulness_reward,
        audit=app.audit,
        steps=cfg.steps,
        tasks_per_step=cfg.tasks_per_step,
        group=cfg.group,
        window=cfg.window,
    )
    reports, _, final = run_flywheel(app, codebook, base, rounds, config=cfg)
    return {
        "note": "simulation: exercises the flywheel's mechanics; not a GEDD finding",
        "seed": seed,
        "audit": {
            "generic": audit_rows(sim.helpfulness_reward),
            "codebook_v1": audit_rows(sim.make_reward(codebook)),
        },
        "generic_arm": {
            "tripped": generic_run.tripped,
            "steps_run": len(generic_run.history),
            "curve": [
                {"step": h["step"], "reward": round(h["reward"], 3), "taste": round(h["audit"], 3)}
                for h in generic_run.history
            ],
        },
        "rounds": [r.summary() for r in reports],
        "codebook": final.to_dict(),
    }


def render(result: dict) -> str:
    out = ["GEDD RL eval flywheel: simulated TravelBot (" + result["note"] + ")", ""]
    out.append(
        "1. Reward audit before training (taste = share of traces with no expert-named failure)"
    )
    for name, a in result["audit"].items():
        rows = ", ".join(
            f"{r['policy']} {r['reward']:.2f}{' LOOPHOLE' if r['loophole'] else ''}"
            for r in a["rows"]
        )
        out.append(f"   {name:<12} {'pass' if a['passed'] else 'FAIL'}  {rows}")
    g = result["generic_arm"]
    first, last = g["curve"][0], g["curve"][-1]
    out += [
        "",
        "2. Generic-reward arm, trained anyway",
        f"   reward {first['reward']:.2f} -> {last['reward']:.2f}, taste {first['taste']:.2f} -> {last['taste']:.2f}; "
        + (
            f"tripwire stopped it after {g['steps_run']} steps"
            if g["tripped"]
            else "tripwire did not fire"
        ),
    ]
    out += ["", "3. GEDD flywheel rounds"]
    for r in result["rounds"]:
        lk = r.get("locked", {})
        out.append(
            f"   round {r['round']} (codebook v{r['codebook_version']}): "
            f"locked taste {lk.get('incoming', 0):.0%} -> {lk.get('trained', 0):.0%} "
            f"(p={lk.get('mcnemar_p', 1):.1g}, CI {lk.get('ci')}) | "
            f"{'PROMOTED' if r['promoted'] else 'kept incoming'} | "
            f"production clean (PPI++) {r['ppi_clean_rate']:.0%} vs judge {r['judge_clean_rate']:.0%} | "
            f"gate {r['gate']}"
        )
        for n in r["notes"]:
            out.append(f"      note: {n}")
        if r["new_codes"]:
            out.append(
                f"      experts named: {', '.join(r['new_codes'])} -> codebook v{r['next_codebook_version']}"
            )
        if r["uncalibrated_judge_codes"]:
            out.append(
                f"      uncalibrated judge codes (need labelled positives): {', '.join(r['uncalibrated_judge_codes'])}"
            )
    out += ["", "Codebook history:"] + [f"   {h}" for h in result["codebook"]["history"]]
    return "\n".join(out)
