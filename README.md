# GEDD — find what your AI agent gets wrong

<img width="1176" height="710" alt="GEDD coach screenshot" src="https://github.com/user-attachments/assets/6cbd262f-6158-41d4-898e-6ad98b4c668a" />

**A Qualitative Analysis research Framework for Product Managers and Domain experts building AI Products.**

---

You shipped an AI agent. Now you have to tell your CEO whether it's good enough — and if it isn't, tell engineering exactly what to fix. The agent fails in ways no rubric anticipated, and the eval tools your team installed expect you to know what to measure before you've seen what breaks.

GEDD is the tool for *before* you have a rubric.

> **The eval pipeline is the product. The agent is just the thing it produces.**

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

- **Not a tracing or observability tool.** It doesn't ingest live production traces. Bring your traces (paste them in, or run queries through GEDD itself). LangSmith, Braintrust, Langfuse cover ingestion better.
- **Not a metric library.** No pre-built "faithfulness," "hallucination index," or 20-evaluator zoo. You discover your metrics; the tool makes them deployable.
- **Not a one-shot rubric generator.** It's a workflow, not a button. Plan ~90 minutes the first time.

---

## Try it before you commit to it

The home page has a one-click demo using a TravelBot example. It loads a complete pre-coded session — golden queries, annotations, error codes, paradigm model, generated judge — without making any LLM calls. You can see the whole pipeline in 5 minutes before deciding whether to use it on your own agent.

A second demo loads a SupportBot (e-commerce customer support) with PII-leak hard-fail criteria, escalation failures, and unauthorized compensation patterns — closer to a real production agent.

---

## Quick start

```bash
cd grounded-evals
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export ADMIN_PASSWORD=your-password
python -m grounded_evals.app
```

Open `http://localhost:8080`, log in, click one of the demos. Walk through.

For AWS Bedrock setup, environment variables, deployment, project structure, and contribution guidelines, see [SETUP.md](SETUP.md).

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
[ Report ]          Generate a deployable judge prompt. Calibrate it
                    against your own scoring. Export.
```

The whole product is one screen at a time, one question at a time. PMs who hate forms find this less painful than it looks.

---

## Doing the user research

If you're considering using GEDD on your own product, the most useful first move is **5 user interviews with the PMs on your team** — to confirm GEDD's solo-PM workflow matches how your people actually work.

We've shipped a complete interview kit at [`grounded-evals/docs/research/`](grounded-evals/docs/research/) — recruiting profile, verbatim consent script, per-call notes template, scoring rubric, and a synthesis template. Run it before deciding to roll GEDD out widely.

---

## Support and license

Security issues: see [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications).

License: MIT-0. See [LICENSE](LICENSE).
