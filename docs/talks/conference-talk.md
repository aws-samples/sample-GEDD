# Conference Talk

## Title

Keeping Your AI Product's Taste While You Build with Agents: Grounded Evidence Driven Development for Product Managers and Domain Experts

---

## Abstract

Every model swap, prompt change, agent-framework change, fine-tune and RL run is optimised against *something*. If that something is generic (a generic LLM judge, a proxy reward, a public benchmark, "be accurate"), your product drifts toward generic model behaviour, and the aggregate score hides it. That is how an AI product loses its taste: not in one bad release, but quietly, one well-scored change at a time.

Product managers already know the cure from product discovery: understand the problem before building the solution. Yet in AI evaluation the industry skips the problem space and jumps to solution-space artifacts: assumed rubrics, borrowed scoring criteria and generic taxonomies no one validated against real failures. You end up measuring your agent against criteria you *imagined* rather than criteria you *discovered*.

**Grounded Evidence Driven Development (GEDD)** keeps the product's standard in the hands of the people who hold it. Domain experts observe real agent outputs, name the failures in their own words and rank them by severity, using qualitative research techniques from social science (Open Coding, Axial Coding and the Paradigm Model). The result is a **failure codebook**: the named, severity-ranked list of ways your product must never fail, such as a subtitle that drops `{player_name}` or an invoice total taken before commission. GEDD turns that one list into your eval, your RL reward and your response gate, so every change is held to your standard.

That codebook, with its labelled cases, severity weights and calibrated judge, is also your moat. A competitor can use the same base model; they can't copy your experts' evidence, and it grows every round as production surfaces new failures.

> **The core insight:** A rubric is a solution-space artifact. Your product's taste lives in the problem-space work behind it. The people closest to your users (PMs and domain experts) should define what good and unacceptable look like, not engineers guessing at failure modes from the outside, and certainly not a generic judge.

## In this talk, you'll learn:

- Why AI evaluation is a **problem-space activity** disguised as a solution-space artifact, and how generic criteria let taste erode silently. Example from the repo's own evidence: prompting traded invented values for missed ones while the headline score barely moved.
- How **Open Coding** (from Grounded Theory) is the evaluation equivalent of customer discovery: domain experts observe real agent outputs and inductively name failure patterns in their own words
- How **Axial Coding's Paradigm Model** maps the causal structure of failures (triggers, contexts, consequences), giving experts a structured canvas to document *why* the agent fails and how much each failure costs
- How to build golden datasets that reach **theoretical saturation**: not "enough seems good" but a rigorous, expert-driven process that covers every critical scenario, edge case and failure mode
- How the codebook becomes the **reward and the gate**, and why a reward audit before RL matters: in the repo's invoice study, every proxy reward paid some degenerate policy (abstaining everywhere, guessing blindly, dumping candidates), while the GEDD reward paid none. Reward hacking is taste loss: the score goes up while the product gets worse.
- A live demo: from raw agent outputs → domain-expert annotation → failure codebook → paradigm model → auto-generated rubric, the full problem-to-solution pipeline, driven by the people who know the product best

## You'll leave with:

A repeatable framework that keeps your AI product's taste as you build with agents: make the standard explicit with your experts, measure against it by failure code, train toward it, enforce it at the response gate, and grow it as production surfaces new failures. Your domain expertise becomes the eval, the reward and the gate. Problem space first, always.
