"""Tests for Wave 16A13: batch newlines, auto-fill, quick capture, chunking."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.batch_parser import parse_batch, parse_batch_ops, parse_quick
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.parser import PROTOCOL_GUIDE
from gobp.mcp.tools.write import TYPE_DEFAULTS, _auto_fill_defaults


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    init_project(tmp_path)
    return tmp_path


def _sid(proj: Path) -> str:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("session:start actor='t' goal='t'", index, proj))
    return str(r["session_id"])


# --- Batch newline parsing ----------------------------------------------------


def test_batch_parse_literal_newline() -> None:
    ops = parse_batch("create: Engine: A | Desc A\\ncreate: Engine: B | Desc B")
    assert len(ops) == 2
    assert ops[0]["name"] == "A"
    assert ops[1]["name"] == "B"


def test_batch_parse_real_newline() -> None:
    ops = parse_batch("create: Engine: A | Desc A\ncreate: Engine: B | Desc B")
    assert len(ops) == 2


def test_batch_parse_double_escaped() -> None:
    raw = "create: Node: X | a\\\\ncreate: Node: Y | b"
    ops, errs = parse_batch_ops(raw)
    assert not errs
    assert len(ops) >= 2


def test_parse_batch_raises_on_any_bad_line() -> None:
    """parse_batch is strict: any invalid line must not return partial ops."""
    bad = "create: Engine: OK | fine\nnot_a_valid_op_prefix: x"
    with pytest.raises(ValueError, match="batch parse failed"):
        parse_batch(bad)


# --- Auto-fill ----------------------------------------------------------------


def test_idea_auto_fill_defaults(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(
        dispatch(
            f"batch session_id='{sid}' ops='create: Idea: QuickIdea | only desc here'",
            index,
            proj,
        )
    )
    assert r.get("ok")
    assert r.get("succeeded", 0) >= 1
    fresh = GraphIndex.load_from_disk(proj)
    found = [n for n in fresh.all_nodes() if n.get("name") == "QuickIdea"]
    assert found
    assert found[0].get("maturity") == "RAW"


def test_auto_fill_testcase_placeholders() -> None:
    node: dict = {
        "id": "tc:test",
        "type": "TestCase",
        "name": "T",
        "kind_id": "tk:x",
        "covers": "node:y",
        "status": "DRAFT",
        "priority": "low",
        "created": "2026-01-01T00:00:00",
        "updated": "2026-01-01T00:00:00",
    }
    _auto_fill_defaults(node, "TestCase")
    assert node.get("given") == "TBD"


def test_node_no_extra_fill(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(
        dispatch(
            f"batch session_id='{sid}' ops='create: Engine: Plain | hi'",
            index,
            proj,
        )
    )
    assert r.get("ok")


# --- Quick capture ------------------------------------------------------------


def test_quick_parse_4_fields() -> None:
    ops = parse_quick("Inverted Index | performance | wave17 | O(1) find")
    assert len(ops) == 1
    assert ops[0]["name"] == "Inverted Index"
    assert ops[0].get("category") == "performance"
    assert ops[0].get("target_wave") == "wave17"


def test_quick_parse_2_fields() -> None:
    ops = parse_quick("OnlyName | short desc")
    assert len(ops) == 1
    assert ops[0]["description"] == "short desc"


def test_quick_parse_3_fields() -> None:
    ops = parse_quick("N | cat | rest desc here")
    assert ops[0].get("category") == "cat"
    assert "rest desc" in ops[0].get("description", "")


def test_quick_action_creates_nodes(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(
        dispatch(
            f"quick: session_id='{sid}' ops='QOne | a | w1 | d1\\nQTwo | b | w2 | d2'",
            index,
            proj,
        )
    )
    assert r.get("ok")
    assert r.get("succeeded", 0) >= 2


# --- Chunking -----------------------------------------------------------------


@pytest.mark.slow
def test_batch_no_limit_300_ops(proj: Path) -> None:
    sid = _sid(proj)
    lines = "\n".join([f"create: Node: B{i} | x" for i in range(300)])
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch(f"batch session_id='{sid}' ops='{lines}'", index, proj))
    assert r.get("ok")
    assert r.get("succeeded", 0) >= 280


@pytest.mark.slow
def test_batch_no_limit_600_ops(proj: Path) -> None:
    sid = _sid(proj)
    lines = "\n".join([f"create: Node: C{i} | x" for i in range(600)])
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch(f"batch session_id='{sid}' ops='{lines}'", index, proj))
    assert r.get("ok")
    assert r.get("succeeded", 0) >= 550


def test_type_defaults_map_has_idea() -> None:
    assert "Idea" in TYPE_DEFAULTS


# --- Integration --------------------------------------------------------------


def test_quick_then_find(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(
        dispatch(
            f"quick: session_id='{sid}' ops='FindMeUnique | x | w | y'",
            index,
            proj,
        )
    )
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("find: FindMeUnique mode=summary", index, proj))
    assert r.get("ok")


def test_batch_newline_then_edges(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    ops = (
        "create: Engine: Ea | a\\n"
        "create: Engine: Eb | b\\n"
        "edge+: Ea --relates_to--> Eb"
    )
    r = asyncio.run(dispatch(f"batch session_id='{sid}' ops='{ops}'", index, proj))
    assert r.get("ok")
    assert r.get("succeeded", 0) >= 2


# --- PROTOCOL_GUIDE -----------------------------------------------------------


def test_protocol_guide_batch_no_fixed_max_ops() -> None:
    actions = PROTOCOL_GUIDE.get("actions", {})
    batch_line = str(
        actions.get(
            "batch session_id='x' ops='create: Engine: A | desc\\nedge+: Hub --implements--> B, C'",
            "",
        )
    ).lower()
    assert "chunk" in batch_line
    assert "max 500" not in batch_line
