"""End-to-end integration test for GoBP v1.

Simulates a complete AI session workflow:
1. gobp_overview → orient
2. find → discover nodes
3. context → deep dive
4. decisions_for → get locked decisions
5. session_log (start) → begin session
6. node_upsert → capture idea
7. decision_lock → lock decision
8. session_log (end) → close session
9. validate → verify graph integrity
10. lessons_extract → scan for lessons

Uses mihos_root fixture (~30 nodes) as starting state.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import read as tools_read
from gobp.mcp.tools import write as tools_write
from gobp.mcp.tools.advanced import lessons_extract

try:
    from gobp.mcp.tools import maintain as tools_maintain

    HAS_VALIDATE = True
except ImportError:
    HAS_VALIDATE = False

from tests.fixtures.mihos_fixture import mihos_root  # noqa: F401


def _load(root: Path) -> GraphIndex:
    return GraphIndex.load_from_disk(root)


def test_full_ai_session_workflow(mihos_root: Path) -> None:
    """Complete AI session: orient → discover → capture → lock → close → validate."""

    root = mihos_root
    index = _load(root)

    # 1. gobp_overview — orient
    overview = tools_read.gobp_overview(index, root, {})
    assert overview["ok"] is True
    assert overview["stats"]["total_nodes"] >= 25

    # 2. find — discover login feature
    found = tools_read.find(index, root, {"query": "login", "limit": 5})
    assert found["ok"] is True
    assert found["count"] >= 1
    login_node = next(
        (n for n in found["matches"] if "login" in n["id"].lower()), None
    )
    assert login_node is not None

    # 3. context — deep dive on login feature
    ctx = tools_read.context(index, root, {"node_id": login_node["id"]})
    assert ctx["ok"] is True
    assert "node" in ctx

    # 4. decisions_for — get locked decisions on auth
    decisions = tools_read.decisions_for(
        index, root, {"topic": "auth:login.method"}
    )
    assert decisions["ok"] is True
    assert decisions["count"] >= 1
    assert decisions["decisions"][0]["status"] == "LOCKED"

    # 5. session_log start
    sess = tools_write.session_log(
        index,
        root,
        {
            "action": "start",
            "actor": "integration-test",
            "goal": "Test full AI session workflow",
        },
    )
    assert sess["ok"] is True
    session_id = sess["session_id"]
    assert session_id.startswith("meta.session.")

    # Reload index after write
    index = _load(root)

    # 6. node_upsert — capture a new idea
    idea = tools_write.node_upsert(
        index,
        root,
        {
            "type": "Idea",
            "name": "Integration test idea",
            "fields": {
                "subject": "integration:test.subject",
                "raw_quote": "Testing the full workflow",
                "interpretation": "End-to-end test of GoBP session workflow",
                "maturity": "RAW",
                "confidence": "high",
            },
            "session_id": session_id,
        },
    )
    assert idea["ok"] is True
    idea_id = idea["node_id"]
    index = _load(root)

    # 7. decision_lock — lock a new decision
    dec = tools_write.decision_lock(
        index,
        root,
        {
            "topic": "integration:test.decision",
            "what": "Use integration tests to verify GoBP end-to-end",
            "why": "Automated verification catches regressions before push",
            "alternatives_considered": [
                {"option": "Manual testing only", "rejected_reason": "Not scalable"},
            ],
            "related_ideas": [idea_id],
            "session_id": session_id,
            "locked_by": ["CEO", "integration-test"],
        },
    )
    assert dec["ok"] is True
    dec_id = dec["decision_id"]
    index = _load(root)

    # 8. session_log end
    end = tools_write.session_log(
        index,
        root,
        {
            "action": "end",
            "session_id": session_id,
            "outcome": "Integration test workflow completed successfully",
            "pending": [],
            "nodes_touched": [idea_id, dec_id],
            "decisions_locked": [dec_id],
        },
    )
    assert end["ok"] is True
    index = _load(root)

    # 9. validate — graph integrity check
    if HAS_VALIDATE:
        val = tools_maintain.validate(index, root, {"scope": "all"})
        assert val["ok"] is True
        hard_errors = [i for i in val.get("issues", []) if i.get("severity") == "hard"]
        assert len(hard_errors) == 0, f"Hard validation errors: {hard_errors}"

    # 10. lessons_extract — scan for candidates
    lessons = asyncio.run(lessons_extract(index, root, {}))
    assert lessons["ok"] is True
    assert "candidates" in lessons
    assert "note" in lessons


def test_session_recent_after_writes(mihos_root: Path) -> None:
    """session_recent returns new session after session_log start."""
    root = mihos_root
    index = _load(root)

    sess = tools_write.session_log(
        index,
        root,
        {
            "action": "start",
            "actor": "recency-test",
            "goal": "Test recency",
        },
    )
    assert sess["ok"] is True
    session_id = sess["session_id"]
    index = _load(root)

    recent = tools_read.session_recent(index, root, {"n": 5})
    assert recent["ok"] is True
    session_ids = [s["id"] for s in recent["sessions"]]
    assert session_id in session_ids


def test_find_returns_newly_created_node(mihos_root: Path) -> None:
    """find() discovers a node created via node_upsert in same session."""
    root = mihos_root
    index = _load(root)

    sess = tools_write.session_log(
        index,
        root,
        {
            "action": "start",
            "actor": "find-test",
            "goal": "Test find after upsert",
        },
    )
    session_id = sess["session_id"]
    index = _load(root)

    tools_write.node_upsert(
        index,
        root,
        {
            "type": "Idea",
            "name": "Uniquely named xyzzy idea for find test",
            "fields": {
                "subject": "find:test",
                "raw_quote": "xyzzy",
                "interpretation": "test",
                "maturity": "RAW",
                "confidence": "low",
            },
            "session_id": session_id,
        },
    )
    index = _load(root)

    found = tools_read.find(index, root, {"query": "xyzzy"})
    assert found["ok"] is True
    assert found["count"] >= 1
