"""Performance benchmarks for GoBP MCP tools.

Targets are read from docs/MCP_TOOLS.md §10 max latency values.
Uses a MIHOS-scale fixture (~1K nodes) for realistic scale.

Also benchmarks ``async dispatch(query, ...)`` for most gobp() actions
(read paths + dry-run writes + validate + extract). Mutating paths that
would corrupt the shared module fixture (edge, import, dedupe, real commit)
are intentionally omitted here — cover them in integration tests instead.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable

import pytest

from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.tools import read as tools_read
from gobp.mcp.tools import write as tools_write
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
    "node_upsert": 1400.0,  # duplicate check reloads index (Wave 16A07); headroom on slow runners
    "decision_lock": 200.0,
    "session_log": 500.0,
    "lessons_extract": 2000.0,
    "validate": 5000.0,
}

# End-to-end dispatch() ceilings (ms) — includes parse + route + tool; more
# generous than direct tool calls where noted.
DISPATCH_MAX_MS: dict[str, float] = {
    "dispatch_overview": 200.0,
    "dispatch_version": 120.0,
    "dispatch_find": 80.0,
    "dispatch_get_batch": 150.0,
    "dispatch_get": 150.0,
    "dispatch_signature": 80.0,
    "dispatch_recent": 80.0,
    "dispatch_decisions": 80.0,
    "dispatch_sections": 60.0,
    "dispatch_code": 150.0,
    "dispatch_invariants": 150.0,
    "dispatch_tests": 200.0,
    "dispatch_related": 200.0,
    "dispatch_template_flow": 100.0,
    "dispatch_template_all": 150.0,
    "dispatch_interview": 200.0,
    "dispatch_validate_nodes": 3000.0,
    "dispatch_validate_metadata": 2000.0,
    "dispatch_validate_schema_docs": 5000.0,
    "dispatch_validate_schema_tests": 5000.0,
    "dispatch_recompute_dry": 1000.0,
    "dispatch_create_dry": 400.0,
    "dispatch_update_dry": 400.0,
    "dispatch_upsert_dry": 400.0,
    "dispatch_lock_dry": 400.0,
    "dispatch_session_dry": 400.0,
    "dispatch_extract": 2500.0,
    "dispatch_commit_fail_fast": 600.0,
}


def _prepare_perf_workspace(root: Path) -> None:
    """Copy SCHEMA.md for governance + add tiny import stub (not used in perf)."""
    repo_root = Path(__file__).resolve().parents[1]
    schema_src = repo_root / "docs" / "SCHEMA.md"
    if schema_src.exists():
        dest_dir = root / "docs"
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(schema_src, dest_dir / "SCHEMA.md")
    stub = root / "import_stub.md"
    stub.write_text("# Perf stub\n\nBody for import tests.\n", encoding="utf-8")


@pytest.fixture(scope="module")
def mihos_perf_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create one MIHOS-scale project for perf tests in this module."""
    root = tmp_path_factory.mktemp("mihos_w9perf")
    _populate_mihos_project(root)
    _prepare_perf_workspace(root)
    return root


def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0


def _load(root: Path) -> GraphIndex:
    return GraphIndex.load_from_disk(root)


def _xdist_headroom() -> float:
    """Extra slack for wall-clock ceilings when pytest-xdist shares CPU across workers."""
    return 2.0 if os.environ.get("PYTEST_XDIST_WORKER") else 1.0


def _assert_under_target(name: str, elapsed_ms: float) -> None:
    limit = MAX_MS[name] * _xdist_headroom()
    assert elapsed_ms < limit, (
        f"{name}: {elapsed_ms:.1f}ms > {limit:.1f}ms"
    )


def _assert_dispatch(name: str, elapsed_ms: float) -> None:
    limit = DISPATCH_MAX_MS[name] * _xdist_headroom()
    assert elapsed_ms < limit, f"{name}: {elapsed_ms:.1f}ms > {limit:.1f}ms"


def _measure_median(call_fn: Callable[[], Any], runs: int = 3) -> float:
    """Run call_fn N times, return median latency in ms."""
    times: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        call_fn()
        times.append((time.perf_counter() - start) * 1000.0)
    times.sort()
    return times[len(times) // 2]


# (bench_name, gobp query string, expect_ok)
DISPATCH_CASES: list[tuple[str, str, bool]] = [
    ("dispatch_overview", "overview:", True),
    ("dispatch_version", "version:", True),
    ("dispatch_find", "find: login", True),
    (
        "dispatch_get_batch",
        "get_batch: ids='node:feat_login,node:feat_register' mode=brief max=5",
        True,
    ),
    ("dispatch_get", "get: node:feat_login", True),
    ("dispatch_signature", "signature: node:feat_login", True),
    ("dispatch_recent", "recent: 3", True),
    ("dispatch_decisions", "decisions: auth:login.method", True),
    ("dispatch_sections", "sections: doc:DOC-07", True),
    ("dispatch_code", "code: node:feat_login", True),
    ("dispatch_invariants", "invariants: node:feat_login", True),
    ("dispatch_tests", "tests: node:feat_login", True),
    ("dispatch_related", "related: node:feat_login", True),
    ("dispatch_template_flow", "template: Flow", True),
    ("dispatch_template_all", "template:", True),
    ("dispatch_interview", "interview: node:feat_login", True),
    ("dispatch_validate_nodes", "validate: nodes", True),
    ("dispatch_validate_metadata", "validate: metadata", True),
    ("dispatch_validate_schema_docs", "validate: schema-docs", True),
    ("dispatch_validate_schema_tests", "validate: schema-tests", True),
    (
        "dispatch_recompute_dry",
        "recompute: priorities dry_run=true session_id='session:2026-04-15_current'",
        True,
    ),
    (
        "dispatch_create_dry",
        "create:Idea name='PerfDispatchDry' session_id='session:2026-04-15_current' "
        "dry_run=true subject='perf' raw_quote='q' interpretation='i' maturity='RAW' confidence='low'",
        True,
    ),
    (
        "dispatch_update_dry",
        "update: id='idea:i001' name='PerfUpdateDry' session_id='session:2026-04-15_current' dry_run=true",
        True,
    ),
    (
        "dispatch_upsert_dry",
        "upsert:Idea dedupe_key='name' name='PerfUpsertOnlyOnce' dry_run=true "
        "session_id='session:2026-04-15_current' subject='s' raw_quote='r' interpretation='i' "
        "maturity='RAW' confidence='low'",
        True,
    ),
    (
        "dispatch_lock_dry",
        "lock:Decision topic='perf.dispatch.only' what='w' why='y' locked_by='CEO' "
        "dry_run=true session_id='session:2026-04-15_current'",
        True,
    ),
    (
        "dispatch_session_dry",
        "session:start actor='perf-dispatch' goal='dry benchmark' dry_run=true",
        True,
    ),
    ("dispatch_extract", "extract: lessons", True),
    (
        "dispatch_commit_fail_fast",
        "commit: imp:no-such-proposal-id session_id='session:2026-04-15_current'",
        False,
    ),
]


@pytest.mark.parametrize("bench_name,query,expect_ok", DISPATCH_CASES)
def test_perf_dispatch_gobp_queries(
    mihos_perf_root: Path,
    bench_name: str,
    query: str,
    expect_ok: bool,
) -> None:
    """``dispatch()`` latency for representative gobp() query strings."""
    index = _load(mihos_perf_root)
    start = time.perf_counter()
    result = asyncio.run(dispatch(query, index, mihos_perf_root))
    elapsed = _ms(start)
    if expect_ok:
        assert result.get("ok") is True, (query, result)
    else:
        assert result.get("ok") is False, (query, result)
    _assert_dispatch(bench_name, elapsed)


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
def test_perf_read_tools(
    mihos_perf_root: Path,
    name: str,
    call_fn: Callable[[GraphIndex, Path], dict[str, Any]],
) -> None:
    """Read tools must stay under documented max latency."""
    index = _load(mihos_perf_root)
    start = time.perf_counter()
    result = call_fn(index, mihos_perf_root)
    elapsed = _ms(start)
    assert result.get("ok") is True
    _assert_under_target(name, elapsed)


def test_perf_session_log_start(mihos_perf_root: Path) -> None:
    """session_log(start) should stay under max latency."""
    index = _load(mihos_perf_root)
    start = time.perf_counter()
    result = tools_write.session_log(
        index,
        mihos_perf_root,
        {"action": "start", "actor": "perf-test", "goal": "session start benchmark"},
    )
    elapsed = _ms(start)
    assert result.get("ok") is True
    _assert_under_target("session_log", elapsed)


def test_perf_node_upsert(mihos_perf_root: Path) -> None:
    """node_upsert should stay under max latency (median of 3 runs)."""
    index = _load(mihos_perf_root)
    sess = tools_write.session_log(
        index,
        mihos_perf_root,
        {"action": "start", "actor": "perf-test", "goal": "node_upsert benchmark"},
    )
    assert sess.get("ok") is True

    index = _load(mihos_perf_root)
    session_id = str(sess["session_id"])

    def do_upsert() -> dict[str, Any]:
        return tools_write.node_upsert(
            index,
            mihos_perf_root,
            {
                "type": "Idea",
                "name": "Performance benchmark idea",
                "fields": {
                    "subject": "perf:benchmark",
                    "raw_quote": "perf test",
                    "interpretation": "performance benchmark node",
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
