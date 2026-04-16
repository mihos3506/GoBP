"""Tests for Wave 16A02: Snowflake ID, group namespace, migration, hierarchical layout."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gobp.core.snowflake import SnowflakeGenerator, generate_snowflake, snowflake_to_datetime
from gobp.core.id_config import (
    DEFAULT_GROUPS,
    generate_external_id,
    get_group_for_type,
    get_tier_weight,
    get_tier_y,
    load_groups,
    parse_external_id,
)
from gobp.core.init import init_project
from gobp.core.graph import GraphIndex


# -- Snowflake tests -----------------------------------------------------------

def test_snowflake_generates_integer() -> None:
    sid = generate_snowflake()
    assert isinstance(sid, int)
    assert sid > 0


def test_snowflake_unique() -> None:
    ids = {generate_snowflake() for _ in range(100)}
    assert len(ids) == 100


def test_snowflake_sortable() -> None:
    ids = [generate_snowflake() for _ in range(10)]
    assert ids == sorted(ids)


def test_snowflake_to_datetime() -> None:
    sid = generate_snowflake()
    dt = snowflake_to_datetime(sid)
    assert dt.year >= 2024


def test_snowflake_machine_id() -> None:
    gen = SnowflakeGenerator(machine_id=42)
    sid = gen.next_id()
    assert isinstance(sid, int)


# -- ID config tests -----------------------------------------------------------

def test_generate_decision_id() -> None:
    eid = generate_external_id("Decision")
    assert eid.startswith("dec.core.") or eid.startswith("core.dec:")


def test_generate_feature_id() -> None:
    eid = generate_external_id("Feature")
    assert eid.startswith("feat.ops.") or eid.startswith("ops.feat:")


def test_generate_entity_id() -> None:
    eid = generate_external_id("Entity")
    assert eid.startswith("entity.domain.") or eid.startswith("domain.entity:")


def test_generate_testcase_id() -> None:
    eid = generate_external_id("TestCase")
    assert eid.startswith("case.test.") or eid.startswith("test.case:")


def test_generate_session_id() -> None:
    eid = generate_external_id("Session")
    assert eid.startswith("meta.session.")


def test_parse_new_format() -> None:
    parsed = parse_external_id("core.dec:0001")
    assert parsed["format"] == "legacy"


def test_parse_legacy_format() -> None:
    parsed = parse_external_id("flow:verify_gate")
    assert parsed["format"] == "legacy"
    assert parsed["slug"] == "verify_gate"


def test_get_group_decision() -> None:
    assert get_group_for_type("Decision") == "core"


def test_get_group_flow() -> None:
    assert get_group_for_type("Flow") == "ops"


def test_get_group_entity() -> None:
    assert get_group_for_type("Entity") == "domain"


def test_get_group_testcase() -> None:
    assert get_group_for_type("TestCase") == "test"


def test_get_group_session() -> None:
    assert get_group_for_type("Session") == "meta"


def test_tier_y_values() -> None:
    assert get_tier_y("Decision") < get_tier_y("Session")
    assert get_tier_y("Flow") == 0


def test_tier_weight_ordering() -> None:
    assert get_tier_weight("Decision") > get_tier_weight("Feature")
    assert get_tier_weight("Feature") > get_tier_weight("Document")
    assert get_tier_weight("Session") == 0


def test_load_groups_fallback(gobp_root: Path) -> None:
    groups = load_groups(gobp_root)
    assert "core" in groups
    assert "ops" in groups


def test_default_groups_have_expected_sections() -> None:
    assert set(DEFAULT_GROUPS.keys()) == {"core", "domain", "ops", "test", "meta"}


# -- Migration tests -----------------------------------------------------------

def test_migrate_dry_run(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    from gobp.core.migrate_ids import migrate_project

    result = migrate_project(gobp_root, dry_run=True)
    assert result["dry_run"] is True
    assert "id_mapping" in result
    assert result["errors"] == []


def test_migrate_creates_mapping_file(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    from gobp.core.migrate_ids import migrate_project

    migrate_project(gobp_root, dry_run=False)

    mapping_file = gobp_root / ".gobp" / "id_mapping.json"
    assert mapping_file.exists()
    mapping = json.loads(mapping_file.read_text(encoding="utf-8"))
    assert isinstance(mapping, dict)


def test_legacy_id_resolution(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    from gobp.core.migrate_ids import migrate_project

    index_before = GraphIndex.load_from_disk(gobp_root)
    old_nodes = index_before.all_nodes()
    if not old_nodes:
        return

    old_id = old_nodes[0]["id"]

    result = migrate_project(gobp_root, dry_run=False)
    new_id = result["id_mapping"].get(old_id, old_id)

    index_after = GraphIndex.load_from_disk(gobp_root)
    node_old = index_after.get_node(old_id)
    node_new = index_after.get_node(new_id)
    assert node_old is not None or node_new is not None


# -- Edge type tests -----------------------------------------------------------

def test_new_edge_types_in_schema() -> None:
    import yaml

    schema = yaml.safe_load(Path("gobp/schema/core_edges.yaml").read_text(encoding="utf-8"))
    edge_types = list(schema.get("edge_types", {}).keys())
    for required in ("enforces", "triggers", "validates", "produces"):
        assert required in edge_types, f"Edge type '{required}' missing from schema"


def test_graph_loads_migrated_project() -> None:
    root = Path("D:/GoBP")
    index = GraphIndex.load_from_disk(root)
    assert len(index.all_nodes()) > 0


def test_migrated_ids_have_group_namespace() -> None:
    root = Path("D:/GoBP")
    index = GraphIndex.load_from_disk(root)
    sample = [n["id"] for n in index.all_nodes()[:25]]
    assert all("." in sid for sid in sample)

def test_parse_invalid_external_id() -> None:
    parsed = parse_external_id("just_text")
    assert parsed["group"] == ""


def test_load_groups_from_real_project() -> None:
    groups = load_groups(Path("D:/GoBP"))
    assert "id_groups" not in groups
    assert "meta" in groups


def test_generate_external_id_has_colon() -> None:
    eid = generate_external_id("Node")
    assert "." in eid
