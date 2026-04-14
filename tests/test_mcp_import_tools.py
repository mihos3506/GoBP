"""Tests for GoBP MCP import tools: import_proposal, import_commit."""

from pathlib import Path

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import import_ as tools_import


@pytest.fixture
def populated_root(tmp_path: Path) -> Path:
    """GoBP root with schemas and an active session."""
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

    (data_dir / "nodes" / "session_2026-04-14_test.md").write_text(
        """---
id: session:2026-04-14_test
type: Session
name: Test
actor: test
started_at: 2026-04-14T09:00:00+00:00
goal: Test import
status: IN_PROGRESS
created: 2026-04-14T09:00:00+00:00
updated: 2026-04-14T09:00:00+00:00
---

Body.
""",
        encoding="utf-8",
    )

    return tmp_path


def _load(root: Path) -> GraphIndex:
    return GraphIndex.load_from_disk(root)


def _valid_node_dict(id: str, name: str) -> dict:
    return {
        "id": id,
        "type": "Node",
        "name": name,
        "status": "ACTIVE",
        "created": "2026-04-14T10:00:00+00:00",
        "updated": "2026-04-14T10:00:00+00:00",
    }


# =============================================================================
# import_proposal tests
# =============================================================================


def test_proposal_creates_pending_file(populated_root):
    index = _load(populated_root)
    result = tools_import.import_proposal(
        index,
        populated_root,
        {
            "source_path": "docs/test.md",
            "proposal_type": "doc",
            "ai_notes": "Test proposal",
            "proposed_nodes": [_valid_node_dict("node:t1", "Test 1")],
            "proposed_edges": [],
            "confidence": "high",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is True
    pending_files = list((populated_root / ".gobp" / "proposals").glob("*.pending.yaml"))
    assert len(pending_files) == 1


def test_proposal_returns_counts(populated_root):
    index = _load(populated_root)
    result = tools_import.import_proposal(
        index,
        populated_root,
        {
            "source_path": "docs/test.md",
            "proposal_type": "doc",
            "ai_notes": "X",
            "proposed_nodes": [
                _valid_node_dict("node:a", "A"),
                _valid_node_dict("node:b", "B"),
            ],
            "proposed_edges": [
                {"from": "node:a", "to": "node:b", "type": "relates_to"},
            ],
            "confidence": "medium",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["node_count"] == 2
    assert result["edge_count"] == 1


def test_proposal_missing_fields(populated_root):
    index = _load(populated_root)
    result = tools_import.import_proposal(
        index,
        populated_root,
        {"source_path": "x"},
    )
    assert result["ok"] is False


def test_proposal_invalid_type(populated_root):
    index = _load(populated_root)
    result = tools_import.import_proposal(
        index,
        populated_root,
        {
            "source_path": "x",
            "proposal_type": "invalid",
            "ai_notes": "x",
            "proposed_nodes": [],
            "proposed_edges": [],
            "confidence": "high",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is False


# =============================================================================
# import_commit tests
# =============================================================================


def test_commit_all(populated_root):
    index = _load(populated_root)
    # First make a proposal
    prop_result = tools_import.import_proposal(
        index,
        populated_root,
        {
            "source_path": "docs/test.md",
            "proposal_type": "doc",
            "ai_notes": "X",
            "proposed_nodes": [_valid_node_dict("node:commit_test", "Test")],
            "proposed_edges": [],
            "confidence": "high",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert prop_result["ok"] is True
    proposal_id = prop_result["proposal_id"]

    # Commit all
    index2 = _load(populated_root)
    commit_result = tools_import.import_commit(
        index2,
        populated_root,
        {
            "proposal_id": proposal_id,
            "accept": "all",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert commit_result["ok"] is True
    assert commit_result["nodes_created"] == 1

    # Proposal file moved to committed
    committed = list((populated_root / ".gobp" / "proposals").glob("*.committed.yaml"))
    assert len(committed) == 1


def test_commit_reject(populated_root):
    index = _load(populated_root)
    prop_result = tools_import.import_proposal(
        index,
        populated_root,
        {
            "source_path": "docs/test.md",
            "proposal_type": "doc",
            "ai_notes": "X",
            "proposed_nodes": [_valid_node_dict("node:reject_test", "X")],
            "proposed_edges": [],
            "confidence": "low",
            "session_id": "session:2026-04-14_test",
        },
    )
    proposal_id = prop_result["proposal_id"]

    index2 = _load(populated_root)
    result = tools_import.import_commit(
        index2,
        populated_root,
        {
            "proposal_id": proposal_id,
            "accept": "reject",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is True
    assert result["nodes_created"] == 0
    rejected = list((populated_root / ".gobp" / "proposals").glob("*.rejected.yaml"))
    assert len(rejected) == 1


def test_commit_missing_proposal(populated_root):
    index = _load(populated_root)
    result = tools_import.import_commit(
        index,
        populated_root,
        {
            "proposal_id": "imp:nonexistent",
            "accept": "all",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is False


def test_commit_validation_failure(populated_root):
    index = _load(populated_root)
    # Proposal with invalid node (missing required fields)
    bad_node = {"id": "node:bad", "type": "Node"}  # missing name, status, etc.
    prop_result = tools_import.import_proposal(
        index,
        populated_root,
        {
            "source_path": "docs/bad.md",
            "proposal_type": "doc",
            "ai_notes": "X",
            "proposed_nodes": [bad_node],
            "proposed_edges": [],
            "confidence": "low",
            "session_id": "session:2026-04-14_test",
        },
    )
    proposal_id = prop_result["proposal_id"]

    index2 = _load(populated_root)
    commit_result = tools_import.import_commit(
        index2,
        populated_root,
        {
            "proposal_id": proposal_id,
            "accept": "all",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert commit_result["ok"] is False
    assert commit_result["nodes_created"] == 0
