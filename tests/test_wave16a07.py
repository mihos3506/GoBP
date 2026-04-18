"""Tests for Wave 16A07: Vietnamese search, edge types, duplicate detection."""

from __future__ import annotations

import asyncio

from gobp.core.search import normalize_text, search_score, search_nodes, find_similar_nodes
from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch


# ── normalize_text tests ──────────────────────────────────────────────────────


def test_normalize_removes_vietnamese_diacritics():
    # unidecode: full romanization
    assert normalize_text("Mi Hốt") == "mi hot"
    assert normalize_text("Hà Nội") == "ha noi"
    assert normalize_text("đăng nhập") == "dang nhap"
    assert normalize_text("Bàn Cờ") == "ban co"


def test_normalize_lowercase():
    assert normalize_text("TrustGate") == "trustgate"
    assert normalize_text("MIHOS") == "mihos"


def test_normalize_ascii_unchanged():
    assert normalize_text("mihot") == "mihot"
    assert normalize_text("trustgate engine") == "trustgate engine"


def test_normalize_equivalence():
    """Vietnamese and ASCII versions normalize to same string."""
    assert normalize_text("Mi Hốt") == normalize_text("mi hot")
    assert normalize_text("đăng nhập") == normalize_text("dang nhap")
    assert normalize_text("Hà Nội") == normalize_text("ha noi")


# ── search_score tests ────────────────────────────────────────────────────────


def test_score_exact_name():
    node = {"name": "TrustGate Engine", "id": "x", "description": ""}
    assert search_score("trustgate engine", node) == 100


def test_score_name_starts_with():
    node = {"name": "TrustGate Engine", "id": "x", "description": ""}
    assert search_score("trustgate", node) == 80


def test_score_name_contains():
    node = {"name": "Core TrustGate", "id": "x", "description": ""}
    assert search_score("trustgate", node) == 60


def test_score_id_contains():
    node = {"name": "Something", "id": "trustgate_engine_ops", "description": ""}
    assert search_score("trustgate", node) == 40


def test_score_description_only():
    node = {"name": "Engine A", "id": "engine_a", "description": "uses trustgate internally"}
    assert search_score("trustgate", node) == 20


def test_score_no_match():
    node = {"name": "Auth Engine", "id": "auth_engine", "description": "handles login"}
    assert search_score("trustgate", node) == 0


# ── search_nodes tests ────────────────────────────────────────────────────────


def test_search_vietnamese(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    # Create a node with Vietnamese name
    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='search test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    asyncio.run(dispatch(
        f"create:Flow name='Mi Hốt Standard' session_id={sid}", index, tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    # Search with ASCII version
    results = search_nodes(index, "mihot", exclude_types=[])
    names = [node.get("name") for _, node in results]
    assert any("Mi H" in n for n in names), f"Expected Mi Hốt in {names}"


def test_search_excludes_sessions_by_default(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='session exclusion test'", index, tmp_path
    ))["session_id"]

    index = GraphIndex.load_from_disk(tmp_path)
    results = search_nodes(index, "test")  # default excludes Session
    types = {node.get("type") for _, node in results}
    assert "Session" not in types


def test_search_includes_sessions_when_requested(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    asyncio.run(dispatch(
        "session:start actor='test' goal='include session test'", index, tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    results = search_nodes(index, "test", exclude_types=[])  # include all
    types = {node.get("type") for _, node in results}
    assert "Session" in types


def test_search_type_filter_exact(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='type filter test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    asyncio.run(dispatch(f"create:Engine name='Test Engine' session_id={sid}", index, tmp_path))
    asyncio.run(dispatch(f"create:Flow name='Test Flow' session_id={sid}", index, tmp_path))

    index = GraphIndex.load_from_disk(tmp_path)
    results = search_nodes(index, "test", type_filter="Engine", exclude_types=[])
    types = {node.get("type") for _, node in results}
    assert types == {"Engine"} or not types


def test_search_relevance_ordering(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='relevance test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    asyncio.run(dispatch(
        f"create:Engine name='TrustGate Engine' session_id={sid}", index, tmp_path
    ))
    asyncio.run(dispatch(
        f"create:Engine name='Other Engine' description='uses trustgate' session_id={sid}",
        index,
        tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    results = search_nodes(index, "trustgate", exclude_types=[])
    assert results, "Expected results"
    top_score, top_node = results[0]
    assert "TrustGate" in top_node.get("name", ""), f"Expected TrustGate first, got {top_node.get('name')}"


# ── depends_on edge type tests ────────────────────────────────────────────────


def test_depends_on_edge_valid(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='edge type test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    r1 = asyncio.run(dispatch(f"create:Engine name='EngineA' session_id={sid}", index, tmp_path))
    index = GraphIndex.load_from_disk(tmp_path)
    r2 = asyncio.run(dispatch(f"create:Engine name='EngineB' session_id={sid}", index, tmp_path))
    id_a, id_b = r1["node_id"], r2["node_id"]

    index = GraphIndex.load_from_disk(tmp_path)
    r3 = asyncio.run(dispatch(f"edge: {id_a} --depends_on--> {id_b}", index, tmp_path))
    assert r3.get("ok") is True, f"depends_on edge failed: {r3}"


def test_tested_by_edge_valid(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='tested_by test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    r1 = asyncio.run(dispatch(f"create:Flow name='MyFlow' session_id={sid}", index, tmp_path))
    index = GraphIndex.load_from_disk(tmp_path)
    kinds = index.nodes_by_type("TestKind")
    assert kinds, "init_project should seed TestKind nodes"
    kind_id = kinds[0]["id"]
    id_flow = r1["node_id"]
    r2 = asyncio.run(
        dispatch(
            f"create:TestCase name='MyTest' kind_id='{kind_id}' testkind='unit' "
            f"covers='{id_flow}' status='DRAFT' priority='medium' session_id={sid}",
            index,
            tmp_path,
        )
    )
    assert r2.get("ok") is True, r2
    id_tc = r2["node_id"]

    index = GraphIndex.load_from_disk(tmp_path)
    r3 = asyncio.run(dispatch(f"edge: {id_flow} --validated_by--> {id_tc}", index, tmp_path))
    assert r3.get("ok") is True, f"validated_by edge failed: {r3}"


# ── duplicate detection tests ─────────────────────────────────────────────────


def test_duplicate_warning_on_similar_name(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='duplicate test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    asyncio.run(dispatch(f"create:Engine name='TrustGate Engine' session_id={sid}", index, tmp_path))

    index = GraphIndex.load_from_disk(tmp_path)
    r = asyncio.run(dispatch(
        f"create:Engine name='TrustGate Engine' session_id={sid}", index, tmp_path
    ))
    assert r.get("ok") is True  # Still created
    warnings = r.get("warnings", [])
    has_dup_warning = any(
        (isinstance(w, dict) and w.get("type") == "potential_duplicate") for w in warnings
    )
    assert has_dup_warning, f"Expected duplicate warning, got: {warnings}"


def test_no_false_positive_duplicate(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='no false positive test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)

    r = asyncio.run(dispatch(
        f"create:Engine name='AuthEngine' session_id={sid}", index, tmp_path
    ))
    assert r.get("ok") is True
    warnings = r.get("warnings", [])
    dup_warnings = [w for w in warnings if isinstance(w, dict) and w.get("type") == "potential_duplicate"]
    assert not dup_warnings, f"False positive duplicate warning: {dup_warnings}"


# ── find: action integration tests ───────────────────────────────────────────


def test_find_excludes_sessions_by_default(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    asyncio.run(dispatch(
        "session:start actor='test' goal='find session exclusion'", index, tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    r = asyncio.run(dispatch("find: test mode=summary", index, tmp_path))
    types = {m.get("type") for m in r.get("matches", [])}
    assert "Session" not in types


def test_protocol_guide_has_depends_on():
    from gobp.mcp.parser import PROTOCOL_GUIDE

    actions = PROTOCOL_GUIDE.get("actions", {})
    assert any("depends_on" in k for k in actions), "depends_on not in PROTOCOL_GUIDE"
