"""GoBP Graph Viewer HTTP server.

Serves index.html, /api/graph, /api/projects, and /api/config.
Read-only — never writes to GoBP data.
"""

from __future__ import annotations

import json
import re as _re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any


def _suggest_db_name(project_root: str) -> str:
    """Suggest DB name from project folder name."""
    folder = Path(project_root).name.lower()
    folder = _re.sub(r"[^a-z0-9]", "_", folder).strip("_")
    folder = _re.sub(r"_v\d+$", "", folder)  # remove _v1, _v2
    return f"gobp_{folder}" if folder != "gobp" else "gobp"


def _get_python_path() -> str:
    """Return current Python executable path with forward slashes."""
    import sys

    return sys.executable.replace("\\", "/")


def _api_config_payload(gobp_root: Path) -> dict[str, Any]:
    """Build JSON object for GET /api/config (MCP Generator)."""
    import yaml as _yaml

    config: dict[str, Any] = {}
    config_path = gobp_root / ".gobp" / "config.yaml"
    if config_path.exists():
        try:
            config = _yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception:
            pass

    root_str = str(gobp_root).replace("\\", "/")
    return {
        "project_root": root_str,
        "project_name": config.get("project_name", gobp_root.name),
        "project_id": config.get("project_id", gobp_root.name.lower()),
        "project_description": config.get("project_description", ""),
        "python_path": _get_python_path(),
        "suggested_db": _suggest_db_name(root_str),
        "suggested_mcp_key": "gobp-" + gobp_root.name.lower().replace("_", "-"),
        "db_host": "postgresql://postgres:Hieu%408283%40@localhost",
    }


def _respond_json(handler: BaseHTTPRequestHandler, data: dict[str, Any]) -> None:
    """Write a JSON response with CORS headers."""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _dashboard_payload(project_root: Path) -> dict[str, Any]:
    """Build JSON for GET /api/dashboard (stats + recent sessions)."""
    from gobp.core.graph import GraphIndex

    index = GraphIndex.load_from_disk(project_root)
    all_nodes = list(index.all_nodes())
    all_edges = list(index.all_edges())

    nodes_by_group: dict[str, int] = {}
    for node in all_nodes:
        group = (node.get("group") or "Unknown").strip()
        if not group:
            top = "Unknown"
        elif ">" in group:
            top = group.split(">")[0].strip() or "Unknown"
        else:
            top = group
        nodes_by_group[top] = nodes_by_group.get(top, 0) + 1

    sessions_raw = [n for n in all_nodes if n.get("type") == "Session"]

    def _session_sort_key(n: dict[str, Any]) -> str:
        return str(
            n.get("updated")
            or n.get("updated_at")
            or n.get("created")
            or n.get("id")
            or ""
        )

    sessions_raw.sort(key=_session_sort_key, reverse=True)
    recent_sessions = [
        {
            "id": n.get("id", ""),
            "goal": (n.get("goal") or "")[:80],
            "status": n.get("status", ""),
            "actor": n.get("actor", ""),
        }
        for n in sessions_raw[:5]
    ]

    return {
        "ok": True,
        "stats": {
            "total_nodes": len(all_nodes),
            "total_edges": len(all_edges),
            "nodes_by_group": nodes_by_group,
        },
        "recent_sessions": recent_sessions,
    }


def _load_graph_data(project_root: Path) -> dict[str, Any]:
    """Load nodes and edges from .gobp/ folder.

    Returns graph data formatted for 3d-force-graph:
    {
        nodes: [{id, name, type, priority, status, ...}],
        links: [{source, target, type}]
    }
    """
    from gobp.core.graph import GraphIndex

    index = GraphIndex.load_from_disk(project_root)

    # Build node list (full node payloads for viewer v2 detail panel)
    nodes = []
    for node in index.all_nodes():
        payload = dict(node)
        payload.setdefault("priority", node.get("priority", "medium"))
        payload.setdefault("status", node.get("status", "ACTIVE"))
        nodes.append(payload)

    # Build edge list (3d-force-graph uses 'source'/'target')
    links = []
    seen = set()
    for edge in index.all_edges():
        from_id = edge.get("from", "")
        to_id = edge.get("to", "")
        edge_type = edge.get("type", "relates_to")
        key = f"{from_id}_{edge_type}_{to_id}"
        if key not in seen and from_id and to_id:
            links.append({
                "source": from_id,  # for 3d-force-graph rendering
                "target": to_id,    # for 3d-force-graph rendering
                "from": from_id,    # for detail panel relations
                "to": to_id,        # for detail panel relations
                "type": edge_type,
                "reason": edge.get("reason", ""),
            })
            seen.add(key)

    config = {}
    config_path = project_root / ".gobp" / "config.yaml"
    if config_path.exists():
        import yaml

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    return {
        "nodes": nodes,
        "links": links,
        "meta": {
            "project_name": config.get("project_name", project_root.name),
            "node_count": len(nodes),
            "link_count": len(links),
        },
    }


def make_handler(project_root: Path, viewer_dir: Path):
    """Create request handler with project_root in closure."""

    class ViewerHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Suppress default access log
            pass

        def do_GET(self):
            path_only = self.path.split("?", 1)[0]
            if path_only == "/dashboard":
                self._serve_file(viewer_dir / "dashboard.html", "text/html")
            elif path_only == "/api/dashboard":
                try:
                    data = _dashboard_payload(project_root)
                    _respond_json(self, data)
                except Exception as e:
                    _respond_json(self, {"ok": False, "error": str(e)})
            elif path_only == "/api/projects":
                # Same shape as multi-project server so index.html boots cleanly.
                one = {
                    "name": project_root.name,
                    "root": str(project_root.resolve()),
                }
                body = json.dumps([one], ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            elif path_only == "/api/config":
                _respond_json(self, _api_config_payload(project_root))
            elif self.path == "/api/graph" or self.path == "/api/graph?refresh=1":
                self._serve_graph()
            elif self.path in ("/", "/index.html"):
                self._serve_file(viewer_dir / "index.html", "text/html")
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")

        def _serve_graph(self):
            try:
                data = _load_graph_data(project_root)
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                error = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(error)

        def _serve_file(self, path: Path, content_type: str):
            if not path.exists():
                self.send_response(404)
                self.end_headers()
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ViewerHandler


def make_multi_handler(projects: list[dict[str, str]], viewer_dir: Path):
    """Handler that supports ?root= query param and /api/projects endpoint."""
    from urllib.parse import parse_qs, urlparse

    class MultiViewerHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            params = parse_qs(parsed.query)

            if path == "/api/projects":
                self._serve_json(projects)
            elif path == "/dashboard":
                self._serve_file(viewer_dir / "dashboard.html", "text/html")
            elif path == "/api/dashboard":
                root_param = params.get("root", [None])[0]
                if root_param:
                    proj_root = Path(root_param)
                else:
                    proj_root = Path(projects[0]["root"]) if projects else Path.cwd()
                try:
                    data = _dashboard_payload(proj_root)
                    self._serve_json(data)
                except Exception as e:
                    err = json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(err)
            elif path == "/api/config":
                root_param = params.get("root", [None])[0]
                if root_param:
                    cfg_root = Path(root_param)
                else:
                    cfg_root = Path(projects[0]["root"]) if projects else Path.cwd()
                _respond_json(self, _api_config_payload(cfg_root))
            elif path == "/api/graph":
                root_param = params.get("root", [None])[0]
                if root_param:
                    project_root = Path(root_param)
                else:
                    project_root = Path(projects[0]["root"]) if projects else Path.cwd()
                self._serve_graph(project_root)
            elif path in ("/", "/index.html"):
                self._serve_file(viewer_dir / "index.html", "text/html")
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")

        def _serve_json(self, data: object):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _serve_graph(self, project_root: Path):
            try:
                data = _load_graph_data(project_root)
                self._serve_json(data)
            except Exception as e:
                error = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(error)

        def _serve_file(self, path: Path, content_type: str):
            if not path.exists():
                self.send_response(404)
                self.end_headers()
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return MultiViewerHandler


def run_server(project_root: Path, port: int = 8080) -> None:
    """Start HTTP server. Blocks until Ctrl+C."""
    viewer_dir = Path(__file__).parent
    handler = make_handler(project_root, viewer_dir)

    server = HTTPServer(("localhost", port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n◈ GoBP viewer stopped.")
    finally:
        server.server_close()


def run_server_with_projects(projects_path: Path, port: int = 8080) -> None:
    """Start HTTP server with multi-project support."""
    projects = json.loads(projects_path.read_text(encoding="utf-8"))
    viewer_dir = Path(__file__).parent

    handler = make_multi_handler(projects, viewer_dir)
    server = HTTPServer(("localhost", port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n◈ GoBP viewer stopped.")
    finally:
        server.server_close()
