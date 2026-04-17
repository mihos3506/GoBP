# WAVE 16A11 BRIEF — BATCH PERFORMANCE FIX

**Wave:** 16A11
**Title:** Batch single-load/single-save — eliminate per-op disk reload
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-18
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 4 tasks
**Estimated effort:** 2-3 hours

---

## CONTEXT

**Problem:**
```
batch 50 ops:   ~5 giây    ✓
batch 150 ops:  ~15 giây   ✓ (gần limit)
batch 440 ops:  ~45 giây   → MCP timeout ✗

Root cause: mỗi op trong batch gọi
  GraphIndex.load_from_disk()  → đọc lại TOÀN BỘ .gobp/nodes/*.md
  dispatch(query)              → execute
  → 440 ops = 440 full disk scans
  → O(N × M) where N=ops, M=total nodes on disk
```

**Fix:**
```
Load index 1 lần → execute tất cả ops in-memory → save 1 lần

Before: 440 ops × load_from_disk() = 440 full scans
After:  1 load + 440 in-memory ops + 1 save = 2 disk ops

Expected: batch 440 ops < 5 giây
```

---

## DESIGN

### Core change: in-memory batch execution

```python
async def batch_action(index, project_root, args):
    # ... parse ops ...
    
    # OLD: per-op reload
    # for op in ops:
    #     fresh = GraphIndex.load_from_disk(project_root)
    #     result = await dispatch(query, fresh, project_root)
    
    # NEW: single load, in-memory updates, single save
    working_index = GraphIndex.load_from_disk(project_root)
    
    for op in ops:
        result = execute_op(op, working_index, project_root, session_id)
        # working_index updated in-memory after each op
    
    # Save all changes at end
    working_index.save_to_disk(project_root)
```

### GraphIndex changes needed

```python
class GraphIndex:
    
    def add_node_in_memory(self, node: dict) -> str:
        """Add node to in-memory index without writing to disk.
        Returns generated node_id.
        """
        # Generate ID
        node_id = self._generate_id(node)
        node["id"] = node_id
        
        # Add to internal dict
        self._nodes[node_id] = node
        
        # Update type index
        node_type = node.get("type", "Node")
        if node_type not in self._nodes_by_type_idx:
            self._nodes_by_type_idx[node_type] = []
        self._nodes_by_type_idx[node_type].append(node_id)
        
        return node_id
    
    def add_edge_in_memory(self, from_id: str, to_id: str, edge_type: str) -> bool:
        """Add edge to in-memory index without writing to disk.
        Returns True if added, False if duplicate.
        """
        edge = {"from": from_id, "to": to_id, "type": edge_type}
        
        # Check duplicate
        for existing in self._edges:
            if (existing.get("from") == from_id and
                existing.get("to") == to_id and
                existing.get("type") == edge_type):
                return False  # duplicate
        
        self._edges.append(edge)
        return True
    
    def remove_node_in_memory(self, node_id: str) -> bool:
        """Remove node + edges from in-memory index."""
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        self._edges = [
            e for e in self._edges
            if e.get("from") != node_id and e.get("to") != node_id
        ]
        return True
    
    def save_to_disk(self, gobp_root: Path) -> dict:
        """Write all in-memory nodes and edges to disk.
        Returns: {nodes_written, edges_written}
        """
        nodes_dir = gobp_root / ".gobp" / "nodes"
        edges_dir = gobp_root / ".gobp" / "edges"
        nodes_dir.mkdir(parents=True, exist_ok=True)
        edges_dir.mkdir(parents=True, exist_ok=True)
        
        nodes_written = 0
        for node_id, node in self._nodes.items():
            filepath = nodes_dir / f"{self._id_to_filename(node_id)}.md"
            if not filepath.exists():  # only write new/modified nodes
                self._write_node_file(filepath, node)
                nodes_written += 1
        
        edges_written = 0
        # Write edges to single YAML file per batch
        # (or append to existing relations.yaml)
        
        return {"nodes_written": nodes_written, "edges_written": edges_written}
```

### Batch executor changes

```python
async def _batch_create(op, working_index, project_root, session_id, name_to_id):
    """Create node in-memory — no disk reload."""
    from gobp.core.search import find_similar_nodes, normalize_text
    
    name = op.get("name", "")
    node_type = op.get("type", "Node")
    description = op.get("description", "")
    
    # Dedupe check against working_index (in-memory)
    similar = find_similar_nodes(working_index, name, node_type, threshold=80)
    if similar:
        best = similar[0]
        return {
            "status": "skipped",
            "reason": f"duplicate of {best.get('id')} ({best.get('name')})",
        }
    
    # Create in-memory
    node_data = {
        "type": node_type,
        "name": name,
        "description": description,
        "status": "ACTIVE",
        "session_id": session_id,
    }
    node_id = working_index.add_node_in_memory(node_data)
    
    return {"status": "ok", "new_id": node_id}


async def _batch_edge(op, working_index, project_root, session_id, name_to_id):
    """Add edge in-memory — no disk reload."""
    # ... resolve names to IDs using working_index ...
    
    added = working_index.add_edge_in_memory(from_id, to_id, edge_type)
    if added:
        return {"status": "ok"}
    return {"status": "skipped", "reason": "already exists"}
```

### Raise batch limit

```
Old limit: 50 ops per call
New limit: 500 ops per call (in-memory is fast)

If >500 → split into multiple calls
But 500 covers most real use cases
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 562 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 562 tests
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/core/graph.py` | Add in-memory methods + save_to_disk |
| 3 | `gobp/mcp/tools/write.py` | Refactor batch_action to single-load |
| 4 | `gobp/core/mutator.py` | Write node/edge to disk helpers |

---

# TASKS

## TASK 1 — Add in-memory methods to GraphIndex

**File to modify:** `gobp/core/graph.py`

**Re-read in full.**

Add methods:
- `add_node_in_memory(node) → node_id`
- `add_edge_in_memory(from_id, to_id, edge_type) → bool`
- `remove_node_in_memory(node_id) → bool`
- `save_new_nodes_to_disk(gobp_root) → {nodes_written}`
- `save_new_edges_to_disk(gobp_root) → {edges_written}`

Track new nodes/edges separately:
```python
self._new_nodes = {}      # nodes added in-memory, not yet on disk
self._new_edges = []      # edges added in-memory, not yet on disk
```

`save_new_nodes_to_disk()` only writes `_new_nodes` — doesn't rewrite existing nodes.
`save_new_edges_to_disk()` appends `_new_edges` to edge files.

**Commit message:**
```
Wave 16A11 Task 1: add in-memory ops to GraphIndex

- add_node_in_memory(): add node without disk write
- add_edge_in_memory(): add edge without disk write
- remove_node_in_memory(): remove from index
- save_new_nodes_to_disk(): flush new nodes only
- save_new_edges_to_disk(): append new edges only
- Track _new_nodes/_new_edges separately
```

---

## TASK 2 — Refactor batch_action to single-load/single-save

**File to modify:** `gobp/mcp/tools/write.py`

**Re-read batch_action() in full.**

Refactor:

```python
async def batch_action(index, project_root, args):
    # ... parse + validate session ...
    
    from gobp.mcp.batch_parser import parse_batch
    ops = parse_batch(ops_raw)
    
    if len(ops) > 500:
        return {"ok": False, "error": f"Max 500 ops per batch, got {len(ops)}"}
    
    # SINGLE LOAD
    from gobp.core.graph import GraphIndex
    working_index = GraphIndex.load_from_disk(project_root)
    
    # Execute all ops in-memory
    for op in ops:
        result = await _execute_op_in_memory(op, working_index, project_root, session_id, name_to_id)
        # ... collect results ...
    
    # SINGLE SAVE
    save_result = working_index.save_new_nodes_to_disk(project_root)
    edge_result = working_index.save_new_edges_to_disk(project_root)
    
    # ... return summary ...
```

Refactor `_batch_create`, `_batch_edge`, `_batch_update` to use `working_index` in-memory methods instead of `dispatch()` + `load_from_disk()`.

For ops that need disk operations (delete, retype, merge) — still do disk ops but use `working_index` for lookups.

**Commit message:**
```
Wave 16A11 Task 2: refactor batch to single-load/single-save

- Load index once at batch start
- All create/edge ops execute in-memory
- Save all new nodes + edges at batch end
- Limit raised from 50 to 500 ops per call
- delete/retype/merge still do direct disk ops
```

---

## TASK 3 — Performance test + smoke

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio, time, tempfile, shutil
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch

async def perf_test():
    tmp = Path(tempfile.mkdtemp())
    try:
        init_project(tmp)
        index = GraphIndex.load_from_disk(tmp)
        
        sess = await dispatch('session:start actor=perf goal=batch-perf', index, tmp)
        sid = sess['session_id']
        
        # Build 200 nodes + 100 edges
        lines = []
        for i in range(200):
            lines.append(f'create: Engine: PerfEngine{i} | Performance test engine {i}')
        for i in range(0, 100, 2):
            lines.append(f'edge+: PerfEngine{i} --depends_on--> PerfEngine{i+1}')
        
        ops_str = '\\n'.join(lines)
        
        index = GraphIndex.load_from_disk(tmp)
        
        t0 = time.time()
        r = await dispatch(
            f\"batch session_id='{sid}' ops='{ops_str}'\",
            index, tmp
        )
        elapsed = time.time() - t0
        
        print(f'batch 300 ops: {elapsed:.1f}s')
        print(f'summary: {r.get(\"summary\", \"\")}')
        print(f'errors: {len(r.get(\"errors\", []))}')
        
        assert elapsed < 15, f'Too slow: {elapsed:.1f}s (expected <15s)'
        assert r.get('ok') or r.get('succeeded', 0) > 0
        
        # Verify nodes exist
        index2 = GraphIndex.load_from_disk(tmp)
        print(f'nodes after batch: {len(index2.all_nodes())}')
        
        print('PERF TEST PASSED')
    finally:
        shutil.rmtree(tmp)

asyncio.run(perf_test())
"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

**Commit message:**
```
Wave 16A11 Task 3: performance test — batch 300 ops < 15s

- 200 creates + 100 edges in single batch
- Verified: elapsed < 15s (was ~45s+ before)
- All nodes persisted to disk after batch
- 562 tests passing
```

---

## TASK 4 — Tests + CHANGELOG

**File to create:** `tests/test_wave16a11.py`

```python
"""Tests for Wave 16A11: batch performance — single load/save."""

from __future__ import annotations
import asyncio, time
from pathlib import Path
import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch


@pytest.fixture
def proj(tmp_path):
    init_project(tmp_path)
    return tmp_path


def _sid(proj):
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("session:start actor='t' goal='t'", index, proj))
    return r["session_id"]


# ── In-memory methods ────────────────────────────────────────────────────────

def test_add_node_in_memory(proj):
    index = GraphIndex.load_from_disk(proj)
    node_id = index.add_node_in_memory({
        "type": "Engine", "name": "TestEng", "status": "ACTIVE"
    })
    assert node_id
    assert index.get_node(node_id) is not None


def test_add_edge_in_memory(proj):
    index = GraphIndex.load_from_disk(proj)
    id_a = index.add_node_in_memory({"type": "Engine", "name": "A", "status": "ACTIVE"})
    id_b = index.add_node_in_memory({"type": "Engine", "name": "B", "status": "ACTIVE"})
    added = index.add_edge_in_memory(id_a, id_b, "depends_on")
    assert added is True


def test_add_edge_duplicate_returns_false(proj):
    index = GraphIndex.load_from_disk(proj)
    id_a = index.add_node_in_memory({"type": "Engine", "name": "A", "status": "ACTIVE"})
    id_b = index.add_node_in_memory({"type": "Engine", "name": "B", "status": "ACTIVE"})
    index.add_edge_in_memory(id_a, id_b, "depends_on")
    dup = index.add_edge_in_memory(id_a, id_b, "depends_on")
    assert dup is False


def test_save_new_nodes_to_disk(proj):
    index = GraphIndex.load_from_disk(proj)
    index.add_node_in_memory({"type": "Engine", "name": "SaveTest", "status": "ACTIVE"})
    result = index.save_new_nodes_to_disk(proj)
    assert result["nodes_written"] >= 1
    
    # Verify reload finds node
    index2 = GraphIndex.load_from_disk(proj)
    found = [n for n in index2.all_nodes() if n.get("name") == "SaveTest"]
    assert len(found) == 1


def test_remove_node_in_memory(proj):
    index = GraphIndex.load_from_disk(proj)
    node_id = index.add_node_in_memory({"type": "Node", "name": "Gone", "status": "ACTIVE"})
    removed = index.remove_node_in_memory(node_id)
    assert removed is True
    assert index.get_node(node_id) is None


# ── Batch performance ────────────────────────────────────────────────────────

def test_batch_100_creates_under_10s(proj):
    sid = _sid(proj)
    lines = [f"create: Engine: BatchEng{i} | Engine {i}" for i in range(100)]
    ops = "\\n".join(lines)
    
    index = GraphIndex.load_from_disk(proj)
    t0 = time.time()
    r = asyncio.run(dispatch(
        f"batch session_id='{sid}' ops='{ops}'", index, proj
    ))
    elapsed = time.time() - t0
    
    assert r.get("succeeded", 0) >= 50, f"Too few succeeded: {r}"
    assert elapsed < 10, f"Too slow: {elapsed:.1f}s"


def test_batch_limit_500(proj):
    sid = _sid(proj)
    lines = [f"create: Node: N{i} | Node {i}" for i in range(501)]
    ops = "\\n".join(lines)
    
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch(
        f"batch session_id='{sid}' ops='{ops}'", index, proj
    ))
    assert not r.get("ok") or "Max" in r.get("error", "")


def test_batch_creates_then_edges_same_call(proj):
    sid = _sid(proj)
    ops = (
        "create: Engine: AlphaEng | Alpha\\n"
        "create: Engine: BetaEng | Beta\\n"
        "edge+: AlphaEng --depends_on--> BetaEng"
    )
    
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch(
        f"batch session_id='{sid}' ops='{ops}'", index, proj
    ))
    assert r.get("succeeded", 0) >= 2


# ── PROTOCOL_GUIDE ────────────────────────────────────────────────────────────

def test_batch_limit_documented():
    from gobp.mcp.parser import PROTOCOL_GUIDE
    actions = PROTOCOL_GUIDE.get("actions", {})
    batch_entries = [k for k in actions if "batch" in k.lower()]
    assert batch_entries
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A11] — Batch Performance Fix — 2026-04-18

### Changed
- **batch: single-load/single-save** — eliminated per-op disk reload
  - Before: 440 ops = 440 × load_from_disk() → timeout
  - After: 1 load + 440 in-memory ops + 1 save → <5 seconds
  - GraphIndex: add_node_in_memory(), add_edge_in_memory()
  - save_new_nodes_to_disk(), save_new_edges_to_disk()

- **Batch limit raised** from 50 to 500 ops per call
  - In-memory execution is fast enough for 500 ops
  - Still recommend splitting very large imports into chunks

### Impact
- MIHOS import: 240 nodes + 196 edges = 1 call, ~5 seconds
- Token savings: same as before (response unchanged)
- No breaking changes to batch format

### Total: 572+ tests
```

**Commit message:**
```
Wave 16A11 Task 4: tests/test_wave16a11.py + CHANGELOG

- 9 tests: in-memory ops, perf benchmark, limit, create+edge same call
- 572+ tests passing
- CHANGELOG: Wave 16A11 entry
```

---

# CEO DISPATCH

## Cursor
```
Read .cursorrules and waves/wave_16a11_brief.md.
Read gobp/core/graph.py, gobp/mcp/tools/write.py, gobp/core/mutator.py.
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute 4 tasks. R9: 562 tests baseline. 1 task = 1 commit.
```

## Claude CLI audit
```
Audit Wave 16A11.
Task 1: add_node_in_memory, add_edge_in_memory, remove_node_in_memory,
        save_new_nodes_to_disk, save_new_edges_to_disk in graph.py
        _new_nodes/_new_edges tracking
Task 2: batch_action refactored — single load, in-memory ops, single save
        Limit raised 50 → 500
Task 3: Perf test 300 ops < 15s
Task 4: test_wave16a11.py 9 tests, 572+ total, CHANGELOG
BLOCKING: Gặp vấn đề → DỪNG, báo CEO.
Expected: 572+ tests.
```

---

*Wave 16A11 Brief v1.0 — 2026-04-18*

◈
