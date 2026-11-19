# The RL eval flywheel: improve an AI agent app's taste, round after round

RL makes an agent better at whatever the reward pays for. Pay for something generic and RL is the
fastest way to lose your product's taste. Pay for your experts' failure codebook, audit it, and check
every run against an independent signal, and RL becomes the fastest way to sharpen that taste.
This guide is for product managers and ML engineers who want that loop for an agent app.

Code: [`grounded_evals.flywheel`](../../grounded-evals/src/grounded_evals/flywheel/) · Try it:
`grounded-evals flywheel demo` · Design background: [LLM-as-Judge as the reward](../judge-reward-rl.md)

## One round

```
 codebook vN (experts' taste) ──► taste reward
   1 AUDIT     degenerate policies (skip every check, escalate everything) must not out-score the
               current agent under the reward. If one does, fix the reward; don't train.
   2 TRAIN     RL under the taste reward (any trainer). Every step logs reward next to an independent
               audit signal; the tripwire stops the run when reward rises while taste falls and sends
               the worst traces to experts.
   3 MEASURE   locked tasks, never trained on, scored by the expert standard. Exact McNemar + cluster
               bootstrap: a gain counts only if both agree.
   4 SHIP?     promote the trained agent only if taste rose significantly and the tripwire stayed quiet.
   5 OPERATE   gate every production trace (allow / revise / review / block). A random expert sample
               plus judge scores on everything give a PPI++ estimate of the true clean rate.
   6 GROW      expert labels refit the judge calibration; failures experts name that the codebook
               lacks (from the tripwire queue or production) become codebook vN+1.
```

| Stage | What protects the taste |
|---|---|
| Reward | **Pay for the goal, charge for the cost**: `efficiency × clamp(goal − Σ severity × P(code), 0, 1)`. Blocking codes zero the reward, so no amount of fluency buys back a hard fail |
| Detectors | Exact rule checks decide the failures you can check (they override judges); LLM-judge members, Platt-calibrated per code against expert labels, cover the rest; disagreement is charged as risk |
| Missing scores | A failed judge call makes the reward `None` and the whole group is dropped. Scoring it 0 would train against API noise |
| Audit | Run before any GPU time. It's the cheapest place to catch a reward that pays for the wrong thing |
| Tripwire | Compares windows of steps, so noise doesn't fire it. Needs an audit signal the policy isn't trained on: a different-family judge, verifiable checks, or a small expert sample |
| Promotion | The locked set decides, not the reward. A round with no significant gain ships nothing, and that is reported |
| Production | PPI++ is unbiased however wrong the judge is. A gap between the judge's estimate and PPI++ means the judge, and any reward built on it, is drifting |

## What the demo shows

`grounded-evals flywheel demo` runs everything on a simulated TravelBot agent: a tabular agent
trained with real GRPO updates, noisy simulated judges, and a hidden expert standard that includes a
failure the starting codebook doesn't have. **It is a simulation that exercises the mechanics; its
numbers are not GEDD findings.** It runs in seconds, needs no API key, and is covered by the tests.

```text
1. Reward audit before training (taste = share of traces with no expert-named failure)
   generic      FAIL  base 0.75, skip_every_check 0.86 LOOPHOLE, escalate_everything 0.23
   codebook_v1  pass  base 0.52, skip_every_check 0.24, escalate_everything 0.08

2. Generic-reward arm, trained anyway
   reward 0.81 -> 0.93, taste 0.67 -> 0.31; tripwire stopped it after 6 steps

3. GEDD flywheel rounds
   round 1 (codebook v1): locked taste 66% -> 83% (p=1e-06) | kept incoming
      note: tripwire at step 12: reward rose while the audit signal fell; experts reviewed the 20 worst traces
      experts named: missed_passenger_rights -> codebook v2
   round 2 (codebook v2): locked taste 68% -> 96% (p=2e-19) | PROMOTED
   round 3 (codebook v2): locked taste 98% -> 98% (p=1) | kept incoming
      note: trained policy not promoted: no significant taste gain on the locked set
```

What to read from it:

1. **A generic reward fails the audit before training**: "helpful and quick" pays an agent that skips every check more than the current agent. Trained anyway, its reward climbs while taste halves, and the tripwire stops it.
2. **RL finds the hole in your codebook.** Codebook v1 doesn't charge for rebooking an EU 261 cancellation without mentioning cash compensation. RL drifts there because it saves tool calls, the tripwire fires, experts review the worst traces and name `missed_passenger_rights`.
3. **The next round fixes it** under codebook v2, and the gain passes both significance tests on the locked set.
4. **The flywheel stops when there's nothing left to gain**: round 3 ships nothing.
5. **It tells you what it doesn't know**: the new code has no judge calibration yet, because experts haven't labelled enough positives, and the judge's clean-rate estimate (70%) lags the PPI++ estimate (100%). Both are reported rather than hidden.

## Plug in your own agent app

```python
from grounded_evals.flywheel import AgentApp, Codebook, LLMJudgeDetector, RuleDetector, TasteReward, run_flywheel

codebook = Codebook.load("codebook.yaml")          # your experts' codes: severity, blocking, description

def make_reward(cb: Codebook) -> TasteReward:
    return TasteReward(cb, [
        RuleDetector("rules", my_exact_checks),      # e.g. booked before the confirm tool call
        LLMJudgeDetector("judge-a", client, "<judge model, different family from the agent>", cb),
        LLMJudgeDetector("judge-b", client, "<second judge>", cb),
    ], goal_fn=did_the_user_get_what_they_needed)

app = AgentApp(
    train_tasks=..., locked_tasks=..., production_tasks=...,   # split by group; locked is never trained on
    make_reward=make_reward,
    make_trainer=lambda policy: MyTrainer(policy),             # adapter over TRL, verl, OpenRLHF, ...
    degenerate={"skip_every_check": ..., "refuse_everything": ...},
    expert=MyExpertQueue(),        # label(task, trace) -> codes; define(code) -> Code
    taste_ok=passes_expert_standard,
    audit=independent_check,       # never the training reward
)
reports, agent, codebook = run_flywheel(app, codebook, current_agent, rounds=3)
```

- **Policy** is anything with `sample(task, n) -> list[trace]`; a trace is a dict of your agent's messages and tool calls, with a `tool_calls` count. Fields starting with `_` are never shown to judges.
- **Trainer** is `policy()` plus `update(groups)`; each group carries the traces, rewards and GRPO advantages. Token-level trainers keep their own token ids and logprobs.
- **Expert** is your review queue. In practice `label` is an annotation task in the GEDD app and `define` is the expert writing the new code's severity and description.
- **Thresholds** (gate, tripwire window, label budgets) live in `RoundConfig` and are product decisions: calibrate them on expert-labelled cases and run the gate in shadow mode first.
- Check a codebook before you train on it: `grounded-evals flywheel audit codebook.yaml`.

## What it doesn't do yet

- No trainer ships with it for real models; the invoice case study's [`rl_harness.py`](../../experiments/docile-invoices/rl_harness.py) and this package share the same protocol shape for adapters.
- The tripwire needs an audit signal. Without a different-family judge, verifiable checks or a small expert sample per step, it can't fire.
- Calibration needs labelled positives for every judge-scored code; rare and new codes stay uncalibrated until experts label enough of them, and the report lists them.
