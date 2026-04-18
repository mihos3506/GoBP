# WAVE 16A16 BRIEF — TEST PERFORMANCE + GRAPH HYGIENE + HOOKS

**Wave:** 16A16
**Title:** pytest-xdist, slow markers, graph hygiene enforcement, hooks layer
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-18
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 6 tasks
**Estimated effort:** 4-5 hours

---

## REFERENCED GOBP NODES

| Node ID | Topic | Summary |
|---|---|---|
| `dec:d004` | `gobp.update.obligation` | Agents PHẢI cập nhật GoBP MCP |
| `dec:d006` | `brief.graph.linkage` | Brief reference nodes |
| `dec:d011` | `graph.hygiene.lessons` | Update over create cho Lessons |

**NEW NODES sẽ tạo:**
- Wave: `Wave 16A16` (type=Wave)

---

## CONTEXT

**P1 — pytest quá chậm (853s = ~14 phút):**
```
626 tests, full suite mỗi wave cuối = 14 phút
Root cause: tests/test_wave16a11.py batch 500 ops tests
           tests/test_wave16a09.py batch operations
           tmp_path I/O mỗi test

Target: < 3 phút với parallel execution
```

**P2 — Graph hygiene chưa có enforcement:**
```
dec:d011 mới lock: Lessons = update over create
Cursor + CLI chưa biết rule này
Cần thêm vào .cursorrules + CLAUDE.md
```

**P3 — Hooks layer chưa có:**
```
before_write: validate schema trước khi ghi
after_batch: auto-recompute priorities
on_error: actionable suggestion
→ AI phát hiện lỗi sớm nhất có thể
→ Lean error prevention
```

---

## CURSOR EXECUTION RULES

R1-R12 standard (xem .cursorrules v6).

**Testing cho wave này:**
- Tasks 1-2 (pytest config): chạy module tests để verify
- Tasks 3-4 (graph hygiene docs): R9-A (docs only, không pytest)
- Tasks 5-6 (hooks): R9-B (module tests only)
- Task 6 cuối: R9-C full suite — target < 3 phút với `-n auto`

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
pip install pytest-xdist
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 626 tests
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` v6 | Current rules |
| 2 | `gobp/mcp/server.py` | Hooks integration point |
| 3 | `gobp/mcp/tools/write.py` | before_write hook |
| 4 | `gobp/mcp/dispatcher.py` | Hook orchestration |
| 5 | GoBP MCP `dec:d011` | graph.hygiene.lessons rule |

---

# TASKS

---

## TASK 1 — pytest-xdist + slow markers

**Goal:** Parallel test execution + mark slow tests.

**File to modify:** `pyproject.toml` hoặc `pytest.ini` hoặc `setup.cfg`:

```ini
[tool.pytest.ini_options]
addopts = "-n auto"
markers = [
    "slow: marks tests as slow (deselect with '-m not slow')",
]
```

**File to modify:** `requirements-dev.txt` hoặc `pyproject.toml`:
```
pytest-xdist>=3.0
```

Install:
```powershell
D:/GoBP/venv/Scripts/pip.exe install pytest-xdist
```

**Mark slow tests** — các tests tạo 100+ nodes hoặc chạy > 5s:
```python
@pytest.mark.slow
def test_batch_500_creates_under_120s(proj):
    ...

@pytest.mark.slow  
def test_batch_no_limit_600_ops(proj):
    ...
```

Scan `tests/test_wave16a09.py`, `tests/test_wave16a11.py`, `tests/test_wave16a13.py` — mark slow tests.

**Verify:**
```powershell
# Fast only (< 1 phút)
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -m "not slow" -q --tb=no

# Full parallel
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -n auto -q --tb=no
```

**GoBP MCP update:**
```
gobp(query="session:start actor='cursor' goal='Wave 16A16 Task 1: pytest-xdist'")
# Record task completion
gobp(query="session:end ...")
```

**Commit message:**
```
Wave 16A16 Task 1: pytest-xdist + slow markers

- pytest-xdist installed, -n auto in pytest config
- @pytest.mark.slow on batch heavy tests (100+ nodes)
- Fast suite: pytest -m "not slow" < 1 min
- Full parallel: pytest -n auto target < 3 min
```

---

## TASK 2 — Verify parallel test stability

**Goal:** Ensure tests pass reliably with parallel execution.

Fix any test isolation issues (shared state, file conflicts) discovered in Task 1.

Common issues with xdist:
```python
# Bad: shared global state
_cache = {}

# Good: fixture-scoped
@pytest.fixture
def cache():
    return {}
```

**Verify:**
```powershell
# Run 3 times, all must pass
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -n auto -q --tb=short
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -n auto -q --tb=short
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -n auto -q --tb=short
```

**Commit message:**
```
Wave 16A16 Task 2: fix test isolation for parallel execution

- Fix shared state issues discovered with -n auto
- All 626 tests pass reliably in parallel
```

---

## TASK 3 — Graph hygiene rule trong .cursorrules

**Goal:** Cursor cập nhật .cursorrules với dec:d011.

**CTO requirements:**
```
Thêm vào .cursorrules (Cursor tự viết phần này):
  Rule dec:d011 — Lessons update over create:
    Trước khi tạo Lesson node mới:
      suggest: <topic> → tìm node cùng topic
      Nếu có → update: node đó, thêm bài học mới, giữ nội dung còn giá trị
      Chỉ tạo mới khi topic hoàn toàn mới
    CHỈ áp dụng cho Lesson nodes — không áp dụng cho project nodes

KHÔNG xóa rules hiện tại, chỉ thêm.
Báo cáo changes cho CEO.
```

**R9-A:** Không cần pytest. Verify: `.cursorrules` cập nhật đúng.

**GoBP MCP:** Update Lesson node liên quan nếu có (dec:d011 reference).

**Commit message:**
```
Wave 16A16 Task 3: .cursorrules — add dec:d011 graph hygiene rule

- Lessons learned = update existing node over create new
- suggest: before create Lesson
- Only for AI self-learning nodes, not project nodes
```

---

## TASK 4 — Graph hygiene rule trong CLAUDE.md

**Đây là task cho Claude CLI dispatch riêng.**

**CTO requirements cho Claude CLI:**
```
Thêm vào CLAUDE.md Lessons Learned section:
  dec:d011 rule — update Lesson nodes over create new
  suggest: before creating Lesson nodes
  Giữ nội dung còn giá trị trong node cũ

KHÔNG xóa lessons hiện tại trong CLAUDE.md
Báo cáo changes cho CEO
```

**Commit message (Claude CLI):**
```
Wave 16A16 Task 4: CLAUDE.md — add dec:d011 graph hygiene rule
```

---

## TASK 5 — Hooks layer: before_write + on_error

**Goal:** Pre-write validation + actionable error suggestions.

**File to create:** `gobp/mcp/hooks.py`

```python
"""MCP hook layer — pre/post action callbacks."""

from __future__ import annotations
from typing import Any
from pathlib import Path


# WRITE_ACTIONS that trigger before_write hook
WRITE_ACTIONS = {
    "create", "upsert", "lock", "batch", "quick",
    "delete", "retype", "merge", "edge", "import",
}


def before_write(action: str, params: dict, index: Any) -> dict | None:
    """Pre-write validation hook.
    
    Returns None if OK, or {ok: False, error: str, suggestion: str} to block.
    """
    # 1. Schema check for create/upsert
    if action in ("create", "upsert"):
        node_type = params.get("type") or _extract_type_from_query(params.get("query", ""))
        name = params.get("name", "")
        
        if node_type and not _type_exists_in_schema(node_type, index):
            return {
                "ok": False,
                "error": f"Unknown node type: {node_type}",
                "suggestion": f"Valid types: {', '.join(_get_valid_types(index))}",
            }
    
    # 2. Session required for writes
    session_id = params.get("session_id", "")
    if action in ("create", "upsert", "lock", "delete") and not session_id:
        return {
            "ok": False,
            "error": "session_id required for write operations",
            "suggestion": "gobp(query=\"session:start actor='...' goal='...'\") first",
        }
    
    return None


def on_error(action: str, error: str, params: dict, index: Any) -> dict:
    """Enrich error with actionable suggestion.
    
    Called when an action fails. Returns enriched error response.
    """
    suggestion = _suggest_fix(action, error, params, index)
    
    result = {"ok": False, "error": error}
    if suggestion:
        result["suggestion"] = suggestion
    return result


def _suggest_fix(action: str, error: str, params: dict, index: Any) -> str:
    """Generate actionable fix suggestion from error."""
    from gobp.core.search import normalize_text, search_nodes
    
    # Node not found → suggest similar
    if "not found" in error.lower():
        name = params.get("name", "") or params.get("id", "")
        if name and index:
            similar = search_nodes(index, name, exclude_types=["Session"], limit=3)
            if similar:
                names = [n.get("name", "") for _, n in similar]
                return f"Similar nodes: {', '.join(names)}"
    
    # Wrong type → suggest valid types
    if "unknown type" in error.lower() or "invalid type" in error.lower():
        if index:
            return f"Valid types: {', '.join(_get_valid_types(index))}"
    
    # Missing session
    if "session" in error.lower():
        return "gobp(query=\"session:start actor='cursor' goal='...'\")"
    
    return ""


def _type_exists_in_schema(node_type: str, index: Any) -> bool:
    """Check if node type exists in schema."""
    try:
        schema = index._nodes_schema
        return node_type in schema.get("node_types", {})
    except Exception:
        return True  # Don't block if can't check


def _get_valid_types(index: Any) -> list[str]:
    """Get valid node types from schema."""
    try:
        schema = index._nodes_schema
        return sorted(schema.get("node_types", {}).keys())
    except Exception:
        return []


def _extract_type_from_query(query: str) -> str:
    """Extract type from 'create:Type' format."""
    if ":" in query:
        parts = query.split(":", 1)
        if len(parts) > 1:
            return parts[1].split()[0].strip() if parts[1].strip() else ""
    return ""
```

**File to modify:** `gobp/mcp/server.py`

Integrate hooks in `call_tool()`:

```python
from gobp.mcp.hooks import before_write, on_error, WRITE_ACTIONS

# In call_tool():
action = _extract_action(query)

if action in WRITE_ACTIONS:
    # Pre-write validation
    block = before_write(action, params, index)
    if block:
        return [types.TextContent(
            type="text",
            text=json.dumps(block, ensure_ascii=False)
        )]

try:
    result = await dispatch(query, index, project_root)
except Exception as e:
    result = on_error(action, str(e), params, index)
```

**Commit message:**
```
Wave 16A16 Task 5: hooks layer — before_write + on_error

- hooks.py: before_write() pre-validates type + session_id
- on_error(): enriches errors with actionable suggestions
- "Node not found" → suggests similar nodes
- "Unknown type" → lists valid types
- "Missing session" → shows session:start example
```

---

## TASK 6 — Tests + CHANGELOG + full suite

**File to create:** `tests/test_wave16a16.py`

```python
"""Tests for Wave 16A16: pytest config, hooks."""

# pytest config tests (2):
#   slow_marker_registered, xdist_installed

# Hook tests (5):
#   before_write_blocks_unknown_type
#   before_write_blocks_missing_session
#   before_write_passes_valid_create
#   on_error_suggests_similar_node
#   on_error_suggests_valid_types

# Total: ~7 tests
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A16] — Test Performance + Graph Hygiene + Hooks — 2026-04-18

### Changed
- **pytest-xdist** — parallel execution (-n auto)
  - Full suite: ~14 min → ~3 min target
  - @pytest.mark.slow on batch heavy tests
  - Fast dev suite: pytest -m "not slow" < 1 min

- **.cursorrules** — dec:d011 graph hygiene rule added
  - Lessons learned = update existing node over create new
  - suggest: before creating Lesson nodes

- **CLAUDE.md** — dec:d011 rule added (Claude CLI task)

### Added
- **Hooks layer** — gobp/mcp/hooks.py
  - before_write(): type validation + session check
  - on_error(): actionable error suggestions
  - "Node not found" → similar node suggestions
  - AI detects errors at earliest possible stage

### Total: 633+ tests
```

**Run full suite với xdist:**
```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -n auto -q --tb=no
# Target: < 3 minutes, 633+ tests
```

**Commit message:**
```
Wave 16A16 Task 6: tests + CHANGELOG — 633+ tests, parallel < 3 min
```

---

# CEO DISPATCH

## Cursor (Tasks 1-3, 5-6)
```
Read .cursorrules v6, waves/wave_16a16_brief.md.
Read GoBP MCP: gobp(query="find:Decision mode=summary")
  Focus: dec:d004, dec:d011

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
pip install pytest-xdist

Execute Tasks 1-3, 5-6. Skip Task 4 (Claude CLI).
Testing: R9-A for docs tasks, R9-B for code tasks.
Task 6: R9-C full suite với -n auto, target < 3 min.

REMEMBER dec:d011: trước khi tạo Lesson node mới
  → suggest: tìm node cùng topic
  → Nếu có → update: existing node
  → Giữ lại nội dung còn giá trị
```

## Claude CLI (Task 4)
```
Read CLAUDE.md + dec:d011 từ GoBP MCP.
Update CLAUDE.md Lessons section với dec:d011 rule.
Giữ lại lessons cũ còn giá trị.
Commit: "Wave 16A16 Task 4: CLAUDE.md — add dec:d011 graph hygiene rule"
GoBP MCP session capture.
```

## Push
```powershell
cd D:\GoBP
git add waves/wave_16a16_brief.md
git commit -m "Add Wave 16A16 Brief — test performance + graph hygiene + hooks"
git push origin main
```

---

*Wave 16A16 Brief v1.0 — 2026-04-18*
*References: dec:d004, dec:d006, dec:d011*

◈
