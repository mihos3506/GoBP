"""GoBP prune - archive stale nodes.

A node is prunable if:
1. Its status field is "WITHDRAWN"
2. It has zero active edges (edges where neither endpoint is ACTIVE/LOCKED)

Prune does NOT delete. It moves nodes to .gobp/archive/YYYY-MM-DD/
and removes their edges from the active graph.

Prune is conservative: when in doubt, do NOT prune.
If a node has ANY edge (even to another WITHDRAWN node), skip it.

This keeps the graph clean for long-running projects without
risking data loss.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.history import append_event


def dry_run(index: GraphIndex) -> list[dict[str, Any]]:
    """Identify prunable nodes without making any changes.

    Args:
        index: Current GraphIndex.

    Returns:
        List of dicts: {id, type, name, reason}
    """
    return _find_prunable(index)


def run_prune(
    index: GraphIndex,
    gobp_root: Path,
    actor: str = "prune",
) -> dict[str, Any]:
    """Archive prunable nodes and their edges.

    Args:
        index: Current GraphIndex (used for discovery only).
        gobp_root: Project root containing .gobp/ folder.
        actor: Who initiated the prune (for history log).

    Returns:
        Dict with:
        - ok: bool
        - pruned_nodes: list[str] (IDs archived)
        - pruned_edges: list[str] (edge filenames archived)
        - archive_path: str
        - message: str
    """
    candidates = _find_prunable(index)

    if not candidates:
        return {
            "ok": True,
            "pruned_nodes": [],
            "pruned_edges": [],
            "archive_path": "",
            "message": "Nothing to prune.",
        }

    # Create archive folder
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_dir = gobp_root / ".gobp" / "archive" / date_str
    archive_dir.mkdir(parents=True, exist_ok=True)

    nodes_dir = gobp_root / ".gobp" / "nodes"
    edges_dir = gobp_root / ".gobp" / "edges"

    pruned_nodes: list[str] = []
    pruned_edges: list[str] = []

    candidate_ids = {c["id"] for c in candidates}

    # Archive node files
    for candidate in candidates:
        node_id = candidate["id"]
        # Node file: nodes/{node_id_slug}.md (replace : with -)
        node_slug = node_id.replace(":", "-")
        node_file = nodes_dir / f"{node_slug}.md"

        if node_file.exists():
            dest = archive_dir / node_file.name
            shutil.move(str(node_file), str(dest))
            pruned_nodes.append(node_id)

    # Archive edge files that reference pruned nodes
    if edges_dir.exists():
        for edge_file in edges_dir.glob("*.yaml"):
            try:
                import yaml
                with open(edge_file, encoding="utf-8") as f:
                    edge = yaml.safe_load(f) or {}
                from_id = edge.get("from", "")
                to_id = edge.get("to", "")
                if from_id in candidate_ids or to_id in candidate_ids:
                    dest = archive_dir / edge_file.name
                    shutil.move(str(edge_file), str(dest))
                    pruned_edges.append(edge_file.name)
            except Exception:
                # Skip unreadable edge files - don't block prune
                continue

    # Log to history
    append_event(
        gobp_root=gobp_root,
        event_type="graph.prune",
        payload={
            "pruned_nodes": pruned_nodes,
            "pruned_edges": pruned_edges,
            "archive_path": str(archive_dir),
        },
        actor=actor,
    )

    return {
        "ok": True,
        "pruned_nodes": pruned_nodes,
        "pruned_edges": pruned_edges,
        "archive_path": str(archive_dir),
        "message": (
            f"Pruned {len(pruned_nodes)} nodes, {len(pruned_edges)} edges "
            f"-> {archive_dir}"
        ),
    }


def _find_prunable(index: GraphIndex) -> list[dict[str, Any]]:
    """Find nodes that qualify for pruning."""
    # Build set of all node IDs referenced in any edge
    connected_ids: set[str] = set()
    for edge in index.all_edges():
        connected_ids.add(edge.get("from", ""))
        connected_ids.add(edge.get("to", ""))

    candidates = []
    for n in index.all_nodes():
        if n.get("status") != "WITHDRAWN":
            continue
        node_id = n.get("id", "")
        if node_id in connected_ids:
            continue  # Has edges, skip
        candidates.append({
            "id": node_id,
            "type": n.get("type", ""),
            "name": n.get("name", ""),
            "reason": "WITHDRAWN status + zero edges",
        })

    return candidates
