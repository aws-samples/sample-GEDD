"""Expert review kit: GEDD review of the fine-tune's remaining errors, with double labelling.

  export   writes review/review_sheet_{reviewer}.csv. Every remaining error of the fine-tune,
           plus a random 10% of its correct fields as controls (so reviewers can't assume every
           row is wrong). A random --overlap share of rows goes to both reviewers.
  score    reads the filled sheets and reports
             * inter-annotator agreement: Krippendorff's alpha on verdict and on failure code,
               on the double-labelled rows;
             * the verdict breakdown (real error / acceptable variant / label gap);
             * round-1 accuracy re-scored under the corrected labels, for every system.

Verdicts: real_error | acceptable_variant | label_gap | correct
Needs splits/test.jsonl (gold text) from 01_build_splits.py; the gold text is not redistributed.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "grounded-evals" / "src"))

import dl_common as d  # noqa: E402

from grounded_evals.stats import krippendorff_alpha_nominal  # noqa: E402

TARGET = "glm_sft_1344"
SYSTEMS = ["glm", "glm_1344", "glm_rules", "glm_rules_ocr", "glm_sft_1344"]
REVIEW = HERE / "review"
VERDICTS = {"real_error", "acceptable_variant", "label_gap", "correct"}
COLUMNS = ["row_id", "case_id", "doc", "field", "image", "prediction", "gold_labels",
           "verdict", "failure_code", "severity", "corrected_value", "notes"]


def export(overlap: float, controls: float, seed: int) -> None:
    if not (d.SPLITS / "test.jsonl").exists():
        raise SystemExit("splits/test.jsonl not found: download DocILE and run 01_build_splits.py first")
    gold = {r["id"]: r for r in d.load_split("test")}
    rng = random.Random(seed)
    rows = []
    for f in d.field_rows(TARGET):
        if f["score"] < 1 or rng.random() < controls:
            g = gold[f["doc"]]["gold"][f["field"]]
            rows.append({"case_id": f["id"], "doc": f["doc"], "field": f["field"],
                         "image": str(d.image_path(f["doc"])), "prediction": json.dumps(f["pred"]),
                         "gold_labels": json.dumps(g[:3])})
    rng.shuffle(rows)
    for i, r in enumerate(rows):
        r["row_id"] = f"r{i:04d}"
    shared = set(rng.sample(range(len(rows)), round(overlap * len(rows))))
    rest = [i for i in range(len(rows)) if i not in shared]
    sheets = {"A": sorted(shared | set(rest[::2])), "B": sorted(shared | set(rest[1::2]))}
    REVIEW.mkdir(exist_ok=True)
    for name, idx in sheets.items():
        with (REVIEW / f"review_sheet_{name}.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS)
            w.writeheader()
            for i in idx:
                w.writerow({c: rows[i].get(c, "") for c in COLUMNS})
    print(f"{len(rows)} rows (errors + controls); {len(shared)} double-labelled; sheets in {REVIEW}/")


def read_sheet(path: Path) -> dict[str, dict]:
    with path.open() as fh:
        out = {}
        for r in csv.DictReader(fh):
            v = r["verdict"].strip()
            if v and v not in VERDICTS:
                raise SystemExit(f"{path.name} {r['row_id']}: unknown verdict {v!r}")
            if v:
                out[r["row_id"]] = r
        return out


def score() -> None:
    sheets = {p.stem.rsplit("_", 1)[1]: read_sheet(p) for p in sorted(REVIEW.glob("review_sheet_*.csv"))}
    if len(sheets) < 2:
        raise SystemExit("need at least two filled review sheets")
    rows = sorted(set().union(*sheets.values()))
    for key in ["verdict", "failure_code"]:
        units = [{name: (s[r][key].strip() or None) if r in s else None for name, s in sheets.items()}
                 for r in rows]
        paired = sum(1 for u in units if sum(v is not None for v in u.values()) >= 2)
        if paired:
            print(f"Krippendorff's alpha ({key}, {paired} double-labelled rows): "
                  f"{krippendorff_alpha_nominal(units):.3f}")

    # adjudicated verdict per case: agreement wins; disagreements go to the more conservative call
    order = ["real_error", "label_gap", "acceptable_variant", "correct"]
    final: dict[str, dict] = {}
    for r in rows:
        votes = [s[r] for s in sheets.values() if r in s]
        best = min(votes, key=lambda v: order.index(v["verdict"]))
        final[best["case_id"]] = best
    print("\nVerdicts on the fine-tune's reviewed cases:", dict(Counter(v["verdict"] for v in final.values())))

    # re-score every system: label_gap -> the corrected value becomes gold; acceptable_variant -> pass
    print("\n| System | Original | Corrected labels | Change |")
    print("|---|---|---|---|")
    for t in SYSTEMS:
        fields = d.field_rows(t)
        orig = sum(f["score"] >= 1 for f in fields) / len(fields)
        fixed = 0
        for f in fields:
            v = final.get(f["id"])
            ok = f["score"] >= 1
            if v and t == TARGET and v["verdict"] in {"acceptable_variant", "correct"}:
                ok = True
            if v and v["verdict"] == "label_gap":
                cv = v["corrected_value"].strip()
                ok = d.match(f["field"], f["pred"], [cv] if cv and cv.lower() != "null" else [])
            fixed += ok
        print(f"| {t} | {orig:.1%} | {fixed / len(fields):.1%} | {(fixed / len(fields) - orig) * 100:+.1f} |")
    print("\nNote: acceptable variants are only adjudicated for the reviewed system; report both numbers.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["export", "score"])
    ap.add_argument("--overlap", type=float, default=0.2, help="share of rows both reviewers label")
    ap.add_argument("--controls", type=float, default=0.1, help="share of correct fields added")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    export(a.overlap, a.controls, a.seed) if a.step == "export" else score()


if __name__ == "__main__":
    main()
