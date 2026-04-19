# WAVE E BRIEF — VIEWER UI IMPROVEMENTS

**Wave:** E  
**Title:** Viewer UI — Sidebar cleanup + Node detail panel overhaul  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-19  
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)  
**Status:** READY FOR EXECUTION  
**Task count:** 7 atomic tasks  
**Estimated effort:** 4-5 hours  

---

## CONTEXT

Sau Wave B+C, viewer đã sạch hơn nhiều. Nhưng vẫn còn 5 vấn đề cụ thể cần fix:

```
Issue 1 — Sidebar counts không thẳng cột:
  "○ BusinessRule 1" → số 1 không thẳng hàng với các số khác
  Cần column riêng cho count → gọn gàng hơn

Issue 2 — Label sai:
  "Show metadata edges" → sai, phải là "Show Edges"
  Hint "e.g. discovered_in" → không còn dùng DISCOVERED_IN
  Phải nói rõ: show/hide tất cả edges

Issue 3 — Node detail thiếu Edges:
  Panel chỉ hiển thị Description + Debug
  Không có section Edges với thông tin từng edge
  Edges phải hiển thị: direction + node name + reason

Issue 4 — gobp query string không nên xuất hiện:
  "gobp(query="get: ... brief=true")" hiển thị trong panel
  → Internal implementation detail, không cho user thấy
  → Xóa hoàn toàn

Issue 5 — Code field + Debug: raw fields:
  Code field không hiển thị khi node có code
  "Debug: raw fields (12)" không cần thiết cho user
  → Thêm Code section, xóa Debug section
```

---

## REFERENCED DOCUMENTS

| Doc | Focus |
|---|---|
| `docs/SCHEMA.md` | Node fields: description + code (schema v3) |
| `gobp/viewer/index.html` | File chính cần sửa |
| `gobp/viewer/server.py` | API response format |

---

## CURSOR EXECUTION RULES

### R1-R8: Standard (xem `.cursorrules` — QR1-QR7)

### R9 — Testing strategy
- Tất cả tasks: R9-A — verify UI, no console errors, no pytest
- End of wave: `pytest tests/ -q --tb=no` (fast suite)

### R10: Session start/end (skip graph writes per CEO)
### R11: Report doc changes
### R12: Docs scope

---

## REQUIRED READING — BEFORE TASK 1

| # | File |
|---|---|
| 1 | `.cursorrules` (full) |
| 2 | `gobp/viewer/index.html` (toàn bộ — hiểu cấu trúc hiện tại) |
| 3 | `gobp/viewer/server.py` (API response format) |
| 4 | `docs/SCHEMA.md` (node fields v3) |

---

## TASKS

---

## TASK 1 — Sidebar: Count Column Alignment

**Goal:** Số lượng nodes trong sidebar thẳng cột, gọn gàng.

**File to modify:** `gobp/viewer/index.html`

**Re-read toàn bộ sidebar rendering code trước.**

Hiện tại: `○ BusinessRule 1` — số 1 không thẳng hàng.

Sửa thành layout 2 cột:

```css
.group-item {
    display: flex;
    align-items: center;
    justify-content: space-between;  /* name left, count right */
    padding: 3px 8px;
    cursor: pointer;
    border-radius: 4px;
}

.group-item:hover {
    background: rgba(255,255,255,0.05);
}

.group-name {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.group-count {
    min-width: 24px;
    text-align: right;
    font-size: 11px;
    color: #636d83;
    font-variant-numeric: tabular-nums;  /* monospace numbers */
    margin-left: 8px;
}
```

```javascript
// Render group item
function renderGroupItem(name, count, depth) {
    return `
    <div class="group-item" style="padding-left: ${8 + depth * 12}px"
         onclick="filterByGroup('${name}')">
        <span class="group-name">
            <span class="group-dot">○</span> ${name}
        </span>
        <span class="group-count">${count}</span>
    </div>`;
}
```

**Acceptance criteria (R9-A):**
- Mở viewer → sidebar có 2 cột rõ ràng: tên bên trái, số bên phải
- Các số thẳng hàng dọc (tabular-nums)
- Depth indentation vẫn hoạt động
- Click group vẫn filter đúng

**Commit message:**
```
Wave E Task 1: sidebar — count column alignment + tabular-nums
```

---

## TASK 2 — Sidebar: Font + Colors

**Goal:** Font và màu sắc sidebar rõ ràng hơn, phân biệt rõ các level.

**File to modify:** `gobp/viewer/index.html`

**Re-read CSS sidebar trước.**

```css
/* Sidebar base */
.sidebar {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
    line-height: 1.6;
}

/* Section titles (SEARCH, GROUP, VIEW) */
.sidebar-section-title {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #636d83;
    margin: 16px 8px 6px;
}

/* Top-level groups (Constraint, Dev, Document...) */
.group-level-0 .group-name {
    font-size: 13px;
    font-weight: 600;
    color: #c9b99a;
}

/* Sub-groups */
.group-level-1 .group-name {
    font-size: 12px;
    font-weight: 500;
    color: #a0a8b8;
}

.group-level-2 .group-name {
    font-size: 12px;
    font-weight: 400;
    color: #6e7681;
}

/* Active group (currently filtered) */
.group-item.active .group-name {
    color: #f0883e;
    font-weight: 600;
}

.group-item.active .group-count {
    color: #f0883e;
}

/* ALL GROUPS button */
.all-groups-btn {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 4px 10px;
    border-radius: 4px;
    border: 1px solid #f0883e;
    color: #f0883e;
    background: transparent;
    cursor: pointer;
}

.all-groups-btn:hover,
.all-groups-btn.active {
    background: #f0883e;
    color: #0f1117;
}
```

**Acceptance criteria (R9-A):**
- Top-level groups (Constraint, Dev...) rõ ràng hơn sub-groups
- Active group highlight màu brand (#f0883e)
- Font size phân biệt theo depth

**Commit message:**
```
Wave E Task 2: sidebar — font hierarchy + colors by depth level
```

---

## TASK 3 — Fix "Show Edges" Label + Hint

**Goal:** Sửa label và hint text trong VIEW section.

**File to modify:** `gobp/viewer/index.html`

**Tìm checkbox "Show metadata edges" trong VIEW section.**

Sửa:
```html
<!-- TRƯỚC -->
<label>
  <input type="checkbox" id="showMetaEdges">
  Show metadata edges
  <span class="hint">e.g. discovered_in</span>
</label>

<!-- SAU -->
<label>
  <input type="checkbox" id="showAllEdges">
  Show all edges
  <span class="hint">including edges without reasons</span>
</label>
```

Update JavaScript handler tương ứng — đổi variable name nếu cần.

**Acceptance criteria (R9-A):**
- Label hiển thị "Show all edges"
- Hint hiển thị "including edges without reasons"
- Checkbox vẫn hoạt động đúng (toggle edges)
- Không còn "metadata" hoặc "discovered_in" trong UI

**Commit message:**
```
Wave E Task 3: viewer — fix "Show all edges" label + hint text
```

---

## TASK 4 — Node Detail: Add Edges Section

**Goal:** Node detail panel hiển thị Edges với direction + node name + reason.

**File to modify:** `gobp/viewer/index.html`

**Re-read detail panel rendering code trước.**

Thêm Edges section vào detail panel, render sau Description:

```javascript
function renderEdges(edges) {
    if (!edges || edges.length === 0) {
        return `
        <div class="detail-section">
            <div class="detail-section-title">EDGES</div>
            <div class="no-edges">No connections</div>
        </div>`;
    }

    const edgeItems = edges.map(edge => {
        const direction = edge.direction || (edge.from === currentNodeId ? '→' : '←');
        const otherName = edge.other_name || edge.to_name || edge.from_name || 'Unknown';
        const reason    = edge.reason || '';

        return `
        <div class="edge-item">
            <div class="edge-header">
                <span class="edge-direction">${direction}</span>
                <span class="edge-node-name"
                      onclick="selectNode('${edge.other_id || edge.to || edge.from}')"
                >${otherName}</span>
            </div>
            ${reason ? `<div class="edge-reason">${reason}</div>` : ''}
        </div>`;
    }).join('');

    return `
    <div class="detail-section">
        <div class="detail-section-title">EDGES (${edges.length})</div>
        ${edgeItems}
    </div>`;
}
```

```css
.edge-item {
    padding: 8px 0;
    border-bottom: 1px solid #21262d;
}

.edge-item:last-child { border-bottom: none; }

.edge-header {
    display: flex;
    align-items: center;
    gap: 6px;
}

.edge-direction {
    font-size: 12px;
    color: #636d83;
    width: 16px;
    flex-shrink: 0;
}

.edge-node-name {
    font-size: 13px;
    color: #c9b99a;
    cursor: pointer;
    text-decoration: none;
}

.edge-node-name:hover {
    color: #f0883e;
    text-decoration: underline;
}

.edge-reason {
    font-size: 12px;
    color: #6e7681;
    margin-top: 3px;
    margin-left: 22px;
    font-style: italic;
    line-height: 1.4;
}

.no-edges {
    font-size: 12px;
    color: #636d83;
    font-style: italic;
}
```

**Acceptance criteria (R9-A):**
- Node detail panel có section EDGES
- Mỗi edge hiển thị: direction (→/←) + node name (clickable) + reason (nếu có)
- Click node name → navigate tới node đó
- Không có DISCOVERED_IN edges (đã filter từ Wave C)
- Edges không có reason → không hiển thị reason line

**Commit message:**
```
Wave E Task 4: node detail — add Edges section with direction + name + reason
```

---

## TASK 5 — Node Detail: Add Code Section + Cleanup

**Goal:** Thêm Code section. Xóa gobp query string. Xóa Debug: raw fields.

**File to modify:** `gobp/viewer/index.html`

**Re-read detail panel rendering code trước.**

### Fix 1: Thêm Code section

```javascript
function renderCode(code) {
    if (!code || !code.trim()) return '';
    return `
    <div class="detail-section">
        <div class="detail-section-title">CODE</div>
        <pre class="code-block"><code>${escapeHtml(code)}</code></pre>
    </div>`;
}
```

```css
.code-block {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 12px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 12px;
    line-height: 1.5;
    color: #e1e4e8;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
}
```

### Fix 2: Xóa gobp query string

Tìm và xóa phần render gobp query:
```javascript
// Tìm và xóa block tương tự:
// gobp(query="get: {node_id} brief=true")
// Đây là internal implementation detail — không hiển thị cho user
```

### Fix 3: Xóa Debug: raw fields

Tìm và xóa/comment out phần render Debug:
```javascript
// Xóa hoàn toàn:
// "▶ Debug: raw fields (N)"
// Collapsible với toàn bộ raw JSON
```

### Thứ tự render của detail panel sau fixes:

```
1. Breadcrumb (◈ Group > SubGroup)
2. Node ID (nhỏ, mờ)
3. Type badge
4. Node Name (heading lớn)
5. DESCRIPTION section
6. CODE section (chỉ khi có code)
7. EDGES section
8. [HẾT — không có Debug, không có gobp query]
```

**Acceptance criteria (R9-A):**
- Node có code → hiển thị CODE section với syntax-like styling
- Node không có code → không có CODE section
- Không có "gobp(query=...)" text bất kỳ đâu trong panel
- Không có "Debug: raw fields" bất kỳ đâu trong panel
- Thứ tự sections đúng như trên

**Commit message:**
```
Wave E Task 5: node detail — add Code section, remove gobp query + Debug panel
```

---

## TASK 6 — Node Detail: Severity Badge cho ErrorCase

**Goal:** ErrorCase nodes hiển thị severity badge rõ ràng.

**File to modify:** `gobp/viewer/index.html`

Khi node có `severity` field (ErrorCase):

```javascript
function renderSeverityBadge(severity) {
    if (!severity) return '';
    const colors = {
        'fatal':   { bg: '#4a1515', text: '#f85149', border: '#f85149' },
        'error':   { bg: '#3a1a10', text: '#f0883e', border: '#f0883e' },
        'warning': { bg: '#2d2610', text: '#e3b341', border: '#e3b341' },
        'info':    { bg: '#0d2137', text: '#58a6ff', border: '#58a6ff' },
    };
    const c = colors[severity.toLowerCase()] || colors['info'];
    return `
    <span class="severity-badge" style="
        background: ${c.bg};
        color: ${c.text};
        border: 1px solid ${c.border};
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    ">${severity.toUpperCase()}</span>`;
}
```

Thêm badge sau Type badge trong detail panel.

**Acceptance criteria (R9-A):**
- ErrorCase node có severity → hiển thị badge màu theo severity
- fatal = đỏ, error = cam, warning = vàng, info = xanh
- Non-ErrorCase nodes → không có badge

**Commit message:**
```
Wave E Task 6: node detail — severity badge for ErrorCase nodes
```

---

## TASK 7 — CHANGELOG Update

**Goal:** Update `CHANGELOG.md` với Wave E entry.

**File to modify:** `CHANGELOG.md`

**Re-read CHANGELOG.md trước.**

Prepend:

```markdown
## [Wave E] — Viewer UI Improvements — 2026-04-19

### Changed (viewer)
- Sidebar: count column alignment (tabular-nums, flex layout)
- Sidebar: font hierarchy by depth level, active group highlight
- VIEW section: "Show all edges" label (was: "Show metadata edges")
- Node detail: added EDGES section (direction + name + reason)
- Node detail: added CODE section (shown when node has code)
- Node detail: added severity badge for ErrorCase nodes
- Node detail: removed gobp query string display
- Node detail: removed Debug: raw fields section
- Rendering order: breadcrumb → name → description → code → edges

---
```

**Verification (R9-A):**
- CHANGELOG.md có Wave E entry ở đầu

**Commit message:**
```
Wave E Task 7: CHANGELOG.md — Wave E viewer improvements
```

---

## POST-WAVE VERIFICATION

```powershell
# Start viewer
python -m gobp.viewer.server --root D:\MIHOS-v1

# http://localhost:8080/ — verify:
# □ Sidebar counts thẳng cột
# □ Font hierarchy rõ (top-level đậm hơn sub-levels)
# □ "Show all edges" label đúng
# □ Click node → DESCRIPTION + CODE (nếu có) + EDGES
# □ Edges hiển thị direction + name + reason
# □ Không có gobp query string
# □ Không có Debug: raw fields
# □ ErrorCase node → severity badge đúng màu

# Fast suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

## CEO DISPATCH INSTRUCTIONS

### 1. Cursor

```
Read .cursorrules (full).
Read gobp/viewer/index.html (TOÀN BỘ — đây là file quan trọng nhất wave này).
Read gobp/viewer/server.py.
Read docs/SCHEMA.md.
Read waves/wave_e_brief.md (this file).

Execute Tasks 1 → 7 sequentially.
Tất cả tasks: R9-A (verify UI, no pytest).
End: pytest tests/ -q --tb=no
DO NOT modify server.py API response format unless Task requires.
```

### 2. Claude CLI audit

```
Audit Wave E.
Task 1: Sidebar counts thẳng cột, tabular-nums
Task 2: Font hierarchy theo depth, active highlight
Task 3: Label "Show all edges", hint đúng
Task 4: Node detail có EDGES section, direction+name+reason
Task 5: Code section hiển thị, gobp query gone, Debug gone
Task 6: ErrorCase severity badge màu đúng
Task 7: CHANGELOG có Wave E entry
End: fast suite pass
BLOCKING: Bất kỳ fail → STOP, báo CEO.
```

### 3. Push (sau khi audit PASS)

```powershell
cd D:\GoBP
git add waves/wave_e_brief.md
git commit -m "Wave E Brief: Viewer UI Improvements — 7 tasks"
git push origin main
```

---

*Wave E Brief — Viewer UI Improvements*  
*2026-04-19 — CTO Chat*  
◈
