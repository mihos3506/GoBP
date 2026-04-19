# WAVE G HOTFIX — VIEWER 3 BUGS

**Wave:** G-Hotfix  
**Title:** Viewer — Show all edges sync + CODE field + HISTORY section  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-19  
**For:** Cursor — thực hiện SAU Wave G  
**Status:** READY FOR EXECUTION  
**Task count:** 3 atomic tasks  

---

## BUGS

```
Bug 1: Show all edges → sidebar group circles không sync
  Expected: Toggle ON → tất cả group items hiển thị ● (active)
  Actual:   Chỉ selected group ●, các group khác ○

Bug 2: CODE section không hiển thị trong node detail
  Expected: Nodes có code field → CODE section render
  Schema v3: code là field bắt buộc trong template
  Actual:   CODE section bị ẩn, không render

Bug 3: HISTORY section không có trong node detail
  Expected: Nodes có history[] → HISTORY section render
  Schema v3: history[] append-only, field có trong nodes
  Actual:   Không có HISTORY section nào trong detail panel
```

---

## FILE: `gobp/viewer/index.html`

---

## TASK 1 — Fix Show all edges: Sidebar circles sync

**Re-read handler của `showAllEdges` checkbox trước.**

Khi "Show all edges" được toggle:
- ON → tất cả group items trong sidebar set active state (●)
- OFF → chỉ giữ item đang được filter active

```javascript
// Tìm handler của showAllEdges checkbox
document.getElementById('showAllEdges').addEventListener('change', function() {
    SHOW_ALL_EDGES = this.checked;

    if (SHOW_ALL_EDGES) {
        // Set tất cả group items sang active state
        document.querySelectorAll('.group-item').forEach(item => {
            item.classList.add('active');
        });
    } else {
        // Restore: chỉ active group đang filter
        document.querySelectorAll('.group-item').forEach(item => {
            item.classList.remove('active');
        });
        // Re-apply current filter highlight
        _highlightActiveGroup(currentGroupFilter);
    }

    updateGraph();
});
```

**Acceptance criteria (R9-A):**
- Toggle ON → tất cả group circles ● active trong sidebar
- Toggle OFF → chỉ group đang filter ● active
- Graph update đúng khi toggle

**Commit message:**
```
Wave G Hotfix Task 1: viewer — show all edges syncs all sidebar circles active
```

---

## TASK 2 — Fix CODE section: Luôn render khi có data

**Re-read `renderCodeBlock` function trước.**

**Vấn đề:** CODE section bị hide khi `node.code` empty/undefined thay vì render với placeholder hoặc không render gì.

**Fix:**

```javascript
function renderCode(node) {
    // Lấy code từ v3 hoặc v2 compat
    const code = node.code
        || (node.description && node.description.code)
        || '';

    if (!code || !code.trim()) return '';

    return `
    <div class="detail-section">
        <div class="detail-section-title">CODE</div>
        <pre class="code-block"><code>${escapeHtml(code.trim())}</code></pre>
    </div>`;
}
```

Thêm vào render pipeline sau DESCRIPTION:
```javascript
// Trong renderNodeDetail():
html += renderDescription(node);
html += renderCode(node);       // ← sau description
html += renderEdges(edges);
html += renderHistory(node);    // ← sau edges
```

**Acceptance criteria (R9-A):**
- Node có `code` field có data → CODE section hiển thị
- Node không có `code` → không có CODE section (không hiện trống)
- Code được escape HTML đúng

**Commit message:**
```
Wave G Hotfix Task 2: viewer — CODE section renders when node has code field
```

---

## TASK 3 — Add HISTORY Section

**Re-read renderNodeDetail() function trước.**

**Implement HISTORY section:**

```javascript
function renderHistory(node) {
    const history = node.history || [];

    if (!history.length) return '';

    const items = history.map((entry, i) => {
        const desc = entry.description || entry.desc || '';
        const code = entry.code || '';
        const ts   = entry.created_at
            ? new Date(entry.created_at * 1000).toLocaleDateString()
            : '';

        return `
        <div class="history-item">
            <div class="history-header">
                <span class="history-index">#${i + 1}</span>
                ${ts ? `<span class="history-date">${ts}</span>` : ''}
            </div>
            <div class="history-desc">${escapeHtml(desc)}</div>
            ${code ? `<pre class="code-block history-code"><code>${escapeHtml(code)}</code></pre>` : ''}
        </div>`;
    }).join('');

    return `
    <div class="detail-section">
        <div class="detail-section-title">HISTORY (${history.length})</div>
        ${items}
    </div>`;
}
```

```css
.history-item {
    padding: 8px 0;
    border-bottom: 1px solid #21262d;
}
.history-item:last-child { border-bottom: none; }

.history-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
}

.history-index {
    font-size: 11px;
    color: #636d83;
    font-variant-numeric: tabular-nums;
}

.history-date {
    font-size: 11px;
    color: #636d83;
}

.history-desc {
    font-size: 13px;
    color: #c9b99a;
    line-height: 1.4;
}

.history-code {
    margin-top: 6px;
    font-size: 11px;
}
```

**Thứ tự render final:**
```
1. Breadcrumb + Type + Severity badge (ErrorCase)
2. Node Name
3. DESCRIPTION
4. CODE (nếu có)
5. EDGES
6. HISTORY (nếu có)
```

**Acceptance criteria (R9-A):**
- Node có `history[]` → HISTORY section hiển thị cuối panel
- Mỗi entry: index + date (nếu có) + description + code (nếu có)
- Node không có history → không có HISTORY section
- Scroll hoạt động đúng khi nhiều history entries

**Commit message:**
```
Wave G Hotfix Task 3: viewer — add HISTORY section to node detail panel
```

---

## POST-HOTFIX VERIFICATION

```powershell
python -m gobp.viewer.server --root D:\GoBP
# http://localhost:8080/
# □ Toggle "Show all edges" → tất cả circles ●
# □ Node có code → CODE section hiện
# □ Node có history → HISTORY section hiện
# □ Thứ tự: DESCRIPTION → CODE → EDGES → HISTORY
```

---

## CEO DISPATCH

### Cursor
```
Read gobp/viewer/index.html (TOÀN BỘ — biết rõ cấu trúc hiện tại).
Read waves/wave_g_hotfix.md (this file).
Execute Tasks 1 → 3 sequentially.
Tất cả R9-A (verify UI, no pytest).
End: pytest tests/ -q --tb=no
```

### Claude CLI audit
```
Task 1: Show all edges → tất cả sidebar circles ● active
Task 2: CODE section render đúng
Task 3: HISTORY section có, thứ tự render đúng
```

### Push
```powershell
cd D:\GoBP
git add waves/wave_g_hotfix.md
git commit -m "Wave G Hotfix: Viewer — 3 bugs (edges sync, CODE, HISTORY)"
git push origin main
```

---

*Wave G Hotfix — 2026-04-19 — CTO Chat*  
◈
