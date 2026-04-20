"""GoBP file format v2 — YAML node/edge serialization.

Node files use ``description: {info, code}``; edges support optional ``reason``.

See ``waves/wave_17a01_brief.md`` Task 4.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

FIELD_ORDER = [
    "id",
    "name",
    "type",
    "group",
    "lifecycle",
    "read_order",
    "description",
    "tags",
    "created_at",
    "session_id",
]


def auto_fill_description(desc: Any) -> dict[str, str]:
    """Normalize description to ``{info, code}`` shape."""
    if isinstance(desc, str):
        return {"info": desc, "code": ""}
    if isinstance(desc, dict):
        return {
            "info": str(desc.get("info", desc.get("description", "") or "")),
            "code": str(desc.get("code", "") or ""),
        }
    return {"info": "", "code": ""}


def serialize_node(node: dict[str, Any]) -> str:
    """Serialize node dict to YAML text (stable field order for common keys)."""
    ordered: dict[str, Any] = {f: node[f] for f in FIELD_ORDER if f in node}
    ordered.update({k: v for k, v in node.items() if k not in ordered})
    return yaml.dump(
        ordered,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )


def serialize_frontmatter(node: dict[str, Any]) -> str:
    """Serialize node fields to YAML safely (special chars escaped by PyYAML)."""
    fm: dict[str, Any] = {}
    field_order = [
        "type",
        "id",
        "name",
        "group",
        "description",
        "code",
        "implemented",
        "status",
        "priority",
        "created_at",
        "updated_at",
    ]
    for key in field_order:
        if key in node and node[key] is not None:
            fm[key] = node[key]
    for key, val in node.items():
        if key not in fm and val is not None:
            fm[key] = val
    return yaml.dump(
        fm,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=10000,
    )


def deserialize_node(content: str) -> dict[str, Any]:
    """Parse YAML node file body to dict."""
    data = yaml.safe_load(content)
    return data if isinstance(data, dict) else {}


def node_file_path(root: Path, node_id: str) -> Path:
    return root / ".gobp" / "nodes" / f"{node_id}.yaml"


def write_node(root: Path, node: dict[str, Any]) -> None:
    path = node_file_path(root, str(node["id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_node(node), encoding="utf-8")


def read_node(root: Path, node_id: str) -> dict[str, Any] | None:
    path = node_file_path(root, node_id)
    if not path.exists():
        return None
    return deserialize_node(path.read_text(encoding="utf-8"))


def append_edge(root: Path, edge: dict[str, Any]) -> None:
    """Append one edge to ``.gobp/edges/relations.yaml`` (dedupe by from/to/type)."""
    path = root / ".gobp" / "edges" / "relations.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    edges: list[Any] = []
    if path.exists() and path.stat().st_size > 0:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            edges = raw
    for e in edges:
        if not isinstance(e, dict):
            continue
        if (
            e.get("from") == edge.get("from")
            and e.get("to") == edge.get("to")
            and e.get("type") == edge.get("type")
        ):
            return
    edge = dict(edge)
    edge.setdefault("reason", "")
    edge.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    edges.append(edge)
    path.write_text(
        yaml.dump(edges, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
