# WAVE 2 BRIEF — FILE STORAGE + HISTORY + MUTATOR

**Wave:** 2
**Title:** File Storage + Append-Only History + Mutator
**Author:** CTO Chat (Claude Opus 4.6)
**Date:** 2026-04-14
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 7 atomic tasks
**Estimated effort:** 2.5-3 hours

---

## CONTEXT

Wave 0 built the skeleton. Wave 1 built the core engine (load, validate, index). Wave 2 builds **write support**: mutator for create/update/delete operations, append-only history log, atomic file writes.

After Wave 2, the system can safely mutate graph data on disk. MCP server (Wave 3) and CLI (Wave 4) will use these primitives.

**In scope:**
- `history.py` — append-only JSONL log writer
- `mutator.py` — 5 mutation functions + helper for atomic file writes
- File-based advisory locking (simple debounce, not cross-platform perfect)
- Tests for history and mutator

**NOT in scope:**
- MCP server (Wave 3)
- CLI commands (Wave 4)
- Import tools (Wave 5)
- Complex inter-process locks (defer to v2)
- Read-back verification after write (callers verify via GraphIndex reload)

---

## SCOPE DISCIPLINE RULE (NEW for Wave 2+)

**Implement EXACTLY the methods and functions specified in each task. No additional methods, no "while I'm at it" helpers, no utility functions beyond what the task requires.**

If you think a method should be added, STOP and escalate. Do not add silently.

**Rationale:** Wave 1 had `get_edges_by_type()` added without Brief authorization. Harmless but violated scope discipline. Wave 2 enforces strict scope.

**Exception:** Private helpers (prefixed `_`) as internal implementation are OK. Public API stays strictly within Brief.

---

## PREREQUISITES

Before Task 1:

```powershell
cd D:\GoBP
git status              # clean
git log --oneline -1    # Wave 1 Task 8 commit as latest
pytest tests/ -v        # All Wave 0 + Wave 1 tests pass (46+)
python -c "from gobp.core.graph import GraphIndex; print('OK')"
```

If any check fails, STOP and escalate.

---

## REQUIRED READING

At wave start:
1. `.cursorrules`
2. `CHARTER.md`
3. `docs/VISION.md`
4. `docs/ARCHITECTURE.md` (focus: file structure, append-only history, multi-project)
5. `docs/SCHEMA.md`
6. `waves/wave_2_brief.md` (this file)

Skim `gobp/core/graph.py`, `loader.py`, `validator.py` to understand existing patterns.

---

# TASKS

## TASK 1 — Implement history.append_event

**Goal:** Create append-only JSONL history logger. Every mutation appends one line to a daily log file.

**File to modify:** `gobp/core/history.py`

**Replace stub content with:**

```python
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
```

**Acceptance criteria:**
- `gobp/core/history.py` has exactly 2 public functions: `append_event`, `read_events`
- No additional functions/helpers beyond these
- Type hints on all signatures
- Docstrings on both functions
- Creates `.gobp/history/` folder automatically
- Daily log file named `YYYY-MM-DD.jsonl` (UTC date)
- Each event is one JSON line
- Raises `ValueError` for non-serializable payloads
- Raises `ValueError` for corrupted logs when reading

**Commit message:**
```
Wave 2 Task 1: implement history.append_event and read_events

- gobp/core/history.py: append-only JSONL history logger
- append_event(root, type, payload, actor): writes one event line
- read_events(root, date): reads one day's events
- Auto-creates .gobp/history/ folder
- Daily log files named YYYY-MM-DD.jsonl (UTC)
- Raises ValueError for bad payloads or corrupted logs

Foundation for audit trail and mutator operations.
```

---

## TASK 2 — Implement mutator helper _atomic_write

**Goal:** Internal helper for atomic file writes using temp-file + rename pattern.

**File to modify:** `gobp/core/mutator.py`

**Replace stub content with:**

```python
"""GoBP mutator — create/update/delete operations.

Performs atomic file writes to .gobp/nodes/ and .gobp/edges/.
Every mutation also writes one entry to the append-only history log.

Mutator does NOT manage the in-memory GraphIndex. Callers are
responsible for reloading the index after mutation if they need
fresh state. This keeps mutator stateless and simple.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from gobp.core.history import append_event
from gobp.core.validator import validate_edge, validate_node


def _atomic_write(target_path: Path, content: str) -> None:
    """Write content to target_path atomically.

    Uses temp-file + rename pattern:
    1. Write to a temp file in the same folder as target
    2. fsync the temp file
    3. Atomically rename temp over target

    This prevents corrupted target file if the process crashes mid-write.

    Args:
        target_path: Final destination path.
        content: File content as string (UTF-8).

    Raises:
        OSError: If folder cannot be created or write fails.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same folder (ensures atomic rename works)
    fd, temp_path_str = tempfile.mkstemp(
        prefix=f".{target_path.name}.",
        suffix=".tmp",
        dir=str(target_path.parent),
    )
    temp_path = Path(temp_path_str)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename (replaces target if exists)
        os.replace(str(temp_path), str(target_path))
    except Exception:
        # Clean up temp file on any error
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise
```

**Acceptance criteria:**
- `_atomic_write` function defined (private, prefixed with `_`)
- Uses `tempfile.mkstemp` in same folder as target
- Calls `f.flush()` and `os.fsync()` before rename
- Uses `os.replace()` for atomic rename
- Cleans up temp file on error
- Type hints + docstring
- Also imports `history.append_event`, `validator.validate_node`, `validator.validate_edge` at top (for use in later tasks)

**Commit message:**
```
Wave 2 Task 2: implement mutator._atomic_write helper

- gobp/core/mutator.py: _atomic_write internal helper
- Temp-file + rename pattern for crash-safe writes
- Calls fsync before rename
- Cleans up temp file on error

Also imports history and validator modules for use in later tasks.
```

---

## TASK 3 — Implement mutator.create_node

**Goal:** Write a new node to disk with validation and history logging.

**File to modify:** `gobp/core/mutator.py` (append function after `_atomic_write`)

**Add this function:**

```python
def create_node(
    gobp_root: Path,
    node: dict[str, Any],
    schema: dict[str, Any],
    actor: str = "unknown",
) -> Path:
    """Create a new node file on disk.

    Validates the node against schema, writes markdown file with YAML
    frontmatter, and appends creation event to history log.

    Args:
        gobp_root: Project root.
        node: Node data dict (must have 'id' and 'type').
        schema: Nodes schema dict (from loader.load_schema).
        actor: Who is creating this node.

    Returns:
        Path to the created node file.

    Raises:
        ValueError: If node fails validation or lacks 'id'.
        FileExistsError: If node file already exists (use update_node instead).
    """
    # Validate first
    result = validate_node(node, schema)
    if not result.ok:
        raise ValueError(f"Node validation failed: {result.errors}")

    node_id = node.get("id")
    if not node_id:
        raise ValueError("Node missing 'id' field")

    # Derive filename from ID (replace ':' with '_' for filesystem safety)
    safe_name = node_id.replace(":", "_").replace("/", "_")
    node_file = gobp_root / ".gobp" / "nodes" / f"{safe_name}.md"

    if node_file.exists():
        raise FileExistsError(
            f"Node file already exists: {node_file}. Use update_node instead."
        )

    # Build markdown content with YAML frontmatter
    frontmatter_yaml = yaml.safe_dump(node, default_flow_style=False, sort_keys=False)
    content = f"---\n{frontmatter_yaml}---\n\n(Auto-generated node file. Edit the YAML above or add body content below.)\n"

    _atomic_write(node_file, content)

    # Log to history
    append_event(
        gobp_root=gobp_root,
        event_type="node.created",
        payload={"id": node_id, "type": node.get("type"), "file": str(node_file)},
        actor=actor,
    )

    return node_file
```

**Acceptance criteria:**
- `create_node` function added
- Validates before writing (raises ValueError on invalid)
- Raises FileExistsError if file already exists
- Filename derived from node id (`:` → `_`)
- Writes markdown with YAML frontmatter
- Calls `_atomic_write` for crash-safety
- Logs to history with event type `node.created`
- Returns Path of created file
- Type hints + docstring

**Commit message:**
```
Wave 2 Task 3: implement mutator.create_node

- gobp/core/mutator.py: create_node function
- Validates node against schema before writing
- Raises FileExistsError if file exists (explicit choice)
- Writes markdown + YAML frontmatter atomically
- Logs node.created event to history

File naming: id "node:foo" -> nodes/node_foo.md
```

---

## TASK 4 — Implement mutator.update_node and delete_node

**Goal:** Add update and soft-delete operations.

**File to modify:** `gobp/core/mutator.py` (append after `create_node`)

**Add these functions:**

```python
def update_node(
    gobp_root: Path,
    node: dict[str, Any],
    schema: dict[str, Any],
    actor: str = "unknown",
) -> Path:
    """Update an existing node file.

    Overwrites the existing node file with new data. Validates first.
    Logs update event to history with the new data (old data lives
    in history as previous create/update events).

    Args:
        gobp_root: Project root.
        node: Full node dict (not partial — includes all fields).
        schema: Nodes schema.
        actor: Who is updating.

    Returns:
        Path to the updated file.

    Raises:
        ValueError: If validation fails or node lacks 'id'.
        FileNotFoundError: If node file does not exist (use create_node).
    """
    result = validate_node(node, schema)
    if not result.ok:
        raise ValueError(f"Node validation failed: {result.errors}")

    node_id = node.get("id")
    if not node_id:
        raise ValueError("Node missing 'id' field")

    safe_name = node_id.replace(":", "_").replace("/", "_")
    node_file = gobp_root / ".gobp" / "nodes" / f"{safe_name}.md"

    if not node_file.exists():
        raise FileNotFoundError(
            f"Node file does not exist: {node_file}. Use create_node instead."
        )

    frontmatter_yaml = yaml.safe_dump(node, default_flow_style=False, sort_keys=False)
    content = f"---\n{frontmatter_yaml}---\n\n(Updated node file.)\n"

    _atomic_write(node_file, content)

    append_event(
        gobp_root=gobp_root,
        event_type="node.updated",
        payload={"id": node_id, "type": node.get("type"), "file": str(node_file)},
        actor=actor,
    )

    return node_file


def delete_node(
    gobp_root: Path,
    node_id: str,
    actor: str = "unknown",
) -> Path:
    """Soft-delete a node by marking status as ARCHIVED.

    Does NOT remove the file from disk. Instead reads the existing
    file, sets status field to "ARCHIVED", and writes back. Keeps the
    file history intact for audit.

    Args:
        gobp_root: Project root.
        node_id: Node ID to delete.
        actor: Who is deleting.

    Returns:
        Path to the archived node file.

    Raises:
        FileNotFoundError: If node file does not exist.
        ValueError: If node file is malformed.
    """
    safe_name = node_id.replace(":", "_").replace("/", "_")
    node_file = gobp_root / ".gobp" / "nodes" / f"{safe_name}.md"

    if not node_file.exists():
        raise FileNotFoundError(f"Node file not found: {node_file}")

    # Read current content
    content = node_file.read_text(encoding="utf-8")

    # Parse frontmatter to get current node data
    from gobp.core.loader import parse_frontmatter
    frontmatter, body = parse_frontmatter(content)

    if not frontmatter:
        raise ValueError(f"Node file has no frontmatter: {node_file}")

    # Mark as archived
    frontmatter["status"] = "ARCHIVED"

    # Rewrite
    frontmatter_yaml = yaml.safe_dump(frontmatter, default_flow_style=False, sort_keys=False)
    new_content = f"---\n{frontmatter_yaml}---\n\n{body}"

    _atomic_write(node_file, new_content)

    append_event(
        gobp_root=gobp_root,
        event_type="node.archived",
        payload={"id": node_id, "file": str(node_file)},
        actor=actor,
    )

    return node_file
```

**Acceptance criteria:**
- `update_node` function added (requires file to exist)
- `delete_node` function added (soft-delete, sets status=ARCHIVED)
- Both use `_atomic_write`
- Both log to history
- `update_node` raises FileNotFoundError if file missing
- `delete_node` raises FileNotFoundError if file missing
- `delete_node` preserves file body (only modifies frontmatter status)
- Type hints + docstrings

**Commit message:**
```
Wave 2 Task 4: implement mutator.update_node and delete_node

- gobp/core/mutator.py: update_node and delete_node
- update_node: overwrites existing node file with validation
- delete_node: soft-delete (sets status=ARCHIVED, keeps file)
- Both use atomic writes and log to history

Soft delete is intentional: files preserved for audit, lessons, replay.
```

---

## TASK 5 — Implement mutator.create_edge and delete_edge

**Goal:** Edge mutation operations.

**File to modify:** `gobp/core/mutator.py` (append after `delete_node`)

**Add these functions:**

```python
def create_edge(
    gobp_root: Path,
    edge: dict[str, Any],
    schema: dict[str, Any],
    edge_file_name: str = "relations.yaml",
    actor: str = "unknown",
) -> Path:
    """Append a new edge to an edge YAML file.

    Edge files contain a YAML list. This function appends one edge
    to the specified file (creating the file if it doesn't exist).

    Args:
        gobp_root: Project root.
        edge: Edge data dict (must have 'from', 'to', 'type').
        schema: Edges schema.
        edge_file_name: Filename within .gobp/edges/. Default "relations.yaml".
        actor: Who is creating.

    Returns:
        Path to the edge file.

    Raises:
        ValueError: If edge validation fails.
    """
    result = validate_edge(edge, schema)
    if not result.ok:
        raise ValueError(f"Edge validation failed: {result.errors}")

    edges_dir = gobp_root / ".gobp" / "edges"
    edges_dir.mkdir(parents=True, exist_ok=True)

    edge_file = edges_dir / edge_file_name

    # Read existing edges (if file exists)
    existing_edges: list[dict[str, Any]] = []
    if edge_file.exists():
        content = edge_file.read_text(encoding="utf-8")
        loaded = yaml.safe_load(content)
        if isinstance(loaded, list):
            existing_edges = loaded

    # Append new edge
    existing_edges.append(edge)

    # Write back atomically
    new_content = yaml.safe_dump(existing_edges, default_flow_style=False, sort_keys=False)
    _atomic_write(edge_file, new_content)

    append_event(
        gobp_root=gobp_root,
        event_type="edge.created",
        payload={
            "from": edge.get("from"),
            "to": edge.get("to"),
            "type": edge.get("type"),
            "file": str(edge_file),
        },
        actor=actor,
    )

    return edge_file


def delete_edge(
    gobp_root: Path,
    from_id: str,
    to_id: str,
    edge_type: str,
    edge_file_name: str = "relations.yaml",
    actor: str = "unknown",
) -> int:
    """Remove all edges matching (from, to, type) from an edge file.

    Hard delete for edges (unlike nodes which are soft-deleted).
    Edges are cheap to recreate from graph context; keeping them as
    tombstones adds complexity without much benefit.

    Args:
        gobp_root: Project root.
        from_id: Edge source node ID.
        to_id: Edge target node ID.
        edge_type: Edge type (e.g., "relates_to").
        edge_file_name: Filename within .gobp/edges/.
        actor: Who is deleting.

    Returns:
        Count of edges deleted.

    Raises:
        FileNotFoundError: If edge file does not exist.
    """
    edge_file = gobp_root / ".gobp" / "edges" / edge_file_name

    if not edge_file.exists():
        raise FileNotFoundError(f"Edge file not found: {edge_file}")

    content = edge_file.read_text(encoding="utf-8")
    loaded = yaml.safe_load(content)
    if not isinstance(loaded, list):
        loaded = []

    # Filter out matching edges
    initial_count = len(loaded)
    remaining = [
        e for e in loaded
        if not (
            e.get("from") == from_id
            and e.get("to") == to_id
            and e.get("type") == edge_type
        )
    ]
    deleted_count = initial_count - len(remaining)

    if deleted_count > 0:
        new_content = yaml.safe_dump(remaining, default_flow_style=False, sort_keys=False)
        _atomic_write(edge_file, new_content)

        append_event(
            gobp_root=gobp_root,
            event_type="edge.deleted",
            payload={
                "from": from_id,
                "to": to_id,
                "type": edge_type,
                "count": deleted_count,
            },
            actor=actor,
        )

    return deleted_count
```

**Acceptance criteria:**
- `create_edge` appends edge to YAML list file
- `delete_edge` removes matching edges (hard delete)
- Both use `_atomic_write`
- Both log to history
- `delete_edge` returns count deleted
- Type hints + docstrings

**Commit message:**
```
Wave 2 Task 5: implement mutator.create_edge and delete_edge

- gobp/core/mutator.py: create_edge and delete_edge
- create_edge: appends to edge YAML list, validates first
- delete_edge: hard delete by (from, to, type) match, returns count
- Both atomic writes + history logging

Edges are hard-deleted (unlike nodes which are soft-deleted) because
edges are cheap to recreate and tombstones add complexity without benefit.
```

---

## TASK 6 — Write history tests

**Goal:** Test `append_event` and `read_events`.

**File to create:** `tests/test_history.py`

**Content:**

```python
"""Tests for gobp.core.history module."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gobp.core.history import append_event, read_events


def test_append_event_creates_folder(tmp_path: Path):
    """append_event creates .gobp/history/ folder if missing."""
    event = append_event(
        gobp_root=tmp_path,
        event_type="test.event",
        payload={"foo": "bar"},
        actor="test",
    )

    history_dir = tmp_path / ".gobp" / "history"
    assert history_dir.exists()
    assert history_dir.is_dir()


def test_append_event_returns_event_dict(tmp_path: Path):
    """append_event returns the event it wrote."""
    event = append_event(
        gobp_root=tmp_path,
        event_type="test.event",
        payload={"key": "value"},
        actor="tester",
    )

    assert event["event_type"] == "test.event"
    assert event["actor"] == "tester"
    assert event["payload"] == {"key": "value"}
    assert "timestamp" in event


def test_append_event_writes_jsonl_line(tmp_path: Path):
    """Event is written as single JSON line."""
    append_event(tmp_path, "a.b", {"x": 1}, "actor1")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = tmp_path / ".gobp" / "history" / f"{date_str}.jsonl"
    assert log_file.exists()

    content = log_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 1

    parsed = json.loads(lines[0])
    assert parsed["event_type"] == "a.b"
    assert parsed["payload"]["x"] == 1


def test_append_multiple_events_all_logged(tmp_path: Path):
    """Multiple events append to same daily file."""
    append_event(tmp_path, "evt.1", {"n": 1}, "a")
    append_event(tmp_path, "evt.2", {"n": 2}, "a")
    append_event(tmp_path, "evt.3", {"n": 3}, "a")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = tmp_path / ".gobp" / "history" / f"{date_str}.jsonl"
    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3


def test_append_event_default_actor(tmp_path: Path):
    """Default actor is 'unknown'."""
    event = append_event(tmp_path, "e", {})
    assert event["actor"] == "unknown"


def test_append_event_non_serializable_raises(tmp_path: Path):
    """Non-JSON-serializable payload raises ValueError."""
    class NotSerializable:
        pass

    with pytest.raises(ValueError, match="not JSON-serializable"):
        append_event(tmp_path, "bad", {"obj": NotSerializable()})


def test_read_events_empty_if_no_log(tmp_path: Path):
    """read_events returns [] if no log file exists."""
    events = read_events(tmp_path)
    assert events == []


def test_read_events_returns_all_events(tmp_path: Path):
    """read_events returns all events from today's log."""
    append_event(tmp_path, "e1", {"x": 1}, "a")
    append_event(tmp_path, "e2", {"x": 2}, "b")
    append_event(tmp_path, "e3", {"x": 3}, "c")

    events = read_events(tmp_path)
    assert len(events) == 3
    assert events[0]["event_type"] == "e1"
    assert events[1]["event_type"] == "e2"
    assert events[2]["event_type"] == "e3"


def test_read_events_specific_date(tmp_path: Path):
    """read_events(date_str) reads a specific day's log."""
    # Create a fake log for a past date
    history_dir = tmp_path / ".gobp" / "history"
    history_dir.mkdir(parents=True)
    past_log = history_dir / "2025-01-01.jsonl"
    past_log.write_text('{"event_type":"old","payload":{},"actor":"a","timestamp":"2025-01-01T00:00:00+00:00"}\n')

    events = read_events(tmp_path, date_str="2025-01-01")
    assert len(events) == 1
    assert events[0]["event_type"] == "old"


def test_read_events_corrupted_log_raises(tmp_path: Path):
    """Corrupted JSON in log raises ValueError."""
    history_dir = tmp_path / ".gobp" / "history"
    history_dir.mkdir(parents=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = history_dir / f"{date_str}.jsonl"
    log_file.write_text("not valid json\n")

    with pytest.raises(ValueError, match="Corrupted history log"):
        read_events(tmp_path)
```

**Acceptance criteria:**
- File `tests/test_history.py` created
- Exactly 10 tests
- All tests pass
- Covers: folder creation, return value, JSONL format, multiple events, default actor, error cases, read empty, read all, read by date, corrupted log

**Commit message:**
```
Wave 2 Task 6: write history module tests

- tests/test_history.py: 10 tests
- Covers append_event (6 tests): folder creation, return value,
  JSONL line format, multiple events, default actor, serialization errors
- Covers read_events (4 tests): empty case, full read, specific date,
  corrupted log error

All tests use tmp_path for isolation.
```

---

## TASK 7 — Write mutator tests

**Goal:** Test all mutator functions.

**File to create:** `tests/test_mutator.py`

**Content:**

```python
"""Tests for gobp.core.mutator module."""

from pathlib import Path

import pytest
import yaml

from gobp.core.history import read_events
from gobp.core.mutator import (
    create_edge,
    create_node,
    delete_edge,
    delete_node,
    update_node,
)


@pytest.fixture
def nodes_schema():
    """Minimal nodes schema for testing."""
    return {
        "schema_version": "1.0",
        "node_types": {
            "Node": {
                "required": {
                    "id": {"type": "str", "pattern": r"^node:[a-z][a-z0-9_]*$"},
                    "type": {"type": "str"},
                    "name": {"type": "str"},
                    "status": {
                        "type": "enum",
                        "enum_values": ["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"],
                    },
                    "created": {"type": "timestamp"},
                    "updated": {"type": "timestamp"},
                },
                "optional": {},
            }
        },
    }


@pytest.fixture
def edges_schema():
    """Minimal edges schema for testing."""
    return {
        "schema_version": "1.0",
        "edge_types": {
            "relates_to": {
                "required": {
                    "from": {"type": "node_ref"},
                    "to": {"type": "node_ref"},
                    "type": {"type": "str", "enum_values": ["relates_to"]},
                },
                "optional": {},
            }
        },
    }


@pytest.fixture
def sample_node():
    return {
        "id": "node:test",
        "type": "Node",
        "name": "Test Node",
        "status": "ACTIVE",
        "created": "2026-04-14T00:00:00",
        "updated": "2026-04-14T00:00:00",
    }


# =============================================================================
# create_node tests
# =============================================================================


def test_create_node_writes_file(tmp_path: Path, sample_node, nodes_schema):
    path = create_node(tmp_path, sample_node, nodes_schema, actor="test")
    assert path.exists()
    assert path.name == "node_test.md"


def test_create_node_writes_frontmatter(tmp_path: Path, sample_node, nodes_schema):
    path = create_node(tmp_path, sample_node, nodes_schema, actor="test")
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "id: node:test" in content


def test_create_node_logs_history(tmp_path: Path, sample_node, nodes_schema):
    create_node(tmp_path, sample_node, nodes_schema, actor="tester")
    events = read_events(tmp_path)
    assert len(events) == 1
    assert events[0]["event_type"] == "node.created"
    assert events[0]["actor"] == "tester"
    assert events[0]["payload"]["id"] == "node:test"


def test_create_node_invalid_raises(tmp_path: Path, nodes_schema):
    bad_node = {"id": "node:bad", "type": "Node"}  # missing required fields
    with pytest.raises(ValueError, match="validation failed"):
        create_node(tmp_path, bad_node, nodes_schema)


def test_create_node_duplicate_raises(tmp_path: Path, sample_node, nodes_schema):
    create_node(tmp_path, sample_node, nodes_schema)
    with pytest.raises(FileExistsError):
        create_node(tmp_path, sample_node, nodes_schema)


# =============================================================================
# update_node tests
# =============================================================================


def test_update_node_overwrites(tmp_path: Path, sample_node, nodes_schema):
    create_node(tmp_path, sample_node, nodes_schema)

    updated = dict(sample_node)
    updated["name"] = "Updated Name"
    path = update_node(tmp_path, updated, nodes_schema, actor="editor")

    content = path.read_text(encoding="utf-8")
    assert "Updated Name" in content


def test_update_node_logs_history(tmp_path: Path, sample_node, nodes_schema):
    create_node(tmp_path, sample_node, nodes_schema)
    updated = dict(sample_node)
    updated["name"] = "New"
    update_node(tmp_path, updated, nodes_schema, actor="editor")

    events = read_events(tmp_path)
    update_events = [e for e in events if e["event_type"] == "node.updated"]
    assert len(update_events) == 1
    assert update_events[0]["actor"] == "editor"


def test_update_node_missing_raises(tmp_path: Path, sample_node, nodes_schema):
    with pytest.raises(FileNotFoundError):
        update_node(tmp_path, sample_node, nodes_schema)


# =============================================================================
# delete_node tests
# =============================================================================


def test_delete_node_sets_archived(tmp_path: Path, sample_node, nodes_schema):
    create_node(tmp_path, sample_node, nodes_schema)
    path = delete_node(tmp_path, "node:test", actor="deleter")

    content = path.read_text(encoding="utf-8")
    assert "status: ARCHIVED" in content


def test_delete_node_file_still_exists(tmp_path: Path, sample_node, nodes_schema):
    """Soft delete keeps file on disk."""
    create_node(tmp_path, sample_node, nodes_schema)
    path = delete_node(tmp_path, "node:test")
    assert path.exists()


def test_delete_node_logs_history(tmp_path: Path, sample_node, nodes_schema):
    create_node(tmp_path, sample_node, nodes_schema)
    delete_node(tmp_path, "node:test", actor="deleter")

    events = read_events(tmp_path)
    archived = [e for e in events if e["event_type"] == "node.archived"]
    assert len(archived) == 1


def test_delete_node_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        delete_node(tmp_path, "node:nonexistent")


# =============================================================================
# create_edge tests
# =============================================================================


def test_create_edge_writes_file(tmp_path: Path, edges_schema):
    edge = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    path = create_edge(tmp_path, edge, edges_schema, actor="test")

    assert path.exists()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert len(data) == 1


def test_create_edge_appends_to_existing(tmp_path: Path, edges_schema):
    edge1 = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    edge2 = {"from": "node:b", "to": "node:c", "type": "relates_to"}

    create_edge(tmp_path, edge1, edges_schema)
    create_edge(tmp_path, edge2, edges_schema)

    edge_file = tmp_path / ".gobp" / "edges" / "relations.yaml"
    data = yaml.safe_load(edge_file.read_text(encoding="utf-8"))
    assert len(data) == 2


def test_create_edge_invalid_raises(tmp_path: Path, edges_schema):
    bad_edge = {"from": "node:a", "type": "relates_to"}  # missing 'to'
    with pytest.raises(ValueError, match="validation failed"):
        create_edge(tmp_path, bad_edge, edges_schema)


def test_create_edge_logs_history(tmp_path: Path, edges_schema):
    edge = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    create_edge(tmp_path, edge, edges_schema, actor="creator")

    events = read_events(tmp_path)
    created = [e for e in events if e["event_type"] == "edge.created"]
    assert len(created) == 1
    assert created[0]["actor"] == "creator"


# =============================================================================
# delete_edge tests
# =============================================================================


def test_delete_edge_removes_matching(tmp_path: Path, edges_schema):
    edge1 = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    edge2 = {"from": "node:b", "to": "node:c", "type": "relates_to"}

    create_edge(tmp_path, edge1, edges_schema)
    create_edge(tmp_path, edge2, edges_schema)

    count = delete_edge(tmp_path, "node:a", "node:b", "relates_to")
    assert count == 1

    edge_file = tmp_path / ".gobp" / "edges" / "relations.yaml"
    data = yaml.safe_load(edge_file.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["from"] == "node:b"


def test_delete_edge_missing_returns_zero(tmp_path: Path, edges_schema):
    edge = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    create_edge(tmp_path, edge, edges_schema)

    count = delete_edge(tmp_path, "node:x", "node:y", "relates_to")
    assert count == 0


def test_delete_edge_file_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        delete_edge(tmp_path, "node:a", "node:b", "relates_to")


def test_delete_edge_logs_history(tmp_path: Path, edges_schema):
    edge = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    create_edge(tmp_path, edge, edges_schema)
    delete_edge(tmp_path, "node:a", "node:b", "relates_to", actor="remover")

    events = read_events(tmp_path)
    deleted = [e for e in events if e["event_type"] == "edge.deleted"]
    assert len(deleted) == 1
    assert deleted[0]["actor"] == "remover"
    assert deleted[0]["payload"]["count"] == 1


# =============================================================================
# Atomic write test
# =============================================================================


def test_mutations_are_atomic(tmp_path: Path, sample_node, nodes_schema):
    """Sanity check: no temp files left after successful create."""
    create_node(tmp_path, sample_node, nodes_schema)

    nodes_dir = tmp_path / ".gobp" / "nodes"
    files = list(nodes_dir.iterdir())
    # Only the final file should exist, no .tmp files
    assert all(not f.name.endswith(".tmp") for f in files)
    assert len(files) == 1
```

**Run all tests:**
```powershell
pytest tests/ -v
```

**Acceptance criteria:**
- File `tests/test_mutator.py` created
- Exactly 20 tests
- All tests pass (including Wave 0 + Wave 1 + Wave 2 new tests = 66+ tests)
- Uses fixtures for schemas and sample nodes
- Tests all 5 mutator functions (create_node, update_node, delete_node, create_edge, delete_edge)
- Tests validation errors, file errors, history logging, atomicity

**Commit message:**
```
Wave 2 Task 7: write mutator tests

- tests/test_mutator.py: 20 tests covering all 5 mutator functions
  - create_node: 5 tests (write, frontmatter, history, invalid, duplicate)
  - update_node: 3 tests (overwrite, history, missing)
  - delete_node: 4 tests (archive status, file preserved, history, missing)
  - create_edge: 4 tests (write, append, invalid, history)
  - delete_edge: 4 tests (remove, no match, file missing, history)

Plus atomic write sanity check (no temp files left behind).

All 66+ tests across Waves 0-2 passing.
```

---

# POST-WAVE VERIFICATION

After all 7 tasks:

```powershell
pytest tests/ -v
# Expected: 66+ tests passing
# Wave 0 smoke: 13
# Wave 1 loader/validator: 26
# Wave 1 graph: 11
# Wave 2 history: 10
# Wave 2 mutator: 20

git log --oneline | Select-Object -First 7
# Expected: 7 Wave 2 task commits

# Manual smoke test
python -c "
from pathlib import Path
from gobp.core.history import append_event, read_events

root = Path('/tmp/gobp_test')
root.mkdir(exist_ok=True)
append_event(root, 'test', {'msg': 'hello'}, 'smoke_test')
events = read_events(root)
print(f'Logged {len(events)} events')
"
```

---

# ESCALATION TRIGGERS

Stop and escalate if:
- pytest fails and cannot fix after 3 retries
- `_atomic_write` doesn't actually work (file shows partial writes)
- YAML round-trip has precision loss
- History file gets corrupted mid-test

---

# WHAT COMES NEXT

After Wave 2 pushed:
- **Wave 3** — MCP server + 6 read tools + `gobp_overview()`
- **Wave 4** — CLI commands
- **Wave 5** — Write tools (uses mutator from Wave 2)
- **Wave 6** — Advanced features
- **Wave 7** — Documentation
- **Wave 8** — MIHOS integration test

---

*Wave 2 Brief v0.1*
*Author: CTO Chat (Claude Opus 4.6)*
*Date: 2026-04-14*

◈
