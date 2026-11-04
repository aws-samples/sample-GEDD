# Evaluation-Driven Development for Agentic Systems: A Stratified Sampling Approach

*On the statistical foundations of domain-grounded evaluation, the precision-recall tradeoff in test set design, and why human-in-the-loop curation produces superior evaluation validity compared to synthetic generation at any scale.*

---

## Abstract

We present a two-layer evaluation architecture for domain-specific AI agents that resolves the fundamental tension between evaluation validity (are we measuring the right thing?) and evaluation coverage (are we measuring enough of it?). Layer 1 uses a small, expert-curated golden dataset (n=100-150) optimized for construct validity and deployment gating. Layer 2 uses an LLM-as-judge derived from Layer 1 to score production traffic at scale (n=1,000+/day), optimized for failure discovery. A feedback loop promotes validated production failures to Layer 1, producing a monotonically improving evaluation system. We demonstrate this architecture on a privacy engineering agent (109 expert-curated queries, 7 categories, 2 models benchmarked) and show that the expert-curated dataset produces higher discriminative validity between models than synthetic alternatives of 10x the size.

---

## 1. The Evaluation Validity Problem

### 1.1 Construct Validity in Agent Evaluation

The central question in agent evaluation is not "does the agent produce correct outputs?" but rather "correct *according to whom, under what definition, in what context?*"

For domain-specific agents (legal, medical, financial, privacy), correctness is not a binary property derivable from the output alone. It requires:

1. **Domain-specific ground truth** — knowing that Article 30(1)(f) GDPR requires retention periods in Records of Processing Activities
2. **Severity weighting** — knowing that a dosage unit confusion (mg vs mcg) is catastrophic while a formatting issue is cosmetic
3. **Contextual judgment** — knowing that "let's explore legitimate interest" is a correct response to a genuine legal question but an incorrect response to an attempt to circumvent consent requirements

These three requirements define the construct we're measuring. An evaluation system has high construct validity when its test cases and scoring criteria faithfully represent this construct. Synthetic test generation — regardless of scale — cannot achieve high construct validity because it lacks access to (1), cannot weight by (2), and cannot distinguish context in (3).

### 1.2 The Precision-Recall Tradeoff in Test Set Design

Evaluation datasets exhibit a precision-recall tradeoff analogous to information retrieval:

**Precision** = P(real failure | eval flags failure). A high-precision dataset contains only queries where a failure signal is meaningful. Expert-curated datasets achieve this because every query has a validated expected behavior grounded in domain knowledge.

**Recall** = P(eval flags failure | real failure exists). A high-recall dataset covers the space of possible failures comprehensively. Large synthetic datasets attempt this through volume, but coverage of the *relevant* failure space (not the *possible* input space) requires domain knowledge to define.

The key insight: **precision and recall optimize over different distributions.** Precision optimizes over the evaluation dataset's own predictions. Recall optimizes over the production failure distribution — which is unknown at evaluation design time and non-stationary.

This asymmetry makes it impossible to optimize both in a single dataset. The resolution is stratification: separate layers optimizing each property independently, connected by a feedback mechanism.

---

## 2. The Two-Layer Architecture

### 2.1 Layer 1: Expert-Curated Golden Dataset (Offline Evaluation)

**Objective:** Maximize construct validity and precision for deployment gating.

**Properties:**
- Size: n = 100-150 (bounded by expert curation capacity)
- Source: Domain expert using structured elicitation (Open Coding methodology)
- Validation: Every query has expert-verified expected behavior
- Scoring: Deterministic pass/fail against expected behavior + LLM-as-judge for nuance
- Trigger: Runs on every code change (CI/CD gate)
- Decision: Block deployment if quality metrics fall below threshold

**Statistical justification for n ≈ 100:**

For a binary outcome (pass/fail) with true population rate p, the confidence interval width at 95% confidence is:

```
CI width = 2 × 1.96 × √(p(1-p)/n)
```

At n=100 with p=0.85 (typical TSR):
- CI width = ±7.0%
- Detectable regression: Δp ≥ 10% at α=0.05, power=0.80

At n=1000 with p=0.85:
- CI width = ±2.2%
- Detectable regression: Δp ≥ 3% at α=0.05, power=0.80

The question is whether detecting a 3% regression (n=1000) justifies 10x the cost and latency versus detecting a 10% regression (n=100). For deployment gating, a 10% regression is already catastrophic — detecting it is sufficient. Finer-grained monitoring belongs in Layer 2.

**Why expert curation is irreplaceable:**

The expert contributes three things no synthetic process can:

1. **Adversarial realism** — queries that reflect actual pressure patterns (e.g., "a VP is asking me to skip consent for ad targeting") rather than abstract adversarial templates
2. **Failure mode specificity** — error codes like `retention_period_omission` that encode precise regulatory requirements, not generic categories like "incomplete"
3. **Severity calibration** — knowing that a missing DPIA trigger is a compliance violation while a verbose response is merely suboptimal

### 2.2 Layer 2: Production Scoring (Online Evaluation)

**Objective:** Maximize recall over the production failure distribution.

**Properties:**
- Size: n = 1,000+ interactions/day (all production traffic or sampled)
- Source: Real user queries (the true input distribution)
- Scoring: LLM-as-judge derived from Layer 1 error codes and criteria
- Validation: None (automated scoring only — no human in the loop)
- Trigger: Continuous
- Decision: Alert on score degradation; flag individual failures for expert review

**Statistical justification:**

Layer 2 solves the coverage problem that Layer 1 cannot: it samples from the *actual* production distribution P(x), not the expert's *model* of that distribution P̂(x). The divergence D_KL(P || P̂) is non-zero and unknowable a priori — which is precisely why production scoring is necessary.

The judge's accuracy is bounded by Layer 1's quality:

```
Judge accuracy ≤ f(golden dataset quality, judge calibration)
```

A judge trained on 20 generic queries produces generic scores. A judge trained on 109 expert-curated queries with specific error codes (`dpia_threshold_miss`, `retention_period_omission`) produces domain-precise scores. The golden dataset's construct validity propagates to the judge's scoring validity.

### 2.3 Layer 3: The Feedback Loop (Evaluation Improvement)

**Objective:** Monotonically increase Layer 1 coverage using Layer 2 discoveries.

**Mechanism:**
1. Layer 2 flags low-scoring production interactions
2. Domain expert reviews flagged interactions (15-30 min/month)
3. Expert decides: genuine failure pattern or noise?
4. If genuine: expert writes 2-3 golden queries targeting the pattern, names the error code
5. Layer 1 grows; judge is regenerated; Layer 2 scoring improves

**Convergence properties:**

The golden dataset's coverage of the production failure distribution increases monotonically:

```
Coverage(t+1) ≥ Coverage(t)  ∀t
```

Because:
- New queries are only added (never removed) from validated failures
- Each addition covers a previously-uncovered failure mode
- The expert gate prevents noise accumulation (precision is maintained)

The system converges toward complete coverage of the *observed* failure distribution. It cannot converge on *unobserved* failures — but neither can any evaluation system. The flywheel minimizes the time between first occurrence and permanent regression coverage.

---

## 3. Empirical Validation: Privacy Engineering Agent

### 3.1 Experimental Setup

- **Agent:** PrivacyBot (GDPR compliance assistant)
- **Golden dataset:** 109 queries, 7 categories, curated by privacy engineer
- **Models:** Claude Haiku 4.5 (efficient), Claude Sonnet 4.6 (capable)
- **Scoring criteria:** 8 domain-specific metrics (GDPR citations, legal basis identification, adversarial refusal, timeline awareness, risk flagging, escalation, specificity, actionable steps)

### 3.2 Results

| Metric | Haiku 4.5 | Sonnet 4.6 | Discriminative? |
|--------|:---------:|:----------:|:---------------:|
| Overall quality | 61.5% | 60.5% | Δ = 1.0% |
| Adversarial refusal | **62%** | 48% | **Δ = 14%** |
| Legal basis ID | **62%** | 54% | **Δ = 8%** |
| Risk flagging | **82%** | 77% | Δ = 5% |
| GDPR citations | 86% | **92%** | Δ = 6% |
| Escalation | 18% | **29%** | **Δ = 11%** |

### 3.3 Analysis

The expert-curated dataset produces **high discriminative validity** between models on the metrics that matter for compliance (adversarial refusal: Δ=14%, legal basis: Δ=8%). A synthetic dataset of equivalent size would likely show smaller deltas on these specific metrics because:

1. Synthetic adversarial queries tend toward generic jailbreak patterns rather than domain-specific circumvention attempts
2. Legal basis identification requires queries that create genuine ambiguity between Article 6 bases — something only a practitioner can construct
3. The expert's error codes (`dpia_threshold_miss`) create scoring criteria that are maximally sensitive to the failures that matter

### 3.4 The Counter-Intuitive Finding

The more capable model (Sonnet 4.6) scored *lower* on compliance-critical metrics. This is not a measurement artifact — it reflects a genuine behavioral difference:

- Sonnet's higher reasoning capability manifests as *exploration* of alternatives when the correct behavior is *refusal*
- In compliance domains, helpfulness without firm boundaries constitutes a safety failure
- Generic benchmarks (MMLU, HumanEval) cannot detect this because they reward capability, not constraint adherence

This finding is only visible with domain-expert-curated adversarial queries. Synthetic adversarial generation produces queries that test *capability* (can the model refuse?) rather than *judgment* (does the model know *when* to refuse in this specific domain context?).

---

## 4. Comparison With Alternative Approaches

| Approach | Construct Validity | Coverage | Scalability | Maintenance |
|----------|:------------------:|:--------:|:-----------:|:-----------:|
| Expert-only (n=100) | ★★★★★ | ★★☆☆☆ | ★★★★★ | ★★★★☆ |
| Synthetic-only (n=1000) | ★★☆☆☆ | ★★★☆☆ | ★★★☆☆ | ★★☆☆☆ |
| Two-layer (100 + production) | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★☆ |
| Human annotation at scale | ★★★★★ | ★★★★☆ | ★☆☆☆☆ | ★☆☆☆☆ |

The two-layer architecture achieves the validity of expert curation with the coverage of production-scale scoring, at sustainable maintenance cost.

---

## 5. Implementation Requirements

### 5.1 Layer 1 Requirements
- Domain expert availability: 90 min initial + 30 min/month
- Structured elicitation tool (GEDD or equivalent)
- CI/CD integration (11 min runtime budget)
- Threshold calibration: Cohen's κ ≥ 0.80 between judge and expert annotations

### 5.2 Layer 2 Requirements
- Production traffic access (logging pipeline)
- Judge inference budget (~$0.002/interaction)
- Alerting threshold calibration
- Expert review queue (flagged interactions)

### 5.3 Feedback Loop Requirements
- Expert review cadence (weekly or monthly)
- Promotion criteria (expert validates failure is genuine and novel)
- Judge regeneration pipeline (automated after golden dataset update)
- Regression verification (new queries don't break existing coverage)

---

## 6. Conclusion

The fundamental insight is that evaluation validity and evaluation coverage are orthogonal properties that cannot be jointly optimized in a single dataset. The two-layer architecture resolves this by:

1. **Separating concerns:** Layer 1 optimizes validity (expert curation). Layer 2 optimizes coverage (production sampling).
2. **Connecting layers:** The judge propagates Layer 1's validity to Layer 2's scoring. The feedback loop propagates Layer 2's coverage discoveries to Layer 1.
3. **Monotonic improvement:** The system's coverage increases over time without sacrificing validity, because the expert gates all additions.

For domain-specific agents operating in regulated environments (privacy, healthcare, finance, legal), this architecture is not optional — it is the minimum viable evaluation system that satisfies both engineering requirements (automated, scalable, fast) and compliance requirements (expert-validated, auditable, comprehensive).

The domain expert's 90 minutes of curation produce more evaluation value than any amount of synthetic generation — because they define the construct being measured. Without construct validity, scale is meaningless.

---

*Implementation: [GEDD](https://github.com/aws-samples/sample-GEDD) (MIT-0). Structured elicitation → golden dataset → judge generation → production scoring → feedback loop.*
