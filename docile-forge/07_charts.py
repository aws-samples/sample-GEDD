"""Charts for the README and the deck (static PNGs). Palette validated with the dataviz validator (light mode)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import dl_common as d  # noqa: E402

FIG = d.HERE / "figures"
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#c9c8c2", "#e6e5e0"
BLUE, ORANGE = "#2a78d6", "#eb6834"   # categorical slots 1-2 (validated: CVD ΔE 24.7, normal 33.6)
SFT, BASE = "glm_sft_1344", "glm_1344"

plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "font.family": "Helvetica Neue", "font.size": 13, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False})


def acc(tag, pred=lambda f: True):
    fr = [f for f in d.field_rows(tag) if pred(f)]
    return sum(f["score"] for f in fr) / len(fr)


def pfmt(p):
    return f"{p:.0e}" if p < 0.001 else f"{p:.2f}"


def title(ax, t, sub=""):
    ax.set_title(t, loc="left", fontsize=17, fontweight="bold", color=INK, pad=28 if sub else 12)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=12, color=INK2, va="bottom")


def leaderboard():
    """Sample-deck style: every system, sorted, gap vs baseline with the significance verdict on the right."""
    rep = json.loads((d.RESULTS / "report.json").read_text())
    rows = [("Vision LoRA fine-tune (SFT on train docs)", SFT, BLUE, (SFT, BASE)),
            ("Harness B: rules + OCR text", "glm_rules_ocr", MUTED, ("glm_rules_ocr", "glm")),
            ("Harness A: rules in prompt", "glm_rules", MUTED, ("glm_rules", "glm")),
            ("GLM 5.3 Flash (baseline)", BASE, None, None)]
    fig, ax = plt.subplots(figsize=(12, 4.8))
    ys = list(range(len(rows)))[::-1]
    for y, (label, tag, c, pair) in zip(ys, rows):
        v = 100 * acc(tag)
        if c is None:  # baseline: hatched, the reference every other row is measured against
            ax.barh(y, v, height=0.58, color=SURFACE, edgecolor=ORANGE, hatch="///", lw=1.5)
        else:
            ax.barh(y, v, height=0.58, color=c)
        ax.text(v + 1, y, f"{v:.1f}%", va="center", fontsize=14, fontweight="bold" if tag == SFT else "normal")
        if pair:
            r = next(x for x in rep["comparisons"] if x["a"] == pair[0] and x["b"] == pair[1] and x["subset"] == "all")
            verdict = "significant" if r["significant"] else "n.s."
            ax.text(103, y, f"{100 * r['bootstrap']['delta']:+.1f} pp  {verdict}", va="center", fontsize=13,
                    fontweight="bold" if tag == SFT else "normal", color=INK if tag == SFT else INK2, clip_on=False)
    ax.set_yticks(ys, [r[0] for r in rows], fontsize=13)
    ax.set_xlim(0, 100)
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Fields correct on the DocILE test set (%)")
    title(ax, "Before vs after: does SFT beat the baseline?", "5,000 field cases from 500 held-out documents · gap vs baseline on the right")
    fig.subplots_adjust(left=0.31, right=0.8, top=0.82, bottom=0.14)
    fig.savefig(FIG / "leaderboard.png", dpi=200)


def teammate():
    if not (d.RESULTS / "teammate_ocr.json").exists():
        return
    """Teammate's OCR-input run. Separate chart: different input, test set and metric from ours."""
    t = json.loads((d.RESULTS / "teammate_ocr.json").read_text())
    ms = sorted(t["models"], key=lambda m: m["f1_fuzzy"], reverse=True)
    fig, ax = plt.subplots(figsize=(12, 4.8))
    ys, h = list(range(len(ms)))[::-1], 0.36
    for y, m in zip(ys, ms):
        ax.barh(y + h / 2 + 0.01, m["f1_fuzzy"], height=h, color=BLUE)
        ax.barh(y - h / 2 - 0.01, m["f1_exact"], height=h, color=ORANGE)
        ax.text(m["f1_fuzzy"] + 1, y + h / 2, f"{m['f1_fuzzy']:.1f}%", va="center", fontsize=12.5, fontweight="bold")
        ax.text(m["f1_exact"] + 1, y - h / 2, f"{m['f1_exact']:.1f}%", va="center", fontsize=12.5, color=INK2)
        ax.text(103, y, f"p50 {m['p50_s']:.2f}s · p95 {m['p95_s']:.2f}s", va="center", fontsize=12, color=INK2, clip_on=False)
    ax.set_yticks(ys, [m["name"] + " (fine-tuned)" for m in ms], fontsize=13)
    ax.set_xlim(0, 100)
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Field F1 on 200 held-out invoices (%)")
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)],
              labels=["Fuzzy match", "Exact match"], frameon=False, loc="lower right")
    title(ax, "OCR-text route: three fine-tuned open models", "Teammate's run · different input, test set and metric from the image run — compare rows, not charts")
    fig.subplots_adjust(left=0.24, right=0.8, top=0.82, bottom=0.14)
    fig.savefig(FIG / "teammate_ocr.png", dpi=200)


def significance():
    rep = json.loads((d.RESULTS / "report.json").read_text())
    want = [(SFT, BASE, "all", "Fine-tune vs baseline", BLUE),
            (SFT, BASE, "unseen layouts", "Fine-tune vs baseline,\nunseen layouts only", BLUE),
            ("glm_rules_ocr", "glm", "all", "Harness B vs baseline", ORANGE),
            ("glm_rules_ocr", "glm", "unseen layouts", "Harness B vs baseline,\nunseen layouts only", ORANGE),
            ("glm_rules", "glm", "all", "Harness A vs baseline", ORANGE)]
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ys = list(range(len(want)))[::-1]
    for y, (a, b, sub, label, c) in zip(ys, want):
        r = next(x for x in rep["comparisons"] if x["a"] == a and x["b"] == b and x["subset"] == sub)
        bs = r["bootstrap"]
        lo, hi, mid = 100 * bs["lo"], 100 * bs["hi"], 100 * bs["delta"]
        ax.plot([lo, hi], [y, y], color=c, lw=2.5, solid_capstyle="round")
        ax.plot(mid, y, "o", ms=10, color=c, mec=SURFACE, mew=2)
        ax.text(hi + 0.4, y, f"{mid:+.1f}  [{lo:+.1f}, {hi:+.1f}]  p={pfmt(r['mcnemar']['p'])}", va="center",
                fontsize=11.5, color=INK2)
    ax.axvline(0, color=INK, lw=1.2)
    ax.text(0.2, len(want) - 0.45, "tie", fontsize=11, color=INK2)
    ax.set_yticks(ys, [w[3] for w in want], fontsize=12)
    ax.set_xlim(-4.5, 21)
    ax.set_ylim(-0.6, len(want) - 0.3)
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Gap in field accuracy, points (dot) with 95% layout-cluster bootstrap interval (line)")
    title(ax, "Is it real? Right of the line is a real gain; crossing it is luck",
          "5,000 resampled test sets of the 204 layout clusters · McNemar p on the right")
    fig.tight_layout()
    fig.savefig(FIG / "significance.png", dpi=200)


def mcnemar():
    rep = json.loads((d.RESULTS / "report.json").read_text())
    want = [(SFT, BASE, "Fine-tune"), ("glm_rules_ocr", "glm", "Harness B"), ("glm_rules", "glm", "Harness A")]
    fig, ax = plt.subplots(figsize=(11, 4.6))
    w = 0.36
    for i, (a, b, label) in enumerate(want):
        r = next(x for x in rep["comparisons"] if x["a"] == a and x["b"] == b and x["subset"] == "all")
        oa, ob = r["mcnemar"]["only_a"], r["mcnemar"]["only_b"]
        ax.bar(i - w / 2 - 0.01, oa, w, color=BLUE)
        ax.bar(i + w / 2 + 0.01, ob, w, color=ORANGE)
        ax.text(i - w / 2, oa + 12, str(oa), ha="center", fontsize=13, fontweight="bold")
        ax.text(i + w / 2, ob + 12, str(ob), ha="center", fontsize=13)
    ax.set_xticks(range(len(want)), [f"{w_[2]} vs baseline" for w_ in want], fontsize=13)
    ax.yaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel("Field cases")
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)],
              labels=["Only the change was right", "Only the baseline was right"], frameon=False, loc="upper right")
    title(ax, "Who wins the disagreements?", "McNemar's test ignores fields both get right or both get wrong")
    fig.tight_layout()
    fig.savefig(FIG / "mcnemar.png", dpi=200)


def per_field():
    rows = sorted(d.FIELDS, key=lambda k: acc(BASE, lambda f: f["field"] == k))
    fig, ax = plt.subplots(figsize=(11, 6))
    for y, k in enumerate(rows):
        b, s = 100 * acc(BASE, lambda f: f["field"] == k), 100 * acc(SFT, lambda f: f["field"] == k)
        ax.plot([b, s], [y, y], color=MUTED, lw=2, zorder=1)
        ax.plot(b, y, "o", ms=10, color=ORANGE, mec=SURFACE, mew=2, zorder=2)
        ax.plot(s, y, "o", ms=10, color=BLUE, mec=SURFACE, mew=2, zorder=2)
        ax.text(s + 1.2, y, f"{s:.0f}%", va="center", fontsize=11.5, fontweight="bold")
        ax.text(b - 1.2, y, f"{b:.0f}%", va="center", ha="right", fontsize=11.5, color=INK2)
    ax.set_yticks(range(len(rows)), rows, fontsize=12)
    ax.set_xlim(50, 102)
    ax.set_ylim(-0.6, len(rows) + 0.4)
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Accuracy on the 500 test documents, %")
    ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", ms=10, color=ORANGE),
                       plt.Line2D([], [], marker="o", ls="", ms=10, color=BLUE)],
              labels=["Baseline", "Fine-tune"], frameon=False, loc="upper left", ncol=2, bbox_to_anchor=(0, 1.0))
    title(ax, "Every field improves", "Biggest gains where the labelling rules matter: order number, currency, vendor")
    fig.tight_layout()
    fig.savefig(FIG / "per_field.png", dpi=200)


def loss():
    path = next(Path(d.HERE / "sft_logs").glob("docile-glm-sft-*/metrics.jsonl"))
    m = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.plot([r["step"] for r in m], [r["loss"] for r in m], color=BLUE, lw=2)
    ax.yaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.set_xlabel("Training step (batch of 16 documents)")
    ax.set_ylabel("Loss per answer token")
    ax.set_ylim(0, None)
    title(ax, "Training loss", "1,400 documents, 1 epoch, 88 steps, LoRA rank 16, learning rate 1e-4")
    fig.tight_layout()
    fig.savefig(FIG / "loss_curve.png", dpi=200)


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    for f in (leaderboard, teammate, significance, mcnemar, per_field, loss):
        f()
    print("wrote", sorted(p.name for p in FIG.glob("*.png")))


def doc_success():
    """Whole-document success: what automation actually needs (every field right, no human touch)."""
    rows = [("Baseline", BASE, None), ("Harness B: rules + OCR", "glm_rules_ocr", MUTED), ("Vision LoRA fine-tune", SFT, BLUE)]
    fig, ax = plt.subplots(figsize=(12, 4.2))
    ys = list(range(len(rows)))[::-1]
    for y, (label, tag, c) in zip(ys, rows):
        R = list(d.load_results(tag).values())
        v = 100 * sum(all(f["score"] for f in r["fields"]) for r in R) / len(R)
        if c is None:
            ax.barh(y, v, height=0.58, color=SURFACE, edgecolor=ORANGE, hatch="///", lw=1.5)
        else:
            ax.barh(y, v, height=0.58, color=c)
        ax.text(v + 1, y, f"{v:.1f}%", va="center", fontsize=15, fontweight="bold" if tag == SFT else "normal")
    ax.set_yticks(ys, [r[0] for r in rows], fontsize=13)
    ax.set_xlim(0, 100)
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Test documents with all 10 fields correct (%)")
    title(ax, "Field accuracy compounds: 3x more invoices need no human touch", "500 held-out documents · a document is automatable only if every field is right")
    fig.subplots_adjust(left=0.22, right=0.95, top=0.8, bottom=0.17)
    fig.savefig(FIG / "doc_success.png", dpi=200)


if __name__ == "__main__":
    doc_success()


def invoiceroute():
    return  # teammate data not published
    """Teammate's InvoiceRoute (OCR text -> JSON): DeepSeek V4.1 Flash baseline vs fine-tuned, 200 held-out docs."""
    metrics = [("Field F1, fuzzy", 47.53, 78.33), ("Field F1, exact", 42.22, 70.17), ("Doc success (all fields exact)", 0.0, 4.5)]
    fig, ax = plt.subplots(figsize=(12, 4.6))
    ys, h = list(range(len(metrics)))[::-1], 0.36
    for y, (m, b, f) in zip(ys, metrics):
        ax.barh(y + h / 2 + 0.01, f, height=h, color=BLUE)
        ax.barh(y - h / 2 - 0.01, max(b, 0.001), height=h, color=SURFACE, edgecolor=ORANGE, hatch="///", lw=1.5)
        ax.text(f + 1, y + h / 2, f"{f:.1f}%", va="center", fontsize=13, fontweight="bold")
        ax.text(b + 1, y - h / 2, f"{b:.1f}%", va="center", fontsize=13, color=INK2)
        ax.text(103, y, f"{f - b:+.1f} pp", va="center", fontsize=14, fontweight="bold", clip_on=False)
    ax.set_yticks(ys, [m[0] for m in metrics], fontsize=13)
    ax.set_xlim(0, 100)
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("200 held-out documents, OCR text input (%)")
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BLUE),
                       plt.Rectangle((0, 0), 1, 1, facecolor=SURFACE, edgecolor=ORANGE, hatch="///")],
              labels=["Fine-tuned", "Baseline"], frameon=False, loc="lower right")
    title(ax, "InvoiceRoute: DeepSeek V4.1 Flash, before vs after", "Teammate's run · OCR text to JSON · exact field F1 +27.95 pp")
    fig.subplots_adjust(left=0.25, right=0.88, top=0.82, bottom=0.15)
    fig.savefig(FIG / "invoiceroute.png", dpi=200)


if __name__ == "__main__":
    invoiceroute()
