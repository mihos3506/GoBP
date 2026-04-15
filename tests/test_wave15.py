"""Tests for Wave 15: parser fix, import doc_id, edge dedupe."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.core.mutator import create_edge, deduplicate_edges
from gobp.mcp.dispatcher import _coerce_value, dispatch, parse_query


def test_find_positional_no_params() -> None:
    action, _, params = parse_query("find: login")
    assert action == "find"
    assert params.get("query") == "login"


def test_find_positional_with_page_size() -> None:
    action, _, params = parse_query("find: login page_size=10")
    assert action == "find"
    assert params.get("query") == "login"
    assert params.get("page_size") == 10


def test_find_type_with_positional_and_pagination() -> None:
    action, node_type, params = parse_query("find:Decision auth page_size=5")
    assert action == "find"
    assert node_type == "Decision"
    assert params.get("query") == "auth"
    assert params.get("page_size") == 5


def test_related_preserves_node_id_with_pagination() -> None:
    action, _, params = parse_query("related: node:x direction='outgoing' page_size=10")
    assert action == "related"
    assert params.get("node_id") == "node:x"
    assert params.get("direction") == "outgoing"
    assert params.get("page_size") == 10


def test_tests_preserves_node_id_with_pagination() -> None:
    action, _, params = parse_query("tests: node:x page_size=20")
    assert action == "tests"
    assert params.get("node_id") == "node:x"
    assert params.get("page_size") == 20


def test_code_preserves_node_id() -> None:
    action, _, params = parse_query("code: node:flow_auth")
    assert action == "code"
    assert params.get("node_id") == "node:flow_auth"


def test_bool_coercion_true() -> None:
    assert _coerce_value("true") is True
    assert _coerce_value("True") is True


def test_bool_coercion_false() -> None:
    assert _coerce_value("false") is False


def test_none_coercion() -> None:
    assert _coerce_value("null") is None
    assert _coerce_value("none") is None


def test_int_coercion() -> None:
    assert _coerce_value("10") == 10
    assert _coerce_value("3") == 3


def test_create_bool_field() -> None:
    _, _, params = parse_query("create:TestCase automated=true name='test'")
    assert params.get("automated") is True


def test_session_start_positional() -> None:
    action, _, params = parse_query("session:start actor='cursor' goal='test'")
    assert action == "session"
    assert params.get("query") == "start"
    assert params.get("actor") == "cursor"
    assert params.get("goal") == "test"


def test_edge_arrow_syntax() -> None:
    action, _, params = parse_query("edge: node:a --implements--> node:b")
    assert action == "edge"
    assert params.get("from") == "node:a"
    assert params.get("edge_type") == "implements"
    assert params.get("to") == "node:b"


def test_import_docid_different_for_same_stem(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    session = asyncio.run(dispatch("session:start actor='test' goal='docid test'", index, gobp_root))
    session_id = session["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    (gobp_root / "docs").mkdir(exist_ok=True)
    (gobp_root / "examples").mkdir(exist_ok=True)
    (gobp_root / "docs" / "README.md").write_text("# Root README", encoding="utf-8")
    (gobp_root / "examples" / "README.md").write_text("# Examples README", encoding="utf-8")

    result1 = asyncio.run(dispatch(f"import: docs/README.md session_id='{session_id}'", index, gobp_root))
    index = GraphIndex.load_from_disk(gobp_root)
    result2 = asyncio.run(dispatch(f"import: examples/README.md session_id='{session_id}'", index, gobp_root))

    assert result1.get("ok") is True
    assert result2.get("ok") is True
    assert result1["document_node"] != result2["document_node"]


def test_import_failed_has_no_success_fields(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = asyncio.run(dispatch("import: nonexistent/file.md session_id='session:fake'", index, gobp_root))

    if not result.get("ok"):
        assert "document_node" not in result
        assert "suggestion" not in result
        assert "error" in result


def test_import_success_has_document_node(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    (gobp_root / "test_doc.md").write_text("# Test\nContent here.", encoding="utf-8")
    session = asyncio.run(dispatch("session:start actor='test' goal='import test'", index, gobp_root))
    session_id = session["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(f"import: test_doc.md session_id='{session_id}'", index, gobp_root))
    assert result.get("ok") is True
    assert "document_node" in result
    assert result["document_node"].startswith("doc:")


def test_create_edge_idempotent(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    from gobp.core.loader import load_schema

    schema_dir = gobp_root / "gobp" / "schema"
    edges_schema = load_schema(schema_dir / "core_edges.yaml")

    edge = {"from": "node:test_a", "to": "node:test_b", "type": "relates_to"}
    create_edge(gobp_root, edge, edges_schema, actor="test")
    create_edge(gobp_root, edge, edges_schema, actor="test")

    edge_file = gobp_root / ".gobp" / "edges" / "relations.yaml"
    edges = yaml.safe_load(edge_file.read_text(encoding="utf-8"))
    matching = [e for e in edges if e.get("from") == "node:test_a" and e.get("to") == "node:test_b" and e.get("type") == "relates_to"]
    assert len(matching) == 1


def test_deduplicate_edges_removes_duplicates(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)

    edges_dir = gobp_root / ".gobp" / "edges"
    edges_dir.mkdir(parents=True, exist_ok=True)
    edge_file = edges_dir / "test_edges.yaml"
    edge_file.write_text(
        yaml.safe_dump(
            [
                {"from": "node:a", "to": "node:b", "type": "relates_to"},
                {"from": "node:a", "to": "node:b", "type": "relates_to"},
                {"from": "node:c", "to": "node:d", "type": "implements"},
            ],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    result = deduplicate_edges(gobp_root)
    assert result["ok"] is True
    assert result["duplicates_removed"] == 1
    assert result["total_edges"] >= 2

    cleaned = yaml.safe_load(edge_file.read_text(encoding="utf-8"))
    assert len(cleaned) == 2


def test_dispatch_dedupe_action(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = asyncio.run(dispatch("dedupe: edges", index, gobp_root))
    assert result["ok"] is True
    assert "duplicates_removed" in result


@pytest.mark.parametrize(
    "query,expected",
    [
        ("find: login page_size=10", {"query": "login", "page_size": 10}),
        ("related: node:x direction=outgoing", {"node_id": "node:x", "direction": "outgoing"}),
        ("tests: node:x page_size=20", {"node_id": "node:x", "page_size": 20}),
        ("create:Node automated=true", {"automated": True}),
    ],
)
def test_parser_smoke_matrix(query: str, expected: dict[str, object]) -> None:
    _, _, params = parse_query(query)
    for key, value in expected.items():
        assert params.get(key) == value
