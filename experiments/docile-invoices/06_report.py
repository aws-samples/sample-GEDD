"""Steps 5-6: score every system on the same 5,000 field cases and test each gap.

Significant = exact McNemar p < 0.05 AND the layout-cluster bootstrap 95% CI excludes zero.
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict

import dl_common as d

ALPHA, B = 0.05, 5000
NAMES = {"glm": "Baseline, 1,600 px", "glm_1344": "Baseline, 1,344 px",
         "glm_rules": "Harness A: rules in prompt", "glm_rules_ocr": "Harness B: rules + OCR text",
         "glm_sft_1344": "Vision LoRA fine-tune, 1,344 px",
         "gemini4": "Gemini 4 Argon", "opus55": "Claude Opus 5.5", "gpt61": "GPT-6.1 Terra Pro"}
SFT = "glm_sft_1344"
# (A, B): every change vs the baseline; the fine-tune also vs its resolution-matched baseline and each harness.
PAIRS = [("glm_rules", "glm"), ("glm_rules_ocr", "glm"), (SFT, "glm_1344"), (SFT, "glm"), (SFT, "glm_rules"),
         (SFT, "glm_rules_ocr"), ("glm_1344", "glm"), (SFT, "gemini4"), (SFT, "opus55"), (SFT, "gpt61")]
PRICE_IN, PRICE_OUT = d.MODELS["glm"]["price"]


def mcnemar(a: list[bool], b: list[bool]) -> dict:
    only_a = sum(x and not y for x, y in zip(a, b))
    only_b = sum(y and not x for x, y in zip(a, b))
    n = only_a + only_b
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(min(only_a, only_b) + 1)) / 2 ** n) if n else 1.0
    return {"only_a": only_a, "only_b": only_b, "p": p}


def cluster_bootstrap(groups: list, a: list[bool], b: list[bool], reps: int = B, seed: int = 42) -> dict:
    by = defaultdict(lambda: [0, 0, 0])  # sum_a, sum_b, n per cluster
    for g, x, y in zip(groups, a, b):
        by[g][0] += x; by[g][1] += y; by[g][2] += 1
    keys = list(by)
    rng = random.Random(seed)
    deltas = []
    for _ in range(reps):
        sa = sb = n = 0
        for k in (rng.choice(keys) for _ in keys):
            sa += by[k][0]; sb += by[k][1]; n += by[k][2]
        deltas.append((sa - sb) / n)
    deltas.sort()
    return {"delta": (sum(a) - sum(b)) / len(a), "lo": deltas[int(0.025 * reps)], "hi": deltas[int(0.975 * reps) - 1],
            "wins": sum(x > 0 for x in deltas), "losses": sum(x < 0 for x in deltas), "clusters": len(keys)}


def compare(a: str, b: str, subset=lambda f: True) -> dict | None:
    A = {f["id"]: f for f in d.field_rows(a) if subset(f)}
    Bm = {f["id"]: f for f in d.field_rows(b) if subset(f)}
    ids = sorted(set(A) & set(Bm))
    if not ids:
        return None
    ac, bc = [A[i]["score"] >= 1 for i in ids], [Bm[i]["score"] >= 1 for i in ids]
    mc, bs = mcnemar(ac, bc), cluster_bootstrap([A[i]["cluster"] for i in ids], ac, bc)
    sig = mc["p"] < ALPHA and (bs["lo"] > 0 or bs["hi"] < 0)
    return {"a": a, "b": b, "n": len(ids), "acc_a": sum(ac) / len(ids), "acc_b": sum(bc) / len(ids),
            "mcnemar": mc, "bootstrap": bs, "significant": sig}


def cost(tag: str) -> float | None:
    res = d.load_results(tag).values()
    if tag == SFT or not res:
        return None
    return sum(r["prompt_tokens"] * PRICE_IN + r["completion_tokens"] * PRICE_OUT for r in res) / 1e6


def main(tags: list[str]) -> None:
    tags = [t for t in tags if d.results_path(t).exists()]
    out = {"leaderboard": [], "comparisons": [], "per_field": {}}
    print("\n## Leaderboard (5,000 field cases, 500 test documents)\n")
    print("| System | Field accuracy | Present | Absent (null) | Unseen layouts | Cost, 500 docs |")
    print("| --- | --- | --- | --- | --- | --- |")
    for t in tags:
        s = d.summarize.__wrapped__(t) if hasattr(d.summarize, "__wrapped__") else _quiet_summary(t)
        c = cost(t)
        out["leaderboard"].append({**s, "cost_usd": c})
        print(f"| {NAMES.get(t, t)} | {s['field_accuracy']:.1%} | {s['present_accuracy']:.1%} | {s['absent_accuracy']:.1%} | "
              f"{s['unseen_layout_accuracy']:.1%} | {'$%.2f' % c if c is not None else 'scored in training session'} |")

    print("\n## Significance vs baseline (McNemar exact + layout-cluster bootstrap, 5,000 reps)\n")
    print("| Comparison | Gap | Only A right / only B right | McNemar p | Cluster bootstrap 95% CI | Verdict |")
    print("| --- | --- | --- | --- | --- | --- |")
    pairs = [(a, b) for a, b in PAIRS if a in tags and b in tags]
    for a, b in pairs:
        for label, sub in (("all", lambda f: True), ("unseen layouts", lambda f: f["unseen_layout"])):
            r = compare(a, b, sub)
            if not r:
                continue
            r["subset"] = label
            out["comparisons"].append(r)
            mc, bs = r["mcnemar"], r["bootstrap"]
            verdict = ("real gain" if bs["delta"] > 0 else "real loss") if r["significant"] else "could be luck"
            print(f"| {NAMES.get(a, a)} vs {NAMES.get(b, b)} ({label}) | {100 * bs['delta']:+.1f} | "
                  f"{mc['only_a']} / {mc['only_b']} | {mc['p']:.2g} | [{100 * bs['lo']:+.1f}, {100 * bs['hi']:+.1f}] | {verdict} |")

    print("\n## Accuracy per field\n")
    print("| Field | " + " | ".join(NAMES.get(t, t) for t in tags) + " |")
    print("| --- |" + " --- |" * len(tags))
    for k in d.FIELDS:
        row = []
        for t in tags:
            fr = [f for f in d.field_rows(t) if f["field"] == k]
            acc = sum(f["score"] for f in fr) / max(len(fr), 1)
            out["per_field"].setdefault(t, {})[k] = acc
            row.append(f"{acc:.0%}")
        print(f"| {k} | " + " | ".join(row) + " |")
    (d.RESULTS / "report.json").write_text(json.dumps(out, indent=2, default=str))


def _quiet_summary(tag: str) -> dict:
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        return d.summarize(tag)


if __name__ == "__main__":
    main(sys.argv[1:] or ["glm", "glm_1344", "glm_rules", "glm_rules_ocr", SFT])
