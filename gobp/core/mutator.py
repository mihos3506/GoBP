"""GoBP mutator - create/update/delete operations.

Performs atomic file writes to .gobp/nodes/ and .gobp/edges/.
Every mutation also writes one entry to the append-only history log.

Mutator does NOT manage the in-memory GraphIndex. Callers are
responsible for reloading the index after mutation if they need
fresh state. This keeps mutator stateless and simple.
"""

from __future__ import annotations

import os
import tempfile
import uuid as _uuid
from pathlib import Path
from typing import Any

import yaml

from gobp.core import cache as _cache_module
from gobp.core import db as _db
from gobp.core.history import append_event
from gobp.core.loader import parse_frontmatter
from gobp.core.validator import validate_edge, validate_node


def _generate_session_id(goal: str = "") -> str:
    """Generate short, unique session ID.

    Format: session:YYYY-MM-DD_XXXXXXXXX
    where XXXXXXXXX = first 9 chars of UUID4 hex
    Never truncated, always exactly 28 chars.
    """
    from datetime import datetime, timezone

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    short_hash = _uuid.uuid4().hex[:9]
    return f"session:{date_str}_{short_hash}"


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

        os.replace(str(temp_path), str(target_path))
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def _node_file_path(gobp_root: Path, node_id: str) -> Path:
    """Return the expected file path for a node given its ID.

    Args:
        gobp_root: Project root.
        node_id: Node ID (e.g., ``"idea:i001"``).

    Returns:
        Path to the ``.md`` file inside ``.gobp/nodes/``.
    """
    safe_name = node_id.replace(":", "_").replace("/", "_")
    return gobp_root / ".gobp" / "nodes" / f"{safe_name}.md"


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
    result = validate_node(node, schema)
    if not result.ok:
        raise ValueError(f"Node validation failed: {result.errors}")

    node_id = node.get("id")
    if not node_id:
        raise ValueError("Node missing 'id' field")

    node_file = _node_file_path(gobp_root, node_id)

    if node_file.exists():
        raise FileExistsError(
            f"Node file already exists: {node_file}. Use update_node instead."
        )

    frontmatter_yaml = yaml.safe_dump(
        node, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    content = (
        f"---\n{frontmatter_yaml}---\n\n"
        "(Auto-generated node file. Edit the YAML above or add body content below.)\n"
    )

    _atomic_write(node_file, content)

    # Write-through: update SQLite index
    try:
        _db.init_schema(gobp_root)
        _db.upsert_node(gobp_root, node)
    except Exception:
        pass  # SQLite failure non-fatal

    # Invalidate cache
    try:
        _cache_module.get_cache().invalidate_all()
    except Exception:
        pass

    append_event(
        gobp_root=gobp_root,
        event_type="node.created",
        payload={"id": node_id, "type": node.get("type"), "file": str(node_file)},
        actor=actor,
    )

    return node_file


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
        node: Full node dict (not partial - includes all fields).
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

    node_file = _node_file_path(gobp_root, node_id)

    if not node_file.exists():
        raise FileNotFoundError(
            f"Node file does not exist: {node_file}. Use create_node instead."
        )

    frontmatter_yaml = yaml.safe_dump(
        node, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    content = f"---\n{frontmatter_yaml}---\n\n(Updated node file.)\n"

    _atomic_write(node_file, content)

    # Write-through: update SQLite index
    try:
        _db.init_schema(gobp_root)
        _db.upsert_node(gobp_root, node)
    except Exception:
        pass  # SQLite failure non-fatal

    # Invalidate cache
    try:
        _cache_module.get_cache().invalidate_all()
    except Exception:
        pass

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
    node_file = _node_file_path(gobp_root, node_id)

    if not node_file.exists():
        raise FileNotFoundError(f"Node file not found: {node_file}")

    content = node_file.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)

    if not frontmatter:
        raise ValueError(f"Node file has no frontmatter: {node_file}")

    frontmatter["status"] = "ARCHIVED"

    frontmatter_yaml = yaml.safe_dump(
        frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    new_content = f"---\n{frontmatter_yaml}---\n\n{body}"

    _atomic_write(node_file, new_content)

    try:
        _db.delete_node(gobp_root, node_id)
        _db.delete_edges_for_node(gobp_root, node_id)
        _cache_module.get_cache().invalidate_all()
    except Exception:
        pass

    append_event(
        gobp_root=gobp_root,
        event_type="node.archived",
        payload={"id": node_id, "file": str(node_file)},
        actor=actor,
    )

    return node_file


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

    existing_edges: list[dict[str, Any]] = []
    if edge_file.exists():
        loaded = yaml.safe_load(edge_file.read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            existing_edges = loaded

    existing_edges.append(edge)

    new_content = yaml.safe_dump(
        existing_edges, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    _atomic_write(edge_file, new_content)

    try:
        _db.init_schema(gobp_root)
        _db.upsert_edge(gobp_root, edge)
        _cache_module.get_cache().invalidate_all()
    except Exception:
        pass

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

    loaded = yaml.safe_load(edge_file.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        loaded = []

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
        new_content = yaml.safe_dump(
            remaining, default_flow_style=False, sort_keys=False, allow_unicode=True
        )
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
