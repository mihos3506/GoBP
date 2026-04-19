# WAVE 17A04 BRIEF — DOCS + AGENTS SELF-UPDATE + BACKFILL

**Wave:** 17A04
**Title:** Cursor self-eval, CLAUDE.md update, GoBP_AI_USER_GUIDE v2, backfill
**Author:** CTO Chat
**Date:** 2026-04-19
**For:** Cursor (Tasks 1,3,4,5) + Claude CLI (Task 2) + CEO dispatch GoBP MCP
**Status:** READY FOR EXECUTION
**Task count:** 5 tasks
**Estimated effort:** 3-4 hours

---

## REFERENCED GOBP NODES

| Node ID | Topic |
|---|---|
| `dec:d003` | Agents tự viết docs của mình |
| `dec:d004` | GoBP update obligation |
| `dec:d005` | Backfill toàn bộ project data |
| `dec:d011` | Graph hygiene — update over create |

---

## CONTEXT

Waves 17A01-17A03 đã complete:
```
✅ Schema v2: 93 types, group breadcrumb
✅ Validator v2: auto_fix, pattern validation
✅ Query engine: find: group, get: modes, explore: siblings
✅ 690 tests
```

Wave 17A04:
```
Task 1: Cursor self-evaluation — đánh giá code 17A01-17A03
Task 2: Claude CLI self-update CLAUDE.md
Task 3: GoBP_AI_USER_GUIDE.md v2
Task 4: IMPORT_CHECKLIST.md update
Task 5: Backfill GoBP MCP (waves 17A01-17A03)
```

---

## CURSOR EXECUTION RULES

R1-R12 (.cursorrules v8).

**Testing:**
- Task 1: R9-A (self-evaluation, không pytest)
- Task 3-4: R9-A (docs only)
- Task 5: R9-A (GoBP MCP writes only)
- Cuối wave: R9-C full suite (690+ baseline)

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

## TASK 1 — Cursor self-evaluation + .cursorrules v9

**Goal:** Cursor tự đánh giá code quality của waves 17A01-17A03,
rút ra lessons, update .cursorrules từ experience thực tế.

**KHÔNG phải:** CTO dictate rules. Cursor tự tìm.

**Cursor phải tự hỏi:**

```
PHẦN 1 — Code quality review:

□ gobp/core/id_generator.py
  - Function nào > 50 lines?
  - Có duplicate logic không?
  - Edge cases có được handle không?
  - Naming có rõ ràng không?

□ gobp/core/file_format.py
  - auto_fill_description() có đủ robust không?
  - append_edge() dedup logic có sạch không?

□ gobp/core/schema_loader.py
  - SchemaV2 có over-engineered không?
  - lru_cache có cần thiết không?

□ gobp/core/validator_v2.py
  - validate_node() có quá dài không?
  - auto_fix() có cover đủ cases không?

□ gobp/core/graph.py — group indexing
  - _build_group_index() performance?
  - find_by_group() edge cases (empty string, None)?
  - find_siblings() khi node không có group?

□ gobp/mcp/tools/read.py — find/explore/get/suggest
  - _parse_find_inline_params() regex có fragile không?
  - _get_relationships() có duplicate với explore không?
  - get_node() mode handling có clean không?

□ Tests 17A01-17A03
  - Có test nào test wrong behavior không?
  - Có edge case nào bị miss không?
  - Test names có mô tả đúng không?

PHẦN 2 — Lessons learned:
  □ Tôi gặp vấn đề gì trong 17A01-17A03?
  □ Tôi fix thế nào?
  □ Có cách làm tốt hơn không?
  □ Pattern nào tôi sẽ dùng lại?
  □ Anti-pattern nào tôi sẽ tránh?

PHẦN 3 — .cursorrules v9 update:
  □ Chỉ thêm rules từ experience thực tế
  □ Cả reactive (tránh lỗi) + proactive (làm tốt hơn)
  □ Format mỗi rule:
     "Do: X → Vì Y [learned Wave 17A0Z]"
     "Don't: X → Vì Y [learned Wave 17A0Z]"
```

**Báo cáo cho CEO:**
```
Cursor báo cáo:
  1. Code quality findings (tốt/cần cải thiện)
  2. Rules thêm vào .cursorrules + lý do từ experience
  3. Có muốn refactor gì không? (CEO quyết định)
```

**Commit:**
```
Wave 17A04 Task 1: .cursorrules v9 — self-evaluation 17A01-17A03

- Code quality review findings
- N rules added from actual experience
- [list rules thêm + lý do]
```

---

## TASK 2 — Claude CLI self-update CLAUDE.md

**Đây là task cho Claude CLI — dispatch riêng.**

**Goal:** Claude CLI tự đánh giá audit process của 17A01-17A03,
update CLAUDE.md từ experience thực tế.

**Claude CLI tự hỏi:**

```
PHẦN 1 — Audit quality review:
  □ Audit 17A01: Tôi verify đủ không?
    Có gì tôi nên check mà đã miss?
  □ Audit 17A02: Cutover verification đủ chưa?
    Backup files tôi có verify content không?
  □ Audit 17A03: Group index tôi test thực tế không?
    Hay chỉ check file exists?

PHẦN 2 — Lessons learned:
  □ Audit pattern nào hiệu quả?
  □ Cần thêm verification step nào?
  □ Schema v2 audit cần check gì thêm?

PHẦN 3 — CLAUDE.md update:
  □ Thêm schema v2 audit checklist
  □ Thêm group index verification steps
  □ Thêm ErrorCase code pattern check
  □ Chỉ từ experience thực tế 17A01-17A03
```

**Commit (Claude CLI):**
```
Wave 17A04 Task 2: CLAUDE.md update — audit lessons 17A01-17A03
```

---

## TASK 3 — GoBP_AI_USER_GUIDE.md v2

**Goal:** Update guide để AI dùng được schema v2 + query v2.

**File:** `docs/GoBP_AI_USER_GUIDE.md`

**Cursor cập nhật các phần sau** (giữ phần còn giá trị, update phần outdated):

**1. Node types table — update hoàn toàn:**
```
Thay 21 node types cũ → 93 types theo taxonomy v2
Format: Type | Group | read_order | Mô tả ngắn

Ví dụ:
  Entity     | Dev > Domain > Entity            | foundational | Domain objects
  AuthFlow   | Dev > Infrastructure > Security  | foundational | Auth flows
  Invariant  | Constraint > Invariant           | foundational | Boolean constraints
  ErrorCase  | Error > ErrorCase                | reference    | Specific errors
  ...
```

**2. find: examples — thêm group filter:**
```
# Group queries (mới):
gobp(query="find: group='Dev > Infrastructure > Security'")
→ Tất cả Security nodes

gobp(query="find: group contains 'Security'")
→ Nodes có Security trong group path

gobp(query="find: group='Dev > Domain' type=Entity")
→ Combined: group + type filter

# Backward compat (vẫn còn):
gobp(query="find: mi hốt mode=summary")
gobp(query="find:Engine mode=summary")
```

**3. get: modes — thêm section mới:**
```
gobp(query="get: node_id")               ← default = brief
gobp(query="get: node_id mode=brief")    ← name/group/description.info/relationships
gobp(query="get: node_id mode=full")     ← tất cả fields có nghĩa
gobp(query="get: node_id mode=debug")    ← tất cả (chỉ khi debug)

Brief mode ẩn: raw metadata, outgoing/incoming lists
Brief mode hiển thị: group, lifecycle, read_order, relationships với reason
```

**4. explore: — update với siblings:**
```
gobp(query="explore: TrustGate")
→ Trả về:
  - breadcrumb: Dev > Infrastructure > Engine
  - siblings: nodes cùng group (Engine group)
  - relationships: với reason field
  - group: "Dev > Infrastructure > Engine"
```

**5. suggest: — update group-aware:**
```
gobp(query="suggest: OTP Flow group='Dev > Infrastructure > Security'")
→ Tìm trong cùng Security group trước
→ HIGH SIMILARITY warning nếu score > 0.8
→ Recommendation: UPDATE vs CREATE
```

**6. ID format — update v2:**
```
Format mới: {group_slug}.{name_slug}.{8hex}

dev.domain.entity.traveller.a1b2c3d4
dev.infra.sec.authflow.otp.b2c3d4e5
const.invariant.balance_nonneg.c3d4e5f6
error.case.gps_e_001.d4e5f6a7
```

**7. Query Rules — thêm rules mới:**
```
11. group:     Dùng group filter thay type filter khi cần hierarchy
12. mode=brief: Default cho get: — ẩn raw fields
13. ErrorCase: Tìm theo domain trước: find: group="Error" domain=gps
14. Invariant: PHẢI có rule field — Boolean expression
```

**8. Workflow — thêm schema v2 workflow:**
```
### Import với schema v2
1. template: Type        ← xem group + required fields
2. suggest: name group=  ← group-aware dedup
3. batch với group field ← auto-infer nếu không set
4. explore: node_id      ← verify breadcrumb + siblings
```

**Giữ lại (không xóa):**
- Session lifecycle
- batch operations reference table
- Token guide
- Những điều KHÔNG làm

**Commit:**
```
Wave 17A04 Task 3: GoBP_AI_USER_GUIDE.md v2

- Node types: 93 types v2 taxonomy
- find: group filter examples
- get: mode=brief/full/debug
- explore: breadcrumb + siblings
- suggest: group-aware
- ID format v2
- Query Rules 11-14
```

---

## TASK 4 — IMPORT_CHECKLIST.md update

**Goal:** Update checklist cho schema v2.

**File:** `docs/IMPORT_CHECKLIST.md`

**Thêm/update các phần:**

```
1. Pre-import checklist (update):
   □ Đọc template: Type → check group + required fields
   □ suggest: name group=X → tìm duplicate trong group
   □ Plan: nodes + group + relationships
   □ CEO review plan

2. Node creation checklist (thêm):
   □ group field: auto-infer từ type nếu không set
   □ description.info: REQUIRED — không để trống
   □ lifecycle: draft nếu chưa specify
   □ read_order: theo type default nếu không set

3. ErrorCase import (thêm mới):
   □ Đọc ErrorDomain trước: find: group="Error > ErrorDomain"
   □ code format: {DOMAIN}_{FEWI}_{SEQ} — VD: GPS_E_001
   □ context.features/flows PHẢI có
   □ trigger phải đủ chi tiết để AI sau tìm được
   □ fix phải có (REQUIRED)

4. Invariant import (update):
   □ rule REQUIRED — Boolean expression
   □ KHÔNG dùng "KHÔNG được X" làm Invariant
   □ "KHÔNG được X" → BusinessRule type
   □ scope: class | object | system
   □ enforcement: hard | soft
   □ violation_action: reject | devalue | flag | log

5. Post-import verify (update):
   □ explore: node_id → check breadcrumb đúng group
   □ explore: node_id → check siblings reasonable
   □ relationships có reason field
   □ validate: → 0 hard errors
```

**Commit:**
```
Wave 17A04 Task 4: IMPORT_CHECKLIST.md v2 — schema v2 aware
```

---

## TASK 5 — Backfill GoBP MCP: waves 17A01-17A03

**Goal:** Ghi waves 17A01-17A03 vào GoBP project graph (dec:d005).

**Read trước:**
```powershell
# Check current state
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -c "
from pathlib import Path
from gobp.core.graph import GraphIndex
index = GraphIndex.load_from_disk(Path('D:/GoBP'))
print('Nodes:', len(list(index.all_nodes())))
"
```

**Batch import waves:**

```
gobp(query="session:start actor='cursor' goal='Backfill waves 17A01-17A03 into GoBP MCP'")

# Wave 17A01
gobp(query="batch session_id='<id>' ops='
create: Wave: Wave 17A01 | Schema + File Format Rewrite. core_nodes_v2.yaml (65+ types), core_edges_v2.yaml, id_generator v2, file_format v2, schema_loader v2. 25 tests.
edge+: Wave 17A01 --references--> dec:d004
edge+: Wave 17A01 --references--> dec:d006
'")

# Wave 17A02
gobp(query="batch session_id='<id>' ops='
create: Wave: Wave 17A02 | Validator Bridge + Cutover. ValidatorV2, cutover core_nodes.yaml=v2, seed update, MCP bridge, .cursorrules v7. 670 tests.
edge+: Wave 17A02 --references--> dec:d004
'")

# Wave 17A03
gobp(query="batch session_id='<id>' ops='
create: Wave: Wave 17A03 | Query Engine. find: group filter, explore: breadcrumb+siblings, get: brief/full/debug, suggest: group-aware. .cursorrules v8. 690 tests.
edge+: Wave 17A03 --references--> dec:d004
'")

gobp(query="session:end session_id='<id>' outcome='Waves 17A01-17A03 backfilled'")
```

**Commit:**
```
Wave 17A04 Task 5: backfill waves 17A01-17A03 into GoBP MCP
```

---

## END OF WAVE — Full suite

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --override-ini="addopts=" -q --tb=no
# Expected: 690+ tests (no new code = same count)
```

**CHANGELOG:**
```markdown
## [Wave 17A04] — Docs + Agents + Backfill — 2026-04-19

### Changed
- .cursorrules v9: self-evaluation lessons from 17A01-17A03
- CLAUDE.md: audit lessons 17A01-17A03 (Claude CLI)
- docs/GoBP_AI_USER_GUIDE.md v2: schema v2, query v2, 93 types
- docs/IMPORT_CHECKLIST.md v2: schema v2 aware

### Added
- GoBP MCP: Wave nodes 17A01-17A03 backfilled

### Tests: 690+ (no new code changes)
```

---

# CEO DISPATCH

## Cursor (Tasks 1, 3, 4, 5)
```
Read .cursorrules v8 + waves/wave_17a04_brief.md.
Read docs/GoBP_AI_USER_GUIDE.md TRƯỚC Task 3.
Read docs/IMPORT_CHECKLIST.md TRƯỚC Task 4.

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute Tasks 1, 3, 4, 5. Skip Task 2 (Claude CLI).

Task 1 (QUAN TRỌNG):
  Tự đánh giá code 17A01-17A03 thật sự
  Không copy requirements từ brief vào cursorrules
  Chỉ thêm rules từ experience thực tế
  Báo cáo findings rõ ràng cho CEO

R9-A for all tasks (docs + MCP writes).
Full suite cuối wave: 690+ expected.

GoBP MCP sau mỗi task (dec:d004).
Lesson: suggest: trước khi tạo (dec:d011).
```

## Claude CLI (Task 2)
```
Read CLAUDE.md current + waves/wave_17a04_brief.md.
Self-evaluate audit process từ waves 17A01-17A03.
Update CLAUDE.md từ experience thực tế.
Không copy requirements từ brief vào CLAUDE.md.
Báo cáo changes + lý do cho CEO.

GoBP MCP session capture (dec:d004).
Commit: "Wave 17A04 Task 2: CLAUDE.md — audit lessons 17A01-17A03"
```

## Push
```powershell
cd D:\GoBP
git add waves/wave_17a04_brief.md
git commit -m "Add Wave 17A04 Brief — docs + agents + backfill"
git push origin main
```

---

*Wave 17A04 Brief v1.0 — 2026-04-19*
*References: dec:d003, dec:d004, dec:d005, dec:d011*
*Part of: Wave 17A Series (7 waves)*
◈
