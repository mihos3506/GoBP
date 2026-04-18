# WAVE 17A01 BRIEF — SCHEMA CORE REDESIGN

**Wave:** 17A01
**Title:** Node types, group field, description standard, fields redesign
**Author:** CTO Chat
**Date:** 2026-04-19
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 6 tasks
**Estimated effort:** 4-6 hours

---

## REFERENCED GOBP NODES

| Node ID | Topic |
|---|---|
| `dec:d004` | GoBP update obligation |
| `dec:d006` | Brief reference nodes |
| `dec:d011` | Graph hygiene — update over create |

**NEW NODES sẽ tạo:**
- Wave: Wave 17A01

**SCHEMA REDESIGN DOC:** `docs/GOBP_SCHEMA_REDESIGN_v2.1.md`

---

## CONTEXT

GoBP schema v1 được build từ brainstorm — không dựa trên chuẩn phần mềm.
Wave 17A01 là bước đầu của 5-wave schema redesign:

```
17A01: Schema core (wave này)
  → node types, group field, description, lifecycle/read_order
17A02: Edge reason field + display modes
17A03: Validation rules + hooks update
17A04: Docs + agents self-update
17A05: MIHOS clean import với schema mới
```

---

## CURSOR EXECUTION RULES

R1-R12 (.cursorrules v6).

**Testing:**
- Tasks 1-4 (schema YAML + migration): R9-B module tests
- Task 5 (docs): R9-A
- Task 6 (cuối wave): R9-C full suite
  `pytest tests/ --override-ini="addopts=" -q`

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 633 tests (fast suite, slow excluded)
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `docs/GOBP_SCHEMA_REDESIGN_v2.1.md` | Full taxonomy spec |
| 2 | `gobp/schema/core_nodes.yaml` | Current schema |
| 3 | `gobp/schema/core_edges.yaml` | Current edges |
| 4 | `gobp/mcp/tools/write.py` | TYPE_DEFAULTS |
| 5 | GoBP MCP `dec:d004`, `dec:d011` | Decisions |

---

# TASKS

---

## TASK 1 — Thêm `group` field vào schema

**Goal:** Mỗi node type có `group` breadcrumb path.

**File:** `gobp/schema/core_nodes.yaml`

Thêm `group` field vào base node spec:
```yaml
group:
  type: str
  required: false
  description: "Breadcrumb path — VD: Dev > Infrastructure > Security"
  default: ""
```

Thêm group default cho mỗi node type hiện có:
```yaml
Document:   group: "Document > Spec"
Decision:   group: "Document > Decision"
Concept:    group: "Document > Concept"
Idea:       group: "Document > Idea"
Session:    group: "Meta > Session"
Wave:       group: "Meta > Wave"
Task:       group: "Meta > Task"
Lesson:     group: "Document > Lesson"
# ... tất cả types còn lại
```

**Commit:**
```
Wave 17A01 Task 1: add group/breadcrumb field to schema

- group field: breadcrumb path showing full hierarchy
- Default groups set for all existing node types
- VD: AuthFlow → "Dev > Infrastructure > Security > AuthFlow"
```

---

## TASK 2 — Thêm node types mới từ taxonomy v2.1

**Goal:** Add tất cả node types mới vào `core_nodes.yaml`.

**NEW TYPES cần thêm** (theo GOBP_SCHEMA_REDESIGN_v2.1.md):

```
Document group:   Idea (nếu chưa có)
                  Lesson.Rule, Lesson.Skill, Lesson.Dev,
                  Lesson.CTO, Lesson.QA

Dev > Domain:     Entity, ValueObject, DomainEvent, Aggregate

Dev > Application: Flow, Feature, Command, UseCase, DTO

Dev > Infrastructure:
  Engine, Repository (nếu chưa có)
  API: APIContract, APIEndpoint, APIRequest, APIResponse,
       APIMiddleware, Webhook
  Security: AuthFlow, AuthZ, Permission, Policy, Token,
            Encryption, Secret, Audit, ThreatModel, Vulnerability
  Database: Schema, Migration, Index, Query, Seed
  Messaging: EventBus, Queue, Topic, Worker
  Observability: Metric, Log, Trace, Alert
  Cache: CacheStrategy
  Storage: FileStorage, CDN
  Config: EnvConfig, FeatureFlag

Dev > Frontend: Screen, Component, Layout, Theme, Animation, State
Dev > Code: Interface, AbstractClass, Class, Mixin, Enum,
            TypeAlias, Generic, Function, Method, Constructor,
            Extension, Field, Variable, Constant, Parameter, Module

Constraint: Invariant (update), Precondition, Postcondition, BusinessRule

Error: ErrorDomain, ErrorCase

Test: TestSuite, TestKind, TestCase
```

**RULE quan trọng:**
- Trước khi thêm type mới → kiểm tra type đã có chưa
- Nếu đã có → update group field, không tạo duplicate
- Invariant đã có → chỉ update, thêm required fields

**Commit:**
```
Wave 17A01 Task 2: add new node types from taxonomy v2.1

- 60+ new node types added across 6 groups
- Each type has group breadcrumb path
- Existing types updated with group field
```

---

## TASK 3 — Description standard: info + code fields

**Goal:** Description thành 2 phần: info (required) + code (optional).

**File:** `gobp/schema/core_nodes.yaml`

Update base description field:
```yaml
description:
  type: dict
  required: true
  fields:
    info:
      type: str
      required: true
      description: "Full description — no length limit"
    code:
      type: str
      required: false
      default: ""
      description: "Code examples, pseudo-code, SQL — optional"
```

**File:** `gobp/mcp/tools/write.py` — TYPE_DEFAULTS

Update auto-fill để handle description dict:
```python
# Nếu AI pass description as string → auto-wrap:
if isinstance(description, str):
    description = {"info": description, "code": ""}
```

**File:** `gobp/mcp/tools/read.py`

Update `get:` để display description đúng:
```python
# mode=brief: chỉ show description.info
# mode=full: show cả info + code
```

**Tests:**
```python
# test: create node với description string → auto-wrap
# test: create node với description dict → store correctly
# test: get mode=brief → shows info only
```

**Commit:**
```
Wave 17A01 Task 3: description split into info + code fields

- description.info: required, full description
- description.code: optional, code examples
- Auto-wrap string description to {info: str, code: ""}
- get: mode=brief shows info only
```

---

## TASK 4 — Replace status → lifecycle, priority → read_order

**Goal:** Đổi tên fields để có nghĩa rõ ràng hơn.

**File:** `gobp/schema/core_nodes.yaml`

```yaml
# Thay status:
lifecycle:
  type: enum
  values: [draft, specified, implemented, tested, deprecated]
  default: draft

# Thay priority:
read_order:
  type: enum
  values: [foundational, important, reference, background]
  default: reference
  description: "AI reading priority: foundational=read first always"
```

**File:** `gobp/mcp/tools/write.py`

Migration logic:
```python
# Backward compat: nếu AI pass status/priority → map sang mới
STATUS_MAP = {
    "ACTIVE": "specified",
    "STALE": "deprecated",
    "DEPRECATED": "deprecated",
}
PRIORITY_MAP = {
    "critical": "foundational",
    "high": "important",
    "medium": "reference",
    "low": "background",
}
```

**File:** `gobp/mcp/tools/read.py`

Update display — dùng lifecycle + read_order, không dùng status/priority.

**Tests:**
```python
# test: create với status="ACTIVE" → stored as lifecycle="specified"
# test: create với priority="critical" → stored as read_order="foundational"
# test: get node → shows lifecycle + read_order, không shows status/priority
```

**Commit:**
```
Wave 17A01 Task 4: status→lifecycle, priority→read_order

- lifecycle: draft|specified|implemented|tested|deprecated
- read_order: foundational|important|reference|background
- Backward compat: old values auto-mapped to new
```

---

## TASK 5 — Update Invariant: required fields

**Goal:** Invariant phải có rule + scope + enforcement + violation_action.

**File:** `gobp/schema/core_nodes.yaml`

```yaml
Invariant:
  group: "Constraint > Invariant"
  required:
    name: ...
    rule:
      type: str
      description: "Boolean expression — VD: balance >= 0"
    scope:
      type: enum
      values: [class, object, system]
    enforcement:
      type: enum
      values: [hard, soft]
    violation_action:
      type: enum
      values: [reject, devalue, flag, log]
  optional:
    spec_source:
      type: str
      description: "DOC-XX section Y"
    description: ...
```

**File:** `gobp/mcp/hooks.py`

Update before_write hook:
```python
# Invariant without rule → block with suggestion
if node_type == "Invariant" and not params.get("rule"):
    return {
        "ok": False,
        "error": "Invariant requires 'rule' field",
        "suggestion": "rule must be a Boolean expression, e.g.: 'balance >= 0'"
    }
```

**Tests:**
```python
# test: create Invariant without rule → rejected
# test: create Invariant with rule → accepted
# test: create Invariant with "KHÔNG được X" as rule → accepted
#       (validation của meaning là CEO responsibility, không phải GoBP)
```

**Commit:**
```
Wave 17A01 Task 5: Invariant required fields + hook validation

- rule, scope, enforcement, violation_action = required
- before_write hook blocks Invariant without rule
- Suggestion: "rule must be Boolean expression"
```

---

## TASK 6 — ErrorCase schema + fix history + full suite

**Goal:** ErrorCase có đủ fields theo spec v2.1.

**File:** `gobp/schema/core_nodes.yaml`

```yaml
ErrorCase:
  group: "Error > ErrorCase"
  required:
    name: ...
    code:
      type: str
      description: "Error code — VD: AUTH_001, GPS_003"
    trigger:
      type: str
      description: "Conditions that cause this error"
    severity:
      type: enum
      values: [fatal, error, warning, info]
    handling:
      type: str
      description: "How system responds"
    fix:
      type: str
      description: "How to fix this error"
  optional:
    domain:        type: node_ref  # → ErrorDomain
    user_message:  type: str
    dev_note:      type: str
    recovery:      type: str
    affects:       type: list[node_ref]
    related_errors: type: list[node_ref]
    fixes:         # append-only history
      type: list[dict]
      fields:
        type:             enum [runtime, dev_code]
        fixed_at:         timestamp
        fixed_by:         str
        symptom:          str
        root_cause:       str
        fix_description:  str
        code:             str  # code change
        files_changed:    list[dict]
        test_result:      str  # dev_code only
        verified_by:      str

ErrorDomain:
  group: "Error > ErrorDomain"
  required:
    name: ...
    domain:
      type: enum
      values: [auth, gps, ember, trust, privacy, network, storage, sync]
    fix_guide:
      type: str
      description: "General debug guide for this error domain"
  optional:
    description: ...
    affects: type: list[node_ref]
```

**CHANGELOG entry:**
```markdown
## [Wave 17A01] — Schema Core Redesign — 2026-04-19

### Changed
- group field: breadcrumb path for all node types
- description: split into info (required) + code (optional)
- status → lifecycle (draft|specified|implemented|tested|deprecated)
- priority → read_order (foundational|important|reference|background)
- Invariant: rule+scope+enforcement+violation_action = required

### Added
- 60+ new node types across 6 groups (Document/Dev/Constraint/Error/Test/Meta)
- ErrorCase: fix history (append-only, type: runtime|dev_code)
- ErrorDomain: fix_guide field
- before_write hook: blocks Invariant without rule

### Total: 640+ tests
```

**Full suite:**
```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --override-ini="addopts=" -q --tb=no
# Expected: 633+ tests
```

**GoBP MCP:**
```
gobp(query="session:start actor='cursor' goal='Wave 17A01 end'")
# Update Wave 17A01 node
gobp(query="session:end ...")
```

**Commit:**
```
Wave 17A01 Task 6: ErrorCase schema + fix history + CHANGELOG + full suite

- ErrorCase: all required fields per spec v2.1
- fixes[]: append-only fix history (runtime + dev_code types)
- ErrorDomain: fix_guide field
- CHANGELOG: Wave 17A01 entry
- Full suite: 633+ tests passing
```

---

# CEO DISPATCH

## Cursor
```
Read docs/GOBP_SCHEMA_REDESIGN_v2.1.md FIRST — đây là spec chính.
Read .cursorrules v6 + waves/wave_17a01_brief.md.
Read GoBP MCP: gobp(query="find:Decision mode=summary")

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute Tasks 1-6 sequentially.
R9-B for code tasks, R9-A for docs, R9-C at Task 6.

KEY RULES:
- Trước khi thêm type mới → check existing types
- description string → auto-wrap to {info, code}
- Invariant without rule → blocked by hook
- ErrorCase fixes → append-only list
- group field = breadcrumb path (REQUIRED)

GoBP MCP update sau mỗi task (dec:d004).
Lesson nodes: suggest: trước khi tạo (dec:d011).
```

## Claude CLI
```
Audit Wave 17A01 sau khi Cursor complete.
Verify:
  - group field present trên node types
  - description.info required
  - lifecycle + read_order thay status/priority
  - Invariant rule required + hook blocks
  - ErrorCase fix history structure

Full suite: 633+ tests.
GoBP MCP session capture (dec:d004). Không cần Lesson node.
```

## Push
```powershell
cd D:\GoBP
git add waves/wave_17a01_brief.md docs/GOBP_SCHEMA_REDESIGN_v2.1.md
git commit -m "Add Wave 17A01 Brief + Schema Redesign v2.1 doc"
git push origin main
```

---

*Wave 17A01 Brief v1.0 — 2026-04-19*
*References: dec:d004, dec:d006, dec:d011*
*Schema doc: docs/GOBP_SCHEMA_REDESIGN_v2.1.md*
◈
