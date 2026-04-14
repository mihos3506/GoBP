"""Tests for GoBP MCP validate tool."""

from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import maintain as tools_maintain


@pytest.fixture
def clean_root(tmp_path: Path) -> Path:
    """GoBP root with only schemas, no data."""
    import gobp

    actual_schema_dir = Path(gobp.__file__).parent / "schema"

    pkg_dir = tmp_path / "gobp"
    schema_dir = pkg_dir / "schema"
    schema_dir.mkdir(parents=True)
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
def root_with_orphan_edge(clean_root: Path) -> Path:
    """GoBP root with an edge pointing to a non-existent node."""
    data_dir = clean_root / ".gobp"
    (data_dir / "nodes").mkdir(parents=True)
    (data_dir / "edges").mkdir(parents=True)

    # Create one valid node
    (data_dir / "nodes" / "node_a.md").write_text(
        """---
id: node:a
type: Node
name: Node A
status: ACTIVE
created: 2026-04-14T00:00:00+00:00
updated: 2026-04-14T00:00:00+00:00
---

Body.
""",
        encoding="utf-8",
    )

    # Create an edge pointing to a non-existent node
    (data_dir / "edges" / "relations.yaml").write_text(
        """- from: node:a
  to: node:nonexistent
  type: relates_to
""",
        encoding="utf-8",
    )

    return clean_root


def _load(root: Path) -> GraphIndex:
    return GraphIndex.load_from_disk(root)


def test_validate_clean_graph(clean_root):
    index = _load(clean_root)
    result = tools_maintain.validate(index, clean_root, {})
    assert result["ok"] is True
    assert result["count"]["hard"] == 0


def test_validate_detects_orphan_edge(root_with_orphan_edge):
    index = _load(root_with_orphan_edge)
    result = tools_maintain.validate(index, root_with_orphan_edge, {})
    assert result["ok"] is False
    assert result["count"]["hard"] >= 1
    assert any("nonexistent" in issue["message"] for issue in result["issues"])


def test_validate_scope_nodes_only(root_with_orphan_edge):
    index = _load(root_with_orphan_edge)
    result = tools_maintain.validate(
        index, root_with_orphan_edge, {"scope": "nodes"}
    )
    # Orphan edge should not be detected in nodes-only scope
    nonexistent_found = any(
        "nonexistent" in issue.get("message", "")
        for issue in result["issues"]
    )
    assert not nonexistent_found


def test_validate_severity_filter_hard(root_with_orphan_edge):
    index = _load(root_with_orphan_edge)
    result = tools_maintain.validate(
        index, root_with_orphan_edge, {"severity_filter": "hard"}
    )
    for issue in result["issues"]:
        assert issue["severity"] == "hard"


def test_validate_invalid_scope(clean_root):
    index = _load(clean_root)
    result = tools_maintain.validate(index, clean_root, {"scope": "invalid"})
    assert result["ok"] is False
    assert "scope" in result["error"]


def test_validate_invalid_severity(clean_root):
    index = _load(clean_root)
    result = tools_maintain.validate(index, clean_root, {"severity_filter": "invalid"})
    assert result["ok"] is False
