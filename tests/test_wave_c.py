"""Wave C — viewer write path v3, batch ``edit:``, cache invalidation (no live DB)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gobp.core.cache import GoBPCache, reset_cache
from gobp.core.db import (
    append_history_v3,
    delete_edge_v3,
    delete_node_v3,
    get_node_updated_at,
    upsert_edge_v3,
    upsert_node_v3,
)
from gobp.core.file_format_v3 import deserialize_node, node_file_path, serialize_node
from gobp.core.mutator_v3 import delete_node, edit_node, write_node
from gobp.core.graph import GraphIndex
from gobp.mcp.batch_parser import coerce_to_edit_op, parse_batch_line
from gobp.mcp.dispatcher import dispatch


def _minimal_node(**extra: object) -> dict:
    base = {
        "id": "dev.test.wavec.aaaaaaaa",
        "name": "WaveCNode",
        "group": "Dev > Test",
        "description": "A valid description for schema v3 validation rules.",
    }
    base.update(extra)
    return base


# -- db.py (mocked PostgreSQL) -------------------------------------------------


def test_upsert_node_v3_insert_sql() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    node = _minimal_node()
    upsert_node_v3(conn, node)
    cur.execute.assert_called_once()
    sql = cur.execute.call_args[0][0]
    assert "INSERT INTO nodes" in sql
    assert "ON CONFLICT" in sql
    conn.commit.assert_called_once()


def test_delete_node_v3() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    delete_node_v3(conn, "n1")
    cur.execute.assert_called_once()
    assert "DELETE FROM nodes" in cur.execute.call_args[0][0]
    conn.commit.assert_called_once()


def test_upsert_edge_v3_no_type_column() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    upsert_edge_v3(conn, "a", "b", "why", "c1")
    sql = cur.execute.call_args[0][0]
    assert "edges" in sql
    assert "type" not in sql.lower() or "reason" in sql.lower()
    conn.commit.assert_called_once()


def test_get_node_updated_at_found_and_missing() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchone.return_value = (1700000000,)
    assert get_node_updated_at(conn, "x") == 1700000000
    cur.fetchone.return_value = None
    assert get_node_updated_at(conn, "missing") is None


def test_append_history_v3() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    append_history_v3(conn, "nid", "desc", "c0")
    assert "node_history" in cur.execute.call_args[0][0]
    conn.commit.assert_called_once()


def test_delete_edge_v3() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    delete_edge_v3(conn, "a", "b")
    assert "DELETE FROM edges" in cur.execute.call_args[0][0]
    conn.commit.assert_called_once()


# -- mutator v3 ----------------------------------------------------------------


def test_write_node_happy_path_file(tmp_path: Path) -> None:
    gobp_dir = tmp_path / ".gobp"
    node = _minimal_node()
    r = write_node(node, gobp_dir, conn=None, session_id="s1")
    assert r["ok"] is True
    fp = node_file_path(gobp_dir, node["id"])
    assert fp.is_file()
    loaded = deserialize_node(fp.read_text(encoding="utf-8"))
    assert loaded.get("name") == "WaveCNode"


def test_write_node_invalid_returns_errors(tmp_path: Path) -> None:
    gobp_dir = tmp_path / ".gobp"
    bad = {"name": "", "group": "Dev > Test", "description": "x"}
    r = write_node(bad, gobp_dir, conn=None, session_id="s1")
    assert r["ok"] is False
    assert "errors" in r


def test_write_node_conflict_warning(tmp_path: Path) -> None:
    gobp_dir = tmp_path / ".gobp"
    node = _minimal_node()
    conn = MagicMock()
    with patch("gobp.core.mutator_v3.get_node_updated_at", return_value=999):
        r = write_node(
            node,
            gobp_dir,
            conn=conn,
            session_id="s1",
            expected_updated_at=1,
        )
    assert r.get("conflict_warning", {}).get("conflict") is True


def test_write_node_expected_match_no_warning(tmp_path: Path) -> None:
    gobp_dir = tmp_path / ".gobp"
    node = _minimal_node()
    conn = MagicMock()
    with patch("gobp.core.mutator_v3.get_node_updated_at", return_value=42):
        r = write_node(
            node,
            gobp_dir,
            conn=conn,
            session_id="s1",
            expected_updated_at=42,
        )
    assert r.get("conflict_warning") is None


def test_edit_node_description_same_id(tmp_path: Path) -> None:
    gobp_dir = tmp_path / ".gobp"
    node = _minimal_node()
    write_node(node, gobp_dir, conn=None, session_id="s1")
    nid = node["id"]
    r = edit_node(
        nid,
        {"description": "Updated description text for the same node id."},
        gobp_dir,
        conn=None,
        session_id="s1",
    )
    assert r["ok"] is True
    assert r["id"] == nid


def test_edit_node_group_change_new_id(tmp_path: Path) -> None:
    gobp_dir = tmp_path / ".gobp"
    node = _minimal_node()
    write_node(node, gobp_dir, conn=None, session_id="s1")
    old_id = node["id"]
    old_fp = node_file_path(gobp_dir, old_id)
    r = edit_node(
        old_id,
        {"group": "Meta > Wave"},
        gobp_dir,
        conn=None,
        session_id="s1",
    )
    assert r["ok"] is True
    new_id = str(r["id"])
    assert new_id != old_id
    assert not old_fp.exists()
    assert node_file_path(gobp_dir, new_id).is_file()


def test_edit_node_history_inherited_on_group_change(tmp_path: Path) -> None:
    gobp_dir = tmp_path / ".gobp"
    node = _minimal_node(
        history=[{"description": "first", "code": ""}],
    )
    write_node(node, gobp_dir, conn=None, session_id="s1")
    old_id = node["id"]
    r = edit_node(
        old_id,
        {
            "group": "Meta > Wave",
            "history": [{"description": "second", "code": ""}],
        },
        gobp_dir,
        conn=None,
        session_id="s1",
    )
    assert r["ok"] is True
    loaded = deserialize_node(
        node_file_path(gobp_dir, str(r["id"])).read_text(encoding="utf-8")
    )
    assert len(loaded.get("history", [])) >= 2


def test_delete_node_archives(tmp_path: Path) -> None:
    gobp_dir = tmp_path / ".gobp"
    node = _minimal_node()
    write_node(node, gobp_dir, conn=None, session_id="s1")
    nid = node["id"]
    r = delete_node(nid, gobp_dir, conn=None, session_id="s1")
    assert r["ok"] is True
    assert not node_file_path(gobp_dir, nid).exists()
    arch = gobp_dir / "archive"
    assert arch.is_dir()
    assert any(arch.iterdir())


# -- batch parser --------------------------------------------------------------


def test_parse_edit_op() -> None:
    p = parse_batch_line(
        'edit: id="n1" description="hello"',
    )
    assert p["kind"] == "edit"
    assert p["node_id"] == "n1"
    assert p["changes"]["description"] == "hello"


def test_parse_edit_type_change() -> None:
    p = parse_batch_line('edit: id=n1 type=Engine')
    assert p["changes"]["type"] == "Engine"


def test_parse_edit_edge_ops() -> None:
    p = parse_batch_line('edit: id=a add_edge=b reason=r')
    assert p["changes"]["add_edge"] == "b"
    assert p["changes"]["reason"] == "r"
    p2 = parse_batch_line("edit: id=a remove_edge=b")
    assert p2["changes"]["remove_edge"] == "b"


def test_edit_missing_id_error() -> None:
    p = parse_batch_line("edit: description=only")
    assert p["kind"] == "error"


def test_coerce_update_to_edit() -> None:
    u = parse_batch_line("update: dev.x name=x description=y")
    assert u["kind"] == "update"
    e = coerce_to_edit_op(u)
    assert e["kind"] == "edit"
    assert e["changes"]["description"] == "y"


def test_coerce_retype_to_edit() -> None:
    r = parse_batch_line("retype: dev.old.12345678 new_type=Engine")
    e = coerce_to_edit_op(r)
    assert e["kind"] == "edit"
    assert e["changes"]["type"] == "Engine"


# -- cache ---------------------------------------------------------------------


def test_cache_invalidate_node_and_edge() -> None:
    reset_cache()
    c = GoBPCache(max_size=50, default_ttl=60.0)
    c.set("ctx:node:a:overview", "1")
    c.set("ctx:node:b:overview", "2")
    c.set("other", "3")
    c.invalidate_node("a")
    assert c.get("ctx:node:a:overview") is None
    assert c.get("ctx:node:b:overview") is not None
    c.invalidate_edge("b", "x")
    assert c.get("ctx:node:b:overview") is None
    assert c.get("other") == "3"


# -- dispatcher edit: (file-backed, no PostgreSQL) -----------------------------


def test_dispatch_edit_requires_session(tmp_path: Path) -> None:
    root = tmp_path
    gobp_dir = root / ".gobp"
    (gobp_dir / "nodes").mkdir(parents=True)
    node = _minimal_node()
    (gobp_dir / "nodes" / f"{node['id'].replace(':', '_')}.md").write_text(
        serialize_node(node),
        encoding="utf-8",
    )
    index = GraphIndex.load_from_disk(root)
    r = asyncio.run(
        dispatch(
            f"edit: id='{node['id']}' description='New text for edit dispatch.'",
            index,
            root,
        )
    )
    assert r.get("ok") is False
    assert "session" in str(r.get("errors", [])).lower()


@pytest.fixture()
def tmp_project_with_v3_node(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path
    gobp_dir = root / ".gobp"
    (gobp_dir / "nodes").mkdir(parents=True)
    node = _minimal_node()
    (gobp_dir / "nodes" / f"{node['id'].replace(':', '_')}.md").write_text(
        serialize_node(node),
        encoding="utf-8",
    )
    return root, node["id"], "meta.session.wavec.test12345678"


def test_dispatch_edit_ok(tmp_project_with_v3_node: tuple[Path, str, str]) -> None:
    root, nid, sid = tmp_project_with_v3_node
    index = GraphIndex.load_from_disk(root)
    with patch("gobp.core.db._get_conn", return_value=None):
        r = asyncio.run(
            dispatch(
                f"edit: id='{nid}' description='Patched via dispatch edit.' session_id='{sid}'",
                index,
                root,
            )
        )
    assert r.get("ok") is True
    loaded = deserialize_node(
        node_file_path(root / ".gobp", nid).read_text(encoding="utf-8")
    )
    assert "Patched via dispatch" in str(loaded.get("description", ""))
