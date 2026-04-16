"""GoBP priority read tools.

Priority recomputation from graph topology.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex


def recompute_priorities(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Recompute numeric priority for nodes from graph topology."""
    from gobp.mcp.tools.read import _truthy
    from gobp.core.graph import priority_label
    from gobp.mcp.tools.write import node_upsert

    dry_run = _truthy(args.get("dry_run", False))
    type_filter = args.get("type") or args.get("query") or None
    session_id = str(args.get("session_id", ""))

    all_nodes = index.all_nodes()
    if type_filter:
        all_nodes = [n for n in all_nodes if n.get("type") == type_filter]

    updated = 0
    skipped = 0
    label_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    changed: list[dict[str, Any]] = []

    for node in all_nodes:
        node_id = node.get("id", "")
        if not node_id:
            continue

        score = index.compute_priority_score(node_id)
        label = priority_label(score)
        label_counts[label] = label_counts.get(label, 0) + 1

        current_score = node.get("priority_score", -1)
        if current_score == score and node.get("priority") == label:
            skipped += 1
            continue

        changed.append({
            "node_id": node_id,
            "type": node.get("type", "Node"),
            "name": node.get("name", ""),
            "priority_score": score,
            "priority": label,
        })

        if not dry_run:
            if not session_id:
                return {
                    "ok": False,
                    "error": "session_id required unless dry_run=true",
                }
            update_fields = {k: v for k, v in node.items() if k not in ("id", "type", "name", "created", "updated")}
            update_fields.update({"priority_score": score, "priority": label})
            upsert_result = node_upsert(
                index,
                project_root,
                {
                    "id": node_id,
                    "type": node.get("type", "Node"),
                    "name": node.get("name", ""),
                    "fields": update_fields,
                    "session_id": session_id,
                },
            )
            if not upsert_result.get("ok"):
                return {
                    "ok": False,
                    "error": upsert_result.get("error", "priority recompute failed"),
                    "node_id": node_id,
                }
        updated += 1

    return {
        "ok": True,
        "updated": updated,
        "skipped": skipped,
        "dry_run": dry_run,
        "priority_distribution": label_counts,
        "changes": changed[:30],
        "summary": f"Recomputed {updated} nodes. {label_counts}",
    }


