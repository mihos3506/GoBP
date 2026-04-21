"""GoBP governance read tools.

Schema governance, metadata linting, validation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from gobp.core.graph import GraphIndex

_METADATA_REQUIREMENTS: dict[str, list[str]] = {
    "Flow": ["description", "spec_source"],
    "Engine": ["description", "spec_source"],
    "Entity": ["description", "spec_source"],
    "Feature": ["description", "spec_source"],
    "Invariant": ["description", "rule"],
    "Screen": ["description"],
    "APIEndpoint": ["description", "spec_source"],
    "Document": ["source_path"],
    "Decision": ["what", "why"],
    "Lesson": ["description"],
    "Node": ["description"],
    "Idea": ["description"],
}


def metadata_lint(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Check all nodes for missing required metadata fields."""
    del project_root
    node_type_filter = args.get("type") or args.get("query") or None
    all_nodes = index.all_nodes()

    if node_type_filter:
        all_nodes = [n for n in all_nodes if n.get("type") == node_type_filter]

    missing_list: list[dict[str, Any]] = []
    by_type: dict[str, dict[str, Any]] = {}
    total_checked = 0
    total_complete = 0

    for node in all_nodes:
        node_type = node.get("type", "Node")
        required = _METADATA_REQUIREMENTS.get(node_type)
        if not required:
            continue

        total_checked += 1
        missing_fields = [f for f in required if not node.get(f)]

        type_stats = by_type.setdefault(node_type, {"total": 0, "complete": 0, "missing": []})
        type_stats["total"] += 1

        if missing_fields:
            missing_list.append({
                "node_id": node.get("id"),
                "node_type": node_type,
                "node_name": node.get("name", ""),
                "missing_fields": missing_fields,
            })
            type_stats["missing"].append(node.get("id"))
        else:
            total_complete += 1
            type_stats["complete"] += 1

    for t, stats in by_type.items():
        stats["score"] = round(stats["complete"] / stats["total"] * 100) if stats["total"] else 100
        del stats["missing"]

    overall_score = round(total_complete / total_checked * 100) if total_checked else 100

    return {
        "ok": True,
        "score": overall_score,
        "total_checked": total_checked,
        "total_complete": total_complete,
        "missing_count": len(missing_list),
        "missing": missing_list[:20],
        "by_type": by_type,
        "summary": (
            f"Metadata score: {overall_score}/100. "
            f"{len(missing_list)} nodes missing required fields."
        ),
    }



def schema_governance(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Cross-check schema vs documentation vs tests for drift.

    Checks:
      1. Every node type in schema has entry in SCHEMA.md
      2. Every node type has id_prefix in schema
      3. Priority field present on important types
      4. Node types referenced in tests exist in schema (when scope allows)

    Args:
        scope: 'all' | 'schema-docs' | 'schema-tests' | 'schema' (default: 'all')

    Returns:
        ok, issues[], score (0-100), summary
    """
    del index  # Unused; signature kept for consistency with other read tools.
    scope = args.get("scope", args.get("query", "all"))
    issues: list[dict[str, Any]] = []

    schema_path = project_root / "gobp" / "schema" / "core_nodes.yaml"

    try:
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
        node_types_in_schema = set(schema.get("node_types", {}).keys())
    except Exception as e:
        return {"ok": False, "error": f"Cannot load schema: {e}"}

    schema_doc_path = project_root / "docs" / "SCHEMA.md"
    if schema_doc_path.exists():
        schema_doc = schema_doc_path.read_text(encoding="utf-8")
        for node_type in node_types_in_schema:
            if node_type not in schema_doc:
                issues.append({
                    "type": "schema_doc_drift",
                    "severity": "warning",
                    "message": f"Node type '{node_type}' in schema but not documented in SCHEMA.md",
                    "node_type": node_type,
                })
    else:
        issues.append({
            "type": "missing_doc",
            "severity": "error",
            "message": "docs/SCHEMA.md not found",
        })

    for type_name, type_def in schema.get("node_types", {}).items():
        if not type_def.get("id_prefix"):
            issues.append({
                "type": "missing_id_prefix",
                "severity": "info",
                "message": (
                    f"Node type '{type_name}' has no id_prefix in schema "
                    "(optional for gobp_core_v2; Wave HOTFIX-A: not scored)"
                ),
                "node_type": type_name,
            })

    important_types = {"Node", "Idea", "Decision", "Document", "Feature", "Flow", "Engine", "Entity"}
    for type_name in important_types:
        if type_name in node_types_in_schema:
            type_def = schema["node_types"][type_name]
            optional = type_def.get("optional", {})
            if "priority" not in optional:
                issues.append({
                    "type": "missing_priority_field",
                    "severity": "warning",
                    "message": f"Node type '{type_name}' missing optional priority field",
                    "node_type": type_name,
                })

    scan_tests = scope in ("all", "schema-tests", "schema")
    tests_dir = project_root / "tests"
    if tests_dir.exists() and scan_tests:
        for test_file in tests_dir.glob("test_*.py"):
            content = test_file.read_text(encoding="utf-8", errors="replace")
            type_refs = re.findall(r'"type":\s*"([A-Z][a-zA-Z]+)"', content)
            type_refs += re.findall(r"type='([A-Z][a-zA-Z]+)'", content)
            for ref in set(type_refs):
                if ref not in node_types_in_schema and ref not in {
                    "GET", "POST", "PUT", "DELETE", "str", "int", "bool",
                }:
                    issues.append({
                        "type": "test_references_unknown_type",
                        "severity": "info",
                        "message": f"Test file '{test_file.name}' references type '{ref}' not in schema",
                        "file": test_file.name,
                        "node_type": ref,
                    })

    error_count = sum(1 for i in issues if i["severity"] == "error")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")
    score = max(0, 100 - (error_count * 20) - (warning_count * 5))

    return {
        "ok": True,
        "scope": scope,
        "issues": issues,
        "issue_count": len(issues),
        "error_count": error_count,
        "warning_count": warning_count,
        "score": score,
        "summary": (
            f"Schema governance: {score}/100. "
            f"{error_count} errors, {warning_count} warnings, "
            f"{len(issues) - error_count - warning_count} info."
        ),
        "node_types_checked": len(node_types_in_schema),
    }

