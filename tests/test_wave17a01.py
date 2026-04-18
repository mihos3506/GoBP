"""Tests for Wave 17A01: schema v2 taxonomy, ID generator v2, file format, SchemaV2."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
import yaml

from gobp.core.file_format import (
    append_edge,
    auto_fill_description,
    deserialize_node,
    read_node,
    serialize_node,
    write_node,
)
from gobp.core.id_generator import (
    _group_to_slug,
    generate_id,
    infer_group_from_type,
)
from gobp.core.schema_loader import SchemaV2


def _write_minimal_v2_schema(schema_dir: Path) -> None:
    """Build a 65+ type taxonomy for SchemaV2 (matches brief scale; not full production YAML)."""
    pairs: list[tuple[str, str]] = []
    # Overrides for tests that assert exact groups
    pairs.append(("Entity", "Dev > Domain > Entity"))
    pairs.append(("AuthFlow", "Dev > Infrastructure > Security > AuthFlow"))
    for i in range(63):
        pairs.append((f"ZPlaceholder{i:02d}", f"Dev > Placeholder > G{i % 7}"))
    assert len(pairs) >= 65

    node_types: dict[str, object] = {}
    for name, group in pairs:
        node_types[name] = {"group": group, "read_order": "reference"}

    node_types["Invariant"] = {
        "group": "Constraint > Invariant",
        "read_order": "foundational",
        "required": {
            "rule": "str",
            "scope": "str",
            "enforcement": "str",
            "violation_action": "str",
        },
    }

    raw = {
        "schema_version": "2.0",
        "version": "2.0",
        "node_types": node_types,
    }
    schema_dir.mkdir(parents=True, exist_ok=True)
    (schema_dir / "core_nodes.yaml").write_text(
        yaml.dump(raw, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (schema_dir / "core_edges.yaml").write_text(
        yaml.dump(
            {"schema_version": "2.0", "edge_types": {"relates_to": {}}},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


@pytest.fixture
def schema(tmp_path: Path) -> SchemaV2:
    d = tmp_path / "schema"
    _write_minimal_v2_schema(d)
    return SchemaV2(d)


# --- ID generator (6) ---------------------------------------------------------


def test_generate_id_entity() -> None:
    id_ = generate_id("Traveller", "Dev > Domain > Entity")
    assert id_.startswith("dev.domain.entity.traveller.")
    assert len(id_.split(".")[-1]) == 8


def test_generate_id_security() -> None:
    id_ = generate_id("OTP Flow", "Dev > Infrastructure > Security > AuthFlow")
    assert "infra" in id_ or "sec" in id_


def test_generate_id_uniqueness() -> None:
    id1 = generate_id("Test", "Dev > Domain > Entity")
    time.sleep(0.001)
    id2 = generate_id("Test", "Dev > Domain > Entity")
    assert id1 != id2


def test_group_to_slug_abbreviation() -> None:
    slug = _group_to_slug("Dev > Infrastructure > Security")
    assert "infra" in slug
    assert "sec" in slug


def test_generate_id_doc() -> None:
    id_ = generate_id("DOC-01 Soul", "Document > Spec")
    assert id_.startswith("doc.spec.")


def test_generate_id_constraint() -> None:
    id_ = generate_id("Balance Non-Negative", "Constraint > Invariant")
    assert id_.startswith("const.invariant.")


# --- File format (7) ----------------------------------------------------------


def test_auto_fill_description_string() -> None:
    result = auto_fill_description("Test description")
    assert result == {"info": "Test description", "code": ""}


def test_auto_fill_description_dict() -> None:
    result = auto_fill_description({"info": "Test", "code": "x = 1"})
    assert result["info"] == "Test"
    assert result["code"] == "x = 1"


def test_auto_fill_description_empty() -> None:
    result = auto_fill_description({})
    assert result["info"] == ""
    assert result["code"] == ""


def test_serialize_deserialize_node() -> None:
    node = {
        "id": "dev.domain.entity.test.a1b2c3d4",
        "name": "Test",
        "type": "Entity",
        "group": "Dev > Domain > Entity",
        "lifecycle": "draft",
        "read_order": "foundational",
        "description": {"info": "Test entity", "code": ""},
    }
    yaml_str = serialize_node(node)
    result = deserialize_node(yaml_str)
    assert result["name"] == "Test"
    assert result["description"]["info"] == "Test entity"


def test_write_read_node(tmp_path: Path) -> None:
    node = {
        "id": "dev.domain.entity.test.a1b2c3d4",
        "name": "Test",
        "type": "Entity",
        "group": "Dev > Domain > Entity",
        "description": {"info": "Test", "code": ""},
    }
    write_node(tmp_path, node)
    result = read_node(tmp_path, "dev.domain.entity.test.a1b2c3d4")
    assert result is not None
    assert result["name"] == "Test"


def test_append_edge_with_reason(tmp_path: Path) -> None:
    edge = {"from": "node_a", "to": "node_b", "type": "references", "reason": "Test reason"}
    append_edge(tmp_path, edge)
    edges = yaml.safe_load((tmp_path / ".gobp" / "edges" / "relations.yaml").read_text(encoding="utf-8"))
    assert len(edges) == 1
    assert edges[0]["reason"] == "Test reason"


def test_append_edge_dedup(tmp_path: Path) -> None:
    edge = {"from": "node_a", "to": "node_b", "type": "references"}
    append_edge(tmp_path, edge)
    append_edge(tmp_path, edge)
    edges = yaml.safe_load((tmp_path / ".gobp" / "edges" / "relations.yaml").read_text(encoding="utf-8"))
    assert len(edges) == 1


# --- SchemaV2 (7) -------------------------------------------------------------


def test_schema_loads(schema: SchemaV2) -> None:
    assert len(schema.node_types) >= 60


def test_all_types_have_group(schema: SchemaV2) -> None:
    for type_name, type_def in schema.node_types.items():
        assert "group" in type_def, f"{type_name} missing group field"


def test_get_group_entity(schema: SchemaV2) -> None:
    assert schema.get_group("Entity") == "Dev > Domain > Entity"


def test_get_group_authflow(schema: SchemaV2) -> None:
    assert "Security" in schema.get_group("AuthFlow")


def test_validate_node_missing_group(schema: SchemaV2) -> None:
    node = {"id": "x", "name": "Test", "type": "Entity", "description": {"info": "Test"}}
    errors = schema.validate_node(node)
    assert any("group" in e for e in errors)


def test_validate_node_missing_description_info(schema: SchemaV2) -> None:
    node = {
        "id": "x",
        "name": "Test",
        "type": "Entity",
        "group": "Dev > Domain > Entity",
        "description": {"code": "x = 1"},
    }
    errors = schema.validate_node(node)
    assert any("description.info" in e for e in errors)


def test_validate_invariant_missing_rule(schema: SchemaV2) -> None:
    node = {
        "id": "x",
        "name": "Test",
        "type": "Invariant",
        "group": "Constraint > Invariant",
        "description": {"info": "Test"},
        "scope": "class",
        "enforcement": "hard",
        "violation_action": "reject",
    }
    errors = schema.validate_node(node)
    assert any("rule" in e for e in errors)


def test_infer_group_from_type(schema: SchemaV2) -> None:
    raw = {
        "node_types": {
            "Entity": {"group": "Dev > Domain > Entity"},
        }
    }
    assert infer_group_from_type("Entity", raw) == "Dev > Domain > Entity"
