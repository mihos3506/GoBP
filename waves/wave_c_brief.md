# WAVE C BRIEF — WRITE PATH v3 + VIEWER FIXES

**Wave:** C  
**Title:** Mutator v3 + edit: action + Viewer UI overhaul  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-19  
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)  
**Status:** READY FOR EXECUTION  
**Task count:** 9 atomic tasks  
**Estimated effort:** 6-8 hours  

---

## CONTEXT

Wave C giải quyết 2 nhóm vấn đề:

**1. Viewer UI (Tasks 1-3):** Viewer đang hiển thị schema v2 artifacts (lifecycle, read_order, DISCOVERED_IN edges) gây noise và khó đọc. Cần cleanup triệt để.

**2. Write Path v3 (Tasks 4-9):** Build mutator v3, edit: action (delete + create semantic), optimistic locking, cache invalidation update.

---

## VIEWER PROBLEMS (từ screenshot)

```
Problem 1 — DISCOVERED_IN flood:
  Relationships panel toàn là "← DISCOVERED_IN [session]"
  reason: (empty) trên tất cả
  → Noise hoàn toàn, không có giá trị
  → Fix: ẩn DISCOVERED_IN edges trong panel

Problem 2 — reason: (empty):
  Edges không có reason vẫn hiển thị "reason: (empty)"
  → Fix: chỉ hiển thị reason khi có nội dung

Problem 3 — lifecycle + read_order:
  "lifecycle: draft · read_order: background" vẫn hiển thị
  → Schema v3 đã xóa 2 fields này
  → Fix: ẩn hoàn toàn

Problem 4 — Sidebar:
  LIFECYCLE filter và READ ORDER filter
  → Không còn ý nghĩa trong schema v3
  → Fix: xóa cả 2 filter sections

Problem 5 — Font/màu/hierarchy:
  Font nhỏ, màu kém contrast
  Node level không phân biệt rõ trong graph
  Sidebar hierarchy không rõ ràng
  → Fix: cải thiện typography + node colors
```

---

## REFERENCED DOCUMENTS

| Doc | Focus |
|---|---|
| `docs/SCHEMA.md` | Schema v3 — no lifecycle, no read_order, no edge type |
| `docs/ARCHITECTURE.md` | Section 7 (write path), Section 9 (cache), Section 15 (multi-agent) |
| `docs/MCP_PROTOCOL.md` | edit: syntax, optimistic lock |

---

## CURSOR EXECUTION RULES

### R1-R8: Standard (xem `.cursorrules`)

### R9 — Testing strategy
- Viewer tasks (1-3): R9-A — verify UI loads, no console errors
- Code tasks (4-8): R9-B — module tests only
- Task 9 (tests): R9-B — `pytest tests/test_wave_c.py -v --tb=short`
- End of wave: `pytest tests/ -q --tb=no` (fast suite, NO slow, NO `--override-ini`)

### R10: Session start/end (per CEO: skip graph writes)
### R11: Report doc changes
### R12: Docs scope

---

## REQUIRED READING — BEFORE TASK 1

| # | File |
|---|---|
| 1 | `.cursorrules` (full — QR1-QR7) |
| 2 | `docs/SCHEMA.md` |
| 3 | `docs/ARCHITECTURE.md` Sections 7, 9, 15 |
| 4 | `docs/MCP_PROTOCOL.md` (edit: section) |
| 5 | `gobp/viewer/index.html` |
| 6 | `gobp/viewer/server.py` |
| 7 | `gobp/core/mutator.py` |
| 8 | `gobp/core/db.py` |
| 9 | `gobp/core/pyramid.py` |
| 10 | `gobp/core/validator_v3.py` |
| 11 | `gobp/mcp/batch_parser.py` |

---

## TASKS

---

## TASK 1 — Viewer: Fix Relationships Panel

**Goal:** Ẩn DISCOVERED_IN edges, ẩn empty reasons, ẩn lifecycle/read_order.

**File to modify:** `gobp/viewer/index.html`

**Re-read toàn bộ `index.html` trước. Tìm phần render node detail panel.**

### Fix 1: Ẩn DISCOVERED_IN trong relationships

Tìm chỗ render relationships/edges trong detail panel. Thêm filter:

```javascript
// Lọc edges trước khi render
function filterRelationships(edges) {
    return edges.filter(edge => {
        const edgeType = (edge.type || edge.relationship || '').toUpperCase();
        // Ẩn DISCOVERED_IN — đây là session tracking, không phải knowledge
        if (edgeType === 'DISCOVERED_IN') return false;
        return true;
    });
}
```

### Fix 2: Ẩn reason khi empty

```javascript
// Chỉ hiển thị reason khi có nội dung
function renderReason(reason) {
    if (!reason || reason.trim() === '' || reason === '(empty)') return '';
    return `<div class="edge-reason">${reason}</div>`;
}
```

### Fix 3: Ẩn lifecycle và read_order

Tìm chỗ render node detail fields. Comment out hoặc xóa render cho:
- `lifecycle`
- `read_order`

```javascript
// Danh sách fields KHÔNG hiển thị trong detail panel
const HIDDEN_FIELDS = [
    'lifecycle', 'read_order', 'priority',
    'session_id', 'content_hash', '_dispatch', '_protocol',
    'revision', 'fts_content'
];

function shouldShowField(fieldName) {
    return !HIDDEN_FIELDS.includes(fieldName.toLowerCase());
}
```

**Acceptance criteria (R9-A):**
- Mở viewer → click node → Relationships panel KHÔNG có DISCOVERED_IN entries
- Edges không có reason → không hiển thị "reason: (empty)"
- Node detail panel KHÔNG hiển thị lifecycle, read_order
- Các relationship có reason thực sự → hiển thị đúng

**Commit message:**
```
Wave C Task 1: viewer — hide DISCOVERED_IN edges, empty reasons, legacy fields

- filterRelationships(): exclude DISCOVERED_IN edge type
- renderReason(): skip empty/null reasons
- HIDDEN_FIELDS: lifecycle, read_order, priority hidden from detail panel
```

---

## TASK 2 — Viewer: Sidebar Cleanup

**Goal:** Xóa LIFECYCLE và READ ORDER filter sections khỏi sidebar.

**File to modify:** `gobp/viewer/index.html`

**Re-read sidebar HTML trước.**

Tìm và xóa (hoặc comment out) các sections:
1. `LIFECYCLE` filter section (checkboxes draft/specified/implemented...)
2. `READ ORDER` filter section (checkboxes foundational/important/reference/background)

Những filter này dựa trên schema v2 fields — schema v3 không còn những fields này.

**Acceptance criteria (R9-A):**
- Sidebar KHÔNG có LIFECYCLE section
- Sidebar KHÔNG có READ ORDER section
- GROUP filter vẫn hoạt động bình thường
- SEARCH vẫn hoạt động bình thường

**Commit message:**
```
Wave C Task 2: viewer sidebar — remove LIFECYCLE + READ ORDER filter sections

- Removed: lifecycle filter (schema v3 has no lifecycle field)
- Removed: read_order filter (schema v3 has no read_order field)
- Kept: GROUP, SEARCH, VIEW filters
```

---

## TASK 3 — Viewer: Typography + Node Colors

**Goal:** Cải thiện font, contrast, node color by group level.

**File to modify:** `gobp/viewer/index.html`

**Re-read CSS/styles trong index.html trước.**

### Fix 1: Typography

```css
/* Tăng font size + contrast */
body, .sidebar {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 
                 'Inter', sans-serif;
    font-size: 14px;          /* tăng từ mức hiện tại */
    line-height: 1.5;
}

/* Node labels trong graph rõ hơn */
.node-label {
    font-size: 13px;
    font-weight: 500;
    color: #f0e6d3;           /* cream white, contrast tốt trên dark bg */
}

/* Sidebar items */
.group-item {
    font-size: 13px;
    color: #c9b99a;
}

/* Node type badge */
.node-type {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: #f0883e;
}

/* Detail panel headings */
.detail-section-title {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #8b949e;
}
```

### Fix 2: Node colors by top-level group

```javascript
// Màu theo top-level group — dễ phân biệt hierarchy
const GROUP_COLORS = {
    'Dev':        '#4a90d9',  // blue
    'Document':   '#f0883e',  // orange (brand color)
    'Constraint': '#e06c75',  // red
    'Error':      '#e06c75',  // red
    'Test':       '#98c379',  // green
    'Meta':       '#c678dd',  // purple
    'Unknown':    '#636d83',  // gray
};

function getNodeColor(node) {
    const group = node.group || node.group_path || '';
    const topGroup = group.split('>')[0].trim();
    return GROUP_COLORS[topGroup] || GROUP_COLORS['Unknown'];
}
```

### Fix 3: Sidebar hierarchy indentation

```css
/* Phân biệt level rõ hơn */
.group-level-0 { padding-left: 8px;  font-weight: 600; }
.group-level-1 { padding-left: 20px; font-weight: 500; }
.group-level-2 { padding-left: 32px; font-weight: 400; color: #8b949e; }
.group-level-3 { padding-left: 44px; font-weight: 400; color: #6e7681; }
```

**Acceptance criteria (R9-A):**
- Graph nodes có màu theo top-level group (Dev=blue, Document=orange, etc.)
- Font size đủ lớn để đọc được
- Sidebar hierarchy có indentation rõ ràng theo level
- Node labels trong graph readable

**Commit message:**
```
Wave C Task 3: viewer — typography + node colors by group level

- GROUP_COLORS: node color by top-level group (Dev/Document/Constraint/etc.)
- Font: size 14px, Inter/system-ui, better contrast
- Sidebar: indentation by depth level
- Node labels: cream white, font-weight 500
```

---

## TASK 4 — PostgreSQL v3 Functions

**Goal:** Thêm v3 DB functions vào `gobp/core/db.py`.

**File to modify:** `gobp/core/db.py`

**Re-read toàn bộ `db.py` trước.**

Thêm các functions:

```python
def upsert_node_v3(conn, node: dict) -> None:
    """Upsert node vào PostgreSQL schema v3."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO nodes
                (id, name, group_path, desc_l1, desc_l2, desc_full,
                 code, severity, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                    extract(epoch from now())::BIGINT)
            ON CONFLICT (id) DO UPDATE SET
                name       = EXCLUDED.name,
                group_path = EXCLUDED.group_path,
                desc_l1    = EXCLUDED.desc_l1,
                desc_l2    = EXCLUDED.desc_l2,
                desc_full  = EXCLUDED.desc_full,
                code       = EXCLUDED.code,
                severity   = EXCLUDED.severity,
                updated_at = EXCLUDED.updated_at
        """, (
            node['id'],
            node['name'],
            node.get('group', node.get('group_path', '')),
            node.get('desc_l1', ''),
            node.get('desc_l2', ''),
            node.get('desc_full', node.get('description', '')),
            node.get('code', ''),
            node.get('severity', ''),
        ))
        conn.commit()


def delete_node_v3(conn, node_id: str) -> None:
    """Delete node + CASCADE edges."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM nodes WHERE id = %s", (node_id,))
        conn.commit()


def upsert_edge_v3(conn, from_id: str, to_id: str,
                   reason: str = '', code: str = '') -> None:
    """Upsert edge — no type field."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO edges (from_id, to_id, reason, code, created_at)
            VALUES (%s, %s, %s, %s, extract(epoch from now())::BIGINT)
            ON CONFLICT (from_id, to_id) DO UPDATE SET
                reason = EXCLUDED.reason,
                code   = EXCLUDED.code
        """, (from_id, to_id, reason, code))
        conn.commit()


def delete_edge_v3(conn, from_id: str, to_id: str) -> None:
    """Delete edge."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM edges WHERE from_id=%s AND to_id=%s",
            (from_id, to_id)
        )
        conn.commit()


def append_history_v3(conn, node_id: str,
                      description: str, code: str = '') -> None:
    """Append history entry (append-only)."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO node_history
                (node_id, description, code, created_at)
            VALUES (%s, %s, %s, extract(epoch from now())::BIGINT)
        """, (node_id, description, code))
        conn.commit()


def get_node_updated_at(conn, node_id: str) -> int | None:
    """Get updated_at — dùng cho optimistic locking."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT updated_at FROM nodes WHERE id = %s", (node_id,)
        )
        row = cur.fetchone()
        return row[0] if row else None
```

**Acceptance criteria:**
- Mỗi function hoạt động đúng với PostgreSQL schema v3
- `upsert_node_v3()` ON CONFLICT DO UPDATE đúng
- `delete_node_v3()` CASCADE xóa edges
- `upsert_edge_v3()` KHÔNG có type field
- `get_node_updated_at()` trả về int hoặc None

**Commit message:**
```
Wave C Task 4: db.py — v3 upsert/delete functions (node, edge, history)
```

---

## TASK 5 — Mutator v3

**Goal:** Tạo `gobp/core/mutator_v3.py` — full write path theo ARCHITECTURE.md Section 7.

**File to create:** `gobp/core/mutator_v3.py`

```python
"""
GoBP Mutator v3.

Write path:
  1. auto_fix   (infer group, normalize description)
  2. validate   (2 templates)
  3. generate_id
  4. extract_pyramid (desc_l1, desc_l2, desc_full)
  5. write PostgreSQL (ON CONFLICT DO UPDATE)
  6. write file backup
  7. append JSONL history log
  8. return {ok, id, conflict_warning?}

edit: = delete old + create new (with inherited history)
"""

from __future__ import annotations
import json
import datetime
from pathlib import Path
from typing import Any

from gobp.core.validator_v3 import ValidatorV3
from gobp.core.id_generator import generate_id
from gobp.core.pyramid import pyramid_from_node
from gobp.core.file_format_v3 import (
    serialize_node, deserialize_node, node_file_path
)
from gobp.core.db import (
    upsert_node_v3, delete_node_v3,
    upsert_edge_v3, delete_edge_v3,
    append_history_v3, get_node_updated_at,
)

_validator = ValidatorV3()


def write_node(
    node_data: dict[str, Any],
    gobp_dir: Path,
    conn=None,
    session_id: str = '',
    expected_updated_at: int | None = None,
) -> dict[str, Any]:
    """Full write path for a single node."""

    # 1. auto_fix
    node = _validator.auto_fix(dict(node_data))

    # 2. validate
    errors = _validator.validate(node)
    if errors:
        return {'ok': False, 'errors': errors}

    # 3. generate_id
    if not node.get('id'):
        node['id'] = generate_id(node['name'], node['group'])

    # 4. extract pyramid
    l1, l2 = pyramid_from_node(node)
    node['desc_l1']   = l1
    node['desc_l2']   = l2
    node['desc_full'] = _get_full_text(node)

    # 5. optimistic lock check
    conflict_warning = None
    if conn and expected_updated_at is not None:
        current_ts = get_node_updated_at(conn, node['id'])
        if current_ts and current_ts != expected_updated_at:
            conflict_warning = {
                'conflict': True,
                'expected': expected_updated_at,
                'actual':   current_ts,
                'message':  'Node was modified by another agent',
            }

    # 6. write PostgreSQL
    if conn:
        upsert_node_v3(conn, node)

    # 7. write file backup
    (gobp_dir / 'nodes').mkdir(parents=True, exist_ok=True)
    node_file_path(gobp_dir, node['id']).write_text(
        serialize_node(node), encoding='utf-8'
    )

    # 8. append history log
    _log(gobp_dir, {
        'ts':      _now(),
        'op':      'node_upsert',
        'actor':   node_data.get('_actor', 'unknown'),
        'id':      node['id'],
        'session': session_id,
    })

    result: dict[str, Any] = {'ok': True, 'id': node['id']}
    if conflict_warning:
        result['conflict_warning'] = conflict_warning
    return result


def edit_node(
    node_id: str,
    changes: dict[str, Any],
    gobp_dir: Path,
    conn=None,
    session_id: str = '',
    expected_updated_at: int | None = None,
) -> dict[str, Any]:
    """
    edit: action — DELETE old + CREATE new.

    - description/code change: same ID, content replaced
    - type/group change: new ID, old deleted, history inherited
    - add_edge/remove_edge: edge operations on this node
    """
    # Load existing node
    fp = node_file_path(gobp_dir, node_id)
    if not fp.exists():
        return {'ok': False, 'errors': [f'Node not found: {node_id}']}
    existing = deserialize_node(fp.read_text(encoding='utf-8'))
    if not existing:
        return {'ok': False, 'errors': [f'Cannot deserialize: {node_id}']}

    # Handle edge operations (separate from field changes)
    changes = dict(changes)
    add_edge    = changes.pop('add_edge', None)
    remove_edge = changes.pop('remove_edge', None)
    edge_reason = changes.pop('reason', '')
    edge_code   = changes.pop('code_edge', '')

    if add_edge and conn:
        upsert_edge_v3(conn, node_id, add_edge, edge_reason, edge_code)
        _log(gobp_dir, {'ts': _now(), 'op': 'edge_add',
                        'from': node_id, 'to': add_edge, 'session': session_id})

    if remove_edge and conn:
        delete_edge_v3(conn, node_id, remove_edge)
        _log(gobp_dir, {'ts': _now(), 'op': 'edge_remove',
                        'from': node_id, 'to': remove_edge, 'session': session_id})

    # No field changes? Done.
    if not changes:
        return {'ok': True, 'id': node_id}

    # Merge: existing + changes
    updated = {**existing, **changes}

    # Inherit history (append new entries)
    updated['history'] = existing.get('history', []) + changes.get('history', [])

    # Check if group or name changed → new ID needed
    old_group = existing.get('group', '')
    new_group  = updated.get('group', old_group)
    old_name   = existing.get('name', '')
    new_name   = updated.get('name', old_name)

    if new_group != old_group or new_name != old_name:
        # New ID, delete old
        new_id = generate_id(new_name, new_group)
        updated['id'] = new_id
        if conn:
            delete_node_v3(conn, node_id)
        if fp.exists():
            fp.unlink()

    updated['_actor'] = changes.get('_actor', 'unknown')
    return write_node(updated, gobp_dir, conn, session_id, expected_updated_at)


def delete_node(
    node_id: str,
    gobp_dir: Path,
    conn=None,
    session_id: str = '',
) -> dict[str, Any]:
    """Soft delete: archive file + remove from PostgreSQL."""
    fp = node_file_path(gobp_dir, node_id)
    if fp.exists():
        archive = gobp_dir / 'archive'
        archive.mkdir(parents=True, exist_ok=True)
        fp.rename(archive / fp.name)

    if conn:
        delete_node_v3(conn, node_id)

    _log(gobp_dir, {'ts': _now(), 'op': 'node_delete',
                    'id': node_id, 'session': session_id})
    return {'ok': True, 'id': node_id}


def _get_full_text(node: dict) -> str:
    desc = node.get('description', '')
    if isinstance(desc, str):
        return desc
    if isinstance(desc, dict):
        return desc.get('info', '') or ''
    return ''


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + 'Z'


def _log(gobp_dir: Path, event: dict) -> None:
    today = datetime.date.today().isoformat()
    log_dir = gobp_dir / 'history'
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / f"{today}.jsonl", 'a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')
```

**Acceptance criteria:**
- `write_node()`: full pipeline — validate → pyramid → PG → file → log
- `write_node()` với `expected_updated_at` sai → `conflict_warning` trong response
- `edit_node()` đổi description: ID giữ nguyên
- `edit_node()` đổi group: ID mới, old deleted, history inherited
- `edit_node()` `add_edge`/`remove_edge`: edge ops
- `delete_node()`: file archived, PG deleted

**Commit message:**
```
Wave C Task 5: gobp/core/mutator_v3.py — full write path v3

- write_node(): validate → pyramid → PG → file → JSONL log
- edit_node(): delete+create semantic, edge ops, history inherit
- delete_node(): soft delete to archive
- Optimistic lock: conflict_warning on updated_at mismatch
```

---

## TASK 6 — Batch Parser: Add edit: op

**Goal:** Update `gobp/mcp/batch_parser.py` — thêm `edit:` op.

**File to modify:** `gobp/mcp/batch_parser.py`

**Re-read toàn bộ batch_parser.py trước.**

`edit:` syntax:
```
edit: id="{node_id}" description="{new}"
edit: id="{node_id}" type="{NewType}"
edit: id="{node_id}" add_edge="{to_id}" reason="{reason}"
edit: id="{node_id}" remove_edge="{to_id}"
```

Parser output: `{'op': 'edit', 'id': '...', 'changes': {...}}`

Rules:
- `id` field là required
- Các fields khác → `changes` dict
- `update:` và `retype:` → backward compat, map tới `edit:`

**Acceptance criteria:**
- `parse("edit: id=\"x\" description=\"y\"")` → `{'op':'edit','id':'x','changes':{'description':'y'}}`
- `parse("edit: id=\"x\" type=\"Engine\"")` → `{'op':'edit','id':'x','changes':{'type':'Engine'}}`
- `parse("edit: id=\"x\" add_edge=\"y\" reason=\"r\"")` → edge op parsed
- Missing `id` → error

**Commit message:**
```
Wave C Task 6: batch_parser.py — add edit: op (supersedes update: + retype:)
```

---

## TASK 7 — MCP write.py: Wire edit: action

**Goal:** Wire `edit:` action vào MCP layer.

**Files to modify:** `gobp/mcp/tools/write.py`, `gobp/mcp/dispatcher.py`

**Re-read cả 2 files trước.**

```python
# write.py
def handle_edit(index, gobp_dir, conn, args):
    from gobp.core.mutator_v3 import edit_node

    node_id    = args.get('id', '')
    session_id = args.get('session_id', '')
    expected   = args.get('expected_updated_at')

    if not node_id:
        return {'ok': False, 'errors': ['id required for edit:']}
    if not session_id:
        return {'ok': False, 'errors': ['session_id required for edit:']}

    changes = {k: v for k, v in args.items()
               if k not in ('id', 'session_id', 'expected_updated_at', '_actor')}
    changes['_actor'] = args.get('_actor', 'unknown')

    return edit_node(
        node_id=node_id, changes=changes,
        gobp_dir=gobp_dir, conn=conn,
        session_id=session_id,
        expected_updated_at=expected,
    )
```

```python
# dispatcher.py — thêm route
'edit': handle_edit,
```

**Acceptance criteria:**
- `gobp(query="edit: id='x' description='new' session_id='s'")` → calls `edit_node()`
- `gobp(query="edit: id='x' type='Engine' session_id='s'")` → type change
- `gobp(query="edit: id='x' add_edge='y' reason='r' session_id='s'")` → edge op
- Missing id/session_id → clear error response
- Response có `conflict_warning` khi có conflict

**Commit message:**
```
Wave C Task 7: wire edit: action — write.py handler + dispatcher route
```

---

## TASK 8 — Cache Invalidation: Node + Edge

**Goal:** Update `QueryCache` — thêm `invalidate_node()` và `invalidate_edge()`.

**File to modify:** `gobp/core/cache.py`

**Re-read `cache.py` trước.**

```python
def invalidate_node(self, node_id: str) -> None:
    """Invalidate sau node write."""
    self._cache = {k: v for k, v in self._cache.items()
                   if node_id not in k}

def invalidate_edge(self, from_id: str, to_id: str) -> None:
    """Invalidate sau edge write — affects cả 2 nodes."""
    self._cache = {k: v for k, v in self._cache.items()
                   if from_id not in k and to_id not in k}
```

**Acceptance criteria:**
- `invalidate_node('x')` → xóa cache entries có 'x' trong key
- `invalidate_edge('a', 'b')` → xóa entries có 'a' hoặc 'b'
- Existing `invalidate_group()` unchanged
- Cache miss sau invalidate → returns None, không crash

**Commit message:**
```
Wave C Task 8: cache.py — invalidate_node() + invalidate_edge()
```

---

## TASK 9 — Tests Wave C

**Goal:** Tests cover write path, edit:, optimistic lock, cache.

**File to create:** `tests/test_wave_c.py`

Tests phải cover:

**DB functions (db.py):**
- `upsert_node_v3()` insert mới và update cũ
- `delete_node_v3()` xóa đúng
- `upsert_edge_v3()` không có type field
- `get_node_updated_at()` trả về timestamp hoặc None

**Mutator v3:**
- `write_node()` happy path: node hợp lệ → ok + file tạo
- `write_node()` invalid node → errors returned
- `write_node()` với `expected_updated_at` match → ok, no warning
- `write_node()` với `expected_updated_at` mismatch → conflict_warning
- `edit_node()` description change → same ID
- `edit_node()` group change → new ID, old file deleted
- `edit_node()` history inherited sau group change
- `delete_node()` file archived, removed from disk

**Batch parser:**
- `edit:` op parsed đúng với id + changes
- `edit:` với `add_edge`/`remove_edge` parsed
- `update:` backward compat mapped tới edit

**Cache:**
- `invalidate_node()` clears relevant entries
- `invalidate_edge()` clears both endpoint entries

**Acceptance criteria:**
- Tất cả behaviors trên có test coverage
- Tests dùng `tmp_path`, không dùng live DB
- Existing tests không bị regression

**Commit message:**
```
Wave C Task 9: tests/test_wave_c.py — write path v3 coverage
```

---

## POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# Viewer
python -m gobp.viewer.server --root D:\MIHOS-v1
# http://localhost:8080/ → no LIFECYCLE/READ ORDER in sidebar
# Click node → no DISCOVERED_IN, no "reason: (empty)", no lifecycle/read_order

# edit: action
# gobp(query="edit: id='x' description='new' session_id='s'") → ok

# Full suite (fast, no slow)
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

## CEO DISPATCH INSTRUCTIONS

### 0. Push new docs (nếu chưa push)

```powershell
cd D:\GoBP
git add docs/SCHEMA.md docs/ARCHITECTURE.md docs/MCP_PROTOCOL.md
git add docs/COOKBOOK.md docs/AGENT_RULES.md docs/HISTORY_SPEC.md
git add docs/README.md .cursorrules
git commit -m "chore: doc set v3 + .cursorrules v10"
git push origin main
```

### 1. Cursor

```
Read .cursorrules (full).
Read docs/SCHEMA.md, docs/ARCHITECTURE.md, docs/MCP_PROTOCOL.md.
Read gobp/viewer/index.html, gobp/viewer/server.py.
Read gobp/core/mutator.py, gobp/core/db.py, gobp/core/cache.py.
Read gobp/mcp/batch_parser.py, gobp/mcp/tools/write.py.
Read waves/wave_c_brief.md (this file).

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute Tasks 1 → 9 sequentially.
Tasks 1-3: R9-A (verify UI, no pytest).
Tasks 4-8: R9-B (module tests only).
Task 9: R9-B (test_wave_c.py only).
End: fast suite only — pytest tests/ -q --tb=no (NO --override-ini, NO slow).
```

### 2. Claude CLI audit

```
Audit Wave C.
Tasks 1-3: Verify viewer UI fixes (DISCOVERED_IN gone, lifecycle gone, fonts improved)
Task 4: upsert/delete functions work, edges have no type field
Task 5: write_node() pipeline correct, edit_node() delete+create semantic
Task 6: edit: op parsed, update:/retype: backward compat
Task 7: edit: action wired, conflict_warning returned when needed
Task 8: invalidate_node/edge work correctly
Task 9: All behaviors covered, no regression
BLOCKING: Bất kỳ fail → STOP, báo CEO.
```

### 3. Push (sau khi audit PASS)

```powershell
cd D:\GoBP
git log --oneline | Select-Object -First 9
git push origin main
```

---

*Wave C Brief — Write Path v3 + Viewer UI Overhaul*  
*2026-04-19 — CTO Chat*  
◈
