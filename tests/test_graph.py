"""Tests for GraphIndex class."""

from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex


@pytest.fixture
def empty_gobp_root(tmp_path: Path) -> Path:
    """Create minimal GoBP root with schemas but no data."""
    # Copy actual schemas
    import gobp

    actual_schema_dir = Path(gobp.__file__).parent / "schema"

    # Create structure
    pkg_dir = tmp_path / "gobp"
    schema_dir = pkg_dir / "schema"
    schema_dir.mkdir(parents=True)

    # Copy schemas
    (schema_dir / "core_nodes.yaml").write_text(
        (actual_schema_dir / "core_nodes.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (schema_dir / "core_edges.yaml").write_text(
        (actual_schema_dir / "core_edges.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def populated_gobp_root(empty_gobp_root: Path) -> Path:
    """Create GoBP root with sample nodes and edges."""
    data_dir = empty_gobp_root / ".gobp"
    nodes_dir = data_dir / "nodes"
    edges_dir = data_dir / "edges"
    nodes_dir.mkdir(parents=True)
    edges_dir.mkdir(parents=True)

    # Create 2 nodes
    (nodes_dir / "node1.md").write_text(
        """---
id: node:first
type: Node
name: First
status: ACTIVE
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
---

Body.
""",
        encoding="utf-8",
    )

    (nodes_dir / "node2.md").write_text(
        """---
id: node:second
type: Node
name: Second
status: ACTIVE
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
---

Body.
""",
        encoding="utf-8",
    )

    # Create edges
    (edges_dir / "rels.yaml").write_text(
        """- from: node:first
  to: node:second
  type: relates_to
""",
        encoding="utf-8",
    )

    return empty_gobp_root


def test_empty_index_has_zero_len():
    index = GraphIndex()
    assert len(index) == 0
    assert index.all_nodes() == []
    assert index.all_edges() == []


def test_load_empty_gobp_root(empty_gobp_root: Path):
    """Loading a root with schemas but no data yields empty index."""
    index = GraphIndex.load_from_disk(empty_gobp_root)
    assert len(index) == 0
    assert index.load_errors == []


def test_load_populated_gobp_root(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    assert len(index) == 2
    assert index.load_errors == []


def test_get_node(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)

    node = index.get_node("node:first")
    assert node is not None
    assert node["name"] == "First"

    missing = index.get_node("node:nonexistent")
    assert missing is None


def test_all_nodes(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    nodes = index.all_nodes()
    assert len(nodes) == 2
    names = {n["name"] for n in nodes}
    assert names == {"First", "Second"}


def test_all_edges(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    edges = index.all_edges()
    assert len(edges) == 1
    assert edges[0]["type"] == "relates_to"


def test_nodes_by_type(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    nodes = index.nodes_by_type("Node")
    assert len(nodes) == 2

    ideas = index.nodes_by_type("Idea")
    assert ideas == []


def test_get_edges_from(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    edges = index.get_edges_from("node:first")
    assert len(edges) == 1
    assert edges[0]["to"] == "node:second"

    none_edges = index.get_edges_from("node:nonexistent")
    assert none_edges == []


def test_get_edges_to(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    edges = index.get_edges_to("node:second")
    assert len(edges) == 1
    assert edges[0]["from"] == "node:first"


def test_get_edges_by_type(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    edges = index.get_edges_by_type("relates_to")
    assert len(edges) == 1

    none = index.get_edges_by_type("implements")
    assert none == []


def test_load_errors_collected_not_raised(empty_gobp_root: Path):
    """Bad node files should add to load_errors, not crash."""
    nodes_dir = empty_gobp_root / ".gobp" / "nodes"
    nodes_dir.mkdir(parents=True)

    # Invalid node file (missing frontmatter)
    (nodes_dir / "bad.md").write_text("Just text, no frontmatter", encoding="utf-8")

    index = GraphIndex.load_from_disk(empty_gobp_root)
    assert len(index) == 0
    assert len(index.load_errors) > 0
    assert "bad.md" in index.load_errors[0]
