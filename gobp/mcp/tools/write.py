"""GoBP MCP write tools.

Implementations for node_upsert, decision_lock, session_log.
All write tools require an active session_id.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.loader import load_schema
from gobp.core.mutator import create_edge, create_node, update_node
from gobp.core.validator import validate_node


def _generate_node_id(node_type: str, index: GraphIndex) -> str:
    """Generate a new node ID for auto-numbered types."""
    prefix_map = {
        "Idea": "idea",
        "Decision": "dec",
        "Lesson": "lesson",
        "Session": "session",
        "Node": "node",
        "Document": "doc",
    }
    prefix = prefix_map.get(node_type, "node")

    # For Idea, Decision, Lesson: numbered (i001, d001, ll001)
    if node_type == "Idea":
        existing_ids = [n.get("id", "") for n in index.nodes_by_type("Idea")]
        numbers = []
        for nid in existing_ids:
            if nid.startswith("idea:i"):
                try:
                    numbers.append(int(nid[6:]))
                except ValueError:
                    pass
        next_num = max(numbers, default=0) + 1
        return f"idea:i{next_num:03d}"
    elif node_type == "Decision":
        existing_ids = [n.get("id", "") for n in index.nodes_by_type("Decision")]
        numbers = []
        for nid in existing_ids:
            if nid.startswith("dec:d"):
                try:
                    numbers.append(int(nid[5:]))
                except ValueError:
                    pass
        next_num = max(numbers, default=0) + 1
        return f"dec:d{next_num:03d}"
    elif node_type == "Lesson":
        existing_ids = [n.get("id", "") for n in index.nodes_by_type("Lesson")]
        numbers = []
        for nid in existing_ids:
            if nid.startswith("lesson:ll"):
                try:
                    numbers.append(int(nid[9:]))
                except ValueError:
                    pass
        next_num = max(numbers, default=0) + 1
        return f"lesson:ll{next_num:03d}"

    # For other types, caller must provide id
    raise ValueError(f"Cannot auto-generate ID for type {node_type}, provide explicit id")


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

    # Check session exists and is active
    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}
    if session.get("status") == "COMPLETED":
        return {"ok": False, "error": "Session already ended, start new one"}

    # Determine ID
    node_id = args.get("id")
    if not node_id:
        try:
            node_id = _generate_node_id(node_type, index)
        except ValueError as e:
            return {"ok": False, "error": str(e)}

    # Build node dict
    now = datetime.now(timezone.utc).isoformat()
    node = {
        "id": node_id,
        "type": node_type,
        "name": name,
        "status": fields.get("status", "ACTIVE"),
        "created": now,
        "updated": now,
        "session_id": session_id,
    }
    # Merge fields (fields override defaults where applicable)
    for k, v in fields.items():
        node[k] = v
    # Ensure core fields stay correct
    node["id"] = node_id
    node["type"] = node_type
    node["name"] = name
    node["session_id"] = session_id

    # Load schema
    try:
        schema_path = Path(__file__).parent.parent.parent / "schema" / "core_nodes.yaml"
        schema = load_schema(schema_path)
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schema: {e}"}

    # Validate
    result = validate_node(node, schema)
    if not result.ok:
        return {"ok": False, "errors": result.errors}

    # Check if node exists
    existing = index.get_node(node_id)
    created = existing is None

    try:
        if created:
            create_node(project_root, node, schema, actor="node_upsert")
        else:
            # Preserve created timestamp on update
            node["created"] = existing.get("created", now)
            update_node(project_root, node, schema, actor="node_upsert")
    except Exception as e:
        return {"ok": False, "error": f"Write failed: {e}"}

    # Handle supersedes (create supersedes edge and mark old node)
    supersedes_id = fields.get("supersedes")
    warnings: list[str] = []
    if supersedes_id:
        old_node = index.get_node(supersedes_id)
        if old_node:
            try:
                edges_schema_path = Path(__file__).parent.parent.parent / "schema" / "core_edges.yaml"
                edges_schema = load_schema(edges_schema_path)
                supersedes_edge = {
                    "from": node_id,
                    "to": supersedes_id,
                    "type": "supersedes",
                }
                create_edge(project_root, supersedes_edge, edges_schema, actor="node_upsert")
            except Exception as e:
                warnings.append(f"Failed to create supersedes edge: {e}")
        else:
            warnings.append(f"supersedes target not found: {supersedes_id}")

    # Create discovered_in edge to session
    try:
        edges_schema_path = Path(__file__).parent.parent.parent / "schema" / "core_edges.yaml"
        edges_schema = load_schema(edges_schema_path)
        discovered_edge = {
            "from": node_id,
            "to": session_id,
            "type": "discovered_in",
        }
        create_edge(project_root, discovered_edge, edges_schema, actor="node_upsert")
    except Exception as e:
        warnings.append(f"Failed to create discovered_in edge: {e}")

    return {
        "ok": True,
        "node_id": node_id,
        "created": created,
        "warnings": warnings,
    }


def decision_lock(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Lock a decision with full verification record.

    Input: topic, what, why, alternatives_considered, risks, related_ideas, session_id, locked_by
    Output: ok, decision_id, warnings
    """
    # Required fields
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

    # Check session
    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}
    if session.get("status") == "COMPLETED":
        return {"ok": False, "error": "Session already ended"}

    # Generate decision ID
    existing_decisions = index.nodes_by_type("Decision")
    numbers: list[int] = []
    for d in existing_decisions:
        did = d.get("id", "")
        if did.startswith("dec:d"):
            try:
                numbers.append(int(did[5:]))
            except ValueError:
                pass
    next_num = max(numbers, default=0) + 1
    decision_id = f"dec:d{next_num:03d}"

    now = datetime.now(timezone.utc).isoformat()
    decision = {
        "id": decision_id,
        "type": "Decision",
        "name": what[:80],  # Short name from 'what'
        "status": "LOCKED",
        "topic": topic,
        "what": what,
        "why": why,
        "alternatives_considered": args.get("alternatives_considered", []),
        "risks": args.get("risks", []),
        "locked_by": locked_by,
        "locked_at": now,
        "created": now,
        "updated": now,
    }

    # Load schema + validate
    try:
        schema_path = Path(__file__).parent.parent.parent / "schema" / "core_nodes.yaml"
        schema = load_schema(schema_path)
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schema: {e}"}

    result = validate_node(decision, schema)
    if not result.ok:
        return {"ok": False, "errors": result.errors}

    warnings = list(result.warnings)
    if not decision["alternatives_considered"]:
        warnings.append("No alternatives_considered — recommended for locked decisions")

    # Write decision
    try:
        create_node(project_root, decision, schema, actor="decision_lock")
    except Exception as e:
        return {"ok": False, "error": f"Write failed: {e}"}

    # Create discovered_in edge
    try:
        edges_schema_path = Path(__file__).parent.parent.parent / "schema" / "core_edges.yaml"
        edges_schema = load_schema(edges_schema_path)
        create_edge(
            project_root,
            {"from": decision_id, "to": session_id, "type": "discovered_in"},
            edges_schema,
            actor="decision_lock",
        )
    except Exception as e:
        warnings.append(f"Failed to create discovered_in edge: {e}")

    # Create relates_to edges to related_ideas
    related_ideas = args.get("related_ideas", [])
    for idea_id in related_ideas:
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
        schema_path = Path(__file__).parent.parent.parent / "schema" / "core_nodes.yaml"
        schema = load_schema(schema_path)
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

        # Generate session ID: session:YYYY-MM-DD_slug
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # Slug from first word of goal
        slug_base = "".join(c if c.isalnum() else "_" for c in goal.lower())[:20].strip("_")
        if not slug_base:
            slug_base = "session"

        # Check for existing sessions today with same slug, append number if needed
        base_id = f"session:{date_str}_{slug_base}"
        session_id = base_id
        counter = 1
        while index.get_node(session_id):
            counter += 1
            session_id = f"{base_id}{counter}"

        session_node = {
            "id": session_id,
            "type": "Session",
            "name": goal[:80],
            "actor": actor,
            "started_at": now,
            "goal": goal,
            "status": "IN_PROGRESS",
            "created": now,
            "updated": now,
        }

        result = validate_node(session_node, schema)
        if not result.ok:
            return {"ok": False, "errors": result.errors}

        try:
            create_node(project_root, session_node, schema, actor="session_log")
        except Exception as e:
            return {"ok": False, "error": f"Write failed: {e}"}

        return {"ok": True, "session_id": session_id}

    # action == update or end
    session_id = args.get("session_id")
    if not session_id:
        return {"ok": False, "error": "session_id required for update/end"}

    existing = index.get_node(session_id)
    if not existing:
        return {"ok": False, "error": f"Session not found: {session_id}"}

    # Build updated session
    updated = dict(existing)
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

    # Update optional fields for both update and end
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

    return {"ok": True, "session_id": session_id}
