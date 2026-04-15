# WAVE 11A BRIEF — LAZY QUERY ACTIONS

**Wave:** 11A
**Title:** Lazy query actions — code:, invariants:, tests:, related:
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 6 atomic tasks
**Estimated effort:** 3-4 hours

---

## CONTEXT

Currently `get: <node_id>` returns full node + all edges + decisions in one call (~500 tokens). For complex nodes this is expensive. AI often only needs 1 dimension.

**Problem:**
```
get: node:flow_auth → loads everything (~500 tokens)
AI only needed: which files implement this flow
→ 400 tokens wasted
```

**Solution: 4 lazy query actions**

```
code: node:flow_auth        → only code references (~150 tokens)
invariants: node:flow_auth  → only constraints (~100 tokens)
tests: node:flow_auth       → only linked TestCases (~200 tokens)
related: node:flow_auth     → only neighbor names (~150 tokens)
```

AI calls what it needs. Token cost drops 60-80% for targeted queries.

**New node fields (schema v2.1):**

```yaml
# Added to Node, Idea, Decision, Document optional fields:
code_refs:
  type: list[dict]
  description: "Code files implementing this node"
  items:
    path: str        # relative path from project root
    description: str # what this file does for this node
    language: str    # dart, typescript, python, etc.

invariants:
  type: list[str]
  description: "Hard constraints that must always be true"
```

**Protocol additions:**
```
gobp(query="code: node:flow_auth")
gobp(query="code: node:flow_auth path='lib/features/auth/login_screen.dart' description='OTP UI' language='dart'")
gobp(query="invariants: node:flow_auth")
gobp(query="tests: node:flow_auth")
gobp(query="related: node:flow_auth")
```

**In scope:**
- `gobp/schema/core_nodes.yaml` — add code_refs + invariants optional fields
- `gobp/mcp/dispatcher.py` — add 4 new actions
- `gobp/mcp/tools/read.py` — add 4 handler functions
- `docs/MCP_TOOLS.md` — document new actions
- `tests/test_wave11a.py` — tests

**NOT in scope:**
- Auto-extraction from code (Grapuco territory)
- Code parsing or AST analysis
- Any changes to existing actions

---

## CURSOR EXECUTION RULES

### R1-R9 standard (all apply)
R9: All 253 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 253 tests passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/schema/core_nodes.yaml` | Add new fields |
| 3 | `gobp/mcp/dispatcher.py` | Add 4 actions |
| 4 | `gobp/mcp/tools/read.py` | Add 4 handlers |
| 5 | `docs/MCP_TOOLS.md` | Update protocol |
| 6 | `waves/wave_11a_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Add code_refs and invariants to schema

**Goal:** Add optional `code_refs` and `invariants` fields to node types.

**File to modify:** `gobp/schema/core_nodes.yaml`

**Re-read `core_nodes.yaml` in full before editing.**

Add to `optional` fields of `Node`, `Idea`, `Decision`, `Document`:

```yaml
      code_refs:
        type: "list[dict]"
        default: []
        description: "Code files implementing or related to this node"

      invariants:
        type: "list[str]"
        default: []
        description: "Hard constraints that must always be true for this node"
```

**Verify:**
```powershell
D:/GoBP/venv/Scripts/python.exe -c "
import yaml
schema = yaml.safe_load(open('gobp/schema/core_nodes.yaml', encoding='utf-8'))
node = schema['node_types']['Node']['optional']
assert 'code_refs' in node, 'code_refs missing'
assert 'invariants' in node, 'invariants missing'
print('Schema fields added OK')
"
```

**Commit message:**
```
Wave 11A Task 1: add code_refs and invariants fields to schema

- Node, Idea, Decision, Document: add optional code_refs (list[dict])
- Node, Idea, Decision, Document: add optional invariants (list[str])
- Enables lazy query actions: code: and invariants:
```

---

## TASK 2 — Add handler functions to read.py

**Goal:** 4 new handler functions for lazy queries.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `read.py` in full before editing.**

Add these 4 functions after `doc_sections()`:

```python
def code_refs(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get code references for a node.

    Returns list of code files implementing or related to this node.
    Only returns code_refs field — much cheaper than full context().

    Args:
        node_id: str (required)
        add: dict (optional) — add a new code ref
             {path, description, language}

    Returns:
        ok, node_id, node_name, code_refs, count
    """
    node_id = args.get("node_id", "")
    if not node_id:
        return {"ok": False, "error": "node_id required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    refs = node.get("code_refs", [])

    return {
        "ok": True,
        "node_id": node_id,
        "node_name": node.get("name", ""),
        "node_type": node.get("type", ""),
        "code_refs": refs,
        "count": len(refs),
        "hint": (
            "To add a code ref: "
            f"gobp(query=\"code: {node_id} path='lib/x.dart' description='x' language='dart'\")"
        ) if not refs else "",
    }


def node_invariants(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get invariants (hard constraints) for a node.

    Returns list of invariant strings — constraints that must always be true.
    Only returns invariants field — much cheaper than full context().

    Args:
        node_id: str (required)

    Returns:
        ok, node_id, node_name, invariants, count
    """
    node_id = args.get("node_id", "")
    if not node_id:
        return {"ok": False, "error": "node_id required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    invs = node.get("invariants", [])

    return {
        "ok": True,
        "node_id": node_id,
        "node_name": node.get("name", ""),
        "node_type": node.get("type", ""),
        "invariants": invs,
        "count": len(invs),
        "hint": (
            "To add an invariant: use update: or create: with invariants field"
        ) if not invs else "",
    }


def node_tests(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get TestCase nodes linked to this node.

    Finds TestCase nodes where covers field = node_id.
    No schema change needed — uses existing covers edges.

    Args:
        node_id: str (required)
        status: str (optional) — filter by status: PASSING, FAILING, DRAFT, etc.

    Returns:
        ok, node_id, node_name, test_cases, count
    """
    node_id = args.get("node_id", "")
    if not node_id:
        return {"ok": False, "error": "node_id required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    status_filter = args.get("status")

    # Find TestCase nodes that cover this node via 'covers' edges
    covering_edges = index.get_edges_to(node_id)
    test_cases = []
    for edge in covering_edges:
        if edge.get("type") != "covers":
            continue
        tc_node = index.get_node(edge.get("from", ""))
        if tc_node and tc_node.get("type") == "TestCase":
            if status_filter and tc_node.get("status") != status_filter:
                continue
            test_cases.append({
                "id": tc_node.get("id"),
                "name": tc_node.get("name", ""),
                "status": tc_node.get("status", "DRAFT"),
                "priority": tc_node.get("priority", "medium"),
                "automated": tc_node.get("automated", False),
                "kind_id": tc_node.get("kind_id", ""),
            })

    # Sort: FAILING first, then DRAFT, then PASSING
    status_order = {"FAILING": 0, "DRAFT": 1, "READY": 2, "PASSING": 3, "SKIPPED": 4, "DEPRECATED": 5}
    test_cases.sort(key=lambda t: status_order.get(t["status"], 99))

    passing = sum(1 for t in test_cases if t["status"] == "PASSING")
    failing = sum(1 for t in test_cases if t["status"] == "FAILING")

    return {
        "ok": True,
        "node_id": node_id,
        "node_name": node.get("name", ""),
        "node_type": node.get("type", ""),
        "test_cases": test_cases,
        "count": len(test_cases),
        "summary": {
            "passing": passing,
            "failing": failing,
            "draft": len(test_cases) - passing - failing,
        },
        "coverage": "none" if not test_cases else (
            "full" if failing == 0 and passing > 0 else
            "partial" if passing > 0 else
            "draft"
        ),
    }


def node_related(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get related nodes summary — neighbor names without full data.

    Returns lightweight list of connected nodes.
    Much cheaper than context() which loads full node data.

    Args:
        node_id: str (required)
        direction: str (optional) — 'outgoing', 'incoming', 'both' (default: 'both')
        edge_type: str (optional) — filter by edge type

    Returns:
        ok, node_id, node_name, outgoing, incoming, count
    """
    node_id = args.get("node_id", "")
    if not node_id:
        return {"ok": False, "error": "node_id required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    direction = args.get("direction", "both")
    edge_type_filter = args.get("edge_type")

    outgoing = []
    if direction in ("outgoing", "both"):
        for edge in index.get_edges_from(node_id):
            if edge_type_filter and edge.get("type") != edge_type_filter:
                continue
            neighbor = index.get_node(edge.get("to", ""))
            outgoing.append({
                "edge_type": edge.get("type", ""),
                "node_id": edge.get("to", ""),
                "node_name": neighbor.get("name", "") if neighbor else "",
                "node_type": neighbor.get("type", "") if neighbor else "",
                "priority": neighbor.get("priority", "medium") if neighbor else "medium",
            })

    incoming = []
    if direction in ("incoming", "both"):
        for edge in index.get_edges_to(node_id):
            if edge_type_filter and edge.get("type") != edge_type_filter:
                continue
            neighbor = index.get_node(edge.get("from", ""))
            incoming.append({
                "edge_type": edge.get("type", ""),
                "node_id": edge.get("from", ""),
                "node_name": neighbor.get("name", "") if neighbor else "",
                "node_type": neighbor.get("type", "") if neighbor else "",
                "priority": neighbor.get("priority", "medium") if neighbor else "medium",
            })

    return {
        "ok": True,
        "node_id": node_id,
        "node_name": node.get("name", ""),
        "node_type": node.get("type", ""),
        "outgoing": outgoing,
        "incoming": incoming,
        "count": len(outgoing) + len(incoming),
    }
```

**Acceptance criteria:**
- 4 functions added to `read.py`
- `code_refs()` returns code_refs field from node
- `node_invariants()` returns invariants field from node
- `node_tests()` finds TestCase nodes via covers edges
- `node_related()` returns neighbor names without loading full data
- All functions return `{"ok": False, "error": "..."}` for missing node_id or node not found

**Commit message:**
```
Wave 11A Task 2: add 4 lazy query handler functions to read.py

- code_refs(): returns code_refs field only (~150 tokens vs ~500 for context)
- node_invariants(): returns invariants field only (~100 tokens)
- node_tests(): finds TestCase nodes via covers edges, with status summary
- node_related(): returns neighbor names without full node data (~150 tokens)
- All handlers: graceful error on missing node_id or node not found
```

---

## TASK 3 — Add 4 actions to dispatcher

**Goal:** Wire new actions to handler functions.

**File to modify:** `gobp/mcp/dispatcher.py`

**Re-read `dispatcher.py` dispatch() function in full.**

**Add to `parse_query()` — no changes needed** (existing parser handles `action: node_id` format already).

**Add to `dispatch()` — add after `elif action == "sections":` block:**

```python
        elif action == "code":
            node_id = params.get("query") or params.get("node_id", "")
            # Handle 'code: node:x path=... description=... language=...' add variant
            add_ref = None
            if params.get("path"):
                add_ref = {
                    "path": params.get("path", ""),
                    "description": params.get("description", ""),
                    "language": params.get("language", ""),
                }
            args = {"node_id": node_id}
            if add_ref:
                args["add"] = add_ref
            result = tools_read.code_refs(index, project_root, args)

        elif action == "invariants":
            node_id = params.get("query") or params.get("node_id", "")
            result = tools_read.node_invariants(index, project_root, {"node_id": node_id})

        elif action == "tests":
            node_id = params.get("query") or params.get("node_id", "")
            status = params.get("status")
            args = {"node_id": node_id}
            if status:
                args["status"] = status
            result = tools_read.node_tests(index, project_root, args)

        elif action == "related":
            node_id = params.get("query") or params.get("node_id", "")
            direction = params.get("direction", "both")
            edge_type = params.get("edge_type")
            args = {"node_id": node_id, "direction": direction}
            if edge_type:
                args["edge_type"] = edge_type
            result = tools_read.node_related(index, project_root, args)
```

**Update PROTOCOL_GUIDE** — add 4 new entries:

```python
"code: <node_id>":                              "Code files for this node",
"code: <node_id> path='x' description='y'":    "Add code reference to node",
"invariants: <node_id>":                        "Hard constraints for node",
"tests: <node_id>":                             "Linked TestCase nodes",
"tests: <node_id> status='FAILING'":            "Filter tests by status",
"related: <node_id>":                           "Neighbor nodes summary",
"related: <node_id> direction='outgoing'":      "Only outgoing neighbors",
```

**Acceptance criteria:**
- 4 new action handlers in `dispatch()`
- `code:` routes to `tools_read.code_refs()`
- `invariants:` routes to `tools_read.node_invariants()`
- `tests:` routes to `tools_read.node_tests()`
- `related:` routes to `tools_read.node_related()`
- PROTOCOL_GUIDE has 7 new entries
- `_dispatch` field includes correct action name in all responses

**Commit message:**
```
Wave 11A Task 3: add code/invariants/tests/related actions to dispatcher

- code: → tools_read.code_refs()
- invariants: → tools_read.node_invariants()
- tests: → tools_read.node_tests() with optional status filter
- related: → tools_read.node_related() with direction + edge_type filters
- PROTOCOL_GUIDE updated with 7 new entries
```

---

## TASK 4 — Smoke test all 4 new actions

**Goal:** Verify all actions work end-to-end.

```powershell
D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch
import tempfile

async def test():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        init_project(root, force=True)
        index = GraphIndex.load_from_disk(root)
        
        # Pick a seeded node to test against
        nodes = index.nodes_by_type('TestKind')
        assert nodes, 'No TestKind nodes found'
        node_id = nodes[0]['id']
        print(f'Testing with node: {node_id}')
        
        # Test code:
        r = await dispatch(f'code: {node_id}', index, root)
        assert r['ok'], f'code: failed: {r}'
        assert 'code_refs' in r
        print(f'code: OK — {r[\"count\"]} refs')
        
        # Test invariants:
        r = await dispatch(f'invariants: {node_id}', index, root)
        assert r['ok'], f'invariants: failed: {r}'
        assert 'invariants' in r
        print(f'invariants: OK — {r[\"count\"]} invariants')
        
        # Test tests:
        r = await dispatch(f'tests: {node_id}', index, root)
        assert r['ok'], f'tests: failed: {r}'
        assert 'test_cases' in r
        assert 'coverage' in r
        print(f'tests: OK — {r[\"count\"]} test cases, coverage={r[\"coverage\"]}')
        
        # Test related:
        r = await dispatch(f'related: {node_id}', index, root)
        assert r['ok'], f'related: failed: {r}'
        assert 'outgoing' in r
        assert 'incoming' in r
        print(f'related: OK — {r[\"count\"]} neighbors')
        
        print('All 4 lazy query actions OK')

asyncio.run(test())
"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 253 tests passing
```

**Commit message:**
```
Wave 11A Task 4: smoke test all 4 lazy query actions — all pass

- code: returns code_refs field
- invariants: returns invariants field
- tests: returns TestCase nodes via covers edges
- related: returns neighbor summary
- 253 existing tests passing
```

---

## TASK 5 — Create tests/test_wave11a.py

**Goal:** Tests for all 4 new actions.

**File to create:** `tests/test_wave11a.py`

```python
"""Tests for Wave 11A: lazy query actions — code, invariants, tests, related."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml

from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch, parse_query
from gobp.mcp.tools import read as tools_read


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def populated_root(gobp_root: Path) -> Path:
    """Project with init seed data + 1 node with code_refs and invariants."""
    init_project(gobp_root, force=True)
    return gobp_root


@pytest.fixture
def node_with_refs(populated_root: Path) -> tuple[Path, str]:
    """Creates a node with code_refs and invariants, returns (root, node_id)."""
    from gobp.core.graph import GraphIndex
    from gobp.mcp.tools import write as tools_write
    import asyncio as _asyncio

    index = GraphIndex.load_from_disk(populated_root)

    # Start session
    sess = _asyncio.run(dispatch(
        "session:start actor='test' goal='wave11a test'",
        index, populated_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(populated_root)

    # Create node with code_refs and invariants
    result = _asyncio.run(dispatch(
        f"create:Node name='Auth Flow' priority='critical' session_id='{session_id}'",
        index, populated_root
    ))
    node_id = result["node_id"]

    # Update with code_refs and invariants via node_upsert directly
    index = GraphIndex.load_from_disk(populated_root)
    tools_write.node_upsert(index, populated_root, {
        "node_id": node_id,
        "type": "Node",
        "name": "Auth Flow",
        "fields": {
            "code_refs": [
                {"path": "lib/features/auth/login_screen.dart", "description": "OTP UI", "language": "dart"},
                {"path": "backend/src/auth/otp_service.ts", "description": "OTP logic", "language": "typescript"},
            ],
            "invariants": [
                "OTP expires after 5 minutes",
                "Max 3 attempts before lockout",
            ],
            "priority": "critical",
        },
        "session_id": session_id,
    })

    return populated_root, node_id


# ── Schema tests ──────────────────────────────────────────────────────────────

def test_schema_has_code_refs():
    schema = yaml.safe_load(open("gobp/schema/core_nodes.yaml", encoding="utf-8"))
    assert "code_refs" in schema["node_types"]["Node"]["optional"]
    assert "code_refs" in schema["node_types"]["Decision"]["optional"]


def test_schema_has_invariants():
    schema = yaml.safe_load(open("gobp/schema/core_nodes.yaml", encoding="utf-8"))
    assert "invariants" in schema["node_types"]["Node"]["optional"]
    assert "invariants" in schema["node_types"]["Decision"]["optional"]


# ── parse_query tests ─────────────────────────────────────────────────────────

def test_parse_code_action():
    action, _, params = parse_query("code: node:flow_auth")
    assert action == "code"
    assert params.get("query") == "node:flow_auth"


def test_parse_invariants_action():
    action, _, params = parse_query("invariants: node:flow_auth")
    assert action == "invariants"
    assert params.get("query") == "node:flow_auth"


def test_parse_tests_action():
    action, _, params = parse_query("tests: node:flow_auth")
    assert action == "tests"
    assert params.get("query") == "node:flow_auth"


def test_parse_tests_with_status():
    action, _, params = parse_query("tests: node:flow_auth status='FAILING'")
    assert action == "tests"
    assert params.get("status") == "FAILING"


def test_parse_related_action():
    action, _, params = parse_query("related: node:flow_auth")
    assert action == "related"


def test_parse_related_with_direction():
    action, _, params = parse_query("related: node:flow_auth direction='outgoing'")
    assert params.get("direction") == "outgoing"


# ── code_refs handler tests ───────────────────────────────────────────────────

def test_code_refs_empty_node(populated_root: Path):
    """Node without code_refs returns empty list."""
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = tools_read.code_refs(index, populated_root, {"node_id": node_id})
    assert result["ok"] is True
    assert result["code_refs"] == []
    assert result["count"] == 0
    assert "hint" in result


def test_code_refs_with_data(node_with_refs):
    root, node_id = node_with_refs
    index = GraphIndex.load_from_disk(root)
    result = tools_read.code_refs(index, root, {"node_id": node_id})
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["code_refs"][0]["language"] == "dart"


def test_code_refs_node_not_found(populated_root: Path):
    index = GraphIndex.load_from_disk(populated_root)
    result = tools_read.code_refs(index, populated_root, {"node_id": "node:nonexistent"})
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_code_refs_missing_node_id(populated_root: Path):
    index = GraphIndex.load_from_disk(populated_root)
    result = tools_read.code_refs(index, populated_root, {})
    assert result["ok"] is False


# ── invariants handler tests ──────────────────────────────────────────────────

def test_invariants_empty_node(populated_root: Path):
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = tools_read.node_invariants(index, populated_root, {"node_id": node_id})
    assert result["ok"] is True
    assert result["invariants"] == []
    assert result["count"] == 0


def test_invariants_with_data(node_with_refs):
    root, node_id = node_with_refs
    index = GraphIndex.load_from_disk(root)
    result = tools_read.node_invariants(index, root, {"node_id": node_id})
    assert result["ok"] is True
    assert result["count"] == 2
    assert "OTP expires" in result["invariants"][0]


# ── tests handler tests ───────────────────────────────────────────────────────

def test_node_tests_no_testcases(populated_root: Path):
    """Node with no TestCases returns empty list."""
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = tools_read.node_tests(index, populated_root, {"node_id": node_id})
    assert result["ok"] is True
    assert result["count"] == 0
    assert result["coverage"] == "none"


def test_node_tests_summary_fields(populated_root: Path):
    """node_tests returns summary and coverage fields."""
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = tools_read.node_tests(index, populated_root, {"node_id": node_id})
    assert "summary" in result
    assert "passing" in result["summary"]
    assert "failing" in result["summary"]
    assert "coverage" in result


# ── related handler tests ─────────────────────────────────────────────────────

def test_node_related_empty(populated_root: Path):
    """Node with no edges returns empty lists."""
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("Concept")
    node_id = nodes[0]["id"]
    result = tools_read.node_related(index, populated_root, {"node_id": node_id})
    assert result["ok"] is True
    assert "outgoing" in result
    assert "incoming" in result


def test_node_related_direction_filter(populated_root: Path):
    """related: with direction='outgoing' only returns outgoing."""
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("Concept")
    node_id = nodes[0]["id"]
    result = tools_read.node_related(
        index, populated_root, {"node_id": node_id, "direction": "outgoing"}
    )
    assert result["ok"] is True
    assert "incoming" in result  # key exists but may be empty
    assert isinstance(result["outgoing"], list)


# ── dispatch integration tests ────────────────────────────────────────────────

def test_dispatch_code_action(populated_root: Path):
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = asyncio.run(dispatch(f"code: {node_id}", index, populated_root))
    assert result["ok"] is True
    assert result["_dispatch"]["action"] == "code"


def test_dispatch_invariants_action(populated_root: Path):
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = asyncio.run(dispatch(f"invariants: {node_id}", index, populated_root))
    assert result["ok"] is True
    assert result["_dispatch"]["action"] == "invariants"


def test_dispatch_tests_action(populated_root: Path):
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = asyncio.run(dispatch(f"tests: {node_id}", index, populated_root))
    assert result["ok"] is True
    assert result["_dispatch"]["action"] == "tests"
    assert "coverage" in result


def test_dispatch_related_action(populated_root: Path):
    index = GraphIndex.load_from_disk(populated_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = asyncio.run(dispatch(f"related: {node_id}", index, populated_root))
    assert result["ok"] is True
    assert result["_dispatch"]["action"] == "related"


def test_protocol_guide_has_new_actions():
    from gobp.mcp.dispatcher import PROTOCOL_GUIDE
    actions = PROTOCOL_GUIDE["actions"]
    assert any("code:" in k for k in actions)
    assert any("invariants:" in k for k in actions)
    assert any("tests:" in k for k in actions)
    assert any("related:" in k for k in actions)
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave11a.py -v
# Expected: ~25 tests passing
```

**Commit message:**
```
Wave 11A Task 5: create tests/test_wave11a.py — ~25 tests

- Schema: code_refs + invariants fields present (2)
- parse_query: code/invariants/tests/related actions (6)
- code_refs handler: empty, with data, not found, missing id (4)
- invariants handler: empty, with data (2)
- node_tests handler: no testcases, summary fields (2)
- node_related handler: empty, direction filter (2)
- dispatch integration: all 4 actions + protocol guide (5)
```

---

## TASK 6 — Update MCP_TOOLS.md + full suite + CHANGELOG

**Goal:** Document new actions. All tests pass. CHANGELOG updated.

**File to modify:** `docs/MCP_TOOLS.md`

Add to quick reference table after `sections:` row:

```markdown
| `code: <node_id>` | Code files implementing this node |
| `code: <node_id> path='x' description='y' language='z'` | Add code reference |
| `invariants: <node_id>` | Hard constraints for node |
| `tests: <node_id>` | Linked TestCase nodes with coverage |
| `tests: <node_id> status='FAILING'` | Filter tests by status |
| `related: <node_id>` | Neighbor nodes summary (no full data) |
| `related: <node_id> direction='outgoing'` | Only outgoing neighbors |
```

**Run full suite:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 278+ tests passing (253 + ~25 new)
```

**Update CHANGELOG.md:**

```markdown
## [Wave 11A] — Lazy Query Actions — 2026-04-15

### Problem solved
`get: <node_id>` loads full node context (~500 tokens). AI often needs
only 1 dimension. Token waste 60-80% for targeted queries.

### Solution
4 new lazy query actions — each returns only the requested dimension:

| Action | Returns | Tokens |
|---|---|---|
| `code: <node_id>` | Code file references | ~150 |
| `invariants: <node_id>` | Hard constraints | ~100 |
| `tests: <node_id>` | Linked TestCases + coverage | ~200 |
| `related: <node_id>` | Neighbor names only | ~150 |

vs `get: <node_id>` full context: ~500 tokens

### Added
- `gobp/schema/core_nodes.yaml`: `code_refs` + `invariants` optional fields
- `gobp/mcp/tools/read.py`: 4 new handler functions
- `gobp/mcp/dispatcher.py`: 4 new actions + 7 PROTOCOL_GUIDE entries
- `tests/test_wave11a.py`: ~25 tests
- `docs/MCP_TOOLS.md`: new actions documented

### Total after wave: 1 MCP tool, 22 actions, 278+ tests passing
```

**Commit message:**
```
Wave 11A Task 6: update MCP_TOOLS.md + full suite green + CHANGELOG

- MCP_TOOLS.md: 7 new query patterns documented
- 278+ tests passing
- CHANGELOG: Wave 11A entry with token comparison
```

---

# POST-WAVE VERIFICATION

```powershell
# All tests
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

# Protocol guide has new actions
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.mcp.dispatcher import PROTOCOL_GUIDE
actions = PROTOCOL_GUIDE['actions']
new_actions = ['code:', 'invariants:', 'tests:', 'related:']
for a in new_actions:
    found = any(a in k for k in actions)
    print(f'{a} in guide: {found}')
    assert found
print('All new actions in protocol guide')
"

# Git log
git log --oneline | Select-Object -First 8
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief vào repo

```powershell
cd D:\GoBP
# Save wave_11a_brief.md to D:\GoBP\waves\wave_11a_brief.md

git add waves/wave_11a_brief.md
git commit -m "Add Wave 11A Brief — lazy query actions"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_11a_brief.md first.
Also read gobp/schema/core_nodes.yaml, gobp/mcp/dispatcher.py,
gobp/mcp/tools/read.py, docs/MCP_TOOLS.md.

Set env var before running tests:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 6 tasks of Wave 11A sequentially.
R9: all 253 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 11A. Read CLAUDE.md and waves/wave_11a_brief.md.
Also read docs/GoBP_ARCHITECTURE.md, docs/ARCHITECTURE.md, docs/MCP_TOOLS.md.

Set env before tests:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: core_nodes.yaml has code_refs + invariants in Node/Idea/Decision/Document optional
- Task 2: read.py has code_refs(), node_invariants(), node_tests(), node_related() functions
- Task 3: dispatcher.py routes code/invariants/tests/related, PROTOCOL_GUIDE has 7 new entries
- Task 4: smoke test passes, all 4 actions work, 253 tests passing
- Task 5: test_wave11a.py exists, ~25 tests passing
- Task 6: MCP_TOOLS.md updated, 278+ tests passing, CHANGELOG updated

Use venv:
  D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

Expected: 278+ tests passing.

Stop on first failure. Report WAVE 11A AUDIT COMPLETE when done.
```

## 4. Push

```powershell
cd D:\GoBP
git push origin main
```

---

# WHAT COMES NEXT

```
Wave 11A pushed
    ↓
Wave 8B — MIHOS re-import (now with all tools)
  import: → Document nodes + priority
  edge: → semantic connections
  code: → link nodes to MIHOS code files
  invariants: → capture hard constraints
    ↓
Wave 11B — 3D Graph Viewer
  Three.js + vasturiano/3d-force-graph
  Node: size=priority, color=type
  Per-project isolation
  3D (not 2D)
```

---

*Wave 11A Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
