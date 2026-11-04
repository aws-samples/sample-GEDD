"""Codebook reward model, response gate and PPI on the round-1 predictions (no API calls).

Two experiments on the fine-tuned model's 5,000 real field predictions, using the other four
systems' predictions as gold-free evidence (how many independent systems agree with the answer):

E-gate · Does decomposing the reward by failure code help the gate?
  Codebook from the round-1 error taxonomy: invented_value (critical, blocking), wrong_value
  (high), missed_value (medium). Each code gets a gold-free detector, Platt-calibrated on
  "expert-labelled" layout clusters; the scalar baseline calibrates a single P(error).
  A document's score is its weakest field's score. On the held-out clusters each method auto-
  posts exactly the same share of documents (its top-ranked ones, ties broken at random), so
  methods are compared at matched straight-through rates. Repeated over random cluster splits;
  the codebook-minus-scalar difference is paired within each split.

E-ppi · Can a small expert sample plus judge scores on everything give valid, tighter intervals?
  Estimate the fine-tune's field accuracy and document success from n random expert labels plus
  the agreement score on every case. Coverage and interval width vs expert-only, over many draws.

Writes results/reward_gate_ppi.json and figures/gate_tradeoff.png, figures/ppi_width.png.
"""

from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import fmean, pstdev

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "grounded-evals" / "src"))

import dl_common as d  # noqa: E402

from grounded_evals.reward import CodebookRewardModel, FailureCode, PlattCalibrator  # noqa: E402
from grounded_evals.stats import (  # noqa: E402
    brier_score,
    classical_mean,
    expected_calibration_error,
    ppi_mean,
)

TARGET = "glm_sft_1344"
OTHERS = ["glm", "glm_1344", "glm_rules", "glm_rules_ocr"]
CODEBOOK = [
    FailureCode("invented_value", "critical", blocking=True),
    FailureCode("wrong_value", "high"),
    FailureCode("missed_value", "medium"),
]
WEIGHT = {c.code: c.w for c in CODEBOOK}
SPLITS = 50
COVERAGES = [0.1, 0.2, 0.3, 0.4]
PPI_NS = [25, 50, 100, 200, 400]
PPI_TRIALS = 2000
METHODS = ["codebook", "scalar", "codebook_sum", "scalar_sum"]
DIFFS = [("codebook", "scalar"), ("codebook_sum", "scalar_sum")]


def norm(field: str, v):
    if d.is_null(v) or isinstance(v, (list, dict)):
        return None
    if field in d.AMOUNTS:
        return d.norm_amount(v)
    if field in d.DATES:
        return d.norm_date(v)
    if field == "currency_code_amount_due":
        return d.norm_currency(v)
    return d.norm_text(v) or None


def true_code(f: dict) -> str | None:
    if f["score"] >= 1:
        return None
    if not f["present"]:
        return "invented_value"
    return "missed_value" if d.is_null(f["pred"]) else "wrong_value"


def build_cases() -> list[dict]:
    target = {f["id"]: f for f in d.field_rows(TARGET)}
    others = [{f["id"]: f for f in d.field_rows(t)} for t in OTHERS]
    cases = []
    for i, f in target.items():
        mine = norm(f["field"], f["pred"])
        votes = [norm(o[i]["field"], o[i]["pred"]) for o in others]
        k = len(votes)
        agree = sum(v == mine for v in votes)
        null_votes = sum(v is None for v in votes)
        if mine is None:
            raw = {"invented_value": 0.0, "wrong_value": 0.0, "missed_value": (k - null_votes) / k}
        else:
            raw = {"invented_value": null_votes / k, "wrong_value": (k - agree - null_votes) / k,
                   "missed_value": 0.0}
        cases.append({"id": i, "doc": f["doc"], "cluster": f["cluster"], "correct": f["score"] >= 1,
                      "code": true_code(f), "agree": agree / k, "raw": raw})
    return cases


def by_doc(cases: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for c in cases:
        out[c["doc"]].append(c)
    return out


def doc_cost(fields: list[dict]) -> float:
    return sum(WEIGHT[c["code"]] for c in fields if c["code"])


def auroc(scores: list[float], labels: list[bool]) -> float:
    pos = [s for s, y in zip(scores, labels, strict=True) if y]
    neg = [s for s, y in zip(scores, labels, strict=True) if not y]
    if not pos or not neg:
        return float("nan")
    ranked = sorted((s, y) for s, y in zip(scores, labels, strict=True))
    rank_sum, i = 0.0, 0
    while i < len(ranked):
        j = i
        while j + 1 < len(ranked) and ranked[j + 1][0] == ranked[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        rank_sum += avg * sum(1 for t in range(i, j + 1) if ranked[t][1])
        i = j + 1
    return (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def fit_models(cal: list[dict]) -> tuple[CodebookRewardModel, PlattCalibrator]:
    rm = CodebookRewardModel(CODEBOOK, k=0.0)
    rm.fit_calibration([c["raw"] for c in cal], [{c["code"]} if c["code"] else set() for c in cal])
    scalar = PlattCalibrator().fit([1 - c["agree"] for c in cal], [not c["correct"] for c in cal])
    return rm, scalar


def doc_scores(docs: dict[str, list[dict]], rm: CodebookRewardModel, scalar: PlattCalibrator,
               ) -> dict[str, dict[str, float]]:
    out = {}
    for k, fields in docs.items():
        out[k] = {
            # weakest-link: a document is only as postable as its riskiest field
            "codebook": min(rm.score([c["raw"]]).reward for c in fields),
            "scalar": min(1 - scalar(1 - c["agree"]) for c in fields),
            # expected-cost rules (Proposition 1): rank by minus the summed expected cost
            "codebook_sum": -sum(sum(WEIGHT[k] * p for k, p in rm.score([c["raw"]]).code_probs.items())
                                 for c in fields),
            "scalar_sum": -sum(scalar(1 - c["agree"]) for c in fields),
        }
    return out


def top_k(scores: dict[str, float], coverage: float, rng: random.Random) -> list[str]:
    """Highest-scoring documents at an exact straight-through rate, ties broken at random."""
    k = max(1, round(coverage * len(scores)))
    jitter = {key: rng.random() for key in scores}
    return sorted(scores, key=lambda key: (scores[key], jitter[key]), reverse=True)[:k]


def gate_experiment(cases: list[dict]) -> dict:
    clusters = sorted({c["cluster"] for c in cases})
    rng = random.Random(0)
    acc: dict = defaultdict(lambda: defaultdict(list))
    calib: dict = defaultdict(list)
    for _ in range(SPLITS):
        rng.shuffle(clusters)
        cal_set = set(clusters[: len(clusters) // 2])
        cal = [c for c in cases if c["cluster"] in cal_set]
        ev = [c for c in cases if c["cluster"] not in cal_set]
        rm, scalar = fit_models(cal)

        # reward-model quality on held-out clusters
        for code in WEIGHT:
            p = [rm.score([c["raw"]]).code_probs[code] for c in ev]
            y = [c["code"] == code for c in ev]
            calib[f"{code}_auroc"].append(auroc(p, y))
            calib[f"{code}_ece"].append(expected_calibration_error(p, y))
        p_err = [scalar(1 - c["agree"]) for c in ev]
        y_err = [not c["correct"] for c in ev]
        calib["scalar_error_auroc"].append(auroc(p_err, y_err))
        calib["scalar_error_ece"].append(expected_calibration_error(p_err, y_err))
        calib["scalar_error_brier"].append(brier_score(p_err, y_err))
        cb_err = [1 - rm.score([c["raw"]]).reward for c in ev]
        calib["codebook_error_auroc"].append(auroc(cb_err, y_err))

        ev_docs = by_doc(ev)
        ev_s = doc_scores(ev_docs, rm, scalar)
        for cov in COVERAGES:
            split_metrics = {}
            for method in METHODS:
                posted = top_k({k: v[method] for k, v in ev_s.items()}, cov, rng)
                m = {"precision": fmean(all(c["correct"] for c in ev_docs[k]) for k in posted),
                     "cost_per_doc": fmean(doc_cost(ev_docs[k]) for k in posted),
                     "invented_slips": sum(c["code"] == "invented_value" for k in posted
                                           for c in ev_docs[k]) / len(posted)}
                split_metrics[method] = m
                for name, val in m.items():
                    acc[method][f"{cov}_{name}"].append(val)
            for name in ["precision", "cost_per_doc", "invented_slips"]:
                for a, b in DIFFS:
                    acc[f"{a}_minus_{b}"][f"{cov}_{name}"].append(split_metrics[a][name] - split_metrics[b][name])
        acc["no_gate"]["precision"].append(fmean(all(c["correct"] for c in v) for v in ev_docs.values()))
        acc["no_gate"]["cost_per_doc"].append(fmean(doc_cost(v) for v in ev_docs.values()))

    def summarise(xs: list[float]) -> dict[str, float]:
        ordered = sorted(xs)
        return {"mean": fmean(xs), "sd": pstdev(xs), "lo": ordered[int(0.025 * len(xs))],
                "hi": ordered[min(len(xs) - 1, int(0.975 * len(xs)))],
                "share_positive": sum(x > 0 for x in xs) / len(xs)}

    return {"splits": SPLITS,
            "calibration": {k: summarise(v) for k, v in calib.items()},
            "gate": {m: {k: summarise(v) for k, v in vals.items()} for m, vals in acc.items()}}


def ppi_experiment(cases: list[dict]) -> dict:
    docs = by_doc(cases)
    doc_rows = [{"y": float(all(c["correct"] for c in v)), "f": min(c["agree"] for c in v)}
                for v in docs.values()]
    field_rows = [{"y": float(c["correct"]), "f": c["agree"]} for c in cases]
    rng = random.Random(1)
    out = {}
    for name, rows, ns in [("field_accuracy", field_rows, PPI_NS), ("doc_success", doc_rows, [25, 50, 100])]:
        truth = fmean(r["y"] for r in rows)
        res = {}
        for n in ns:
            cov_p = cov_c = 0
            w_p, w_c = [], []
            for _ in range(PPI_TRIALS):
                idx = list(range(len(rows)))
                rng.shuffle(idx)
                lab, unl = [rows[i] for i in idx[:n]], [rows[i] for i in idx[n:]]
                yl = [r["y"] for r in lab]
                if len(set(yl)) < 2:
                    yl[0] = 1 - yl[0]  # avoid a zero-variance draw breaking the normal CI
                p = ppi_mean(yl, [r["f"] for r in lab], [r["f"] for r in unl])
                c = classical_mean(yl)
                cov_p += p.lo <= truth <= p.hi
                cov_c += c.lo <= truth <= c.hi
                w_p.append(p.width)
                w_c.append(c.width)
            res[n] = {"ppi_coverage": cov_p / PPI_TRIALS, "expert_only_coverage": cov_c / PPI_TRIALS,
                      "ppi_width": fmean(w_p), "expert_only_width": fmean(w_c),
                      "width_ratio": fmean(w_p) / fmean(w_c)}
        out[name] = {"truth": truth, "population": len(rows), "by_n": res}
    return out


def plots(gate: dict, ppi: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    styles = {"codebook_sum": ("#8250df", "Codebook expected cost (sum over fields)"),
              "scalar_sum": ("#57606a", "Scalar expected errors (sum over fields)"),
              "codebook": ("#c297ff", "Codebook, weakest field"),
              "scalar": ("#afb8c1", "Scalar, weakest field")}
    for metric, ax, label in [("precision", axes[0], "Auto-posted invoices fully correct"),
                              ("cost_per_doc", axes[1], "Severity-weighted error cost per posted invoice")]:
        for m, (color, name) in styles.items():
            xs = COVERAGES
            ys = [gate["gate"][m][f"{c}_{metric}"]["mean"] for c in COVERAGES]
            es = [gate["gate"][m][f"{c}_{metric}"]["sd"] for c in COVERAGES]
            ax.errorbar(xs, ys, yerr=es, marker="o", color=color, label=name, capsize=3, lw=1.5)
        ax.axhline(gate["gate"]["no_gate"][metric]["mean"], color="#cf222e", ls="--", lw=1,
                   label="No gate (post everything)")
        ax.set_xlabel("Straight-through rate (share of invoices auto-posted)")
        ax.set_ylabel(label)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    fig.savefig(HERE / "figures" / "gate_tradeoff.png", dpi=200)

    fig, ax = plt.subplots(figsize=(5, 3.5))
    by_n = ppi["field_accuracy"]["by_n"]
    ns = sorted(by_n, key=int)
    ax.plot(ns, [by_n[n]["expert_only_width"] * 100 for n in ns], "o-", color="#57606a", label="Expert labels only")
    ax.plot(ns, [by_n[n]["ppi_width"] * 100 for n in ns], "o-", color="#8250df", label="PPI++ (experts + agreement score)")
    ax.set_xscale("log")
    ax.set_xticks(ns, [str(n) for n in ns])
    ax.set_xlabel("Expert-labelled field cases")
    ax.set_ylabel("95% CI width (points)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / "figures" / "ppi_width.png", dpi=200)


def main() -> None:
    cases = build_cases()
    print(f"{len(cases)} field cases, {len(by_doc(cases))} documents, "
          f"{sum(not c['correct'] for c in cases)} errors")
    gate = gate_experiment(cases)
    ppi = ppi_experiment(cases)
    (d.RESULTS / "reward_gate_ppi.json").write_text(json.dumps({"gate": gate, "ppi": ppi}, indent=2))
    plots(gate, ppi)

    cal = gate["calibration"]
    print("\n## Reward model quality on held-out clusters (mean over", SPLITS, "splits)\n")
    print("| Detector | AUROC | ECE |")
    print("|---|---|---|")
    for code in WEIGHT:
        print(f"| {code} | {cal[f'{code}_auroc']['mean']:.3f} | {cal[f'{code}_ece']['mean']:.3f} |")
    print(f"| scalar P(error) | {cal['scalar_error_auroc']['mean']:.3f} | {cal['scalar_error_ece']['mean']:.3f} |")
    print(f"| codebook 1 - reward, as P(error) ranker | {cal['codebook_error_auroc']['mean']:.3f} | |")

    g = gate["gate"]
    print("\n## Gate: auto-post invoices whose weakest field clears the threshold\n")
    print(f"No gate: {g['no_gate']['precision']['mean']:.1%} fully correct, "
          f"cost/doc {g['no_gate']['cost_per_doc']['mean']:.3f}\n")
    print("| Straight-through | Method | Fully correct | Cost / posted doc | Invented / posted doc |")
    print("|---|---|---|---|---|")
    for cov in COVERAGES:
        for m in METHODS:
            r = g[m]
            print(f"| {cov:.0%} | {m} | {r[f'{cov}_precision']['mean']:.1%} ± {r[f'{cov}_precision']['sd']:.1%} "
                  f"| {r[f'{cov}_cost_per_doc']['mean']:.3f} | {r[f'{cov}_invented_slips']['mean']:.3f} |")
    print("\n## Paired difference, codebook minus scalar (2.5-97.5% over splits; share of splits > 0)\n")
    print("| Straight-through | Fully correct | Cost / posted doc | Invented / posted doc |")
    print("|---|---|---|---|")
    for a, b in DIFFS:
        print(f"\n{a} - {b}:")
        for cov in COVERAGES:
            r = g[f"{a}_minus_{b}"]
            cells = []
            for name, scale in [("precision", 100), ("cost_per_doc", 1), ("invented_slips", 1)]:
                x = r[f"{cov}_{name}"]
                cells.append(f"{x['mean'] * scale:+.3g} [{x['lo'] * scale:+.3g}, {x['hi'] * scale:+.3g}]; "
                             f"{x['share_positive']:.0%}")
            print(f"| {cov:.0%} | " + " | ".join(cells) + " |")

    for name, block in ppi.items():
        print(f"\n## PPI++: {name} (truth {block['truth']:.3f}, N = {block['population']}, "
              f"{PPI_TRIALS} draws)\n")
        print("| Expert labels | PPI coverage | Expert-only coverage | PPI width | Expert-only width | Ratio |")
        print("|---|---|---|---|---|---|")
        for n, r in block["by_n"].items():
            print(f"| {n} | {r['ppi_coverage']:.1%} | {r['expert_only_coverage']:.1%} | {r['ppi_width'] * 100:.1f} "
                  f"| {r['expert_only_width'] * 100:.1f} | {r['width_ratio']:.0%} |")


if __name__ == "__main__":
    main()
