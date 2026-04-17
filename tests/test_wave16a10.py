"""Tests for Wave 16A10: smart template, compact, query rules."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.parser import PROTOCOL_GUIDE


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    init_project(tmp_path)
    return tmp_path


def _sid(proj: Path) -> str:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("session:start actor='t' goal='t'", index, proj))
    return str(r["session_id"])


# --- template + edges ---------------------------------------------------------


def test_template_has_suggested_edges(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template: Engine", index, proj))
    assert r["ok"]
    se = r.get("suggested_edges", [])
    assert isinstance(se, list)
    assert len(se) >= 1


def test_template_edges_from_schema(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template: Engine", index, proj))
    assert r["ok"]
    types_out = {e["type"] for e in r["suggested_edges"] if e.get("direction") == "outgoing"}
    assert "depends_on" in types_out or "implements" in types_out


def test_template_batch_example_has_edge_lines(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template: Flow", index, proj))
    assert r["ok"]
    ex = r.get("batch_example", "")
    assert "create:" in ex
    assert "edge+:" in ex


# --- template_batch -----------------------------------------------------------


def test_template_batch_returns_blocks(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template_batch: Engine count=3", index, proj))
    assert r["ok"]
    bt = r.get("batch_template", "")
    assert "{name_1}" in bt and "{name_2}" in bt and "{name_3}" in bt


def test_template_batch_custom_count(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template_batch: Engine count=5", index, proj))
    assert r["ok"]
    assert r.get("count") == 5
    bt = r.get("batch_template", "")
    assert bt.count("create:") == 5


def test_template_batch_has_instructions(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template_batch: Flow", index, proj))
    assert r["ok"]
    instr = r.get("instructions", [])
    assert isinstance(instr, list)
    assert any("batch" in str(s).lower() for s in instr)


# --- compact ------------------------------------------------------------------


def test_explore_compact_returns_strings(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(
        dispatch(f"create:Engine name='EngCompact' session_id={sid} description='d'", index, proj)
    )
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("explore: EngCompact compact=true", index, proj))
    assert r["ok"]
    assert isinstance(r.get("edges"), list)
    assert all(isinstance(x, str) for x in r["edges"])


def test_explore_compact_smaller_than_full(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(
        dispatch(f"create:Engine name='EngSize' session_id={sid} description='long desc'", index, proj)
    )
    index = GraphIndex.load_from_disk(proj)
    full_r = asyncio.run(dispatch("explore: EngSize", index, proj))
    index = GraphIndex.load_from_disk(proj)
    compact_r = asyncio.run(dispatch("explore: EngSize compact=true", index, proj))
    assert full_r["ok"] and compact_r["ok"]
    assert len(str(compact_r)) < len(str(full_r))


def test_find_compact_minimal_fields(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(
        dispatch(f"create:Engine name='FindCmp' session_id={sid} description='d'", index, proj)
    )
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("find: FindCmp compact=true", index, proj))
    assert r["ok"]
    assert r["matches"]
    m0 = r["matches"][0]
    assert set(m0.keys()) == {"id", "name", "type"}


def test_get_compact_minimal_fields(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(
        dispatch(f"create:Engine name='GetCmp' session_id={sid} description='d'", index, proj)
    )
    index = GraphIndex.load_from_disk(proj)
    fr = asyncio.run(dispatch("find: GetCmp mode=summary", index, proj))
    nid = fr["matches"][0]["id"]
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch(f"get: {nid} compact=true", index, proj))
    assert r["ok"]
    assert set(r["node"].keys()) == {"id", "name", "type"}
    assert "edge_count" in r


# --- query rules --------------------------------------------------------------


def test_protocol_guide_has_query_rules() -> None:
    rules = PROTOCOL_GUIDE.get("query_rules")
    assert isinstance(rules, list)
    assert len(rules) >= 10


def test_protocol_guide_has_token_guide() -> None:
    tg = PROTOCOL_GUIDE.get("token_guide")
    assert isinstance(tg, dict)
    assert "batch response" in tg


# --- integration --------------------------------------------------------------


def test_template_then_batch_create(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template: Engine", index, proj))
    assert r["ok"]
    ops = "create: Engine: TmplBatch1 | from template test"
    r2 = asyncio.run(dispatch(f"batch session_id='{sid}' ops='{ops}'", index, proj))
    assert r2["ok"]


def test_template_batch_fill_and_submit(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template_batch: Engine count=2", index, proj))
    assert r["ok"]
    ops = (
        "create: Engine: TBOne | d1\n"
        "create: Engine: TBTwo | d2"
    )
    r2 = asyncio.run(dispatch(f"batch session_id='{sid}' ops='{ops}'", index, proj))
    assert r2["ok"]
    assert r2.get("succeeded", 0) >= 1
