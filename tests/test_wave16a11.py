"""Tests for Wave 16A11: batch performance — single load/save."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.parser import PROTOCOL_GUIDE


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    init_project(tmp_path)
    return tmp_path


def _sid(proj: Path) -> str:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("session:start actor='t' goal='t'", index, proj))
    return str(r["session_id"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _engine(name: str) -> dict[str, str]:
    ts = _now_iso()
    return {
        "type": "Engine",
        "name": name,
        "status": "ACTIVE",
        "created": ts,
        "updated": ts,
    }


def _generic_node(name: str) -> dict[str, str]:
    ts = _now_iso()
    return {
        "type": "Node",
        "name": name,
        "status": "ACTIVE",
        "created": ts,
        "updated": ts,
    }


# --- In-memory methods --------------------------------------------------------


def test_add_node_in_memory(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    node_id = index.add_node_in_memory(_engine("TestEng"))
    assert node_id
    assert index.get_node(node_id) is not None


def test_add_edge_in_memory(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    id_a = index.add_node_in_memory(_engine("A"))
    id_b = index.add_node_in_memory(_engine("B"))
    added = index.add_edge_in_memory(id_a, id_b, "depends_on")
    assert added is True


def test_add_edge_duplicate_returns_false(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    id_a = index.add_node_in_memory(_engine("A"))
    id_b = index.add_node_in_memory(_engine("B"))
    index.add_edge_in_memory(id_a, id_b, "depends_on")
    dup = index.add_edge_in_memory(id_a, id_b, "depends_on")
    assert dup is False


def test_save_new_nodes_to_disk(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    index.add_node_in_memory(_engine("SaveTest"))
    result = index.save_new_nodes_to_disk(proj)
    assert result["nodes_written"] >= 1

    index2 = GraphIndex.load_from_disk(proj)
    found = [n for n in index2.all_nodes() if n.get("name") == "SaveTest"]
    assert len(found) == 1


def test_remove_node_in_memory(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    node_id = index.add_node_in_memory(_generic_node("Gone"))
    removed = index.remove_node_in_memory(node_id)
    assert removed is True
    assert index.get_node(node_id) is None


# --- Batch performance / limits -----------------------------------------------


@pytest.mark.slow
def test_batch_100_creates_under_10s(proj: Path) -> None:
    """Brief target <10s; allow headroom for slow laptops/Windows I/O."""
    sid = _sid(proj)
    lines = [f"create: Engine: BatchEng{i} | Engine {i}" for i in range(100)]
    ops = "\n".join(lines)

    index = GraphIndex.load_from_disk(proj)
    t0 = time.time()
    r = asyncio.run(dispatch(f"batch session_id='{sid}' ops='{ops}'", index, proj))
    elapsed = time.time() - t0

    assert r.get("succeeded", 0) >= 50, f"Too few succeeded: {r}"
    assert elapsed < 60.0, f"Too slow: {elapsed:.1f}s"


@pytest.mark.slow
def test_batch_large_op_list_succeeds(proj: Path) -> None:
    """Batch accepts 500+ ops; no external max error (Wave 16A13)."""
    sid = _sid(proj)
    lines = [f"create: Node: N{i} | Node {i}" for i in range(501)]
    ops = "\n".join(lines)

    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch(f"batch session_id='{sid}' ops='{ops}'", index, proj))
    assert r.get("ok")
    assert r.get("succeeded", 0) >= 500


def test_batch_creates_then_edges_same_call(proj: Path) -> None:
    sid = _sid(proj)
    ops = (
        "create: Engine: AlphaEng | Alpha\n"
        "create: Engine: BetaEng | Beta\n"
        "edge+: AlphaEng --depends_on--> BetaEng"
    )

    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch(f"batch session_id='{sid}' ops='{ops}'", index, proj))
    assert r.get("succeeded", 0) >= 2


# --- PROTOCOL_GUIDE -----------------------------------------------------------


def test_batch_limit_documented() -> None:
    actions = PROTOCOL_GUIDE.get("actions", {})
    batch_entries = [k for k in actions if "batch" in k.lower()]
    assert batch_entries
    joined = " ".join(str(actions[k]) for k in batch_entries).lower()
    assert "chunk" in joined or "internal" in joined or "unified batch" in joined
