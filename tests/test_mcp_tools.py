"""Tests for Wave 3 MCP read tools."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import read as tools_read


def _write_node(node_path: Path, payload: dict) -> None:
    node_path.parent.mkdir(parents=True, exist_ok=True)
    body = "---\n" + yaml.safe_dump(payload, sort_keys=False) + "---\n\nBody\n"
    node_path.write_text(body, encoding="utf-8")


@pytest.fixture
def populated_root(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir(parents=True)

    # Schema expected at <root>/gobp/schema
    schema_src = Path("gobp/schema")
    schema_dst = root / "gobp" / "schema"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(schema_src, schema_dst)

    nodes_dir = root / ".gobp" / "nodes"
    edges_dir = root / ".gobp" / "edges"
    nodes_dir.mkdir(parents=True, exist_ok=True)
    edges_dir.mkdir(parents=True, exist_ok=True)
    doc_hash = hashlib.sha256("charter".encode("utf-8")).hexdigest()

    _write_node(
        nodes_dir / "charter.md",
        {
            "id": "doc:charter",
            "type": "Document",
            "name": "GoBP Charter",
            "source_path": "docs/spec.md",
            "content_hash": f"sha256:{doc_hash}",
            "registered_at": "2026-04-14T00:00:00Z",
            "last_verified": "2026-04-14T00:00:00Z",
            "sections": [
                {"heading": "Introduction", "lines": [1, 20], "tags": ["intro"]},
                {"heading": "Goals", "lines": [21, 50], "tags": ["goals"]},
            ],
            "created": "2026-04-14T00:00:00Z",
            "updated": "2026-04-14T00:00:00Z",
        },
    )
    _write_node(
        nodes_dir / "feature_login.md",
        {
            "id": "node:feature_login",
            "type": "Node",
            "name": "User Login",
            "subtype": "feature",
            "description": "Enable user login flow.",
            "status": "ACTIVE",
            "created": "2026-04-14T00:00:00Z",
            "updated": "2026-04-14T00:00:00Z",
        },
    )
    _write_node(
        nodes_dir / "feature_profile.md",
        {
            "id": "node:feature_profile",
            "type": "Node",
            "name": "Profile Page",
            "subtype": "feature",
            "description": "Allow profile updates.",
            "status": "ACTIVE",
            "created": "2026-04-14T00:00:00Z",
            "updated": "2026-04-14T00:00:00Z",
        },
    )
    _write_node(
        nodes_dir / "session_1.md",
        {
            "id": "session:2026-04-14-1",
            "type": "Session",
            "actor": "cursor",
            "started_at": "2026-04-14T10:00:00Z",
            "ended_at": "2026-04-14T11:00:00Z",
            "goal": "Ship MCP server",
            "outcome": "done",
            "status": "COMPLETED",
            "pending": ["cli polish"],
            "handoff_notes": "next wave",
            "created": "2026-04-14T10:00:00Z",
            "updated": "2026-04-14T11:00:00Z",
        },
    )
    _write_node(
        nodes_dir / "session_2.md",
        {
            "id": "session:2026-04-15-1",
            "type": "Session",
            "actor": "cursor",
            "started_at": "2026-04-15T10:00:00Z",
            "goal": "Implement read tools",
            "status": "IN_PROGRESS",
            "created": "2026-04-15T10:00:00Z",
            "updated": "2026-04-15T10:00:00Z",
        },
    )
    _write_node(
        nodes_dir / "decision_1.md",
        {
            "id": "dec:d001",
            "type": "Decision",
            "topic": "MCP Transport",
            "what": "Use stdio server mode for compatibility and simplicity.",
            "why": "Broad client support and lower operational complexity.",
            "status": "LOCKED",
            "locked_at": "2026-04-15T12:00:00Z",
            "locked_by": ["cursor"],
            "session_id": "session:2026-04-15-1",
            "alternatives_considered": [{"name": "http", "reason_rejected": "extra ops"}],
            "created": "2026-04-15T12:00:00Z",
            "updated": "2026-04-15T12:00:00Z",
        },
    )
    _write_node(
        nodes_dir / "decision_2.md",
        {
            "id": "dec:d002",
            "type": "Decision",
            "topic": "MCP Transport",
            "what": "Retain exactly seven read tools in Wave 3 scope.",
            "why": "Matches brief and keeps v1 minimal.",
            "status": "SUPERSEDED",
            "locked_at": "2026-04-14T12:00:00Z",
            "locked_by": ["cursor"],
            "session_id": "session:2026-04-14-1",
            "created": "2026-04-14T12:00:00Z",
            "updated": "2026-04-14T12:00:00Z",
        },
    )

    edge_data = [
        {"from": "node:feature_login", "to": "dec:d001", "type": "implements"},
        {"from": "node:feature_login", "to": "doc:charter", "type": "references", "section": "Constraints", "lines": [3, 4]},
        {"from": "node:feature_profile", "to": "dec:d001", "type": "implements"},
        {"from": "node:feature_login", "to": "session:2026-04-15-1", "type": "discovered_in"},
    ]
    (edges_dir / "main.yaml").write_text(yaml.safe_dump(edge_data, sort_keys=False), encoding="utf-8")

    return root


@pytest.fixture
def index(populated_root: Path) -> GraphIndex:
    return GraphIndex.load_from_disk(populated_root)


# gobp_overview (6)
def test_gobp_overview_ok(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.gobp_overview(index, populated_root, {})
    assert out["ok"] is True


def test_gobp_overview_project_from_charter(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.gobp_overview(index, populated_root, {})
    assert out["project"]["name"] == "GoBP Charter"


def test_gobp_overview_stats_counts(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.gobp_overview(index, populated_root, {})
    assert out["stats"]["total_nodes"] >= 7
    assert out["stats"]["total_edges"] == 4


def test_gobp_overview_topics(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.gobp_overview(index, populated_root, {})
    assert "MCP Transport" in out["main_topics"]


def test_gobp_overview_recent_decisions(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.gobp_overview(index, populated_root, {})
    assert len(out["recent_decisions"]) >= 1
    assert out["recent_decisions"][0]["id"] == "dec:d001"


def test_gobp_overview_suggestions(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.gobp_overview(index, populated_root, {})
    assert len(out["suggested_next_queries"]) == 3


# find (5)
def test_find_requires_query(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.find(index, populated_root, {})
    assert out["ok"] is False


def test_find_exact_id(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.find(index, populated_root, {"query": "node:feature_login"})
    assert out["ok"] is True
    assert out["matches"][0]["match"] == "exact_id"


def test_find_exact_name(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.find(index, populated_root, {"query": "User Login"})
    assert any(m["match"] == "exact_name" for m in out["matches"])


def test_find_substring(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.find(index, populated_root, {"query": "feature"})
    assert out["count"] >= 2


def test_find_limit_and_truncated(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.find(index, populated_root, {"query": ":", "limit": 1})
    assert out["count"] == 1
    assert out["truncated"] is True


# signature (3)
def test_signature_requires_node_id(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.signature(index, populated_root, {})
    assert out["ok"] is False


def test_signature_not_found(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.signature(index, populated_root, {"node_id": "node:missing"})
    assert out["ok"] is False


def test_signature_happy_path(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.signature(index, populated_root, {"node_id": "node:feature_login"})
    assert out["ok"] is True
    assert out["signature"]["id"] == "node:feature_login"


# context (4)
def test_context_requires_node_id(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.context(index, populated_root, {})
    assert out["ok"] is False


def test_context_not_found(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.context(index, populated_root, {"node_id": "node:missing"})
    assert out["ok"] is False


def test_context_includes_outgoing_and_incoming(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.context(index, populated_root, {"node_id": "node:feature_login"})
    assert out["ok"] is True
    assert len(out["outgoing"]) >= 2


def test_context_includes_references_and_invariants(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.context(index, populated_root, {"node_id": "node:feature_login"})
    assert out["invariants"] == []
    assert len(out["references"]) == 1


# session_recent (3)
def test_session_recent_default(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.session_recent(index, populated_root, {})
    assert out["ok"] is True
    assert out["count"] <= 3


def test_session_recent_respects_n(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.session_recent(index, populated_root, {"n": 1})
    assert out["count"] == 1


def test_session_recent_actor_filter(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.session_recent(index, populated_root, {"actor": "cursor"})
    assert out["ok"] is True
    assert out["count"] >= 1


# decisions_for (4)
def test_decisions_for_requires_topic_or_node(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.decisions_for(index, populated_root, {})
    assert out["ok"] is False


def test_decisions_for_topic(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.decisions_for(index, populated_root, {"topic": "MCP Transport"})
    assert out["ok"] is True
    assert out["count"] >= 1


def test_decisions_for_node(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.decisions_for(index, populated_root, {"node_id": "node:feature_login"})
    assert out["ok"] is True
    assert any(d["id"] == "dec:d001" for d in out["decisions"])


def test_decisions_for_all_status(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.decisions_for(
        index, populated_root, {"topic": "MCP Transport", "status": "ALL"}
    )
    assert out["count"] >= 2


# doc_sections (3)
def test_doc_sections_requires_doc_id(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.doc_sections(index, populated_root, {})
    assert out["ok"] is False


def test_doc_sections_happy_path(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.doc_sections(index, populated_root, {"doc_id": "doc:charter"})
    assert out["ok"] is True
    assert out["document"]["id"] == "doc:charter"
    assert out["document"]["name"] == "GoBP Charter"
    assert out["sections"][0]["heading"] == "Introduction"
    assert out["sections"][0]["lines"] == [1, 20]
    assert out["sections"][0]["tags"] == ["intro"]


def test_doc_sections_non_document_node(index: GraphIndex, populated_root: Path) -> None:
    out = tools_read.doc_sections(index, populated_root, {"doc_id": "node:feature_login"})
    assert out["ok"] is False


def test_mcp_server_registers_all_14_tools():
    """Smoke test: MCP server must list all 14 tools (7 read + 6 write/import/validate + lessons_extract)."""
    from gobp.mcp import server as srv
    import asyncio

    tools = asyncio.run(srv.list_tools())
    tool_names = [t.name for t in tools]

    expected = {
        "gobp_overview",
        "find",
        "signature",
        "context",
        "session_recent",
        "decisions_for",
        "doc_sections",
        "node_upsert",
        "decision_lock",
        "session_log",
        "import_proposal",
        "import_commit",
        "validate",
        "lessons_extract",
    }

    assert set(tool_names) == expected, f"Got {tool_names}, expected {expected}"
    assert len(tools) == 14
