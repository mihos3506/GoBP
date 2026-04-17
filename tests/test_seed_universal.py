"""Tests for seed-universal repair and id_groups merge."""

from __future__ import annotations

import yaml
from pathlib import Path

from gobp.core.graph import GraphIndex
from gobp.core.id_config import DEFAULT_GROUPS, merge_id_groups_with_defaults
from gobp.core.init import INIT_SCHEMA_VERSION, init_project, seed_universal_nodes, sync_config_schema_version
import asyncio

from gobp.mcp.dispatcher import dispatch
from gobp.mcp.parser import parse_query


def test_seed_universal_only_missing_restores_deleted(tmp_path: Path) -> None:
    init_project(tmp_path, force=True)
    unit = tmp_path / ".gobp" / "nodes" / "testkind_unit.md"
    assert unit.exists()
    unit.unlink()
    out = seed_universal_nodes(tmp_path, only_missing=True)
    assert "testkind:unit" in out["created"]
    assert unit.exists()


def test_seed_universal_only_missing_skips_existing(tmp_path: Path) -> None:
    init_project(tmp_path, force=True)
    out = seed_universal_nodes(tmp_path, only_missing=True)
    assert out["created"] == []
    assert len(out["skipped"]) == 17


def test_merge_id_groups_adds_missing_type(tmp_path: Path) -> None:
    init_project(tmp_path, force=True)
    cfg_path = tmp_path / ".gobp" / "config.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    groups = raw["id_groups"]
    groups["test"]["types"] = [t for t in groups["test"]["types"] if t != "TestKind"]
    cfg_path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    res = merge_id_groups_with_defaults(tmp_path)
    assert res["ok"] and res["changed"]
    raw2 = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert "TestKind" in raw2["id_groups"]["test"]["types"]


def test_merge_id_groups_replaces_empty_block(tmp_path: Path) -> None:
    init_project(tmp_path, force=True)
    cfg_path = tmp_path / ".gobp" / "config.yaml"
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    raw["id_groups"] = {}
    cfg_path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    res = merge_id_groups_with_defaults(tmp_path)
    assert res["ok"] and res["changed"]
    raw2 = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert raw2["id_groups"].keys() == DEFAULT_GROUPS.keys()


def test_create_testkind_gets_defaults(tmp_path: Path) -> None:
    init_project(tmp_path, force=True)
    index = GraphIndex.load_from_disk(tmp_path)
    sid = asyncio.run(dispatch("session:start actor='t' goal='t'", index, tmp_path))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    q = (
        f"create:TestKind name='Custom Kind' session_id={sid} "
        "id='testkind:custom_acme'"
    )
    r = asyncio.run(dispatch(q, index, tmp_path))
    assert r.get("ok"), r
    index = GraphIndex.load_from_disk(tmp_path)
    node = index.get_node("testkind:custom_acme")
    assert node is not None
    assert node.get("group") == "functional"
    assert node.get("scope") == "project"
    assert isinstance(node.get("template"), dict)


def test_sync_config_schema_version_bumps_when_low(tmp_path: Path) -> None:
    init_project(tmp_path, force=True)
    cfg = tmp_path / ".gobp" / "config.yaml"
    raw = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    raw["schema_version"] = 1
    cfg.write_text(
        yaml.safe_dump(raw, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    out = sync_config_schema_version(tmp_path)
    assert out["ok"] and out.get("changed")
    raw2 = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert raw2["schema_version"] == INIT_SCHEMA_VERSION


def test_parse_create_handoff_types() -> None:
    a, t, p = parse_query("create:CtoDevHandoff name='m' session_id='s'")
    assert a == "create" and t == "CtoDevHandoff" and p.get("name") == "m"
    a2, t2, p2 = parse_query("create:QaCodeDevHandoff name='q' session_id='s'")
    assert t2 == "QaCodeDevHandoff"


def test_create_ctodev_handoff_node(tmp_path: Path) -> None:
    init_project(tmp_path, force=True)
    index = GraphIndex.load_from_disk(tmp_path)
    sid = asyncio.run(dispatch("session:start actor='t' goal='t'", index, tmp_path))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    q = f"create:CtoDevHandoff name='Thread head' session_id={sid} id='ctodev:thread_a'"
    r = asyncio.run(dispatch(q, index, tmp_path))
    assert r.get("ok"), r
    index = GraphIndex.load_from_disk(tmp_path)
    n = index.get_node("ctodev:thread_a")
    assert n and n.get("type") == "CtoDevHandoff"
    assert n.get("status") == "OPEN"
