# GEDD Methodology — Evidence-Driven LLM Judge + SPEC Generation

GEDD is a systematic evidence-driven framework that combines LLM-as-a-Judge evaluation with structured SPEC generation in a continuous learning lifecycle. This document covers the academic depth — grounded theory foundations, calibration statistics, and generation techniques — for product leaders, researchers, and engineers who need to defend the approach in a design review.

The practical product guide lives in [README.md](README.md).

---

## The mapping

GEDD applies three phases of Strauss & Corbin's grounded theory to LLM evaluation and spec generation:

| Grounded Theory Concept | GEDD Implementation |
|---|---|
| **Open Coding** — fracturing data into concepts | Break agent domain into testable categories, discover error codes inductively |
| **Constant Comparison** — comparing each datum to existing | Each new query compared against existing set for uniqueness |
| **Theoretical Saturation** — stop when no new concepts emerge | Stop adding queries when categories are fully covered |
| **Axial Coding** — relating categories via Paradigm Model | Map errors to causal conditions, context, consequences |
| **Selective Coding** — identifying core category | Central failure phenomenon becomes primary eval criterion |
| **Memos** — researcher's documented rationale | PM documents reasoning behind each annotation |

---

## Phase 1: Open Coding

The inductive discovery phase. You break the agent's domain into testable pieces, then observe what actually happens.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1e3a5f', 'primaryTextColor': '#e2e8f0', 'primaryBorderColor': '#4a7fa5', 'lineColor': '#64b5f6', 'secondaryColor': '#1a3a2a', 'tertiaryColor': '#2d2a1a'}}}%%
flowchart TD
    subgraph Fracture["1. Domain Fracturing"]
        AS[Agent Spec<br/><i>name, capabilities, users</i>] --> FD[fracture_domain]
        FD --> CAT[8-15 Categories<br/><i>happy-path, edge cases,<br/>adversarial, multi-turn...</i>]
        CAT --> CODES[Codes<br/><i>exemplar prompts per category</i>]
    end

    subgraph Golden["2. Golden Query Construction"]
        CODES --> GQ[PM Writes Queries]
        GQ --> CC{Constant<br/>Comparison}
        CC -->|Unique| ADD[Add to Dataset]
        CC -->|Redundant| SKIP[Skip / Revise]
        ADD --> SAT{Saturation<br/>Check}
        SAT -->|Gaps Remain| GQ
        SAT -->|Saturated| DONE[Golden Dataset Complete]
    end

    subgraph Observe["3. Observation"]
        DONE --> EVAL[Run Against Models]
        EVAL --> ANN[PM Annotates<br/>✓ Correct  ⚠ Partial  ✗ Incorrect]
        ANN --> ERR[Error Codes Emerge<br/><i>in-vivo from failures</i>]
    end

    style Fracture fill:#1a3a2a,stroke:#27a644,color:#a7f3c1
    style Golden fill:#2d2a1a,stroke:#d4a017,color:#fde68a
    style Observe fill:#1a2a3a,stroke:#4a7fa5,color:#93c5fd
```

### Key concepts

- **In-vivo codes** — Named in the PM's own words from observed failures (e.g., "hallucinated pricing")
- **Constructed codes** — AI-suggested labels for patterns (e.g., "context_window_overflow")
- **Properties & dimensions** — Each category varies along axes (complexity: low↔high, tone: casual↔formal)
- **Saturation** — A category is saturated when ≥3 prompts cover it and no new patterns emerge

### Saturation states

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1e3a5f', 'primaryTextColor': '#e2e8f0'}}}%%
stateDiagram-v2
    [*] --> UNSATURATED: < 2 prompts
    UNSATURATED --> APPROACHING: 2 prompts
    APPROACHING --> SATURATED: ≥ 3 prompts
    SATURATED --> [*]: No new concepts emerging

    note right of UNSATURATED: Keep adding queries
    note right of APPROACHING: Almost there
    note right of SATURATED: Move to next category
```

---

## Phase 2: Axial Coding

Connects the error patterns you discovered into a causal model. Answers: *why* do failures happen?

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1e3a5f', 'primaryTextColor': '#e2e8f0', 'primaryBorderColor': '#4a7fa5', 'lineColor': '#64b5f6', 'secondaryColor': '#1a3a2a', 'tertiaryColor': '#2d1f3d'}}}%%
flowchart TD
    subgraph Input["Discovered Error Codes"]
        E1[hallucinated_pricing]
        E2[ignored_constraints]
        E3[tone_mismatch]
        E4[incomplete_response]
    end

    subgraph Mapping["Error → Category Mapping"]
        E1 --> M[map_errors_to_categories]
        E2 --> M
        E3 --> M
        E4 --> M
        M --> D1[accuracy]
        M --> D2[instruction_following]
        M --> D3[tone]
        M --> D4[completeness]
    end

    subgraph Paradigm["Paradigm Model"]
        D1 --> PM[build_paradigm_model]
        D2 --> PM
        D3 --> PM
        D4 --> PM
        PM --> MODEL
    end

    subgraph MODEL["Strauss & Corbin Paradigm Model"]
        CC[Causal Conditions<br/><i>What triggers failures?</i>]
        PH[Phenomenon<br/><i>Central failure pattern</i>]
        CTX[Context<br/><i>When does it happen?</i>]
        IC[Intervening Conditions<br/><i>What makes it worse/better?</i>]
        AS2[Action Strategies<br/><i>How to address it?</i>]
        CON[Consequences<br/><i>What's the impact?</i>]

        CC --> PH
        CTX --> PH
        IC --> PH
        PH --> AS2
        AS2 --> CON
    end

    style Input fill:#2d2a1a,stroke:#d4a017,color:#fde68a
    style Mapping fill:#1a2a3a,stroke:#4a7fa5,color:#93c5fd
    style Paradigm fill:#2d1f3d,stroke:#a855f7,color:#e9d5ff
    style MODEL fill:#3a1a2a,stroke:#ec4899,color:#fbcfe8
```

### The 8 standard evaluation dimensions

Errors map to these categories:

| Dimension | What it measures |
|---|---|
| **Quality** | Overall response quality and coherence |
| **Accuracy** | Factual correctness, no hallucinations |
| **Brand Relevance** | Alignment with brand voice and guidelines |
| **Bias** | Fairness, no discriminatory patterns |
| **Safety** | No harmful, dangerous, or inappropriate content |
| **Completeness** | All parts of the query addressed |
| **Tone** | Appropriate register and style |
| **Instruction Following** | Adherence to constraints and directives |

---

## Phase 3: Selective Coding (Judge Builder)

Transforms the qualitative analysis into a deployable automated judge — using ML research techniques grounded in your own annotations.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1e3a5f', 'primaryTextColor': '#e2e8f0', 'primaryBorderColor': '#4a7fa5', 'lineColor': '#64b5f6', 'secondaryColor': '#1a3a2a', 'tertiaryColor': '#2d1f3d'}}}%%
flowchart TD
    subgraph Inputs["From Axial Coding"]
        EM[Error Mappings<br/><i>errors → 8 dimensions</i>]
        PM[Paradigm Model<br/><i>causal relationships</i>]
        ANN[Human Annotations<br/><i>coded examples + severity</i>]
    end

    subgraph Build["Judge Construction — 3 ML Modes"]
        EM --> RUB[generate_rubric<br/><i>paradigm-enriched criteria</i>]
        PM --> RUB
        RUB --> RUBRIC[Judge Rubric<br/><i>weighted by severity</i>]

        RUBRIC --> STD[Standard Judge<br/><i>zero-shot rubric</i>]
        ANN --> FS[Few-Shot Judge<br/><i>Prometheus-style<br/>Kim et al. 2023</i>]
        RUBRIC --> FS
        RUBRIC --> GE[G-EVAL Judge<br/><i>chain-of-thought<br/>Liu et al. 2023</i>]
        ANN --> CONST[Constitutional Judge<br/><i>principle-by-principle<br/>Bai et al. 2022</i>]
        PM --> CONST
    end

    subgraph Calibrate["Calibration + Active Learning"]
        STD & FS & GE & CONST --> RUN[Judge Scores Responses]
        RUN --> ENS[Ensemble / Self-Consistency<br/><i>Wang et al. 2023</i>]
        ENS --> CAL[Cohen's Kappa Calibration<br/><i>weighted κ + 95% CI</i>]
        HUMAN[Human PM Scores] --> CAL
        CAL --> AGR{κ ≥ 0.80?}
        AGR -->|Yes| DEPLOY[Deploy Judge ✓]
        AGR -->|No| AL[Active Learning<br/><i>margin sampling → next<br/>annotations to collect</i>]
        AL --> ANN
    end

    style Inputs fill:#2d1f3d,stroke:#a855f7,color:#e9d5ff
    style Build fill:#1a3a2a,stroke:#27a644,color:#a7f3c1
    style Calibrate fill:#2d2a1a,stroke:#d4a017,color:#fde68a
```

### ML techniques and citations

| Technique | Paper | What it does |
|---|---|---|
| **Few-Shot / Prometheus** | Kim et al. 2023 | Injects your highest-confidence annotated examples into the judge prompt — the model sees what a Policy Hallucination looks like before evaluating. Typical κ improvement: +0.15–0.25. |
| **G-EVAL Chain-of-Thought** | Liu et al. 2023 | Forces step-by-step reasoning per criterion (structured sub-questions) before scoring. Reduces anchoring bias and improves inter-rater reliability. |
| **Constitutional AI** | Bai et al. 2022, Anthropic | Converts each error code into an independent principle. Judge checks each principle sequentially — no overall-score anchoring. Produces per-principle verdicts traceable to your Open Coding. |
| **Self-Consistency Ensemble** | Wang et al. 2023 | Runs the same judge N times at temperature 0.7, aggregates via majority vote (binary) / median score (rubric). Identifies borderline responses where the judge disagrees with itself. |
| **Active Learning** | Settles 2009 | Margin sampling: finds responses whose judge score is closest to the 3.5 pass/fail boundary — highest information gain for the next annotation round. Also reports coverage gaps per error code. |
| **Cohen's Weighted Kappa** | Cohen 1968 | Replaces naive agreement % with a statistically principled inter-rater measure. Weighted κ accounts for ordinal distance (a score-diff of 4 is penalised more than 1). Reports 95% CI and per-criterion breakdown. |

### Generated rubric structure

Each criterion is enriched with Paradigm Model context and severity-weighted:

```
5 — Excellent: No issues observed in this dimension
4 — Good: Minor issues, core value delivered
3 — Acceptable: Noticeable issues but functional
2 — Poor: Significant issues matching observed error patterns (root causes embedded)
1 — Failing: Critical failure — e.g., Policy Hallucination, Data Fabrication
```

Dimension weights reflect real-world severity:

| Dimension | Weight |
|---|---|
| Safety | 2.0× |
| Accuracy / Bias | 1.5× |
| Instruction Following | 1.3× |
| Completeness | 1.2× |
| Quality | 1.0× |
| Tone / Brand Relevance | 0.8× |

The judge outputs structured JSON:

```json
{
  "scores": {"accuracy": 4, "completeness": 3, "tone": 5},
  "justifications": {"accuracy": "Minor imprecision in...", ...},
  "overall_score": 4.0,
  "pass": true,
  "confidence": "high",
  "summary": "Response meets criteria with minor accuracy gap."
}
```

---

## Why grounded theory?

Most eval frameworks ask: *"What should we measure?"* — then build rubrics from assumptions.

Grounded Theory asks: *"What is actually happening?"* — then builds theory from evidence.

This matters because:

1. **You can't evaluate what you haven't observed.** Assumed rubrics miss failure modes unique to your agent.
2. **Criteria should be weighted by evidence.** Not all dimensions matter equally for every agent.
3. **Evaluation evolves.** As your agent improves, new failure patterns emerge; the methodology handles this naturally.
4. **Calibration proves validity.** If your judge agrees with human annotators ≥85% of the time, your grounded criteria are working.

---

## The grounded evals flywheel

```mermaid
flowchart TD
    A["🧑‍💼 DOMAIN EXPERTS + PMs
    Collaborative qualitative coding"]
    B["🔍 OPEN CODING
    Discover failure patterns
    inductively from agent output"]
    C["🔗 AXIAL CODING
    Map causes, contexts,
    strategies, consequences"]
    D["📋 RUBRIC GENERATION
    Observable criteria from
    empirical failure patterns"]
    E["✨ GOLDEN DATASET
    Human-annotated ground truth
    with inter-annotator agreement"]
    F["⚖️ LLM-AS-JUDGE
    Calibrated against humans
    Scalable automated eval"]
    G["📡 PRODUCTION MONITORING
    Detect drift, new patterns"]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G -->|"feeds back"| B

    style A fill:#1565c0,stroke:#0d47a1,color:#fff
    style B fill:#1976d2,stroke:#1565c0,color:#fff
    style C fill:#1e88e5,stroke:#1976d2,color:#fff
    style D fill:#2196f3,stroke:#1e88e5,color:#fff
    style E fill:#42a5f5,stroke:#2196f3,color:#fff
    style F fill:#64b5f6,stroke:#42a5f5,color:#fff
    style G fill:#90caf9,stroke:#64b5f6,color:#1a1a1a
```

> **The flywheel never stops.** Production monitoring surfaces new failure patterns that feed back into Open Coding — your evaluation evolves as your agent evolves.

---

## Further reading

- Strauss, A. & Corbin, J. (1990). *Basics of Qualitative Research: Grounded Theory Procedures and Techniques.*
- Hamel Husain, [Field Guide to AI Evals](https://hamel.dev/blog/posts/field-guide).
- Eugene Yan, [Evaluation & Hallucination Detection](https://eugeneyan.com/writing/evals/).
- Shankar et al. 2024, [Who Validates the Validators? Aligning LLM-Assisted Evaluation of LLM Outputs with Human Preferences](https://arxiv.org/abs/2404.12272).

---

For the engineering setup (AWS Bedrock, environment variables, project structure, deployment), see [SETUP.md](SETUP.md). For the user-facing tour, see [README.md](README.md).
