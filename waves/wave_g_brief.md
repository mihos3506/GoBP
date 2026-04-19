# WAVE G BRIEF — CODE REFACTOR + CLEAN

**Wave:** G  
**Title:** Xóa code v2 + Sửa pre-existing bugs + Clean codebase  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-19  
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)  
**Status:** READY FOR EXECUTION  
**Task count:** 8 atomic tasks  
**Estimated effort:** 4-5 hours  

---

## CONTEXT

GoBP đã qua Waves A-F với schema v3 hoàn chỉnh. Wave G dọn dẹp:

```
1. Xóa code v2 không còn dùng:
   validator_v2.py, old mutator.py, old graph.py stubs,
   legacy schema files, deprecated CLI tools

2. Sửa pre-existing bugs phát hiện qua audit:
   - VISIBLE_LIFECYCLES + VISIBLE_READ_ORDERS referenced nhưng không defined
   - test_wave16a02.py expects nodes trong DB nhưng DB đang empty

3. Clean .cursorrules:
   - Xóa v2 legacy section
   - Update QR rules phản ánh v3

4. README.md update:
   - Reading order cập nhật
   - Current state đúng
```

**QUAN TRỌNG:** Không xóa test files liên quan đến v3 (test_wave_a/b/c/d/e/f). Chỉ xóa v2 legacy code.

---

## REFERENCED DOCUMENTS

| Doc | Focus |
|---|---|
| `docs/SCHEMA.md` | Schema v3 authoritative |
| `docs/ARCHITECTURE.md` | Architecture v3 |
| `docs/README.md` | File index |

---

## CURSOR EXECUTION RULES

### R1-R8: Standard (xem `.cursorrules` — QR1-QR7)

### R9 — Testing strategy
- Tasks 1-6: R9-A hoặc R9-B tùy task
- Task 7 (tests): `pytest tests/ -q --tb=no` — full suite clean
- End of wave: `pytest tests/ -q --tb=no`

---

## REQUIRED READING — BEFORE TASK 1

| # | File |
|---|---|
| 1 | `.cursorrules` (full) |
| 2 | `docs/README.md` |
| 3 | `docs/SCHEMA.md` |
| 4 | `gobp/core/` (list tất cả files) |
| 5 | `gobp/mcp/tools/` (list tất cả files) |
| 6 | `gobp/viewer/index.html` (tìm VISIBLE_LIFECYCLES) |
| 7 | `tests/test_wave16a02.py` |

---

## TASKS

---

## TASK 1 — Xóa v2 Core Files

**Goal:** Xóa các files schema v2 không còn dùng trong `gobp/core/`.

**Re-read toàn bộ `gobp/core/` directory trước. List files, verify từng file có còn được import không.**

Files cần xóa (chỉ xóa nếu confirm không còn import):
```
gobp/core/validator_v2.py     ← replaced by validator_v3.py
gobp/core/mutator.py          ← replaced by mutator_v3.py (nếu còn tồn tại)
```

**Quy trình verify trước khi xóa:**
```powershell
# Check xem có file nào import validator_v2 không
Select-String -Path "gobp\**\*.py" -Pattern "validator_v2" -Recurse
# Nếu không có → xóa an toàn

Select-String -Path "gobp\**\*.py" -Pattern "from gobp.core.mutator import" -Recurse
# Nếu không có → xóa an toàn
```

Nếu tìm thấy import → cập nhật import trỏ sang v3 trước khi xóa.

**Acceptance criteria:**
- `validator_v2.py` không còn trong codebase
- `mutator.py` (v2) không còn trong codebase (nếu tồn tại)
- Không có file nào import từ deleted files
- Tests vẫn pass

**Commit message:**
```
Wave G Task 1: remove v2 core files — validator_v2.py, mutator.py
```

---

## TASK 2 — Xóa v2 Legacy trong MCP

**Goal:** Xóa v2 legacy code trong MCP layer.

**Re-read `gobp/mcp/tools/write.py` và `gobp/mcp/dispatcher.py` trước.**

Tìm và xóa:
```python
# Xóa backward compat wrappers đã deprecated:
# - update: action (alias của edit:)
# - retype: action (alias của edit:)
# Nếu còn trong dispatcher.py → xóa, chỉ giữ edit:
```

Tìm và xóa các v2 node type handling nếu còn:
```python
# Bất kỳ code nào check lifecycle, read_order, priority fields
# trong write path → xóa
```

**Acceptance criteria:**
- `update:` và `retype:` không còn là separate actions
- Không còn reference đến `lifecycle`, `read_order` trong write path
- `edit:` là action duy nhất cho writes
- Tests pass

**Commit message:**
```
Wave G Task 2: remove v2 legacy actions — update:, retype: aliases
```

---

## TASK 3 — Fix Viewer: VISIBLE_LIFECYCLES + VISIBLE_READ_ORDERS

**Goal:** Fix pre-existing bug — `VISIBLE_LIFECYCLES` và `VISIBLE_READ_ORDERS` được reference nhưng chưa defined.

**File to modify:** `gobp/viewer/index.html`

**Tìm trong index.html:**
```javascript
// Tìm: VISIBLE_LIFECYCLES, VISIBLE_READ_ORDERS
// Những references này gây ReferenceError khi click CORE ONLY / SHOW ALL
```

**Fix:** Xóa hoàn toàn references tới 2 biến này. Không cần define chúng — đây là schema v2 artifact.

```javascript
// Trong handler của btn-core và btn-all:
// Xóa bất kỳ line nào check/filter VISIBLE_LIFECYCLES
// Xóa bất kỳ line nào check/filter VISIBLE_READ_ORDERS
```

**Acceptance criteria (R9-A):**
- Click "CORE ONLY" → không có ReferenceError trong console
- Click "SHOW ALL" → không có ReferenceError trong console
- Graph filter vẫn hoạt động đúng

**Commit message:**
```
Wave G Task 3: fix viewer — remove undefined VISIBLE_LIFECYCLES + VISIBLE_READ_ORDERS
```

---

## TASK 4 — Fix test_wave16a02.py

**Goal:** Fix hoặc xóa test expect nodes trong DB (fail khi DB empty).

**File:** `tests/test_wave16a02.py`

**Re-read file trước.**

```
test_graph_loads_migrated_project:
  Loads GraphIndex từ D:/GoBP
  Expects len(all_nodes()) > 0
  → Fail khi .gobp/ empty
```

**Options:**
1. Xóa test này (migration test không còn relevant sau Wave G)
2. Sửa thành skip khi không có data

**Preferred:** Xóa test `test_graph_loads_migrated_project` vì:
- Migration từ v2 → v3 không còn cần thiết (DB đã clear)
- Test này phụ thuộc vào live data (anti-pattern)

Nếu toàn bộ `test_wave16a02.py` chỉ có migration tests → xóa cả file.

**Acceptance criteria:**
- `pytest tests/ -q --tb=no` → 0 failures
- Không còn test nào expect live data tại D:/GoBP

**Commit message:**
```
Wave G Task 4: remove test_wave16a02.py — migration tests no longer relevant
```

---

## TASK 5 — Clean .cursorrules

**Goal:** Update `.cursorrules` — xóa v2 legacy section, update cho v3.

**File to modify:** `.cursorrules`

**Re-read `.cursorrules` toàn bộ trước.**

**Xóa:**
```
- "Schema v2 Rules" section (hoặc legacy v2 section còn sót lại)
- Bất kỳ reference nào đến lifecycle, read_order, priority
- Bất kỳ reference nào đến validator_v2, mutator.py (v2)
- QR rules về v2 edge types (discovered_in, typed edges)
```

**Update:**
```
- Schema section: chỉ còn Schema v3
- Testing: R9 guidelines đúng với waves hiện tại
- Module references: chỉ v3 modules
```

**Acceptance criteria (R9-A):**
- `.cursorrules` không còn reference v2 artifacts
- Schema v3 section đầy đủ và accurate
- QR rules phản ánh đúng codebase hiện tại

**Commit message:**
```
Wave G Task 5: .cursorrules — remove v2 legacy, update to v3 only
```

---

## TASK 6 — Clean docs/README.md

**Goal:** Update `docs/README.md` — current state đúng, deprecated list updated.

**File to modify:** `docs/README.md`

**Re-read README.md trước.**

**Update:**
```
CURRENT STATE:
  Schema:       v3 — 2 templates, ~75 node types
  Waves done:   A, B, C, D, E, F, G
  Tests:        765+ passing
  DB:           PostgreSQL primary (clean, schema v3)
  Viewer:       3D graph + Dashboard
  Multi-agent:  import lock + validate v3 + session watchdog + ping

DEPRECATED (đã xóa trong Wave G):
  validator_v2.py
  mutator.py (v2)
  update: / retype: actions
  lifecycle / read_order fields
  test_wave16a02.py
```

**Acceptance criteria (R9-A):**
- README.md có current state đúng
- Deprecated section phản ánh Wave G cleanups

**Commit message:**
```
Wave G Task 6: docs/README.md — update current state + deprecated list
```

---

## TASK 7 — Orphaned CSS Cleanup trong Viewer

**Goal:** Xóa orphaned CSS và dead code trong viewer.

**File to modify:** `gobp/viewer/index.html`

**Tìm và xóa:**
```css
/* .gobp-query class — không còn được render (Wave E đã xóa gobp query display) */
.gobp-query { ... }
```

**Tìm và xóa dead JavaScript variables/functions nếu có:**
```javascript
// Bất kỳ variable/function nào không còn được gọi
// Liên quan đến v2 features đã xóa
```

**Không xóa:** Bất kỳ CSS/JS nào vẫn đang active.

**Acceptance criteria (R9-A):**
- `.gobp-query` CSS class không còn trong stylesheet
- Không có console warnings về undefined/unused variables
- Viewer vẫn load và hoạt động đúng

**Commit message:**
```
Wave G Task 7: viewer — remove orphaned .gobp-query CSS + dead code
```

---

## TASK 8 — CHANGELOG Update

**Goal:** Update `CHANGELOG.md` với Wave G entry.

**File to modify:** `CHANGELOG.md`

**Re-read CHANGELOG.md trước.**

Prepend:

```markdown
## [Wave G] — Code Refactor + Clean — 2026-04-19

### Removed
- `gobp/core/validator_v2.py` — superseded by validator_v3.py
- `gobp/core/mutator.py` (v2) — superseded by mutator_v3.py
- `update:` / `retype:` MCP actions — use `edit:` instead
- `lifecycle`, `read_order` references in write path
- `tests/test_wave16a02.py` — migration test no longer relevant
- Orphaned CSS `.gobp-query` in viewer

### Fixed
- Viewer: `VISIBLE_LIFECYCLES` + `VISIBLE_READ_ORDERS` ReferenceError
  (pre-existing from Wave C, btn-core/btn-all handlers now clean)

### Changed
- `.cursorrules` — v2 legacy section removed, v3 only
- `docs/README.md` — current state updated (Wave A-G done, 765+ tests)

---
```

**Commit message:**
```
Wave G Task 8: CHANGELOG.md — Wave G code refactor + clean
```

---

## POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# Verify v2 files gone
Test-Path gobp/core/validator_v2.py   # False
Test-Path gobp/core/mutator.py         # False (nếu đã tồn tại)

# Verify no v2 imports
Select-String -Path "gobp\**\*.py" -Pattern "validator_v2|from gobp.core.mutator import" -Recurse
# Expected: no matches

# Fast suite — 0 failures
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

## CEO DISPATCH INSTRUCTIONS

### 1. Cursor

```
Read .cursorrules (full).
Read docs/README.md, gobp/core/ directory, gobp/mcp/tools/ directory.
Read gobp/viewer/index.html (tìm VISIBLE_LIFECYCLES, .gobp-query).
Read tests/test_wave16a02.py.
Read waves/wave_g_brief.md (this file).

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute Tasks 1 → 8 sequentially.
Tasks 1-2: verify imports trước khi xóa (Select-String).
Task 3: R9-A — verify console no errors.
Tasks 4-6: R9-A — verify files.
Task 7: R9-A — verify viewer.
Task 8: R9-A — verify CHANGELOG.
End: pytest tests/ -q --tb=no → 0 failures.
```

### 2. Claude CLI audit

```
Audit Wave G.
Task 1: validator_v2.py gone, no remaining imports
Task 2: update:/retype: gone, no lifecycle/read_order in write path
Task 3: viewer btn-core/btn-all no ReferenceError
Task 4: test_wave16a02.py gone, full suite 0 failures
Task 5: .cursorrules has no v2 references
Task 6: README.md current state correct
Task 7: .gobp-query CSS gone, viewer works
Task 8: CHANGELOG Wave G entry correct
BLOCKING: Bất kỳ fail → STOP, báo CEO.
```

### 3. Push (sau khi audit PASS)

```powershell
cd D:\GoBP
git add waves/wave_g_brief.md
git commit -m "Wave G Brief: Code Refactor + Clean — 8 tasks"
git push origin main
```

---

*Wave G Brief — Code Refactor + Clean*  
*2026-04-19 — CTO Chat*  
◈
