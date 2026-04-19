"""Tests for Wave 16A06: delete: and retype: actions."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    init_project(tmp_path)
    return tmp_path


def _start_session(root: Path) -> str:
    index = GraphIndex.load_from_disk(root)
    r = asyncio.run(dispatch("session:start actor='test' goal='test'", index, root))
    return r["session_id"]


# ── delete: tests ─────────────────────────────────────────────────────────────


def test_delete_node(tmp_project: Path) -> None:
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)
    r = asyncio.run(dispatch(f"create:Node name='Temp Node' session_id='{sid}'", index, tmp_project))
    node_id = r["node_id"]

    index = GraphIndex.load_from_disk(tmp_project)
    r2 = asyncio.run(dispatch(f"delete: {node_id} session_id='{sid}'", index, tmp_project))
    assert r2["ok"] is True
    assert r2["deleted_node_id"] == node_id

    index = GraphIndex.load_from_disk(tmp_project)
    assert index.get_node(node_id) is None


def test_delete_removes_edges(tmp_project: Path) -> None:
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)

    r1 = asyncio.run(dispatch(f"create:Node name='NodeA' session_id='{sid}'", index, tmp_project))
    index = GraphIndex.load_from_disk(tmp_project)
    r2 = asyncio.run(dispatch(f"create:Node name='NodeB' session_id='{sid}'", index, tmp_project))
    id_a, id_b = r1["node_id"], r2["node_id"]

    index = GraphIndex.load_from_disk(tmp_project)
    asyncio.run(dispatch(f"edge: {id_a} --relates_to--> {id_b}", index, tmp_project))

    index = GraphIndex.load_from_disk(tmp_project)
    asyncio.run(dispatch(f"delete: {id_a} session_id='{sid}'", index, tmp_project))

    index = GraphIndex.load_from_disk(tmp_project)
    edges_dir = tmp_project / ".gobp" / "edges"
    remaining_edges = []
    if edges_dir.exists():
        for f in edges_dir.glob("*.yaml"):
            e = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(e, list):
                for edge in e:
                    if edge and (edge.get("from") == id_a or edge.get("to") == id_a):
                        remaining_edges.append(edge)
    assert len(remaining_edges) == 0


def test_delete_protected_session(tmp_project: Path) -> None:
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)
    r = asyncio.run(dispatch(f"delete: {sid} session_id='{sid}'", index, tmp_project))
    assert r["ok"] is False
    assert "protected" in r["error"].lower() or "cannot" in r["error"].lower()


def test_delete_not_found(tmp_project: Path) -> None:
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)
    r = asyncio.run(
        dispatch(
            f"delete: nonexistent.meta.00000099 session_id='{sid}'",
            index,
            tmp_project,
        )
    )
    assert r["ok"] is False


# ── retype: tests ─────────────────────────────────────────────────────────────


def test_retype_node_changes_group(tmp_project: Path) -> None:
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)
    r = asyncio.run(dispatch(f"create:Node name='TrustGate' session_id='{sid}'", index, tmp_project))
    old_id = r["node_id"]
    assert ".meta." in old_id

    index = GraphIndex.load_from_disk(tmp_project)
    r2 = asyncio.run(
        dispatch(f"retype: id='{old_id}' new_type=Engine session_id='{sid}'", index, tmp_project)
    )
    assert r2["ok"] is True
    new_id = r2["new_id"]
    # v2 ids use group.name.hex; legacy tests expected slug.ops.digits
    assert old_id != new_id
    assert "." in new_id


def test_retype_old_node_deleted(tmp_project: Path) -> None:
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)
    r = asyncio.run(dispatch(f"create:Node name='OldNode' session_id='{sid}'", index, tmp_project))
    old_id = r["node_id"]

    index = GraphIndex.load_from_disk(tmp_project)
    asyncio.run(dispatch(f"retype: id='{old_id}' new_type=Flow session_id='{sid}'", index, tmp_project))

    index = GraphIndex.load_from_disk(tmp_project)
    assert index.get_node(old_id) is None


def test_retype_preserves_name(tmp_project: Path) -> None:
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)
    r = asyncio.run(
        dispatch(f"create:Node name='Verify Gate Flow' session_id='{sid}'", index, tmp_project)
    )
    old_id = r["node_id"]

    index = GraphIndex.load_from_disk(tmp_project)
    r2 = asyncio.run(
        dispatch(f"retype: id='{old_id}' new_type=Flow session_id='{sid}'", index, tmp_project)
    )
    new_id = r2["new_id"]

    index = GraphIndex.load_from_disk(tmp_project)
    new_node = index.get_node(new_id)
    assert new_node is not None
    assert new_node.get("name") == "Verify Gate Flow"


def test_retype_migrates_edges(tmp_project: Path) -> None:
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)

    r1 = asyncio.run(dispatch(f"create:Node name='NodeA' session_id='{sid}'", index, tmp_project))
    index = GraphIndex.load_from_disk(tmp_project)
    r2 = asyncio.run(dispatch(f"create:Entity name='EntityB' session_id='{sid}'", index, tmp_project))
    id_a, id_b = r1["node_id"], r2["node_id"]

    index = GraphIndex.load_from_disk(tmp_project)
    asyncio.run(dispatch(f"edge: {id_a} --relates_to--> {id_b}", index, tmp_project))

    index = GraphIndex.load_from_disk(tmp_project)
    r3 = asyncio.run(dispatch(f"retype: id='{id_a}' new_type=Flow session_id='{sid}'", index, tmp_project))
    new_id = r3["new_id"]
    assert r3["edges_migrated"] >= 1

    index = GraphIndex.load_from_disk(tmp_project)
    edges_dir = tmp_project / ".gobp" / "edges"
    found = False
    if edges_dir.exists():
        for f in edges_dir.glob("*.yaml"):
            e = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(e, list):
                for edge in e:
                    if edge and (edge.get("from") == new_id or edge.get("to") == new_id):
                        found = True
    assert found


def test_protocol_guide_has_delete_retype() -> None:
    from gobp.mcp.parser import PROTOCOL_GUIDE

    actions = PROTOCOL_GUIDE.get("actions", {})
    assert any("delete:" in k for k in actions)
    assert any("retype:" in k for k in actions)
