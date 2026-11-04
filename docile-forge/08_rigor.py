"""Rigor pass on the round-1 results: Holm-corrected significance, power, error taxonomy.

Closes the statistical gaps flagged in RESEARCH.md §3.5 using only the saved per-case results
(no API calls, no DocILE download needed):
  * every pre-specified comparison, Holm-adjusted for family-wise error;
  * cluster-robust standard error and minimum detectable effect (80% power) for each;
  * the unseen-layout slice under the same tests;
  * the invented / wrong / missed error taxonomy for every system;
  * document-level success (all 10 fields right) with a cluster bootstrap interval.

Writes results/rigor.json and prints markdown tables.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "grounded-evals" / "src"))

import dl_common as d  # noqa: E402

from grounded_evals.stats import compare, holm, minimum_detectable_effect  # noqa: E402

SYSTEMS = ["glm", "glm_1344", "glm_rules", "glm_rules_ocr", "glm_sft_1344"]
NAMES = {
    "glm": "Baseline 1,600 px",
    "glm_1344": "Baseline 1,344 px",
    "glm_rules": "Harness A (rules)",
    "glm_rules_ocr": "Harness B (rules + OCR)",
    "glm_sft_1344": "SFT (vision LoRA)",
}
# The family of comparisons reported in the README, in order.
PAIRS = [
    ("glm_sft_1344", "glm_1344", "all"),
    ("glm_sft_1344", "glm_1344", "unseen"),
    ("glm_sft_1344", "glm_rules_ocr", "all"),
    ("glm_rules", "glm", "all"),
    ("glm_rules_ocr", "glm", "all"),
    ("glm_rules_ocr", "glm", "unseen"),
    ("glm_1344", "glm", "all"),
]
REPS = 5000


def rows(tag: str) -> dict[str, dict]:
    return {f["id"]: f for f in d.field_rows(tag)}


def taxonomy(fields: list[dict]) -> dict[str, int]:
    out = {"invented": 0, "wrong": 0, "missed": 0}
    for f in fields:
        if f["score"] >= 1:
            continue
        if not f["present"]:
            out["invented"] += 1
        elif d.is_null(f["pred"]):
            out["missed"] += 1
        else:
            out["wrong"] += 1
    out["total"] = sum(out.values())
    return out


def doc_success(tag: str) -> dict[str, tuple[bool, int]]:
    by: dict[str, list[dict]] = defaultdict(list)
    for f in d.field_rows(tag):
        by[f["doc"]].append(f)
    return {k: (all(f["score"] >= 1 for f in v), v[0]["cluster"]) for k, v in by.items()}


def main() -> None:
    data = {t: rows(t) for t in SYSTEMS}
    out: dict = {"comparisons": [], "taxonomy": {}, "doc_success": []}

    results = []
    for a, b, subset in PAIRS:
        ids = sorted(i for i in set(data[a]) & set(data[b])
                     if subset == "all" or data[b][i]["unseen_layout"])
        c = compare([data[a][i]["score"] >= 1 for i in ids], [data[b][i]["score"] >= 1 for i in ids],
                    [data[b][i]["cluster"] for i in ids], reps=REPS)
        results.append((a, b, subset, c))
    adj = holm([c.mcnemar.p_value for *_, c in results])

    print("## Pre-specified comparisons (Holm-adjusted, family of", len(results), ")\n")
    print("| A vs B | Slice | Cases | Gap | p | p (Holm) | Cluster 95% CI | MDE@80% | Real? |")
    print("|---|---|---|---|---|---|---|---|---|")
    for (a, b, subset, c), p_h in zip(results, adj, strict=True):
        mde = minimum_detectable_effect(c.cluster_se)
        real = p_h < 0.05 and c.bootstrap.excludes_zero
        out["comparisons"].append({"a": a, "b": b, "slice": subset, "n": c.n, "delta": c.delta,
                                   "p": c.mcnemar.p_value, "p_holm": p_h, "only_a": c.mcnemar.only_a,
                                   "only_b": c.mcnemar.only_b, "ci": [c.bootstrap.lo, c.bootstrap.hi],
                                   "cluster_se": c.cluster_se, "mde_80": mde, "clusters": c.bootstrap.clusters,
                                   "real": real})
        print(f"| {NAMES[a]} vs {NAMES[b]} | {subset} | {c.n:,} | {c.delta * 100:+.1f} | {c.mcnemar.p_value:.1g} "
              f"| {p_h:.1g} | [{c.bootstrap.lo * 100:+.1f}, {c.bootstrap.hi * 100:+.1f}] | {mde * 100:.1f} "
              f"| {'yes' if real else 'no'} |")

    print("\n## Error taxonomy (of 5,000 field cases)\n")
    print("| System | Invented | Wrong value | Missed | Total |")
    print("|---|---|---|---|---|")
    for t in SYSTEMS:
        tx = taxonomy(list(data[t].values()))
        out["taxonomy"][t] = tx
        print(f"| {NAMES[t]} | {tx['invented']} | {tx['wrong']} | {tx['missed']} | {tx['total']} |")

    print("\n## Document-level success (all 10 fields right)\n")
    print("| System vs baseline 1,344 px | System | Baseline | Gap | p | Cluster 95% CI |")
    print("|---|---|---|---|---|---|")
    base = doc_success("glm_1344")
    for t in ["glm_rules", "glm_rules_ocr", "glm_sft_1344"]:
        s = doc_success(t)
        ids = sorted(set(s) & set(base))
        c = compare([s[i][0] for i in ids], [base[i][0] for i in ids], [base[i][1] for i in ids], reps=REPS)
        out["doc_success"].append({"system": t, "acc": c.acc_a, "baseline": c.acc_b, "delta": c.delta,
                                   "p": c.mcnemar.p_value, "ci": [c.bootstrap.lo, c.bootstrap.hi], "n": c.n})
        print(f"| {NAMES[t]} | {c.acc_a:.1%} | {c.acc_b:.1%} | {c.delta * 100:+.1f} | {c.mcnemar.p_value:.1g} "
              f"| [{c.bootstrap.lo * 100:+.1f}, {c.bootstrap.hi * 100:+.1f}] |")

    (d.RESULTS / "rigor.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {d.RESULTS / 'rigor.json'}")


if __name__ == "__main__":
    main()
