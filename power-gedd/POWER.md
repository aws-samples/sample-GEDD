---
name: "gedd"
displayName: "GEDD – Error-Driven Agent Specs"
description: "Turn domain-expert error analysis and annotations of AI agent failures into structured requirements, design docs, and implementation tasks using grounded theory methodology"
keywords: ["gedd", "error analysis", "annotation", "failure codes", "codebook", "agent evaluation", "grounded theory", "open coding", "axial coding", "judge", "golden dataset", "saturation", "paradigm model", "llm judge", "eval"]
author: "GEDD Team"
---

# GEDD Power – Error-Driven Agent Spec Generation

This power helps domain experts and PMs convert observed AI agent failures into actionable engineering specs using the GEDD (Grounded Evidence-Driven Development) methodology.

## What This Power Does

GEDD applies grounded theory (Strauss & Corbin) to AI agent evaluation:

1. **Observe failures** — Review agent responses and name what goes wrong in your own vocabulary
2. **Discover patterns** — Group failures into root causes using open coding and axial coding
3. **Generate specs** — Convert failure patterns into requirements, design constraints, and implementation tasks

The output is a Kiro-compatible spec (requirements.md + design.md + tasks.md) that tells engineering exactly what to fix, why it matters, and how to verify the fix.

## Core Workflow

```
Agent Failures → Annotate → Codebook → Paradigm Model → Requirements → Design → Tasks
```

| GEDD Artifact | Becomes | In Spec |
|---------------|---------|---------|
| Failure codes + severity | Acceptance criteria | requirements.md |
| Paradigm model (root causes) | Architecture constraints | design.md |
| Golden queries + annotations | Verification test cases | requirements.md |
| Saturation evidence | Coverage confidence | requirements.md |
| Implementation queue | Prioritized work items | tasks.md |

---

# Onboarding

## Step 1: Check for existing GEDD session

Look for an existing error analysis markdown file in the workspace. Common locations:
- `./*_error_analysis.md`
- `./error-analysis.md`
- `./outputs/*_error_analysis.md`

Also check for legacy `session.json` files:
- `./session.json`
- `./outputs/session.json`

If a markdown file is found, offer to load it directly.
If only a session.json exists, suggest: `grounded-evals export-md --session session.json`
If neither is found, guide the user through creating annotations from scratch.

## Step 2: Understand the annotation state

When loading an error-analysis.md (or session.json), check for:
- **Agent spec** — name, description, capabilities, system prompt
- **Golden queries** — the test queries with category assignments
- **Annotations** — verdicts (correct/partial/incorrect), failure codes, severity, memos
- **Codebook** — failure labels with definitions
- **Paradigm model** — if axial coding has been done (causal conditions → phenomenon → consequences)
- **Saturation status** — whether categories are fully covered

Report what's present and what's missing before proceeding.

## Step 3: Create workspace hook for annotation review

Create a hook at `.kiro/hooks/gedd-review.kiro.hook`:

```json
{
  "name": "GEDD Annotation Review",
  "version": "1.0.0",
  "description": "After editing annotation files, validate coverage and suggest next steps",
  "when": {
    "type": "fileEdited",
    "patterns": ["**/*_error_analysis.md", "**/error-analysis.md", "**/session.json", "**/annotations.json", "**/codebook.json"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "The GEDD session data was updated. Check saturation status, identify coverage gaps, and suggest whether we have enough evidence to generate or update the spec documents."
  }
}
```

---

# When to Load Steering Files

- Starting fresh annotations or reviewing agent output → `annotation-workflow.md`
- Building the failure codebook and paradigm model → `pattern-discovery.md`
- Generating requirements.md from annotations → `requirements-generation.md`
- Generating design.md from root cause analysis → `design-generation.md`
- Generating tasks.md from implementation queue → `tasks-generation.md`
- Importing an existing error-analysis.md or session.json → `session-import.md`

---

# Key Concepts

## Failure Codes
Named in the domain expert's own vocabulary. Examples:
- "Hallucinated Pricing" (not "accuracy_error")
- "Rating Disclosure Softening" (not "compliance_issue")
- "RTL Input Direction Drift" (not "layout_bug")

The power of GEDD is that codes come from observation, not assumption.

## Saturation
A category is saturated when:
- ≥3 prompts cover it
- No new failure patterns emerge from additional examples
- The domain expert confirms coverage is sufficient

## Paradigm Model (Axial Coding)
Maps failures causally:
- **Causal Conditions** — What triggers the failure?
- **Phenomenon** — The central failure pattern
- **Context** — When/where does it happen?
- **Intervening Conditions** — What makes it worse/better?
- **Action Strategies** — How should the agent handle it?
- **Consequences** — What's the impact if unfixed?

## The 8 Evaluation Dimensions
Failures map to standard dimensions for the judge rubric:
1. Quality
2. Accuracy
3. Brand Relevance
4. Bias
5. Safety
6. Completeness
7. Tone
8. Instruction Following

---

# Spec Output Format

The power generates specs in Kiro format at `.kiro/specs/{agent-name}/`:

### requirements.md
- User stories derived from failure patterns ("As a user, I expect the agent to NOT [failure behavior]")
- Acceptance criteria from golden query annotations
- Correctness properties from saturation evidence

### design.md
- Architecture constraints from paradigm model root causes
- Component responsibilities addressing causal conditions
- Integration patterns that prevent intervening conditions

### tasks.md
- Implementation items prioritized by severity × frequency
- Each task references specific failure codes and test cases
- Dependencies reflect the paradigm model's causal chain
