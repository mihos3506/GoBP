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
from gobp.core.loader import load_node_file, parse_frontmatter
from gobp.core.validator import validate_edge, validate_node

_EDGE_DEDUPE_CACHE: dict[str, tuple[int, int, int, int]] = {}


def _generate_session_id(goal: str = "") -> str:
    """Generate session ID in new format.

    Format: meta.session.YYYY-MM-DD.XXXXXXXXX
    where XXXXXXXXX = first 9 chars of UUID4 hex (33 chars total).
    """
    from datetime import datetime, timezone

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    short_hash = _uuid.uuid4().hex[:9]
    return f"meta.session.{date_str}.{short_hash}"


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
    safe_name = (
        node_id.replace(":", "_").replace("/", "_").replace(".", "_")
    )
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


def create_nodes_batch(
    gobp_root: Path,
    nodes: list[dict[str, Any]],
    schema: dict[str, Any],
    actor: str = "unknown",
) -> dict[str, Any]:
    """Create many node files with one cache invalidate and batched history (Wave 16A11)."""
    from gobp.core.history import append_events_batch

    paths: list[Path] = []
    history_items: list[tuple[str, dict[str, Any], str]] = []
    try:
        _db.init_schema(gobp_root)
    except Exception:
        pass
    for node in nodes:
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
        try:
            _db.upsert_node(gobp_root, node)
        except Exception:
            pass
        paths.append(node_file)
        history_items.append(
            (
                "node.created",
                {"id": node_id, "type": node.get("type"), "file": str(node_file)},
                actor,
            )
        )
    try:
        _cache_module.get_cache().invalidate_all()
    except Exception:
        pass
    append_events_batch(gobp_root, history_items)
    return {"nodes_written": len(nodes), "paths": paths}


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


def remove_node_from_disk(
    gobp_root: Path,
    node_id: str,
    session_id: str = "",
    actor: str = "unknown",
) -> dict[str, Any]:
    """Delete a node file and remove all edges referencing it from edge YAML lists.

    Unlike :func:`delete_node` (soft-delete / archive), this removes the node
    markdown file from disk and rewrites edge files.

    Args:
        gobp_root: Project root.
        node_id: Node ID to remove.
        session_id: Active session (for audit payload).
        actor: Who is deleting.

    Returns:
        Dict with ``ok``, ``deleted_node_id``, ``deleted_edges_count``, or ``error``.
    """
    nodes_dir = gobp_root / ".gobp" / "nodes"
    node_file = _node_file_path(gobp_root, node_id)

    if not node_file.exists() and nodes_dir.exists():
        for f in nodes_dir.rglob("*.md"):
            try:
                n = load_node_file(f)
                if n.get("id") == node_id:
                    node_file = f
                    break
            except Exception:
                continue

    if not node_file.exists():
        return {"ok": False, "error": f"Node not found: {node_id}"}

    try:
        node = load_node_file(node_file)
    except Exception as e:
        return {"ok": False, "error": f"Failed to read node: {e}"}

    protected_types = {"Session", "Document"}
    if node.get("type") in protected_types:
        return {
            "ok": False,
            "error": f"Cannot delete {node.get('type')} nodes — protected type",
        }

    deleted_edges = 0
    edges_dir = gobp_root / ".gobp" / "edges"
    if edges_dir.exists():
        for edge_file in edges_dir.rglob("*.yaml"):
            try:
                data = yaml.safe_load(edge_file.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    continue
                before = len(data)
                filtered = [
                    e for e in data
                    if e.get("from") != node_id and e.get("to") != node_id
                ]
                removed = before - len(filtered)
                if removed:
                    deleted_edges += removed
                    new_content = yaml.safe_dump(
                        filtered,
                        default_flow_style=False,
                        sort_keys=False,
                        allow_unicode=True,
                    )
                    _atomic_write(edge_file, new_content)
            except Exception:
                continue

    node_file.unlink()

    try:
        _db.init_schema(gobp_root)
        _db.delete_node(gobp_root, node_id)
        _db.delete_edges_for_node(gobp_root, node_id)
        _cache_module.get_cache().invalidate_all()
    except Exception:
        pass

    append_event(
        gobp_root=gobp_root,
        event_type="node.deleted",
        payload={
            "id": node_id,
            "session_id": session_id,
            "deleted_edges_count": deleted_edges,
            "file": str(node_file),
        },
        actor=actor,
    )

    return {
        "ok": True,
        "deleted_node_id": node_id,
        "deleted_edges_count": deleted_edges,
    }


def create_edge(
    gobp_root: Path,
    edge: dict[str, Any],
    schema: dict[str, Any],
    edge_file_name: str = "relations.yaml",
    actor: str = "unknown",
) -> dict[str, Any]:
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
        Dict with edge creation status and edge_id.

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

    from_id = edge.get("from", "")
    to_id = edge.get("to", "")
    edge_type = edge.get("type", "")
    edge_id = f"{from_id}__{edge_type}__{to_id}"
    for existing in existing_edges:
        if (
            existing.get("from") == from_id
            and existing.get("to") == to_id
            and existing.get("type") == edge_type
        ):
            return {
                "ok": True,
                "action": "skipped",
                "edge_id": edge_id,
                "reason": f"Edge {from_id} --{edge_type}--> {to_id} already exists",
            }

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

    return {
        "ok": True,
        "action": "created",
        "edge_id": edge_id,
    }


def append_edges_batch(
    gobp_root: Path,
    edges: list[dict[str, Any]],
    schema: dict[str, Any],
    edge_file_name: str = "relations.yaml",
    actor: str = "unknown",
) -> dict[str, Any]:
    """Append many edges with a single read/write of the YAML file (Wave 16A11).

    Validates each edge; skips duplicates already present in the file or in-batch.
    """
    if not edges:
        return {"ok": True, "edges_written": 0, "edges_skipped": 0}

    edges_dir = gobp_root / ".gobp" / "edges"
    edges_dir.mkdir(parents=True, exist_ok=True)
    edge_file = edges_dir / edge_file_name

    existing: list[dict[str, Any]] = []
    if edge_file.exists():
        loaded = yaml.safe_load(edge_file.read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            existing = list(loaded)

    seen: set[tuple[str, str, str]] = {
        (
            str(e.get("from", "")),
            str(e.get("to", "")),
            str(e.get("type", "")),
        )
        for e in existing
    }
    appended: list[dict[str, Any]] = []
    for edge in edges:
        result = validate_edge(edge, schema)
        if not result.ok:
            raise ValueError(f"Edge validation failed: {result.errors}")
        key = (
            str(edge.get("from", "")),
            str(edge.get("to", "")),
            str(edge.get("type", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        existing.append(edge)
        appended.append(edge)

    new_content = yaml.safe_dump(
        existing, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    _atomic_write(edge_file, new_content)

    try:
        _db.init_schema(gobp_root)
        for edge in appended:
            _db.upsert_edge(gobp_root, edge)
        _cache_module.get_cache().invalidate_all()
    except Exception:
        pass

    from gobp.core.history import append_events_batch

    edge_history: list[tuple[str, dict[str, Any], str]] = [
        (
            "edge.created",
            {
                "from": edge.get("from"),
                "to": edge.get("to"),
                "type": edge.get("type"),
                "file": str(edge_file),
            },
            actor,
        )
        for edge in appended
    ]
    append_events_batch(gobp_root, edge_history)

    skipped = len(edges) - len(appended)
    return {
        "ok": True,
        "edges_written": len(appended),
        "edges_skipped": skipped,
    }


def deduplicate_edges(gobp_root: Path) -> dict[str, Any]:
    """Remove duplicate edge triples from all YAML edge files."""
    from gobp.core.loader import load_edge_file

    edges_dir = gobp_root / ".gobp" / "edges"
    if not edges_dir.exists():
        return {"ok": True, "files_processed": 0, "duplicates_removed": 0, "total_edges": 0}

    files_processed = 0
    total_duplicates = 0
    total_edges = 0

    for edge_file in edges_dir.rglob("*.yaml"):
        try:
            cache_key = str(edge_file.resolve())
            stat = edge_file.stat()
            sig = (int(stat.st_mtime_ns), stat.st_size)
            cached = _EDGE_DEDUPE_CACHE.get(cache_key)
            if cached and cached[0] == sig[0] and cached[1] == sig[1]:
                files_processed += 1
                total_duplicates += cached[2]
                total_edges += cached[3]
                continue

            # Fast-path: skip files with obvious empty-list content.
            if edge_file.stat().st_size <= 4:
                files_processed += 1
                _EDGE_DEDUPE_CACHE[cache_key] = (sig[0], sig[1], 0, 0)
                continue
            edges = load_edge_file(edge_file)
            seen: set[tuple[str, str, str]] = set()
            deduped: list[dict[str, Any]] = []
            file_duplicates = 0

            for e in edges:
                triple = (e.get("from", ""), e.get("type", ""), e.get("to", ""))
                if triple in seen:
                    total_duplicates += 1
                    file_duplicates += 1
                else:
                    seen.add(triple)
                    deduped.append(e)

            if len(deduped) < len(edges):
                edge_file.write_text(
                    yaml.safe_dump(deduped, allow_unicode=True, default_flow_style=False),
                    encoding="utf-8",
                )

            files_processed += 1
            file_total_edges = len(deduped)
            total_edges += file_total_edges
            _EDGE_DEDUPE_CACHE[cache_key] = (sig[0], sig[1], file_duplicates, file_total_edges)
        except Exception:
            continue

    return {
        "ok": True,
        "files_processed": files_processed,
        "duplicates_removed": total_duplicates,
        "total_edges": total_edges,
    }


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


def remove_edge_from_disk(
    gobp_root: Path,
    from_id: str,
    to_id: str,
    edge_type: str,
    actor: str = "unknown",
) -> int:
    """Remove edges matching ``(from_id, to_id, edge_type)`` from any YAML under ``.gobp/edges``.

    Unlike :func:`delete_edge`, which only checks a single file, this scans
    all ``*.yaml`` edge bundles so callers do not need to know which file
    stores a particular triple.

    Returns:
        Total number of matching edge rows removed across all files.
    """
    edges_dir = gobp_root / ".gobp" / "edges"
    if not edges_dir.exists():
        return 0

    total_deleted = 0
    for edge_file in edges_dir.rglob("*.yaml"):
        try:
            if not edge_file.is_file():
                continue
            loaded = yaml.safe_load(edge_file.read_text(encoding="utf-8"))
            if not isinstance(loaded, list):
                continue
            before = len(loaded)
            remaining = [
                e
                for e in loaded
                if not (
                    e.get("from") == from_id
                    and e.get("to") == to_id
                    and e.get("type") == edge_type
                )
            ]
            removed = before - len(remaining)
            if removed:
                total_deleted += removed
                new_content = yaml.safe_dump(
                    remaining,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )
                _atomic_write(edge_file, new_content)
                append_event(
                    gobp_root=gobp_root,
                    event_type="edge.deleted",
                    payload={
                        "from": from_id,
                        "to": to_id,
                        "type": edge_type,
                        "count": removed,
                        "file": str(edge_file),
                    },
                    actor=actor,
                )
        except Exception:
            continue

    try:
        _cache_module.get_cache().invalidate_all()
    except Exception:
        pass

    return total_deleted
