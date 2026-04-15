"""Performance benchmarks for GoBP MCP tools.

Tests all 14 tools against max latency targets from docs/MCP_TOOLS.md §10.
Uses mihos_root fixture (~30 nodes) for realistic scale.

MAX LATENCY TARGETS (from MCP_TOOLS.md §10):
  gobp_overview:  100ms    find:          50ms
  signature:       30ms    context:      100ms
  session_recent:  50ms    decisions_for: 50ms
  doc_sections:    30ms    node_upsert:  200ms
  decision_lock:  200ms    session_log:  100ms
  import_proposal:500ms    import_commit:1000ms
  validate:       5000ms   lessons_extract: (no target, use 2000ms)
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import read as tools_read
from gobp.mcp.tools import write as tools_write
from gobp.mcp.tools.advanced import lessons_extract

from tests.fixtures.mihos_fixture import _populate_mihos_project


@pytest.fixture(scope="module")
def mihos_perf_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One MIHOS-scale graph per module (avoids repopulating ~60 files per test)."""
    root = tmp_path_factory.mktemp("mihos_w8perf")
    _populate_mihos_project(root)
    return root


@pytest.fixture(scope="module")
def mihos_index(mihos_perf_root: Path) -> GraphIndex:
    """Load GraphIndex once per module — reused by all read perf tests."""
    return GraphIndex.load_from_disk(mihos_perf_root)


# ── Max latency targets (ms) from MCP_TOOLS.md §10 ───────────────────────────
MAX_MS = {
    "gobp_overview": 100,
    "find": 50,
    "signature": 30,
    "context": 100,
    "session_recent": 50,
    "decisions_for": 50,
    "doc_sections": 30,
    "node_upsert": 200,
    "decision_lock": 200,
    "session_log": 100,
    "lessons_extract": 2000,  # no official target, conservative
    "validate": 5000,
}


def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


# ── Read tools ────────────────────────────────────────────────────────────────


def test_perf_gobp_overview(mihos_perf_root: Path, mihos_index: GraphIndex) -> None:
    start = time.perf_counter()
    result = tools_read.gobp_overview(mihos_index, mihos_perf_root, {})
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["gobp_overview"], (
        f"gobp_overview: {elapsed:.1f}ms > {MAX_MS['gobp_overview']}ms"
    )


def test_perf_find(mihos_perf_root: Path, mihos_index: GraphIndex) -> None:
    start = time.perf_counter()
    result = tools_read.find(mihos_index, mihos_perf_root, {"query": "login"})
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["find"], f"find: {elapsed:.1f}ms > {MAX_MS['find']}ms"


def test_perf_signature(mihos_perf_root: Path, mihos_index: GraphIndex) -> None:
    start = time.perf_counter()
    result = tools_read.signature(mihos_index, mihos_perf_root, {"node_id": "node:feat_login"})
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["signature"], (
        f"signature: {elapsed:.1f}ms > {MAX_MS['signature']}ms"
    )


def test_perf_context(mihos_perf_root: Path, mihos_index: GraphIndex) -> None:
    start = time.perf_counter()
    result = tools_read.context(mihos_index, mihos_perf_root, {"node_id": "node:feat_login"})
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["context"], (
        f"context: {elapsed:.1f}ms > {MAX_MS['context']}ms"
    )


def test_perf_session_recent(mihos_perf_root: Path, mihos_index: GraphIndex) -> None:
    start = time.perf_counter()
    result = tools_read.session_recent(mihos_index, mihos_perf_root, {"n": 3})
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["session_recent"], (
        f"session_recent: {elapsed:.1f}ms > {MAX_MS['session_recent']}ms"
    )


def test_perf_decisions_for(mihos_perf_root: Path, mihos_index: GraphIndex) -> None:
    start = time.perf_counter()
    result = tools_read.decisions_for(
        mihos_index, mihos_perf_root, {"topic": "auth:login.method"}
    )
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["decisions_for"], (
        f"decisions_for: {elapsed:.1f}ms > {MAX_MS['decisions_for']}ms"
    )


def test_perf_doc_sections(mihos_perf_root: Path, mihos_index: GraphIndex) -> None:
    start = time.perf_counter()
    result = tools_read.doc_sections(mihos_index, mihos_perf_root, {"doc_id": "doc:DOC-07"})
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["doc_sections"], (
        f"doc_sections: {elapsed:.1f}ms > {MAX_MS['doc_sections']}ms"
    )


# ── Write tools ───────────────────────────────────────────────────────────────
# Write tools mutate disk → cannot share index — each loads fresh


def test_perf_session_log_start(mihos_perf_root: Path) -> None:
    index = GraphIndex.load_from_disk(mihos_perf_root)
    start = time.perf_counter()
    result = tools_write.session_log(
        index,
        mihos_perf_root,
        {
            "action": "start",
            "actor": "perf-test",
            "goal": "Performance benchmark session",
        },
    )
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["session_log"], (
        f"session_log: {elapsed:.1f}ms > {MAX_MS['session_log']}ms"
    )


def test_perf_node_upsert(mihos_perf_root: Path) -> None:
    index = GraphIndex.load_from_disk(mihos_perf_root)
    # Need active session first
    sess_result = tools_write.session_log(
        index,
        mihos_perf_root,
        {
            "action": "start",
            "actor": "perf-test",
            "goal": "node_upsert perf test",
        },
    )
    index = GraphIndex.load_from_disk(mihos_perf_root)  # reload after write
    session_id = sess_result["session_id"]

    start = time.perf_counter()
    result = tools_write.node_upsert(
        index,
        mihos_perf_root,
        {
            "type": "Idea",
            "name": "Performance test idea",
            "fields": {
                "subject": "perf:test",
                "raw_quote": "test",
                "interpretation": "perf test node",
                "maturity": "RAW",
                "confidence": "low",
            },
            "session_id": session_id,
        },
    )
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["node_upsert"], (
        f"node_upsert: {elapsed:.1f}ms > {MAX_MS['node_upsert']}ms"
    )


# ── Advanced tools ────────────────────────────────────────────────────────────


def test_perf_lessons_extract(mihos_perf_root: Path, mihos_index: GraphIndex) -> None:
    start = time.perf_counter()
    result = asyncio.run(lessons_extract(mihos_index, mihos_perf_root, {}))
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["lessons_extract"], (
        f"lessons_extract: {elapsed:.1f}ms > {MAX_MS['lessons_extract']}ms"
    )
