# Pattern Discovery (Open Coding → Axial Coding)

Transform raw annotations into structured failure patterns using grounded theory.

## Prerequisites
- Completed annotations with failure codes, severity, and memos
- Saturation evidence (≥3 examples per category, no new codes emerging)

---

## Phase 1: Open Coding — Organize the Codebook

### Step 1: List all failure codes

Gather every unique failure code from annotations. For each code, record:

| Field | Description |
|-------|-------------|
| Label | The domain expert's name for this failure |
| Type | in_vivo (expert's own words) or constructed (AI-suggested) |
| Definition | What exactly this failure means |
| Exemplar prompts | 2-3 queries that trigger this failure |
| Severity range | Min-max severity across annotations |
| Frequency | How often this code appears |

### Step 2: Check for overlaps and merges

Review codes for:
- **Duplicates** — Two codes that describe the same failure differently → merge
- **Hierarchy** — One code is a subset of another → make it a sub-code
- **Splits** — One code covers two distinct failures → split into two

### Step 3: Assign to categories

Group codes into higher-order categories. Standard groupings:

| Dimension | Typical Codes |
|-----------|---------------|
| Accuracy | Hallucination, fabrication, outdated info |
| Safety | Harmful content, dangerous advice |
| Completeness | Missing steps, partial answers |
| Instruction Following | Ignored constraints, exceeded boundaries |
| Tone | Wrong register, inappropriate language |
| Brand Relevance | Off-brand voice, misaligned values |
| Bias | Discriminatory patterns, unfair assumptions |
| Quality | Incoherent, repetitive, poorly structured |

Note: Not all codes fit standard dimensions. Domain-specific dimensions are expected and valuable.

---

## Phase 2: Axial Coding — Build the Paradigm Model

For each major failure pattern (severity ≥ 3, frequency ≥ 2), construct a paradigm model:

### The Paradigm Model Template

```
PHENOMENON: [The central failure pattern]
  What is actually happening when this failure occurs?

CAUSAL CONDITIONS: [What triggers it?]
  - Specific input types that cause this
  - System states that enable it
  - Missing context or information

CONTEXT: [When/where does it happen?]
  - Which query categories trigger it most
  - Environmental conditions (model version, context length, etc.)
  - User interaction patterns

INTERVENING CONDITIONS: [What makes it worse/better?]
  - Factors that increase severity
  - Conditions that partially mitigate
  - Related system behaviors

ACTION STRATEGIES: [How should the agent handle it?]
  - Desired behavior when this situation occurs
  - Fallback strategies
  - Escalation paths

CONSEQUENCES: [Impact if unfixed]
  - User harm (confusion, misinformation, safety risk)
  - Business impact (trust, compliance, revenue)
  - System impact (cascading failures, data corruption)
```

### Example Paradigm Model

```
PHENOMENON: Hallucinated Pricing
  Agent invents prices for products/services not in its context.

CAUSAL CONDITIONS:
  - User asks about specific pricing
  - No pricing data in system prompt or context
  - Model confuses training data with current facts

CONTEXT:
  - Storefront and e-commerce queries
  - Comparison shopping scenarios
  - When user explicitly asks "how much does X cost?"

INTERVENING CONDITIONS:
  - Worse when multiple products mentioned (model confabulates)
  - Better when system prompt explicitly says "do not quote prices"
  - Partially mitigated by RAG with current pricing data

ACTION STRATEGIES:
  - Agent should say "I don't have current pricing information"
  - Redirect to official pricing page
  - Never invent a number

CONSEQUENCES:
  - User makes purchase decisions on false information
  - Legal liability for advertised prices
  - Trust erosion when user discovers mismatch
```

---

## Phase 3: Map to Evaluation Dimensions

For each failure code, assign a primary dimension and optional secondary:

```
Code: "Hallucinated Pricing"
  Primary: Accuracy
  Secondary: Safety (financial harm)
  Weight: 1.5× (accuracy dimension default)

Code: "RTL Input Direction Drift"
  Primary: Completeness
  Secondary: Instruction Following
  Weight: 1.2× (completeness dimension default)
```

### Standard Dimension Weights

| Dimension | Default Weight | Rationale |
|-----------|---------------|-----------|
| Safety | 2.0× | Highest priority — user harm |
| Accuracy | 1.5× | Factual correctness critical |
| Bias | 1.5× | Fairness and equity |
| Instruction Following | 1.3× | Agent must obey constraints |
| Completeness | 1.2× | All parts of query addressed |
| Quality | 1.0× | Baseline coherence |
| Tone | 0.8× | Important but not blocking |
| Brand Relevance | 0.8× | Style over substance |

---

## Output

After pattern discovery, you have:
- **Codebook** — All failure codes with definitions, types, exemplars
- **Category mapping** — Codes grouped by evaluation dimension
- **Paradigm models** — Causal analysis for each major failure
- **Dimension weights** — Severity-informed priority ordering

This feeds into Requirements Generation (`requirements-generation.md`).
