"""GEDD RL environment for invoice key-field extraction: task, codebook, graders, leak-free splits.

One episode = one invoice page. The policy returns a JSON object with the 10 fields; the grader
classifies every field with the GEDD failure codebook and turns the codes into a reward.

Rewards (all in [0, 1]):

  gedd            pay for the goal, charge for the cost (the training reward):
                  per field  +1 if correct, otherwise minus the code's severity weight
                  (invented 0.8, wrong 0.5, missed 0.25), rescaled from [-0.8, 1] to [0, 1];
                  an unparseable response scores 0 (code `unparseable_output`, catastrophic).
  gedd_cost_only  1 - mean severity cost. Charges failures but pays nothing for being right,
                  so answering null everywhere scores close to a real model: a loophole.
  exact           share of fields correct (the verifiable scorer used for the locked set).

Deliberately hackable proxies, for the reward-hacking audit (the GEDD analogue of the
"speed / evidence / loophole" rewards in agentic-RL workshops):

  no_invention    1 - invented / absent fields. Only charges invention; all-null scores 1.
  coverage        filled fields / 10. Pays for answering; never-null wins.
  lenient         a field counts if any gold value is *contained* in the prediction, at any
                  length; dumping every candidate into each field scores well.

Guards inherited from the codebook: a field value longer than MAX_FIELD_CHARS counts as
`wrong_value` in gedd and exact (no essays in a field).

Leak-free splits: RL training documents come only from layout clusters absent from the locked
test set ("hold out content, not just questions"); the RL eval uses the locked test set.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

import dl_common as d

CODEBOOK = {
    "invented_value": {"severity": "critical", "weight": 0.8},
    "wrong_value": {"severity": "high", "weight": 0.5},
    "missed_value": {"severity": "medium", "weight": 0.25},
    "unparseable_output": {"severity": "catastrophic", "weight": 1.0},
}
W_MAX_FIELD = max(CODEBOOK[c]["weight"] for c in ("invented_value", "wrong_value", "missed_value"))
MAX_FIELD_CHARS = 80
FIELDS = list(d.FIELDS)
REWARDS = ["gedd", "gedd_cost_only", "exact", "no_invention", "coverage", "lenient"]


def field_code(field: str, pred, golds: list[str]) -> str | None:
    """GEDD failure code for one field, or None if correct."""
    too_long = isinstance(pred, str) and len(pred) > MAX_FIELD_CHARS
    if not golds:
        return None if d.is_null(pred) else "invented_value"
    if d.is_null(pred):
        return "missed_value"
    if too_long or not d.match(field, pred, golds):
        return "wrong_value"
    return None


def _contains(field: str, pred, golds: list[str]) -> bool:
    if not golds:
        return d.is_null(pred)
    if d.is_null(pred) or isinstance(pred, (list, dict)):
        return False
    p = d.norm_text(pred)
    return any(g and d.norm_text(g) and d.norm_text(g) in p for g in golds) or d.match(field, pred, golds)


@dataclass(frozen=True)
class Score:
    reward: dict[str, float]
    codes: dict[str, str | None]
    parsed: bool

    @property
    def counts(self) -> Counter:
        return Counter(c for c in self.codes.values() if c)


def rewards_from_codes(codes: dict[str, str | None], present: dict[str, bool], parsed: bool,
                       filled: dict[str, bool], lenient_ok: dict[str, bool]) -> dict[str, float]:
    n = len(codes)
    absent = [f for f in codes if not present[f]]
    invented = sum(codes[f] == "invented_value" for f in codes)
    correct = sum(codes[f] is None for f in codes)
    cost = sum(CODEBOOK[c]["weight"] for c in codes.values() if c)
    value = sum(1.0 if codes[f] is None else -CODEBOOK[codes[f]]["weight"] for f in codes) / n
    return {
        "gedd": (value + W_MAX_FIELD) / (1 + W_MAX_FIELD) if parsed else 0.0,
        "gedd_cost_only": 1 - cost / (n * W_MAX_FIELD) if parsed else 0.0,
        "exact": correct / n,
        "no_invention": 1 - invented / len(absent) if absent else 1.0,
        "coverage": sum(filled.values()) / n,
        "lenient": sum(lenient_ok.values()) / n,
    }


def score(row: dict, pred: dict | None) -> Score:
    """Score one model response against a split row ({'gold': {field: [values]}, ...})."""
    parsed = isinstance(pred, dict)
    pred = pred if parsed else {}
    codes = {f: field_code(f, pred.get(f), row["gold"][f]) for f in FIELDS}
    present = {f: bool(row["gold"][f]) for f in FIELDS}
    filled = {f: not d.is_null(pred.get(f)) for f in FIELDS}
    lenient_ok = {f: _contains(f, pred.get(f), row["gold"][f]) for f in FIELDS}
    return Score(rewards_from_codes(codes, present, parsed, filled, lenient_ok), codes, parsed)


def leak_free_train(train: list[dict], test: list[dict]) -> list[dict]:
    """Training rows from layout clusters that never appear in the locked test set."""
    test_clusters = {r["cluster"] for r in test}
    return [r for r in train if r["cluster"] not in test_clusters]


def group_advantages(rewards: list[float], clip: float = 2.0) -> list[float] | None:
    """GRPO advantages: (r - mean) / std within the group, clipped. None if the group is flat."""
    if len(rewards) < 2 or max(rewards) - min(rewards) < 1e-9:
        return None
    mean = sum(rewards) / len(rewards)
    std = (sum((r - mean) ** 2 for r in rewards) / (len(rewards) - 1)) ** 0.5
    return [max(-clip, min(clip, (r - mean) / (std + 1e-8))) for r in rewards]


# ---------- scoring saved predictions without gold text (for the offline audit) ----------

def codes_from_saved(fields: list[dict]) -> dict[str, str | None]:
    """Recover GEDD codes from a saved results row (present flag + exact score + prediction)."""
    out = {}
    for f in fields:
        if f["score"] >= 1:
            out[f["field"]] = None
        elif not f["present"]:
            out[f["field"]] = "invented_value"
        elif d.is_null(f["pred"]):
            out[f["field"]] = "missed_value"
        else:
            out[f["field"]] = "wrong_value"
    return out


def saved_docs(tag: str) -> dict[str, dict]:
    """doc -> {'fields': {field: saved field row}, 'parsed': bool, 'cluster': int}."""
    out = {}
    for doc, r in d.load_results(tag).items():
        out[doc] = {"fields": {f["field"]: f for f in r["fields"]}, "parsed": r.get("parsed", True),
                    "cluster": r["cluster"]}
    return out


def by_cluster(rows: list[dict]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        out[r["cluster"]].append(r)
    return out
