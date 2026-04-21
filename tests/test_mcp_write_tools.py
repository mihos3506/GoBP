"""Tests for GoBP MCP write tools: node_upsert, decision_lock, session_log."""

from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import write as tools_write


@pytest.fixture
def populated_root(tmp_path: Path) -> Path:
    """GoBP root with schemas, an active session, and one existing idea."""
    import gobp

    actual_schema_dir = Path(gobp.__file__).parent / "schema"

    pkg_dir = tmp_path / "gobp"
    schema_dir = pkg_dir / "schema"
    schema_dir.mkdir(parents=True)
    (schema_dir / "core_nodes.yaml").write_text(
        (actual_schema_dir / "core_nodes.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (schema_dir / "core_edges.yaml").write_text(
        (actual_schema_dir / "core_edges.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    data_dir = tmp_path / ".gobp"
    (data_dir / "nodes").mkdir(parents=True)
    (data_dir / "edges").mkdir(parents=True)

    # Active session
    (data_dir / "nodes" / "session_2026-04-14_test.md").write_text(
        """---
id: session:2026-04-14_test
type: Session
name: Test session
actor: test_actor
started_at: 2026-04-14T09:00:00+00:00
goal: Test write tools
status: IN_PROGRESS
created: 2026-04-14T09:00:00+00:00
updated: 2026-04-14T09:00:00+00:00
---

Body.
""",
        encoding="utf-8",
    )

    return tmp_path


def _load_index(root: Path) -> GraphIndex:
    return GraphIndex.load_from_disk(root)


# =============================================================================
# node_upsert tests
# =============================================================================


def test_node_upsert_creates_idea(populated_root):
    index = _load_index(populated_root)
    result = tools_write.node_upsert(
        index,
        populated_root,
        {
            "type": "Idea",
            "name": "Try Email OTP",
            "fields": {
                "status": "ACTIVE",
                "subject": "auth:login.method",
                "raw_quote": "Dùng OTP email đi",
                "interpretation": "Switch to Email OTP",
                "maturity": "RAW",
                "confidence": "medium",
            },
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is True, result
    assert result["created"] is True
    nid = result["node_id"]
    assert nid.startswith("idea:i") or ".meta." in nid or "idea." in nid or ".idea." in nid


def test_node_upsert_opaque_session_id_without_graph_session(populated_root):
    """Unknown session id is treated as opaque audit (no Session node required)."""
    index = _load_index(populated_root)
    result = tools_write.node_upsert(
        index,
        populated_root,
        {
            "type": "Idea",
            "name": "X",
            "fields": {
                "status": "ACTIVE",
                "subject": "test:opaque",
                "raw_quote": "q",
                "interpretation": "i",
                "maturity": "RAW",
                "confidence": "low",
            },
            "session_id": "session:nonexistent",
        },
    )
    assert result["ok"] is True, result
    assert result["node_id"]


def test_node_upsert_completed_graph_session_rejected(populated_root):
    """When session_id points to a Session node with status COMPLETED, reject writes."""
    data_dir = populated_root / ".gobp" / "nodes"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "session_done.md").write_text(
        """---
id: session:done_test
type: Session
name: Done
actor: test
started_at: 2026-04-14T09:00:00+00:00
goal: done
status: COMPLETED
created: 2026-04-14T09:00:00+00:00
updated: 2026-04-14T09:00:00+00:00
---

x
""",
        encoding="utf-8",
    )
    index = _load_index(populated_root)
    result = tools_write.node_upsert(
        index,
        populated_root,
        {
            "type": "Idea",
            "name": "After close",
            "fields": {
                "status": "ACTIVE",
                "subject": "t",
                "raw_quote": "q",
                "interpretation": "i",
                "maturity": "RAW",
                "confidence": "low",
            },
            "session_id": "session:done_test",
        },
    )
    assert result["ok"] is False
    assert "ended" in result["error"].lower() or "COMPLETED" in result["error"]


def test_node_upsert_missing_required_fields(populated_root):
    index = _load_index(populated_root)
    result = tools_write.node_upsert(
        index,
        populated_root,
        {"type": "Idea", "fields": {}, "session_id": "session:2026-04-14_test"},
    )
    assert result["ok"] is False
    assert "name" in result["error"]


def test_node_upsert_validation_failure(populated_root):
    index = _load_index(populated_root)
    result = tools_write.node_upsert(
        index,
        populated_root,
        {
            "type": "Decision",
            "name": "Bad decision",
            "fields": {"what": "", "why": "missing what"},
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is False
    assert "errors" in result or "error" in result


# =============================================================================
# decision_lock tests
# =============================================================================


def test_decision_lock_creates_decision(populated_root):
    index = _load_index(populated_root)
    result = tools_write.decision_lock(
        index,
        populated_root,
        {
            "topic": "auth:login.method",
            "what": "Use Email OTP",
            "why": "SMS unreliable in VN",
            "alternatives_considered": [{"option": "SMS", "rejected_reason": "spam"}],
            "session_id": "session:2026-04-14_test",
            "locked_by": ["CEO", "AI-Witness"],
        },
    )
    assert result["ok"] is True, result
    assert result["decision_id"].startswith("dec:d")


def test_decision_lock_missing_locked_by(populated_root):
    index = _load_index(populated_root)
    result = tools_write.decision_lock(
        index,
        populated_root,
        {
            "topic": "x",
            "what": "y",
            "why": "z",
            "session_id": "session:2026-04-14_test",
            "locked_by": ["CEO"],  # only 1 entity
        },
    )
    assert result["ok"] is False
    assert "at least 2" in result["error"]


def test_decision_lock_warns_empty_alternatives(populated_root):
    index = _load_index(populated_root)
    result = tools_write.decision_lock(
        index,
        populated_root,
        {
            "topic": "test:topic",
            "what": "Do X",
            "why": "Reason",
            "session_id": "session:2026-04-14_test",
            "locked_by": ["CEO", "AI"],
        },
    )
    assert result["ok"] is True
    assert any("alternatives" in w.lower() for w in result["warnings"])


# =============================================================================
# session_log tests
# =============================================================================


def test_session_log_start(populated_root):
    index = _load_index(populated_root)
    result = tools_write.session_log(
        index,
        populated_root,
        {
            "action": "start",
            "actor": "Claude Test",
            "goal": "Test session start",
        },
    )
    assert result["ok"] is True, result
    assert result["session_id"].startswith("meta.session.")


def test_session_log_start_then_end_same_index_without_reload(populated_root):
    """After ``start``, the same GraphIndex must see the new session for ``end``."""
    index = _load_index(populated_root)
    r1 = tools_write.session_log(
        index,
        populated_root,
        {"action": "start", "actor": "t", "goal": "same-index session"},
    )
    assert r1.get("ok"), r1
    sid = str(r1["session_id"])
    assert index.get_node(sid) is not None
    r2 = tools_write.session_log(
        index,
        populated_root,
        {
            "action": "end",
            "session_id": sid,
            "outcome": "closed for test",
        },
    )
    assert r2.get("ok"), r2


def test_session_log_end(populated_root):
    index = _load_index(populated_root)
    # End the existing test session
    result = tools_write.session_log(
        index,
        populated_root,
        {
            "action": "end",
            "session_id": "session:2026-04-14_test",
            "outcome": "Test completed",
        },
    )
    assert result["ok"] is True, result


def test_session_log_end_twice_is_idempotent(populated_root):
    index = _load_index(populated_root)
    r0 = tools_write.session_log(
        index,
        populated_root,
        {"action": "start", "actor": "t", "goal": "idempotent end test"},
    )
    assert r0.get("ok"), r0
    sid = str(r0["session_id"])
    r1 = tools_write.session_log(
        index,
        populated_root,
        {"action": "end", "session_id": sid, "outcome": "first close"},
    )
    assert r1.get("ok"), r1
    r2 = tools_write.session_log(
        index,
        populated_root,
        {"action": "end", "session_id": sid, "outcome": "second close ignored"},
    )
    assert r2.get("ok"), r2
    assert r2.get("action") == "skipped"


def test_session_log_end_missing_outcome(populated_root):
    index = _load_index(populated_root)
    result = tools_write.session_log(
        index,
        populated_root,
        {
            "action": "end",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is False
    assert "outcome" in result["error"]


def test_session_log_start_missing_actor(populated_root):
    index = _load_index(populated_root)
    result = tools_write.session_log(
        index,
        populated_root,
        {"action": "start", "goal": "Test"},
    )
    assert result["ok"] is False


def test_session_log_invalid_action(populated_root):
    index = _load_index(populated_root)
    result = tools_write.session_log(
        index,
        populated_root,
        {"action": "invalid"},
    )
    assert result["ok"] is False


def test_session_log_update(populated_root):
    index = _load_index(populated_root)
    result = tools_write.session_log(
        index,
        populated_root,
        {
            "action": "update",
            "session_id": "session:2026-04-14_test",
            "handoff_notes": "Continue with import tasks",
        },
    )
    assert result["ok"] is True
