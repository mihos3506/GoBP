"""PostgreSQL helper safety: parameterized SQL and connection context manager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


def test_upsert_node_v3_passes_values_as_params_not_in_sql() -> None:
    """Malicious ``name`` must appear only in bound parameters, not in SQL text."""
    from gobp.core import db as db_mod

    malicious = "'; DROP TABLE nodes; --"
    captured: list[tuple[str, tuple | None]] = []

    cur = MagicMock()

    def _exec(sql: str, params: tuple | None = None) -> None:
        captured.append((sql, params))

    cur.execute = _exec
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cm

    node = {
        "id": "lesson:test_security_001",
        "name": malicious,
        "group": "Test",
        "desc_l1": "L1",
        "desc_l2": "L2",
        "description": {"info": "body"},
        "code": "",
        "severity": "",
    }
    db_mod.upsert_node_v3(conn, node)

    assert captured, "execute should have been called"
    sql, params = captured[0]
    assert "DROP TABLE" not in sql.upper()
    assert malicious in params


def test_postgres_connection_yields_none_when_no_db(monkeypatch: pytest.MonkeyPatch) -> None:
    from gobp.core import db as db_mod

    monkeypatch.delenv("GOBP_DB_URL", raising=False)

    with db_mod.postgres_connection(Path("/nonexistent/gobp")) as conn:
        assert conn is None


def test_postgres_connection_commits_and_closes_on_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from gobp.core import db as db_mod

    conn = MagicMock()
    monkeypatch.setattr(db_mod, "_get_conn", lambda _root: conn)

    with db_mod.postgres_connection(tmp_path):
        pass

    conn.commit.assert_called_once()
    conn.close.assert_called_once()


def test_postgres_connection_rollback_and_closes_on_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from gobp.core import db as db_mod

    conn = MagicMock()
    monkeypatch.setattr(db_mod, "_get_conn", lambda _root: conn)

    with pytest.raises(RuntimeError):
        with db_mod.postgres_connection(tmp_path):
            raise RuntimeError("boom")

    conn.rollback.assert_called_once()
    conn.close.assert_called_once()
