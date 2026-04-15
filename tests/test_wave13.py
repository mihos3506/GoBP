"""Tests for Wave 13: pagination, upsert, guardrails, observability."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.tools import read as tools_read


def test_find_returns_page_info(gobp_root: Path) -> None:
    """find() returns page_info with pagination fields."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "unit", "page_size": 5})
    assert result["ok"] is True
    assert "page_info" in result
    pi = result["page_info"]
    assert "next_cursor" in pi
    assert "has_more" in pi
    assert "total_estimate" in pi
    assert "page_size" in pi


def test_find_page_size_limit(gobp_root: Path) -> None:
    """find() page_size capped at 100."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "", "page_size": 999})
    assert result["page_info"]["page_size"] <= 100


def test_find_cursor_pagination(gobp_root: Path) -> None:
    """find() cursor returns next page."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    r1 = tools_read.find(index, gobp_root, {"query": "", "page_size": 5})
    assert r1["ok"] is True

    if not r1["page_info"]["has_more"]:
        pytest.skip("Not enough nodes to test pagination")

    cursor = r1["page_info"]["next_cursor"]
    assert cursor is not None

    r2 = tools_read.find(index, gobp_root, {"query": "", "page_size": 5, "cursor": cursor})
    assert r2["ok"] is True
    ids1 = {m["id"] for m in r1["matches"]}
    ids2 = {m["id"] for m in r2["matches"]}
    assert ids1.isdisjoint(ids2), "Pages should not overlap"


def test_find_backward_compat_matches_key(gobp_root: Path) -> None:
    """find() still returns matches key (backward compatible)."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "unit"})
    assert "matches" in result


def test_related_returns_page_info(gobp_root: Path) -> None:
    """node_related() returns page_info."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = tools_read.node_related(index, gobp_root, {"node_id": node_id})
    assert result["ok"] is True
    assert "page_info" in result


def test_tests_returns_page_info(gobp_root: Path) -> None:
    """node_tests() returns page_info."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = tools_read.node_tests(index, gobp_root, {"node_id": node_id})
    assert result["ok"] is True
    assert "page_info" in result


def test_node_upsert_returns_action_field(gobp_root: Path) -> None:
    """node_upsert() returns action: created/updated/skipped."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch("session:start actor='test' goal='guardrails test'", index, gobp_root))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(
        dispatch(f"create:Node name='Test Node' session_id='{session_id}'", index, gobp_root)
    )
    assert result["ok"] is True
    assert "action" in result
    assert result["action"] in ("created", "updated", "skipped")


def test_node_upsert_returns_changed_fields(gobp_root: Path) -> None:
    """node_upsert() returns changed_fields list."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch("session:start actor='test' goal='changed fields test'", index, gobp_root))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(
        dispatch(
            f"create:Node name='Changed Fields Test' session_id='{session_id}'",
            index,
            gobp_root,
        )
    )
    assert result["ok"] is True
    assert "changed_fields" in result
    assert isinstance(result["changed_fields"], list)


def test_dry_run_no_write(gobp_root: Path) -> None:
    """dry_run=true returns preview without writing."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch("session:start actor='test' goal='dry run test'", index, gobp_root))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    before_count = len(index.all_nodes())

    result = asyncio.run(
        dispatch(
            f"create:Node name='Dry Run Node' session_id='{session_id}' dry_run=true",
            index,
            gobp_root,
        )
    )
    assert result["ok"] is True
    assert result.get("dry_run") is True
    assert "would_action" in result

    index2 = GraphIndex.load_from_disk(gobp_root)
    assert len(index2.all_nodes()) == before_count


def test_upsert_creates_if_not_exists(gobp_root: Path) -> None:
    """upsert: creates node if dedupe_key not found."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch("session:start actor='test' goal='upsert test'", index, gobp_root))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(
        dispatch(
            f"upsert:Node dedupe_key='name' name='Unique Feature' session_id='{session_id}'",
            index,
            gobp_root,
        )
    )
    assert result["ok"] is True
    assert result.get("action") == "created"


def test_upsert_updates_if_exists(gobp_root: Path) -> None:
    """upsert: updates node if dedupe_key matches existing."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch("session:start actor='test' goal='upsert update test'", index, gobp_root))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    r1 = asyncio.run(
        dispatch(
            f"upsert:Node dedupe_key='name' name='Dedup Node' session_id='{session_id}'",
            index,
            gobp_root,
        )
    )
    assert r1["action"] == "created"
    node_id = r1["node_id"]

    index = GraphIndex.load_from_disk(gobp_root)

    r2 = asyncio.run(
        dispatch(
            f"upsert:Node dedupe_key='name' name='Dedup Node' priority='critical' session_id='{session_id}'",
            index,
            gobp_root,
        )
    )
    assert r2["ok"] is True
    assert r2.get("action") == "updated"
    assert r2["node_id"] == node_id


def test_upsert_dry_run(gobp_root: Path) -> None:
    """upsert: with dry_run=true returns preview."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch("session:start actor='test' goal='upsert dry run'", index, gobp_root))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(
        dispatch(
            f"upsert:Node dedupe_key='name' name='Dry Node' session_id='{session_id}' dry_run=true",
            index,
            gobp_root,
        )
    )
    assert result["ok"] is True
    assert result.get("dry_run") is True
    assert "would_action" in result


def test_protocol_guide_has_stats() -> None:
    from gobp.mcp.dispatcher import PROTOCOL_GUIDE

    actions = PROTOCOL_GUIDE["actions"]
    assert any("stats:" in k for k in actions)


def test_protocol_guide_has_upsert() -> None:
    from gobp.mcp.dispatcher import PROTOCOL_GUIDE

    actions = PROTOCOL_GUIDE["actions"]
    assert any("upsert:" in k for k in actions)
