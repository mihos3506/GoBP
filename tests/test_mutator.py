"""Tests for gobp.core.mutator module."""

from pathlib import Path

import pytest
import yaml

from gobp.core.history import read_events
from gobp.core.mutator import (
    create_edge,
    create_node,
    delete_edge,
    delete_node,
    update_node,
)


@pytest.fixture
def nodes_schema():
    """Minimal nodes schema for testing."""
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
                "optional": {},
            }
        },
    }


@pytest.fixture
def edges_schema():
    """Minimal edges schema for testing."""
    return {
        "schema_version": "1.0",
        "edge_types": {
            "relates_to": {
                "required": {
                    "from": {"type": "node_ref"},
                    "to": {"type": "node_ref"},
                    "type": {"type": "str", "enum_values": ["relates_to"]},
                },
                "optional": {},
            }
        },
    }


@pytest.fixture
def sample_node():
    return {
        "id": "node:test",
        "type": "Node",
        "name": "Test Node",
        "status": "ACTIVE",
        "created": "2026-04-14T00:00:00",
        "updated": "2026-04-14T00:00:00",
    }


# =============================================================================
# create_node tests
# =============================================================================


def test_create_node_writes_file(tmp_path: Path, sample_node, nodes_schema):
    path = create_node(tmp_path, sample_node, nodes_schema, actor="test")
    assert path.exists()
    assert path.name == "node_test.md"


def test_create_node_writes_frontmatter(tmp_path: Path, sample_node, nodes_schema):
    path = create_node(tmp_path, sample_node, nodes_schema, actor="test")
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "id: node:test" in content


def test_create_node_logs_history(tmp_path: Path, sample_node, nodes_schema):
    create_node(tmp_path, sample_node, nodes_schema, actor="tester")
    events = read_events(tmp_path)
    assert len(events) == 1
    assert events[0]["event_type"] == "node.created"
    assert events[0]["actor"] == "tester"
    assert events[0]["payload"]["id"] == "node:test"


def test_create_node_invalid_raises(tmp_path: Path, nodes_schema):
    bad_node = {"id": "node:bad", "type": "Node"}  # missing required fields
    with pytest.raises(ValueError, match="validation failed"):
        create_node(tmp_path, bad_node, nodes_schema)


def test_create_node_duplicate_raises(tmp_path: Path, sample_node, nodes_schema):
    create_node(tmp_path, sample_node, nodes_schema)
    with pytest.raises(FileExistsError):
        create_node(tmp_path, sample_node, nodes_schema)


# =============================================================================
# update_node tests
# =============================================================================


def test_update_node_overwrites(tmp_path: Path, sample_node, nodes_schema):
    create_node(tmp_path, sample_node, nodes_schema)

    updated = dict(sample_node)
    updated["name"] = "Updated Name"
    path = update_node(tmp_path, updated, nodes_schema, actor="editor")

    content = path.read_text(encoding="utf-8")
    assert "Updated Name" in content


def test_update_node_logs_history(tmp_path: Path, sample_node, nodes_schema):
    create_node(tmp_path, sample_node, nodes_schema)
    updated = dict(sample_node)
    updated["name"] = "New"
    update_node(tmp_path, updated, nodes_schema, actor="editor")

    events = read_events(tmp_path)
    update_events = [e for e in events if e["event_type"] == "node.updated"]
    assert len(update_events) == 1
    assert update_events[0]["actor"] == "editor"


def test_update_node_missing_raises(tmp_path: Path, sample_node, nodes_schema):
    with pytest.raises(FileNotFoundError):
        update_node(tmp_path, sample_node, nodes_schema)


# =============================================================================
# delete_node tests
# =============================================================================


def test_delete_node_sets_archived(tmp_path: Path, sample_node, nodes_schema):
    create_node(tmp_path, sample_node, nodes_schema)
    path = delete_node(tmp_path, "node:test", actor="deleter")

    content = path.read_text(encoding="utf-8")
    assert "status: ARCHIVED" in content


def test_delete_node_file_still_exists(tmp_path: Path, sample_node, nodes_schema):
    """Soft delete keeps file on disk."""
    create_node(tmp_path, sample_node, nodes_schema)
    path = delete_node(tmp_path, "node:test")
    assert path.exists()


def test_delete_node_logs_history(tmp_path: Path, sample_node, nodes_schema):
    create_node(tmp_path, sample_node, nodes_schema)
    delete_node(tmp_path, "node:test", actor="deleter")

    events = read_events(tmp_path)
    archived = [e for e in events if e["event_type"] == "node.archived"]
    assert len(archived) == 1


def test_delete_node_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        delete_node(tmp_path, "node:nonexistent")


# =============================================================================
# create_edge tests
# =============================================================================


def test_create_edge_writes_file(tmp_path: Path, edges_schema):
    edge = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    path = create_edge(tmp_path, edge, edges_schema, actor="test")

    assert path.exists()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert len(data) == 1


def test_create_edge_appends_to_existing(tmp_path: Path, edges_schema):
    edge1 = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    edge2 = {"from": "node:b", "to": "node:c", "type": "relates_to"}

    create_edge(tmp_path, edge1, edges_schema)
    create_edge(tmp_path, edge2, edges_schema)

    edge_file = tmp_path / ".gobp" / "edges" / "relations.yaml"
    data = yaml.safe_load(edge_file.read_text(encoding="utf-8"))
    assert len(data) == 2


def test_create_edge_invalid_raises(tmp_path: Path, edges_schema):
    bad_edge = {"from": "node:a", "type": "relates_to"}  # missing 'to'
    with pytest.raises(ValueError, match="validation failed"):
        create_edge(tmp_path, bad_edge, edges_schema)


def test_create_edge_logs_history(tmp_path: Path, edges_schema):
    edge = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    create_edge(tmp_path, edge, edges_schema, actor="creator")

    events = read_events(tmp_path)
    created = [e for e in events if e["event_type"] == "edge.created"]
    assert len(created) == 1
    assert created[0]["actor"] == "creator"


# =============================================================================
# delete_edge tests
# =============================================================================


def test_delete_edge_removes_matching(tmp_path: Path, edges_schema):
    edge1 = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    edge2 = {"from": "node:b", "to": "node:c", "type": "relates_to"}

    create_edge(tmp_path, edge1, edges_schema)
    create_edge(tmp_path, edge2, edges_schema)

    count = delete_edge(tmp_path, "node:a", "node:b", "relates_to")
    assert count == 1

    edge_file = tmp_path / ".gobp" / "edges" / "relations.yaml"
    data = yaml.safe_load(edge_file.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["from"] == "node:b"


def test_delete_edge_missing_returns_zero(tmp_path: Path, edges_schema):
    edge = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    create_edge(tmp_path, edge, edges_schema)

    count = delete_edge(tmp_path, "node:x", "node:y", "relates_to")
    assert count == 0


def test_delete_edge_file_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        delete_edge(tmp_path, "node:a", "node:b", "relates_to")


def test_delete_edge_logs_history(tmp_path: Path, edges_schema):
    edge = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    create_edge(tmp_path, edge, edges_schema)
    delete_edge(tmp_path, "node:a", "node:b", "relates_to", actor="remover")

    events = read_events(tmp_path)
    deleted = [e for e in events if e["event_type"] == "edge.deleted"]
    assert len(deleted) == 1
    assert deleted[0]["actor"] == "remover"
    assert deleted[0]["payload"]["count"] == 1


# =============================================================================
# Atomic write test
# =============================================================================


def test_mutations_are_atomic(tmp_path: Path, sample_node, nodes_schema):
    """Sanity check: no temp files left after successful create."""
    create_node(tmp_path, sample_node, nodes_schema)

    nodes_dir = tmp_path / ".gobp" / "nodes"
    files = list(nodes_dir.iterdir())
    # Only the final file should exist, no .tmp files
    assert all(not f.name.endswith(".tmp") for f in files)
    assert len(files) == 1
