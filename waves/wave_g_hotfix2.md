# WAVE G HOTFIX 2 — VIEWER EDGE BUG

**Wave:** G-Hotfix-2  
**Title:** Viewer — EDGES section hiển thị tất cả edges liên quan, không phân biệt chiều  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-20  
**For:** Cursor  
**Status:** READY FOR EXECUTION  
**Task count:** 1 atomic task  

---

## VẤN ĐỀ

```
Screenshot: Node "Phase 1: Import 7 GoBP docs" có 35 edges trên graph
Nhưng detail panel → EDGES: "No connections"

Root cause:
  renderEdges() chỉ filter edges where e.from === nodeId
  Node này chỉ có incoming edges (discovered_in từ các nodes khác)
  → Tất cả edges bị bỏ qua → "No connections"

Sai bản chất:
  Edge = mối quan hệ giữa 2 nodes — không có incoming/outgoing
  Khi click node X → hiển thị TẤT CẢ edges liên quan X
  Chỉ cần: tên node kia + reason
```

---

## TASK 1 — Fix renderEdges(): hiển thị tất cả edges liên quan node

**File to modify:** `gobp/viewer/index.html`

**Re-read `renderEdges()` function trước.**

**Fix:** Filter cả 2 chiều, render tên node kia + reason:

```javascript
function renderEdges(nodeId, allEdges, allNodes) {
    // Lấy tất cả edges liên quan nodeId — cả 2 chiều
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

    const items = related.map(e => {
        // Lấy ID của node kia
        const otherId = (e.from === nodeId || e.from_id === nodeId)
            ? (e.to || e.to_id)
            : (e.from || e.from_id);

        // Lấy tên node kia
        const otherNode = (allNodes || []).find(n => n.id === otherId);
        const otherName = otherNode
            ? (otherNode.name || otherId)
            : (e.to_name || e.from_name || otherId);

        const reason = e.reason || '';

        return `
        <div class="edge-item">
            <div class="edge-header">
                <span class="edge-node-name"
                      onclick="selectNode('${otherId}')"
                >${otherName}</span>
            </div>
            ${reason ? `<div class="edge-reason">${reason}</div>` : ''}
        </div>`;
    }).join('');

    return `
    <div class="detail-section">
        <div class="detail-section-title">EDGES (${related.length})</div>
        ${items}
    </div>`;
}
```

**Lưu ý quan trọng:**
- Không còn `direction` (→/←) — chỉ show tên node kia + reason
- `reason` vẫn hiển thị khi có — giúp AI hiểu tại sao kết nối tồn tại
- Click tên node → navigate tới node đó
- Tên node kia lấy từ `allNodes` lookup hoặc `to_name`/`from_name` field

**Acceptance criteria (R9-A):**
- Click node "Phase 1 session" → EDGES hiển thị 35 connections
- Click node "GoBP Schema v3" → EDGES hiển thị tất cả references + discovered_in
- Mỗi edge item: tên node kia (clickable) + reason (nếu có)
- Không còn phân biệt → hay ← trong UI

**Commit message:**
```
Wave G Hotfix2: viewer EDGES — show all related edges, no direction distinction
```

---

## POST-HOTFIX VERIFICATION

```powershell
python -m gobp.viewer.server --root D:\GoBP
# http://localhost:8080/
# □ Click Session node → EDGES hiển thị 35 connections
# □ Click GoBP Schema v3 → EDGES hiển thị tất cả edges
# □ Click tên node trong EDGES → navigate đúng
# □ reason hiển thị dưới tên node khi có
```

---

## CEO DISPATCH

### Cursor
```
Read gobp/viewer/index.html — tìm renderEdges() function.
Read waves/wave_g_hotfix2.md (this file).
Execute Task 1.
R9-A: verify UI — Session node shows all 35 edges.
End: pytest tests/ -q --tb=no
```

### Push
```powershell
cd D:\GoBP
git add waves/wave_g_hotfix2.md
git commit -m "Wave G Hotfix2 Brief: viewer EDGES — 1 task"
git push origin main
```

---

*Wave G Hotfix 2 — 2026-04-20 — CTO Chat*  
◈
