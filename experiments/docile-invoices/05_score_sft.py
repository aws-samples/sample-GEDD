#!/usr/bin/env python3
"""Step 5: (re)score the locked test set on a saved fine-tuned checkpoint, without retraining.

Uses Fireworks' standalone serverless sampling of an existing training session's checkpoint, with bounded
concurrency and retries. Cached: only documents missing or errored in results/results_<tag>.jsonl are re-run.

    uv run python 05_score_sft.py --checkpoint accounts/<acct>/trainingSessions/<ts>/checkpoints/<ckpt> --limit 3
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import dl_common as d

BASE = "zai-org/GLM-5.3-Flash"
PREFILL_PRICE = 2.96  # USD per 1M prompt tokens on the serverless training sampler


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--tag", default="glm_sft")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--max-usd", type=float, default=6.0)
    args = p.parse_args()

    from fireworks.training import sdk
    from fireworks.training.sdk import FiretitanServiceClient
    from training.renderer import get_text_content
    from training.renderer.tokenizer import get_tokenizer
    from training.utils.supervised import build_renderer

    import importlib
    sft = importlib.import_module("04_sft")

    tok = get_tokenizer(BASE)
    renderer = build_renderer(tok, BASE, "glm53_flash")
    service = FiretitanServiceClient(api_key=os.environ["FIREWORKS_API_KEY"],
                                     base_url="https://api.fireworks.ai/training/v1/serverless")
    sampler = service.create_sampling_client(model_path=args.checkpoint, tokenizer=tok)
    params = sdk.SamplingParams(max_tokens=512, temperature=0.0, stop=renderer.get_stop_sequences())

    test = d.load_split("test")
    done = {k for k, r in d.load_results(args.tag).items() if not r.get("error")}
    todo = [r for r in test if r["id"] not in done][: args.limit]
    est = len(todo) * 2830 * PREFILL_PRICE / 1e6
    print(f"to score: {len(todo)} docs, est. ${est:.2f}", flush=True)
    if est > args.max_usd:
        raise SystemExit(f"estimate exceeds --max-usd {args.max_usd}")

    def one(r):
        sp, imgs = sft.sampling_prompt(renderer, tok, d.messages(r))
        err, text = None, ""
        for attempt in range(4):
            try:
                res = sampler.sample(prompt=sp, num_samples=1, sampling_params=params, images=imgs).result()
                text = get_text_content(renderer.parse_response(list(res.sequences[0].tokens))[0])
                err = None
                break
            except Exception as e:  # noqa: BLE001
                body = getattr(getattr(e, "response", None), "text", "")
                err = f"{type(e).__name__}: {str(e)[:200]} | {body[:400]}"
                time.sleep(5 * (attempt + 1))
        pred = d.parse(text)
        return {"doc": r["id"], "model": args.tag, "cluster": r["cluster"], "parsed": pred is not None,
                "fields": d.grade(r, pred), "text": text[-2000:], "error": err if not text else None,
                "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "latency_s": 0.0}

    # Rewrite the file without the errored rows, then append fresh ones.
    keep = [r for r in d.load_results(args.tag).values() if not r.get("error")]
    path = d.results_path(args.tag)
    path.write_text("".join(json.dumps(r) + "\n" for r in keep))
    with ThreadPoolExecutor(args.workers) as ex, path.open("a") as out:
        for i, rec in enumerate(ex.map(one, todo), 1):
            out.write(json.dumps(rec) + "\n")
            out.flush()
            if rec["error"]:
                print(f"ERROR {rec['doc']}: {rec['error']}", flush=True)
            if i % 50 == 0:
                print(f"  scored {i}/{len(todo)}", flush=True)
    d.summarize(args.tag)


if __name__ == "__main__":
    main()
