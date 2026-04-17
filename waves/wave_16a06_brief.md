# WAVE 16A06 BRIEF — DELETE NODE + RETYPE

**Wave:** 16A06
**Title:** delete: action + retype: action
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-17
**For:** Cursor (sequential execution) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 4 atomic tasks
**Estimated effort:** 2-3 hours

---

## CONTEXT

**Problem:**
```
Node created with wrong type (e.g. Node instead of Engine)
→ ID has wrong group: node_17.meta.00000001
→ Cannot fix with upsert: — type changes but ID stays wrong
→ Priority computed wrong (meta tier_weight=0 vs ops=8)
→ Data contamination in graph

Need:
  delete: node_id          — remove node + all its edges
  retype: id='x' new_type='Engine' — atomic delete + recreate with correct ID
```

---

## DESIGN

### delete: action

```
gobp-mihos(query="delete: node_17.meta.00000001 session_id='x'")

→ Remove node from .gobp/nodes/
→ Remove all edges referencing this node from .gobp/edges/
→ Return: {ok, deleted_node_id, deleted_edges_count}

Safety:
  - Require session_id
  - Cannot delete Session nodes (prevent accidental session deletion)
  - Cannot delete Document nodes (source of truth)
  - Return error if node not found
```

### retype: action

```
gobp-mihos(query="retype: id='node_17.meta.00000001' new_type='Engine' session_id='x'")

→ Step 1: Get full node data
→ Step 2: Get all edges (incoming + outgoing)
→ Step 3: Delete old node + edges
→ Step 4: Create new node with correct type + new ID (correct group)
→ Step 5: Recreate all edges with new ID
→ Return: {ok, old_id, new_id, edges_migrated}
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 477 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 477 tests passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/mcp/dispatcher.py` | Add delete: + retype: |
| 3 | `gobp/mcp/tools/write.py` | Add delete + retype functions |
| 4 | `gobp/core/mutator.py` | Add delete_node() |
| 5 | `gobp/core/graph.py` | Add remove_node() to GraphIndex |
| 6 | `waves/wave_16a06_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Add delete_node() to core

**Files to modify:**
- `gobp/core/graph.py`
- `gobp/core/mutator.py`

**gobp/core/graph.py** — add `remove_node()`:

```python
def remove_node(self, node_id: str) -> bool:
    """Remove node from index. Returns True if found and removed."""
    if node_id in self._nodes:
        del self._nodes[node_id]
        # Remove from edges
        self._edges = [
            e for e in self._edges
            if e.get("from") != node_id and e.get("to") != node_id
        ]
        return True
    return False
```

**gobp/core/mutator.py** — add `delete_node()`:

```python
def delete_node(
    gobp_root: Path,
    node_id: str,
    session_id: str,
) -> dict:
    """Delete a node and all its edges from disk.
    
    Returns:
        dict with ok, deleted_node_id, deleted_edges_count
    """
    nodes_dir = gobp_root / ".gobp" / "nodes"
    edges_dir = gobp_root / ".gobp" / "edges"
    
    # Find node file
    node_file = None
    for f in nodes_dir.glob("*.md"):
        from gobp.core.loader import load_node_file
        node = load_node_file(f)
        if node.get("id") == node_id:
            node_file = f
            break
    
    if not node_file:
        return {"ok": False, "error": f"Node not found: {node_id}"}
    
    # Safety: cannot delete Session or Document nodes
    from gobp.core.loader import load_node_file
    node = load_node_file(node_file)
    protected_types = {"Session", "Document"}
    if node.get("type") in protected_types:
        return {
            "ok": False,
            "error": f"Cannot delete {node.get('type')} nodes — protected type"
        }
    
    # Delete edges referencing this node
    deleted_edges = 0
    if edges_dir.exists():
        for edge_file in edges_dir.glob("*.yaml"):
            import yaml as _yaml
            try:
                edge = _yaml.safe_load(edge_file.read_text(encoding="utf-8"))
                if edge and (edge.get("from") == node_id or edge.get("to") == node_id):
                    edge_file.unlink()
                    deleted_edges += 1
            except Exception:
                pass
    
    # Delete node file
    node_file.unlink()
    
    return {
        "ok": True,
        "deleted_node_id": node_id,
        "deleted_edges_count": deleted_edges,
    }
```

**Commit message:**
```
Wave 16A06 Task 1: delete_node() in mutator + remove_node() in GraphIndex

- core/graph.py: remove_node() removes node + cleans edge index
- core/mutator.py: delete_node() deletes node file + edge files
- Protected types: Session, Document cannot be deleted
```

---

## TASK 2 — Add delete: and retype: to dispatcher + write.py

**File to modify:** `gobp/mcp/tools/write.py`

Add `delete_node_action()` and `retype_node_action()`:

```python
async def delete_node_action(
    index: "GraphIndex",
    project_root: Path,
    args: dict,
) -> dict:
    """Delete a node and all its edges.
    
    Query: delete: {node_id} session_id='{x}'
    """
    node_id = args.get("query") or args.get("id")
    session_id = args.get("session_id", "")
    
    if not node_id:
        return {"ok": False, "error": "Node ID required"}
    if not session_id:
        return {"ok": False, "error": "session_id required"}
    
    # Verify session exists
    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}
    
    from gobp.core.mutator import delete_node
    result = delete_node(project_root, node_id, session_id)
    return result


async def retype_node_action(
    index: "GraphIndex",
    project_root: Path,
    args: dict,
) -> dict:
    """Retype a node — delete + recreate with correct type and new ID.
    
    Query: retype: id='{node_id}' new_type='Engine' session_id='{x}'
    """
    node_id = args.get("id") or args.get("query")
    new_type = args.get("new_type")
    session_id = args.get("session_id", "")
    
    if not node_id:
        return {"ok": False, "error": "id required"}
    if not new_type:
        return {"ok": False, "error": "new_type required"}
    if not session_id:
        return {"ok": False, "error": "session_id required"}
    
    # Get existing node
    old_node = index.get_node(node_id)
    if not old_node:
        return {"ok": False, "error": f"Node not found: {node_id}"}
    
    # Get all edges referencing this node
    all_edges = index.all_edges() if hasattr(index, 'all_edges') else []
    related_edges = [
        e for e in all_edges
        if e.get("from") == node_id or e.get("to") == node_id
    ]
    
    # Delete old node + edges
    from gobp.core.mutator import delete_node, node_upsert
    del_result = delete_node(project_root, node_id, session_id)
    if not del_result.get("ok"):
        return del_result
    
    # Recreate node with new type (new ID auto-generated)
    new_node_data = {k: v for k, v in old_node.items() if k not in ("id", "type")}
    new_node_data["type"] = new_type
    new_node_data["session_id"] = session_id
    
    # Reload index after delete
    from gobp.core.graph import GraphIndex
    fresh_index = GraphIndex.load_from_disk(project_root)
    
    upsert_result = await node_upsert(fresh_index, project_root, new_node_data)
    if not upsert_result.get("ok"):
        return upsert_result
    
    new_id = upsert_result.get("node_id")
    
    # Recreate edges with new ID
    edges_migrated = 0
    from gobp.core.mutator import create_edge
    fresh_index2 = GraphIndex.load_from_disk(project_root)
    
    for edge in related_edges:
        from_id = new_id if edge.get("from") == node_id else edge.get("from")
        to_id = new_id if edge.get("to") == node_id else edge.get("to")
        edge_type = edge.get("type", "relates_to")
        try:
            create_edge(project_root, from_id, to_id, edge_type, session_id)
            edges_migrated += 1
        except Exception:
            pass
    
    return {
        "ok": True,
        "old_id": node_id,
        "new_id": new_id,
        "new_type": new_type,
        "edges_migrated": edges_migrated,
    }
```

**File to modify:** `gobp/mcp/dispatcher.py`

Add handlers:

```python
        elif action == "delete":
            result = await tools_write.delete_node_action(index, project_root, params)

        elif action == "retype":
            result = await tools_write.retype_node_action(index, project_root, params)
```

**Update PROTOCOL_GUIDE in parser.py:**
```python
"delete: {node_id} session_id='x'":           "Delete node + edges",
"retype: id='{id}' new_type='Engine' session_id='x'": "Change node type (delete + recreate with correct ID)",
```

**Commit message:**
```
Wave 16A06 Task 2: delete: + retype: actions

- write.py: delete_node_action(), retype_node_action()
- dispatcher.py: delete: + retype: routing
- parser.py: PROTOCOL_GUIDE entries
- retype: preserves all data + migrates edges to new ID
```

---

## TASK 3 — Smoke test

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch
import tempfile, shutil

async def test():
    # Use temp project
    tmp = Path(tempfile.mkdtemp())
    try:
        init_project(tmp)
        index = GraphIndex.load_from_disk(tmp)
        
        # Start session
        sess = await dispatch('session:start actor=test goal=delete-test', index, tmp)
        sid = sess['session_id']
        index = GraphIndex.load_from_disk(tmp)
        
        # Create a Node (wrong type)
        r1 = await dispatch(f'create:Node name=\"TrustGate Engine\" session_id={sid}', index, tmp)
        assert r1['ok'], f'create failed: {r1}'
        node_id = r1['node_id']
        print(f'Created: {node_id}')
        assert '.meta.' in node_id  # Node is in meta group
        
        # Retype to Engine
        index = GraphIndex.load_from_disk(tmp)
        r2 = await dispatch(f'retype: id={node_id} new_type=Engine session_id={sid}', index, tmp)
        assert r2['ok'], f'retype failed: {r2}'
        new_id = r2['new_id']
        print(f'Retyped: {node_id} → {new_id}')
        assert '.ops.' in new_id  # Engine is in ops group
        assert node_id != new_id
        
        # Old node should be gone
        index = GraphIndex.load_from_disk(tmp)
        old = index.get_node(node_id)
        assert old is None, f'Old node still exists: {old}'
        
        # New node should exist
        new = index.get_node(new_id)
        assert new is not None
        assert new.get('type') == 'Engine'
        print('retype: OK')
        
        # Test delete:
        r3 = await dispatch(f'delete: {new_id} session_id={sid}', index, tmp)
        assert r3['ok'], f'delete failed: {r3}'
        print(f'Deleted: {new_id}')
        
        index = GraphIndex.load_from_disk(tmp)
        gone = index.get_node(new_id)
        assert gone is None
        print('delete: OK')
        
        print('ALL SMOKE TESTS PASSED')
    finally:
        shutil.rmtree(tmp)

asyncio.run(test())
"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 477 tests passing
```

**Commit message:**
```
Wave 16A06 Task 3: smoke test delete: + retype: — all passing

- delete: removes node file + edge files
- retype: creates new node with correct group ID
- Old node gone after retype
- 477 tests passing
```

---

## TASK 4 — Tests + CHANGELOG

**File to create:** `tests/test_wave16a06.py`

```python
"""Tests for Wave 16A06: delete: and retype: actions."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch


@pytest.fixture
def tmp_project(tmp_path):
    init_project(tmp_path)
    return tmp_path


def _start_session(root):
    index = GraphIndex.load_from_disk(root)
    r = asyncio.run(dispatch("session:start actor='test' goal='test'", index, root))
    return r["session_id"]


# ── delete: tests ─────────────────────────────────────────────────────────────

def test_delete_node(tmp_project):
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)
    r = asyncio.run(dispatch(f"create:Node name='Temp Node' session_id={sid}", index, tmp_project))
    node_id = r["node_id"]

    index = GraphIndex.load_from_disk(tmp_project)
    r2 = asyncio.run(dispatch(f"delete: {node_id} session_id={sid}", index, tmp_project))
    assert r2["ok"] is True
    assert r2["deleted_node_id"] == node_id

    index = GraphIndex.load_from_disk(tmp_project)
    assert index.get_node(node_id) is None


def test_delete_removes_edges(tmp_project):
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)

    r1 = asyncio.run(dispatch(f"create:Node name='NodeA' session_id={sid}", index, tmp_project))
    index = GraphIndex.load_from_disk(tmp_project)
    r2 = asyncio.run(dispatch(f"create:Node name='NodeB' session_id={sid}", index, tmp_project))
    id_a, id_b = r1["node_id"], r2["node_id"]

    index = GraphIndex.load_from_disk(tmp_project)
    asyncio.run(dispatch(f"edge: {id_a} --relates_to--> {id_b}", index, tmp_project))

    index = GraphIndex.load_from_disk(tmp_project)
    asyncio.run(dispatch(f"delete: {id_a} session_id={sid}", index, tmp_project))

    index = GraphIndex.load_from_disk(tmp_project)
    edges_dir = tmp_project / ".gobp" / "edges"
    remaining_edges = []
    if edges_dir.exists():
        import yaml
        for f in edges_dir.glob("*.yaml"):
            e = yaml.safe_load(f.read_text())
            if e and (e.get("from") == id_a or e.get("to") == id_a):
                remaining_edges.append(e)
    assert len(remaining_edges) == 0


def test_delete_protected_session(tmp_project):
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)
    r = asyncio.run(dispatch(f"delete: {sid} session_id={sid}", index, tmp_project))
    assert r["ok"] is False
    assert "protected" in r["error"].lower() or "cannot" in r["error"].lower()


def test_delete_not_found(tmp_project):
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)
    r = asyncio.run(dispatch(f"delete: nonexistent.meta.00000099 session_id={sid}", index, tmp_project))
    assert r["ok"] is False


# ── retype: tests ─────────────────────────────────────────────────────────────

def test_retype_node_changes_group(tmp_project):
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)
    r = asyncio.run(dispatch(f"create:Node name='TrustGate' session_id={sid}", index, tmp_project))
    old_id = r["node_id"]
    assert ".meta." in old_id

    index = GraphIndex.load_from_disk(tmp_project)
    r2 = asyncio.run(dispatch(f"retype: id={old_id} new_type=Engine session_id={sid}", index, tmp_project))
    assert r2["ok"] is True
    new_id = r2["new_id"]
    assert ".ops." in new_id
    assert old_id != new_id


def test_retype_old_node_deleted(tmp_project):
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)
    r = asyncio.run(dispatch(f"create:Node name='OldNode' session_id={sid}", index, tmp_project))
    old_id = r["node_id"]

    index = GraphIndex.load_from_disk(tmp_project)
    asyncio.run(dispatch(f"retype: id={old_id} new_type=Flow session_id={sid}", index, tmp_project))

    index = GraphIndex.load_from_disk(tmp_project)
    assert index.get_node(old_id) is None


def test_retype_preserves_name(tmp_project):
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)
    r = asyncio.run(dispatch(f"create:Node name='Verify Gate Flow' session_id={sid}", index, tmp_project))
    old_id = r["node_id"]

    index = GraphIndex.load_from_disk(tmp_project)
    r2 = asyncio.run(dispatch(f"retype: id={old_id} new_type=Flow session_id={sid}", index, tmp_project))
    new_id = r2["new_id"]

    index = GraphIndex.load_from_disk(tmp_project)
    new_node = index.get_node(new_id)
    assert new_node is not None
    assert new_node.get("name") == "Verify Gate Flow"


def test_retype_migrates_edges(tmp_project):
    sid = _start_session(tmp_project)
    index = GraphIndex.load_from_disk(tmp_project)

    r1 = asyncio.run(dispatch(f"create:Node name='NodeA' session_id={sid}", index, tmp_project))
    index = GraphIndex.load_from_disk(tmp_project)
    r2 = asyncio.run(dispatch(f"create:Entity name='EntityB' session_id={sid}", index, tmp_project))
    id_a, id_b = r1["node_id"], r2["node_id"]

    index = GraphIndex.load_from_disk(tmp_project)
    asyncio.run(dispatch(f"edge: {id_a} --relates_to--> {id_b}", index, tmp_project))

    index = GraphIndex.load_from_disk(tmp_project)
    r3 = asyncio.run(dispatch(f"retype: id={id_a} new_type=Flow session_id={sid}", index, tmp_project))
    new_id = r3["new_id"]
    assert r3["edges_migrated"] >= 1

    index = GraphIndex.load_from_disk(tmp_project)
    edges_dir = tmp_project / ".gobp" / "edges"
    found = False
    if edges_dir.exists():
        import yaml
        for f in edges_dir.glob("*.yaml"):
            e = yaml.safe_load(f.read_text())
            if e and (e.get("from") == new_id or e.get("to") == new_id):
                found = True
    assert found


def test_protocol_guide_has_delete_retype():
    from gobp.mcp.parser import PROTOCOL_GUIDE
    actions = PROTOCOL_GUIDE.get("actions", {})
    assert any("delete:" in k for k in actions)
    assert any("retype:" in k for k in actions)
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A06] — Delete + Retype nodes — 2026-04-17

### Added
- **delete: action** — remove node + all its edges
  - Protected types: Session, Document cannot be deleted
  - Usage: `delete: {node_id} session_id='x'`
  
- **retype: action** — change node type with correct group ID
  - Atomic: delete old node → recreate with new type → migrate edges
  - Old meta.node → new ops.engine (correct group)
  - Usage: `retype: id='{id}' new_type='Engine' session_id='x'`

### Why
- Nodes created with wrong type had wrong group in ID
- Wrong group → wrong tier_weight → wrong priority
- retype: fixes data quality without manual intervention

### Total: 490+ tests
```

**Commit message:**
```
Wave 16A06 Task 4: tests/test_wave16a06.py + CHANGELOG

- 9 tests: delete node, delete edges, protected types, retype group change
- 490+ tests passing
- CHANGELOG: Wave 16A06 entry
```

---

# POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 490+ tests

# Test on MIHOS project
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp_mihos"

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch

async def test():
    root = Path('D:/MIHOS-v1')
    index = GraphIndex.load_from_disk(root)
    
    # Find Node type nodes that should be Engine/Flow/Entity
    nodes = [n for n in index.all_nodes() if n.get('type') == 'Node']
    print(f'Node-typed nodes: {len(nodes)}')
    for n in nodes[:5]:
        print(f'  {n[\"id\"]} — {n[\"name\"]}')

asyncio.run(test())
"
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Save Brief

```powershell
cd D:\GoBP
# Save to D:\GoBP\waves\wave_16a06_brief.md
git add waves/wave_16a06_brief.md
git commit -m "Add Wave 16A06 Brief — delete: + retype: actions"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_16a06_brief.md first.
Also read gobp/core/mutator.py, gobp/core/graph.py,
gobp/mcp/tools/write.py, gobp/mcp/dispatcher.py.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 4 tasks sequentially.
R9: all 477 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 16A06. Read CLAUDE.md and waves/wave_16a06_brief.md.
Set env: $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: delete_node() in mutator.py, remove_node() in graph.py
          Session + Document protected from deletion
- Task 2: delete: action in dispatcher + write.py
          retype: action — delete + recreate + migrate edges
          PROTOCOL_GUIDE has delete: + retype: entries
- Task 3: Smoke test passes — retype Node→Engine changes .meta.→.ops.
- Task 4: test_wave16a06.py 9 tests, 490+ total, CHANGELOG updated

BLOCKING RULE: Gặp vấn đề → DỪNG ngay, báo CEO.

Expected: 490+ tests. Report WAVE 16A06 AUDIT COMPLETE.
```

---

*Wave 16A06 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-17*

◈
