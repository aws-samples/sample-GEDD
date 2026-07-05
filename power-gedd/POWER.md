---
name: "gedd"
displayName: "GEDD - Kiro Domain Specs + LLM Judge"
description: "A Kiro Power for consuming GEDD's domain-expert-curated evidence and generating two outputs: Kiro requirements.md and an LLM-as-a-Judge release gate"
keywords: ["gedd", "kiro", "requirements.md", "ears", "llm judge", "error analysis", "annotation", "failure codes", "codebook", "agent evaluation", "grounded theory", "open coding", "axial coding", "golden dataset", "saturation", "domain specs"]
author: "GEDD Team"
---

# GEDD Power - Kiro Domain Specs + LLM Judge

GEDD is the Coach-led workflow for converting domain expert review of AI agent failures into curated evidence. This Power consumes that evidence and generates two concrete artifacts:

1. `.kiro/specs/{agent-name}/requirements.md`
2. `llm-judge.md`

Use the GEDD web UI when SMEs need a guided annotation surface to curate evidence. Use this Kiro Power when Kiro should consume that evidence and write Kiro-ready specs directly into the workspace.

## Product Workflow

```
Coach -> SME Error Analysis -> Annotations -> Kiro requirements.md + LLM Judge
```

| Phase | Who | What Happens | Output |
|-------|-----|--------------|--------|
| Coach | SME + product owner | Define the agent, users, task boundary, risk posture, and query plan | Agent spec + golden queries |
| Error Analysis | SME + evaluator | Review real or proposed agent responses and identify incorrect behavior | Curated evidence queue |
| Annotations | SME | Capture verdict, failure code, severity, confidence, and memo | Domain-expert-curated codebook + annotated failures |
| Domain Specs | GEDD Power + Kiro | Convert curated evidence into EARS acceptance criteria in Kiro's requirements format | `requirements.md` |
| Judge | GEDD Power + evaluator | Convert the same failure modes into an automated release gate | `llm-judge.md` |

Kiro's feature-spec workflow is requirements-first. GEDD provides the domain evidence Kiro needs: user stories and EARS acceptance criteria that come from SME-curated failures rather than generic assumptions.

## What GEDD Generates

### Primary Output 1: Kiro `requirements.md`

Generated at:

```text
.kiro/specs/{agent-name}/requirements.md
```

The file uses Kiro's requirements structure and EARS notation:

```markdown
# Requirements Document

## Introduction

## Requirements

### Requirement 1
**User Story:** As a {user}, I want {capability}, so that {domain outcome}.

#### Acceptance Criteria
1. WHEN {trigger}, THE SYSTEM SHALL {expected behavior}.
2. IF {unwanted condition}, THEN THE SYSTEM SHALL {safe response}.
3. WHILE {domain state}, THE SYSTEM SHALL {required invariant}.
```

### Primary Output 2: LLM Judge

Generated at:

```text
.kiro/specs/{agent-name}/llm-judge.md
```

The judge prompt enforces the same failure codes and release gates used in `requirements.md`. It should return a structured decision with:

```json
{
  "pass_fail": "pass | fail",
  "failure_code": "domain failure label or null",
  "severity": "low | medium | high | critical | catastrophic",
  "rationale": "why the response passes or fails",
  "evidence_references": ["query id", "requirement id"],
  "recommended_action": "ship | revise | block release"
}
```

## Source Evidence

GEDD provides the evidence layer. Treat these inputs as the domain-expert-curated source of truth:

- A GEDD web UI export containing session data, annotations, codebook, and judge prompt inputs
- A markdown `error-analysis.md` handoff
- Manually supplied agent description, golden queries, and SME annotations

The minimum viable curated evidence for generation:

| Curated Evidence | Required For |
|----------|--------------|
| Agent name and task boundary | Both outputs |
| Target users and capabilities | User stories |
| Golden queries or traces | Acceptance criteria and judge examples |
| SME verdicts | Failure-mode grounding |
| Failure codes | Requirements and judge rules |
| Severity and memos | Priority, release gates, rationale |

## EARS Mapping

Use EARS patterns from the curated domain evidence:

| Evidence | EARS Pattern | Output |
|----------|--------------|--------|
| Always-active rule | Ubiquitous | `THE SYSTEM SHALL ...` |
| Triggering user scenario | Event-driven | `WHEN ..., THE SYSTEM SHALL ...` |
| Domain state or context | State-driven | `WHILE ..., THE SYSTEM SHALL ...` |
| Observed unsafe failure | Unwanted behavior | `IF ..., THEN THE SYSTEM SHALL ...` |
| State plus trigger | Complex | `WHILE ..., WHEN ..., THE SYSTEM SHALL ...` |

Most GEDD failures map naturally to unwanted behavior because the SME has already named what must not happen again.

## Onboarding

### Step 1: Assess Workspace State

Check for existing artifacts:

- `.kiro/specs/{agent-name}/requirements.md`
- `.kiro/specs/{agent-name}/llm-judge.md`
- `./*_error_analysis.md`
- `./error-analysis.md`
- `./outputs/*_error_analysis.md`
- `./session.json`

Choose the entry point:

| Found | Start Here |
|-------|------------|
| No evidence, no spec | Coach the agent definition and golden queries |
| Curated evidence, no requirements | Generate Kiro `requirements.md` and LLM Judge |
| Existing requirements, new annotations | Upgrade requirements and judge from the delta |
| Requirements but no judge | Generate LLM Judge from the same failure modes |

### Step 2: Validate Evidence

Before generation, report what is present and missing:

- Agent spec
- System prompt or behavior contract
- Golden queries or traces
- SME annotations
- Failure codebook
- Severity labels
- Memos or release-gate notes
- Saturation evidence

If failure codes or SME annotations are missing, do not fabricate domain requirements. Ask for GEDD evidence curation first.

### Step 3: Generate the Two Outputs

Load steering files in this order:

1. `steering/annotation-workflow.md` if evidence is missing or unclear
2. `steering/pattern-discovery.md` if codes need consolidation
3. `steering/requirements-generation.md` to write Kiro `requirements.md`
4. `steering/judge-generation.md` to write `llm-judge.md`

Optional Kiro follow-ons:

- `steering/design-generation.md`
- `steering/tasks-generation.md`

These are not the core GEDD product. Generate them only when the user explicitly wants Kiro design/tasks after `requirements.md` and the LLM Judge are complete.

## Workspace Hook

Create `.kiro/hooks/gedd-review.kiro.hook` when the project uses ongoing annotation rounds:

```json
{
  "name": "GEDD Domain Spec Review",
  "version": "1.0.0",
  "description": "When GEDD curated evidence changes, check whether requirements.md or the LLM Judge must be updated",
  "when": {
    "type": "fileEdited",
    "patterns": ["**/*_error_analysis.md", "**/error-analysis.md", "**/session.json"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "GEDD curated evidence changed. Compare the evidence to current requirements.md and llm-judge.md. Identify new failure codes, severity changes, missing EARS criteria, and judge rules that should be added."
  }
}
```

## Quality Bar

Before calling the output complete:

- Every high-severity failure code maps to at least one EARS acceptance criterion.
- Every generated requirement has a user story and traceable acceptance criteria.
- The judge covers the same failure codes as `requirements.md`.
- The judge output contract is structured enough for CI or release review.
- The documents avoid generic "be accurate" requirements unless tied to domain evidence.

## Example Command

```text
Use GEDD to turn this domain-expert-curated evidence into Kiro requirements.md and an LLM Judge.
```

Expected behavior:

1. Validate evidence completeness.
2. Consolidate failure codes.
3. Generate `.kiro/specs/{agent-name}/requirements.md`.
4. Generate `.kiro/specs/{agent-name}/llm-judge.md`.
5. Report gaps that still need SME annotation.
