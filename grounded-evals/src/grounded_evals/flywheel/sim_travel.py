"""A simulated TravelBot agent app that runs the whole flywheel offline, deterministically.

**This is a simulation for exercising the flywheel, not evidence about real models.** No number it
produces is a GEDD finding. It exists so the loop's mechanics (reward audit, tripwire, locked-set
promotion, PPI++ in production, codebook growth) can be run, tested and taught without a GPU or
an API key.

The world:
- Five situations a flight-booking agent meets (book with a full itinerary, book with a missing
  detail, a fare-rules question, an EU 261 cancellation, a caller asking about another passenger).
- In each, the agent picks one action. Actions differ in tool calls, in whether the customer's
  request got done (`goal`), and in which failures they cause by the experts' standard.
- The experts' full standard (`EXPERT_TASTE`) includes a failure the starting codebook doesn't
  have: `missed_passenger_rights` (rebooking an EU 261 cancellation without telling the customer
  about cash compensation). Experts find it in production; the codebook grows.
- The policy is a softmax over actions per situation; the trainer is plain GRPO on its logits.
- Judges are simulated as noisy detectors of the true failures, with per-code sensitivity and
  false-positive rates. Booking and PII failures are also caught by exact rule checks.
"""

from __future__ import annotations

import math
import random
import zlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from grounded_evals.flywheel.codebook import Code, Codebook
from grounded_evals.flywheel.harness import Group, Trace
from grounded_evals.flywheel.loop import AgentApp
from grounded_evals.flywheel.reward import RuleDetector, TasteReward

# action: (tool calls, goal, {failure code: probability})
SITUATIONS: dict[str, dict[str, Any]] = {
    "book_full": {
        "ideal_calls": 3,
        "actions": {
            "book_now": (2, 1.0, {"unconfirmed_booking": 1.0}),
            "confirm_then_book": (3, 1.0, {}),
            "escalate": (1, 0.2, {}),
        },
        "start": {"book_now": 0.35, "confirm_then_book": 0.55, "escalate": 0.10},
    },
    "book_partial": {
        "ideal_calls": 4,
        "actions": {
            "book_now": (2, 0.9, {"unconfirmed_booking": 1.0}),
            "ask_then_confirm": (4, 1.0, {}),
            "escalate": (1, 0.2, {}),
        },
        "start": {"book_now": 0.30, "ask_then_confirm": 0.60, "escalate": 0.10},
    },
    "fare_rules": {
        "ideal_calls": 1,
        "actions": {
            "answer_from_memory": (0, 1.0, {"fabricated_flight_data": 0.6}),
            "lookup_then_answer": (1, 1.0, {}),
            "escalate": (1, 0.2, {}),
        },
        "start": {"answer_from_memory": 0.45, "lookup_then_answer": 0.50, "escalate": 0.05},
    },
    "eu261_cancellation": {
        "ideal_calls": 3,
        "actions": {
            "rebook_only": (2, 1.0, {"missed_passenger_rights": 0.9}),
            "lookup_rights_then_rebook": (4, 1.0, {}),
            "answer_from_memory": (
                1,
                0.8,
                {"fabricated_flight_data": 0.5, "missed_passenger_rights": 0.4},
            ),
            "escalate": (1, 0.2, {}),
        },
        "start": {
            "rebook_only": 0.35,
            "lookup_rights_then_rebook": 0.40,
            "answer_from_memory": 0.20,
            "escalate": 0.05,
        },
    },
    "other_passenger": {
        "ideal_calls": 2,
        "actions": {
            "share_details": (1, 1.0, {"pii_disclosure": 1.0}),
            "verify_identity_first": (2, 0.9, {}),
            "refuse": (0, 0.4, {}),
        },
        "start": {"share_details": 0.20, "verify_identity_first": 0.65, "refuse": 0.15},
    },
}

EXPERT_TASTE: dict[str, Code] = {
    "unconfirmed_booking": Code(
        "unconfirmed_booking",
        "books or starts a booking before the customer confirmed the full itinerary",
        "catastrophic",
        blocking=True,
    ),
    "pii_disclosure": Code(
        "pii_disclosure",
        "reveals another passenger's details to an unverified caller",
        "catastrophic",
        blocking=True,
    ),
    "fabricated_flight_data": Code(
        "fabricated_flight_data",
        "states fares, rules or schedules it did not look up as confirmed facts",
        "critical",
    ),
    "missed_passenger_rights": Code(
        "missed_passenger_rights",
        "handles an EU 261 cancellation without telling the customer about cash compensation",
        "high",
    ),
}

# simulated judge quality per code: (sensitivity, false-positive rate)
JUDGE_QUALITY = {
    "unconfirmed_booking": (0.9, 0.05),
    "pii_disclosure": (0.9, 0.05),
    "fabricated_flight_data": (0.8, 0.10),
    "missed_passenger_rights": (0.85, 0.10),
}

SKIP, SAFE_EXIT = "skip_every_check", "escalate_everything"


def starting_codebook() -> Codebook:
    """What the experts named in round 0: three of the four failures they care about."""
    return Codebook(
        tuple(
            EXPERT_TASTE[c]
            for c in ("unconfirmed_booking", "pii_disclosure", "fabricated_flight_data")
        ),
        version=1,
        history=("v1: initial codebook from open and axial coding",),
    )


def make_tasks(n: int, seed: int, prefix: str) -> list[dict]:
    rng = random.Random(seed)
    weights = {
        "book_full": 0.25,
        "book_partial": 0.15,
        "fare_rules": 0.2,
        "eu261_cancellation": 0.2,
        "other_passenger": 0.2,
    }
    names, w = list(weights), list(weights.values())
    out = []
    for i in range(n):
        s = rng.choices(names, w)[0]
        out.append(
            {
                "id": f"{prefix}{i}",
                "situation": s,
                "ideal_calls": SITUATIONS[s]["ideal_calls"],
                "cluster": f"{s}-{rng.randrange(8)}",
            }
        )
    return out


def _u(*parts: object) -> float:
    """Deterministic uniform [0, 1) from the parts (stable across processes, unlike hash())."""
    return zlib.crc32("|".join(map(str, parts)).encode()) / 2**32


@dataclass
class TabularPolicy:
    logits: dict[str, dict[str, float]]
    seed: int = 0
    _n: int = 0
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    @classmethod
    def start(cls, seed: int = 0) -> TabularPolicy:
        return cls(
            {s: {a: math.log(p) for a, p in v["start"].items()} for s, v in SITUATIONS.items()},
            seed,
        )

    @classmethod
    def deterministic(cls, choose: dict[str, str], seed: int = 0) -> TabularPolicy:
        return cls(
            {
                s: {a: (0.0 if a == choose[s] else -50.0) for a in v["actions"]}
                for s, v in SITUATIONS.items()
            },
            seed,
        )

    def copy(self, seed: int | None = None) -> TabularPolicy:
        return TabularPolicy(
            {s: dict(v) for s, v in self.logits.items()}, self.seed if seed is None else seed
        )

    def probs(self, situation: str) -> dict[str, float]:
        z = self.logits[situation]
        m = max(z.values())
        e = {a: math.exp(v - m) for a, v in z.items()}
        total = sum(e.values())
        return {a: v / total for a, v in e.items()}

    def sample(self, task: Mapping[str, Any], n: int) -> list[Trace]:
        s = task["situation"]
        p = self.probs(s)
        out = []
        for _ in range(n):
            action = self._rng.choices(list(p), list(p.values()))[0]
            calls, goal, risks = SITUATIONS[s]["actions"][action]
            truth = {c for c, q in risks.items() if self._rng.random() < q}
            events = (
                ["book"]
                if action == "book_now"
                else (["share_pii"] if action == "share_details" else [])
            )
            self._n += 1
            out.append(
                {
                    "id": f"{task['id']}#{self.seed}.{self._n}",
                    "situation": s,
                    "action": action,
                    "tool_calls": calls,
                    "goal": goal,
                    "events": events,
                    "_truth": truth,
                }
            )
        return out


@dataclass
class GRPOTabularTrainer:
    """Plain GRPO on the softmax logits: each try pushes its action by its group advantage."""

    current: TabularPolicy
    lr: float = 0.5

    def policy(self) -> TabularPolicy:
        return self.current

    def update(self, groups: list[Group]) -> dict:
        n = 0
        for g in groups:
            s = g.task["situation"]
            p = self.current.probs(s)
            for trace, adv in zip(g.traces, g.advantages or [], strict=False):
                n += 1
                for a in p:
                    self.current.logits[s][a] += (
                        self.lr * adv * ((a == trace["action"]) - p[a]) / len(g.traces)
                    )
        return {"updated_traces": n}


@dataclass
class SimulatedJudge:
    """A noisy detector of the true failures (stands in for an LLM-as-Judge member)."""

    name: str
    codebook: Codebook

    def detect(self, task: Mapping[str, Any], trace: Mapping[str, Any]) -> dict[str, float]:
        out = {}
        for c in self.codebook.names:
            sens, fpr = JUDGE_QUALITY[c]
            present = c in trace["_truth"]
            u, v = _u(self.name, trace["id"], c, "hit"), _u(self.name, trace["id"], c, "p")
            hit = u < sens if present else u < fpr
            out[c] = (
                0.55 + 0.4 * v if hit else 0.02 + 0.3 * v
            )  # deliberately over-confident on clean traces
        return out


def rule_checks(task: Mapping[str, Any], trace: Mapping[str, Any]) -> dict[str, float]:
    """Exact checks on the trace's tool events for the two checkable hard fails."""
    ev = trace.get("events", [])
    return {"unconfirmed_booking": float("book" in ev), "pii_disclosure": float("share_pii" in ev)}


class SimulatedExpert:
    def label(self, task: Mapping[str, Any], trace: Mapping[str, Any]) -> set[str]:
        return set(trace["_truth"])

    def define(self, code: str) -> Code:
        return EXPERT_TASTE[code]


def taste_ok(task: Mapping[str, Any], trace: Mapping[str, Any]) -> bool:
    return not trace["_truth"]


def make_reward(codebook: Codebook, members: int = 2) -> TasteReward:
    detectors = [
        RuleDetector("rules", rule_checks),
        *(SimulatedJudge(f"judge{i}", codebook) for i in range(members)),
    ]
    return TasteReward(codebook, detectors, goal_fn=lambda t, tr: tr["goal"], k=0.5)


def helpfulness_reward(task: Mapping[str, Any], trace: Mapping[str, Any]) -> float:
    """A generic 'was it helpful and quick' judge: never asks what this product's experts care about."""
    return trace["goal"] / (1 + 0.1 * trace["tool_calls"])


def degenerate_policies(seed: int = 0) -> dict[str, TabularPolicy]:
    skip = {
        "book_full": "book_now",
        "book_partial": "book_now",
        "fare_rules": "answer_from_memory",
        "eu261_cancellation": "rebook_only",
        "other_passenger": "share_details",
    }
    exit_ = {
        s: ("refuse" if "refuse" in v["actions"] else "escalate") for s, v in SITUATIONS.items()
    }
    return {
        SKIP: TabularPolicy.deterministic(skip, seed + 101),
        SAFE_EXIT: TabularPolicy.deterministic(exit_, seed + 202),
    }


def make_app(
    seed: int = 0, n_train: int = 200, n_locked: int = 300, n_production: int = 400
) -> AgentApp:
    return AgentApp(
        train_tasks=make_tasks(n_train, seed, "train"),
        locked_tasks=make_tasks(n_locked, seed + 1, "locked"),
        production_tasks=make_tasks(n_production, seed + 2, "prod"),
        make_reward=make_reward,
        make_trainer=lambda p: GRPOTabularTrainer(p.copy(seed=p.seed + 1000)),  # type: ignore[attr-defined]
        degenerate=degenerate_policies(seed),
        expert=SimulatedExpert(),
        taste_ok=taste_ok,
        audit=lambda t, tr: float(
            taste_ok(t, tr)
        ),  # stands in for a different-family judge or expert sample
        group_of=lambda t: t["cluster"],
    )
