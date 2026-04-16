# WAVE 16A05 BRIEF — MCP GENERATOR + PROJECT IDENTITY + TASK QUEUE

**Wave:** 16A05
**Title:** MCP Generator in Viewer, project identity, GoBP Task Queue
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-16
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 8 atomic tasks
**Estimated effort:** 4-5 hours

---

## CONTEXT

3 problems after Wave 16A04:

**P1 — No visual tool to create MCP configs**
```
Current: CEO edits ~/.claude.json manually — dangerous, error-prone
Problem: Wrong project path → AI writes to wrong GoBP instance
Fix: MCP Generator tab IN the viewer
     Viewer already knows project root → auto-fill
     CEO opens viewer → click MCP → copy config
```

**P2 — No project identity**
```
Current: overview: returns no project name
Problem: AI can't tell which project it's connected to
Fix: project_name in .gobp/config.yaml
     overview: shows project name prominently
```

**P3 — No communication layer CTO → Cursor**
```
Current: CEO manually pastes briefs
Fix: GoBP Task Queue — Task node type
     CTO creates Task → Cursor polls tasks: → executes
```

---

## DESIGN

### MCP Generator in Viewer

```
Viewer left panel:
  [CORE ONLY] [SHOW ALL]
  [LABELS]    [RESET CAMERA]
  [◈ REFRESH]
  [⚙ MCP]    ← NEW BUTTON

Click [⚙ MCP] → MCP Generator panel slides in (replaces detail panel on right)

Panel layout:
  ┌─────────────────────────────────┐
  │ ⚙ MCP CONFIG GENERATOR         │
  ├─────────────────────────────────┤
  │ PROJECT ROOT                    │
  │ [D:/GoBP/________________] ← auto-filled from server
  │                                 │
  │ PROJECT NAME                    │
  │ [GoBP___________________]  ← from config.yaml
  │                                 │
  │ DB NAME                         │
  │ [gobp___________________]  ← auto-suggest from root
  │                                 │
  │ PYTHON PATH                     │
  │ [D:/GoBP/venv/Scripts/python.exe]
  │                                 │
  │ DB HOST                         │
  │ [postgresql://postgres:***@localhost]
  │                                 │
  │ MCP KEY: gobp-gobp              │
  ├─────────────────────────────────┤
  │ [Claude CLI] [Cursor] [PS]      │
  ├─────────────────────────────────┤
  │ { generated config... }         │
  │                          [Copy] │
  └─────────────────────────────────┘
```

### /api/config endpoint

```python
# viewer/server.py — new endpoint
GET /api/config
Response:
{
  "project_root": "D:/GoBP",
  "project_name": "GoBP",        # from .gobp/config.yaml
  "project_id": "gobp",
  "python_path": "D:/GoBP/venv/Scripts/python.exe",
  "suggested_db": "gobp",        # derived from root folder name
  "suggested_mcp_key": "gobp-gobp"
}
```

### DB name auto-suggest logic

```python
def suggest_db_name(project_root: str) -> str:
    """Suggest DB name from project root folder.
    
    D:/GoBP        → gobp
    D:/MIHOS-v1    → gobp_mihos
    D:/MyProject   → gobp_myproject
    """
    folder = Path(project_root).name.lower()
    folder = re.sub(r'[^a-z0-9]', '_', folder).strip('_')
    folder = re.sub(r'-v\d+$', '', folder)  # remove -v1, -v2 suffix
    return f"gobp_{folder}" if folder != "gobp" else "gobp"
```

### Project identity

```yaml
# .gobp/config.yaml additions
project_name: "GoBP"
project_id: "gobp"
project_description: "Graph of Brainstorm Project"
```

`overview:` response:
```json
{
  "project": {
    "name": "GoBP",
    "id": "gobp",
    "description": "Graph of Brainstorm Project"
  }
}
```

### Task node type

```
Task: work item for AI agent communication
  required: name, assignee, status
  optional: brief_path, wave, priority, error, result_summary

ID format: {slug}.meta.{8digits}
Example: wave_8b_import.meta.00000001

New action: tasks:
  tasks:                    → pending tasks for cursor
  tasks: assignee='haiku'   → pending for haiku  
  tasks: status='ALL'       → all tasks
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 439 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 439 tests passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/viewer/index.html` | Add MCP panel |
| 3 | `gobp/viewer/server.py` | Add /api/config endpoint |
| 4 | `gobp/core/init.py` | Add project_name to config |
| 5 | `gobp/mcp/tools/read.py` | Update overview: |
| 6 | `gobp/mcp/dispatcher.py` | Add tasks: action |
| 7 | `gobp/schema/core_nodes.yaml` | Add Task node type |
| 8 | `waves/wave_16a05_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Add /api/config to viewer/server.py

**Goal:** Viewer serves project config to MCP Generator panel.

**File to modify:** `gobp/viewer/server.py`

**Re-read in full.**

Add `/api/config` endpoint:

```python
import re as _re

def _suggest_db_name(project_root: str) -> str:
    """Suggest DB name from project folder name."""
    folder = Path(project_root).name.lower()
    folder = _re.sub(r'[^a-z0-9]', '_', folder).strip('_')
    folder = _re.sub(r'_v\d+$', '', folder)  # remove _v1, _v2
    return f"gobp_{folder}" if folder != "gobp" else "gobp"

def _get_python_path() -> str:
    """Get current Python executable path."""
    import sys
    return sys.executable.replace("\\", "/")

# In the HTTP handler, add:
elif path == "/api/config":
    import yaml as _yaml
    config = {}
    config_path = gobp_root / ".gobp" / "config.yaml"
    if config_path.exists():
        try:
            config = _yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception:
            pass

    root_str = str(gobp_root).replace("\\", "/")
    result = {
        "project_root": root_str,
        "project_name": config.get("project_name", gobp_root.name),
        "project_id": config.get("project_id", gobp_root.name.lower()),
        "project_description": config.get("project_description", ""),
        "python_path": _get_python_path(),
        "suggested_db": _suggest_db_name(root_str),
        "suggested_mcp_key": "gobp-" + gobp_root.name.lower().replace("_", "-"),
        "db_host": "postgresql://postgres:Hieu%408283%40@localhost",
    }
    self._send_json(result)
```

**Verify:**
```powershell
# Start viewer then:
curl http://localhost:8080/api/config
# Should return project_root, project_name, python_path, suggested_db
```

**Commit message:**
```
Wave 16A05 Task 1: add /api/config endpoint to viewer/server.py

- Returns project_root, project_name, python_path, suggested_db, mcp_key
- _suggest_db_name(): D:/MIHOS-v1 → gobp_mihos, D:/GoBP → gobp
- _get_python_path(): current Python executable
- MCP Generator panel will call this on load
```

---

## TASK 2 — Add MCP Generator panel to viewer/index.html

**Goal:** Click [⚙ MCP] in left panel → MCP Generator slides into detail panel.

**File to modify:** `gobp/viewer/index.html`

**Re-read in full before editing.**

**Add MCP button to left panel** (after REFRESH button):

```html
<button id="btn-mcp" onclick="toggleMCPPanel()">⚙ MCP</button>
```

**Add MCP panel HTML** (inside `<div id="detail">` or as sibling):

```html
<div id="mcp-panel" style="display:none">
  <div class="detail-header">
    <span class="node-type">CONFIG</span>
    <button onclick="toggleMCPPanel()" style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:14px">✕</button>
  </div>
  <h2 style="font-size:16px;margin-bottom:16px">⚙ MCP Config Generator</h2>

  <div class="mcp-field">
    <label>PROJECT ROOT</label>
    <input id="mcp-root" readonly style="opacity:0.7">
  </div>
  <div class="mcp-field">
    <label>PROJECT NAME</label>
    <input id="mcp-name" oninput="generateMCP()">
  </div>
  <div class="mcp-field">
    <label>DB NAME</label>
    <input id="mcp-db" oninput="generateMCP()">
  </div>
  <div class="mcp-field">
    <label>PYTHON PATH</label>
    <input id="mcp-python" oninput="generateMCP()">
  </div>
  <div class="mcp-field">
    <label>DB HOST</label>
    <input id="mcp-dbhost" oninput="generateMCP()">
  </div>
  <div id="mcp-key-preview" style="color:var(--amber);font-size:11px;margin:8px 0">MCP KEY: gobp-project</div>

  <div class="mcp-tabs">
    <button class="mcp-tab active" onclick="switchMCPTab('cli')">Claude CLI</button>
    <button class="mcp-tab" onclick="switchMCPTab('cursor')">Cursor</button>
    <button class="mcp-tab" onclick="switchMCPTab('ps')">PowerShell</button>
  </div>

  <div id="mcp-output" style="position:relative">
    <pre id="mcp-code" style="background:#050508;border:1px solid var(--border);border-radius:6px;padding:12px;font-size:10px;color:#c8c8d4;overflow-x:auto;max-height:200px;overflow-y:auto;white-space:pre-wrap;margin-top:8px"></pre>
    <button onclick="copyMCP()" style="position:absolute;top:16px;right:8px;font-size:10px;padding:3px 8px" id="mcp-copy-btn">Copy</button>
  </div>
</div>
```

**Add CSS** (in `<style>`):

```css
#btn-mcp {
  margin-top: 4px;
  width: 100%;
  background: rgba(255,193,7,0.08);
  color: var(--amber);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 5px;
  cursor: pointer;
  font-size: 11px;
  font-family: var(--mono);
}
#btn-mcp:hover { background: rgba(255,193,7,0.15); }
.mcp-field { margin-bottom: 8px; }
.mcp-field label { display: block; color: var(--text-dim); font-size: 10px; margin-bottom: 3px; }
.mcp-field input { width: 100%; background: rgba(255,255,255,0.05); border: 1px solid var(--border); border-radius: 4px; color: var(--text); padding: 5px 8px; font-family: var(--mono); font-size: 11px; }
.mcp-field input:focus { outline: none; border-color: var(--amber); }
.mcp-tabs { display: flex; gap: 4px; margin-top: 12px; }
.mcp-tab { flex: 1; background: transparent; border: 1px solid var(--border); border-radius: 4px 4px 0 0; color: var(--text-dim); padding: 4px; font-size: 10px; cursor: pointer; font-family: var(--mono); }
.mcp-tab.active { border-color: var(--amber); color: var(--amber); background: rgba(255,193,7,0.05); }
#mcp-panel { padding: 16px; overflow-y: auto; }
```

**Add JavaScript:**

```javascript
let mcpTab = 'cli';

async function toggleMCPPanel() {
  const panel = document.getElementById('mcp-panel');
  const detail = document.getElementById('detail');
  
  if (panel.style.display === 'none') {
    panel.style.display = 'block';
    detail.classList.remove('visible');
    
    // Load config from server
    try {
      const cfg = await fetch('/api/config').then(r => r.json());
      document.getElementById('mcp-root').value = cfg.project_root || '';
      document.getElementById('mcp-name').value = cfg.project_name || '';
      document.getElementById('mcp-db').value = cfg.suggested_db || '';
      document.getElementById('mcp-python').value = cfg.python_path || '';
      document.getElementById('mcp-dbhost').value = cfg.db_host || 'postgresql://postgres:***@localhost';
      generateMCP();
    } catch(e) {
      console.error('Failed to load config:', e);
    }
  } else {
    panel.style.display = 'none';
  }
}

function getMCPKey() {
  const name = document.getElementById('mcp-name').value || 'project';
  return 'gobp-' + name.toLowerCase().replace(/[^a-z0-9]/g, '-');
}

function switchMCPTab(tab) {
  mcpTab = tab;
  document.querySelectorAll('.mcp-tab').forEach((el, i) => {
    el.classList.toggle('active', ['cli','cursor','ps'][i] === tab);
  });
  generateMCP();
}

function generateMCP() {
  const root = document.getElementById('mcp-root').value;
  const name = document.getElementById('mcp-name').value;
  const db = document.getElementById('mcp-db').value;
  const python = document.getElementById('mcp-python').value;
  const dbhost = document.getElementById('mcp-dbhost').value;
  const key = getMCPKey();
  
  document.getElementById('mcp-key-preview').textContent = 'MCP KEY: ' + key;
  
  const serverObj = {
    type: 'stdio',
    command: python,
    args: ['-m', 'gobp.mcp.server'],
    env: {
      GOBP_PROJECT_ROOT: root,
      GOBP_DB_URL: dbhost + '/' + db
    }
  };
  
  const cursorObj = { ...serverObj };
  delete cursorObj.type;
  
  let output = '';
  if (mcpTab === 'cli') {
    output = JSON.stringify({ mcpServers: { [key]: serverObj } }, null, 2);
  } else if (mcpTab === 'cursor') {
    output = JSON.stringify({ mcpServers: { [key]: cursorObj } }, null, 2);
  } else {
    output = `# Add ${key} to ~/.claude.json
$server = [PSCustomObject]@{
  type = "stdio"
  command = "${python}"
  args = @("-m", "gobp.mcp.server")
  env = [PSCustomObject]@{
    GOBP_PROJECT_ROOT = "${root}"
    GOBP_DB_URL = "${dbhost}/${db}"
  }
}
# Run this script to add the MCP server automatically`;
  }
  
  document.getElementById('mcp-code').textContent = output;
}

function copyMCP() {
  const text = document.getElementById('mcp-code').textContent;
  navigator.clipboard.writeText(text);
  const btn = document.getElementById('mcp-copy-btn');
  btn.textContent = 'Copied!';
  setTimeout(() => btn.textContent = 'Copy', 2000);
}
```

**Acceptance criteria:**
- [⚙ MCP] button visible in left panel
- Click → MCP panel appears on right, detail panel hides
- Auto-filled from /api/config: root, name, db, python path
- Tabs: Claude CLI / Cursor / PowerShell
- Copy button works
- MCP key preview updates on name change

**Commit message:**
```
Wave 16A05 Task 2: add MCP Generator panel to viewer

- index.html: ⚙ MCP button in left panel
- MCP panel: auto-fill from /api/config
- Tabs: Claude CLI / Cursor / PowerShell configs
- Copy button per tab
- MCP key preview: gobp-{name}
```

---

## TASK 3 — Add project identity to config.yaml

**Goal:** `project_name` field in .gobp/config.yaml, shown in overview:.

**File to modify:** `gobp/core/init.py`

Update `_write_config()`:

```python
config = {
    "schema_version": "2.1",
    "project_name": name,
    "project_id": name.lower().replace(" ", "-"),
    "project_description": "",
    "created": datetime.now(timezone.utc).isoformat(),
    "id_groups": { ... }
}
```

**File to modify:** `gobp/mcp/tools/read.py`

Update `gobp_overview()`:

```python
# Load project identity from config
from gobp.core.id_config import load_groups
import yaml as _yaml
config = {}
config_path = project_root / ".gobp" / "config.yaml"
if config_path.exists():
    try:
        config = _yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        pass

result["project"] = {
    "name": config.get("project_name", project_root.name),
    "id": config.get("project_id", ""),
    "description": config.get("project_description", ""),
    "root": str(project_root),
}
```

**Commit message:**
```
Wave 16A05 Task 3: project identity in config.yaml + overview:

- init.py: project_name, project_id, project_description in config
- read.py: overview: returns project.name, project.id, project.description
- AI sees which project it's connected to from first overview: call
```

---

## TASK 4 — Add Task node type to schema

**File to modify:** `gobp/schema/core_nodes.yaml`

Add Task:

```yaml
  Task:
    id_prefix: "task"
    group: "meta"
    tier_weight: 5
    description: "Work item for AI agent communication queue"
    required:
      name:
        type: "string"
      assignee:
        type: "enum"
        enum_values: ["cursor", "claude-cli", "haiku", "any"]
        default: "cursor"
      status:
        type: "enum"
        enum_values: ["PENDING", "RUNNING", "DONE", "FAILED", "BLOCKED"]
        default: "PENDING"
    optional:
      brief_path:
        type: "string"
      wave:
        type: "string"
      priority:
        type: "enum"
        enum_values: ["critical", "high", "medium", "low"]
        default: "medium"
      error:
        type: "string"
      result_summary:
        type: "string"
```

**File to modify:** `gobp/core/id_config.py`

Add Task to meta group and TYPE_PREFIXES:

```python
DEFAULT_GROUPS = {
    ...
    "meta": {
        "types": ["Session", "Wave", "Document", "Lesson", "Node",
                  "Repository", "Idea", "Task"],  # ADD Task
        ...
    },
}

TYPE_PREFIXES = {
    ...
    "Task": "task",
}
```

**Commit message:**
```
Wave 16A05 Task 4: add Task node type

- core_nodes.yaml: Task with status/assignee/brief_path/wave fields
- id_config.py: Task in meta group, prefix "task"
- create:Task name='...' assignee='cursor' → task.meta.XXXXXXXX
```

---

## TASK 5 — Add tasks: action to dispatcher

**File to modify:** `gobp/mcp/dispatcher.py`

**Re-read in full.**

Add `tasks:` action before `session:` handler:

```python
        elif action == "tasks":
            # Find tasks filtered by assignee + status
            assignee = params.get("assignee", params.get("query", "cursor"))
            status_filter = params.get("status", "PENDING")
            
            # Find all Task nodes
            all_nodes = index.all_nodes()
            tasks = [n for n in all_nodes if n.get("type") == "Task"]
            
            # Filter
            filtered = []
            for t in tasks:
                t_status = t.get("status", "PENDING")
                t_assignee = t.get("assignee", "cursor")
                status_ok = status_filter == "ALL" or t_status == status_filter
                assignee_ok = assignee == "any" or t_assignee == assignee or t_assignee == "any"
                if status_ok and assignee_ok:
                    filtered.append({
                        "id": t.get("id"),
                        "name": t.get("name"),
                        "status": t_status,
                        "assignee": t_assignee,
                        "wave": t.get("wave", ""),
                        "brief_path": t.get("brief_path", ""),
                        "priority": t.get("priority", "medium"),
                    })
            
            # Sort by priority
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            filtered.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 2))
            
            result = {
                "ok": True,
                "tasks": filtered,
                "count": len(filtered),
                "filter": {"assignee": assignee, "status": status_filter},
                "hint": f"Use upsert: to update task status. Example: upsert: id='task:x' status='RUNNING' session_id='y'",
            }
```

**Update PROTOCOL_GUIDE:**
```python
"tasks:":                                          "Pending tasks for cursor",
"tasks: assignee='haiku'":                        "Pending tasks for haiku",
"tasks: status='ALL'":                            "All tasks",
"create:Task name='...' assignee='cursor' wave='8B' brief_path='waves/...' session_id='x'": "Create task",
```

**Commit message:**
```
Wave 16A05 Task 5: add tasks: action to dispatcher

- tasks: returns filtered Task nodes by assignee + status
- Default: PENDING tasks for cursor
- Sorted by priority
- PROTOCOL_GUIDE: 4 task queue entries
```

---

## TASK 6 — Set project identities + smoke test

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# Set GoBP identity
D:/GoBP/venv/Scripts/python.exe -c "
import yaml
from pathlib import Path

root = Path('D:/GoBP')
cfg_path = root / '.gobp' / 'config.yaml'
config = yaml.safe_load(cfg_path.read_text(encoding='utf-8')) or {}
config['project_name'] = 'GoBP'
config['project_id'] = 'gobp'
config['project_description'] = 'Graph of Brainstorm Project — AI team memory layer'
cfg_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding='utf-8')
print('GoBP identity set')
"

# Set MIHOS identity
D:/GoBP/venv/Scripts/python.exe -c "
import yaml
from pathlib import Path

root = Path('D:/MIHOS-v1')
cfg_path = root / '.gobp' / 'config.yaml'
if cfg_path.exists():
    config = yaml.safe_load(cfg_path.read_text(encoding='utf-8')) or {}
    config['project_name'] = 'MIHOS'
    config['project_id'] = 'mihos-v1'
    config['project_description'] = 'Heritage-Tech platform — Proof of Presence'
    cfg_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding='utf-8')
    print('MIHOS identity set')
else:
    print('MIHOS config not found - skip')
"

# Smoke test
D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch

async def test():
    root = Path('D:/GoBP')
    index = GraphIndex.load_from_disk(root)

    # Test overview: project name
    r = await dispatch('overview:', index, root)
    name = r.get('project', {}).get('name', '')
    assert name == 'GoBP', f'Expected GoBP, got: {name}'
    print(f'overview: project.name = {name} OK')

    # Test create Task
    sess = await dispatch(\"session:start actor='test' goal='task test'\", index, root)
    sid = sess['session_id']
    index = GraphIndex.load_from_disk(root)

    r2 = await dispatch(
        f\"create:Task name='Test Task' assignee='cursor' wave='test' session_id='{sid}'\",
        index, root
    )
    assert r2['ok'], f'create:Task failed: {r2}'
    task_id = r2['node_id']
    print(f'create:Task OK: {task_id}')

    # Test tasks:
    index = GraphIndex.load_from_disk(root)
    r3 = await dispatch('tasks:', index, root)
    assert r3['ok']
    ids = [t['id'] for t in r3['tasks']]
    assert task_id in ids, f'{task_id} not in tasks'
    print(f'tasks: found {r3[\"count\"]} pending tasks OK')

asyncio.run(test())
"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 439 tests passing
```

**Commit message:**
```
Wave 16A05 Task 6: set project identities + smoke test

- GoBP: project_name="GoBP" in .gobp/config.yaml
- MIHOS: project_name="MIHOS" in .gobp/config.yaml
- overview: shows correct project.name
- create:Task + tasks: working end-to-end
- 439 tests passing
```

---

## TASK 7 — Create tests/test_wave16a05.py

**File to create:** `tests/test_wave16a05.py`

```python
"""Tests for Wave 16A05: project identity, Task queue, MCP generator."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch


# ── Project identity tests ────────────────────────────────────────────────────

def test_init_creates_project_name(gobp_root: Path):
    init_project(gobp_root, force=True)
    import yaml
    config = yaml.safe_load((gobp_root / ".gobp" / "config.yaml").read_text())
    assert "project_name" in config


def test_overview_returns_project_name(gobp_root: Path):
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    r = asyncio.run(dispatch("overview:", index, gobp_root))
    assert r["ok"] is True
    assert "project" in r
    assert "name" in r["project"]
    assert r["project"]["name"]  # not empty


def test_overview_project_name_from_config(gobp_root: Path):
    init_project(gobp_root, force=True)
    import yaml
    cfg_path = gobp_root / ".gobp" / "config.yaml"
    config = yaml.safe_load(cfg_path.read_text()) or {}
    config["project_name"] = "TestProject"
    cfg_path.write_text(yaml.safe_dump(config))

    index = GraphIndex.load_from_disk(gobp_root)
    r = asyncio.run(dispatch("overview:", index, gobp_root))
    assert r["project"]["name"] == "TestProject"


# ── Task node tests ───────────────────────────────────────────────────────────

def test_create_task_node(gobp_root: Path):
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='task test'", index, gobp_root
    ))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch(
        f"create:Task name='Build auth flow' assignee='cursor' wave='8B' session_id='{sid}'",
        index, gobp_root
    ))
    assert r["ok"] is True
    assert "task" in r["node_id"]


def test_task_id_format(gobp_root: Path):
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='task id test'", index, gobp_root
    ))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch(
        f"create:Task name='Verify Gate Flow' assignee='cursor' session_id='{sid}'",
        index, gobp_root
    ))
    node_id = r["node_id"]
    assert ".meta." in node_id
    assert "verify_gate_flow" in node_id or "task" in node_id


def test_task_default_status_pending(gobp_root: Path):
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='task status test'", index, gobp_root
    ))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch(
        f"create:Task name='My Task' session_id='{sid}'",
        index, gobp_root
    ))
    task_id = r["node_id"]
    index2 = GraphIndex.load_from_disk(gobp_root)
    node = index2.get_node(task_id)
    assert node is not None
    assert node.get("status") == "PENDING"


# ── tasks: action tests ───────────────────────────────────────────────────────

def test_tasks_action_returns_pending(gobp_root: Path):
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='tasks action test'", index, gobp_root
    ))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    asyncio.run(dispatch(
        f"create:Task name='Task A' assignee='cursor' session_id='{sid}'",
        index, gobp_root
    ))
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch("tasks:", index, gobp_root))
    assert r["ok"] is True
    assert "tasks" in r
    assert r["count"] >= 1


def test_tasks_filter_by_assignee(gobp_root: Path):
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='assignee filter test'", index, gobp_root
    ))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    asyncio.run(dispatch(
        f"create:Task name='Cursor Task' assignee='cursor' session_id='{sid}'",
        index, gobp_root
    ))
    asyncio.run(dispatch(
        f"create:Task name='Haiku Task' assignee='haiku' session_id='{sid}'",
        index, gobp_root
    ))
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch("tasks: assignee='haiku'", index, gobp_root))
    assert r["ok"] is True
    for t in r["tasks"]:
        assert t["assignee"] == "haiku"


def test_tasks_protocol_guide_has_entries():
    from gobp.mcp.parser import PROTOCOL_GUIDE
    actions = PROTOCOL_GUIDE.get("actions", {})
    assert any("tasks:" in k for k in actions)


# ── Viewer config endpoint tests ──────────────────────────────────────────────

def test_suggest_db_name():
    from gobp.viewer.server import _suggest_db_name
    assert _suggest_db_name("D:/GoBP") == "gobp"
    assert _suggest_db_name("D:/MIHOS-v1") == "gobp_mihos"
    assert _suggest_db_name("D:/MyProject") == "gobp_myproject"


def test_suggest_db_name_strips_version():
    from gobp.viewer.server import _suggest_db_name
    assert _suggest_db_name("D:/MIHOS-v1") == "gobp_mihos"
    assert _suggest_db_name("D:/App-v2") == "gobp_app"
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave16a05.py -v
# Expected: ~16 tests

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 455+ tests
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A05] — MCP Generator + Project Identity + Task Queue — 2026-04-16

### Added
- **MCP Generator in Viewer**: ⚙ MCP button in left panel
  - Auto-fills from /api/config: root, name, python path
  - Generates Claude CLI / Cursor / PowerShell configs
  - Copy buttons per format
  - No new files — integrated into existing viewer
  
- **Project identity**: project_name in .gobp/config.yaml
  - overview: returns project.name prominently
  - AI can tell which project it's connected to
  - GoBP → "GoBP", MIHOS → "MIHOS"
  
- **Task Queue**: Task node type for CTO→Cursor communication
  - create:Task name='...' assignee='cursor' wave='8B'
  - tasks: → pending tasks for cursor
  - tasks: assignee='haiku' → filter by assignee
  - Enables automation without CEO as bridge

- **/api/config** endpoint: viewer serves project config to MCP Generator

### Changed
- viewer/server.py: /api/config endpoint
- viewer/index.html: MCP Generator panel
- core/init.py: project_name in new configs
- mcp/tools/read.py: overview: includes project identity
- mcp/dispatcher.py: tasks: action
- schema/core_nodes.yaml: Task node type
- core/id_config.py: Task in meta group

### Total: 455+ tests
```

**Commit message:**
```
Wave 16A05 Task 7: tests/test_wave16a05.py + full suite + CHANGELOG

- ~16 tests: project identity, Task node, tasks: action, _suggest_db_name
- 455+ tests passing
- CHANGELOG: Wave 16A05 entry
```

---

# POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

# Open viewer and verify MCP button
Start-Process "http://localhost:8080"
# Click ⚙ MCP → should see auto-filled config

# Verify project identity
D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch

async def check():
    root = Path('D:/GoBP')
    index = GraphIndex.load_from_disk(root)
    r = await dispatch('overview:', index, root)
    print('GoBP project.name:', r.get('project', {}).get('name'))
    
    r2 = await dispatch('tasks: status=ALL', index, root)
    print('Total tasks:', r2.get('count', 0))

asyncio.run(check())
"

git log --oneline | Select-Object -First 10
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief

```powershell
cd D:\GoBP
# Save to D:\GoBP\waves\wave_16a05_brief.md
git add waves/wave_16a05_brief.md
git commit -m "Add Wave 16A05 Brief — MCP Generator + project identity + Task queue"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_16a05_brief.md first.
Also read gobp/viewer/index.html, gobp/viewer/server.py,
gobp/core/init.py, gobp/mcp/tools/read.py,
gobp/mcp/dispatcher.py, gobp/schema/core_nodes.yaml.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 7 tasks sequentially.
R9: all 439 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 16A05. Read CLAUDE.md and waves/wave_16a05_brief.md.
Set env: $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: /api/config endpoint in server.py, _suggest_db_name() function
- Task 2: ⚙ MCP button in viewer, MCP panel, auto-fill from /api/config
- Task 3: project_name in init.py config, overview: returns project.name
- Task 4: Task node in core_nodes.yaml, id_config.py meta group
- Task 5: tasks: action in dispatcher, PROTOCOL_GUIDE entries
- Task 6: GoBP + MIHOS identities set, smoke test passed, 439 tests
- Task 7: test_wave16a05.py ~16 tests, 455+ total, CHANGELOG

BLOCKING RULE: Gặp vấn đề → DỪNG ngay, báo CEO.

Expected: 455+ tests. Report WAVE 16A05 AUDIT COMPLETE.
```

---

# WHAT COMES NEXT

```
Wave 16A05 done
    ↓
Wave 8B — MIHOS import
  CEO opens viewer → ⚙ MCP → copy config → done
  gobp-mihos connected → import docs
  project.name = "MIHOS" confirms right project
    ↓
CTO creates Task nodes for Cursor
  create:Task name='Build auth' assignee='cursor' wave='1'
  Cursor: tasks: → read brief → execute → done
```

---

*Wave 16A05 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-16*

◈
