"""Tests for Wave 10B: session ID, unicode, priority, edge creation, import enhancement."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml

from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch, parse_query, _classify_doc_priority


# -- Session ID tests ----------------------------------------------------------

def test_session_id_length():
    from gobp.core.mutator import _generate_session_id
    for _ in range(10):
        sid = _generate_session_id("Very long goal string that used to cause truncation issues in MIHOS Phase 2 import session")
        assert len(sid) == 33, f"Wrong length: {len(sid)}"
        assert sid.startswith("meta.session:20")


def test_session_id_unique():
    from gobp.core.mutator import _generate_session_id
    ids = {_generate_session_id() for _ in range(20)}
    assert len(ids) == 20  # all unique


# -- Unicode encoding tests ----------------------------------------------------

def test_unicode_in_node_yaml(gobp_root: Path):
    """Vietnamese text stored as UTF-8, not escaped."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        "session:start actor='test' goal='Xây dựng cơ chế xác thực'",
        index, gobp_root
    ))
    assert result["ok"] is True

    # Reload index and check session node
    index2 = GraphIndex.load_from_disk(gobp_root)
    session_id = result["session_id"]
    session = index2.get_node(session_id)
    assert session is not None
    assert "Xây dựng" in session.get("goal", ""), "Vietnamese text should be readable"


def test_node_file_no_escaped_unicode(gobp_root: Path):
    """Node files should not contain \\xNN escape sequences."""
    init_project(gobp_root, force=True)
    for node_file in (gobp_root / ".gobp" / "nodes").glob("*.md"):
        content = node_file.read_text(encoding="utf-8")
        assert "\\xe2" not in content, f"Escaped unicode in {node_file.name}"
        assert "\\u1" not in content, f"Escaped unicode in {node_file.name}"


# -- Priority field tests ------------------------------------------------------

def test_priority_field_in_schema():
    """priority field exists in Node schema."""
    schema = yaml.safe_load(
        open("gobp/schema/core_nodes.yaml", encoding="utf-8")
    )
    node_optional = schema["node_types"]["Node"].get("optional", {})
    assert "priority" in node_optional


def test_create_node_with_priority(gobp_root: Path):
    """create: action accepts priority field."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    # Start session first
    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='priority test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        f"create:Node name='Core Login' priority='critical' session_id='{session_id}'",
        index, gobp_root
    ))
    assert result["ok"] is True

    index2 = GraphIndex.load_from_disk(gobp_root)
    node_id = result.get("node_id", "")
    node = index2.get_node(node_id)
    assert node is not None
    assert node.get("priority") == "critical"


def test_priority_classify_critical():
    content = "Core user flows authentication proof of presence trust gate verification"
    assert _classify_doc_priority(content, "DOC-07_core_user_flows.md") == "critical"


def test_priority_classify_high():
    content = "Engine architecture entity domain database migration API interface"
    assert _classify_doc_priority(content, "DOC-16_engine_specs.md") in ("high", "critical")


def test_priority_classify_low():
    content = "Mascot character design growth campaign level system gamification"
    assert _classify_doc_priority(content, "DOC-17_mascot.md") == "low"


# -- Auto-generate ID tests ----------------------------------------------------

def test_create_without_id(gobp_root: Path):
    """create: auto-generates ID if not provided."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='id test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        f"create:Idea name='Auto ID test' session_id='{session_id}'",
        index, gobp_root
    ))
    assert result["ok"] is True
    node_id = result.get("node_id", "")
    assert ".meta." in node_id or node_id.startswith("meta.idea:"), f"Wrong ID format: {node_id}"


# -- Edge creation tests -------------------------------------------------------

def test_parse_edge_query():
    action, ntype, params = parse_query("edge: node:a --implements--> node:b")
    assert action == "edge"
    assert params["from"] == "node:a"
    assert params["edge_type"] == "implements"
    assert params["to"] == "node:b"


def test_parse_edge_with_reason():
    action, ntype, params = parse_query(
        "edge: node:flow_auth --implements--> node:pop_protocol reason='auth implements PoP'"
    )
    assert params["from"] == "node:flow_auth"
    assert params["reason"] == "auth implements PoP"


def test_dispatch_edge_creation(gobp_root: Path):
    """edge: creates semantic edge between existing nodes."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='edge test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    # Create 2 nodes
    r1 = asyncio.run(dispatch(
        f"create:Node name='Node A' session_id='{session_id}'", index, gobp_root
    ))
    r2 = asyncio.run(dispatch(
        f"create:Node name='Node B' session_id='{session_id}'", index, gobp_root
    ))
    id_a = r1["node_id"]
    id_b = r2["node_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    # Create edge
    result = asyncio.run(dispatch(
        f"edge: {id_a} --relates_to--> {id_b}",
        index, gobp_root
    ))
    assert result["ok"] is True
    assert result["edge_created"]["from"] == id_a
    assert result["edge_created"]["to"] == id_b
    assert result["edge_created"]["type"] == "relates_to"


def test_dispatch_edge_node_not_found(gobp_root: Path):
    """edge: returns error if node not found."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        "edge: node:nonexistent --relates_to--> node:also_nonexistent",
        index, gobp_root
    ))
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


# -- Import enhancement tests --------------------------------------------------

def test_import_creates_document_node(gobp_root: Path, tmp_path: Path):
    """import: creates Document node."""
    # Create a test doc file
    doc_file = tmp_path / "test_doc.md"
    doc_file.write_text(
        "# Test Document\n\nUser flows authentication proof of presence.\n\n## Section 1\nContent here.",
        encoding="utf-8"
    )

    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='import test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        f"import: {doc_file} session_id='{session_id}'",
        index, gobp_root
    ))
    assert result["ok"] is True
    assert result["document_node"].startswith("doc:")
    assert result["sections_found"] >= 1
    assert result["priority"] in ("critical", "high", "medium", "low")


def test_import_file_not_found(gobp_root: Path):
    """import: returns error if file not found."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        "import: nonexistent/file.md session_id='session:x'",
        index, gobp_root
    ))
    # Should still create Document node but with file_exists=False
    assert "file_exists" in result
    assert result["file_exists"] is False


# -- gobp_overview priority summary tests -------------------------------------

def test_gobp_overview_priority_summary(gobp_root: Path):
    """gobp_overview returns priority_summary."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch("overview:", index, gobp_root))
    assert result["ok"] is True
    assert "priority_summary" in result
    ps = result["priority_summary"]
    assert "critical" in ps
    assert "high" in ps
    assert "medium" in ps
    assert "low" in ps
    assert "critical_nodes" in ps
