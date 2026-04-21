"""Tests for gobp/core/cache.py and PostgreSQL v3 helpers in gobp/core/db.py."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from gobp.core.cache import GoBPCache, get_cache, reset_cache
from gobp.core import db as db_module
from tests.fixtures.db_v3 import (
    minimal_v3_node,
    pytest_skip_if_database_name_unsafe_for_truncate,
    pytest_skip_without_v3,
    unique_test_id,
)

# ── Cache tests (no database) ───────────────────────────────────────────────


def test_cache_get_miss():
    cache = GoBPCache()
    assert cache.get("missing") is None


def test_cache_set_and_get():
    cache = GoBPCache()
    cache.set("key", {"value": 42})
    result = cache.get("key")
    assert result == {"value": 42}


def test_cache_ttl_expiry():
    cache = GoBPCache(default_ttl=0.05)  # 50ms TTL
    cache.set("key", "value")
    time.sleep(0.1)
    assert cache.get("key") is None


def test_cache_lru_eviction():
    cache = GoBPCache(max_size=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)  # evicts "a" (LRU)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_cache_invalidate():
    cache = GoBPCache()
    cache.set("key", "value")
    cache.invalidate("key")
    assert cache.get("key") is None


def test_cache_invalidate_prefix():
    cache = GoBPCache()
    cache.set("node:a", 1)
    cache.set("node:b", 2)
    cache.set("edge:x", 3)
    cache.invalidate_prefix("node:")
    assert cache.get("node:a") is None
    assert cache.get("node:b") is None
    assert cache.get("edge:x") == 3


def test_cache_invalidate_all():
    cache = GoBPCache()
    cache.set("a", 1)
    cache.set("b", 2)
    cache.invalidate_all()
    assert len(cache) == 0


def test_cache_singleton():
    reset_cache()
    c1 = get_cache()
    c2 = get_cache()
    assert c1 is c2


def test_cache_stats():
    cache = GoBPCache()
    cache.set("a", 1)
    stats = cache.stats()
    assert stats["total_entries"] == 1
    assert stats["active_entries"] == 1


# ── PostgreSQL v3 (requires GOBP_DB_URL + v3 schema) ─────────────────────────


@pytest.mark.postgres_v3
def test_v3_upsert_select_delete_roundtrip(gobp_root: Path) -> None:
    """``upsert_node_v3`` + SQL read + ``delete_node_v3``."""
    pytest_skip_without_v3(gobp_root)
    from gobp.core.db import delete_node_v3, ensure_v3_connection, upsert_node_v3

    nid = unique_test_id("node:pytest_dbcache_")
    conn = ensure_v3_connection(gobp_root)
    try:
        upsert_node_v3(
            conn,
            minimal_v3_node(
                nid,
                name="DB cache v3 roundtrip",
                group_path="Test > DBCache",
            ),
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name, group_path, desc_l1 FROM nodes WHERE id = %s", (nid,)
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == "DB cache v3 roundtrip"
        assert row[1] == "Test > DBCache"
        assert row[2] == "L1 summary"
    finally:
        delete_node_v3(conn, nid)
        conn.close()


@pytest.mark.postgres_v3
def test_v3_edge_upsert_and_delete(gobp_root: Path) -> None:
    """``upsert_edge_v3`` between two nodes; edges removed when node deleted."""
    pytest_skip_without_v3(gobp_root)
    from gobp.core.db import (
        delete_node_v3,
        ensure_v3_connection,
        upsert_edge_v3,
        upsert_node_v3,
    )

    a = unique_test_id("node:pytest_dbcache_a_")
    b = unique_test_id("node:pytest_dbcache_b_")
    conn = ensure_v3_connection(gobp_root)
    try:
        upsert_node_v3(
            conn,
            minimal_v3_node(a, name="A", group_path="Test > DBCache"),
        )
        upsert_node_v3(
            conn,
            minimal_v3_node(b, name="B", group_path="Test > DBCache"),
        )
        upsert_edge_v3(conn, a, b, reason="relates_to test", code="")
        with conn.cursor() as cur:
            cur.execute(
                "SELECT from_id, to_id FROM edges WHERE from_id = %s AND to_id = %s",
                (a, b),
            )
            row = cur.fetchone()
        assert row is not None
    finally:
        delete_node_v3(conn, a)
        delete_node_v3(conn, b)
        conn.close()


@pytest.mark.postgres_v3
@pytest.mark.postgres_v3
def test_v3_upsert_stores_node_type(gobp_root: Path) -> None:
    """``node_type`` column mirrors graph ``type``."""
    pytest_skip_without_v3(gobp_root)
    from gobp.core.db import delete_node_v3, ensure_v3_connection, upsert_node_v3

    nid = unique_test_id("node:pytest_dbcache_type_")
    conn = ensure_v3_connection(gobp_root)
    try:
        upsert_node_v3(
            conn,
            minimal_v3_node(
                nid,
                name="Typed node",
                group_path="Test > DBCache",
                node_type="Invariant",
            ),
        )
        with conn.cursor() as cur:
            cur.execute("SELECT node_type FROM nodes WHERE id = %s", (nid,))
            row = cur.fetchone()
        assert row is not None
        assert row[0] == "Invariant"
    finally:
        delete_node_v3(conn, nid)
        conn.close()


@pytest.mark.postgres_v3
def test_v3_find_v3_type_filter_excludes_other_types(gobp_root: Path) -> None:
    """PostgreSQL FTS find respects ``type_filter`` via ``node_type``."""
    pytest_skip_without_v3(gobp_root)
    from gobp.core.db import delete_node_v3, ensure_v3_connection, upsert_node_v3
    from gobp.mcp.tools import read_v3

    token = unique_test_id("tok_")[-10:]
    a = unique_test_id("node:pytest_find_a_")
    b = unique_test_id("node:pytest_find_b_")
    conn = ensure_v3_connection(gobp_root)
    try:
        upsert_node_v3(
            conn,
            minimal_v3_node(
                a,
                name=f"Alpha {token} lessonish",
                group_path="Test > DBCache",
                node_type="Lesson",
            ),
        )
        upsert_node_v3(
            conn,
            minimal_v3_node(
                b,
                name=f"Beta {token} flowish",
                group_path="Test > DBCache",
                node_type="Flow",
            ),
        )
        out = read_v3.find_v3(conn, token, None, "summary", 20, None, type_filter="Lesson")
        assert out["ok"] is True
        ids = {m["id"] for m in out["matches"]}
        assert a in ids
        assert b not in ids
        for m in out["matches"]:
            if m["id"] == a:
                assert m.get("type") == "Lesson"
    finally:
        delete_node_v3(conn, a)
        delete_node_v3(conn, b)
        conn.close()


def test_v3_name_substring_search_sql(gobp_root: Path) -> None:
    """ILIKE on ``name`` (replaces legacy ``query_nodes_substring`` for v3)."""
    pytest_skip_without_v3(gobp_root)
    from gobp.core.db import delete_node_v3, ensure_v3_connection, upsert_node_v3

    nid = unique_test_id("node:pytest_dbcache_login_")
    conn = ensure_v3_connection(gobp_root)
    try:
        upsert_node_v3(
            conn,
            minimal_v3_node(
                nid,
                name="Login Feature XYZ",
                group_path="Test > DBCache",
            ),
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM nodes WHERE id = %s AND name ILIKE %s",
                (nid, "%login%"),
            )
            found = cur.fetchone()
        assert found is not None
        assert found[0] == nid
    finally:
        delete_node_v3(conn, nid)
        conn.close()


@pytest.mark.postgres_v3
def test_v3_group_path_filter_sql(gobp_root: Path) -> None:
    """Filter by ``group_path`` prefix (v3 ``nodes`` includes ``node_type`` for FTS filters)."""
    pytest_skip_without_v3(gobp_root)
    from gobp.core.db import delete_node_v3, ensure_v3_connection, upsert_node_v3

    nid = unique_test_id("node:pytest_dbcache_grp_")
    conn = ensure_v3_connection(gobp_root)
    try:
        upsert_node_v3(
            conn,
            minimal_v3_node(
                nid,
                name="auth feature filter",
                group_path="Test > DBCache > Alpha",
            ),
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM nodes
                WHERE id = %s AND group_path LIKE %s
                """,
                (nid, "Test > DBCache%"),
            )
            row = cur.fetchone()
        assert row is not None
    finally:
        delete_node_v3(conn, nid)
        conn.close()


@pytest.mark.destructive
@pytest.mark.postgres_v3
@pytest.mark.skipif(
    os.environ.get("GOBP_TEST_ALLOW_TRUNCATE") != "1",
    reason=(
        "rebuild_index TRUNCATEs all nodes/edges — set GOBP_TEST_ALLOW_TRUNCATE=1 "
        "only on a disposable PostgreSQL database"
    ),
)
def test_v3_rebuild_index_from_file_graph(gobp_root: Path) -> None:
    """``rebuild_index`` reloads PG from :class:`GraphIndex` (destructive)."""
    pytest_skip_without_v3(gobp_root)
    pytest_skip_if_database_name_unsafe_for_truncate(gobp_root)
    from gobp.core.init import init_project
    from gobp.core.graph import GraphIndex

    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = db_module.rebuild_index(gobp_root, index)
    assert result["ok"] is True
    assert result["nodes_indexed"] >= 1
