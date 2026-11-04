"""CLI tests for `stats compare`, `stats ppi` and `reward score`."""

from __future__ import annotations

import json
import random
from pathlib import Path

from click.testing import CliRunner

from grounded_evals.cli import main


def _write(path: Path, rows: list[dict]) -> str:
    path.write_text("\n".join(json.dumps(r) for r in rows))
    return str(path)


def test_stats_compare_json(tmp_path: Path) -> None:
    rng = random.Random(0)
    base = [{"id": i, "score": float(rng.random() < 0.6), "cluster": i // 10} for i in range(400)]
    better = [{"id": i, "score": float(rng.random() < 0.9), "cluster": i // 10} for i in range(400)]
    res = CliRunner().invoke(
        main,
        [
            "stats",
            "compare",
            _write(tmp_path / "a.jsonl", better),
            _write(tmp_path / "b.jsonl", base),
            "--reps",
            "300",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    (row,) = json.loads(res.output)
    assert row["significant"] and row["delta"] > 0.2 and row["p_holm"] < 1e-6


def test_stats_compare_needs_shared_ids(tmp_path: Path) -> None:
    a = _write(tmp_path / "a.jsonl", [{"id": 1, "score": 1, "cluster": 0}])
    b = _write(tmp_path / "b.jsonl", [{"id": 2, "score": 1, "cluster": 0}])
    res = CliRunner().invoke(main, ["stats", "compare", a, b])
    assert res.exit_code != 0 and "shares no case ids" in res.output


def test_stats_ppi(tmp_path: Path) -> None:
    rng = random.Random(1)
    y = [float(rng.random() < 0.3) for _ in range(1100)]
    f = [v if rng.random() < 0.9 else 1 - v for v in y]
    lab = _write(
        tmp_path / "l.jsonl", [{"expert": a, "judge": b} for a, b in zip(y[:100], f[:100])]
    )
    unl = _write(tmp_path / "u.jsonl", [{"judge": b} for b in f[100:]])
    res = CliRunner().invoke(main, ["stats", "ppi", lab, unl])
    assert res.exit_code == 0, res.output
    assert "PPI++ estimate" in res.output and "Expert-only" in res.output


def test_reward_score(tmp_path: Path) -> None:
    cb = tmp_path / "codebook.yaml"
    cb.write_text(
        "codes:\n  - {code: invented_value, severity: critical, blocking: true}\n"
        "  - {code: format_drift, severity: low}\n"
    )
    judged = _write(
        tmp_path / "j.jsonl",
        [{"id": "ok", "members": [{}]}, {"id": "bad", "members": [{"invented_value": 0.9}]}],
    )
    res = CliRunner().invoke(main, ["reward", "score", str(cb), judged])
    assert res.exit_code == 0, res.output
    out = {r["id"]: r for r in map(json.loads, res.output.splitlines())}
    assert out["ok"]["recommended_action"] == "allow"
    assert out["bad"]["recommended_action"] == "block"
    assert out["bad"]["failure_code"] == "invented_value"
