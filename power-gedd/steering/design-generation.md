# Design Generation from GEDD Root Cause Analysis

Convert paradigm models and dimension mappings into architectural design constraints.

## Prerequisites
- Paradigm models for each major failure pattern
- Dimension mappings with causal conditions
- Requirements document (requirements.md) already generated
- Agent spec with system prompt and capabilities

---

## Mapping Strategy

### From Paradigm Model → Architecture Decisions

Each paradigm model reveals *why* failures happen. The design document addresses root causes structurally.

| Paradigm Element | Design Decision Type |
|-----------------|---------------------|
| Causal Conditions | Input validation, guardrails, context requirements |
| Context | Environment constraints, configuration needs |
| Intervening Conditions | Feature flags, fallback paths, degradation strategy |
| Action Strategies | Component behavior specs, response templates |
| Consequences | Monitoring hooks, alerting thresholds |

### From Causal Conditions → System Constraints

**Template:**
```
CONSTRAINT: {name}
BECAUSE: {causal condition from paradigm model}
THE SYSTEM SHALL: {architectural decision}
IMPLEMENTED AS: {component/module/pattern}
```

**Example:**
```
CONSTRAINT: No Ungrounded Price Claims
BECAUSE: Agent hallucinates pricing when no pricing data is in context
THE SYSTEM SHALL: Require pricing data in retrieval context before allowing price-related responses
IMPLEMENTED AS: RAG pipeline with mandatory pricing index lookup + response filter
```

### From Intervening Conditions → Mitigation Patterns

For each "what makes it worse" condition:
```
MITIGATION: {name}
WORSENED BY: {intervening condition}
PATTERN: {architectural pattern that prevents escalation}
```

**Example:**
```
MITIGATION: Multi-product confusion guard
WORSENED BY: Multiple products mentioned in single query (causes confabulation)
PATTERN: Entity extraction → per-entity context retrieval → response templating per entity
```

---

## Design Document Structure

Generate `.kiro/specs/{agent-name}/design.md` with this structure:

```markdown
# Design: {Agent Name} — Iteration {N}

## Overview
Architectural approach to address {X} root causes identified through
GEDD analysis of {Y} failure patterns across {Z} evaluation dimensions.

## System Context
- Agent: {name} — {description}
- Runtime: {Bedrock/Anthropic/AgentCore}
- Integration points: {list of systems the agent connects to}

## High-Level Architecture

### Component Diagram
{Describe or diagram the components that address root causes}

### Data Flow
{How information flows to prevent identified failures}

## Design Decisions

### Decision 1: {Addresses highest-priority paradigm model}

**Problem:** {phenomenon from paradigm model}
**Root Cause:** {causal conditions}
**Decision:** {architectural choice}
**Alternatives Considered:** {what else was evaluated}
**Tradeoffs:** {what this costs}

#### Components Affected
- {component}: {what changes}
- {component}: {what changes}

#### Verification
- Property: {correctness property from requirements}
- Test approach: {how to verify this design choice works}

### Decision 2: ...
(repeat for each paradigm model)

## Guardrails & Constraints

### Input Guardrails
{From causal conditions — what inputs must be validated/filtered}

### Output Guardrails
{From consequences — what outputs must be checked before delivery}

### Context Requirements
{What information MUST be available for the agent to respond safely}

## Failure Modes & Fallbacks

| Failure Mode | Detection | Fallback | Escalation |
|--------------|-----------|----------|------------|
| {from paradigm} | {how to detect} | {graceful degradation} | {when to alert} |

## Monitoring & Observability

### Metrics (derived from failure codes)
| Metric | Source | Threshold | Action |
|--------|--------|-----------|--------|
| {failure_code}_rate | Judge scoring | > {threshold} | Alert + retrain |

### Drift Detection
{How to detect when new failure patterns emerge — feeds back into GEDD annotation}

## Dependencies
- requirements.md: {link to requirements this design satisfies}
- Paradigm models: {which root cause analyses informed decisions}
- Failure codes: {which codes are architecturally addressed}
```

---

## Design Principles from GEDD

### 1. Evidence-Driven Architecture
Every design decision traces to an observed failure, not an assumed risk. If it wasn't in the annotations, it's not a priority.

### 2. Root Cause Over Symptom
Address causal conditions (paradigm model), not surface behaviors. Fixing symptoms creates whack-a-mole; fixing causes prevents classes of failures.

### 3. Verifiable by Construction
Each design decision maps to a correctness property that can be tested against golden queries. If you can't test it with the golden dataset, question whether it's needed.

### 4. Proportional Response
Design complexity should match failure severity:
- Severity 5 (release blocker) → Hard guardrails, architectural changes
- Severity 4 (critical) → Validation layers, fallback paths
- Severity 3 (major) → Configuration changes, prompt engineering
- Severity 2 (minor) → Logging and monitoring only

### 5. Flywheel-Ready
Design should include monitoring hooks that feed back into the GEDD annotation loop. New failures discovered in production become new annotation rounds.

---

## When to Regenerate

Update design when:
- New paradigm models reveal previously unknown root causes
- Requirements change after additional annotation rounds
- Architectural constraints change (new runtime, new integrations)
- Mitigation patterns prove ineffective (failure rate doesn't decrease)
