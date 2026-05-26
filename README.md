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

## For engineers: CLI and Claude Code skills

The web UI is built for PMs. If you'd rather stay in the terminal, there are two engineer-native paths that produce the same outputs — a Claude Code skill that runs the full pipeline conversationally, and a standalone CLI for scripting and CI.

Both read and write the same `session.json` file, so you can switch between them freely mid-session.

---

### Claude Code skills

#### `/gedd-chat` — full pipeline in one conversation

Open Claude Code in the project directory and run `/gedd-chat`. No separate credentials, no REPL, no extra process — Claude acts as both coach and executor.

```bash
cd grounded-evals
claude        # opens Claude Code CLI
```

```
/gedd-chat
```

Claude reads `session.json` if it exists and resumes where you left off. The full 7-step pipeline runs inside the conversation:

```
Step 1  Define Agent        Name, capabilities, target users → saved to session.json
Step 2  System Prompt       Draft and refine collaboratively → saved to session.json
Step 3  Golden Queries      Open Coding: fracture domain → generate queries in batches
                            Live coverage table shown after every approved batch:

                            Coverage snapshot  (12 queries)
                              happy_path      ███░░   3   ✓ saturated
                              edge_case       ██░░░   2   ~ approx.
                              adversarial     █░░░░   1   ✗ thin
                              ambiguous       ░░░░░   0   ✗ none

Step 4  Eval                Runs grounded-evals eval inline via Bash — no CLI switch needed
Step 5  Annotation          Shows each Q/A pair in conversation, collects c/p/i + error codes,
                            writes annotations to session.json in real time
Step 6  Error Analysis      Groups error codes (Open Coding), maps to 8 standard dimensions
                            (accuracy, tone, safety, completeness, ...), builds paradigm model
Step 7  Judge Prompt        Generates deployable LLM-as-a-Judge prompt grounded in your
                            observed failures → saves to judge_prompt.md, exports dataset
```

Type `quit` at any point — state is saved after every turn.

---

#### `/gedd-status` — session dashboard

Check where you are without entering the coaching conversation:

```
/gedd-status
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GEDD Session Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Agent      : TravelBot
  Step       : 4 / 7  (Eval)
  Session    : session.json

  ── Golden Queries ──────────────────────────

  Total: 15 queries across 5 categories

  happy_path        █████   5   ✓ saturated
  edge_case         ███░░   3   ✓ saturated
  adversarial       ███░░   3   ✓ saturated
  ambiguous         ██░░░   2   ~ approx.
  multi_turn        ██░░░   2   ~ approx.

  Overall saturation: 3 / 5 categories ✓  (60%)

  ── Annotations ─────────────────────────────

  Total: 8 annotated
    ✓ correct     5  (63%)
    ⚠ partial     2  (25%)
    ✗ incorrect   1  (12%)

  Error codes found:
    hallucination     ×2   → accuracy
    wrong_tone        ×1   → tone

  ── What's next ─────────────────────────────

  7 responses left to annotate — run /gedd-chat

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Standalone CLI (Path B)

Use this when scripting, running in CI, or working without Claude Code.

**1. Install and set credentials**

```bash
cd grounded-evals
source .venv/bin/activate

export ANTHROPIC_API_KEY=sk-ant-…  # easiest for local dev
# OR configure AWS credentials for Bedrock (IAM, us-east-1)
```

**2. Run the coaching session**

```bash
grounded-evals chat
```

A conversational LLM coach guides you through Steps 1-4. Type `quit` to exit — progress is saved to `session.json` and resumes on the next run.

```
New GEDD session. State will be saved to: session.json
Type 'quit' to exit.

Coach: Hi! Let's build a golden evaluation dataset for your AI agent.
       What's the agent's name, and what does it do?

You: ▌
```

**3. Run queries against the model**

```bash
grounded-evals eval
# target a specific model:
grounded-evals eval --model us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Streams each query and agent response to stdout. Saves results to `eval_results.json`.

**4. Annotate responses**

```bash
grounded-evals annotate
```

```
──── [1/15] ────────────────────────────────
Category : happy_path
Query    : Where is my order #12345?
Expected : Return real-time order status with tracking link
Response : Your order #12345 is currently in transit...

Annotation [c/p/i/s]: ▌
```

Keys: `c` correct · `p` partial · `i` incorrect · `s` skip.
For failures, prompts for an error code and a note.

**5. Export**

```bash
grounded-evals export --format jsonl   # one query per line — feeds into eval pipelines
grounded-evals export --format csv     # shareable spreadsheet
grounded-evals export --format json    # full Pydantic model dump with all metadata
```

Output defaults to `<agent_name>_golden_dataset.<fmt>`.

---

### Multiple agents

Both paths support `--session` to keep separate files per agent:

```bash
grounded-evals chat     --session travelbot.json
grounded-evals eval     --session travelbot.json
grounded-evals annotate --session travelbot.json
grounded-evals export   --session travelbot.json --format jsonl
```

---

### All CLI commands

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
