# WAVE 3 BRIEF — MCP SERVER + READ TOOLS

**Wave:** 3
**Title:** MCP Server + 7 Read Tools (6 core + gobp_overview)
**Author:** CTO Chat (Claude Opus 4.6)
**Date:** 2026-04-14
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 9 atomic tasks
**Estimated effort:** 4-5 hours

---

## CONTEXT

Wave 0 built the skeleton. Wave 1 built the core engine (GraphIndex, loader, validator). Wave 2 built write primitives (mutator, history log).

**Wave 3 makes GoBP accessible to AI clients via MCP protocol.** This is the most important wave — after Wave 3, Cursor, Claude Desktop, Claude CLI, and any MCP-capable AI client can connect to GoBP and query data.

**In scope:**
- `gobp/mcp/server.py` — MCP server entry point
- `gobp/mcp/tools/read.py` — 6 core read tools + gobp_overview
- Token budget enforcement (truncate oversized results)
- Example MCP config for 4 clients (Cursor, Claude Desktop, Claude CLI, Continue)
- Tests for all 7 tools
- README update: how to connect MCP clients

**NOT in scope:**
- Write tools (Wave 5)
- Import tools (Wave 5)
- Validate tool (Wave 5)
- CLI commands (Wave 4)
- MIHOS integration test (Wave 8)

---

## SCOPE DISCIPLINE RULE

**Implement EXACTLY the 7 read tools specified. No additional tools, no "while I'm at it" helpers.**

The 7 tools:
1. `gobp_overview` — orientation (new, first-call)
2. `find` — search nodes
3. `signature` — minimal node summary
4. `context` — node + relations + decisions
5. `session_recent` — latest sessions
6. `decisions_for` — decisions for topic
7. `doc_sections` — Document node sections

Anything beyond these 7 tools → STOP and escalate.

---

## AUTHORITATIVE SOURCE

**`docs/MCP_TOOLS.md` is the source of truth for tool specs.** This Brief provides implementation scaffolding and acceptance criteria, but the tool input/output schemas MUST match `docs/MCP_TOOLS.md` verbatim.

Cursor MUST re-read `docs/MCP_TOOLS.md` before implementing each tool. If Brief conflicts with `docs/MCP_TOOLS.md` → **MCP_TOOLS.md wins**, Cursor stops and escalates to CEO.

---

## PREREQUISITES

Before Task 1:

```powershell
cd D:\GoBP
git status              # clean
pytest tests/ -v        # All Wave 0+1+2 tests pass (66+)
python -c "from gobp.core.graph import GraphIndex; print('OK')"
python -c "import mcp; print('mcp OK')"
```

If any check fails, STOP.

---

## REQUIRED READING

At wave start:
1. `.cursorrules` (v4)
2. `CHARTER.md`
3. `docs/VISION.md`
4. `docs/ARCHITECTURE.md` (multi-project section, file structure)
5. `docs/SCHEMA.md`
6. **`docs/MCP_TOOLS.md`** (THE SOURCE OF TRUTH for tool specs)
7. `waves/wave_3_brief.md` (this file)

Re-read `docs/MCP_TOOLS.md` before implementing EACH tool in Tasks 2-8.

---

# TASKS

## TASK 1 — MCP server skeleton + tool registration

**Goal:** Create MCP server entry point with tool registration for all 7 tools. Each tool initially returns a stub response "not yet implemented". Tasks 2-8 fill in actual logic.

**File to modify:** `gobp/mcp/server.py`

**Replace stub content with:**

```python
"""GoBP MCP Server.

Exposes GoBP graph data to MCP-capable AI clients (Cursor, Claude Desktop,
Claude CLI, Continue, etc.) via standard MCP protocol over stdio.

Server loads .gobp/ data on startup and serves read tools. Write tools
are added in Wave 5.

Usage:
    python -m gobp.mcp.server

The server reads GOBP_PROJECT_ROOT environment variable to locate the
project folder. Defaults to current working directory.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import read as tools_read


logger = logging.getLogger("gobp.mcp.server")


def _get_project_root() -> Path:
    """Determine project root from env var or cwd."""
    env_root = os.environ.get("GOBP_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path.cwd().resolve()


def _load_index(project_root: Path) -> GraphIndex:
    """Load GraphIndex from disk, logging any errors."""
    logger.info(f"Loading GoBP index from {project_root}")
    index = GraphIndex.load_from_disk(project_root)
    if index.load_errors:
        logger.warning(f"Load errors encountered: {len(index.load_errors)} files")
        for err in index.load_errors[:5]:
            logger.warning(f"  {err}")
    logger.info(f"Index loaded: {len(index)} nodes, {len(index.all_edges())} edges")
    return index


# Global server instance and index (loaded on startup)
server: Server = Server("gobp")
_index: GraphIndex | None = None
_project_root: Path | None = None


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Return the list of available tools for MCP discovery."""
    return [
        types.Tool(
            name="gobp_overview",
            description="Orientation tool for AI clients. Returns project metadata, stats, main topics, and recent activity. Call this first when connecting.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="find",
            description="Fuzzy search GoBP nodes by id, name, or keyword.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="signature",
            description="Get minimal node summary (id, type, name, status, key fields).",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                },
                "required": ["node_id"],
            },
        ),
        types.Tool(
            name="context",
            description="Get node + outgoing/incoming edges + applicable decisions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "depth": {"type": "integer", "default": 1},
                },
                "required": ["node_id"],
            },
        ),
        types.Tool(
            name="session_recent",
            description="Get the latest N sessions for continuity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "n": {"type": "integer", "default": 3},
                    "before": {"type": "string"},
                    "actor": {"type": "string"},
                },
                "required": [],
            },
        ),
        types.Tool(
            name="decisions_for",
            description="Get locked decisions for a topic or node.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "node_id": {"type": "string"},
                    "status": {"type": "string", "default": "LOCKED"},
                },
                "required": [],
            },
        ),
        types.Tool(
            name="doc_sections",
            description="List sections of a Document node without loading content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string"},
                },
                "required": ["doc_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Route tool calls to handlers in tools_read module."""
    global _index, _project_root

    if _index is None or _project_root is None:
        result = {"ok": False, "error": "GoBP index not loaded"}
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    dispatch = {
        "gobp_overview": tools_read.gobp_overview,
        "find": tools_read.find,
        "signature": tools_read.signature,
        "context": tools_read.context,
        "session_recent": tools_read.session_recent,
        "decisions_for": tools_read.decisions_for,
        "doc_sections": tools_read.doc_sections,
    }

    handler = dispatch.get(name)
    if not handler:
        result = {"ok": False, "error": f"Unknown tool: {name}"}
    else:
        try:
            result = handler(_index, _project_root, arguments)
        except Exception as e:
            logger.exception(f"Tool '{name}' raised exception")
            result = {"ok": False, "error": str(e), "tool": name}

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def main() -> None:
    """MCP server entry point."""
    global _index, _project_root

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    _project_root = _get_project_root()
    _index = _load_index(_project_root)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
```

**Acceptance criteria:**
- `gobp/mcp/server.py` replaces stub
- Imports mcp SDK correctly
- Registers exactly 7 tools via `@server.list_tools()`
- Tool names match MCP_TOOLS.md exactly: `gobp_overview`, `find`, `signature`, `context`, `session_recent`, `decisions_for`, `doc_sections`
- `call_tool` dispatches to handler functions in `tools_read` module (stubs OK for now — real logic in Tasks 2-8)
- Loads GraphIndex on startup from GOBP_PROJECT_ROOT env var
- Logs to stderr (stdout is reserved for MCP protocol)
- Can be run as `python -m gobp.mcp.server`

**Create stub `gobp/mcp/tools/read.py` with placeholder functions:**

```python
"""GoBP MCP read tools.

Implementations in Tasks 2-8 of Wave 3.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex


def gobp_overview(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "gobp_overview not yet implemented"}


def find(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "find not yet implemented"}


def signature(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "signature not yet implemented"}


def context(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "context not yet implemented"}


def session_recent(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "session_recent not yet implemented"}


def decisions_for(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "decisions_for not yet implemented"}


def doc_sections(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "doc_sections not yet implemented"}
```

**Self-test:**
```powershell
# Verify server module can be imported and started (will hang waiting for stdio, Ctrl+C to exit)
python -c "from gobp.mcp.server import server; print('Server registered:', server.name)"
```

**Commit message:**
```
Wave 3 Task 1: MCP server skeleton and tool registration

- gobp/mcp/server.py: server entry point with 7 tools registered
- gobp/mcp/tools/read.py: 7 stub handler functions
- Reads GOBP_PROJECT_ROOT env var for project location
- Loads GraphIndex on startup
- Logs to stderr (stdout reserved for MCP protocol)
- Dispatches tool calls to read module

All 7 tools return "not yet implemented" stubs.
Real logic in Tasks 2-8.
```

---

## TASK 2 — Implement gobp_overview

**Goal:** Implement the orientation tool. This is the first tool AI should call.

**Re-read `docs/MCP_TOOLS.md` section on `gobp_overview` before starting.**

**File to modify:** `gobp/mcp/tools/read.py`

**Replace `gobp_overview` stub with:**

```python
import gobp


def _truncate(text: str, max_chars: int = 100) -> str:
    """Truncate text to max_chars, appending '...' if truncated."""
    if text is None:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def gobp_overview(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Return project metadata, stats, main topics, and suggested next queries.

    First tool AI should call when connecting to a new GoBP instance.
    Takes no arguments.
    """
    all_nodes = index.all_nodes()
    all_edges = index.all_edges()

    # Project metadata from charter Document node if exists
    project_name = "Unknown"
    project_description = "GoBP-managed project"

    charter = index.get_node("doc:charter")
    if charter:
        project_name = charter.get("name", project_name)
        project_description = charter.get("description", project_description)
    else:
        # Try first Document node
        docs = index.nodes_by_type("Document")
        if docs:
            project_name = docs[0].get("name", project_name)

    # Stats
    nodes_by_type: dict[str, int] = {}
    for node in all_nodes:
        t = node.get("type", "Unknown")
        nodes_by_type[t] = nodes_by_type.get(t, 0) + 1

    edges_by_type: dict[str, int] = {}
    for edge in all_edges:
        t = edge.get("type", "Unknown")
        edges_by_type[t] = edges_by_type.get(t, 0) + 1

    # Main topics from Decision nodes (top by frequency)
    topic_counts: dict[str, int] = {}
    for node in index.nodes_by_type("Decision"):
        topic = node.get("topic")
        if topic:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

    main_topics = sorted(topic_counts.keys(), key=lambda k: -topic_counts[k])[:10]

    # Recent decisions (top 5 by locked_at, if available)
    decision_nodes = index.nodes_by_type("Decision")
    locked_decisions = [
        n for n in decision_nodes if n.get("status") == "LOCKED" and n.get("locked_at")
    ]
    locked_decisions.sort(key=lambda n: n.get("locked_at", ""), reverse=True)

    recent_decisions = [
        {
            "id": n.get("id"),
            "topic": n.get("topic", ""),
            "what": _truncate(n.get("what", "")),
            "locked_at": n.get("locked_at"),
        }
        for n in locked_decisions[:5]
    ]

    # Recent sessions (top 3 by started_at)
    session_nodes = index.nodes_by_type("Session")
    session_nodes.sort(key=lambda n: n.get("started_at", ""), reverse=True)

    recent_sessions = [
        {
            "id": n.get("id"),
            "goal": _truncate(n.get("goal", "")),
            "status": n.get("status", ""),
            "started_at": n.get("started_at"),
        }
        for n in session_nodes[:3]
    ]

    return {
        "ok": True,
        "project": {
            "name": project_name,
            "description": project_description,
            "gobp_version": getattr(gobp, "__version__", "0.1.0"),
            "schema_version": "1.0",
            "pattern": "per_project",
        },
        "stats": {
            "total_nodes": len(all_nodes),
            "total_edges": len(all_edges),
            "nodes_by_type": nodes_by_type,
            "edges_by_type": edges_by_type,
        },
        "main_topics": main_topics,
        "recent_decisions": recent_decisions,
        "recent_sessions": recent_sessions,
        "suggested_next_queries": [
            "find(query='<keyword>') to search nodes by keyword",
            "decisions_for(topic='<topic>') to find locked decisions on a topic",
            "session_recent(n=3) to see recent session history",
        ],
    }
```

**Acceptance criteria:**
- Function returns structure matching MCP_TOOLS.md spec
- Uses `_truncate` helper for string fields (≤100 chars)
- `main_topics` sorted by frequency descending, max 10
- `recent_decisions` limited to 5, sorted by locked_at desc
- `recent_sessions` limited to 3, sorted by started_at desc
- Falls back gracefully if no charter Document node exists
- Returns `ok: true` on success

**Commit message:**
```
Wave 3 Task 2: implement gobp_overview tool

- gobp/mcp/tools/read.py: gobp_overview implementation
- Returns project metadata, stats, main topics, recent activity
- Falls back to first Document node if no doc:charter exists
- Truncates long strings to 100 chars
- Lists top 10 decision topics by frequency
```

---

## TASK 3 — Implement find

**Re-read `docs/MCP_TOOLS.md` section on `find` before starting.**

**Replace `find` stub with:**

```python
def find(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Fuzzy search nodes by id, exact name, or substring match.

    Args:
        query: str (required) - search term
        limit: int (optional, default 20) - max results

    Returns:
        matches list with match type: exact_id | exact_name | substring
    """
    query = args.get("query")
    if not query or not isinstance(query, str):
        return {"ok": False, "error": "query parameter required"}

    limit = int(args.get("limit", 20))
    query_lower = query.lower()

    matches: list[dict[str, Any]] = []

    # Exact ID match (highest priority)
    exact_id_node = index.get_node(query)
    if exact_id_node:
        matches.append({
            "id": exact_id_node.get("id"),
            "type": exact_id_node.get("type"),
            "name": exact_id_node.get("name", ""),
            "status": exact_id_node.get("status", ""),
            "match": "exact_id",
        })

    # Exact name + substring matches
    for node in index.all_nodes():
        node_id = node.get("id", "")
        if node_id == query:
            continue  # Already added as exact_id

        name = node.get("name", "")
        name_lower = name.lower()

        if name_lower == query_lower:
            match_type = "exact_name"
        elif query_lower in name_lower or query_lower in node_id.lower():
            match_type = "substring"
        else:
            continue

        matches.append({
            "id": node_id,
            "type": node.get("type"),
            "name": name,
            "status": node.get("status", ""),
            "match": match_type,
        })

    # Sort: exact_id > exact_name > substring
    priority = {"exact_id": 0, "exact_name": 1, "substring": 2}
    matches.sort(key=lambda m: priority.get(m["match"], 99))

    total = len(matches)
    truncated = total > limit
    matches = matches[:limit]

    return {
        "ok": True,
        "matches": matches,
        "count": len(matches),
        "truncated": truncated,
    }
```

**Acceptance criteria:**
- Requires `query` parameter (returns error if missing)
- Default limit 20, configurable
- Match types: exact_id, exact_name, substring
- Sorted by match priority
- Returns truncated=true if more matches exist beyond limit

**Commit message:**
```
Wave 3 Task 3: implement find tool

- Fuzzy search by id, name, or substring
- Match types: exact_id > exact_name > substring
- Default limit 20, configurable
- Returns truncated flag if results exceed limit
```

---

## TASK 4 — Implement signature

**Re-read MCP_TOOLS.md `signature` section.**

**Replace stub with:**

```python
def signature(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get minimal node summary.

    Args:
        node_id: str (required)

    Returns:
        Basic node fields without edges or decisions.
    """
    node_id = args.get("node_id")
    if not node_id:
        return {"ok": False, "error": "node_id parameter required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    # Copy key fields
    signature_fields = {
        "id": node.get("id"),
        "type": node.get("type"),
        "name": node.get("name", ""),
        "status": node.get("status", ""),
    }

    # Add common optional fields if present
    for field in ["subtype", "description", "tags", "topic", "what", "why", "goal"]:
        if field in node:
            signature_fields[field] = node[field]

    return {
        "ok": True,
        "signature": signature_fields,
    }
```

**Acceptance criteria:**
- Requires `node_id`
- Returns `{ok: false}` with error if node not found
- Returns minimal key fields + common optional fields if present

**Commit message:**
```
Wave 3 Task 4: implement signature tool

- Returns minimal node summary (id, type, name, status + common optional fields)
- Returns error if node_id missing or node not found
```

---

## TASK 5 — Implement context

**Re-read MCP_TOOLS.md `context` section.**

**Replace stub with:**

```python
def context(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get node + outgoing/incoming edges + applicable decisions.

    Args:
        node_id: str (required)
        depth: int (optional, default 1) - hop depth, v1 max 2

    Returns:
        Full node, edges, decisions, references.
    """
    node_id = args.get("node_id")
    if not node_id:
        return {"ok": False, "error": "node_id parameter required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    # Outgoing edges
    outgoing_raw = index.get_edges_from(node_id)
    outgoing = []
    for edge in outgoing_raw:
        to_node = index.get_node(edge.get("to", ""))
        outgoing.append({
            "type": edge.get("type"),
            "to": edge.get("to"),
            "to_name": to_node.get("name", "") if to_node else "",
            "to_type": to_node.get("type", "") if to_node else "",
        })

    # Incoming edges
    incoming_raw = index.get_edges_to(node_id)
    incoming = []
    for edge in incoming_raw:
        from_node = index.get_node(edge.get("from", ""))
        incoming.append({
            "type": edge.get("type"),
            "from": edge.get("from"),
            "from_name": from_node.get("name", "") if from_node else "",
            "from_type": from_node.get("type", "") if from_node else "",
        })

    # Applicable decisions: via 'implements' edges + topic match
    decisions: list[dict[str, Any]] = []
    seen_decision_ids: set[str] = set()

    # Decisions via edges
    for edge in outgoing_raw:
        target = index.get_node(edge.get("to", ""))
        if target and target.get("type") == "Decision":
            dec_id = target.get("id")
            if dec_id not in seen_decision_ids:
                decisions.append({
                    "id": dec_id,
                    "what": target.get("what", ""),
                    "why": target.get("why", ""),
                    "status": target.get("status", ""),
                })
                seen_decision_ids.add(dec_id)

    # References (via 'references' edges to Document nodes)
    references = []
    for edge in outgoing_raw:
        if edge.get("type") != "references":
            continue
        target = index.get_node(edge.get("to", ""))
        if target and target.get("type") == "Document":
            references.append({
                "doc_id": target.get("id"),
                "section": edge.get("section", ""),
                "lines": edge.get("lines", []),
            })

    return {
        "ok": True,
        "node": node,
        "outgoing": outgoing,
        "incoming": incoming,
        "decisions": decisions,
        "invariants": [],  # Extension schemas; empty in core v1
        "references": references,
    }
```

**Acceptance criteria:**
- Requires `node_id`
- Returns full node + outgoing + incoming + decisions + references
- Decisions extracted from edges pointing to Decision nodes
- References from `references` edges to Document nodes
- `invariants` always empty list in v1 (extension only)

**Commit message:**
```
Wave 3 Task 5: implement context tool

- Returns node + outgoing edges + incoming edges + decisions + references
- Decisions extracted from edges to Decision nodes
- References from 'references' edges to Document nodes
- depth parameter accepted but v1 always depth=1
```

---

## TASK 6 — Implement session_recent and decisions_for

**Re-read MCP_TOOLS.md sections on both tools.**

**Replace stubs with:**

```python
def session_recent(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get the latest N sessions for continuity.

    Args:
        n: int (optional, default 3, max 10)
        before: str (optional) - ISO timestamp filter
        actor: str (optional) - filter by actor
    """
    n = min(int(args.get("n", 3)), 10)
    before = args.get("before")
    actor_filter = args.get("actor")

    sessions = index.nodes_by_type("Session")

    # Filter by actor
    if actor_filter:
        sessions = [s for s in sessions if s.get("actor") == actor_filter]

    # Filter by before timestamp
    if before:
        sessions = [s for s in sessions if s.get("started_at", "") < before]

    # Sort by started_at descending
    sessions.sort(key=lambda s: s.get("started_at", ""), reverse=True)
    sessions = sessions[:n]

    session_list = [
        {
            "id": s.get("id"),
            "actor": s.get("actor", ""),
            "started_at": s.get("started_at"),
            "ended_at": s.get("ended_at"),
            "goal": s.get("goal", ""),
            "outcome": s.get("outcome", ""),
            "status": s.get("status", ""),
            "pending": s.get("pending", []),
            "handoff_notes": s.get("handoff_notes", ""),
        }
        for s in sessions
    ]

    return {
        "ok": True,
        "sessions": session_list,
        "count": len(session_list),
    }


def decisions_for(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get locked decisions for a topic or node.

    Args:
        topic: str (optional) - topic filter
        node_id: str (optional) - get decisions related to this node
        status: str (optional, default LOCKED) - LOCKED | SUPERSEDED | WITHDRAWN | ALL

    One of topic or node_id must be provided.
    """
    topic = args.get("topic")
    node_id = args.get("node_id")
    status_filter = args.get("status", "LOCKED")

    if not topic and not node_id:
        return {"ok": False, "error": "Either 'topic' or 'node_id' must be provided"}

    all_decisions = index.nodes_by_type("Decision")

    # Status filter
    if status_filter != "ALL":
        all_decisions = [d for d in all_decisions if d.get("status") == status_filter]

    # Topic filter
    if topic:
        matching = [d for d in all_decisions if d.get("topic") == topic]
    else:
        # node_id filter: decisions that have an edge pointing to/from this node
        matching = []
        seen: set[str] = set()
        # Decisions where this node is referenced via edges
        for edge in index.all_edges():
            if edge.get("type") not in ("implements", "relates_to"):
                continue
            dec_id = None
            if edge.get("from") == node_id:
                dec_id = edge.get("to")
            elif edge.get("to") == node_id:
                dec_id = edge.get("from")
            if dec_id and dec_id not in seen:
                dec = index.get_node(dec_id)
                if dec and dec.get("type") == "Decision":
                    if status_filter == "ALL" or dec.get("status") == status_filter:
                        matching.append(dec)
                        seen.add(dec_id)

    decisions_out = [
        {
            "id": d.get("id"),
            "topic": d.get("topic", ""),
            "what": d.get("what", ""),
            "why": d.get("why", ""),
            "status": d.get("status", ""),
            "locked_at": d.get("locked_at"),
            "alternatives_considered": d.get("alternatives_considered", []),
        }
        for d in matching
    ]

    return {
        "ok": True,
        "decisions": decisions_out,
        "count": len(decisions_out),
    }
```

**Acceptance criteria:**
- `session_recent`: default n=3, max 10, filters by actor and before
- `decisions_for`: requires topic OR node_id, default status=LOCKED
- Both return `count` field

**Commit message:**
```
Wave 3 Task 6: implement session_recent and decisions_for

- session_recent: latest N sessions with actor/before filters
- decisions_for: decisions by topic or related node, status filter
- Both sorted and limited per MCP_TOOLS.md spec
```

---

## TASK 7 — Implement doc_sections

**Re-read MCP_TOOLS.md `doc_sections` section.**

**Replace stub with:**

```python
def doc_sections(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """List sections of a Document node without loading content.

    Args:
        doc_id: str (required)
    """
    doc_id = args.get("doc_id")
    if not doc_id:
        return {"ok": False, "error": "doc_id parameter required"}

    doc = index.get_node(doc_id)
    if not doc:
        return {"ok": False, "error": f"Document not found: {doc_id}"}

    if doc.get("type") != "Document":
        return {"ok": False, "error": f"Node {doc_id} is not a Document (type={doc.get('type')})"}

    sections = doc.get("sections", [])

    return {
        "ok": True,
        "document": {
            "id": doc.get("id"),
            "name": doc.get("name", ""),
            "source_path": doc.get("source_path", ""),
            "last_verified": doc.get("last_verified"),
        },
        "sections": sections,
        "count": len(sections),
    }
```

**Acceptance criteria:**
- Requires `doc_id`
- Errors if not found or not a Document type
- Returns document metadata + sections list from node data

**Commit message:**
```
Wave 3 Task 7: implement doc_sections tool

- Returns document metadata + sections list
- Errors if node not found or not Document type
- Sections read from node's 'sections' field
```

---

## TASK 8 — Write MCP tools tests

**Goal:** Test all 7 tools with a populated GraphIndex fixture.

**File to create:** `tests/test_mcp_tools.py`

**Content:**

```python
"""Tests for GoBP MCP read tools."""

from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import read as tools_read


@pytest.fixture
def populated_root(tmp_path: Path) -> Path:
    """Create a GoBP root with schemas and sample data for MCP tool testing."""
    import gobp
    actual_schema_dir = Path(gobp.__file__).parent / "schema"

    # Copy schemas
    pkg_dir = tmp_path / "gobp"
    schema_dir = pkg_dir / "schema"
    schema_dir.mkdir(parents=True)
    (schema_dir / "core_nodes.yaml").write_text(
        (actual_schema_dir / "core_nodes.yaml").read_text(encoding="utf-8"),
        encoding="utf-8"
    )
    (schema_dir / "core_edges.yaml").write_text(
        (actual_schema_dir / "core_edges.yaml").read_text(encoding="utf-8"),
        encoding="utf-8"
    )

    # Create sample data
    data_dir = tmp_path / ".gobp"
    nodes_dir = data_dir / "nodes"
    edges_dir = data_dir / "edges"
    nodes_dir.mkdir(parents=True)
    edges_dir.mkdir(parents=True)

    # Charter document
    (nodes_dir / "doc_charter.md").write_text(
        """---
id: doc:charter
type: Document
name: Test Project Charter
description: A test project for MCP tools
source_path: CHARTER.md
content_hash: sha256:abc123
registered_at: 2026-04-14T00:00:00
last_verified: 2026-04-14T00:00:00
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
sections:
  - heading: Introduction
    lines: [1, 20]
    tags: [intro]
  - heading: Goals
    lines: [21, 50]
    tags: [goals]
---

Body.
""",
        encoding="utf-8"
    )

    # Feature node
    (nodes_dir / "node_feat_login.md").write_text(
        """---
id: node:feat_login
type: Node
name: Login Feature
status: ACTIVE
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
---

Body.
""",
        encoding="utf-8"
    )

    # Decision node
    (nodes_dir / "dec_d001.md").write_text(
        """---
id: dec:d001
type: Decision
name: OTP Method
status: LOCKED
topic: auth:login.method
what: Use Email OTP for login
why: SMS has spam issues
locked_at: 2026-04-14T10:00:00
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
---

Body.
""",
        encoding="utf-8"
    )

    # Session node
    (nodes_dir / "session_test.md").write_text(
        """---
id: session:2026-04-14_test
type: Session
actor: Claude Test
started_at: 2026-04-14T09:00:00
goal: Test MCP tools
status: IN_PROGRESS
created: 2026-04-14T09:00:00
updated: 2026-04-14T09:00:00
---

Body.
""",
        encoding="utf-8"
    )

    # Edges
    (edges_dir / "relations.yaml").write_text(
        """- from: node:feat_login
  to: dec:d001
  type: implements
- from: node:feat_login
  to: doc:charter
  type: references
  section: Goals
  lines: [21, 50]
""",
        encoding="utf-8"
    )

    return tmp_path


@pytest.fixture
def index(populated_root: Path) -> GraphIndex:
    return GraphIndex.load_from_disk(populated_root)


# =============================================================================
# gobp_overview tests
# =============================================================================


def test_overview_returns_ok(index: GraphIndex, populated_root: Path):
    result = tools_read.gobp_overview(index, populated_root, {})
    assert result["ok"] is True
    assert "project" in result
    assert "stats" in result


def test_overview_project_from_charter(index: GraphIndex, populated_root: Path):
    result = tools_read.gobp_overview(index, populated_root, {})
    assert result["project"]["name"] == "Test Project Charter"


def test_overview_stats_counts(index: GraphIndex, populated_root: Path):
    result = tools_read.gobp_overview(index, populated_root, {})
    assert result["stats"]["total_nodes"] == 4  # charter, feat_login, dec, session
    assert result["stats"]["total_edges"] == 2


def test_overview_main_topics(index: GraphIndex, populated_root: Path):
    result = tools_read.gobp_overview(index, populated_root, {})
    assert "auth:login.method" in result["main_topics"]


def test_overview_recent_decisions(index: GraphIndex, populated_root: Path):
    result = tools_read.gobp_overview(index, populated_root, {})
    assert len(result["recent_decisions"]) == 1
    assert result["recent_decisions"][0]["id"] == "dec:d001"


def test_overview_suggested_queries(index: GraphIndex, populated_root: Path):
    result = tools_read.gobp_overview(index, populated_root, {})
    assert len(result["suggested_next_queries"]) >= 3


# =============================================================================
# find tests
# =============================================================================


def test_find_exact_id(index: GraphIndex, populated_root: Path):
    result = tools_read.find(index, populated_root, {"query": "node:feat_login"})
    assert result["ok"] is True
    assert result["matches"][0]["match"] == "exact_id"


def test_find_substring(index: GraphIndex, populated_root: Path):
    result = tools_read.find(index, populated_root, {"query": "login"})
    assert result["ok"] is True
    assert result["count"] >= 1


def test_find_no_results(index: GraphIndex, populated_root: Path):
    result = tools_read.find(index, populated_root, {"query": "nonexistent_xyz"})
    assert result["ok"] is True
    assert result["count"] == 0


def test_find_missing_query(index: GraphIndex, populated_root: Path):
    result = tools_read.find(index, populated_root, {})
    assert result["ok"] is False
    assert "query" in result["error"]


def test_find_limit(index: GraphIndex, populated_root: Path):
    result = tools_read.find(index, populated_root, {"query": "node", "limit": 1})
    assert result["ok"] is True
    assert len(result["matches"]) <= 1


# =============================================================================
# signature tests
# =============================================================================


def test_signature_found(index: GraphIndex, populated_root: Path):
    result = tools_read.signature(index, populated_root, {"node_id": "node:feat_login"})
    assert result["ok"] is True
    assert result["signature"]["id"] == "node:feat_login"


def test_signature_not_found(index: GraphIndex, populated_root: Path):
    result = tools_read.signature(index, populated_root, {"node_id": "node:nonexistent"})
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_signature_missing_node_id(index: GraphIndex, populated_root: Path):
    result = tools_read.signature(index, populated_root, {})
    assert result["ok"] is False


# =============================================================================
# context tests
# =============================================================================


def test_context_found(index: GraphIndex, populated_root: Path):
    result = tools_read.context(index, populated_root, {"node_id": "node:feat_login"})
    assert result["ok"] is True
    assert result["node"]["id"] == "node:feat_login"
    assert len(result["outgoing"]) == 2  # implements + references
    assert len(result["decisions"]) == 1


def test_context_not_found(index: GraphIndex, populated_root: Path):
    result = tools_read.context(index, populated_root, {"node_id": "node:nonexistent"})
    assert result["ok"] is False


def test_context_references(index: GraphIndex, populated_root: Path):
    result = tools_read.context(index, populated_root, {"node_id": "node:feat_login"})
    refs = result["references"]
    assert len(refs) == 1
    assert refs[0]["doc_id"] == "doc:charter"


# =============================================================================
# session_recent tests
# =============================================================================


def test_session_recent_default(index: GraphIndex, populated_root: Path):
    result = tools_read.session_recent(index, populated_root, {})
    assert result["ok"] is True
    assert result["count"] == 1


def test_session_recent_actor_filter(index: GraphIndex, populated_root: Path):
    result = tools_read.session_recent(index, populated_root, {"actor": "Claude Test"})
    assert result["ok"] is True
    assert result["count"] == 1


def test_session_recent_actor_no_match(index: GraphIndex, populated_root: Path):
    result = tools_read.session_recent(index, populated_root, {"actor": "Unknown Actor"})
    assert result["count"] == 0


# =============================================================================
# decisions_for tests
# =============================================================================


def test_decisions_for_topic(index: GraphIndex, populated_root: Path):
    result = tools_read.decisions_for(index, populated_root, {"topic": "auth:login.method"})
    assert result["ok"] is True
    assert result["count"] == 1
    assert result["decisions"][0]["id"] == "dec:d001"


def test_decisions_for_node(index: GraphIndex, populated_root: Path):
    result = tools_read.decisions_for(index, populated_root, {"node_id": "node:feat_login"})
    assert result["ok"] is True
    assert result["count"] == 1


def test_decisions_for_missing_filter(index: GraphIndex, populated_root: Path):
    result = tools_read.decisions_for(index, populated_root, {})
    assert result["ok"] is False


def test_decisions_for_status_filter(index: GraphIndex, populated_root: Path):
    result = tools_read.decisions_for(
        index, populated_root, {"topic": "auth:login.method", "status": "WITHDRAWN"}
    )
    assert result["count"] == 0


# =============================================================================
# doc_sections tests
# =============================================================================


def test_doc_sections_found(index: GraphIndex, populated_root: Path):
    result = tools_read.doc_sections(index, populated_root, {"doc_id": "doc:charter"})
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["sections"][0]["heading"] == "Introduction"


def test_doc_sections_not_found(index: GraphIndex, populated_root: Path):
    result = tools_read.doc_sections(index, populated_root, {"doc_id": "doc:nonexistent"})
    assert result["ok"] is False


def test_doc_sections_not_document(index: GraphIndex, populated_root: Path):
    result = tools_read.doc_sections(index, populated_root, {"doc_id": "node:feat_login"})
    assert result["ok"] is False
    assert "not a Document" in result["error"]
```

**Run:**
```powershell
pytest tests/test_mcp_tools.py -v
```

**Acceptance criteria:**
- File `tests/test_mcp_tools.py` created
- At least 28 tests covering all 7 tools
- All tests pass
- Uses tmp_path fixture + real GraphIndex load
- Tests happy path + error cases for each tool

**Commit message:**
```
Wave 3 Task 8: write MCP read tools tests

- tests/test_mcp_tools.py: 28+ tests across 7 tools
- gobp_overview: 6 tests
- find: 5 tests
- signature: 3 tests
- context: 3 tests
- session_recent: 3 tests
- decisions_for: 4 tests
- doc_sections: 3 tests

Uses populated_root fixture with charter, feature, decision, session nodes + edges.
All 7 tools verified against MCP_TOOLS.md spec.
```

---

## TASK 9 — MCP config examples + README update

**Goal:** Ship example MCP client configs and update README with connection guide.

**Files to create:**

### `examples/mcp_configs/cursor_mcp.json`

```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["-m", "gobp.mcp.server"],
      "cwd": "D:\\GoBP",
      "env": {
        "GOBP_PROJECT_ROOT": "D:\\GoBP"
      }
    }
  }
}
```

### `examples/mcp_configs/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["-m", "gobp.mcp.server"],
      "env": {
        "GOBP_PROJECT_ROOT": "D:\\GoBP"
      }
    }
  }
}
```

### `examples/mcp_configs/claude_cli_config.json`

```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["-m", "gobp.mcp.server"],
      "env": {
        "GOBP_PROJECT_ROOT": "D:\\GoBP"
      }
    }
  }
}
```

### `examples/mcp_configs/continue_config.json`

```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["-m", "gobp.mcp.server"],
      "env": {
        "GOBP_PROJECT_ROOT": "D:\\GoBP"
      }
    }
  }
}
```

### `examples/mcp_configs/README.md`

```markdown
# GoBP MCP Client Configurations

Example configs for connecting MCP-capable AI clients to GoBP.

## Prerequisites

- GoBP installed: `pip install -e .` in a GoBP repo clone
- Python 3.10+ available in PATH
- GOBP_PROJECT_ROOT set to the folder containing `.gobp/` data

## Cursor IDE

Copy `cursor_mcp.json` to `.cursor/mcp.json` in your project folder.
Edit `cwd` and `GOBP_PROJECT_ROOT` to match your project path.
Restart Cursor.

## Claude Desktop

Copy `claude_desktop_config.json` content into:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Edit `GOBP_PROJECT_ROOT` to your project path. Restart Claude Desktop.

## Claude Code CLI

Copy `claude_cli_config.json` content into your Claude CLI config file
(usually `.claude.json` in project or home directory).

## Continue.dev

Copy `continue_config.json` content into `~/.continue/config.json`
(merge with existing mcpServers section).

## Verification

After connecting, the AI client should be able to call:
- `gobp_overview()` to see project info
- `find(query='...')` to search nodes
- Other read tools listed in `docs/MCP_TOOLS.md`

## Notes

- Per-project isolation: each project needs its own config pointing at its `.gobp/` folder
- Multiple projects: one config per project, each spawns its own MCP server subprocess
- See `docs/ARCHITECTURE.md` multi-project section for details
```

### Update `README.md` — add section after Installation

Add this section to `README.md` after the Installation section:

```markdown
## 🔌 Connect an AI Client (MCP)

GoBP exposes data to AI clients via Model Context Protocol (MCP). Any MCP-capable client can connect.

### Quick setup for Cursor IDE

Create `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["-m", "gobp.mcp.server"],
      "cwd": "${workspaceFolder}",
      "env": {
        "GOBP_PROJECT_ROOT": "${workspaceFolder}"
      }
    }
  }
}
```

Restart Cursor. The AI can now call GoBP tools like `gobp_overview`, `find`, `context`.

### Other clients

See `examples/mcp_configs/` for example configurations for:
- Cursor IDE
- Claude Desktop
- Claude Code CLI
- Continue.dev

See `docs/MCP_TOOLS.md` for the complete list of available tools.
```

**Acceptance criteria:**
- 4 example config files in `examples/mcp_configs/`
- `examples/mcp_configs/README.md` with setup instructions
- `README.md` has new "Connect an AI Client (MCP)" section
- No foundational docs modified

**Commit message:**
```
Wave 3 Task 9: MCP config examples and README update

- examples/mcp_configs/: 4 client configs (Cursor, Claude Desktop, Claude CLI, Continue)
- examples/mcp_configs/README.md: setup instructions per client
- README.md: add "Connect an AI Client (MCP)" section

After this commit, users can copy example configs, restart their MCP client,
and start querying GoBP data from their AI tools.
```

---

# POST-WAVE VERIFICATION

After all 9 tasks:

```powershell
# All tests pass
pytest tests/ -v
# Expected: 94+ tests (66 from Wave 0-2 + 28 from Wave 3)

# MCP server can start (will hang, Ctrl+C to exit)
python -c "from gobp.mcp import server; print('MCP module loads OK')"

# Git log
git log --oneline | Select-Object -First 9
# Expected: 9 Wave 3 commits
```

**Manual smoke test (optional, ~5 minutes):**

1. Copy `examples/mcp_configs/cursor_mcp.json` to `.cursor/mcp.json`
2. Edit paths to match `D:\GoBP`
3. Restart Cursor
4. In Cursor chat, ask: "What tools are available from gobp?"
5. Cursor should list 7 tools from GoBP MCP server

---

# ESCALATION TRIGGERS

Stop and escalate if:
- mcp SDK API changed (import errors, different Server signature)
- Tests fail and cannot be fixed after 3 retries
- Tool spec in Brief conflicts with docs/MCP_TOOLS.md (docs/MCP_TOOLS.md always wins)
- MCP server crashes on startup (not just tool call failure)

---

# WHAT COMES NEXT

After Wave 3 pushed:
- **CEO can connect Cursor** (or any MCP client) to GoBP and query real data
- **Wave 4** — CLI commands (`gobp init`, `gobp validate`)
- **Wave 5** — Write tools (node_upsert, decision_lock, session_log)
- **Wave 5** — Import tools (import_proposal, import_commit)
- **Wave 8** — MIHOS integration test (import MIHOS 31 docs as real dataset)

---

*Wave 3 Brief v0.1*
*Author: CTO Chat (Claude Opus 4.6)*
*Date: 2026-04-14*

◈
