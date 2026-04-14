"""Tests for gobp.core.prune module."""

from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.core.prune import dry_run, run_prune


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


def test_dry_run_empty_graph(tmp_path: Path):
    """dry_run returns empty list on empty graph."""
    root = _make_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    result = dry_run(index)
    assert result == []


def test_dry_run_finds_withdrawn_node(tmp_path: Path):
    """dry_run identifies WITHDRAWN node with no edges."""
    root = _make_root(tmp_path)
    _write_node(root, {
        "id": "dec:d901",
        "type": "Decision",
        "name": "Old decision",
        "topic": "cleanup:old",
        "what": "Withdraw this stale item",
        "why": "No longer needed",
        "status": "WITHDRAWN",
        "locked_at": _now(),
        "locked_by": ["CEO"],
        "session_id": "session:2026-04-14_test",
        "created": _now(),
        "updated": _now(),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = dry_run(index)
    assert len(candidates) == 1
    assert candidates[0]["id"] == "dec:d901"


def test_dry_run_skips_active_node(tmp_path: Path):
    """dry_run skips ACTIVE nodes even with no edges."""
    root = _make_root(tmp_path)
    _write_node(root, {
        "id": "node:active001",
        "type": "Node",
        "name": "Active feature",
        "status": "ACTIVE",
        "created": _now(),
        "updated": _now(),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = dry_run(index)
    assert candidates == []


def test_run_prune_nothing_to_prune(tmp_path: Path):
    """run_prune returns ok with empty lists when nothing prunable."""
    root = _make_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    result = run_prune(index, root)
    assert result["ok"] is True
    assert result["pruned_nodes"] == []
    assert result["pruned_edges"] == []
    assert "Nothing to prune" in result["message"]


def test_run_prune_archives_node_file(tmp_path: Path):
    """run_prune moves node file to archive directory."""
    root = _make_root(tmp_path)
    _write_node(root, {
        "id": "dec:d902",
        "type": "Decision",
        "name": "Stale decision",
        "topic": "cleanup:stale",
        "what": "Archive stale decision",
        "why": "Outdated",
        "status": "WITHDRAWN",
        "locked_at": _now(),
        "locked_by": ["CEO"],
        "session_id": "session:2026-04-14_test",
        "created": _now(),
        "updated": _now(),
    })
    index = GraphIndex.load_from_disk(root)
    result = run_prune(index, root)

    assert result["ok"] is True
    assert "dec:d902" in result["pruned_nodes"]
    # Original file should be gone
    node_file = root / ".gobp" / "nodes" / "dec-d902.md"
    assert not node_file.exists()
    # Archive directory should exist
    assert result["archive_path"] != ""
    archive_dir = Path(result["archive_path"])
    assert archive_dir.exists()


def test_run_prune_logs_history_event(tmp_path: Path):
    """run_prune appends to history log."""
    root = _make_root(tmp_path)
    _write_node(root, {
        "id": "dec:d903",
        "type": "Decision",
        "name": "Stale decision 2",
        "topic": "cleanup:stale2",
        "what": "Archive stale decision 2",
        "why": "Outdated",
        "status": "WITHDRAWN",
        "locked_at": _now(),
        "locked_by": ["CEO"],
        "session_id": "session:2026-04-14_test",
        "created": _now(),
        "updated": _now(),
    })
    index = GraphIndex.load_from_disk(root)
    run_prune(index, root, actor="test-prune")

    from gobp.core.history import read_events
    events = read_events(root)
    prune_events = [e for e in events if e.get("event_type") == "graph.prune"]
    assert len(prune_events) >= 1
    assert prune_events[0]["actor"] == "test-prune"
