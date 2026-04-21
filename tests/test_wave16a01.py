"""Tests for Wave 16A01: response modes, get_batch, metadata lint, numeric priority."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex, priority_label
from gobp.core.id_config import DEFAULT_GROUPS, get_tier_weight
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.tools import read as tools_read


@pytest.fixture
def seeded_root(gobp_root: Path) -> Path:
    init_project(gobp_root, force=True)
    return gobp_root


def test_find_mode_summary_has_edge_count(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.find(index, seeded_root, {"query": "", "mode": "summary"})
    assert r["ok"] is True
    assert r["mode"] == "summary"
    for match in r["matches"]:
        assert "edge_count" in match
        assert "detail_available" in match


def test_find_mode_summary_no_heavy_fields(seeded_root: Path) -> None:
    """summary mode should not have description or code_refs."""
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.find(index, seeded_root, {"query": "", "mode": "summary"})
    for match in r["matches"]:
        assert "code_refs" not in match or match.get("code_refs") is None


def test_find_mode_brief_has_extra_fields(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.find(index, seeded_root, {"query": "", "mode": "brief"})
    assert r["mode"] == "brief"
    assert r["ok"] is True


def test_find_default_mode_backward_compat(seeded_root: Path) -> None:
    """Default mode should not break existing behavior."""
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.find(index, seeded_root, {"query": "unit"})
    assert r["ok"] is True
    assert "matches" in r


def test_dispatch_find_mode_summary(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("find: unit mode=summary", index, seeded_root))
    assert r["ok"] is True
    assert r.get("mode") == "summary"


def test_dispatch_find_mode_brief(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("find: unit mode=brief", index, seeded_root))
    assert r["ok"] is True
    assert r.get("mode") == "brief"


def test_find_type_filter_uses_file_index_when_pg_unavailable(
    seeded_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without a v3 connection, type-filtered find lists from the file-backed index."""
    index = GraphIndex.load_from_disk(seeded_root)

    from gobp.mcp.tools import read_v3 as _read_v3

    monkeypatch.setattr(_read_v3, "_conn_v3", lambda _root: (None, False))

    r = tools_read.find(index, seeded_root, {"query": "", "type": "Engine", "mode": "summary"})
    assert r["ok"] is True
    assert r.get("type_filter") == "Engine"
    assert r.get("search_source") == "file_index"
    assert all(m.get("type") == "Engine" for m in r.get("matches", []))


def test_get_batch_fetches_multiple(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    nodes = index.all_nodes()[:3]
    ids = ",".join(n["id"] for n in nodes)
    r = tools_read.get_batch(index, seeded_root, {"ids": ids, "mode": "summary"})
    assert r["ok"] is True
    assert r["found"] == 3
    assert r["not_found"] == []


def test_get_batch_handles_missing_ids(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.get_batch(
        index,
        seeded_root,
        {"ids": "node:real_node,node:nonexistent", "mode": "summary"},
    )
    assert r["ok"] is True
    assert "nonexistent" in str(r["not_found"])


def test_get_batch_max_50(seeded_root: Path) -> None:
    """get_batch respects max 50 limit."""
    index = GraphIndex.load_from_disk(seeded_root)
    ids = ",".join(n["id"] for n in index.all_nodes())
    r = tools_read.get_batch(index, seeded_root, {"ids": ids, "max": 200})
    assert r["found"] <= 50


def test_dispatch_get_batch(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    nodes = index.all_nodes()[:2]
    ids = ",".join(n["id"] for n in nodes)
    r = asyncio.run(dispatch(f"get_batch: ids='{ids}'", index, seeded_root))
    assert r["ok"] is True
    assert r["_dispatch"]["action"] == "get_batch"


def test_dispatch_edit_accepts_node_prefix_id(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    sid = asyncio.run(dispatch("session:start actor='test' goal='edit node prefix'", index, seeded_root))["session_id"]
    index = GraphIndex.load_from_disk(seeded_root)
    create_r = asyncio.run(
        dispatch(f"create:Node name='EditPrefixNode' session_id='{sid}'", index, seeded_root)
    )
    assert create_r.get("ok") is True
    nid = str(create_r.get("node_id", ""))
    assert nid

    index = GraphIndex.load_from_disk(seeded_root)
    edit_r = asyncio.run(
        dispatch(
            f"edit: id='node:{nid}' description='Edited via node prefix id.' session_id='{sid}'",
            index,
            seeded_root,
        )
    )
    assert edit_r.get("ok") is True, edit_r

    index = GraphIndex.load_from_disk(seeded_root)
    node = index.get_node(nid)
    assert node is not None
    assert str(node.get("id", "")) == nid


def test_get_batch_pg_missing_falls_back_to_file_index(
    seeded_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    node_id = index.all_nodes()[0]["id"]

    class _FakeConn:
        def close(self) -> None:
            return None

    from gobp.mcp.tools import read_v3 as _read_v3

    monkeypatch.setattr(_read_v3, "_conn_v3", lambda _root: (_FakeConn(), True))
    monkeypatch.setattr(
        _read_v3,
        "get_batch_v3",
        lambda _conn, ids, _mode, _since: {
            "ok": True,
            "mode": "brief",
            "nodes": {ids[0]: {"ok": False, "error": f"Node not found: {ids[0]}"}},
            "summary": {"total": 1, "unchanged": 0, "fetched": 1},
        },
    )

    r = tools_read.get_batch(index, seeded_root, {"ids": node_id, "mode": "brief"})
    assert r["ok"] is True
    assert r["found"] == 1
    assert r["not_found"] == []
    assert r.get("source") == "hybrid_pg_file"
    assert r.get("mirror_fallback_count") == 1
    assert isinstance(r["nodes"][node_id], dict)
    assert r["nodes"][node_id].get("id") == node_id
    assert r["nodes"][node_id].get("_source") == "file_index_fallback"


def test_metadata_lint_returns_score(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.metadata_lint(index, seeded_root, {})
    assert r["ok"] is True
    assert "score" in r
    assert 0 <= r["score"] <= 100


def test_metadata_lint_returns_by_type(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.metadata_lint(index, seeded_root, {})
    assert "by_type" in r
    assert isinstance(r["by_type"], dict)


def test_dispatch_validate_metadata(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("validate: metadata", index, seeded_root))
    assert r["ok"] is True
    assert "score" in r


def test_dispatch_validate_metadata_type_filter(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("validate: metadata type=TestKind", index, seeded_root))
    assert r["ok"] is True


def test_priority_label_thresholds() -> None:
    assert priority_label(25) == "critical"
    assert priority_label(20) == "critical"
    assert priority_label(19) == "high"
    assert priority_label(10) == "high"
    assert priority_label(9) == "medium"
    assert priority_label(5) == "medium"
    assert priority_label(4) == "low"
    assert priority_label(0) == "low"


def test_tier_weights_defined() -> None:
    assert "Decision" in DEFAULT_GROUPS["core"]["types"]
    assert "Engine" in DEFAULT_GROUPS["ops"]["types"]
    assert get_tier_weight("Invariant") >= get_tier_weight("Feature")
    assert get_tier_weight("Decision") >= get_tier_weight("Document")


def test_compute_priority_score(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    nodes = index.all_nodes()
    if nodes:
        node_id = nodes[0]["id"]
        score = index.compute_priority_score(node_id)
        assert isinstance(score, int)
        assert score >= 0


def test_dispatch_recompute_dry_run(seeded_root: Path) -> None:
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("recompute: priorities dry_run=true", index, seeded_root))
    assert r["ok"] is True
    assert r["dry_run"] is True
    assert "priority_distribution" in r


def test_recompute_no_write_when_dry_run(seeded_root: Path) -> None:
    """dry_run=true should not change any nodes."""
    index = GraphIndex.load_from_disk(seeded_root)
    node_before = dict(index.all_nodes()[0]) if index.all_nodes() else {}

    asyncio.run(dispatch("recompute: priorities dry_run=true", index, seeded_root))

    index2 = GraphIndex.load_from_disk(seeded_root)
    node_after = index2.all_nodes()[0] if index2.all_nodes() else {}
    assert node_after.get("priority_score") == node_before.get("priority_score")
