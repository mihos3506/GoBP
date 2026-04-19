# WAVE B BRIEF — CLEANUP + VIEWER DASHBOARD

**Wave:** B  
**Title:** Remove Deprecated Docs + Viewer Dashboard Page  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-19  
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)  
**Status:** READY FOR EXECUTION  
**Task count:** 9 atomic tasks  
**Estimated effort:** 5-6 hours  

---

## CONTEXT

Wave A đã build foundation cho schema v3. Wave B dọn dẹp docs cũ, thêm Dashboard page vào viewer, verify Page 1 compatibility, và cập nhật CHANGELOG.

```
Viewer hiện tại:
  Page 1: 3D force graph — GIỮ NGUYÊN, verify compatibility
  
Thêm mới:
  Page 2: Dashboard — stats, sessions, graph health

Cleanup:
  Xóa deprecated docs (superseded bởi v3 docs)
  Update .cursorrules schema section
  Update README.md deprecated list
  Update CHANGELOG.md
```

**Page 1 KHÔNG thay đổi UI** — chỉ verify data fields vẫn load đúng sau schema changes.

---

## REFERENCED DOCUMENTS

| Doc | Mục đích |
|---|---|
| `docs/SCHEMA.md` | Schema v3 — source of truth |
| `docs/ARCHITECTURE.md` | Tiers, PostgreSQL, performance |
| `docs/README.md` | Deprecated files list |
| `docs/AGENT_RULES.md` | Pipeline rules |
| `gobp/viewer/` | Existing viewer code |

---

## CURSOR EXECUTION RULES (READ FIRST — NON-NEGOTIABLE)

### R1 — Sequential execution
Tasks 1 → 9 in order. No skipping, no reordering.

### R2 — Discovery before creation
Read existing files before modifying anything.

### R3 — 1 task = 1 commit
Tests pass → commit immediately with exact message from Brief.

### R4 — Docs are supreme authority
Conflict with `docs/SCHEMA.md`, `docs/ARCHITECTURE.md`, `docs/README.md` → docs win, STOP and report.

### R5 — Document disagreement = STOP
Believe a doc has error → STOP, report, wait.

### R6 — 3 retries = STOP
Test fails 3 times → STOP, report, wait.

### R7 — No scope creep
Implement exactly what Brief specifies. Page 1 UI = DO NOT TOUCH.

### R8 — Brief code blocks are authoritative
Disagree → STOP and escalate. Never substitute silently.

### R9 — Testing strategy
- Tasks 1, 5, 8, 9 (docs/cleanup): R9-A — verify files exist/deleted, no pytest
- Tasks 2, 3, 4 (viewer): R9-B — verify viewer loads + API returns correct data
- Task 6 (verify Page 1): R9-B — manual verify Page 1 loads without errors
- Task 7 (tests): R9-B — run `pytest tests/test_wave_b.py -v`
- End of wave: R9-C — full suite

### R10 — GoBP MCP update (immutable)
`session:start` → thực hiện tasks → `session:end` với outcome.

### R11 — Report doc changes to CEO
Mọi thay đổi docs phải được summary trong wave report.

### R12 — Docs scope
Chỉ edit docs được authorized trong Brief này.

---

## REQUIRED READING — BEFORE TASK 1

| # | File | Focus |
|---|---|---|
| 1 | `.cursorrules` | Execution rules, current state |
| 2 | `docs/README.md` | Deprecated files list |
| 3 | `docs/SCHEMA.md` | Schema v3 overview |
| 4 | `docs/ARCHITECTURE.md` | Section 3 (file format) |
| 5 | `gobp/viewer/server.py` | Viewer server structure |
| 6 | `gobp/viewer/index.html` | Existing viewer UI — understand fields used |
| 7 | `CHANGELOG.md` | Current state trước khi update |

---

## TASKS

---

## TASK 1 — Remove Deprecated Docs

**Goal:** Xóa các docs đã được supersede bởi doc set v3 theo `docs/README.md`.

**Files to DELETE:**

```
docs/GoBP_ARCHITECTURE.md
docs/MCP_TOOLS.md
docs/GoBP_AI_USER_GUIDE.md
docs/GOBP_SCHEMA_REDESIGN_v2_1.md
docs/INPUT_MODEL.md
docs/IMPORT_MODEL.md
docs/IMPORT_CHECKLIST.md
```

**Không xóa:** `docs/VISION.md` — giữ làm historical context.

**Command:**
```powershell
cd D:\GoBP
git rm docs/GoBP_ARCHITECTURE.md
git rm docs/MCP_TOOLS.md
git rm docs/GoBP_AI_USER_GUIDE.md
git rm "docs/GOBP_SCHEMA_REDESIGN_v2_1.md"
git rm docs/INPUT_MODEL.md
git rm docs/IMPORT_MODEL.md
git rm docs/IMPORT_CHECKLIST.md
```

**Verification (R9-A):**
```powershell
Test-Path "docs/GoBP_ARCHITECTURE.md"   # False
Test-Path "docs/MCP_TOOLS.md"            # False
Test-Path "docs/GoBP_AI_USER_GUIDE.md"  # False
Test-Path "docs/SCHEMA.md"              # True (v3 — keep)
Test-Path "docs/ARCHITECTURE.md"         # True (v3 — keep)
Test-Path "docs/MCP_PROTOCOL.md"         # True (v3 — keep)
```

**Commit message:**
```
Wave B Task 1: remove 7 deprecated docs — superseded by doc set v3

- Removed: GoBP_ARCHITECTURE.md, MCP_TOOLS.md, GoBP_AI_USER_GUIDE.md
- Removed: GOBP_SCHEMA_REDESIGN_v2_1.md, INPUT_MODEL.md, IMPORT_MODEL.md
- Removed: IMPORT_CHECKLIST.md
- Kept: SCHEMA.md, ARCHITECTURE.md, MCP_PROTOCOL.md, COOKBOOK.md,
        AGENT_RULES.md, HISTORY_SPEC.md, README.md, VISION.md
```

---

## TASK 2 — Viewer: Add Dashboard Route + API

**Goal:** Thêm `/dashboard` route và `/api/dashboard` endpoint vào viewer server.  
Page 1 (`/`) KHÔNG thay đổi.

**File to modify:** `gobp/viewer/server.py`

**Re-read `server.py` toàn bộ trước khi sửa.**

Thêm 2 routes:

```python
@app.get("/dashboard")
async def dashboard(request: Request):
    return FileResponse(
        Path(__file__).parent / "dashboard.html"
    )


@app.get("/api/dashboard")
async def api_dashboard():
    """Dashboard stats từ GraphIndex."""
    try:
        index = get_index()

        all_nodes = index.all_nodes() if hasattr(index, 'all_nodes') else []
        all_edges = index.all_edges() if hasattr(index, 'all_edges') else []

        # Nodes by top-level group
        nodes_by_group: dict[str, int] = {}
        for node in all_nodes:
            group = node.get('group', 'Unknown')
            top = group.split('>')[0].strip() if '>' in group else group
            nodes_by_group[top] = nodes_by_group.get(top, 0) + 1

        # Recent sessions (last 5, most recent first)
        sessions = [
            {
                'id':     n.get('id', ''),
                'goal':   (n.get('goal') or '')[:80],
                'status': n.get('status', ''),
                'actor':  n.get('actor', ''),
            }
            for n in all_nodes
            if n.get('type') == 'Session'
        ][:5]

        return {
            'ok': True,
            'stats': {
                'total_nodes':    len(all_nodes),
                'total_edges':    len(all_edges),
                'nodes_by_group': nodes_by_group,
            },
            'recent_sessions': sessions,
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}
```

**Verification (R9-B):**
```powershell
python -m gobp.viewer.server --root D:\MIHOS-v1
# In another terminal:
Invoke-WebRequest http://localhost:8080/dashboard       # 200
Invoke-WebRequest http://localhost:8080/api/dashboard   # JSON với ok:true
```

**Commit message:**
```
Wave B Task 2: viewer server — /dashboard route + /api/dashboard

- GET /dashboard: serves dashboard.html
- GET /api/dashboard: total nodes/edges, by_group, recent sessions
- Page 1 (/) unchanged
```

---

## TASK 3 — Viewer: Dashboard HTML

**Goal:** Tạo `gobp/viewer/dashboard.html`.

**File to create:** `gobp/viewer/dashboard.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GoBP Dashboard</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #0f1117; color: #e1e4e8; min-height: 100vh;
    }
    header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 16px 24px; background: #161b22;
      border-bottom: 1px solid #30363d;
    }
    header h1 { font-size: 18px; font-weight: 600; color: #f0883e; }
    header nav a {
      color: #8b949e; text-decoration: none;
      margin-left: 16px; font-size: 14px;
    }
    header nav a:hover { color: #e1e4e8; }
    .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px; margin-bottom: 24px;
    }
    .stat-card {
      background: #161b22; border: 1px solid #30363d;
      border-radius: 8px; padding: 20px;
    }
    .stat-card .value {
      font-size: 36px; font-weight: 700; color: #f0883e;
      line-height: 1; margin-bottom: 8px;
    }
    .stat-card .label {
      font-size: 13px; color: #8b949e;
      text-transform: uppercase; letter-spacing: 0.5px;
    }
    .section {
      background: #161b22; border: 1px solid #30363d;
      border-radius: 8px; padding: 20px; margin-bottom: 16px;
    }
    .section h2 {
      font-size: 14px; font-weight: 600; color: #8b949e;
      text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 16px;
    }
    .group-bar { display: flex; align-items: center; margin-bottom: 10px; gap: 12px; }
    .group-name { width: 120px; font-size: 13px; color: #e1e4e8; flex-shrink: 0; }
    .bar-track { flex: 1; background: #21262d; border-radius: 4px; height: 8px; overflow: hidden; }
    .bar-fill { height: 100%; background: #f0883e; border-radius: 4px; transition: width 0.5s ease; }
    .group-count { width: 40px; text-align: right; font-size: 13px; color: #8b949e; }
    .session-list { list-style: none; }
    .session-item {
      display: flex; align-items: center; gap: 12px;
      padding: 10px 0; border-bottom: 1px solid #21262d;
    }
    .session-item:last-child { border-bottom: none; }
    .session-status { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
    .status-in-progress { background: #3fb950; }
    .status-completed   { background: #8b949e; }
    .status-failed      { background: #f85149; }
    .session-goal { flex: 1; font-size: 13px; color: #e1e4e8; }
    .session-actor {
      font-size: 12px; color: #8b949e;
      background: #21262d; padding: 2px 8px; border-radius: 12px;
    }
    .error-text { color: #f85149; font-size: 14px; }
    .loading { color: #8b949e; font-size: 14px; text-align: center; padding: 40px; }
    .refresh-btn {
      background: #21262d; border: 1px solid #30363d; color: #e1e4e8;
      padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px;
    }
    .refresh-btn:hover { background: #30363d; }
  </style>
</head>
<body>
  <header>
    <h1>◈ GoBP Dashboard</h1>
    <nav>
      <a href="/">Graph View</a>
      <a href="/dashboard">Dashboard</a>
      <button class="refresh-btn" onclick="loadDashboard()">↻ Refresh</button>
    </nav>
  </header>
  <div class="container">
    <div id="content"><div class="loading">Loading dashboard...</div></div>
  </div>
  <script>
    async function loadDashboard() {
      const content = document.getElementById('content');
      content.innerHTML = '<div class="loading">Loading...</div>';
      try {
        const res = await fetch('/api/dashboard');
        const data = await res.json();
        if (!data.ok) {
          content.innerHTML = `<div class="error-text">Error: ${data.error}</div>`;
          return;
        }
        const { stats, recent_sessions } = data;
        const byGroup = stats.nodes_by_group || {};
        const sorted = Object.entries(byGroup).sort((a,b) => b[1]-a[1]);
        const maxCount = sorted.length > 0 ? sorted[0][1] : 1;
        const groupBars = sorted.map(([g, c]) => `
          <div class="group-bar">
            <span class="group-name">${g}</span>
            <div class="bar-track">
              <div class="bar-fill" style="width:${(c/maxCount*100).toFixed(1)}%"></div>
            </div>
            <span class="group-count">${c}</span>
          </div>`).join('');
        const sessionItems = (recent_sessions||[]).map(s => {
          const cls = s.status==='IN_PROGRESS' ? 'status-in-progress'
                    : s.status==='COMPLETED'   ? 'status-completed'
                    : 'status-failed';
          return `<li class="session-item">
            <div class="session-status ${cls}"></div>
            <span class="session-goal">${s.goal||'(no goal)'}</span>
            <span class="session-actor">${s.actor||'unknown'}</span>
          </li>`;
        }).join('') || '<li style="color:#8b949e;padding:10px 0;font-size:13px">No sessions</li>';
        const active = (recent_sessions||[]).filter(s=>s.status==='IN_PROGRESS').length;
        content.innerHTML = `
          <div class="stats-grid">
            <div class="stat-card"><div class="value">${stats.total_nodes.toLocaleString()}</div><div class="label">Total Nodes</div></div>
            <div class="stat-card"><div class="value">${stats.total_edges.toLocaleString()}</div><div class="label">Total Edges</div></div>
            <div class="stat-card"><div class="value">${sorted.length}</div><div class="label">Top Groups</div></div>
            <div class="stat-card"><div class="value">${active}</div><div class="label">Active Sessions</div></div>
          </div>
          <div class="section"><h2>Nodes by Group</h2>${groupBars||'<div style="color:#8b949e;font-size:13px">No data</div>'}</div>
          <div class="section"><h2>Recent Sessions</h2><ul class="session-list">${sessionItems}</ul></div>`;
      } catch(err) {
        content.innerHTML = `<div class="error-text">Failed: ${err.message}</div>`;
      }
    }
    loadDashboard();
  </script>
</body>
</html>
```

**Verification (R9-B):**
```powershell
Test-Path "gobp/viewer/dashboard.html"  # True
# Browse http://localhost:8080/dashboard → stats cards + group bars visible
```

**Commit message:**
```
Wave B Task 3: gobp/viewer/dashboard.html — stats dashboard

- Stats cards: nodes, edges, groups, active sessions
- Group distribution bar chart
- Recent sessions list with status indicator
```

---

## TASK 4 — Viewer: Dashboard Nav Link

**Goal:** Thêm link Dashboard vào Page 1 (index.html).  
**Page 1 UI không thay đổi** — chỉ thêm nav link nhỏ.

**File to modify:** `gobp/viewer/index.html`

**Re-read `index.html` toàn bộ trước khi sửa.**

Tìm existing nav/header → thêm dashboard link.  
Nếu không có nav → thêm overlay button:

```html
<!-- Thêm ngay sau <body> tag -->
<div style="
  position:fixed;top:0;right:0;z-index:1000;
  padding:8px 16px;
  background:rgba(22,27,34,0.9);
  border-bottom-left-radius:8px;
">
  <a href="/dashboard" style="
    color:#f0883e;text-decoration:none;
    font-size:13px;font-family:sans-serif;
  ">◈ Dashboard</a>
</div>
```

**Verification (R9-B):**
```
# Browse http://localhost:8080/ → dashboard link/button visible
# Click → navigates to /dashboard
# 3D graph unchanged
```

**Commit message:**
```
Wave B Task 4: viewer index.html — add dashboard nav link

- Fixed overlay link to /dashboard
- Minimal style, does not interfere with 3D graph
```

---

## TASK 5 — Verify Page 1 Compatibility

**Goal:** Verify Page 1 (3D graph) vẫn load data đúng sau Wave A schema changes.

**Re-read `gobp/viewer/server.py` và `gobp/viewer/index.html` toàn bộ.**

Kiểm tra viewer đang query những fields nào từ nodes:
- Nếu viewer dùng `type`, `lifecycle`, `read_order` → ghi note vào wave report (không phải block)
- Nếu viewer dùng `description.info` → verify vẫn nhận data (v3 dùng plain text description)
- Nếu viewer dùng `edge.type` → ghi note (v3 edges không có type)

**Không sửa Page 1 code** trong task này — chỉ verify và report.

**Verification (R9-B):**
```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
python -m gobp.viewer.server --root D:\MIHOS-v1
# Browse http://localhost:8080/ → 3D graph loads
# No JavaScript console errors
# Nodes visible với labels
```

**Report compatibility notes trong commit message.**

**Commit message:**
```
Wave B Task 5: verify viewer Page 1 compatibility with schema changes

- Page 1 loads correctly after Wave A foundation changes
- Fields used: [list fields viewer queries]
- Compatibility notes: [any notes for future waves]
- No UI changes made
```

---

## TASK 6 — Update .cursorrules Schema Section

**Goal:** Thêm schema v3 section vào `.cursorrules`.

**File to modify:** `.cursorrules`

Tìm `## Schema v2 Rules` → thêm schema v3 section TRÊN NÓ:

```markdown
## Schema v3 (Wave A — new foundation)

Schema v3 đã được define trong `docs/SCHEMA.md`. 2 templates:

**Template 1 — Mọi node:**
  name + group + description (plain text) + code (optional) + history[]

**Template 2 — ErrorCase:**
  name + group + severity (fatal|error|warning|info) + description + code + history[]

**Edge format (v3):**
  from + to + reason (plain text, no type field)
  Edge type inferred by system từ group breadcrumb

**Modules:**
  Validator:   `gobp/core/validator_v3.py` — ValidatorV3
  Pyramid:     `gobp/core/pyramid.py` — extract_pyramid()
  File format: `gobp/core/file_format_v3.py`

**Taxonomy:** ~75 node types với group breadcrumb — xem `docs/SCHEMA.md`

---

```

**KHÔNG xóa** Schema v2 section — vẫn cần cho existing code (migration = Wave F).

**Verification (R9-A):**
```powershell
Select-String -Path ".cursorrules" -Pattern "Schema v3"
# Expected: match found
```

**Commit message:**
```
Wave B Task 6: .cursorrules — add schema v3 section

- Added "Schema v3 (Wave A)" section above legacy v2 rules
- Documents 2 templates, edge format, new module references
- v2 section preserved until Wave F migration
```

---

## TASK 7 — Tests Wave B

**Goal:** Tests verify dashboard API và deprecated docs cleanup.

**File to create:** `tests/test_wave_b.py`

```python
"""Tests for GoBP Wave B — Cleanup + Dashboard."""

import pytest
from pathlib import Path


# ── Deprecated docs cleanup ───────────────────────────────────────────────────

DOCS_ROOT = Path(__file__).parent.parent / "docs"

DEPRECATED_DOCS = [
    "GoBP_ARCHITECTURE.md",
    "MCP_TOOLS.md",
    "GoBP_AI_USER_GUIDE.md",
    "GOBP_SCHEMA_REDESIGN_v2_1.md",
    "INPUT_MODEL.md",
    "IMPORT_MODEL.md",
    "IMPORT_CHECKLIST.md",
]

V3_DOCS = [
    "SCHEMA.md",
    "ARCHITECTURE.md",
    "MCP_PROTOCOL.md",
    "COOKBOOK.md",
    "AGENT_RULES.md",
    "HISTORY_SPEC.md",
    "README.md",
]


@pytest.mark.parametrize("filename", DEPRECATED_DOCS)
def test_deprecated_doc_removed(filename):
    """Deprecated docs phải không còn tồn tại."""
    path = DOCS_ROOT / filename
    assert not path.exists(), (
        f"Deprecated doc still exists: {path}. "
        f"Should have been removed in Wave B Task 1."
    )


@pytest.mark.parametrize("filename", V3_DOCS)
def test_v3_doc_exists(filename):
    """V3 docs phải tồn tại."""
    path = DOCS_ROOT / filename
    assert path.exists(), f"V3 doc missing: {path}"


# ── Viewer files ──────────────────────────────────────────────────────────────

VIEWER_ROOT = Path(__file__).parent.parent / "gobp" / "viewer"


def test_dashboard_html_exists():
    """dashboard.html phải tồn tại."""
    assert (VIEWER_ROOT / "dashboard.html").exists()


def test_dashboard_html_has_api_call():
    """dashboard.html phải call /api/dashboard."""
    content = (VIEWER_ROOT / "dashboard.html").read_text(encoding="utf-8")
    assert "/api/dashboard" in content


def test_dashboard_html_has_nav_link():
    """dashboard.html phải có nav link về Graph View."""
    content = (VIEWER_ROOT / "dashboard.html").read_text(encoding="utf-8")
    assert 'href="/"' in content


def test_index_html_has_dashboard_link():
    """index.html phải có link tới /dashboard."""
    index = VIEWER_ROOT / "index.html"
    if index.exists():
        content = index.read_text(encoding="utf-8")
        assert "/dashboard" in content, (
            "index.html should contain a link to /dashboard"
        )


# ── .cursorrules ──────────────────────────────────────────────────────────────

def test_cursorrules_has_schema_v3():
    """.cursorrules phải có schema v3 section."""
    cursorrules = Path(__file__).parent.parent / ".cursorrules"
    assert cursorrules.exists(), ".cursorrules not found"
    content = cursorrules.read_text(encoding="utf-8")
    assert "Schema v3" in content, (
        ".cursorrules missing Schema v3 section"
    )


# ── Wave A modules still importable ──────────────────────────────────────────

def test_wave_a_modules_importable():
    """Wave A modules phải vẫn importable sau Wave B cleanup."""
    from gobp.core.pyramid import extract_pyramid
    from gobp.core.validator_v3 import ValidatorV3
    from gobp.core.file_format_v3 import serialize_node
    assert extract_pyramid("test.") == ("test.", "test.")
    assert ValidatorV3() is not None
    assert serialize_node({"name":"x","group":"y","description":"z"})
```

**Verification (R9-B):**
```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave_b.py -v --tb=short
# Expected: 12+ tests passing
```

**Commit message:**
```
Wave B Task 7: tests/test_wave_b.py — 12+ tests

- Deprecated docs removed (7 tests)
- V3 docs exist (7 tests)
- Dashboard HTML + nav link (3 tests)
- .cursorrules has v3 section (1 test)
- Wave A modules still importable (1 test)
```

---

## TASK 8 — Update docs/README.md

**Goal:** Update `docs/README.md` — xóa deprecated entries khỏi DEPRECATED section, update Current State.

**File to modify:** `docs/README.md`

**Re-read `docs/README.md` trước khi sửa.**

1. Update `CURRENT STATE` date và Wave A entries:

```markdown
## CURRENT STATE (2026-04-19)

Schema:     v3 — 2 templates, ~75 node types
Protocol:   v2 — single tool gobp(), 30+ actions  
PostgreSQL: primary storage
Tests:      705+ (Wave A adds 35+, Wave B adds 12+)
Viewer:     3D graph (Page 1) + Dashboard (Page 2)
```

2. Update DEPRECATED section — xóa các files đã bị delete:

```markdown
## DEPRECATED — ĐÃ XÓA (Wave B)

Các files sau đã được xóa khỏi repo:
  GoBP_ARCHITECTURE.md   → superseded by ARCHITECTURE.md
  MCP_TOOLS.md           → superseded by MCP_PROTOCOL.md
  GoBP_AI_USER_GUIDE.md  → merged into MCP_PROTOCOL.md + COOKBOOK.md
  GOBP_SCHEMA_REDESIGN_v2_1.md → implemented in SCHEMA.md v3
  INPUT_MODEL.md         → merged into COOKBOOK.md
  IMPORT_MODEL.md        → merged into COOKBOOK.md
  IMPORT_CHECKLIST.md    → merged into COOKBOOK.md + AGENT_RULES.md
```

**Verification (R9-A):**
```powershell
# File updated
(Get-Content docs/README.md) -join "`n" | Select-String "Wave B"
# Expected: matches found
```

**Commit message:**
```
Wave B Task 8: docs/README.md — update current state + deprecated list

- Current state: v3 schema, Wave A+B test counts, viewer pages
- Deprecated section: list files removed in Wave B Task 1
```

---

## TASK 9 — CHANGELOG.md Update

**Goal:** Update `CHANGELOG.md` với Wave A và Wave B entries.

**File to modify:** `CHANGELOG.md`

**Re-read `CHANGELOG.md` hiện tại trước khi sửa.**

Prepend (thêm vào đầu sau `# CHANGELOG`):

```markdown
## [Wave B] — Cleanup + Viewer Dashboard — 2026-04-19

### Removed
- 7 deprecated docs superseded by v3 doc set
- `docs/GoBP_ARCHITECTURE.md`, `docs/MCP_TOOLS.md`, `docs/GoBP_AI_USER_GUIDE.md`
- `docs/GOBP_SCHEMA_REDESIGN_v2_1.md`, `docs/INPUT_MODEL.md`
- `docs/IMPORT_MODEL.md`, `docs/IMPORT_CHECKLIST.md`

### Added
- `gobp/viewer/dashboard.html` — stats dashboard page (Page 2)
- `gobp/viewer/server.py`: `/dashboard` route + `/api/dashboard` endpoint
- `tests/test_wave_b.py`: 12+ tests

### Changed
- `gobp/viewer/index.html`: dashboard nav link
- `.cursorrules`: schema v3 section added
- `docs/README.md`: current state + deprecated list updated

### Total after wave: 705+ tests passing

---

## [Wave A] — Database Foundation — 2026-04-19

### Added
- `gobp/core/pyramid.py` — description pyramid extractor (L1/L2/full)
- `gobp/core/validator_v3.py` — schema v3 validator (2 templates)
- `gobp/core/file_format_v3.py` — schema v3 serialize/deserialize
- `gobp/core/db.py`: `create_schema_v3()`, `get_schema_version()`
- `tests/test_wave_a.py`: 35+ tests
- `waves/wave_a_brief.md`

### Changed
- `gobp/core/id_generator.py`: verified v2 format (group_slug.name_slug.8hex)

### PostgreSQL Schema v3
- `nodes`: desc_l1/l2/full pyramid, BM25F search_vec, no typed fields
- `edges`: from/to/reason only (no type field), reason_vec index
- `node_history`: append-only per node

### Total after wave: 705+ tests passing

---
```

**Verification (R9-A):**
```powershell
(Get-Content CHANGELOG.md)[0..5]
# Expected: Wave B entry at top
```

**Commit message:**
```
Wave B Task 9: CHANGELOG.md — Wave A + Wave B entries

- Wave B: cleanup + dashboard (7 removed, 3 added)
- Wave A: database foundation (pyramid, validator v3, file format v3)
- Total: 705+ tests
```

---

## POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# Deprecated docs gone
Test-Path "docs/GoBP_ARCHITECTURE.md"  # False
Test-Path "docs/MCP_TOOLS.md"           # False

# Dashboard accessible
python -m gobp.viewer.server --root D:\MIHOS-v1
# http://localhost:8080/dashboard → loads OK
# http://localhost:8080/ → 3D graph unchanged

# Full test suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --override-ini="addopts=" -q --tb=no
# Expected: 705+ tests passing
```

---

## CEO DISPATCH INSTRUCTIONS

### 1. Cursor

```
Read .cursorrules (full).
Read docs/README.md, docs/SCHEMA.md, docs/ARCHITECTURE.md.
Read gobp/viewer/server.py, gobp/viewer/index.html.
Read CHANGELOG.md.
Read waves/wave_b_brief.md (this file).

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute Tasks 1 → 9 sequentially.
R9: Docs tasks = R9-A. Viewer tasks = R9-B. End = R9-C.
1 task = 1 commit with exact message from Brief.
DO NOT modify Page 1 UI in Tasks 2-4.
```

### 2. Claude CLI audit

```
Audit Wave B.
Task 1: 7 deprecated docs deleted, v3 docs intact (7+)
Task 2: /dashboard + /api/dashboard routes work
Task 3: dashboard.html loads with data, has nav link
Task 4: index.html has /dashboard link
Task 5: Page 1 loads without errors, compatibility notes reported
Task 6: .cursorrules has schema v3 section
Task 7: 12+ tests pass
Task 8: README.md updated correctly
Task 9: CHANGELOG.md has Wave A + B entries at top
End: 705+ tests pass
BLOCKING: Bất kỳ fail → STOP, báo CEO.
```

### 3. Push (sau khi audit PASS)

```powershell
cd D:\GoBP
git log --oneline | Select-Object -First 9
# Expected: 9 Wave B commits

git push origin main
```

**Không push nếu audit chưa PASS.**

---

*Wave B Brief — GoBP Cleanup + Viewer Dashboard*  
*2026-04-19 — CTO Chat*  
◈
