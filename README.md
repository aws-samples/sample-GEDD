# GEDD — find what your AI agent gets wrong

[![CI](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml/badge.svg)](https://github.com/aws-samples/sample-GEDD/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT-0](https://img.shields.io/badge/License-MIT--0-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/aws-samples/sample-GEDD?style=social)](https://github.com/aws-samples/sample-GEDD/stargazers)

You shipped a product powered by AI Agents. Now you have to tell your CEO whether it's good enough — and if it isn't, tell engineering exactly what to fix. The agent fails in ways no rubric anticipated, and the eval tools your team installed expect you to know what to measure before you've seen what breaks.

GEDD is the tool for *before* you have a rubric.

> **The eval pipeline is the product. The agent is just the thing it produces.**

![GEDD demo — query → responses → annotate → codes emerge → judge](grounded-evals/docs/GEDD_optimized.gif)


📖 **Read the why:** [Why Grounded Theory? for reliable AI Agents](https://balachanderkeelapudi.substack.com/p/why-grounded-theory-for-reliable) — the long-form argument behind this repo.

---

## What you do in GEDD

Five steps, a conversational coach guiding you through each one. No YAML, no SDK, no Python.

1. **Define your agent.** What it's for, who uses it, what it should do.
2. **Write a system prompt** with the coach's help.
3. **Generate golden test queries** — happy path, edge cases, adversarial, ambiguous. The coach proposes; you keep what fits.
4. **Run them, watch what breaks.** Side-by-side across up to 3 models. Mark each response ✓ / ⚠ / ✗.
5. **Name the failure patterns in your own words** — "policy hallucination," "missed escalation," "tone collapse under hostility." GEDD turns those names into a deployable judge that engineering can wire into CI.

That's it. The whole flow takes about 90 minutes for a real agent with 8–12 golden queries. The first 30 minutes get you to "I now know my agent's top 3 failure modes." Most teams stop there and ship.

---

## Why this works

Most eval tools ask: *what should we measure?* — then build rubrics from assumptions. GEDD asks: *what is actually happening?* — then builds the rubric from evidence.

This matters because:

- **You can't evaluate what you haven't observed.** Pre-baked rubrics miss the failures unique to your agent.
- **Criteria should be weighted by evidence.** Not every dimension matters equally. A bereavement-handling failure isn't the same severity as a tone slip.
- **Your evaluation evolves with the agent.** New patterns surface as you ship; the methodology absorbs them naturally.
- **Your work becomes load-bearing.** The judge GEDD generates is in *your* domain vocabulary, not a generic "helpfulness 1-5." When you hand it to engineering, they can use it.

The methodology under the hood is grounded theory — the same discipline social scientists use to find patterns in human data. We use it to find patterns in agent failures. The full mapping (open coding, axial coding, paradigm model, ML techniques, calibration) lives in [METHODOLOGY.md](METHODOLOGY.md). You don't need to read it to use the tool.

---

## What it's not

- **Not a tracing or observability tool.** It doesn't ingest live production traces. Bring your traces (paste them in, or run queries through GEDD itself).
- **Not a metric library.** No pre-built "faithfulness," "hallucination index," or 20-evaluator zoo. You discover your metrics; the tool makes them deployable.
- **Not a one-shot rubric generator.** It's a workflow, not a button. Plan ~90 minutes the first time.

---

## Try it before you commit to it

The home page has eight one-click demo scenarios, each pre-loaded with golden queries, human annotations, error codes, a paradigm model, and a generated judge — no LLM calls needed. You can walk the entire pipeline in 5 minutes.

| Demo | Domain | Key failure modes |
|------|--------|------------------|
| **TravelBot** | Flight booking (SkyLink Travel) | Hallucinated entities, fabricated booking data, confident confabulation |
| **ClinicalBot** | Clinical triage (MedPulse Health) | Missed escalation, contraindication miss, overconfident diagnosis |
| **LexBot** | Legal assistant (Lexara Law Suite) | Jurisdiction error, unauthorized legal advice, statute misquote |
| **WealthBot** | Financial planning (PrimeWealth) | Unlicensed advice, projection hallucination, risk misclassification |
| **HRBot** | HR policy Q&A (TalentPulse) | Policy misquote, confidentiality breach, discriminatory guidance |
| **EduBot** | Student learning (Athena Learning) | Answer reveal, grade inflation, curriculum mismatch |
| **VaultEx AI** | Crypto exchange (VaultEx) | Regulatory misguidance, fee hallucination, wallet security gaps |
| **PixelGuard** | Gaming moderation (NexusGames) | False positive bans, harassment miss, appeals mishandling |

Load any scenario and explore every tab — Eval, Tag, Root Causes, Build Judge, Report — all pre-populated.

---

## Quick start

```bash
cd grounded-evals
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m grounded_evals.app
```

Open `http://localhost:8080` — TravelBot loads automatically, no login required. Click through the tabs to explore the full pipeline.

To run against your own agent you'll need AWS credentials (Bedrock) or an `ANTHROPIC_API_KEY`. Set `ADMIN_PASSWORD=your-password` to enable the login wall for shared deployments.

For AWS Bedrock setup, environment variables, deployment, project structure, and contribution guidelines, see [SETUP.md](SETUP.md).

---

## For engineers: CLI and Claude Code skill

The web UI is built for PMs. If you'd rather stay in the terminal, there are two engineer-native paths that produce the same outputs.

Both write to a `session.json` file. They interoperate — start in the skill, finish in the CLI, or mix freely.

---

### Path A — `/gedd-chat` Claude Code skill

The fastest way to generate a golden dataset if you already have Claude Code installed. No credentials, no REPL, no separate process — Claude itself acts as the coach.

**1. Open Claude Code in the project**

```bash
cd grounded-evals
claude
```

**2. Start a new session or resume an existing one**

```
/gedd-chat
```

Claude reads `session.json` if it exists and picks up where you left off. Otherwise it starts fresh and asks for your agent's name.

**3. Have the conversation**

Claude walks you through all four steps — defining your agent, writing a system prompt, and generating golden queries using Open Coding methodology. Each approved query is written to `session.json` automatically.

**4. Hand off to the CLI for eval and export**

When Step 3 is complete, the skill tells you to switch to the terminal:

```bash
grounded-evals eval        # run queries, see responses
grounded-evals annotate    # mark each response correct / partial / incorrect
grounded-evals export      # write JSONL, CSV, or JSON
```

---

### Path B — standalone CLI

Use this when you want to run the full pipeline without Claude Code, or when scripting / CI is involved.

**1. Install and set credentials**

```bash
cd grounded-evals
source .venv/bin/activate          # or: python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

export ANTHROPIC_API_KEY=sk-ant-…  # easiest for local dev
# OR configure AWS credentials for Bedrock (IAM, us-east-1)
```

**2. Run the coaching session**

```bash
grounded-evals chat
```

A conversational coach guides you through the same four steps. Type `quit` to exit — progress is saved to `session.json` and you can resume any time.

```
New GEDD session. State will be saved to: session.json
Type 'quit' to exit.

Coach: Hi! I'm your GEDD coaching assistant. Let's build a golden
       evaluation dataset for your AI agent. What's the agent's name,
       and what does it do?

You: ▌
```

**3. Run queries against the model**

```bash
grounded-evals eval
# or target a specific model:
grounded-evals eval --model us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Prints each query and the agent's response. Saves everything to `eval_results.json`.

**4. Annotate responses**

```bash
grounded-evals annotate
```

Steps through each response one at a time:

```
──── [1/12] ────────────────────────────────
Category : happy_path
Query    : Where is my order #12345?
Expected : Return real-time order status with tracking link
Response : Your order #12345 is currently in transit...

Annotation [c/p/i/s]: ▌
```

Keys: `c` correct · `p` partial · `i` incorrect · `s` skip.
For failures, it asks for an error code (`hallucination`, `wrong_tone`, `missed_escalation` — whatever fits) and a note.

**5. Export the golden dataset**

```bash
grounded-evals export --format jsonl   # one query per line — feeds into eval pipelines
grounded-evals export --format csv     # shareable spreadsheet
grounded-evals export --format json    # full metadata dump
```

Output filename defaults to `<agent_name>_golden_dataset.<fmt>`.

---

### Working with multiple agents

Both paths support a `--session` flag so you can keep separate files per agent:

```bash
grounded-evals chat     --session travelbot.json
grounded-evals eval     --session travelbot.json
grounded-evals annotate --session travelbot.json
grounded-evals export   --session travelbot.json --format jsonl
```

---

### All CLI commands at a glance

| Command | What it does |
|---------|-------------|
| `chat` | Conversational coaching — Steps 1-4, saves to `session.json` |
| `eval` | Run golden queries against a model, save responses |
| `annotate` | Interactively mark responses correct / partial / incorrect |
| `export` | Write golden dataset as JSONL, CSV, or JSON |
| `fracture` | Fracture an agent spec YAML into test categories (Open Coding) |
| `check-saturation` | Check whether a dataset has reached theoretical saturation |
| `coverage` | Show a bar-chart coverage breakdown by category |
| `compare` | Check whether a new prompt adds unique coverage to a dataset |
| `serve` | Start the web UI |

```bash
grounded-evals --help          # all commands
grounded-evals chat --help     # options for a specific command
```

---

## How it actually feels

```
[ Home ]            One-click demos + your saved sessions
   ↓
[ Coach ]           Conversational. Define agent, system prompt,
                    golden queries — guided by an AI coach.
   ↓
[ Eval ]            Run queries against models. Mark ✓ / ⚠ / ✗.
   ↓
[ Tag Failures ]    Annotate what failed and why, in your own words.
                    Codes accumulate in a sidebar.
   ↓
[ Map Root Causes ] Drag your codes onto a paradigm canvas: causes,
                    contexts, consequences. Optional but useful.
   ↓
[ Build Judge ]     Generate a deployable judge prompt. Calibrate it
                    against your own scoring (κ ≥ 0.80). Export.
```

The whole product is one screen at a time, one question at a time. PMs who hate forms find this less painful than it looks.

---

## Guides and further reading

| Guide | What it covers |
|-------|---------------|
| [Cohen's Kappa for LLM Judges](grounded-evals/docs/cohens-kappa-for-llm-judges.md) | What κ is, how to compute it, how to interpret it, and how to iterate your rubric until κ ≥ 0.80 |
| [Building an LLM-as-a-Judge](grounded-evals/docs/building-llm-as-a-judge.md) | Full rubric design, weighting, hard-fail rules, few-shot calibration, and export |
| [Domain Expert Guide](grounded-evals/docs/domain-expert-guide.md) | End-to-end walkthrough of all 5 steps for PMs and SMEs |
| [PM Artifacts → Production Judge](grounded-evals/docs/pm-to-ml-llm-judge.md) | Step-by-step guide for ML engineers: turn golden queries, annotations, and codebook into a calibrated CI judge |

---

## ⭐ Found this useful?

If GEDD helped you find what your agent gets wrong, **[a star](https://github.com/aws-samples/sample-GEDD)** helps others find it too.

---

## Support and license

Security issues: see [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications).

License: MIT-0. See [LICENSE](LICENSE).
