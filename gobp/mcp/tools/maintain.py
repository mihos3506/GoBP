"""GoBP MCP maintenance tools.

Implementation for validate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from functools import lru_cache

from gobp.core.graph import GraphIndex
from gobp.core.loader import load_schema, package_schema_dir
from gobp.core.validator import validate_edge, validate_node


@lru_cache(maxsize=1)
def _cached_schemas() -> tuple[dict[str, Any], dict[str, Any]]:
    """Load and cache node/edge schemas for validate calls."""
    schema_dir = package_schema_dir()
    nodes_schema = load_schema(schema_dir / "core_nodes.yaml")
    edges_schema = load_schema(schema_dir / "core_edges.yaml")
    return nodes_schema, edges_schema


def validate(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Run full schema + constraint check on the entire graph.

    Input: scope (all|nodes|edges|references), severity_filter (all|hard|warning)
    Output: ok, issues, count
    """
    scope = args.get("scope", "all")
    severity_filter = args.get("severity_filter", "all")

    if scope not in ("all", "nodes", "edges", "references"):
        return {"ok": False, "error": "scope must be all, nodes, edges, or references"}

    if severity_filter not in ("all", "hard", "warning"):
        return {"ok": False, "error": "severity_filter must be all, hard, or warning"}

    # Load schemas (cached after first call)
    try:
        nodes_schema, edges_schema = _cached_schemas()
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schemas: {e}"}

    issues: list[dict[str, Any]] = []

    # Nodes
    if scope in ("all", "nodes"):
        for node in index.all_nodes():
            result = validate_node(node, nodes_schema)
            node_id = node.get("id", "<unknown>")
            for err in result.errors:
                issues.append(
                    {
                        "severity": "hard",
                        "type": "schema",
                        "node_id": node_id,
                        "message": err,
                    }
                )
            for warn in result.warnings:
                issues.append(
                    {
                        "severity": "warning",
                        "type": "schema",
                        "node_id": node_id,
                        "message": warn,
                    }
                )

    # Edges
    if scope in ("all", "edges"):
        for edge in index.all_edges():
            result = validate_edge(edge, edges_schema)
            edge_desc = f"{edge.get('from', '?')} -> {edge.get('to', '?')} ({edge.get('type', '?')})"
            for err in result.errors:
                issues.append(
                    {
                        "severity": "hard",
                        "type": "schema",
                        "edge": edge,
                        "message": f"{edge_desc}: {err}",
                    }
                )
            for warn in result.warnings:
                issues.append(
                    {
                        "severity": "warning",
                        "type": "schema",
                        "edge": edge,
                        "message": f"{edge_desc}: {warn}",
                    }
                )

    # Reference check: edge endpoints must exist as nodes
    if scope in ("all", "references"):
        for edge in index.all_edges():
            from_id = edge.get("from")
            to_id = edge.get("to")
            if from_id and not index.get_node(from_id):
                issues.append(
                    {
                        "severity": "hard",
                        "type": "reference",
                        "edge": edge,
                        "message": f"Edge source {from_id} does not exist",
                    }
                )
            if to_id and not index.get_node(to_id):
                issues.append(
                    {
                        "severity": "hard",
                        "type": "reference",
                        "edge": edge,
                        "message": f"Edge target {to_id} does not exist",
                    }
                )

    # Apply severity filter
    if severity_filter != "all":
        issues = [i for i in issues if i["severity"] == severity_filter]

    # Truncate if too many
    truncated = False
    if len(issues) > 50:
        issues = issues[:50]
        truncated = True

    hard_count = sum(1 for i in issues if i["severity"] == "hard")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")

    result_dict = {
        "ok": hard_count == 0,
        "issues": issues,
        "count": {
            "total": len(issues),
            "hard": hard_count,
            "warning": warning_count,
        },
    }
    if truncated:
        result_dict["truncated"] = True

    return result_dict
