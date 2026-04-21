"""Helpers for tests that require PostgreSQL schema v3.

Schema matches :func:`gobp.core.db.create_schema_v3` (see ``gobp/core/db.py``),
including ``nodes.node_type``.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pytest


def pytest_skip_if_database_name_unsafe_for_truncate(gobp_root: Path) -> None:
    """Skip destructive tests when ``current_database()`` looks like production.

    Call after :func:`pytest_skip_without_v3` so a connection is known possible.
    This is a second line of defense beyond ``GOBP_TEST_ALLOW_TRUNCATE=1``.
    """
    from gobp.core import db as db_mod

    conn = db_mod._get_conn(gobp_root)
    if conn is None:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            row = cur.fetchone()
        name = (row[0] if row else "").strip().lower()
    finally:
        conn.close()
    if not name:
        return
    if name in {"prod", "production", "live"}:
        pytest.skip(f"Refusing TRUNCATE tests on database named {name!r}")
    if "production" in name:
        pytest.skip(f"Refusing TRUNCATE tests: database {name!r} contains 'production'")


def pytest_skip_without_v3(gobp_root: Path) -> None:
    """Skip current test if PostgreSQL v3 is not available for ``gobp_root``."""
    from gobp.core import db as db_mod
    from gobp.core.db_config import is_postgres_available

    if not is_postgres_available(gobp_root):
        pytest.skip("PostgreSQL not configured (set GOBP_DB_URL)")
    conn = db_mod._get_conn(gobp_root)
    if conn is None:
        pytest.skip("Could not open PostgreSQL connection")
    try:
        if db_mod.get_schema_version(conn) != "v3":
            pytest.skip("Connected database is not schema v3")
    finally:
        conn.close()


def unique_test_id(prefix: str) -> str:
    """Return a collision-resistant node id for tests."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def minimal_v3_node(
    node_id: str,
    *,
    name: str,
    group_path: str,
    desc_full: str = "Test node body",
    desc_l1: str | None = None,
    desc_l2: str | None = None,
    node_type: str = "TestKind",
) -> dict[str, Any]:
    """Build a node dict suitable for :func:`gobp.core.db.upsert_node_v3`."""
    l1 = desc_l1 if desc_l1 is not None else "L1 summary"
    l2 = desc_l2 if desc_l2 is not None else "L2 summary"
    return {
        "id": node_id,
        "name": name,
        "type": node_type,
        "group": group_path,
        "group_path": group_path,
        "desc_l1": l1,
        "desc_l2": l2,
        "desc_full": desc_full,
        "description": {"info": desc_full},
        "code": "",
        "severity": "",
    }
