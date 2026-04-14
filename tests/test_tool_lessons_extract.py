"""Tests for gobp.mcp.tools.advanced.lessons_extract tool."""

import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.mcp.tools.advanced import lessons_extract


def _make_root(tmp_path: Path) -> Path:
    """Create minimal .gobp/ structure with required schema files."""
    (tmp_path / ".gobp" / "nodes").mkdir(parents=True)
    (tmp_path / ".gobp" / "edges").mkdir(parents=True)
    (tmp_path / ".gobp" / "history").mkdir(parents=True)

    # GraphIndex.load_from_disk requires schema files at <root>/gobp/schema/
    import shutil
    repo_schema = Path(__file__).parent.parent / "gobp" / "schema"
    dest_schema = tmp_path / "gobp" / "schema"
    dest_schema.mkdir(parents=True)
    shutil.copy(repo_schema / "core_nodes.yaml", dest_schema / "core_nodes.yaml")
    shutil.copy(repo_schema / "core_edges.yaml", dest_schema / "core_edges.yaml")

    return tmp_path


def _write_node(root: Path, node: dict) -> None:
    node_id = node["id"].replace(":", "-")
    path = root / ".gobp" / "nodes" / f"{node_id}.md"
    fm = yaml.dump(node, allow_unicode=True, default_flow_style=False)
    path.write_text(f"---\n{fm}---\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(coro):
    return asyncio.run(coro)


def test_lessons_extract_empty_graph(tmp_path: Path):
    """lessons_extract returns ok with empty candidates on empty graph."""
    root = _make_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    result = _run(lessons_extract(index, root, {}))
    assert result["ok"] is True
    assert result["candidates"] == []
    assert result["count"] == 0
    assert "note" in result


def test_lessons_extract_invalid_pattern(tmp_path: Path):
    """lessons_extract returns error for invalid pattern."""
    root = _make_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    result = _run(lessons_extract(index, root, {"patterns": ["P99"]}))
    assert result["ok"] is False
    assert "Invalid pattern" in result["error"]


def test_lessons_extract_default_args(tmp_path: Path):
    """lessons_extract works with no args (all defaults)."""
    root = _make_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    result = _run(lessons_extract(index, root, {}))
    assert result["ok"] is True


def test_lessons_extract_pattern_filter(tmp_path: Path):
    """lessons_extract only returns candidates for requested patterns."""
    root = _make_root(tmp_path)
    _write_node(root, {
        "id": "session:2026-04-14_s001",
        "type": "Session",
        "actor": "test",
        "started_at": _now(),
        "goal": "test",
        "status": "INTERRUPTED",
        "outcome": "interrupted",
        "pending": [],
        "created": _now(),
        "updated": _now(),
    })
    index = GraphIndex.load_from_disk(root)

    # Only request P2, P3, P4 — should not return P1 candidates
    result = _run(lessons_extract(index, root, {"patterns": ["P2", "P3", "P4"]}))
    assert result["ok"] is True
    for c in result["candidates"]:
        assert c["pattern"] != "P1"


def test_lessons_extract_max_candidates_respected(tmp_path: Path):
    """lessons_extract respects max_candidates parameter."""
    root = _make_root(tmp_path)
    for i in range(10):
        _write_node(root, {
            "id": f"session:2026-04-14_s{i:03d}",
            "type": "Session",
            "actor": "test",
            "started_at": _now(),
            "goal": f"goal {i}",
            "status": "INTERRUPTED",
            "outcome": "interrupted",
            "pending": [],
            "created": _now(),
            "updated": _now(),
        })
    index = GraphIndex.load_from_disk(root)
    result = _run(lessons_extract(index, root, {"max_candidates": 3}))
    assert result["ok"] is True
    assert len(result["candidates"]) <= 3


def test_lessons_extract_note_always_present(tmp_path: Path):
    """lessons_extract always includes note reminding about proposals."""
    root = _make_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    result = _run(lessons_extract(index, root, {}))
    assert "note" in result
    assert "node_upsert" in result["note"]
