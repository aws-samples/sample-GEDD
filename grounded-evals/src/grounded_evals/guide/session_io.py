"""Validated session persistence for CLI, UI, and handoff artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from grounded_evals.agent.tools import StateBundle
from grounded_evals.guide.session import Session

SESSION_SCHEMA_VERSION = 1


@dataclass
class SessionValidation:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_session_payload(state: StateBundle, messages: list[dict]) -> dict[str, Any]:
    """Serialize a StateBundle into the canonical session.json shape."""
    return {
        "schema_version": SESSION_SCHEMA_VERSION,
        "exported_at": _now_iso(),
        "session": state.session.model_dump(mode="json"),
        "annotations": state.annotations,
        "current_step": state.current_step,
        "prompt_variants": state.prompt_variants,
        "messages": messages,
    }


def load_session_state(session_file: str | Path) -> tuple[StateBundle, list[dict]]:
    """Load a session file, tolerating older files without schema_version."""
    path = Path(session_file)
    if not path.exists():
        return StateBundle(session=Session()), []

    try:
        data = json.loads(path.read_text())
        session = Session.model_validate(data["session"])
    except KeyError as exc:
        raise ValueError(f"{path} is missing required key: {exc.args[0]}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc
    except ValidationError as exc:
        raise ValueError(f"{path} does not match the GEDD session schema: {exc}") from exc

    state = StateBundle(
        session=session,
        annotations=data.get("annotations", []),
        current_step=data.get("current_step", session.current_step),
        prompt_variants=data.get("prompt_variants", []),
    )
    return state, data.get("messages", [])


def save_session_state(session_file: str | Path, state: StateBundle, messages: list[dict]) -> None:
    """Write a canonical session file with schema metadata."""
    payload = build_session_payload(state, messages)
    Path(session_file).write_text(json.dumps(payload, indent=2, default=str))


def validate_session_handoff(state: StateBundle) -> SessionValidation:
    """Validate whether a session is ready for a domain-expert to engineer handoff."""
    validation = SessionValidation()
    session = state.session
    agent = session.agent_spec
    prompts = session.golden_prompts
    annotations = state.annotations

    if not agent.name.strip():
        validation.errors.append("Agent name is missing.")
    if not agent.description.strip():
        validation.warnings.append("Agent description is missing.")
    if not agent.system_prompt.strip():
        validation.errors.append("System prompt is missing.")
    if not prompts:
        validation.errors.append("No golden queries are saved.")
    if prompts and len(prompts) < 15:
        validation.warnings.append(
            f"Only {len(prompts)} golden queries found; 15-20 is the recommended minimum."
        )

    categories = {p.rationale or "uncategorized" for p in prompts}
    if prompts and len(categories) < 3:
        validation.warnings.append("Golden queries cover fewer than 3 categories.")

    missing_expected = sum(1 for p in prompts if not p.expected_behavior.strip())
    if missing_expected:
        validation.warnings.append(
            f"{missing_expected} golden queries are missing expected behavior."
        )

    if not annotations:
        validation.warnings.append("No response annotations are saved yet.")
    else:
        failures = [a for a in annotations if a.get("annotation") in {"partial", "incorrect"}]
        unnamed = [a for a in failures if not a.get("error_code")]
        if unnamed:
            validation.warnings.append(
                f"{len(unnamed)} partial/incorrect annotations have no error code."
            )
        if not failures:
            validation.warnings.append(
                "No partial or incorrect annotations found; judge generation may be weak."
            )

    return validation
