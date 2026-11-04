# From SME Evidence to LLM-as-Judge Gates: How We Refocused GEDD

AI teams keep running into the same evaluation problem: everyone wants a reliable judge, but the judge is often written before the team has enough evidence to know what it should judge.

GEDD, Grounded Evidence Driven Development, takes the opposite path. It starts with domain experts, product managers, and SMEs. They define the domain, curate the risky scenarios, review baseline responses, name the failure modes, and only then generate the judge spec, judge prompt, and response gate.

This post walks through the step-by-step process we used to refocus GEDD around one clear product idea:

> GEDD turns SME evidence into systematic LLM-as-Judge response gates.

The result is not a generic rubric builder. It is an evidence pipeline for creating a domain-specific guardrail calibration set and an LLM-as-Judge gate that checks customer-facing responses before customers see them.

## Why We Had to Refocus

The product had accumulated too many ideas at once.

Some parts described GEDD as a domain expert workflow. Some parts described a generated requirements handoff. Some parts emphasized a tool-specific implementation path. Some demos were strong, but their language made the product sound like it existed to feed another system rather than to solve the actual evaluation problem.

That created a messaging problem:

- Domain experts could not immediately tell what job GEDD did for them.
- Product managers saw multiple output names and could not tell which artifact mattered most.
- Engineers saw generated files, but not the evidence chain that made those files trustworthy.
- The demo flow mixed baseline requirements, judge requirements, response gates, and app-specific terminology.

The fix was to make the product spine simple:

```text
Domain context
  -> curated query set
  -> baseline responses
  -> SME annotations
  -> failure codebook
  -> guardrail calibration scenarios
  -> systematic LLM-as-Judge
  -> response gate before customers see answers
```

Everything that did not support that spine had to be removed, renamed, or repositioned.

## Step 1: Name the Product Job

We started by writing the product sentence in plain language:

> GEDD is Grounded Evidence Driven Development for systematic LLM-as-Judge curation.

The important word is evidence.

GEDD is not trying to invent quality criteria from generic best practices. It is trying to preserve what SMEs learn from actual baseline behavior:

- What did the user ask?
- What did the assistant answer?
- What would a domain expert accept, reject, or escalate?
- What failure mode explains the bad answer?
- How severe is the failure?
- What would the corrected behavior look like?
- Should this failure block a customer-visible response?

Once that was clear, the rest of the product language had to align with it.

## Step 2: Remove Tool-Specific Framing

The next step was cleanup. We removed implementation-tool-specific steering files, legacy handoff folders, and old blog content that made GEDD sound like an accessory to another workflow.

That mattered because the product is broader than one implementation target. A team should be able to use GEDD whether their judge gate is implemented in a service, CI workflow, model-evaluation harness, agent runtime, or human-in-the-loop review queue.

The new product language uses these terms consistently:

- Baseline evidence
- SME annotations
- Failure codebook
- Guardrail calibration set
- Judge spec
- LLM-as-Judge prompt
- Response gate
- Measurement report

The generated judge output is now a judge spec, not a platform-specific requirements file. The response gate is the executable decision point: pass, fail, block, escalate, or request human review.

## Step 3: Rewrite the README Around the Evidence Flow

The README became the product entry point.

The old README was trying to explain too much history. The new README answers four questions quickly:

1. What is GEDD?
2. What does it produce?
3. How does the workflow run?
4. How do I try it locally?

The artifact table now centers the actual outputs:

| Artifact | Purpose |
|---|---|
| `SME_error_analysis.md` | Evidence handoff with domain context, query coverage, baseline responses, annotations, failure codes, memos, and traceability |
| Guardrail calibration set | Scenario rows with conversation turns, input/output side, expected pass/fail or tier, category labels, SME rationale, and corrective feedback |
| Judge spec | Structured description of what the LLM-as-Judge must detect, block, escalate, and explain |
| LLM-as-Judge prompt | Domain-specific judge prompt grounded in SME-defined failure modes |
| Response gate | Pass/fail decision contract that runs before an answer becomes customer-visible |
| Measurement report | Before/after quality view across specificity, traceability, testability, domain coverage, and response accuracy |

That table became a useful forcing function. If a UI label, CLI command, test, or demo did not map to one of those artifacts, it needed to be cleaned up.

## Step 4: Update the Coach Prompt

The Coach is the part of GEDD that keeps SMEs in the evidence workflow.

We updated the system prompt so the Coach now leads users through six product steps:

1. Domain expert intake
2. Baseline evidence
3. Domain query curation
4. Baseline agent test
5. SME annotation and error analysis
6. Systematic LLM-as-Judge generation and measurement

The biggest change was Step 3. Each approved query is no longer just a "golden prompt." It is the start of a guardrail calibration scenario:

- Conversation turns
- Evaluation side
- Expected result or tier
- Category label
- SME reason
- Corrective feedback when the baseline answer fails

This makes the query set more useful. It can become a regression suite, a judge calibration set, and a coverage report, not just a prompt list.

## Step 5: Reframe the UI

The UI had to match the new product spine.

We updated visible pages to use the same vocabulary:

- Home: SME evidence to LLM-as-Judge response gates
- Coach: Grounded Evidence Driven Development
- Annotations: review customer-facing answers and tag product failures
- Judge Spec: generate the structured judge specification
- Judge: generate the pre-customer LLM-as-Judge gate
- Evidence: export `SME_error_analysis.md` and the judge package
- Measurement: compare baseline and GEDD-generated judge quality

We also changed downloads and labels so the judge artifact is `judge-spec.md`. That makes the artifact name match its job.

The UI message is now direct:

> Coach leads SMEs and product managers from baseline evidence to a systematic judge spec and an LLM-as-Judge gate that checks customer-facing responses before customers see them.

## Step 6: Keep the Demo, Remove the Brand-Specific Dependency

The AAA game localization demo was useful because it showed a domain where generic helpfulness is not enough.

A localization answer can sound fluent and still be wrong if it:

- Breaks runtime placeholders or markup
- Reverses a gameplay instruction
- Softens an age rating or regional disclosure
- Uses inconsistent franchise terminology
- Flattens character voice or canon roles
- Mishandles RTL controller prompts

We anonymized the demo so it became a general AAA game localization assistant instead of a named franchise scenario. That keeps the demo focused on the product lesson:

SME evidence creates gates that generic fluency checks miss.

## Step 7: Bring in Guardrail Calibration as the Structural Pattern

The useful inspiration from SonderMind's public guardrail evaluation work is the structure, not the domain.

Their repo shows a clean idea: guardrail evaluation scenarios should be simple, explicit, and framework-agnostic. A scenario can include conversation turns, category labels, expected outcomes, reasons, and feedback. That structure is what makes the dataset useful for calibration, regression testing, and per-category coverage analysis.

GEDD now adopts that pattern in a domain-neutral way.

For GEDD, a guardrail calibration scenario should include:

| Field | Purpose |
|---|---|
| `conversation_turns` | User and assistant messages needed to reproduce the risk |
| `evaluation_side` | Whether the scenario tests an input guardrail, output guardrail, or pre-customer response gate |
| `expected_result` | SME-approved result, such as allow, continue with resources, block, or human review |
| `category` | Domain grouping for coverage and per-category pass/fail analysis |
| `failure_code` | Exact codebook label when the scenario should fail |
| `reason` | SME rationale for why the expected result is correct |
| `feedback` | Corrective guidance or safer-response notes when the baseline fails |

This is a practical bridge between qualitative SME judgment and automated judge calibration.

## Step 8: Make the Judge Gate Contract Explicit

The judge has to return a structured decision. Otherwise teams end up with prose that sounds reasonable but is hard to automate.

The GEDD judge gate contract is intentionally simple:

```json
{
  "pass_fail": "pass | fail",
  "failure_code": "domain failure label or null",
  "severity": "low | medium | high | critical | catastrophic",
  "rationale": "why the response passes or fails",
  "evidence_references": ["query id", "failure code", "judge criterion"],
  "recommended_action": "allow | revise_response | request_human_review",
  "customer_visible_block": true
}
```

The engineering handoff now also tracks:

- `evaluation_side`: input guardrail, output guardrail, or response gate
- `expected_tier`: allow, continue with resources, block, human review, or null
- Guardrail calibration set readiness
- Clean pass examples
- Coded fail examples
- Borderline examples
- Judge-human agreement target
- False positive and false negative gates
- Output schema validity

This makes the handoff concrete enough for CI, shadow evaluation, and blocking release gates.

## Step 9: Test the Refactor Like a Product Change

This was not just a copy change. It touched the Coach prompt, README, methodology, UI labels, report handoff, release smoke checks, and tests.

The validation pass included:

```bash
python3 -m compileall src
python3 -m pytest tests
python3 scripts/release_check.py --base-url http://127.0.0.1:8080
```

The full test suite passed:

```text
246 passed
```

We also scanned the repo for old tool-specific language and brand-specific demo references to make sure the product surface stayed clean.

## The Final Shape

After the refocus, GEDD has one clear product story:

1. SMEs define the domain and risks.
2. SMEs curate query scenarios that expose real product boundaries.
3. The baseline assistant is tested against those scenarios.
4. SMEs annotate what passed, failed, or needs review.
5. Failure codes become a domain codebook.
6. The scenario set becomes a guardrail calibration set.
7. The codebook and scenarios generate a judge spec and LLM-as-Judge prompt.
8. The response gate checks candidate customer-facing answers before release or display.
9. Measurement tracks whether the judge is specific, testable, traceable, covered, calibrated, and useful.

That is Grounded Evidence Driven Development.

It is not "write a rubric first." It is "earn the judge from evidence."

## Why This Matters

Most teams want LLM-as-Judge systems because they need scale. But scale without domain evidence just automates vague judgment.

GEDD makes the judge accountable to the people who know the domain:

- The SME owns the scenarios.
- The SME owns the failure definitions.
- The SME owns severity.
- The SME owns the corrective feedback.
- The judge inherits those decisions and makes them executable.

That is the difference between a generic evaluator and a customer-facing response gate a product team can defend.
