# WAVE 17A06 BRIEF — SELF-UPGRADE LOOP + INCIDENT HISTORY

**Wave:** 17A06  
**Title:** LessonSkill v2, incident_history fields, Reflection node, self-upgrade loop  
**Author:** CTO Chat  
**Date:** 2026-04-19  
**For:** Cursor (sequential) + Claude CLI (audit)  
**Status:** READY FOR EXECUTION  
**Task count:** 6 tasks  
**Estimated effort:** 4-5 hours  

---

## REFERENCED GOBP NODES

| Node ID | Topic |
|---|---|
| `dec:d004` | GoBP update obligation |
| `dec:d006` | Brief reference nodes |
| `dec:d011` | Graph hygiene: update over create |

---

## CONTEXT — Tại sao Wave này quan trọng

**GoBP hiện tại (sau 17A05):**
```
✅ Memory layer: AI ghi nhớ qua sessions
✅ Schema v2: 93 types, group breadcrumb
✅ Query engine: find/get/explore hoạt động tốt
✅ Viewer v2: breadcrumb, relationships, ErrorCase layout
❌ Learning layer: Lessons tích lũy nhưng không có vòng lặp tự nâng cấp
❌ incident_history: Production incidents không trace về schema node
```

**Wave 17A06 đóng vòng lặp:**
```
Build → Learn → Improve → Build tốt hơn
         ↑          ↓
    Reflection ← LessonSkill v2
```

Không có Wave này: GoBP là memory layer.  
Sau Wave này: GoBP là **learning layer**.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 705 tests (baseline từ 17A05)
```

---

## CURSOR EXECUTION RULES

R1-R12 (.cursorrules hiện hành).

**Testing:**
- Tasks 1-4: R9-B (module tests only)
- Task 5: R9-B (integration)
- Task 6: R9-C (full suite)

**QUAN TRỌNG:**
- Không đụng GraphIndex hay query engine
- 705 baseline tests PHẢI vẫn pass
- Mỗi task: GoBP MCP update (dec:d004)

---

# TASKS

---

## TASK 1 — Upgrade LessonSkill schema trong `core_nodes.yaml`

**File:** `gobp/schema/core_nodes.yaml`

**Vấn đề hiện tại:**
```yaml
# Hiện tại (không đủ để enforce self-upgrade loop)
LessonSkill:
  group: "Document > Lesson > Skill"
  read_order: important
  # Chỉ có description.info/code — không có structure
```

**Target schema:**
```yaml
LessonSkill:
  group: "Document > Lesson > Skill"
  read_order: important
  required:
    sub_type:
      type: enum
      values: [ai_self, work_quality, product]
      description: >
        ai_self: cách AI tự hành xử và tự nâng cấp
        work_quality: cách làm việc tốt hơn (brief, audit, process)
        product: cách build product tốt hơn (schema, arch, UX)
    procedure:
      type: str
      description: >
        Step-by-step instructions. PHẢI có 3 phần:
        1. HOW: làm gì, theo thứ tự nào
        2. EVALUATE: kiểm tra kết quả như thế nào
        3. EVOLVE_TRIGGER: khi nào cần nâng cấp skill này
  optional:
    supersedes:
      type: str
      description: ID của LessonSkill cũ mà skill này thay thế
    versions:
      type: list[str]
      description: History các version IDs, oldest first
    applies_to:
      type: list[str]
      description: Roles áp dụng — [cursor, claude_cli, cto_chat, all]
    evolve_count:
      type: int
      default: 0
      description: Số lần skill đã được nâng cấp
```

**Validator update** (`gobp/core/validator_v2.py`):

Thêm validation rule cho LessonSkill:
```python
# Trong _validate_type_specific() hoặc validate_node()
if node_type == 'LessonSkill':
    procedure = node.get('procedure', '')
    if procedure:
        # Kiểm tra 3 phần bắt buộc
        required_sections = ['HOW', 'EVALUATE', 'EVOLVE_TRIGGER']
        missing = [s for s in required_sections
                   if s.upper() not in procedure.upper()]
        if missing:
            errors.append(
                f"LessonSkill.procedure missing sections: {missing}. "
                f"Required: HOW + EVALUATE + EVOLVE_TRIGGER"
            )
    # sub_type phải là enum hợp lệ
    sub_type = node.get('sub_type', '')
    valid_subtypes = ['ai_self', 'work_quality', 'product']
    if sub_type and sub_type not in valid_subtypes:
        errors.append(
            f"LessonSkill.sub_type '{sub_type}' invalid. "
            f"Must be one of: {valid_subtypes}"
        )
```

**Tests (6):**
```python
# tests/test_wave17a06.py

def test_lesson_skill_valid_full():
    """LessonSkill với đủ fields không có lỗi"""
    node = {
        "id": "doc.lesson.skill.test.a1b2c3d4",
        "type": "LessonSkill",
        "name": "Test Skill",
        "group": "Document > Lesson > Skill",
        "description": {"info": "Test skill", "code": ""},
        "sub_type": "ai_self",
        "procedure": "HOW: step1\nEVALUATE: check result\nEVOLVE_TRIGGER: when fails"
    }
    errors = schema.validate_node(node)
    assert errors == []

def test_lesson_skill_missing_sub_type():
    node = {
        "id": "doc.lesson.skill.test.a1b2c3d4",
        "type": "LessonSkill",
        "name": "Test",
        "group": "Document > Lesson > Skill",
        "description": {"info": "Test"},
    }
    errors = schema.validate_node(node)
    assert any("sub_type" in e for e in errors)

def test_lesson_skill_invalid_sub_type():
    node = {**valid_skill_node, "sub_type": "invalid_type"}
    errors = schema.validate_node(node)
    assert any("sub_type" in e for e in errors)

def test_lesson_skill_procedure_missing_evaluate():
    node = {**valid_skill_node,
            "procedure": "HOW: do this\nEVOLVE_TRIGGER: when fails"}
    errors = schema.validate_node(node)
    assert any("EVALUATE" in e for e in errors)

def test_lesson_skill_procedure_missing_evolve_trigger():
    node = {**valid_skill_node,
            "procedure": "HOW: do this\nEVALUATE: check"}
    errors = schema.validate_node(node)
    assert any("EVOLVE_TRIGGER" in e for e in errors)

def test_lesson_skill_supersedes_optional():
    node = {**valid_skill_node, "supersedes": "doc.lesson.skill.old.a1b2c3d4"}
    errors = schema.validate_node(node)
    assert errors == []
```

**Commit:**
```
Wave 17A06 Task 1: LessonSkill schema v2

- sub_type: ai_self | work_quality | product (required)
- procedure: HOW + EVALUATE + EVOLVE_TRIGGER (required, 3-part)
- supersedes: skill version chain (optional)
- versions[]: upgrade history (optional)
- Validator enforces 3-part procedure structure
```

---

## TASK 2 — Thêm `incident_history` field cho 6 infrastructure node types

**Files:** `gobp/schema/core_nodes.yaml`

**6 types cần update:**

```
Vulnerability, Migration, AuthFlow,
Engine, APIEndpoint, Encryption
```

**incident_history schema** (shared optional field):

```yaml
# Thêm vào optional fields của mỗi type trên
incident_history:
  type: list[dict]
  default: []
  description: >
    Append-only history các incidents liên quan node này.
    NEVER modify existing entries — chỉ append.
  item_schema:
    date:       {type: str, required: true}   # ISO date
    type:       {type: enum, required: true,
                 values: [runtime, dev_code, security, migration]}
    summary:    {type: str, required: true}   # 1-2 câu
    root_cause: {type: str, required: false}
    fix_ref:    {type: str, required: false}  # Wave ID hoặc commit hash
    reporter:   {type: str, required: false}  # actor: cursor|cto_chat|claude_cli

# Fields đặc thù thêm vào từng type:

Vulnerability:
  optional thêm:
    cve_id:     {type: str}        # CVE-YYYY-NNNNN format
    cvss_score: {type: float}      # 0.0 - 10.0
    patched_in: {type: str}        # Wave ID hoặc version

Migration:
  optional thêm:
    rollback_plan: {type: str}     # Step-by-step rollback
    tested_on:     {type: str}     # staging|prod
    duration_min:  {type: int}     # Thời gian migration (phút)
```

**Không cần validator logic riêng** — field optional, item schema là documentation.  
Append-only enforcement là convention, không phải code constraint (same as ErrorCase.fix_history).

**Tests (5):**
```python
def test_engine_accepts_incident_history():
    node = {
        **valid_engine_node,
        "incident_history": [
            {
                "date": "2026-04-18",
                "type": "runtime",
                "summary": "TrustGate timeout spike 3s under load",
                "root_cause": "N+1 query in score calculation",
                "fix_ref": "17A05",
                "reporter": "cursor"
            }
        ]
    }
    errors = schema.validate_node(node)
    assert errors == []

def test_vulnerability_accepts_cve_id():
    node = {**valid_vulnerability_node, "cve_id": "CVE-2026-12345", "cvss_score": 7.5}
    errors = schema.validate_node(node)
    assert errors == []

def test_migration_accepts_rollback_plan():
    node = {**valid_migration_node, "rollback_plan": "Step 1: ...\nStep 2: ..."}
    errors = schema.validate_node(node)
    assert errors == []

def test_authflow_accepts_incident_history():
    node = {**valid_authflow_node, "incident_history": []}
    errors = schema.validate_node(node)
    assert errors == []

def test_apiendpoint_accepts_incident_history():
    node = {**valid_apiendpoint_node,
            "incident_history": [{"date": "2026-04-19", "type": "dev_code",
                                   "summary": "Wrong status code 200 → 201"}]}
    errors = schema.validate_node(node)
    assert errors == []
```

**Commit:**
```
Wave 17A06 Task 2: incident_history field cho 6 infra node types

- Vulnerability: incident_history + cve_id + cvss_score + patched_in
- Migration: incident_history + rollback_plan + tested_on + duration_min
- AuthFlow, Engine, APIEndpoint, Encryption: incident_history
- Append-only convention (same as ErrorCase.fix_history)
```

---

## TASK 3 — Thêm `Reflection` node type vào schema

**File:** `gobp/schema/core_nodes.yaml`

**Vấn đề cần giải quyết:**  
Hiện tại không có mechanism để trigger review sau wave.  
Session kết thúc → lessons tích lũy → không có link "wave này sinh ra lessons nào".

**Reflection node** — thuộc nhóm Meta:

```yaml
Reflection:
  group: "Meta > Reflection"
  read_order: important
  description: >
    Trigger vòng lặp tự nâng cấp sau mỗi wave/milestone.
    Link từ Session → Reflection → LessonSkill updates.
    Không phải journal — là action item cho next cycle.
  required:
    trigger:
      type: enum
      values: [wave_complete, milestone, ceo_feedback, quality_drop]
      description: Điều gì kích hoạt Reflection này
    wave_ref:
      type: str
      description: Wave ID hoặc milestone name (e.g. "17A05", "Phase 1 MVP")
    findings:
      type: list[str]
      description: >
        Danh sách findings từ wave.
        Mỗi item: "[KEEP|UPGRADE|CREATE] <skill_name> — <reason>"
        Format bắt buộc để parse được trong evolve loop.
  optional:
    skills_upgraded:
      type: list[str]
      description: IDs của LessonSkill nodes đã được upgrade trong cycle này
    skills_created:
      type: list[str]
      description: IDs của LessonSkill nodes mới tạo trong cycle này
    next_focus:
      type: str
      description: Bottleneck lớn nhất cần giải quyết ở wave tiếp theo
    actor:
      type: str
      description: AI role thực hiện Reflection (cto_chat|cursor|claude_cli)
```

**Edge pattern** cho Reflection:
```
Session --triggers--> Reflection
Reflection --references--> LessonSkill (upgraded)
Reflection --produces--> LessonSkill (created)
Wave --triggers--> Reflection
```

**Tests (5):**
```python
def test_reflection_valid_full():
    node = {
        "id": "meta.reflection.17a05.a1b2c3d4",
        "type": "Reflection",
        "name": "Wave 17A05 Reflection",
        "group": "Meta > Reflection",
        "description": {"info": "Post-wave evolve cycle", "code": ""},
        "trigger": "wave_complete",
        "wave_ref": "17A05",
        "findings": [
            "UPGRADE batch_parser_skill — named params parsing now proven",
            "CREATE viewer_v2_skill — new pattern for schema-aware panels",
            "KEEP session_protocol — H1-H6 still effective"
        ]
    }
    errors = schema.validate_node(node)
    assert errors == []

def test_reflection_missing_trigger():
    node = {**valid_reflection_node}
    del node['trigger']
    errors = schema.validate_node(node)
    assert any("trigger" in e for e in errors)

def test_reflection_invalid_trigger():
    node = {**valid_reflection_node, "trigger": "random"}
    errors = schema.validate_node(node)
    assert any("trigger" in e for e in errors)

def test_reflection_missing_findings():
    node = {**valid_reflection_node}
    del node['findings']
    errors = schema.validate_node(node)
    assert any("findings" in e for e in errors)

def test_reflection_with_skills_upgraded():
    node = {**valid_reflection_node,
            "skills_upgraded": ["doc.lesson.skill.batch_parser.a1b2"],
            "next_focus": "MIHOS import pipeline"}
    errors = schema.validate_node(node)
    assert errors == []
```

**Commit:**
```
Wave 17A06 Task 3: Reflection node type

- group: "Meta > Reflection"
- trigger: wave_complete | milestone | ceo_feedback | quality_drop
- findings: [KEEP|UPGRADE|CREATE] format
- skills_upgraded + skills_created links
- Closes the Build → Learn → Improve loop
```

---

## TASK 4 — MCP: `evolve:` action

**File:** `gobp/mcp/dispatcher.py` + `gobp/mcp/tools/read.py` (hoặc new `evolve.py`)

**Goal:** Một MCP action giúp AI agent chạy evolve cycle mà không cần biết node IDs.

**Protocol:**
```
gobp(query="evolve: wave='17A05'")
→ Returns checklist để CTO Chat điền vào, tạo Reflection node

gobp(query="evolve: wave='17A05' status='complete'")
→ Lấy Reflection node của wave đó (nếu đã tạo)
```

**Implementation `evolve_action()`:**

```python
def evolve_action(index, project_root, args: dict) -> dict:
    """
    evolve: wave='17A05'
    → Trả về checklist Reflection template + existing LessonSkills
    
    evolve: wave='17A05' status='complete'
    → Tìm Reflection node cho wave này (nếu có)
    """
    wave_ref = args.get('wave', '')
    status = args.get('status', '')

    if status == 'complete':
        # Tìm Reflection node đã tạo cho wave này
        matches = index.find_by_field('wave_ref', wave_ref, node_type='Reflection')
        if matches:
            return {"ok": True, "reflection": matches[0]}
        return {"ok": False, "message": f"No Reflection found for wave '{wave_ref}'"}

    # Default: trả về checklist + existing skills để CTO Chat evaluate
    existing_skills = index.find_by_type('LessonSkill')
    skill_summary = [
        {
            "id": s.get('id'),
            "name": s.get('name'),
            "sub_type": s.get('sub_type', ''),
            "evolve_count": s.get('evolve_count', 0)
        }
        for s in existing_skills[:20]  # Top 20, không dump toàn bộ
    ]

    checklist = {
        "wave_ref": wave_ref,
        "instruction": (
            "Tạo Reflection node với:\n"
            "  trigger: wave_complete\n"
            "  wave_ref: '{wave}'\n"
            "  findings: list of [KEEP|UPGRADE|CREATE] <skill_name> — <reason>\n"
            "Sau đó dùng batch: để upgrade/create LessonSkill nodes."
        ).format(wave=wave_ref),
        "existing_skills": skill_summary,
        "template": {
            "type": "Reflection",
            "group": "Meta > Reflection",
            "trigger": "wave_complete",
            "wave_ref": wave_ref,
            "findings": [],
            "next_focus": ""
        }
    }
    return {"ok": True, "checklist": checklist}
```

**Dispatcher registration** (`dispatcher.py`):
```python
# Thêm vào action map
'evolve': handle_evolve,  # evolve: wave='...' [status='complete']
```

**Tests (4):**
```python
def test_evolve_returns_checklist(mock_index):
    result = evolve_action(mock_index, project_root, {"wave": "17A05"})
    assert result["ok"] is True
    assert "checklist" in result
    assert result["checklist"]["wave_ref"] == "17A05"
    assert "existing_skills" in result["checklist"]

def test_evolve_complete_found(mock_index_with_reflection):
    result = evolve_action(mock_index_with_reflection, project_root,
                           {"wave": "17A05", "status": "complete"})
    assert result["ok"] is True
    assert "reflection" in result

def test_evolve_complete_not_found(mock_index):
    result = evolve_action(mock_index, project_root,
                           {"wave": "99Z99", "status": "complete"})
    assert result["ok"] is False
    assert "No Reflection" in result["message"]

def test_evolve_skill_summary_max_20(mock_index_many_skills):
    result = evolve_action(mock_index_many_skills, project_root, {"wave": "17A06"})
    skills = result["checklist"]["existing_skills"]
    assert len(skills) <= 20
```

**Commit:**
```
Wave 17A06 Task 4: evolve: MCP action

- gobp(query="evolve: wave='17A05'") → checklist + existing skills
- gobp(query="evolve: wave='17A05' status='complete'") → Reflection lookup
- Giúp CTO Chat chạy evolve cycle không cần nhớ node IDs
```

---

## TASK 5 — TYPE_DEFAULTS: Reflection + LessonSkill auto-fill

**File:** `gobp/mcp/tools/write.py`

Thêm vào `TYPE_DEFAULTS` (hoặc `_apply_v2_defaults()`):

```python
TYPE_DEFAULTS = {
    # ... existing ...
    
    'LessonSkill': {
        'evolve_count': 0,
        'applies_to': ['all'],
        'versions': [],
    },
    
    'Reflection': {
        'skills_upgraded': [],
        'skills_created': [],
        'actor': 'cto_chat',  # default actor
    },
}
```

Thêm `supersedes` edge auto-creation khi LessonSkill có `supersedes` field:

```python
def _handle_lesson_skill_supersedes(index, project_root, node: dict,
                                     session_id: str) -> list[dict]:
    """
    Nếu LessonSkill mới có supersedes='old_skill_id':
    1. Auto-create edge: new --supersedes--> old
    2. Update old skill: lifecycle = 'deprecated'
    3. Append new skill ID vào old.versions[]
    """
    supersedes_id = node.get('supersedes', '')
    if not supersedes_id:
        return []

    edges = [{
        'from': node['id'],
        'to': supersedes_id,
        'type': 'supersedes',
        'reason': f"Upgraded by wave {node.get('session_id', 'unknown')}"
    }]

    # Update old node lifecycle
    old_node = index.get_node(supersedes_id)
    if old_node:
        old_node['lifecycle'] = 'deprecated'
        write_node(project_root, old_node)

    return edges
```

**Integration:** Gọi `_handle_lesson_skill_supersedes()` trong `node_upsert()` sau khi node được write thành công.

**Tests (3):**
```python
def test_lesson_skill_defaults_applied(mock_index, tmp_path):
    node = {
        "type": "LessonSkill", "name": "Test",
        "group": "Document > Lesson > Skill",
        "description": {"info": "test"},
        "sub_type": "ai_self",
        "procedure": "HOW:\nEVALUATE:\nEVOLVE_TRIGGER:"
    }
    result_id = node_upsert(mock_index, tmp_path, node)
    saved = read_node(tmp_path, result_id)
    assert saved.get('evolve_count') == 0
    assert saved.get('applies_to') == ['all']

def test_lesson_skill_supersedes_creates_edge(mock_index, tmp_path):
    # Setup: old skill exists
    old_id = "doc.lesson.skill.old.a1b2c3d4"
    write_node(tmp_path, {**valid_skill_node, "id": old_id})
    # Create new skill that supersedes old
    new_node = {**valid_skill_node, "id": "doc.lesson.skill.new.a1b2c3d4",
                "supersedes": old_id}
    node_upsert(mock_index, tmp_path, new_node)
    # Edge should exist
    edges = load_edges(tmp_path)
    supersedes_edges = [e for e in edges if e.get('type') == 'supersedes']
    assert len(supersedes_edges) == 1

def test_reflection_defaults_applied(mock_index, tmp_path):
    node = {
        "type": "Reflection", "name": "17A05 Reflection",
        "group": "Meta > Reflection",
        "description": {"info": "post-wave"},
        "trigger": "wave_complete", "wave_ref": "17A05",
        "findings": ["KEEP test_skill — still effective"]
    }
    result_id = node_upsert(mock_index, tmp_path, node)
    saved = read_node(tmp_path, result_id)
    assert saved.get('actor') == 'cto_chat'
    assert saved.get('skills_upgraded') == []
```

**Commit:**
```
Wave 17A06 Task 5: TYPE_DEFAULTS + supersedes auto-edge

- LessonSkill defaults: evolve_count=0, applies_to=['all'], versions=[]
- Reflection defaults: actor='cto_chat', skills_upgraded/created=[]
- LessonSkill.supersedes: auto-create supersedes edge + deprecate old
```

---

## TASK 6 — Tests + CHANGELOG + Self-eval + Full Suite

**Tests:**
```python
# tests/test_wave17a06.py — 23 tests total
# Task 1: 6 tests (LessonSkill schema)
# Task 2: 5 tests (incident_history)
# Task 3: 5 tests (Reflection node)
# Task 4: 4 tests (evolve: action)
# Task 5: 3 tests (defaults + supersedes)
```

**Self-evaluation (Cursor):**
```
Sau Tasks 1-5, tự hỏi:
□ LessonSkill procedure validator: bắt đúng missing sections chưa?
□ evolve: action có trả về đủ context để CTO Chat tạo Reflection không?
□ supersedes auto-edge có idempotent không? (gọi 2 lần có tạo duplicate edge không?)
□ incident_history: append-only có được document rõ không?
□ Reflection.findings format "[KEEP|UPGRADE|CREATE]" có được validate không?
   → Nếu không: đây là improvement cho 17A07
→ Update .cursorrules v10 với lessons thực tế
→ Báo cáo CEO
```

**CHANGELOG:**
```markdown
## [Wave 17A06] — Self-Upgrade Loop + Incident History — 2026-04-19

### Changed — LessonSkill schema v2
- sub_type: ai_self | work_quality | product (required)
- procedure: HOW + EVALUATE + EVOLVE_TRIGGER (3-part, required)
- supersedes: version chain field (optional)
- versions[]: upgrade history (optional)
- Validator enforces 3-part procedure structure

### Added — incident_history on 6 infra node types
- Vulnerability: incident_history + cve_id + cvss_score + patched_in
- Migration: incident_history + rollback_plan + tested_on + duration_min
- AuthFlow, Engine, APIEndpoint, Encryption: incident_history (append-only)

### Added — Reflection node type
- group: "Meta > Reflection"
- trigger: wave_complete | milestone | ceo_feedback | quality_drop
- findings: [KEEP|UPGRADE|CREATE] structured format
- Closes Build → Learn → Improve loop

### Added — evolve: MCP action
- gobp(query="evolve: wave='17A05'") → checklist + skills
- gobp(query="evolve: wave='17A05' status='complete'") → lookup Reflection
- CTO Chat can run evolve cycle without manual node ID lookup

### Changed — TYPE_DEFAULTS
- LessonSkill: evolve_count=0, applies_to=['all']
- Reflection: actor='cto_chat', skills_upgraded/created=[]
- LessonSkill.supersedes: auto-create edge + deprecate old node

### Tests: 728+ (705 + 23 new)
```

**Full suite:**
```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --override-ini="addopts=" -q --tb=no
# Expected: 728+ tests
```

**GoBP MCP:**
```
gobp(query="session:start actor='cursor' goal='Wave 17A06 complete'")
gobp(query="session:end outcome='Self-upgrade loop closed: LessonSkill v2 + Reflection + evolve: action + incident_history. 728+ tests.'")
```

**Commit:**
```
Wave 17A06 Task 6: tests + CHANGELOG + self-eval — 728+ tests
```

---

# CEO DISPATCH

## Cursor
```
Read waves/wave_17a06_brief.md.
Read gobp/schema/core_nodes.yaml TRƯỚC Task 1 — biết cấu trúc LessonSkill hiện tại.
Read gobp/core/validator_v2.py TRƯỚC Task 1 — biết cách thêm type-specific validation.
Read gobp/mcp/dispatcher.py TRƯỚC Task 4 — biết cách register action mới.
Read gobp/mcp/tools/write.py TRƯỚC Task 5 — biết TYPE_DEFAULTS pattern.
Read GoBP MCP: gobp(query="find:Decision mode=summary")

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute Tasks 1-6. Sequential.
Testing: R9-B Tasks 1-5, R9-C Task 6.

PRIORITY ORDER:
  Task 1: LessonSkill schema (foundation)
  Task 2: incident_history fields (additive, low risk)
  Task 3: Reflection type (additive)
  Task 4: evolve: action (new MCP surface)
  Task 5: TYPE_DEFAULTS + supersedes (write path)
  Task 6: Tests + self-eval + full suite

QUAN TRỌNG:
  LessonSkill.procedure validator — chỉ warn nếu procedure có nội dung
  nhưng thiếu section. Nếu procedure trống → OK (backward compat).
  
  evolve: action là READ-ONLY — không tạo node, chỉ trả về checklist.
  CTO Chat tạo Reflection node bằng batch: sau khi nhận checklist.

  supersedes auto-edge phải idempotent:
  gọi 2 lần không tạo 2 edges.

STOP nếu evolve: action scope không rõ → báo CEO.
GoBP MCP sau mỗi task (dec:d004).
Lesson: suggest: trước khi tạo node (dec:d011).
```

## Claude CLI
```
Audit Wave 17A06.
Verify:

Schema:
  □ LessonSkill.sub_type: enum [ai_self, work_quality, product]
  □ LessonSkill.procedure: validator bắt missing HOW/EVALUATE/EVOLVE_TRIGGER
  □ Reflection: group="Meta > Reflection", trigger enum, findings list
  □ incident_history: present trên Vulnerability, Migration, AuthFlow,
    Engine, APIEndpoint, Encryption

MCP:
  □ gobp(query="evolve: wave='17A06'") → trả về checklist (không tạo node)
  □ gobp(query="evolve: wave='17A06' status='complete'") → trả về message khi không có

Write path:
  □ LessonSkill create: defaults evolve_count=0
  □ LessonSkill với supersedes='old_id' → edge tạo + old node deprecated
  □ supersedes idempotent

Tests: 728+ passing.
GoBP MCP session capture. Không cần Lesson node.
```

## Push
```powershell
cd D:\GoBP
git add waves/wave_17a06_brief.md
git commit -m "Add Wave 17A06 Brief — self-upgrade loop + incident history"
git push origin main
```

---

## SAU WAVE 17A06 — MIHOS IMPORT

Wave 17A06 complete → GoBP có đủ schema cho cả Lessons lẫn Reflection.

Bước tiếp theo với MIHOS graph:
```
1. Tạo LessonSkill nodes cho cto-execute + cto-evolve skills
   (đang tồn tại trong /mnt/skills/user/ nhưng chưa có trong GoBP MCP)
2. Import MIHOS 32 docs còn lại (session 2026-04-18 IN_PROGRESS)
3. Tạo Reflection cho Wave 17A01-17A05 retrospective
```

---

*Wave 17A06 Brief v1.0 — 2026-04-19*  
*References: dec:d004, dec:d006, dec:d011*  
*Part of: Wave 17A Series*  
◈
