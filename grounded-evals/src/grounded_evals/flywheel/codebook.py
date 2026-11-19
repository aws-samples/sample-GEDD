"""The versioned failure codebook: the product's taste, written down by its domain experts.

Every round of the flywheel reads the codebook (to build the reward and the gate) and may write a
new version (when experts name a failure the codebook didn't cover). Versions are never edited in
place, so every training run and gate decision can name the exact standard it was held to.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from grounded_evals.reward.model import SEVERITY_WEIGHTS, FailureCode


@dataclass(frozen=True)
class Code:
    code: str
    description: str = ""
    severity: str = "medium"
    blocking: bool = False
    weight: float | None = None  # overrides the severity mapping when set

    @property
    def w(self) -> float:
        if self.weight is not None:
            return self.weight
        try:
            return SEVERITY_WEIGHTS[self.severity]
        except KeyError as exc:
            raise ValueError(f"unknown severity {self.severity!r} for {self.code}") from exc


@dataclass(frozen=True)
class Codebook:
    codes: tuple[Code, ...]
    version: int = 1
    history: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        names = [c.code for c in self.codes]
        if len(set(names)) != len(names):
            raise ValueError("duplicate failure codes in codebook")
        for c in self.codes:
            c.w  # noqa: B018  validates the severity

    @property
    def names(self) -> list[str]:
        return [c.code for c in self.codes]

    @property
    def total_weight(self) -> float:
        return sum(c.w for c in self.codes)

    def get(self, code: str) -> Code:
        for c in self.codes:
            if c.code == code:
                return c
        raise KeyError(code)

    def __contains__(self, code: object) -> bool:
        return any(c.code == code for c in self.codes)

    def add(self, code: Code, reason: str) -> Codebook:
        """A new version with one more code. The reason is kept in the history."""
        if code.code in self:
            raise ValueError(f"{code.code} is already in the codebook")
        return Codebook(
            self.codes + (code,),
            self.version + 1,
            self.history + (f"v{self.version + 1}: +{code.code} ({reason})",),
        )

    def failure_codes(self) -> list[FailureCode]:
        """The same codes in the shape `grounded_evals.reward` uses."""
        return [FailureCode(c.code, c.severity, c.blocking, c.weight) for c in self.codes]

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "history": list(self.history),
            "codes": [{k: v for k, v in asdict(c).items() if v is not None} for c in self.codes],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Codebook:
        codes = tuple(
            Code(
                **{
                    k: e[k]
                    for k in ("code", "description", "severity", "blocking", "weight")
                    if k in e
                }
            )
            for e in data["codes"]
        )
        return cls(codes, int(data.get("version", 1)), tuple(data.get("history", ())))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(yaml.safe_dump(self.to_dict(), sort_keys=False))

    @classmethod
    def load(cls, path: str | Path) -> Codebook:
        return cls.from_dict(yaml.safe_load(Path(path).read_text()))
