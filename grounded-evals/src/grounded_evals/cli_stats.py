"""CLI commands for GEDD statistics and the codebook reward model.

grounded-evals stats compare SYSTEM.jsonl ... BASELINE.jsonl
grounded-evals stats ppi LABELLED.jsonl UNLABELLED.jsonl
grounded-evals reward score CODEBOOK.yaml JUDGE.jsonl
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click
import yaml  # type: ignore[import-untyped]

from grounded_evals.reward import CodebookRewardModel, FailureCode, GatePolicy
from grounded_evals.stats import compare, holm, minimum_detectable_effect, ppi_mean
from grounded_evals.stats.ppi import classical_mean


def _read_jsonl(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(Path(path).read_text().splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise click.ClickException(f"{path}:{i}: invalid JSON ({exc.msg})") from exc
    return rows


def _outcomes(
    path: str, id_key: str, outcome_key: str, group_key: str, threshold: float
) -> dict[str, tuple[bool, Any]]:
    out: dict[str, tuple[bool, Any]] = {}
    for row in _read_jsonl(path):
        try:
            out[str(row[id_key])] = (float(row[outcome_key]) >= threshold, row[group_key])
        except KeyError as exc:
            raise click.ClickException(f"{path}: row missing key {exc}") from exc
    return out


@click.group()
def stats() -> None:
    """Significance, power and PPI estimates for GEDD evaluations."""


@stats.command("compare")
@click.argument("systems", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--id-key", default="id", show_default=True, help="Case id field.")
@click.option("--outcome-key", default="score", show_default=True, help="Per-case score field.")
@click.option("--group-key", default="cluster", show_default=True, help="Cluster/group field.")
@click.option("--threshold", default=1.0, show_default=True, help="Score counted as correct.")
@click.option("--alpha", default=0.05, show_default=True)
@click.option("--reps", default=5000, show_default=True, help="Bootstrap resamples.")
@click.option("--json", "as_json", is_flag=True, help="Print machine-readable JSON.")
def stats_compare(
    systems: tuple[str, ...],
    id_key: str,
    outcome_key: str,
    group_key: str,
    threshold: float,
    alpha: float,
    reps: int,
    as_json: bool,
) -> None:
    """Compare every SYSTEM against the last file (the baseline) on shared cases.

    Each file is JSONL with one row per case. A gain is significant only if the exact McNemar
    test (Holm-adjusted across all comparisons) and the cluster bootstrap interval agree.
    """
    if len(systems) < 2:
        raise click.UsageError("give at least one system and a baseline")
    *candidates, baseline = systems
    base = _outcomes(baseline, id_key, outcome_key, group_key, threshold)
    results = []
    for path in candidates:
        cand = _outcomes(path, id_key, outcome_key, group_key, threshold)
        ids = sorted(set(cand) & set(base))
        if not ids:
            raise click.ClickException(f"{path} shares no case ids with {baseline}")
        c = compare(
            [cand[i][0] for i in ids],
            [base[i][0] for i in ids],
            [base[i][1] for i in ids],
            alpha=alpha,
            reps=reps,
        )
        results.append((path, c))
    adjusted = holm([c.mcnemar.p_value for _, c in results])
    rows: list[dict[str, Any]] = []
    for (path, c), p_holm in zip(results, adjusted, strict=True):
        rows.append(
            {
                "system": path,
                "baseline": baseline,
                "n": c.n,
                "acc_system": c.acc_a,
                "acc_baseline": c.acc_b,
                "delta": c.delta,
                "only_system": c.mcnemar.only_a,
                "only_baseline": c.mcnemar.only_b,
                "p": c.mcnemar.p_value,
                "p_holm": p_holm,
                "ci": [c.bootstrap.lo, c.bootstrap.hi],
                "clusters": c.bootstrap.clusters,
                "mde_80": minimum_detectable_effect(c.cluster_se, alpha=alpha),
                "significant": p_holm < alpha and c.bootstrap.excludes_zero,
            }
        )
    if as_json:
        click.echo(json.dumps(rows, indent=2))
        return
    click.echo("| System | Acc | Baseline | Gap | p (Holm) | Cluster CI | MDE@80% | Real? |")
    click.echo("|---|---|---|---|---|---|---|---|")
    for r in rows:
        click.echo(
            f"| {Path(r['system']).name} | {r['acc_system']:.1%} | {r['acc_baseline']:.1%} "
            f"| {r['delta'] * 100:+.1f} | {r['p_holm']:.2g} "
            f"| [{r['ci'][0] * 100:+.1f}, {r['ci'][1] * 100:+.1f}] "
            f"| {r['mde_80'] * 100:.1f} | {'yes' if r['significant'] else 'no'} |"
        )


@stats.command("ppi")
@click.argument("labelled", type=click.Path(exists=True))
@click.argument("unlabelled", type=click.Path(exists=True))
@click.option("--y-key", default="expert", show_default=True, help="Expert label (0/1 or real).")
@click.option("--f-key", default="judge", show_default=True, help="Judge prediction field.")
@click.option("--alpha", default=0.05, show_default=True)
@click.option("--classic", is_flag=True, help="Use lambda = 1 (classic PPI) instead of PPI++.")
def stats_ppi(
    labelled: str, unlabelled: str, y_key: str, f_key: str, alpha: float, classic: bool
) -> None:
    """Estimate a rate from judge scores on all traces plus expert labels on a random sample."""
    lab = _read_jsonl(labelled)
    unl = _read_jsonl(unlabelled)
    try:
        y = [float(r[y_key]) for r in lab]
        fl = [float(r[f_key]) for r in lab]
        fu = [float(r[f_key]) for r in unl]
    except KeyError as exc:
        raise click.ClickException(f"row missing key {exc}") from exc
    est = ppi_mean(y, fl, fu, alpha=alpha, lam=1.0 if classic else None)
    base = classical_mean(y, alpha=alpha)
    level = int(round((1 - alpha) * 100))
    click.echo(f"PPI{'' if classic else '++'} estimate: {est.estimate:.4f}")
    click.echo(f"  {level}% CI [{est.lo:.4f}, {est.hi:.4f}]  (lambda = {est.lam:.2f})")
    click.echo(f"Expert-only: {base.estimate:.4f}  {level}% CI [{base.lo:.4f}, {base.hi:.4f}]")
    if base.width > 0:
        click.echo(f"Interval width vs expert-only: {est.width / base.width:.0%}")


@click.group()
def reward() -> None:
    """Score responses with the codebook-grounded reward model and gate them."""


def _load_codebook(path: str) -> list[FailureCode]:
    data = yaml.safe_load(Path(path).read_text())
    entries = data.get("codes", data) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise click.ClickException("codebook must be a list of codes or {codes: [...]}")
    try:
        return [
            FailureCode(
                code=str(e["code"]),
                severity=str(e.get("severity", "medium")),
                blocking=bool(e.get("blocking", False)),
                weight=e.get("weight"),
            )
            for e in entries
        ]
    except (KeyError, TypeError) as exc:
        raise click.ClickException(f"bad codebook entry: {exc}") from exc


@reward.command("score")
@click.argument("codebook", type=click.Path(exists=True))
@click.argument("judgements", type=click.Path(exists=True))
@click.option("-k", "k", default=1.0, show_default=True, help="Ensemble std penalty.")
@click.option("--allow", "allow_t", default=0.85, show_default=True)
@click.option("--revise", "revise_t", default=0.6, show_default=True)
@click.option("--block", "block_t", default=0.5, show_default=True)
@click.option("--uncertainty", "unc_t", default=0.15, show_default=True)
def reward_score(
    codebook: str,
    judgements: str,
    k: float,
    allow_t: float,
    revise_t: float,
    block_t: float,
    unc_t: float,
) -> None:
    """Emit one gate decision per row of JUDGEMENTS ({id, members: [{code: prob}, ...]})."""
    rm = CodebookRewardModel(_load_codebook(codebook), k=k)
    policy = GatePolicy(allow_t, revise_t, block_t, unc_t)
    for row in _read_jsonl(judgements):
        members = row.get("members")
        if not members:
            raise click.ClickException(f"row {row.get('id')!r} has no judge members")
        r = rm.score(members)
        d = policy.decide(r)
        click.echo(
            json.dumps(
                {
                    "id": row.get("id"),
                    "recommended_action": d.action.value,
                    "customer_visible_block": d.customer_visible_block,
                    "failure_code": d.failure_code,
                    "reward": round(r.reward, 4),
                    "reward_std": round(r.std, 4),
                    "reason": d.reason,
                }
            )
        )
