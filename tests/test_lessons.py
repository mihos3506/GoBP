"""Tests for gobp.core.lessons module."""

from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.core.lessons import extract_candidates


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gobp_root(tmp_path: Path) -> Path:
    """Create minimal .gobp/ structure with required schema files."""
    (tmp_path / ".gobp" / "nodes").mkdir(parents=True)
    (tmp_path / ".gobp" / "edges").mkdir(parents=True)
    (tmp_path / ".gobp" / "history").mkdir(parents=True)

    # GraphIndex.load_from_disk requires schema files at <root>/gobp/schema/
    import shutil
    repo_schema = Path(__file__).parent.parent / "gobp" / "schema"
    dest_schema = tmp_path / "gobp" / "schema"
    dest_schema.mkdir(parents=True)
    shutil.copy(repo_schema / "core_nodes.yaml", dest_schema / "core_nodes.yaml")
    shutil.copy(repo_schema / "core_edges.yaml", dest_schema / "core_edges.yaml")

    return tmp_path


def _write_node(gobp_root: Path, node: dict) -> None:
    """Write a node to .gobp/nodes/."""
    node_id = node["id"].replace(":", "-")
    node_path = gobp_root / ".gobp" / "nodes" / f"{node_id}.md"
    frontmatter = yaml.dump(node, allow_unicode=True, default_flow_style=False)
    node_path.write_text(f"---\n{frontmatter}---\n", encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# Tests: empty graph
# ---------------------------------------------------------------------------

def test_extract_candidates_empty_graph(tmp_path: Path):
    """Empty graph returns empty candidates."""
    root = _make_gobp_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    assert candidates == []


# ---------------------------------------------------------------------------
# Tests: P1 — failed sessions
# ---------------------------------------------------------------------------

def test_p1_detects_interrupted_session(tmp_path: Path):
    """P1 fires for INTERRUPTED session."""
    root = _make_gobp_root(tmp_path)
    _write_node(root, {
        "id": "session:2026-04-14_s001",
        "type": "Session",
        "actor": "test",
        "started_at": _days_ago_iso(2),
        "goal": "Build something complex",
        "status": "INTERRUPTED",
        "outcome": "ran out of context",
        "pending": ["task A"],
        "created": _days_ago_iso(2),
        "updated": _days_ago_iso(1),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)

    p1 = [c for c in candidates if c["pattern"] == "P1"]
    assert len(p1) >= 1
    assert "session:2026-04-14_s001" in p1[0]["evidence"]
    assert p1[0]["severity"] == "medium"


def test_p1_detects_failed_session_as_high_severity(tmp_path: Path):
    """P1 FAILED session -> severity=high."""
    root = _make_gobp_root(tmp_path)
    _write_node(root, {
        "id": "session:2026-04-14_s002",
        "type": "Session",
        "actor": "test",
        "started_at": _days_ago_iso(3),
        "goal": "Ship wave",
        "status": "FAILED",
        "outcome": "tests broke",
        "pending": [],
        "created": _days_ago_iso(3),
        "updated": _days_ago_iso(2),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)

    p1 = [c for c in candidates if c["pattern"] == "P1"]
    assert any(c["severity"] == "high" for c in p1)


def test_p1_skips_completed_sessions(tmp_path: Path):
    """P1 does not flag COMPLETED sessions."""
    root = _make_gobp_root(tmp_path)
    _write_node(root, {
        "id": "session:s003",
        "type": "Session",
        "actor": "test",
        "started_at": _now_iso(),
        "goal": "Write docs",
        "status": "COMPLETED",
        "outcome": "done",
        "created": _now_iso(),
        "updated": _now_iso(),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p1 = [c for c in candidates if c["pattern"] == "P1"]
    assert p1 == []


# ---------------------------------------------------------------------------
# Tests: P2 — recurring uncertainty
# ---------------------------------------------------------------------------

def test_p2_detects_undecided_topic(tmp_path: Path):
    """P2 fires when 3+ Ideas share a topic with no Decision."""
    root = _make_gobp_root(tmp_path)
    for i in range(3):
        _write_node(root, {
            "id": f"idea:i00{i}",
            "type": "Idea",
            "name": f"idea {i}",
            "subject": "auth:login",
            "raw_quote": "some thought",
            "interpretation": "login idea",
            "maturity": "RAW",
            "confidence": "low",
            "session_id": "session:2026-04-14_test",
            "created": _now_iso(),
            "updated": _now_iso(),
        })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p2 = [c for c in candidates if c["pattern"] == "P2"]
    assert len(p2) >= 1
    assert "auth:login" in p2[0]["title"]


def test_p2_skips_topic_with_locked_decision(tmp_path: Path):
    """P2 does not flag a topic if a locked Decision exists."""
    root = _make_gobp_root(tmp_path)
    for i in range(3):
        _write_node(root, {
            "id": f"idea:i01{i}",
            "type": "Idea",
            "name": f"idea {i}",
            "subject": "storage:backend",
            "raw_quote": "thought",
            "interpretation": "storage idea",
            "maturity": "ROUGH",
            "confidence": "low",
            "created": _now_iso(),
            "updated": _now_iso(),
        })
    _write_node(root, {
        "id": "dec:d001",
        "type": "Decision",
        "name": "Use file storage",
        "topic": "storage:backend",
        "what": "Use YAML files",
        "why": "Simple",
        "status": "LOCKED",
        "locked_at": _now_iso(),
        "locked_by": ["CEO"],
        "created": _now_iso(),
        "updated": _now_iso(),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p2 = [c for c in candidates if c["pattern"] == "P2" and "storage:backend" in c.get("title", "")]
    assert p2 == []


# ---------------------------------------------------------------------------
# Tests: P3 — premature decisions
# ---------------------------------------------------------------------------

def test_p3_detects_decision_superseded_within_7_days(tmp_path: Path):
    """P3 fires when Decision is superseded within 7 days."""
    root = _make_gobp_root(tmp_path)
    locked_at = _days_ago_iso(5)
    updated = _days_ago_iso(3)
    _write_node(root, {
        "id": "dec:d010",
        "type": "Decision",
        "name": "Old decision",
        "topic": "ui:theme",
        "what": "Use dark mode",
        "why": "Trend",
        "status": "SUPERSEDED",
        "locked_at": locked_at,
        "locked_by": ["CEO"],
        "session_id": "session:2026-04-14_test",
        "created": locked_at,
        "updated": updated,
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p3 = [c for c in candidates if c["pattern"] == "P3"]
    assert len(p3) >= 1
    assert "dec:d010" in p3[0]["evidence"]


def test_p3_skips_decision_superseded_after_7_days(tmp_path: Path):
    """P3 skips Decision superseded after 7+ days (normal lifecycle)."""
    root = _make_gobp_root(tmp_path)
    locked_at = _days_ago_iso(30)
    updated = _days_ago_iso(15)
    _write_node(root, {
        "id": "dec:d011",
        "type": "Decision",
        "name": "Old decision 2",
        "topic": "api:version",
        "what": "Use REST",
        "why": "Standard",
        "status": "SUPERSEDED",
        "locked_at": locked_at,
        "locked_by": ["CEO"],
        "created": locked_at,
        "updated": updated,
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p3 = [c for c in candidates if c["pattern"] == "P3" and "dec:d011" in c.get("evidence", [])]
    assert p3 == []


# ---------------------------------------------------------------------------
# Tests: P4 — orphan nodes
# ---------------------------------------------------------------------------

def test_p4_detects_old_orphan_node(tmp_path: Path):
    """P4 fires for non-Session node older than 30 days with no edges."""
    root = _make_gobp_root(tmp_path)
    _write_node(root, {
        "id": "node:orphan001",
        "type": "Node",
        "name": "Forgotten feature",
        "status": "ACTIVE",
        "created": _days_ago_iso(45),
        "updated": _days_ago_iso(45),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p4 = [c for c in candidates if c["pattern"] == "P4"]
    assert len(p4) >= 1
    assert "node:orphan001" in p4[0]["evidence"]


def test_p4_skips_recent_orphan(tmp_path: Path):
    """P4 skips orphan nodes created less than 30 days ago."""
    root = _make_gobp_root(tmp_path)
    _write_node(root, {
        "id": "node:recent001",
        "type": "Node",
        "name": "New feature",
        "status": "ACTIVE",
        "created": _days_ago_iso(5),
        "updated": _days_ago_iso(5),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p4 = [c for c in candidates if c["pattern"] == "P4" and "node:recent001" in c.get("evidence", [])]
    assert p4 == []


# ---------------------------------------------------------------------------
# Tests: max_candidates cap
# ---------------------------------------------------------------------------

def test_max_candidates_cap(tmp_path: Path):
    """extract_candidates respects max_candidates cap."""
    root = _make_gobp_root(tmp_path)
    # Create 10 interrupted sessions to get 10 P1 candidates
    for i in range(10):
        _write_node(root, {
            "id": f"session:s{i:03d}",
            "type": "Session",
            "actor": "test",
            "started_at": _days_ago_iso(i + 1),
            "goal": f"Goal {i}",
            "status": "INTERRUPTED",
            "outcome": "interrupted",
            "pending": [],
            "created": _days_ago_iso(i + 1),
            "updated": _days_ago_iso(i),
        })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root, max_candidates=3)
    assert len(candidates) <= 3
