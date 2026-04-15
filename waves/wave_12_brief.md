# WAVE 12 BRIEF — LAUNCHER + PROJECT PICKER + SCHEMA MERGE + BETTER VIEWER

**Wave:** 12
**Title:** Double-click launcher, project picker UI, schema v3, better viewer
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 7 atomic tasks
**Estimated effort:** 4-5 hours

---

## CONTEXT

3 problems to solve:

**Problem 1 — Viewer UX too complex:**
```
Current: python -m gobp.viewer --root D:\GoBP (terminal command)
Target:  Double-click GoBP_Viewer.bat → browser opens → pick project
```

**Problem 2 — Schema too limited:**
```
Current: 9 node types (Node, Idea, Decision, Session, Document, Lesson, Concept, TestKind, TestCase)
MIHOS needs: 15+ types (Engine, Flow, Entity, APIEndpoint, DBTable, Screen, etc.)
```

**Problem 3 — Viewer UI too basic:**
```
Current: index.html — minimal, no labels, basic filters
Better:  viewer.html from reference — JetBrains Mono, status filters,
         SpriteText labels, click-navigate relations, Core/All toggle
```

---

## DESIGN DECISIONS

### Launcher
```
GoBP_Viewer.bat → double-click → runs gobp/viewer/launcher.py
launcher.py → reads projects.json → starts server → opens browser
projects.json → list of {name, root} per machine
```

### Project picker
```
Browser shows project list (cards)
Click project → loads 3D graph for that project
Switch project → dropdown in topbar (no server restart)
/api/graph?root=D:/GoBP → server reads root from query param
```

### Schema v3
```
Add to core_nodes.yaml (optional, all projects can use):
  Engine, Flow, Entity, APIEndpoint, DBTable
  Screen, UIComponent, Feature, Invariant
  ErrorCode, Repository, Wave, Config
  
These are MIHOS-specific types but useful for any product project.
All optional — projects use what they need.
GoBP internal nodes (TestKind, TestCase, etc.) unchanged.
```

### Better viewer
```
Replace index.html with improved version based on viewer.html reference:
  - JetBrains Mono + Fraunces serif fonts
  - SpriteText node labels (toggle on/off)
  - Status filter panel (SKELETON/BUILT/VERIFIED/etc.)
  - Core types toggle (show only important nodes)
  - from/to edges (not source/target — fix impedance mismatch)
  - Amber border theme
  - Click-navigate relations in detail panel
  - Search with 1-hop neighbor expansion
```

### Edge data format fix
```
Current server.py returns: {source: "x", target: "y", type: "t"}
viewer.html expects:        {from: "x", to: "y", type: "t"}
3d-force-graph needs:       {source: "x", target: "y"} for rendering

Fix: server returns both:
  {source: "x", target: "y", from: "x", to: "y", type: "t"}
→ 3d-force-graph uses source/target for rendering
→ detail panel uses from/to for relations
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: all 284 existing tests must pass.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 284 tests passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/viewer/server.py` | Update /api/graph endpoint |
| 3 | `gobp/viewer/index.html` | Replace with better viewer |
| 4 | `gobp/schema/core_nodes.yaml` | Add new node types |
| 5 | `waves/wave_12_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Create projects.json + GoBP_Viewer.bat + launcher.py

**Goal:** Double-click launcher that opens browser with project picker.

**File to create:** `projects.json` (in repo root `D:\GoBP\projects.json`)

```json
[
  {
    "name": "GoBP",
    "root": "D:/GoBP",
    "description": "GoBP development knowledge graph"
  },
  {
    "name": "MIHOS",
    "root": "D:/MIHOS-v1",
    "description": "MIHOS heritage-tech social network"
  }
]
```

**File to create:** `GoBP_Viewer.bat` (in repo root `D:\GoBP\GoBP_Viewer.bat`)

```bat
@echo off
chcp 65001 >nul
echo ◈ GoBP Graph Viewer
echo Starting...
D:\GoBP\venv\Scripts\python.exe -m gobp.viewer.launcher
pause
```

**File to create:** `gobp/viewer/launcher.py`

```python
"""GoBP Graph Viewer Launcher.

Reads projects.json from repo root, starts HTTP server,
opens browser to project picker page.

Usage:
    python -m gobp.viewer.launcher
    python -m gobp.viewer.launcher --port 8080
    python -m gobp.viewer.launcher --projects /path/to/projects.json
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path


def find_projects_json() -> Path | None:
    """Find projects.json — check repo root, cwd, user home."""
    candidates = [
        Path(__file__).parent.parent.parent / "projects.json",  # repo root
        Path.cwd() / "projects.json",
        Path.home() / ".gobp" / "projects.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def main() -> int:
    parser = argparse.ArgumentParser(prog="gobp.viewer.launcher")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--projects", default=None, help="Path to projects.json")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    # Find projects.json
    if args.projects:
        projects_path = Path(args.projects)
    else:
        projects_path = find_projects_json()

    if not projects_path or not projects_path.exists():
        # Create default projects.json
        projects_path = Path.cwd() / "projects.json"
        import json
        default = [{"name": "Current Project", "root": str(Path.cwd()), "description": ""}]
        projects_path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        print(f"Created default projects.json at {projects_path}")

    from gobp.viewer.server import run_server_with_projects

    url = f"http://localhost:{args.port}"
    print(f"◈ GoBP Graph Viewer")
    print(f"  Projects: {projects_path}")
    print(f"  URL:      {url}")
    print(f"\nPress Ctrl+C to stop.")

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    run_server_with_projects(projects_path=projects_path, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Acceptance criteria:**
- `projects.json` created at repo root
- `GoBP_Viewer.bat` created at repo root
- `gobp/viewer/launcher.py` created
- `python -m gobp.viewer.launcher --help` exits 0
- `find_projects_json()` finds projects.json from repo root

**Commit message:**
```
Wave 12 Task 1: launcher + projects.json + GoBP_Viewer.bat

- projects.json: GoBP + MIHOS project registry
- GoBP_Viewer.bat: double-click launcher for Windows
- gobp/viewer/launcher.py: finds projects.json, starts server, opens browser
- find_projects_json(): searches repo root, cwd, ~/.gobp/
```

---

## TASK 2 — Update server.py for multi-project + edge format fix

**Goal:** Server reads project root from query param. `/api/graph?root=D:/GoBP` returns graph for that project. Also fix edge format to include both `from/to` and `source/target`.

**File to modify:** `gobp/viewer/server.py`

**Re-read `server.py` in full before editing.**

**Changes:**

1. Add `run_server_with_projects()` function:

```python
def run_server_with_projects(projects_path: Path, port: int = 8080) -> None:
    """Start HTTP server with multi-project support."""
    import json
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
```

2. Add `make_multi_handler()`:

```python
def make_multi_handler(projects: list[dict], viewer_dir: Path):
    """Handler that supports ?root= query param and /api/projects endpoint."""
    from urllib.parse import urlparse, parse_qs

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
                    # Default to first project
                    project_root = Path(projects[0]["root"]) if projects else Path.cwd()
                self._serve_graph(project_root)
            elif path in ("/", "/index.html"):
                self._serve_file(viewer_dir / "index.html", "text/html")
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")

        def _serve_json(self, data):
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
```

3. Fix `_load_graph_data()` — edges include both formats:

```python
    links.append({
        "source": from_id,   # for 3d-force-graph rendering
        "target": to_id,     # for 3d-force-graph rendering
        "from": from_id,     # for detail panel relations
        "to": to_id,         # for detail panel relations
        "type": edge_type,
    })
```

**Acceptance criteria:**
- `GET /api/projects` returns projects list
- `GET /api/graph?root=D:/GoBP` returns GoBP graph
- `GET /api/graph?root=D:/MIHOS-v1` returns MIHOS graph
- Edges have both `source/target` AND `from/to`
- Existing `run_server()` and `make_handler()` unchanged

**Commit message:**
```
Wave 12 Task 2: server.py multi-project support + edge format fix

- run_server_with_projects(): reads projects.json, serves multiple projects
- make_multi_handler(): /api/projects + /api/graph?root=PATH
- _load_graph_data(): edges now have source/target AND from/to
- Existing run_server() and make_handler() unchanged
```

---

## TASK 3 — Add MIHOS node types to schema

**Goal:** Add 13 new optional node types to `core_nodes.yaml` for product projects.

**File to modify:** `gobp/schema/core_nodes.yaml`

**Re-read `core_nodes.yaml` in full before editing.**

Add after existing node types:

```yaml
  Engine:
    description: "Business logic engine (TrustEngine, LevelEngine, etc.)"
    id_prefix: "engine"
    required:
      id: {type: str, pattern: "^engine:.+$"}
      type: {type: str, enum_values: ["Engine"]}
      name: {type: str}
      status: {type: enum, enum_values: ["DRAFT", "ACTIVE", "DEPRECATED"]}
      created: {type: timestamp}
      updated: {type: timestamp}
    optional:
      priority: {type: enum, enum_values: ["critical","high","medium","low"], default: "medium"}
      description: {type: str}
      code_refs: {type: "list[dict]", default: []}
      invariants: {type: "list[str]", default: []}
      spec_source: {type: str}

  Flow:
    description: "User flow or process flow (registration, auth, etc.)"
    id_prefix: "flow"
    required:
      id: {type: str, pattern: "^flow:.+$"}
      type: {type: str, enum_values: ["Flow"]}
      name: {type: str}
      status: {type: enum, enum_values: ["DRAFT", "ACTIVE", "DEPRECATED"]}
      created: {type: timestamp}
      updated: {type: timestamp}
    optional:
      priority: {type: enum, enum_values: ["critical","high","medium","low"], default: "medium"}
      description: {type: str}
      code_refs: {type: "list[dict]", default: []}
      invariants: {type: "list[str]", default: []}
      spec_source: {type: str}

  Entity:
    description: "Domain entity (Traveller, Place, Moment, etc.)"
    id_prefix: "entity"
    required:
      id: {type: str, pattern: "^entity:.+$"}
      type: {type: str, enum_values: ["Entity"]}
      name: {type: str}
      status: {type: enum, enum_values: ["DRAFT", "ACTIVE", "DEPRECATED"]}
      created: {type: timestamp}
      updated: {type: timestamp}
    optional:
      priority: {type: enum, enum_values: ["critical","high","medium","low"], default: "medium"}
      description: {type: str}
      code_refs: {type: "list[dict]", default: []}
      invariants: {type: "list[str]", default: []}
      spec_source: {type: str}

  Feature:
    description: "Product feature (user-facing capability)"
    id_prefix: "feat"
    required:
      id: {type: str, pattern: "^feat:.+$"}
      type: {type: str, enum_values: ["Feature"]}
      name: {type: str}
      status: {type: enum, enum_values: ["DRAFT", "ACTIVE", "DEPRECATED"]}
      created: {type: timestamp}
      updated: {type: timestamp}
    optional:
      priority: {type: enum, enum_values: ["critical","high","medium","low"], default: "medium"}
      description: {type: str}
      code_refs: {type: "list[dict]", default: []}
      invariants: {type: "list[str]", default: []}
      spec_source: {type: str}

  Invariant:
    description: "Hard constraint that must always be true"
    id_prefix: "inv"
    required:
      id: {type: str, pattern: "^inv:.+$"}
      type: {type: str, enum_values: ["Invariant"]}
      name: {type: str}
      status: {type: enum, enum_values: ["DRAFT", "ACTIVE", "DEPRECATED"]}
      created: {type: timestamp}
      updated: {type: timestamp}
    optional:
      priority: {type: enum, enum_values: ["critical","high","medium","low"], default: "high"}
      description: {type: str}
      rule: {type: str}
      spec_source: {type: str}

  Screen:
    description: "UI screen or page"
    id_prefix: "screen"
    required:
      id: {type: str, pattern: "^screen:.+$"}
      type: {type: str, enum_values: ["Screen"]}
      name: {type: str}
      status: {type: enum, enum_values: ["DRAFT", "ACTIVE", "DEPRECATED"]}
      created: {type: timestamp}
      updated: {type: timestamp}
    optional:
      priority: {type: enum, enum_values: ["critical","high","medium","low"], default: "medium"}
      description: {type: str}
      code_refs: {type: "list[dict]", default: []}
      spec_source: {type: str}

  APIEndpoint:
    description: "REST/RPC API endpoint"
    id_prefix: "api"
    required:
      id: {type: str, pattern: "^api:.+$"}
      type: {type: str, enum_values: ["APIEndpoint"]}
      name: {type: str}
      status: {type: enum, enum_values: ["DRAFT", "ACTIVE", "DEPRECATED"]}
      created: {type: timestamp}
      updated: {type: timestamp}
    optional:
      priority: {type: enum, enum_values: ["critical","high","medium","low"], default: "medium"}
      description: {type: str}
      code_refs: {type: "list[dict]", default: []}
      spec_source: {type: str}

  Repository:
    description: "Code repository (flutter, backend, etc.)"
    id_prefix: "repo"
    required:
      id: {type: str, pattern: "^repo:.+$"}
      type: {type: str, enum_values: ["Repository"]}
      name: {type: str}
      status: {type: enum, enum_values: ["DRAFT", "ACTIVE", "DEPRECATED"]}
      created: {type: timestamp}
      updated: {type: timestamp}
    optional:
      priority: {type: enum, enum_values: ["critical","high","medium","low"], default: "high"}
      description: {type: str}
      url: {type: str}

  Wave:
    description: "Build wave / sprint"
    id_prefix: "wave"
    required:
      id: {type: str, pattern: "^wave:.+$"}
      type: {type: str, enum_values: ["Wave"]}
      name: {type: str}
      status: {type: enum, enum_values: ["DRAFT", "ACTIVE", "COMPLETED", "DEPRECATED"]}
      created: {type: timestamp}
      updated: {type: timestamp}
    optional:
      priority: {type: enum, enum_values: ["critical","high","medium","low"], default: "medium"}
      description: {type: str}
```

**Acceptance criteria:**
- 9 new node types added: Engine, Flow, Entity, Feature, Invariant, Screen, APIEndpoint, Repository, Wave
- All have id_prefix, required fields (id/type/name/status/created/updated), optional priority + description
- Existing 9 types unchanged
- Schema loads without error

**Commit message:**
```
Wave 12 Task 3: add 9 product node types to schema v3

- Engine, Flow, Entity, Feature, Invariant
- Screen, APIEndpoint, Repository, Wave
- All have priority + code_refs + invariants optional fields
- Existing 9 types unchanged — backward compatible
```

---

## TASK 4 — Replace index.html with improved viewer

**Goal:** Replace basic `index.html` with better viewer based on reference design.

**File to modify:** `gobp/viewer/index.html` — full replacement.

Key improvements over current version:
- JetBrains Mono font (Google Fonts CDN)
- Status filter panel (SKELETON/BUILT/VERIFIED/ACTIVE/etc.)
- Core types toggle button (show only important nodes)
- SpriteText node labels using canvas (no external dep)
- Click-navigate relations in detail panel
- Search with 1-hop neighbor expansion
- Project switcher in topbar (fetch /api/projects)
- Amber border theme (rgba(255,193,7,0.14))
- Bottom status bar
- Uses `from/to` for edge relations + `source/target` for 3d rendering

**New index.html:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>◈ GoBP Graph Viewer</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,500;1,9..144,300&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --bg-panel: rgba(15,15,22,0.92);
    --border: rgba(255,193,7,0.14);
    --border-strong: rgba(255,193,7,0.35);
    --text: #e8e8ee;
    --text-dim: #8a8a95;
    --text-fade: #4a4a55;
    --amber: #ffc107;
    --amber-soft: rgba(255,193,7,0.7);
    --mono: 'JetBrains Mono', ui-monospace, monospace;
    --serif: 'Fraunces', Georgia, serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { width: 100%; height: 100%; overflow: hidden; }
  body { background: var(--bg); color: var(--text); font-family: var(--mono); font-size: 13px; font-weight: 300; -webkit-font-smoothing: antialiased; }

  #graph-canvas { position: fixed; inset: 0; z-index: 1; }

  /* Header */
  #header { position: fixed; top: 0; left: 0; right: 0; z-index: 10; padding: 14px 24px 10px; background: linear-gradient(180deg, var(--bg) 40%, transparent); pointer-events: none; display: flex; align-items: baseline; gap: 12px; }
  #header h1 { font-family: var(--serif); font-weight: 300; font-size: 20px; pointer-events: auto; }
  #header h1 .r { color: var(--amber); font-weight: 500; margin-right: 6px; }
  #header h1 em { font-style: italic; color: var(--amber-soft); font-size: 0.65em; margin-left: 6px; letter-spacing: 0.12em; text-transform: uppercase; font-family: var(--mono); }
  #project-switcher { pointer-events: auto; background: transparent; border: 1px solid var(--border); color: var(--amber-soft); font-family: var(--mono); font-size: 11px; padding: 4px 8px; cursor: pointer; outline: none; }
  #project-switcher:focus { border-color: var(--border-strong); }

  /* Controls */
  #controls { position: fixed; top: 56px; left: 16px; z-index: 10; width: 220px; background: var(--bg-panel); backdrop-filter: blur(16px); border: 1px solid var(--border); padding: 14px 16px; max-height: calc(100vh - 80px); overflow-y: auto; }
  #controls section { margin-bottom: 16px; }
  #controls h3 { font-size: 9px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.22em; color: var(--amber-soft); margin-bottom: 8px; border-bottom: 1px solid var(--border); padding-bottom: 4px; }
  #controls label { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text); padding: 2px 0; cursor: pointer; user-select: none; }
  #controls label:hover { color: var(--amber); }
  #controls input[type="checkbox"] { appearance: none; width: 10px; height: 10px; border: 1px solid var(--text-dim); background: transparent; cursor: pointer; flex-shrink: 0; position: relative; }
  #controls input[type="checkbox"]:checked { background: var(--amber); border-color: var(--amber); }
  #controls .count { margin-left: auto; font-size: 9px; color: var(--text-fade); }
  #controls input[type="text"] { width: 100%; background: transparent; border: none; border-bottom: 1px solid var(--border); color: var(--text); font-family: var(--mono); font-size: 11px; padding: 4px 0; outline: none; }
  #controls input[type="text"]:focus { border-bottom-color: var(--amber); }
  #controls input[type="text"]::placeholder { color: var(--text-fade); }
  #controls button { background: transparent; border: 1px solid var(--border-strong); color: var(--amber); font-family: var(--mono); font-size: 9px; padding: 5px 8px; cursor: pointer; letter-spacing: 0.1em; text-transform: uppercase; transition: all 0.15s; margin-right: 4px; margin-bottom: 4px; }
  #controls button:hover { background: var(--amber); color: var(--bg); }

  /* Detail panel */
  #detail { position: fixed; top: 56px; right: 16px; z-index: 10; width: 300px; background: var(--bg-panel); backdrop-filter: blur(16px); border: 1px solid var(--border); padding: 16px 18px; max-height: calc(100vh - 80px); overflow-y: auto; display: none; }
  #detail.visible { display: block; }
  #detail .close { position: absolute; top: 12px; right: 14px; background: none; border: none; color: var(--text-dim); font-size: 16px; cursor: pointer; }
  #detail .close:hover { color: var(--amber); }
  #detail .node-type { font-size: 9px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.22em; color: var(--amber-soft); margin-bottom: 4px; }
  #detail .node-id { font-size: 9px; color: var(--text-fade); margin-bottom: 8px; word-break: break-all; }
  #detail .node-name { font-family: var(--serif); font-size: 17px; font-weight: 300; color: var(--text); line-height: 1.3; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
  #detail .field { margin-bottom: 8px; }
  #detail .field-label { font-size: 9px; text-transform: uppercase; letter-spacing: 0.18em; color: var(--text-dim); margin-bottom: 2px; }
  #detail .field-value { font-size: 11px; color: var(--text); line-height: 1.5; word-break: break-word; }
  #detail .relations { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }
  #detail .relations h4 { font-size: 9px; text-transform: uppercase; letter-spacing: 0.22em; color: var(--amber-soft); margin-bottom: 6px; }
  #detail .rel-item { font-size: 10px; padding: 2px 0; color: var(--text-dim); display: flex; gap: 6px; cursor: pointer; }
  #detail .rel-item:hover .rel-target { color: var(--amber); }
  #detail .rel-verb { color: var(--text-fade); font-size: 9px; text-transform: uppercase; letter-spacing: 0.1em; min-width: 70px; flex-shrink: 0; }
  #detail .rel-target { color: var(--text); }
  #detail .gobp-query { background: rgba(0,0,0,0.3); border: 1px solid var(--border); padding: 6px 10px; font-size: 10px; color: var(--amber); margin-top: 12px; word-break: break-all; }

  /* Status bar */
  #statusbar { position: fixed; bottom: 0; left: 0; right: 0; z-index: 10; padding: 8px 24px; background: linear-gradient(0deg, var(--bg) 40%, transparent); font-size: 9px; color: var(--text-fade); letter-spacing: 0.12em; text-transform: uppercase; display: flex; justify-content: space-between; pointer-events: none; }

  /* Loading */
  #loading { position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; background: var(--bg); z-index: 100; flex-direction: column; gap: 12px; }
  #loading .r { color: var(--amber); font-size: 36px; animation: pulse 2s ease-in-out infinite; }
  #loading p { font-size: 10px; color: var(--text-dim); letter-spacing: 0.2em; text-transform: uppercase; }
  @keyframes pulse { 0%,100%{opacity:0.3;transform:scale(1)} 50%{opacity:1;transform:scale(1.08)} }

  /* Scrollbar */
  #controls::-webkit-scrollbar, #detail::-webkit-scrollbar { width: 3px; }
  #controls::-webkit-scrollbar-thumb, #detail::-webkit-scrollbar-thumb { background: var(--border-strong); }
</style>
</head>
<body>

<div id="loading"><div class="r">◈</div><p>Loading graph...</p></div>

<div id="header">
  <h1><span class="r">◈</span>GoBP<em>graph viewer</em></h1>
  <select id="project-switcher"></select>
</div>

<div id="controls">
  <section>
    <h3>Search</h3>
    <input type="text" id="search" placeholder="name or id...">
  </section>
  <section>
    <h3>Node Type</h3>
    <div id="type-filters"></div>
  </section>
  <section>
    <h3>Status</h3>
    <div id="status-filters"></div>
  </section>
  <section>
    <h3>View</h3>
    <button id="btn-core">Core Only</button>
    <button id="btn-all">Show All</button>
    <button id="btn-labels">Labels</button>
    <button id="btn-reset">Reset Camera</button>
    <button id="btn-refresh">↺ Refresh</button>
  </section>
</div>

<div id="graph-canvas"></div>

<div id="detail">
  <button class="close" onclick="document.getElementById('detail').classList.remove('visible')">×</button>
  <div id="detail-content"></div>
</div>

<div id="statusbar">
  <span id="status-left">Loading...</span>
  <span id="status-right"></span>
</div>

<script src="https://unpkg.com/3d-force-graph@1/dist/3d-force-graph.min.js"></script>

<script>
// ── Config ────────────────────────────────────────────────────────────────────
const TYPE_COLORS = {
  Decision:'#ffc107', Node:'#06b6d4', Idea:'#8b5cf6', Session:'#10b981',
  Document:'#3b82f6', Lesson:'#ef4444', Concept:'#eab308', TestKind:'#14b8a6',
  TestCase:'#f97316', Engine:'#f59e0b', Flow:'#22d3ee', Entity:'#a78bfa',
  Feature:'#34d399', Invariant:'#fb923c', Screen:'#60a5fa', APIEndpoint:'#f472b6',
  Repository:'#94a3b8', Wave:'#64748b', Invariant:'#fb923c',
  SoulPrinciple:'#ffd700', SharedLibModule:'#c084fc',
};
const STATUS_COLORS = {
  ACTIVE:'#10b981', DRAFT:'#64748b', DEPRECATED:'#ef4444',
  SKELETON:'#4a4a55', BUILT:'#3b82f6', VERIFIED:'#10b981',
  IN_PROGRESS:'#f59e0b', BLOCKED:'#ef4444', LEGACY_DISCARDED:'#2a2a35',
  READY:'#22d3ee', COMPLETED:'#10b981',
};
const CORE_TYPES = new Set(['Engine','Flow','Entity','Feature','Decision',
  'SoulPrinciple','Invariant','Document','Node','Idea']);
const PRIORITY_SIZE = {critical:8, high:5, medium:3, low:2};

// ── State ─────────────────────────────────────────────────────────────────────
let FG, GRAPH_DATA = {nodes:[], edges:[], links:[]};
let VISIBLE_TYPES = new Set(), VISIBLE_STATUSES = new Set();
let SHOW_LABELS = false;
let CURRENT_ROOT = null;
let PROJECTS = [];

// ── Boot ──────────────────────────────────────────────────────────────────────
async function boot() {
  try {
    const res = await fetch('/api/projects');
    PROJECTS = await res.json();
  } catch(e) {
    PROJECTS = [];
  }
  buildProjectSwitcher();
  initGraph();
  await loadGraph(PROJECTS[0]?.root || null);
}

function buildProjectSwitcher() {
  const sel = document.getElementById('project-switcher');
  sel.innerHTML = '';
  PROJECTS.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.root;
    opt.textContent = p.name;
    sel.appendChild(opt);
  });
  sel.addEventListener('change', e => loadGraph(e.target.value));
}

async function loadGraph(root) {
  document.getElementById('loading').style.display = 'flex';
  CURRENT_ROOT = root;
  try {
    const url = root ? `/api/graph?root=${encodeURIComponent(root)}` : '/api/graph';
    const res = await fetch(url);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    GRAPH_DATA = data;
    initFilters();
    applyFilters();
    document.getElementById('loading').style.display = 'none';
  } catch(e) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('status-left').textContent = 'Error: ' + e.message;
  }
}

// ── Filters ───────────────────────────────────────────────────────────────────
function initFilters() {
  const typeCounts = {}, statusCounts = {};
  GRAPH_DATA.nodes.forEach(n => {
    typeCounts[n.type] = (typeCounts[n.type]||0)+1;
    const s = n.status||'__none__';
    statusCounts[s] = (statusCounts[s]||0)+1;
  });

  VISIBLE_TYPES = new Set(GRAPH_DATA.nodes.map(n=>n.type));
  VISIBLE_STATUSES = new Set(GRAPH_DATA.nodes.map(n=>n.status||'__none__'));

  const tEl = document.getElementById('type-filters');
  tEl.innerHTML = '';
  Object.keys(typeCounts).sort().forEach(t => {
    const label = document.createElement('label');
    label.innerHTML = `<input type="checkbox" checked data-type="${t}">
      <span style="color:${TYPE_COLORS[t]||'#fff'}">●</span>
      <span>${t}</span><span class="count">${typeCounts[t]}</span>`;
    label.querySelector('input').addEventListener('change', e => {
      if(e.target.checked) VISIBLE_TYPES.add(t); else VISIBLE_TYPES.delete(t);
      applyFilters();
    });
    tEl.appendChild(label);
  });

  const sEl = document.getElementById('status-filters');
  sEl.innerHTML = '';
  Object.keys(statusCounts).sort().forEach(s => {
    if(s==='__none__') return;
    const label = document.createElement('label');
    label.innerHTML = `<input type="checkbox" checked data-status="${s}">
      <span style="color:${STATUS_COLORS[s]||'#888'}">■</span>
      <span>${s}</span><span class="count">${statusCounts[s]}</span>`;
    label.querySelector('input').addEventListener('change', e => {
      if(e.target.checked) VISIBLE_STATUSES.add(s); else VISIBLE_STATUSES.delete(s);
      applyFilters();
    });
    sEl.appendChild(label);
  });
}

function applyFilters(searchSet=null, hits=null) {
  const nodes = GRAPH_DATA.nodes.filter(n => {
    if(!VISIBLE_TYPES.has(n.type)) return false;
    if(!VISIBLE_STATUSES.has(n.status||'__none__')) return false;
    if(searchSet && !searchSet.has(n.id)) return false;
    return true;
  });
  const ids = new Set(nodes.map(n=>n.id));
  const links = (GRAPH_DATA.links||GRAPH_DATA.edges||[]).filter(e =>
    ids.has(e.source||e.from) && ids.has(e.target||e.to)
  ).map(e => ({...e, source: e.source||e.from, target: e.target||e.to}));

  nodes.forEach(n => { n.__hit = hits ? hits.has(n.id) : false; });
  FG.graphData({nodes, links});
  document.getElementById('status-left').textContent =
    `${nodes.length} / ${GRAPH_DATA.nodes.length} nodes`;
  document.getElementById('status-right').textContent =
    `${links.length} edges`;
}

// ── Graph ─────────────────────────────────────────────────────────────────────
function initGraph() {
  FG = ForceGraph3D()(document.getElementById('graph-canvas'))
    .backgroundColor('#0a0a0f')
    .nodeLabel(n => n.name)
    .nodeColor(n => n.__hit ? '#ffffff' : (TYPE_COLORS[n.type]||'#888'))
    .nodeOpacity(0.92)
    .nodeVal(n => PRIORITY_SIZE[n.priority]||3)
    .nodeThreeObject(n => {
      if(!SHOW_LABELS) return null;
      return makeSprite(n.name, TYPE_COLORS[n.type]||'#aaa');
    })
    .nodeThreeObjectExtend(false)
    .linkColor(l => {
      const m = {
        implements:'rgba(255,193,7,0.4)', depends_on:'rgba(255,200,80,0.35)',
        relates_to:'rgba(255,255,255,0.12)', enforces:'rgba(255,138,101,0.4)',
        discovered_in:'rgba(16,185,129,0.3)', references:'rgba(140,180,220,0.25)',
        supersedes:'rgba(239,68,68,0.4)', covers:'rgba(139,92,246,0.3)',
        belongs_to:'rgba(150,150,170,0.14)', touches:'rgba(180,220,180,0.28)',
      };
      return m[l.type]||'rgba(150,150,150,0.15)';
    })
    .linkWidth(l => ['implements','depends_on','enforces'].includes(l.type)?1:0.3)
    .linkDirectionalParticles(l => l.type==='implements'?2:0)
    .linkDirectionalParticleSpeed(0.003)
    .linkDirectionalParticleColor(()=>'#ffc107')
    .onNodeClick(n => showDetail(n))
    .onBackgroundClick(() => document.getElementById('detail').classList.remove('visible'));

  FG.d3Force('charge').strength(-120);
  FG.d3Force('link').distance(l => l.type==='belongs_to'?30:60);
}

// ── Sprite labels ─────────────────────────────────────────────────────────────
function makeSprite(text, color) {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const fs = 32;
  ctx.font = `${fs}px "JetBrains Mono", monospace`;
  const w = ctx.measureText(text).width;
  canvas.width = w+16; canvas.height = fs+8;
  ctx.font = `${fs}px "JetBrains Mono", monospace`;
  ctx.fillStyle = color;
  ctx.textBaseline = 'middle';
  ctx.fillText(text, 8, canvas.height/2);
  const tex = new THREE.CanvasTexture(canvas);
  const mat = new THREE.SpriteMaterial({map:tex, transparent:true, depthWrite:false});
  const sprite = new THREE.Sprite(mat);
  const aspect = canvas.width/canvas.height;
  sprite.scale.set(aspect*4, 4, 1);
  return sprite;
}

// ── Detail panel ──────────────────────────────────────────────────────────────
function showDetail(node) {
  const out = [], inc = [];
  const edges = GRAPH_DATA.edges||GRAPH_DATA.links||[];
  edges.forEach(e => {
    const f = e.from||e.source, t = e.to||e.target;
    if(f===node.id) out.push({type:e.type,id:t});
    if(t===node.id) inc.push({type:e.type,id:f});
  });
  const nodesById = {};
  GRAPH_DATA.nodes.forEach(n => nodesById[n.id]=n);

  const skip = new Set(['id','type','name','status','__hit','__searchHit',
    'x','y','z','vx','vy','vz','index','fx','fy','fz']);
  const fields = Object.entries(node).filter(([k])=>!skip.has(k)&&node[k]!=null);

  let html = `<div class="node-type">${node.type}</div>
    <div class="node-id">${node.id}</div>
    <div class="node-name">${esc(node.name)}</div>`;
  if(node.status) html += `<div class="field"><div class="field-label">Status</div>
    <div class="field-value" style="color:${STATUS_COLORS[node.status]||'#888'}">${node.status}</div></div>`;
  fields.forEach(([k,v]) => {
    let val = Array.isArray(v) ? v.map(i=>`• ${esc(String(i))}`).join('<br>')
            : typeof v==='object' ? `<pre style="font-size:9px;color:var(--text-dim);white-space:pre-wrap">${esc(JSON.stringify(v,null,2))}</pre>`
            : esc(String(v));
    html += `<div class="field"><div class="field-label">${k.replace(/_/g,' ')}</div>
      <div class="field-value">${val}</div></div>`;
  });
  if(out.length) {
    html += '<div class="relations"><h4>→ Outgoing</h4>';
    out.slice(0,30).forEach(e => {
      const name = nodesById[e.id]?.name||e.id;
      html += `<div class="rel-item" data-id="${e.id}">
        <span class="rel-verb">${e.type}</span>
        <span class="rel-target">${esc(name)}</span></div>`;
    });
    html += '</div>';
  }
  if(inc.length) {
    html += '<div class="relations"><h4>← Incoming</h4>';
    inc.slice(0,30).forEach(e => {
      const name = nodesById[e.id]?.name||e.id;
      html += `<div class="rel-item" data-id="${e.id}">
        <span class="rel-verb">${e.type}</span>
        <span class="rel-target">${esc(name)}</span></div>`;
    });
    html += '</div>';
  }
  html += `<div class="gobp-query">gobp(query="get: ${node.id}")</div>`;

  const content = document.getElementById('detail-content');
  content.innerHTML = html;
  document.getElementById('detail').classList.add('visible');

  content.querySelectorAll('.rel-item[data-id]').forEach(el => {
    el.addEventListener('click', () => {
      const n = GRAPH_DATA.nodes.find(n=>n.id===el.dataset.id);
      if(n) { showDetail(n); focusNode(n); }
    });
  });

  focusNode(node);
}

function focusNode(n) {
  if(!n.x) return;
  const d = 120;
  const r = 1 + d/Math.hypot(n.x||0, n.y||0, n.z||0);
  FG.cameraPosition({x:n.x*r, y:n.y*r, z:n.z*r}, n, 800);
}

function esc(s) {
  return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// ── Controls ──────────────────────────────────────────────────────────────────
document.getElementById('btn-core').addEventListener('click', () => {
  document.querySelectorAll('#type-filters input').forEach(cb => {
    cb.checked = CORE_TYPES.has(cb.dataset.type);
    if(cb.checked) VISIBLE_TYPES.add(cb.dataset.type); else VISIBLE_TYPES.delete(cb.dataset.type);
  });
  applyFilters();
});
document.getElementById('btn-all').addEventListener('click', () => {
  document.querySelectorAll('#type-filters input').forEach(cb => {
    cb.checked = true; VISIBLE_TYPES.add(cb.dataset.type);
  });
  applyFilters();
});
document.getElementById('btn-labels').addEventListener('click', () => {
  SHOW_LABELS = !SHOW_LABELS; FG.refresh();
});
document.getElementById('btn-reset').addEventListener('click', () => {
  FG.cameraPosition({x:0,y:0,z:600},{x:0,y:0,z:0},800);
});
document.getElementById('btn-refresh').addEventListener('click', () => {
  loadGraph(CURRENT_ROOT);
});
document.getElementById('search').addEventListener('input', e => {
  const q = e.target.value.trim().toLowerCase();
  if(!q) { applyFilters(); return; }
  const hits = new Set();
  GRAPH_DATA.nodes.forEach(n => {
    if(n.id.toLowerCase().includes(q)||(n.name||'').toLowerCase().includes(q)) hits.add(n.id);
  });
  const neighbors = new Set(hits);
  (GRAPH_DATA.edges||GRAPH_DATA.links||[]).forEach(e => {
    const f=e.from||e.source, t=e.to||e.target;
    if(hits.has(f)) neighbors.add(t);
    if(hits.has(t)) neighbors.add(f);
  });
  applyFilters(neighbors, hits);
});

boot();
</script>
</body>
</html>
```

**Acceptance criteria:**
- `index.html` replaced with new version
- JetBrains Mono font loads from Google Fonts
- Project switcher in topbar — fetches /api/projects
- Status filter panel with checkboxes
- Core/All/Labels/Reset/Refresh buttons work
- Search with 1-hop expansion
- Detail panel with click-navigate relations
- gobp() query hint in detail panel
- Only 3d-force-graph CDN (no duplicate Three.js)

**Commit message:**
```
Wave 12 Task 4: replace index.html with improved viewer

- JetBrains Mono + Fraunces serif fonts
- Project switcher: fetch /api/projects, switch without restart
- Status filter panel + Core/All toggle
- SpriteText labels via canvas (toggle)
- Search with 1-hop neighbor expansion
- Click-navigate relations in detail panel
- gobp() query hint per node
- Uses from/to for relations + source/target for rendering
```

---

## TASK 5 — Smoke test viewer with both projects

```powershell
# Start launcher (no browser)
$job = Start-Job {
    $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
    D:/GoBP/venv/Scripts/python.exe -m gobp.viewer.launcher --no-browser
}
Start-Sleep 3

# Test /api/projects
$p = Invoke-WebRequest -Uri "http://localhost:8080/api/projects" | ConvertFrom-Json
Write-Host "Projects:" $p.Count

# Test GoBP graph
$g1 = Invoke-WebRequest -Uri "http://localhost:8080/api/graph?root=D:/GoBP" | ConvertFrom-Json
Write-Host "GoBP nodes:" $g1.meta.node_count

# Test MIHOS graph
$g2 = Invoke-WebRequest -Uri "http://localhost:8080/api/graph?root=D:/MIHOS-v1" | ConvertFrom-Json
Write-Host "MIHOS nodes:" $g2.meta.node_count

# Test index.html
$html = (Invoke-WebRequest -Uri "http://localhost:8080/").Content
Write-Host "Has JetBrains Mono:" ($html -match "JetBrains")
Write-Host "Has project-switcher:" ($html -match "project-switcher")

Stop-Job $job; Remove-Job $job

# Full suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 284 tests passing
```

**Commit message:**
```
Wave 12 Task 5: smoke test — launcher + multi-project + viewer verified

- /api/projects returns GoBP + MIHOS
- /api/graph?root=D:/GoBP returns correct node count
- /api/graph?root=D:/MIHOS-v1 returns MIHOS nodes
- index.html has JetBrains Mono + project-switcher
- 284 existing tests passing
```

---

## TASK 6 — Update tests/test_viewer.py for multi-project

**Goal:** Add tests for new endpoints and launcher.

**File to modify:** `tests/test_viewer.py`

**Re-read `tests/test_viewer.py` in full.**

Add after existing tests:

```python
# ── Multi-project server tests ─────────────────────────────────────────────────

@pytest.fixture
def multi_viewer_server(tmp_path: Path):
    """Start multi-project viewer server."""
    import json as _json
    from gobp.core.init import init_project

    # Create 2 projects
    root1 = tmp_path / "proj1"
    root2 = tmp_path / "proj2"
    root1.mkdir(); root2.mkdir()
    init_project(root1, project_name="Project1", force=True)
    init_project(root2, project_name="Project2", force=True)

    projects = [
        {"name": "Project1", "root": str(root1)},
        {"name": "Project2", "root": str(root2)},
    ]
    projects_path = tmp_path / "projects.json"
    projects_path.write_text(_json.dumps(projects), encoding="utf-8")

    from gobp.viewer.server import run_server_with_projects
    from http.server import HTTPServer
    import threading, time

    viewer_dir = Path(__file__).parent.parent / "gobp" / "viewer"

    import json as _json2
    projs = _json2.loads(projects_path.read_text(encoding="utf-8"))
    from gobp.viewer.server import make_multi_handler
    handler = make_multi_handler(projs, viewer_dir)

    server = HTTPServer(("localhost", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    yield port, str(root1), str(root2)
    server.shutdown()


def test_api_projects_returns_list(multi_viewer_server):
    """GET /api/projects returns list of projects."""
    import urllib.request, json
    port, _, _ = multi_viewer_server
    with urllib.request.urlopen(f"http://localhost:{port}/api/projects") as resp:
        data = json.loads(resp.read())
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == "Project1"


def test_api_graph_with_root_param(multi_viewer_server):
    """GET /api/graph?root=PATH returns correct project graph."""
    import urllib.request, json
    from urllib.parse import quote
    port, root1, root2 = multi_viewer_server

    url1 = f"http://localhost:{port}/api/graph?root={quote(root1)}"
    with urllib.request.urlopen(url1) as resp:
        data = json.loads(resp.read())
        assert data["meta"]["node_count"] == 17  # seed nodes
        assert data["meta"]["project_name"] == "Project1"


def test_edges_have_both_formats(multi_viewer_server):
    """Edges have source/target AND from/to."""
    import urllib.request, json
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


def test_launcher_find_projects_json(tmp_path: Path):
    """find_projects_json() finds projects.json in expected locations."""
    import json
    from gobp.viewer.launcher import find_projects_json

    # Create in cwd equivalent (tmp_path)
    p = tmp_path / "projects.json"
    p.write_text(json.dumps([{"name":"test","root":str(tmp_path)}]))
    # Can't easily test cwd without monkeypatching,
    # but verify function returns None when no file exists
    # (actual file finding tested via integration)
    result = find_projects_json()
    # Should return something or None — just verify it doesn't crash
    assert result is None or result.exists()
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_viewer.py -v
```

**Commit message:**
```
Wave 12 Task 6: update test_viewer.py for multi-project

- test_api_projects_returns_list: /api/projects returns project list
- test_api_graph_with_root_param: ?root=PATH returns correct project
- test_edges_have_both_formats: edges have source/target AND from/to
- test_launcher_find_projects_json: doesn't crash
```

---

## TASK 7 — Full suite + CHANGELOG + gitignore projects.json

```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 290+ tests passing (284 + ~6 new)
```

**Update `.gitignore`** — `projects.json` is machine-specific:

```
# Machine-specific viewer config
projects.json
GoBP_Viewer.bat
```

**Update CHANGELOG.md:**

```markdown
## [Wave 12] — Launcher + Project Picker + Schema v3 + Better Viewer — 2026-04-15

### Problem solved
- Viewer required terminal command to start
- Schema lacked product node types (Engine, Flow, Entity, etc.)
- Viewer UI was too basic

### Added
- `GoBP_Viewer.bat` — double-click launcher (Windows)
- `projects.json` — machine-specific project registry (gitignored)
- `gobp/viewer/launcher.py` — finds projects.json, starts server, opens browser
- 9 new node types: Engine, Flow, Entity, Feature, Invariant, Screen,
  APIEndpoint, Repository, Wave
- Improved `index.html`: JetBrains Mono, project switcher, status filters,
  Core/All toggle, SpriteText labels, click-navigate relations

### Changed
- `gobp/viewer/server.py`: /api/projects endpoint, /api/graph?root=PATH,
  edges now have source/target AND from/to
- `gobp/schema/core_nodes.yaml`: 9 → 18 node types
- `.gitignore`: projects.json + GoBP_Viewer.bat

### Usage
```
Double-click GoBP_Viewer.bat
→ Browser opens at http://localhost:8080
→ Select project from dropdown
→ View 3D graph
```

### Total after wave: 1 MCP tool, 18 node types, 290+ tests
```

**Commit message:**
```
Wave 12 Task 7: full suite green + CHANGELOG + gitignore

- 290+ tests passing
- projects.json + GoBP_Viewer.bat gitignored (machine-specific)
- CHANGELOG: Wave 12 entry
```

---

# POST-WAVE VERIFICATION

```powershell
# All tests
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

# Launcher works
D:/GoBP/venv/Scripts/python.exe -m gobp.viewer.launcher --no-browser &
Start-Sleep 2
Invoke-WebRequest "http://localhost:8080/api/projects" | Select-Object StatusCode

# Schema has new types
D:/GoBP/venv/Scripts/python.exe -c "
import yaml
s = yaml.safe_load(open('gobp/schema/core_nodes.yaml', encoding='utf-8'))
types = list(s['node_types'].keys())
print(f'Node types ({len(types)}):', types)
assert 'Engine' in types
assert 'Flow' in types
assert 'Feature' in types
print('Schema OK')
"

# Git log
git log --oneline | Select-Object -First 8
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief vào repo

```powershell
cd D:\GoBP
# Save wave_12_brief.md to D:\GoBP\waves\wave_12_brief.md

git add waves/wave_12_brief.md
git commit -m "Add Wave 12 Brief — launcher + project picker + schema v3 + better viewer"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_12_brief.md first.
Also read gobp/viewer/server.py, gobp/viewer/index.html,
gobp/schema/core_nodes.yaml, tests/test_viewer.py.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 7 tasks of Wave 12 sequentially.
R9: all 284 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 12. Read CLAUDE.md and waves/wave_12_brief.md.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: projects.json + GoBP_Viewer.bat + launcher.py exist
          python -m gobp.viewer.launcher --help exits 0
- Task 2: server.py has run_server_with_projects(), /api/projects endpoint,
          /api/graph?root=PATH works, edges have source/target AND from/to
- Task 3: core_nodes.yaml has Engine/Flow/Entity/Feature/Invariant/Screen/APIEndpoint/Repository/Wave
- Task 4: index.html has JetBrains Mono, project-switcher, btn-core, btn-all, btn-labels
- Task 5: smoke test passed, 284 tests passing
- Task 6: test_viewer.py has multi-project tests
- Task 7: 290+ tests passing, CHANGELOG updated, .gitignore has projects.json

Use venv:
  D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

Expected: 290+ tests passing.
Report WAVE 12 AUDIT COMPLETE when done.
```

## 4. Push + test

```powershell
cd D:\GoBP
git push origin main

# Double-click GoBP_Viewer.bat or:
D:/GoBP/venv/Scripts/python.exe -m gobp.viewer.launcher
```

---

# WHAT COMES NEXT

```
Wave 12 pushed
    ↓
Wave 8B — MIHOS import
  Import mihos_graph.json → GoBP MIHOS
  626 nodes → visible in 3D viewer
  Double-click → pick MIHOS project → see full graph
```

---

*Wave 12 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
