"""GoBP schema validator.

Validates node and edge dicts against schemas loaded by loader.py.
Returns structured ValidationResult with errors and warnings.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ValidationResult:
    """Result of validating a node or edge against a schema.

    Attributes:
        ok: True if no errors (warnings are allowed).
        errors: List of error messages. Non-empty means validation failed.
        warnings: List of warning messages. Non-blocking.
    """

    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok


def _check_type(value: Any, expected_type: str, field_name: str) -> list[str]:
    """Check if value matches the expected type string from schema.

    Returns:
        List of error messages (empty if OK).
    """
    errors: list[str] = []

    if expected_type == "str":
        if not isinstance(value, str):
            errors.append(f"{field_name}: expected str, got {type(value).__name__}")
    elif expected_type == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{field_name}: expected int, got {type(value).__name__}")
    elif expected_type == "bool":
        if not isinstance(value, bool):
            errors.append(f"{field_name}: expected bool, got {type(value).__name__}")
    elif expected_type == "timestamp":
        if not isinstance(value, (str, datetime)):
            errors.append(f"{field_name}: expected timestamp (str or datetime), got {type(value).__name__}")
    elif expected_type == "node_ref":
        if not isinstance(value, str):
            errors.append(f"{field_name}: expected node_ref (str), got {type(value).__name__}")
    elif expected_type == "list[str]":
        if not isinstance(value, list):
            errors.append(f"{field_name}: expected list, got {type(value).__name__}")
        elif not all(isinstance(x, str) for x in value):
            errors.append(f"{field_name}: all items must be str")
    elif expected_type == "list[node_ref]":
        if not isinstance(value, list):
            errors.append(f"{field_name}: expected list, got {type(value).__name__}")
        elif not all(isinstance(x, str) for x in value):
            errors.append(f"{field_name}: all node_refs must be str")
    elif expected_type == "list[dict]":
        if not isinstance(value, list):
            errors.append(f"{field_name}: expected list, got {type(value).__name__}")
        elif not all(isinstance(x, dict) for x in value):
            errors.append(f"{field_name}: all items must be dict")
    elif expected_type == "list[int]":
        if not isinstance(value, list):
            errors.append(f"{field_name}: expected list, got {type(value).__name__}")
        elif not all(isinstance(x, int) for x in value):
            errors.append(f"{field_name}: all items must be int")
    elif expected_type == "dict":
        if not isinstance(value, dict):
            errors.append(f"{field_name}: expected dict, got {type(value).__name__}")
    elif expected_type == "enum":
        # enum validation handled separately via enum_values
        pass

    return errors


def _check_field(
    data: dict[str, Any],
    field_name: str,
    field_spec: dict[str, Any],
    is_required: bool,
) -> list[str]:
    """Check a single field against its schema spec.

    Returns:
        List of error messages (empty if OK).
    """
    errors: list[str] = []

    if field_name not in data:
        if is_required:
            errors.append(f"missing required field: {field_name}")
        return errors

    value = data[field_name]
    field_type = field_spec.get("type", "str")

    # Enum check
    if field_type == "enum":
        enum_values = field_spec.get("enum_values", [])
        if value not in enum_values:
            errors.append(f"{field_name}: value '{value}' not in allowed enum {enum_values}")
    else:
        errors.extend(_check_type(value, field_type, field_name))

    # Pattern check (for str fields)
    if "pattern" in field_spec and isinstance(value, str):
        pattern = field_spec["pattern"]
        if not re.match(pattern, value):
            errors.append(f"{field_name}: value '{value}' does not match pattern {pattern}")

    return errors


def _validate_typed_entity(
    data: dict[str, Any],
    schema: dict[str, Any],
    type_key: str,
    entity_label: str,
) -> ValidationResult:
    """Validate a data dict against a typed schema section.

    Shared implementation for validate_node and validate_edge.

    Args:
        data: Entity data dict (node or edge).
        schema: Full schema dict from loader.load_schema.
        type_key: Key within schema for the type registry
            (``"node_types"`` or ``"edge_types"``).
        entity_label: Human-readable label used in error messages
            (``"node"`` or ``"edge"``).

    Returns:
        ValidationResult.
    """
    errors: list[str] = []
    warnings: list[str] = []

    entity_type = data.get("type")
    if not entity_type:
        return ValidationResult(ok=False, errors=[f"{entity_label} missing 'type' field"])

    type_registry = schema.get(type_key, {})
    if entity_type not in type_registry:
        return ValidationResult(
            ok=False,
            errors=[f"unknown {entity_label} type: {entity_type}. Known: {list(type_registry.keys())}"],
        )

    type_def = type_registry[entity_type]

    required = type_def.get("required", {})
    for field_name, field_spec in required.items():
        errors.extend(_check_field(data, field_name, field_spec, is_required=True))

    optional = type_def.get("optional", {})
    for field_name, field_spec in optional.items():
        errors.extend(_check_field(data, field_name, field_spec, is_required=False))

    known_fields = set(required.keys()) | set(optional.keys())
    for unknown in set(data.keys()) - known_fields:
        warnings.append(f"unknown field: {unknown}")

    return ValidationResult(ok=len(errors) == 0, errors=errors, warnings=warnings)


def validate_node(node: dict[str, Any], schema: dict[str, Any]) -> ValidationResult:
    """Validate a node dict against the core_nodes schema.

    Args:
        node: Node data dict (from loader.load_node_file).
        schema: Schema dict (from loader.load_schema on core_nodes.yaml).

    Returns:
        ValidationResult with ok=True if valid.
    """
    return _validate_typed_entity(node, schema, "node_types", "node")


def validate_edge(edge: dict[str, Any], schema: dict[str, Any]) -> ValidationResult:
    """Validate an edge dict against the core_edges schema.

    Args:
        edge: Edge data dict.
        schema: Schema dict (from loader.load_schema on core_edges.yaml).

    Returns:
        ValidationResult.
    """
    return _validate_typed_entity(edge, schema, "edge_types", "edge")
