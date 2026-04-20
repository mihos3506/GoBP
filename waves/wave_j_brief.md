# WAVE J BRIEF — IMPLEMENTED FIELD

**Wave:** J  
**Title:** Thêm `implemented` field vào GoBP schema — boolean status cho nodes  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-20  
**For:** Cursor (sequential execution) + Claude CLI (audit)  
**Status:** READY FOR EXECUTION  
**Task count:** 4 atomic tasks  

---

## CONTEXT

Hiện tại GoBP không có cách để AI biết một Spec/Feature node đã được
implement trong code chưa. AI đọc node nhưng không biết:
- Đây là plan chưa làm hay đã có code?
- Code nằm ở đâu?

**Giải pháp:** Thêm field `implemented` (boolean) vào schema.

```
implemented: false   ← default, chưa có code
implemented: true    ← đã implement, code field chứa file path
```

**Đơn giản — chỉ Yes/No:**
```
false = planned, chưa có implementation
true  = có implementation, đọc code field để biết đâu
```

---

## REQUIRED READING

| # | File |
|---|---|
| 1 | `gobp/schema/core_nodes.yaml` |
| 2 | `gobp/core/validator_v3.py` |
| 3 | `gobp/mcp/tools/write.py` — node create/upsert |
| 4 | `gobp/mcp/tools/read_v3.py` — context: action |
| 5 | `docs/SCHEMA.md` |

---

## TASK 1 — core_nodes.yaml: Thêm implemented field

**File to modify:** `gobp/schema/core_nodes.yaml`

**Re-read file trước.**

Thêm `implemented` vào base template (áp dụng cho mọi node type trừ Meta):

```yaml
base_fields:
  name:          {str, required}
  group:         {str, required}
  description:   {str, required}
  code:          {str, optional}
  implemented:   {bool, optional, default: false}
  history:       {list, optional, append-only}
```

**Không áp dụng cho:**
```yaml
excluded_from_implemented:
  - Session
  - Wave
  - Task
  - Reflection
```

**Acceptance criteria:**
- `implemented` field có trong base template
- Default value: `false`
- Meta group nodes không có field này

**Commit message:**
```
Wave J Task 1: core_nodes.yaml — add implemented boolean field
```

---

## TASK 2 — validator_v3.py: Validate + default implemented

**File to modify:** `gobp/core/validator_v3.py`

**Re-read validator_v3.py trước.**

```python
# Meta node types không cần implemented field
META_TYPES = {'Session', 'Wave', 'Task', 'Reflection'}

def coerce_implemented(node: dict) -> dict:
    """
    Auto-set implemented=False nếu chưa có.
    Không apply cho Meta types.
    """
    node_type = node.get('type', '')
    if node_type in META_TYPES:
        return node
    
    if 'implemented' not in node:
        node['implemented'] = False
    else:
        # Coerce to bool
        node['implemented'] = bool(node['implemented'])
    
    return node


def validate_implemented(node: dict) -> list[str]:
    """
    Warnings:
    - implemented=True nhưng code field trống → warning
    """
    warnings = []
    node_type = node.get('type', '')
    
    if node_type in META_TYPES:
        return warnings
    
    if node.get('implemented') is True:
        code = node.get('code', '')
        if not code or not code.strip():
            warnings.append(
                f"Node '{node.get('name', '?')}': implemented=True "
                f"nhưng code field trống. "
                f"Nên thêm file path vào code field."
            )
    
    return warnings
```

Wire vào `coerce_and_validate_node()`:
```python
def coerce_and_validate_node(node):
    # ... existing validation ...
    node = coerce_implemented(node)
    warnings = validate_implemented(node)
    # attach warnings to result
    return node, warnings
```

**Acceptance criteria:**
- Node tạo mới không có `implemented` → auto-set `false`
- Node `implemented=true` không có code → warning (non-blocking)
- Meta nodes không bị touch

**Commit message:**
```
Wave J Task 2: validator_v3 — coerce + validate implemented field
```

---

## TASK 3 — PostgreSQL: Thêm implemented column

**File to modify:** `gobp/core/db.py`

**Re-read `create_schema_v3()` và `upsert_node_v3()` trước.**

Thêm `implemented` column vào nodes table:

```python
# Trong create_schema_v3():
CREATE TABLE IF NOT EXISTS nodes (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    group_path  TEXT,
    desc_l1     TEXT,
    desc_l2     TEXT,
    desc_full   TEXT,
    code        TEXT,
    implemented BOOLEAN NOT NULL DEFAULT FALSE,  -- ← thêm
    node_type   TEXT,
    search_vec  TSVECTOR,
    created_at  BIGINT,
    updated_at  BIGINT
);
```

Update `upsert_node_v3()`:
```python
def upsert_node_v3(conn, node: dict) -> None:
    implemented = bool(node.get('implemented', False))
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO nodes 
                (id, name, group_path, desc_l1, desc_l2, desc_full,
                 code, implemented, node_type, search_vec,
                 created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    to_tsvector('simple', %s),
                    %s,%s)
            ON CONFLICT (id) DO UPDATE SET
                name        = EXCLUDED.name,
                group_path  = EXCLUDED.group_path,
                desc_l1     = EXCLUDED.desc_l1,
                desc_l2     = EXCLUDED.desc_l2,
                desc_full   = EXCLUDED.desc_full,
                code        = EXCLUDED.code,
                implemented = EXCLUDED.implemented,
                node_type   = EXCLUDED.node_type,
                search_vec  = EXCLUDED.search_vec,
                updated_at  = EXCLUDED.updated_at
        """, (
            node['id'], node.get('name', ''),
            node.get('group', ''),
            node.get('desc_l1', ''), node.get('desc_l2', ''),
            node.get('desc_full', node.get('description', '')),
            node.get('code', ''),
            implemented,
            node.get('type', ''),
            _build_search_text(node),
            node.get('created_at', int(time.time())),
            node.get('updated_at', int(time.time())),
        ))
    conn.commit()
```

**Migration:** Nếu table đã tồn tại, thêm column:
```python
def migrate_add_implemented(conn) -> None:
    """Add implemented column if not exists."""
    with conn.cursor() as cur:
        cur.execute("""
            ALTER TABLE nodes 
            ADD COLUMN IF NOT EXISTS implemented BOOLEAN NOT NULL DEFAULT FALSE
        """)
    conn.commit()
```

Gọi `migrate_add_implemented()` trong `_init_postgresql_backend()` sau `create_schema_v3()`.

**Acceptance criteria:**
- Column `implemented` tồn tại trong nodes table
- `implemented=false` khi không set
- `upsert_node_v3` lưu đúng giá trị

**Commit message:**
```
Wave J Task 3: db.py — add implemented column to nodes table
```

---

## TASK 4 — Tests + SCHEMA.md + CHANGELOG

**Files:** `tests/test_wave_j.py` (mới), `docs/SCHEMA.md`, `CHANGELOG.md`

**Tests:**

```python
"""Wave J: implemented field tests"""
import pytest
from gobp.core.validator_v3 import coerce_implemented, validate_implemented

def test_default_implemented_false():
    node = {'type': 'Spec', 'name': 'x', 'group': 'y'}
    result = coerce_implemented(node)
    assert result['implemented'] is False

def test_implemented_true_preserved():
    node = {'type': 'Engine', 'implemented': True, 'code': 'path/to/file.py'}
    result = coerce_implemented(node)
    assert result['implemented'] is True

def test_implemented_true_no_code_warning():
    node = {'type': 'Flow', 'name': 'x', 'implemented': True, 'code': ''}
    warnings = validate_implemented(node)
    assert len(warnings) == 1
    assert 'code field' in warnings[0]

def test_implemented_true_with_code_no_warning():
    node = {'type': 'Engine', 'name': 'x', 'implemented': True, 'code': 'gobp/core/graph.py'}
    warnings = validate_implemented(node)
    assert len(warnings) == 0

def test_meta_nodes_skip_implemented():
    for meta_type in ['Session', 'Wave', 'Task', 'Reflection']:
        node = {'type': meta_type, 'name': 'x'}
        result = coerce_implemented(node)
        assert 'implemented' not in result

def test_coerce_truthy_values():
    for val in [1, 'true', True]:
        node = {'type': 'Spec', 'implemented': val}
        result = coerce_implemented(node)
        assert result['implemented'] is True

def test_coerce_falsy_values():
    for val in [0, False, None]:
        node = {'type': 'Spec', 'implemented': val}
        result = coerce_implemented(node)
        assert result['implemented'] is False
```

**Update docs/SCHEMA.md** — thêm vào Template 1:

```markdown
## TEMPLATE 1 — MỌI NODE

name:           {tên mô tả rõ ràng}
group:          {breadcrumb đầy đủ}
description:    {plain text — mô tả đầy đủ}
code:           {optional — snippet kỹ thuật hoặc file path khi implemented=true}
implemented:    {false (default) | true — đã có implementation trong code}
history[]:      [{description, code}]   # append-only

Ghi chú implemented:
  false = planned, chưa có code implementation
  true  = đã implement — code field nên chứa file path
```

**Update CHANGELOG.md** — prepend:

```markdown
## [Wave J] — Implemented Field — 2026-04-20

### Added
- `implemented` boolean field vào GoBP schema (default: false)
- `coerce_implemented()` + `validate_implemented()` trong validator_v3.py
- `implemented` column trong PostgreSQL nodes table
- Migration: `ALTER TABLE nodes ADD COLUMN IF NOT EXISTS implemented`
- Warning khi `implemented=true` nhưng `code` field trống
- `tests/test_wave_j.py`: 7 tests

### Changed
- `docs/SCHEMA.md` Template 1: thêm implemented field
- Meta nodes (Session/Wave/Task/Reflection) không có implemented field
```

**Commit message:**
```
Wave J Task 4: tests/test_wave_j.py + SCHEMA.md + CHANGELOG
```

---

## POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# Tests
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave_j.py -v

# Verify column exists in PG
D:/GoBP/venv/Scripts/python.exe -c "
import psycopg2
conn = psycopg2.connect('postgresql://postgres:Hieu%408283%40@localhost/gobp')
cur = conn.cursor()
cur.execute(\"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='nodes' AND column_name='implemented'\")
print(cur.fetchall())
conn.close()
"
# Expected: [('implemented', 'boolean')]

# Fast suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

## CEO DISPATCH

### Cursor
```
Read gobp/schema/core_nodes.yaml.
Read gobp/core/validator_v3.py.
Read gobp/core/db.py (create_schema_v3, upsert_node_v3).
Read docs/SCHEMA.md.
Read waves/wave_j_brief.md (this file).

Execute Tasks 1 → 4 sequentially.
Task 3: Verify PG column exists after migration.
Task 4: pytest tests/test_wave_j.py → 7 passed.
End: pytest tests/ -q --tb=no → 0 new failures.
```

### Claude CLI Audit
```
Task 1: core_nodes.yaml có implemented field + Meta exclusion
Task 2: coerce_implemented() + validate_implemented() đúng spec
Task 3: PG column implemented BOOLEAN DEFAULT FALSE
Task 4: 7 tests pass, SCHEMA.md + CHANGELOG đúng
BLOCKING: Bất kỳ fail → STOP.
```

### Push
```powershell
cd D:\GoBP
git add waves/wave_j_brief.md
git commit -m "Wave J Brief: implemented field — 4 tasks"
git push origin main
```

---

*Wave J Brief — Implemented Field*  
*2026-04-20 — CTO Chat*  
◈
