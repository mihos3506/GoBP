# ◈ GoBP MCP TOOLS

**File:** `D:\GoBP\docs\MCP_TOOLS.md`
**Version:** v0.1
**Status:** draft
**Depends on:** ARCHITECTURE.md, SCHEMA.md
**Audience:** Cursor implementing MCP server, AI agents calling tools

> **Protocol version:** 2.0 — Call `gobp(query="version:")` for full version info.
> **Read-only mode:** Set `GOBP_READ_ONLY=true` to prevent all write operations.

---

## gobp() - Primary Interface (v2)

As of Wave 10A, GoBP exposes a single MCP tool: `gobp()`.

**Why:** MCP clients may limit visible tools per server. `gobp()` provides
access to all capabilities through 1 tool using structured query protocol (see `overview:` / `PROTOCOL_GUIDE` in code).

### Protocol

```
gobp(query="<action>:<NodeType> <key>='<value>' ...")
```

### Quick reference

| Query | Capability |
|---|---|
| `version:` | Protocol version + changelog |
| `validate: schema-docs` | Cross-check schema vs SCHEMA.md |
| `validate: schema-tests` | Check tests reference valid types |
| `session:start actor='x' goal='y' role='observer'` | Start read-only session |
| `overview:` | Project stats (slim); small `interface_summary` + pagination hint |
| `overview: full_interface=true` | Same stats + full `interface` / PROTOCOL_GUIDE (large) |
| `get: <node_id> brief=true` | Node context with capped edges + truncated text fields |
| `find: <keyword> mode=summary` | Lightweight results (~50 tokens/node) |
| `find: <keyword> mode=brief` | Medium results (~150 tokens/node) |
| `get: <node_id> mode=brief` | Brief node detail |
| `get_batch: ids='a,b,c' mode=brief` | Fetch multiple nodes |
| `validate: metadata` | Check nodes for missing required fields |
| `validate: metadata type=Flow` | Check specific node type |
| `recompute: priorities session_id='x'` | Recompute priorities from graph |
| `recompute: priorities dry_run=true` | Preview priority changes |
| `find: <keyword>` | Search any node |
| `find: <keyword> page_size=50` | Paginated search |
| `find: <keyword> cursor='node:x' page_size=50` | Next page |
| `find:<NodeType> <keyword>` | Search by type + keyword |
| `get: <node_id>` | Full node + edges + decisions |
| `signature: <node_id>` | Minimal node summary |
| `recent: <n>` | Latest N sessions |
| `decisions: <topic>` | Locked decisions for topic |
| `sections: <doc_id>` | Document sections |
| `code: <node_id>` | Code files implementing this node |
| `code: <node_id> path='x' description='y' language='z'` | Add code reference |
| `invariants: <node_id>` | Hard constraints for node |
| `tests: <node_id>` | Linked TestCase nodes with coverage |
| `tests: <node_id> status='FAILING'` | Filter tests by status |
| `related: <node_id>` | Neighbor nodes summary (no full data) |
| `related: <node_id> direction='outgoing'` | Only outgoing neighbors |
| `create:<NodeType> name='x' session_id='y'` | Create node |
| `create:<Type> ... dry_run=true` | Preview create without writing |
| `upsert:<Type> dedupe_key='name' name='x' session_id='y'` | Create or update by key |
| `upsert:<Type> ... dry_run=true` | Preview upsert without writing |
| `update: id='x' name='y'` | Update node |
| `lock:Decision topic='x' what='y' why='z'` | Lock decision |
| `session:start actor='x' goal='y'` | Start session |
| `session:end outcome='x' handoff='y'` | End session |
| `edge: node:a --<type>--> node:b` | Create semantic edge |
| `edge: node:a --implements--> node:b reason='x'` | Edge with reason |
| `import: path/to/doc.md session_id='x'` | Import doc -> creates Document node + priority |
| `commit: imp:proposal-id` | Commit proposal |
| `validate: <scope>` | Validate graph |
| `extract: lessons` | Extract lesson candidates |
| `stats:` | All action stats (calls, latency, errors) |
| `stats: <action>` | Stats for specific action |
| `stats: reset` | Reset stat counters |

### First call

Always call `gobp(query="overview:")` first. Default response includes:
- Project state (nodes, edges, recent decisions)
- **`interface_summary`** (protocol line, format, action count, tip) — not the full catalog
- **`pagination_hint`** for `find` / `related` / `tests` cursor paging
- Suggested next queries in gobp() syntax

Use `gobp(query="overview: full_interface=true")` only when you need every action string + description (large JSON; Cursor tree view gets heavy).

For a single node, prefer `gobp(query="signature: <id>")` or `gobp(query="get: <id> brief=true")` before loading full `get:` / `context` payloads.

### Notes
- `locked_by` in lock action: comma-separated string e.g. `locked_by='CEO,Claude'`
- `session_id` required for create/update/lock - get from `session:start` first
- `_dispatch` field in every response - shows what was routed internally (for audit)

---

## 0. PURPOSE

**Primary contract (use this):** protocol **v2** — a single MCP tool `gobp` and the query strings documented in **§ gobp() - Primary Interface (v2)** at the top of this file.

**Historical appendix:** The subsections **§1 onward** document the older **v1** era when each capability had its own MCP tool name. Implementations today still map those names to the same Python helpers, but clients should call **`gobp()`** only.

MCP_TOOLS.md (full file) therefore mixes:
- **v2** — what you ship and test against (`gobp` + `query`)
- **v1 inventory** — field-level detail kept for parity with internal function names

Every legacy tool subsection is documented with:
- Name and purpose
- Input schema (required, optional, types)
- Output schema (success, error)
- Token budget (target and max size)
- Examples
- Error cases

If a capability is not described here, it is not part of the supported contract. In **v2**, it must be reachable via **`gobp(query="…")`** (see top of this file and `gobp/mcp/parser.py` `PROTOCOL_GUIDE`).

---

## 1. TOOL INVENTORY (historical v1 — discrete MCP tools)

**Current product:** use the single tool **`gobp()`** (section at top of this doc).  
The list below describes the **older v1 surface** when each capability was a separate MCP tool name. It is kept for reference.

GoBP v1 originally exposed **13** discrete tools over MCP. Grouped by purpose:

### Read tools (7)
1. `gobp_overview` — orientation tool, first call for new AI connections → **`gobp(query="overview:")`**
2. `find` — search by name/id/substring → **`gobp(query="find: …")`**
3. `signature` — minimal node summary → **`gobp(query="signature: …")`**
4. `context` — node + relations + applicable decisions → **`gobp(query="get: …")`**
5. `session_recent` — latest N sessions → **`gobp(query="recent: N")`**
6. `decisions_for` — locked decisions for a topic → **`gobp(query="decisions: …")`**
7. `doc_sections` — sections of a Document node → **`gobp(query="sections: …")`**

### Write tools (3)
8. `node_upsert` — create or update a node → **`create:` / `update:` / `upsert:`** via `gobp()`
9. `decision_lock` — lock a decision (with verification) → **`gobp(query="lock:Decision …")`**
10. `session_log` — start/end/update session → **`gobp(query="session:start …")` / `session:end …`**

### Import tools (2)
11. `import_proposal` — AI proposes batch import → **`gobp(query="import: …")`**
12. `import_commit` — commit approved proposal → **`gobp(query="commit: …")`**

### Maintenance tools (1)
13. `validate` — run schema check on graph → **`gobp(query="validate: …")`**

---

## 2. TOOL CALL CONVENTION

All tools follow MCP standard JSON-RPC over stdio.

### 2.1 Request format

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "find",
    "arguments": {
      "query": "login"
    }
  }
}
```

### 2.2 Response format (success)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"ok\": true, \"matches\": [...]}"
      }
    ]
  }
}
```

### 2.3 Response format (error)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"ok\": false, \"error\": \"Node not found: feat:unknown\"}"
      }
    ]
  }
}
```

Note: MCP SDK wraps results in `content` array with `type: text`. Tool payloads are JSON strings inside.

---

## 3. READ TOOLS

### 3.1 gobp_overview
> **v2 note:** Use `gobp(query="overview:")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** Orientation tool for AI clients connecting to a GoBP instance. Returns project metadata, stats, main topics, and suggested next queries. **First tool AI should call** when connecting - requires no prior knowledge of IDs.

**Input:** No parameters.

**Output:**
```yaml
ok: boolean
project:
  name: string
  description: string
  gobp_version: string
  schema_version: string
  pattern: string  # "per_project" | "shared_workspace"
stats:
  total_nodes: integer
  total_edges: integer
  nodes_by_type: dict[string, int]
  edges_by_type: dict[string, int]
main_topics: list[string]  # top 10 by Decision frequency
recent_decisions:
  type: list
  items:
    id: string
    topic: string
    what: string  # truncated to 100 chars
    locked_at: timestamp
recent_sessions:
  type: list
  items:
    id: string
    goal: string  # truncated to 100 chars
    status: string
    started_at: timestamp
suggested_next_queries: list[string]
```

**Token budget:** Target 500-1000 tokens, max 1500.

**Example call:**
```json
{"name": "gobp_overview", "arguments": {}}
```

**Example response:**
```json
{
  "ok": true,
  "project": {
    "name": "MIHOS",
    "description": "Heritage-Tech Proof of Presence platform",
    "gobp_version": "0.1.0",
    "schema_version": "1.0",
    "pattern": "per_project"
  },
  "stats": {
    "total_nodes": 89,
    "total_edges": 156,
    "nodes_by_type": {"Node": 45, "Idea": 23, "Decision": 12, "Session": 5, "Document": 3, "Lesson": 1},
    "edges_by_type": {"relates_to": 67, "implements": 30, "references": 25, "supersedes": 8, "discovered_in": 26}
  },
  "main_topics": ["auth:login.method", "trust:gate.policy", "ui:dissolving.timing"],
  "recent_decisions": [
    {
      "id": "dec:d042",
      "topic": "auth:login.method",
      "what": "Use Email OTP for login authentication",
      "locked_at": "2026-04-14T14:35:00"
    }
  ],
  "recent_sessions": [
    {
      "id": "session:2026-04-14_pm",
      "goal": "Write GoBP Wave 3 Brief",
      "status": "IN_PROGRESS",
      "started_at": "2026-04-14T14:00:00"
    }
  ],
  "suggested_next_queries": [
    "find(query='<keyword>') to search nodes by keyword",
    "decisions_for(topic='<topic>') to find locked decisions",
    "session_recent(n=3) to see recent session history"
  ]
}
```

**Implementation notes:**
- `project.name` and `description` pulled from Document node `doc:charter` if exists, else from first Document node, else GoBP package metadata
- `main_topics` computed from Decision nodes' `topic` field, sorted by frequency descending
- `recent_decisions` limited to 5, sorted by `locked_at` descending
- `recent_sessions` limited to 3, sorted by `started_at` descending
- `suggested_next_queries` is a static list (hints for AI to know what tools exist)
- All counts read live from GraphIndex at call time (no caching)

**Rule:** No read tool should be callable only with ID. Every tool must have a path from zero knowledge (keyword, topic, type) to useful output. Only `signature` and `context` require ID, and they are called after `find` or `overview:` returns IDs.

**Errors:**
- No errors expected under normal operation. If GraphIndex has load errors, they are reported in server logs but the overview action still returns best-effort data.

---

### 3.2 find
> **v2 note:** Use `gobp(query="find: ...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** Fuzzy search nodes by id, exact name, or substring match.

**Input:**
```yaml
query:
  type: string
  required: true
  description: Search term (id, name, or keyword)
limit:
  type: integer
  required: false
  default: 20
  description: Max results to return
```

**Output:**
```yaml
ok: boolean
matches:
  type: list
  items:
    id: string
    type: string
    name: string
    status: string
    match: string  # "exact_id" | "exact_name" | "substring"
count: integer
truncated: boolean  # true if more results exist beyond limit
```

**Token budget:** Target 200 tokens, max 500.

**Example call:**
```json
{"name": "find", "arguments": {"query": "login"}}
```

**Example response:**
```json
{
  "ok": true,
  "matches": [
    {"id": "node:feat_login", "type": "Node", "name": "Login", "status": "ACTIVE", "match": "exact_name"},
    {"id": "idea:i042", "type": "Idea", "name": "", "status": "ACTIVE", "match": "substring"},
    {"id": "dec:d015", "type": "Decision", "name": "", "status": "LOCKED", "match": "substring"}
  ],
  "count": 3,
  "truncated": false
}
```

**Errors:**
- Empty query → `{"ok": false, "error": "Query must not be empty"}`

**Match priority:**
1. Exact ID match → return immediately
2. Exact name match (case-insensitive) → collect all
3. Substring match in id or name → collect up to limit

### 3.3 signature
> **v2 note:** Use `gobp(query="signature: ...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** Get minimal spec of a single node. Fast summary, small payload.

**Input:**
```yaml
node_id:
  type: string
  required: true
  description: Exact node ID
```

**Output:**
```yaml
ok: boolean
signature:
  id: string
  type: string
  name: string
  status: string
  subtype: string (optional)
  description: string (optional)
  tags: list[string] (optional)
  topic: string (optional, Decision only)
  what: string (optional, Decision only)
  why: string (optional, Decision only)
  goal: string (optional, Session only)
```

**Note:** Output key renamed from `node` to `signature` to avoid collision with `context()` output and to keep naming consistent with tool output patterns.

**Token budget:** Target 100-300 tokens, max 500.

**Example call:**
```json
{"name": "signature", "arguments": {"node_id": "dec:d015"}}
```

**Example response:**
```json
{
  "ok": true,
  "signature": {
    "id": "dec:d015",
    "type": "Decision",
    "name": "",
    "status": "LOCKED",
    "topic": "auth:login.method",
    "what": "Use Email OTP for login authentication",
    "locked_at": "2026-04-14T14:35:00"
  }
}
```

**Errors:**
- Node not found → `{"ok": false, "error": "Node not found: dec:d999"}`

### 3.4 context
> **v2 note:** Use `gobp(query="get: ...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** Full context bundle for a node. Includes outgoing + incoming edges + applicable decisions. Use before starting a task.

**Input:**
```yaml
node_id:
  type: string
  required: true
depth:
  type: integer
  required: false
  default: 1
  description: How many hops to traverse (v1 max 2)
```

**Output:**
```yaml
ok: boolean
node: dict  # Full node
outgoing:
  type: list
  items:
    type: string  # edge type
    to: string
    to_name: string
    to_type: string
incoming:
  type: list
  items:
    type: string
    from: string
    from_name: string
    from_type: string
decisions:
  type: list
  description: Applicable decisions (via topic match or edge)
  items:
    id: string
    what: string
    why: string
    status: string
invariants:
  type: list
  description: Invariants enforced on this node (if extension schema has Invariant)
references:
  type: list
  description: Document references (via references edge)
  items:
    doc_id: string
    section: string
    lines: list
```

**Token budget:** Target 300-800 tokens, max 1500.

**Example call:**
```json
{"name": "context", "arguments": {"node_id": "node:feat_login"}}
```

**Example response:**
```json
{
  "ok": true,
  "node": {
    "id": "node:feat_login",
    "type": "Node",
    "subtype": "Feature",
    "name": "Login",
    "status": "ACTIVE",
    "description": "Email OTP authentication for returning users"
  },
  "outgoing": [
    {"type": "references", "to": "doc:DOC-07", "to_name": "Core User Flows", "to_type": "Document"},
    {"type": "implements", "to": "dec:d015", "to_name": "", "to_type": "Decision"}
  ],
  "incoming": [
    {"type": "relates_to", "from": "node:feat_register", "from_name": "Register", "from_type": "Node"}
  ],
  "decisions": [
    {"id": "dec:d015", "what": "Use Email OTP for login authentication", "why": "Face ID device-dependent...", "status": "LOCKED"}
  ],
  "invariants": [],
  "references": [
    {"doc_id": "doc:DOC-07", "section": "F2 Login", "lines": [90, 156]}
  ]
}
```

**Errors:**
- Node not found → `{"ok": false, "error": "Node not found"}`

### 3.5 session_recent
> **v2 note:** Use `gobp(query="recent: ...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** Get latest N sessions for continuity. AI calls at session start to see "what happened recently".

**Input:**
```yaml
n:
  type: integer
  required: false
  default: 3
  description: How many recent sessions (max 10)
before:
  type: timestamp
  required: false
  description: Filter to sessions before this time
actor:
  type: string
  required: false
  description: Filter by specific AI actor
```

**Output:**
```yaml
ok: boolean
sessions:
  type: list
  items:
    id: string
    actor: string
    started_at: timestamp
    ended_at: timestamp
    goal: string
    outcome: string
    status: string
    pending: list[string]
    handoff_notes: string
count: integer
```

**Token budget:** Target 500-1500 tokens, max 3000.

**Example call:**
```json
{"name": "session_recent", "arguments": {"n": 3}}
```

**Example response:**
```json
{
  "ok": true,
  "sessions": [
    {
      "id": "session:2026-04-14_pm",
      "actor": "Claude Opus 4.6 Desktop",
      "started_at": "2026-04-14T14:00:00",
      "ended_at": null,
      "goal": "Write GoBP foundational docs",
      "outcome": null,
      "status": "IN_PROGRESS",
      "pending": ["IMPORT_MODEL.md", "SCHEMA.md", "MCP_TOOLS.md"],
      "handoff_notes": "Focus on file-first architecture, 6 node types"
    },
    {
      "id": "session:2026-04-14_am",
      "actor": "Claude Opus 4.6 Desktop",
      "started_at": "2026-04-14T08:00:00",
      "ended_at": "2026-04-14T12:30:00",
      "goal": "Reconcile M7 framework with workflow v2",
      "outcome": "Scrapped M7 duplicates, shipped skill v3, shipped mihos_v2_additions bundle",
      "status": "COMPLETED",
      "pending": ["Pre-Wave 0 split decision", "Canonical bundle assembly"],
      "handoff_notes": "Skill v3 Protocol 0 is critical mitigation"
    }
  ],
  "count": 2
}
```

### 3.6 decisions_for
> **v2 note:** Use `gobp(query="decisions: ...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** Get locked decisions for a topic or node. Use when starting a task to know what's already decided.

**Input:**
```yaml
topic:
  type: string
  required: false
  description: Decision topic (e.g. "auth:login.method")
node_id:
  type: string
  required: false
  description: Get decisions related to this node
status:
  type: enum
  required: false
  default: LOCKED
  values: [LOCKED, SUPERSEDED, WITHDRAWN, ALL]
```

One of `topic` or `node_id` must be provided.

**Output:**
```yaml
ok: boolean
decisions:
  type: list
  items:
    id: string
    topic: string
    what: string
    why: string
    status: string
    locked_at: timestamp
    alternatives_considered: list
count: integer
```

**Token budget:** Target 400-1000 tokens, max 2000.

**Example call:**
```json
{"name": "decisions_for", "arguments": {"topic": "auth:login.method"}}
```

**Example response:**
```json
{
  "ok": true,
  "decisions": [
    {
      "id": "dec:d015",
      "topic": "auth:login.method",
      "what": "Use Email OTP for login authentication",
      "why": "Biometric device-dependent, SMS VN spam",
      "status": "LOCKED",
      "locked_at": "2026-04-14T14:35:00",
      "alternatives_considered": [
        {"option": "Face ID", "rejected_reason": "Device dependency"},
        {"option": "SMS OTP", "rejected_reason": "VN spam filters"}
      ]
    }
  ],
  "count": 1
}
```

### 3.7 doc_sections
> **v2 note:** Use `gobp(query="sections: ...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** List sections of a Document node without loading content.

**Input:**
```yaml
doc_id:
  type: string
  required: true
```

**Output:**
```yaml
ok: boolean
document:
  id: string
  name: string
  source_path: string
  last_verified: timestamp
sections:
  type: list
  items:
    heading: string
    lines: list[int]
    tags: list[string]
count: integer
```

**Token budget:** Target 200-500 tokens, max 1000.

**Example call:**
```json
{"name": "doc_sections", "arguments": {"doc_id": "doc:DOC-07"}}
```

**Example response:**
```json
{
  "ok": true,
  "document": {
    "id": "doc:DOC-07",
    "name": "Core User Flows",
    "source_path": "mihos-shared/docs/DOC-07_core_user_flows.md",
    "last_verified": "2026-04-14T15:00:00"
  },
  "sections": [
    {"heading": "F1 Register", "lines": [15, 89], "tags": ["auth", "onboarding"]},
    {"heading": "F2 Login", "lines": [90, 156], "tags": ["auth"]},
    {"heading": "F3 Mi Hốt", "lines": [157, 278], "tags": ["core", "heritage"]},
    {"heading": "F4 Provider Scan", "lines": [279, 380], "tags": ["core"]},
    {"heading": "F5 Imprint Capture", "lines": [381, 445], "tags": ["core"]},
    {"heading": "F6 Wallet", "lines": [446, 520], "tags": ["economy"]},
    {"heading": "F7 Memory Review", "lines": [521, 590], "tags": ["ui"]},
    {"heading": "F8 Settings", "lines": [591, 650], "tags": ["ui"]}
  ],
  "count": 8
}
```

---

## 4. WRITE TOOLS

### 4.1 node_upsert
> **v2 note:** Use `gobp(query="create:...")` or `gobp(query="update:...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** Create or update a node. Idempotent. Handles rename via supersedes pattern.

**Input:**
```yaml
type:
  type: string
  required: true
  description: Node type (Node, Idea, Decision, Session, Document, Lesson, or extension type)
id:
  type: string
  required: false
  description: Explicit ID (auto-generated if missing for Idea/Decision/Lesson)
name:
  type: string
  required: true
fields:
  type: dict
  required: true
  description: Type-specific fields per SCHEMA.md
session_id:
  type: string
  required: true
  description: Current session (for discovered_in edge)
```

**Output:**
```yaml
ok: boolean
node_id: string
created: boolean  # true if new, false if updated
warnings: list[string]
```

**Token budget:** Target 100 tokens, max 300 (small response, most data is in write).

**Example call:**
```json
{
  "name": "node_upsert",
  "arguments": {
    "type": "Idea",
    "name": "Use Email OTP for login",
    "fields": {
      "subject": "auth:login.method",
      "raw_quote": "Thôi dùng OTP email đi",
      "interpretation": "Changes auth method from Face ID to Email OTP",
      "maturity": "REFINED",
      "confidence": "high",
      "supersedes": "idea:i042"
    },
    "session_id": "session:2026-04-14_pm"
  }
}
```

**Example response:**
```json
{
  "ok": true,
  "node_id": "idea:i043",
  "created": true,
  "warnings": []
}
```

**Side effects:**
- Creates node in `.gobp/nodes/`
- Creates `discovered_in` edge to session
- If `supersedes` field present → creates supersedes edge, marks old node SUPERSEDED
- Appends history log entry
- Validates against schema before commit

**Errors:**
- Schema violation → `{"ok": false, "errors": [...]}`
- Invalid session → `{"ok": false, "error": "Session not found"}`

### 4.2 decision_lock
> **v2 note:** Use `gobp(query="lock:Decision ...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** Lock a decision with full verification. Founder has confirmed.

**Input:**
```yaml
topic:
  type: string
  required: true
what:
  type: string
  required: true
why:
  type: string
  required: true
alternatives_considered:
  type: list[dict]
  required: false
  default: []
risks:
  type: list[string]
  required: false
related_ideas:
  type: list[string]
  required: false
  description: IDs of ideas that led to this decision
session_id:
  type: string
  required: true
locked_by:
  type: list[string]
  required: true
  description: Who confirmed (e.g. ["CEO", "Claude-Opus-4.6"])
```

**Output:**
```yaml
ok: boolean
decision_id: string
warnings: list[string]
```

**Token budget:** Target 100 tokens, max 300.

**Example call:**
```json
{
  "name": "decision_lock",
  "arguments": {
    "topic": "auth:login.method",
    "what": "Use Email OTP for login authentication",
    "why": "Biometric is device-dependent. SMS unreliable in VN due to spam.",
    "alternatives_considered": [
      {"option": "Face ID", "rejected_reason": "iPhone-only, device dependency"},
      {"option": "SMS OTP", "rejected_reason": "VN spam filter issues"}
    ],
    "related_ideas": ["idea:i042", "idea:i043"],
    "session_id": "session:2026-04-14_pm",
    "locked_by": ["CEO", "Claude-Opus-4.6-Desktop"]
  }
}
```

**Example response:**
```json
{
  "ok": true,
  "decision_id": "dec:d015",
  "warnings": []
}
```

**Side effects:**
- Creates Decision node
- Status auto-set to LOCKED
- Creates `discovered_in` edge to session
- Creates `relates_to` edges to related_ideas
- Appends history log with `op: decision_lock`

**Errors:**
- Missing required fields → `{"ok": false, "error": "Missing 'what' field"}`
- Empty alternatives with hard constraint → warning (not error)

**CRITICAL:** AI MUST verify with founder before calling this. See INPUT_MODEL.md §3.

### 4.3 session_log
> **v2 note:** Use `gobp(query="session:start ...")` / `gobp(query="session:end ...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** Start, update, or end a session. AI calls at start and end of every conversation session.

**Input:**
```yaml
action:
  type: enum
  required: true
  values: [start, update, end]
session_id:
  type: string
  required: false  # auto-generated on start
actor:
  type: string
  required_if: action=start
goal:
  type: string
  required_if: action=start
outcome:
  type: string
  required_if: action=end
pending:
  type: list[string]
  required_if: action=end
nodes_touched:
  type: list[string]
  required: false
decisions_locked:
  type: list[string]
  required: false
handoff_notes:
  type: string
  required: false
```

**Output:**
```yaml
ok: boolean
session_id: string
```

**Example call (start):**
```json
{
  "name": "session_log",
  "arguments": {
    "action": "start",
    "actor": "Claude Opus 4.6 Desktop",
    "goal": "Write GoBP Wave 0 Brief"
  }
}
```

**Example response:**
```json
{
  "ok": true,
  "session_id": "session:2026-04-14_pm2"
}
```

**Example call (end):**
```json
{
  "name": "session_log",
  "arguments": {
    "action": "end",
    "session_id": "session:2026-04-14_pm2",
    "outcome": "Shipped Wave 0 Brief v0.1",
    "pending": ["CEO review", "Dispatch to Cursor"],
    "handoff_notes": "Wave 0 includes repo init + schema implementation"
  }
}
```

**Side effects:**
- Creates/updates Session node
- Start action auto-generates `session_id` with format `session:YYYY-MM-DD_slug`
- End action sets `ended_at` to current time, status to COMPLETED

**Errors:**
- Update/end on non-existent session → `{"ok": false, "error": "Session not found"}`
- End without outcome → `{"ok": false, "error": "outcome required for end action"}`

---

## 5. IMPORT TOOLS

### 5.1 import_proposal
> **v2 note:** Use `gobp(query="import: ...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** AI proposes a batch import from an existing file. Founder reviews before commit.

**Input:**
```yaml
source_path:
  type: string
  required: true
proposal_type:
  type: enum
  required: true
  values: [doc, code, spec]
ai_notes:
  type: string
  required: true
  description: AI's analysis notes
proposed_document:
  type: dict
  required: false
  description: If doc type, the Document node spec
proposed_nodes:
  type: list[dict]
  required: true
proposed_edges:
  type: list[dict]
  required: true
confidence:
  type: enum
  required: true
  values: [low, medium, high]
session_id:
  type: string
  required: true
```

**Output:**
```yaml
ok: boolean
proposal_id: string
summary: string  # Human-readable summary
node_count: integer
edge_count: integer
warnings: list[string]
```

**Token budget:** Target 400 tokens, max 1000 (response is summary only).

**Example call:**
```json
{
  "name": "import_proposal",
  "arguments": {
    "source_path": "mihos-shared/docs/DOC-07_core_user_flows.md",
    "proposal_type": "doc",
    "ai_notes": "Extracted 8 features from F1-F8 section headers",
    "proposed_document": {
      "id": "doc:DOC-07",
      "name": "Core User Flows",
      "content_hash": "sha256:abc123...",
      "sections": [...]
    },
    "proposed_nodes": [
      {"type": "Node", "subtype": "Feature", "name": "Register", "fields": {...}},
      {"type": "Node", "subtype": "Feature", "name": "Login", "fields": {...}}
    ],
    "proposed_edges": [
      {"from": "node:feat_register", "to": "doc:DOC-07", "type": "references"}
    ],
    "confidence": "high",
    "session_id": "session:2026-04-14_pm"
  }
}
```

**Example response:**
```json
{
  "ok": true,
  "proposal_id": "imp:2026-04-14_DOC-07",
  "summary": "Import DOC-07: 1 Document + 8 Feature nodes + 8 edges. Confidence: high.",
  "node_count": 9,
  "edge_count": 8,
  "warnings": []
}
```

**Side effects:**
- Creates `.gobp/proposals/imp_2026-04-14_DOC-07.pending.yaml`
- NOTHING is written to actual graph until commit

### 5.2 import_commit
> **v2 note:** Use `gobp(query="commit: ...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** Commit an approved proposal atomically.

**Input:**
```yaml
proposal_id:
  type: string
  required: true
accept:
  type: enum
  required: true
  values: [all, partial, reject]
accepted_node_ids:
  type: list[string]
  required_if: accept=partial
accepted_edge_ids:
  type: list[string]
  required_if: accept=partial
overrides:
  type: dict
  required: false
  description: Per-node field overrides from founder feedback
session_id:
  type: string
  required: true
```

**Output:**
```yaml
ok: boolean
nodes_created: integer
edges_created: integer
errors: list[dict]
```

**Token budget:** Target 200 tokens, max 500.

**Example call:**
```json
{
  "name": "import_commit",
  "arguments": {
    "proposal_id": "imp:2026-04-14_DOC-07",
    "accept": "all",
    "session_id": "session:2026-04-14_pm"
  }
}
```

**Example response:**
```json
{
  "ok": true,
  "nodes_created": 9,
  "edges_created": 8,
  "errors": []
}
```

**Side effects:**
- All proposed nodes created in `.gobp/nodes/`
- All proposed edges added to `.gobp/edges/edges.yaml`
- Proposal file moved to `.gobp/proposals/imp_2026-04-14_DOC-07.committed.yaml`
- History log entry: `op: import_commit`
- If any validation fails → ALL rolled back, nothing written

**Atomicity:** Implementation must use tempfile + rename pattern. No partial state on disk.

---

## 6. MAINTENANCE TOOLS

### 6.1 validate
> **v2 note:** Use `gobp(query="validate: ...")` via the gobp() interface.
> Direct tool calls below are for internal/test use only.

**Purpose:** Run full schema + constraint check on the entire graph. Returns issues.

**Input:**
```yaml
scope:
  type: enum
  required: false
  default: all
  values: [all, nodes, edges, references]
severity_filter:
  type: enum
  required: false
  default: all
  values: [all, hard, warning]
```

**Output:**
```yaml
ok: boolean
issues:
  type: list
  items:
    severity: string
    type: string  # "schema", "constraint", "reference", "orphan"
    node_id: string  # if applicable
    edge: dict  # if applicable
    message: string
count:
  total: integer
  hard: integer
  warning: integer
```

**Token budget:** Variable — depends on issue count. Truncate if > 50 issues.

**Example call:**
```json
{"name": "validate", "arguments": {"scope": "all"}}
```

**Example response (clean):**
```json
{
  "ok": true,
  "issues": [],
  "count": {"total": 0, "hard": 0, "warning": 0}
}
```

**Example response (issues):**
```json
{
  "ok": false,
  "issues": [
    {
      "severity": "hard",
      "type": "reference",
      "edge": {"from": "node:feat_login", "to": "doc:DOC-99"},
      "message": "Edge target doc:DOC-99 does not exist"
    },
    {
      "severity": "warning",
      "type": "schema",
      "node_id": "dec:d015",
      "message": "Decision missing related_ideas field (recommended)"
    }
  ],
  "count": {"total": 2, "hard": 1, "warning": 1}
}
```

**Usage:** AI runs validate before important operations. Humans run via CLI `gobp validate`.

---

## 7. ERROR HANDLING PATTERNS

### 7.1 Standard error format

All tools return errors in this format:

```json
{
  "ok": false,
  "error": "Short error message",
  "details": {
    "field": "fieldname",
    "got": "actual value",
    "expected": "what was expected"
  }
}
```

### 7.2 Common errors

| Error | Example | AI action |
|---|---|---|
| Node not found | `"Node not found: dec:d999"` | Retry with different ID or create first |
| Schema violation | `"Field 'maturity' invalid"` | Fix value, retry |
| Missing required field | `"Missing 'why' field"` | Add field, retry |
| Broken reference | `"Edge to doc:DOC-99 not found"` | Create target first or remove edge |
| Duplicate ID | `"Node already exists: idea:i042"` | Use node_upsert instead of create |
| Session not active | `"Session ended, cannot write"` | Start new session |
| Validation cycle | `"Supersedes cycle detected"` | Fix supersedes chain |

### 7.3 Retry logic

AI should retry on:
- Transient failures (file locked, index rebuilding)

AI should NOT retry on:
- Schema violations (fix the input instead)
- Missing references (create prerequisites first)
- Cycles (fix the graph structure)

---

## 8. TOOL DEPENDENCIES

Some tools depend on others being called first:

```
Session start required before writes:
  session_log(action=start) → required before:
    - node_upsert (needs session_id)
    - decision_lock (needs session_id)
    - import_proposal (needs session_id)
    - import_commit (needs session_id)

Proposal must exist before commit:
  import_proposal → import_commit
  
Node must exist before edge operations:
  node_upsert → edges via node_upsert(type=edge?) or relations

Context needs node existence:
  find → signature → context → decisions_for
```

AI should check dependencies. If a dependency is missing, call it first.

---

## 9. PROTOCOL 0 CHECKLIST (SKILL V3 INTEGRATION)

From skill v3: AI must run Protocol 0 at session start. With GoBP MCP tools:

```python
# Protocol 0 for GoBP-enabled session
def protocol_0(gobp, user_context):
    # 1. Start session
    session = gobp.session_log(
        action="start",
        actor=my_identity,
        goal=user_context.goal
    )
    
    # 2. Recent sessions for continuity
    recent = gobp.session_recent(n=3)
    # Read pending items from latest session
    
    # 3. Latest decisions for current topic
    if user_context.topic:
        decisions = gobp.decisions_for(topic=user_context.topic)
        # Load locked knowledge
    
    # 4. Find relevant nodes
    matches = gobp.find(query=user_context.keywords)
    
    # 5. Deep context for top match
    if matches.count > 0:
        ctx = gobp.context(node_id=matches[0].id)
    
    # Total: 4-5 MCP calls, ~5K tokens, <30 seconds
    # AI now has full state to participate in conversation
```

---

## 10. PERFORMANCE TARGETS

> **Note:** This table names **internal actions** (same helpers `gobp()` dispatches to). The MCP process exposes **one** round-trip per user query (`gobp`); latency is dominated by graph reload + the selected action.

| Tool | Target latency | Max latency | Target tokens | Max tokens |
|---|---|---|---|---|
| gobp_overview | 30ms | 100ms | 800 | 1500 |
| find | 20ms | 50ms | 200 | 500 |
| signature | 10ms | 30ms | 200 | 500 |
| context | 30ms | 100ms | 500 | 1500 |
| session_recent | 20ms | 50ms | 1000 | 3000 |
| decisions_for | 20ms | 50ms | 700 | 2000 |
| doc_sections | 10ms | 30ms | 300 | 1000 |
| node_upsert | 50ms | 200ms | 100 | 300 |
| decision_lock | 50ms | 200ms | 100 | 300 |
| session_log | 30ms | 100ms | 100 | 200 |
| import_proposal | 100ms | 500ms | 400 | 1000 |
| import_commit | 200ms | 1000ms | 200 | 500 |
| validate | 500ms | 5000ms | 500 | 3000 |

Numbers based on MIHOS M1 baseline (5 tools, 625 nodes) scaled to the **v2** action set and 1K-10K nodes.

Performance tested in Wave 8 (MIHOS integration test).

---

## 11. TOOL REGISTRATION (MCP SERVER CODE PATTERN)

**Shipped implementation:** `gobp/mcp/server.py` registers **exactly one** MCP tool named `gobp` with a required string field `query`. All actions route through `parse_query` → `dispatch`.

```python
# Accurate shape (simplified) — see repository for full inputSchema text

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="gobp",
            description="GoBP knowledge graph (protocol v2) — pass query per PROTOCOL_GUIDE.",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "gobp":
        return [error_json(f"Unknown tool: {name}. Use gobp().")]
    query = arguments.get("query", "overview:")
    result = await dispatch(query, index, project_root)
    # ... wrap as MCP TextContent JSON

# Historical v1 (pre–single-tool) dispatch map — not used by the shipped server:
# tools_read.gobp_overview, find, context, … — now reached only via dispatch(query, …).
```

Older MIHOS M1 servers used a per-tool name map; GoBP **v2** replaces that with `parse_query` + `dispatch`.

---

## 12. ENFORCEMENT RULES

### 12.1 Output size enforcement

Every read tool must check output size before returning:

```python
def enforce_size(result, target_tokens, max_tokens):
    estimated = len(json.dumps(result)) // 4  # rough chars-to-tokens
    if estimated > max_tokens:
        # Truncate list results
        if "matches" in result:
            keep = int(len(result["matches"]) * target_tokens / estimated)
            result["matches"] = result["matches"][:keep]
            result["truncated"] = True
            result["note"] = f"Truncated from {estimated} to {target_tokens} tokens"
    return result
```

### 12.2 Write verification

Decision locks MUST have been verified in conversation. GoBP cannot enforce this directly, but:

- `decision_lock` requires `locked_by` with at least 2 entities (CEO + AI witness)
- AI system prompts instruct verification before call
- History log tracks verification via `handoff_notes` or `ai_notes` fields

### 12.3 Session isolation

Writes must include `session_id`. If session doesn't exist or is COMPLETED, writes fail:

```python
def check_session(session_id):
    session = index.get(session_id)
    if not session:
        raise Error("Session not found")
    if session["status"] == "COMPLETED":
        raise Error("Session already ended, start new one")
```

---

## 13. VERSION STABILITY

MCP_TOOLS.md defines the **contract** for GoBP capabilities. The **wire protocol** for clients is **v2** (`gobp` + `query`). Legacy §1–§9 tool names describe the same behavior for humans and for code that maps actions to Python helpers. Changes after ship:

**Allowed without version bump:**
- Bug fixes
- New optional fields
- New enum values (additive)
- Performance improvements

**Require v1.x → v1.y bump:**
- New tools
- New required fields (with defaults)

**Require v1 → v2 bump:**
- Removing tools
- Removing required fields
- Breaking enum changes
- Changing input/output shape

AI clients should check server version via MCP initialization handshake.

---

## 14. REFERENCES

- ARCHITECTURE.md — 6 node types + 5 edge types that tools operate on
- SCHEMA.md — validation rules tools enforce
- INPUT_MODEL.md — how AI uses write tools from conversation
- IMPORT_MODEL.md — how import tools orchestrate batch imports
- mcp_server.py M1 from MIHOS — reference implementation pattern

---

*Written: 2026-04-14*
*Status: v0.1 draft*
*Next: README.md (final foundational doc)*

◈
