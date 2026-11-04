"""Reward audit before any RL: does any candidate reward pay a degenerate policy?

"Write and read the grader first": every reward in rl_env.py is scored on the same 500 locked
test invoices for
  * the real systems (base model, two prompt harnesses, the SFT fine-tune), and
  * three degenerate policies built from the saved predictions, each the cheapest way to game
    one kind of reward:
      ALL_NULL    answer null everywhere (abstention)
      NEVER_NULL  the base model, but never abstain: every null becomes a blind guess (the
                  field's most common answer across documents), assumed wrong
      DUMP        put every distinct candidate any of the five systems gave into the field
                  (an "essay"); stands in for a policy that lists everything plausible on the page

A reward is *hackable* if a degenerate policy scores at or above the base model under it: RL
started from the base model would then be paid to drift toward the degenerate behaviour.

Also reports headroom ("check the model sometimes succeeds"): field and invoice accuracy if we
could pick the best of the five systems per case (pass@any), versus the best single system.

No API calls, no gold text: field outcomes are recovered from the saved per-case scores. The
lenient reward for real systems is a lower bound (exact matches only).
Writes results/reward_audit.json and figures/reward_audit.png.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import fmean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "grounded-evals" / "src"))

import dl_common as d  # noqa: E402
import rl_env as env  # noqa: E402

SYSTEMS = {"glm_1344": "Base model", "glm_rules": "Harness A (rules)",
           "glm_rules_ocr": "Harness B (rules + OCR)", "glm_sft_1344": "SFT fine-tune"}
DONORS = ["glm_sft_1344", "glm_rules_ocr", "glm_rules", "glm_1344", "glm"]  # candidate pool for DUMP
HACKS = {"ALL_NULL": "All null (abstain)", "NEVER_NULL": "Never null (always answer)",
         "DUMP": "Dump every candidate"}


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


def _stable(obj):
    if isinstance(obj, float):
        return float(f"{obj:.10g}")
    if isinstance(obj, dict):
        return {k: _stable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_stable(v) for v in obj]
    return obj


def system_rewards(doc: dict) -> dict[str, float]:
    fields = list(doc["fields"].values())
    codes = env.codes_from_saved(fields)
    present = {f["field"]: f["present"] for f in fields}
    filled = {f["field"]: not d.is_null(f["pred"]) for f in fields}
    lenient = {f["field"]: f["score"] >= 1 for f in fields}  # lower bound without gold text
    return env.rewards_from_codes(codes, present, doc["parsed"], filled, lenient)


def hack_rewards(name: str, doc_id: str, docs: dict[str, dict[str, dict]]) -> dict[str, float]:
    """Field outcomes for a degenerate policy on one invoice."""
    ref = docs["glm_1344"][doc_id]["fields"]
    codes, filled, lenient = {}, {}, {}
    present = {f: ref[f]["present"] for f in ref}
    for f in ref:
        cands = [(t, docs[t][doc_id]["fields"][f]) for t in DONORS if doc_id in docs[t]]
        nonnull = [(t, x) for t, x in cands if not d.is_null(x["pred"])]
        if name == "ALL_NULL":
            codes[f] = None if not present[f] else "missed_value"
            filled[f], lenient[f] = False, not present[f]
        elif name == "NEVER_NULL":
            mine = ref[f]
            if d.is_null(mine["pred"]):  # a blind guess: invented if absent, wrong if present
                codes[f] = "invented_value" if not present[f] else "wrong_value"
                filled[f], lenient[f] = True, False
            else:
                codes[f] = env.codes_from_saved([mine])[f]
                filled[f], lenient[f] = True, mine["score"] >= 1
        else:  # DUMP
            distinct = {norm(f, x["pred"]) for _, x in nonnull}
            if not nonnull:
                codes[f] = None if not present[f] else "missed_value"
            elif len(distinct) == 1:
                codes[f] = env.codes_from_saved([nonnull[0][1]])[f]
            else:
                codes[f] = "invented_value" if not present[f] else "wrong_value"
            filled[f] = bool(nonnull)
            # contains-matching credits the dump if any listed candidate was right
            lenient[f] = (not present[f] and not nonnull) or any(x["score"] >= 1 and x["present"] for _, x in nonnull)
    return env.rewards_from_codes(codes, present, True, filled, lenient)


def main() -> None:
    docs = {t: env.saved_docs(t) for t in set(SYSTEMS) | set(DONORS)}
    ids = sorted(set.intersection(*(set(v) for v in docs.values())))
    table: dict[str, dict[str, float]] = {}
    for t, name in SYSTEMS.items():
        rows = [system_rewards(docs[t][i]) for i in ids]
        table[name] = {r: fmean(x[r] for x in rows) for r in env.REWARDS}
    for h, name in HACKS.items():
        rows = [hack_rewards(h, i, docs) for i in ids]
        table[name] = {r: fmean(x[r] for x in rows) for r in env.REWARDS}

    base, sft = table["Base model"], table["SFT fine-tune"]
    hackable = {r: [h for h in HACKS.values() if table[h][r] >= base[r]] for r in env.REWARDS}
    beats_sft = {r: [h for h in HACKS.values() if table[h][r] >= sft[r]] for r in env.REWARDS}
    # safety margin: how far the best degenerate policy sits below the base model (negative = hackable)
    margin = {r: base[r] - max(table[h][r] for h in HACKS.values()) for r in env.REWARDS}

    # headroom: best of the five systems per field / per invoice vs the best single system
    field_any = fmean(any(docs[t][i]["fields"][f]["score"] >= 1 for t in DONORS)
                      for i in ids for f in env.FIELDS)
    doc_any = fmean(all(any(docs[t][i]["fields"][f]["score"] >= 1 for t in DONORS) for f in env.FIELDS)
                    for i in ids)
    doc_any_one = fmean(any(all(docs[t][i]["fields"][f]["score"] >= 1 for f in env.FIELDS) for t in DONORS)
                        for i in ids)
    best_single = max(fmean(docs[t][i]["fields"][f]["score"] >= 1 for i in ids for f in env.FIELDS)
                      for t in DONORS)
    headroom = {"field_best_single": best_single, "field_pass_at_any": field_any,
                "invoice_pass_at_any_system": doc_any_one, "invoice_pass_at_any_field_mix": doc_any}

    out = {"documents": len(ids), "rewards": table, "hackable_vs_base": hackable,
           "hack_beats_sft": beats_sft, "margin_vs_best_hack": margin,
           "headroom": headroom}
    (d.RESULTS / "reward_audit.json").write_text(json.dumps(_stable(out), indent=2))

    cols = env.REWARDS
    print(f"## Same {len(ids)} invoices, six rewards\n")
    print("| Policy | " + " | ".join(cols) + " |")
    print("|---|" + "---|" * len(cols))
    for name, row in table.items():
        cells = []
        for r in cols:
            flag = " ⚠" if name in HACKS.values() and row[r] >= base[r] else ""
            cells.append(f"{row[r]:.3f}{flag}")
        print(f"| {name} | " + " | ".join(cells) + " |")
    print("\n⚠ = degenerate policy scores at or above the base model under this reward (hackable)\n")
    for r in cols:
        print(f"- {r}: margin over best hack {margin[r]:+.3f}; hackable by {hackable[r] or 'none'}; "
              f"a hack beats SFT: {beats_sft[r] or 'none'}")
    print(f"\nHeadroom: best single system {best_single:.1%} of fields; pass@any of 5 systems {field_any:.1%}. "
          f"Invoices fully right by at least one system: {doc_any_one:.1%}.")
    plot(table)


def plot(table: dict[str, dict[str, float]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rewards = env.REWARDS
    names = list(table)
    m = np.array([[table[n][r] for r in rewards] for n in names])
    fig, ax = plt.subplots(figsize=(9, 4.2))
    im = ax.imshow(m, cmap="Purples", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(rewards)), rewards, rotation=20)
    ax.set_yticks(range(len(names)), names)
    base = table["Base model"]
    for i, n in enumerate(names):
        for j, r in enumerate(rewards):
            hack = n in HACKS.values() and table[n][r] >= base[r]
            ax.text(j, i, f"{m[i, j]:.2f}{' ⚠' if hack else ''}", ha="center", va="center", fontsize=9,
                    color="white" if m[i, j] > 0.6 else "black", fontweight="bold" if hack else "normal")
    ax.axhline(len(SYSTEMS) - 0.5, color="#cf222e", lw=1.5)
    ax.set_title("Same invoices, six rewards (⚠ = a degenerate policy matches or beats the base model)",
                 fontsize=10, loc="left")
    fig.colorbar(im, ax=ax, fraction=0.03)
    fig.tight_layout()
    fig.savefig(HERE / "figures" / "reward_audit.png", dpi=200)


if __name__ == "__main__":
    main()
