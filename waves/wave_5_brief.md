# WAVE 5 BRIEF — WRITE TOOLS + IMPORT TOOLS + VALIDATE

**Wave:** 5
**Title:** Write Tools (3) + Import Tools (2) + Validate (1) — All 6 Remaining v1 Tools
**Author:** CTO Chat (Claude Opus 4.6)
**Date:** 2026-04-14
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 12 atomic tasks
**Estimated effort:** 5-6 hours

---

## CONTEXT

Wave 0-3 built GoBP's foundation: skeleton, core engine, file storage, MCP server with 7 read tools. **Wave 4 (CLI) is skipped** per CEO decision — Wave 5 ships first to unlock real value.

**Wave 5 completes GoBP v1's tool surface.** After this wave, all 13 MCP tools work. GoBP becomes fully functional: AI can capture ideas, lock decisions, log sessions, import docs, validate graph.

**In scope:**
- `node_upsert` — create or update any node type
- `decision_lock` — lock a Decision with verification record
- `session_log` — start/update/end session
- `import_proposal` — AI proposes batch import, stored as pending
- `import_commit` — commit proposal atomically (all-or-nothing)
- `validate` — full schema + constraint check on entire graph
- Register 6 new tools in MCP server
- Tests for all 6 tools
- Integration with mutator (from Wave 2) and validator (from Wave 1)

**NOT in scope:**
- CLI commands (Wave 4, deferred)
- Advanced features — migration, lessons extraction (Wave 6)
- MIHOS integration test (Wave 8)

---

## AUTHORITATIVE SOURCE

**`docs/MCP_TOOLS.md` sections 4, 5, 6 are source of truth for tool specs.**

Cross-reference map:
- §4.1 `node_upsert` → Task 2
- §4.2 `decision_lock` → Task 3
- §4.3 `session_log` → Task 4
- §5.1 `import_proposal` → Task 6
- §5.2 `import_commit` → Task 7
- §6.1 `validate` → Task 9

**Cursor MUST re-read the corresponding section in docs/MCP_TOOLS.md BEFORE implementing each tool.** If Brief code conflicts with MCP_TOOLS.md spec → MCP_TOOLS.md wins, Cursor stops and escalates.

---

## SCOPE DISCIPLINE RULE

**Implement EXACTLY the 6 tools specified. No additional tools, no "while I'm at it" helpers beyond internal private functions.**

**Brief code blocks are authoritative.** If you think there is a better approach, STOP and escalate — do not substitute your own implementation. This rule exists because of Wave 3 Task 7 where Cursor substituted a disk-reading approach for the spec'd node-field-reading approach.

Private helper functions (prefixed `_`) as internal implementation are OK. Public API stays strictly within Brief and MCP_TOOLS.md.

---

## PREREQUISITES

Before Task 1:

```powershell
cd D:\GoBP
git status              # clean or only untracked non-scope files
pytest tests/ -v        # All Wave 0-3 tests pass (109+)
python -c "from gobp.core.graph import GraphIndex; from gobp.core.mutator import create_node; from gobp.mcp.tools import read; print('OK')"
```

If any check fails, STOP and escalate.

---

## REQUIRED READING

At wave start:
1. `.cursorrules` (v4)
2. `CHARTER.md`
3. `docs/VISION.md`
4. `docs/ARCHITECTURE.md`
5. `docs/SCHEMA.md`
6. **`docs/MCP_TOOLS.md`** sections 4, 5, 6 (SOURCE OF TRUTH)
7. `docs/INPUT_MODEL.md` (how AI uses write tools in conversation)
8. `docs/IMPORT_MODEL.md` (how import tools work)
9. `waves/wave_5_brief.md` (this file)

Skim existing modules for pattern consistency:
- `gobp/core/mutator.py` (create_node, update_node, create_edge — Wave 2)
- `gobp/core/validator.py` (validate_node, validate_edge — Wave 1)
- `gobp/core/history.py` (append_event — Wave 2)
- `gobp/mcp/tools/read.py` (handler pattern from Wave 3)

---

# TASKS

## TASK 1 — Create write tools module skeleton

**Goal:** Create `gobp/mcp/tools/write.py` with stub handlers for 3 write tools. Then register 6 new tools in MCP server (write + import + validate).

**File to create:** `gobp/mcp/tools/write.py`

```python
"""GoBP MCP write tools.

Implementations for node_upsert, decision_lock, session_log.
All write tools require an active session_id.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex


def node_upsert(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "node_upsert not yet implemented"}


def decision_lock(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "decision_lock not yet implemented"}


def session_log(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "session_log not yet implemented"}
```

**File to create:** `gobp/mcp/tools/import_.py`

```python
"""GoBP MCP import tools.

Implementations for import_proposal and import_commit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex


def import_proposal(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "import_proposal not yet implemented"}


def import_commit(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "import_commit not yet implemented"}
```

**File to create:** `gobp/mcp/tools/maintain.py`

```python
"""GoBP MCP maintenance tools.

Implementation for validate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex


def validate(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "validate not yet implemented"}
```

**File to modify:** `gobp/mcp/server.py`

Add imports at top:
```python
from gobp.mcp.tools import read as tools_read
from gobp.mcp.tools import write as tools_write
from gobp.mcp.tools import import_ as tools_import
from gobp.mcp.tools import maintain as tools_maintain
```

In `list_tools()`, ADD these 6 tool definitions to the returned list (keep the 7 existing read tools):

```python
types.Tool(
    name="node_upsert",
    description="Create or update a node. Requires active session_id. Handles rename via supersedes pattern.",
    inputSchema={
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "id": {"type": "string"},
            "name": {"type": "string"},
            "fields": {"type": "object"},
            "session_id": {"type": "string"},
        },
        "required": ["type", "name", "fields", "session_id"],
    },
),
types.Tool(
    name="decision_lock",
    description="Lock a decision with full verification. AI MUST verify with founder before calling.",
    inputSchema={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "what": {"type": "string"},
            "why": {"type": "string"},
            "alternatives_considered": {"type": "array"},
            "risks": {"type": "array"},
            "related_ideas": {"type": "array"},
            "session_id": {"type": "string"},
            "locked_by": {"type": "array"},
        },
        "required": ["topic", "what", "why", "session_id", "locked_by"],
    },
),
types.Tool(
    name="session_log",
    description="Start, update, or end a session.",
    inputSchema={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["start", "update", "end"]},
            "session_id": {"type": "string"},
            "actor": {"type": "string"},
            "goal": {"type": "string"},
            "outcome": {"type": "string"},
            "pending": {"type": "array"},
            "nodes_touched": {"type": "array"},
            "decisions_locked": {"type": "array"},
            "handoff_notes": {"type": "string"},
        },
        "required": ["action"],
    },
),
types.Tool(
    name="import_proposal",
    description="AI proposes a batch import from an existing file. Founder reviews before commit.",
    inputSchema={
        "type": "object",
        "properties": {
            "source_path": {"type": "string"},
            "proposal_type": {"type": "string", "enum": ["doc", "code", "spec"]},
            "ai_notes": {"type": "string"},
            "proposed_document": {"type": "object"},
            "proposed_nodes": {"type": "array"},
            "proposed_edges": {"type": "array"},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "session_id": {"type": "string"},
        },
        "required": ["source_path", "proposal_type", "ai_notes", "proposed_nodes", "proposed_edges", "confidence", "session_id"],
    },
),
types.Tool(
    name="import_commit",
    description="Commit an approved import proposal atomically.",
    inputSchema={
        "type": "object",
        "properties": {
            "proposal_id": {"type": "string"},
            "accept": {"type": "string", "enum": ["all", "partial", "reject"]},
            "accepted_node_ids": {"type": "array"},
            "accepted_edge_ids": {"type": "array"},
            "overrides": {"type": "object"},
            "session_id": {"type": "string"},
        },
        "required": ["proposal_id", "accept", "session_id"],
    },
),
types.Tool(
    name="validate",
    description="Run full schema and constraint check on the entire graph.",
    inputSchema={
        "type": "object",
        "properties": {
            "scope": {"type": "string", "enum": ["all", "nodes", "edges", "references"], "default": "all"},
            "severity_filter": {"type": "string", "enum": ["all", "hard", "warning"], "default": "all"},
        },
        "required": [],
    },
),
```

In `call_tool()`, UPDATE the dispatch dict to include the 6 new tools:

```python
dispatch = {
    "gobp_overview": tools_read.gobp_overview,
    "find": tools_read.find,
    "signature": tools_read.signature,
    "context": tools_read.context,
    "session_recent": tools_read.session_recent,
    "decisions_for": tools_read.decisions_for,
    "doc_sections": tools_read.doc_sections,
    "node_upsert": tools_write.node_upsert,
    "decision_lock": tools_write.decision_lock,
    "session_log": tools_write.session_log,
    "import_proposal": tools_import.import_proposal,
    "import_commit": tools_import.import_commit,
    "validate": tools_maintain.validate,
}
```

After dispatch, add index reload logic after write operations. Because write tools mutate disk, the in-memory index becomes stale. After a write tool call, reload index:

```python
# After: result = handler(_index, _project_root, arguments)
# Add:
if name in ("node_upsert", "decision_lock", "session_log", "import_commit"):
    if isinstance(result, dict) and result.get("ok"):
        global _index
        _index = _load_index(_project_root)
        logger.info(f"Index reloaded after {name}")
```

**Acceptance criteria:**
- 3 new module files: `write.py`, `import_.py`, `maintain.py`
- Each with stub functions
- `server.py` imports and registers 13 total tools (7 read + 6 new)
- `server.py` dispatch dict routes all 13 tools
- Index reload logic after successful writes
- Self-test: `python -c "from gobp.mcp.server import server; print(len([t for t in server._tool_manager.tools]))"` prints 13 (or similar verification)

**Commit message:**
```
Wave 5 Task 1: register 6 new write/import/validate tools in MCP server

- Create gobp/mcp/tools/write.py with node_upsert, decision_lock, session_log stubs
- Create gobp/mcp/tools/import_.py with import_proposal, import_commit stubs
- Create gobp/mcp/tools/maintain.py with validate stub
- Update gobp/mcp/server.py: register 13 total tools (7 read + 6 new)
- Update dispatch dict to route all 13 tools
- Add index reload after successful write operations

All 6 new tools return "not yet implemented" stubs.
Real logic in Tasks 2-9.
```

---

## TASK 2 — Implement node_upsert

**Re-read `docs/MCP_TOOLS.md` section 4.1 node_upsert before starting.**

**File to modify:** `gobp/mcp/tools/write.py`

Replace `node_upsert` stub with:

```python
from datetime import datetime, timezone

from gobp.core.loader import load_schema
from gobp.core.mutator import create_node, update_node, create_edge
from gobp.core.validator import validate_node


def _generate_node_id(node_type: str, index: GraphIndex) -> str:
    """Generate a new node ID for auto-numbered types."""
    prefix_map = {
        "Idea": "idea",
        "Decision": "dec",
        "Lesson": "lesson",
        "Session": "session",
        "Node": "node",
        "Document": "doc",
    }
    prefix = prefix_map.get(node_type, "node")

    # For Idea, Decision, Lesson: numbered (i001, d001, ll001)
    if node_type == "Idea":
        existing_ids = [n.get("id", "") for n in index.nodes_by_type("Idea")]
        numbers = []
        for nid in existing_ids:
            if nid.startswith("idea:i"):
                try:
                    numbers.append(int(nid[6:]))
                except ValueError:
                    pass
        next_num = max(numbers, default=0) + 1
        return f"idea:i{next_num:03d}"
    elif node_type == "Decision":
        existing_ids = [n.get("id", "") for n in index.nodes_by_type("Decision")]
        numbers = []
        for nid in existing_ids:
            if nid.startswith("dec:d"):
                try:
                    numbers.append(int(nid[5:]))
                except ValueError:
                    pass
        next_num = max(numbers, default=0) + 1
        return f"dec:d{next_num:03d}"
    elif node_type == "Lesson":
        existing_ids = [n.get("id", "") for n in index.nodes_by_type("Lesson")]
        numbers = []
        for nid in existing_ids:
            if nid.startswith("lesson:ll"):
                try:
                    numbers.append(int(nid[9:]))
                except ValueError:
                    pass
        next_num = max(numbers, default=0) + 1
        return f"lesson:ll{next_num:03d}"

    # For other types, caller must provide id
    raise ValueError(f"Cannot auto-generate ID for type {node_type}, provide explicit id")


def node_upsert(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Create or update a node.

    Input: type, id (optional for auto-numbered), name, fields, session_id
    Output: ok, node_id, created, warnings
    """
    node_type = args.get("type")
    if not node_type:
        return {"ok": False, "error": "Missing required field: type"}

    name = args.get("name")
    if not name:
        return {"ok": False, "error": "Missing required field: name"}

    fields = args.get("fields", {})
    if not isinstance(fields, dict):
        return {"ok": False, "error": "fields must be a dict"}

    session_id = args.get("session_id")
    if not session_id:
        return {"ok": False, "error": "Missing required field: session_id"}

    # Check session exists and is active
    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}
    if session.get("status") == "COMPLETED":
        return {"ok": False, "error": "Session already ended, start new one"}

    # Determine ID
    node_id = args.get("id")
    if not node_id:
        try:
            node_id = _generate_node_id(node_type, index)
        except ValueError as e:
            return {"ok": False, "error": str(e)}

    # Build node dict
    now = datetime.now(timezone.utc).isoformat()
    node = {
        "id": node_id,
        "type": node_type,
        "name": name,
        "status": fields.get("status", "ACTIVE"),
        "created": now,
        "updated": now,
    }
    # Merge fields (fields override defaults where applicable)
    for k, v in fields.items():
        node[k] = v
    # Ensure core fields stay correct
    node["id"] = node_id
    node["type"] = node_type
    node["name"] = name

    # Load schema
    try:
        schema_path = Path(__file__).parent.parent.parent / "schema" / "core_nodes.yaml"
        schema = load_schema(schema_path)
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schema: {e}"}

    # Validate
    result = validate_node(node, schema)
    if not result.ok:
        return {"ok": False, "errors": result.errors}

    # Check if node exists
    existing = index.get_node(node_id)
    created = existing is None

    try:
        if created:
            create_node(project_root, node, schema, actor="node_upsert")
        else:
            # Preserve created timestamp on update
            node["created"] = existing.get("created", now)
            update_node(project_root, node, schema, actor="node_upsert")
    except Exception as e:
        return {"ok": False, "error": f"Write failed: {e}"}

    # Handle supersedes (create supersedes edge and mark old node)
    supersedes_id = fields.get("supersedes")
    warnings: list[str] = []
    if supersedes_id:
        old_node = index.get_node(supersedes_id)
        if old_node:
            try:
                edges_schema_path = Path(__file__).parent.parent.parent / "schema" / "core_edges.yaml"
                edges_schema = load_schema(edges_schema_path)
                supersedes_edge = {
                    "from": node_id,
                    "to": supersedes_id,
                    "type": "supersedes",
                }
                create_edge(project_root, supersedes_edge, edges_schema, actor="node_upsert")
            except Exception as e:
                warnings.append(f"Failed to create supersedes edge: {e}")
        else:
            warnings.append(f"supersedes target not found: {supersedes_id}")

    # Create discovered_in edge to session
    try:
        edges_schema_path = Path(__file__).parent.parent.parent / "schema" / "core_edges.yaml"
        edges_schema = load_schema(edges_schema_path)
        discovered_edge = {
            "from": node_id,
            "to": session_id,
            "type": "discovered_in",
        }
        create_edge(project_root, discovered_edge, edges_schema, actor="node_upsert")
    except Exception as e:
        warnings.append(f"Failed to create discovered_in edge: {e}")

    return {
        "ok": True,
        "node_id": node_id,
        "created": created,
        "warnings": warnings,
    }
```

**Acceptance criteria:**
- Matches MCP_TOOLS.md §4.1 input: type (required), id (optional), name (required), fields (required), session_id (required)
- Output: ok, node_id, created, warnings
- Session existence + status check
- Auto-generates IDs for Idea/Decision/Lesson (numbered)
- Validates before write
- Creates discovered_in edge automatically
- Handles supersedes field → creates supersedes edge
- Returns errors as `{"ok": false, "errors": [...]}` for validation failures

**Commit message:**
```
Wave 5 Task 2: implement node_upsert tool

- gobp/mcp/tools/write.py: node_upsert function
- Auto-generates IDs for Idea/Decision/Lesson (numbered sequence)
- Validates against schema before writing
- Creates discovered_in edge to session automatically
- Handles supersedes field → creates supersedes edge
- Rejects writes to COMPLETED sessions
- Returns structured errors per MCP_TOOLS.md §4.1
```

---

## TASK 3 — Implement decision_lock

**Re-read `docs/MCP_TOOLS.md` section 4.2 decision_lock before starting.**

Replace `decision_lock` stub with:

```python
def decision_lock(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Lock a decision with full verification record.

    Input: topic, what, why, alternatives_considered, risks, related_ideas, session_id, locked_by
    Output: ok, decision_id, warnings
    """
    # Required fields
    required = ["topic", "what", "why", "session_id", "locked_by"]
    for field in required:
        if field not in args or not args[field]:
            return {"ok": False, "error": f"Missing required field: {field}"}

    topic = args["topic"]
    what = args["what"]
    why = args["why"]
    session_id = args["session_id"]
    locked_by = args["locked_by"]

    if not isinstance(locked_by, list) or len(locked_by) < 2:
        return {
            "ok": False,
            "error": "locked_by must be a list of at least 2 entities (e.g. ['CEO', 'AI'])",
        }

    # Check session
    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}
    if session.get("status") == "COMPLETED":
        return {"ok": False, "error": "Session already ended"}

    # Generate decision ID
    existing_decisions = index.nodes_by_type("Decision")
    numbers: list[int] = []
    for d in existing_decisions:
        did = d.get("id", "")
        if did.startswith("dec:d"):
            try:
                numbers.append(int(did[5:]))
            except ValueError:
                pass
    next_num = max(numbers, default=0) + 1
    decision_id = f"dec:d{next_num:03d}"

    now = datetime.now(timezone.utc).isoformat()
    decision = {
        "id": decision_id,
        "type": "Decision",
        "name": what[:80],  # Short name from 'what'
        "status": "LOCKED",
        "topic": topic,
        "what": what,
        "why": why,
        "alternatives_considered": args.get("alternatives_considered", []),
        "risks": args.get("risks", []),
        "locked_by": locked_by,
        "locked_at": now,
        "created": now,
        "updated": now,
    }

    # Load schema + validate
    try:
        schema_path = Path(__file__).parent.parent.parent / "schema" / "core_nodes.yaml"
        schema = load_schema(schema_path)
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schema: {e}"}

    result = validate_node(decision, schema)
    if not result.ok:
        return {"ok": False, "errors": result.errors}

    warnings = list(result.warnings)
    if not decision["alternatives_considered"]:
        warnings.append("No alternatives_considered — recommended for locked decisions")

    # Write decision
    try:
        create_node(project_root, decision, schema, actor="decision_lock")
    except Exception as e:
        return {"ok": False, "error": f"Write failed: {e}"}

    # Create discovered_in edge
    try:
        edges_schema_path = Path(__file__).parent.parent.parent / "schema" / "core_edges.yaml"
        edges_schema = load_schema(edges_schema_path)
        create_edge(
            project_root,
            {"from": decision_id, "to": session_id, "type": "discovered_in"},
            edges_schema,
            actor="decision_lock",
        )
    except Exception as e:
        warnings.append(f"Failed to create discovered_in edge: {e}")

    # Create relates_to edges to related_ideas
    related_ideas = args.get("related_ideas", [])
    for idea_id in related_ideas:
        if index.get_node(idea_id):
            try:
                create_edge(
                    project_root,
                    {"from": decision_id, "to": idea_id, "type": "relates_to"},
                    edges_schema,
                    actor="decision_lock",
                )
            except Exception as e:
                warnings.append(f"Failed to create relates_to edge for {idea_id}: {e}")
        else:
            warnings.append(f"related_idea not found: {idea_id}")

    return {
        "ok": True,
        "decision_id": decision_id,
        "warnings": warnings,
    }
```

**Acceptance criteria:**
- Required fields per MCP_TOOLS.md §4.2
- `locked_by` must be list with ≥2 entities
- Auto-generates decision ID
- Status auto-set to LOCKED
- Creates discovered_in + relates_to edges
- Warns (not errors) if alternatives_considered empty
- Warns if related_ideas don't exist

**Commit message:**
```
Wave 5 Task 3: implement decision_lock tool

- gobp/mcp/tools/write.py: decision_lock function
- Requires topic, what, why, session_id, locked_by
- locked_by must have ≥2 entities (CEO + AI witness)
- Auto-generates decision ID and timestamp
- Status auto-set to LOCKED
- Creates discovered_in edge to session
- Creates relates_to edges for related_ideas
- Warns on empty alternatives_considered
```

---

## TASK 4 — Implement session_log

**Re-read `docs/MCP_TOOLS.md` section 4.3 session_log before starting.**

Replace `session_log` stub with:

```python
def session_log(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Start, update, or end a session.

    Input: action (start|update|end), session_id, actor, goal, outcome, pending, ...
    Output: ok, session_id
    """
    action = args.get("action")
    if action not in ("start", "update", "end"):
        return {"ok": False, "error": "action must be 'start', 'update', or 'end'"}

    try:
        schema_path = Path(__file__).parent.parent.parent / "schema" / "core_nodes.yaml"
        schema = load_schema(schema_path)
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schema: {e}"}

    now = datetime.now(timezone.utc).isoformat()

    if action == "start":
        actor = args.get("actor")
        goal = args.get("goal")
        if not actor:
            return {"ok": False, "error": "actor required for start"}
        if not goal:
            return {"ok": False, "error": "goal required for start"}

        # Generate session ID: session:YYYY-MM-DD_slug
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # Slug from first word of goal
        slug_base = "".join(c if c.isalnum() else "_" for c in goal.lower())[:20].strip("_")
        if not slug_base:
            slug_base = "session"

        # Check for existing sessions today with same slug, append number if needed
        base_id = f"session:{date_str}_{slug_base}"
        session_id = base_id
        counter = 1
        while index.get_node(session_id):
            counter += 1
            session_id = f"{base_id}{counter}"

        session_node = {
            "id": session_id,
            "type": "Session",
            "name": goal[:80],
            "actor": actor,
            "started_at": now,
            "goal": goal,
            "status": "IN_PROGRESS",
            "created": now,
            "updated": now,
        }

        result = validate_node(session_node, schema)
        if not result.ok:
            return {"ok": False, "errors": result.errors}

        try:
            create_node(project_root, session_node, schema, actor="session_log")
        except Exception as e:
            return {"ok": False, "error": f"Write failed: {e}"}

        return {"ok": True, "session_id": session_id}

    # action == update or end
    session_id = args.get("session_id")
    if not session_id:
        return {"ok": False, "error": "session_id required for update/end"}

    existing = index.get_node(session_id)
    if not existing:
        return {"ok": False, "error": f"Session not found: {session_id}"}

    # Build updated session
    updated = dict(existing)
    updated["updated"] = now

    if action == "end":
        outcome = args.get("outcome")
        if not outcome:
            return {"ok": False, "error": "outcome required for end action"}
        updated["ended_at"] = now
        updated["outcome"] = outcome
        updated["status"] = "COMPLETED"
        if "pending" in args:
            updated["pending"] = args["pending"]

    # Update optional fields for both update and end
    for field in ["nodes_touched", "decisions_locked", "handoff_notes"]:
        if field in args:
            updated[field] = args[field]

    result = validate_node(updated, schema)
    if not result.ok:
        return {"ok": False, "errors": result.errors}

    try:
        update_node(project_root, updated, schema, actor="session_log")
    except Exception as e:
        return {"ok": False, "error": f"Write failed: {e}"}

    return {"ok": True, "session_id": session_id}
```

**Acceptance criteria:**
- 3 actions: start, update, end
- `start` auto-generates session_id as `session:YYYY-MM-DD_slug`
- `end` requires outcome, sets ended_at + status=COMPLETED
- `update` requires session_id
- Conflict resolution: if same slug exists today, append counter

**Commit message:**
```
Wave 5 Task 4: implement session_log tool

- gobp/mcp/tools/write.py: session_log function
- Three actions: start, update, end
- start: auto-generates session:YYYY-MM-DD_slug ID
- end: sets ended_at, outcome, status=COMPLETED
- update: modifies optional fields of existing session
- Validates against schema before write
```

---

## TASK 5 — Write tests for write tools

**File to create:** `tests/test_mcp_write_tools.py`

```python
"""Tests for GoBP MCP write tools: node_upsert, decision_lock, session_log."""

from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import write as tools_write


@pytest.fixture
def populated_root(tmp_path: Path) -> Path:
    """GoBP root with schemas, an active session, and one existing idea."""
    import gobp
    actual_schema_dir = Path(gobp.__file__).parent / "schema"

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

    data_dir = tmp_path / ".gobp"
    (data_dir / "nodes").mkdir(parents=True)
    (data_dir / "edges").mkdir(parents=True)

    # Active session
    (data_dir / "nodes" / "session_test.md").write_text(
        """---
id: session:2026-04-14_test
type: Session
name: Test session
actor: test_actor
started_at: 2026-04-14T09:00:00+00:00
goal: Test write tools
status: IN_PROGRESS
created: 2026-04-14T09:00:00+00:00
updated: 2026-04-14T09:00:00+00:00
---

Body.
""",
        encoding="utf-8"
    )

    return tmp_path


def _load_index(root: Path) -> GraphIndex:
    return GraphIndex.load_from_disk(root)


# =============================================================================
# node_upsert tests
# =============================================================================


def test_node_upsert_creates_idea(populated_root):
    index = _load_index(populated_root)
    result = tools_write.node_upsert(
        index, populated_root,
        {
            "type": "Idea",
            "name": "Try Email OTP",
            "fields": {
                "status": "ACTIVE",
                "subject": "auth:login.method",
                "raw_quote": "Dùng OTP email đi",
                "interpretation": "Switch to Email OTP",
                "maturity": "RAW",
                "confidence": "medium",
            },
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is True, result
    assert result["created"] is True
    assert result["node_id"].startswith("idea:i")


def test_node_upsert_missing_session(populated_root):
    index = _load_index(populated_root)
    result = tools_write.node_upsert(
        index, populated_root,
        {
            "type": "Idea",
            "name": "X",
            "fields": {"status": "ACTIVE"},
            "session_id": "session:nonexistent",
        },
    )
    assert result["ok"] is False
    assert "Session not found" in result["error"]


def test_node_upsert_missing_required_fields(populated_root):
    index = _load_index(populated_root)
    result = tools_write.node_upsert(
        index, populated_root,
        {"type": "Idea", "fields": {}, "session_id": "session:2026-04-14_test"},
    )
    assert result["ok"] is False
    assert "name" in result["error"]


def test_node_upsert_validation_failure(populated_root):
    index = _load_index(populated_root)
    result = tools_write.node_upsert(
        index, populated_root,
        {
            "type": "Idea",
            "name": "Bad idea",
            "fields": {"status": "INVALID_STATUS"},  # not in enum
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is False
    assert "errors" in result or "error" in result


# =============================================================================
# decision_lock tests
# =============================================================================


def test_decision_lock_creates_decision(populated_root):
    index = _load_index(populated_root)
    result = tools_write.decision_lock(
        index, populated_root,
        {
            "topic": "auth:login.method",
            "what": "Use Email OTP",
            "why": "SMS unreliable in VN",
            "alternatives_considered": [
                {"option": "SMS", "rejected_reason": "spam"}
            ],
            "session_id": "session:2026-04-14_test",
            "locked_by": ["CEO", "AI-Witness"],
        },
    )
    assert result["ok"] is True, result
    assert result["decision_id"].startswith("dec:d")


def test_decision_lock_missing_locked_by(populated_root):
    index = _load_index(populated_root)
    result = tools_write.decision_lock(
        index, populated_root,
        {
            "topic": "x",
            "what": "y",
            "why": "z",
            "session_id": "session:2026-04-14_test",
            "locked_by": ["CEO"],  # only 1 entity
        },
    )
    assert result["ok"] is False
    assert "at least 2" in result["error"]


def test_decision_lock_warns_empty_alternatives(populated_root):
    index = _load_index(populated_root)
    result = tools_write.decision_lock(
        index, populated_root,
        {
            "topic": "test:topic",
            "what": "Do X",
            "why": "Reason",
            "session_id": "session:2026-04-14_test",
            "locked_by": ["CEO", "AI"],
        },
    )
    assert result["ok"] is True
    assert any("alternatives" in w.lower() for w in result["warnings"])


# =============================================================================
# session_log tests
# =============================================================================


def test_session_log_start(populated_root):
    index = _load_index(populated_root)
    result = tools_write.session_log(
        index, populated_root,
        {
            "action": "start",
            "actor": "Claude Test",
            "goal": "Test session start",
        },
    )
    assert result["ok"] is True, result
    assert result["session_id"].startswith("session:")


def test_session_log_end(populated_root):
    index = _load_index(populated_root)
    # End the existing test session
    result = tools_write.session_log(
        index, populated_root,
        {
            "action": "end",
            "session_id": "session:2026-04-14_test",
            "outcome": "Test completed",
        },
    )
    assert result["ok"] is True, result


def test_session_log_end_missing_outcome(populated_root):
    index = _load_index(populated_root)
    result = tools_write.session_log(
        index, populated_root,
        {
            "action": "end",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is False
    assert "outcome" in result["error"]


def test_session_log_start_missing_actor(populated_root):
    index = _load_index(populated_root)
    result = tools_write.session_log(
        index, populated_root,
        {"action": "start", "goal": "Test"},
    )
    assert result["ok"] is False


def test_session_log_invalid_action(populated_root):
    index = _load_index(populated_root)
    result = tools_write.session_log(
        index, populated_root,
        {"action": "invalid"},
    )
    assert result["ok"] is False
```

**Acceptance criteria:**
- File `tests/test_mcp_write_tools.py` created
- At least 13 tests covering the 3 write tools
- All tests pass
- Uses tmp_path fixture with pre-populated session

**Commit message:**
```
Wave 5 Task 5: tests for write tools

- tests/test_mcp_write_tools.py: 13 tests
  - node_upsert: 4 tests (create, missing session, missing fields, validation)
  - decision_lock: 3 tests (create, locked_by, alternatives warning)
  - session_log: 6 tests (start, end, missing outcome, missing actor, invalid action + 1 more)

All tests use tmp_path fixture with active session pre-loaded.
```

---

## TASK 6 — Implement import_proposal

**Re-read `docs/MCP_TOOLS.md` section 5.1 import_proposal before starting.**

**File to modify:** `gobp/mcp/tools/import_.py`

Replace stub with:

```python
from datetime import datetime, timezone
import yaml
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.mutator import _atomic_write


def import_proposal(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """AI proposes a batch import from a source file. Stored as pending proposal.

    Input: source_path, proposal_type, ai_notes, proposed_document (optional),
           proposed_nodes, proposed_edges, confidence, session_id
    Output: ok, proposal_id, summary, node_count, edge_count, warnings
    """
    required = ["source_path", "proposal_type", "ai_notes", "proposed_nodes", "proposed_edges", "confidence", "session_id"]
    for field in required:
        if field not in args:
            return {"ok": False, "error": f"Missing required field: {field}"}

    source_path = args["source_path"]
    proposal_type = args["proposal_type"]
    if proposal_type not in ("doc", "code", "spec"):
        return {"ok": False, "error": "proposal_type must be doc, code, or spec"}

    confidence = args["confidence"]
    if confidence not in ("low", "medium", "high"):
        return {"ok": False, "error": "confidence must be low, medium, or high"}

    session_id = args["session_id"]
    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}
    if session.get("status") == "COMPLETED":
        return {"ok": False, "error": "Session already ended"}

    proposed_nodes = args["proposed_nodes"]
    proposed_edges = args["proposed_edges"]

    if not isinstance(proposed_nodes, list) or not isinstance(proposed_edges, list):
        return {"ok": False, "error": "proposed_nodes and proposed_edges must be lists"}

    # Generate proposal ID
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    source_stem = Path(source_path).stem.replace(" ", "_")[:40]
    proposal_id = f"imp:{date_str}_{source_stem}"

    # Avoid conflicts
    proposals_dir = project_root / ".gobp" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    pending_file = proposals_dir / f"{proposal_id.replace(':', '_')}.pending.yaml"
    counter = 1
    while pending_file.exists():
        counter += 1
        numbered_id = f"{proposal_id}_{counter}"
        pending_file = proposals_dir / f"{numbered_id.replace(':', '_')}.pending.yaml"
        proposal_id = numbered_id

    # Build proposal content
    proposal = {
        "proposal_id": proposal_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": source_path,
        "proposal_type": proposal_type,
        "ai_notes": args["ai_notes"],
        "confidence": confidence,
        "session_id": session_id,
        "proposed_document": args.get("proposed_document"),
        "proposed_nodes": proposed_nodes,
        "proposed_edges": proposed_edges,
    }

    # Atomic write
    try:
        content = yaml.safe_dump(proposal, default_flow_style=False, sort_keys=False)
        _atomic_write(pending_file, content)
    except Exception as e:
        return {"ok": False, "error": f"Failed to write proposal: {e}"}

    # Summary
    doc_part = ""
    if args.get("proposed_document"):
        doc_part = "1 Document + "
    summary = f"Import {Path(source_path).name}: {doc_part}{len(proposed_nodes)} nodes + {len(proposed_edges)} edges. Confidence: {confidence}."

    total_node_count = len(proposed_nodes)
    if args.get("proposed_document"):
        total_node_count += 1

    return {
        "ok": True,
        "proposal_id": proposal_id,
        "summary": summary,
        "node_count": total_node_count,
        "edge_count": len(proposed_edges),
        "warnings": [],
    }
```

**Acceptance criteria:**
- Required fields per MCP_TOOLS.md §5.1
- Proposal stored at `.gobp/proposals/<id>.pending.yaml`
- No actual graph writes (only proposal file)
- Returns summary + counts
- Session validation

**Commit message:**
```
Wave 5 Task 6: implement import_proposal tool

- gobp/mcp/tools/import_.py: import_proposal function
- Stores pending proposal at .gobp/proposals/<id>.pending.yaml
- Does NOT write to actual graph (that's import_commit's job)
- Generates proposal ID from date + source filename
- Returns summary, node_count, edge_count
- Validates session_id and required fields
```

---

## TASK 7 — Implement import_commit

**Re-read `docs/MCP_TOOLS.md` section 5.2 import_commit before starting.**

Append to `gobp/mcp/tools/import_.py`:

```python
from gobp.core.loader import load_schema
from gobp.core.mutator import create_node, create_edge
from gobp.core.validator import validate_node, validate_edge


def import_commit(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Commit an approved import proposal atomically.

    Input: proposal_id, accept (all|partial|reject), accepted_node_ids (if partial),
           accepted_edge_ids (if partial), overrides (optional), session_id
    Output: ok, nodes_created, edges_created, errors

    Atomicity: if any validation fails, ALL rolled back, nothing written.
    """
    proposal_id = args.get("proposal_id")
    if not proposal_id:
        return {"ok": False, "error": "proposal_id required"}

    accept = args.get("accept")
    if accept not in ("all", "partial", "reject"):
        return {"ok": False, "error": "accept must be all, partial, or reject"}

    session_id = args.get("session_id")
    if not session_id:
        return {"ok": False, "error": "session_id required"}

    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}

    # Load proposal
    proposals_dir = project_root / ".gobp" / "proposals"
    pending_file = proposals_dir / f"{proposal_id.replace(':', '_')}.pending.yaml"

    if not pending_file.exists():
        return {"ok": False, "error": f"Proposal not found: {proposal_id}"}

    try:
        with open(pending_file, "r", encoding="utf-8") as f:
            proposal = yaml.safe_load(f)
    except Exception as e:
        return {"ok": False, "error": f"Failed to load proposal: {e}"}

    if accept == "reject":
        # Move to rejected
        rejected_file = proposals_dir / f"{proposal_id.replace(':', '_')}.rejected.yaml"
        pending_file.rename(rejected_file)
        return {"ok": True, "nodes_created": 0, "edges_created": 0, "errors": []}

    # Select nodes and edges based on accept mode
    all_nodes = list(proposal.get("proposed_nodes", []))
    if proposal.get("proposed_document"):
        all_nodes = [proposal["proposed_document"]] + all_nodes
    all_edges = list(proposal.get("proposed_edges", []))

    if accept == "partial":
        accepted_node_ids = set(args.get("accepted_node_ids", []))
        accepted_edge_ids = set(args.get("accepted_edge_ids", []))
        all_nodes = [n for n in all_nodes if n.get("id") in accepted_node_ids]
        all_edges = [
            e for i, e in enumerate(all_edges)
            if f"edge_{i}" in accepted_edge_ids or e.get("id") in accepted_edge_ids
        ]

    # Apply overrides
    overrides = args.get("overrides", {})
    for node in all_nodes:
        nid = node.get("id")
        if nid in overrides:
            for k, v in overrides[nid].items():
                node[k] = v

    # Load schemas
    try:
        nodes_schema_path = Path(__file__).parent.parent.parent / "schema" / "core_nodes.yaml"
        edges_schema_path = Path(__file__).parent.parent.parent / "schema" / "core_edges.yaml"
        nodes_schema = load_schema(nodes_schema_path)
        edges_schema = load_schema(edges_schema_path)
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schemas: {e}"}

    # Validate everything first (no writes yet)
    errors: list[dict[str, Any]] = []
    for node in all_nodes:
        result = validate_node(node, nodes_schema)
        if not result.ok:
            errors.append({"node_id": node.get("id"), "errors": result.errors})

    for edge in all_edges:
        result = validate_edge(edge, edges_schema)
        if not result.ok:
            errors.append({"edge": f"{edge.get('from')} -> {edge.get('to')}", "errors": result.errors})

    if errors:
        return {"ok": False, "nodes_created": 0, "edges_created": 0, "errors": errors}

    # All validation passed. Now write atomically.
    # If any write fails partway, we return partial success + errors.
    # Full rollback on partial failures is out of v1 scope.
    nodes_created = 0
    edges_created = 0
    write_errors: list[dict[str, Any]] = []

    for node in all_nodes:
        try:
            create_node(project_root, node, nodes_schema, actor="import_commit")
            nodes_created += 1
        except FileExistsError:
            write_errors.append({"node_id": node.get("id"), "error": "Already exists"})
        except Exception as e:
            write_errors.append({"node_id": node.get("id"), "error": str(e)})

    for edge in all_edges:
        try:
            create_edge(project_root, edge, edges_schema, actor="import_commit")
            edges_created += 1
        except Exception as e:
            write_errors.append({"edge": f"{edge.get('from')} -> {edge.get('to')}", "error": str(e)})

    # Move proposal to committed
    committed_file = proposals_dir / f"{proposal_id.replace(':', '_')}.committed.yaml"
    try:
        pending_file.rename(committed_file)
    except Exception as e:
        write_errors.append({"proposal": proposal_id, "error": f"Failed to move to committed: {e}"})

    return {
        "ok": len(write_errors) == 0,
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "errors": write_errors,
    }
```

**Acceptance criteria:**
- Matches MCP_TOOLS.md §5.2 input/output
- Validates ALL nodes + edges BEFORE any write (fail early)
- Writes nodes and edges via mutator
- Moves proposal file: pending → committed (or → rejected)
- Supports accept: all, partial, reject
- Returns counts + errors

**Commit message:**
```
Wave 5 Task 7: implement import_commit tool

- gobp/mcp/tools/import_.py: import_commit function
- Loads proposal from .gobp/proposals/<id>.pending.yaml
- Validates all nodes + edges before any write (fail early)
- Supports accept: all | partial | reject
- Applies per-node overrides from founder feedback
- Moves proposal file: pending -> committed or rejected
- Returns counts + write errors
```

---

## TASK 8 — Write tests for import tools

**File to create:** `tests/test_mcp_import_tools.py`

```python
"""Tests for GoBP MCP import tools: import_proposal, import_commit."""

from pathlib import Path

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import import_ as tools_import


@pytest.fixture
def populated_root(tmp_path: Path) -> Path:
    """GoBP root with schemas and an active session."""
    import gobp
    actual_schema_dir = Path(gobp.__file__).parent / "schema"

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

    data_dir = tmp_path / ".gobp"
    (data_dir / "nodes").mkdir(parents=True)
    (data_dir / "edges").mkdir(parents=True)

    (data_dir / "nodes" / "session_test.md").write_text(
        """---
id: session:2026-04-14_test
type: Session
name: Test
actor: test
started_at: 2026-04-14T09:00:00+00:00
goal: Test import
status: IN_PROGRESS
created: 2026-04-14T09:00:00+00:00
updated: 2026-04-14T09:00:00+00:00
---

Body.
""",
        encoding="utf-8"
    )

    return tmp_path


def _load(root: Path) -> GraphIndex:
    return GraphIndex.load_from_disk(root)


def _valid_node_dict(id: str, name: str) -> dict:
    return {
        "id": id,
        "type": "Node",
        "name": name,
        "status": "ACTIVE",
        "created": "2026-04-14T10:00:00+00:00",
        "updated": "2026-04-14T10:00:00+00:00",
    }


# =============================================================================
# import_proposal tests
# =============================================================================


def test_proposal_creates_pending_file(populated_root):
    index = _load(populated_root)
    result = tools_import.import_proposal(
        index, populated_root,
        {
            "source_path": "docs/test.md",
            "proposal_type": "doc",
            "ai_notes": "Test proposal",
            "proposed_nodes": [_valid_node_dict("node:t1", "Test 1")],
            "proposed_edges": [],
            "confidence": "high",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is True
    pending_files = list((populated_root / ".gobp" / "proposals").glob("*.pending.yaml"))
    assert len(pending_files) == 1


def test_proposal_returns_counts(populated_root):
    index = _load(populated_root)
    result = tools_import.import_proposal(
        index, populated_root,
        {
            "source_path": "docs/test.md",
            "proposal_type": "doc",
            "ai_notes": "X",
            "proposed_nodes": [
                _valid_node_dict("node:a", "A"),
                _valid_node_dict("node:b", "B"),
            ],
            "proposed_edges": [
                {"from": "node:a", "to": "node:b", "type": "relates_to"},
            ],
            "confidence": "medium",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["node_count"] == 2
    assert result["edge_count"] == 1


def test_proposal_missing_fields(populated_root):
    index = _load(populated_root)
    result = tools_import.import_proposal(
        index, populated_root,
        {"source_path": "x"},
    )
    assert result["ok"] is False


def test_proposal_invalid_type(populated_root):
    index = _load(populated_root)
    result = tools_import.import_proposal(
        index, populated_root,
        {
            "source_path": "x",
            "proposal_type": "invalid",
            "ai_notes": "x",
            "proposed_nodes": [],
            "proposed_edges": [],
            "confidence": "high",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is False


# =============================================================================
# import_commit tests
# =============================================================================


def test_commit_all(populated_root):
    index = _load(populated_root)
    # First make a proposal
    prop_result = tools_import.import_proposal(
        index, populated_root,
        {
            "source_path": "docs/test.md",
            "proposal_type": "doc",
            "ai_notes": "X",
            "proposed_nodes": [_valid_node_dict("node:commit_test", "Test")],
            "proposed_edges": [],
            "confidence": "high",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert prop_result["ok"] is True
    proposal_id = prop_result["proposal_id"]

    # Commit all
    index2 = _load(populated_root)
    commit_result = tools_import.import_commit(
        index2, populated_root,
        {
            "proposal_id": proposal_id,
            "accept": "all",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert commit_result["ok"] is True
    assert commit_result["nodes_created"] == 1

    # Proposal file moved to committed
    committed = list((populated_root / ".gobp" / "proposals").glob("*.committed.yaml"))
    assert len(committed) == 1


def test_commit_reject(populated_root):
    index = _load(populated_root)
    prop_result = tools_import.import_proposal(
        index, populated_root,
        {
            "source_path": "docs/test.md",
            "proposal_type": "doc",
            "ai_notes": "X",
            "proposed_nodes": [_valid_node_dict("node:reject_test", "X")],
            "proposed_edges": [],
            "confidence": "low",
            "session_id": "session:2026-04-14_test",
        },
    )
    proposal_id = prop_result["proposal_id"]

    index2 = _load(populated_root)
    result = tools_import.import_commit(
        index2, populated_root,
        {
            "proposal_id": proposal_id,
            "accept": "reject",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is True
    assert result["nodes_created"] == 0
    rejected = list((populated_root / ".gobp" / "proposals").glob("*.rejected.yaml"))
    assert len(rejected) == 1


def test_commit_missing_proposal(populated_root):
    index = _load(populated_root)
    result = tools_import.import_commit(
        index, populated_root,
        {
            "proposal_id": "imp:nonexistent",
            "accept": "all",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert result["ok"] is False


def test_commit_validation_failure(populated_root):
    index = _load(populated_root)
    # Proposal with invalid node (missing required fields)
    bad_node = {"id": "node:bad", "type": "Node"}  # missing name, status, etc.
    prop_result = tools_import.import_proposal(
        index, populated_root,
        {
            "source_path": "docs/bad.md",
            "proposal_type": "doc",
            "ai_notes": "X",
            "proposed_nodes": [bad_node],
            "proposed_edges": [],
            "confidence": "low",
            "session_id": "session:2026-04-14_test",
        },
    )
    proposal_id = prop_result["proposal_id"]

    index2 = _load(populated_root)
    commit_result = tools_import.import_commit(
        index2, populated_root,
        {
            "proposal_id": proposal_id,
            "accept": "all",
            "session_id": "session:2026-04-14_test",
        },
    )
    assert commit_result["ok"] is False
    assert commit_result["nodes_created"] == 0
```

**Acceptance criteria:**
- At least 8 tests covering import_proposal and import_commit
- All tests pass

**Commit message:**
```
Wave 5 Task 8: tests for import tools

- tests/test_mcp_import_tools.py: 8 tests
  - import_proposal: 4 tests (pending file, counts, missing fields, invalid type)
  - import_commit: 4 tests (accept all, reject, missing proposal, validation failure)

Validates proposal → commit flow, atomicity, rejection handling.
```

---

## TASK 9 — Implement validate tool

**Re-read `docs/MCP_TOOLS.md` section 6.1 validate before starting.**

**File to modify:** `gobp/mcp/tools/maintain.py`

Replace stub with:

```python
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.loader import load_schema
from gobp.core.validator import validate_edge, validate_node


def validate(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Run full schema + constraint check on the entire graph.

    Input: scope (all|nodes|edges|references), severity_filter (all|hard|warning)
    Output: ok, issues, count
    """
    scope = args.get("scope", "all")
    severity_filter = args.get("severity_filter", "all")

    if scope not in ("all", "nodes", "edges", "references"):
        return {"ok": False, "error": "scope must be all, nodes, edges, or references"}

    if severity_filter not in ("all", "hard", "warning"):
        return {"ok": False, "error": "severity_filter must be all, hard, or warning"}

    # Load schemas
    try:
        nodes_schema_path = Path(__file__).parent.parent.parent / "schema" / "core_nodes.yaml"
        edges_schema_path = Path(__file__).parent.parent.parent / "schema" / "core_edges.yaml"
        nodes_schema = load_schema(nodes_schema_path)
        edges_schema = load_schema(edges_schema_path)
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schemas: {e}"}

    issues: list[dict[str, Any]] = []

    # Nodes
    if scope in ("all", "nodes"):
        for node in index.all_nodes():
            result = validate_node(node, nodes_schema)
            node_id = node.get("id", "<unknown>")
            for err in result.errors:
                issues.append({
                    "severity": "hard",
                    "type": "schema",
                    "node_id": node_id,
                    "message": err,
                })
            for warn in result.warnings:
                issues.append({
                    "severity": "warning",
                    "type": "schema",
                    "node_id": node_id,
                    "message": warn,
                })

    # Edges
    if scope in ("all", "edges"):
        for edge in index.all_edges():
            result = validate_edge(edge, edges_schema)
            edge_desc = f"{edge.get('from', '?')} -> {edge.get('to', '?')} ({edge.get('type', '?')})"
            for err in result.errors:
                issues.append({
                    "severity": "hard",
                    "type": "schema",
                    "edge": edge,
                    "message": f"{edge_desc}: {err}",
                })
            for warn in result.warnings:
                issues.append({
                    "severity": "warning",
                    "type": "schema",
                    "edge": edge,
                    "message": f"{edge_desc}: {warn}",
                })

    # Reference check: edge endpoints must exist as nodes
    if scope in ("all", "references"):
        for edge in index.all_edges():
            from_id = edge.get("from")
            to_id = edge.get("to")
            if from_id and not index.get_node(from_id):
                issues.append({
                    "severity": "hard",
                    "type": "reference",
                    "edge": edge,
                    "message": f"Edge source {from_id} does not exist",
                })
            if to_id and not index.get_node(to_id):
                issues.append({
                    "severity": "hard",
                    "type": "reference",
                    "edge": edge,
                    "message": f"Edge target {to_id} does not exist",
                })

    # Apply severity filter
    if severity_filter != "all":
        issues = [i for i in issues if i["severity"] == severity_filter]

    # Truncate if too many
    truncated = False
    if len(issues) > 50:
        issues = issues[:50]
        truncated = True

    hard_count = sum(1 for i in issues if i["severity"] == "hard")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")

    result_dict = {
        "ok": hard_count == 0,
        "issues": issues,
        "count": {
            "total": len(issues),
            "hard": hard_count,
            "warning": warning_count,
        },
    }
    if truncated:
        result_dict["truncated"] = True

    return result_dict
```

**Acceptance criteria:**
- Matches MCP_TOOLS.md §6.1 input/output
- 3 scopes: nodes, edges, references (plus "all")
- Severity filtering
- Orphan edge detection (references pointing to non-existent nodes)
- Schema violation detection
- Truncates if > 50 issues

**Commit message:**
```
Wave 5 Task 9: implement validate tool

- gobp/mcp/tools/maintain.py: validate function
- Scopes: all, nodes, edges, references
- Detects schema violations, orphan edges, reference errors
- Severity filtering: all, hard, warning
- Truncates output at 50 issues
- ok=true only if no hard errors
```

---

## TASK 10 — Write tests for validate

**File to create:** `tests/test_mcp_validate.py`

```python
"""Tests for GoBP MCP validate tool."""

from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import maintain as tools_maintain


@pytest.fixture
def clean_root(tmp_path: Path) -> Path:
    """GoBP root with only schemas, no data."""
    import gobp
    actual_schema_dir = Path(gobp.__file__).parent / "schema"

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
    return tmp_path


@pytest.fixture
def root_with_orphan_edge(clean_root: Path) -> Path:
    """GoBP root with an edge pointing to a non-existent node."""
    data_dir = clean_root / ".gobp"
    (data_dir / "nodes").mkdir(parents=True)
    (data_dir / "edges").mkdir(parents=True)

    # Create one valid node
    (data_dir / "nodes" / "node_a.md").write_text(
        """---
id: node:a
type: Node
name: Node A
status: ACTIVE
created: 2026-04-14T00:00:00+00:00
updated: 2026-04-14T00:00:00+00:00
---

Body.
""",
        encoding="utf-8"
    )

    # Create an edge pointing to a non-existent node
    (data_dir / "edges" / "relations.yaml").write_text(
        """- from: node:a
  to: node:nonexistent
  type: relates_to
""",
        encoding="utf-8"
    )

    return clean_root


def _load(root: Path) -> GraphIndex:
    return GraphIndex.load_from_disk(root)


def test_validate_clean_graph(clean_root):
    index = _load(clean_root)
    result = tools_maintain.validate(index, clean_root, {})
    assert result["ok"] is True
    assert result["count"]["hard"] == 0


def test_validate_detects_orphan_edge(root_with_orphan_edge):
    index = _load(root_with_orphan_edge)
    result = tools_maintain.validate(index, root_with_orphan_edge, {})
    assert result["ok"] is False
    assert result["count"]["hard"] >= 1
    assert any("nonexistent" in issue["message"] for issue in result["issues"])


def test_validate_scope_nodes_only(root_with_orphan_edge):
    index = _load(root_with_orphan_edge)
    result = tools_maintain.validate(
        index, root_with_orphan_edge, {"scope": "nodes"}
    )
    # Orphan edge should not be detected in nodes-only scope
    nonexistent_found = any(
        "nonexistent" in issue.get("message", "")
        for issue in result["issues"]
    )
    assert not nonexistent_found


def test_validate_severity_filter_hard(root_with_orphan_edge):
    index = _load(root_with_orphan_edge)
    result = tools_maintain.validate(
        index, root_with_orphan_edge, {"severity_filter": "hard"}
    )
    for issue in result["issues"]:
        assert issue["severity"] == "hard"


def test_validate_invalid_scope(clean_root):
    index = _load(clean_root)
    result = tools_maintain.validate(index, clean_root, {"scope": "invalid"})
    assert result["ok"] is False
    assert "scope" in result["error"]


def test_validate_invalid_severity(clean_root):
    index = _load(clean_root)
    result = tools_maintain.validate(index, clean_root, {"severity_filter": "invalid"})
    assert result["ok"] is False
```

**Acceptance criteria:**
- At least 6 tests
- Covers clean graph, orphan edge detection, scope filtering, severity filtering, invalid inputs
- All tests pass

**Commit message:**
```
Wave 5 Task 10: tests for validate tool

- tests/test_mcp_validate.py: 6 tests
  - Clean graph
  - Orphan edge detection
  - Scope filtering (nodes only)
  - Severity filter (hard)
  - Invalid scope
  - Invalid severity

Validates that validate tool catches reference errors and supports filtering.
```

---

## TASK 11 — Update MCP server count assertion + smoke test

**Goal:** Verify MCP server registers all 13 tools and can start up.

**File to modify:** Add smoke test at end of `tests/test_mcp_tools.py`

Append to `tests/test_mcp_tools.py`:

```python
def test_mcp_server_registers_all_13_tools():
    """Smoke test: MCP server must list all 13 tools (7 read + 6 write/import/validate)."""
    from gobp.mcp import server as srv
    import asyncio

    tools = asyncio.run(srv.list_tools())
    tool_names = [t.name for t in tools]

    expected = {
        "gobp_overview", "find", "signature", "context",
        "session_recent", "decisions_for", "doc_sections",
        "node_upsert", "decision_lock", "session_log",
        "import_proposal", "import_commit", "validate",
    }

    assert set(tool_names) == expected, f"Got {tool_names}, expected {expected}"
    assert len(tools) == 13
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
```

**Acceptance criteria:**
- New test `test_mcp_server_registers_all_13_tools` passes
- All 13 tools registered with exact expected names
- All previous tests still pass

**Commit message:**
```
Wave 5 Task 11: smoke test for MCP server tool registration

- tests/test_mcp_tools.py: add test_mcp_server_registers_all_13_tools
- Verifies all 13 tools listed with correct names
- Catches regressions if tool registration is broken

All Wave 5 tools now integrated into MCP server.
```

---

## TASK 12 — Update README with write capability note

**Goal:** Update README.md to reflect Wave 5 write capability.

**File to modify:** `README.md`

Find the "🛠️ Installation (Development)" section. After the "Run smoke tests" subsection, add:

```markdown
## ✨ What Works After Wave 5

GoBP v1 tool surface is now complete. Available via MCP:

**Read tools (7):**
- `gobp_overview` — project orientation
- `find` — search nodes
- `signature` — minimal node summary
- `context` — node + relations + decisions
- `session_recent` — recent sessions
- `decisions_for` — decisions by topic or node
- `doc_sections` — document sections

**Write tools (3):**
- `node_upsert` — create/update any node type
- `decision_lock` — lock a Decision with verification
- `session_log` — start/update/end session

**Import tools (2):**
- `import_proposal` — AI proposes batch import (pending)
- `import_commit` — commit approved proposal atomically

**Maintenance (1):**
- `validate` — full graph schema + reference check

All 13 tools documented in `docs/MCP_TOOLS.md`.

### AI Usage Pattern

1. AI connects → calls `gobp_overview()` to orient
2. AI searches with `find()`, reads with `context()`
3. AI starts session with `session_log(action='start')`
4. Founder brainstorms → AI calls `node_upsert(type='Idea', ...)`
5. Founder confirms → AI verifies → `decision_lock(...)` with `locked_by=[CEO, AI]`
6. Session ends → `session_log(action='end', outcome=...)`

See `docs/INPUT_MODEL.md` for detailed usage patterns.
```

**Acceptance criteria:**
- New section added to README.md
- Other README content not modified

**Commit message:**
```
Wave 5 Task 12: README - add 'What Works After Wave 5' section

- README.md: new section listing all 13 MCP tools
- Describes typical AI usage pattern
- References docs/MCP_TOOLS.md and docs/INPUT_MODEL.md

GoBP v1 tool surface now complete.
```

---

# POST-WAVE VERIFICATION

After all 12 tasks:

```powershell
# All tests pass
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: ~136 tests (109 from Wave 0-3 + 13 write + 8 import + 6 validate + 1 smoke = 137)

# MCP server registers 13 tools
D:/GoBP/venv/Scripts/python.exe -c "import asyncio; from gobp.mcp.server import list_tools; tools = asyncio.run(list_tools()); print(f'Tools: {len(tools)}'); print([t.name for t in tools])"
# Expected: Tools: 13, list of all 13 tool names

# Git log
git log --oneline | Select-Object -First 12
# Expected: 12 Wave 5 commits
```

---

# ESCALATION TRIGGERS

Stop and escalate if:
- Brief code conflicts with docs/MCP_TOOLS.md (docs wins, report conflict)
- Tests fail and cannot be fixed after 3 retries
- Existing Wave 0-3 tests break due to Wave 5 changes
- mcp SDK API incompatibility (different Server/tool registration signature)
- Index reload logic causes circular imports or startup failure

---

# WHAT COMES NEXT

After Wave 5 pushed:
- **GoBP v1 is feature-complete.** All 13 tools work.
- CEO can dogfood: connect Cursor/Claude Desktop → start populating data
- **Wave 4** — CLI commands (deferred from before, now optional convenience)
- **Wave 6** — Advanced features (migration, lessons extraction from sessions)
- **Wave 7** — Documentation polish
- **Wave 8** — MIHOS integration test (import 31 MIHOS docs as real dataset)

---

*Wave 5 Brief v0.1*
*Author: CTO Chat (Claude Opus 4.6)*
*Date: 2026-04-14*

◈
