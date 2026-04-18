"""Schema loader v2 (taxonomy + lightweight validation).

Used by Wave 17A01 tests and future GraphIndex v2. Does not replace
:class:`gobp.core.loader.load_schema` for the legacy flat validator until
migration completes.

See ``waves/wave_17a01_brief.md`` Task 5.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_SCHEMA_SKIP_REQUIRED = frozenset({"what", "why", "definition", "usage_guide"})


class SchemaV2:
    """Load ``core_nodes.yaml`` / ``core_edges.yaml`` with ``node_types`` taxonomy."""

    def __init__(self, schema_dir: Path) -> None:
        nodes_path = schema_dir / "core_nodes.yaml"
        edges_path = schema_dir / "core_edges.yaml"
        self._nodes: dict[str, Any] = yaml.safe_load(nodes_path.read_text(encoding="utf-8")) or {}
        self._edges: dict[str, Any] = {}
        if edges_path.exists():
            self._edges = yaml.safe_load(edges_path.read_text(encoding="utf-8")) or {}

    @property
    def node_types(self) -> dict[str, Any]:
        return dict(self._nodes.get("node_types") or {})

    @property
    def edge_types(self) -> dict[str, Any]:
        return dict(self._edges.get("edge_types") or {})

    def get_group(self, node_type: str) -> str:
        entry = self.node_types.get(node_type, {})
        if isinstance(entry, dict):
            g = entry.get("group")
            return str(g) if g else ""
        return ""

    def get_default_read_order(self, node_type: str) -> str:
        entry = self.node_types.get(node_type, {})
        if isinstance(entry, dict):
            ro = entry.get("read_order", "reference")
            return str(ro) if ro else "reference"
        return "reference"

    def is_valid_type(self, node_type: str) -> bool:
        return node_type in self.node_types

    def validate_node(self, node: dict[str, Any]) -> list[str]:
        """Lightweight checks: core fields + type-specific required keys."""
        errors: list[str] = []
        for f in ("id", "name", "type", "group"):
            if not node.get(f):
                errors.append(f"Missing required: {f}")
        desc = node.get("description")
        if isinstance(desc, dict):
            if not str(desc.get("info", "")).strip():
                errors.append("description.info is required")
        else:
            errors.append("description.info is required")

        node_type = str(node.get("type", ""))
        type_def = self.node_types.get(node_type)
        if not isinstance(type_def, dict):
            return errors

        req = type_def.get("required")
        if isinstance(req, dict):
            for field in req:
                if field in _SCHEMA_SKIP_REQUIRED:
                    continue
                if not node.get(field):
                    errors.append(f"{node_type} requires: {field}")
        return errors


@lru_cache(maxsize=4)
def load_schema_v2(schema_dir: Path) -> SchemaV2:
    """Cached :class:`SchemaV2` for a schema directory."""
    return SchemaV2(schema_dir)
