#!/usr/bin/env python3
"""Step 4: serverless vision LoRA SFT of GLM 5.3 Flash on DocILE key-field extraction (train split only),
then score the locked test set in-session on the exact trained weights and promote the adapter.

Adapted from the Forge sample (sinanuozdemir/ai-experiments, floorplancad-symbol-counting/fp_sft.py).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor

import dl_common as d

BASE_MODEL = "accounts/fireworks/models/glm-5p3-flash"
TOKENIZER_MODEL = "zai-org/GLM-5.3-Flash"
RENDERER_NAME = "glm53_flash"
# Serverless training list prices, USD per 1M tokens (docs.fireworks.ai/fine-tuning/training-api/serverless).
PRICE = {"prefill": 2.96, "sample": 7.41, "train": 8.89}


def sampling_prompt(renderer, tokenizer, messages):
    """The serverless sampler takes text tokens; images travel separately (from the Forge sample's fw_utils)."""
    from fireworks.training import sdk
    from training.utils.rl.rollout.renderer import build_multimodal_completions_prompt_token_ids
    from training.utils.supervised import normalize_messages

    expanded = renderer.build_generation_prompt(normalize_messages(messages))
    ids, images = build_multimodal_completions_prompt_token_ids(messages, expanded, tokenizer, renderer=renderer)
    return sdk.ModelInput.from_ints(ids), images


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tag", default="glm_sft")
    p.add_argument("--n-train", type=int, default=1400)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--lora-rank", type=int, default=16)
    p.add_argument("--learning-rate", type=float, default=1e-4)
    p.add_argument("--max-seq-len", type=int, default=6144)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--no-promote", action="store_true")
    p.add_argument("--max-usd", type=float, default=42.0, help="hard cap on estimated spend for this run")
    p.add_argument("--dry-run", action="store_true", help="render data and print the cost estimate only")
    args = p.parse_args()

    from fireworks import Fireworks
    from fireworks.training import sdk
    from fireworks.training.sdk import FiretitanServiceClient, FireworksClient
    from training.renderer import get_text_content
    from training.renderer.tokenizer import get_tokenizer
    from training.utils.supervised import build_renderer, render_messages_to_datum

    train = d.load_split("train")
    random.Random(args.seed).shuffle(train)
    train = train[: args.n_train]
    test = d.load_split("test")
    with ThreadPoolExecutor(8) as ex:  # render page images up front
        list(ex.map(d.image_path, [r["id"] for r in train + test]))

    run_id = time.strftime(f"docile-{args.tag.replace('_', '-')}-%Y%m%d-%H%M%S")
    run_dir = d.HERE / "sft_logs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "args.json").write_text(json.dumps(vars(args), indent=2))
    print(f"run_id={run_id} train={len(train)} test={len(test)}", flush=True)

    tok = get_tokenizer(TOKENIZER_MODEL)
    renderer = build_renderer(tok, TOKENIZER_MODEL, RENDERER_NAME)
    datums, lens, n_tokens = [], [], 0
    for i, r in enumerate(train):
        x = render_messages_to_datum(d.messages(r) + [{"role": "assistant", "content": d.target_json(r)}],
                                     renderer=renderer, max_seq_len=args.max_seq_len)
        if len(x.token_ids) <= args.max_seq_len and any(w > 0 for w in x.token_weights):
            n_tokens += len(x.token_ids)
            lens.append(len(x.token_ids))
            datums.append(sdk.Datum(model_input=x.datum.model_input.model_dump(),
                                    loss_fn_inputs={k: v.tolist() for k, v in x.datum.loss_fn_inputs.items()}))
        if (i + 1) % 500 == 0:
            print(f"  rendered {i + 1}/{len(train)}", flush=True)
    print(f"datums={len(datums)} train_tokens/epoch={n_tokens:,}", flush=True)

    # Pre-flight: the serverless sampler rejects any single image over 2,048 prompt tokens (training does not),
    # so check every test image before paying for training. Run with DOCILE_MAX_SIDE=1344 to fit.
    blank = [{"role": "system", "content": d.SYSTEM}, {"role": "user", "content": d.PROMPT}, {"role": "assistant", "content": "x"}]
    text_only = len(render_messages_to_datum(blank, renderer=renderer, max_seq_len=args.max_seq_len).token_ids)
    worst = max(len(render_messages_to_datum(d.messages(r) + [blank[2]], renderer=renderer, max_seq_len=8192).token_ids)
                - text_only for r in test)
    print(f"largest test image: {worst} tokens (sampler limit 2048)", flush=True)
    if worst > 2048:
        raise SystemExit("test images exceed the serverless sampler's 2,048-token image limit; set DOCILE_MAX_SIDE=1344")

    # Budget guard: estimate the whole run (training + in-session test scoring) before touching the GPU pool.
    test_prefill = n_tokens / max(len(datums), 1) * len(test)  # test prompts are the same shape as train rows
    est = {"train": n_tokens * args.epochs * PRICE["train"] / 1e6, "test_prefill": test_prefill * PRICE["prefill"] / 1e6,
           "test_sample": len(test) * 200 * PRICE["sample"] / 1e6}
    est["total"] = sum(est.values())
    (run_dir / "cost_estimate.json").write_text(json.dumps(est, indent=2))
    print("cost estimate USD: " + ", ".join(f"{k} {v:.2f}" for k, v in est.items()), flush=True)
    if est["total"] > args.max_usd:
        raise SystemExit(f"estimated ${est['total']:.2f} exceeds --max-usd {args.max_usd}; lower --n-train")
    if args.dry_run:
        return
    budget_train_tokens = (args.max_usd - est["test_prefill"] - est["test_sample"]) / PRICE["train"] * 1e6

    service = FiretitanServiceClient(
        api_key=os.environ["FIREWORKS_API_KEY"],
        base_url=os.environ.get("FIREWORKS_BASE_URL", "https://api.fireworks.ai").rstrip("/") + "/training/v1/serverless",
    )
    metrics = (run_dir / "metrics.jsonl").open("a")
    try:
        for attempt in range(1, 9):
            try:
                tc = service.create_lora_training_client(base_model=BASE_MODEL, rank=args.lora_rank, alpha=2 * args.lora_rank,
                                                         train_mlp=True, train_attn=True, train_unembed=True)
                break
            except Exception as e:  # noqa: BLE001
                if getattr(e, "status_code", None) not in (429, 500, 502, 503, 504) or attempt == 8:
                    raise
                time.sleep(min(30 * 2 ** (attempt - 1), 600))
        adam = sdk.AdamParams(learning_rate=args.learning_rate, beta1=0.9, beta2=0.999, eps=1e-8, weight_decay=0.0,
                              grad_clip_norm=1.0)
        rng, step, spent_tokens = random.Random(args.seed), 0, 0
        for epoch in range(args.epochs):
            order = list(range(len(datums)))
            rng.shuffle(order)
            for s in range(0, len(order), args.batch_size):
                idx = order[s:s + args.batch_size]
                batch, batch_tokens = [datums[i] for i in idx], sum(lens[i] for i in idx)
                if spent_tokens + batch_tokens > budget_train_tokens:
                    print(f"budget stop at step {step}: {spent_tokens:,} train tokens", flush=True)
                    break
                fb = tc.forward_backward(batch, "cross_entropy").result()
                spent_tokens += batch_tokens
                tc.optim_step(adam).result()
                step += 1
                m = dict(getattr(fb, "metrics", None) or {})
                toks = m.get("response_tokens") or m.get("num_loss_tokens") or 1.0
                rec = {"step": step, "epoch": epoch + 1, "loss": round(m.get("loss:sum", 0.0) / max(float(toks), 1.0), 4)}
                metrics.write(json.dumps(rec) + "\n")
                metrics.flush()
                if step % 10 == 0 or step == 1:
                    print(json.dumps(rec), flush=True)

        snap = tc.save_weights_for_sampler("docile-tuned").result().path
        sampler = service.create_sampling_client(model_path=snap, tokenizer=tok)
        params = sdk.SamplingParams(max_tokens=512, temperature=0.0, stop=renderer.get_stop_sequences())
        print(f"scoring test n={len(test)}…", flush=True)
        futs = []
        for r in test:  # the SDK's adaptive concurrency controller throttles these
            sp, imgs = sampling_prompt(renderer, tok, d.messages(r))
            futs.append(sampler.sample(prompt=sp, num_samples=1, sampling_params=params, images=imgs))
        out_path = d.results_path(args.tag)
        out_path.unlink(missing_ok=True)
        with out_path.open("w") as out:
            for i, (r, fut) in enumerate(zip(test, futs)):
                err, text = None, ""
                try:
                    text = get_text_content(renderer.parse_response(list(fut.result().sequences[0].tokens))[0])
                except Exception as e:  # noqa: BLE001
                    err = f"{type(e).__name__}: {e}"[:500]
                pred = d.parse(text)
                out.write(json.dumps({"doc": r["id"], "model": args.tag, "cluster": r["cluster"], "parsed": pred is not None,
                                      "fields": d.grade(r, pred), "text": text[-2000:], "error": err,
                                      "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "latency_s": 0.0}) + "\n")
                if (i + 1) % 100 == 0:
                    print(f"  scored {i + 1}/{len(test)}", flush=True)
        d.summarize(args.tag)

        if not args.no_promote:
            fw = FireworksClient(api_key=os.environ["FIREWORKS_API_KEY"],
                                 base_url=os.environ.get("FIREWORKS_BASE_URL", "https://api.fireworks.ai"))
            acct = next(iter(Fireworks().accounts.list(page_size=1))).name.split("/")[-1]
            cks = [c for c in fw.list_training_session_checkpoints(service.training_session_name)
                   if c.get("promotable") and "docile-tuned" in (c.get("checkpointName") or c.get("name") or "")]
            if cks:
                model_id = run_id[:63].rstrip("-")
                fw.promote_session_checkpoint(name=max(cks, key=lambda c: c.get("createTime", ""))["name"],
                                              output_model_id=model_id, base_model=BASE_MODEL)
                print(f"promoted accounts/{acct}/models/{model_id}", flush=True)
    finally:
        metrics.close()
        service.close()
        print("serverless session closed", flush=True)


if __name__ == "__main__":
    main()
