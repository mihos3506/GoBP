"""GoBP MCP write tools.

Implementations for node_upsert, decision_lock, session_log.
Writes require an audit ``session_id`` (opaque string, env ``GOBP_SESSION_ID``, or an
existing graph ``Session`` node id). Opaque ids do not create or require Session nodes.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.mcp.session_audit import resolve_write_session
from gobp.core.id_config import generate_external_id
from gobp.core.id_generator import generate_id
from gobp.core.search import find_similar_nodes, normalize_text
from gobp.core.loader import load_schema, package_schema_dir
from gobp.core.fs_mutator import (
    coerce_and_validate_node,
    create_edge,
    create_node,
    remove_edge_from_disk,
    remove_node_from_disk,
    update_node,
)


# Defaults for types with many required fields — quick capture / minimal batch lines.
TYPE_DEFAULTS: dict[str, dict[str, Any]] = {
    "Idea": {
        "raw_quote": lambda n: (
            str(n.get("description") or n.get("name") or "captured via quick entry")
        ),
        "interpretation": lambda n: str(n.get("description") or n.get("name") or ""),
        "subject": lambda n: str(n.get("subject") or n.get("category") or "general"),
        "maturity": "RAW",
        "confidence": "low",
    },
    "TestCase": {
        "given": "TBD",
        "when": "TBD",
        "then": "TBD",
    },
    "Document": {
        "registered_at": lambda n: datetime.now(timezone.utc).isoformat(),
        "last_verified": lambda n: datetime.now(timezone.utc).isoformat(),
        "content_hash": lambda n: "sha256:pending",
        "source_path": lambda n: f"docs/{str(n.get('name', '')).lower().replace(' ', '-')}.md",
    },
    "Concept": {
        "definition": lambda n: (
            str((n.get("description") or {}).get("info", ""))
            if isinstance(n.get("description"), dict)
            else str(n.get("description", "") or "")
        ),
        "usage_guide": lambda n: str(
            n.get("usage_guide") or "Usage guide — update after import"
        ),
    },
    "LessonSkill": {
        "evolve_count": 0,
        "applies_to": ["all"],
        "versions": [],
    },
    "Reflection": {
        "skills_upgraded": [],
        "skills_created": [],
        "actor": "cto_chat",
    },
    "ErrorDomain": {
        "domain": lambda n: str(n.get("domain") or n.get("name", "") or "").strip(),
        "fix_guide": lambda n: (
            str(n.get("fix_guide") or "").strip()
            or (
                str((n.get("description") or {}).get("info", ""))
                if isinstance(n.get("description"), dict)
                else str(n.get("description", "") or "")
            )
        ),
    },
}

# Inferred from ``core_nodes_v2.yaml`` (group, lifecycle, read_order). Applied after
# TYPE_DEFAULTS; :func:`coerce_and_validate_node` uses Validator v2 when schema is v2.
_TYPE_DEFAULTS_V2_CACHE: dict[str, dict[str, Any]] | None = None


def _build_type_defaults_v2() -> dict[str, dict[str, Any]]:
    from gobp.core.schema_loader import load_schema_v2

    try:
        sv2 = load_schema_v2(package_schema_dir())
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for tname in sv2.node_types:
        g = sv2.get_group(tname)
        ro = sv2.get_default_read_order(tname)
        out[tname] = {
            "group": lambda n, _g=g: _g,
            "lifecycle": "draft",
            "read_order": lambda n, _r=ro: _r,
        }
    return out


def _type_defaults_v2() -> dict[str, dict[str, Any]]:
    global _TYPE_DEFAULTS_V2_CACHE
    if _TYPE_DEFAULTS_V2_CACHE is None:
        _TYPE_DEFAULTS_V2_CACHE = _build_type_defaults_v2()
    return _TYPE_DEFAULTS_V2_CACHE


def _ensure_node_id(node: dict[str, Any], project_root: Path | None) -> None:
    """Assign ``id`` when missing (batch create / node_upsert) using v2 ``generate_id``.

    Preserves :func:`generate_external_id` behaviour for ``Session`` and ``TestCase``.
    """
    if str(node.get("id", "")).strip():
        return

    node_type = str(node.get("type", "") or "")
    name = str(node.get("name", "") or "").strip()

    if node_type == "Session":
        node["id"] = generate_external_id("Session", name=name, gobp_root=project_root)
        return
    if node_type == "TestCase":
        testkind = str(node.get("kind_id", "") or node.get("testkind", "") or "")
        node["id"] = generate_external_id(
            "TestCase",
            name=name,
            testkind=testkind,
            gobp_root=project_root,
        )
        return

    group = str(node.get("group", "") or "").strip()
    if not group and node_type:
        try:
            from gobp.core.schema_loader import load_schema_v2

            sv2 = load_schema_v2(package_schema_dir())
            g = sv2.get_group(node_type)
            if g:
                group = str(g)
                node["group"] = group
        except Exception:
            pass

    if name and group:
        node["id"] = generate_id(name, group)
    elif name and node_type:
        node["id"] = generate_id(name, node_type)
    else:
        import hashlib
        import time

        h = hashlib.md5(
            f"{node_type}:{name}:{time.time_ns()}".encode(),
            usedforsecurity=False,
        ).hexdigest()[:16]
        node["id"] = f"{node_type.lower()}.{h}" if node_type else h


def _normalize_document_content_hash(node: dict[str, Any]) -> None:
    """Normalize ``content_hash`` for Document nodes before schema validation.

    - Accepts ``sha256:<64 hex>`` (unchanged aside from lowercasing hex).
    - Accepts a bare 64-character hex string and prepends ``sha256:``.
    - Maps placeholder ``sha256:pending`` to a valid schema hash (64 zero digits).
    """
    if node.get("type") != "Document":
        return
    ch = node.get("content_hash")
    if not isinstance(ch, str):
        return
    s = ch.strip()
    if s == "sha256:pending":
        node["content_hash"] = "sha256:" + "0" * 64
        return
    if re.fullmatch(r"[a-fA-F0-9]{64}", s):
        node["content_hash"] = "sha256:" + s.lower()
        return
    if s.startswith("sha256:") and len(s) == 71:
        rest = s[7:]
        if re.fullmatch(r"[a-fA-F0-9]{64}", rest):
            node["content_hash"] = "sha256:" + rest.lower()


def _apply_v2_defaults(node: dict[str, Any], schema_v2: Any) -> None:
    """Apply schema v2 taxonomy and normalize ``description`` (mutates ``node``)."""
    from gobp.core.file_format import auto_fill_description

    nt = str(node.get("type", ""))
    if not node.get("group") and nt:
        g = schema_v2.get_group(nt)
        if g:
            node["group"] = g
    if not node.get("lifecycle"):
        node["lifecycle"] = "draft"
    if not node.get("read_order") and nt:
        node["read_order"] = schema_v2.get_default_read_order(nt)
    if "description" in node:
        node["description"] = auto_fill_description(node["description"])


def _auto_fill_defaults(node: dict[str, Any], node_type: str) -> None:
    """Fill missing required schema fields with safe defaults (mutates ``node``)."""
    defaults = TYPE_DEFAULTS.get(node_type, {})
    for field, default in defaults.items():
        cur = node.get(field)
        if cur is not None and str(cur).strip() != "":
            continue
        node[field] = default(node) if callable(default) else default
    for field, default in _type_defaults_v2().get(node_type, {}).items():
        cur = node.get(field)
        if cur is not None and str(cur).strip() != "":
            continue
        node[field] = default(node) if callable(default) else default
    try:
        from gobp.core.schema_loader import load_schema_v2

        _apply_v2_defaults(node, load_schema_v2(package_schema_dir()))
    except Exception:
        pass


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


def _handle_lesson_skill_supersedes(
    project_root: Path,
    nodes_schema: dict[str, Any],
    edges_schema: dict[str, Any],
    fresh_index: GraphIndex,
    node: dict[str, Any],
    node_id: str,
    now: str,
) -> list[str]:
    """Deprecate superseded skill, append new id to ``versions``, ensure ``supersedes`` edge.

    :func:`gobp.core.fs_mutator.create_edge` skips duplicate (from, to, type) — idempotent.
    """
    warnings: list[str] = []
    supersedes_id = str(node.get("supersedes") or "").strip()
    if not supersedes_id:
        return warnings
    old = fresh_index.get_node(supersedes_id)
    if not old:
        warnings.append(f"supersedes target not found: {supersedes_id}")
        return warnings
    old_copy = dict(old)
    old_copy["lifecycle"] = "deprecated"
    vers = list(old_copy.get("versions") or [])
    if node_id not in vers:
        vers.append(node_id)
    old_copy["versions"] = vers
    old_copy["updated"] = now
    try:
        update_node(project_root, old_copy, nodes_schema, actor="lesson_skill_supersedes")
    except Exception as e:
        warnings.append(f"Failed to update superseded LessonSkill: {e}")
    try:
        create_edge(
            project_root,
            {"from": node_id, "to": supersedes_id, "type": "supersedes"},
            edges_schema,
            actor="lesson_skill_supersedes",
        )
    except Exception as e:
        warnings.append(f"Failed to create supersedes edge: {e}")
    return warnings


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

    raw_session = args.get("session_id")
    resolved_id, session_node, sess_err, audit_auto = resolve_write_session(
        index, raw_session if raw_session else None
    )
    if sess_err:
        return {"ok": False, "error": sess_err}
    session_id = resolved_id

    explicit_id = str(args.get("id", "") or "").strip()

    now = datetime.now(timezone.utc).isoformat()
    if node_type == "Task":
        status_default = "PENDING"
    elif node_type in ("CtoDevHandoff", "QaCodeDevHandoff"):
        status_default = "OPEN"
    else:
        status_default = "ACTIVE"
    node: dict[str, Any] = {
        "type": node_type,
        "name": name,
        "status": fields.get("status", status_default),
        "created": now,
        "updated": now,
        "session_id": session_id,
    }
    if explicit_id:
        node["id"] = explicit_id
    # Merge caller fields; then re-pin the identity fields so they cannot be overridden.
    node.update(fields)
    if explicit_id:
        node["id"] = explicit_id
    node["type"] = node_type
    node["name"] = name
    node["session_id"] = session_id
    if node_type == "Task":
        if not node.get("assignee"):
            node["assignee"] = "cursor"

    if node_type == "TestKind":
        if not node.get("scope"):
            node["scope"] = "project"
        if node.get("template") is None:
            node["template"] = {}
        if not node.get("description"):
            node["description"] = (
                f'Project-local TestKind "{name}". Edit description and template as needed.'
            )

    _auto_fill_defaults(node, node_type)
    _normalize_document_content_hash(node)
    if not str(node.get("id", "")).strip():
        _ensure_node_id(node, project_root)
    node_id = str(node["id"])

    try:
        nodes_schema = load_schema(package_schema_dir() / "core_nodes.yaml")
        edges_schema = load_schema(package_schema_dir() / "core_edges.yaml")
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schema: {e}"}

    result = coerce_and_validate_node(project_root, node, nodes_schema)
    if not result.ok:
        return {"ok": False, "errors": result.errors}

    val_warnings: list[str] = list(getattr(result, "warnings", None) or [])

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
    warnings.extend(val_warnings)
    if audit_auto:
        warnings.append(
            "session_id was auto-generated (audit:…); set GOBP_SESSION_ID for stable audit grouping"
        )

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
        if node_type == "LessonSkill":
            warnings.extend(
                _handle_lesson_skill_supersedes(
                    project_root,
                    nodes_schema,
                    edges_schema,
                    fresh_index,
                    node,
                    node_id,
                    now,
                )
            )
    except Exception:
        pass

    if session_node is not None:
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
    raw_s = args.get("session_id")
    resolved_id, _session_node, sess_err, _auto = resolve_write_session(
        index, str(raw_s).strip() if raw_s is not None and str(raw_s).strip() else None
    )
    if sess_err:
        return {"ok": False, "error": sess_err}
    session_id = resolved_id

    if not node_id:
        return {"ok": False, "error": "Node ID required"}

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
    raw_s = args.get("session_id")
    resolved_id, _session_node, sess_err, _auto = resolve_write_session(
        index, str(raw_s).strip() if raw_s is not None and str(raw_s).strip() else None
    )
    if sess_err:
        return {"ok": False, "error": sess_err}
    session_id = resolved_id

    if not node_id:
        return {"ok": False, "error": "id required"}
    if not new_type:
        return {"ok": False, "error": "new_type required"}

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


def handle_edit(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Handle ``edit:`` — mutator v3 node edits (file + optional PostgreSQL v3)."""
    from gobp.core import db as db_mod
    from gobp.core.mutator_v3 import edit_node

    _ = index
    gobp_dir = project_root / ".gobp"
    node_id = str(args.get("id", "") or args.get("node_id", "")).strip()
    raw_s = args.get("session_id")
    resolved_id, _sn, sess_err, _auto = resolve_write_session(
        index,
        str(raw_s).strip() if raw_s is not None and str(raw_s).strip() else None,
    )
    if sess_err:
        return {"ok": False, "errors": [sess_err]}
    session_id = resolved_id
    exp_raw = args.get("expected_updated_at")

    expected: int | None
    if exp_raw is None or exp_raw == "":
        expected = None
    else:
        try:
            expected = int(exp_raw)
        except (TypeError, ValueError):
            expected = None

    if not node_id:
        return {"ok": False, "errors": ["id required for edit:"]}

    changes = {
        k: v
        for k, v in args.items()
        if k not in ("id", "node_id", "session_id", "expected_updated_at", "_actor")
    }
    changes["_actor"] = args.get("_actor", "unknown")

    conn = db_mod._get_conn(project_root)
    try:
        return edit_node(
            node_id=node_id,
            changes=changes,
            gobp_dir=gobp_dir,
            conn=conn,
            session_id=session_id,
            expected_updated_at=expected,
        )
    finally:
        if conn is not None:
            conn.close()


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

    resolved_id, session_node, sess_err, _auto = resolve_write_session(
        index, session_id if session_id else None
    )
    if sess_err:
        return {"ok": False, "error": sess_err}
    session_id = resolved_id

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

    result = coerce_and_validate_node(project_root, decision, nodes_schema)
    if not result.ok:
        return {"ok": False, "errors": result.errors}

    warnings = list(result.warnings)
    if not decision["alternatives_considered"]:
        warnings.append("No alternatives_considered — recommended for locked decisions")

    try:
        create_node(project_root, decision, nodes_schema, actor="decision_lock")
    except Exception as e:
        return {"ok": False, "error": f"Write failed: {e}"}

    if session_node is not None:
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


def session_resume(project_root: Path, params: dict[str, Any]) -> dict[str, Any]:
    """Load previous session handoff and nodes changed since (schema v3 PostgreSQL)."""
    from gobp.core import db as db_mod

    sid = str(params.get("id") or params.get("session_id") or "").strip()
    if not sid:
        return {"ok": False, "error": "id required for session:resume"}

    conn = db_mod._get_conn(project_root)
    if conn is None:
        return {
            "ok": False,
            "error": "PostgreSQL not available",
            "hint": "Set GOBP_DB_URL",
        }
    try:
        if db_mod.get_schema_version(conn) != "v3":
            return {
                "ok": False,
                "error": "session:resume requires PostgreSQL schema v3",
                "hint": "Use overview: to start a new session",
            }
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, desc_full, updated_at
                FROM nodes
                WHERE id = %s AND group_path LIKE 'Meta > Session%%'
                """,
                (sid,),
            )
            row = cur.fetchone()
        if not row:
            return {
                "ok": False,
                "error": f"Session not found: {sid}",
                "hint": "Use overview: to start a new session",
            }
        _prev_id, _prev_name, prev_desc, prev_updated_at = row
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, group_path, desc_l1
                FROM nodes
                WHERE updated_at > %s
                  AND group_path NOT LIKE 'Meta > Session%%'
                ORDER BY updated_at DESC
                LIMIT 20
                """,
                (prev_updated_at,),
            )
            changed_rows = cur.fetchall()
        changed_nodes = [
            {"id": r[0], "name": r[1], "group": r[2], "desc": r[3]}
            for r in changed_rows
        ]
        return {
            "ok": True,
            "resumed_from": sid,
            "prev_outcome": prev_desc or "(no outcome recorded)",
            "changes_since": changed_nodes,
            "changes_count": len(changed_nodes),
            "hint": (
                "Start new session with session:start. "
                "Changes since your last session are listed above."
            ),
        }
    finally:
        conn.close()


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

        result = coerce_and_validate_node(project_root, session_node, schema)
        if not result.ok:
            return {"ok": False, "errors": result.errors}

        try:
            create_node(project_root, session_node, schema, actor="session_log")
        except Exception as e:
            return {"ok": False, "error": f"Write failed: {e}"}

        try:
            index.register_persisted_node(session_node)
        except Exception:
            # Index sync is best-effort; disk is source of truth — caller may reload.
            pass

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
        fresh = GraphIndex.load_from_disk(project_root)
        existing = fresh.get_node(session_id)
    if not existing:
        return {"ok": False, "error": f"Session not found: {session_id}"}

    updated: dict[str, Any] = dict(existing)
    updated["updated"] = now

    if action == "end":
        status_now = str(existing.get("status", "") or "").strip().upper()
        desc_blob = f"{existing.get('desc_full', '')!s}{existing.get('description', '')!s}"
        if status_now == "COMPLETED":
            return {
                "ok": True,
                "session_id": session_id,
                "action": "skipped",
                "note": "Session already COMPLETED",
                "revision": _get_revision(session_id, project_root),
            }
        if "STALE_CLOSED" in desc_blob or "WATCHDOG CLOSED" in desc_blob:
            return {
                "ok": False,
                "error": (
                    "Session was auto-closed as stale; start a new session with "
                    "session:start instead of session:end"
                ),
            }
        if status_now and status_now != "IN_PROGRESS":
            return {
                "ok": False,
                "error": (
                    f"Cannot end session from status {existing.get('status')!r}; "
                    "expected IN_PROGRESS"
                ),
            }
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

    result = coerce_and_validate_node(project_root, updated, schema)
    if not result.ok:
        return {"ok": False, "errors": result.errors}

    try:
        update_node(project_root, updated, schema, actor="session_log")
    except Exception as e:
        return {"ok": False, "error": f"Write failed: {e}"}

    try:
        index.register_persisted_node(updated)
    except Exception:
        pass

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


INTERNAL_CHUNK_SIZE = 200

_BATCH_CREATE_RESERVED = frozenset({"kind", "node_type", "name", "description", "raw"})


def _batch_build_create_node(
    index: GraphIndex,
    project_root: Path,
    op: dict[str, Any],
    session_id: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Build a node dict for batch create (same shape as :func:`node_upsert` create path)."""
    node_type = str(op.get("node_type", ""))
    name = str(op.get("name", ""))
    desc = str(op.get("description", ""))
    if not node_type or not name:
        return None, "missing node_type or name"

    fields: dict[str, Any] = {}
    if desc:
        fields["description"] = desc
    for k, v in op.items():
        if k in _BATCH_CREATE_RESERVED:
            continue
        fields[k] = v

    explicit_id = str(op.get("id", "") or "").strip()

    now = datetime.now(timezone.utc).isoformat()
    if node_type == "Task":
        status_default = "PENDING"
    elif node_type in ("CtoDevHandoff", "QaCodeDevHandoff"):
        status_default = "OPEN"
    else:
        status_default = "ACTIVE"
    node: dict[str, Any] = {
        "type": node_type,
        "name": name,
        "status": fields.get("status", status_default),
        "created": now,
        "updated": now,
        "session_id": session_id,
    }
    if explicit_id:
        node["id"] = explicit_id
    node.update(fields)
    if explicit_id:
        node["id"] = explicit_id
    node["type"] = node_type
    node["name"] = name
    node["session_id"] = session_id
    if node_type == "Task":
        if not node.get("assignee"):
            node["assignee"] = "cursor"

    if node_type == "TestKind":
        if not node.get("scope"):
            node["scope"] = "project"
        if node.get("template") is None:
            node["template"] = {}
        if not node.get("description"):
            node["description"] = (
                f'Project-local TestKind "{name}". Edit description and template as needed.'
            )

    _auto_fill_defaults(node, node_type)
    _normalize_document_content_hash(node)
    if not str(node.get("id", "")).strip():
        _ensure_node_id(node, project_root)

    nodes_schema = load_schema(package_schema_dir() / "core_nodes.yaml")
    result = coerce_and_validate_node(project_root, node, nodes_schema)
    if not result.ok:
        return None, str(result.errors)
    return node, None


def _batch_resolve_session(
    index: GraphIndex,
    session_id: str | None,
) -> tuple[str | None, dict[str, Any] | None]:
    """Resolve audit session for batch/quick; return ``(resolved_id, error_dict)``."""
    rid, _sn, err, _auto = resolve_write_session(
        index, session_id.strip() if isinstance(session_id, str) and session_id.strip() else None
    )
    if err:
        return None, {"ok": False, "error": err}
    return rid, None


def _resolve_node_ref(index: GraphIndex, ref: str) -> str | None:
    ref = ref.strip()
    if not ref:
        return None
    if index.get_node(ref):
        return ref
    key = normalize_text(ref).replace(" ", "")
    if not key:
        return None
    matches: list[dict[str, Any]] = []
    for n in index.all_nodes():
        nk = normalize_text(str(n.get("name", ""))).replace(" ", "")
        if nk == key:
            matches.append(n)
    if not matches:
        return None
    actives = [n for n in matches if n.get("status") == "ACTIVE"]
    pick = actives[0] if actives else matches[0]
    return str(pick.get("id"))


def merge_nodes_action(
    index: GraphIndex,
    project_root: Path,
    keep_id: str,
    absorb_id: str,
    session_id: str,
) -> dict[str, Any]:
    """Rewire edges from ``absorb_id`` onto ``keep_id``, then delete absorbed node."""
    resolved, gate = _batch_resolve_session(index, session_id)
    if gate:
        return gate
    session_id = resolved or ""
    if keep_id == absorb_id:
        return {"ok": False, "error": "keep and absorb must differ"}

    keep_n = index.get_node(keep_id)
    absorb_n = index.get_node(absorb_id)
    if not keep_n or not absorb_n:
        return {"ok": False, "error": "keep or absorb node not found"}

    warnings: list[dict[str, Any]] = []
    if keep_n.get("type") != absorb_n.get("type"):
        warnings.append(
            {
                "op": "merge",
                "note": f"types differ: {keep_n.get('type')} vs {absorb_n.get('type')}",
            }
        )

    edges_schema = load_schema(package_schema_dir() / "core_edges.yaml")

    migrated = 0
    for edge in list(index.all_edges()):
        f = str(edge.get("from", ""))
        t = str(edge.get("to", ""))
        typ = str(edge.get("type", "relates_to"))
        if absorb_id not in (f, t):
            continue
        nf = keep_id if f == absorb_id else f
        nt = keep_id if t == absorb_id else t
        remove_edge_from_disk(project_root, f, t, typ, actor="merge_nodes_action")
        if nf == nt:
            continue
        new_edge: dict[str, Any] = {"from": nf, "to": nt, "type": typ}
        for extra in ("reason", "section", "lines", "legacy_from", "legacy_to"):
            if extra in edge:
                new_edge[extra] = edge[extra]
        try:
            out = create_edge(project_root, new_edge, edges_schema, actor="merge_nodes_action")
            if out.get("ok") and out.get("action") in ("created", "skipped"):
                migrated += 1
        except Exception:
            pass

    del_res = remove_node_from_disk(
        project_root,
        absorb_id,
        session_id=session_id,
        actor="merge_nodes_action",
    )
    if not del_res.get("ok"):
        return del_res

    return {
        "ok": True,
        "merged": True,
        "keep": keep_id,
        "absorbed": absorb_id,
        "edges_rewired": migrated,
        "warnings": warnings,
    }


def quick_action(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Quick capture: one line per node, ``Name | category | wave | description``."""
    from gobp.mcp.batch_parser import parse_quick

    raw_s = args.get("session_id")
    session_id = str(raw_s).strip() if raw_s is not None else ""
    ops_raw = str(args.get("ops", args.get("query", "")))
    resolved, gate = _batch_resolve_session(index, session_id if session_id else None)
    if gate:
        return gate
    session_id = resolved or ""

    qops = parse_quick(ops_raw)
    if not qops:
        return {
            "ok": False,
            "error": "No items parsed",
            "hint": "Format: Name | category | wave | description",
        }

    lines: list[str] = []
    for q in qops:
        nt = str(q.get("node_type", "Node"))
        name = str(q.get("name", "")).strip()
        if not name:
            continue
        desc = str(q.get("description", "")).strip()
        cat = str(q.get("category", "")).strip()
        wave = str(q.get("target_wave", "")).strip()
        bits: list[str] = []
        if desc:
            bits.append(desc)
        if cat:
            bits.append(f"category: {cat}")
        if wave:
            bits.append(f"wave: {wave}")
        full_desc = " ".join(bits)
        lines.append(f"create: {nt}: {name} | {full_desc}")

    batch_text = "\n".join(lines)
    if not batch_text.strip():
        return {
            "ok": False,
            "error": "No items parsed",
            "hint": "Format: Name | category | wave | description",
        }

    merged = dict(args)
    merged["session_id"] = session_id
    merged["ops"] = batch_text
    return batch_action(index, project_root, merged)


def batch_action(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Execute structured batch mutations; large op lists are processed in chunks."""
    from gobp.mcp.batch_parser import parse_batch_ops
    from gobp.mcp.session_audit import session_id_is_graph_session

    raw_s = args.get("session_id")
    session_id = str(raw_s).strip() if raw_s is not None else ""
    ops_text = str(args.get("ops", args.get("query", "")))
    resolved, gate = _batch_resolve_session(index, session_id if session_id else None)
    if gate:
        return gate
    session_id = resolved or ""

    ops, parse_errors = parse_batch_ops(ops_text)
    if parse_errors:
        return {
            "ok": False,
            "summary": "",
            "total_ops": 0,
            "succeeded": 0,
            "skipped": [],
            "errors": parse_errors,
            "warnings": [],
        }
    if not ops:
        return {
            "ok": False,
            "summary": "",
            "total_ops": 0,
            "succeeded": 0,
            "skipped": [],
            "errors": ["No operations parsed"],
            "warnings": [],
        }

    tally: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    skipped: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[dict[str, Any]] = []

    nodes_schema = load_schema(package_schema_dir() / "core_nodes.yaml")
    edges_schema = load_schema(package_schema_dir() / "core_edges.yaml")

    for chunk_start in range(0, len(ops), INTERNAL_CHUNK_SIZE):
        chunk = ops[chunk_start : chunk_start + INTERNAL_CHUNK_SIZE]
        working_index = GraphIndex.load_from_disk(project_root)

        for op in chunk:
            kind = str(op.get("kind", ""))
            tally[kind][1] += 1
            if kind not in ("create", "edge_add"):
                if working_index.has_pending_writes():
                    working_index.flush_pending_writes(project_root)
                working_index = GraphIndex.load_from_disk(project_root)
            idx = working_index
            try:
                if kind == "create":
                    nt = str(op.get("node_type", ""))
                    name = str(op.get("name", ""))
                    sim = find_similar_nodes(idx, name, nt, threshold=80)
                    if sim:
                        skipped.append(
                            {
                                "op": "create",
                                "reason": f"duplicate of {sim[0].get('id')}",
                                "name": name,
                            }
                        )
                        continue
                    node_dict, build_err = _batch_build_create_node(
                        idx, project_root, op, session_id
                    )
                    if build_err:
                        errors.append(f"create {name!r}: {build_err}")
                        continue
                    try:
                        nid = idx.add_node_in_memory(node_dict)
                        if session_id_is_graph_session(idx, session_id):
                            idx.add_edge_in_memory(nid, session_id, "discovered_in")
                    except ValueError as exc:
                        errors.append(f"create {name!r}: {exc}")
                        continue
                    tally[kind][0] += 1
    
                elif kind in ("update", "replace"):
                    nid = str(op.get("node_id", ""))
                    existing = idx.get_node(nid)
                    if not existing:
                        errors.append(f"{kind} missing node {nid}")
                        continue
                    node = dict(existing)
                    for fk, fv in (op.get("fields") or {}).items():
                        node[str(fk)] = fv
                    node["updated"] = datetime.now(timezone.utc).isoformat()
                    update_node(project_root, node, nodes_schema, actor="batch_action")
                    tally[kind][0] += 1
                    working_index = GraphIndex.load_from_disk(project_root)
                    if kind == "replace":
                        warnings.append(
                            {
                                "op": "replace",
                                "note": "replace: uses same partial merge path as update in this build",
                                "node_id": nid,
                            }
                        )
    
                elif kind == "delete":
                    nid = str(op.get("node_id", ""))
                    res = delete_node_action(
                        idx, project_root, {"id": nid, "query": nid, "session_id": session_id}
                    )
                    if not res.get("ok"):
                        errors.append(f"delete {nid!r}: {res.get('error', res)}")
                        continue
                    tally[kind][0] += 1
                    working_index = GraphIndex.load_from_disk(project_root)
    
                elif kind == "retype":
                    res = retype_node_action(
                        idx,
                        project_root,
                        {
                            "id": op.get("node_id"),
                            "new_type": op.get("new_type"),
                            "session_id": session_id,
                        },
                    )
                    if not res.get("ok"):
                        errors.append(f"retype: {res.get('error', res)}")
                        continue
                    tally[kind][0] += 1
                    working_index = GraphIndex.load_from_disk(project_root)
    
                elif kind == "merge":
                    res = merge_nodes_action(
                        idx,
                        project_root,
                        str(op.get("keep", "")),
                        str(op.get("absorb", "")),
                        session_id,
                    )
                    if not res.get("ok"):
                        errors.append(f"merge: {res.get('error', res)}")
                        continue
                    tally[kind][0] += 1
                    for w in res.get("warnings", []) or []:
                        warnings.append(w)
                    working_index = GraphIndex.load_from_disk(project_root)
    
                elif kind == "edge_add":
                    fid = _resolve_node_ref(idx, str(op.get("from_name", "")))
                    et = str(op.get("edge_type", "relates_to"))
                    if not fid:
                        errors.append(f"edge+: unresolved from in {op.get('raw')!r}")
                        continue
                    targets = op.get("targets") or []
                    if not targets:
                        errors.append(f"edge+: missing target(s) in {op.get('raw')!r}")
                        continue
                    for tgt in targets:
                        tid = _resolve_node_ref(idx, str(tgt).strip())
                        if not tid:
                            errors.append(
                                f"edge+: unresolved target {tgt!r} in {op.get('raw')!r}"
                            )
                            continue
                        try:
                            added = idx.add_edge_in_memory(fid, tid, et)
                        except ValueError as exc:
                            errors.append(f"edge+: {exc}")
                            continue
                        if not added:
                            skipped.append(
                                {
                                    "op": "edge+",
                                    "reason": "duplicate edge",
                                    "from": fid,
                                    "to": tid,
                                    "type": et,
                                }
                            )
                        else:
                            tally[kind][0] += 1
    
                elif kind == "edge_remove":
                    fid = _resolve_node_ref(idx, str(op.get("from_name", "")))
                    et = str(op.get("edge_type", "relates_to"))
                    if not fid:
                        errors.append(f"edge-: unresolved from in {op.get('raw')!r}")
                        continue
                    targets_rm = op.get("targets") or []
                    if not targets_rm:
                        errors.append(f"edge-: missing target(s) in {op.get('raw')!r}")
                        continue
                    for tgt in targets_rm:
                        tid = _resolve_node_ref(idx, str(tgt).strip())
                        if not tid:
                            errors.append(
                                f"edge-: unresolved target {tgt!r} in {op.get('raw')!r}"
                            )
                            continue
                        removed = remove_edge_from_disk(
                            project_root, fid, tid, et, actor="batch_action"
                        )
                        if removed == 0:
                            warnings.append(
                                {
                                    "op": "edge-",
                                    "note": "edge not found",
                                    "from": fid,
                                    "to": tid,
                                    "type": et,
                                }
                            )
                        tally[kind][0] += 1
                    working_index = GraphIndex.load_from_disk(project_root)
    
                elif kind == "edge_ret_type":
                    fid = _resolve_node_ref(idx, str(op.get("from_name", "")))
                    tid = _resolve_node_ref(idx, str(op.get("targets", [""])[0]))
                    old_t = str(op.get("edge_type", "relates_to"))
                    new_t = str(op.get("new_edge_type") or "").strip()
                    if not fid or not tid or not new_t:
                        errors.append(f"edge~: missing data in {op.get('raw')!r}")
                        continue
                    remove_edge_from_disk(project_root, fid, tid, old_t, actor="batch_action")
                    create_edge(
                        project_root,
                        {"from": fid, "to": tid, "type": new_t},
                        edges_schema,
                        actor="batch_action",
                    )
                    tally[kind][0] += 1
                    working_index = GraphIndex.load_from_disk(project_root)
    
                elif kind == "edge_replace_all":
                    fid = _resolve_node_ref(idx, str(op.get("from_name", "")))
                    et = str(op.get("edge_type", "relates_to"))
                    if not fid:
                        errors.append(f"edge*: unresolved from in {op.get('raw')!r}")
                        continue
                    for e in list(idx.get_edges_from(fid)):
                        if str(e.get("type", "")) == et:
                            remove_edge_from_disk(
                                project_root,
                                fid,
                                str(e.get("to", "")),
                                et,
                                actor="batch_action",
                            )
                    for tgt in op.get("targets") or []:
                        tid = _resolve_node_ref(idx, str(tgt))
                        if not tid:
                            errors.append(f"edge*: unresolved target {tgt!r}")
                            continue
                        create_edge(
                            project_root,
                            {"from": fid, "to": tid, "type": et},
                            edges_schema,
                            actor="batch_action",
                        )
                    tally[kind][0] += 1
                    working_index = GraphIndex.load_from_disk(project_root)
    
                else:
                    errors.append(f"unsupported op kind {kind!r}")
            except Exception as exc:
                errors.append(f"{kind}: {exc}")
    
        if working_index.has_pending_writes():
            working_index.flush_pending_writes(project_root)

    try:
        from gobp.mcp.server import update_cache

        final_index = GraphIndex.load_from_disk(project_root)
        update_cache(final_index, project_root)
    except ImportError:
        pass

    succeeded = sum(v[0] for v in tally.values())
    total = sum(v[1] for v in tally.values())
    parts = [f"{k}:{tally[k][0]}/{tally[k][1]}" for k in sorted(tally.keys()) if tally[k][1]]
    summary = " ".join(parts) if parts else f"ops:{total}"

    verbose = str(args.get("verbose", "false")).strip().lower() in ("true", "1", "yes", "on")
    result: dict[str, Any] = {
        "ok": len(errors) == 0,
        "summary": summary,
        "total_ops": total,
        "succeeded": succeeded,
        "errors": errors,
    }
    if verbose:
        result["skipped"] = skipped
        result["warnings"] = warnings
    else:
        if skipped:
            result["skipped"] = skipped[:10]
            if len(skipped) > 10:
                result["skipped_truncated"] = True
        if warnings:
            result["warnings"] = warnings[:10]
            if len(warnings) > 10:
                result["warnings_truncated"] = True
    return result
