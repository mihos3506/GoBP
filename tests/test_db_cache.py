"""Tests for gobp/core/db.py and gobp/core/cache.py."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from gobp.core.cache import GoBPCache, get_cache, reset_cache
from gobp.core import db as db_module


# ── Cache tests ───────────────────────────────────────────────────────────────

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


# ── SQLite db tests ───────────────────────────────────────────────────────────

def test_db_init_schema_idempotent(gobp_root: Path):
    """init_schema can be called twice without error."""
    db_module.init_schema(gobp_root)
    db_module.init_schema(gobp_root)
    assert db_module.index_exists(gobp_root)


def test_db_upsert_and_query_node(gobp_root: Path):
    """upsert_node + query_nodes_by_type roundtrip."""
    db_module.init_schema(gobp_root)
    node = {
        "id": "node:test001",
        "type": "Node",
        "name": "Test Node",
        "status": "ACTIVE",
        "created": "2026-04-15T00:00:00",
        "updated": "2026-04-15T00:00:00",
    }
    db_module.upsert_node(gobp_root, node)
    ids = db_module.query_nodes_by_type(gobp_root, "Node")
    assert "node:test001" in ids


def test_db_delete_node(gobp_root: Path):
    """delete_node removes from index."""
    db_module.init_schema(gobp_root)
    node = {"id": "node:del001", "type": "Node", "name": "Delete Me",
            "status": "ACTIVE", "created": "2026-04-15T00:00:00", "updated": "2026-04-15T00:00:00"}
    db_module.upsert_node(gobp_root, node)
    db_module.delete_node(gobp_root, "node:del001")
    ids = db_module.query_nodes_by_type(gobp_root, "Node")
    assert "node:del001" not in ids


def test_db_upsert_and_query_edges(gobp_root: Path):
    """upsert_edge + query_edges_from roundtrip."""
    db_module.init_schema(gobp_root)
    edge = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    db_module.upsert_edge(gobp_root, edge)
    edges = db_module.query_edges_from(gobp_root, "node:a")
    assert len(edges) == 1
    assert edges[0]["to"] == "node:b"


def test_db_query_edges_to(gobp_root: Path):
    """query_edges_to returns correct edges."""
    db_module.init_schema(gobp_root)
    edge = {"from": "node:x", "to": "node:y", "type": "implements"}
    db_module.upsert_edge(gobp_root, edge)
    edges = db_module.query_edges_to(gobp_root, "node:y")
    assert len(edges) == 1
    assert edges[0]["from"] == "node:x"


def test_db_substring_search(gobp_root: Path):
    """query_nodes_substring finds by name substring."""
    db_module.init_schema(gobp_root)
    node = {"id": "node:login001", "type": "Node", "name": "Login Feature",
            "status": "ACTIVE", "created": "2026-04-15T00:00:00", "updated": "2026-04-15T00:00:00"}
    db_module.upsert_node(gobp_root, node)
    ids = db_module.query_nodes_substring(gobp_root, "login")
    assert "node:login001" in ids


def test_db_type_filter_in_search(gobp_root: Path):
    """query_nodes_substring with type_filter."""
    db_module.init_schema(gobp_root)
    n1 = {"id": "node:f001", "type": "Node", "name": "auth feature",
          "status": "ACTIVE", "created": "2026-04-15T00:00:00", "updated": "2026-04-15T00:00:00"}
    n2 = {"id": "dec:d001", "type": "Decision", "name": "auth decision",
          "status": "LOCKED", "topic": "auth:method",
          "created": "2026-04-15T00:00:00", "updated": "2026-04-15T00:00:00"}
    db_module.upsert_node(gobp_root, n1)
    db_module.upsert_node(gobp_root, n2)

    node_ids = db_module.query_nodes_substring(gobp_root, "auth", type_filter="Node")
    assert "node:f001" in node_ids
    assert "dec:d001" not in node_ids


def test_db_rebuild_index(gobp_root: Path):
    """rebuild_index creates fresh index from GraphIndex."""
    from gobp.core.init import init_project
    from gobp.core.graph import GraphIndex

    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = db_module.rebuild_index(gobp_root, index)
    assert result["ok"] is True
    assert result["nodes_indexed"] >= 17  # seed nodes
