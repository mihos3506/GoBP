# WAVE 17A05 BRIEF — BUG FIXES + VIEWER v2

**Wave:** 17A05
**Title:** Batch parser bugs, create: auto-id, Viewer v2 display
**Author:** CTO Chat
**Date:** 2026-04-19
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 7 tasks
**Estimated effort:** 5-7 hours

---

## REFERENCED GOBP NODES

| Node ID | Topic |
|---|---|
| `dec:d004` | GoBP update obligation |
| `dec:d006` | Brief reference nodes |

---

## CONTEXT — Bugs phát hiện từ end-to-end test

4 bugs phát hiện khi CTO tự test import:

```
Bug 1: batch pipe format KHÔNG parse named params key="value"
  create: Decision: Name | what="..." why="..."
  → what/why không được đọc → required field missing

Bug 2: \n trong multiline string → batch parser split thành ops mới
  fix_guide="line1\nline2"
  → line2 bị parse là op mới → error

Bug 3: create:Type named params không auto-generate id
  create:Invariant rule='...' scope='...'
  → "Missing required field: id" → user phải tự truyền id

Bug 4: Concept pipe format → description thay vì definition
  create: Concept: Name | text
  → text đi vào description.info thay vì definition field
```

**Viewer vẫn là v1** — chưa reflect schema v2:
```
STATUS → phải là lifecycle
PRIORITY → phải là read_order
DESCRIPTION: flat → phải có info + code riêng
TOPIC: trống → phải là GROUP breadcrumb
OUTGOING → phải là RELATIONSHIPS với reason
Show raw fields → mặc định ẩn
ErrorCase → cần layout riêng đặc biệt
```

---

## CURSOR EXECUTION RULES

R1-R12 (.cursorrules v8).

**Testing:**
- Tasks 1-4 (bug fixes): R9-B module tests
- Tasks 5-6 (viewer): R9-B viewer tests
- Task 7: R9-C full suite (690+ baseline)

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 591 fast suite
```

---

# TASKS

---

## TASK 1 — Fix batch parser: named params trong pipe format

**Problem:**
```
create: Decision: Name | what="CTO manages" why="Thin harness"
→ Parser chỉ lấy "Name" và description từ pipe
→ what/why bị bỏ qua
```

**File:** `gobp/mcp/batch_parser.py`

Fix `_parse_create_op()` để extract named params sau `|`:

```python
def _parse_create_op(text: str) -> dict:
    """Parse create: op.

    Formats supported:
    1. create: Type: Name | description
    2. create: Type: Name | description key="value" key2='value2'
    3. create: Type: Name | key="value" key2='value2'  (no plain description)
    """
    # Split type:name from rest
    # Format: "Type: Name | rest"
    type_name_match = re.match(r'^(\w+):\s*(.+?)(?:\s*\|\s*(.*))?$', text)
    if not type_name_match:
        return {"op": "create", "error": f"invalid create format: {text}"}

    node_type = type_name_match.group(1).strip()
    name = type_name_match.group(2).strip()
    rest = type_name_match.group(3) or ""

    result = {"op": "create", "type": node_type, "name": name}

    if not rest:
        return result

    # Extract named params: key="value" or key='value' or key=value
    named_params = {}
    # Match key="value", key='value', key=value(no spaces)
    param_pattern = re.compile(
        r'(\w+)=(?:"([^"]*?)"|\'([^\']*?)\'|(\S+))'
    )
    matches = list(param_pattern.finditer(rest))

    # Extract named params
    for m in matches:
        key = m.group(1)
        value = m.group(2) or m.group(3) or m.group(4) or ""
        named_params[key] = value

    # Whatever is left before first named param = plain description
    if matches:
        first_param_start = matches[0].start()
        plain_desc = rest[:first_param_start].strip()
        if plain_desc:
            result["description"] = plain_desc
    else:
        result["description"] = rest.strip()

    # Merge named params
    result.update(named_params)

    return result
```

**Tests:**
```python
# test_batch_parser_named_params_double_quote
# test_batch_parser_named_params_single_quote
# test_batch_parser_named_params_with_description
# test_batch_parser_no_named_params (backward compat)
# test_batch_parser_decision_what_why
```

**Commit:**
```
Wave 17A05 Task 1: fix batch parser named params key="value"

- create: Type: Name | key="value" key2='value2' now parsed
- Plain description before named params preserved
- Backward compat: create: Type: Name | description still works
```

---

## TASK 2 — Fix batch parser: multiline string \n

**Problem:**
```
fix_guide="line1\nline2\nline3"
→ \n được interpret là newline → split thành ops
```

**File:** `gobp/mcp/batch_parser.py`

Fix `_split_ops()` để không split trong quoted strings:

```python
def _split_ops(ops_text: str) -> list[str]:
    """Split ops text into individual op lines.

    Rules:
    - Split on newlines ONLY when not inside quotes
    - Lines starting with known op prefixes are ops
    - Continuation lines (no prefix) are appended to previous op
    """
    lines = ops_text.split('\n')
    ops = []
    current_op = []
    in_quote = None  # None, '"', or "'"
    quote_depth = 0

    OP_PREFIXES = {
        'create:', 'update:', 'replace:', 'delete:',
        'retype:', 'merge:', 'edge+:', 'edge-:',
        'edge~:', 'edge*:', 'quick:', 'lock:'
    }

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check if this line starts a new op
        is_new_op = any(
            stripped.startswith(prefix)
            for prefix in OP_PREFIXES
        )

        if is_new_op and not in_quote:
            if current_op:
                ops.append(' '.join(current_op))
            current_op = [stripped]
            # Check if quote opened but not closed
            in_quote = _detect_unclosed_quote(stripped)
        else:
            # Continuation of previous op (e.g., inside quoted value)
            if current_op:
                current_op.append(stripped)
                # Check if quote closed
                if in_quote and in_quote in stripped:
                    in_quote = None
            # else: orphan line, skip

    if current_op:
        ops.append(' '.join(current_op))

    return [op for op in ops if op.strip()]


def _detect_unclosed_quote(text: str) -> str | None:
    """Return quote char if text has unclosed quote, else None."""
    in_quote = None
    for char in text:
        if char in ('"', "'") and not in_quote:
            in_quote = char
        elif char == in_quote:
            in_quote = None
    return in_quote
```

**Tests:**
```python
# test_split_ops_no_newline_in_value
# test_split_ops_multiline_quoted_value
# test_split_ops_normal_ops
```

**Commit:**
```
Wave 17A05 Task 2: fix batch parser multiline \n in quoted strings

- \n inside "..." or '...' no longer splits into new ops
- Continuation lines appended to current op
```

---

## TASK 3 — Fix create: auto-generate id

**Problem:**
```
create:Invariant rule='...' scope='class'
→ "Missing required field: id"
→ User phải tự truyền id — không thể
```

**File:** `gobp/mcp/tools/write.py`

Trong `node_upsert()` hoặc `_batch_build_create_node()`:

```python
from gobp.core.id_generator import generate_id
from gobp.core.schema_loader import load_schema_v2

def _ensure_node_id(node: dict, schema_v2=None) -> dict:
    """Auto-generate id if missing."""
    if node.get('id'):
        return node

    name = node.get('name', '')
    node_type = node.get('type', '')
    group = node.get('group', '')

    # Infer group from type if not set
    if not group and node_type and schema_v2:
        group = schema_v2.get_group(node_type)
        node['group'] = group

    if name and group:
        node['id'] = generate_id(name, group)
    elif name and node_type:
        # Fallback: use type as group slug
        node['id'] = generate_id(name, node_type)
    else:
        # Last resort: timestamp-based
        import time, hashlib
        node['id'] = hashlib.md5(
            f"{node_type}:{name}:{time.time_ns()}".encode()
        ).hexdigest()[:16]

    return node
```

Update `node_upsert()` để call `_ensure_node_id()` trước validation:
```python
def node_upsert(index, project_root, args):
    node = dict(args)
    node = _apply_v2_defaults(node, ...)
    node = _ensure_node_id(node, schema_v2)  # ← thêm đây
    node = _auto_fill_defaults(node)
    # ... continue với validate ...
```

**Tests:**
```python
# test_create_node_auto_id_from_name_group
# test_create_node_id_preserved_if_set
# test_create_invariant_no_id_required
```

**Commit:**
```
Wave 17A05 Task 3: auto-generate id for create: operations

- id auto-generated from name + group via id_generator v2
- Existing id preserved if already set
- Fallback: type-based id if group not available
```

---

## TASK 4 — Fix Concept pipe format → definition field

**Problem:**
```
create: Concept: Proof of Presence | GPS + device signal = proof
→ text → description.info ✓
→ definition field = empty ✗ (required)
```

**File:** `gobp/mcp/tools/write.py` — TYPE_DEFAULTS

```python
TYPE_DEFAULTS = {
    # ... existing ...
    "Concept": {
        "definition": lambda node: (
            node.get("description", {}).get("info", "")
            if isinstance(node.get("description"), dict)
            else node.get("description", "")
        ),
        "usage_guide": lambda node: (
            node.get("usage_guide") or
            "Usage guide — update after import"
        ),
    },
}
```

Tương tự cho các types có required fields không được pipe format truyền vào:
```python
"ErrorDomain": {
    "domain": lambda node: node.get("domain", ""),
    "fix_guide": lambda node: (
        node.get("fix_guide") or
        node.get("description", {}).get("info", "")
        if isinstance(node.get("description"), dict)
        else node.get("description", "")
    ),
},
```

**Tests:**
```python
# test_concept_pipe_format_fills_definition
# test_concept_named_param_definition_preserved
# test_errordomain_pipe_format_fills_fix_guide
```

**Commit:**
```
Wave 17A05 Task 4: TYPE_DEFAULTS fix — Concept definition, ErrorDomain fix_guide

- Concept: definition auto-filled from description
- ErrorDomain: fix_guide auto-filled from description
- Explicit named params override defaults
```

---

## TASK 5 — Viewer v2: Panel layout redesign

**Goal:** Update viewer panel để hiển thị đúng schema v2.

**File:** `gobp/viewer/static/` hoặc `gobp/viewer/templates/`

**Trước (v1 panel):**
```
ENGINE
  trustgate.ops.05993728
  TrustGate

  STATUS: ACTIVE
  PRIORITY: medium
  DESCRIPTION: Trust scoring engine...
  TOPIC:
  GROUP: Dev > Infrastructure > Engine
  ▶ Show raw fields (1)
  - OUTGOING
    DISCOVERED_IN: session...
```

**Sau (v2 panel) — standard node:**
```
◈ Dev > Infrastructure > Engine     ← BREADCRUMB (clickable)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENGINE
TrustGate

lifecycle: specified    read_order: foundational
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESCRIPTION
Trust scoring engine. Devalues low-trust actions,
NEVER blocks access. GPS spoofing → silent private_draft.

[CODE]                              ← chỉ hiện nếu có code
```dart
class TrustGate extends Engine { }
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RELATIONSHIPS
  → discovered_in: Session "GoBP v2 test"
    reason: (trống)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[▶ Debug: raw fields]               ← collapsed mặc định
```

**ErrorCase layout đặc biệt:**
```
◈ Error > ErrorCase
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ERROR CASE
GPS_E_001 · GPS Signal Lost
severity: error

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRIGGER
GPS accuracy > 50m or signal null
Thường xảy ra: trong nhà, tầng hầm

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM RESPONSE
Block Mi Hốt action, retry 3 times...

USER MESSAGE
"Không tìm thấy tín hiệu GPS..."

DEV NOTE
Check GPS_ACCURACY_THRESHOLD config...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT
  domains: [gps]
  features: [mi_hot]
  flows: [mi_hot_flow]
  engines: [trust_gate]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX HISTORY
  [2026-04-18] cursor / wave 17A05  type: dev_code
  Symptom: GPS_E_001 triggered khi accuracy = 45m
  Root cause: hardcoded threshold 40m
  ▶ Show code diff
```

**Implementation requirements:**

```python
# Panel rendering logic
def render_panel(node: dict) -> str:
    node_type = node.get('type', '')

    if node_type == 'ErrorCase':
        return render_errorcase_panel(node)
    elif node_type == 'Invariant':
        return render_invariant_panel(node)
    elif node_type in ('Decision', 'LessonRule', 'LessonSkill',
                       'LessonDev', 'LessonCTO', 'LessonQA'):
        return render_knowledge_panel(node)
    else:
        return render_standard_panel(node)
```

**Key changes:**
```
1. Breadcrumb: group path → clickable sections
2. lifecycle + read_order thay STATUS + PRIORITY
3. description.info + description.code riêng
4. RELATIONSHIPS thay OUTGOING/INCOMING
   → Hiển thị reason field
5. Raw fields: collapsed mặc định, toggle "Debug"
6. ErrorCase: dedicated layout với fix history
7. Invariant: hiển thị rule + scope + enforcement
```

**Commit:**
```
Wave 17A05 Task 5: Viewer panel layout v2

- Breadcrumb: group path clickable
- lifecycle/read_order replaces STATUS/PRIORITY
- description.info + code sections
- RELATIONSHIPS with reason (not OUTGOING/INCOMING)
- Raw fields collapsed by default
- ErrorCase: dedicated layout
```

---

## TASK 6 — Viewer v2: Sidebar + filter updates

**Goal:** Sidebar filter reflects schema v2 taxonomy.

**Current sidebar:**
```
NODE TYPE
  ● AuthFlow 1
  ● BusinessRule 1
  ● Concept 1
  ...

STATUS
  ■ ACTIVE 8
  ■ COMPLETED 1
  ■ LOCKED 1
```

**New sidebar v2:**
```
GROUP
  ▼ Document (2)
      Concept · Decision · Spec · Idea
      Lesson: Rule · Skill · Dev · CTO · QA
  ▼ Dev (4)
    ▼ Domain (1): Entity · ValueObject
    ▼ Infrastructure (2)
      ▼ Security (1): AuthFlow · Token
      Engine · Repository
    ▼ Application (1): Flow · Feature
    ▼ Frontend: Screen · Component
    ▼ Code: Interface · Class · Function
  ▼ Constraint (1): Invariant · BusinessRule
  ▼ Error (0): ErrorDomain · ErrorCase
  ▼ Test (0): TestSuite · TestKind · TestCase
  ▼ Meta (1): Session · Wave · Task

LIFECYCLE
  ■ draft 7
  ■ specified 1
  ■ deprecated 0

READ ORDER
  ■ foundational 3
  ■ important 2
  ■ reference 3
  ■ background 1
```

**Implementation:**
```javascript
// Build group tree from nodes
function buildGroupTree(nodes) {
    const tree = {};
    nodes.forEach(node => {
        const group = node.group || 'Ungrouped';
        const parts = group.split(' > ');
        let current = tree;
        parts.forEach(part => {
            if (!current[part]) current[part] = { _count: 0, _children: {} };
            current[part]._count++;
            current = current[part]._children;
        });
    });
    return tree;
}

// Render clickable group tree
function renderGroupTree(tree, depth = 0) {
    // Collapsible tree with counts
    // Click → filter by group prefix
}
```

**Commit:**
```
Wave 17A05 Task 6: Viewer sidebar v2

- GROUP tree (collapsible) replaces NODE TYPE flat list
- LIFECYCLE replaces STATUS filter
- READ ORDER replaces PRIORITY filter
- Group click → filter by group prefix
```

---

## TASK 7 — Tests + CHANGELOG + Self-eval + Full Suite

**Tests:**
```python
# tests/test_wave17a05.py — 15 tests

# Bug fixes (9):
# test_batch_named_params_double_quote
# test_batch_named_params_single_quote
# test_batch_named_params_with_plain_desc
# test_batch_no_split_on_newline_in_quoted
# test_create_auto_id_from_name_group
# test_create_id_preserved_if_set
# test_concept_definition_from_pipe
# test_errordomain_fix_guide_from_pipe
# test_batch_decision_what_why_parsed

# Viewer (6):
# test_render_standard_panel_has_breadcrumb
# test_render_standard_panel_no_status_priority
# test_render_standard_panel_lifecycle_read_order
# test_render_errorcase_panel_has_code_section
# test_render_errorcase_panel_has_fix_history
# test_render_invariant_panel_has_rule
```

**Self-evaluation (Cursor):**
```
Sau Tasks 1-6, tự hỏi:
□ Code quality: function nào > 50 lines?
□ Duplicate logic nào?
□ Tests cover đủ edge cases chưa?
□ Viewer code có clean không?
□ Bug fixes có regression risk không?
→ Update .cursorrules v9 với lessons thực tế
→ Báo cáo CEO
```

**CHANGELOG:**
```markdown
## [Wave 17A05] — Bug Fixes + Viewer v2 — 2026-04-19

### Fixed
- batch parser: named params key="value" now parsed correctly
- batch parser: \n in quoted strings no longer splits into new ops
- create: auto-generates id from name + group (no manual id required)
- TYPE_DEFAULTS: Concept.definition, ErrorDomain.fix_guide auto-fill

### Changed
- Viewer panel v2:
  - GROUP breadcrumb (clickable) replaces TOPIC
  - lifecycle + read_order replaces STATUS + PRIORITY
  - description.info + code sections
  - RELATIONSHIPS with reason (not OUTGOING/INCOMING)
  - Raw fields collapsed by default (Debug toggle)
  - ErrorCase: dedicated layout with fix history
  - Invariant: rule + scope + enforcement displayed
- Viewer sidebar v2:
  - GROUP tree (collapsible) replaces NODE TYPE flat list
  - LIFECYCLE + READ ORDER filters

### Tests: 705+ (690 + 15 new)
```

**Full suite:**
```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --override-ini="addopts=" -q --tb=no
# Expected: 705+ tests
```

**GoBP MCP:**
```
gobp(query="session:start actor='cursor' goal='Wave 17A05 complete'")
gobp(query="session:end outcome='4 bugs fixed, viewer v2 shipped. 705+ tests.'")
```

**Commit:**
```
Wave 17A05 Task 7: tests + CHANGELOG + self-eval + full suite — 705+ tests
```

---

# CEO DISPATCH

## Cursor
```
Read waves/wave_17a05_brief.md.
Read gobp/mcp/batch_parser.py TRƯỚC Task 1.
Read gobp/mcp/tools/write.py TRƯỚC Task 3.
Read gobp/viewer/ TRƯỚC Task 5.
Read GoBP MCP: gobp(query="find:Decision mode=summary")

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute Tasks 1-7.
R9-B Tasks 1-6, R9-C Task 7.

PRIORITY ORDER:
  Task 1-4: Bug fixes (phải fix trước viewer)
  Task 5-6: Viewer v2 (sau bug fixes)
  Task 7: Tests + self-eval + full suite

ErrorCase viewer layout:
  Phải hiển thị: code, severity, trigger,
  handling, user_message, dev_note, context,
  fix history (append-only)
  Layout khác standard node

STOP nếu viewer structure không rõ → báo CEO.
GoBP MCP sau mỗi task (dec:d004).
```

## Claude CLI
```
Audit Wave 17A05.
Verify bugs fixed:
  1. batch: create: Decision: Name | what="x" why="y" → works
  2. batch: fix_guide="line1\nline2" → không split
  3. create:Invariant → id auto-generated
  4. create: Concept: Name | text → definition filled

Verify viewer v2:
  1. GROUP breadcrumb hiển thị
  2. lifecycle/read_order (không phải STATUS/PRIORITY)
  3. RELATIONSHIPS với reason (không phải OUTGOING)
  4. Raw fields collapsed mặc định
  5. ErrorCase layout đặc biệt

705+ tests passing.
GoBP MCP session capture. Không cần Lesson node.
```

## Push
```powershell
cd D:\GoBP
git add waves/wave_17a05_brief.md
git commit -m "Add Wave 17A05 Brief — bug fixes + viewer v2"
git push origin main
```

---

*Wave 17A05 Brief v1.0 — 2026-04-19*
*References: dec:d004, dec:d006*
*Part of: Wave 17A Series*
◈
