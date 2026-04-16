"""Wave 9A+ performance benchmarks (v2).

Use this module instead of tests/test_performance.py for ongoing perf checks.
Targets are read from docs/MCP_TOOLS.md §10 max latency values.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Callable

import pytest

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import read as tools_read
from gobp.mcp.tools import write as tools_write
from gobp.mcp.tools.advanced import lessons_extract
from tests.fixtures.mihos_fixture import _populate_mihos_project

# Max latency targets (ms) aligned with docs/MCP_TOOLS.md §10.
MAX_MS = {
    "gobp_overview": 150.0,
    "find": 50.0,
    "signature": 30.0,
    "context": 100.0,
    "session_recent": 50.0,
    "decisions_for": 50.0,
    "doc_sections": 30.0,
    "node_upsert": 700.0,
    "decision_lock": 200.0,
    "session_log": 500.0,
    "lessons_extract": 2000.0,
    "validate": 5000.0,
}


@pytest.fixture(scope="module")
def mihos_perf_root_v2(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create one MIHOS-scale project for perf tests in this module."""
    root = tmp_path_factory.mktemp("mihos_w9perf_v2")
    _populate_mihos_project(root)
    return root


def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0


def _load(root: Path) -> GraphIndex:
    return GraphIndex.load_from_disk(root)


def _assert_under_target(name: str, elapsed_ms: float) -> None:
    assert elapsed_ms < MAX_MS[name], (
        f"{name}: {elapsed_ms:.1f}ms > {MAX_MS[name]:.1f}ms"
    )


def _measure_median(call_fn: Callable[[], Any], runs: int = 3) -> float:
    """Run call_fn N times, return median latency in ms."""
    times: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        call_fn()
        times.append((time.perf_counter() - start) * 1000.0)
    times.sort()
    return times[len(times) // 2]


@pytest.mark.parametrize(
    ("name", "call_fn"),
    [
        ("gobp_overview", lambda i, r: tools_read.gobp_overview(i, r, {})),
        ("find", lambda i, r: tools_read.find(i, r, {"query": "login"})),
        (
            "signature",
            lambda i, r: tools_read.signature(i, r, {"node_id": "node:feat_login"}),
        ),
        ("context", lambda i, r: tools_read.context(i, r, {"node_id": "node:feat_login"})),
        ("session_recent", lambda i, r: tools_read.session_recent(i, r, {"n": 3})),
        (
            "decisions_for",
            lambda i, r: tools_read.decisions_for(i, r, {"topic": "auth:login.method"}),
        ),
        ("doc_sections", lambda i, r: tools_read.doc_sections(i, r, {"doc_id": "doc:DOC-07"})),
    ],
)
def test_perf_read_tools_v2(
    mihos_perf_root_v2: Path,
    name: str,
    call_fn: Callable[[GraphIndex, Path], dict[str, Any]],
) -> None:
    """Read tools must stay under documented max latency."""
    index = _load(mihos_perf_root_v2)
    start = time.perf_counter()
    result = call_fn(index, mihos_perf_root_v2)
    elapsed = _ms(start)
    assert result.get("ok") is True
    _assert_under_target(name, elapsed)


def test_perf_session_log_start_v2(mihos_perf_root_v2: Path) -> None:
    """session_log(start) should stay under max latency."""
    index = _load(mihos_perf_root_v2)
    start = time.perf_counter()
    result = tools_write.session_log(
        index,
        mihos_perf_root_v2,
        {"action": "start", "actor": "perf-test-v2", "goal": "session start benchmark"},
    )
    elapsed = _ms(start)
    assert result.get("ok") is True
    _assert_under_target("session_log", elapsed)


def test_perf_node_upsert_v2(mihos_perf_root_v2: Path) -> None:
    """node_upsert should stay under max latency (median of 3 runs)."""
    index = _load(mihos_perf_root_v2)
    sess = tools_write.session_log(
        index,
        mihos_perf_root_v2,
        {"action": "start", "actor": "perf-test-v2", "goal": "node_upsert benchmark"},
    )
    assert sess.get("ok") is True

    index = _load(mihos_perf_root_v2)
    session_id = str(sess["session_id"])

    def do_upsert() -> dict[str, Any]:
        return tools_write.node_upsert(
            index,
            mihos_perf_root_v2,
            {
                "type": "Idea",
                "name": "Performance v2 idea",
                "fields": {
                    "subject": "perf:v2",
                    "raw_quote": "perf test",
                    "interpretation": "v2 performance benchmark node",
                    "maturity": "RAW",
                    "confidence": "low",
                },
                "session_id": session_id,
            },
        )

    result = do_upsert()
    assert result.get("ok") is True
    elapsed = _measure_median(do_upsert, runs=3)
    _assert_under_target("node_upsert", elapsed)


def test_perf_lessons_extract_v2(mihos_perf_root_v2: Path) -> None:
    """lessons_extract should stay under the conservative max latency."""
    index = _load(mihos_perf_root_v2)
    start = time.perf_counter()
    result = asyncio.run(lessons_extract(index, mihos_perf_root_v2, {}))
    elapsed = _ms(start)
    assert result.get("ok") is True
    _assert_under_target("lessons_extract", elapsed)
