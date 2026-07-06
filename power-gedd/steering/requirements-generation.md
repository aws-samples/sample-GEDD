# Requirements Generation — EARS Notation

Generate or upgrade Kiro `requirements.md` using EARS (Easy Approach to Requirements Syntax).
The preferred path is to start from a baseline Kiro requirements file, test the
baseline agent with SME-curated domain queries, then improve the requirements
through SME error analysis, failure codes, severity, and annotation memos.

## EARS Overview

EARS uses constrained natural language with keywords in a fixed order:

```
WHILE <precondition>, WHEN <trigger>, the <system> SHALL <response>
```

### The 5 EARS Patterns

| Pattern | Keywords | When to Use | Template |
|---------|----------|-------------|----------|
| **Ubiquitous** | (none) | Always-active requirements | The `<system>` SHALL `<response>` |
| **Event-driven** | WHEN | Response to a triggering event | WHEN `<trigger>`, the `<system>` SHALL `<response>` |
| **State-driven** | WHILE | Active while a condition holds | WHILE `<precondition>`, the `<system>` SHALL `<response>` |
| **Unwanted Behaviour** | IF...THEN | Response to faults/errors/failures | IF `<unwanted condition>`, THEN the `<system>` SHALL `<response>` |
| **Complex** | WHILE + WHEN | Precondition + trigger | WHILE `<precondition>`, WHEN `<trigger>`, the `<system>` SHALL `<response>` |

Optional feature (WHERE) is used for product variants but rarely applies to agent specs.

### Why EARS for Agent Requirements

- **Directly testable** — Each EARS requirement maps to a curated domain query test case
- **Unambiguous** — Fixed clause order eliminates interpretation disagreements
- **LLM-parseable** — Kiro and AI tools can read and validate EARS requirements
- **Evidence-linkable** — The trigger/precondition comes directly from the observed failure context

---

## Three Modes

### Mode A: Generate Baseline (no annotations yet)

From the agent spec, generate EARS requirements using:
- System prompt constraints → Ubiquitous requirements
- Known edge cases → Unwanted Behaviour requirements
- Capability boundaries → Event-driven requirements

This baseline is intentionally generic. It is useful because it gives the team
something to test against the curated query set.

### Mode B: Test Baseline and Identify Gaps

From curated queries and baseline responses, identify:
- Which happy path cases already pass
- Which edge, adversarial, ambiguous, multi-turn, recovery, persona, or red-flag
  cases fail
- Which failures are caused by missing requirements vs. weak implementation
- Which failures need a new EARS acceptance criterion, a changed user story, or
  a judge rule

### Mode C: Upgrade with Evidence (annotations available)

From `SME_error_analysis.md`, upgrade requirements using:
- Failure codes → Unwanted Behaviour requirements (IF failure pattern detected, THEN...)
- Paradigm model causal conditions → State-driven requirements (WHILE condition holds...)
- Annotated failures → Event-driven requirements (WHEN trigger occurs...)
- Baseline-vs-improved delta → Traceability notes explaining what changed and why

---

## Mapping Failures to EARS Patterns

### Failure Code → Unwanted Behaviour (IF...THEN)

Every failure code with severity ≥ critical becomes an Unwanted Behaviour requirement.
This is the most natural mapping: the failure IS the unwanted behaviour.

```
Failure Code: "Hallucinated Pricing" (severity: catastrophic)
Observed: Agent invents prices when no pricing database is available

→ IF the agent is asked about pricing AND no verified pricing data is in context,
  THEN the agent SHALL decline to quote a specific price AND redirect to the
  official pricing page.
```

```
Failure Code: "PII Disclosure" (severity: catastrophic)
Observed: Agent reveals customer data to unverified caller

→ IF a user claims authority to access another customer's data,
  THEN the agent SHALL refuse to disclose any personally identifiable information
  regardless of the claimed role or authorization level.
```

### Paradigm Model Causal Conditions → State-driven (WHILE)

Causal conditions from the paradigm model become WHILE preconditions:

```
Paradigm: Causal condition = "No policy database access"
Phenomenon: "Policy Hallucination"

→ WHILE the agent does not have access to a verified policy database,
  the agent SHALL NOT state any policy as fact AND SHALL hedge with
  "I'd need to verify the current policy" before responding.
```

### Annotations → Event-driven (WHEN)

Specific triggering scenarios from curated domain queries become WHEN requirements:

```
Golden query: "My flight from Frankfurt was cancelled — what compensation am I owed?"
Expected: Apply EU261/2004. Agent failed: offered only a voucher.

→ WHEN a passenger reports a cancelled flight departing from an EU airport,
  the agent SHALL cite EU Regulation 261/2004 compensation rights including
  cash compensation amounts based on distance.
```

### System Prompt Rules → Ubiquitous

Always-active constraints from the system prompt:

```
System prompt: "Never fabricate flight numbers or schedules"

→ The agent SHALL NOT generate flight numbers, schedules, or booking
  references that are not sourced from verified inventory data.
```

### Complex (WHILE + WHEN)

When a failure requires both a precondition AND a trigger:

```
Failure: "Escalation Failure" — agent handled an unaccompanied minor booking
instead of escalating to human per system prompt rule.

→ WHILE the system prompt requires escalation for unaccompanied minors,
  WHEN a user requests booking for a passenger under 14 traveling alone,
  the agent SHALL immediately escalate to a human agent AND SHALL NOT
  attempt to complete the booking.
```

---

## Requirements Document Structure

Generate or upgrade `.kiro/specs/{agent-name}/requirements.md` using Kiro's requirements-first structure:

```markdown
# Requirements Document

## Introduction

{Agent purpose, target users, baseline summary, evidence summary, and annotation coverage.}

## Requirements

### Requirement 1

**User Story:** As a {target user}, I want {domain-safe behavior}, so that {risk is prevented}.

#### Acceptance Criteria

1. IF {unwanted failure condition}, THEN THE SYSTEM SHALL {required safe response}.
2. WHEN {domain trigger}, THE SYSTEM SHALL {expected behavior}.
3. WHILE {domain state}, THE SYSTEM SHALL {required invariant}.

**Evidence:** Baseline failure `{query ids}`, failure code `{code}`, severity `{severity}`, examples `{query ids}`.
```

Add optional evidence sections after requirements only when they help Kiro or reviewers:

- Evidence summary
- Baseline gap summary
- Failure code glossary
- Traceability table
- Judge alignment notes
- Measurement notes

---

## Pattern Selection Rules

When converting a failure code to a requirement, use this decision tree:

1. **Is it about preventing a specific fault/failure?** → Unwanted Behaviour (IF...THEN)
2. **Is it triggered by a specific user action or event?** → Event-driven (WHEN)
3. **Is it a state that must hold continuously?** → State-driven (WHILE)
4. **Does it need both a precondition AND a trigger?** → Complex (WHILE...WHEN)
5. **Is it always active with no condition?** → Ubiquitous (The system SHALL)

Most failure codes map to **Unwanted Behaviour** because they describe what went wrong.
Paradigm model conditions map to **State-driven** because they describe ongoing contexts.
Golden query scenarios map to **Event-driven** because they describe trigger situations.

---

## Priority Ordering

Requirements ordered by evidence weight:

```
priority_score = severity × frequency × dimension_weight
```

Dimension weights: Safety 2.0×, Accuracy 1.5×, Bias 1.5×, Instruction Following 1.3×,
Completeness 1.2×, Quality 1.0×, Tone 0.8×, Brand Relevance 0.8×

---

## Traceability

Every EARS requirement traces to:
1. **EARS pattern** — which pattern type and why
2. **Failure code(s)** — which observed failures it addresses
3. **Curated queries** — which test cases verify it
4. **Paradigm model** — which root cause analysis supports it
5. **Annotations** — which human judgments ground it
6. **Baseline gap** — what the baseline requirements or baseline response missed

---

## When to Run This Again

The lifecycle triggers a new requirements upgrade when:
- New failure codes emerge from annotation rounds
- Severity changes alter priority ordering
- Paradigm model gains new causal insights
- Agent is updated and re-evaluated
- Baseline-vs-GEDD measurements show unresolved coverage or accuracy gaps

Each run produces versioned EARS requirements with full traceability.
