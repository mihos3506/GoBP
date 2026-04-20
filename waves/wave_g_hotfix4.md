# WAVE G HOTFIX 4 — VIEWER EDGE COLLAPSE/EXPAND + NAVIGATION

**Wave:** G-Hotfix-4  
**Title:** Viewer — Edges collapse/expand per item + navigation guide  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-20  
**For:** Cursor  
**Status:** READY FOR EXECUTION  
**Task count:** 2 atomic tasks  

---

## MỤC TIÊU

```
Edge list hiện tại: tất cả edges render dọc đầy đủ
→ 35 edges = quá dài, AI/dev khó scan

Cần:
  1. Mỗi edge = 1 dòng collapsed (chỉ show tên node kia)
     Click → expand → show reason + code
  
  2. Navigation hint sau edge list:
     "→ Click tên node để navigate"
     "→ Click edge để xem reason + code"
```

---

## TASK 1 — Edges: collapse/expand per item

**File to modify:** `gobp/viewer/index.html`

**Re-read `renderEdges()` và CSS hiện tại trước.**

### Behavior

```
EDGES (10)
  ▶ Schema Base Node Template          ← collapsed, click to expand
  ▼ Schema ErrorCase Template          ← expanded
      Schema v3 defines ErrorCase...   ← reason text
      [CODE block nếu có]              ← code block
  ▶ Schema Edge Format
  ▶ GoBP Architecture v3
  ...
```

### Implementation

```javascript
function renderEdges(nodeId, allEdges, allNodes) {
    const related = (allEdges || []).filter(e =>
        e.from === nodeId || e.to === nodeId ||
        e.from_id === nodeId || e.to_id === nodeId
    );

    if (!related.length) {
        return `
        <div class="detail-section">
            <div class="detail-section-title">EDGES</div>
            <div class="no-edges">No connections</div>
        </div>`;
    }

    const items = related.map((e, idx) => {
        const otherId = (e.from === nodeId || e.from_id === nodeId)
            ? (e.to || e.to_id)
            : (e.from || e.from_id);

        const otherNode = (allNodes || []).find(n => n.id === otherId);
        const otherName = otherNode
            ? (otherNode.name || otherId)
            : (e.to_name || e.from_name || otherId || 'Unknown');

        const reason = e.reason || '';
        const code   = e.code   || '';

        const expandId = `edge-expand-${nodeId.replace(/\./g, '_')}-${idx}`;

        const expandContent = (reason || code) ? `
        <div class="edge-expand" id="${expandId}" style="display:none">
            ${reason ? `<div class="edge-reason-text">${reason}</div>` : ''}
            ${code   ? `<pre class="edge-code-block"><code>${escapeHtml(code)}</code></pre>` : ''}
        </div>` : '';

        const hasDetail = reason || code;
        const toggleBtn = hasDetail
            ? `<span class="edge-toggle" onclick="toggleEdgeDetail('${expandId}', this)">▶</span>`
            : `<span class="edge-toggle edge-toggle--empty">·</span>`;

        return `
        <div class="edge-item">
            <div class="edge-header">
                ${toggleBtn}
                <span class="edge-node-name"
                      onclick="selectNodeById('${otherId}')"
                >${otherName}</span>
            </div>
            ${expandContent}
        </div>`;
    }).join('');

    return `
    <div class="detail-section">
        <div class="detail-section-title">EDGES (${related.length})</div>
        ${items}
        <div class="edge-nav-hint">
            ▶ Click tên node để navigate · Click ▶ để xem reason + code
        </div>
    </div>`;
}

function toggleEdgeDetail(expandId, toggleEl) {
    const el = document.getElementById(expandId);
    if (!el) return;
    const isOpen = el.style.display !== 'none';
    el.style.display = isOpen ? 'none' : 'block';
    toggleEl.textContent = isOpen ? '▶' : '▼';
}
```

### CSS

```css
.edge-toggle {
    width: 16px;
    flex-shrink: 0;
    font-size: 10px;
    color: #636d83;
    cursor: pointer;
    user-select: none;
    transition: color 0.15s;
}
.edge-toggle:hover { color: #f0883e; }
.edge-toggle--empty { cursor: default; }

.edge-expand {
    margin-top: 6px;
    margin-left: 22px;
    padding: 8px;
    background: #161b22;
    border-radius: 4px;
    border-left: 2px solid #30363d;
}

.edge-reason-text {
    font-size: 12px;
    color: #8b949e;
    line-height: 1.5;
    margin-bottom: 4px;
}

.edge-code-block {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 11px;
    color: #e1e4e8;
    margin: 4px 0 0;
    white-space: pre-wrap;
    word-break: break-word;
}

.edge-nav-hint {
    margin-top: 10px;
    font-size: 11px;
    color: #3d4450;
    font-style: italic;
    padding-top: 8px;
    border-top: 1px solid #21262d;
}
```

**Acceptance criteria (R9-A):**
- Mỗi edge = 1 dòng collapsed khi mới load node
- Click ▶ → expand reason + code (nếu có)
- Click ▼ → collapse lại
- Click tên node → navigate sang node đó
- Navigation hint hiển thị cuối EDGES section
- Edges không có reason/code → dấu `·` (không clickable toggle)

**Commit message:**
```
Wave G Hotfix4 Task 1: viewer EDGES — collapse/expand per item + nav hint
```

---

## TASK 2 — selectNodeById helper

**Goal:** Đảm bảo click tên node trong EDGES section navigate đúng.

**Re-read hàm navigate/select node hiện tại trong viewer.**

Tạo hoặc cập nhật helper:

```javascript
function selectNodeById(nodeId) {
    // Tìm node trong GRAPH_DATA.nodes
    const node = (GRAPH_DATA.nodes || []).find(n => n.id === nodeId);
    if (node) {
        // Dùng existing select/highlight function
        selectNode(node);  // hoặc tên function tương đương hiện có
    } else {
        // Fallback: search by id
        console.warn('Node not found in graph:', nodeId);
    }
}
```

**Lưu ý:** Re-read code trước — có thể `selectNode` đã tồn tại với signature khác. Adapt cho phù hợp.

**Acceptance criteria (R9-A):**
- Click tên node trong EDGES → node được highlight trên graph
- Detail panel chuyển sang node đó
- Không có console errors

**Commit message:**
```
Wave G Hotfix4 Task 2: viewer — selectNodeById helper for edge navigation
```

---

## POST-HOTFIX VERIFICATION

```
python -m gobp.viewer.server --root D:\GoBP
# http://localhost:8080/

# □ Click node "GoBP Schema v3" 
#   → EDGES (10) — tất cả collapsed
#   → Click ▶ cạnh "Schema Base Node Template"
#   → Expand: hiện reason "Schema v3 defines base node..."
#   → Click ▶ lần nữa → collapse
#   → Click tên "GoBP Architecture v3" → navigate sang node đó
#   → Navigation hint hiển thị cuối list
```

---

## CEO DISPATCH

### Cursor
```
Read gobp/viewer/index.html — renderEdges(), CSS, select/navigate functions.
Read waves/wave_g_hotfix4.md (this file).
Execute Tasks 1 → 2 sequentially.
R9-A: verify collapse/expand + navigate.
End: pytest tests/ -q --tb=no
```

### Push
```powershell
cd D:\GoBP
git add waves/wave_g_hotfix4.md
git commit -m "Wave G Hotfix4 Brief: viewer EDGES collapse/expand + navigation — 2 tasks"
git push origin main
```

---

*Wave G Hotfix 4 — 2026-04-20 — CTO Chat*  
◈
