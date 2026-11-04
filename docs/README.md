# GEDD documentation

Start with the [latest findings](../FINDINGS.md), then pick a path by flywheel stage or by role.

## By flywheel stage

| Stage | Read |
|---|---|
| **1 · Evidence**: cases, expert labels, failure codebook | [Methodology: open and axial coding](methodology.md) · [Domain expert guide](guides/domain-expert-guide.md) · [Paste in traces](guides/paste-in-traces.md) |
| **2 · Measure**: locked set, paired tests | [Findings log and the GEDD bar](../FINDINGS.md) · [Cohen's kappa for LLM judges](guides/cohens-kappa-for-llm-judges.md) · `grounded-evals stats compare` |
| **3 · Improve**: harness, SFT, DPO, RL | [Invoice case study](../experiments/docile-invoices/) · [Round-2 roadmap](../experiments/docile-invoices/docs/roadmap-sft-dpo-gedd.md) · [LoRA explained](../experiments/docile-invoices/docs/lora-explained.md) |
| **Reward model** | [README: the reward model](../README.md#the-gedd-flywheel) · [Research positioning](research.md) · `grounded-evals reward score` |
| **4 · Guard**: response gate | [Building an LLM-as-Judge](guides/building-llm-as-a-judge.md) · [PM to ML judge handoff](guides/pm-to-ml-llm-judge.md) · [Launch checklist](guides/launch-checklist.md) |
| **5 · Production**: traces, PPI, new codes | [Pipeline guide](guides/pipeline-guide.md) · `grounded-evals stats ppi` |

## By role

| Role | Start here |
|---|---|
| Domain expert | [Domain expert guide](guides/domain-expert-guide.md) → [a worked judge for your domain](judges/) |
| Product manager | [Findings](../FINDINGS.md) → [Why accuracy is worth money](../experiments/docile-invoices/docs/market-and-why-accuracy.md) → [Launch checklist](guides/launch-checklist.md) |
| ML engineer | [Setup](setup.md) → [Pipeline guide](guides/pipeline-guide.md) → [Invoice experiments](../experiments/docile-invoices/) |
| Researcher | [Research positioning](research.md) → [Findings log](../FINDINGS.md) |

## Everything else

| Folder | Contents |
|---|---|
| [`judges/`](judges/) | Worked LLM-as-Judge write-ups for 17 domains (claims, clinical, Rx, tax, legal, HR, energy and more) |
| [`blog/`](blog/) | Articles on GEDD for different audiences |
| [`talks/`](talks/) | Conference talk material |
| [`setup.md`](setup.md) | Install, configure a model provider, run locally or deploy the app |
