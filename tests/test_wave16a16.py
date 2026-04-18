"""Tests for Wave 16A16: pytest config, MCP hooks."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.hooks import before_write, on_error


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    init_project(tmp_path)
    return tmp_path


def _sid(proj: Path) -> str:
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("session:start actor='t' goal='t'", index, proj))
    return str(r["session_id"])


def test_slow_marker_registered() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "slow" in text
    assert "[tool.pytest.ini_options]" in text


def test_xdist_installed() -> None:
    assert importlib.util.find_spec("xdist") is not None


def test_before_write_blocks_unknown_type(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    out = before_write(
        "create",
        {"type": "TotallyUnknownTypeXYZ", "session_id": "sess1"},
        index,
    )
    assert out is not None
    assert out.get("ok") is False
    assert "Unknown node type" in (out.get("error") or "")
    assert "suggestion" in out


def test_before_write_blocks_missing_session(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    out = before_write("create", {"type": "Engine"}, index)
    assert out is not None
    assert out.get("ok") is False
    assert "session" in (out.get("error") or "").lower()


def test_before_write_passes_valid_create(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    assert before_write("create", {"type": "Engine", "session_id": "s"}, index) is None


def test_on_error_suggests_similar_node(proj: Path) -> None:
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    created = asyncio.run(
        dispatch(f"create:Engine name='LedgerAlpha' session_id={sid}", index, proj)
    )
    assert created.get("ok")
    index = GraphIndex.load_from_disk(proj)
    r = on_error(
        "get",
        "node not found: Ledger",
        {"name": "Ledger"},
        index,
    )
    assert r.get("ok") is False
    assert "suggestion" in r
    assert "LedgerAlpha" in (r.get("suggestion") or "")


def test_on_error_suggests_valid_types(proj: Path) -> None:
    index = GraphIndex.load_from_disk(proj)
    r = on_error("create", "unknown type invalidthing", {}, index)
    assert r.get("ok") is False
    assert "suggestion" in r
    assert "Valid types" in (r.get("suggestion") or "")
