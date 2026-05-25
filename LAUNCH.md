# GEDD Launch Playbook

## Pre-Launch Checklist

- [ ] Set GitHub Topics (Settings → Topics): `llm-evaluation`, `ai-agents`, `ai-testing`, `prompt-engineering`, `grounded-theory`, `eval-framework`, `amazon-bedrock`, `python`, `ai-quality`, `product-management`
- [ ] Record 15-second GIF of eval flow (query → responses → ✓/⚠/✗ → codes emerge)
- [ ] Verify one-click demo works without login (http://localhost:8080, click TravelBot demo)
- [ ] Set repo description: "Find what your AI agent gets wrong — before you have a rubric. Qualitative eval for PMs."

---

## Show HN Post

**Title:**
```
Show HN: GEDD – Find what your AI agent gets wrong before you write a rubric
```

**URL:** `https://github.com/aws-samples/sample-GEDD`

**First comment (post immediately after submitting):**

---

Hi HN — I built this because I kept watching PMs struggle with the same problem: they shipped an AI agent, now they need to tell their CEO whether it's good enough, and the eval tools expect them to already know what to measure.

The problem with existing eval tools (Promptfoo, DeepEval, Ragas, etc.) is they ask "what should we measure?" and then build rubrics from assumptions. But you can't evaluate what you haven't observed. Pre-baked rubrics like "helpfulness 1-5" miss the failures unique to YOUR agent — "policy hallucination," "missed escalation," "tone collapse under hostility."

GEDD is the tool for *before* you have a rubric. It uses grounded theory (the same methodology social scientists use to find patterns in human data) to find patterns in agent failures.

The workflow takes ~90 minutes:
1. Define your agent with a conversational coach
2. Generate golden test queries (happy path, edge cases, adversarial)
3. Run them side-by-side across up to 3 models, mark ✓/⚠/✗
4. Name the failure patterns in your own words
5. GEDD turns those names into a deployable judge prompt

The first 30 minutes get you to "I now know my agent's top 3 failure modes." Most teams stop there and ship.

There's a one-click demo on the home page (TravelBot) that loads a complete pre-coded session — no LLM calls, no AWS account needed. You can see the whole pipeline in 5 minutes.

Tech: Python/NiceGUI, runs against Amazon Bedrock (Claude, Nova, Llama, Mistral). Works locally with just an Anthropic API key too.

Happy to answer questions about the methodology, the architecture, or why I think "the eval pipeline is the product and the agent is just the thing it produces."

---

## Reddit Posts

### r/LocalLLaMA (practical angle)

**Title:** I built an open-source tool that finds what your AI agent gets wrong — before you write eval rubrics

**Body:** [Same as HN first comment, but add:] It's fully open source (MIT-0), runs locally, and works with any Bedrock model or direct Anthropic API. No cloud dependency required for the core workflow.

### r/MachineLearning (methodology angle)

**Title:** [P] Applying Grounded Theory (qualitative research methodology) to LLM agent evaluation

**Body:** We adapted grounded theory — the methodology social scientists use to discover patterns in qualitative data — for finding failure modes in AI agents. Instead of starting with pre-defined rubrics, you observe failures first, name them in your domain vocabulary, then build evaluation criteria from evidence. The tool (GEDD) implements the full open coding → axial coding → paradigm model → judge generation pipeline. Paper-length writeup: [link to substack]. Code: [link to repo].

---

## Awesome List Submissions

### awesome-llm (submit PR)
```markdown
- [GEDD](https://github.com/aws-samples/sample-GEDD) - Qualitative evaluation framework that discovers AI agent failure modes using grounded theory methodology, then generates deployable judge prompts.
```

### awesome-ai-agents (submit PR)
```markdown
- [GEDD](https://github.com/aws-samples/sample-GEDD) - Find what your AI agent gets wrong before you have a rubric. Guided workflow for PMs: observe failures → name patterns → generate judges.
```

### awesome-evaluation (submit PR)
```markdown
- [GEDD](https://github.com/aws-samples/sample-GEDD) - Open-source qualitative eval framework. Discovers failure modes via grounded theory, generates LLM-as-a-Judge prompts calibrated to your domain vocabulary.
```

---

## Newsletter Submissions

- **TLDR AI** (tldr.tech/ai) — submit via their form
- **The Batch** (deeplearning.ai) — email submissions
- **AI Engineering Weekly** — submit via GitHub
- **Last Week in AI** — submit via their form

**Pitch (1 sentence):** "GEDD is an open-source tool that helps PMs find what their AI agent gets wrong before they write eval rubrics — using grounded theory methodology to discover failure modes and generate deployable judges."

---

## Launch Day Timeline (Pick a Tuesday or Wednesday)

| Time (PT) | Action |
|-----------|--------|
| 8:00 AM | Post Show HN + first comment |
| 8:05 AM | Tweet with demo GIF from personal account |
| 8:10 AM | LinkedIn post (targets PMs and eng managers) |
| 12:00 PM | Reddit r/LocalLLaMA post |
| 2:00 PM | Reddit r/MachineLearning post |
| Day 2 | Dev.to tutorial cross-post |
| Day 3 | Submit to awesome lists |
| Day 3-5 | Submit to newsletters |

**Critical:** Respond to EVERY HN comment for 48 hours. This is the #1 ranking factor.

---

## Post-Launch (Week 2+)

- [ ] Submit to AWS Open Source Blog
- [ ] Submit re:Invent 2026 CFP (workshop session)
- [ ] Create Discord server
- [ ] Add "good first issue" labels to 5-10 issues
- [ ] Write comparison post: "GEDD vs Promptfoo vs DeepEval: when to use what"
