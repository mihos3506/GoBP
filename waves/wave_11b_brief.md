# WAVE 11B BRIEF — 3D GRAPH VIEWER

**Wave:** 11B
**Title:** GoBP 3D Graph Viewer — per-project knowledge visualization
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 5 atomic tasks
**Estimated effort:** 3-4 hours

---

## CONTEXT

GoBP stores project knowledge as a graph. Until now, that graph is only accessible via text queries. Wave 11B adds a 3D visual graph viewer — a browser-based app that reads from GoBP's `.gobp/` folder and renders the knowledge graph in 3D.

**Tech stack:**
- `3d-force-graph` library (vasturiano) — WebGL 3D physics graph, built on Three.js
- CDN: `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js` + `3d-force-graph@1`
- Pure HTML + vanilla JS — no build step, no framework
- Python HTTP server to serve files and read `.gobp/` data

**Visual design:**
```
Node size    = priority (critical=large, high=medium, medium=small, low=tiny)
Node color   = type (Decision=amber, Node=cyan, Idea=violet, Session=green,
                     Document=blue, Lesson=red, Concept=gold,
                     TestKind=teal, TestCase=orange)
Node label   = node name (shown on hover)
Node glow    = critical nodes pulse with amber glow (◈ color)
Edge color   = edge type (implements=bright, relates_to=dim, etc.)
Edge width   = edge type weight
Background   = deep space dark (#0a0a0f)
Camera       = auto-rotate slowly when idle, click to focus
```

**Per-project isolation:**
```
python -m gobp.viewer --root D:\GoBP         → GoBP project graph
python -m gobp.viewer --root D:\MIHOS-v1     → MIHOS project graph
```

**Architecture:**
```
gobp/viewer/
  __main__.py    ← CLI entry: python -m gobp.viewer --root PATH --port 8080
  server.py      ← Python HTTP server + /api/graph endpoint
  index.html     ← 3D viewer SPA (single file, all JS inline)
```

**API endpoint:**
```
GET /api/graph
→ Returns {nodes: [...], edges: [...]} from .gobp/ folder
→ Read-only — viewer never writes to GoBP
```

**In scope:**
- `gobp/viewer/__init__.py`
- `gobp/viewer/__main__.py` — CLI entry point
- `gobp/viewer/server.py` — HTTP server + graph API
- `gobp/viewer/index.html` — 3D viewer SPA
- `tests/test_viewer.py` — basic server tests

**NOT in scope:**
- Authentication
- Real-time updates (refresh button is enough for v1)
- Editing nodes from viewer
- MCP integration in viewer

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: all 276 existing tests must pass.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 276 tests passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/core/graph.py` | GraphIndex to read nodes/edges |
| 3 | `gobp/core/loader.py` | load_node_file, load_edge_file |
| 4 | `waves/wave_11b_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Create gobp/viewer/ package

**Goal:** Viewer package with CLI entry point and HTTP server.

**Files to create:**

### `gobp/viewer/__init__.py`
```python
"""GoBP 3D Graph Viewer."""
```

### `gobp/viewer/__main__.py`
```python
"""GoBP 3D Graph Viewer — CLI entry point.

Usage:
    python -m gobp.viewer
    python -m gobp.viewer --root D:/MIHOS-v1
    python -m gobp.viewer --root D:/GoBP --port 8080

Opens browser automatically at http://localhost:8080
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="gobp.viewer",
        description="GoBP 3D Graph Viewer",
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("GOBP_PROJECT_ROOT", str(Path.cwd())),
        help="Project root containing .gobp/ folder",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="HTTP server port (default: 8080)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open browser automatically",
    )
    args = parser.parse_args()

    project_root = Path(args.root).resolve()
    gobp_dir = project_root / ".gobp"

    if not gobp_dir.exists():
        print(
            f"Error: No .gobp/ folder at {project_root}",
            file=sys.stderr,
        )
        print(
            "Run `python -m gobp.cli init` first to initialize a GoBP project.",
            file=sys.stderr,
        )
        return 1

    from gobp.viewer.server import run_server

    url = f"http://localhost:{args.port}"
    print(f"◈ GoBP Graph Viewer")
    print(f"  Project: {project_root.name}")
    print(f"  Root:    {project_root}")
    print(f"  URL:     {url}")
    print(f"\nPress Ctrl+C to stop.")

    if not args.no_browser:
        # Open browser after short delay to let server start
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    run_server(project_root=project_root, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### `gobp/viewer/server.py`

```python
"""GoBP Graph Viewer HTTP server.

Serves index.html and /api/graph endpoint.
Read-only — never writes to GoBP data.
"""

from __future__ import annotations

import json
import os
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
                "source": from_id,
                "target": to_id,
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
        }
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
```

**Acceptance criteria:**
- `gobp/viewer/` package created with 3 files
- `python -m gobp.viewer --help` exits 0
- `python -m gobp.viewer --no-browser` starts server without opening browser
- Server returns 404 for unknown paths

**Commit message:**
```
Wave 11B Task 1: create gobp/viewer package — CLI + HTTP server

- gobp/viewer/__main__.py: CLI entry with --root, --port, --no-browser
- gobp/viewer/server.py: HTTP server + /api/graph endpoint
- /api/graph: reads .gobp/ via GraphIndex, returns {nodes, links, meta}
- Read-only: viewer never writes to GoBP data
```

---

## TASK 2 — Create gobp/viewer/index.html (3D viewer SPA)

**Goal:** Single-file 3D graph viewer. All JS inline. No build step.

**File to create:** `gobp/viewer/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>◈ GoBP Graph Viewer</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --bg: #0a0a0f;
      --surface: #12121a;
      --border: #1e1e2e;
      --text: #e2e8f0;
      --text-dim: #64748b;
      --amber: #f59e0b;
      --cyan: #06b6d4;
      --violet: #8b5cf6;
      --green: #10b981;
      --blue: #3b82f6;
      --red: #ef4444;
      --gold: #eab308;
      --teal: #14b8a6;
      --orange: #f97316;
    }

    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'SF Mono', 'Fira Code', monospace;
      overflow: hidden;
      height: 100vh;
      width: 100vw;
    }

    #graph-container {
      position: fixed;
      inset: 0;
      z-index: 1;
    }

    /* ── Top bar ── */
    #topbar {
      position: fixed;
      top: 0; left: 0; right: 0;
      height: 48px;
      background: rgba(18, 18, 26, 0.9);
      border-bottom: 1px solid var(--border);
      backdrop-filter: blur(12px);
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 0 20px;
      z-index: 10;
    }

    #logo {
      color: var(--amber);
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0.05em;
    }

    #project-name {
      color: var(--text-dim);
      font-size: 13px;
    }

    #stats {
      margin-left: auto;
      display: flex;
      gap: 16px;
      font-size: 12px;
      color: var(--text-dim);
    }

    #stats span { color: var(--text); }

    #refresh-btn {
      background: var(--border);
      border: 1px solid #2a2a3e;
      color: var(--text);
      padding: 4px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-family: inherit;
      transition: all 0.2s;
    }
    #refresh-btn:hover { background: #1e1e2e; border-color: var(--amber); }

    /* ── Side panel ── */
    #panel {
      position: fixed;
      top: 48px; right: 0;
      width: 280px;
      height: calc(100vh - 48px);
      background: rgba(18, 18, 26, 0.92);
      border-left: 1px solid var(--border);
      backdrop-filter: blur(12px);
      display: flex;
      flex-direction: column;
      z-index: 10;
      transform: translateX(100%);
      transition: transform 0.3s ease;
    }

    #panel.open { transform: translateX(0); }

    #panel-header {
      padding: 16px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    #panel-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--amber);
    }

    #panel-close {
      background: none;
      border: none;
      color: var(--text-dim);
      cursor: pointer;
      font-size: 18px;
      line-height: 1;
    }

    #panel-body {
      padding: 16px;
      overflow-y: auto;
      flex: 1;
    }

    .field { margin-bottom: 12px; }
    .field-label {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--text-dim);
      margin-bottom: 4px;
    }
    .field-value {
      font-size: 13px;
      color: var(--text);
      word-break: break-word;
    }

    .priority-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 3px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .priority-critical { background: rgba(245,158,11,0.2); color: var(--amber); }
    .priority-high     { background: rgba(239,68,68,0.15); color: var(--red); }
    .priority-medium   { background: rgba(100,116,139,0.2); color: #94a3b8; }
    .priority-low      { background: rgba(30,30,46,0.8); color: var(--text-dim); }

    /* ── Filter panel ── */
    #filters {
      position: fixed;
      top: 60px; left: 16px;
      background: rgba(18, 18, 26, 0.9);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      z-index: 10;
      backdrop-filter: blur(12px);
      min-width: 160px;
    }

    #filter-title {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--text-dim);
      margin-bottom: 8px;
    }

    .filter-item {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
      cursor: pointer;
      font-size: 12px;
    }

    .filter-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    .filter-item input { cursor: pointer; accent-color: var(--amber); }

    /* ── Search ── */
    #search-wrap {
      position: fixed;
      top: 60px; left: 50%;
      transform: translateX(-50%);
      z-index: 10;
    }

    #search {
      background: rgba(18, 18, 26, 0.9);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 6px 16px;
      color: var(--text);
      font-family: inherit;
      font-size: 13px;
      width: 280px;
      backdrop-filter: blur(12px);
      outline: none;
      transition: border-color 0.2s;
    }
    #search:focus { border-color: var(--amber); }
    #search::placeholder { color: var(--text-dim); }

    /* ── Loading ── */
    #loading {
      position: fixed;
      inset: 0;
      background: var(--bg);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      z-index: 100;
      gap: 16px;
    }

    #loading-logo {
      font-size: 48px;
      color: var(--amber);
      animation: pulse 2s ease-in-out infinite;
    }

    #loading-text {
      color: var(--text-dim);
      font-size: 13px;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.6; transform: scale(0.95); }
    }

    /* ── Tooltip ── */
    #tooltip {
      position: fixed;
      background: rgba(18, 18, 26, 0.95);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 12px;
      font-size: 12px;
      pointer-events: none;
      z-index: 20;
      display: none;
      max-width: 220px;
    }

    #tooltip-name { font-weight: 600; margin-bottom: 2px; }
    #tooltip-type { color: var(--text-dim); font-size: 11px; }
  </style>
</head>
<body>

<div id="loading">
  <div id="loading-logo">◈</div>
  <div id="loading-text">Loading graph...</div>
</div>

<div id="topbar">
  <div id="logo">◈ GoBP</div>
  <div id="project-name">—</div>
  <div id="stats">
    <div>Nodes: <span id="stat-nodes">0</span></div>
    <div>Edges: <span id="stat-edges">0</span></div>
  </div>
  <button id="refresh-btn" onclick="loadGraph()">↺ Refresh</button>
</div>

<div id="search-wrap">
  <input id="search" type="text" placeholder="Search nodes..." oninput="onSearch(this.value)">
</div>

<div id="filters">
  <div id="filter-title">Node Types</div>
  <div id="filter-list"></div>
</div>

<div id="graph-container"></div>

<div id="panel">
  <div id="panel-header">
    <div id="panel-title">Node Detail</div>
    <button id="panel-close" onclick="closePanel()">×</button>
  </div>
  <div id="panel-body" id="panel-content"></div>
</div>

<div id="tooltip">
  <div id="tooltip-name"></div>
  <div id="tooltip-type"></div>
</div>

<!-- 3d-force-graph via CDN -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://unpkg.com/3d-force-graph@1/dist/3d-force-graph.min.js"></script>

<script>
// ── Color config ──────────────────────────────────────────────────────────────
const TYPE_COLORS = {
  Decision:  '#f59e0b',  // amber
  Node:      '#06b6d4',  // cyan
  Idea:      '#8b5cf6',  // violet
  Session:   '#10b981',  // green
  Document:  '#3b82f6',  // blue
  Lesson:    '#ef4444',  // red
  Concept:   '#eab308',  // gold
  TestKind:  '#14b8a6',  // teal
  TestCase:  '#f97316',  // orange
};

const PRIORITY_SIZE = {
  critical: 8,
  high: 5,
  medium: 3,
  low: 2,
};

const EDGE_COLORS = {
  implements:    '#f59e0b88',
  relates_to:    '#ffffff22',
  supersedes:    '#ef444488',
  discovered_in: '#10b98144',
  references:    '#3b82f644',
  covers:        '#8b5cf644',
  of_kind:       '#14b8a644',
};

// ── State ─────────────────────────────────────────────────────────────────────
let graph = null;
let graphData = { nodes: [], links: [] };
let activeFilters = new Set();
let searchQuery = '';

// ── Init graph ────────────────────────────────────────────────────────────────
function initGraph() {
  graph = ForceGraph3D()(document.getElementById('graph-container'))
    .backgroundColor('#0a0a0f')
    .nodeId('id')
    .nodeLabel(node => `${node.name} [${node.type}]`)
    .nodeVal(node => PRIORITY_SIZE[node.priority] || 3)
    .nodeColor(node => {
      const color = TYPE_COLORS[node.type] || '#ffffff';
      // Dim if filtered out
      if (activeFilters.size > 0 && !activeFilters.has(node.type)) {
        return '#ffffff11';
      }
      if (searchQuery && !node.name.toLowerCase().includes(searchQuery)) {
        return '#ffffff11';
      }
      return color;
    })
    .nodeOpacity(0.9)
    .linkSource('source')
    .linkTarget('target')
    .linkColor(link => EDGE_COLORS[link.type] || '#ffffff22')
    .linkWidth(link => link.type === 'implements' ? 1.5 : 0.5)
    .linkDirectionalArrowLength(3)
    .linkDirectionalArrowRelPos(1)
    .linkDirectionalParticles(link => link.type === 'implements' ? 2 : 0)
    .linkDirectionalParticleSpeed(0.004)
    .onNodeClick(node => openPanel(node))
    .onNodeHover(node => {
      document.getElementById('graph-container').style.cursor = node ? 'pointer' : 'default';
      showTooltip(node);
    });
}

// ── Load data ─────────────────────────────────────────────────────────────────
async function loadGraph() {
  try {
    const res = await fetch('/api/graph');
    const data = await res.json();

    graphData = data;

    document.getElementById('project-name').textContent = data.meta?.project_name || '';
    document.getElementById('stat-nodes').textContent = data.meta?.node_count || 0;
    document.getElementById('stat-edges').textContent = data.meta?.link_count || 0;

    buildFilters(data.nodes);
    graph.graphData({ nodes: data.nodes, links: data.links });

    document.getElementById('loading').style.display = 'none';
  } catch (e) {
    document.getElementById('loading-text').textContent = 'Error loading graph: ' + e.message;
  }
}

// ── Filters ───────────────────────────────────────────────────────────────────
function buildFilters(nodes) {
  const types = [...new Set(nodes.map(n => n.type))].sort();
  const list = document.getElementById('filter-list');
  list.innerHTML = '';

  types.forEach(type => {
    const color = TYPE_COLORS[type] || '#ffffff';
    const count = nodes.filter(n => n.type === type).length;
    const item = document.createElement('label');
    item.className = 'filter-item';
    item.innerHTML = `
      <input type="checkbox" checked onchange="toggleFilter('${type}', this.checked)">
      <div class="filter-dot" style="background:${color}"></div>
      <span>${type} <span style="color:#475569">(${count})</span></span>
    `;
    list.appendChild(item);
  });
}

function toggleFilter(type, checked) {
  if (checked) {
    activeFilters.delete(type);
  } else {
    activeFilters.add(type);
  }
  graph.nodeColor(graph.nodeColor()); // force re-render
}

// ── Search ────────────────────────────────────────────────────────────────────
function onSearch(value) {
  searchQuery = value.toLowerCase();
  graph.nodeColor(graph.nodeColor()); // force re-render

  if (searchQuery) {
    const match = graphData.nodes.find(n =>
      n.name.toLowerCase().includes(searchQuery)
    );
    if (match) {
      graph.centerAt(
        match.x, match.y, match.z,
        1000
      );
    }
  }
}

// ── Panel ─────────────────────────────────────────────────────────────────────
function openPanel(node) {
  const panel = document.getElementById('panel');
  const body = document.getElementById('panel-body');

  const priorityClass = `priority-${node.priority || 'medium'}`;

  body.innerHTML = `
    <div class="field">
      <div class="field-label">ID</div>
      <div class="field-value" style="color:#64748b;font-size:11px">${node.id}</div>
    </div>
    <div class="field">
      <div class="field-label">Name</div>
      <div class="field-value">${node.name}</div>
    </div>
    <div class="field">
      <div class="field-label">Type</div>
      <div class="field-value">
        <span style="color:${TYPE_COLORS[node.type] || '#fff'}">${node.type}</span>
      </div>
    </div>
    <div class="field">
      <div class="field-label">Priority</div>
      <div class="field-value">
        <span class="priority-badge ${priorityClass}">${node.priority || 'medium'}</span>
      </div>
    </div>
    <div class="field">
      <div class="field-label">Status</div>
      <div class="field-value" style="color:#94a3b8">${node.status || '—'}</div>
    </div>
    ${node.description ? `
    <div class="field">
      <div class="field-label">Description</div>
      <div class="field-value" style="color:#94a3b8;font-size:12px;line-height:1.5">${node.description}</div>
    </div>` : ''}
    ${node.topic ? `
    <div class="field">
      <div class="field-label">Topic</div>
      <div class="field-value" style="color:#64748b;font-size:11px">${node.topic}</div>
    </div>` : ''}
    <div class="field" style="margin-top:16px;padding-top:16px;border-top:1px solid #1e1e2e">
      <div class="field-label">GoBP Query</div>
      <div class="field-value" style="color:#f59e0b;font-size:11px;background:#0a0a0f;padding:8px;border-radius:4px;margin-top:4px">
        gobp(query="get: ${node.id}")
      </div>
    </div>
  `;

  panel.classList.add('open');

  // Focus camera on node
  graph.centerAt(node.x, node.y, node.z, 1000);
  graph.zoom(2, 1000);
}

function closePanel() {
  document.getElementById('panel').classList.remove('open');
}

// ── Tooltip ───────────────────────────────────────────────────────────────────
function showTooltip(node) {
  const tooltip = document.getElementById('tooltip');
  if (!node) {
    tooltip.style.display = 'none';
    return;
  }
  document.getElementById('tooltip-name').textContent = node.name;
  document.getElementById('tooltip-type').textContent = `${node.type} · ${node.priority || 'medium'}`;
  tooltip.style.display = 'block';
}

document.addEventListener('mousemove', e => {
  const tooltip = document.getElementById('tooltip');
  if (tooltip.style.display !== 'none') {
    tooltip.style.left = (e.clientX + 12) + 'px';
    tooltip.style.top = (e.clientY - 8) + 'px';
  }
});

// ── Boot ──────────────────────────────────────────────────────────────────────
initGraph();
loadGraph();
</script>
</body>
</html>
```

**Acceptance criteria:**
- `gobp/viewer/index.html` created
- Single file, all JS inline
- Loads from `/api/graph`
- Shows nodes with type colors + priority sizes
- Filter panel by node type
- Search bar highlights matching nodes
- Click node → side panel with details
- Refresh button reloads graph
- Loading screen while fetching

**Commit message:**
```
Wave 11B Task 2: create gobp/viewer/index.html — 3D graph SPA

- 3d-force-graph via CDN (Three.js r128)
- Node color = type, node size = priority
- Filter panel by node type (left sidebar)
- Search bar with node highlighting
- Click node → detail panel (right sidebar)
- Loading screen, refresh button
- Dark theme: deep space (#0a0a0f) + amber accent (◈ color)
```

---

## TASK 3 — Smoke test the viewer

**Goal:** Verify server starts and serves graph data.

```powershell
# Test CLI help
D:/GoBP/venv/Scripts/python.exe -m gobp.viewer --help

# Test server starts (kill after 3 seconds)
$job = Start-Job {
    $env:GOBP_PROJECT_ROOT = "D:\GoBP"
    D:/GoBP/venv/Scripts/python.exe -m gobp.viewer --no-browser --root D:\GoBP
}
Start-Sleep 3

# Test /api/graph endpoint
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/api/graph" -TimeoutSec 2
    $data = $response.Content | ConvertFrom-Json
    Write-Host "Nodes:" $data.meta.node_count
    Write-Host "Edges:" $data.meta.link_count
    Write-Host "API OK"
} catch {
    Write-Host "API test failed: $_"
}

Stop-Job $job
Remove-Job $job

# All existing tests still pass
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 276 tests passing
```

**Commit message:**
```
Wave 11B Task 3: smoke test viewer — server starts, API responds

- python -m gobp.viewer --help: OK
- /api/graph returns {nodes, links, meta}
- 276 existing tests passing
```

---

## TASK 4 — Create tests/test_viewer.py

**Goal:** Basic tests for viewer server.

**File to create:** `tests/test_viewer.py`

```python
"""Tests for gobp/viewer — HTTP server and graph API."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from gobp.core.init import init_project
from gobp.viewer.server import _load_graph_data, make_handler, run_server


# ── _load_graph_data tests ────────────────────────────────────────────────────

def test_load_graph_data_returns_structure(gobp_root: Path):
    """_load_graph_data returns nodes, links, meta."""
    init_project(gobp_root, force=True)
    data = _load_graph_data(gobp_root)
    assert "nodes" in data
    assert "links" in data
    assert "meta" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["links"], list)


def test_load_graph_data_has_seed_nodes(gobp_root: Path):
    """After init, graph has 17 seed nodes."""
    init_project(gobp_root, force=True)
    data = _load_graph_data(gobp_root)
    assert data["meta"]["node_count"] == 17
    assert len(data["nodes"]) == 17


def test_load_graph_data_node_fields(gobp_root: Path):
    """Nodes have required fields for 3d-force-graph."""
    init_project(gobp_root, force=True)
    data = _load_graph_data(gobp_root)
    for node in data["nodes"]:
        assert "id" in node
        assert "name" in node
        assert "type" in node
        assert "priority" in node


def test_load_graph_data_links_format(gobp_root: Path):
    """Links use source/target (not from/to) for 3d-force-graph."""
    init_project(gobp_root, force=True)
    data = _load_graph_data(gobp_root)
    for link in data["links"]:
        assert "source" in link
        assert "target" in link
        assert "type" in link


def test_load_graph_meta(gobp_root: Path):
    """Meta includes project_name, node_count, link_count."""
    init_project(gobp_root, project_name="TestProject", force=True)
    data = _load_graph_data(gobp_root)
    assert data["meta"]["project_name"] == "TestProject"
    assert data["meta"]["node_count"] == 17
    assert isinstance(data["meta"]["link_count"], int)


# ── HTTP server tests ─────────────────────────────────────────────────────────

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


def test_api_graph_returns_200(viewer_server):
    """GET /api/graph returns 200 with JSON."""
    import urllib.request
    port = viewer_server
    with urllib.request.urlopen(f"http://localhost:{port}/api/graph") as resp:
        assert resp.status == 200
        data = json.loads(resp.read())
        assert "nodes" in data
        assert "links" in data


def test_index_html_returns_200(viewer_server):
    """GET / returns 200 HTML."""
    import urllib.request
    port = viewer_server
    with urllib.request.urlopen(f"http://localhost:{port}/") as resp:
        assert resp.status == 200
        content = resp.read().decode()
        assert "GoBP" in content
        assert "3d-force-graph" in content


def test_unknown_path_returns_404(viewer_server):
    """GET /unknown returns 404."""
    import urllib.request, urllib.error
    port = viewer_server
    try:
        urllib.request.urlopen(f"http://localhost:{port}/unknown")
        assert False, "Should have raised"
    except urllib.error.HTTPError as e:
        assert e.code == 404
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_viewer.py -v
# Expected: ~9 tests passing
```

**Commit message:**
```
Wave 11B Task 4: create tests/test_viewer.py — ~9 tests

- _load_graph_data: structure, seed nodes, node fields, links format, meta
- HTTP server: /api/graph returns 200 + JSON, / returns HTML, 404 for unknown
```

---

## TASK 5 — Full suite + CHANGELOG

```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 285+ tests passing (276 + ~9)
```

**Update CHANGELOG.md:**

```markdown
## [Wave 11B] — 3D Graph Viewer — 2026-04-15

### Added
- `gobp/viewer/` — 3D graph viewer package
  - `__main__.py` — CLI entry: `python -m gobp.viewer --root PATH`
  - `server.py` — HTTP server + `/api/graph` endpoint
  - `index.html` — 3D graph SPA (3d-force-graph, dark theme, ◈ amber accent)
- `tests/test_viewer.py` — ~9 tests

### Usage
```bash
python -m gobp.viewer --root D:\GoBP
python -m gobp.viewer --root D:\MIHOS-v1 --port 8081
```

Opens browser at `http://localhost:8080`. Press Ctrl+C to stop.

### Visual design
- Node size = priority (critical=large, low=tiny)
- Node color = type (Decision=amber, Node=cyan, Idea=violet, etc.)
- Edge particles for `implements` relationships
- Filter panel by node type
- Search highlights matching nodes
- Click node → detail panel with gobp() query hint
- Dark theme: deep space background + amber ◈ accent

### Per-project isolation
Each `--root` is a separate project graph. Projects never share data.

### Total after wave: 1 MCP tool, 22 actions, 285+ tests
```

**Commit message:**
```
Wave 11B Task 5: full suite green + CHANGELOG updated

- 285+ tests passing
- CHANGELOG: Wave 11B entry with usage + visual design
```

---

# POST-WAVE VERIFICATION

```powershell
# All tests
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

# Viewer starts
D:/GoBP/venv/Scripts/python.exe -m gobp.viewer --root D:\GoBP --no-browser
# Expected: "◈ GoBP Graph Viewer" + server running message

# Git log
git log --oneline | Select-Object -First 7
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief vào repo

```powershell
cd D:\GoBP
# Save wave_11b_brief.md to D:\GoBP\waves\wave_11b_brief.md

git add waves/wave_11b_brief.md
git commit -m "Add Wave 11B Brief — 3D Graph Viewer"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_11b_brief.md first.
Also read gobp/core/graph.py, gobp/core/loader.py.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 5 tasks of Wave 11B sequentially.
R9: all 276 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 11B. Read CLAUDE.md and waves/wave_11b_brief.md.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: gobp/viewer/__init__.py + __main__.py + server.py exist
          python -m gobp.viewer --help exits 0
          /api/graph returns {nodes, links, meta}
- Task 2: gobp/viewer/index.html exists, has 3d-force-graph CDN reference,
          has TYPE_COLORS, PRIORITY_SIZE, filter/search/panel logic
- Task 3: smoke test passed, 276 tests passing
- Task 4: tests/test_viewer.py exists, ~9 tests passing
- Task 5: 285+ tests passing, CHANGELOG updated

Use venv:
  D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

Expected: 285+ tests passing.

Stop on first failure. Report WAVE 11B AUDIT COMPLETE when done.
```

## 4. Push + test viewer

```powershell
cd D:\GoBP
git push origin main

# Test with GoBP project
D:/GoBP/venv/Scripts/python.exe -m gobp.viewer --root D:\GoBP

# Test with MIHOS project (after Wave 8B import)
D:/GoBP/venv/Scripts/python.exe -m gobp.viewer --root D:\MIHOS-v1 --port 8081
```

---

# WHAT COMES NEXT

```
Wave 11B pushed
    ↓
Wave 8B — MIHOS re-import (full toolset)
  import: → Document nodes + priority
  edge: → semantic connections
  code: → link nodes to MIHOS code files
    ↓
View MIHOS graph in 3D:
  python -m gobp.viewer --root D:\MIHOS-v1
```

---

*Wave 11B Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
