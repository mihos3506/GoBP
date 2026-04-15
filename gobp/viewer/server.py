"""GoBP Graph Viewer HTTP server.

Serves index.html and /api/graph endpoint.
Read-only — never writes to GoBP data.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any


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

    # Build node list
    nodes = []
    for node in index.all_nodes():
        nodes.append({
            "id": node.get("id", ""),
            "name": node.get("name", ""),
            "type": node.get("type", "Node"),
            "priority": node.get("priority", "medium"),
            "status": node.get("status", "ACTIVE"),
            "description": node.get("description", "")[:200],
            "topic": node.get("topic", ""),
            "group": node.get("group", ""),
        })

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
            if self.path == "/api/graph" or self.path == "/api/graph?refresh=1":
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
