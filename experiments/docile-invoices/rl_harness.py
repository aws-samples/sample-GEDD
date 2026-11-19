#!/usr/bin/env python3
"""Trainer-agnostic RL eval harness for the GEDD invoice environment.

The harness owns everything except the gradient step: sampling groups from a policy, scoring every
try under *all* rewards in `rl_env.py`, GRPO group advantages, per-step logging of rewards and
failure-code counts, headroom (flat-group share) and a reward-hacking tripwire. Any RL trainer
(TRL, verl, OpenRLHF, your own loop) plugs in by implementing two small protocols:

  Policy   sample(row, n, temperature) -> list[str]     completions for one invoice
  Trainer  policy() -> Policy                           the current weights, for the next step
           update(groups: list[Group]) -> dict          one optimiser step from scored groups

Token-level trainers keep their own token ids and logprobs; the harness only needs the decoded
text of each try, and returns one advantage per try in the same order the policy produced them.

Without a trainer the harness is an eval: it measures headroom under a reward before any RL is
spent (do the tries in a group differ, and does the reward tell them apart?).

  uv run python rl_harness.py headroom --reward gedd --tasks 16 --group 4
  uv run python rl_harness.py headroom --reward no_invention --tasks 16 --group 4

The policy for `headroom` is any OpenAI-compatible endpoint (vLLM, SGLang, LiteLLM, a gateway in
front of a managed service): set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL (see dl_common.py).

Tripwire: if the trained reward rises while the gold `exact` score falls for `patience` steps in a
row, the harness stops and writes the worst-scoring tries of the last step for expert review. This
is the GEDD rule "if the reward rises but locked-set accuracy doesn't, send those cases to experts",
automated.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from statistics import fmean
from typing import Protocol

import dl_common as d
import rl_env as env


class Policy(Protocol):
    def sample(self, row: dict, n: int, temperature: float) -> list[str]: ...


@dataclass
class Group:
    row: dict
    texts: list[str]
    scores: list[env.Score]
    advantages: list[float] | None  # None: flat group, carries no learning signal


class Trainer(Protocol):
    def policy(self) -> Policy: ...

    def update(self, groups: list[Group]) -> dict: ...


def score_group(row: dict, texts: Sequence[str], reward: str, adv_clip: float = 2.0) -> Group:
    scores = [env.score(row, d.parse(t)) for t in texts]
    advs = env.group_advantages([s.reward[reward] for s in scores], adv_clip)
    return Group(row=row, texts=list(texts), scores=scores, advantages=advs)


def step_metrics(groups: Sequence[Group], reward: str) -> dict:
    scores = [s for g in groups for s in g.scores]
    codes = Counter()
    for s in scores:
        codes.update(s.counts)
    preds = [p for g in groups for p in (d.parse(t) for t in g.texts) if isinstance(p, dict)]
    n_fields = len(preds) * len(env.FIELDS)  # over parsed responses; a missing key counts as null
    nulls = sum(d.is_null(p.get(f)) for p in preds for f in env.FIELDS)
    return {
        "trained_on": reward,
        **{r: fmean(s.reward[r] for s in scores) for r in env.REWARDS},
        **{f"n_{c}": codes[c] for c in env.CODEBOOK},
        "parsed": fmean(s.parsed for s in scores),
        "null_rate": nulls / n_fields if n_fields else 0.0,
        "flat_groups": sum(g.advantages is None for g in groups),
        "groups": len(groups),
    }


@dataclass
class Tripwire:
    """Fires when the trained reward rises while gold `exact` falls, `patience` steps in a row."""

    reward: str
    patience: int = 3
    tol: float = 1e-6
    _prev: dict | None = None
    _streak: int = 0
    history: list[bool] = field(default_factory=list)

    def update(self, m: dict) -> bool:
        diverging = False
        if self._prev is not None and self.reward != "exact":
            diverging = (m[self.reward] > self._prev[self.reward] + self.tol
                         and m["exact"] < self._prev["exact"] - self.tol)
        self._streak = self._streak + 1 if diverging else 0
        self._prev = m
        self.history.append(diverging)
        return self._streak >= self.patience


def run(policy: Policy, rows: Sequence[dict], *, reward: str, steps: int, tasks: int, group: int,
        temperature: float = 1.0, trainer: Trainer | None = None, log_dir: Path | None = None,
        patience: int = 3, adv_clip: float = 2.0) -> list[dict]:
    """Sample → score under every reward → advantages → (optional) trainer update, per step."""
    if reward not in env.REWARDS:
        raise ValueError(f"unknown reward {reward!r}; choose from {env.REWARDS}")
    log = (log_dir / "steps.jsonl").open("a") if log_dir else None
    wire, history = Tripwire(reward, patience), []
    try:
        for step in range(steps):
            current = trainer.policy() if trainer else policy
            batch = [rows[(step * tasks + i) % len(rows)] for i in range(tasks)]
            groups = [score_group(r, current.sample(r, group, temperature), reward, adv_clip) for r in batch]
            m = {"step": step, **step_metrics(groups, reward)}
            if trainer:
                m.update({f"train/{k}": v for k, v in trainer.update([g for g in groups if g.advantages]).items()})
            history.append(m)
            if log:
                log.write(json.dumps(m) + "\n")
                log.flush()
            print(f"step {step}: {reward} {m[reward]:.3f} | exact {m['exact']:.3f} | "
                  f"invented {m['n_invented_value']} missed {m['n_missed_value']} wrong {m['n_wrong_value']} | "
                  f"null {m['null_rate']:.2f} | flat {m['flat_groups']}/{m['groups']}", flush=True)
            if wire.update(m):
                print(f"TRIPWIRE: {reward} rose while exact fell for {patience} steps; stopping", flush=True)
                if log_dir:
                    worst = sorted(((s.reward["exact"], g.row["id"], t) for g in groups
                                    for s, t in zip(g.scores, g.texts, strict=True)))[:20]
                    (log_dir / "expert_review.jsonl").write_text(
                        "".join(json.dumps({"doc": doc, "exact": e, "text": t}) + "\n" for e, doc, t in worst))
                break
    finally:
        if log:
            log.close()
    return history


# ---------- an OpenAI-compatible policy, for headroom checks without a trainer ----------

class OpenAIPolicy:
    def __init__(self, model: str = "glm", max_tokens: int = 512) -> None:
        self.client, self.kw = d.sync_client(d.MODELS[model]["host"])
        self.model, self.max_tokens = d.MODELS[model]["model"], max_tokens

    def sample(self, row: dict, n: int, temperature: float) -> list[str]:
        out = []
        for _ in range(n):  # one call per try: not every server honours `n` for vision models
            resp = self.client.chat.completions.create(model=self.model, messages=d.messages(row),
                                                       max_tokens=self.max_tokens, temperature=temperature,
                                                       **self.kw)
            out.append(resp.choices[0].message.content or "")
        return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("headroom", help="sample groups from the base policy and score them; no training")
    h.add_argument("--reward", default="gedd", choices=env.REWARDS)
    h.add_argument("--model", default="glm", choices=list(d.MODELS))
    h.add_argument("--tasks", type=int, default=16)
    h.add_argument("--group", type=int, default=4)
    h.add_argument("--temperature", type=float, default=1.0)
    h.add_argument("--seed", type=int, default=0)
    a = p.parse_args()

    test = d.load_split("test")
    pool = env.leak_free_train(d.load_split("train"), test)
    random.Random(a.seed).shuffle(pool)
    log_dir = d.HERE / "rl_logs" / time.strftime(f"headroom-{a.reward}-%Y%m%d-%H%M%S")
    log_dir.mkdir(parents=True, exist_ok=True)
    print(f"leak-free pool: {len(pool)} invoices; {a.tasks} tasks x {a.group} tries", flush=True)
    run(OpenAIPolicy(a.model), pool, reward=a.reward, steps=1, tasks=a.tasks, group=a.group,
        temperature=a.temperature, log_dir=log_dir)
    print(f"logs: {log_dir}")


if __name__ == "__main__":
    main()
