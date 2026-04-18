# WAVE 16A17 BRIEF — REMOVE XDIST + SLOW MARKERS + TEST ORGANIZATION

**Wave:** 16A17
**Title:** Remove pytest-xdist, add slow markers, clean test strategy
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-18
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 3 tasks
**Estimated effort:** 1-2 hours

---

## REFERENCED GOBP NODES

| Node ID | Topic |
|---|---|
| `dec:d004` | GoBP update obligation |

---

## CONTEXT

Wave 16A16 Task 1 đã install pytest-xdist + `-n auto`.
**Vấn đề:** xdist chiếm CPU quá lớn → không phù hợp.

**Mục tiêu:**
```
1. Uninstall pytest-xdist
2. Remove -n auto từ config
3. Add @pytest.mark.slow markers
4. Default: pytest = fast suite (không slow)
5. End of wave: pytest -m "" = full suite

Dev workflow:
  Daily:      pytest tests/ -q          → < 1 phút (default skip slow)
  End of wave: pytest tests/ -m "" -q   → full suite, chạy 1 lần
```

---

## CURSOR EXECUTION RULES

R1-R12 (.cursorrules v6).
Testing:
- Task 1-2: R9-B (code change, chạy module tests)
- Task 3: R9-C full suite 1 lần (không dùng -n auto)

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -m "" -q --tb=no
# Expected: 626+ tests (baseline sau Wave 16A16)
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` v6 | Current rules |
| 2 | `pytest.ini` / `pyproject.toml` | Remove xdist config |
| 3 | `tests/test_wave16a09.py` | Mark slow |
| 4 | `tests/test_wave16a11.py` | Mark slow |
| 5 | `tests/test_wave16a13.py` | Mark slow |

---

# TASKS

---

## TASK 1 — Remove xdist + configure pytest defaults

**Step 1: Uninstall**
```powershell
D:/GoBP/venv/Scripts/pip.exe uninstall pytest-xdist -y
```

**Step 2: Update pytest config** — xóa `-n auto`, thêm slow marker:

```ini
[pytest]
addopts = -m "not slow"
markers =
    slow: marks tests as slow (batch 100+ nodes, > 5s)
```

**Step 3: Remove từ requirements** — xóa `pytest-xdist` khỏi requirements file.

**Verify:**
```powershell
# Default fast suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: subset, < 1 min, no xdist warning

# Full suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -m "" -q --tb=no
# Expected: 626+ tests
```

**GoBP MCP:** session:start + session:end (dec:d004).

**Commit message:**
```
Wave 16A17 Task 1: remove pytest-xdist, add slow marker config

- Uninstall pytest-xdist (CPU too heavy)
- pytest default: -m "not slow" (fast suite)
- Full suite: pytest -m "" or --override-ini="addopts="
- markers: slow defined
```

---

## TASK 2 — Mark slow tests

**Rule:** Mark `@pytest.mark.slow` khi test:
- Tạo > 50 nodes
- Chạy > 5s trên SSD
- Benchmark / perf tests

**Scan và mark:**

`tests/test_wave16a09.py`:
```python
@pytest.mark.slow
def test_batch_creates_nodes(proj): ...

@pytest.mark.slow
def test_batch_no_limit_300_ops(proj): ...
```

`tests/test_wave16a11.py`:
```python
@pytest.mark.slow
def test_batch_100_creates_under_10s(proj): ...

@pytest.mark.slow
def test_batch_limit_500(proj): ...
```

`tests/test_wave16a13.py`:
```python
# Mark any test creating 100+ ops
@pytest.mark.slow
def test_large_batch(proj): ...
```

Scan tất cả `tests/test_wave16a*.py` — mark bất kỳ test nào tạo 100+ nodes.

**Verify:**
```powershell
# Fast suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: < 1 min

# Count slow tests
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -m slow --collect-only -q
# Expected: danh sách slow tests
```

**Commit message:**
```
Wave 16A17 Task 2: @pytest.mark.slow on batch heavy tests

- Marked tests creating 100+ nodes or running > 5s
- Fast suite excludes slow tests by default
```

---

## TASK 3 — Update .cursorrules testing strategy + full suite verify

**Goal:** Cursor cập nhật .cursorrules R9 section để reflect testing strategy mới.

**CTO requirements:**
```
R9 phải nói rõ:
  A) Docs/data tasks: không pytest
  B) Code tasks: module tests only
  C) End of wave: pytest tests/ -m "" -q (full, không slow default)
  
Thêm note: KHÔNG dùng -n auto (CPU issue)
Thêm note: MIHOS data KHÔNG được dùng trong GoBP tests
```

Cursor tự viết phần R9, giữ phần còn lại của .cursorrules.
Báo cáo changes cho CEO.

**Full suite verify:**
```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -m "" -q --tb=no
# Expected: 626+ tests passing
```

**GoBP MCP:**
```
gobp(query="session:start actor='cursor' goal='Wave 16A17 Task 3 + end'")
# Cập nhật Lesson node liên quan nếu có (suggest: trước khi tạo mới)
gobp(query="session:end ...")
```

**CHANGELOG entry:**
```markdown
## [Wave 16A17] — Remove xdist + Test Organization — 2026-04-18

### Changed
- **pytest-xdist removed** — chiếm CPU quá lớn
- **Default suite** — `pytest tests/` = fast (skip slow)
- **Full suite** — `pytest tests/ -m ""` = tất cả tests
- **@pytest.mark.slow** — batch 100+ nodes tests
- **.cursorrules R9** — testing strategy cập nhật
```

**Commit message:**
```
Wave 16A17 Task 3: .cursorrules R9 update + CHANGELOG + full suite verify

- R9 updated: no -n auto, MIHOS data rule added
- Full suite: 626+ tests passing
- CHANGELOG: Wave 16A17 entry
```

---

# CEO DISPATCH

## Cursor
```
Read .cursorrules v6 + waves/wave_16a17_brief.md.

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute 3 tasks.
R9-B for Tasks 1-2, R9-C for Task 3.
Full suite: pytest tests/ -m "" (không dùng -n auto).

NHỚ:
- MIHOS data KHÔNG được dùng trong GoBP tests
- Lesson node: suggest: trước khi tạo mới (dec:d011)
```

## Claude CLI
```
Audit Wave 16A17.
Task 1: xdist removed, config correct
Task 2: slow markers on batch heavy tests
Task 3: .cursorrules R9 updated, 626+ tests passing

GoBP MCP session capture (dec:d004). Không cần Lesson node.
```

## Push
```powershell
cd D:\GoBP
git add waves/wave_16a17_brief.md
git commit -m "Add Wave 16A17 Brief — remove xdist + slow markers + test strategy"
git push origin main
```

---

*Wave 16A17 Brief v1.0 — 2026-04-18*
*References: dec:d004*

◈
