"""Tests for Wave 16A09: template, explore, suggest, batch, batch_parser."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.core.search import suggest_related
from gobp.mcp.batch_parser import parse_batch, parse_batch_line, parse_batch_ops
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.parser import PROTOCOL_GUIDE, parse_query


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    init_project(tmp_path)
    return tmp_path


def _sid(proj: Path) -> str:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("session:start actor='t' goal='t'", index, proj))
    return str(r["session_id"])


# --- template -----------------------------------------------------------------


def test_template_returns_frame(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template: Engine", index, proj))
    assert r["ok"]
    assert "frame" in r
    assert "required" in r["frame"]
    # Schema v2 compact YAML may omit per-field required blocks; v2_template carries taxonomy.
    if r.get("v2_template"):
        assert r["v2_template"].get("group")
    else:
        assert "name" in r["frame"]["required"]


def test_template_invalid_type(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template: FakeType", index, proj))
    assert not r["ok"]
    assert "available" in r


def test_template_catalog(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template:", index, proj))
    assert r["ok"]
    assert r.get("catalog") is True
    assert "node_types" in r


# --- explore ------------------------------------------------------------------


def test_explore_returns_node_and_edges(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(
        dispatch(f"create:Engine name='EngW16' session_id={sid} description='d'", index, proj)
    )
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(dispatch(f"create:Flow name='FlowW16' session_id={sid} description='f'", index, proj))
    index = GraphIndex.load_from_disk(proj)
    r1 = asyncio.run(dispatch("find: EngW16 mode=summary", index, proj))
    r2 = asyncio.run(dispatch("find: FlowW16 mode=summary", index, proj))
    if r1.get("matches") and r2.get("matches"):
        id_a = r1["matches"][0]["id"]
        id_b = r2["matches"][0]["id"]
        asyncio.run(dispatch(f"edge: {id_a} --implements--> {id_b}", index, proj))
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("explore: EngW16", index, proj))
    assert r["ok"]
    assert "node" in r
    assert "edges" in r
    assert r.get("edge_count", 0) >= 1


def test_explore_not_found(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("explore: NonExistentXYZ123", index, proj))
    assert not r["ok"]


def test_explore_multi_word_query(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(
        dispatch(
            f"create:Engine name='Alpha Beta' session_id={sid} description='x'",
            index,
            proj,
        )
    )
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("explore: Alpha Beta", index, proj))
    assert r["ok"]
    assert r["node"]["name"] == "Alpha Beta"


# --- suggest ------------------------------------------------------------------


def test_suggest_finds_related(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(
        dispatch(
            f"create:Engine name='EmberEngine' session_id={sid} "
            "description='payment and revenue processing'",
            index,
            proj,
        )
    )
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("suggest: payment flow", index, proj))
    assert r["ok"]
    assert r["count"] >= 1
    names = [s["name"] for s in r["suggestions"]]
    assert any("Ember" in n for n in names)


def test_suggest_empty(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("suggest: xyznonexistent999", index, proj))
    assert r["ok"]
    assert r["count"] == 0


def test_suggest_excludes_sessions(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("suggest: test session", index, proj))
    types = {s["type"] for s in r.get("suggestions", [])}
    assert "Session" not in types
    assert "Document" not in types


# --- batch parse --------------------------------------------------------------


def test_parse_batch_create() -> None:
    p = parse_batch_line("create: Engine: TrustGate | Trust scoring")
    assert p["kind"] == "create"
    assert p["node_type"] == "Engine"
    assert p["name"] == "TrustGate"


def test_parse_batch_update() -> None:
    p = parse_batch_line("update: node.test.123 description=Hello")
    assert p["kind"] == "update"
    assert p["node_id"] == "node.test.123"
    assert p["fields"]["description"] == "Hello"


def test_parse_batch_merge() -> None:
    p = parse_batch_line("merge: keep=a.ops.1 absorb=b.ops.2")
    assert p["kind"] == "merge"
    assert p["keep"] == "a.ops.1"
    assert p["absorb"] == "b.ops.2"


def test_parse_batch_edge_add() -> None:
    p = parse_batch_line("edge+: FromNode --depends_on--> ToNode")
    assert p["kind"] == "edge_add"
    assert p["from_name"] == "FromNode"
    assert p["edge_type"] == "depends_on"
    assert p["targets"] == ["ToNode"]


def test_parse_batch_edge_add_multiple_targets() -> None:
    p = parse_batch_line("edge+: Hub --implements--> EngineA, EngineB, EngineC")
    assert p["kind"] == "edge_add"
    assert p["targets"] == ["EngineA", "EngineB", "EngineC"]


def test_parse_batch_edge_colon_in_node_ids() -> None:
    """Edge endpoints may contain ':' (e.g. doc:doc_01); delimiter is --type-->."""
    ops = parse_batch("edge+: doc:doc_01 --references--> node:inv_01")
    assert ops[0]["from_name"] == "doc:doc_01"
    assert ops[0]["targets"] == ["node:inv_01"]
    assert ops[0]["edge_type"] == "references"
    star = parse_batch("edge*: hub:x --implements--> doc:a, node:b")
    assert star[0]["from_name"] == "hub:x"
    assert star[0]["targets"] == ["doc:a", "node:b"]


def test_parse_batch_ops_multiline() -> None:
    text = "create: Flow: A | x\n\ncreate: Engine: B | y\n"
    ops, errs = parse_batch_ops(text)
    assert not errs
    assert len(ops) == 2


def test_parse_query_batch_embedded_colons() -> None:
    sid = "meta.session.2026-04-17.testabc123"
    ops = "create: Engine: A | d"
    q = f"batch session_id='{sid}' ops='{ops}'"
    a, nt, p = parse_query(q)
    assert a == "batch"
    assert nt == ""
    assert p.get("session_id") == sid
    assert "create:" in str(p.get("ops", ""))


# --- batch execute ------------------------------------------------------------


def test_batch_creates_nodes(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    ops = "create: Engine: BatchEng1 | one\ncreate: Flow: BatchFlow1 | two"
    r = asyncio.run(dispatch(f"batch session_id='{sid}' ops='{ops}'", index, proj))
    assert r["ok"]
    assert r["succeeded"] >= 2


def test_batch_skips_duplicate(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(dispatch(f"create:Engine name='DupEng' session_id={sid}", index, proj))
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(
        dispatch(
            f"batch session_id='{sid}' ops='create: Engine: DupEng | retry'",
            index,
            proj,
        )
    )
    assert r["ok"]
    assert r["skipped"]


def test_batch_requires_session(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("batch ops='create: Engine: X | y'", index, proj))
    assert not r["ok"]


def test_batch_edge_add_by_name(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    ops = (
        "create: Engine: EdgeFrom | a\n"
        "create: Flow: EdgeTo | b\n"
        "edge+: EdgeFrom --implements--> EdgeTo"
    )
    r = asyncio.run(dispatch(f"batch session_id='{sid}' ops='{ops}'", index, proj))
    assert r["ok"]
    assert r["errors"] == []


def test_batch_edge_add_multiple_targets_one_line(proj: Path) -> None:
    """One edge+ line can fan out to many nodes (comma-separated targets)."""
    sid = _sid(proj)
    ops = (
        "create: Engine: HubEng | hub\n"
        "create: Engine: LeafA | a\n"
        "create: Engine: LeafB | b\n"
        "edge+: HubEng --depends_on--> LeafA, LeafB"
    )
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(
        dispatch(f"batch session_id='{sid}' ops='{ops}'", index, proj),
    )
    assert r["ok"], r
    assert r.get("errors") == []
    fresh = GraphIndex.load_from_disk(proj)
    hub_id = _resolve_name(fresh, "HubEng")
    a_id = _resolve_name(fresh, "LeafA")
    b_id = _resolve_name(fresh, "LeafB")
    assert hub_id and a_id and b_id
    outs = fresh.get_edges_from(hub_id)
    types_to = {(e.get("type"), e.get("to")) for e in outs}
    assert ("depends_on", a_id) in types_to
    assert ("depends_on", b_id) in types_to


def _resolve_name(index: GraphIndex, name: str) -> str | None:
    from gobp.core.search import normalize_text

    key = normalize_text(name).replace(" ", "")
    for n in index.all_nodes():
        nk = normalize_text(str(n.get("name", ""))).replace(" ", "")
        if nk == key:
            return str(n.get("id"))
    return None


@pytest.mark.slow
def test_batch_max_ops_guard(proj: Path) -> None:
    """Large batches are accepted; execution is chunked internally (Wave 16A13)."""
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    lines = "\n".join([f"create: Engine: N{i} | x" for i in range(501)])
    r = asyncio.run(dispatch(f"batch session_id='{sid}' ops='{lines}'", index, proj))
    assert r["ok"]
    assert r.get("succeeded", 0) >= 500


def test_batch_update_node(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    cr = asyncio.run(
        dispatch(f"create:Engine name='UpdMe' session_id={sid} description='old'", index, proj)
    )
    assert cr.get("ok")
    nid = str(cr["node_id"])
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(
        dispatch(
            f"batch session_id='{sid}' ops=\"update: {nid} description=NewDesc\"",
            index,
            proj,
        )
    )
    assert r["ok"]
    fresh = GraphIndex.load_from_disk(proj).get_node(nid)
    assert fresh
    desc = fresh.get("description")
    if isinstance(desc, dict):
        assert desc.get("info") == "NewDesc"
    else:
        assert desc == "NewDesc"


# --- suggest_related + protocol -----------------------------------------------


def test_suggest_related_keyword_overlap(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(
        dispatch(
            f"create:Entity name='EarningLedger' session_id={sid} "
            "description='tracks payment earnings'",
            index,
            proj,
        )
    )
    index = GraphIndex.load_from_disk(proj)
    results = suggest_related(index, "payment ledger tracking")
    assert len(results) >= 1


def test_protocol_guide_lists_wave16a09_actions() -> None:
    actions = PROTOCOL_GUIDE.get("actions", {})
    keys = " ".join(actions.keys())
    assert "template:" in keys
    assert "explore:" in keys
    assert "suggest:" in keys
    assert any("batch" in k for k in actions)


def test_parse_batch_edge_tilde() -> None:
    p = parse_batch_line("edge~: A --relates_to--> B to=depends_on")
    assert p["kind"] == "edge_ret_type"
    assert p["new_edge_type"] == "depends_on"


def test_parse_batch_edge_star() -> None:
    p = parse_batch_line("edge*: Hub --implements--> A, B, C")
    assert p["kind"] == "edge_replace_all"
    assert p["targets"] == ["A", "B", "C"]


def test_parse_batch_delete() -> None:
    p = parse_batch_line("delete: node.meta.12345678")
    assert p["kind"] == "delete"
    assert p["node_id"] == "node.meta.12345678"


def test_batch_merge_nodes(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r0 = asyncio.run(dispatch(f"create:Node name='KeepNode' session_id={sid}", index, proj))
    r1 = asyncio.run(dispatch(f"create:Node name='AbsorbNode' session_id={sid}", index, proj))
    assert r0.get("ok") and r1.get("ok")
    keep = str(r0["node_id"])
    absorb = str(r1["node_id"])
    index = GraphIndex.load_from_disk(proj)
    ops = f"merge: keep={keep} absorb={absorb}"
    r = asyncio.run(dispatch(f"batch session_id='{sid}' ops='{ops}'", index, proj))
    assert r["ok"]
    index = GraphIndex.load_from_disk(proj)
    assert index.get_node(keep) is not None
    assert index.get_node(absorb) is None


def test_suggest_related_excludes_document(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    out = suggest_related(index, "document ledger payment", exclude_types=["Session", "Document"])
    assert all(x["type"] not in ("Session", "Document") for x in out)
