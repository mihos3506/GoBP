"""Wave F — import lock, validate v3, session watchdog, ping (mocked, no live DB)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from gobp.core import import_lock
from gobp.core import session_watchdog
from gobp.mcp.tools import read_v3


def test_import_lock_acquired_mock_conn() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchone.return_value = (True,)

    with patch.object(import_lock, "create_import_locks_table"):
        with patch.object(import_lock, "_register_lock"):
            with patch.object(import_lock, "_unregister_lock"):
                with import_lock.acquire_import_lock(conn, "doc-a", "sess-1") as lock:
                    assert lock.acquired is True
                    assert lock.doc_id == "doc-a"


def test_import_lock_second_call_blocked() -> None:
    """Simulate: first lock held → second try returns False."""
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchone.side_effect = [(True,), (False,)]

    with patch.object(import_lock, "create_import_locks_table"):
        with patch.object(import_lock, "_register_lock"):
            with patch.object(import_lock, "_unregister_lock"):
                with import_lock.acquire_import_lock(conn, "same-doc", "s1") as lock1:
                    assert lock1.acquired is True
                with import_lock.acquire_import_lock(conn, "same-doc", "s2") as lock2:
                    assert lock2.acquired is False
                    assert lock2.hint


def test_import_lock_none_conn_always_acquired() -> None:
    with import_lock.acquire_import_lock(None, "x", "y") as lock:
        assert lock.acquired is True


def test_validate_v3_missing_description_error() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchall.side_effect = [
        [("n1", "", "g", "d")],
        [],
        [],
        [],
        [],
    ]
    cur.fetchone.return_value = (5,)

    out = read_v3.validate_v3(conn)
    assert out["ok"] is True
    assert any("Missing required" in i["issue"] for i in out["issues"])
    assert out["score"] < 100


def test_validate_v3_invalid_errorcase_severity() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchall.side_effect = [
        [],
        [("e1", "oops")],
        [],
        [],
        [],
    ]
    cur.fetchone.return_value = (3,)

    out = read_v3.validate_v3(conn)
    assert any("severity" in i["issue"].lower() for i in out["issues"])


def test_validate_v3_stale_session_warning() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    old_ts = 0
    cur.fetchall.side_effect = [
        [],
        [],
        [],
        [],
        [("sess-old", "S", old_ts)],
    ]
    cur.fetchone.return_value = (10,)

    out = read_v3.validate_v3(conn)
    assert any("Stale session" in i["issue"] for i in out["issues"])


def test_validate_v3_perfect_graph_score_100() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchall.side_effect = [[], [], [], [], []]
    cur.fetchone.return_value = (7,)

    out = read_v3.validate_v3(conn)
    assert out["score"] == 100
    assert out["total"] == 7


def test_watchdog_skips_recent_session() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchall.return_value = []

    closed = session_watchdog.close_stale_sessions(conn)
    assert closed == []


def test_watchdog_closes_stale(tmp_path: Path) -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    old = 1_000_000
    cur.fetchall.return_value = [
        ("sid1", "goal IN_PROGRESS x", old),
    ]

    closed = session_watchdog.close_stale_sessions(conn)
    assert "sid1" in closed
    assert cur.execute.called


def test_ping_ok_structure() -> None:
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    cur.fetchone.return_value = (2,)
    cur.fetchall.return_value = [("d1", "s1")]

    with patch("gobp.core.db.get_schema_version", return_value="v3"):
        out = read_v3.ping_action(conn, Path("/tmp"))
    assert out["ok"] is True
    assert out["db"] == "connected"
    assert out["schema_version"] == "v3"
    assert out["active_sessions"] == 2
    assert out["import_locks"]["d1"] == "s1"


def test_ping_db_failure() -> None:
    conn = MagicMock()
    conn.cursor.side_effect = RuntimeError("down")

    out = read_v3.ping_action(conn, Path("/tmp"))
    assert out["ok"] is False
    assert "down" in out["db"]
