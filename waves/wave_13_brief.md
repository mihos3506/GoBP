# WAVE 13 BRIEF — PAGINATION + UPSERT + GUARDRAILS + OBSERVABILITY

**Wave:** 13
**Title:** Cursor-based pagination, upsert-first write model, AI guardrails, observability
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 9 atomic tasks
**Estimated effort:** 5-6 hours

---

## CONTEXT

Cursor (AI dev agent) identified 4 critical gaps after using GoBP in production:

**Gap 1 — Hard limit pagination (blocking for MIHOS scale)**
```
Current: find() returns max 20 results — hard cut
Problem: MIHOS will have 500+ Feature nodes, 1000+ TestCases
         AI only sees first 20 → misses 480+ nodes
Fix:     Cursor-based pagination — AI loops safely through all data
```

**Gap 2 — No upsert (causes duplicates)**
```
Current: create: fails if exists, update: fails if not exists
Problem: AI re-imports same node → duplicate knowledge
Fix:     upsert: action with dedupe_key — merge if exists, create if not
```

**Gap 3 — No guardrails (AI can corrupt graph)**
```
Current: write succeeds or fails, no preview
Problem: AI writes wrong data silently
Fix:     dry_run=true, write response with created/updated/merged/skipped
         conflict detection, revision check
```

**Gap 4 — No observability (can't optimize)**
```
Current: no usage tracking
Problem: can't know which queries are slow or broken
Fix:     stats: action — per-action call count, avg latency, error rate
```

---

## DESIGN DECISIONS

### Pagination protocol
```
Standard page_info in all list responses:
{
  "items": [...],
  "page_info": {
    "next_cursor": "node:abc123",  # opaque cursor (last item id)
    "has_more": true,
    "total_estimate": 500,
    "page_size": 20
  }
}

Query format:
  gobp(query="find: auth page_size=50")
  gobp(query="find: auth cursor='node:abc123' page_size=50")
  gobp(query="related: node:x page_size=10")
  gobp(query="tests: node:x page_size=100")
```

Keyset pagination (not OFFSET) — stable under concurrent writes.

### Upsert protocol
```
gobp(query="upsert:Node dedupe_key='name' name='Auth Flow' priority='critical' session_id='x'")
gobp(query="upsert:Feature dedupe_key='name' name='Login' status='ACTIVE' session_id='x'")
gobp(query="upsert:Decision dedupe_key='topic' topic='auth:login' what='OTP' why='SMS unreliable'")

Response:
{
  "ok": true,
  "action": "created" | "updated" | "merged" | "skipped",
  "node_id": "node:abc123",
  "changed_fields": ["status", "priority"],
  "conflicts": [],
  "revision": 2
}
```

dedupe_key = field name to match on. If existing node has same value → update instead of create.

### Guardrails
```
dry_run support:
  gobp(query="upsert:Node name='x' session_id='y' dry_run=true")
  → Returns what would happen, no writes

All write responses include:
  action: created/updated/merged/skipped
  changed_fields: list of modified fields
  conflicts: list of conflicting values
  revision: incrementing counter per node
```

### Observability
```
gobp(query="stats:")           → all action stats
gobp(query="stats: find")      → stats for find action only
gobp(query="stats: reset")     → reset counters

Response:
{
  "ok": true,
  "stats": {
    "find": {"calls": 142, "avg_ms": 0.8, "errors": 0, "last_called": "..."},
    "create": {"calls": 38, "avg_ms": 210, "errors": 2, "last_called": "..."},
    ...
  },
  "top_queries": ["find: auth", "get: node:flow_auth", ...],
  "session": {"started": "...", "total_calls": 180}
}
```

Stats stored in-memory (reset on server restart). Not persisted — use for current session optimization only.

---

## CURSOR EXECUTION RULES

R1-R9 standard.
R9: All 290+ existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 290+ tests passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/mcp/dispatcher.py` | Add upsert + stats actions |
| 3 | `gobp/mcp/tools/read.py` | Add pagination to find/related/tests |
| 4 | `gobp/mcp/tools/write.py` | Add guardrails to write responses |
| 5 | `gobp/mcp/server.py` | Add stats middleware |
| 6 | `docs/MCP_TOOLS.md` | Update protocol |
| 7 | `waves/wave_13_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Add pagination to find()

**Goal:** `find:` returns paginated results with cursor-based page_info.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `find()` in full before editing.**

Replace the return statement in `find()`:

```python
def find(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Search nodes by keyword with cursor-based pagination.

    Args:
        query: Search keyword (required)
        type: Node type filter (optional)
        limit: Deprecated alias for page_size
        page_size: Max results per page (default 20, max 100)
        cursor: Opaque pagination cursor (node id of last item)
        sort: Sort field (default: 'id')
        direction: 'asc' or 'desc' (default: 'asc')
    """
    query_str = args.get("query", "")
    type_filter = args.get("type")
    page_size = min(int(args.get("page_size", args.get("limit", 20))), 100)
    cursor = args.get("cursor")
    sort_field = args.get("sort", "id")
    direction = args.get("direction", "asc")

    # Get all matching nodes
    if not query_str:
        candidates = index.all_nodes()
    else:
        # Try PostgreSQL FTS first
        try:
            from gobp.core import db as _db
            node_ids = _db.query_nodes_fts(project_root, query_str, type_filter, limit=1000)
            if not node_ids:
                node_ids = _db.query_nodes_substring(project_root, query_str, type_filter, limit=1000)
            candidates = [index.get_node(nid) for nid in node_ids if index.get_node(nid)]
        except Exception:
            # Fallback: in-memory search
            candidates = [
                n for n in index.all_nodes()
                if query_str.lower() in n.get("id", "").lower()
                or query_str.lower() in n.get("name", "").lower()
                or query_str.lower() in n.get("topic", "").lower()
                or query_str.lower() in n.get("subject", "").lower()
            ]

    # Apply type filter
    if type_filter:
        candidates = [n for n in candidates if n.get("type") == type_filter]

    # Sort
    reverse = direction == "desc"
    candidates.sort(key=lambda n: n.get(sort_field, n.get("id", "")), reverse=reverse)

    # Apply cursor (keyset pagination)
    total_estimate = len(candidates)
    if cursor:
        try:
            cursor_idx = next(i for i, n in enumerate(candidates) if n.get("id") == cursor)
            candidates = candidates[cursor_idx + 1:]
        except StopIteration:
            candidates = []

    # Page
    page = candidates[:page_size]
    has_more = len(candidates) > page_size
    next_cursor = page[-1].get("id") if has_more and page else None

    # Format results
    matches = [
        {
            "id": n.get("id"),
            "type": n.get("type"),
            "name": n.get("name", ""),
            "status": n.get("status", ""),
            "priority": n.get("priority", "medium"),
        }
        for n in page
    ]

    return {
        "ok": True,
        "matches": matches,
        "count": len(matches),
        "page_info": {
            "next_cursor": next_cursor,
            "has_more": has_more,
            "total_estimate": total_estimate,
            "page_size": page_size,
        },
    }
```

**Acceptance criteria:**
- `find: auth` returns `page_info` with `next_cursor`, `has_more`, `total_estimate`
- `find: auth cursor='node:abc' page_size=10` returns next page
- `page_size` capped at 100
- Existing `matches` key preserved (backward compatible)
- `limit` param still works as alias for `page_size`

**Commit message:**
```
Wave 13 Task 1: add cursor-based pagination to find()

- page_size param (default 20, max 100) replaces hard limit
- cursor param for keyset pagination (stable under concurrent writes)
- page_info: next_cursor, has_more, total_estimate, page_size
- limit= still works as alias for page_size (backward compat)
- sort + direction params
```

---

## TASK 2 — Add pagination to related() and tests()

**Goal:** `related:` and `tests:` support pagination.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `node_related()` and `node_tests()` in full.**

**Update `node_related()`** — add page_info to return:

```python
    # After building outgoing + incoming lists, add pagination:
    page_size = min(int(args.get("page_size", 50)), 200)
    cursor = args.get("cursor")
    direction_filter = args.get("direction", "both")

    all_items = []
    if direction_filter in ("outgoing", "both"):
        all_items.extend([{**item, "_dir": "outgoing"} for item in outgoing])
    if direction_filter in ("incoming", "both"):
        all_items.extend([{**item, "_dir": "incoming"} for item in incoming])

    total_estimate = len(all_items)

    # Apply cursor
    if cursor:
        try:
            idx = next(i for i, item in enumerate(all_items) if item.get("node_id") == cursor)
            all_items = all_items[idx + 1:]
        except StopIteration:
            all_items = []

    page = all_items[:page_size]
    has_more = len(all_items) > page_size
    next_cursor = page[-1].get("node_id") if has_more and page else None

    page_outgoing = [i for i in page if i.get("_dir") == "outgoing"]
    page_incoming = [i for i in page if i.get("_dir") == "incoming"]
    # Remove _dir from output
    for i in page_outgoing + page_incoming:
        i.pop("_dir", None)

    return {
        "ok": True,
        "node_id": node_id,
        "node_name": node.get("name", ""),
        "node_type": node.get("type", ""),
        "outgoing": page_outgoing,
        "incoming": page_incoming,
        "count": len(page),
        "page_info": {
            "next_cursor": next_cursor,
            "has_more": has_more,
            "total_estimate": total_estimate,
            "page_size": page_size,
        },
    }
```

**Update `node_tests()`** — add page_info:

```python
    page_size = min(int(args.get("page_size", 50)), 200)
    cursor = args.get("cursor")

    total_estimate = len(test_cases)

    if cursor:
        try:
            idx = next(i for i, t in enumerate(test_cases) if t.get("id") == cursor)
            test_cases = test_cases[idx + 1:]
        except StopIteration:
            test_cases = []

    page = test_cases[:page_size]
    has_more = len(test_cases) > page_size
    next_cursor = page[-1].get("id") if has_more and page else None

    # ... rest of return with page_info added
    return {
        "ok": True,
        "node_id": node_id,
        "node_name": node.get("name", ""),
        "node_type": node.get("type", ""),
        "test_cases": page,
        "count": len(page),
        "summary": {...},
        "coverage": ...,
        "page_info": {
            "next_cursor": next_cursor,
            "has_more": has_more,
            "total_estimate": total_estimate,
            "page_size": page_size,
        },
    }
```

**Commit message:**
```
Wave 13 Task 2: add pagination to related() and node_tests()

- related(): page_size, cursor, page_info
- node_tests(): page_size, cursor, page_info
- Both cap page_size at 200
- Keyset pagination by node_id
```

---

## TASK 3 — Add guardrails to write responses

**Goal:** All write operations return `action`, `changed_fields`, `conflicts`, `revision`.

**File to modify:** `gobp/mcp/tools/write.py`

**Re-read `write.py` in full before editing.**

**Update `node_upsert()` response:**

```python
    # After successful write, determine what changed:
    existing = index.get_node(node_id) if node_id else None
    
    if existing:
        changed_fields = [
            k for k, v in new_fields.items()
            if existing.get(k) != v and k not in ("updated", "session_id")
        ]
        write_action = "updated" if changed_fields else "skipped"
    else:
        changed_fields = list(new_fields.keys())
        write_action = "created"

    # Include in response:
    return {
        "ok": True,
        "node_id": result_node_id,
        "action": write_action,           # created | updated | skipped
        "changed_fields": changed_fields,
        "conflicts": [],                   # future: optimistic locking
        "revision": _get_revision(result_node_id, project_root),
    }
```

**Add `_get_revision()` helper:**

```python
def _get_revision(node_id: str, project_root: Path) -> int:
    """Get revision count from history log for this node."""
    try:
        from gobp.core.history import count_events_for_node
        return count_events_for_node(project_root, node_id)
    except Exception:
        return 1
```

**Update `decision_lock()` response similarly.**

**Update `session_log()` response similarly.**

**Commit message:**
```
Wave 13 Task 3: add guardrails to write responses

- node_upsert: action (created/updated/skipped), changed_fields, conflicts, revision
- decision_lock: action + changed_fields
- session_log: action field
- _get_revision(): reads history log for node revision count
```

---

## TASK 4 — Add dry_run support

**Goal:** `dry_run=true` in any write query returns preview without writing.

**File to modify:** `gobp/mcp/dispatcher.py`

**Re-read `dispatch()` create/update/lock/session handlers.**

**Add dry_run check before each write call:**

```python
        elif action in ("create", "upsert"):
            # ... build args ...
            
            # dry_run support
            if params.get("dry_run") in ("true", "1", True):
                existing = index.get_node(args.get("node_id", ""))
                result = {
                    "ok": True,
                    "dry_run": True,
                    "would_action": "updated" if existing else "created",
                    "node_id": args.get("node_id", "(auto-generated)"),
                    "name": args.get("name", ""),
                    "type": node_type,
                    "message": "dry_run=true: no changes made",
                }
            else:
                result = tools_write.node_upsert(index, project_root, args)
```

Apply same pattern to `lock:` and `session:` actions.

**Update PROTOCOL_GUIDE:**

```python
"create:Node name='x' session_id='y' dry_run=true": "Preview without writing",
"upsert:Node dedupe_key='name' name='x' session_id='y'": "Create or update by key",
```

**Commit message:**
```
Wave 13 Task 4: add dry_run support to write actions

- create:/upsert:/lock:/session: accept dry_run=true param
- dry_run=true: returns would_action preview, no disk writes
- PROTOCOL_GUIDE updated with dry_run examples
```

---

## TASK 5 — Add upsert: action

**Goal:** `upsert:` action creates or updates based on dedupe_key.

**File to modify:** `gobp/mcp/dispatcher.py`

**Add `upsert` action handler in `dispatch()`:**

```python
        elif action == "upsert":
            node_type = node_type or params.pop("type", "Node")
            dedupe_key = params.pop("dedupe_key", "name")
            dedupe_value = params.get(dedupe_key, "")
            session_id = params.get("session_id", "")
            
            # dry_run check
            is_dry = params.get("dry_run") in ("true", "1", True)
            
            # Find existing node by dedupe_key
            existing_node = None
            if dedupe_value:
                candidates = index.nodes_by_type(node_type)
                existing_node = next(
                    (n for n in candidates if str(n.get(dedupe_key, "")) == str(dedupe_value)),
                    None
                )
            
            if is_dry:
                result = {
                    "ok": True,
                    "dry_run": True,
                    "would_action": "updated" if existing_node else "created",
                    "dedupe_key": dedupe_key,
                    "dedupe_value": dedupe_value,
                    "existing_id": existing_node.get("id") if existing_node else None,
                    "message": "dry_run=true: no changes made",
                }
            else:
                node_id = existing_node.get("id") if existing_node else None
                
                args = {
                    "node_id": node_id,
                    "type": node_type,
                    "name": params.get("name", dedupe_value),
                    "fields": {
                        k: v for k, v in params.items()
                        if k not in ("name", "type", "session_id", "dry_run")
                    },
                    "session_id": session_id,
                }
                
                result = tools_write.node_upsert(index, project_root, args)
                if result.get("ok"):
                    result["dedupe_key"] = dedupe_key
                    result["dedupe_value"] = dedupe_value
                    if not result.get("action"):
                        result["action"] = "updated" if existing_node else "created"
```

**Acceptance criteria:**
- `upsert:Node dedupe_key='name' name='Auth Flow'` creates if not exists
- Same query again → updates existing node (no duplicate)
- `dry_run=true` → preview only
- Response includes `action: created|updated`, `dedupe_key`, `dedupe_value`

**Commit message:**
```
Wave 13 Task 5: add upsert: action with dedupe_key

- upsert: finds existing node by dedupe_key value
- If found: update. If not: create. No duplicates.
- dry_run=true: preview without writing
- Response: action (created/updated), dedupe_key, dedupe_value, existing_id
- Fixes: AI re-importing same node creates duplicates
```

---

## TASK 6 — Add in-memory stats tracking

**Goal:** Track per-action call count, latency, error rate in server memory.

**File to modify:** `gobp/mcp/server.py`

**Re-read `server.py` in full before editing.**

**Add stats module at top of server.py:**

```python
# ── In-memory stats ───────────────────────────────────────────────────────────
import time as _time
from collections import defaultdict as _defaultdict

_stats: dict[str, dict] = _defaultdict(lambda: {
    "calls": 0,
    "total_ms": 0.0,
    "errors": 0,
    "last_called": None,
    "recent_queries": [],
})
_stats_session_start: float = _time.time()


def _record_stat(action: str, elapsed_ms: float, error: bool = False, query: str = "") -> None:
    """Record a tool call stat."""
    s = _stats[action]
    s["calls"] += 1
    s["total_ms"] += elapsed_ms
    if error:
        s["errors"] += 1
    s["last_called"] = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
    if query:
        s["recent_queries"] = ([query] + s["recent_queries"])[:5]


def _get_stats_summary() -> dict:
    """Return stats summary for all actions."""
    result = {}
    total_calls = 0
    for action, s in _stats.items():
        calls = s["calls"]
        total_calls += calls
        avg_ms = round(s["total_ms"] / calls, 1) if calls > 0 else 0
        result[action] = {
            "calls": calls,
            "avg_ms": avg_ms,
            "errors": s["errors"],
            "last_called": s["last_called"],
            "recent_queries": s["recent_queries"],
        }
    return {
        "actions": result,
        "session": {
            "started": _time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                _time.gmtime(_stats_session_start)
            ),
            "total_calls": total_calls,
            "uptime_seconds": round(_time.time() - _stats_session_start),
        }
    }
```

**Wrap `call_tool()` with timing:**

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    global _index, _project_root
    
    query = arguments.get("query", "overview:")
    
    # Handle stats: action before dispatch
    from gobp.mcp.dispatcher import parse_query as _pq
    action, _, _ = _pq(query)
    
    if action == "stats":
        # Handle stats query directly
        parts = query.split(":", 1)
        sub = parts[1].strip() if len(parts) > 1 else ""
        if sub == "reset":
            _stats.clear()
            result = {"ok": True, "message": "Stats reset"}
        elif sub and sub != "":
            action_stats = _stats.get(sub, {})
            result = {"ok": True, "action": sub, "stats": action_stats}
        else:
            result = {"ok": True, **_get_stats_summary()}
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    # ... existing lazy load index ...
    
    start = _time.time()
    error = False
    try:
        from gobp.mcp.dispatcher import dispatch
        result = await dispatch(query, _index, _project_root)
        if not result.get("ok"):
            error = True
    except Exception as e:
        error = True
        result = {"ok": False, "error": str(e)}
    finally:
        elapsed = (_time.time() - start) * 1000
        _record_stat(action, elapsed, error, query[:100])
    
    # ... index reload for writes ...
    
    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
```

**Acceptance criteria:**
- `gobp(query="stats:")` returns per-action stats
- `gobp(query="stats: find")` returns find-specific stats
- `gobp(query="stats: reset")` resets counters
- Stats reset on server restart (in-memory only)
- No performance impact on normal queries (< 1ms overhead)

**Commit message:**
```
Wave 13 Task 6: add in-memory stats tracking to server.py

- _record_stat(): tracks calls, total_ms, errors, last_called per action
- _get_stats_summary(): aggregates all action stats
- stats: action handled in call_tool() before dispatch
- stats: reset clears all counters
- Overhead: < 1ms per call
```

---

## TASK 7 — Add stats: to dispatcher PROTOCOL_GUIDE

**Goal:** `stats:` visible in protocol guide. Add to dispatcher routing.

**File to modify:** `gobp/mcp/dispatcher.py`

**Add to PROTOCOL_GUIDE:**

```python
"stats:":              "All action stats (calls, latency, errors)",
"stats: <action>":     "Stats for specific action (e.g. stats: find)",
"stats: reset":        "Reset all stat counters",
```

**Note:** `stats:` is handled in `server.py` before `dispatch()` is called. Dispatcher does not need to route it — just add to PROTOCOL_GUIDE for AI visibility.

Also add `upsert:` to PROTOCOL_GUIDE if not already there from Task 5.

**Commit message:**
```
Wave 13 Task 7: add stats/upsert to PROTOCOL_GUIDE

- stats: / stats: <action> / stats: reset in protocol guide
- upsert: with dedupe_key in protocol guide
- AI can discover both actions via overview:
```

---

## TASK 8 — Write tests/test_wave13.py

**Goal:** Tests for all Wave 13 changes.

**File to create:** `tests/test_wave13.py`

```python
"""Tests for Wave 13: pagination, upsert, guardrails, observability."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch, parse_query
from gobp.mcp.tools import read as tools_read
from gobp.mcp.tools import write as tools_write


# ── Pagination tests ──────────────────────────────────────────────────────────

def test_find_returns_page_info(gobp_root: Path):
    """find() returns page_info with pagination fields."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "unit", "page_size": 5})
    assert result["ok"] is True
    assert "page_info" in result
    pi = result["page_info"]
    assert "next_cursor" in pi
    assert "has_more" in pi
    assert "total_estimate" in pi
    assert "page_size" in pi


def test_find_page_size_limit(gobp_root: Path):
    """find() page_size capped at 100."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "", "page_size": 999})
    assert result["page_info"]["page_size"] <= 100


def test_find_cursor_pagination(gobp_root: Path):
    """find() cursor returns next page."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    # Get first page
    r1 = tools_read.find(index, gobp_root, {"query": "", "page_size": 5})
    assert r1["ok"] is True

    if not r1["page_info"]["has_more"]:
        pytest.skip("Not enough nodes to test pagination")

    cursor = r1["page_info"]["next_cursor"]
    assert cursor is not None

    # Get second page
    r2 = tools_read.find(index, gobp_root, {"query": "", "page_size": 5, "cursor": cursor})
    assert r2["ok"] is True
    # Second page should not overlap first page
    ids1 = {m["id"] for m in r1["matches"]}
    ids2 = {m["id"] for m in r2["matches"]}
    assert ids1.isdisjoint(ids2), "Pages should not overlap"


def test_find_backward_compat_matches_key(gobp_root: Path):
    """find() still returns 'matches' key (backward compat)."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "unit"})
    assert "matches" in result  # NOT 'nodes' — known decision dec:d001


def test_related_returns_page_info(gobp_root: Path):
    """node_related() returns page_info."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = tools_read.node_related(index, gobp_root, {"node_id": node_id})
    assert result["ok"] is True
    assert "page_info" in result


def test_tests_returns_page_info(gobp_root: Path):
    """node_tests() returns page_info."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    nodes = index.nodes_by_type("TestKind")
    node_id = nodes[0]["id"]
    result = tools_read.node_tests(index, gobp_root, {"node_id": node_id})
    assert result["ok"] is True
    assert "page_info" in result


# ── Guardrails tests ──────────────────────────────────────────────────────────

def test_node_upsert_returns_action_field(gobp_root: Path):
    """node_upsert() returns action: created/updated/skipped."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='guardrails test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        f"create:Node name='Test Node' session_id='{session_id}'",
        index, gobp_root
    ))
    assert result["ok"] is True
    assert "action" in result
    assert result["action"] in ("created", "updated", "skipped")


def test_node_upsert_returns_changed_fields(gobp_root: Path):
    """node_upsert() returns changed_fields list."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='changed fields test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        f"create:Node name='Changed Fields Test' session_id='{session_id}'",
        index, gobp_root
    ))
    assert result["ok"] is True
    assert "changed_fields" in result
    assert isinstance(result["changed_fields"], list)


# ── dry_run tests ─────────────────────────────────────────────────────────────

def test_dry_run_no_write(gobp_root: Path):
    """dry_run=true returns preview without writing."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='dry run test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    before_count = len(index.all_nodes())

    result = asyncio.run(dispatch(
        f"create:Node name='Dry Run Node' session_id='{session_id}' dry_run=true",
        index, gobp_root
    ))
    assert result["ok"] is True
    assert result.get("dry_run") is True
    assert "would_action" in result

    # No new nodes written
    index2 = GraphIndex.load_from_disk(gobp_root)
    assert len(index2.all_nodes()) == before_count


# ── upsert: tests ─────────────────────────────────────────────────────────────

def test_upsert_creates_if_not_exists(gobp_root: Path):
    """upsert: creates node if dedupe_key not found."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='upsert test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        f"upsert:Node dedupe_key='name' name='Unique Feature' session_id='{session_id}'",
        index, gobp_root
    ))
    assert result["ok"] is True
    assert result.get("action") == "created"


def test_upsert_updates_if_exists(gobp_root: Path):
    """upsert: updates node if dedupe_key matches existing."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='upsert update test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    # Create first
    r1 = asyncio.run(dispatch(
        f"upsert:Node dedupe_key='name' name='Dedup Node' session_id='{session_id}'",
        index, gobp_root
    ))
    assert r1["action"] == "created"
    node_id = r1["node_id"]

    index = GraphIndex.load_from_disk(gobp_root)

    # Upsert again — should update, not create new
    r2 = asyncio.run(dispatch(
        f"upsert:Node dedupe_key='name' name='Dedup Node' priority='critical' session_id='{session_id}'",
        index, gobp_root
    ))
    assert r2["ok"] is True
    assert r2.get("action") == "updated"
    assert r2["node_id"] == node_id  # same node, not new


def test_upsert_dry_run(gobp_root: Path):
    """upsert: with dry_run=true returns preview."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='upsert dry run'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        f"upsert:Node dedupe_key='name' name='Dry Node' session_id='{session_id}' dry_run=true",
        index, gobp_root
    ))
    assert result["ok"] is True
    assert result.get("dry_run") is True
    assert "would_action" in result


# ── Protocol guide tests ──────────────────────────────────────────────────────

def test_protocol_guide_has_stats():
    from gobp.mcp.dispatcher import PROTOCOL_GUIDE
    actions = PROTOCOL_GUIDE["actions"]
    assert any("stats:" in k for k in actions)


def test_protocol_guide_has_upsert():
    from gobp.mcp.dispatcher import PROTOCOL_GUIDE
    actions = PROTOCOL_GUIDE["actions"]
    assert any("upsert:" in k for k in actions)
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave13.py -v
# Expected: ~20 tests passing
```

**Commit message:**
```
Wave 13 Task 8: create tests/test_wave13.py — ~20 tests

- Pagination: find page_info, page_size cap, cursor pagination,
  backward compat matches key, related/tests page_info (6)
- Guardrails: action field, changed_fields, dry_run no write (3)
- Upsert: creates if not exists, updates if exists, dry_run (3)
- Protocol guide: stats + upsert visible (2)
```

---

## TASK 9 — Update MCP_TOOLS.md + full suite + CHANGELOG

**File to modify:** `docs/MCP_TOOLS.md`

Add to quick reference table:

```markdown
| `find: <keyword> page_size=50` | Paginated search |
| `find: <keyword> cursor='node:x' page_size=50` | Next page |
| `upsert:<Type> dedupe_key='name' name='x' session_id='y'` | Create or update by key |
| `upsert:<Type> ... dry_run=true` | Preview upsert without writing |
| `create:<Type> ... dry_run=true` | Preview create without writing |
| `stats:` | All action stats (calls, latency, errors) |
| `stats: <action>` | Stats for specific action |
| `stats: reset` | Reset stat counters |
```

**Run full suite:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 310+ tests (290 + ~20 new)
```

**Update CHANGELOG.md:**

```markdown
## [Wave 13] — Pagination + Upsert + Guardrails + Observability — 2026-04-15

### Problems solved
- Hard limit pagination: AI missed nodes when results > 20
- No upsert: AI re-importing same node created duplicates
- No guardrails: AI could write wrong data silently
- No observability: couldn't optimize slow queries

### Added
- Cursor-based pagination for find(), related(), tests()
- upsert: action with dedupe_key (create or update, no duplicates)
- dry_run=true support for all write actions
- Write response guardrails: action, changed_fields, conflicts, revision
- In-memory stats tracking: calls, avg_ms, errors per action
- stats: action (overview + per-action + reset)

### Protocol additions
  find: auth page_size=50              → paginated search
  find: auth cursor='node:x'           → next page
  upsert:Node dedupe_key='name' name='x' → create or update
  create:Node ... dry_run=true         → preview
  stats:                               → observability

### page_info format
  { next_cursor, has_more, total_estimate, page_size }

### Total after wave: 1 MCP tool, 25 actions, 310+ tests
```

**Commit message:**
```
Wave 13 Task 9: MCP_TOOLS.md updated + full suite green + CHANGELOG

- 310+ tests passing
- MCP_TOOLS.md: pagination + upsert + dry_run + stats documented
- CHANGELOG: Wave 13 entry
```

---

# POST-WAVE VERIFICATION

```powershell
# All tests
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

# Pagination works
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
        r = await dispatch('find: unit page_size=3', index, root)
        assert r['ok']
        assert 'page_info' in r
        print('Pagination OK:', r['page_info'])

asyncio.run(test())
"

# Upsert deduplication
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.mcp.dispatcher import parse_query
a, _, p = parse_query(\"upsert:Node dedupe_key='name' name='Test'\")
assert a == 'upsert'
assert p['dedupe_key'] == 'name'
print('Upsert parse OK')
"

# Stats tracking
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.mcp.dispatcher import PROTOCOL_GUIDE
assert any('stats:' in k for k in PROTOCOL_GUIDE['actions'])
assert any('upsert:' in k for k in PROTOCOL_GUIDE['actions'])
print('Protocol guide OK')
"
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief vào repo

```powershell
cd D:\GoBP
# Save wave_13_brief.md to D:\GoBP\waves\wave_13_brief.md

git add waves/wave_13_brief.md
git commit -m "Add Wave 13 Brief — pagination + upsert + guardrails + observability"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_13_brief.md first.
Also read gobp/mcp/tools/read.py, gobp/mcp/tools/write.py,
gobp/mcp/dispatcher.py, gobp/mcp/server.py, docs/MCP_TOOLS.md.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 9 tasks of Wave 13 sequentially.
R9: all 290+ existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 13. Read CLAUDE.md and waves/wave_13_brief.md.
Also read docs/GoBP_ARCHITECTURE.md, docs/MCP_TOOLS.md.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: find() returns page_info with next_cursor/has_more/total_estimate/page_size
          cursor param for keyset pagination, page_size capped at 100
- Task 2: related() + node_tests() return page_info
- Task 3: node_upsert() returns action/changed_fields/conflicts/revision
- Task 4: dry_run=true returns preview, no writes, would_action field
- Task 5: upsert: action with dedupe_key — creates or updates, no duplicates
- Task 6: stats tracking in server.py, stats: action works
- Task 7: PROTOCOL_GUIDE has stats: and upsert: entries
- Task 8: test_wave13.py exists, ~20 tests passing
- Task 9: 310+ tests passing, MCP_TOOLS.md updated, CHANGELOG updated

Expected: 310+ tests passing.
Report WAVE 13 AUDIT COMPLETE when done.
```

## 4. Push

```powershell
cd D:\GoBP
git push origin main
```

---

# WHAT COMES NEXT

```
Wave 13 pushed
    ↓
Wave 14 — Schema governance + Protocol versioning + Access model
  - validate: schema-docs drift check
  - version: action
  - read-only mode + role-based access
    ↓
Wave 8B — MIHOS import (with full toolset)
  - upsert: for idempotent import
  - pagination for large result sets
  - stats: to measure import performance
```

---

*Wave 13 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
