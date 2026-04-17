"""Conservative data normalization for MIHOS with dry-run/apply modes.

Safety rules:
- Never hard-delete nodes or edges
- Only normalize duplicate ACTIVE nodes with same (type, normalized_name_key)
- Keep one canonical node, mark the others DEPRECATED
- Add relates_to edge from deprecated duplicate -> canonical with reason
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.loader import load_schema, package_schema_dir
from gobp.core.mutator import create_edge, update_node
from gobp.core.search import normalize_text


TARGET_TYPES = {"Engine", "Entity", "Flow", "Document"}


@dataclass
class DuplicateGroup:
    node_type: str
    normalized_name_key: str
    nodes: list[dict[str, Any]]


def find_duplicate_groups(index: GraphIndex) -> list[DuplicateGroup]:
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for node in index.all_nodes():
        node_type = str(node.get("type", ""))
        if node_type not in TARGET_TYPES:
            continue
        name = str(node.get("name", "")).strip()
        if not name:
            continue
        key = (node_type, normalize_text(name).replace(" ", ""))
        by_key.setdefault(key, []).append(node)

    groups: list[DuplicateGroup] = []
    for (node_type, norm), nodes in by_key.items():
        if len(nodes) > 1:
            groups.append(DuplicateGroup(node_type=node_type, normalized_name_key=norm, nodes=nodes))
    groups.sort(key=lambda g: len(g.nodes), reverse=True)
    return groups


def select_actions(groups: list[DuplicateGroup]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for group in groups:
        active = [n for n in group.nodes if n.get("status", "ACTIVE") == "ACTIVE"]
        deprecated = [n for n in group.nodes if n.get("status") == "DEPRECATED"]
        # If already has exactly one ACTIVE and others DEPRECATED, skip (already normalized enough)
        if len(active) == 1 and len(deprecated) >= 1:
            continue
        # Conservative: only handle groups with >=2 ACTIVE nodes
        if len(active) < 2:
            continue

        # Canonical: pick lexicographically smallest id for deterministic behavior
        active_sorted = sorted(active, key=lambda n: str(n.get("id", "")))
        canonical = active_sorted[0]
        duplicates = active_sorted[1:]
        for dup in duplicates:
            actions.append(
                {
                    "type": "deprecate_duplicate",
                    "canonical_id": canonical.get("id"),
                    "duplicate_id": dup.get("id"),
                    "node_type": group.node_type,
                    "normalized_name_key": group.normalized_name_key,
                }
            )
    return actions


def apply_actions(root: Path, actions: list[dict[str, Any]]) -> dict[str, Any]:
    nodes_schema = load_schema(package_schema_dir() / "core_nodes.yaml")
    edges_schema = load_schema(package_schema_dir() / "core_edges.yaml")
    index = GraphIndex.load_from_disk(root)
    applied = []
    errors = []

    for action in actions:
        dup_id = str(action["duplicate_id"])
        canonical_id = str(action["canonical_id"])
        dup_node = index.get_node(dup_id)
        canonical_node = index.get_node(canonical_id)
        if dup_node is None or canonical_node is None:
            errors.append({"action": action, "error": "Node missing at apply time"})
            continue

        try:
            node_out = dict(dup_node)
            node_out["status"] = "DEPRECATED"
            update_node(root, node_out, nodes_schema, actor="data_normalize")
            create_edge(
                root,
                {
                    "from": dup_id,
                    "to": canonical_id,
                    "type": "relates_to",
                    "reason": "potential_duplicate_normalized",
                },
                edges_schema,
                actor="data_normalize",
            )
            applied.append(action)
        except Exception as exc:
            errors.append({"action": action, "error": str(exc)})

    return {"applied_count": len(applied), "errors": errors, "applied": applied}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="D:/MIHOS-v1")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json-out", default=".gobp/history/mihos_data_normalize_plan.json")
    args = parser.parse_args()

    root = Path(args.root)
    index = GraphIndex.load_from_disk(root)
    groups = find_duplicate_groups(index)
    actions = select_actions(groups)

    report: dict[str, Any] = {
        "project_root": str(root),
        "group_count": len(groups),
        "planned_actions": len(actions),
        "groups_preview": [
            {
                "type": g.node_type,
                "normalized_name_key": g.normalized_name_key,
                "count": len(g.nodes),
                "nodes": [
                    {"id": n.get("id"), "name": n.get("name"), "status": n.get("status")}
                    for n in g.nodes
                ],
            }
            for g in groups[:30]
        ],
        "actions": actions,
        "mode": "apply" if args.apply else "dry_run",
    }

    if args.apply:
        report["apply_result"] = apply_actions(root, actions)

    out = Path(args.json_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSaved report: {out}")

    if args.apply and report.get("apply_result", {}).get("errors"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
