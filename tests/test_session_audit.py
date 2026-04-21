"""Tests for :mod:`gobp.mcp.session_audit`."""

from __future__ import annotations

from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.mcp.session_audit import resolve_write_session, session_id_is_graph_session


@pytest.fixture
def tiny_root(tmp_path: Path) -> Path:
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
    data_dir = tmp_path / ".gobp"
    (data_dir / "nodes").mkdir(parents=True)
    (data_dir / "edges").mkdir(parents=True)
    return tmp_path


def test_resolve_opaque_id_without_node(tiny_root: Path) -> None:
    index = GraphIndex.load_from_disk(tiny_root)
    rid, node, err, auto = resolve_write_session(index, "audit:custom1")
    assert err is None
    assert node is None
    assert rid == "audit:custom1"
    assert auto is False
    assert not session_id_is_graph_session(index, rid)


def test_resolve_graph_session_node(tiny_root: Path) -> None:
    (tiny_root / ".gobp" / "nodes" / "s.md").write_text(
        """---
id: meta.session.2026-01-01.abc12345
type: Session
name: Test
actor: a
started_at: 2026-01-01T00:00:00+00:00
goal: g
status: IN_PROGRESS
created: 2026-01-01T00:00:00+00:00
updated: 2026-01-01T00:00:00+00:00
---
x
""",
        encoding="utf-8",
    )
    index = GraphIndex.load_from_disk(tiny_root)
    rid, node, err, auto = resolve_write_session(index, "meta.session.2026-01-01.abc12345")
    assert err is None
    assert node is not None
    assert node.get("type") == "Session"
    assert auto is False
    assert session_id_is_graph_session(index, rid)
