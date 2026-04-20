"""Helpers for tests that require PostgreSQL schema v3.

Schema matches :func:`gobp.core.db.create_schema_v3` (see ``gobp/core/db.py``).
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pytest


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
) -> dict[str, Any]:
    """Build a node dict suitable for :func:`gobp.core.db.upsert_node_v3`."""
    return {
        "id": node_id,
        "name": name,
        "group": group_path,
        "group_path": group_path,
        "desc_l1": "L1 summary",
        "desc_l2": "L2 summary",
        "desc_full": desc_full,
        "description": {"info": desc_full},
        "code": "",
        "severity": "",
    }
