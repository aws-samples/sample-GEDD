# GEDD — find what your AI agent gets wrong

You shipped a product powered by AI Agents. Now you have to tell your CEO whether it's good enough — and if it isn't, tell engineering exactly what to fix. The agent fails in ways no rubric anticipated, and the eval tools your team installed expect you to know what to measure before you've seen what breaks.

GEDD is the tool for *before* you have a rubric.

> **The eval pipeline is the product. The agent is just the thing it produces.**


📖 **Read the why:** [Why Grounded Theory? for reliable AI Agents](https://balachanderkeelapudi.substack.com/p/why-grounded-theory-for-reliable) — the long-form argument behind this repo.

---

## What you do in GEDD

Six steps. Define → Prompt → **Deploy** → Test → Judge → Ship. A conversational coach guides you through each one. No YAML, no SDK, no Python.

1. **Define your agent.** What it's for, who uses it, what it should do.
2. **Write a system prompt** with the coach's help — the agent's character, rules, and constraints.
3. **Deploy to AgentCore.** Your agent is live. Everything after this tests the *real thing*.
4. **Generate golden test queries** — happy path, edge cases, adversarial, ambiguous. Run them against the live agent. The coach proposes; you keep what fits.
5. **Annotate & judge.** Mark each response ✓ / ⚠ / ✗. Name the failure patterns in your own words — "coverage hallucination," "missed escalation," "bad faith underexplain." GEDD turns those names into a deployable judge.
6. **Export & redeploy.** Golden dataset, judge prompt, and updated agent — all shipped together.

That's it. The whole flow takes about 90 minutes for a real agent with 15–20 golden queries. The first 30 minutes get you to "I now know my agent's top 3 failure modes." Most teams stop there and ship.

> **Why deploy before testing?** The deployed agent is stateless — it only needs the system prompt from Step 2. By deploying early, your golden queries are tested against the *real endpoint* (latency, IAM, cold starts), not a local mock. If the prompt needs changes, redeployment is one command.

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

---

## Try it before you commit to it

The home page has **17 one-click demo scenarios** — no LLM calls needed. Each is pre-loaded with golden queries, human annotations, error codes, a paradigm model, and a generated judge. Walk the entire pipeline in 5 minutes.

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
| **InsureBot** | Insurance claims (ShieldPoint) | Bad-faith denial, coverage hallucination, state regulation miss |
| **PropBot** | Real estate (NestKey Realty) | Fair Housing steering, fabricated comps, disclosure miss |
| **RxBot** | Pharmacy (PharmaLink) | Drug interaction miss, dosage unit confusion (mg vs mcg), off-label promotion |
| **TaxBot** | Tax/accounting (FileSmart) | Deduction hallucination, entity misguidance, Circular 230 violation |
| **ClaimsBot** | Defense contracting (AeroGuard) | ITAR violation, CUI spillage, foreign national access error |
| **FoodBot** | Food safety (SafePlate) | Allergen cross-contact miss, HACCP temp error, anaphylaxis delay |
| **AutoBot** | Automotive (DrivePulse Motors) | Lemon law omission, FTC CARS Rule violation, odometer fraud miss |
| **MigrateBot** | Immigration (PathForward Legal) | Asylum deadline miss, unauthorized practice, bar misapplication |
| **EnergyBot** | Energy/utilities (GridSync) | Solar ITC outdated (§25D terminated), NEM 3.0 confusion, DC voltage safety |

Load any scenario and explore every tab — Eval, Tag, Root Causes, Build Judge, Report — all pre-populated.

---

## Why this works

Most eval tools ask: *what should we measure?* — then build rubrics from assumptions. GEDD asks: *what is actually happening?* — then builds the rubric from evidence.

- **You can't evaluate what you haven't observed.** Pre-baked rubrics miss the failures unique to your agent.
- **Criteria should be weighted by evidence.** A bereavement-handling failure isn't the same severity as a tone slip.
- **Your evaluation evolves with the agent.** New patterns surface as you ship; the methodology absorbs them naturally.
- **Your work becomes load-bearing.** The judge GEDD generates is in *your* domain vocabulary, not a generic "helpfulness 1-5."

The methodology under the hood is grounded theory — the same discipline social scientists use to find patterns in human data. We use it to find patterns in agent failures. The full mapping lives in [METHODOLOGY.md](METHODOLOGY.md).

---

## What it's not

- **Not a tracing or observability tool.** It doesn't ingest live production traces. Bring your traces (paste them in, or run queries through GEDD itself).
- **Not a metric library.** No pre-built "faithfulness," "hallucination index," or 20-evaluator zoo. You discover your metrics; the tool makes them deployable.
- **Not a one-shot rubric generator.** It's a workflow, not a button. Plan ~90 minutes the first time.

---

## For engineers: CLI and Claude Code skills

The web UI is built for PMs. If you'd rather stay in the terminal, there are two engineer-native paths that produce the same outputs — a Claude Code skill that runs the full pipeline conversationally, and a standalone CLI for scripting and CI.

Both read and write the same `session.json` file, so you can switch between them freely mid-session.

### Claude Code skills

#### `/gedd` — full pipeline in one conversation

```bash
cd grounded-evals
claude        # opens Claude Code CLI
```

```
/gedd
```

Claude reads `session.json` if it exists and resumes where you left off. The full 6-step pipeline runs inside the conversation:

```
Step 1  Define Agent        Name, capabilities, target users, domain → saved to session.json
Step 2  System Prompt       Draft and refine collaboratively → saved to session.json
Step 3  Deploy              Deploy to Amazon Bedrock AgentCore → live endpoint ready
Step 4  Golden Queries      Open Coding: fracture domain → generate queries in batches
                            Run against the LIVE agent. Coverage table after every batch:

                            Saturation: happy_path 3/3 ✓ | edge_case 2/3 ~ | adversarial 1/3 ✗
                            Overall: 1/7 categories saturated (14%)

Step 5  Annotate & Judge    Shows each Q/A pair, collects ✓/⚠/✗ + error codes,
                            generates G-Eval judge prompt with weighted criteria
Step 6  Export & Redeploy   Golden dataset + judge exported, agent redeployed with guardrails
```

Type `quit` at any point — state is saved after every turn.

#### `/gedd-status` — session dashboard

```
/gedd-status
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GEDD Session Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Agent      : TravelBot
  Step       : 4 / 6  (Eval)
  Session    : session.json

  ── Golden Queries ──────────────────────────
  happy_path        █████   5   ✓ saturated
  edge_case         ███░░   3   ✓ saturated
  adversarial       ███░░   3   ✓ saturated

  ── What's next ─────────────────────────────
  Run evaluation → grounded-evals eval
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### CLI commands

| Command | What it does |
|---------|-------------|
| `chat` | Conversational coaching — Steps 1-4; shows live coverage table after each query batch |
| `eval` | Run golden queries against a model, stream responses |
| `annotate` | Mark responses correct / partial / incorrect; shows error code hints and running tally |
| `analyze` | Map error codes to 8 standard eval dimensions (`--llm` for LLM-based rationale) |
| `judge` | Generate a judge prompt — `--style geval` (chain-of-thought) or `--style standard` |
| `status` | Session dashboard — agent, step, coverage bars, annotations, error codes, what's next |
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

<details>
<summary><strong>Multiple agents</strong></summary>

Both paths support `--session` to keep separate files per agent:

```bash
grounded-evals chat     --session travelbot.json
grounded-evals eval     --session travelbot.json
grounded-evals annotate --session travelbot.json
grounded-evals export   --session travelbot.json --format jsonl
```

</details>

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

---

## Guides and further reading

| Guide | What it covers |
|-------|---------------|
| [Cohen's Kappa for LLM Judges](grounded-evals/docs/cohens-kappa-for-llm-judges.md) | What κ is, how to compute it, how to interpret it, and how to iterate your rubric until κ ≥ 0.80 |
| [Building an LLM-as-a-Judge](grounded-evals/docs/building-llm-as-a-judge.md) | Full rubric design, weighting, hard-fail rules, few-shot calibration, and export |
| [Domain Expert Guide](grounded-evals/docs/domain-expert-guide.md) | End-to-end walkthrough of all 5 steps for PMs and SMEs |
| [PM Artifacts → Production Judge](grounded-evals/docs/pm-to-ml-llm-judge.md) | Step-by-step guide for ML engineers: turn golden queries, annotations, and codebook into a calibrated CI judge |

For AWS Bedrock setup, environment variables, deployment, project structure, and contribution guidelines, see [SETUP.md](SETUP.md).

---

## ⭐ Found this useful?

If GEDD helped you find what your agent gets wrong, **[a star](https://github.com/aws-samples/sample-GEDD)** helps others find it too.

---

## Support and license

Security issues: see [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications).

License: MIT-0. See [LICENSE](LICENSE).
