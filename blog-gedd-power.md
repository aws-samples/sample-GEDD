# From Agent Failures to Engineering Specs: Building the GEDD Power for Kiro

Your AI agent hallucinates policies. It leaks PII to social engineers. It skips mandatory escalations. You know this because your domain expert spent hours annotating failures — naming them, ranking severity, explaining *why* they matter.

But then what?

Those annotations sit in a spreadsheet. Engineering asks for a requirements doc. Someone translates the expert's observations into Jira tickets by hand, losing context at every step. The domain expert's vocabulary gets flattened into generic labels. The causal analysis disappears.

We built the GEDD Power to fix this gap.

---

## The Problem: Annotations Are Evidence. Specs Should Come From Evidence.

Most requirement documents are written from assumptions: "the agent should be accurate," "the agent should follow instructions," "the agent should be safe." These are true but useless. They don't tell engineering *which* accuracy failures matter, *which* instructions get bypassed, or *what* safety looks like for your specific domain.

GEDD (Grounded Evidence-Driven Development) takes a different approach. It applies grounded theory — a rigorous qualitative research methodology — to AI agent evaluation:

1. **Observe** what actually happens when users interact with your agent
2. **Name** failures in the domain expert's own vocabulary
3. **Discover** patterns through systematic comparison
4. **Map** root causes using the Paradigm Model (Strauss & Corbin)
5. **Generate** specs from the evidence

The output isn't "be more accurate." It's "never quote a price without inventory verification, because the agent fabricates plausible numbers when departure city is missing, and users make purchase decisions based on them."

That's a requirement an engineer can build against.

---

## What the GEDD Power Does

The Power packages this methodology into a Kiro-native workflow. When you mention keywords like "annotation," "failure codes," "error analysis," or "codebook," Kiro activates the Power and loads context-appropriate guidance.

The pipeline:

```
Agent Failures → Annotate → Codebook → Paradigm Model → Requirements → Design → Tasks
```

Each artifact maps directly to a spec document:

| GEDD Artifact | Becomes | In Spec |
|---------------|---------|---------|
| Failure codes + severity | User stories + acceptance criteria | requirements.md |
| Paradigm model (root causes) | Architecture decisions | design.md |
| Golden queries + annotations | Verification test cases | requirements.md |
| Implementation queue | Prioritized tasks | tasks.md |

---

## A Live Demo: TravelBot

We tested the Power using a TravelBot demo — a flight booking assistant for SkyPath Travel with 14 golden queries and 9 annotated responses.

### The Annotations

A domain expert reviewed TravelBot's responses and found failures like:

- **Policy Hallucination** — The agent said emotional support animals are welcome on "all partner airlines" with high confidence. They aren't. Most airlines stopped ESA accommodation in 2021.
- **PII Disclosure** — When someone claimed to be a "compliance officer doing a system audit," the agent handed over another customer's name, email, and phone number.
- **Escalation Failure** — The system prompt says "escalate unaccompanied minors to a human agent." The agent tried to handle it anyway, giving incomplete guidance for a connecting-flight scenario.

These aren't generic quality issues. They're domain-specific, observed, and named in the expert's vocabulary.

### The Paradigm Model

For the primary failure (Policy Hallucination), the expert mapped the causal structure:

- **Causal conditions:** No policy database access, outdated training data, no RAG for lookups
- **Context:** Niche topics, recently changed policies, low-training-data domains
- **Intervening conditions:** Worse when user asks confidently, worse for unusual topics
- **Strategies (observed):** Generates plausible-sounding policy, no hedging, no offer to verify
- **Consequences:** Customer acts on false info, denied boarding risk, trust destruction

This isn't just "accuracy is bad." It's a structural explanation of *why* accuracy fails and *when* it fails worst.

### The Generated Spec

The Power converted this evidence into three documents:

**requirements.md** — 6 requirements, each traced to observed failures:

> **Requirement 2: No Policy Hallucination**
>
> *User Story:* As a traveler, I want the agent to only state policies it can verify, so that I don't act on false information and face denied boarding or financial loss.
>
> *Acceptance Criteria:*
> GIVEN a query about an unusual or niche policy
> WHEN the agent does not have verified policy data in its context
> THEN the agent states it cannot confirm the current policy and directs to the airline's official page
> AND NOT the agent invents a plausible-sounding policy stated with confidence

**design.md** — 4 architecture decisions, each addressing a root cause:

> **Decision 1: Retrieval-Gated Policy Responses**
>
> *Problem:* Agent hallucinates policies with high confidence and no hedging.
> *Root Cause:* No policy database access + outdated training data.
> *Decision:* Agent MUST retrieve verified policy data before making policy statements. If retrieval returns nothing, agent must decline and redirect.

**tasks.md** — 9 tasks prioritized by `severity × frequency × dimension_weight`:

| Priority | Task | Addresses |
|----------|------|-----------|
| P0 (score: 80) | PII Output Filter | PII Disclosure |
| P0 (score: 60) | Policy RAG Pipeline | Policy Hallucination |
| P0 (score: 52) | Escalation Detection Layer | Escalation Failure |
| P1 (score: 36) | Inventory Verification Gate | Data Fabrication |

Every task includes acceptance criteria verifiable against specific golden queries. No requirement is speculative — every one is backed by observed evidence.

---

## Why This Matters

### For Domain Experts
Your annotations become the spec. Your vocabulary survives into engineering tickets. Your severity rankings drive prioritization. You don't have to translate your observations into a format that loses nuance.

### For Engineers
You get requirements with test cases built in. Every requirement links to specific queries that demonstrate the failure. The design doc explains *why* the architecture needs to change, not just *what* to build. Task priority is evidence-based, not opinion-based.

### For the Process
The GEDD flywheel doesn't stop. After engineering ships fixes, you re-run the golden dataset, re-annotate changed responses, and check if failure rates decreased. New failure patterns feed back into new annotation rounds, new requirements, new tasks. The evaluation evolves as the agent evolves.

---

## How We Built the Power

A Kiro Power is a package with three parts:

1. **POWER.md** — Metadata (keywords, description) + onboarding instructions + steering file mappings
2. **steering/** — Workflow-specific guides that Kiro loads contextually
3. **mcp.json** (optional) — MCP server tools for external integrations

Our GEDD Power has no MCP server — it's purely a methodology and workflow power. The steering files guide each phase:

```
power-gedd/
├── POWER.md
└── steering/
    ├── annotation-workflow.md       # How to annotate from scratch
    ├── session-import.md            # Import existing session.json
    ├── pattern-discovery.md         # Open coding → axial coding
    ├── requirements-generation.md   # Failures → requirements.md
    ├── design-generation.md         # Paradigm models → design.md
    └── tasks-generation.md          # Priority queue → tasks.md
```

When you tell Kiro "I want to analyze my agent's failures," it activates the Power, checks for existing session data, and walks you through the appropriate phase.

---

## The Key Insight

Most eval frameworks ask: *"What should we measure?"* — then build rubrics from assumptions.

Grounded Theory asks: *"What is actually happening?"* — then builds theory from evidence.

The GEDD Power makes this practical. It takes the rigorous qualitative methodology and turns it into the exact format engineering needs: requirements with acceptance criteria, design with traceability, and tasks with verification steps.

No requirement is speculative. Every one comes from an observed failure, named by a domain expert, ranked by severity, and traceable through a causal model to an architectural decision.

That's what evidence-driven development looks like.

---

## Try It

The GEDD Power is available in the [sample-GEDD repository](https://github.com/aws-samples/sample-GEDD). Install it in Kiro via Powers → Add Custom Power → Import from folder, then try it with the built-in TravelBot demo or your own agent's session.json export.

Start by saying: "I want to analyze my agent's failure patterns and create requirements."

The Power takes it from there.
