"""Tests for Wave S1 — tier-aware loading (TIER 1 / TIER 2)."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.postgres_v3
def test_count_nodes_in_db(gobp_root: Path) -> None:
    """count_nodes_in_db returns correct count from PostgreSQL v3."""
    from gobp.core.db import count_nodes_in_db, delete_node_v3, ensure_v3_connection, upsert_node_v3
    from tests.fixtures.db_v3 import minimal_v3_node, pytest_skip_without_v3, unique_test_id

    pytest_skip_without_v3(gobp_root)

    conn = ensure_v3_connection(gobp_root)
    try:
        test_ids: list[str] = []
        for i in range(3):
            nid = unique_test_id(f"node:s1_count_{i}_")
            test_ids.append(nid)
            upsert_node_v3(
                conn,
                minimal_v3_node(nid, name=f"S1 Test {i}", group_path="Test > S1"),
            )

        count = count_nodes_in_db(gobp_root)
        assert count >= 3

        for nid in test_ids:
            delete_node_v3(conn, nid)
    finally:
        conn.close()


def test_count_nodes_file_only(tmp_path: Path) -> None:
    """count_nodes_in_db returns 0 when no PostgreSQL available."""
    from gobp.core.db import count_nodes_in_db
    from gobp.core.init import init_project

    init_project(tmp_path)
    count = count_nodes_in_db(tmp_path)
    assert count == 0


def test_tier1_loads_full_nodes(tmp_path: Path) -> None:
    """TIER 1 loads full node data."""
    from gobp.core.graph import GraphIndex
    from gobp.core.init import init_project

    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    assert index.tier == 1
    assert len(index.nodes) > 0

    first_node = next(iter(index.nodes.values()))
    assert "_metadata_only" not in first_node
    assert "description" in first_node or "desc_full" in first_node


@pytest.mark.postgres_v3
def test_adjacency_tier2_lazy_load(gobp_root: Path) -> None:
    """AdjacencyIndex merges PostgreSQL edges with in-memory edges in TIER 2."""
    from gobp.core.db import (
        delete_edge_v3,
        delete_node_v3,
        ensure_v3_connection,
        upsert_edge_v3,
        upsert_node_v3,
    )
    from gobp.core.indexes import AdjacencyIndex
    from tests.fixtures.db_v3 import minimal_v3_node, pytest_skip_without_v3, unique_test_id

    pytest_skip_without_v3(gobp_root)

    conn = ensure_v3_connection(gobp_root)
    try:
        n1 = unique_test_id("node:s1_adj_from_")
        n2 = unique_test_id("node:s1_adj_to_")

        upsert_node_v3(conn, minimal_v3_node(n1, name="From", group_path="Test"))
        upsert_node_v3(conn, minimal_v3_node(n2, name="To", group_path="Test"))
        upsert_edge_v3(conn, n1, n2, reason="test edge")

        adj = AdjacencyIndex()
        adj.set_tier(2, gobp_root)

        outgoing = adj.get_outgoing(n1)
        assert any(e.get("to") == n2 for e in outgoing)

        incoming = adj.get_incoming(n2)
        assert any(e.get("from") == n1 for e in incoming)

        delete_edge_v3(conn, n1, n2)
        delete_node_v3(conn, n1)
        delete_node_v3(conn, n2)
    finally:
        conn.close()


@pytest.mark.postgres_v3
def test_get_node_lazy_load_tier2(gobp_root: Path) -> None:
    """get_node() hydrates from PostgreSQL when the slim row has no file path."""
    from gobp.core.db import delete_node_v3, ensure_v3_connection, upsert_node_v3
    from gobp.core.graph import GraphIndex
    from tests.fixtures.db_v3 import minimal_v3_node, pytest_skip_without_v3, unique_test_id

    pytest_skip_without_v3(gobp_root)

    conn = ensure_v3_connection(gobp_root)
    try:
        nid = unique_test_id("node:s1_lazy_")
        upsert_node_v3(
            conn,
            minimal_v3_node(
                nid,
                name="Lazy Test",
                group_path="Test",
                desc_full="Full description here",
            ),
        )

        index = GraphIndex()
        index.tier = 2
        index._tier2_metadata = True
        index._gobp_root = gobp_root
        index.nodes[nid] = {
            "id": nid,
            "name": "Lazy Test",
            "group": "Test",
            "desc_l1": "L1",
            "type": "Unknown",
            "_metadata_only": True,
        }

        full = index.get_node(nid)
        assert full is not None
        assert full.get("desc_full") == "Full description here"
        assert "_metadata_only" not in full

        delete_node_v3(conn, nid)
    finally:
        conn.close()


@pytest.mark.postgres_v3
def test_get_edges_tier2_lazy(gobp_root: Path) -> None:
    """get_edges_from/to use lazy PostgreSQL in TIER 2."""
    from gobp.core.db import (
        delete_edge_v3,
        delete_node_v3,
        ensure_v3_connection,
        upsert_edge_v3,
        upsert_node_v3,
    )
    from gobp.core.graph import GraphIndex
    from tests.fixtures.db_v3 import minimal_v3_node, pytest_skip_without_v3, unique_test_id

    pytest_skip_without_v3(gobp_root)

    conn = ensure_v3_connection(gobp_root)
    try:
        n1 = unique_test_id("node:s1_edge_from_")
        n2 = unique_test_id("node:s1_edge_to_")

        upsert_node_v3(conn, minimal_v3_node(n1, name="From", group_path="Test"))
        upsert_node_v3(conn, minimal_v3_node(n2, name="To", group_path="Test"))
        upsert_edge_v3(conn, n1, n2, reason="test")

        index = GraphIndex()
        index.tier = 2
        index._gobp_root = gobp_root
        index._tier2_metadata = True
        index._adjacency.set_tier(2, gobp_root)

        edges_from = index.get_edges_from(n1)
        assert len(edges_from) == 1
        assert edges_from[0]["to"] == n2

        edges_to = index.get_edges_to(n2)
        assert len(edges_to) == 1
        assert edges_to[0]["from"] == n1

        delete_edge_v3(conn, n1, n2)
        delete_node_v3(conn, n1)
        delete_node_v3(conn, n2)
    finally:
        conn.close()
