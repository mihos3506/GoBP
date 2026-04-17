"""Whitelist-safe cleanup for schema warning fields on MIHOS data.

This migration is conservative:
- Only touches fields that are unknown to schema AND in SAFE_REMOVE_FIELDS
- Never deletes nodes/edges
- Uses update_node() so writes stay validated and auditable
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.loader import load_schema, package_schema_dir
from gobp.core.mutator import update_node

SAFE_REMOVE_FIELDS = {
    "legacy_id",
    "priority_score",
    "session_id",
    "source_doc",
    "node_id",
    "fields",
    "input",
    "output",
    "category",
    "entity_kind",
    "phase_1_required",
}


def allowed_fields_for_type(nodes_schema: dict[str, Any], node_type: str) -> set[str]:
    type_def = nodes_schema.get("node_types", {}).get(node_type, {})
    req = set(type_def.get("required", {}).keys())
    opt = set(type_def.get("optional", {}).keys())
    return req | opt


def plan_cleanup(index: GraphIndex, nodes_schema: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for node in index.all_nodes():
        node_type = str(node.get("type", ""))
        allowed = allowed_fields_for_type(nodes_schema, node_type)
        unknown = [k for k in node.keys() if k not in allowed]
        removable = [k for k in unknown if k in SAFE_REMOVE_FIELDS]
        if removable:
            actions.append(
                {
                    "node_id": node.get("id"),
                    "type": node_type,
                    "remove_fields": sorted(removable),
                    "unknown_fields": sorted(unknown),
                }
            )
    return actions


def apply_cleanup(root: Path, nodes_schema: dict[str, Any], actions: list[dict[str, Any]]) -> dict[str, Any]:
    index = GraphIndex.load_from_disk(root)
    applied: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for action in actions:
        node_id = str(action["node_id"])
        node = index.get_node(node_id)
        if node is None:
            errors.append({"node_id": node_id, "error": "node_not_found"})
            continue
        node_out = dict(node)
        for field in action["remove_fields"]:
            node_out.pop(field, None)
        try:
            update_node(root, node_out, nodes_schema, actor="schema_warning_cleanup")
            applied.append(action)
        except Exception as exc:
            errors.append({"node_id": node_id, "error": str(exc), "action": action})

    return {"applied_count": len(applied), "error_count": len(errors), "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="D:/MIHOS-v1")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--json-out",
        default=".gobp/history/mihos_schema_warning_cleanup_plan.json",
    )
    args = parser.parse_args()

    root = Path(args.root)
    nodes_schema = load_schema(package_schema_dir() / "core_nodes.yaml")
    index = GraphIndex.load_from_disk(root)
    actions = plan_cleanup(index, nodes_schema)

    report: dict[str, Any] = {
        "project_root": str(root),
        "mode": "apply" if args.apply else "dry_run",
        "candidate_nodes": len(actions),
        "actions_preview": actions[:50],
    }

    if args.apply:
        report["apply_result"] = apply_cleanup(root, nodes_schema, actions)

    out = Path(args.json_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSaved report: {out}")

    if args.apply and report.get("apply_result", {}).get("error_count", 0) > 0:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
