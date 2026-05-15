# GEDD — Grounded Eval-Driven Development

**Build LLM evaluation judges grounded in real observed failures, not assumptions.**

GEDD applies [Grounded Theory](https://en.wikipedia.org/wiki/Grounded_theory) — a rigorous qualitative research methodology — to the problem of evaluating AI agents. Instead of inventing rubrics from guesses about what might go wrong, you discover evaluation criteria inductively from what *actually* goes wrong.

---

## The Problem

Traditional LLM evaluation starts with assumed rubrics: "check for helpfulness, accuracy, safety." But how do you know those are the right criteria for *your* agent? How do you weight them? What failure modes are you missing?

GEDD flips this: **observe first, theorize second.**

---

## How It Works — The GEDD Pipeline

```mermaid
flowchart TD
    A[Define Agent Spec] --> B[Fracture Domain]
    B --> C[Write Golden Queries]
    C --> D[Run Eval Against Models]
    D --> E[Annotate Responses]
    E --> F[Discover Error Patterns]
    F --> G[Map Causal Relationships]
    G --> H[Generate Rubric]
    H --> I[Generate Judge Prompt]
    I --> J[Calibrate Judge vs Human]
    J -->|Low Agreement| K[Refine & Iterate]
    K --> E
    J -->|High Agreement| L[Deploy Automated Judge]

    style A fill:#e8f5e9
    style B fill:#e8f5e9
    style C fill:#e8f5e9
    style D fill:#fff3e0
    style E fill:#fff3e0
    style F fill:#e3f2fd
    style G fill:#e3f2fd
    style H fill:#fce4ec
    style I fill:#fce4ec
    style J fill:#fce4ec
    style L fill:#c8e6c9
```

---

## Qualitative Research Methodology

GEDD maps three phases of Grounded Theory to LLM evaluation:

```mermaid
flowchart LR
    subgraph GT["Grounded Theory"]
        OC[Open Coding] --> AC[Axial Coding] --> SC[Selective Coding]
    end

    subgraph GEDD["GEDD Application"]
        OC2[Discover Failure<br/>Patterns] --> AC2[Map Causal<br/>Relationships] --> SC2[Build Automated<br/>Judge]
    end

    OC -.->|maps to| OC2
    AC -.->|maps to| AC2
    SC -.->|maps to| SC2

    style GT fill:#f3e5f5
    style GEDD fill:#e8f5e9
```

| Grounded Theory Concept | GEDD Implementation |
|---|---|
| **Open Coding** — fracturing data into concepts | Break agent domain into testable categories, discover error codes |
| **Constant Comparison** — comparing each datum to existing | Each new query compared against existing set for uniqueness |
| **Theoretical Saturation** — stop when no new concepts emerge | Stop adding queries when categories are fully covered |
| **Axial Coding** — relating categories via Paradigm Model | Map errors to causal conditions, context, consequences |
| **Selective Coding** — identifying core category | Central failure phenomenon becomes primary eval criterion |
| **Memos** — researcher's documented rationale | PM documents reasoning behind each annotation |

---

## Phase 1: Open Coding

Open Coding is the inductive discovery phase. You break the agent's domain into testable pieces, then observe what actually happens.

```mermaid
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

    style Fracture fill:#e8f5e9
    style Golden fill:#fff3e0
    style Observe fill:#e3f2fd
```

### Key Concepts

- **In Vivo Codes** — Named in the PM's own words from observed failures (e.g., "hallucinated pricing")
- **Constructed Codes** — AI-suggested labels for patterns (e.g., "context_window_overflow")
- **Properties & Dimensions** — Each category varies along axes (complexity: low↔high, tone: casual↔formal)
- **Saturation** — A category is saturated when ≥3 prompts cover it and no new patterns emerge

### Saturation Model

```mermaid
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

Axial Coding connects the error patterns you discovered into a causal model. It answers: *why* do failures happen?

```mermaid
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

    style Input fill:#fff3e0
    style Mapping fill:#e3f2fd
    style Paradigm fill:#f3e5f5
    style MODEL fill:#fce4ec
```

### The 8 Standard Evaluation Dimensions

Errors are mapped to these categories:

| Dimension | What It Measures |
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

## Phase 3: Judge Builder (Selective Coding)

The final phase transforms your qualitative analysis into a deployable automated judge.

```mermaid
flowchart TD
    subgraph Inputs["From Axial Coding"]
        EM[Error Mappings<br/><i>errors → 8 dimensions</i>]
        PM[Paradigm Model<br/><i>causal relationships</i>]
    end

    subgraph Build["Judge Construction"]
        EM --> RUB[generate_rubric]
        PM --> RUB
        RUB --> RUBRIC[Judge Rubric<br/><i>criteria + 5-point scales</i>]
        RUBRIC --> GEN[generate_judge_prompt]
        GEN --> PROMPT[Judge System Prompt<br/><i>deployable LLM-as-Judge</i>]
    end

    subgraph Calibrate["Calibration Loop"]
        PROMPT --> RUN[Judge Scores Responses]
        RUN --> CAL[calibrate]
        HUMAN[Human PM Scores] --> CAL
        CAL --> AGR{Agreement<br/>≥ 85%?}
        AGR -->|Yes| DEPLOY[Deploy Judge ✓]
        AGR -->|No| REFINE[Refine Rubric]
        REFINE --> RUB
    end

    style Inputs fill:#f3e5f5
    style Build fill:#e8f5e9
    style Calibrate fill:#fff3e0
```

### Generated Rubric Structure

Each criterion gets a 5-point scoring scale grounded in observed failures:

```
5 — Excellent: No issues observed
4 — Good: Minor issues, acceptable
3 — Adequate: Some issues, borderline
2 — Poor: Significant issues matching observed error patterns
1 — Failing: Critical failures (e.g., hallucinated_pricing, ignored_constraints)
```

The judge outputs structured JSON:
```json
{
  "scores": {"accuracy": 4, "completeness": 3, "tone": 5},
  "justifications": {"accuracy": "Minor imprecision in...", ...},
  "overall_score": 4.0,
  "pass": true,
  "summary": "Response meets criteria with minor accuracy gap."
}
```

---

## Architecture

```mermaid
flowchart TD
    subgraph UI["NiceGUI Web App"]
        HOME[Home Page]
        COACH[Coach Chat]
        EVAL[Eval Runner]
        CODING[Open Coding Workbench]
        ANALYSIS[Axial Coding Canvas]
        REPORT[Report & Export]
    end

    subgraph Core["Core Engine"]
        OC[open_coding<br/><i>fracture, compare, saturation</i>]
        AX[axial_coding<br/><i>mapper, paradigm</i>]
        JB[judge_builder<br/><i>rubric, prompt_gen, calibrate</i>]
        LLM[llm/client<br/><i>Bedrock + Anthropic</i>]
    end

    subgraph Agent["Agent Runtime"]
        LOCAL[Local Agent<br/><i>handler + tools + prompt</i>]
        REMOTE[AgentCore<br/><i>coach + evaluator</i>]
    end

    subgraph Infra["AWS Infrastructure"]
        ECS[ECS Fargate]
        COG[Cognito]
        ECR[ECR]
        AC[AgentCore]
    end

    UI --> Core
    UI --> Agent
    Core --> LLM
    Agent --> LLM
    LOCAL -.->|or| REMOTE
    ECS --> ECR
    COG --> ECS
    AC --> REMOTE

    style UI fill:#e8f5e9
    style Core fill:#e3f2fd
    style Agent fill:#fff3e0
    style Infra fill:#fce4ec
```

---

## Quick Start

```bash
cd grounded-evals

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run the app
python -m grounded_evals.app
```

The app runs at `http://localhost:8080`.

### Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8080` |
| `AWS_REGION` | Bedrock region | `us-west-2` |
| `ANTHROPIC_MODEL` | Default model | `claude-haiku-4-5-20250315` |
| `AGENTCORE_AGENT_ID` | Remote agent ID (optional) | — |
| `ADMIN_PASSWORD` | Fallback auth password | — |
| `LANGSMITH_API_KEY` | Tracing (optional) | — |

---

## Project Structure

```
grounded-evals/
├── src/grounded_evals/
│   ├── open_coding/        # Phase 1: Discover patterns
│   │   ├── fracture.py     #   Domain → categories + codes
│   │   ├── compare.py      #   Constant comparison method
│   │   └── saturation.py   #   Theoretical saturation checks
│   ├── axial_coding/       # Phase 2: Relate patterns
│   │   ├── mapper.py       #   Errors → 8 standard dimensions
│   │   └── paradigm.py     #   Build Paradigm Model
│   ├── judge_builder/      # Phase 3: Build judge
│   │   ├── rubric.py       #   Generate scoring rubric
│   │   ├── prompt_gen.py   #   Generate judge system prompt
│   │   └── calibrate.py    #   Human vs judge agreement
│   ├── agent/              # Conversational coach
│   │   ├── handler.py      #   Tool-use loop
│   │   ├── tools.py        #   6 coaching tools
│   │   └── prompt.py       #   Coach system prompt
│   ├── ingest/             # Input parsing
│   │   ├── parser.py       #   YAML agent spec parser
│   │   └── models.py       #   AgentSpec, Capability, Persona
│   ├── models/core.py      # All data models (Pydantic)
│   ├── ui/                 # NiceGUI pages
│   └── app.py              # App entry point
├── agentcore/              # AWS AgentCore runtime
├── infra/                  # CDK infrastructure
├── configs/                # Example YAML specs
└── tests/
```

---

## Deployment

Infrastructure is defined with AWS CDK:

```bash
cd infra
pip install -r requirements.txt
cdk deploy --all
```

Stacks: Network (VPC) → ECR → ECS Fargate (UI) → Cognito (auth) → AgentCore (agent runtime)

---

## Why Grounded Theory?

Most eval frameworks ask: "What should we measure?" — then build rubrics from assumptions.

Grounded Theory asks: "What is actually happening?" — then builds theory from evidence.

This matters because:
1. **You can't evaluate what you haven't observed** — Assumed rubrics miss failure modes unique to your agent
2. **Criteria should be weighted by evidence** — Not all dimensions matter equally for every agent
3. **Evaluation evolves** — As your agent improves, new failure patterns emerge; the methodology handles this naturally
4. **Calibration proves validity** — If your judge agrees with human annotators ≥85% of the time, your grounded criteria are working

---

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
