# Requirements Generation — Baseline to Improved

Generate requirements from the agent spec (baseline), then upgrade them with domain expert annotations (improved). Each annotation round sharpens the specs.

## Two Modes

### Mode A: Generate Baseline (no annotations yet)

When the agent has a spec but no annotation evidence, generate initial requirements from:
- Agent description and capabilities → user stories
- System prompt constraints → acceptance criteria
- Known edge cases → assumed test scenarios

This gives Kiro a starting point. It will be wrong in ways no one can predict yet.

### Mode B: Upgrade with Evidence (annotations available)

When an `error-analysis.md` exists, compare annotations against the baseline and produce improved requirements. This is the core value — every upgrade is grounded in observed reality.

---

## The Delta: Baseline → Improved

| Spec Element | Baseline (v1) | Improved (v2+) |
|-------------|---------------|----------------|
| User stories | "Agent handles pricing queries" | "Agent NEVER fabricates prices; redirects to official source" |
| Acceptance criteria | Assumed from system prompt | Actual failed responses as negative test cases |
| Correctness properties | Theoretical | Formal invariants from paradigm model |
| Priority | Engineer's intuition | `severity × frequency × dimension_weight` |
| Coverage | "Should cover edge cases" | Saturation metrics: 8/10 categories at ≥3 examples |
| Verification | Unit tests | Golden queries + judge agreement κ ≥ 0.80 |

---

## Mode A: Baseline Generation

### From Agent Spec → Initial User Stories

For each capability in the agent spec:

```
As a [target user],
I want the agent to [capability],
so that [value proposition from description].
```

### From System Prompt → Initial Acceptance Criteria

For each constraint/rule in the system prompt:

```
GIVEN [constraint context]
WHEN [trigger condition]
THEN [required agent behavior per system prompt]
```

### From Known Edge Cases → Initial Test Scenarios

For each `known_edge_case` in the agent spec, generate a requirement noting it needs validation.

**Baseline requirements are always marked as unvalidated:**

```markdown
### Requirement B-1: [From capability]
**Status:** ⚠️ Baseline — not yet validated by domain expert

**User Story:** As a [user], I want [capability], so that [value]

#### Acceptance Criteria (assumed)
1. GIVEN ... WHEN ... THEN ...

#### Validation Needed
- [ ] Domain expert has reviewed agent responses for this scenario
- [ ] Failure patterns (if any) have been coded
- [ ] Severity has been assessed
```

---

## Mode B: Evidence-Backed Upgrade

### Prerequisites
- `error-analysis.md` with failure codebook, annotations, and optionally paradigm model
- Existing baseline `requirements.md` (if not present, generate baseline first)

### From Failure Codes → Upgraded User Stories

Each failure code with severity ≥ critical becomes a requirement:

```
As a [target user from agent spec],
I want the agent to [desired behavior — opposite of observed failure],
so that [consequence avoidance from paradigm model].
```

**Example of the upgrade:**
```
BASELINE:
  As a shopper, I want the agent to answer pricing questions.

IMPROVED (after annotation):
  As a shopper, I want the agent to NEVER invent pricing information
  and always redirect to the official pricing page,
  so that I don't make purchase decisions based on fabricated data.

  Evidence: Failure code "Hallucinated Pricing" (severity: catastrophic,
  frequency: 7, paradigm consequence: "User acts on false info")
```

### From Annotations → Upgraded Acceptance Criteria

Each incorrect/partial annotation becomes a concrete test case:

```
GIVEN [the query context from golden prompt]
WHEN [the user asks / the agent receives]
THEN [the expected behavior — what the agent SHOULD do]
AND NOT [the observed failure — what it actually did wrong]
```

**Example:**
```
GIVEN a user asking about product pricing without a pricing database
WHEN the user asks "How much does the Pro plan cost?"
THEN the agent responds "I don't have current pricing" + links to pricing page
AND NOT invents "$49/month" (observed in annotation #12, severity: catastrophic)
```

### From Paradigm Model → Correctness Properties

Each paradigm model's causal chain becomes a formal invariant:

```
PROPERTY: [name from phenomenon]
FOR ALL queries WHERE [causal conditions]
THE agent SHALL [action strategy]
AND SHALL NOT [phenomenon behavior]
VERIFIED BY [golden queries that test this]
```

---

## Requirements Document Structure

Generate `.kiro/specs/{agent-name}/requirements.md`:

```markdown
# Requirements: {Agent Name}

**Iteration:** {N} | **Last updated from:** {error-analysis.md date}
**Evidence:** {X} annotations, {Y} failure codes, {Z}% saturation

## Improvement Summary (v{N} delta)

| What changed | Why | Evidence |
|-------------|-----|----------|
| Added: "Never fabricate prices" | Observed 7× in annotations | Code: Hallucinated Pricing |
| Upgraded severity: Escalation → P0 | Domain expert rated catastrophic | Annotations #3, #8 |
| New property: No PII disclosure | Social engineering succeeded | Code: PII Disclosure |

## Glossary
| Term | Definition |
|------|------------|
| {failure code} | {definition from codebook} |

## Functional Requirements

### REQ-1: {Highest-priority failure code}
**Status:** ✓ Evidence-backed (iteration {N})
**Priority:** {severity × frequency × dimension_weight}

**User Story:** As a {user}, I want {behavior}, so that {benefit}

#### Acceptance Criteria
1. GIVEN ... WHEN ... THEN ... AND NOT {observed failure}
2. GIVEN ... WHEN ... THEN ... AND NOT {observed failure}

#### Correctness Properties
- PROPERTY: {from paradigm model}

#### Evidence Chain
- Failure code: {label} (severity {N}, frequency {N})
- Golden queries: #{id}, #{id}
- Paradigm model: {phenomenon} → {consequences}
- Saturation: {category status}

### REQ-2: ...

## Non-Functional Requirements

### NFR-1: Coverage Confidence
Evaluation must demonstrate ≥{saturation_score}% category saturation.

### NFR-2: Judge Agreement
LLM-as-a-judge must achieve Cohen's κ ≥ 0.80 against human annotations.

### NFR-3: Regression Gate
All previously-passing golden queries must continue passing after changes.
```

---

## Priority Ordering

Requirements ordered by evidence weight:

```
priority_score = severity × frequency × dimension_weight
```

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Safety | 2.0× | Non-negotiable — failures here block release |
| Accuracy | 1.5× | Factual errors erode trust irreversibly |
| Bias | 1.5× | Fairness failures have outsized impact |
| Instruction Following | 1.3× | System prompt violations indicate fundamental issues |
| Completeness | 1.2× | Partial answers frustrate users |
| Quality | 1.0× | Baseline expectation |
| Tone | 0.8× | Important but rarely blocking |
| Brand Relevance | 0.8× | Company-specific, not universal |

---

## Traceability

Every improved requirement traces to:
1. **Failure code(s)** — which observed failures it addresses
2. **Golden queries** — which test cases demonstrate it
3. **Paradigm model** — which root cause analysis supports it
4. **Annotations** — which human judgments ground it
5. **Baseline requirement** — which original requirement it upgrades (or "NEW" if not in baseline)

---

## When to Run This Again

The lifecycle triggers a new requirements upgrade when:
- New annotation round adds failure codes not in current specs
- Severity reassessment changes priority ordering
- Paradigm model gains new causal insights → new design constraints
- Saturation changes (new categories discovered or achieved)
- Agent is updated and re-evaluated → new failures may emerge

Each run produces a versioned delta, so the improvement history is preserved.
