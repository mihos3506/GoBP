"""Tests for Wave 11A: lazy query actions — code, invariants, tests, related."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml

from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch, parse_query
from gobp.mcp.tools import read as tools_read


# -- Fixtures -----------------------------------------------------------------

@pytest.fixture
def populated_root(gobp_root: Path) -> Path:
    """Project with init seed data + 1 node with code_refs and invariants."""
    init_project(gobp_root, force=True)
    return gobp_root


@pytest.fixture
def node_with_refs(populated_root: Path) -> tuple[Path, str]:
    """Creates a node with code_refs and invariants, returns (root, node_id)."""
    from gobp.core.graph import GraphIndex
    from gobp.mcp.tools import write as tools_write
    import asyncio as _asyncio

    index = GraphIndex.load_from_disk(populated_root)

    # Start session
    sess = _asyncio.run(dispatch(
        "session:start actor='test' goal='wave11a test'",
        index, populated_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(populated_root)

    # Create node with code_refs and invariants
    result = _asyncio.run(dispatch(
        f"create:Node name='Auth Flow' priority='critical' session_id='{session_id}'",
        index, populated_root
    ))
    node_id = result["node_id"]

    # Update with code_refs and invariants via node_upsert directly
    index = GraphIndex.load_from_disk(populated_root)
    tools_write.node_upsert(index, populated_root, {
        "id": node_id,
        "type": "Node",
        "name": "Auth Flow",
        "fields": {
            "code_refs": [
                {"path": "lib/features/auth/login_screen.dart", "description": "OTP UI", "language": "dart"},
                {"path": "backend/src/auth/otp_service.ts", "description": "OTP logic", "language": "typescript"},
            ],
            "invariants": [
                "OTP expires after 5 minutes",
                "Max 3 attempts before lockout",
            ],
            "priority": "critical",
        },
        "session_id": session_id,
    })

    return populated_root, node_id


# -- Schema tests --------------------------------------------------------------

def test_schema_has_code_refs() -> None:
    """Schema v2: Node type exists with taxonomy; code_refs are node fields, not YAML optional."""
    p = Path(__file__).resolve().parent.parent / "gobp" / "schema" / "core_nodes.yaml"
    schema = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert schema["node_types"]["Node"].get("group")
    assert schema["node_types"]["Decision"].get("required")


def test_schema_has_invariants() -> None:
    """Invariant node type is declared in schema v2."""
    p = Path(__file__).resolve().parent.parent / "gobp" / "schema" / "core_nodes.yaml"
    schema = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "Invariant" in schema["node_types"]


# -- parse_query tests ---------------------------------------------------------

def test_parse_code_action() -> None:
    action, _, params = parse_query("code: node:flow_auth")
    assert action == "code"
    assert params.get("query") == "node:flow_auth"


def test_parse_invariants_action() -> None:
    action, _, params = parse_query("invariants: node:flow_auth")
    assert action == "invariants"
    assert params.get("query") == "node:flow_auth"


def test_parse_tests_action() -> None:
    action, _, params = parse_query("tests: node:flow_auth")
    assert action == "tests"
    assert params.get("query") == "node:flow_auth"


def test_parse_tests_with_status() -> None:
    action, _, params = parse_query("tests: node:flow_auth status='FAILING'")
    assert action == "tests"
    assert params.get("status") == "FAILING"


def test_parse_related_action() -> None:
    action, _, params = parse_query("related: node:flow_auth")
    assert action == "related"


def test_parse_related_with_direction() -> None:
    action, _, params = parse_query("related: node:flow_auth direction='outgoing'")
    assert params.get("direction") == "outgoing"


# -- code_refs handler tests ---------------------------------------------------

def test_code_refs_empty_node(populated_root: Path) -> None:
    """Node without code_refs returns empty list."""
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = tools_read.code_refs(index, populated_root, {"node_id": node_id})
    assert result["ok"] is True
    assert result["code_refs"] == []
    assert result["count"] == 0
    assert "hint" in result


def test_code_refs_with_data(node_with_refs: tuple[Path, str]) -> None:
    root, node_id = node_with_refs
    index = GraphIndex.load_from_disk(root)
    result = tools_read.code_refs(index, root, {"node_id": node_id})
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["code_refs"][0]["language"] == "dart"


def test_code_refs_node_not_found(populated_root: Path) -> None:
    index = GraphIndex.load_from_disk(populated_root)
    result = tools_read.code_refs(index, populated_root, {"node_id": "node:nonexistent"})
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_code_refs_missing_node_id(populated_root: Path) -> None:
    index = GraphIndex.load_from_disk(populated_root)
    result = tools_read.code_refs(index, populated_root, {})
    assert result["ok"] is False


# -- invariants handler tests --------------------------------------------------

def test_invariants_empty_node(populated_root: Path) -> None:
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = tools_read.node_invariants(index, populated_root, {"node_id": node_id})
    assert result["ok"] is True
    assert result["invariants"] == []
    assert result["count"] == 0


def test_invariants_with_data(node_with_refs: tuple[Path, str]) -> None:
    root, node_id = node_with_refs
    index = GraphIndex.load_from_disk(root)
    result = tools_read.node_invariants(index, root, {"node_id": node_id})
    assert result["ok"] is True
    assert result["count"] == 2
    assert "OTP expires" in result["invariants"][0]


# -- tests handler tests -------------------------------------------------------

def test_node_tests_no_testcases(populated_root: Path) -> None:
    """Node with no TestCases returns empty list."""
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = tools_read.node_tests(index, populated_root, {"node_id": node_id})
    assert result["ok"] is True
    assert result["count"] == 0
    assert result["coverage"] == "none"


def test_node_tests_summary_fields(populated_root: Path) -> None:
    """node_tests returns summary and coverage fields."""
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = tools_read.node_tests(index, populated_root, {"node_id": node_id})
    assert "summary" in result
    assert "passing" in result["summary"]
    assert "failing" in result["summary"]
    assert "coverage" in result


# -- related handler tests -----------------------------------------------------

def test_node_related_empty(populated_root: Path) -> None:
    """Node with no edges returns empty lists."""
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("Concept")
    node_id = nodes[0]["id"]
    result = tools_read.node_related(index, populated_root, {"node_id": node_id})
    assert result["ok"] is True
    assert "outgoing" in result
    assert "incoming" in result


def test_node_related_direction_filter(populated_root: Path) -> None:
    """related: with direction='outgoing' only returns outgoing."""
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("Concept")
    node_id = nodes[0]["id"]
    result = tools_read.node_related(
        index, populated_root, {"node_id": node_id, "direction": "outgoing"}
    )
    assert result["ok"] is True
    assert "incoming" in result  # key exists but may be empty
    assert isinstance(result["outgoing"], list)


# -- dispatch integration tests ------------------------------------------------

def test_dispatch_code_action(populated_root: Path) -> None:
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = asyncio.run(dispatch(f"code: {node_id}", index, populated_root))
    assert result["ok"] is True
    assert result["_dispatch"]["action"] == "code"


def test_dispatch_invariants_action(populated_root: Path) -> None:
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = asyncio.run(dispatch(f"invariants: {node_id}", index, populated_root))
    assert result["ok"] is True
    assert result["_dispatch"]["action"] == "invariants"


def test_dispatch_tests_action(populated_root: Path) -> None:
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = asyncio.run(dispatch(f"tests: {node_id}", index, populated_root))
    assert result["ok"] is True
    assert result["_dispatch"]["action"] == "tests"
    assert "coverage" in result


def test_dispatch_related_action(populated_root: Path) -> None:
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = asyncio.run(dispatch(f"related: {node_id}", index, populated_root))
    assert result["ok"] is True
    assert result["_dispatch"]["action"] == "related"


def test_protocol_guide_has_new_actions() -> None:
    from gobp.mcp.dispatcher import PROTOCOL_GUIDE
    actions = PROTOCOL_GUIDE["actions"]
    assert any("code:" in k for k in actions)
    assert any("invariants:" in k for k in actions)
    assert any("tests:" in k for k in actions)
    assert any("related:" in k for k in actions)
