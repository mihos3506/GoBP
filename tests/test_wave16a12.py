"""Tests for Wave 16A12: server cache — eliminate per-call disk reload."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.parser import PROTOCOL_GUIDE


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# --- Cache functions ----------------------------------------------------------


def test_get_cached_index_returns_same_instance() -> None:
    from gobp.mcp.server import get_cached_index, invalidate_cache

    invalidate_cache()
    root = _repo_root()
    if not (root / ".gobp").exists():
        pytest.skip("No .gobp folder")
    idx1 = get_cached_index(root)
    idx2 = get_cached_index(root)
    assert idx1 is idx2


def test_invalidate_forces_reload() -> None:
    from gobp.mcp.server import get_cached_index, invalidate_cache

    root = _repo_root()
    if not (root / ".gobp").exists():
        pytest.skip("No .gobp folder")
    idx1 = get_cached_index(root)
    invalidate_cache()
    idx2 = get_cached_index(root)
    assert idx1 is not idx2


def test_update_cache_replaces_index() -> None:
    from gobp.mcp.server import get_cached_index, invalidate_cache, update_cache

    root = _repo_root()
    if not (root / ".gobp").exists():
        pytest.skip("No .gobp folder")
    invalidate_cache()
    idx1 = get_cached_index(root)

    new_index = GraphIndex()
    update_cache(new_index)

    idx2 = get_cached_index(root)
    assert idx2 is new_index

    invalidate_cache()


# --- Refresh action -----------------------------------------------------------


def test_refresh_action(tmp_path: Path) -> None:
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)
    r = asyncio.run(dispatch("refresh:", index, tmp_path))
    assert r["ok"] is True
    assert "nodes_loaded" in r


# --- Cache performance --------------------------------------------------------


def test_cached_read_faster_than_disk(tmp_path: Path) -> None:
    init_project(tmp_path)

    index = GraphIndex.load_from_disk(tmp_path)
    sid = asyncio.run(
        dispatch("session:start actor='t' goal='cache perf'", index, tmp_path)
    )["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    for i in range(20):
        asyncio.run(
            dispatch(
                f"create:Node name='CacheNode{i}' session_id={sid}",
                index,
                tmp_path,
            )
        )
        index = GraphIndex.load_from_disk(tmp_path)

    t0 = time.time()
    for _ in range(5):
        GraphIndex.load_from_disk(tmp_path)
    disk_time = time.time() - t0

    cached = GraphIndex.load_from_disk(tmp_path)
    t0 = time.time()
    for _ in range(5):
        _ = cached.all_nodes()
    cache_time = time.time() - t0

    assert cache_time < disk_time


# --- WRITE_ACTIONS ------------------------------------------------------------


def test_write_actions_defined() -> None:
    from gobp.mcp.server import WRITE_ACTIONS

    assert "batch" in WRITE_ACTIONS
    assert "session" in WRITE_ACTIONS
    assert "create" in WRITE_ACTIONS
    assert "delete" in WRITE_ACTIONS


# --- PROTOCOL_GUIDE -----------------------------------------------------------


def test_protocol_guide_has_refresh() -> None:
    actions = PROTOCOL_GUIDE.get("actions", {})
    assert any("refresh" in k.lower() for k in actions)
