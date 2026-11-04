#!/usr/bin/env python3
"""GRPO on the GEDD invoice environment, with any reward from rl_env.py (vision LoRA, serverless).

The recipe, in the shape of an agentic-RL workshop:
  1 MODEL   the base vision-language model + a small LoRA; only the adapter trains
  2 TASK    read 10 key fields off one invoice page, return JSON (single turn)
  3 REWARD  --reward gedd (pay for the goal, charge severity) or a hackable proxy
  4 EVAL    the locked test set, scored by the fixed exact scorer, before and after
            (written to results/results_rl_<reward>_<tag>.jsonl, same format as every
            other system, so `08_rigor.py`-style tests and `grounded-evals stats compare` apply)

Every step logs *all* rewards, not just the one being optimised, plus the failure-code counts,
so reward hacking shows up as the trained reward rising while `exact` stalls and one code
(invented / missed) moves the wrong way.

Guards
  * leak-free training pool: no training document shares a layout cluster with the test set
  * headroom check: the share of groups whose tries differ (flat groups teach nothing)
  * budget: the run is estimated before any GPU time, and stops at --max-usd

UNTESTED AGAINST THE LIVE API in this repo. Run the smoke configuration first:
  DOCILE_MAX_SIDE=1344 uv run python 13_rl_grpo.py --reward gedd --smoke
Full run (~$19 per reward arm at list price; three arms for the hacking comparison):
  DOCILE_MAX_SIDE=1344 uv run python 13_rl_grpo.py --reward gedd --dry-run
  DOCILE_MAX_SIDE=1344 uv run python 13_rl_grpo.py --reward gedd
  DOCILE_MAX_SIDE=1344 uv run python 13_rl_grpo.py --reward no_invention
  DOCILE_MAX_SIDE=1344 uv run python 13_rl_grpo.py --reward coverage
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from statistics import fmean

import dl_common as d
import rl_env as env

BASE_MODEL = "accounts/fireworks/models/glm-5p3-flash"
TOKENIZER_MODEL = "zai-org/GLM-5.3-Flash"
RENDERER_NAME = "glm53_flash"
PRICE = {"prefill": 2.96, "sample": 7.41, "train": 8.89}  # USD per 1M tokens, serverless list price
PROMPT_TOKENS, COMPLETION_TOKENS = 2830, 220  # measured on the 1,344 px test pages


def estimate(a) -> dict[str, float]:
    episodes = a.steps * a.tasks * a.group
    eval_docs = 2 * a.eval_docs  # base + final
    est = {
        "rollout_prefill": a.steps * a.tasks * PROMPT_TOKENS * PRICE["prefill"] / 1e6,
        "rollout_sample": episodes * COMPLETION_TOKENS * PRICE["sample"] / 1e6,
        "train": episodes * (PROMPT_TOKENS + COMPLETION_TOKENS) * PRICE["train"] / 1e6,
        "eval": eval_docs * (PROMPT_TOKENS * PRICE["prefill"] + COMPLETION_TOKENS * PRICE["sample"]) / 1e6,
    }
    est["total"] = sum(est.values())
    return est


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--reward", default="gedd", choices=env.REWARDS)
    p.add_argument("--steps", type=int, default=18)
    p.add_argument("--tasks", type=int, default=4, help="training invoices per step")
    p.add_argument("--group", type=int, default=4, help="tries per invoice (GRPO group)")
    p.add_argument("--eval-docs", type=int, default=500, help="locked test documents scored before/after")
    p.add_argument("--lora-rank", type=int, default=16)
    p.add_argument("--learning-rate", type=float, default=1e-4)
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--max-seq-len", type=int, default=6144)
    p.add_argument("--adv-clip", type=float, default=2.0)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-usd", type=float, default=25.0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--smoke", action="store_true", help="1 step, 1 task, group 2, 5 eval docs")
    a = p.parse_args()
    if a.smoke:
        a.steps, a.tasks, a.group, a.eval_docs = 1, 1, 2, 5

    test = d.load_split("test")
    train = env.leak_free_train(d.load_split("train"), test)
    random.Random(a.seed).shuffle(train)
    eval_rows = test[: a.eval_docs]
    print(f"leak-free training pool: {len(train)} invoices from clusters absent from the test set; "
          f"eval: {len(eval_rows)} locked test invoices", flush=True)

    est = estimate(a)
    print("cost estimate USD: " + ", ".join(f"{k} {v:.2f}" for k, v in est.items()), flush=True)
    if est["total"] > a.max_usd:
        raise SystemExit(f"estimate ${est['total']:.2f} exceeds --max-usd {a.max_usd}")
    if a.dry_run:
        return

    import importlib

    from fireworks.training import sdk
    from fireworks.training.sdk import FiretitanServiceClient
    from training.renderer import get_text_content
    from training.renderer.tokenizer import get_tokenizer
    from training.utils.supervised import (
        build_multimodal_policy_datum,
        build_renderer,
        normalize_messages,
    )

    sft = importlib.import_module("04_sft")  # reuse its vision sampling-prompt builder
    tok = get_tokenizer(TOKENIZER_MODEL)
    renderer = build_renderer(tok, TOKENIZER_MODEL, RENDERER_NAME)
    stop = renderer.get_stop_sequences()

    run_id = time.strftime(f"rl-{a.reward}-%Y%m%d-%H%M%S")
    run_dir = d.HERE / "rl_logs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "args.json").write_text(json.dumps(vars(a), indent=2))
    log = (run_dir / "steps.jsonl").open("a")

    service = FiretitanServiceClient(api_key=os.environ["FIREWORKS_API_KEY"],
                                     base_url="https://api.fireworks.ai/training/v1/serverless")
    tc = service.create_lora_training_client(base_model=BASE_MODEL, rank=a.lora_rank, alpha=2 * a.lora_rank,
                                             train_mlp=True, train_attn=True, train_unembed=True)
    adam = sdk.AdamParams(learning_rate=a.learning_rate, beta1=0.9, beta2=0.95, eps=1e-12, weight_decay=0.0)

    def sampler_for(tag: str):
        path = tc.save_weights_for_sampler(f"{run_id}-{tag}").result().path
        return service.create_sampling_client(model_path=path, tokenizer=tok)

    def sample(sampler, row: dict, n: int, temperature: float):
        msgs = d.messages(row)
        prompt_ids, images = sft.sampling_prompt(renderer, tok, msgs)
        params = sdk.SamplingParams(max_tokens=a.max_tokens, temperature=temperature, stop=stop)
        res = sampler.sample(prompt=prompt_ids, num_samples=n, sampling_params=params, images=images).result()
        prompt_mi = renderer.build_generation_prompt(normalize_messages(msgs))
        out = []
        for seq in res.sequences:
            tokens = list(seq.tokens or [])
            text = get_text_content(renderer.parse_response(tokens)[0]) if tokens else ""
            out.append({"tokens": tokens, "logprobs": [float(x) for x in (seq.logprobs or [])], "text": text})
        return prompt_mi, out

    def is_datum(prompt_mi, tokens: list[int], logprobs: list[float], adv: float):
        """Importance-sampling datum that keeps the image chunks of the prompt."""
        base = build_multimodal_policy_datum(prompt_mi, tokens, max_seq_len=a.max_seq_len)
        target = list(base.loss_fn_inputs["target_tokens"].data)
        weights = list(base.loss_fn_inputs["weights"].data)
        resp = [i for i, w in enumerate(weights) if w > 0]
        if not resp or len(logprobs) < len(resp):
            return None
        lp = [0.0] * len(target)
        for i, v in zip(resp, logprobs[-len(resp):], strict=True):
            lp[i] = v
        n = len(target)
        return sdk.Datum(model_input=base.model_input, loss_fn_inputs={
            "target_tokens": sdk.TensorData(data=target, dtype="int64", shape=[n]),
            "logprobs": sdk.TensorData(data=lp, dtype="float32", shape=[n]),
            "advantages": sdk.TensorData(data=[adv * w for w in weights], dtype="float32", shape=[n]),
        })

    def evaluate(tag: str, sampler) -> dict:
        """Greedy single try on the locked eval documents, written in the standard results format."""
        path = d.results_path(f"rl_{a.reward}_{tag}")
        path.unlink(missing_ok=True)

        def one(row):
            try:
                _, outs = sample(sampler, row, 1, 0.0)
                text = outs[0]["text"]
            except Exception as e:  # noqa: BLE001
                return row, "", f"{type(e).__name__}: {e}"[:300]
            return row, text, None

        scores = []
        with ThreadPoolExecutor(8) as ex, path.open("w") as fh:
            for row, text, err in ex.map(one, eval_rows):
                pred = d.parse(text)
                s = env.score(row, pred)
                scores.append(s)
                fh.write(json.dumps({"doc": row["id"], "model": f"rl_{a.reward}_{tag}", "cluster": row["cluster"],
                                     "parsed": pred is not None, "fields": d.grade(row, pred), "text": text[-2000:],
                                     "error": err, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0,
                                     "latency_s": 0.0}) + "\n")
        summary = {r: fmean(s.reward[r] for s in scores) for r in env.REWARDS}
        summary.update({f"n_{c}": sum(s.counts[c] for s in scores) for c in env.CODEBOOK})
        print(f"[eval {tag}] " + ", ".join(f"{k} {v:.3f}" if isinstance(v, float) else f"{k} {v}"
                                         for k, v in summary.items()), flush=True)
        return summary

    try:
        before = evaluate("base", sampler_for("base"))
        log.write(json.dumps({"phase": "eval_base", **before}) + "\n")
        flat_total = groups_total = 0
        for step in range(a.steps):
            sampler = sampler_for(f"step{step:03d}")
            batch = [train[(step * a.tasks + i) % len(train)] for i in range(a.tasks)]
            datums, all_scores, flat, skipped = [], [], 0, 0
            for row in batch:
                prompt_mi, outs = sample(sampler, row, a.group, a.temperature)
                scores = [env.score(row, d.parse(o["text"])) for o in outs]
                all_scores += scores
                advs = env.group_advantages([s.reward[a.reward] for s in scores], a.adv_clip)
                groups_total += 1
                if advs is None:
                    flat += 1
                    continue
                for o, adv in zip(outs, advs, strict=True):
                    x = is_datum(prompt_mi, o["tokens"], o["logprobs"], adv) if o["tokens"] else None
                    if x is None:
                        skipped += 1
                    else:
                        datums.append(x)
            flat_total += flat
            if datums:
                tc.forward_backward(datums, "importance_sampling").result()
                tc.optim_step(adam).result()
            codes = Counter()
            for s in all_scores:
                codes.update(s.counts)
            row = {"step": step, "trained_on": a.reward, "datums": len(datums), "flat_groups": flat,
                   "skipped": skipped, **{r: fmean(s.reward[r] for s in all_scores) for r in env.REWARDS},
                   **{f"n_{c}": codes[c] for c in env.CODEBOOK},
                   "parsed": fmean(s.parsed for s in all_scores)}
            log.write(json.dumps(row) + "\n")
            log.flush()
            print(f"step {step}: {a.reward} {row[a.reward]:.3f} | exact {row['exact']:.3f} | "
                  f"invented {codes['invented_value']} missed {codes['missed_value']} wrong {codes['wrong_value']} | "
                  f"flat {flat}/{len(batch)}", flush=True)
            if step == 0 and flat == len(batch):
                print("WARNING: every group was flat on step 0 - no headroom for RL under this reward", flush=True)
        after = evaluate("final", sampler_for("final"))
        log.write(json.dumps({"phase": "eval_final", **after, "flat_share": flat_total / max(groups_total, 1)}) + "\n")
        state = tc.save_state(f"{run_id}-final").result().path
        print(f"final state: {state}\nlogs: {run_dir}", flush=True)
    finally:
        log.close()
        service.close()


if __name__ == "__main__":
    main()
