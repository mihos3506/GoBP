"""Schema loader v2 (taxonomy + lightweight validation).

Used by Wave 17A01 tests and future GraphIndex v2. Does not replace
:class:`gobp.core.loader.load_schema` for the legacy flat validator until
migration completes.

See ``waves/wave_17a01_brief.md`` Task 5.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_SCHEMA_SKIP_REQUIRED = frozenset({"what", "why", "definition", "usage_guide"})


class SchemaV2:
    """Load ``core_nodes_v2.yaml`` / ``core_edges_v2.yaml`` (taxonomy v2).

    Legacy :func:`gobp.core.loader.load_schema` continues to use
    ``core_nodes.yaml`` / ``core_edges.yaml`` for validator v1 until cutover.
    """

    def __init__(self, schema_dir: Path) -> None:
        nodes_path = schema_dir / "core_nodes_v2.yaml"
        edges_path = schema_dir / "core_edges_v2.yaml"
        if not nodes_path.exists():
            raise FileNotFoundError(
                f"Schema v2 not found: {nodes_path} (expected packaged core_nodes_v2.yaml)"
            )
        self._nodes = yaml.safe_load(nodes_path.read_text(encoding="utf-8")) or {}
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
            for field, spec in req.items():
                if field in _SCHEMA_SKIP_REQUIRED:
                    continue
                if isinstance(spec, dict) and spec.get("type") == "str":
                    val = node.get(field)
                    if val is None or (isinstance(val, str) and not val.strip()):
                        errors.append(f"{node_type} requires: {field}")
                        continue
                    pat = spec.get("pattern")
                    if pat and isinstance(val, str) and not re.match(pat, val):
                        errors.append(
                            f"{field}: value '{val}' does not match pattern {pat}"
                        )
                elif not node.get(field):
                    errors.append(f"{node_type} requires: {field}")
        return errors


@lru_cache(maxsize=4)
def load_schema_v2(schema_dir: Path) -> SchemaV2:
    """Cached :class:`SchemaV2` for a schema directory."""
    return SchemaV2(schema_dir)


def clear_schema_v2_cache() -> None:
    """Clear :func:`load_schema_v2` cache (tests / reload after schema edits)."""
    load_schema_v2.cache_clear()
