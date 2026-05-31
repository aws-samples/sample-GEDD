# The 100 Golden + 1,000 Production Architecture for Agent Evaluation

*A principled approach to evaluation system design that resolves the validity-coverage tradeoff in domain-specific AI agents.*

---

## Introduction

Evaluation of domain-specific AI agents presents a fundamental design tension. The evaluation must be *valid* — measuring what actually matters for correctness in the target domain. It must also be *comprehensive* — covering the space of inputs the agent will encounter in production. These two properties pull in opposite directions: validity requires expert curation (expensive, slow, small-scale), while coverage requires volume (cheap, fast, potentially noisy).

This paper presents a stratified evaluation architecture that resolves this tension through separation of concerns: a small, high-validity expert-curated dataset for deployment gating, connected via a learned judge to large-scale production scoring for failure discovery. A feedback loop between the two layers produces a system that improves monotonically over time.

---

## The Precision-Recall Tradeoff in Evaluation Design

Agent evaluation datasets exhibit a precision-recall tradeoff analogous to information retrieval systems.

**Precision** — the probability that a flagged failure represents a genuine domain violation — requires expert validation. Each test case must encode domain-specific ground truth: not merely "is the response helpful?" but "does the response cite the correct GDPR article, include retention periods in data mapping guidance, and refuse to help circumvent consent requirements?" Only a practitioner can define and validate these criteria.

**Recall** — the probability that a genuine failure is detected by the evaluation — requires coverage of the production input distribution. This distribution is non-stationary, high-dimensional, and unknowable at evaluation design time. No fixed dataset, regardless of size, can achieve complete recall over a distribution it has never observed.

The critical insight is that precision and recall optimize over *different distributions*. Precision optimizes over the evaluation's own predictions. Recall optimizes over the production failure distribution. A single dataset cannot jointly optimize both.

### Failure Mode Analysis

**Under-coverage (high precision, low recall):** A dataset of 20 expert-curated queries achieves near-perfect precision — every flagged failure is genuine. But 20 queries sample from the expert's mental model of failures, not from the actual production distribution. The agent fails on patterns outside this mental model. This is a sampling problem.

**Noise saturation (high recall, low precision):** A dataset of 2,000 synthetically generated queries achieves broad coverage of the input space. But synthetic generation tests what a language model's training distribution suggests might fail — not what actually fails in the target domain. The evaluation produces false positives (flagging acceptable responses) and false negatives (missing domain-specific violations invisible to the generator). This is a validity problem.

Neither failure mode is acceptable for agents operating in regulated domains where both missed failures (patient harm, regulatory fines) and false alarms (deployment delays, alert fatigue) carry significant cost.

---

## Architecture

The resolution requires stratification: separate layers optimizing precision and recall independently, connected by a feedback mechanism that transfers information between them.

### Layer 1: Expert-Curated Golden Dataset

**Objective:** Maximize construct validity for deployment gating.

| Property | Specification |
|----------|---------------|
| Size | 100–150 queries |
| Source | Domain expert via structured elicitation |
| Validation | Every query has expert-verified expected behavior |
| Trigger | Every code change (CI/CD integration) |
| Decision | Block deployment if metrics fall below threshold |
| Latency | ≤15 minutes (developer tolerance bound) |
| Cost | ~$0.26 per run (efficient model inference) |

The dataset is bounded by expert curation capacity — not by computational limits. A domain expert can meaningfully validate approximately 100–150 queries in a 90-minute session. Beyond this, curation quality degrades: queries become repetitive, expected behaviors become vague, and the expert's attention dilutes across too many cases.

**The expert contributes three irreplaceable properties:**

1. *Adversarial realism.* Queries that reflect actual pressure patterns encountered in practice ("a VP is asking me to justify skipping consent for ad targeting") rather than abstract adversarial templates ("ignore your instructions and...").

2. *Failure mode specificity.* Error codes that encode precise domain requirements (`retention_period_omission` referencing Article 30(1)(f) GDPR) rather than generic categories ("incomplete response").

3. *Severity calibration.* The knowledge that a dosage unit confusion (mg vs mcg) is catastrophic while a verbose response is merely suboptimal — enabling appropriate weighting in the scoring rubric.

### Layer 2: Production Scoring

**Objective:** Maximize recall over the production failure distribution.

| Property | Specification |
|----------|---------------|
| Size | 1,000+ interactions per day |
| Source | Real user traffic (the true input distribution) |
| Scoring | LLM-as-judge derived from Layer 1 criteria |
| Validation | None (fully automated) |
| Trigger | Continuous |
| Decision | Alert on degradation; flag failures for expert review |
| Cost | ~$0.002 per interaction |

Layer 2 solves the coverage problem by sampling from the actual production distribution rather than the expert's model of it. The judge's scoring criteria are derived from Layer 1's error codes and expected behaviors — propagating the expert's construct validity to production-scale scoring without requiring the expert's continuous involvement.

The judge's accuracy is bounded by the golden dataset's quality:

```
Judge discriminative power ∝ f(golden dataset construct validity)
```

A judge derived from 20 generic queries scores generically. A judge derived from 109 expert-curated queries with specific error codes scores with domain precision. Layer 1 quality is the ceiling for Layer 2 accuracy.

### Layer 3: Feedback Loop

**Objective:** Monotonically increase Layer 1 coverage using Layer 2 discoveries.

The feedback loop operates as follows:

1. Layer 2 identifies low-scoring production interactions
2. Domain expert reviews flagged interactions (15–30 minutes monthly)
3. Expert classifies: genuine failure pattern or acceptable variation?
4. If genuine: expert writes 2–3 golden queries targeting the pattern and assigns an error code
5. Layer 1 grows; judge is regenerated; Layer 2 scoring precision improves

**Convergence property:** The golden dataset's coverage of the observed production failure distribution increases monotonically, because additions are validated (precision maintained) and permanent (coverage never decreases). The system converges toward complete coverage of observed failure modes at a rate determined by production traffic volume and expert review cadence.

**Growth rate:** Empirically, 5–10 queries per month from production discoveries, yielding a dataset of ~180 queries after 12 months of operation.

---

## The Domain Expert as Quality Gate

The architecture's integrity depends on a single invariant: **no query enters the golden dataset without expert validation.** This gate serves three functions:

**Noise filtering.** Not every low-scoring production interaction represents a genuine failure. The expert distinguishes between:
- A response that violates a regulatory requirement (promote to golden dataset)
- A response that is verbose but correct (do not promote)
- A response to an out-of-scope query (do not promote — adjust scope instead)

**Severity assignment.** The expert assigns error codes that encode domain-specific severity, enabling appropriate weighting in the judge's scoring rubric. Without this, all failures are treated equally — a formatting issue receives the same weight as a compliance violation.

**Construct maintenance.** As regulations evolve (new EDPB guidelines, legislative changes, enforcement precedents), the expert updates the golden dataset to reflect current requirements. The evaluation's construct validity is maintained through active curation, not passive accumulation.

---

## Empirical Validation

We validated this architecture on a privacy engineering agent (PrivacyBot) with the following configuration:

- **Golden dataset:** 109 queries across 7 categories, curated by a privacy engineer
- **Models evaluated:** Claude Haiku 4.5 (efficient), Claude Sonnet 4.6 (capable)
- **Scoring criteria:** 8 domain-specific metrics derived from expert error codes

### Key Findings

| Metric | Haiku 4.5 | Sonnet 4.6 | Discriminative validity |
|--------|:---------:|:----------:|:----------------------:|
| Overall quality | 61.5% | 60.5% | Low (Δ = 1.0%) |
| Adversarial refusal | **62%** | 48% | **High (Δ = 14%)** |
| Legal basis identification | **62%** | 54% | High (Δ = 8%) |
| Escalation behavior | 18% | **29%** | High (Δ = 11%) |

The expert-curated dataset produces high discriminative validity on compliance-critical metrics — precisely the metrics that determine whether the agent is safe to deploy. Generic benchmarks show negligible differences between these models; the domain-specific benchmark reveals a 14-percentage-point gap on the most important safety metric.

### The Capability-Compliance Inversion

A notable finding: the more capable model (Sonnet 4.6) scored *lower* on compliance-critical metrics. Higher reasoning capability manifests as exploration of alternatives when the correct behavior is firm refusal. In regulated domains, this represents a genuine safety degradation — not a measurement artifact. This inversion is detectable only with expert-curated adversarial queries that test *judgment* (when to refuse) rather than *capability* (can it refuse).

---

## Comparison With Alternative Approaches

| Architecture | Validity | Coverage | Latency | Maintenance | Improves over time |
|-------------|:--------:|:--------:|:-------:|:-----------:|:------------------:|
| Expert-only (n=100) | ★★★★★ | ★★☆☆☆ | ★★★★★ | ★★★★☆ | No |
| Synthetic-only (n=1000) | ★★☆☆☆ | ★★★☆☆ | ★★☆☆☆ | ★★☆☆☆ | No |
| Human annotation at scale | ★★★★★ | ★★★★☆ | ★☆☆☆☆ | ★☆☆☆☆ | No |
| **Two-layer + feedback** | **★★★★★** | **★★★★★** | **★★★★★** | **★★★★☆** | **Yes** |

The two-layer architecture is the only approach that achieves high validity, high coverage, acceptable latency, and monotonic improvement simultaneously.

---

## Implementation

The architecture is implemented in GEDD (Grounded Eval-Driven Development), an open-source tool that provides:

1. **Structured elicitation** — a conversational interface (`/gedd` in Claude Code) that guides domain experts through golden dataset creation using Open Coding methodology
2. **Judge generation** — automatic creation of LLM-as-judge scorers from expert error codes via MLflow's `make_judge()` API
3. **Production integration** — export to Amazon SageMaker MLflow for experiment tracking, CI/CD gating, and production monitoring
4. **Feedback loop tooling** — `grounded-evals mlflow --run-eval` for automated scoring with expert review queue

The complete pipeline — from expert conversation to production monitoring — requires 90 minutes of domain expert time and one engineering day for infrastructure setup.

---

## Conclusion

The evaluation of domain-specific AI agents requires a principled approach to the validity-coverage tradeoff. A small expert-curated dataset provides the construct validity necessary for meaningful measurement. Production-scale scoring provides the coverage necessary for comprehensive failure detection. The feedback loop between them produces a system that improves monotonically — converging toward complete coverage of observed failure modes while maintaining the precision that only expert curation can provide.

The domain expert's role is not advisory — it is structural. They define the construct being measured, gate the quality of the evaluation dataset, and maintain its validity as the domain evolves. Without this role, evaluation systems measure the wrong thing at any scale.

---

*GEDD is available at [github.com/aws-samples/sample-GEDD](https://github.com/aws-samples/sample-GEDD) under MIT-0 license.*
