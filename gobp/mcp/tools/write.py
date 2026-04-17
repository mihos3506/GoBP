"""GoBP MCP write tools.

Implementations for node_upsert, decision_lock, session_log.
All write tools require an active session_id.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.id_config import generate_external_id
from gobp.core.search import find_similar_nodes
from gobp.core.loader import load_schema, package_schema_dir
from gobp.core.mutator import create_edge, create_node, remove_node_from_disk, update_node
from gobp.core.validator import validate_node


# (type_name, id_prefix_full, slice_index) — for auto-numbered node types.
# slice_index is the position in the full prefix where the numeric suffix begins.
_AUTO_ID_CONFIG: dict[str, tuple[str, int]] = {
    "Idea":     ("idea:i",    6),
    "Decision": ("dec:d",     5),
    "Lesson":   ("lesson:ll", 9),
}


def _get_revision(node_id: str, project_root: Path) -> int:
    """Get revision count from history log for this node."""
    try:
        from gobp.core.history import count_events_for_node

        return count_events_for_node(project_root, node_id)
    except Exception:
        return 1


def _generate_node_id(node_type: str, index: GraphIndex) -> str:
    """Generate a sequential node ID for auto-numbered types.

    Args:
        node_type: One of ``"Idea"``, ``"Decision"``, ``"Lesson"``.
        index: Current graph index used to find the highest existing number.

    Returns:
        New ID string (e.g. ``"idea:i003"``).

    Raises:
        ValueError: If node_type does not support auto-numbering.
    """
    config = _AUTO_ID_CONFIG.get(node_type)
    if config is None:
        raise ValueError(f"Cannot auto-generate ID for type {node_type}, provide explicit id")

    full_prefix, slice_idx = config
    numbers: list[int] = []
    for n in index.nodes_by_type(node_type):
        nid = n.get("id", "")
        if nid.startswith(full_prefix):
            try:
                numbers.append(int(nid[slice_idx:]))
            except ValueError:
                pass

    next_num = max(numbers, default=0) + 1
    return f"{full_prefix}{next_num:03d}"


def node_upsert(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Create or update a node.

    Input: type, id (optional for auto-numbered), name, fields, session_id
    Output: ok, node_id, created, warnings
    """
    node_type = args.get("type")
    if not node_type:
        return {"ok": False, "error": "Missing required field: type"}

    name = args.get("name")
    if not name:
        return {"ok": False, "error": "Missing required field: name"}

    fields = args.get("fields", {})
    if not isinstance(fields, dict):
        return {"ok": False, "error": "fields must be a dict"}

    session_id = args.get("session_id")
    if not session_id:
        return {"ok": False, "error": "Missing required field: session_id"}

    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}
    if session.get("status") == "COMPLETED":
        return {"ok": False, "error": "Session already ended, start new one"}

    node_id = args.get("id")
    if not node_id:
        testkind = str(fields.get("kind_id", ""))
        node_id = generate_external_id(
            node_type,
            name=name,
            testkind=testkind,
            gobp_root=project_root,
        )

    now = datetime.now(timezone.utc).isoformat()
    status_default = "PENDING" if node_type == "Task" else "ACTIVE"
    node: dict[str, Any] = {
        "id": node_id,
        "type": node_type,
        "name": name,
        "status": fields.get("status", status_default),
        "created": now,
        "updated": now,
        "session_id": session_id,
    }
    # Merge caller fields; then re-pin the identity fields so they cannot be overridden.
    node.update(fields)
    node["id"] = node_id
    node["type"] = node_type
    node["name"] = name
    node["session_id"] = session_id
    if node_type == "Task":
        if not node.get("assignee"):
            node["assignee"] = "cursor"

    try:
        nodes_schema = load_schema(package_schema_dir() / "core_nodes.yaml")
        edges_schema = load_schema(package_schema_dir() / "core_edges.yaml")
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schema: {e}"}

    result = validate_node(node, nodes_schema)
    if not result.ok:
        return {"ok": False, "errors": result.errors}

    existing = index.get_node(node_id)
    created = existing is None

    try:
        if created:
            create_node(project_root, node, nodes_schema, actor="node_upsert")
        else:
            node["created"] = existing.get("created", now)
            update_node(project_root, node, nodes_schema, actor="node_upsert")
    except Exception as e:
        return {"ok": False, "error": f"Write failed: {e}"}

    warnings: list[Any] = []

    try:
        fresh_index = GraphIndex.load_from_disk(project_root)
        similar = find_similar_nodes(fresh_index, name, node_type, threshold=80)
        similar = [n for n in similar if n.get("id") != node_id]
        if similar:
            preview = ", ".join(
                f"{n['id']} ({n.get('type', '')})" for n in similar[:3]
            )
            warnings.append(
                {
                    "type": "potential_duplicate",
                    "message": f"Similar nodes found: {preview}",
                    "similar_ids": [n["id"] for n in similar[:3]],
                }
            )
    except Exception:
        pass

    supersedes_id = fields.get("supersedes")
    if supersedes_id:
        if index.get_node(supersedes_id):
            try:
                create_edge(
                    project_root,
                    {"from": node_id, "to": supersedes_id, "type": "supersedes"},
                    edges_schema,
                    actor="node_upsert",
                )
            except Exception as e:
                warnings.append(f"Failed to create supersedes edge: {e}")
        else:
            warnings.append(f"supersedes target not found: {supersedes_id}")

    try:
        create_edge(
            project_root,
            {"from": node_id, "to": session_id, "type": "discovered_in"},
            edges_schema,
            actor="node_upsert",
        )
    except Exception as e:
        warnings.append(f"Failed to create discovered_in edge: {e}")

    if created:
        changed_fields = sorted([k for k in node.keys() if k not in ("updated", "session_id")])
        write_action = "created"
    else:
        changed_fields = sorted(
            [
                k for k, v in node.items()
                if existing is not None
                and existing.get(k) != v
                and k not in ("updated", "session_id")
            ]
        )
        write_action = "updated" if changed_fields else "skipped"

    return {
        "ok": True,
        "node_id": node_id,
        "created": created,
        "warnings": warnings,
        "action": write_action,
        "changed_fields": changed_fields,
        "conflicts": [],
        "revision": _get_revision(node_id, project_root),
    }


def delete_node_action(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Hard-delete a node and strip edges from YAML lists.

    Query shape: ``delete: {node_id} session_id='…'``.
    """
    node_id = str(args.get("query") or args.get("id") or "").strip()
    session_id = str(args.get("session_id", "")).strip()

    if not node_id:
        return {"ok": False, "error": "Node ID required"}
    if not session_id:
        return {"ok": False, "error": "session_id required"}

    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}
    if session.get("status") == "COMPLETED":
        return {"ok": False, "error": "Session already ended, start new one"}

    return remove_node_from_disk(
        project_root,
        node_id,
        session_id=session_id,
        actor="delete_node_action",
    )


def retype_node_action(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Change node type by removing the old node and creating a new ID in the correct group."""
    from gobp.mcp.parser import _normalize_type

    node_id = str(args.get("id") or args.get("query") or "").strip()
    new_type_raw = args.get("new_type")
    new_type = str(new_type_raw).strip() if new_type_raw is not None else ""
    session_id = str(args.get("session_id", "")).strip()

    if not node_id:
        return {"ok": False, "error": "id required"}
    if not new_type:
        return {"ok": False, "error": "new_type required"}
    if not session_id:
        return {"ok": False, "error": "session_id required"}

    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}
    if session.get("status") == "COMPLETED":
        return {"ok": False, "error": "Session already ended, start new one"}

    old_node = index.get_node(node_id)
    if not old_node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    new_type = _normalize_type(new_type)

    related_edges = [
        e
        for e in index.all_edges()
        if e.get("from") == node_id or e.get("to") == node_id
    ]

    del_result = remove_node_from_disk(
        project_root,
        node_id,
        session_id=session_id,
        actor="retype_node_action",
    )
    if not del_result.get("ok"):
        return del_result

    name = str(old_node.get("name", ""))
    skip = {"id", "type"}
    fields = {k: v for k, v in old_node.items() if k not in skip}
    for drop in ("session_id", "created", "updated"):
        fields.pop(drop, None)

    fresh_index = GraphIndex.load_from_disk(project_root)

    upsert_result = node_upsert(
        fresh_index,
        project_root,
        {
            "type": new_type,
            "name": name,
            "fields": fields,
            "session_id": session_id,
        },
    )
    if not upsert_result.get("ok"):
        return upsert_result

    new_id = str(upsert_result.get("node_id", ""))

    try:
        edges_schema = load_schema(package_schema_dir() / "core_edges.yaml")
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schema for edge migration: {e}"}

    edges_migrated = 0
    for edge in related_edges:
        from_id = new_id if edge.get("from") == node_id else edge.get("from")
        to_id = new_id if edge.get("to") == node_id else edge.get("to")
        edge_type = edge.get("type", "relates_to")
        new_edge: dict[str, Any] = {"from": from_id, "to": to_id, "type": edge_type}
        for extra in ("reason", "section", "lines", "legacy_from", "legacy_to"):
            if extra in edge:
                new_edge[extra] = edge[extra]
        try:
            out = create_edge(
                project_root,
                new_edge,
                edges_schema,
                actor="retype_node_action",
            )
            if out.get("ok") and out.get("action") in ("created", "skipped"):
                edges_migrated += 1
        except Exception:
            pass

    return {
        "ok": True,
        "old_id": node_id,
        "new_id": new_id,
        "new_type": new_type,
        "edges_migrated": edges_migrated,
    }


def decision_lock(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Lock a decision with full verification record.

    Input: topic, what, why, alternatives_considered, risks, related_ideas, session_id, locked_by
    Output: ok, decision_id, warnings
    """
    required = ["topic", "what", "why", "session_id", "locked_by"]
    for field in required:
        if field not in args or not args[field]:
            return {"ok": False, "error": f"Missing required field: {field}"}

    topic = args["topic"]
    what = args["what"]
    why = args["why"]
    session_id = args["session_id"]
    locked_by = args["locked_by"]

    if not isinstance(locked_by, list) or len(locked_by) < 2:
        return {
            "ok": False,
            "error": "locked_by must be a list of at least 2 entities (e.g. ['CEO', 'AI'])",
        }

    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}
    if session.get("status") == "COMPLETED":
        return {"ok": False, "error": "Session already ended"}

    decision_id = _generate_node_id("Decision", index)

    now = datetime.now(timezone.utc).isoformat()
    decision: dict[str, Any] = {
        "id": decision_id,
        "type": "Decision",
        "name": what[:80],
        "status": "LOCKED",
        "topic": topic,
        "what": what,
        "why": why,
        "alternatives_considered": args.get("alternatives_considered", []),
        "risks": args.get("risks", []),
        "locked_by": locked_by,
        "locked_at": now,
        "session_id": session_id,
        "created": now,
        "updated": now,
    }

    try:
        nodes_schema = load_schema(package_schema_dir() / "core_nodes.yaml")
        edges_schema = load_schema(package_schema_dir() / "core_edges.yaml")
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schema: {e}"}

    result = validate_node(decision, nodes_schema)
    if not result.ok:
        return {"ok": False, "errors": result.errors}

    warnings = list(result.warnings)
    if not decision["alternatives_considered"]:
        warnings.append("No alternatives_considered — recommended for locked decisions")

    try:
        create_node(project_root, decision, nodes_schema, actor="decision_lock")
    except Exception as e:
        return {"ok": False, "error": f"Write failed: {e}"}

    try:
        create_edge(
            project_root,
            {"from": decision_id, "to": session_id, "type": "discovered_in"},
            edges_schema,
            actor="decision_lock",
        )
    except Exception as e:
        warnings.append(f"Failed to create discovered_in edge: {e}")

    for idea_id in args.get("related_ideas", []):
        if index.get_node(idea_id):
            try:
                create_edge(
                    project_root,
                    {"from": decision_id, "to": idea_id, "type": "relates_to"},
                    edges_schema,
                    actor="decision_lock",
                )
            except Exception as e:
                warnings.append(f"Failed to create relates_to edge for {idea_id}: {e}")
        else:
            warnings.append(f"related_idea not found: {idea_id}")

    return {
        "ok": True,
        "decision_id": decision_id,
        "warnings": warnings,
        "action": "created",
        "changed_fields": sorted(
            [k for k in decision.keys() if k not in ("updated", "session_id")]
        ),
        "conflicts": [],
        "revision": _get_revision(decision_id, project_root),
    }


def session_log(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Start, update, or end a session.

    Input: action (start|update|end), session_id, actor, goal, outcome, pending, ...
    Output: ok, session_id
    """
    action = args.get("action")
    if action not in ("start", "update", "end"):
        return {"ok": False, "error": "action must be 'start', 'update', or 'end'"}

    try:
        schema = load_schema(package_schema_dir() / "core_nodes.yaml")
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schema: {e}"}

    now = datetime.now(timezone.utc).isoformat()

    if action == "start":
        actor = args.get("actor")
        goal = args.get("goal")
        if not actor:
            return {"ok": False, "error": "actor required for start"}
        if not goal:
            return {"ok": False, "error": "goal required for start"}

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        short_hash = __import__("uuid").uuid4().hex[:9]
        base_id = f"meta.session.{date_str}.{short_hash}"
        session_id = base_id
        counter = 1
        while index.get_node(session_id):
            counter += 1
            session_id = f"{base_id}{counter}"

        role = args.get("role", "contributor")
        valid_roles = {"observer", "contributor", "admin"}
        if role not in valid_roles:
            role = "contributor"

        session_node: dict[str, Any] = {
            "id": session_id,
            "type": "Session",
            "name": goal[:80],
            "actor": actor,
            "started_at": now,
            "goal": goal,
            "status": "IN_PROGRESS",
            "created": now,
            "updated": now,
            "role": role,
        }

        result = validate_node(session_node, schema)
        if not result.ok:
            return {"ok": False, "errors": result.errors}

        try:
            create_node(project_root, session_node, schema, actor="session_log")
        except Exception as e:
            return {"ok": False, "error": f"Write failed: {e}"}

        return {
            "ok": True,
            "session_id": session_id,
            "action": "created",
            "changed_fields": sorted(
                [k for k in session_node.keys() if k not in ("updated",)]
            ),
            "conflicts": [],
            "revision": _get_revision(session_id, project_root),
        }

    # action == "update" or "end"
    session_id = args.get("session_id")
    if not session_id:
        return {"ok": False, "error": "session_id required for update/end"}

    existing = index.get_node(session_id)
    if not existing:
        return {"ok": False, "error": f"Session not found: {session_id}"}

    updated: dict[str, Any] = dict(existing)
    updated["updated"] = now

    if action == "end":
        outcome = args.get("outcome")
        if not outcome:
            return {"ok": False, "error": "outcome required for end action"}
        updated["ended_at"] = now
        updated["outcome"] = outcome
        updated["status"] = "COMPLETED"
        if "pending" in args:
            updated["pending"] = args["pending"]

    for field in ["nodes_touched", "decisions_locked", "handoff_notes"]:
        if field in args:
            updated[field] = args[field]

    result = validate_node(updated, schema)
    if not result.ok:
        return {"ok": False, "errors": result.errors}

    try:
        update_node(project_root, updated, schema, actor="session_log")
    except Exception as e:
        return {"ok": False, "error": f"Write failed: {e}"}

    changed_fields = sorted(
        [k for k, v in updated.items() if existing.get(k) != v and k not in ("updated",)]
    )
    write_action = "updated" if changed_fields else "skipped"

    return {
        "ok": True,
        "session_id": session_id,
        "action": write_action,
        "changed_fields": changed_fields,
        "conflicts": [],
        "revision": _get_revision(session_id, project_root),
    }
