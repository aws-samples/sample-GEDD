# Tasks: TravelBot — Iteration 1

## Task Dependency Graph

```
T1 (PII Output Filter) ──────────────────┐
T2 (Escalation Detection Layer) ─────────┤
T3 (Policy RAG Pipeline) ────────────────┼──→ T7 (Integration Test Suite)
T4 (Inventory Verification Gate) ────────┤
T5 (EU261 Policy Documents) ─→ T3       │
T6 (Completeness Validator) ─────────────┘
T7 ──→ T8 (Judge Calibration)
T8 ──→ T9 (CI Gate Setup)
```

---

## Tasks

### Task 1: Implement PII Output Filter

- **Priority:** P0 (score: 80)
- **Status:** not_started
- **Addresses:** PII Disclosure (severity: catastrophic, frequency: 1)
- **Implements:** Design Decision 2 — Hard-Gated PII Isolation
- **Satisfies:** Requirement 1 — No PII Disclosure Under Any Pretext

#### Description
Add a post-generation output filter that scans agent responses for PII patterns (names, email addresses, phone numbers, booking codes) that do not belong to the authenticated session customer. If detected, block the response and substitute a refusal message. This addresses the root cause architecturally — the agent's prompt-level PII rule was bypassed by social engineering with authority framing.

#### Sub-tasks
- [ ] 1.1: Define PII pattern regex set (names, emails, phones, booking codes)
- [ ] 1.2: Build output scanner that checks response against session customer identity
- [ ] 1.3: Implement response blocking with standard refusal substitution
- [ ] 1.4: Add logging for blocked PII attempts (for security review)
- [ ] 1.5: Write tests against golden query #11

#### Acceptance Criteria
- [ ] Golden query #11 (compliance officer pretext) returns refusal, no PII in output
- [ ] Authenticated customer's own data still accessible in normal flows
- [ ] `pii_disclosure_count` metric = 0 across full golden dataset
- [ ] Security log captures blocked attempt details

#### Dependencies
- Depends on: None (highest priority, no dependencies)
- Blocks: Task 7 (Integration Test Suite)

---

### Task 2: Implement Escalation Trigger Detection Layer

- **Priority:** P0 (score: 52)
- **Status:** not_started
- **Addresses:** Escalation Failure (severity: critical, frequency: 2), Unaccompanied Minor Escalation Failure (severity: critical)
- **Implements:** Design Decision 3 — Escalation Trigger Detection Layer
- **Satisfies:** Requirement 3 — Mandatory Escalation for System-Prompt-Defined Triggers

#### Description
Add a pre-response classification step that detects escalation triggers BEFORE the agent generates a full response. When triggered, constrain the agent to: acknowledge the request empathetically, explain why a specialist handles this, and initiate handoff. This addresses the root cause — the agent's helpfulness objective overrides prompt instructions without an enforcement layer.

#### Sub-tasks
- [ ] 2.1: Define escalation trigger patterns (UM keywords, medical terms, group size, dispute language)
- [ ] 2.2: Build pre-response intent classifier
- [ ] 2.3: Implement response constrainer (empathy + escalation message template)
- [ ] 2.4: Integrate with human agent handoff system
- [ ] 2.5: Write tests against golden query #10

#### Acceptance Criteria
- [ ] Golden query #10 (7-year-old UM LAX→JFK via DFW) triggers immediate escalation
- [ ] Agent does not provide partial UM booking guidance
- [ ] All system-prompt escalation triggers detected: UM, medical, group 10+, disputes
- [ ] `escalation_miss_rate` = 0% across golden dataset

#### Dependencies
- Depends on: None
- Blocks: Task 7 (Integration Test Suite)

---

### Task 3: Build Policy RAG Pipeline

- **Priority:** P0 (score: 60)
- **Status:** not_started
- **Addresses:** Policy Hallucination (severity: catastrophic, frequency: 2)
- **Implements:** Design Decision 1 — Retrieval-Gated Policy Responses
- **Satisfies:** Requirement 2 — No Policy Hallucination

#### Description
Implement a retrieval-augmented generation pipeline for policy information. The agent must retrieve verified policy documents before making policy statements. If retrieval returns no results, the agent must decline and redirect to the authoritative source. This addresses the primary paradigm model root cause — lack of policy database access combined with confident generation.

#### Sub-tasks
- [ ] 3.1: Design policy document schema (airline, topic, effective date, source URL)
- [ ] 3.2: Build policy index with initial document set (ESA, UM, EU261, DOT rules)
- [ ] 3.3: Implement retrieval step in agent pipeline (query → retrieve → ground response)
- [ ] 3.4: Add "no retrieval result" fallback (decline + redirect pattern)
- [ ] 3.5: Add system prompt instruction for retrieval-gated responses
- [ ] 3.6: Write tests against golden query #5 (ESA) and #9 (EU261)

#### Acceptance Criteria
- [ ] Golden query #5 (ESA peacock) → agent declines to confirm policy, redirects to airline
- [ ] Golden query #9 (Frankfurt cancellation) → agent retrieves EU261 and mentions €600 right
- [ ] `policy_hallucination_rate` = 0% across golden dataset
- [ ] Responses include source attribution when policy data is retrieved

#### Dependencies
- Depends on: Task 5 (EU261 Policy Documents — content needed for index)
- Blocks: Task 7 (Integration Test Suite)

---

### Task 4: Add Inventory Verification Gate

- **Priority:** P1 (score: 36)
- **Status:** not_started
- **Addresses:** Data Fabrication (severity: critical, frequency: 3)
- **Implements:** Design Decision 1 — Retrieval-Gated Policy Responses (extended to data)
- **Satisfies:** Requirement 4 — No Data Fabrication

#### Description
Ensure the agent only quotes prices, flight numbers, and availability that are verified against real-time inventory. When required parameters are missing (departure city, dates), the agent must ask rather than assume. This addresses the data fabrication pattern where plausible-sounding numbers are generated without inventory backing.

#### Sub-tasks
- [ ] 4.1: Add parameter completeness check before inventory query (require: origin, destination, date)
- [ ] 4.2: Implement response validator — flag specific prices/flights without API backing
- [ ] 4.3: Add "missing parameters" conversation flow (ask before proceeding)
- [ ] 4.4: Write tests against golden queries #2 and #6

#### Acceptance Criteria
- [ ] Golden query #2 (flexible warm destination) → agent asks for departure city first
- [ ] Golden query #6 (book 3:45 United Denver) → agent asks for departure city and passenger count
- [ ] No response contains prices without inventory API verification
- [ ] `data_fabrication_rate` < 5% across golden dataset

#### Dependencies
- Depends on: None
- Blocks: Task 7 (Integration Test Suite)

---

### Task 5: Add EU261 Policy Documents to RAG Index

- **Priority:** P1 (score: 30)
- **Status:** not_started
- **Addresses:** EU Passenger Rights Miss (severity: catastrophic, frequency: 1)
- **Implements:** Design Decision 1 — supports Policy RAG Pipeline
- **Satisfies:** Requirement 5 — EU Regulation 261/2004 Compliance

#### Description
Create and index EU Regulation 261/2004 policy documents covering: compensation amounts by distance (€250/€400/€600), applicability rules (EU-departing flights regardless of airline), care rights (meals, hotel, transport), extraordinary circumstances exceptions, and the cash-vs-voucher distinction.

#### Sub-tasks
- [ ] 5.1: Write EU261 policy document covering all compensation tiers
- [ ] 5.2: Write applicability rules (EU departure = EU rules, regardless of airline nationality)
- [ ] 5.3: Write care rights document (meals, hotel, transport during delay)
- [ ] 5.4: Index documents in policy RAG pipeline
- [ ] 5.5: Validate retrieval for Frankfurt→Chicago scenario

#### Acceptance Criteria
- [ ] Policy retrieval for "Frankfurt flight cancelled" returns EU261 compensation data
- [ ] Document includes €600 for flights > 3,500 km
- [ ] Document distinguishes cash compensation right from voucher offers
- [ ] Golden query #9 passes after Task 3 + Task 5 are complete

#### Dependencies
- Depends on: None (content creation, no system dependency)
- Blocks: Task 3 (Policy RAG Pipeline needs these documents)

---

### Task 6: Implement Completeness Validator

- **Priority:** P1 (score: 24)
- **Status:** not_started
- **Addresses:** Incomplete Response (severity: critical, frequency: 2)
- **Implements:** Design Decision 4 — Completeness Validator for Explicit "All" Requests
- **Satisfies:** Requirement 6 — Complete Responses When User Requests "All Options"

#### Description
When the user's query contains explicit completeness markers ("all", "every", "what are my options"), enforce a minimum response breadth of 3 options across different providers/times. This addresses the pattern where urgency causes the agent to optimize for speed over completeness.

#### Sub-tasks
- [ ] 6.1: Build intent detector for completeness markers in queries
- [ ] 6.2: When flagged, expand inventory search across multiple airlines/routes
- [ ] 6.3: Implement minimum 3-option response template
- [ ] 6.4: Write test against golden query #3

#### Acceptance Criteria
- [ ] Golden query #3 (weather cancellation, "ALL my options") returns ≥3 options
- [ ] Options span multiple airlines when available
- [ ] `incomplete_response_rate` for completeness-flagged queries < 5%

#### Dependencies
- Depends on: None
- Blocks: Task 7 (Integration Test Suite)

---

### Task 7: Golden Query Integration Test Suite

- **Priority:** P1 (score: 20)
- **Status:** not_started
- **Addresses:** All failure codes — regression prevention
- **Implements:** All design decisions — verification layer
- **Satisfies:** NFR-1 (Coverage Confidence)

#### Description
Build an automated test suite that runs the full golden dataset against TravelBot and validates verdicts using the GEDD judge prompt. This serves as the regression gate for all previous fixes.

#### Sub-tasks
- [ ] 7.1: Set up test harness (run golden queries → collect responses)
- [ ] 7.2: Integrate GEDD judge prompt for automated scoring
- [ ] 7.3: Define pass/fail thresholds per criterion
- [ ] 7.4: Add hard-fail detection (PII, unconfirmed booking, fabricated data)
- [ ] 7.5: Generate test report with per-query verdicts

#### Acceptance Criteria
- [ ] All 14 golden queries run successfully
- [ ] Hard-fail criteria trigger correctly (PII, fabrication, unconfirmed booking)
- [ ] Overall pass rate ≥ 75% (up from current 25-50%)
- [ ] Per-dimension scores reported

#### Dependencies
- Depends on: Tasks 1, 2, 3, 4, 5, 6 (all fixes must be in place)
- Blocks: Task 8 (Judge Calibration)

---

### Task 8: Judge Calibration Against Human Annotations

- **Priority:** P2 (score: 15)
- **Status:** not_started
- **Addresses:** NFR-2 (Judge Agreement)
- **Implements:** Calibration from judge_builder/calibrate.py
- **Satisfies:** NFR-2 — Judge Agreement κ ≥ 0.80

#### Description
Run the GEDD judge prompt against all annotated responses and compare scores with human annotations. Calculate Cohen's weighted κ per dimension and overall. If κ < 0.80, identify disagreement patterns and refine the judge prompt.

#### Sub-tasks
- [ ] 8.1: Score all annotated responses with judge prompt
- [ ] 8.2: Calculate Cohen's weighted κ (overall + per dimension)
- [ ] 8.3: Identify disagreement patterns (which queries, which dimensions)
- [ ] 8.4: Refine judge prompt if κ < 0.80 (add examples, clarify criteria)
- [ ] 8.5: Re-run until κ ≥ 0.80

#### Acceptance Criteria
- [ ] Cohen's weighted κ ≥ 0.80 overall
- [ ] Per-dimension κ ≥ 0.70 for all 4 dimensions
- [ ] Disagreement patterns documented

#### Dependencies
- Depends on: Task 7 (need test results to calibrate against)
- Blocks: Task 9 (CI Gate Setup)

---

### Task 9: CI Gate Setup

- **Priority:** P2 (score: 12)
- **Status:** not_started
- **Addresses:** Automated regression prevention
- **Implements:** Production monitoring from design
- **Satisfies:** NFR-1, NFR-2

#### Description
Integrate the golden query test suite + calibrated judge into CI/CD pipeline. Every deploy must pass the golden dataset with the judge prompt before shipping.

#### Sub-tasks
- [ ] 9.1: Add golden query test to GitHub Actions CI workflow
- [ ] 9.2: Configure pass/fail thresholds (overall ≥ 3.5, no hard-fails)
- [ ] 9.3: Add judge scoring step after golden query run
- [ ] 9.4: Report results in PR comments
- [ ] 9.5: Block merge on failure

#### Acceptance Criteria
- [ ] CI runs golden queries on every PR
- [ ] Hard-fails block merge immediately
- [ ] Score regression (drop > 0.5 on any dimension) blocks merge
- [ ] Results visible in PR summary

#### Dependencies
- Depends on: Task 8 (need calibrated judge)
- Blocks: None (final task)

---

## Summary

| Tier | Count | Failure Codes Addressed |
|------|-------|------------------------|
| P0 | 3 | PII Disclosure, Escalation Failure, UM Escalation Failure, Policy Hallucination |
| P1 | 4 | Data Fabrication, EU Passenger Rights Miss, Incomplete Response, All (regression) |
| P2 | 2 | Judge calibration, CI automation |
| P3 | 0 | — |

**Total tasks:** 9
**Estimated coverage:** 100% of observed failure codes addressed
**Current pass rate:** 25-50% → **Target pass rate:** ≥75% after P0+P1 completion
