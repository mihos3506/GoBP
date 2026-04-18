"""Tests for Wave 16A14: inverted index, adjacency, read paths, cycle detection."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from gobp.core.graph import GraphIndex
from gobp.core.graph_algorithms import detect_cycles
from gobp.core.indexes import AdjacencyIndex, InvertedIndex
from gobp.core.init import init_project
from gobp.core.search import search_nodes, suggest_related
from gobp.mcp.tools import maintain as tools_maintain
from gobp.mcp.tools import read as tools_read


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _engine(name: str, **extra: str) -> dict[str, str]:
    ts = _now_iso()
    base: dict[str, str] = {
        "type": "Engine",
        "name": name,
        "status": "ACTIVE",
        "created": ts,
        "updated": ts,
    }
    base.update(extra)
    return base


# --- InvertedIndex (5) --------------------------------------------------------


def test_inverted_search_and_logic() -> None:
    inv = InvertedIndex()
    inv.build(
        [
            {"id": "a1", "name": "alpha beta", "description": ""},
            {"id": "a2", "name": "alpha gamma", "description": ""},
            {"id": "a3", "name": "delta only", "description": ""},
        ]
    )
    out = set(inv.search("alpha beta", 20))
    assert out == {"a1"}


def test_inverted_or_fallback_when_and_empty() -> None:
    inv = InvertedIndex()
    inv.build(
        [
            {"id": "x1", "name": "foo only here", "description": ""},
            {"id": "x2", "name": "bar other side", "description": ""},
        ]
    )
    out = set(inv.search("foo bar", 20))
    assert "x1" in out and "x2" in out


def test_inverted_remove_node() -> None:
    inv = InvertedIndex()
    inv.add_node({"id": "n1", "name": "keep token", "description": ""})
    inv.remove_node("n1")
    assert inv.search("token", 10) == []


def test_inverted_update_node() -> None:
    inv = InvertedIndex()
    inv.add_node({"id": "u1", "name": "old", "description": ""})
    inv.update_node({"id": "u1", "name": "newbrand", "description": ""})
    ids = inv.search("newbrand", 10)
    assert "u1" in ids
    assert inv.search("old", 10) == []


def test_inverted_short_query_no_tokens() -> None:
    inv = InvertedIndex()
    inv.add_node({"id": "s1", "name": "ab cd", "description": ""})
    assert inv.search("x", 10) == []


# --- AdjacencyIndex (5) -------------------------------------------------------


def test_adjacency_build_and_lookup() -> None:
    adj = AdjacencyIndex()
    adj.build(
        [
            {"from": "a", "to": "b", "type": "relates_to"},
            {"from": "b", "to": "c", "type": "relates_to"},
        ]
    )
    assert len(adj.get_outgoing("a")) == 1
    assert len(adj.get_incoming("c")) == 1


def test_adjacency_exclude_types() -> None:
    adj = AdjacencyIndex()
    adj.add_edge("a", "b", "relates_to")
    adj.add_edge("a", "c", "discovered_in")
    out = adj.get_outgoing("a", exclude_types={"discovered_in"})
    assert len(out) == 1
    assert out[0].get("to") == "b"


def test_adjacency_add_remove_edge() -> None:
    adj = AdjacencyIndex()
    adj.add_edge("p", "q", "relates_to")
    assert adj.edge_count("p") == 1
    adj.remove_edge("p", "q", "relates_to")
    assert adj.edge_count("p") == 0


def test_adjacency_remove_node() -> None:
    adj = AdjacencyIndex()
    adj.add_edge("u", "v", "relates_to")
    adj.add_edge("v", "w", "relates_to")
    adj.remove_node("v")
    assert adj.edge_count("u") == 0
    assert adj.edge_count("w") == 0


def test_adjacency_get_all() -> None:
    adj = AdjacencyIndex()
    adj.add_edge("a", "b", "relates_to")
    adj.add_edge("c", "a", "relates_to")
    o, i = adj.get_all("a")
    assert len(o) == 1 and len(i) == 1


# --- GraphIndex integration (3) -----------------------------------------------


def test_graphindex_load_builds_secondary_indexes(tmp_path: Path) -> None:
    init_project(tmp_path)
    idx = GraphIndex.load_from_disk(tmp_path)
    assert hasattr(idx, "_inverted") and hasattr(idx, "_adjacency")


def test_graphindex_add_node_updates_inverted(tmp_path: Path) -> None:
    init_project(tmp_path)
    idx = GraphIndex.load_from_disk(tmp_path)
    nid = idx.add_node_in_memory(
        _engine("uniquewave tokenxyz", description="")
    )
    hits = idx._inverted.search("tokenxyz", 10)
    assert nid in hits


def test_graphindex_add_edge_updates_adjacency(tmp_path: Path) -> None:
    init_project(tmp_path)
    idx = GraphIndex.load_from_disk(tmp_path)
    a = idx.add_node_in_memory(_engine("A node"))
    b = idx.add_node_in_memory(_engine("B node"))
    idx.add_edge_in_memory(a, b, "relates_to")
    out = idx._adjacency.get_outgoing(a)
    assert len(out) == 1 and out[0].get("to") == b


# --- Read paths (4) -----------------------------------------------------------


def test_search_nodes_uses_inverted_candidates(tmp_path: Path) -> None:
    init_project(tmp_path)
    idx = GraphIndex.load_from_disk(tmp_path)
    idx.add_node_in_memory(
        _engine("findme specialword", description="extra")
    )
    rows = search_nodes(idx, "specialword", exclude_types=[], limit=10)
    assert rows and rows[0][1].get("name", "").find("specialword") >= 0


def test_suggest_related_with_index(tmp_path: Path) -> None:
    init_project(tmp_path)
    idx = GraphIndex.load_from_disk(tmp_path)
    idx.add_node_in_memory(
        _engine(
            "payment gateway flow",
            description="handles payment gateway integration",
        )
    )
    sug = suggest_related(
        idx, "payment gateway integration", exclude_types=[], limit=5
    )
    assert sug


def test_explore_uses_adjacency(tmp_path: Path) -> None:
    init_project(tmp_path)
    idx = GraphIndex.load_from_disk(tmp_path)
    a = idx.add_node_in_memory(_engine("explore alpha keyword"))
    b = idx.add_node_in_memory(_engine("neighbor beta"))
    idx.add_edge_in_memory(a, b, "relates_to")
    r = tools_read.explore_action(idx, tmp_path, {"query": "alpha keyword"})
    assert r.get("ok") is True
    assert r.get("edge_count", 0) >= 1


def test_find_legacy_substring_after_inverted(tmp_path: Path) -> None:
    init_project(tmp_path)
    idx = GraphIndex.load_from_disk(tmp_path)
    idx.add_node_in_memory(
        _engine("Z", description="longdescription legacysubstringmatch")
    )
    r = tools_read.find(
        idx, tmp_path, {"query": "legacysubstringmatch", "page_size": 20}
    )
    assert r.get("ok") is True
    assert r.get("count", 0) >= 1


# --- Cycle detection (4) ------------------------------------------------------


def test_detect_cycles_finds_triangle() -> None:
    idx = GraphIndex()
    # minimal manual graph without load_from_disk — use empty schema path issues
    # Use in-memory only for structure: GraphIndex needs edges list
    idx._edges = [
        {"from": "a", "to": "b", "type": "depends_on"},
        {"from": "b", "to": "c", "type": "depends_on"},
        {"from": "c", "to": "a", "type": "depends_on"},
    ]
    cyc = detect_cycles(idx, ["depends_on"])
    assert cyc


def test_detect_cycles_empty_when_acyclic() -> None:
    idx = GraphIndex()
    idx._edges = [
        {"from": "a", "to": "b", "type": "depends_on"},
        {"from": "b", "to": "c", "type": "depends_on"},
    ]
    assert detect_cycles(idx, ["depends_on"]) == []


def test_validate_reports_cycle(tmp_path: Path) -> None:
    init_project(tmp_path)
    idx = GraphIndex.load_from_disk(tmp_path)
    a = idx.add_node_in_memory(_engine("CA"))
    b = idx.add_node_in_memory(_engine("CB"))
    c = idx.add_node_in_memory(_engine("CC"))
    idx.add_edge_in_memory(a, b, "depends_on")
    idx.add_edge_in_memory(b, c, "depends_on")
    idx.add_edge_in_memory(c, a, "depends_on")
    r = tools_maintain.validate(idx, tmp_path, {"scope": "edges"})
    types = {i.get("type") for i in r.get("issues", [])}
    assert "cycle" in types


def test_detect_cycles_respects_edge_types() -> None:
    idx = GraphIndex()
    idx._edges = [
        {"from": "a", "to": "b", "type": "depends_on"},
        {"from": "b", "to": "c", "type": "depends_on"},
    ]
    assert detect_cycles(idx, ["depends_on"]) == []

    idx2 = GraphIndex()
    idx2._edges = [
        {"from": "a", "to": "b", "type": "relates_to"},
        {"from": "b", "to": "a", "type": "relates_to"},
    ]
    assert detect_cycles(idx2, ["relates_to"])
