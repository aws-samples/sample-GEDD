# Conference Talk

## Title

Grounded Evidence Driven Development Approach for Product Managers and Domain Experts building AI Agents

---

## Abstract

Every product manager knows the cardinal rule: understand the problem before building the solution. We don't ship features based on assumptions — we talk to customers, observe behavior, and validate that we're solving a real problem. Yet when it comes to evaluating AI agents, the entire industry skips the problem space and jumps straight to solution-space artifacts: assumed rubrics, borrowed scoring criteria, and generic taxonomies that no one validated against real failures.

This is the most expensive mistake in AI agent development. You're measuring your agent against criteria you *imagined* rather than criteria you *discovered*. It's the evaluation equivalent of building a Segway — technically impressive, solving a problem nobody actually has.

**Grounded Evidence Driven Development (GEDD)** is a problem-space framework for AI evaluation — purpose-built for product managers and domain experts who need to curate golden datasets for their AI products. It applies the same discipline you already use in product discovery (observe → understand → validate → build) to the problem of evaluating AI agents. Using qualitative research techniques from social science (Open Coding, Axial Coding, and the Paradigm Model), GEDD keeps you in the problem space until you've *earned the right* to write a rubric — by observing real agent behavior, inductively coding failure patterns from data, and mapping the causal relationships that explain why your agent fails under specific conditions.

The people who know the domain — not the engineers writing the code — are the ones who must curate what "good" looks like. A golden dataset built by someone who doesn't deeply understand the customer's context, language, and edge cases is just a collection of guesses wearing a spreadsheet. GEDD gives domain experts a structured, repeatable methodology to translate their expertise into golden datasets that actually reflect how users interact with the product and where the agent breaks down.

> **The core insight:** A rubric is a solution-space artifact. A golden dataset is only as good as the problem-space work behind it. The people closest to your users (PMs and domain experts) are the ones who should be curating evaluation data for their AI products — not engineers guessing at failure modes from the outside.

## In this talk, you'll learn:

- Why AI evaluation is a **problem-space activity** disguised as a solution-space artifact — and why skipping the problem space produces golden datasets that test what's easy to imagine rather than what's hard to discover
- How **Open Coding** (from Grounded Theory) is the evaluation equivalent of customer discovery — letting domain experts observe real agent outputs and inductively name failure patterns in their own words, grounded in their expertise about what users actually need
- How **Axial Coding's Paradigm Model** maps the causal structure of failures (triggers, contexts, consequences) — giving domain experts a structured canvas to document *why* the agent fails in ways that matter to their specific product and users
- How to build golden datasets that achieve **theoretical saturation** — not "enough seems good" but a rigorous, domain-expert-driven process that ensures every critical user scenario, edge case, and failure mode your product faces is represented
- How your **human annotations** become the ground truth that bridges problem space (observed failures) to solution space (automated judge) — domain expertise encoded as evaluation criteria, not lost in a handoff to engineering
- A live demo: from raw agent outputs → domain-expert annotation → failure codebook → paradigm model → auto-generated rubric — the full problem-to-solution pipeline, driven by the people who know the product best

## You'll leave with:

A repeatable problem-space framework that gives product managers and domain experts the structured methodology to curate golden datasets and own AI agent evaluation for their products — from discovering how your agent actually fails in your domain, to understanding *why* it fails, to building the automated judge grounded in what you observed rather than what you assumed. Your domain expertise becomes the evaluation criteria. Your observations become the golden dataset. Problem space first — always.
