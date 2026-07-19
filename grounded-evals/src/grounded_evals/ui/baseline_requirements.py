"""Upload and store baseline evidence for the current assistant."""

from __future__ import annotations

from datetime import UTC, datetime

from nicegui import app, ui


def save_baseline_requirements(
    content: str,
    filename: str = "requirements.md",
    storage: dict | None = None,
) -> int:
    """Persist uploaded baseline requirements text and return its character count."""
    text = content.strip()
    if not text:
        raise ValueError("baseline evidence file is empty")
    target = app.storage.user if storage is None else storage
    target["baseline_requirements_md"] = text
    target["baseline_requirements_filename"] = filename or "requirements.md"
    target["baseline_requirements_uploaded_at"] = datetime.now(UTC).isoformat()
    return len(text)


def render_baseline_requirements_upload(label: str = "Upload baseline evidence") -> None:
    """Render a NiceGUI upload control for baseline evidence."""
    storage = app.storage.user

    def handle_upload(event) -> None:
        try:
            raw = event.content.read()
            text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
            count = save_baseline_requirements(text, getattr(event, "name", "requirements.md"))
            ui.notify(
                f"Uploaded baseline evidence ({count:,} chars)",
                type="positive",
            )
        except Exception as exc:
            ui.notify(f"Upload failed: {exc}", type="negative")

    ui.upload(
        label=label,
        on_upload=handle_upload,
        auto_upload=True,
    ).props("accept=.md,.markdown,text/markdown,text/plain flat dense dark").style(
        "color: var(--accent-bright); border: 1px solid var(--border-subtle); "
        "border-radius: 6px; padding: 2px 8px; font-size: 0.8rem"
    )
    if storage.get("baseline_requirements_md"):
        filename = storage.get("baseline_requirements_filename") or "requirements.md"
        ui.label(f"Uploaded: {filename}").style(
            "font-size: 0.68rem; color: var(--green-bright); margin-left: 4px"
        )
