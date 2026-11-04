"""E2 (+ E1-lite): codebook vs scalar LLM-judge rewards under best-of-N optimisation pressure.

1. sample   K candidate extractions per test document from base GLM at temperature 1.0
            (cached per sample in results/results_glm_t1_s{i}.jsonl; ~$0.24 per sample).
2. judge    score every candidate with the same judge model under two criteria arms, M members
            each (temperature 0.7), cached in results/judge_{arm}.jsonl:
              scalar   - "probability each field is correct" (a generic judge)
              codebook - per-field probabilities of each GEDD failure code
3. analyse  per-code Platt calibration on half the layout clusters ("expert" labels = the exact
            scorer, since DocILE is verifiable), then best-of-N curves on the other half:
            proxy reward vs gold field accuracy for N = 1..K, single member vs conservative
            ensemble (mean - k*std). Repeated over cluster splits.

Hypothesis H2 (docs/research.md): the codebook reward's gold curve peaks later and higher than the
scalar judge's, and the conservative ensemble flattens any decline.

  uv run python 10_bon_overopt.py estimate          # token/cost estimate, no API calls
  uv run python 10_bon_overopt.py sample --k 8
  uv run python 10_bon_overopt.py judge --k 8 --members 2
  uv run python 10_bon_overopt.py analyse --k 8
  uv run python 10_bon_overopt.py analyse --smoke   # pipeline check on the 5 saved systems
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import fmean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "grounded-evals" / "src"))

import dl_common as d  # noqa: E402

from grounded_evals.reward import CodebookRewardModel, FailureCode, PlattCalibrator  # noqa: E402
from grounded_evals.stats import best_of_n_curve, overoptimization_gap  # noqa: E402

CODES = {
    "invented_value": "a value is returned but the field is not printed on the page",
    "wrong_value": "the field is printed but the returned value is not the printed one "
                   "(wrong number, wrong company, wrong date, wrong total)",
    "missed_value": "the field is printed on the page but null was returned",
}
CODEBOOK = [
    FailureCode("invented_value", "critical", blocking=True),
    FailureCode("wrong_value", "high"),
    FailureCode("missed_value", "medium"),
]
JUDGE_MODEL = "glm"
SPLITS = 20


def sample_tag(i: int) -> str:
    return f"glm_t1_s{i}"


def judge_path(arm: str) -> Path:
    return d.RESULTS / f"judge_{arm}.jsonl"


def judge_prompt(arm: str, candidate: dict) -> str:
    cand = json.dumps({k: candidate.get(k) for k in d.FIELDS}, ensure_ascii=False)
    fields = "\n".join(f"- {k}: {v}" for k, v in d.FIELDS.items())
    if arm == "scalar":
        ask = ('For each field, give the probability (0 to 1) that the extracted value is correct '
               '(a null is correct only if the field is not printed). Answer with only JSON: '
               '{"<field>": {"pass": p}, ...} for all 10 fields.')
    else:
        codes = "\n".join(f"- {c}: {desc}" for c, desc in CODES.items())
        ask = (f"Failure codes:\n{codes}\n\nFor each field, give the probability (0 to 1) that each "
               'failure code applies. Answer with only JSON: {"<field>": {"invented_value": p, '
               '"wrong_value": p, "missed_value": p}, ...} for all 10 fields.')
    return (f"You are auditing an automatic extraction from this document image.\n\nFields:\n{fields}\n\n"
            f"Extraction:\n{cand}\n\n{ask}")


async def run_judges(k: int, members: int, concurrency: int, limit: int | None) -> None:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url="https://api.fireworks.ai/inference/v1",
                         api_key=os.environ["FIREWORKS_API_KEY"], timeout=300)
    split = {r["id"]: r for r in d.load_split("test")}
    model = d.MODELS[JUDGE_MODEL]["model"]
    sem, lock = asyncio.Semaphore(concurrency), asyncio.Lock()
    jobs = []
    for arm in ["scalar", "codebook"]:
        done = set()
        if judge_path(arm).exists():
            for line in judge_path(arm).read_text().splitlines():
                r = json.loads(line)
                if r.get("probs"):
                    done.add((r["doc"], r["sample"], r["member"]))
        for i in range(k):
            res = d.load_results(sample_tag(i))
            for doc, rec in list(res.items())[:limit]:
                for m in range(members):
                    if (doc, i, m) not in done:
                        jobs.append((arm, doc, i, m, {f["field"]: f["pred"] for f in rec["fields"]}))

    async def one(arm: str, doc: str, i: int, m: int, cand: dict) -> None:
        msgs = [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": d.image_url(doc)}},
            {"type": "text", "text": judge_prompt(arm, cand)}]}]
        text, err = "", None
        async with sem:
            for attempt in range(4):
                try:
                    resp = await client.chat.completions.create(
                        model=model, messages=msgs, max_tokens=1500, temperature=0.7,
                        reasoning_effort="low")
                    text, err = resp.choices[0].message.content or "", None
                    break
                except Exception as e:  # noqa: BLE001
                    err = f"{type(e).__name__}: {e}"[:300]
                    await asyncio.sleep(3 * (attempt + 1))
        probs = d.parse(text)
        rec = {"doc": doc, "sample": i, "member": m, "cluster": split[doc]["cluster"],
               "probs": probs, "error": err}
        async with lock:
            with judge_path(arm).open("a") as f:
                f.write(json.dumps(rec) + "\n")

    print(f"judge calls to run: {len(jobs)}")
    for start in range(0, len(jobs), 500):
        await asyncio.gather(*(one(*j) for j in jobs[start:start + 500]))
        print(f"  {min(start + 500, len(jobs))}/{len(jobs)}")


def _p(x) -> float:
    try:
        return min(1.0, max(0.0, float(x)))
    except (TypeError, ValueError):
        return 0.5


def load_judgements(arm: str) -> dict[tuple[str, int], list[dict]]:
    """(doc, sample) -> list of members, each {field: {key: prob}}."""
    out: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for line in judge_path(arm).read_text().splitlines():
        r = json.loads(line)
        if isinstance(r.get("probs"), dict):
            out[(r["doc"], r["sample"])].append(r["probs"])
    return out


def true_code(f: dict) -> str | None:
    if f["score"] >= 1:
        return None
    if not f["present"]:
        return "invented_value"
    return "missed_value" if d.is_null(f["pred"]) else "wrong_value"


def analyse(tags: list[str], judged: dict[str, dict], ensemble_k: float, out_name: str) -> dict:
    """judged[arm][(doc, s)] = members; tags[s] = results tag of sample s."""
    cands = {s: d.load_results(t) for s, t in enumerate(tags)}
    docs = sorted(set.intersection(*(set(c) for c in cands.values())))
    cluster = {doc: cands[0][doc]["cluster"] for doc in docs}
    fields = {(doc, s): {f["field"]: f for f in cands[s][doc]["fields"]} for doc in docs for s in cands}
    gold = {key: fmean(f["score"] >= 1 for f in fs.values()) for key, fs in fields.items()}

    def member_field_probs(arm: str, member: dict, field: str) -> dict[str, float]:
        cell = member.get(field) if isinstance(member.get(field), dict) else {}
        if arm == "scalar":
            return {"error": 1 - _p(cell.get("pass"))}
        return {c: _p(cell.get(c)) for c in CODES}

    rng = random.Random(0)
    clusters = sorted(set(cluster.values()))
    curves: dict[str, list[list]] = defaultdict(list)
    for _ in range(SPLITS):
        rng.shuffle(clusters)
        cal_c = set(clusters[: len(clusters) // 2])
        cal_docs = [x for x in docs if cluster[x] in cal_c]
        ev_docs = [x for x in docs if cluster[x] not in cal_c]
        for arm in judged:
            # fit calibrators on the calibration clusters, first member only
            raw, labels = [], []
            for doc in cal_docs:
                for s in cands:
                    members = judged[arm].get((doc, s))
                    if not members:
                        continue
                    for field, f in fields[(doc, s)].items():
                        raw.append(member_field_probs(arm, members[0], field))
                        labels.append(true_code(f))
            if arm == "scalar":
                cal = PlattCalibrator().fit([r["error"] for r in raw], [y is not None for y in labels])
                rm = CodebookRewardModel([FailureCode("error", weight=1.0)], k=0.0,
                                         calibrators={"error": cal})
            else:
                rm = CodebookRewardModel(CODEBOOK, k=0.0)
                rm.fit_calibration(raw, [{y} if y else set() for y in labels])
            for variant, k in [("single", 0.0), ("ensemble", ensemble_k)]:
                rm.k = k
                proxy_all, gold_all = [], []
                for doc in ev_docs:
                    p_row, g_row = [], []
                    for s in cands:
                        members = judged[arm].get((doc, s))
                        if not members:
                            break
                        if variant == "single":
                            members = members[:1]
                        per_field = [rm.score([member_field_probs(arm, m, fld) for m in members]).reward
                                     for fld in fields[(doc, s)]]
                        p_row.append(fmean(per_field))
                        g_row.append(gold[(doc, s)])
                    if len(p_row) == len(cands):
                        proxy_all.append(p_row)
                        gold_all.append(g_row)
                if proxy_all:
                    curves[f"{arm}_{variant}"].append(best_of_n_curve(proxy_all, gold_all))
        ev_gold = [[gold[(doc, s)] for s in cands] for doc in ev_docs]
        curves["oracle"].append(best_of_n_curve(ev_gold, ev_gold))

    summary = {}
    for name, runs in curves.items():
        pts = list(zip(*runs, strict=True))
        summary[name] = [{"n": p[0].n, "kl": p[0].kl, "proxy": fmean(x.proxy for x in p),
                          "gold": fmean(x.gold for x in p)} for p in pts]
        gaps = [overoptimization_gap(r) for r in runs]
        summary[name + "_overopt_gap"] = fmean(gaps)
    (d.RESULTS / out_name).write_text(json.dumps(summary, indent=2))
    print(f"\n| Reward | " + " | ".join(f"N={p['n']}" for p in summary["oracle"]) + " | Overopt. gap |")
    print("|---|" + "---|" * (len(summary["oracle"]) + 1))
    for name in sorted(k for k in summary if not k.endswith("_gap")):
        row = " | ".join(f"{p['gold']:.3f}" for p in summary[name])
        print(f"| {name} | {row} | {summary[name + '_overopt_gap']:.3f} |")
    print(f"\n(gold = field accuracy of the selected candidate; wrote results/{out_name})")
    return summary


def smoke() -> None:
    """Exercise the analysis path on the 5 saved systems as K=5 'candidates', using a fake
    judge derived from cross-system agreement. Checks plumbing only; not a result."""
    tags = ["glm", "glm_1344", "glm_rules", "glm_rules_ocr", "glm_sft_1344"]
    res = [d.load_results(t) for t in tags]
    judged: dict[str, dict] = {"scalar": {}, "codebook": {}}
    for doc in res[0]:
        preds = [{f["field"]: d.norm_text(f["pred"]) if not d.is_null(f["pred"]) else None
                  for f in r[doc]["fields"]} for r in res]
        for s, mine in enumerate(preds):
            sc, cb = {}, {}
            for fld, v in mine.items():
                others = [p[fld] for j, p in enumerate(preds) if j != s]
                agree = sum(o == v for o in others) / len(others)
                nulls = sum(o is None for o in others) / len(others)
                sc[fld] = {"pass": agree}
                cb[fld] = ({"invented_value": nulls, "wrong_value": 1 - agree - nulls, "missed_value": 0}
                           if v is not None else
                           {"invented_value": 0, "wrong_value": 0, "missed_value": 1 - nulls})
            judged["scalar"][(doc, s)] = [sc, sc]
            judged["codebook"][(doc, s)] = [cb, cb]
    analyse(tags, judged, ensemble_k=1.0, out_name="bon_smoke.json")


def estimate(k: int, members: int) -> None:
    base = list(d.load_results("glm_1344").values()) or list(d.load_results("glm").values())
    pin, pout = d.MODELS["glm"]["price"]
    p_tok = fmean(r["prompt_tokens"] for r in base)
    c_tok = fmean(r["completion_tokens"] for r in base)
    n = len(base)
    sample = k * n * (p_tok * pin + c_tok * pout) / 1e6
    judge = 2 * members * k * n * ((p_tok + 400) * pin + 600 * pout) / 1e6
    print(f"{n} docs, K={k}, members={members}: sampling ≈ ${sample:.2f}, judging ≈ ${judge:.2f}, "
          f"total ≈ ${sample + judge:.2f} at list price")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["estimate", "sample", "judge", "analyse"])
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--members", type=int, default=2)
    ap.add_argument("--ensemble-k", type=float, default=1.0)
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.step == "estimate":
        estimate(a.k, a.members)
    elif a.step == "sample":
        for i in range(a.k):
            asyncio.run(d.eval_model("glm", sample_tag(i), temperature=1.0, concurrency=a.concurrency,
                                     limit=a.limit))
    elif a.step == "judge":
        asyncio.run(run_judges(a.k, a.members, a.concurrency, a.limit))
    elif a.smoke:
        smoke()
    else:
        judged = {arm: load_judgements(arm) for arm in ["scalar", "codebook"] if judge_path(arm).exists()}
        analyse([sample_tag(i) for i in range(a.k)], judged, a.ensemble_k, "bon_overopt.json")


if __name__ == "__main__":
    main()
