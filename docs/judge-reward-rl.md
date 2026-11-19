# GEDD's LLM-as-Judge as the RL reward model

*Design note, 2026-11-18. Status: research and plan. No new results yet.*

**Why this matters for the product.** RL makes an agent better at whatever the reward pays for. If the reward is
generic, RL is the fastest way to lose a product's taste. If the reward is the experts' own failure codebook, RL
becomes the fastest way to sharpen it. Most products have no gold answer to check against, so the codebook has to
reach the training loop through a judge.

GEDD was built so expert evidence becomes SFT data. This note moves its centre of gravity: the
**codebook-grounded LLM judge becomes the reward model**, and expert evidence calibrates and
audits that judge, inside a GRPO loop built on the practices of agentic-RL environment design: check headroom,
read the grader first, pay for the goal and charge for the cost, hold out content, and audit for reward hacking.

## 1. What we have and what's missing

| Piece | Where | State |
|---|---|---|
| Codebook reward model: per-code P(code) × severity weight, Platt calibration per code, conservative ensemble (mean − k·std), gate | `grounded_evals/reward/` | ✅ tested |
| LLM judges, scalar and codebook arms, per-field code probabilities, reference-free (image + extraction) | `10_bon_overopt.py` | ✅ script, not run |
| Best-of-N overoptimization curves (proxy vs gold against KL) | `grounded_evals/stats/overoptimization.py` | ✅ |
| RL environment, leak-free splits, GRPO advantages | `rl_env.py` | ✅ but the reward is computed **from gold** |
| Trainer-agnostic RL harness: groups, every reward per step, advantages, headroom, tripwire | `rl_harness.py` | ✅ |
| Reward audit with degenerate policies | `12_reward_audit.py` | ✅ for rule rewards only |
| PPI++ for unbiased estimates from judge + small expert sample | `grounded_evals/stats/ppi.py` | ✅ |

**The gap:** `rl_harness.py` scores with `rl_env.score(row, pred)`, which reads `row["gold"]`. That is
RL with a verifiable reward (RLVR). Nothing connects the judge, which is what transfers to domains
without gold, to the training loop.

## 2. The pivot in one picture

```
             ┌──────────── policy (GLM 5.3 Flash + LoRA) ───────────┐
 invoice ──► │  G tries per task                                     │
             └───────────────┬───────────────────────────────────────┘
                             ▼
   judge members (different model family; per field P(code))  ◄── codebook (codes, severity, blocking)
                             ▼
   CodebookRewardModel: Platt-calibrated, pay +1 for correct, charge severity,
                        conservative mean − k·std, blocking code ⇒ 0
                             ▼
            GRPO group advantage ──► LoRA update
                             │
   audit channel (never a reward): exact scorer on gold, failure-code counts, diversity,
                                   judge–gold gap; expert sample + PPI where no gold exists
                             ▼
   flywheel: disagreements and high-reward/low-confidence rollouts ──► experts ──► recalibrate, new codes
```

DocILE is the right first testbed **because** it has gold. The gold is hidden from the reward but
available to the audit, so every step tells us how far the judge reward has drifted from the truth.
That's Gao et al.'s proxy-vs-gold setup ([2022](https://arxiv.org/abs/2210.10760)) on a real task. Once the
loop holds there, the same code runs on a domain with no gold (finance, claims, Rx), where the
expert sample + PPI is the audit channel.

## 3. Agentic-RL design lessons, translated

| Lesson | What it means once the reward is a judge | GEDD implementation |
|---|---|---|
| **Check the model sometimes succeeds** (any-of-4 > one try) | Two kinds of headroom: the policy must vary within a group, **and the judge must rank those variants correctly**. GRPO only uses within-group ranking, so the reward model's quality is its *within-group pairwise accuracy vs gold*, not its overall AUROC | New metric in the judge audit: pairwise accuracy within groups, the share of groups the judge leaves flat, and its Spearman ρ with gold `exact` |
| **Write and read the grader first** ("a strict grader marked half the right answers wrong") | Read judged rollouts. Run a known-answer gate before every paid run (a known-answer judge check): a fixed set of extractions with known codes. Any mismatch stops the run | `judge_reward.py --check` known-answer gate. Ten judged samples printed side by side with gold |
| **Pay for the goal, charge for the cost** | Pay `P(correct)` from the judge, not only `1 − cost`. F8 already showed that the cost-only form nearly pays abstention | Judge reward = calibrated version of the `gedd` form: +1·P(no code) − Σ w_c·P(c), rescaled |
| **Hold out content, not just questions** | Unchanged, plus: the **calibration** slice must also be disjoint from the RL pool and the locked set | Three-way split by layout cluster: RL pool / calibration / locked test |
| **Train long enough; report the 95% range** | Unchanged. 18 steps, McNemar + cluster bootstrap on the locked set | `08_rigor.py`-style tests on `results_rl_*` |
| **Reward hacking: proxy → gap → amplify** | A judge adds new gaps that a string matcher lacks (next row) | Judge reward audit before training (§4) |
| A failed scorer call is a missing score, not 0 | A judge timeout scored 0 gives a good answer a negative advantage and trains against API noise | Drop the group for that step and log `scorer_failed_groups` |
| Reward judge ≠ eval judge; satisfying your own gate inflates its metric | The policy is GLM. `10_bon_overopt.py` currently judges with GLM too (self-preference) | Judge from another family. Report the locked set **only** with the exact scorer and experts |
| A reward can hold while outputs collapse onto one pattern | For extraction: watch for a collapse onto nulls or onto one formatting convention | Log the null rate and the distinct-value ratio per field each step |

### Judge-specific loopholes to audit

These are the gaps a reference-free judge has that `exact` doesn't:

1. **Plausible inventions.** A well-formed invoice number that isn't printed. F6's detector AUROC for
   `invented_value` was 0.55, the weakest code and the most expensive one, so this is where RL
   will push.
2. **Abstention.** If the judge can't see that a field is printed, all-null looks safe.
3. **Self-preference.** A same-family judge rates its own style and errors higher
   ([Panickssery et al., 2024](https://arxiv.org/abs/2404.13076)).
4. **Injection / persuasion.** Extra keys or values such as `"note": "verified against the page"`,
   or text inside a field addressed to the auditor.
5. **Format and length.** Values with extra context ("INV-123 (invoice no.)") that a lenient judge accepts.
6. **Judge noise as reward.** Temperature-0.7 members disagree, and if the policy's variants differ less than the judge's noise, GRPO
   learns noise. The conservative ensemble and `--judge-members 2` handle this, and the audit measures it.

## 4. Plan

### Phase 0: judge audit, no training (~$15, one day)

Reuses `10_bon_overopt.py` (K = 8 samples at T = 1, scalar and codebook judges), extended with
`12b_judge_audit.py`:

- **Known-answer gate:** 20 hand-built extractions covering each code, clean cases and loopholes 1–5.
- **Degenerate policies** from F8 plus judge-specific ones: all null, never null, dump candidates,
  plausible-invented values, injected "verified" note, padded values. Under the judge reward, each one
  must stay below the base model, as in the F8 table.
- **Reward-model quality:** per-code calibration (ECE) and AUROC on the calibration clusters; **within-group
  pairwise accuracy** and flat-group share on the RL pool; best-of-N curves (already scripted).
- **Go / no-go for RL:** within-group pairwise accuracy ≥ 0.65 and no degenerate policy at or above the base model.
  Below that, GRPO mostly learns judge noise, so fix the judge first (better prompt, a stronger judge model,
  per-field calls, more members).

### Phase 1: wire the judge into GRPO (code)

- `experiments/docile-invoices/judge_reward.py`: prompt (from `10_bon_overopt.py`), member calls with retries,
  parse per-field code probabilities, cache by (doc, sha(text)), return `None` on failure; build a
  `CodebookRewardModel` with calibrators fitted on the calibration clusters and loaded from JSON.
- `rl_env.py`: `judge_score(row, pred, members) -> Score` with the reward from the judge and `codes` from gold
  (audit only). The reward function never reads `row["gold"]`, and a unit test asserts it by passing a row with the gold removed.
- `rl_harness.py`: `--reward judge_codebook | judge_scalar`, `--judge-model`, `--judge-members`, `--ensemble-k`;
  drop groups on scorer failure; log the judge–gold gap next to proxy and gold `exact` (the tripwire and
  expert-review sheet already exist).
- Cost estimate gains a judge line: steps × tasks × group × members × (prompt + output) at inference price.

### Phase 2: experiment R2, "Can a codebook judge stand in for gold in RL?"

Same recipe as R1 (18 steps × 4 invoices × 4 tries, leak-free pool, locked set scored by `exact`), five arms:

| Arm | Reward | Role |
|---|---|---|
| A | `gedd` from gold | Upper bound (RLVR) |
| B | Scalar judge, P(field correct) | Generic LLM-as-judge baseline |
| C | Codebook judge, calibrated, pay + charge | The GEDD claim |
| D | C with 2 members, mean − k·std | Overoptimization control ([Coste et al., 2023](https://arxiv.org/abs/2310.02743)) |
| E | `no_invention` proxy (from R1) | Known-hackable control |

**Primary outcome:** locked-set field accuracy, C vs base and C vs B (Holm, McNemar + cluster bootstrap).
**Secondary:** the gap from A ("how much of RLVR does the judge recover"), per-code error changes, and the proxy–gold divergence over steps.
**Prediction:** C and D track A; B shows proxy up and gold flat (overoptimization); E drifts to nulls.
**Budget:** about $19 per arm for training plus judge calls (to be estimated in Phase 1), roughly $100–120 in total.

### Phase 3: close the flywheel (the part that's specifically GEDD)

Each round, the judge is recalibrated from new expert evidence rather than frozen:

1. Rank rollouts by member disagreement, and by high reward with low judge confidence (`active_learning.py`).
2. Experts label a small batch (`11_expert_kit.py`): verdict, code, correction.
3. Refit the Platt calibrators; add codes when an expert names a new failure (criteria drift, logged per round).
4. Corrections → SFT warm start or DPO pairs, so SFT becomes the *initialiser* and RL the main loop.
5. PPI++ on the expert sample gives an unbiased estimate of true reward for the round. If it disagrees with the judge's mean, the judge is being hacked.

This is experiment E3 (label efficiency, multi-round) with RL as the improver.

### Phase 4: beyond verifiable tasks and single turns

- **Domain without gold** (e.g. the finance domain pack): hard-fail invariants become blocking codes and
  zero the reward, the way a research-agent reward zeroes an answer given without opening a document. Expert sample + PPI
  is the only gold.
- **Agentic traces:** the judge scores the trajectory, not just the answer. Use the trace-evaluation codes (first divergence point,
  tool boundary drift, source hierarchy drift, silent numeric corruption) as per-step codes. Add an efficiency term
  (correctness × efficiency) so cost can't be hidden in extra tool calls. `rl_env` grows a
  multi-turn episode (one datum per assistant turn, sharing the episode advantage).

## 5. Open decisions

- **Judge model.** It must be a vision model from a different family than GLM (e.g. a Qwen-VL or Kimi model), served behind
  the same OpenAI-compatible endpoint settings as the policy.
  Cost and latency per call decide members × group size.
- **Reference-free vs reference-guided.** Reference-free is what transfers. A reference-guided judge (given the
  expert correction) is a cheaper intermediate for domains where experts write corrections.
- **Calibration labels on DocILE.** Use the exact scorer as stand-in "experts" (as `10_bon_overopt.py` does), then
  replace it with real double labels from L1 when they exist.

## References

Literature already cited in [research.md](research.md); additions: Gao, Schulman & Hilton (2022) reward-model
overoptimization; Coste et al. (2023) reward-model ensembles; Panickssery et al. (2024) self-preference.
