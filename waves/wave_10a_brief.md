# WAVE 10A BRIEF — GOBP() SINGLE TOOL + STRUCTURED QUERY PROTOCOL

**Wave:** 10A
**Title:** Collapse 14 MCP tools → 1 gobp() tool with structured query protocol
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 8 atomic tasks
**Estimated effort:** 3-4 hours

---

## CONTEXT

**Problem:** Claude.ai web exposes only 5/14 GoBP tools. AI connecting via Claude.ai cannot call write tools (node_upsert, decision_lock, session_log, etc.) — they are invisible.

**Root cause:** Claude.ai platform filters MCP tools for token optimization. Not a GoBP bug. Not fixable from GoBP server side via tool count reduction alone.

**Solution:** Collapse 14 tools → 1 `gobp()` tool with structured query protocol.

```
Before:  find(query="login")           → only visible if platform exposes it
After:   gobp(query="find: login")     → always visible, 1 tool
```

**Protocol:**
```
gobp(query="<action>:<type> <key>='<value>' ...")

Examples:
  gobp(query="overview:")
  gobp(query="find: login")
  gobp(query="find:Decision auth")
  gobp(query="get: node:feat_login")
  gobp(query="create:Idea name='use OTP' subject='auth:login' session_id='session:x'")
  gobp(query="lock:Decision topic='auth:login' what='use OTP' why='SMS unreliable'")
  gobp(query="session:start actor='cursor' goal='implement login'")
  gobp(query="session:end outcome='done' handoff='next: test'")
  gobp(query="validate: nodes")
  gobp(query="extract: lessons")
  gobp(query="sections: doc:wave_4_brief")
  gobp(query="import: docs/DOC-07.md")
  gobp(query="commit: imp:2026-04-15_DOC-07")
```

**Key design decisions:**
- Dispatcher uses deterministic pattern matching — no AI, no ambiguity
- Tool functions (read.py, write.py, etc.) unchanged — zero regression risk
- Existing tests unchanged — test functions directly, not via dispatcher
- `gobp_overview()` response includes protocol guide — AI orients immediately
- Dispatch log in response — audit gate can verify routing

**In scope:**
- `gobp/mcp/dispatcher.py` — query parser + router
- `gobp/mcp/server.py` — collapse to 1 tool
- `gobp/mcp/tools/read.py` — gobp_overview adds interface guide
- `docs/MCP_TOOLS.md` — add gobp() protocol spec
- `tests/test_dispatcher.py` — dispatcher tests
- `.gobp/` data unchanged

**NOT in scope:**
- AI intent parser (natural language without prefix)
- Any changes to tool functions
- Any changes to existing tests
- SQLite or performance changes

---

## CURSOR EXECUTION RULES

### R1 — Sequential execution
Tasks 1 → 8 in order.

### R2 — Discovery before creation
Explorer subagent before creating any file.

### R3 — 1 task = 1 commit
Tests pass → commit with exact message.

### R4 — Docs are supreme authority
Conflict with `docs/MCP_TOOLS.md` → docs win, STOP.

### R5 — Document disagreement = STOP
Believe doc has error → STOP, report, wait.

### R6 — 3 retries = STOP
Test fails 3 times → STOP, report.

### R7 — No scope creep
No natural language parsing, no AI intent, no tool function changes.

### R8 — Brief code is authoritative
Disagree → STOP and escalate.

### R9 — Backward compatibility mandatory
All 217 existing tests must pass after every task.

---

## STOP REPORT FORMAT

```
STOP — Wave 10A Task <N>
Rule triggered: R<N>
Completed: Tasks 1–<N-1>
Current task: <N> — <title>
What went wrong: <exact error>
Git state: staged=<list> unstaged=<list>
Need from CEO/CTO: <question>
```

---

## AUTHORITATIVE SOURCE

- `gobp/mcp/tools/read.py` — existing tool functions
- `gobp/mcp/tools/write.py` — existing tool functions
- `gobp/mcp/server.py` — current server to replace
- `docs/MCP_TOOLS.md` — tool specs (update, don't break)
- `tests/conftest.py` — fixture pattern

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 217 tests passing
```

---

## REQUIRED READING — WAVE START

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/mcp/server.py` | Current server to replace |
| 3 | `gobp/mcp/tools/read.py` | Tool function signatures |
| 4 | `gobp/mcp/tools/write.py` | Tool function signatures |
| 5 | `gobp/mcp/tools/maintain.py` | validate signature |
| 6 | `gobp/mcp/tools/advanced.py` | lessons_extract signature |
| 7 | `gobp/mcp/tools/import_.py` | import signatures |
| 8 | `docs/MCP_TOOLS.md` | Current spec |
| 9 | `waves/wave_10a_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Create gobp/mcp/dispatcher.py

**Goal:** Query parser + deterministic router. No AI, no ambiguity.

**File to create:** `gobp/mcp/dispatcher.py`

```python
"""GoBP query dispatcher.

Parses structured query protocol and routes to correct tool handler.

Protocol:
    gobp(query="<action>:<type> <key>='<value>' ...")

Actions:
    overview    → gobp_overview()
    find        → find()
    get         → context() or signature()
    create      → node_upsert()
    update      → node_upsert() with existing id
    lock        → decision_lock()
    session     → session_log()
    import      → import_proposal()
    commit      → import_commit()
    validate    → validate()
    extract     → lessons_extract()
    sections    → doc_sections()
    recent      → session_recent()
    decisions   → decisions_for()
    signature   → signature()

Examples:
    "overview:"
    "find: login"
    "find:Decision auth"
    "get: node:feat_login"
    "create:Idea name='use OTP' subject='auth:login' session_id='session:x'"
    "lock:Decision topic='auth:login' what='use OTP' why='SMS unreliable' locked_by='CEO,Claude'"
    "session:start actor='cursor' goal='implement login'"
    "session:end outcome='done' handoff='next: write tests'"
    "validate: nodes"
    "extract: lessons"
    "sections: doc:wave_4_brief"
    "recent: 3"
    "decisions: auth:login.method"
    "signature: node:feat_login"
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex


# ── Query parser ──────────────────────────────────────────────────────────────

def parse_query(query: str) -> tuple[str, str, dict[str, Any]]:
    """Parse query string into (action, node_type, params).

    Format: "<action>:<type> <key>='<value>' ..."
    or:     "<action>: <bare_value>"

    Returns:
        (action, node_type, params)
        action: lowercase action string
        node_type: node type if specified, else ""
        params: dict of key=value pairs, or {"query": bare_value}
    """
    query = query.strip()
    if not query:
        return "overview", "", {}

    # Find action:type separator
    colon_idx = query.find(":")
    if colon_idx == -1:
        # No colon — treat as find query
        return "find", "", {"query": query}

    action_part = query[:colon_idx].strip().lower()
    rest = query[colon_idx + 1:].strip()

    # Split action and node_type (e.g. "find:Decision" → action="find", type="Decision")
    action_parts = action_part.split(None, 1)
    action = action_parts[0]
    node_type = action_parts[1] if len(action_parts) > 1 else ""

    if not rest:
        return action, node_type, {}

    # Parse params: key='value' or key=value or bare value
    params: dict[str, Any] = {}

    # Try key=value parsing first
    kv_pattern = re.compile(r"(\w+)='([^']*)'|(\w+)=\"([^\"]*)\"|(\w+)=(\S+)")
    matches = list(kv_pattern.finditer(rest))

    if matches:
        for m in matches:
            if m.group(1) is not None:
                params[m.group(1)] = m.group(2)
            elif m.group(3) is not None:
                params[m.group(3)] = m.group(4)
            elif m.group(5) is not None:
                params[m.group(5)] = m.group(6)
    else:
        # No key=value pairs — bare value
        params["query"] = rest

    return action, node_type, params


# ── Dispatch router ───────────────────────────────────────────────────────────

async def dispatch(
    query: str,
    index: GraphIndex,
    project_root: Path,
) -> dict[str, Any]:
    """Route parsed query to correct tool handler.

    Returns tool result dict with added _dispatch_info for audit.
    """
    from gobp.mcp.tools import read as tools_read
    from gobp.mcp.tools import write as tools_write
    from gobp.mcp.tools import maintain as tools_maintain
    from gobp.mcp.tools import import_ as tools_import
    from gobp.mcp.tools.advanced import lessons_extract

    action, node_type, params = parse_query(query)
    dispatch_info = {"action": action, "type": node_type, "params": params}

    try:
        # ── Read actions ──────────────────────────────────────────────────────
        if action == "overview":
            result = tools_read.gobp_overview(index, project_root, params)

        elif action == "find":
            args: dict[str, Any] = {}
            if "query" in params:
                args["query"] = params["query"]
            elif node_type:
                args["query"] = node_type
                node_type = ""
            else:
                args["query"] = ""
            if node_type:
                args["type"] = node_type
            if "limit" in params:
                args["limit"] = int(params["limit"])
            result = tools_read.find(index, project_root, args)

        elif action in ("get", "context"):
            node_id = params.get("query") or params.get("id") or params.get("node_id", "")
            result = tools_read.context(index, project_root, {"node_id": node_id})

        elif action == "signature":
            node_id = params.get("query") or params.get("id") or params.get("node_id", "")
            result = tools_read.signature(index, project_root, {"node_id": node_id})

        elif action in ("recent", "sessions"):
            n = int(params.get("query", params.get("n", 3)))
            result = tools_read.session_recent(index, project_root, {"n": n})

        elif action == "decisions":
            topic = params.get("query") or params.get("topic", "")
            node_id = params.get("node_id", "")
            args = {}
            if topic:
                args["topic"] = topic
            if node_id:
                args["node_id"] = node_id
            result = tools_read.decisions_for(index, project_root, args)

        elif action == "sections":
            doc_id = params.get("query") or params.get("doc_id", "")
            result = tools_read.doc_sections(index, project_root, {"doc_id": doc_id})

        # ── Write actions ─────────────────────────────────────────────────────
        elif action == "create":
            args = {
                "type": node_type or params.pop("type", "Node"),
                "name": params.get("name", ""),
                "fields": {k: v for k, v in params.items() if k not in ("name", "type")},
                "session_id": params.get("session_id", ""),
            }
            result = tools_write.node_upsert(index, project_root, args)

        elif action == "update":
            node_id = params.pop("id", params.pop("node_id", ""))
            args = {
                "node_id": node_id,
                "type": node_type or params.pop("type", ""),
                "name": params.get("name", ""),
                "fields": {k: v for k, v in params.items() if k not in ("name", "type")},
                "session_id": params.get("session_id", ""),
            }
            result = tools_write.node_upsert(index, project_root, args)

        elif action == "lock":
            locked_by_raw = params.get("locked_by", "CEO,Claude-CLI")
            locked_by = [s.strip() for s in locked_by_raw.split(",")]
            args = {
                "topic": params.get("topic", ""),
                "what": params.get("what", ""),
                "why": params.get("why", ""),
                "locked_by": locked_by,
                "session_id": params.get("session_id", ""),
                "alternatives_considered": [],
            }
            result = tools_write.decision_lock(index, project_root, args)

        elif action == "session":
            sub = params.get("query", "start")
            args = {
                "action": sub,
                "actor": params.get("actor", "unknown"),
                "goal": params.get("goal", ""),
                "outcome": params.get("outcome", ""),
                "pending": params.get("pending", "").split(",") if params.get("pending") else [],
                "handoff_notes": params.get("handoff", params.get("handoff_notes", "")),
            }
            if "session_id" in params:
                args["session_id"] = params["session_id"]
            result = tools_write.session_log(index, project_root, args)

        # ── Import actions ────────────────────────────────────────────────────
        elif action == "import":
            source_path = params.get("query") or params.get("source_path", "")
            args = {
                "source_path": source_path,
                "session_id": params.get("session_id", ""),
                "proposal_type": params.get("type", "doc"),
                "ai_notes": params.get("notes", ""),
                "proposed_nodes": [],
                "proposed_edges": [],
                "confidence": params.get("confidence", "medium"),
            }
            result = tools_import.import_proposal(index, project_root, args)

        elif action == "commit":
            proposal_id = params.get("query") or params.get("proposal_id", "")
            args = {
                "proposal_id": proposal_id,
                "accept": params.get("accept", "all"),
                "session_id": params.get("session_id", ""),
            }
            result = tools_import.import_commit(index, project_root, args)

        # ── Maintenance actions ───────────────────────────────────────────────
        elif action == "validate":
            scope = params.get("query", params.get("scope", "all"))
            result = tools_maintain.validate(
                index, project_root, {"scope": scope, "severity_filter": "all"}
            )

        elif action == "extract":
            result = await lessons_extract(index, project_root, {})

        # ── Unknown action ────────────────────────────────────────────────────
        else:
            # Fallback: try find
            result = tools_read.find(index, project_root, {"query": query})
            dispatch_info["fallback"] = True

    except Exception as e:
        result = {
            "ok": False,
            "error": str(e),
            "hint": _get_hint(action, node_type),
        }

    # Add dispatch info for audit
    result["_dispatch"] = dispatch_info
    return result


def _get_hint(action: str, node_type: str) -> str:
    """Return helpful hint for failed action."""
    hints = {
        "create": "Usage: gobp(query=\"create:<NodeType> name='x' session_id='session:y'\")",
        "lock": "Usage: gobp(query=\"lock:Decision topic='x' what='y' why='z' locked_by='CEO,Claude'\")",
        "session": "Usage: gobp(query=\"session:start actor='x' goal='y'\") or session:end",
        "import": "Usage: gobp(query=\"import: path/to/file.md session_id='session:x'\")",
        "commit": "Usage: gobp(query=\"commit: imp:proposal-id accept=all session_id='session:x'\")",
    }
    return hints.get(action, "Call gobp(query='overview:') to see all available actions")


# ── Protocol guide (included in gobp_overview response) ──────────────────────

PROTOCOL_GUIDE = {
    "protocol": "gobp query protocol v1",
    "format": "<action>:<NodeType> <key>='<value>' ...",
    "actions": {
        "overview:":                                    "Project stats and orientation",
        "find: <keyword>":                              "Search any node by keyword",
        "find:<NodeType> <keyword>":                    "Search by type + keyword",
        "get: <node_id>":                               "Full node + edges + decisions",
        "signature: <node_id>":                         "Minimal node summary",
        "recent: <n>":                                  "Latest N sessions",
        "decisions: <topic>":                           "Locked decisions for topic",
        "sections: <doc_id>":                           "Document sections list",
        "create:<NodeType> name='x' session_id='y'":   "Create a new node",
        "update: id='x' name='y' session_id='z'":      "Update existing node",
        "lock:Decision topic='x' what='y' why='z'":    "Lock a decision",
        "session:start actor='x' goal='y'":             "Start a session",
        "session:end outcome='x' handoff='y'":          "End a session",
        "import: path/to/doc.md session_id='x'":       "Propose doc import",
        "commit: imp:proposal-id":                      "Commit approved proposal",
        "validate: <scope>":                            "Validate graph (all|nodes|edges)",
        "extract: lessons":                             "Extract lesson candidates",
    },
    "tip": "Always start with overview: to see project state",
}
```

**Acceptance criteria:**
- `gobp/mcp/dispatcher.py` created
- `parse_query()` correctly parses all example formats
- `dispatch()` routes all 14 actions to correct handlers
- `_get_hint()` returns helpful error message per action
- `PROTOCOL_GUIDE` dict exported
- File imports cleanly

**Commit message:**
```
Wave 10A Task 1: create gobp/mcp/dispatcher.py

- parse_query(): parse "action:type key='value'" format
- dispatch(): deterministic router to all 14 tool handlers
- PROTOCOL_GUIDE: machine-readable interface guide
- _get_hint(): helpful error messages per action
- No AI intent parsing — pure pattern matching
```

---

## TASK 2 — Update gobp_overview to include protocol guide

**Goal:** `gobp_overview()` response includes `interface` section so AI orients immediately.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `gobp/mcp/tools/read.py` in full before editing.**

Find the `return` statement in `gobp_overview()`. Add `interface` key:

```python
    from gobp.mcp.dispatcher import PROTOCOL_GUIDE

    return {
        "ok": True,
        "project": { ... },  # unchanged
        "stats": { ... },    # unchanged
        "main_topics": main_topics,
        "recent_decisions": recent_decisions,
        "recent_sessions": recent_sessions,
        "suggested_next_queries": [
            "gobp(query='find: <keyword>') to search nodes",
            "gobp(query='find:Decision <topic>') to find decisions",
            "gobp(query='session:start actor=<name> goal=<goal>') to start session",
        ],
        "concepts": concepts,
        "test_coverage": { ... },  # unchanged
        "interface": PROTOCOL_GUIDE,  # ← ADD THIS
    }
```

**Acceptance criteria:**
- `gobp_overview()` returns `interface` key with `PROTOCOL_GUIDE`
- All existing `gobp_overview` tests still pass (interface is additive)
- `suggested_next_queries` updated to use gobp() syntax

**Commit message:**
```
Wave 10A Task 2: gobp_overview includes protocol guide

- Import PROTOCOL_GUIDE from dispatcher
- gobp_overview response: add 'interface' key
- suggested_next_queries: updated to gobp() syntax
- Additive change — existing tests unchanged
```

---

## TASK 3 — Rewrite gobp/mcp/server.py to expose 1 tool

**Goal:** Replace 14 tool registrations with 1 `gobp()` tool.

**File to modify:** `gobp/mcp/server.py`

**Re-read current `gobp/mcp/server.py` in full before editing.**

**Replace `list_tools()` function:**

```python
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Register single gobp() tool."""
    return [
        types.Tool(
            name="gobp",
            description=(
                "GoBP knowledge graph — create, query, and manage project knowledge. "
                "Pass a structured query: '<action>:<NodeType> <key>=\\'<value>\\' ...'. "
                "Call gobp(query='overview:') first to see all actions and project state."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Structured query. Format: '<action>:<type> <key>=\\'<value>\\''. "
                            "Examples: 'overview:' | 'find: login' | 'find:Decision auth' | "
                            "'create:Idea name=\\'x\\' session_id=\\'y\\'' | "
                            "'lock:Decision topic=\\'x\\' what=\\'y\\' why=\\'z\\'' | "
                            "'session:start actor=\\'x\\' goal=\\'y\\'' | "
                            "'validate: nodes' | 'extract: lessons'"
                        ),
                    }
                },
                "required": ["query"],
            },
        )
    ]
```

**Replace `call_tool()` function:**

```python
@server.call_tool()
async def call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent]:
    """Dispatch gobp() query to correct handler."""
    global _index, _project_root

    if name != "gobp":
        result = {"ok": False, "error": f"Unknown tool: {name}. Use gobp()."}
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    # Lazy load index
    if _index is None or _project_root is None:
        _project_root = _get_project_root()
        _index = _load_index(_project_root)

    query = arguments.get("query", "overview:")

    try:
        from gobp.mcp.dispatcher import dispatch, parse_query
        result = await dispatch(query, _index, _project_root)

        # Reload index after write operations
        action, _, _ = parse_query(query)
        if action in ("create", "update", "lock", "session", "commit"):
            _index = _load_index(_project_root)
            # Invalidate cache
            try:
                from gobp.core.cache import get_cache
                get_cache().invalidate_all()
            except Exception:
                pass

    except Exception as e:
        result = {
            "ok": False,
            "error": str(e),
            "hint": "Call gobp(query='overview:') to see available actions",
        }

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
```

**Acceptance criteria:**
- `list_tools()` returns exactly 1 tool named `gobp`
- `call_tool()` dispatches to `dispatcher.dispatch()`
- Index reloads after write operations
- Cache invalidated after writes
- Server starts without error

**Commit message:**
```
Wave 10A Task 3: server.py — collapse 14 tools to 1 gobp() tool

- list_tools(): register single gobp() tool with full description
- call_tool(): dispatch to dispatcher.dispatch()
- Index reload after write operations (create/update/lock/session/commit)
- Cache invalidate after writes
- Unknown tool name returns helpful error
```

---

## TASK 4 — Verify server starts and gobp() works

**Goal:** Smoke test the new server.

```powershell
# Server imports cleanly
D:/GoBP/venv/Scripts/python.exe -c "from gobp.mcp.server import server; print('OK')"

# Dispatcher works
D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from gobp.mcp.dispatcher import parse_query, dispatch, PROTOCOL_GUIDE

# Test parse_query
cases = [
    ('overview:', ('overview', '', {})),
    ('find: login', ('find', '', {'query': 'login'})),
    ('find:Decision auth', ('find', 'Decision', {'query': 'auth'})),
    ('session:start actor=cursor goal=test', ('session', '', {'query': 'start', 'actor': 'cursor', 'goal': 'test'})),
]
for q, expected in cases:
    result = parse_query(q)
    action, ntype, params = result
    exp_action, exp_type, exp_params = expected
    assert action == exp_action, f'action mismatch: {action} != {exp_action} for {q!r}'
    assert ntype == exp_type, f'type mismatch: {ntype} != {exp_type} for {q!r}'
    print(f'OK: {q!r}')

print('PROTOCOL_GUIDE keys:', list(PROTOCOL_GUIDE.keys()))
print('All parse_query tests passed')
"

# All existing tests still pass
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 217 tests passing
```

**Commit message:**
```
Wave 10A Task 4: smoke test gobp() server and dispatcher

- Server imports cleanly
- parse_query() handles all protocol formats
- All 217 existing tests passing (tool functions unchanged)
```

---

## TASK 5 — Create tests/test_dispatcher.py

**Goal:** Test dispatcher routing and parse_query correctness.

**File to create:** `tests/test_dispatcher.py`

```python
"""Tests for gobp/mcp/dispatcher.py — parse_query and dispatch routing."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.mcp.dispatcher import parse_query, dispatch, PROTOCOL_GUIDE
from gobp.core.init import init_project
from gobp.core.graph import GraphIndex


# ── parse_query tests ─────────────────────────────────────────────────────────

def test_parse_overview():
    action, ntype, params = parse_query("overview:")
    assert action == "overview"
    assert ntype == ""
    assert params == {}


def test_parse_overview_empty():
    action, ntype, params = parse_query("")
    assert action == "overview"


def test_parse_find_bare():
    action, ntype, params = parse_query("find: login")
    assert action == "find"
    assert ntype == ""
    assert params["query"] == "login"


def test_parse_find_with_type():
    action, ntype, params = parse_query("find:Decision auth")
    assert action == "find"
    assert ntype == "Decision"
    assert params["query"] == "auth"


def test_parse_get():
    action, ntype, params = parse_query("get: node:feat_login")
    assert action == "get"
    assert params["query"] == "node:feat_login"


def test_parse_create_with_kv():
    action, ntype, params = parse_query("create:Idea name='use OTP' subject='auth:login'")
    assert action == "create"
    assert ntype == "Idea"
    assert params["name"] == "use OTP"
    assert params["subject"] == "auth:login"


def test_parse_lock():
    action, ntype, params = parse_query(
        "lock:Decision topic='auth:login' what='use OTP' why='SMS unreliable'"
    )
    assert action == "lock"
    assert ntype == "Decision"
    assert params["topic"] == "auth:login"
    assert params["what"] == "use OTP"
    assert params["why"] == "SMS unreliable"


def test_parse_session_start():
    action, ntype, params = parse_query("session:start actor='cursor' goal='implement login'")
    assert action == "session"
    assert params.get("query") == "start" or ntype == "start"


def test_parse_validate():
    action, ntype, params = parse_query("validate: nodes")
    assert action == "validate"
    assert params.get("query") == "nodes"


def test_parse_no_colon_fallback():
    action, ntype, params = parse_query("login feature")
    assert action == "find"
    assert "login feature" in str(params)


def test_protocol_guide_has_required_keys():
    assert "protocol" in PROTOCOL_GUIDE
    assert "format" in PROTOCOL_GUIDE
    assert "actions" in PROTOCOL_GUIDE
    assert "tip" in PROTOCOL_GUIDE
    assert len(PROTOCOL_GUIDE["actions"]) >= 10


# ── dispatch routing tests ────────────────────────────────────────────────────

@pytest.fixture
def disp_root(gobp_root: Path) -> Path:
    """GoBP root with init data for dispatch tests."""
    init_project(gobp_root, force=True)
    return gobp_root


def test_dispatch_overview(disp_root: Path):
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("overview:", index, disp_root))
    assert result["ok"] is True
    assert "stats" in result
    assert "_dispatch" in result
    assert result["_dispatch"]["action"] == "overview"


def test_dispatch_find(disp_root: Path):
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("find: unit", index, disp_root))
    assert result["ok"] is True
    assert "matches" in result
    assert result["_dispatch"]["action"] == "find"


def test_dispatch_find_with_type(disp_root: Path):
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("find:TestKind unit", index, disp_root))
    assert result["ok"] is True
    for match in result.get("matches", []):
        assert match["type"] == "TestKind"


def test_dispatch_overview_has_interface(disp_root: Path):
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("overview:", index, disp_root))
    assert "interface" in result
    assert result["interface"]["protocol"] == "gobp query protocol v1"


def test_dispatch_unknown_action_fallback(disp_root: Path):
    """Unknown action falls back to find()."""
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("unknown: test", index, disp_root))
    # Should not crash — either find result or error with hint
    assert "ok" in result


def test_dispatch_includes_dispatch_info(disp_root: Path):
    """Every dispatch result includes _dispatch audit info."""
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("find: login", index, disp_root))
    assert "_dispatch" in result
    assert "action" in result["_dispatch"]
    assert "params" in result["_dispatch"]


def test_dispatch_validate(disp_root: Path):
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(dispatch("validate: nodes", index, disp_root))
    assert "ok" in result
    assert result["_dispatch"]["action"] == "validate"


def test_dispatch_session_start(disp_root: Path):
    index = GraphIndex.load_from_disk(disp_root)
    result = asyncio.run(
        dispatch("session:start actor='test' goal='dispatcher test'", index, disp_root)
    )
    assert result["ok"] is True
    assert "session_id" in result
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_dispatcher.py -v
# Expected: ~20 tests passing
```

**Commit message:**
```
Wave 10A Task 5: create tests/test_dispatcher.py

- 11 parse_query tests: overview, find bare/type, get, create kv,
  lock, session start, validate, no-colon fallback, protocol guide
- 8 dispatch tests: overview, find, find+type, interface present,
  unknown fallback, _dispatch audit info, validate, session start
- ~20 tests total
```

---

## TASK 6 — Update docs/MCP_TOOLS.md with gobp() protocol

**Goal:** Document the new gobp() interface as primary API.

**File to modify:** `docs/MCP_TOOLS.md`

**Step 1:** Read `docs/MCP_TOOLS.md` in full.

**Step 2:** Add new section at the TOP (after the file header, before existing content):

```markdown
## gobp() — Primary Interface (v2)

As of Wave 10A, GoBP exposes a single MCP tool: `gobp()`.

**Why:** MCP clients may limit visible tools per server. `gobp()` provides
access to all 14 capabilities through 1 tool using structured query protocol.

### Protocol

```
gobp(query="<action>:<NodeType> <key>='<value>' ...")
```

### Quick reference

| Query | Capability |
|---|---|
| `overview:` | Project stats, orientation, protocol guide |
| `find: <keyword>` | Search any node |
| `find:<NodeType> <keyword>` | Search by type + keyword |
| `get: <node_id>` | Full node + edges + decisions |
| `signature: <node_id>` | Minimal node summary |
| `recent: <n>` | Latest N sessions |
| `decisions: <topic>` | Locked decisions for topic |
| `sections: <doc_id>` | Document sections |
| `create:<NodeType> name='x' session_id='y'` | Create node |
| `update: id='x' name='y'` | Update node |
| `lock:Decision topic='x' what='y' why='z'` | Lock decision |
| `session:start actor='x' goal='y'` | Start session |
| `session:end outcome='x' handoff='y'` | End session |
| `import: path/to/doc.md` | Propose import |
| `commit: imp:proposal-id` | Commit proposal |
| `validate: <scope>` | Validate graph |
| `extract: lessons` | Extract lesson candidates |

### First call

Always call `gobp(query="overview:")` first. Response includes:
- Project state (nodes, edges, recent decisions)
- Full protocol guide in `interface` field
- Suggested next queries in gobp() syntax

### Notes
- `locked_by` in lock action: comma-separated string e.g. `locked_by='CEO,Claude'`
- `session_id` required for create/update/lock — get from `session:start` first
- `_dispatch` field in every response — shows what was routed internally (for audit)
```

**Step 3:** Add note to existing tool sections:

At top of each existing tool section (find, gobp_overview, etc.), add:

```markdown
> **v2 note:** Use `gobp(query="find: ...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.
```

**Acceptance criteria:**
- `docs/MCP_TOOLS.md` has gobp() section at top
- Quick reference table complete
- Existing tool sections have v2 note
- Valid markdown

**Commit message:**
```
Wave 10A Task 6: update docs/MCP_TOOLS.md with gobp() protocol

- Add gobp() primary interface section at top
- Quick reference table: all 17 query patterns
- v2 notes on existing tool sections
- Protocol format + first call guidance
```

---

## TASK 7 — Full suite + update CHANGELOG

**Goal:** All tests pass. CHANGELOG updated.

```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 237+ tests (217 + ~20 dispatcher)
```

**Update CHANGELOG.md** — prepend:

```markdown
## [Wave 10A] — gobp() Single Tool + Structured Query Protocol — 2026-04-15

### Problem solved
Claude.ai web and other MCP clients may limit visible tools per server.
GoBP's 14 tools were reduced to 5 visible tools — write operations invisible.

### Solution
Collapsed 14 MCP tools → 1 `gobp()` tool with structured query protocol.
All 14 capabilities accessible via `gobp(query="<action>:<type> ...")`.

### Added
- `gobp/mcp/dispatcher.py` — deterministic query parser + router
- `tests/test_dispatcher.py` — ~20 dispatcher tests
- `gobp_overview()` response: `interface` field with full protocol guide

### Changed
- `gobp/mcp/server.py` — 14 tools → 1 gobp() tool
- `gobp/mcp/tools/read.py` — gobp_overview includes PROTOCOL_GUIDE
- `docs/MCP_TOOLS.md` — gobp() protocol documented as primary API

### NOT changed
- All tool functions (read.py, write.py, etc.) — unchanged
- All existing 217 tests — unchanged (test functions directly)

### Protocol
```
gobp(query="overview:")                              → project state
gobp(query="find: login")                            → search nodes
gobp(query="create:Idea name='x' session_id='y'")   → create node
gobp(query="lock:Decision topic='x' what='y'")      → lock decision
gobp(query="session:start actor='x' goal='y'")      → start session
```

### Total after wave: 1 MCP tool, 237+ tests passing
```

**Commit message:**
```
Wave 10A Task 7: full suite green + CHANGELOG updated

- 237+ tests passing
- CHANGELOG: Wave 10A entry
```

---

## TASK 8 — End-to-end verification

**Goal:** Verify gobp() works end-to-end with real GoBP project.

```powershell
# Test via Python (simulates MCP call)
D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch

root = Path('D:/GoBP')
index = GraphIndex.load_from_disk(root)

async def test():
    # Test 1: overview
    r = await dispatch('overview:', index, root)
    assert r['ok'], f'overview failed: {r}'
    assert 'interface' in r
    print(f'overview: {r[\"stats\"][\"total_nodes\"]} nodes')
    
    # Test 2: find
    r = await dispatch('find: decision', index, root)
    assert r['ok'], f'find failed: {r}'
    print(f'find decision: {r[\"count\"]} matches')
    
    # Test 3: find with type
    r = await dispatch('find:TestKind security', index, root)
    assert r['ok'], f'find:TestKind failed: {r}'
    for m in r['matches']:
        assert m['type'] == 'TestKind'
    print(f'find:TestKind security: {r[\"count\"]} matches')
    
    # Test 4: validate
    r = await dispatch('validate: nodes', index, root)
    assert 'ok' in r
    print(f'validate: ok={r[\"ok\"]}')
    
    print('All end-to-end tests passed')

asyncio.run(test())
"
```

**Commit message:**
```
Wave 10A Task 8: end-to-end verification passed

- gobp() dispatches correctly with real GoBP project data
- overview, find, find:Type, validate all work
- Wave 10A complete
```

---

# POST-WAVE VERIFICATION

```powershell
# All tests pass
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 237+ tests

# Server exposes 1 tool
D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from gobp.mcp.server import list_tools
tools = asyncio.run(list_tools())
print(f'Tools: {len(tools)}')
assert len(tools) == 1
assert tools[0].name == 'gobp'
print('OK — 1 tool: gobp()')
"

# Protocol works
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.mcp.dispatcher import parse_query
assert parse_query('overview:')[0] == 'overview'
assert parse_query('find: login')[2]['query'] == 'login'
assert parse_query('find:Decision auth')[1] == 'Decision'
print('Protocol parsing OK')
"

# Git log
git log --oneline | Select-Object -First 10
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief vào repo

```powershell
cd D:\GoBP
# Save wave_10a_brief.md to D:\GoBP\waves\wave_10a_brief.md

git add waves/wave_10a_brief.md
git commit -m "Add Wave 10A Brief — gobp() single tool + structured query protocol"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_10a_brief.md first.
Also read gobp/mcp/server.py, gobp/mcp/tools/read.py,
gobp/mcp/tools/write.py, gobp/mcp/tools/maintain.py,
gobp/mcp/tools/import_.py, gobp/mcp/tools/advanced.py,
docs/MCP_TOOLS.md.

Execute ALL 8 tasks of Wave 10A sequentially.
Rules:
- R9 critical: all 217 existing tests must pass after every task
- Tool functions unchanged — only server.py and dispatcher are new
- Brief code blocks are authoritative (R8)
- 1 task = 1 commit, exact message
- Report full summary after Task 8

Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 10A. Read CLAUDE.md and waves/wave_10a_brief.md.
Also read docs/GoBP_ARCHITECTURE.md, docs/ARCHITECTURE.md, docs/MCP_TOOLS.md.

Critical verification:
- Task 1: dispatcher.py exists, parse_query handles all formats, PROTOCOL_GUIDE exported
- Task 2: gobp_overview returns interface field with PROTOCOL_GUIDE
- Task 3: server.py list_tools() returns exactly 1 tool named 'gobp'
- Task 4: server imports clean, parse_query smoke tests pass, 217 tests passing
- Task 5: test_dispatcher.py exists, ~20 tests passing
- Task 6: MCP_TOOLS.md has gobp() section at top, quick reference table
- Task 7: 237+ tests passing, CHANGELOG updated
- Task 8: end-to-end verification passed with real GoBP data

Use venv:
  D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

Expected: 237+ tests passing.

Stop on first failure. Report WAVE 10A AUDIT COMPLETE when done.
```

## 4. Push + test in Claude.ai

```powershell
cd D:\GoBP
git push origin main
```

Sau push → reconnect MCP trong Claude.ai Settings → verify chỉ thấy 1 tool `gobp` → test:

```
gobp(query="overview:")
```

Expected: full project state + interface guide.

---

# WHAT COMES NEXT

```
Wave 10A pushed + verified in Claude.ai
    ↓
Wave 8B Phase 2 — MIHOS real import
  gobp(query="session:start actor='claude-cli' goal='MIHOS import'")
  gobp(query="import: docs/DOC-07.md session_id='...'")
  gobp(query="overview:") → see imported nodes
```

---

*Wave 10A Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
