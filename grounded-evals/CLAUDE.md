# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product Vision & Value Proposition

**Agent Playground** is an AI Product Manager's tool for building golden evaluation datasets and performing qualitative error analysis on AI Agents. The product name is "Agent Playground — Powered by Grounded Eval Driven Development."

### Core Value Proposition (FOCUS HERE)

**The #1 value this product delivers:**
1. **Golden Eval Dataset Generation** — Systematically create comprehensive test queries for AI Agents using Open Coding methodology (not ad-hoc prompt writing)
2. **Qualitative Error Analysis** — Apply Open Coding + Axial Coding to identify, categorize, and map agent failure patterns to standard error codes
3. **Human-in-the-loop Annotation** — Domain experts annotate agent responses as correct/incorrect, providing ground truth for automated eval systems

These three capabilities are the product's reason to exist. All features should serve these purposes. Everything else is secondary.

### What Makes This Different

Traditional eval tools just run prompts and compare outputs. This product applies **Grounded Theory qualitative research methodology** to:
- Ensure test coverage is systematic and complete (not random)
- Discover failure patterns empirically from data (not assumed)
- Map errors to standardized categories with traceable rationale
- Build evaluation criteria grounded in real observations, not heuristics

## V1.0 Scope (Current Implementation)

The app is a **single conversational interface** where an LLM coach guides the PM through 4 steps:

1. **Define Agent** — name, capabilities, target users
2. **System Prompt** — collaboratively write and refine the agent's system prompt
3. **Golden Queries** — generate 10-20 diverse test queries using Open Coding (fracture domain into categories, vary dimensions, constant comparison for coverage)
4. **Error Analysis** — run queries against the agent, PM annotates responses with human feedback, identify failure patterns using Open Coding + Axial Coding

### UI Architecture (V1.0)

- **Conversational interface** — single chat input, LLM guides the PM step by step
- **Right sidebar** — shows accumulated outputs (Agent Definition, System Prompt, Golden Queries) with individual download buttons (JSON, TXT, CSV)
- **Progress tracker** — 4 dots showing current step, driven by LLM tool calls
- **Branded design** — Inter font, green gradient theme, polished SaaS feel (Linear/Notion vibes)
- **Non-technical PM audience** — simple, no jargon, one question at a time

### Key UX Decisions

- Conversational > forms (PMs prefer talking to an AI coach over filling out structured inputs)
- LLM uses tool calls to save data to session (save_agent_info, save_golden_query, set_current_step)
- Sidebar updates in real-time as data accumulates
- Each output section downloadable individually in appropriate format
- Confetti celebrations at query milestones (1st, 5th, 10th, 20th)

## High-Effort Features to Build (Golden Queries + Error Analysis)

### Golden Query Generation (Open Coding Applied)

This is the heart of the product. The LLM should:

1. **Fracture the domain** into 6-10 test categories based on the agent's capabilities:
   - Happy path (straightforward requests)
   - Edge cases (boundary conditions, unusual inputs)
   - Adversarial (attempts to misuse, jailbreak, confuse)
   - Ambiguous (unclear requests requiring clarification)
   - Multi-turn (context-dependent follow-ups)
   - Error recovery (agent fails, then user tries again)

2. **Vary dimensions** within each category:
   - Complexity: simple → compound
   - Tone: polite → frustrated → hostile
   - Specificity: vague → highly detailed
   - User expertise: novice → expert
   - Length: terse → verbose

3. **Constant comparison** — as each query is added, compare against existing set to ensure unique coverage (not redundant)

4. **Theoretical saturation** — indicate when new queries stop revealing new categories (PM has enough)

5. **Persona × Category matrix** — generate queries from different user personas at different categories for comprehensive coverage

### Error Analysis (Open Coding + Axial Coding)

After golden queries are written, the PM runs them against their agent and annotates:

**Open Coding phase:**
- Each agent response is labeled: correct, partially correct, incorrect
- Incorrect responses are "coded" — labeled with the type of failure
- Failure codes emerge from the data (not pre-defined): hallucination, wrong tone, missed context, safety violation, incomplete answer, etc.
- Constant comparison groups similar failures together

**Axial Coding phase:**
- Failure codes are organized via the Paradigm Model:
  - Causal Conditions → what triggers this failure?
  - Phenomenon → what is the failure pattern?
  - Context → under what conditions does it occur?
  - Intervening Conditions → what makes it worse/better?
  - Action Strategies → how does the agent respond (incorrectly)?
  - Consequences → what is the user impact?
- Failures mapped to standard dimensions: Quality, Accuracy, Brand Relevance, Bias, Safety, Completeness, Tone, Instruction Following
- This mapping directly produces LLM-as-a-Judge rubric criteria

### Human Annotation Interface

For error analysis, the PM needs to:
- See each golden query + agent response side by side
- Mark as: ✓ Correct | ⚠️ Partially Correct | ✗ Incorrect
- For incorrect: assign or create error codes
- Add free-text notes explaining WHY it failed
- These annotations become the training data for automated judges

## Technical Stack

- **UI**: NiceGUI (Python, Quasar/Material Design)
- **LLM**: Amazon Bedrock (IAM auth, model: `us.anthropic.claude-haiku-4-5-20251001-v1:0`)
- **Backend**: Python, Pydantic models, session state
- **Data persistence**: JSON/CSV file exports (V1.0), database later
- **Dev tools**: pytest, ruff, mypy

## LLM Configuration

- **Auth**: AWS IAM via boto3 credential chain (Cloud Desktop role)
- **Region**: us-east-1
- **Model**: `us.anthropic.claude-haiku-4-5-20251001-v1:0`
- **Fallback**: Set `ANTHROPIC_API_KEY` for direct Anthropic API access (local dev)
- **Tool use**: The conversational coach uses Claude tool calls (save_agent_info, save_golden_query, set_current_step) to persist data during conversation

## Commands

```bash
# Install
pip install -e ".[dev]"

# Run the app
python -m grounded_evals.app

# Run tests
pytest tests/

# Lint
ruff check src/ tests/
ruff format src/ tests/
```

## Architecture

```
src/grounded_evals/
├── app.py               # NiceGUI main app (conversational UI + sidebar)
├── models/core.py       # Pydantic data models
├── ingest/              # Agent spec parsing
├── open_coding/         # Fracturing, comparison, saturation
├── axial_coding/        # Paradigm model, error mapping
├── judge_builder/       # Rubric + judge prompt generation
├── guide/session.py     # Session state management
├── llm/client.py        # Bedrock client (IAM auth)
└── ui/                  # UI components (journey map, theme)
```

## Design Principles

- **Conversational first** — single chat input, LLM guides everything
- **PM-friendly** — no technical jargon, one question at a time, acknowledge before advancing
- **Playful & branded** — gradient backgrounds, Inter font, rounded cards, green theme, polished SaaS
- **Outputs sidebar** — live display of accumulated data with per-section downloads
- **Tool use for state** — LLM calls tools to save data; sidebar/progress update reactively
- **Open Coding methodology** — systematic, traceable, grounded in data not assumptions
