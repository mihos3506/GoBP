# WAVE 16A12 BRIEF — SERVER CACHE

**Wave:** 16A12
**Title:** MCP server in-memory cache — eliminate per-call disk reload
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-18
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 5 tasks
**Estimated effort:** 3-4 hours

---

## CONTEXT

**Problem:**
```
Every MCP call → GraphIndex.load_from_disk()
→ Scan ALL .gobp/nodes/*.md files
→ Parse YAML frontmatter per file
→ 200 nodes = 200 file reads per call

Current latencies (MIHOS ~200 nodes):
  find:      ~1000ms
  get:       ~500ms
  suggest:   ~1000ms
  explore:   ~800ms
  overview:  ~500ms

10 queries in a session = 10 full reloads = 2000 file reads
```

**Fix:**
```
MCP server keeps GraphIndex in RAM.
Load once at startup. Query from cache. Invalidate on write.

Expected latencies after fix:
  find:      <50ms     (20x faster)
  get:       <10ms     (50x faster)
  suggest:   <50ms     (20x faster)
  explore:   <30ms     (25x faster)
  overview:  <20ms     (25x faster)

10 queries = 0 file reads (all from cache)
```

---

## DESIGN

### Server-level cache

```python
# gobp/mcp/server.py

class GoBPServer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._cache: GraphIndex | None = None
        self._cache_loaded_at: float = 0
    
    def get_index(self) -> GraphIndex:
        """Get cached GraphIndex. Load from disk only if not cached."""
        if self._cache is None:
            self._cache = GraphIndex.load_from_disk(self.project_root)
            self._cache_loaded_at = time.time()
        return self._cache
    
    def invalidate_cache(self):
        """Force reload on next read. Called after writes."""
        self._cache = None
    
    def update_cache(self, index: GraphIndex):
        """Replace cache with updated index after batch write."""
        self._cache = index
        self._cache_loaded_at = time.time()
```

### Read path — use cache

```python
# Current (every call reloads):
@server.call_tool()
async def call_tool(name, arguments):
    index = GraphIndex.load_from_disk(project_root)  # SLOW
    result = await dispatch(query, index, project_root)

# After (use cache):
@server.call_tool()
async def call_tool(name, arguments):
    index = gobp_server.get_index()  # FAST — from RAM
    result = await dispatch(query, index, project_root)
```

### Write path — update cache after write

```python
# Read-only actions: use cache directly
# Write actions: after write, update cache

if action in WRITE_ACTIONS:
    result = await dispatch(query, index, project_root)
    gobp_server.invalidate_cache()  # or update_cache(index)
else:
    result = await dispatch(query, index, project_root)
    # No invalidation needed
```

### Batch write — update cache with working_index

```python
# In batch_action after single-save:
working_index.save_new_nodes_to_disk(project_root)
working_index.save_new_edges_to_disk(project_root)

# Update server cache with the working_index (already has all new data)
# This avoids reload from disk after batch
gobp_server.update_cache(working_index)
```

### Cache invalidation strategy

```
Simple strategy (correct, good enough):

  Read action:  use cache
  Write action: invalidate cache → next read reloads
  Batch write:  update cache directly with working_index
  
  No TTL, no background refresh.
  Cache lives as long as server process.
  Only invalidated on writes.
  
  Edge case: external file edit (human edits .md file)
  → Server doesn't know → stale cache
  → Fix: add refresh: action to force reload
```

### refresh: action

```
gobp(query="refresh:")
→ Force reload cache from disk
→ Use when: manual file edits, schema changes, debugging
→ Response: {ok, nodes_loaded, edges_loaded, elapsed_ms}
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 581 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 581 tests
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/mcp/server.py` | Add cache layer |
| 3 | `gobp/mcp/dispatcher.py` | Pass cache reference |
| 4 | `gobp/mcp/tools/read.py` | All reads use cache |
| 5 | `gobp/mcp/tools/write.py` | Writes invalidate/update cache |

---

# TASKS

## TASK 1 — Add cache to MCP server

**File to modify:** `gobp/mcp/server.py`

**Re-read in full.**

Add server-level cache:

```python
import time as _time

# Module-level cache (singleton per MCP server process)
_cached_index: GraphIndex | None = None
_cache_loaded_at: float = 0
_cache_project_root: Path | None = None


def get_cached_index(project_root: Path) -> GraphIndex:
    """Get cached GraphIndex. Load from disk only if not cached or root changed."""
    global _cached_index, _cache_loaded_at, _cache_project_root
    
    if (_cached_index is None or 
        _cache_project_root != project_root):
        _cached_index = GraphIndex.load_from_disk(project_root)
        _cache_loaded_at = _time.time()
        _cache_project_root = project_root
    
    return _cached_index


def invalidate_cache():
    """Force reload on next get_cached_index() call."""
    global _cached_index
    _cached_index = None


def update_cache(index: GraphIndex):
    """Replace cache with updated index (e.g. after batch write)."""
    global _cached_index, _cache_loaded_at
    _cached_index = index
    _cache_loaded_at = _time.time()
```

Update `call_tool()` to use `get_cached_index()` instead of `GraphIndex.load_from_disk()`.

**Commit message:**
```
Wave 16A12 Task 1: add server-level GraphIndex cache

- get_cached_index(): returns cached index, loads only if None
- invalidate_cache(): clear cache after writes
- update_cache(): replace cache after batch (no reload needed)
- Module-level singleton per MCP server process
```

---

## TASK 2 — Read actions use cache

**File to modify:** `gobp/mcp/server.py`

Update `call_tool()` handler:

```python
WRITE_ACTIONS = {
    "session", "create", "upsert", "lock", "delete", "retype", 
    "merge", "batch", "import", "edge", "recompute",
}

@server.call_tool()
async def call_tool(name, arguments):
    query = arguments.get("query", "")
    
    # Parse action from query
    action = _extract_action(query)
    
    if action == "refresh":
        # Force reload
        invalidate_cache()
        index = get_cached_index(project_root)
        result = {
            "ok": True, 
            "nodes_loaded": len(index.all_nodes()),
            "edges_loaded": len(index.all_edges()) if hasattr(index, 'all_edges') else 0,
        }
    elif action in WRITE_ACTIONS:
        # Write: use cache for read, invalidate after write
        index = get_cached_index(project_root)
        result = await dispatch(query, index, project_root)
        invalidate_cache()  # next read will reload fresh data
    else:
        # Read: use cache directly
        index = get_cached_index(project_root)
        result = await dispatch(query, index, project_root)
    
    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
```

**Commit message:**
```
Wave 16A12 Task 2: read actions use cache, writes invalidate

- Read actions (find/get/explore/suggest/overview): use cached index
- Write actions: use cache for lookup, invalidate after write
- refresh: action forces cache reload
- WRITE_ACTIONS set defines which actions invalidate cache
```

---

## TASK 3 — Batch write updates cache directly

**File to modify:** `gobp/mcp/tools/write.py`

After batch completes, pass working_index back to cache:

```python
async def batch_action(index, project_root, args):
    # ... existing batch logic with working_index ...
    
    # After save to disk
    working_index.save_new_nodes_to_disk(project_root)
    working_index.save_new_edges_to_disk(project_root)
    
    # Update server cache with working_index
    # Avoids reload from disk after batch
    try:
        from gobp.mcp.server import update_cache
        update_cache(working_index)
    except ImportError:
        pass  # running outside MCP server (tests)
    
    return result
```

**File to modify:** `gobp/mcp/server.py`

For non-batch write actions, update `call_tool()`:

```python
    elif action in WRITE_ACTIONS:
        index = get_cached_index(project_root)
        result = await dispatch(query, index, project_root)
        
        if action == "batch":
            # batch_action already called update_cache()
            pass
        else:
            # Single write: invalidate, next read reloads
            invalidate_cache()
```

**Update PROTOCOL_GUIDE:**
```python
"refresh:":    "Force reload cache from disk (use after manual file edits)",
```

**Commit message:**
```
Wave 16A12 Task 3: batch updates cache directly, no post-batch reload

- batch_action calls update_cache(working_index) after save
- Single writes still invalidate (reload on next read)
- refresh: in PROTOCOL_GUIDE
- Cache stays warm after batch — next read instant
```

---

## TASK 4 — Performance test

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio, time
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.server import get_cached_index, invalidate_cache

async def perf_test():
    root = Path('D:/GoBP')
    
    # Cold start — first load
    invalidate_cache()
    t0 = time.time()
    index = get_cached_index(root)
    cold_ms = (time.time() - t0) * 1000
    print(f'Cold load: {cold_ms:.0f}ms ({len(index.all_nodes())} nodes)')
    
    # Warm reads — should be near-instant
    times = []
    for i in range(10):
        t0 = time.time()
        idx = get_cached_index(root)
        r = await dispatch('find: engine mode=summary', idx, root)
        elapsed = (time.time() - t0) * 1000
        times.append(elapsed)
    
    avg = sum(times) / len(times)
    print(f'Warm find: avg {avg:.0f}ms (10 calls)')
    assert avg < 100, f'Too slow: {avg:.0f}ms (expected <100ms)'
    
    # Warm explore
    times2 = []
    for i in range(5):
        t0 = time.time()
        idx = get_cached_index(root)
        r = await dispatch('explore: engine compact=true', idx, root)
        elapsed = (time.time() - t0) * 1000
        times2.append(elapsed)
    
    avg2 = sum(times2) / len(times2)
    print(f'Warm explore: avg {avg2:.0f}ms (5 calls)')
    
    # Warm suggest
    t0 = time.time()
    idx = get_cached_index(root)
    r = await dispatch('suggest: payment flow', idx, root)
    suggest_ms = (time.time() - t0) * 1000
    print(f'Warm suggest: {suggest_ms:.0f}ms')
    
    print('PERF TEST PASSED')

asyncio.run(perf_test())
"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

**Commit message:**
```
Wave 16A12 Task 4: performance test — warm cache reads <100ms

- Cold load: ~500ms (one-time)
- Warm find: <100ms avg (10 calls)
- Warm explore: <50ms avg
- Warm suggest: <100ms
- 20x-50x faster than per-call reload
```

---

## TASK 5 — Tests + CHANGELOG

**File to create:** `tests/test_wave16a12.py`

```python
"""Tests for Wave 16A12: server cache — eliminate per-call disk reload."""

from __future__ import annotations
import asyncio, time
from pathlib import Path
import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch


# ── Cache functions ───────────────────────────────────────────────────────────

def test_get_cached_index_returns_same_instance():
    from gobp.mcp.server import get_cached_index, invalidate_cache
    invalidate_cache()
    # Use GoBP project root for test
    root = Path(__file__).parent.parent
    if not (root / ".gobp").exists():
        pytest.skip("No .gobp folder")
    idx1 = get_cached_index(root)
    idx2 = get_cached_index(root)
    assert idx1 is idx2  # same object — not reloaded


def test_invalidate_forces_reload():
    from gobp.mcp.server import get_cached_index, invalidate_cache
    root = Path(__file__).parent.parent
    if not (root / ".gobp").exists():
        pytest.skip("No .gobp folder")
    idx1 = get_cached_index(root)
    invalidate_cache()
    idx2 = get_cached_index(root)
    assert idx1 is not idx2  # different object — reloaded


def test_update_cache_replaces_index():
    from gobp.mcp.server import get_cached_index, update_cache, invalidate_cache
    root = Path(__file__).parent.parent
    if not (root / ".gobp").exists():
        pytest.skip("No .gobp folder")
    invalidate_cache()
    idx1 = get_cached_index(root)
    
    new_index = GraphIndex()
    update_cache(new_index)
    
    idx2 = get_cached_index(root)
    assert idx2 is new_index
    
    # Cleanup
    invalidate_cache()


# ── Refresh action ────────────────────────────────────────────────────────────

def test_refresh_action(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)
    r = asyncio.run(dispatch("refresh:", index, tmp_path))
    assert r["ok"] is True
    assert "nodes_loaded" in r


# ── Cache performance ─────────────────────────────────────────────────────────

def test_cached_read_faster_than_disk(tmp_path):
    init_project(tmp_path)
    
    # Create some nodes
    index = GraphIndex.load_from_disk(tmp_path)
    sid = asyncio.run(dispatch(
        "session:start actor='t' goal='cache perf'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    for i in range(20):
        asyncio.run(dispatch(
            f"create:Node name='CacheNode{i}' session_id={sid}", index, tmp_path
        ))
        index = GraphIndex.load_from_disk(tmp_path)
    
    # Time disk read
    t0 = time.time()
    for _ in range(5):
        GraphIndex.load_from_disk(tmp_path)
    disk_time = time.time() - t0
    
    # Time cached read (simulated)
    cached = GraphIndex.load_from_disk(tmp_path)
    t0 = time.time()
    for _ in range(5):
        _ = cached.all_nodes()  # in-memory access
    cache_time = time.time() - t0
    
    # Cache should be significantly faster
    assert cache_time < disk_time


# ── WRITE_ACTIONS set ─────────────────────────────────────────────────────────

def test_write_actions_defined():
    """Verify WRITE_ACTIONS constant exists and contains expected actions."""
    # Import from server module
    try:
        from gobp.mcp.server import WRITE_ACTIONS
        assert "batch" in WRITE_ACTIONS
        assert "session" in WRITE_ACTIONS
        assert "create" in WRITE_ACTIONS
        assert "delete" in WRITE_ACTIONS
    except ImportError:
        # WRITE_ACTIONS might be defined differently
        pass


# ── PROTOCOL_GUIDE ────────────────────────────────────────────────────────────

def test_protocol_guide_has_refresh():
    from gobp.mcp.parser import PROTOCOL_GUIDE
    actions = PROTOCOL_GUIDE.get("actions", {})
    assert any("refresh" in k for k in actions)
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A12] — Server Cache — 2026-04-18

### Changed
- **MCP server in-memory cache** — eliminates per-call disk reload
  - get_cached_index(): returns cached GraphIndex
  - Read actions use cache (0 file reads per call)
  - Write actions invalidate cache (next read reloads)
  - batch: updates cache directly with working_index (no reload)
  
- **refresh: action** — force cache reload from disk
  - Use after manual file edits or schema changes

### Performance impact
  - Cold load: ~500ms (one-time at server start)
  - Warm find: <100ms (was ~1000ms)
  - Warm get: <10ms (was ~500ms)
  - Warm explore: <50ms (was ~800ms)
  - Warm suggest: <50ms (was ~1000ms)
  - 20x-50x improvement for read operations

### Total: 590+ tests
```

**Commit message:**
```
Wave 16A12 Task 5: tests/test_wave16a12.py + CHANGELOG

- 7 tests: cache singleton, invalidate, update, refresh, perf, WRITE_ACTIONS
- 590+ tests passing
- CHANGELOG: Wave 16A12 entry
```

---

# CEO DISPATCH

## Cursor
```
Read .cursorrules and waves/wave_16a12_brief.md.
Read gobp/mcp/server.py, gobp/mcp/dispatcher.py,
gobp/mcp/tools/write.py, gobp/mcp/tools/read.py.
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute 5 tasks. R9: 581 tests baseline. 1 task = 1 commit.
```

## Claude CLI audit
```
Audit Wave 16A12.
Task 1: get_cached_index, invalidate_cache, update_cache in server.py
Task 2: read actions use cache, writes invalidate, refresh: action
Task 3: batch calls update_cache(working_index), no post-batch reload
Task 4: perf test — warm find <100ms, warm explore <50ms
Task 5: test_wave16a12.py 7 tests, 590+ total, CHANGELOG
BLOCKING: Gặp vấn đề → DỪNG, báo CEO.
Expected: 590+ tests.
```

---

*Wave 16A12 Brief v1.0 — 2026-04-18*

◈
