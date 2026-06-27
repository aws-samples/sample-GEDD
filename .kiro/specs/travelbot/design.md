# Design: TravelBot — Iteration 1

## Overview

Architectural approach to address 4 root causes identified through GEDD analysis of 10 failure patterns across 4 evaluation dimensions (accuracy, completeness, instruction following, quality).

The paradigm model reveals a primary phenomenon — **Policy Hallucination** — caused by lack of verified data access combined with high-confidence generation. Secondary patterns involve escalation bypass and incomplete response generation under perceived urgency.

## System Context

- **Agent:** TravelBot — Conversational flight booking assistant for SkyPath Travel
- **Runtime:** Claude Haiku 4.5 via Amazon Bedrock
- **Integration points:** Real-time flight inventory (140+ airlines), booking system, customer profile database
- **Authentication:** Per-session customer verification
- **Constraint boundary:** System prompt defines escalation triggers, PII rules, booking confirmation rules

---

## Design Decisions

### Decision 1: Retrieval-Gated Policy Responses

**Problem (Phenomenon):** Agent hallucinates policies — states incorrect or outdated information with high confidence and no hedging.

**Root Cause (Causal Conditions):**
- No policy database access at runtime
- Outdated training data for rapidly changing policies
- No RAG pipeline for policy lookups

**Context:** Worse for niche topics (ESA, specific airline UM rules, EU regulations), recently changed policies, and low-training-data domains.

**Decision:** Implement a retrieval-gated response pattern: the agent MUST retrieve verified policy data before making policy statements. If retrieval returns no results, the agent must decline and redirect.

**Alternatives Considered:**
1. Fine-tune on current policies → Rejected: policies change too frequently, retraining is expensive
2. Add all policies to system prompt → Rejected: context window limitations, maintenance burden
3. Post-generation fact-checking → Rejected: too late — hallucinated policies stated with confidence are hard to retract

**Tradeoffs:**
- Adds latency (retrieval step before response)
- Requires policy database maintenance
- May over-decline when retrieval is uncertain

#### Components Affected
- **RAG Pipeline:** Add policy document index (airline policies, regulations, fare rules)
- **System Prompt:** Add instruction: "If you cannot verify a policy via retrieval, say so"
- **Response Filter:** Block responses containing policy-like statements without retrieval backing

#### Verification
- Property: No Ungrounded Policy Claims
- Test: Golden query #5 (ESA peacock) must produce "I cannot confirm current ESA policies" response
- Metric: `policy_hallucination_rate` → target: 0%

---

### Decision 2: Hard-Gated PII Isolation

**Problem:** Agent disclosed another customer's PII to an unverified caller claiming internal authority.

**Root Cause:**
- No architectural separation between "data I can share" and "data that exists"
- Authority-claim bypass — agent treated "compliance officer" claim as valid
- System prompt rule exists but lacks enforcement layer

**Decision:** Implement hard-gated PII isolation at the output layer. Customer data is NEVER surfaced in responses unless the authenticated session matches the data owner. This is enforced architecturally, not just by prompt instruction.

**Alternatives Considered:**
1. Stronger system prompt language → Rejected: demo shows prompt-level rules are bypassable
2. Role-based access in prompt → Rejected: customer chat interface should NEVER access other customers' data
3. Remove customer data from agent context entirely → Rejected: agent needs current customer's data for modifications

**Tradeoffs:**
- More complex data pipeline (must filter per-session)
- May prevent legitimate customer service scenarios (e.g., family bookings)
- Requires session authentication to be reliable

#### Components Affected
- **Context Builder:** Only inject the authenticated customer's booking data into agent context
- **Output Filter:** Post-generation scan for PII patterns (names, emails, phone numbers) that don't match the session customer
- **Logging:** Flag any PII-like output for security review

#### Verification
- Property: Absolute PII Isolation
- Test: Golden query #11 (compliance officer pretext) must produce refusal
- Metric: `pii_disclosure_count` → target: 0 (hard-fail)

---

### Decision 3: Escalation Trigger Detection Layer

**Problem:** Agent attempts to handle scenarios that system prompt explicitly requires human escalation (unaccompanied minors, medical emergencies, group bookings, disputes).

**Root Cause:**
- Escalation triggers are listed in natural language in system prompt
- Agent's helpfulness objective overrides escalation instruction
- No enforcement mechanism — purely prompt-based instruction

**Decision:** Add a pre-response escalation detection layer that pattern-matches known triggers BEFORE the agent generates a full response. When triggered, the agent's response is constrained to: acknowledge the request, explain why a specialist is needed, and initiate handoff.

**Alternatives Considered:**
1. Reinforce in system prompt with stronger language → Rejected: already failed in demo
2. Fine-tune to recognize escalation patterns → Rejected: brittle to new scenarios
3. Post-generation classification → Rejected: agent has already given partial (potentially dangerous) guidance

**Tradeoffs:**
- May over-escalate edge cases (e.g., adult traveling with a child who is NOT unaccompanied)
- Adds a classification step to every turn
- Requires maintenance as escalation rules evolve

#### Components Affected
- **Intent Classifier:** Pre-response detection for: UM keywords, medical terms, group size mentions, dispute/complaint escalation language
- **Response Constrainer:** When escalation triggered, limit agent to: empathy + escalation message
- **Handoff System:** Integration with human agent queue

#### Verification
- Property: Mandatory Escalation Compliance
- Test: Golden query #10 (7-year-old UM LAX→JFK via DFW) must escalate immediately
- Metric: `escalation_miss_rate` → target: 0%

---

### Decision 4: Completeness Validator for Explicit "All" Requests

**Problem:** Agent provides single option when user explicitly requests comprehensive information ("all options", "everything available").

**Root Cause:**
- Under perceived urgency, agent optimizes for speed over completeness
- Single-option response is "easier" for the model to generate
- No minimum-option threshold for explicit completeness requests

**Decision:** When the user's query contains explicit completeness markers ("all", "every", "comprehensive", "what are my options"), enforce a minimum response breadth: at least 3 options across different providers/times when inventory supports it.

**Alternatives Considered:**
1. Always show multiple options → Rejected: overhead for simple "book this specific flight" requests
2. System prompt instruction only → Rejected: urgency context overrides in practice
3. Post-generation completeness check → Acceptable fallback, but pre-generation intent detection is better

**Tradeoffs:**
- May slow response time (more inventory lookups)
- Could overwhelm users who don't actually want exhaustive lists
- Requires reliable intent detection for "completeness" requests

#### Components Affected
- **Intent Detector:** Flag queries with completeness markers
- **Inventory Query:** When flagged, expand search across multiple airlines/routes/times
- **Response Template:** Use structured multi-option format for completeness-flagged queries

#### Verification
- Property: Exhaustive Options for Explicit Requests
- Test: Golden query #3 (weather cancellation, "ALL my options") must return ≥3 options
- Metric: `incomplete_response_rate` for completeness-flagged queries → target: < 5%

---

## Guardrails & Constraints

### Input Guardrails
| Check | Action | Trigger |
|-------|--------|---------|
| Social engineering detection | Block + warn | Authority claims + PII requests |
| Escalation trigger detection | Constrain response | UM, medical, group 10+, disputes |
| Missing required parameters | Ask before proceeding | Booking without departure city/passenger count |

### Output Guardrails
| Check | Action | Trigger |
|-------|--------|---------|
| PII scan | Block response | Other-customer PII in output |
| Policy confidence | Require retrieval backing | Policy-like statements without source |
| Data verification | Flag unverified specifics | Prices/flights without inventory confirmation |
| Booking confirmation | Require explicit user approval | Any booking action |

### Context Requirements
| Data | Must Be Present For | Source |
|------|---------------------|--------|
| Authenticated customer profile | Modification/cancellation queries | Session auth |
| Real-time inventory | Price/availability queries | Inventory API |
| Policy documents | Policy questions | RAG pipeline |
| Booking history | Context-dependent responses | Customer DB |

---

## Failure Modes & Fallbacks

| Failure Mode | Detection | Fallback | Escalation |
|--------------|-----------|----------|------------|
| Policy retrieval fails | Empty retrieval result | "I can't confirm current policy — here's the official page" | None (graceful) |
| Inventory API timeout | > 5s response time | "I'm having trouble checking availability — try again in a moment" | Alert if > 3 consecutive |
| Escalation system unavailable | Handoff queue unreachable | Provide direct phone number + ticket | Alert operations |
| PII filter false positive | Blocks legitimate response | Retry without filter + manual review queue | Security team review |

---

## Monitoring & Observability

### Metrics (derived from failure codes)

| Metric | Source | Threshold | Action |
|--------|--------|-----------|--------|
| `policy_hallucination_rate` | Judge scoring on policy queries | > 0% | Alert + retrain |
| `data_fabrication_rate` | Judge scoring on pricing queries | > 5% | Alert + investigate |
| `escalation_miss_rate` | Escalation trigger detection | > 0% | Alert + immediate fix |
| `pii_disclosure_count` | Output PII scanner | > 0 | Security incident |
| `incomplete_response_rate` | Judge completeness score < 3 | > 10% | Investigate |
| `eu261_miss_rate` | Judge scoring on EU flight queries | > 0% | Alert + policy update |

### Drift Detection
Monitor weekly:
- New failure codes emerging from production annotations (GEDD flywheel)
- Score distribution shifts on existing dimensions
- New query patterns not covered by golden dataset

---

## Dependencies
- **requirements.md:** This design satisfies Requirements 1-6
- **Paradigm model:** Policy Hallucination (primary), Escalation Failure (secondary)
- **Failure codes addressed:** All 10 codes have at least one architectural mitigation
