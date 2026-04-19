"""Wave D — MCP read actions v3 (mocked PostgreSQL, no live DB)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gobp.mcp.tools import read_v3
from gobp.mcp.tools import read as tools_read


def _mock_cursor(rows: list[tuple] | None = None) -> MagicMock:
    cur = MagicMock()
    cur.fetchall.return_value = rows or []
    cur.fetchone.return_value = rows[0] if rows else None
    return cur


def test_find_v3_blank_query() -> None:
    conn = MagicMock()
    out = read_v3.find_v3(conn, "   ")
    assert out["ok"] is False


def test_find_v3_compact_format() -> None:
    conn = MagicMock()
    cur = _mock_cursor(
        [
            ("n1", "PaymentService", "Dev > Infra", "l1", "l2", 2.5),
            ("n2", "Other", "Dev > Infra", "l1", "l2", 0.5),
        ]
    )
    conn.cursor.return_value.__enter__.return_value = cur
    out = read_v3.find_v3(conn, "payment", None, "compact", 20, None)
    assert out["ok"] is True
    assert out["matches"][0]["id"] == "n1"
    assert set(out["matches"][0].keys()) == {"id", "name", "group"}


def test_find_v3_name_match_ranks_first() -> None:
    """Higher rank (BM25F) appears first — enforced by SQL order; mock row order."""
    conn = MagicMock()
    cur = _mock_cursor(
        [
            ("name_hit", "PaymentService", "Dev", "l1", "l2", 3.0),
            ("desc_hit", "Other", "Dev", "l1", "payment in desc", 0.4),
        ]
    )
    conn.cursor.return_value.__enter__.return_value = cur
    out = read_v3.find_v3(conn, "payment", None, "summary", 20, None)
    assert out["matches"][0]["id"] == "name_hit"
    assert out["matches"][0]["desc"] == "l1"


def test_find_v3_group_filter_passed() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchall.return_value = []
    read_v3.find_v3(conn, "x", "Dev > Infra", "brief", 10, None)
    sql = cur.execute.call_args[0][0]
    assert "group_path" in sql
    params = cur.execute.call_args[0][1]
    assert "Dev > Infra" in params


def test_find_v3_pagination_next_cursor() -> None:
    conn = MagicMock()
    rows = [
        (f"id{i}", "n", "g", "l1", "l2", 1.0 - i * 0.01)
        for i in range(25)
    ]
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchall.return_value = rows
    out = read_v3.find_v3(conn, "q", None, "brief", 20, None)
    assert out["page_info"]["has_more"] is True
    assert out["next_cursor"] == "id19"


def test_get_v3_brief_edges_need_reason() -> None:
    conn = MagicMock()
    cur1 = MagicMock()
    cur2 = MagicMock()
    cur1.fetchone.return_value = (
        "nid",
        "N",
        "Dev > G",
        "l1",
        "l2 text",
        "full text",
        "",
        "",
        1000,
    )
    cur2.fetchall.return_value = [
        ("nid", "o1", "because", "N", "O"),
        ("nid", "o2", "", "N", "Empty"),
    ]
    conn.cursor.return_value.__enter__.side_effect = [cur1, cur2]
    out = read_v3.get_v3(conn, "nid", "brief")
    assert out["ok"] is True
    assert out["description"] == "l2 text"
    assert len(out["edges"]) == 1
    assert out["edges"][0]["reason"] == "because"


def test_get_batch_v3_since_unchanged() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchall.return_value = [
        ("a", 100),
        ("b", 50),
    ]
    out = read_v3.get_batch_v3(conn, ["a", "b"], "brief", since=200)
    assert out["ok"] is True
    assert out["nodes"]["a"]["unchanged"] is True
    assert out["nodes"]["b"]["unchanged"] is True
    assert out["summary"]["unchanged"] == 2


def test_get_batch_v3_since_fetch_changed() -> None:
    conn = MagicMock()
    cur_ts = MagicMock()
    cur_ts.fetchall.return_value = [("a", 300)]
    g3 = {
        "ok": True,
        "id": "a",
        "name": "A",
        "group": "g",
        "description": "d",
        "updated_at": 300,
        "edges": [],
    }

    def cursor_seq() -> MagicMock:
        return cur_ts

    conn.cursor.return_value.__enter__.side_effect = cursor_seq
    with patch.object(read_v3, "get_v3", return_value=g3):
        out = read_v3.get_batch_v3(conn, ["a"], "brief", since=100)
    assert out["nodes"]["a"]["ok"] is True
    assert out["summary"]["fetched"] == 1


def test_context_action_empty_task() -> None:
    conn = MagicMock()
    assert read_v3.context_action(conn, "  ")["ok"] is False


def test_context_action_no_seed() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchall.return_value = []
    out = read_v3.context_action(conn, "zzzunused")
    assert out["ok"] is True
    assert out["nodes"] == []


def test_overview_v3_structure(tmp_path: Path) -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchone.side_effect = [(10,), (3,)]
    cur.fetchall.side_effect = [
        [("Dev", 5), ("Meta", 2)],
        [],
    ]
    out = read_v3.overview_v3(conn, tmp_path, False)
    assert out["project"]["schema_version"] == "v3"
    assert out["stats"]["nodes_by_group"]["Dev"] == 5
    assert out["stats"]["total_nodes"] == 10


def test_explore_v3_siblings_same_group() -> None:
    conn = MagicMock()
    cur1 = MagicMock()
    cur1.fetchone.return_value = (
        "nid",
        "Node",
        "Dev > G",
        "l2",
        "full",
        "",
        "",
    )
    cur2 = MagicMock()
    cur2.fetchall.return_value = [
        ("nid", "o", "r", "N", "O"),
    ]
    cur3 = MagicMock()
    cur3.fetchall.return_value = [
        ("s1", "Sib", "d1"),
    ]
    seq = [cur1, cur2, cur3]

    def enter(*_a: object, **_k: object) -> MagicMock:
        return seq.pop(0)

    conn.cursor.return_value.__enter__.side_effect = enter
    out = read_v3.explore_v3(conn, "kw")
    assert out["ok"] is True
    assert out["desc"] == "l2"
    assert len(out["edges"]) == 1
    assert out["siblings"][0]["id"] == "s1"


def test_session_resume_not_found() -> None:
    from gobp.mcp.tools import write as tools_write

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchone.return_value = None
    with patch("gobp.core.db._get_conn", return_value=conn):
        with patch("gobp.core.db.get_schema_version", return_value="v3"):
            out = tools_write.session_resume(
                Path("/tmp"), {"id": "meta.session.x.missing"}
            )
    assert out["ok"] is False
    assert "overview" in out.get("hint", "").lower()


@patch("gobp.mcp.tools.read_v3._conn_v3")
def test_find_routes_to_v3(mock_cv3: MagicMock, tmp_path: Path) -> None:
    from gobp.core.graph import GraphIndex

    conn = MagicMock()
    mock_cv3.return_value = (conn, True)
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchall.return_value = []
    idx = GraphIndex()
    args = {"query": "hello", "mode": "summary", "page_size": 10}
    out = tools_read.find(idx, tmp_path, args)
    assert out.get("ok") is True
    mock_cv3.assert_called()


@patch("gobp.mcp.tools.read_v3._conn_v3")
def test_explore_routes_to_v3(mock_cv3: MagicMock, tmp_path: Path) -> None:
    from gobp.core.graph import GraphIndex

    conn = MagicMock()
    mock_cv3.return_value = (conn, True)
    with patch.object(read_v3, "explore_v3", return_value={"ok": True, "id": "x"}):
        idx = GraphIndex()
        out = tools_read.explore_action(
            idx, tmp_path, {"query": "PaymentService"}
        )
    assert out["ok"] is True
    assert out["id"] == "x"
