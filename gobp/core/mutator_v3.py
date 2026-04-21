"""
GoBP Mutator v3.

Write path:
  1. auto_fix   (infer group, normalize description)
  2. validate   (2 templates)
  3. generate_id
  4. extract_pyramid (desc_l1, desc_l2, desc_full)
  5. write PostgreSQL (ON CONFLICT DO UPDATE)
  6. write file backup
  7. append JSONL history log
  8. return {ok, id, conflict_warning?}

edit: = delete old + create new (with inherited history) when identity changes.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from gobp.core.db import (
    append_history_v3,
    delete_edge_v3,
    delete_node_v3,
    get_node_updated_at,
    upsert_edge_v3,
    upsert_node_v3,
)
from gobp.core.file_format_v3 import deserialize_node, node_file_path, serialize_node
from gobp.core.id_generator import generate_id
from gobp.core.pyramid import pyramid_from_node
from gobp.core.validator_v3 import ValidatorV3

_validator = ValidatorV3()


def write_node(
    node_data: dict[str, Any],
    gobp_dir: Path,
    conn: Any = None,
    session_id: str = "",
    expected_updated_at: int | None = None,
) -> dict[str, Any]:
    """Full write path for a single node.

    When ``expected_updated_at`` is set (optimistic concurrency), ``id`` must be
    present in ``node_data``. Identity-changing edits belong to :func:`edit_node`.
    """
    # 1. auto_fix
    node = _validator.auto_fix(dict(node_data))

    # 2. validate
    errors = _validator.validate(node)
    if errors:
        return {"ok": False, "errors": errors}

    # 2b. Optimistic updates must keep a stable id — otherwise a new id is generated
    # from (name, group) and upsert creates a second row while the old node remains.
    if expected_updated_at is not None and not str(node.get("id", "")).strip():
        return {
            "ok": False,
            "errors": [
                "id is required when expected_updated_at is set. "
                "For renames that change identity (name/group/type), use edit: instead of write_node."
            ],
        }

    # 3. generate_id
    if not node.get("id"):
        node["id"] = generate_id(str(node["name"]), str(node["group"]))

    # 4. extract pyramid
    l1, l2 = pyramid_from_node(node)
    node["desc_l1"] = l1
    node["desc_l2"] = l2
    node["desc_full"] = _get_full_text(node)

    # 5. optimistic lock check
    conflict_warning: dict[str, Any] | None = None
    if conn is not None and expected_updated_at is not None:
        current_ts = get_node_updated_at(conn, str(node["id"]))
        if current_ts is not None and current_ts != expected_updated_at:
            conflict_warning = {
                "conflict": True,
                "expected": expected_updated_at,
                "actual": current_ts,
                "message": "Node was modified by another agent",
            }

    # 6. write PostgreSQL
    if conn is not None:
        upsert_node_v3(conn, node)

    # 7. write file backup
    (gobp_dir / "nodes").mkdir(parents=True, exist_ok=True)
    node_file_path(gobp_dir, str(node["id"])).write_text(
        serialize_node(node), encoding="utf-8"
    )

    # 8. append history log
    _log(
        gobp_dir,
        {
            "ts": _now(),
            "op": "node_upsert",
            "actor": node_data.get("_actor", "unknown"),
            "id": node["id"],
            "session": session_id,
        },
    )

    result: dict[str, Any] = {"ok": True, "id": node["id"]}
    if conflict_warning:
        result["conflict_warning"] = conflict_warning
    return result


def edit_node(
    node_id: str,
    changes: dict[str, Any],
    gobp_dir: Path,
    conn: Any = None,
    session_id: str = "",
    expected_updated_at: int | None = None,
) -> dict[str, Any]:
    """
    edit: action — DELETE old + CREATE new when identity (name/group/type) changes.

    - description/code change: same ID, content replaced
    - type/group/name change: new ID, old deleted, history inherited
    - add_edge/remove_edge: edge operations on this node
    """
    fp = node_file_path(gobp_dir, node_id)
    if not fp.exists():
        resolved_fp = _find_node_file_by_id(gobp_dir, node_id)
        if resolved_fp is not None:
            fp = resolved_fp
        else:
            return {"ok": False, "errors": [f"Node not found: {node_id}"]}
    existing = deserialize_node(fp.read_text(encoding="utf-8"))
    if not existing:
        return {"ok": False, "errors": [f"Cannot deserialize: {node_id}"]}

    changes = dict(changes)
    add_edge = changes.pop("add_edge", None)
    remove_edge = changes.pop("remove_edge", None)
    edge_reason = str(changes.pop("reason", "") or "")
    edge_code = str(changes.pop("code_edge", "") or "")

    if add_edge and conn is not None:
        upsert_edge_v3(conn, node_id, str(add_edge), edge_reason, edge_code)
        _log(
            gobp_dir,
            {
                "ts": _now(),
                "op": "edge_add",
                "from": node_id,
                "to": str(add_edge),
                "session": session_id,
            },
        )

    if remove_edge and conn is not None:
        delete_edge_v3(conn, node_id, str(remove_edge))
        _log(
            gobp_dir,
            {
                "ts": _now(),
                "op": "edge_remove",
                "from": node_id,
                "to": str(remove_edge),
                "session": session_id,
            },
        )

    extra_hist = changes.pop("history", None)
    if not changes:
        return {"ok": True, "id": node_id}

    updated = {**existing, **changes}
    if extra_hist is not None:
        updated["history"] = list(existing.get("history", [])) + list(extra_hist)
    else:
        updated["history"] = list(existing.get("history", []))

    old_group = str(existing.get("group", "") or "")
    new_group = str(updated.get("group", old_group) or "")
    old_name = str(existing.get("name", "") or "")
    new_name = str(updated.get("name", old_name) or "")
    old_type = str(existing.get("type", "") or "")
    new_type = str(updated.get("type", old_type) or "")

    identity_changed = (new_group != old_group) or (new_name != old_name) or (new_type != old_type)

    if identity_changed:
        if new_group != old_group or new_name != old_name:
            new_id = generate_id(new_name, new_group)
        else:
            new_id = generate_id(f"{new_name}|{new_type}", new_group)
        updated["id"] = new_id
        if conn is not None:
            delete_node_v3(conn, node_id)
        if fp.exists():
            fp.unlink()
        updated["_actor"] = changes.get("_actor", "unknown")
        return write_node(updated, gobp_dir, conn, session_id, None)

    updated["_actor"] = changes.get("_actor", "unknown")
    return write_node(updated, gobp_dir, conn, session_id, expected_updated_at)


def delete_node(
    node_id: str,
    gobp_dir: Path,
    conn: Any = None,
    session_id: str = "",
) -> dict[str, Any]:
    """Soft delete: archive file + remove from PostgreSQL."""
    fp = node_file_path(gobp_dir, node_id)
    if not fp.exists():
        resolved_fp = _find_node_file_by_id(gobp_dir, node_id)
        if resolved_fp is not None:
            fp = resolved_fp
    if fp.exists():
        archive = gobp_dir / "archive"
        archive.mkdir(parents=True, exist_ok=True)
        fp.rename(archive / fp.name)

    if conn is not None:
        delete_node_v3(conn, node_id)

    _log(
        gobp_dir,
        {"ts": _now(), "op": "node_delete", "id": node_id, "session": session_id},
    )
    return {"ok": True, "id": node_id}


def _get_full_text(node: dict[str, Any]) -> str:
    desc = node.get("description", "")
    if isinstance(desc, str):
        return desc
    if isinstance(desc, dict):
        return str(desc.get("info", "") or "")
    return ""


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(gobp_dir: Path, event: dict[str, Any]) -> None:
    today = datetime.date.today().isoformat()
    log_dir = gobp_dir / "history"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / f"{today}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _find_node_file_by_id(gobp_dir: Path, node_id: str) -> Path | None:
    """Fallback lookup when canonical ``node_file_path`` is absent.

    Some legacy or external-imported projects keep node files in nested paths
    that do not match ``node_file_path(id)``. Scan ``.gobp/nodes`` and return
    the first file whose parsed ``id`` matches.
    """
    nodes_dir = gobp_dir / "nodes"
    if not nodes_dir.exists():
        return None
    for fp in nodes_dir.rglob("*.md"):
        try:
            parsed = deserialize_node(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(parsed.get("id", "") or "") == node_id:
            return fp
    return None
