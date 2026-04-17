"""Tests for Wave 4: CLI, schema v2, TestKind/TestCase/Concept, find type filter, gobp_overview concepts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from gobp.core.graph import GraphIndex
from gobp.core.init import INIT_SCHEMA_VERSION, init_project
from gobp.mcp.tools import read as tools_read


# ── init_project tests ────────────────────────────────────────────────────────


def test_init_creates_structure(tmp_path: Path) -> None:
    """init_project creates all .gobp/ subdirs."""
    result = init_project(tmp_path)
    assert result["ok"] is True
    assert (tmp_path / ".gobp" / "nodes").is_dir()
    assert (tmp_path / ".gobp" / "edges").is_dir()
    assert (tmp_path / ".gobp" / "history").is_dir()


def test_init_config_schema_version_2(tmp_path: Path) -> None:
    """config.yaml has schema_version=2."""
    init_project(tmp_path)
    config = yaml.safe_load((tmp_path / ".gobp" / "config.yaml").read_text())
    assert config["schema_version"] == 2
    assert INIT_SCHEMA_VERSION == 2


def test_init_config_multiuser_placeholders(tmp_path: Path) -> None:
    """config.yaml has multi-user placeholder fields all null/empty."""
    init_project(tmp_path)
    config = yaml.safe_load((tmp_path / ".gobp" / "config.yaml").read_text())
    assert "owner" in config and config["owner"] is None
    assert "collaborators" in config and config["collaborators"] == []
    assert "access_model" in config and config["access_model"] == "open"
    assert "project_id" in config
    assert config["project_id"] == str(config["project_name"]).lower().replace(" ", "-")
    assert "project_description" in config and config["project_description"] == ""


def test_init_seeds_17_nodes(gobp_root: Path) -> None:
    """gobp init seeds 16 TestKind + 1 Concept = 17 nodes."""
    result = init_project(gobp_root, force=True)
    assert result["ok"] is True
    seeded = result.get("seeded_nodes", [])
    assert len(seeded) == 17
    assert len([s for s in seeded if s.startswith("testkind:")]) == 16
    assert len([s for s in seeded if s.startswith("concept:")]) == 1


def test_init_seeded_kinds_loadable(gobp_root: Path) -> None:
    """Seeded TestKind nodes load correctly via GraphIndex."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    kinds = [n for n in index.all_nodes() if n.get("type") == "TestKind"]
    assert len(kinds) == 16


def test_init_all_groups_present(gobp_root: Path) -> None:
    """All 4 groups present in seeded TestKind nodes."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    groups = {n.get("group") for n in index.all_nodes() if n.get("type") == "TestKind"}
    assert "functional" in groups
    assert "non_functional" in groups
    assert "security" in groups
    assert "process" in groups


def test_init_security_kinds_count(gobp_root: Path) -> None:
    """Security group has exactly 5 TestKind nodes."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    sec = [
        n
        for n in index.all_nodes()
        if n.get("type") == "TestKind" and n.get("group") == "security"
    ]
    assert len(sec) == 5


def test_init_all_universal_scope(gobp_root: Path) -> None:
    """All seeded TestKind nodes have scope=universal."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    for node in index.all_nodes():
        if node.get("type") == "TestKind":
            assert node.get("scope") == "universal", (
                f"{node['id']} has wrong scope: {node.get('scope')}"
            )


def test_init_fails_if_exists(tmp_path: Path) -> None:
    """Second init without force returns ok=False."""
    init_project(tmp_path)
    result = init_project(tmp_path)
    assert result["ok"] is False
    assert result["already_exists"] is True


def test_init_force_reinits(tmp_path: Path) -> None:
    """Init with force=True succeeds even if .gobp/ exists."""
    init_project(tmp_path)
    result = init_project(tmp_path, force=True)
    assert result["ok"] is True


# ── find() type filter tests ──────────────────────────────────────────────────


def test_find_type_filter_testkind(gobp_root: Path) -> None:
    """find(type='TestKind') returns only TestKind nodes."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "test", "type": "TestKind"})
    assert result["ok"] is True
    for node in result["matches"]:
        assert node["type"] == "TestKind"


def test_find_type_filter_concept(gobp_root: Path) -> None:
    """find(type='Concept') returns only Concept nodes."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "taxonomy", "type": "Concept"})
    assert result["ok"] is True
    for node in result["matches"]:
        assert node["type"] == "Concept"


def test_find_type_filter_security_kinds(gobp_root: Path) -> None:
    """find(query='security', type='TestKind') returns security TestKind nodes."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(
        index, gobp_root, {"query": "security", "type": "TestKind"}
    )
    assert result["ok"] is True
    assert result["count"] >= 1


def test_find_type_filter_no_match(gobp_root: Path) -> None:
    """find(type='Session') returns empty when no sessions exist."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "session", "type": "Session"})
    assert result["ok"] is True
    assert result["count"] == 0


# ── gobp_overview tests ───────────────────────────────────────────────────────


def test_gobp_overview_has_concepts(gobp_root: Path) -> None:
    """gobp_overview returns concepts array with at least 1 entry."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.gobp_overview(index, gobp_root, {})
    assert result["ok"] is True
    assert "concepts" in result
    assert len(result["concepts"]) >= 1


def test_gobp_overview_has_test_coverage(gobp_root: Path) -> None:
    """gobp_overview returns test_coverage with 16 kinds."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.gobp_overview(index, gobp_root, {})
    assert result["ok"] is True
    assert "test_coverage" in result
    tc = result["test_coverage"]
    assert tc["kinds_available"] == 16
    assert "security" in tc["kinds_by_group"]
    assert tc["kinds_by_group"]["functional"] == 1  # acceptance
    assert tc["kinds_by_group"]["process"] == 7
    assert tc["kinds_by_group"]["non_functional"] == 3
    assert tc["kinds_by_group"]["security"] == 5


# ── CLI subprocess tests ──────────────────────────────────────────────────────


def _cli(args: list[str], env_root: str | None = None) -> tuple[int, str, str]:
    import os

    env = os.environ.copy()
    if env_root:
        env["GOBP_PROJECT_ROOT"] = env_root
    r = subprocess.run(
        [sys.executable, "-m", "gobp.cli"] + args,
        capture_output=True,
        text=True,
        env=env,
    )
    return r.returncode, r.stdout, r.stderr


def test_cli_help() -> None:
    rc, out, _ = _cli(["--help"])
    assert rc == 0
    assert "init" in out and "validate" in out and "status" in out


def test_cli_init_creates_project(tmp_path: Path) -> None:
    rc, out, err = _cli(["init", "--name", "test"], env_root=str(tmp_path))
    assert rc == 0, f"err: {err}"
    assert (tmp_path / ".gobp" / "nodes").is_dir()


def test_cli_init_prints_seeded_count(tmp_path: Path) -> None:
    rc, out, _ = _cli(["init"], env_root=str(tmp_path))
    assert rc == 0
    assert "17" in out or "Seeded" in out


def test_cli_status_shows_nodes(tmp_path: Path) -> None:
    init_project(tmp_path)
    rc, out, err = _cli(["status"], env_root=str(tmp_path))
    assert rc == 0, f"err: {err}"
    assert "nodes" in out.lower() or "GoBP" in out


def test_cli_validate_clean_project(tmp_path: Path) -> None:
    init_project(tmp_path)
    rc, out, err = _cli(["validate"], env_root=str(tmp_path))
    assert rc == 0, f"err: {err}\nout: {out}"
