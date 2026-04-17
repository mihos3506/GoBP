"""GoBP append-only history log.

Every mutation appends one JSON object per line (JSONL format) to a
daily log file at .gobp/history/YYYY-MM-DD.jsonl.

History is append-only: never deleted, never overwritten. Used for
audit trail and future replay/restore capability.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def append_event(
    gobp_root: Path,
    event_type: str,
    payload: dict[str, Any],
    actor: str = "unknown",
) -> dict[str, Any]:
    """Append a single event to today's history log file.

    Creates .gobp/history/ folder and daily log file if needed.
    Each event is one JSON object on a single line.

    Args:
        gobp_root: Project root containing .gobp/ folder.
        event_type: Event type identifier (e.g., "node.created", "edge.deleted").
        payload: Event data as dict. Must be JSON-serializable.
        actor: Who caused this event (e.g., "cursor", "cli", "import"). Default "unknown".

    Returns:
        The full event dict that was written, including auto-generated fields.

    Raises:
        ValueError: If payload is not JSON-serializable.
        OSError: If history folder cannot be created or file cannot be written.
    """
    timestamp = datetime.now(timezone.utc)

    event = {
        "timestamp": timestamp.isoformat(),
        "event_type": event_type,
        "actor": actor,
        "payload": payload,
    }

    # Verify JSON-serializable before touching disk
    try:
        event_line = json.dumps(event, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Event payload not JSON-serializable: {e}") from e

    # Ensure history folder exists
    history_dir = gobp_root / ".gobp" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    # Daily log file based on UTC date
    date_str = timestamp.strftime("%Y-%m-%d")
    log_file = history_dir / f"{date_str}.jsonl"

    # Append one line
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(event_line + "\n")

    return event


def append_events_batch(
    gobp_root: Path,
    items: list[tuple[str, dict[str, Any], str]],
) -> None:
    """Append multiple history events in one file open (Wave 16A11 batch flush)."""
    if not items:
        return
    timestamp = datetime.now(timezone.utc)
    date_str = timestamp.strftime("%Y-%m-%d")
    history_dir = gobp_root / ".gobp" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    log_file = history_dir / f"{date_str}.jsonl"
    lines: list[str] = []
    for event_type, payload, actor in items:
        event = {
            "timestamp": timestamp.isoformat(),
            "event_type": event_type,
            "actor": actor,
            "payload": payload,
        }
        lines.append(json.dumps(event, ensure_ascii=False) + "\n")
    with open(log_file, "a", encoding="utf-8") as f:
        f.writelines(lines)


def read_events(
    gobp_root: Path,
    date_str: str | None = None,
) -> list[dict[str, Any]]:
    """Read events from a specific day's log file.

    Args:
        gobp_root: Project root containing .gobp/ folder.
        date_str: Date in YYYY-MM-DD format. If None, reads today's log.

    Returns:
        List of event dicts. Empty list if log file doesn't exist.

    Raises:
        ValueError: If any line in the log is not valid JSON.
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    log_file = gobp_root / ".gobp" / "history" / f"{date_str}.jsonl"

    if not log_file.exists():
        return []

    events: list[dict[str, Any]] = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                events.append(event)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Corrupted history log at {log_file}:{line_num}: {e}"
                ) from e

    return events
