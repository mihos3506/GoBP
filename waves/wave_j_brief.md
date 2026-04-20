# WAVE J BRIEF — IMPLEMENTED FIELD + BUG FIXES

**Wave:** J  
**Title:** implemented field + 3 bug fixes trong write/read path  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-20  
**For:** Cursor (sequential execution) + Claude CLI (audit)  
**Status:** READY FOR EXECUTION  
**Task count:** 5 atomic tasks  

---

## CONTEXT

Wave J giải quyết 4 vấn đề:

```
1. Schema thiếu implemented field
   AI không biết Spec/Feature đã có code chưa

2. Bug: file_format.py ghi description không sanitize YAML
   description chứa :, {, }, (, ) → file .md corrupt
   Toàn bộ write path fail vì 1 file lỗi

3. Bug: GraphIndex.load_from_disk() crash khi gặp 1 file lỗi
   1 file .md bad → toàn bộ write operations fail
   edit:/create:/delete: không dùng được

4. Bug: edit:/delete: dùng file lookup khác get:/find:
   get: tìm được node nhưng edit: không tìm được
   Inconsistent behavior giữa read và write path
```

---

## REQUIRED READING

| # | File |
|---|---|
| 1 | `gobp/core/file_format.py` — serialize/deserialize |
| 2 | `gobp/core/graph.py` — _load_nodes, _load_edges |
| 3 | `gobp/mcp/dispatcher.py` — edit: delete: handlers |
| 4 | `gobp/schema/core_nodes.yaml` |
| 5 | `gobp/core/validator_v3.py` |
| 6 | `gobp/mcp/tools/read_v3.py` — get_node_v3 |
| 7 | `docs/SCHEMA.md` |

---

## TASK 1 — implemented field: schema + validator

**Files:** `gobp/schema/core_nodes.yaml`, `gobp/core/validator_v3.py`

### core_nodes.yaml — thêm implemented:

```yaml
base_fields:
  implemented:
    type: bool
    default: false
    excluded_types: [Session, Wave, Task, Reflection]
    note: "false = planned, true = has code implementation"
```

### validator_v3.py:

```python
META_TYPES = {'Session', 'Wave', 'Task', 'Reflection'}

def coerce_implemented(node: dict) -> dict:
    """Auto-set implemented=False nếu chưa có. Skip Meta types."""
    if node.get('type', '') in META_TYPES:
        return node
    if 'implemented' not in node:
        node['implemented'] = False
    else:
        node['implemented'] = bool(node['implemented'])
    return node

def validate_implemented(node: dict) -> list[str]:
    """Warning: implemented=True nhưng code field trống."""
    if node.get('type', '') in META_TYPES:
        return []
    if node.get('implemented') is True:
        if not (node.get('code') or '').strip():
            return [
                f"Node '{node.get('name','?')}': "
                f"implemented=True nhưng code field trống."
            ]
    return []
```

Wire vào `coerce_and_validate_node()`.

**Commit message:**
```
Wave J Task 1: implemented field — schema + validator
```

---

## TASK 2 — file_format.py: Fix YAML serialization

**Root cause:** Description được ghi dạng raw string vào frontmatter.
Nếu chứa `:`, `{`, `}`, `|`, `#`... → YAML parser lỗi → file corrupt
→ GraphIndex.load_from_disk() fail → toàn bộ write path fail.

**File to modify:** `gobp/core/file_format.py`

**Re-read serialize_node() hoặc write_node_file() trước.**

**Fix — dùng yaml.dump() thay vì string interpolation:**

```python
import yaml

def serialize_frontmatter(node: dict) -> str:
    """
    Serialize node dict thành YAML frontmatter.
    Dùng yaml.dump() — không dùng f-string/concatenation.
    yaml.dump() tự handle escaping mọi ký tự đặc biệt.
    """
    fm = {}
    field_order = [
        'type', 'id', 'name', 'group', 'description',
        'code', 'implemented', 'status', 'priority',
        'created_at', 'updated_at'
    ]
    for key in field_order:
        if key in node and node[key] is not None:
            fm[key] = node[key]
    # Include any extra fields
    for key, val in node.items():
        if key not in fm and val is not None:
            fm[key] = val

    return yaml.dump(
        fm,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=10000,  # Prevent line wrapping
    )


def write_node_file(gobp_root: Path, node: dict) -> Path:
    """Ghi node ra file .md với frontmatter luôn valid YAML."""
    nodes_dir = gobp_root / '.gobp' / 'nodes'
    nodes_dir.mkdir(parents=True, exist_ok=True)

    filename = _node_id_to_filename(node['id'])
    filepath = nodes_dir / filename

    frontmatter = serialize_frontmatter(node)
    content = f"---\n{frontmatter}---\n"

    filepath.write_text(content, encoding='utf-8')
    return filepath
```

**Acceptance criteria:**
- description chứa `:`, `{`, `}`, `(`, `)`, `|`, `#` → ghi xuống → load lại đúng
- Round-trip test: write → read → description không thay đổi
- Không còn YAML corrupt files từ write path

**Commit message:**
```
Wave J Task 2: file_format.py — yaml.dump() for safe YAML serialization
```

---

## TASK 3 — graph.py: Resilient _load_nodes/_load_edges

**Root cause:** `_load_nodes()` và `_load_edges()` bare loop —
1 file lỗi → Exception propagate → load_from_disk() crash →
write path hoàn toàn fail dù chỉ 1 file bị hỏng.

Task 2 ngăn tạo file lỗi mới.
Task 3 handle legacy files đã bị hỏng từ trước.
Cả 2 đều cần thiết.

**File to modify:** `gobp/core/graph.py`

```python
def _load_nodes(self, nodes_dir: Path) -> None:
    if not nodes_dir.exists():
        return
    for f in sorted(nodes_dir.glob("*.md")):
        try:
            node = load_node_file(f)
            if node:
                self._add_node(node)
        except Exception as e:
            logger.warning(
                "skip corrupted node file %s: %s", f.name, e
            )

def _load_edges(self, edges_dir: Path) -> None:
    if not edges_dir.exists():
        return
    for f in sorted(edges_dir.glob("*.yaml")):
        try:
            edges = load_edge_file(f)
            for edge in (edges or []):
                self._add_edge(edge)
        except Exception as e:
            logger.warning(
                "skip corrupted edge file %s: %s", f.name, e
            )
```

**Acceptance criteria:**
- 1 file .md YAML lỗi → chỉ node đó bị skip + warning logged
- GraphIndex.load_from_disk() không crash
- edit:/create:/delete: hoạt động bình thường

**Commit message:**
```
Wave J Task 3: graph.py — resilient _load_nodes/_load_edges
```

---

## TASK 4 — dispatcher.py: Unify edit:/delete: lookup

**Root cause:** `edit:` và `delete:` lookup node từ GraphIndex (file).
`get:` và `find:` lookup từ PostgreSQL.
→ Node tồn tại trong PG, file corrupt → get: OK, edit: "Node not found".

**File to modify:** `gobp/mcp/dispatcher.py`

**Re-read edit: và delete: handlers trước.**

Fix — thêm PG lookup trước GraphIndex fallback:

```python
def _resolve_node(node_id: str, index, project_root: Path) -> dict | None:
    """
    Lookup node — PG trước, GraphIndex fallback.
    Đảm bảo edit:/delete: nhất quán với get:/find:.
    """
    # Try PostgreSQL first (source of truth)
    try:
        from gobp.mcp.tools import read_v3 as _read_v3
        conn_v, is_v3 = _read_v3._conn_v3(project_root)
        if conn_v is not None and is_v3:
            try:
                node = _read_v3.get_node_v3(conn_v, node_id)
                if node:
                    return node
            finally:
                conn_v.close()
    except Exception:
        pass

    # Fallback to GraphIndex
    return index.get_node(node_id)
```

Dùng `_resolve_node()` trong cả `edit:` và `delete:` handlers:

```python
elif action == 'edit':
    node_id = params.get('id', '')
    node = _resolve_node(node_id, index, project_root)
    if node is None:
        result = {'ok': False, 'error': f'Node not found: {node_id}'}
    else:
        result = tools_write.node_edit(
            index, project_root, {**params, '_existing_node': node}
        )

elif action == 'delete':
    node_id = params.get('query', '')
    node = _resolve_node(node_id, index, project_root)
    if node is None:
        result = {'ok': False, 'error': f'Node not found: {node_id}'}
    else:
        result = tools_write.node_delete(index, project_root, params)
```

**Acceptance criteria:**
- `get: node_id` OK → `edit: id=node_id` phải OK
- `get: node_id` OK → `delete: node_id` phải OK
- Không còn asymmetry giữa read và write path

**Commit message:**
```
Wave J Task 4: dispatcher — unify edit:/delete: lookup with PG like get:/find:
```

---

## TASK 5 — Tests + docs + CHANGELOG

**File mới:** `tests/test_wave_j.py`

```python
"""Wave J: implemented field + bug fixes"""
import pytest

def test_default_implemented_false():
    from gobp.core.validator_v3 import coerce_implemented
    node = {'type': 'Spec', 'name': 'x', 'group': 'y'}
    assert coerce_implemented(node)['implemented'] is False

def test_implemented_true_preserved():
    from gobp.core.validator_v3 import coerce_implemented
    node = {'type': 'Engine', 'implemented': True, 'code': 'path.py'}
    assert coerce_implemented(node)['implemented'] is True

def test_implemented_true_no_code_warning():
    from gobp.core.validator_v3 import validate_implemented
    node = {'type': 'Flow', 'name': 'x', 'implemented': True, 'code': ''}
    assert len(validate_implemented(node)) == 1

def test_implemented_true_with_code_no_warning():
    from gobp.core.validator_v3 import validate_implemented
    node = {'type': 'Engine', 'name': 'x', 'implemented': True, 'code': 'file.py'}
    assert len(validate_implemented(node)) == 0

def test_meta_nodes_skip_implemented():
    from gobp.core.validator_v3 import coerce_implemented
    for t in ['Session', 'Wave', 'Task', 'Reflection']:
        node = coerce_implemented({'type': t, 'name': 'x'})
        assert 'implemented' not in node

def test_yaml_safe_description_colon():
    """description với : phải round-trip đúng"""
    from gobp.core.file_format import serialize_frontmatter
    import yaml
    desc = 'Role: Dev — execute: task'
    node = {'type': 'Spec', 'id': 'x', 'name': 'x',
            'group': 'y', 'description': desc}
    parsed = yaml.safe_load(serialize_frontmatter(node))
    assert parsed['description'] == desc

def test_yaml_safe_description_braces():
    """description với {, } phải round-trip đúng"""
    from gobp.core.file_format import serialize_frontmatter
    import yaml
    desc = 'Config: {key: value} format'
    node = {'type': 'Spec', 'id': 'x', 'name': 'x',
            'group': 'y', 'description': desc}
    parsed = yaml.safe_load(serialize_frontmatter(node))
    assert parsed['description'] == desc

def test_load_from_disk_skips_broken_file(tmp_path):
    """GraphIndex skips corrupted node files instead of crashing."""
    nodes_dir = tmp_path / '.gobp' / 'nodes'
    nodes_dir.mkdir(parents=True)
    (nodes_dir / 'valid.md').write_text(
        '---\ntype: Spec\nid: spec.valid\nname: Valid\n'
        'group: Document > Spec\ndescription: Valid node\n---\n'
    )
    (nodes_dir / 'broken.md').write_text(
        '---\ntype: Spec\ndescription: Role: broken yaml here\n---\n'
    )
    from gobp.core.graph import GraphIndex
    index = GraphIndex.load_from_disk(tmp_path)
    assert index.get_node('spec.valid') is not None
```

**docs/SCHEMA.md** — update Template 1:

```markdown
## TEMPLATE 1 — MỌI NODE

name:           {tên mô tả rõ ràng}
group:          {breadcrumb đầy đủ}
description:    {plain text — không dùng ký tự đặc biệt :, {, }, |, #}
code:           {optional — snippet hoặc file path khi implemented=true}
implemented:    {false (default) | true}
history[]:      [{description, code}]
```

**CHANGELOG.md** — prepend:

```markdown
## [Wave J] — implemented field + Bug Fixes — 2026-04-20

### Added
- implemented boolean field (default: false)
- Warning khi implemented=true nhưng code field trống

### Fixed
- file_format.py: yaml.dump() thay string interpolation — không còn YAML corrupt
- graph.py: _load_nodes/_load_edges skip corrupted files thay vì crash
- dispatcher.py: edit:/delete: lookup PG trước — nhất quán với get:/find:
```

**Commit message:**
```
Wave J Task 5: tests + SCHEMA.md + CHANGELOG — Wave J complete
```

---

## POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave_j.py -v
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

## CEO DISPATCH

### Cursor
```
Read gobp/core/file_format.py.
Read gobp/core/graph.py.
Read gobp/mcp/dispatcher.py (edit:, delete:).
Read gobp/schema/core_nodes.yaml.
Read gobp/core/validator_v3.py.
Read gobp/mcp/tools/read_v3.py (get_node_v3, _conn_v3).
Read waves/wave_j_brief.md (this file).

Execute Tasks 1 → 5 sequentially.
Task 2: Round-trip test — write node với : trong description → load lại đúng.
Task 3: Load GraphIndex với 1 file YAML lỗi → không crash.
Task 4: get: node_id OK → edit: id=node_id OK.
Task 5: pytest tests/test_wave_j.py → 8 passed.
End: pytest tests/ -q --tb=no → 0 new failures.
```

### Claude CLI Audit
```
Task 1: implemented field đúng schema + coerce/validate đúng spec
Task 2: yaml.dump() được dùng — không còn string interpolation/f-string
Task 3: try/except trong _load_nodes/_load_edges + logger.warning
Task 4: _resolve_node() helper tồn tại + edit:/delete: dùng nó
Task 5: 8 tests pass, SCHEMA.md + CHANGELOG đúng
BLOCKING: Bất kỳ fail → STOP.
```

### Push
```powershell
cd D:\GoBP
git add waves/wave_j_brief.md
git commit -m "Wave J Brief: implemented field + 3 bug fixes — 5 tasks"
git push origin main
```

---

*Wave J Brief — 2026-04-20 — CTO Chat*  
◈
