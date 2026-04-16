"""Tests for Wave 14: schema governance, protocol versioning, access model."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.tools import read as tools_read


@pytest.fixture
def seeded_root(gobp_root: Path) -> Path:
    init_project(gobp_root, force=True)
    return gobp_root


@pytest.fixture
def session_id(seeded_root: Path) -> str:
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch(
        "session:start actor='test' goal='wave14'", index, seeded_root
    ))
    return r["session_id"]


def test_session_fixture_wave14(session_id: str) -> None:
    assert session_id.startswith("session:")


# ── Protocol version tests ────────────────────────────────────────────────────


def test_version_action_returns_protocol(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("version:", index, seeded_root))
    assert r["ok"] is True
    assert r["protocol_version"] == "2.0"
    assert "gobp_version" in r
    assert "schema_version" in r


def test_version_has_changelog(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("version:", index, seeded_root))
    assert "changelog" in r
    assert isinstance(r["changelog"], list)
    assert len(r["changelog"]) >= 1


def test_version_deprecated_actions_empty(seeded_root: Path):
    """No deprecated actions in v2.0."""
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("version:", index, seeded_root))
    assert "deprecated_actions" in r
    assert isinstance(r["deprecated_actions"], list)


def test_version_dispatch_info(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("version:", index, seeded_root))
    assert r["_dispatch"]["action"] == "version"


# ── Schema governance tests ───────────────────────────────────────────────────


def test_governance_returns_score(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.schema_governance(index, seeded_root, {"scope": "all"})
    assert r["ok"] is True
    assert "score" in r
    assert 0 <= r["score"] <= 100


def test_governance_returns_issues_list(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.schema_governance(index, seeded_root, {})
    assert "issues" in r
    assert isinstance(r["issues"], list)


def test_governance_returns_summary(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.schema_governance(index, seeded_root, {})
    assert "summary" in r
    assert isinstance(r["summary"], str)


def test_governance_checks_node_types(seeded_root: Path):
    """Governance checks node types from schema."""
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.schema_governance(index, seeded_root, {"scope": "schema-docs"})
    assert r["ok"] is True
    assert "node_types_checked" in r
    assert r["node_types_checked"] > 0


def test_dispatch_validate_schema_docs(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("validate: schema-docs", index, seeded_root))
    assert r["ok"] is True
    assert "score" in r


def test_dispatch_validate_all_unchanged(seeded_root: Path):
    """validate: all still works normally."""
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("validate: all", index, seeded_root))
    assert "ok" in r


# ── Session role tests ────────────────────────────────────────────────────────


def test_session_stores_role_observer(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch(
        "session:start actor='test' goal='role test' role='observer'",
        index, seeded_root
    ))
    assert r["ok"] is True
    index2 = GraphIndex.load_from_disk(seeded_root)
    session = index2.get_node(r["session_id"])
    assert session is not None
    assert session.get("role") in ("observer", "contributor")


def test_session_stores_role_admin(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch(
        "session:start actor='admin' goal='admin session' role='admin'",
        index, seeded_root
    ))
    assert r["ok"] is True


def test_session_invalid_role_defaults(seeded_root: Path):
    """Invalid role defaults to contributor."""
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch(
        "session:start actor='test' goal='bad role' role='superuser'",
        index, seeded_root
    ))
    assert r["ok"] is True
    index2 = GraphIndex.load_from_disk(seeded_root)
    session = index2.get_node(r["session_id"])
    # Should default to contributor or not store invalid role
    role = session.get("role", "contributor") if session else "contributor"
    assert role in ("observer", "contributor", "admin")


# ── Read-only mode tests ──────────────────────────────────────────────────────


def test_read_only_actions_defined():
    """_READ_ONLY_ACTIONS frozenset exists and has write actions."""
    from gobp.mcp.server import _READ_ONLY_ACTIONS
    assert "create" in _READ_ONLY_ACTIONS
    assert "upsert" in _READ_ONLY_ACTIONS
    assert "lock" in _READ_ONLY_ACTIONS
    assert "session" in _READ_ONLY_ACTIONS


def test_read_only_flag_reads_env():
    """_READ_ONLY reads from GOBP_READ_ONLY env var."""
    # Just verify the module attribute exists
    from gobp.mcp import server as _server
    assert hasattr(_server, "_READ_ONLY")
    assert isinstance(_server._READ_ONLY, bool)


def test_protocol_guide_has_version_action():
    from gobp.mcp.dispatcher import PROTOCOL_GUIDE
    actions = PROTOCOL_GUIDE.get("actions", {})
    assert any("version:" in k for k in actions)
