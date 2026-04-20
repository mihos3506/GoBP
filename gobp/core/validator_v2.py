"""GoBP Validator v2 ΓÇö validates nodes and edges against schema v2.

See ``waves/wave_17a02_brief.md`` Task 1.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from gobp.core.file_format import auto_fill_description
from gobp.core.schema_loader import SchemaV2, load_schema_v2


class ValidatorV2:
    """Node and edge validator for GoBP schema v2 (taxonomy YAML)."""

    def __init__(self, schema: SchemaV2) -> None:
        self._schema = schema

    def validate_node(self, node: dict[str, Any]) -> list[str]:
        """Validate node dict. Returns a list of error strings (empty if OK)."""
        errors: list[str] = []
        node_type = str(node.get("type", ""))

        for field in ("id", "name", "type", "group"):
            if not node.get(field):
                errors.append(f"Missing required field: '{field}'")

        desc = node.get("description")
        if isinstance(desc, str):
            if not desc.strip():
                errors.append("description must be non-empty string or {info, code} dict")
        elif isinstance(desc, dict):
            if not str(desc.get("info", "")).strip():
                errors.append("description.info is required and cannot be empty")
        else:
            errors.append("description must be string or {info, code} dict")

        if node_type and not self._schema.is_valid_type(node_type):
            valid = sorted(self._schema.node_types.keys())
            preview = ", ".join(valid[:12])
            errors.append(
                f"Unknown node type: '{node_type}'. Valid types (sample): {preview}..."
            )
            return errors

        type_def = self._schema.node_types.get(node_type, {})
        if not isinstance(type_def, dict):
            return errors

        type_required = type_def.get("required", {})
        if isinstance(type_required, dict):
            for field, field_spec in type_required.items():
                value = node.get(field)
                if _is_empty_value(value):
                    errors.append(f"Type '{node_type}' requires field: '{field}'")
                    continue
                if isinstance(field_spec, dict):
                    pat = field_spec.get("pattern")
                    if pat and isinstance(value, str) and not re.match(pat, value):
                        errors.append(
                            f"Field '{field}' value '{value}' does not match pattern: {pat}"
                        )
                    enum_values = field_spec.get("values") or field_spec.get("enum_values")
                    if enum_values and value not in enum_values:
                        errors.append(
                            f"Field '{field}' must be one of: "
                            f"{', '.join(str(v) for v in enum_values)}. Got: '{value}'"
                        )
                elif isinstance(field_spec, str):
                    if _is_empty_value(value):
                        errors.append(f"Type '{node_type}' requires field: '{field}'")

        type_optional = type_def.get("optional", {})
        if isinstance(type_optional, dict):
            for field, field_spec in type_optional.items():
                value = node.get(field)
                if value is None:
                    continue
                if not isinstance(field_spec, dict):
                    continue
                enum_values = field_spec.get("values") or field_spec.get("enum_values")
                if enum_values and value not in enum_values:
                    errors.append(
                        f"Field '{field}' must be one of: "
                        f"{', '.join(str(v) for v in enum_values)}. Got: '{value}'"
                    )

        return errors

    def validate_edge(self, edge: dict[str, Any]) -> list[str]:
        """Validate edge dict (from, to, type, optional reason)."""
        errors: list[str] = []
        for field in ("from", "to", "type"):
            if not edge.get(field):
                errors.append(f"Edge missing required field: '{field}'")
        edge_type = str(edge.get("type", ""))
        if edge_type and not self._schema.is_valid_edge_type(edge_type):
            errors.append(f"Unknown edge type: '{edge_type}'")
        return errors

    def auto_fix(self, node: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of node with common fixes (description, group, lifecycle, read_order)."""
        out = dict(node)
        if "description" in out:
            out["description"] = auto_fill_description(out["description"])
        else:
            out["description"] = {"info": "", "code": ""}
        if not str(out["description"].get("info", "")).strip():
            fb = (
                str(out.get("name") or "").strip()
                or str(out.get("goal") or "").strip()
                or str(out.get("what") or "").strip()
                or "ΓÇö"
            )
            out["description"] = {
                "info": fb[:8000],
                "code": str(out["description"].get("code", "") or ""),
            }

        nt = str(out.get("type", ""))
        if not out.get("group") and nt:
            g = self._schema.get_group(nt)
            if g:
                out["group"] = g
        if not out.get("lifecycle"):
            out["lifecycle"] = "draft"
        if not out.get("read_order") and nt:
            out["read_order"] = self._schema.get_default_read_order(nt)
        return out


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def make_validator_v2(schema_dir: Path) -> ValidatorV2:
    """Build a :class:`ValidatorV2` from a directory containing v2 schema files."""
    return ValidatorV2(load_schema_v2(schema_dir))
