"""Tests for Wave 16A04: coverage gaps, refactor verification."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.core.id_config import generate_external_id, make_id_slug
from gobp.core.init import init_project
from gobp.core.fs_mutator import create_edge
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.parser import _normalize_type, parse_query

_REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def core_edges_schema() -> dict[str, Any]:
    """Edges schema from repo (for create_edge validation)."""
    p = _REPO / "gobp" / "schema" / "core_edges.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


# -- Parser edge cases ---------------------------------------------------------


def test_parse_empty_query() -> None:
    a, t, p = parse_query("")
    assert a == "overview"
    assert t == ""
    assert p == {}


def test_parse_whitespace_only() -> None:
    a, t, p = parse_query("   ")
    assert a == "overview"


def test_parse_no_colon() -> None:
    a, t, p = parse_query("some query")
    assert a == "find"
    assert p.get("query") == "some query"


def test_parse_malformed_edge_rest_still_returns() -> None:
    a, _, p = parse_query("edge: not an arrow line")
    assert a == "edge"
    assert "_edge_raw" in p


def test_normalize_type_all_variants() -> None:
    assert _normalize_type("decision") == "Decision"
    assert _normalize_type("DECISION") == "Decision"
    assert _normalize_type("DeciSion") == "Decision"
    assert _normalize_type("flow") == "Flow"
    assert _normalize_type("TESTCASE") == "TestCase"
    assert _normalize_type("unknown_type") == "unknown_type"


# -- ID generation edge cases --------------------------------------------------


def test_slug_very_long_name() -> None:
    slug = make_id_slug("A" * 100)
    assert len(slug) <= 40


def test_slug_only_special_chars() -> None:
    slug = make_id_slug("!@#$%^&*()")
    assert slug == "" or slug.strip("_") == ""


def test_generate_id_invalid_testkind() -> None:
    eid = generate_external_id("TestCase", "My Test", "invalid_kind")
    assert ".test.unit." in eid


def test_generate_id_empty_name() -> None:
    eid = generate_external_id("Flow", "")
    assert ".ops." in eid
    assert len(eid.split(".")[-1]) == 8


# -- Session ID format ---------------------------------------------------------


def test_session_id_new_format(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    r = asyncio.run(
        dispatch("session:start actor='test' goal='format test'", index, gobp_root)
    )
    assert r["ok"] is True
    sid = r["session_id"]
    assert sid.startswith("meta.session."), f"Wrong format: {sid}"
    assert len(sid.split(".")) == 4


# -- Module split verification -------------------------------------------------


def test_parser_module_importable() -> None:
    from gobp.mcp.parser import _normalize_type as nt
    from gobp.mcp.parser import parse_query as pq

    assert callable(pq)
    assert callable(nt)


def test_read_governance_importable() -> None:
    from gobp.mcp.tools.read_governance import metadata_lint, schema_governance

    assert callable(schema_governance)
    assert callable(metadata_lint)


def test_read_priority_importable() -> None:
    from gobp.mcp.tools.read_priority import recompute_priorities

    assert callable(recompute_priorities)


def test_read_interview_importable() -> None:
    from gobp.mcp.tools.read_interview import node_interview, node_template

    assert callable(node_template)
    assert callable(node_interview)


# -- Edge creation edge cases --------------------------------------------------


def test_create_edge_missing_from(gobp_root: Path, core_edges_schema: dict[str, Any]) -> None:
    init_project(gobp_root, force=True)
    with pytest.raises(ValueError, match="validation failed"):
        create_edge(
            gobp_root,
            {"to": "node:b", "type": "relates_to"},
            core_edges_schema,
        )


def test_create_edge_empty_type(gobp_root: Path, core_edges_schema: dict[str, Any]) -> None:
    init_project(gobp_root, force=True)
    with pytest.raises(ValueError, match="validation failed"):
        create_edge(
            gobp_root,
            {"from": "node:a", "to": "node:b", "type": ""},
            core_edges_schema,
        )


# -- migrate_ids dry-run --------------------------------------------------------


def test_migrate_project_empty_project(gobp_root: Path) -> None:
    """Fresh fixture: no node markdown files yet."""
    from gobp.core.migrate_ids import migrate_project

    r = migrate_project(gobp_root, dry_run=True)
    assert r.get("dry_run") is True
    assert r["migrated"] == 0
    assert r["errors"] == []


def test_migrate_project_dry_run_after_init(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    from gobp.core.migrate_ids import migrate_project

    r = migrate_project(gobp_root, dry_run=True)
    assert r.get("dry_run") is True
    assert isinstance(r["id_mapping"], dict)
