"""Tests for gobp/mcp/dispatcher.py - parse_query and dispatch routing."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import PROTOCOL_GUIDE, dispatch, parse_query


# -- parse_query tests ---------------------------------------------------------

def test_parse_overview():
    action, ntype, params = parse_query("overview:")
    assert action == "overview"
    assert ntype == ""
    assert params == {}


def test_parse_overview_empty():
    action, ntype, params = parse_query("")
    assert action == "overview"


def test_parse_find_bare():
    action, ntype, params = parse_query("find: login")
    assert action == "find"
    assert ntype == ""
    assert params["query"] == "login"


def test_parse_find_with_type():
    action, ntype, params = parse_query("find:Decision auth")
    assert action == "find"
    assert ntype == "Decision"
    assert params["query"] == "auth"


def test_parse_get():
    action, ntype, params = parse_query("get: node:feat_login")
    assert action == "get"
    assert params["query"] == "node:feat_login"


def test_parse_create_with_kv():
    action, ntype, params = parse_query("create:Idea name='use OTP' subject='auth:login'")
    assert action == "create"
    assert ntype == "Idea"
    assert params["name"] == "use OTP"
    assert params["subject"] == "auth:login"


def test_parse_lock():
    action, ntype, params = parse_query(
        "lock:Decision topic='auth:login' what='use OTP' why='SMS unreliable'"
    )
    assert action == "lock"
    assert ntype == "Decision"
    assert params["topic"] == "auth:login"
    assert params["what"] == "use OTP"
    assert params["why"] == "SMS unreliable"


def test_parse_session_start():
    action, ntype, params = parse_query("session:start actor='cursor' goal='implement login'")
    assert action == "session"
    assert params.get("query") == "start" or ntype == "start"


def test_parse_validate():
    action, ntype, params = parse_query("validate: nodes")
    assert action == "validate"
    assert params.get("query") == "nodes"


def test_parse_no_colon_fallback():
    action, ntype, params = parse_query("login feature")
    assert action == "find"
    assert "login feature" in str(params)


def test_protocol_guide_has_required_keys():
    assert "protocol" in PROTOCOL_GUIDE
    assert "format" in PROTOCOL_GUIDE
    assert "actions" in PROTOCOL_GUIDE
    assert "tip" in PROTOCOL_GUIDE
    assert len(PROTOCOL_GUIDE["actions"]) >= 10


# -- dispatch routing tests ----------------------------------------------------

@pytest.fixture
def disp_root(gobp_root: Path) -> Path:
    """GoBP root with init data for dispatch tests."""
    init_project(gobp_root, force=True)
    return gobp_root


def test_dispatch_overview(disp_root: Path):
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("overview:", index, disp_root))
    assert result["ok"] is True
    assert "stats" in result
    assert "_dispatch" in result
    assert result["_dispatch"]["action"] == "overview"


def test_dispatch_find(disp_root: Path):
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("find: unit", index, disp_root))
    assert result["ok"] is True
    assert "matches" in result
    assert result["_dispatch"]["action"] == "find"


def test_dispatch_find_with_type(disp_root: Path):
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("find:TestKind unit", index, disp_root))
    assert result["ok"] is True
    for match in result.get("matches", []):
        assert match["type"] == "TestKind"


def test_dispatch_overview_has_interface(disp_root: Path):
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("overview:", index, disp_root))
    assert "interface" in result
    assert result["interface"]["protocol"] == "gobp query protocol v1"


def test_dispatch_unknown_action_fallback(disp_root: Path):
    """Unknown action falls back to find()."""
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("unknown: test", index, disp_root))
    # Should not crash - either find result or error with hint
    assert "ok" in result


def test_dispatch_includes_dispatch_info(disp_root: Path):
    """Every dispatch result includes _dispatch audit info."""
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("find: login", index, disp_root))
    assert "_dispatch" in result
    assert "action" in result["_dispatch"]
    assert "params" in result["_dispatch"]


def test_dispatch_validate(disp_root: Path):
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("validate: nodes", index, disp_root))
    assert "ok" in result
    assert result["_dispatch"]["action"] == "validate"


def test_dispatch_session_start(disp_root: Path):
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(
        dispatch("session:start actor='test' goal='dispatcher test'", index, disp_root)
    )
    assert result["ok"] is True
    assert "session_id" in result
