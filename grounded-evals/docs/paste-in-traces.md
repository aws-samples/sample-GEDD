# Paste-in trace mode — design doc

**Status:** proposal · **Owner:** TBD · **Last updated:** 2026-05-23

## TL;DR

Add a second entry point to GEDD: a textarea on the home page that accepts 20+ pasted agent transcripts (or a CSV upload). Within 60 seconds, the user sees auto-suggested open codes against the pasted data, with a one-click path to refine in the existing `/coding` workbench. The `/coach` flow stays untouched as the guided onboarding for users who don't have data yet.

## The user this serves

The PM who already has data — exported from LangSmith, Braintrust, a CSV someone forwarded them, or copy-pasted from Slack threads — and wants to *find patterns*, not *define an agent from scratch*. Today, GEDD forces them through a 4-step Coach wizard before they see a single trace. That's wrong shape for someone who has the artifact in hand.

This is the same JTBD as Dovetail's "raw → structured" promise, applied to AI traces. Hamel Husain's field guide identifies friction-removal as the #1 enabler of error analysis: *"You must remove all friction from the process of looking at data."*

## Riskiest assumption (test before building)

**That the user already has traces in a portable format.** If the most common reality is "my traces live behind a SOC2-restricted internal tool I can't paste from," paste-in is dead and we need an integration (LangSmith importer, Braintrust importer). Validate via the user interview script (see `interview-script.md`) — specifically Q4: *"Show me where your traces live right now."*

## Flow

1. **Entry.** Home page gets a primary CTA card: *"Already have transcripts? Paste them →"* (sits next to the existing "Load Demo Data" buttons but is more prominent).
2. **Paste screen.** Single textarea, accepts:
   - One trace per double-newline-separated block: `User: ...\nAssistant: ...`
   - JSONL: one `{"query": ..., "response": ...}` per line
   - CSV upload (drag-drop), columns `query,response`
   - LangSmith CSV export (auto-detect column names: `inputs.input`, `outputs.output`)
3. **Parse + preview.** Show the parsed pairs as a list ("12 traces detected — looks right?"). One click to confirm.
4. **Auto-suggest open codes.** Send all traces to Bedrock with a single prompt that asks Claude to identify 5–10 candidate failure patterns *in PM language* (not "hallucination" — "stated price without checking"). Pre-tag each trace with the candidate code that best fits. Latency target: <60s for 20 traces.
5. **Land in `/coding`.** Drop the user into the existing annotation workbench with codes pre-populated and traces queued. They review, rename, merge, delete — same as the post-Coach flow.
6. **Optional reverse-engineer.** A button at the top: *"Generate the agent definition from these traces."* This back-fills `agent_spec` in the session so `/synthesize` and `/report` work normally. Skips the Coach entirely. Reverse-engineering is best-effort; the user can edit.

## Data model

The existing `coding_annotations` and `codebook` shapes already match what we need. The only new persistent state:

```python
storage["pasted_traces"] = [
    {"id": "pt-uuid", "query": "...", "response": "...", "source": "paste|csv|jsonl|langsmith"},
    ...
]
```

These feed `_build_responses()` in `coding_page.py:13` exactly the way `eval_results` already does. Zero schema migration; one new branch in the helper.

## What this is NOT

- **Not an integration with LangSmith / Braintrust APIs.** That's a future bet. Paste-in is the unauthenticated, no-SDK, no-API-key entry. The integration version comes if paste-in proves the demand.
- **Not a tracing tool.** GEDD does not ingest live traces. The user pastes finished trace pairs. The "instrument your agent with our SDK" path is explicitly out of scope (see synthesis doc).
- **Not a replacement for `/coach`.** Coach stays. It's the right flow for "I'm thinking about building an agent" or "I want to write golden queries before I run anything." Paste-in serves "I already shipped, here's the bug pile."

## Wedge against competitors

| Tool | Has paste-in? | Auto-codes traces? | PM-shaped? |
|---|---|---|---|
| LangSmith | No (SDK only) | No | No |
| Braintrust | No (SDK only) | No | No |
| Athina | No (SDK + dashboard) | Cluster, not theorize | Yes |
| Dovetail | Yes (transcripts) | Yes | Yes — but not for AI traces |
| **GEDD + paste-in** | **Yes** | **Yes (grounded-theory framing)** | **Yes** |

Paste-in turns GEDD from "I'll build my eval pipeline" into "I'll review my agent's mistakes" — same product, much wider top-of-funnel.

## Phases

**v0.1 (1-2 days):** Textarea + double-newline parser + drop into `/coding` with no auto-codes. Validates the entry-point bet alone.

**v0.2 (3-5 days):** CSV upload + LangSmith column auto-detect + Bedrock auto-coding pass with a one-shot prompt.

**v0.3:** "Reverse-engineer agent definition" button. JSONL parser. Better dedup of near-identical traces.

## Open questions

1. **How many traces should we accept in one paste?** Auto-coding 200 traces may take >2 minutes. Paginate the auto-coding pass, or cap at 50?
2. **Show codes inline as they're being generated?** Streaming UX vs. wait-then-show. Streaming feels faster even when it isn't.
3. **What happens if the user pastes traces in 3 batches?** Codes from batch 1 should auto-suggest for batch 2 (don't reinvent). Means the auto-coding prompt needs the existing codebook as input from batch 2 onward.

## Success metric

Time-to-first-tagged-failure for a paste-in user, measured from "land on home" to "first annotation saved." Target: under 90 seconds for 20 pasted traces. Compare against the same metric for the Coach flow (today: ~5–10 minutes minimum).
