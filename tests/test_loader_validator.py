"""Tests for loader.py and validator.py."""

from pathlib import Path

import pytest
import yaml

from gobp.core.loader import (
    load_edge_file,
    load_node_file,
    load_schema,
    parse_frontmatter,
)
from gobp.core.validator import ValidationResult, validate_edge, validate_node


# =============================================================================
# parse_frontmatter tests
# =============================================================================


def test_parse_frontmatter_basic():
    content = "---\nid: test\ntype: Node\n---\nBody here"
    fm, body = parse_frontmatter(content)
    assert fm == {"id": "test", "type": "Node"}
    assert body == "Body here"


def test_parse_frontmatter_crlf():
    content = "---\r\nid: test\r\ntype: Node\r\n---\r\nBody"
    fm, body = parse_frontmatter(content)
    assert fm["id"] == "test"
    assert "Body" in body


def test_parse_frontmatter_empty_body():
    content = "---\nid: test\n---\n"
    fm, body = parse_frontmatter(content)
    assert fm == {"id": "test"}


def test_parse_frontmatter_no_frontmatter():
    content = "Just plain text without frontmatter"
    fm, body = parse_frontmatter(content)
    assert fm == {}
    assert body == content


def test_parse_frontmatter_malformed_raises():
    content = "---\nid: test\nno closing marker"
    with pytest.raises(ValueError, match="missing closing"):
        parse_frontmatter(content)


# =============================================================================
# load_schema tests
# =============================================================================


def test_load_schema_nodes(tmp_path: Path):
    schema_content = {
        "schema_version": "1.0",
        "node_types": {"Node": {"required": {"id": {"type": "str"}}}},
    }
    schema_file = tmp_path / "schema.yaml"
    schema_file.write_text(yaml.dump(schema_content))

    loaded = load_schema(schema_file)
    assert loaded["schema_version"] == "1.0"
    assert "Node" in loaded["node_types"]


def test_load_schema_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_schema(tmp_path / "nonexistent.yaml")


def test_load_schema_missing_version_raises(tmp_path: Path):
    schema_file = tmp_path / "bad.yaml"
    schema_file.write_text("node_types: {}")

    with pytest.raises(ValueError, match="schema_version"):
        load_schema(schema_file)


def test_load_core_schemas_actual():
    """Load the actual GoBP core schemas."""
    import gobp

    schema_dir = Path(gobp.__file__).parent / "schema"

    nodes_schema = load_schema(schema_dir / "core_nodes.yaml")
    edges_schema = load_schema(schema_dir / "core_edges.yaml")

    assert nodes_schema["schema_version"] == "1.0"
    assert edges_schema["schema_version"] == "1.0"
    assert "node_types" in nodes_schema
    assert "edge_types" in edges_schema


# =============================================================================
# load_node_file tests
# =============================================================================


def test_load_node_file(tmp_path: Path):
    node_content = """---
id: node:test
type: Node
name: Test Node
status: ACTIVE
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
---

Body content here.
"""
    node_file = tmp_path / "test_node.md"
    node_file.write_text(node_content)

    data = load_node_file(node_file)
    assert data["id"] == "node:test"
    assert data["type"] == "Node"


def test_load_node_file_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_node_file(tmp_path / "nope.md")


def test_load_node_file_no_frontmatter_raises(tmp_path: Path):
    bad_file = tmp_path / "bad.md"
    bad_file.write_text("Just content, no frontmatter")

    with pytest.raises(ValueError, match="no frontmatter"):
        load_node_file(bad_file)


# =============================================================================
# load_edge_file tests
# =============================================================================


def test_load_edge_file_list(tmp_path: Path):
    edge_content = """
- from: node:a
  to: node:b
  type: relates_to
- from: node:b
  to: node:c
  type: implements
"""
    edge_file = tmp_path / "edges.yaml"
    edge_file.write_text(edge_content)

    edges = load_edge_file(edge_file)
    assert len(edges) == 2
    assert edges[0]["type"] == "relates_to"


def test_load_edge_file_empty(tmp_path: Path):
    edge_file = tmp_path / "empty.yaml"
    edge_file.write_text("")

    edges = load_edge_file(edge_file)
    assert edges == []


def test_load_edge_file_not_list_raises(tmp_path: Path):
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("not_a_list: true")

    with pytest.raises(ValueError, match="must contain a YAML list"):
        load_edge_file(bad_file)


# =============================================================================
# validate_node tests
# =============================================================================


@pytest.fixture
def sample_nodes_schema():
    return {
        "schema_version": "1.0",
        "node_types": {
            "Node": {
                "required": {
                    "id": {"type": "str", "pattern": r"^node:[a-z][a-z0-9_]*$"},
                    "type": {"type": "str"},
                    "name": {"type": "str"},
                    "status": {
                        "type": "enum",
                        "enum_values": ["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"],
                    },
                    "created": {"type": "timestamp"},
                    "updated": {"type": "timestamp"},
                },
                "optional": {
                    "tags": {"type": "list[str]"},
                },
            }
        },
    }


def test_validate_node_valid(sample_nodes_schema):
    node = {
        "id": "node:test",
        "type": "Node",
        "name": "Test",
        "status": "ACTIVE",
        "created": "2026-04-14T00:00:00",
        "updated": "2026-04-14T00:00:00",
    }
    result = validate_node(node, sample_nodes_schema)
    assert result.ok
    assert result.errors == []


def test_validate_node_missing_required(sample_nodes_schema):
    node = {"id": "node:test", "type": "Node"}  # missing name, status, etc.
    result = validate_node(node, sample_nodes_schema)
    assert not result.ok
    assert any("name" in e for e in result.errors)


def test_validate_node_invalid_enum(sample_nodes_schema):
    node = {
        "id": "node:test",
        "type": "Node",
        "name": "Test",
        "status": "INVALID_STATUS",
        "created": "2026-04-14T00:00:00",
        "updated": "2026-04-14T00:00:00",
    }
    result = validate_node(node, sample_nodes_schema)
    assert not result.ok
    assert any("enum" in e for e in result.errors)


def test_validate_node_pattern_fail(sample_nodes_schema):
    node = {
        "id": "BAD_ID",  # doesn't match pattern
        "type": "Node",
        "name": "Test",
        "status": "ACTIVE",
        "created": "2026-04-14T00:00:00",
        "updated": "2026-04-14T00:00:00",
    }
    result = validate_node(node, sample_nodes_schema)
    assert not result.ok
    assert any("pattern" in e for e in result.errors)


def test_validate_node_unknown_type(sample_nodes_schema):
    node = {"id": "x:1", "type": "UnknownType"}
    result = validate_node(node, sample_nodes_schema)
    assert not result.ok
    assert any("unknown node type" in e for e in result.errors)


def test_validate_node_missing_type(sample_nodes_schema):
    node = {"id": "x:1"}
    result = validate_node(node, sample_nodes_schema)
    assert not result.ok
    assert any("type" in e for e in result.errors)


def test_validate_node_unknown_field_warns(sample_nodes_schema):
    node = {
        "id": "node:test",
        "type": "Node",
        "name": "Test",
        "status": "ACTIVE",
        "created": "2026-04-14T00:00:00",
        "updated": "2026-04-14T00:00:00",
        "extra_unknown_field": "hello",
    }
    result = validate_node(node, sample_nodes_schema)
    assert result.ok  # warnings don't fail
    assert any("extra_unknown_field" in w for w in result.warnings)


# =============================================================================
# validate_edge tests
# =============================================================================


@pytest.fixture
def sample_edges_schema():
    return {
        "schema_version": "1.0",
        "edge_types": {
            "relates_to": {
                "required": {
                    "from": {"type": "node_ref"},
                    "to": {"type": "node_ref"},
                    "type": {"type": "str", "enum_values": ["relates_to"]},
                },
                "optional": {
                    "reason": {"type": "str"},
                },
            }
        },
    }


def test_validate_edge_valid(sample_edges_schema):
    edge = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    result = validate_edge(edge, sample_edges_schema)
    assert result.ok


def test_validate_edge_missing_from(sample_edges_schema):
    edge = {"to": "node:b", "type": "relates_to"}
    result = validate_edge(edge, sample_edges_schema)
    assert not result.ok
    assert any("from" in e for e in result.errors)


def test_validate_edge_unknown_type(sample_edges_schema):
    edge = {"from": "node:a", "to": "node:b", "type": "unknown_edge"}
    result = validate_edge(edge, sample_edges_schema)
    assert not result.ok


# =============================================================================
# ValidationResult tests
# =============================================================================


def test_validation_result_truthy():
    ok_result = ValidationResult(ok=True)
    assert bool(ok_result) is True

    fail_result = ValidationResult(ok=False, errors=["e"])
    assert bool(fail_result) is False
