"""Wave 17A05 — batch parser named params, multiline quotes, auto id, TYPE_DEFAULTS, viewer v2."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.batch_parser import parse_batch, parse_batch_line, parse_batch_ops
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.tools import write as tools_write
from gobp.viewer.detail_panel import (
    render_errorcase_panel,
    render_invariant_panel,
    render_standard_panel,
)


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    init_project(tmp_path)
    return tmp_path


def _sid(proj: Path) -> str:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("session:start actor='w17a05' goal='t'", index, proj))
    return str(r["session_id"])


# --- Bug fixes (batch) ---------------------------------------------------------


def test_batch_named_params_double_quote() -> None:
    p = parse_batch_line(
        'create: Decision: Name | what="CTO manages" why="Thin harness"'
    )
    assert p.get("kind") == "create"
    assert p.get("what") == "CTO manages"
    assert p.get("why") == "Thin harness"


def test_batch_named_params_single_quote() -> None:
    p = parse_batch_line("create: Invariant: R | rule='x' scope='class'")
    assert p["name"] == "R"
    assert p.get("rule") == "x"
    assert p.get("scope") == "class"


def test_batch_named_params_with_plain_desc() -> None:
    p = parse_batch_line(
        'create: Decision: D | plain text first what="a" why="b"'
    )
    assert p.get("description") == "plain text first"
    assert p.get("what") == "a"


def test_batch_no_split_on_newline_in_quoted() -> None:
    raw = 'create: ErrorDomain: GPS | fix_guide="line1\nline2"\ncreate: Node: After | x'
    ops, errs = parse_batch_ops(raw)
    assert not errs
    assert len(ops) == 2
    assert "line1" in ops[0].get("fix_guide", "")
    assert ops[1].get("name") == "After"


def test_batch_decision_what_why_parsed() -> None:
    ops = parse_batch(
        'create: Decision: X | short what="w" why="y"'
    )
    assert len(ops) == 1
    assert ops[0]["what"] == "w"
    assert ops[0]["why"] == "y"


# --- Bug fixes (write path) --------------------------------------------------


def test_create_auto_id_from_name_group(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(
        dispatch(
            f"batch session_id='{sid}' ops='create: Engine: BalanceEngine | minimal'",
            index,
            proj,
        )
    )
    assert r.get("ok"), r
    fresh = GraphIndex.load_from_disk(proj)
    found = [n for n in fresh.all_nodes() if n.get("name") == "BalanceEngine"]
    assert found and found[0].get("id")


def test_create_id_preserved_if_set(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    explicit = "fixed_node.testpreserve.12345678"
    ops = f"create: Engine: FixedEngine | hello id={explicit}"
    r = asyncio.run(
        dispatch(
            f"batch session_id='{sid}' ops={repr(ops)}",
            index,
            proj,
        )
    )
    assert r.get("ok"), r
    fresh = GraphIndex.load_from_disk(proj)
    assert fresh.get_node(explicit)


def test_concept_definition_from_pipe(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(
        dispatch(
            f"batch session_id='{sid}' ops="
            f"'create: Concept: Proof of Presence | GPS + device signal = proof'",
            index,
            proj,
        )
    )
    assert r.get("ok"), r
    fresh = GraphIndex.load_from_disk(proj)
    c = next((n for n in fresh.all_nodes() if n.get("name") == "Proof of Presence"), None)
    assert c is not None
    assert str(c.get("definition", "")).strip()


def test_errordomain_fix_guide_from_pipe(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(
        dispatch(
            f"batch session_id='{sid}' ops="
            f"'create: ErrorDomain: GPS | See this guide fix_guide=\"check antenna\"'",
            index,
            proj,
        )
    )
    assert r.get("ok"), r
    fresh = GraphIndex.load_from_disk(proj)
    d = next((n for n in fresh.all_nodes() if n.get("name") == "GPS"), None)
    assert d is not None
    assert str(d.get("fix_guide", "")).strip()


# --- Viewer panel (Python reference HTML) ------------------------------------


def test_render_standard_panel_has_breadcrumb() -> None:
    html = render_standard_panel(
        {"type": "Engine", "name": "TrustGate", "group": "Dev > Infrastructure > Engine"}
    )
    assert "Dev" in html and "Infrastructure" in html


def test_render_standard_panel_no_status_priority() -> None:
    html = render_standard_panel({"type": "X", "name": "N", "group": "G"})
    assert "STATUS" not in html.upper()
    assert "PRIORITY" not in html.upper()


def test_render_standard_panel_lifecycle_read_order() -> None:
    html = render_standard_panel(
        {
            "type": "Engine",
            "name": "E",
            "group": "Dev",
            "lifecycle": "specified",
            "read_order": "foundational",
        }
    )
    assert "lifecycle" in html.lower()
    assert "read_order" in html.lower()


def test_render_errorcase_panel_has_code_section() -> None:
    html = render_errorcase_panel(
        {
            "name": "GPS lost",
            "code": "GPS_E_001",
            "severity": "error",
            "trigger": "t",
            "handling": "h",
            "user_message": "u",
            "dev_note": "d",
            "context": {"domains": ["gps"]},
        }
    )
    assert "GPS_E_001" in html


def test_render_errorcase_panel_has_fix_history() -> None:
    html = render_errorcase_panel(
        {"name": "X", "code": "C", "severity": "warn", "fix_history": [{"when": "2026"}]}
    )
    assert "FIX HISTORY" in html


def test_render_invariant_panel_has_rule() -> None:
    html = render_invariant_panel({"name": "I", "rule": "always validate", "scope": "class"})
    assert "always validate" in html

