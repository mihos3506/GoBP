# WAVE 16A13 BRIEF — BATCH FIXES + QUICK CAPTURE + AUTO CHUNKING

**Wave:** 16A13
**Title:** Fix batch \n parsing, auto-fill defaults, quick capture format, auto chunking
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-18
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 6 tasks
**Estimated effort:** 4-5 hours

---

## CONTEXT

CTO session ghi 10 ideas vào GoBP — gặp friction thực tế:

**P1 — batch \n bị escape**
```
Current:  MCP truyền \n literal → batch_parser thấy 1 dòng dài
          → Chỉ parse 1 op thay vì 10
Fix:      Nhận cả literal \n và real newline
```

**P2 — Idea type reject quick capture**
```
Current:  create:Idea → cần raw_quote, interpretation, subject, maturity, confidence
          → 5 required fields chỉ để ghi 1 ý tưởng nhanh → reject
Fix:      Auto-fill defaults cho fields thiếu
          → Chỉ cần name + description → GoBP điền phần còn lại
```

**P3 — Không có quick capture format**
```
Current:  Mỗi node cần "create: Type: Name | Description"
          → Verbose, tốn tokens
Fix:      1 dòng = 1 node: "Name | category | wave | description"
          → GoBP auto-detect type, auto-fill fields
```

**P4 — Batch limit 500 ops — AI phải tự chia**
```
Current:  AI gửi 1000 ops → reject "Max 500"
          → AI phải biết limit → tự chia → extra logic
Fix:      GoBP nhận bất kỳ số ops → tự chunk internal
          → AI không biết limit, không cần biết
          → 1 response tổng hợp
```

---

## DESIGN

### 1. Fix batch \n parsing

```python
# In batch_parser.py, parse_batch():

def parse_batch(raw: str) -> list[dict]:
    # Handle both literal \n and real newlines
    raw = raw.replace("\\n", "\n")
    
    # ... existing parse logic ...
```

### 2. Auto-fill defaults for all node types

```python
# In write.py, _batch_create():

# Schema defaults per type
TYPE_DEFAULTS = {
    "Idea": {
        "raw_quote": lambda op: op.get("description", ""),
        "interpretation": lambda op: op.get("description", ""),
        "subject": lambda op: _extract_subject(op.get("name", "")),
        "maturity": "raw",
        "confidence": "low",
    },
    "TestCase": {
        "given": "",
        "when": "",
        "then": "",
        "expected_result": "PASS",
    },
    # Other types: name + description sufficient
}

def _auto_fill(op: dict) -> dict:
    """Fill missing required fields with smart defaults."""
    node_type = op.get("type", "Node")
    defaults = TYPE_DEFAULTS.get(node_type, {})
    
    for field, default in defaults.items():
        if field not in op or not op[field]:
            if callable(default):
                op[field] = default(op)
            else:
                op[field] = default
    
    return op
```

### 3. Quick capture format

Thêm prefix `quick:` vào batch — format tối giản:

```
gobp(query="quick: session_id='x'
  Inverted Index for Search | performance | wave17 | O(N) to O(1) find
  Adjacency List Index | performance | wave17 | O(E) to O(1) related
  MCP Auth Token | security | wave17 | reject unauthorized
  File-based Write Lock | concurrent | wave17 | 1 writer at a time
")
```

**Parse rule:** `Name | category | target_wave | description`

```python
def _parse_quick_line(line: str) -> dict:
    """Parse quick capture format: Name | category | wave | description"""
    parts = [p.strip() for p in line.split("|")]
    
    result = {"op": "create", "type": "Node"}
    
    if len(parts) >= 1:
        result["name"] = parts[0]
    if len(parts) >= 2:
        result["category"] = parts[1]
    if len(parts) >= 3:
        result["target_wave"] = parts[2]
    if len(parts) >= 4:
        result["description"] = parts[3]
    elif len(parts) >= 2:
        # Last part is always description if no explicit field
        result["description"] = parts[-1]
    
    return result
```

**Response compact:**
```json
{
  "ok": true,
  "summary": "4 created, 0 skipped",
  "ids": ["inverted_index.meta.001", "adjacency.meta.002", ...]
}
```

### 4. Auto batch chunking — no external limit

```python
# In write.py, batch_action():

# Remove hard reject
# OLD: if len(ops) > 500: return error

# NEW: auto chunk
CHUNK_SIZE = 200  # internal chunk size for memory efficiency

async def batch_action(index, project_root, args):
    ops = parse_batch(ops_raw)
    
    # No limit check — process all ops
    all_results = {
        "succeeded": 0, "skipped": [], "errors": [], "warnings": []
    }
    
    # Chunk internally for memory management
    for chunk_start in range(0, len(ops), CHUNK_SIZE):
        chunk = ops[chunk_start:chunk_start + CHUNK_SIZE]
        
        working_index = GraphIndex.load_from_disk(project_root)
        
        for op in chunk:
            result = await _execute_op_in_memory(op, working_index, ...)
            # ... collect results ...
        
        # Save chunk
        working_index.save_new_nodes_to_disk(project_root)
        working_index.save_new_edges_to_disk(project_root)
    
    # Update cache with final state
    final_index = GraphIndex.load_from_disk(project_root)
    update_cache(final_index)
    
    return all_results
```

**Externally:** AI gửi bao nhiêu ops cũng được.
**Internally:** GoBP chunk 200 ops, save mỗi chunk, tổng hợp response.

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 588 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 588 tests
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/mcp/batch_parser.py` | Fix \n + add quick format |
| 3 | `gobp/mcp/tools/write.py` | Auto-fill + auto chunk + quick action |
| 4 | `gobp/mcp/dispatcher.py` | Route quick: action |
| 5 | `gobp/mcp/parser.py` | PROTOCOL_GUIDE |
| 6 | `gobp/schema/core_nodes.yaml` | Required fields per type |

---

# TASKS

## TASK 1 — Fix batch \n parsing

**File to modify:** `gobp/mcp/batch_parser.py`

**Re-read parse_batch() in full.**

Add at start of `parse_batch()`:
```python
# Handle literal \n from MCP transport
raw = raw.replace("\\n", "\n")
```

Also handle `\\\\n` (double-escaped):
```python
raw = raw.replace("\\\\n", "\n").replace("\\n", "\n")
```

**Test:**
```python
def test_batch_parse_literal_newline():
    ops = parse_batch("create: Engine: A | Desc A\\ncreate: Engine: B | Desc B")
    assert len(ops) == 2
    assert ops[0]["name"] == "A"
    assert ops[1]["name"] == "B"

def test_batch_parse_real_newline():
    ops = parse_batch("create: Engine: A | Desc A\ncreate: Engine: B | Desc B")
    assert len(ops) == 2
```

**Commit message:**
```
Wave 16A13 Task 1: fix batch \n parsing — handle literal and real newlines

- parse_batch: replace literal \\n with real newline before parsing
- Handle double-escaped \\\\n
- batch now parses multi-op strings from MCP transport correctly
```

---

## TASK 2 — Auto-fill defaults for required fields

**File to modify:** `gobp/mcp/tools/write.py`

Add `_auto_fill_defaults()` function:

```python
TYPE_DEFAULTS = {
    "Idea": {
        "raw_quote": lambda op: op.get("description", "captured via quick entry"),
        "interpretation": lambda op: op.get("description", ""),
        "subject": lambda op: op.get("category", "general"),
        "maturity": "raw",
        "confidence": "low",
    },
    "TestCase": {
        "given": "TBD",
        "when": "TBD",
        "then": "TBD",
        "expected_result": "PASS",
    },
}

def _auto_fill_defaults(node_data: dict, node_type: str) -> dict:
    """Fill missing required fields with smart defaults.
    Allows quick capture without rejection.
    """
    defaults = TYPE_DEFAULTS.get(node_type, {})
    for field, default in defaults.items():
        if field not in node_data or not node_data[field]:
            node_data[field] = default(node_data) if callable(default) else default
    return node_data
```

Call `_auto_fill_defaults()` in `_batch_create()` before dispatch/validation.

Also apply in single `create:` action path.

**Commit message:**
```
Wave 16A13 Task 2: auto-fill defaults for required fields

- TYPE_DEFAULTS: smart defaults per type (Idea, TestCase)
- _auto_fill_defaults(): fills missing required fields
- create:Idea name='X' description='Y' → no rejection
- Applied in batch_create and single create paths
```

---

## TASK 3 — Quick capture format

**File to modify:** `gobp/mcp/batch_parser.py`

Add `parse_quick()`:

```python
def parse_quick(raw: str) -> list[dict]:
    """Parse quick capture format.
    
    Format: Name | category | target_wave | description
    Minimum: Name | description
    
    Example:
      Inverted Index | performance | wave17 | O(N) to O(1) find
      MCP Auth Token | security | wave17 | reject unauthorized
    """
    raw = raw.replace("\\n", "\n")
    ops = []
    
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        
        parts = [p.strip() for p in line.split("|")]
        if not parts or not parts[0]:
            continue
        
        op = {"op": "create", "type": "Node", "name": parts[0]}
        
        if len(parts) == 2:
            op["description"] = parts[1]
        elif len(parts) == 3:
            op["category"] = parts[1]
            op["description"] = parts[2]
        elif len(parts) >= 4:
            op["category"] = parts[1]
            op["target_wave"] = parts[2]
            op["description"] = parts[3]
        
        ops.append(op)
    
    return ops
```

**File to modify:** `gobp/mcp/tools/write.py`

Add `quick_action()`:

```python
async def quick_action(index, project_root, args):
    """Quick capture: multiple nodes with minimal format.
    
    Query: quick: session_id='x' ops='Name | cat | wave | desc'
    """
    session_id = args.get("session_id", "")
    if not session_id:
        return {"ok": False, "error": "session_id required"}
    
    ops_raw = args.get("ops", "") or args.get("query", "")
    
    from gobp.mcp.batch_parser import parse_quick
    ops = parse_quick(ops_raw)
    
    if not ops:
        return {"ok": False, "error": "No items parsed",
                "hint": "Format: Name | category | wave | description"}
    
    # Convert to batch ops and execute
    # ... reuse batch_action internals ...
```

**File to modify:** `gobp/mcp/dispatcher.py`

Add routing:
```python
        elif action == "quick":
            result = await tools_write.quick_action(index, project_root, params)
```

**Update PROTOCOL_GUIDE:**
```python
"quick: session_id='x' ops='Idea Name | category | wave | description'":
    "Quick capture: 1 line = 1 node, auto-fill all fields",
```

**Commit message:**
```
Wave 16A13 Task 3: quick: action — minimal format capture

- parse_quick(): Name | category | wave | description
- quick_action(): auto-creates Node type with defaults
- 10 ideas = 1 call, ~300 tokens vs 10 calls ~5000 tokens
- PROTOCOL_GUIDE updated
```

---

## TASK 4 — Auto batch chunking — remove external limit

**File to modify:** `gobp/mcp/tools/write.py`

Refactor `batch_action()`:

```python
INTERNAL_CHUNK_SIZE = 200

async def batch_action(index, project_root, args):
    # ... parse + validate session ...
    
    ops = parse_batch(ops_raw)
    
    # NO LIMIT CHECK — accept any number of ops
    # Old: if len(ops) > 500: return error
    
    if not ops:
        return {"ok": False, "error": "No operations parsed"}
    
    all_succeeded = []
    all_skipped = []
    all_errors = []
    all_warnings = []
    
    # Internal chunking for memory management
    for chunk_start in range(0, len(ops), INTERNAL_CHUNK_SIZE):
        chunk = ops[chunk_start:chunk_start + INTERNAL_CHUNK_SIZE]
        
        # Load fresh index per chunk
        working_index = GraphIndex.load_from_disk(project_root)
        name_to_id = _build_name_map(working_index)
        
        for op in chunk:
            result = await _execute_op_in_memory(
                op, working_index, project_root, session_id, name_to_id
            )
            # ... collect into all_succeeded/skipped/errors/warnings ...
        
        # Save this chunk
        working_index.save_new_nodes_to_disk(project_root)
        working_index.save_new_edges_to_disk(project_root)
    
    # Update cache with final state
    try:
        from gobp.mcp.server import update_cache
        final_index = GraphIndex.load_from_disk(project_root)
        update_cache(final_index)
    except ImportError:
        pass
    
    # Build summary
    return {
        "ok": len(all_errors) == 0,
        "summary": _build_summary(all_succeeded, all_skipped, all_errors),
        "total_ops": len(ops),
        "succeeded": len(all_succeeded),
        "skipped": all_skipped,
        "errors": all_errors,
        "warnings": all_warnings,
    }
```

Also update `quick_action()` to use same chunking.

Remove `MAX_BATCH_OPS` constant or set it to a very large number.

**Update PROTOCOL_GUIDE:** remove "Max 50/500 ops" references.

**Update QUERY_RULES:** remove limit mention, add "GoBP auto-chunks internally".

**Commit message:**
```
Wave 16A13 Task 4: auto batch chunking — no external limit

- Remove MAX_BATCH_OPS limit
- Internal chunking at 200 ops per chunk
- AI sends any number of ops → GoBP handles internally
- Load/save per chunk for memory efficiency
- Cache updated with final state after all chunks
```

---

## TASK 5 — Smoke test

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio, tempfile, shutil
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch

async def test():
    tmp = Path(tempfile.mkdtemp())
    try:
        init_project(tmp)
        index = GraphIndex.load_from_disk(tmp)
        
        sess = await dispatch('session:start actor=test goal=smoke-16a13', index, tmp)
        sid = sess['session_id']
        
        # Test 1: batch with literal \\n
        index = GraphIndex.load_from_disk(tmp)
        r = await dispatch(
            f\"batch session_id='{sid}' ops='create: Engine: EngA | Engine A\\\\ncreate: Engine: EngB | Engine B'\",
            index, tmp
        )
        print(f'batch \\\\n: succeeded={r.get(\"succeeded\", 0)}')
        assert r.get('succeeded', 0) >= 2, f'batch \\\\n failed: {r}'
        
        # Test 2: quick capture
        index = GraphIndex.load_from_disk(tmp)
        r = await dispatch(
            f\"quick: session_id='{sid}' ops='Idea Alpha | perf | wave17 | fast search\\\\nIdea Beta | security | wave18 | auth token'\",
            index, tmp
        )
        print(f'quick: succeeded={r.get(\"succeeded\", 0)}')
        assert r.get('succeeded', 0) >= 2
        
        # Test 3: large batch (300 ops, no limit)
        lines = [f'create: Node: LargeNode{i} | Node number {i}' for i in range(300)]
        ops_str = '\\\\n'.join(lines)
        index = GraphIndex.load_from_disk(tmp)
        r = await dispatch(
            f\"batch session_id='{sid}' ops='{ops_str}'\",
            index, tmp
        )
        print(f'large batch 300: succeeded={r.get(\"succeeded\", 0)}')
        assert r.get('succeeded', 0) >= 250  # some may dedupe
        
        # Verify nodes exist
        index = GraphIndex.load_from_disk(tmp)
        total = len(index.all_nodes())
        print(f'total nodes after all: {total}')
        
        print('ALL SMOKE TESTS PASSED')
    finally:
        shutil.rmtree(tmp)

asyncio.run(test())
"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

**Commit message:**
```
Wave 16A13 Task 5: smoke test — batch \\n + quick + large batch

- batch literal \\n: 2 ops parsed correctly
- quick: 2 nodes from minimal format
- large batch 300: no limit, auto chunked
- All tests passing
```

---

## TASK 6 — Tests + CHANGELOG

**File to create:** `tests/test_wave16a13.py`

```python
"""Tests for Wave 16A13: batch fixes, quick capture, auto chunking."""

# Batch \n tests (3):
#   parse_literal_newline, parse_real_newline, parse_double_escaped

# Auto-fill tests (3):
#   idea_auto_fill_defaults, testcase_auto_fill, node_no_fill_needed

# Quick capture tests (4):
#   quick_parse_4_fields, quick_parse_2_fields, quick_parse_3_fields
#   quick_action_creates_nodes

# Auto chunking tests (3):
#   batch_no_limit_300_ops, batch_no_limit_600_ops
#   batch_chunking_saves_per_chunk

# Integration (2):
#   quick_then_explore, batch_newline_then_edges

# PROTOCOL_GUIDE (1):
#   no_max_ops_in_guide_or_unlimited

# Total: ~16 tests
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A13] — Batch Fixes + Quick Capture + Auto Chunking — 2026-04-18

### Fixed
- **batch \n parsing** — handle literal \\n from MCP transport
  - Both literal \\n and real newlines parsed correctly
  - Double-escaped \\\\n also handled

### Added
- **Auto-fill defaults** for required fields
  - create:Idea with just name + description → no rejection
  - TYPE_DEFAULTS: smart defaults per type (Idea, TestCase)

- **quick: action** — minimal format capture
  - Format: Name | category | wave | description
  - 1 call = N nodes, auto-fill all fields
  - 10 ideas = 1 call, ~300 tokens (was 10 calls, ~5000 tokens)

### Changed
- **batch: no external limit** — auto internal chunking
  - AI sends any number of ops → GoBP chunks at 200 internally
  - No more "Max 500 ops" error
  - QUERY_RULES updated: no limit mention

### Impact
- 16x token reduction for idea capture
- Zero rejections for quick entries
- AI doesn't need to know or manage batch limits

### Total: 604+ tests
```

**Commit message:**
```
Wave 16A13 Task 6: tests/test_wave16a13.py + CHANGELOG

- 16 tests: \n parsing, auto-fill, quick capture, auto chunking
- 604+ tests passing
- CHANGELOG: Wave 16A13 entry
```

---

# CEO DISPATCH

## Cursor
```
Read .cursorrules and waves/wave_16a13_brief.md.
Read gobp/mcp/batch_parser.py, gobp/mcp/tools/write.py,
gobp/mcp/dispatcher.py, gobp/mcp/parser.py.
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute 6 tasks. R9: 588 tests baseline. 1 task = 1 commit.
```

## Claude CLI audit
```
Audit Wave 16A13.
Task 1: batch_parser handles literal \\n and real newlines
Task 2: _auto_fill_defaults for Idea/TestCase, no rejection on quick entry
Task 3: quick: action — parse_quick() + quick_action() + PROTOCOL_GUIDE
Task 4: batch no external limit, INTERNAL_CHUNK_SIZE=200, auto chunk
Task 5: Smoke: batch \\n + quick + 300 ops no limit
Task 6: test_wave16a13.py 16 tests, 604+ total, CHANGELOG
BLOCKING: Gặp vấn đề → DỪNG, báo CEO.
Expected: 604+ tests.
```

---

*Wave 16A13 Brief v1.0 — 2026-04-18*

◈
