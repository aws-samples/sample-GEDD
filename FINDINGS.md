# GEDD findings log

Each finding has an id, a status, the evidence and the script that regenerates it. CI re-runs the
scripts on every pull request and fails if a committed result drifts. When a new round changes a
finding, update its status and date here rather than deleting it: superseded findings stay as a
record.

**Status:** ✅ proven (passes the GEDD bar) · ⚠️ pilot (real data, limited design) · ❌ not supported · ⏳ planned

**The GEDD bar for "real":** exact McNemar p < 0.05 after Holm correction across the round's
comparisons **and** a group-bootstrap 95% interval that excludes zero, with the minimum detectable
effect (MDE) reported, so a null result can be read as underpowered or as evidence of no effect.

| Id | Finding | Status | Updated |
|---|---|---|---|
| [F1](#f1) | Fine-tuning beats the base model on real invoices (+9.8 pts; invoices fully correct 3×) | ✅ | 2026-11-03 |
| [F2](#f2) | The gain holds on layouts never seen in training (+4.7 pts) | ✅ | 2026-11-03 |
| [F3](#f3) | Prompting gains are real overall but not on unseen layouts (underpowered) | ✅ / ❌ | 2026-11-03 |
| [F4](#f4) | Aggregate accuracy hides error trade-offs (fewer invented values, more missed ones) | ✅ | 2026-11-03 |
| [F5](#f5) | Requiring both tests changes conclusions (rules prompt at invoice level: McNemar yes, bootstrap no) | ✅ | 2026-11-03 |
| [F6](#f6) | With weak gold-free detectors, a decomposed codebook reward doesn't reliably beat a scalar reward at the gate | ⚠️ null | 2026-11-03 |
| [F7](#f7) | PPI++ online estimates stay valid; a weak judge saves few expert labels | ⚠️ | 2026-11-03 |
| [E1](#e1) | Criteria source: generic vs a-priori expert vs LLM-written vs GEDD codebook, at equal expert budget | ⏳ | — |
| [E2](#e2) | Codebook vs scalar LLM-judge reward under best-of-N pressure (overoptimization) | ⏳ script ready | — |
| [E3](#e3) | Expert-label efficiency and multi-round online improvement | ⏳ | — |
| [L1](#l1) | Inter-annotator agreement and label-gap correction on the 582 remaining errors | ⏳ kit ready | — |

All case-study findings use the same setup: DocILE scanned business documents, 500 locked test
documents = 5,000 field cases in 204 layout clusters (124 documents on unseen layouts), 10 fields,
normalised exact match, absent fields must be null. Systems: an open vision-language model at
temperature 0, two prompt harnesses, and a vision LoRA fine-tune on 1,400 training documents.
Details: [experiments/docile-invoices/](experiments/docile-invoices/).

---

### F1
**Fine-tuning beats the base model.** Field accuracy rose from 78.5% to 88.4%: +9.8 pts, 625 vs
134 discordant cases, Holm p ≈ 1e-75, cluster CI [+7.7, +12.2], MDE 3.2. Invoices with all
10 fields correct rose from 12.8% to 38.8%: +26.0 pts, CI [+19.2, +33.5]. Compute was under $50.
*Script:* `08_rigor.py` → `results/rigor.json`.

### F2
**The gain transfers to unseen layouts.** +4.7 pts on the 124 unseen-layout documents, Holm
p ≈ 9e-6, CI [+1.8, +8.1], MDE 4.6. That's smaller than the +9.8 overall, so part of the gain is
layout familiarity. *Script:* `08_rigor.py`.

### F3
**Prompting helps overall but the unseen-layout result is uninformative.** Harness A (rules) +2.2
and Harness B (rules + OCR) +2.6 are real overall. Harness B on unseen layouts is +0.2,
CI [−3.1, +3.6], but the MDE there is 4.9, so the test couldn't have detected a gain of that size.
Record it as *underpowered*, not *no effect*. *Script:* `08_rigor.py`.

### F4
**Aggregate scores hide trade-offs.** Errors out of 5,000 cases:

| System | Invented | Wrong value | Missed | Total |
|---|---|---|---|---|
| Base | 600 | 363 | 110 | 1,073 |
| Harness B | 390 | 303 | 251 | 944 |
| Fine-tune | 228 | 220 | 134 | 582 |

The fine-tune mostly learned restraint: invented values fell 62%. Missed values rose 22% relative
to the base model. Prompting traded invented values for missed ones. Each round should report
changes by failure code. *Script:* `08_rigor.py`.

### F5
**Requiring both tests matters.** At the invoice level, the rules prompt gains +4.0 pts with
McNemar p = 0.01, but the layout-cluster interval [−0.4, +8.6] includes zero. Layouts share
mistakes, so case-level tests alone are overconfident. Under the GEDD bar this is not a real gain.
*Script:* `08_rigor.py`.

### F6
**Decomposition needs good detectors.** This is a pilot on the fine-tune's saved predictions, using
gold-free detectors built from the other systems' answers. Per-code detectors were calibrated on
half the layout clusters and evaluated on the other half, over 50 splits, with gating at matched
straight-through rates.

- The detectors are calibrated (ECE ≤ 0.02) but weak: AUROC 0.55 for invented values, 0.73 for
  wrong values, 0.83 for missed values.
- At 10% straight-through, the codebook reward posts about 11 pts more fully correct invoices in
  90% of splits, but the 95% range across splits crosses zero. At 20–40% there's no difference.
- *Implication:* under calibration, the codebook reward is the expected-cost-optimal gate, but its
  advantage scales with detector quality. E2 tests it with real LLM judges.

*Script:* `09_reward_gate_ppi.py` → `results/reward_gate_ppi.json`, `figures/gate_tradeoff.png`.

### F7
**PPI++ online estimates stay valid.** The pilot treats the 5,000 cases as a production stream,
with a random "expert" sample of n = 25–400 and the agreement score as the judge. Coverage was
92–97% at a nominal 95%, slightly low at n ≤ 50. Intervals were only 1–6% narrower than expert
labels alone, because PPI++ correctly discounts a weak judge. *Script:* `09_reward_gate_ppi.py`,
`figures/ppi_width.png`.

---

### E1
**Where should criteria come from?** Four arms at a fixed 10 expert-hours per domain: a generic
judge, an expert rubric written before seeing outputs, an LLM-written rubric or checklist, and the
GEDD codebook. Primary outcome: macro-F1 by failure code against held-out double-labelled expert
judgments. Hypothesis: the codebook beats the generic judge and the LLM rubric, and matches or
beats the a-priori expert rubric. *Needs:* experts and a second domain without a verifiable reward.

### E2
**Reward form under optimization pressure.** K = 8 samples per document. Scalar vs codebook LLM
judges, each as a single member and as a conservative ensemble. Best-of-N curves of proxy reward
vs gold accuracy. Hypothesis: the codebook reward peaks later and higher, and the ensemble removes
any decline. *Script:* `10_bon_overopt.py` (≈ $12). *Needs:* DocILE data and an API key.

### E3
**Expert-label efficiency and the online loop.** n ∈ {50, 100, 200, 400} expert labels, chosen at
random or by lowest reward plus highest disagreement. Three simulated production rounds with
PPI++ estimates and SFT/DPO retraining. Hypothesis: guided selection needs fewer labels, and
locked-set accuracy rises every round.

### L1
**Label quality.** Two experts review the 582 remaining errors plus 10% correct controls, with 20%
overlap. Report Krippendorff's α for verdict and code, then re-score every system under the
adjudicated labels. *Script:* `11_expert_kit.py`.
