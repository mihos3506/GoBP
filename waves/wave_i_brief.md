# WAVE I BRIEF — EDGE POLICY IMPLEMENTATION

**Wave:** I  
**Title:** Implement Edge Policy v1 — 5 groups × 5 edge types vào GoBP schema + dispatcher  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-20  
**For:** Cursor (sequential execution) + Claude CLI (audit)  
**Status:** READY FOR EXECUTION  
**Task count:** 5 atomic tasks  
**Source:** `docs/EDGE_POLICY.md` (file policy đã commit)  

---

## CONTEXT

GoBP hiện chỉ có 2 edge types: `discovered_in` + `references`.  
Wave I expand lên 5 core edge types theo Edge Policy v1:

```
depends_on   — phụ thuộc kỹ thuật (traverse tier 1)
implements   — hiện thực đặc tả (traverse tier 1)
enforces     — ràng buộc áp lên Code/Test (traverse tier 2)
covers       — Test bao phủ (traverse tier 2)
discovered_in — provenance (skip traverse)
```

5 role groups:
```
Knowledge  = Doc + Spec + Lesson
Code       = Flow/Engine/Entity/ErrorCase/...
Constraint = Invariant/BusinessRule/...
Test       = TestSuite/TestKind/TestCase
Meta       = Session/Wave/Task/Reflection
```

---

## REQUIRED READING

| # | File |
|---|---|
| 1 | `docs/EDGE_POLICY.md` (full) |
| 2 | `gobp/schema/core_edges.yaml` |
| 3 | `gobp/core/validator_v3.py` |
| 4 | `gobp/mcp/dispatcher.py` — edge: handler |
| 5 | `gobp/mcp/tools/read_v3.py` — context: action |

---

## TASK 1 — core_edges.yaml: Thêm 4 edge types mới

**File to modify:** `gobp/schema/core_edges.yaml`

**Re-read file hiện tại trước.**

Thêm 4 edge types mới (giữ `discovered_in`, thêm `depends_on`, `implements`, `enforces`, `covers`):

```yaml
edge_types:
  discovered_in:
    description: "Node được tạo ra trong session nào (provenance)"
    traverse_priority: skip
    reason_required: false
    reason_template: null

  depends_on:
    description: "from cần to để đứng vững / hoạt động đúng"
    traverse_priority: high
    reason_required: false
    reason_template: "{from_name} cần {to_name} để hoạt động đúng."

  implements:
    description: "from hiện thực đặc tả / contract của to"
    traverse_priority: high
    reason_required: false
    reason_template: "{from_name} hiện thực đặc tả {to_name}."

  enforces:
    description: "Constraint áp ràng buộc lên Code hoặc Test"
    traverse_priority: medium
    reason_required: true   # required_short khi from=Constraint
    reason_template: "{from_name} ràng buộc {to_name}."

  covers:
    description: "Test bao phủ Code / Constraint / Knowledge"
    traverse_priority: low
    reason_required: false
    reason_template: "{from_name} kiểm chứng {to_name}."

role_groups:
  Knowledge:
    node_types: [Document, Spec, Idea, Lesson, LessonRule, LessonDev, LessonQA, LessonCTO]

  Code:
    node_types: [Flow, Feature, Engine, UseCase, Command, Entity, ValueObject, Aggregate,
                 Repository, APIContract, APIEndpoint, Module, Class, Function, Interface,
                 ErrorCase, ErrorDomain]

  Constraint:
    node_types: [Invariant, BusinessRule, Precondition, Postcondition, Policy]

  Test:
    node_types: [TestSuite, TestKind, TestCase]

  Meta:
    node_types: [Session, Wave, Task, Reflection]

matrix:
  # from_group: {to_group: allowed_edge_type}
  Knowledge:
    Knowledge: depends_on
    Code: implements
    Constraint: depends_on
    Test: covers
    Meta: discovered_in
  Code:
    Knowledge: implements
    Code: depends_on
    Constraint: enforces
    Test: covers
    Meta: discovered_in
  Constraint:
    Knowledge: depends_on
    Code: enforces
    Meta: discovered_in
  Test:
    Knowledge: covers
    Code: covers
    Constraint: enforces
    Test: depends_on
    Meta: discovered_in
  Meta:
    Knowledge: depends_on
    Meta: discovered_in
```

**Acceptance criteria:**
- `core_edges.yaml` có 5 edge types với đầy đủ fields
- `role_groups` mapping đúng node types
- `matrix` đúng theo Edge Policy v1

**Commit message:**
```
Wave I Task 1: core_edges.yaml — 5 edge types + role groups + matrix
```

---

## TASK 2 — validator_v3.py: Validate edge type + matrix

**File to modify:** `gobp/core/validator_v3.py`

**Re-read validator_v3.py trước — tìm edge validation logic.**

Thêm validation cho:

```python
# 1. Edge type phải thuộc 5 core types
VALID_EDGE_TYPES = {
    'depends_on', 'implements', 'enforces', 'covers', 'discovered_in'
}

# 2. Load role_groups và matrix từ core_edges.yaml
def _get_role_group(node_type: str) -> str | None:
    """Trả về role group của node type. None nếu không tìm thấy."""
    for group, config in ROLE_GROUPS.items():
        if node_type in config['node_types']:
            return group
    return None

# 3. Validate edge theo matrix
def validate_edge_type(from_type: str, to_type: str, edge_type: str) -> dict:
    """
    Returns: {ok: bool, warning: str | None}
    Soft validation — warning, không fail write
    """
    from_group = _get_role_group(from_type)
    to_group   = _get_role_group(to_type)

    if not from_group or not to_group:
        return {'ok': True, 'warning': None}  # unknown group → skip

    if edge_type not in VALID_EDGE_TYPES:
        return {'ok': False, 'warning': f"Unknown edge type: {edge_type}"}

    allowed = MATRIX.get(from_group, {}).get(to_group)
    if allowed and edge_type != allowed:
        return {
            'ok': True,
            'warning': f"Edge {from_group}→{to_group} expected '{allowed}', got '{edge_type}'"
        }

    # enforces từ Constraint → Code cần reason
    if edge_type == 'enforces' and from_group == 'Constraint':
        return {'ok': True, 'needs_reason': True}

    return {'ok': True, 'warning': None}

# 4. Auto-generate reason từ template nếu không có
def auto_reason(from_name: str, to_name: str, edge_type: str) -> str:
    """Sinh reason từ template nếu không được cung cấp."""
    templates = {
        'depends_on':   f"{from_name} cần {to_name} để hoạt động đúng.",
        'implements':   f"{from_name} hiện thực đặc tả {to_name}.",
        'enforces':     f"{from_name} ràng buộc {to_name}.",
        'covers':       f"{from_name} kiểm chứng {to_name}.",
        'discovered_in': '',
    }
    return templates.get(edge_type, '')
```

**Acceptance criteria:**
- `validate_edge_type()` trả về warning khi edge type sai matrix
- `auto_reason()` sinh template đúng cho từng edge type
- Không có hard failure — chỉ warning (soft validation)
- Tests pass

**Commit message:**
```
Wave I Task 2: validator_v3 — edge type validation + auto_reason template
```

---

## TASK 3 — dispatcher.py: Wire edge validation + auto_reason

**File to modify:** `gobp/mcp/dispatcher.py`

**Re-read `edge:` handler trước.**

Trong `edge:` action handler:

```python
elif action == 'edge':
    from_id    = params.get('from', '')
    to_id      = params.get('to', '')
    edge_type  = params.get('edge_type', 'depends_on')  # default depends_on
    reason     = params.get('reason', '')
    code       = params.get('code', '')

    # Lấy node types để validate
    from_node = index.get_node(from_id)
    to_node   = index.get_node(to_id)

    if from_node and to_node:
        from gobp.core.validator_v3 import validate_edge_type, auto_reason

        validation = validate_edge_type(
            from_node.get('type', ''),
            to_node.get('type', ''),
            edge_type
        )

        # Auto-generate reason nếu trống
        if not reason:
            reason = auto_reason(
                from_node.get('name', from_id),
                to_node.get('name', to_id),
                edge_type
            )

        # Attach warning vào response nếu có
        result = tools_write.edge_create(index, project_root, {
            'from': from_id, 'to': to_id,
            'edge_type': edge_type,
            'reason': reason, 'code': code,
            **params
        })

        if validation.get('warning'):
            result['warning'] = validation['warning']
```

**Acceptance criteria:**
- `edge: A --depends_on--> B` không có reason → auto-fill từ template
- `edge: A --wrongtype--> B` → warning trong response, không fail
- `edge: A --enforces--> B` từ Constraint → warning nếu không có reason

**Commit message:**
```
Wave I Task 3: dispatcher edge: — wire edge validation + auto_reason
```

---

## TASK 4 — read_v3.py: context: BFS theo traverse_priority

**File to modify:** `gobp/mcp/tools/read_v3.py`

**Re-read `context:` action trước.**

Update BFS trong `context:` để follow traverse_priority:

```python
TRAVERSE_PRIORITY = {
    'depends_on':    'tier_1',   # luôn expand
    'implements':    'tier_1',   # luôn expand
    'enforces':      'tier_2',   # expand nếu còn budget
    'covers':        'tier_2',   # expand nếu còn budget
    'discovered_in': 'skip',     # không traverse
    # legacy
    'references':    'tier_2',
}

def _bfs_context(seed_ids: list[str], conn, budget: int = 500) -> list[dict]:
    """
    BFS expand từ seed nodes theo traverse_priority.
    budget = token estimate limit.
    """
    visited = set(seed_ids)
    result  = []
    queue   = list(seed_ids)
    tokens_used = 0

    while queue and tokens_used < budget:
        node_id = queue.pop(0)
        node    = _fetch_node(conn, node_id)
        if not node:
            continue

        # Estimate tokens
        tokens_used += len(node.get('desc_l2', '') or '') // 4 + 20

        result.append(node)

        # Expand tier_1 edges
        edges = _fetch_edges(conn, node_id)
        for e in edges:
            priority = TRAVERSE_PRIORITY.get(e.get('type', ''), 'skip')
            if priority == 'skip':
                continue
            other_id = e['to'] if e['from'] == node_id else e['from']
            if other_id not in visited:
                if priority == 'tier_1':
                    queue.insert(0, other_id)  # high priority → front
                elif priority == 'tier_2' and tokens_used < budget * 0.7:
                    queue.append(other_id)     # low priority → back
                visited.add(other_id)

    return result
```

**Acceptance criteria:**
- `context: task="implement payment"` → expand `depends_on` + `implements` trước
- `discovered_in` edges không được traverse trong context:
- Token budget được tôn trọng

**Commit message:**
```
Wave I Task 4: read_v3 context: — BFS follows traverse_priority from edge policy
```

---

## TASK 5 — Tests + CHANGELOG

**Files to modify:** `tests/test_wave_i.py` (mới), `CHANGELOG.md`

**Tạo `tests/test_wave_i.py`:**

```python
"""Wave I: Edge Policy tests"""
import pytest
from gobp.core.validator_v3 import validate_edge_type, auto_reason

def test_valid_edge_knowledge_to_code():
    r = validate_edge_type('Spec', 'Flow', 'implements')
    assert r['ok'] is True
    assert r.get('warning') is None

def test_wrong_edge_type_warning():
    r = validate_edge_type('Spec', 'Flow', 'covers')
    assert r['ok'] is True
    assert 'warning' in r and r['warning']

def test_auto_reason_depends_on():
    r = auto_reason('Flow A', 'Engine B', 'depends_on')
    assert 'Flow A' in r and 'Engine B' in r

def test_auto_reason_implements():
    r = auto_reason('PaymentEngine', 'Payment Spec', 'implements')
    assert 'hiện thực đặc tả' in r

def test_auto_reason_empty_for_discovered_in():
    r = auto_reason('NodeX', 'Session Y', 'discovered_in')
    assert r == ''

def test_enforces_needs_reason_from_constraint():
    r = validate_edge_type('Invariant', 'Flow', 'enforces')
    assert r.get('needs_reason') is True

def test_unknown_node_type_skip():
    r = validate_edge_type('UnknownType', 'Flow', 'depends_on')
    assert r['ok'] is True

def test_discovered_in_must_go_to_meta():
    r = validate_edge_type('Spec', 'Flow', 'discovered_in')
    assert r.get('warning')  # Flow không thuộc Meta

def test_valid_test_covers_code():
    r = validate_edge_type('TestCase', 'Engine', 'covers')
    assert r['ok'] is True
    assert not r.get('warning')
```

**Update CHANGELOG.md** — prepend:

```markdown
## [Wave I] — Edge Policy Implementation — 2026-04-20

### Added
- `gobp/schema/core_edges.yaml`: 5 edge types (depends_on, implements, enforces, covers, discovered_in)
- `gobp/schema/core_edges.yaml`: role_groups (5 groups) + matrix 5×5
- `gobp/core/validator_v3.py`: validate_edge_type() + auto_reason() template
- `gobp/mcp/dispatcher.py`: edge: handler wired với edge validation + auto_reason
- `gobp/mcp/tools/read_v3.py`: context: BFS theo traverse_priority
- `tests/test_wave_i.py`: 9 tests

### Changed
- Edge type mặc định khi tạo edge là `depends_on` (trước: không có default)
- `context:` action ưu tiên `depends_on` + `implements` trong BFS (tier 1)
- `discovered_in` không còn được traverse trong context:
```

**Commit message:**
```
Wave I Task 5: tests/test_wave_i.py + CHANGELOG
```

---

## POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# Fast suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave_i.py -v
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no

# Manual verify
# gobp(query="edge: doc.spec.schema_v3.xxx --implements--> doc.spec.schema_base.yyy")
# → reason auto-filled + no warning
```

---

## CEO DISPATCH

### Cursor
```
Read docs/EDGE_POLICY.md (full).
Read gobp/schema/core_edges.yaml.
Read gobp/core/validator_v3.py.
Read gobp/mcp/dispatcher.py (edge: handler).
Read gobp/mcp/tools/read_v3.py (context: action).
Read waves/wave_i_brief.md (this file).

Execute Tasks 1 → 5 sequentially.
Task 1-3: R9-B verify.
Task 4: R9-B verify context: action.
Task 5: pytest tests/test_wave_i.py → 9 passed.
End: pytest tests/ -q --tb=no → 0 new failures.
```

### Claude CLI Audit
```
Task 1: core_edges.yaml — 5 types + role_groups + matrix đúng policy
Task 2: validate_edge_type() + auto_reason() đúng spec
Task 3: dispatcher edge: — auto_reason + warning wired
Task 4: context: BFS tier_1 expand trước, skip discovered_in
Task 5: 9 tests pass, CHANGELOG đúng
BLOCKING: Bất kỳ fail → STOP.
```

### Push
```powershell
cd D:\GoBP
git add waves/wave_i_brief.md
git commit -m "Wave I Brief: Edge Policy Implementation — 5 tasks"
git push origin main
```

---

*Wave I Brief — Edge Policy Implementation*  
*2026-04-20 — CTO Chat*  
◈
