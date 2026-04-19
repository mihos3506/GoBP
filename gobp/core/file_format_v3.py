"""
GoBP File Format v3.

Node file format:
---
id: dev.infrastructure.engine.paymentservice.a1b2c3d4
name: PaymentService
group: Dev > Infrastructure > Engine
description: |
  Plain text description.
code: |
  optional code snippet
history:
  - description: "change log entry"
    code: ""
created_at: 2026-04-19T10:00:00Z
session_id: meta.session.2026-04-19.abc12345
---

Edge file format (relations.yaml):
- from: node_id_1
  to:   node_id_2
  reason: "why this connection exists"
  code: ""
  created_at: 2026-04-19T10:00:00Z
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def serialize_node(node: dict[str, Any]) -> str:
    """
    Serialize node dict → YAML frontmatter markdown string.

    Returns:
        String với YAML frontmatter (---...---) chứa node data.
    """
    # Build frontmatter dict — chỉ những fields cần thiết
    fm: dict[str, Any] = {
        "id": node.get("id", ""),
        "name": node.get("name", ""),
        "group": node.get("group", ""),
        "description": node.get("description", ""),
    }

    # Optional fields
    if node.get("code"):
        fm["code"] = node["code"]

    # ErrorCase severity
    if node.get("type") == "ErrorCase" and node.get("severity"):
        fm["severity"] = node["severity"]

    # History
    history = node.get("history", [])
    if history:
        fm["history"] = history

    # Metadata
    if node.get("created_at"):
        fm["created_at"] = node["created_at"]
    if node.get("session_id"):
        fm["session_id"] = node["session_id"]

    yaml_str = yaml.dump(
        fm,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    return f"---\n{yaml_str}---\n"


def deserialize_node(content: str) -> dict[str, Any]:
    """
    Deserialize YAML frontmatter markdown → node dict.

    Args:
        content: File content string

    Returns:
        Node dict. Empty dict nếu parse fail.
    """
    if not content.startswith("---"):
        return {}

    # Extract frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    try:
        node = yaml.safe_load(parts[1]) or {}
        if not isinstance(node, dict):
            return {}
        return node
    except yaml.YAMLError:
        return {}


def serialize_edges(edges: list[dict[str, Any]]) -> str:
    """
    Serialize list of edges → YAML string cho relations.yaml.

    Edge format: from, to, reason, code, created_at
    Không có type field.
    """
    if not edges:
        return ""

    edge_list = []
    for edge in edges:
        e: dict[str, Any] = {
            "from": edge.get("from_id") or edge.get("from", ""),
            "to": edge.get("to_id") or edge.get("to", ""),
            "reason": edge.get("reason", ""),
        }
        if edge.get("code"):
            e["code"] = edge["code"]
        if edge.get("created_at"):
            e["created_at"] = edge["created_at"]
        edge_list.append(e)

    return yaml.dump(
        edge_list,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )


def deserialize_edges(content: str) -> list[dict[str, Any]]:
    """
    Deserialize YAML string → list of edge dicts.

    Returns:
        List of edge dicts. Empty list nếu parse fail.
    """
    if not content.strip():
        return []
    try:
        result = yaml.safe_load(content)
        if isinstance(result, list):
            return result
        return []
    except yaml.YAMLError:
        return []


def node_file_path(gobp_dir: Path, node_id: str) -> Path:
    """Return path cho node file: .gobp/nodes/{node_id}.md"""
    safe_id = node_id.replace("/", "_").replace(":", "_")
    return gobp_dir / "nodes" / f"{safe_id}.md"


def edges_file_path(gobp_dir: Path) -> Path:
    """Return path cho edges file: .gobp/edges/relations.yaml"""
    return gobp_dir / "edges" / "relations.yaml"
