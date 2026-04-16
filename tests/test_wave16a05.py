"""Tests for Wave 16A05: project identity, Task queue, MCP generator."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch


# ── Project identity tests ────────────────────────────────────────────────────


def test_init_creates_project_name(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    config = yaml.safe_load((gobp_root / ".gobp" / "config.yaml").read_text(encoding="utf-8"))
    assert "project_name" in config


def test_overview_returns_project_name(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    r = asyncio.run(dispatch("overview:", index, gobp_root))
    assert r["ok"] is True
    assert "project" in r
    assert "name" in r["project"]
    assert r["project"]["name"]


def test_overview_project_name_from_config(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    cfg_path = gobp_root / ".gobp" / "config.yaml"
    config = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    config["project_name"] = "TestProject"
    cfg_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")

    index = GraphIndex.load_from_disk(gobp_root)
    r = asyncio.run(dispatch("overview:", index, gobp_root))
    assert r["project"]["name"] == "TestProject"


# ── Task node tests ───────────────────────────────────────────────────────────


def test_create_task_node(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(
        dispatch("session:start actor='test' goal='task test'", index, gobp_root)
    )
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(
        dispatch(
            f"create:Task name='Build auth flow' assignee='cursor' wave='8B' session_id='{sid}'",
            index,
            gobp_root,
        )
    )
    assert r["ok"] is True
    assert ".meta." in r["node_id"]


def test_task_id_format(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(
        dispatch("session:start actor='test' goal='task id test'", index, gobp_root)
    )
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(
        dispatch(
            f"create:Task name='Verify Gate Flow' assignee='cursor' session_id='{sid}'",
            index,
            gobp_root,
        )
    )
    node_id = r["node_id"]
    assert ".meta." in node_id
    assert "verify_gate_flow" in node_id or "task" in node_id


def test_task_default_status_pending(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(
        dispatch("session:start actor='test' goal='task status test'", index, gobp_root)
    )
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(
        dispatch(
            f"create:Task name='My Task' session_id='{sid}'",
            index,
            gobp_root,
        )
    )
    task_id = r["node_id"]
    index2 = GraphIndex.load_from_disk(gobp_root)
    node = index2.get_node(task_id)
    assert node is not None
    assert node.get("status") == "PENDING"


# ── tasks: action tests ───────────────────────────────────────────────────────


def test_tasks_action_returns_pending(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(
        dispatch("session:start actor='test' goal='tasks action test'", index, gobp_root)
    )
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    asyncio.run(
        dispatch(
            f"create:Task name='Task A' assignee='cursor' session_id='{sid}'",
            index,
            gobp_root,
        )
    )
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch("tasks:", index, gobp_root))
    assert r["ok"] is True
    assert "tasks" in r
    assert r["count"] >= 1


def test_tasks_filter_by_assignee(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(
        dispatch("session:start actor='test' goal='assignee filter test'", index, gobp_root)
    )
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    asyncio.run(
        dispatch(
            f"create:Task name='Cursor Task' assignee='cursor' session_id='{sid}'",
            index,
            gobp_root,
        )
    )
    asyncio.run(
        dispatch(
            f"create:Task name='Haiku Task' assignee='haiku' session_id='{sid}'",
            index,
            gobp_root,
        )
    )
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch("tasks: assignee='haiku'", index, gobp_root))
    assert r["ok"] is True
    for t in r["tasks"]:
        assert t["assignee"] == "haiku"


def test_tasks_protocol_guide_has_entries() -> None:
    from gobp.mcp.parser import PROTOCOL_GUIDE

    actions = PROTOCOL_GUIDE.get("actions", {})
    assert any("tasks:" in k for k in actions)


# ── Viewer config endpoint tests ──────────────────────────────────────────────


def test_suggest_db_name() -> None:
    from gobp.viewer.server import _suggest_db_name

    assert _suggest_db_name("D:/GoBP") == "gobp"
    assert _suggest_db_name("D:/MIHOS-v1") == "gobp_mihos"
    assert _suggest_db_name("D:/MyProject") == "gobp_myproject"


def test_suggest_db_name_strips_version() -> None:
    from gobp.viewer.server import _suggest_db_name

    assert _suggest_db_name("D:/MIHOS-v1") == "gobp_mihos"
    assert _suggest_db_name("D:/App-v2") == "gobp_app"
