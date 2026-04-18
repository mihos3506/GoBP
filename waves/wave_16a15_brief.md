# WAVE 16A15 BRIEF — THIN HARNESS + FAT SKILLS SETUP

**Wave:** 16A15
**Title:** Agent self-evolution, docs ownership, GoBP backfill, import protocol
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-18
**For:** Cursor (sequential) + Claude CLI (audit + self-update)
**Status:** READY FOR EXECUTION
**Task count:** 8 tasks
**Estimated effort:** 6-8 hours

---

## REFERENCED GOBP NODES

This brief implements the following locked decisions:

| Decision ID | Topic | Summary |
|---|---|---|
| `dec:d001` | `team.workflow` | CTO quản lý, không làm trực tiếp |
| `dec:d002` | `import.protocol` | template→plan→review→batch |
| `dec:d003` | `docs.ownership` | Agents tự viết docs của mình |
| `dec:d004` | `gobp.update.obligation` | **BẤT BIẾN**: Mọi agent PHẢI cập nhật GoBP MCP |
| `dec:d005` | `gobp.backfill` | Backfill toàn bộ project data vào GoBP MCP |
| `dec:d006` | `brief.graph.linkage` | Brief PHẢI reference nodes, tạo mới PHẢI thông báo |

Task node: `thin_harness_fat_skills_setup.meta.42927104`

**NEW NODES sẽ tạo trong wave này:**
- Wave: Wave 16A15 (type=Wave)
- Lessons: từ quá trình Cursor tự viết rules (type=Lesson, nếu có)

---

## CONTEXT

GoBP đã có 626 tests, 30+ actions, đủ features. Nhưng quy trình làm việc chưa theo Thin Harness / Fat Skills:

```
Hiện tại:
  CTO viết .cursorrules cho Cursor       → Cursor không ownership
  CTO viết GoBP_AI_USER_GUIDE            → Cursor không học
  CTO viết CLAUDE.md cho Claude CLI      → CLI không ownership
  90% project history chưa trong GoBP MCP → Graph outdated
  Brief không reference GoBP nodes        → Brief cô lập

Sau wave này:
  Cursor tự viết .cursorrules             → Cursor ownership + tự học
  Cursor cập nhật GoBP_AI_USER_GUIDE      → Cursor biết best practices
  Claude CLI tự cập nhật CLAUDE.md        → CLI ownership
  Toàn bộ history trong GoBP MCP          → Graph = single source of truth
  Brief reference GoBP nodes              → Brief linked to graph
```

---

## CRITICAL PRINCIPLE

**CTO đặt yêu cầu + boundary. Agents tự viết implementation.**

CTO KHÔNG viết nội dung .cursorrules, GoBP_AI_USER_GUIDE, CLAUDE.md trong brief này. CTO chỉ đặt:
- PHẢI có gì
- KHÔNG được có gì
- Logic nào phải tuân theo
- Review criteria

Agents tự viết → CTO review → approve/reject.

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 626 existing tests must pass after every task.

**THÊM cho wave này:**
- R10: Sau mỗi task, Cursor PHẢI cập nhật GoBP MCP (dec:d004)
- R11: Cursor báo cáo mọi thay đổi docs cho CEO
- R12: Cursor chỉ sửa docs theo yêu cầu CTO, không sửa ngoài scope

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 626 tests

# Verify GoBP MCP decisions exist
D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch
root = Path('D:/GoBP')
index = GraphIndex.load_from_disk(root)
r = asyncio.run(dispatch('find:Decision mode=summary', index, root))
print(f'Decisions: {len(r.get(\"matches\", []))}')
for m in r.get('matches', []):
    print(f'  {m[\"id\"]}: {m[\"name\"][:60]}')
"
# Expected: dec:d001 through dec:d006
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Current version — Cursor will rewrite |
| 2 | `CLAUDE.md` | Current version — Claude CLI will update |
| 3 | `docs/AGENTS.md` | Agent roles + boundaries |
| 4 | `docs/GoBP_AI_USER_GUIDE.md` | Current guide — Cursor will update |
| 5 | `waves/wave_16a15_brief.md` | This file |
| 6 | GoBP MCP `dec:d001` through `dec:d006` | Locked decisions |

---

# TASKS

---

## TASK 1 — Cursor: đọc decisions, viết .cursorrules v6

**Goal:** Cursor đọc AGENTS.md + dec:d001 through dec:d006 từ GoBP MCP → tự viết .cursorrules v6.

**CTO requirements (PHẢI có):**
```
1. Role definition theo AGENTS.md — Cursor là dev, không phải architect
2. R9: baseline tests pass mỗi task
3. R10: cập nhật GoBP MCP sau mỗi wave (dec:d004 — bất biến)
4. Import protocol: template→plan→review→batch (dec:d002)
5. Mỗi node tạo ra trong graph có data PHẢI relate tới node đã có
6. Sequential execution, 1 task = 1 commit
7. Discovery before creation
8. Brief code authoritative
9. Lessons learned section — Cursor tự thêm khi gặp mistakes
```

**CTO requirements (KHÔNG được có):**
```
1. KHÔNG hardcode node IDs hay project-specific data
2. KHÔNG tự quyết kiến trúc
3. KHÔNG sửa foundational docs mà không có brief authorization
4. KHÔNG skip GoBP MCP update obligation
```

**Cursor tự viết phần còn lại** — format, structure, examples, wording.

**Sau khi viết xong:**
```
gobp(query="session:start actor='cursor' goal='Write .cursorrules v6'")
gobp(query="create:Lesson name='.cursorrules v6 rewrite' description='...' session_id='...'")
gobp(query="session:end ...")
```

**Commit message:**
```
Wave 16A15 Task 1: Cursor self-writes .cursorrules v6

- Cursor reads AGENTS.md + GoBP decisions dec:d001-d006
- Rewrites .cursorrules with ownership
- Includes GoBP MCP update obligation (dec:d004)
- Includes import protocol (dec:d002)
- GoBP MCP session captured
```

---

## TASK 2 — Cursor: viết import protocol checklist

**Goal:** Cursor tự viết import protocol document dựa trên dec:d002.

**CTO requirements:**
```
1. Checklist cho AI trước khi import bất kỳ document nào
2. Steps: đọc toàn bộ doc → liệt kê nodes+edges → CEO review → batch
3. Rule: KHÔNG tạo nodes trước rồi tính sau edges
4. Rule: Khi graph đã có data, node mới PHẢI relate tới node đã có
5. Rule: project mới chưa có data → không bắt edge cho node đầu tiên
6. Template trước → yêu cầu chi tiết cho mỗi node → tuần tự từng node
7. Lưu tại: docs/IMPORT_CHECKLIST.md
```

**Cursor tự viết nội dung.** CEO review khi xong.

**Sau khi viết:**
```
gobp(query="create:Document name='Import Checklist' description='...' session_id='...'")
```

**Commit message:**
```
Wave 16A15 Task 2: Cursor writes import protocol checklist

- docs/IMPORT_CHECKLIST.md — AI import protocol
- Based on dec:d002 (template→plan→review→batch)
- GoBP MCP node created for document
```

---

## TASK 3 — Cursor: cập nhật GoBP_AI_USER_GUIDE.md

**Goal:** Cursor cập nhật guide dựa trên lessons từ Wave 16A04-16A14.

**CTO requirements:**
```
1. Thêm import protocol reference (link to IMPORT_CHECKLIST.md)
2. Thêm Query Rule 11: node mới PHẢI relate (khi graph có data)
3. Thêm Query Rule 12: đọc toàn bộ doc trước khi import
4. Cập nhật node types nếu có thay đổi
5. Cập nhật edge types nếu có thay đổi
6. Reflect features mới: InvertedIndex, AdjacencyIndex, DFS cycle detection
7. KHÔNG xóa rules CTO đã viết, chỉ thêm mới
```

**Cursor tự viết phần mới.** Báo cáo changes cho CEO.

**Commit message:**
```
Wave 16A15 Task 3: Cursor updates GoBP_AI_USER_GUIDE.md

- Import protocol rules added
- New features documented (indexes, cycle detection)
- GoBP MCP update captured
```

---

## TASK 4 — Backfill: import tất cả wave history vào GoBP MCP

**Goal:** Ghi toàn bộ Wave 0-16A14 vào GoBP MCP (dec:d005).

**CTO requirements:**
```
1. Tạo Wave nodes cho Wave 0, 1, 2, 3, 5, 16A04-16A14
2. Mỗi Wave node: name, description (summary), status=COMPLETED
3. Batch import — dùng batch hoặc quick: action
4. Edge: Wave --references--> relevant Decision/Task nodes nếu biết
5. Đọc CHANGELOG.md + git log để lấy data
6. KHÔNG đoán — chỉ ghi những gì có evidence
```

**Commit message:**
```
Wave 16A15 Task 4: backfill Wave 0-16A14 history into GoBP MCP

- Wave nodes created for all completed waves
- Edges to relevant decisions where known
- Based on CHANGELOG.md + git log evidence
```

---

## TASK 5 — Backfill: import architecture decisions vào GoBP MCP

**Goal:** Ghi decisions từ foundational docs vào GoBP MCP.

**CTO requirements:**
```
1. Đọc CHARTER.md, ARCHITECTURE.md, VISION.md
2. Extract locked decisions đã có trong docs
3. Kiểm tra trùng trước khi tạo (suggest: trước batch)
4. Tạo Decision nodes qua lock:Decision
5. Edge: Decision --references--> Document nếu biết source doc
6. KHÔNG duplicate dec:d001-d006 đã có
```

**Commit message:**
```
Wave 16A15 Task 5: backfill architecture decisions into GoBP MCP

- Decisions from CHARTER/ARCHITECTURE/VISION imported
- Duplicate check via suggest: before create
- Edges to source documents
```

---

## TASK 6 — Claude CLI: tự cập nhật CLAUDE.md

**Đây là task cho Claude CLI, KHÔNG phải Cursor.**

CEO sẽ dispatch riêng cho Claude CLI sau khi Cursor hoàn thành Task 1-5.

**CTO requirements cho Claude CLI:**
```
1. Đọc AGENTS.md + dec:d001 through dec:d006
2. Tự cập nhật CLAUDE.md phù hợp role QA audit gate
3. Thêm: GoBP MCP update obligation — PHẢI capture session sau mỗi audit
4. Thêm: import wave brief vào GoBP MCP sau audit
5. KHÔNG xóa audit checklist hiện tại
6. Tự thêm lessons learned section
7. Báo cáo changes cho CEO
```

**Claude CLI tự ghi vào GoBP MCP:**
```
gobp(query="session:start actor='claude-cli' goal='Self-update CLAUDE.md'")
gobp(query="create:Lesson name='CLAUDE.md self-update' description='...' session_id='...'")
gobp(query="session:end ...")
```

**Commit message (Claude CLI commits):**
```
Wave 16A15 Task 6: Claude CLI self-updates CLAUDE.md

- Claude CLI reads AGENTS.md + GoBP decisions
- Rewrites CLAUDE.md with ownership
- GoBP MCP update obligation added
- Session captured in GoBP MCP
```

---

## TASK 7 — Test: import protocol trên MIHOS data

**Goal:** Cursor áp dụng import checklist (Task 2) trên MIHOS GoBP.

**CTO requirements:**
```
1. Dùng gobp-mihos MCP
2. Chọn 1 nhóm Invariants chưa có enforces edges
3. Áp dụng import checklist:
   - Đọc Invariant descriptions
   - Liệt kê nodes + edges cần tạo
   - Báo cáo plan cho CEO (trong commit message)
   - Batch tạo edges
4. Verify: explore: Invariant → thấy enforces edges
5. Báo cáo kết quả: bao nhiêu orphan Invariants còn lại
```

**Commit message:**
```
Wave 16A15 Task 7: test import protocol on MIHOS — fix orphan Invariants

- Import checklist applied to MIHOS Invariants
- N enforces edges added
- M orphan Invariants remaining (from N total)
- Import protocol validated on real data
```

---

## TASK 8 — Verify + CHANGELOG

**CTO requirements:**
```
1. Run full test suite — 626+ tests
2. Verify GoBP MCP has new data:
   - Wave nodes for 0-16A14
   - Architecture decisions
   - .cursorrules v6 lesson
   - Import checklist document
3. CHANGELOG entry for Wave 16A15
4. Cursor self-evaluate: "Tôi đã học gì trong wave này?"
   → Ghi vào GoBP MCP as Lesson node
```

**Commit message:**
```
Wave 16A15 Task 8: verify + CHANGELOG + lessons learned

- 626+ tests passing
- GoBP MCP verified: waves, decisions, docs backfilled
- CHANGELOG: Wave 16A15 entry
- Lesson: Cursor self-evaluation captured in GoBP MCP
```

---

# CEO DISPATCH

## Cursor (Task 1-5, 7-8)
```
Read .cursorrules, AGENTS.md, docs/GoBP_AI_USER_GUIDE.md,
and waves/wave_16a15_brief.md.

CRITICAL: Read GoBP MCP decisions FIRST:
  gobp(query="find:Decision mode=summary")
  Read dec:d001 through dec:d006 — these are your requirements.

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute Tasks 1-5, 7-8. Skip Task 6 (Claude CLI task).
R9: 626 tests baseline. R10: GoBP MCP update after each task.
1 task = 1 commit.

REMEMBER: You are WRITING .cursorrules yourself. 
CTO gave you requirements, not content. 
You own the implementation. You write it. You learn from it.
```

## Claude CLI (Task 6)
```
Read CLAUDE.md and AGENTS.md.
Read GoBP MCP decisions:
  gobp(query="find:Decision mode=summary")

You are UPDATING CLAUDE.md yourself.
CTO requirements:
  1. GoBP MCP update obligation (dec:d004) — MUST capture session after every audit
  2. Import wave brief into GoBP MCP after audit
  3. Add lessons learned section
  4. Keep existing audit checklist
  5. Report changes to CEO

Commit: "Wave 16A15 Task 6: Claude CLI self-updates CLAUDE.md"

After update:
  gobp(query="session:start actor='claude-cli' goal='Self-update CLAUDE.md per dec:d003'")
  gobp(query="create:Lesson name='CLAUDE.md v3 self-update' ...")
  gobp(query="session:end ...")
```

## Push
```powershell
cd D:\GoBP
git add -A
git push origin main
```

---

*Wave 16A15 Brief v1.0 — 2026-04-18*
*References: dec:d001-d006, thin_harness_fat_skills_setup.meta.42927104*

◈
