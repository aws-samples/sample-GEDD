# Requirements Generation from GEDD Annotations

Convert failure patterns, codebook, and paradigm models into structured requirements.

## Prerequisites
- Completed codebook with failure codes, definitions, and severity
- Paradigm models for major failures (severity ≥ 3)
- Saturation evidence confirming coverage
- Dimension mappings with weights

---

## Mapping Strategy

### From Failure Codes → User Stories

Each failure code with severity ≥ 3 becomes a requirement:

**Template:**
```
As a [target user from agent spec],
I want the agent to [desired behavior — opposite of failure],
so that [consequence avoidance from paradigm model].
```

**Example:**
```
Failure Code: "Hallucinated Pricing" (severity 5)
Paradigm consequence: "User makes purchase decisions on false information"

→ As a shopper,
  I want the agent to never invent pricing information,
  so that I don't make purchase decisions based on fabricated data.
```

### From Annotations → Acceptance Criteria

Each annotated golden query with verdict ≗ incorrect/partial becomes a test case:

**Template:**
```
GIVEN [the query context from golden prompt]
WHEN [the user asks / the agent receives]
THEN [the expected behavior — what the agent SHOULD do]
AND NOT [the observed failure — what it must NOT do]
```

**Example:**
```
GIVEN a user asking about product pricing without a pricing database connected
WHEN the user asks "How much does the Pro plan cost?"
THEN the agent responds with "I don't have current pricing information" and links to the pricing page
AND NOT the agent invents a price like "$49/month"
```

### From Paradigm Model → Correctness Properties

Each paradigm model's action strategies become formal properties:

**Template:**
```
PROPERTY: [name derived from phenomenon]
FOR ALL queries WHERE [causal conditions exist]
THE agent SHALL [action strategy]
AND SHALL NOT [phenomenon behavior]
VERIFIED BY [golden queries that test this]
```

**Example:**
```
PROPERTY: No Price Hallucination
FOR ALL queries WHERE user asks about pricing AND no pricing data is in context
THE agent SHALL decline to quote a price and redirect to official source
AND SHALL NOT generate any numerical price value
VERIFIED BY golden queries #12, #27, #34
```

---

## Requirements Document Structure

Generate `.kiro/specs/{agent-name}/requirements.md` with this structure:

```markdown
# Requirements: {Agent Name} — Iteration {N}

## Introduction
Brief description of what these requirements address.
Generated from GEDD session with {X} annotations, {Y} failure codes,
{Z} saturated categories.

## Glossary
| Term | Definition |
|------|------------|
| {failure code} | {definition from codebook} |
| ... | ... |

## Functional Requirements

### Requirement 1: {Derived from highest-severity failure code}

**User Story:** As a {user}, I want {behavior}, so that {benefit}

#### Acceptance Criteria
1. {From annotation — GIVEN/WHEN/THEN}
2. {From annotation — GIVEN/WHEN/THEN}
3. ...

#### Correctness Properties
- PROPERTY: {formal property from paradigm model}

#### Evidence
- Failure code: {code label} (severity {N}, frequency {N})
- Golden queries: #{id}, #{id}, #{id}
- Saturation: {status}

### Requirement 2: ...
(repeat for each failure code with severity ≥ 3)

## Non-Functional Requirements

### NFR-1: Coverage Confidence
The agent evaluation must demonstrate ≥{saturation_score}% category saturation
before release.

### NFR-2: Judge Agreement
The automated LLM-as-a-judge must achieve Cohen's κ ≥ 0.80 against human
annotations before deployment.
```

---

## Priority Ordering

Requirements are ordered by a combined score:

```
priority_score = severity × frequency × dimension_weight
```

| Severity | Frequency | Dimension Weight | Priority Score |
|----------|-----------|-----------------|----------------|
| 5 | 8 | 2.0 (safety) | 80 |
| 4 | 5 | 1.5 (accuracy) | 30 |
| 3 | 3 | 1.3 (instruction) | 11.7 |

Higher scores appear first in the requirements document.

---

## Traceability

Every requirement must trace back to:
1. **Failure code(s)** — which observed failures it addresses
2. **Golden queries** — which test cases demonstrate it
3. **Paradigm model** — which root cause analysis supports it
4. **Annotations** — which human judgments ground it

This ensures no requirement is speculative — every one is backed by observed evidence.

---

## When to Regenerate

Update requirements when:
- New failure codes emerge from additional annotation rounds
- Severity changes after re-evaluation
- Paradigm model is refined with new causal insights
- Saturation status changes (new categories discovered)

The GEDD flywheel means requirements evolve as the agent evolves.
