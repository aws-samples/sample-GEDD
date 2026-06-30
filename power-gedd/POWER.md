---
name: "gedd"
displayName: "GEDD – Continuous Learning for Agent Specs"
description: "A continuous learning lifecycle where Kiro-generated baseline requirements are improved through domain expert error analysis and annotations — turning observed agent failures into better specs, every iteration"
keywords: ["gedd", "error analysis", "annotation", "failure codes", "codebook", "agent evaluation", "grounded theory", "open coding", "axial coding", "judge", "golden dataset", "saturation", "paradigm model", "llm judge", "eval", "requirements", "continuous improvement"]
author: "GEDD Team"
---

# GEDD Power – Continuous Learning for Agent Specs

Kiro generates baseline requirements. The agent runs. A domain expert reviews what went wrong. GEDD converts those observations into improved requirements. The cycle repeats.

This is not a one-shot spec generator — it's a **continuous learning lifecycle** where every annotation round makes the specs more precise, more grounded, and more defensible.

## The Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   ① Kiro Baseline ──→ ② Agent Runs ──→ ③ Domain Expert         │
│        Specs              Queries           Annotates            │
│         ↑                                      │                │
│         │                                      ↓                │
│   ⑤ Improved    ←── ④ GEDD Processes ←── Failure Codes,        │
│      Specs            Evidence              Severity,           │
│                                             Memos               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

| Phase | Who | What Happens | Output |
|-------|-----|-------------|--------|
| ① Baseline | Kiro + engineer | Generate initial requirements from agent description | `requirements.md` v1 |
| ② Run | Agent | Execute golden queries against the agent | Responses |
| ③ Annotate | Domain expert | Review responses, name failures, set severity | `error-analysis.md` |
| ④ Process | GEDD Power | Discover patterns, build paradigm models | Codebook + causal analysis |
| ⑤ Improve | Kiro + GEDD | Upgrade specs with evidence-backed criteria | `requirements.md` v2+ |

Each iteration adds precision. The first pass catches broad failures. The second sharpens severity. The third reaches saturation. By v3, you have requirements that no LLM could have generated from first principles — they come from observed reality.

## What Gets Better Each Iteration

| Spec Element | Baseline (v1) | After Annotations (v2+) |
|-------------|---------------|------------------------|
| User stories | Generic capabilities | Grounded in observed failures |
| Acceptance criteria | Assumed edge cases | Actual incorrect responses as test cases |
| Correctness properties | Theoretical constraints | Evidence-backed invariants from paradigm model |
| Priority ordering | Engineer's guess | severity × frequency × dimension_weight |
| Coverage confidence | Unknown | Saturation metrics from annotation rounds |
| Verification | Unit tests | Golden queries + LLM judge with κ ≥ 0.80 |

---

# Onboarding

## Step 1: Assess the current state

Check what exists in the workspace:

**Already have specs?** Look for existing Kiro specs:
- `.kiro/specs/{agent-name}/requirements.md`
- `.kiro/specs/{agent-name}/design.md`

**Already have annotations?** Look for GEDD output:
- `./*_error_analysis.md`
- `./error-analysis.md`
- `./outputs/*_error_analysis.md`
- `./session.json` (legacy — suggest `grounded-evals export-md`)

**Starting fresh?** No specs, no annotations — begin at Phase ①.

Based on what's found, determine where in the lifecycle to start:
- Specs exist, no annotations → "Let's run the agent and annotate what goes wrong"
- Annotations exist, no specs → "Let's generate improved requirements from this evidence"
- Both exist → "Let's compare the baseline to the annotations and upgrade the specs"
- Neither exists → "Let's start with a baseline spec for your agent"

## Step 2: Understand the evidence

When loading an error-analysis.md, check for:
- **Agent spec** — name, description, capabilities, system prompt
- **Golden queries** — test queries with category assignments
- **Annotations** — verdicts (correct/partial/incorrect), failure codes, severity, memos
- **Codebook** — failure labels with definitions
- **Paradigm model** — causal analysis (conditions → phenomenon → consequences)
- **Saturation status** — whether categories are fully covered

Report what's present and what's missing. Identify which lifecycle phase to enter.

## Step 3: Create workspace hook

Create a hook at `.kiro/hooks/gedd-review.kiro.hook`:

```json
{
  "name": "GEDD Learning Cycle",
  "version": "1.0.0",
  "description": "When annotation evidence changes, check if specs should be upgraded",
  "when": {
    "type": "fileEdited",
    "patterns": ["**/*_error_analysis.md", "**/error-analysis.md", "**/session.json"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "The GEDD annotation evidence was updated. Compare against current specs: are there new failure codes not yet captured in requirements? Has severity changed? Are there new paradigm model insights that should become design constraints? Suggest specific upgrades."
  }
}
```

---

# When to Load Steering Files

- Agent has no specs yet; generate baseline → `requirements-generation.md`
- Starting fresh annotations on agent output → `annotation-workflow.md`
- Building the failure codebook and paradigm model → `pattern-discovery.md`
- Upgrading requirements from new annotation evidence → `requirements-generation.md`
- Upgrading design from new root cause analysis → `design-generation.md`
- Generating tasks from the improvement delta → `tasks-generation.md`
- Importing an existing error-analysis.md or session.json → `session-import.md`

---

# Key Concepts

## The Learning Delta

The most important output of each cycle isn't the spec itself — it's the **delta** between what the baseline predicted and what the domain expert observed:

- Baseline said: "Agent should handle pricing questions"
- Expert observed: "Agent fabricates prices with high confidence"
- Delta: **New acceptance criterion** — "MUST refuse to quote prices without database access"

Each delta is a lesson the agent (and its specs) couldn't have learned without human observation.

## Failure Codes

Named in the domain expert's own vocabulary:
- "Hallucinated Pricing" (not "accuracy_error")
- "Rating Disclosure Softening" (not "compliance_issue")
- "RTL Input Direction Drift" (not "layout_bug")

Codes come from observation, not assumption. They get more precise each iteration.

## Saturation

A category is saturated when:
- ≥3 prompts cover it
- No new failure patterns emerge from additional examples
- The domain expert confirms coverage is sufficient

Saturation is the signal that an annotation round is complete and specs can be upgraded.

## Paradigm Model (Axial Coding)

Maps failures causally — this is what turns observations into design constraints:
- **Causal Conditions** — What triggers the failure? → becomes a guardrail
- **Phenomenon** — The central failure pattern → becomes the requirement
- **Context** — When/where it happens → becomes the test scope
- **Intervening Conditions** — What makes it worse/better → becomes config
- **Action Strategies** — How the agent should handle it → becomes the spec
- **Consequences** — Impact if unfixed → becomes the priority

## The 8 Evaluation Dimensions

Failures map to standard dimensions with weights:
1. Safety (2.0×)
2. Accuracy (1.5×)
3. Bias (1.5×)
4. Instruction Following (1.3×)
5. Completeness (1.2×)
6. Quality (1.0×)
7. Tone (0.8×)
8. Brand Relevance (0.8×)

---

# Spec Output Format

The power generates and upgrades specs at `.kiro/specs/{agent-name}/`:

### requirements.md
- **Baseline (v1):** User stories from agent description and assumed capabilities
- **Improved (v2+):** Evidence-backed acceptance criteria from annotations, correctness properties from paradigm models, priority from severity × frequency

### design.md
- Architecture constraints derived from paradigm model root causes
- Guardrails addressing causal conditions
- Monitoring hooks from consequence analysis

### tasks.md
- Implementation items prioritized by the learning delta
- Each task traces to failure codes and golden queries
- Completion = golden queries pass + judge agrees with human (κ ≥ 0.80)
