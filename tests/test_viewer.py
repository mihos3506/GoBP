"""Tests for gobp/viewer — HTTP server and graph API."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from gobp.core.init import init_project
from gobp.viewer.server import _load_graph_data, make_handler, run_server


# -- _load_graph_data tests ----------------------------------------------------

def test_load_graph_data_returns_structure(gobp_root: Path) -> None:
    """_load_graph_data returns nodes, links, meta."""
    init_project(gobp_root, force=True)
    data = _load_graph_data(gobp_root)
    assert "nodes" in data
    assert "links" in data
    assert "meta" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["links"], list)


def test_load_graph_data_has_seed_nodes(gobp_root: Path) -> None:
    """After init, graph has 17 seed nodes."""
    init_project(gobp_root, force=True)
    data = _load_graph_data(gobp_root)
    assert data["meta"]["node_count"] == 17
    assert len(data["nodes"]) == 17


def test_load_graph_data_node_fields(gobp_root: Path) -> None:
    """Nodes have required fields for 3d-force-graph."""
    init_project(gobp_root, force=True)
    data = _load_graph_data(gobp_root)
    for node in data["nodes"]:
        assert "id" in node
        assert "name" in node
        assert "type" in node
        assert "priority" in node


def test_load_graph_data_links_format(gobp_root: Path) -> None:
    """Links use source/target (not from/to) for 3d-force-graph."""
    init_project(gobp_root, force=True)
    data = _load_graph_data(gobp_root)
    for link in data["links"]:
        assert "source" in link
        assert "target" in link
        assert "type" in link


def test_load_graph_meta(gobp_root: Path) -> None:
    """Meta includes project_name, node_count, link_count."""
    init_project(gobp_root, project_name="TestProject", force=True)
    data = _load_graph_data(gobp_root)
    assert data["meta"]["project_name"] == "TestProject"
    assert data["meta"]["node_count"] == 17
    assert isinstance(data["meta"]["link_count"], int)


# -- HTTP server tests ---------------------------------------------------------

@pytest.fixture
def viewer_server(gobp_root: Path):
    """Start viewer server in background thread."""
    init_project(gobp_root, force=True)
    viewer_dir = Path(__file__).parent.parent / "gobp" / "viewer"
    handler = make_handler(gobp_root, viewer_dir)

    from http.server import HTTPServer

    server = HTTPServer(("localhost", 0), handler)  # port 0 = random free port
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)  # let server start

    yield port

    server.shutdown()


def test_api_graph_returns_200(viewer_server) -> None:
    """GET /api/graph returns 200 with JSON."""
    import urllib.request
    port = viewer_server
    with urllib.request.urlopen(f"http://localhost:{port}/api/graph") as resp:
        assert resp.status == 200
        data = json.loads(resp.read())
        assert "nodes" in data
        assert "links" in data


def test_index_html_returns_200(viewer_server) -> None:
    """GET / returns 200 HTML."""
    import urllib.request
    port = viewer_server
    with urllib.request.urlopen(f"http://localhost:{port}/") as resp:
        assert resp.status == 200
        content = resp.read().decode()
        assert "GoBP" in content
        assert "3d-force-graph" in content


def test_dashboard_html_returns_200(viewer_server) -> None:
    """GET /dashboard returns 200 HTML."""
    import urllib.request
    port = viewer_server
    with urllib.request.urlopen(f"http://localhost:{port}/dashboard") as resp:
        assert resp.status == 200
        content = resp.read().decode()
        assert "Dashboard" in content


def test_api_dashboard_returns_ok(viewer_server) -> None:
    """GET /api/dashboard returns JSON with ok and stats."""
    import urllib.request
    port = viewer_server
    with urllib.request.urlopen(f"http://localhost:{port}/api/dashboard") as resp:
        assert resp.status == 200
        data = json.loads(resp.read())
        assert data.get("ok") is True
        assert "stats" in data
        assert data["stats"]["total_nodes"] == 17
        assert "recent_sessions" in data


def test_api_projects_single_root_returns_one_entry(viewer_server, gobp_root: Path) -> None:
    """GET /api/projects works in single-project mode (matches multi-server shape)."""
    import urllib.request
    port = viewer_server
    with urllib.request.urlopen(f"http://localhost:{port}/api/projects") as resp:
        assert resp.status == 200
        data = json.loads(resp.read())
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == gobp_root.name
        assert Path(data[0]["root"]).resolve() == gobp_root.resolve()


def test_unknown_path_returns_404(viewer_server) -> None:
    """GET /unknown returns 404."""
    import urllib.request
    import urllib.error
    port = viewer_server
    try:
        urllib.request.urlopen(f"http://localhost:{port}/unknown")
        assert False, "Should have raised"
    except urllib.error.HTTPError as e:
        assert e.code == 404


# -- Multi-project server tests -------------------------------------------------

@pytest.fixture
def multi_viewer_server(tmp_path: Path):
    """Start multi-project viewer server."""
    import json as _json
    from http.server import HTTPServer

    from gobp.viewer.server import make_multi_handler

    root1 = tmp_path / "proj1"
    root2 = tmp_path / "proj2"
    root1.mkdir()
    root2.mkdir()
    init_project(root1, project_name="Project1", force=True)
    init_project(root2, project_name="Project2", force=True)

    projects = [
        {"name": "Project1", "root": str(root1)},
        {"name": "Project2", "root": str(root2)},
    ]
    projects_path = tmp_path / "projects.json"
    projects_path.write_text(_json.dumps(projects), encoding="utf-8")

    viewer_dir = Path(__file__).parent.parent / "gobp" / "viewer"
    projs = _json.loads(projects_path.read_text(encoding="utf-8"))
    handler = make_multi_handler(projs, viewer_dir)

    server = HTTPServer(("localhost", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    yield port, str(root1), str(root2)
    server.shutdown()


def test_api_projects_returns_list(multi_viewer_server) -> None:
    """GET /api/projects returns list of projects."""
    import urllib.request

    port, _, _ = multi_viewer_server
    with urllib.request.urlopen(f"http://localhost:{port}/api/projects") as resp:
        data = json.loads(resp.read())
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == "Project1"


def test_api_graph_with_root_param(multi_viewer_server) -> None:
    """GET /api/graph?root=PATH returns correct project graph."""
    import urllib.request
    from urllib.parse import quote

    port, root1, _ = multi_viewer_server
    url1 = f"http://localhost:{port}/api/graph?root={quote(root1)}"
    with urllib.request.urlopen(url1) as resp:
        data = json.loads(resp.read())
        assert data["meta"]["node_count"] == 17
        assert data["meta"]["project_name"] == "Project1"


def test_edges_have_both_formats(multi_viewer_server) -> None:
    """Edges have source/target AND from/to."""
    import urllib.request
    from urllib.parse import quote

    port, root1, _ = multi_viewer_server
    url = f"http://localhost:{port}/api/graph?root={quote(root1)}"
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read())
        for link in data.get("links", []):
            assert "source" in link
            assert "target" in link
            assert "from" in link
            assert "to" in link


def test_launcher_find_projects_json() -> None:
    """find_projects_json() finds projects.json in expected locations."""
    from gobp.viewer.launcher import find_projects_json

    result = find_projects_json()
    assert result is None or result.exists()
