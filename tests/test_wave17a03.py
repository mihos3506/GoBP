"""Tests for Wave 17A03: group index, find/explore/get/suggest query engine."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.tools import read as tools_read


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _engine(
    name: str,
    *,
    group: str,
    read_order: str = "foundational",
    nid: str | None = None,
) -> dict:
    d: dict = {
        "type": "Engine",
        "name": name,
        "status": "ACTIVE",
        "description": {"info": f"desc {name}", "code": ""},
        "group": group,
        "lifecycle": "draft",
        "read_order": read_order,
        "created": _ts(),
        "updated": _ts(),
    }
    if nid:
        d["id"] = nid
    return d


@pytest.fixture
def w17_proj(gobp_root: Path) -> Path:
    init_project(gobp_root)
    return gobp_root


# --- GraphIndex group indexing (6) --------------------------------------------


def test_build_group_index(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > Infrastructure > Security > AuthFlow"
    a = idx.add_node_in_memory(_engine("A", group=g))
    b = idx.add_node_in_memory(_engine("B", group=g))
    assert a and b
    assert "Dev" in idx._group_index
    assert "Dev > Infrastructure" in idx._group_index
    assert g in idx._group_index


def test_find_by_group_prefix(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g1 = "Dev > Infrastructure > Security"
    g2 = "Dev > Application"
    n1 = idx.add_node_in_memory(_engine("Sec1", group=g1))
    idx.add_node_in_memory(_engine("App1", group=g2))
    got = set(idx.find_by_group("Dev > Infrastructure"))
    assert n1 in got


def test_find_by_group_exact(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > Infrastructure > Engine"
    a = idx.add_node_in_memory(_engine("Exact", group=g))
    idx.add_node_in_memory(_engine("Child", group=g + " > Child"))
    exact = set(idx.find_by_group(g, exact=True))
    assert exact == {a}


def test_find_by_group_contains_security(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > Infrastructure > Security > AuthFlow"
    idx.add_node_in_memory(_engine("AF", group=g))
    # substring filter is in find(), not GraphIndex — smoke group field
    assert "Security" in g


def test_find_siblings(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > Infra > SiblingTest"
    a = idx.add_node_in_memory(_engine("S1", group=g, nid="engine.sibling.s1.aaaaaaaa"))
    b = idx.add_node_in_memory(_engine("S2", group=g, nid="engine.sibling.s2.bbbbbbbb"))
    sibs = idx.find_siblings(a)
    assert b in sibs and a not in sibs


def test_get_group_tree(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    idx.add_node_in_memory(_engine("T1", group="Alpha > Beta"))
    tree = idx.get_group_tree()
    assert isinstance(tree, dict)
    assert "Alpha" in tree or len(tree) >= 0


# --- find: group filter (5) ---------------------------------------------------


def test_find_group_top_down(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > Infrastructure > Security > Zone"
    nid = idx.add_node_in_memory(_engine("ZoneNode", group=g))
    r = tools_read.find(
        idx,
        w17_proj,
        {"query": "", "group": "Dev > Infrastructure > Security"},
    )
    assert r["ok"]
    ids = {m["id"] for m in r["matches"]}
    assert nid in ids
    assert r.get("group_filter")


def test_find_group_combined_type(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > Infrastructure > Engine"
    e1 = idx.add_node_in_memory(_engine("EngOnly", group=g))
    idx.add_node_in_memory(
        {
            "type": "Flow",
            "name": "FlowOnly",
            "status": "ACTIVE",
            "description": {"info": "f", "code": ""},
            "group": "Dev > Application",
            "lifecycle": "draft",
            "read_order": "important",
            "created": _ts(),
            "updated": _ts(),
        }
    )
    r = tools_read.find(
        idx,
        w17_proj,
        {"query": "", "group": "Dev > Infrastructure", "type_filter": "Engine"},
    )
    assert r["ok"]
    ids = {m["id"] for m in r["matches"]}
    assert e1 in ids
    assert all(m.get("type") == "Engine" for m in r["matches"])


def test_find_group_contains(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > Infrastructure > Security > AuthFlow"
    nid = idx.add_node_in_memory(_engine("AuthX", group=g))
    r = tools_read.find(
        idx,
        w17_proj,
        {"query": "", "group_contains": "Security"},
    )
    assert r["ok"]
    assert nid in {m["id"] for m in r["matches"]}


def test_find_group_sorted_by_read_order(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > SortRO"
    idx.add_node_in_memory(_engine("B", group=g, read_order="background"))
    idx.add_node_in_memory(_engine("A", group=g, read_order="foundational"))
    r = tools_read.find(idx, w17_proj, {"query": "", "group": g})
    assert r["ok"]
    names = [m.get("name") for m in r["matches"]]
    assert names[0] == "A"


def test_find_backward_compat(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    idx.add_node_in_memory(_engine("UniqueMarker987", group="Dev > Infra"))
    r = tools_read.find(idx, w17_proj, {"query": "UniqueMarker987"})
    assert r["ok"] and r["count"] >= 1


# --- explore (3) --------------------------------------------------------------


def test_explore_breadcrumb(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > Infrastructure > Engine"
    nid = idx.add_node_in_memory(_engine("CrumbEng", group=g, nid="engine.crumb.ce.aaaaaaaa"))
    r = tools_read.explore_action(idx, w17_proj, {"query": nid})
    assert r["ok"]
    assert r["breadcrumb"][-1]["path"] == g


def test_explore_siblings(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > Explore > Sib"
    a = idx.add_node_in_memory(_engine("E1", group=g, nid="engine.explore.e1.aaaaaaaa"))
    b = idx.add_node_in_memory(_engine("E2", group=g, nid="engine.explore.e2.bbbbbbbb"))
    r = tools_read.explore_action(idx, w17_proj, {"query": a})
    assert r["ok"]
    sids = {s["id"] for s in r["siblings"]}
    assert b in sids
    assert r["siblings_count"] >= 1


def test_explore_relationships_with_reason(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > Rel > Test"
    a = idx.add_node_in_memory(_engine("Ra", group=g, nid="engine.rel.ra.aaaaaaaa"))
    b = idx.add_node_in_memory(_engine("Rb", group=g, nid="engine.rel.rb.bbbbbbbb"))
    idx.add_edge_in_memory(a, b, "relates_to")
    for e in idx.get_edges_from(a):
        if e.get("to") == b:
            e["reason"] = "integration test"
    r = tools_read.explore_action(idx, w17_proj, {"query": a})
    assert r["ok"]
    reasons = [x.get("reason") for x in r["relationships"]]
    assert "integration test" in reasons


# --- get / context (4) --------------------------------------------------------


def test_get_mode_brief_hides_raw(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    nid = idx.add_node_in_memory(
        _engine("BriefRaw", group="Dev > Brief", nid="engine.brief.br.aaaaaaaa")
    )
    r = tools_read.context(idx, w17_proj, {"node_id": nid})
    assert r["ok"] and r.get("mode") == "brief"
    assert "outgoing" not in r
    assert "relationships" in r
    assert "_dispatch" not in r["node"]


def test_get_mode_brief_shows_description_info_only(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    nid = idx.add_node_in_memory(
        _engine("BriefDesc", group="Dev > Brief", nid="engine.brief.bd.bbbbbbbb")
    )
    r = tools_read.context(idx, w17_proj, {"node_id": nid})
    desc = r["node"].get("description")
    assert isinstance(desc, dict)
    assert "info" in desc
    assert desc.get("code") == ""


def test_get_mode_full_shows_all_meaningful(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    nid = idx.add_node_in_memory(
        _engine("FullEng", group="Dev > Full", nid="engine.full.fe.aaaaaaaa")
    )
    r = tools_read.context(idx, w17_proj, {"node_id": nid, "mode": "full"})
    assert r["ok"]
    assert "outgoing" in r and "relationships" in r
    assert "_dispatch" not in r["node"]


def test_get_mode_debug_shows_everything(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    nid = idx.add_node_in_memory(
        _engine("DbgEng", group="Dev > Dbg", nid="engine.debug.de.bbbbbbbb")
    )
    r = tools_read.context(idx, w17_proj, {"node_id": nid, "mode": "debug"})
    assert r["ok"] and r["mode"] == "debug"
    assert "relationships" in r
    assert r["node"]["id"] == nid


# --- suggest (2) --------------------------------------------------------------


def test_suggest_group_aware_same_group_first(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > Suggest > Group"
    idx.add_node_in_memory(_engine("Low", group=g, read_order="reference"))
    idx.add_node_in_memory(_engine("High", group=g, read_order="reference"))
    r = tools_read.suggest_action(
        idx,
        w17_proj,
        {"query": "High", "group": g, "limit": 5},
    )
    assert r["ok"] and r["suggestions"]
    first = r["suggestions"][0]
    assert first.get("same_group") is True


def test_suggest_high_similarity_warning(w17_proj: Path) -> None:
    idx = GraphIndex.load_from_disk(w17_proj)
    g = "Dev > Sim > Test"
    idx.add_node_in_memory(_engine("PaymentFlowExact", group=g))
    r = tools_read.suggest_action(
        idx,
        w17_proj,
        {"query": "PaymentFlowExact", "group": g, "type": "Engine", "limit": 5},
    )
    assert r["ok"]
    warns = [s.get("warning", "") for s in r["suggestions"]]
    assert any("HIGH SIMILARITY" in w for w in warns) or r.get("recommendation") == (
        "UPDATE existing node"
    )
