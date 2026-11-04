# What's next: hill-climbing past SFT with GEDD, DPO and RL

*Research and plan for round 2 of the DocILE fine-tune. Every number marked "measured" comes from our 500-document test
set; costs are Fireworks serverless list prices (Oct 2026) and are estimates.*

## 1. Where SFT got us, and what's left

SFT on 1,400 invoices took GLM 5.3 Flash from 78.5% to 88.4% of fields correct. Splitting every remaining error into
three kinds shows *what* it fixed and *what* it didn't (measured):

| Error type | What it means | Baseline | After SFT | Change |
| --- | --- | --- | --- | --- |
| **Invented** | Field isn't labelled, model returned a value | 600 | 228 | **−62%** |
| **Wrong value** | Field is labelled, model returned a different value | 363 | 220 | −39% |
| **Missed** | Field is labelled, model returned null | 110 | 134 | **+22%** |
| **Total** | of 5,000 field cases | 1,073 | 582 | −46% |

Three lessons:

1. **SFT mostly taught restraint.** Invented values fell by almost two thirds. That's the house rule "only extract what
   is printed".
2. **It slightly over-learned it.** Missed fields went *up*. The model now sometimes says null when the value is
   there: the classic trade-off a pure imitation objective can't resolve on its own.
3. **The rest is about choosing, not reading.** The biggest remaining buckets are choice errors: which order number
   (`order_id`: 104 errors), which company is the customer or vendor (`customer_billing_name` 78, `vendor_name` 77).

Remaining errors per field after SFT (measured):

| Field | Invented | Wrong value | Missed | Total |
| --- | --- | --- | --- | --- |
| order_id | 37 | 19 | 48 | 104 |
| customer_billing_name | 9 | 59 | 10 | 78 |
| vendor_name | 14 | 49 | 14 | 77 |
| document_id | 30 | 31 | 5 | 66 |
| amount_total_gross | 26 | 28 | 7 | 61 |
| date_issue | 36 | 11 | 10 | 57 |
| amount_due | 27 | 14 | 7 | 48 |
| currency_code_amount_due | 37 | 1 | 10 | 48 |
| payment_terms | 12 | 6 | 15 | 33 |
| date_due | 0 | 2 | 8 | 10 |

**Not every "error" is an error.** Some "invented" values are really label gaps: a visible issue date the annotators
didn't label (`date_issue`: 36 "invented"). Some "wrong values" are defensible variants: the division vs the parent
company as vendor. A fixed exact-match metric can't tell these apart. **That is the job GEDD does**, and it has to
happen before any more training, or round 2 trains the model to copy annotation mistakes.

## 2. Which technique fixes which error

| Remaining problem | Best tool | Why |
| --- | --- | --- |
| Label gaps and inconsistent labels | **GEDD review → corrected SFT targets** | Garbage in, confident garbage out. Fix the evidence first. |
| Not enough examples / train-test resolution mismatch | **SFT round 2** | All 5,180 training docs, trained at the 1,344 px the sampler accepts, 2 epochs. |
| Choice errors: which order number, which company | **DPO** | A preference objective learns "this, *not* that" directly; SFT only sees the right answer. |
| Over-cautious nulls vs invented values | **DPO with targeted pairs** | Pairs where chosen = the value and rejected = null (and the reverse) teach the boundary from both sides. |
| Errors that cost different amounts | **RL with a GEDD-weighted reward** | A wrong amount is a wrong payment; a missed payment term is a minor fix. RL can optimise that directly. |
| Post / block / human-review routing | **Decision tuning of a small judge** | Fireworks' `decision_loop` trains a calibrated K-way classifier: the GEDD gate as a fine-tuned model. |

### SFT round 2: cleaner, bigger, matched

- **Clean targets.** Apply GEDD's SME corrections to the training labels (fill label gaps, settle division vs parent).
- **More data.** All 5,180 training documents instead of 1,400.
- **Match train and test resolution.** Train at 1,344 px. Round 1 trained at 1,600 px and scored at 1,344 px because the
  serverless sampler caps an image at 2,048 tokens.
- **Up-weight hard fields.** Oversample documents with order numbers and multi-company headers.
- **Cost:** about 10M tokens per epoch at ~1,950 tokens/doc → **~$90 per epoch on GLM 5.3 Flash**, or **~$23 on
  Nemotron 3.5 Super VL** ($2.32/M) if we want a cheaper vision base to compare.

### DPO: teach the choices

**Building the pairs (on training documents only, never the test set):**

1. Run the SFT model on training documents, sampling 4 answers per document at temperature 0.7.
2. Grade each answer field by field with the same scorer we use for evaluation.
3. Make pairs per document: **chosen** = an answer with every field right (or the SME-corrected label);
   **rejected** = an answer that fails, tagged with its GEDD failure code (`INVENTED_CURRENCY`, `WRONG_ORDER_NUMBER`,
   `DIVISION_VS_PARENT`, `MISSED_FIELD`, …).
4. Balance the failure codes so DPO isn't dominated by one error type, and include both directions of the
   null boundary (value-vs-null and null-vs-invented).

**Training:** Fireworks cookbook `recipes/dpo_loop.py`. It accepts `{"chosen": …, "rejected": …}` rows, supports
base64-image multimodal data, and uses the SFT checkpoint as the frozen reference. Defaults: β = 0.1 (must be
between 0 and 0.5), learning rate 1e-5. Start from the SFT adapter, not the base model.

**Cost estimate:** ~2,000 training docs × 4 samples to mine pairs (~$12 prefill + ~$7 sampling), then ~1,000 pairs ×
~4,000 tokens ≈ 4M training tokens (~$36) → **~$55 per DPO round on GLM 5.3 Flash.**

**Variant:** ORPO (`recipes/orpo_loop.py`) combines the SFT and preference losses with no reference model. It's
cheaper if we want one combined round.

### RL: optimise the business cost, not the string match

Fireworks cookbook `recipes/rl_loop.py`. The reward is **verifiable**: it's our own scorer, so no judge model is needed
for the base signal.

```text
reward = Σ over fields  w(field, failure_code) × (1 if correct else −1)
         where w comes from GEDD severity:
         wrong or invented amount = catastrophic,  wrong vendor / customer = high,
         missed payment terms     = low,           label-gap cases          = excluded
```

This optimises what an AP team actually cares about. Run it after DPO, once the reward weights have SME sign-off.

### Decision tuning: make the GEDD gate a model

GEDD's gate decides post / block / send to human review. Instead of a prompted LLM-as-Judge only, train a small
judge with `recipes/decision_loop.py`, which produces a calibrated checkpoint (one fitted temperature per question
type) from SME-labelled decisions. That gives calibrated confidence for routing and is cheap enough to run on every
invoice.

## 3. The guardrails on the hill-climb

- **Lock the test set; add a dev set.** Round 1 used the test set once. Hill-climbing over many rounds on the same test
  set overfits it. Carve a **dev split from the training clusters** (by layout cluster) for checkpoint selection and
  pair mining. Touch the 500-document test set **once per round**, for the final claim.
- **Same bar every round.** A round counts only if it beats the previous round on the locked test set with **both**
  McNemar p < 0.05 **and** a layout-cluster bootstrap interval above zero. Report the unseen-layout subset every time.
- **Report the trade-offs.** Track invented / wrong / missed separately; a round that cuts invented values by raising
  missed ones (as round 1 partly did) must say so.
- **Track document-level success.** The business metric is invoices with all fields right (12.8% → 38.8% after round 1),
  plus "both money fields right" (74% → 84%).

## 4. The round-2 plan

| Step | What | Owner | Cost |
| --- | --- | --- | --- |
| 1 | GEDD review of the 582 remaining errors: real error / acceptable variant / label gap, with a failure code | AP SME + PM | time |
| 2 | Build the codebook, corrected labels and a dev split by layout cluster | ML | free |
| 3 | Re-score round 1 under the corrected labels (does the 88.4% move?) | ML | free |
| 4 | SFT round 2: corrected labels, all training docs, 1,344 px | ML | ~$90 / epoch |
| 5 | DPO from the round-2 SFT checkpoint on mined, code-balanced pairs | ML | ~$55 |
| 6 | Decision-tune the gate on SME post / block / review labels; measure judge-human agreement | ML + SME | small |
| 7 | Optional: RL with the GEDD-weighted reward | ML | depends on rollouts |
| 8 | Each round: locked test set, McNemar + cluster bootstrap, unseen layouts, error-type table | ML | ~$3 / scoring run |

## Sources

- Fireworks cookbook (github.com/fw-ai/cookbook), `training/recipes/`: `sft_loop.py`, `dpo_loop.py`, `orpo_loop.py`,
  `rl_loop.py`, `decision_loop.py`; preference row formats in `training/utils/data.py`.
- Fireworks serverless training pricing (docs.fireworks.ai/fine-tuning/training-api/serverless).
- Rafailov et al., *Direct Preference Optimization: Your Language Model is Secretly a Reward Model*, NeurIPS 2023.
- Hong et al., *ORPO: Monolithic Preference Optimization without Reference Model*, 2024.
- Measured figures: this repo, `results/results_glm_1344.jsonl` and `results/results_glm_sft_1344.jsonl`.
