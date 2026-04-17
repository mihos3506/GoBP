**Architecture doc model:** The long-form base spec is [`GoBP_ARCHITECTURE.md`](./GoBP_ARCHITECTURE.md). **This file** (`ARCHITECTURE.md`) holds **patches, deltas, and pasted update blocks** relative to that base—read both when auditing or implementing anything that touches project layout, MCP wiring, or scaling notes.

**Current runtime (2026):** The MCP server exposes a **single** tool, `gobp`, with the **gobp query protocol v2** (`gobp(query="overview:")`, `find:…`, `get:…`, `batch …`, …). Older sections below that mention separate tools such as `gobp_find` / `gobp_overview` describe the **same capabilities** routed through `gobp()` — see [`MCP_TOOLS.md`](./MCP_TOOLS.md) for the authoritative contract.

---

## MCP tools structure (Wave 16A04)

Runtime layout under `gobp/mcp/`:

- `parser.py` — Query parsing (`parse_query`, `_normalize_type`, coercion helpers).
- `dispatcher.py` — Routes parsed actions to tool implementations.
- `batch_parser.py` — Parses multi-line `batch` operations.
- `server.py` — MCP stdio server entrypoint.
- `tools/read.py` — Core reads: `find`, `get`/`context`, `related`, `sections`, batch helpers, etc.
- `tools/read_governance.py` — `schema_governance`, `metadata_lint`.
- `tools/read_priority.py` — `recompute_priorities`.
- `tools/read_interview.py` — `node_template`, `node_interview` and edge-declaration templates.
- `tools/write.py` — Node upsert, sessions, decision lock.
- `tools/maintain.py` — Validate, prune, stats.

---

# FOUNDATIONAL DOCS UPDATES — 2026-04-14

These are additions to existing foundational docs. CEO (or Cursor) pastes each section into the corresponding file at the indicated location.

---

# UPDATE 1 — MCP_TOOLS.md

**File:** `docs/MCP_TOOLS.md`
**Action:** Add new tool spec section
**Location:** Near the top of the tools list, before `gobp_find()`. This is the **first tool AI should call** when connecting to a new GoBP instance.

**Section to add:**

> **Status (2026):** This wave brief targets the old multi-tool MCP surface. The shipped server registers only `gobp`; use **`gobp(query="overview:")`** for the behavior below.

---

## Tool: `gobp_overview`

**Purpose:** Orientation tool for AI clients connecting to a GoBP instance for the first time. Returns project metadata, data scope, main topics, and suggested next queries. This is the only tool that requires no prior knowledge of IDs, types, or project structure.

**Priority:** Call this first when starting a session or connecting for the first time.

### Signature

```python
gobp_overview() -> dict
```

No input parameters.

### Output schema

```json
{
  "project": {
    "name": "string",
    "description": "string",
    "gobp_version": "string",
    "schema_version": "string"
  },
  "stats": {
    "total_nodes": "int",
    "total_edges": "int",
    "nodes_by_type": {
      "Node": "int",
      "Idea": "int",
      "Decision": "int",
      "Session": "int",
      "Document": "int",
      "Lesson": "int"
    },
    "edges_by_type": {
      "relates_to": "int",
      "supersedes": "int",
      "implements": "int",
      "discovered_in": "int",
      "references": "int"
    }
  },
  "main_topics": ["string"],
  "recent_decisions": [
    {
      "id": "string",
      "topic": "string",
      "what": "string (truncated to 100 chars)",
      "locked_at": "timestamp"
    }
  ],
  "recent_sessions": [
    {
      "id": "string",
      "goal": "string (truncated to 100 chars)",
      "status": "string",
      "started_at": "timestamp"
    }
  ],
  "suggested_next_queries": [
    "gobp_find('<your keyword>') to search nodes by keyword",
    "gobp_list_types() to see full type breakdown",
    "gobp_decisions_for('<topic>') to find locked decisions on a topic"
  ]
}
```

### Fields explained

- **`project.name`** — Name of the project (from first Document node named "charter" or "project" or from config)
- **`project.description`** — Short description (from Charter node or project metadata)
- **`project.gobp_version`** — GoBP package version
- **`project.schema_version`** — Schema version (1.0 for v1)
- **`stats.total_nodes`** — Total count of all nodes in `.gobp/nodes/`
- **`stats.total_edges`** — Total count of all edges in `.gobp/edges/`
- **`stats.nodes_by_type`** — Count per node type
- **`stats.edges_by_type`** — Count per edge type
- **`main_topics`** — Top 5-10 topics by frequency across Decision nodes (extracted from `topic` field)
- **`recent_decisions`** — 5 most recent Decision nodes (by `locked_at` desc), truncated
- **`recent_sessions`** — 3 most recent Session nodes (by `started_at` desc), truncated
- **`suggested_next_queries`** — Hard-coded hints for AI to know what tools exist

### Token budget

- Target: 500-1000 tokens
- Hard max: 1500 tokens
- If output exceeds max, truncate `recent_decisions` and `recent_sessions` first, then `main_topics`

### Example usage flow

```
# AI connects to GoBP for the first time in a session
AI -> gobp_overview()
AI receives: {
  project: {name: "MIHOS", description: "Heritage-Tech Proof of Presence", ...},
  stats: {total_nodes: 89, total_edges: 156, nodes_by_type: {...}, ...},
  main_topics: ["Proof of Presence", "Dissolving UI", "Circular Economy", ...],
  recent_decisions: [{id: "dec:d042", topic: "traveller_id from JWT only", ...}, ...],
  ...
  suggested_next_queries: [
    "gobp_find('...') to search",
    "gobp_decisions_for('...')",
    ...
  ]
}

# AI now knows project scope. It can ask targeted questions.
AI -> gobp_find("register flow")
AI receives: [{id: "node:user_register", ...}, ...]

# AI has IDs now. It can dive deeper.
AI -> gobp_context(id="node:user_register")
AI receives: related nodes, decisions, lessons
```

### Implementation notes (for Wave 3)

- Pulls `project.name` and `description` from a special Document node with `id=doc:charter` if exists, otherwise from GoBP package metadata
- `main_topics` computed by: collect all `topic` field values from Decision nodes, count frequency, return top 5-10
- `recent_decisions` and `recent_sessions` sorted by timestamp, limited, fields truncated to fit token budget
- `suggested_next_queries` is a static list in the tool implementation (not computed)
- All counts read from live GraphIndex at call time (no caching)

### Why this tool is critical

Without `gobp_overview()`, an AI connecting to a new GoBP instance has no way to know:
- What project this is about
- What topics are covered
- What data exists to query
- What tools to call next

This violates the **Discovery > Creation** principle. AI would either:
- Guess node IDs (fail)
- Call `gobp_find()` with random keywords (inefficient)
- Give up and ask the human (defeats the purpose)

`gobp_overview()` is the "welcome mat" that enables self-service discovery.

### Also applies to

Ensure these other tools have a **keyword-based** query option (not ID-only):

- **`gobp_find(query, type?, limit?)`** — always keyword-first (already designed this way)
- **`gobp_decisions_for(topic)`** — takes topic string, not ID
- **`gobp_session_recent(limit, since?)`** — no ID needed
- **`gobp_doc_sections(doc_name_or_id, section?)`** — accept name OR id

Only these tools require ID:
- **`gobp_context(id)`** — needs node ID for deep dive (justified, called after `find`)
- **`gobp_signature(id)`** — needs node ID (justified, called after `find`)

**Rule:** No tool should be callable only with ID. Every tool must have a path from zero knowledge (keyword, topic, type) to useful output.

---

# UPDATE 2 — ARCHITECTURE.md

**File:** `docs/ARCHITECTURE.md`
**Action:** Add new section on multi-project architecture
**Location:** After the existing section on `.gobp/` folder structure, before scaling limits section.

**Section to add:**

---

## Multi-Project Architecture

GoBP supports multiple projects on the same machine. The design separates **code (package)** from **data (project folder)** to enable clean isolation.

### Architecture principle

```
GoBP package (installed once)
        │
        │ runs as subprocess per client connection
        │
        ▼
GoBP MCP server instance (per project)
        │
        │ reads/writes
        │
        ▼
Project .gobp/ folder (per project)
```

**One install, many projects, many instances.**

### Per-project instances (Pattern A — v1 default)

Each project has its own `.gobp/` data folder. Each MCP client config spawns its own MCP server subprocess pointing at that project's data.

**Folder layout:**

```
# GoBP package installed globally
~/.pyenv/versions/3.12/lib/python3.12/site-packages/gobp/  (or similar)
  # (code, schemas, templates)

# Project A
D:\project-a\
  ├── .gobp\
  │   ├── nodes\
  │   │   └── *.md
  │   ├── edges\
  │   │   └── *.yaml
  │   ├── history\
  │   │   └── YYYY-MM-DD.jsonl
  │   └── index.sqlite  (deferred to v2)
  └── .cursor\
      └── mcp.json       # spawns instance #1, points at D:\project-a\.gobp\

# Project B
D:\project-b\
  ├── .gobp\
  │   └── ...            # independent data
  └── .cursor\
      └── mcp.json       # spawns instance #2, points at D:\project-b\.gobp\
```

**Config example (Cursor, Pattern A):**

```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["-m", "gobp.mcp.server"],
      "cwd": "D:\\project-a",
      "env": {
        "GOBP_PROJECT_ROOT": "D:\\project-a"
      }
    }
  }
}
```

The `GOBP_PROJECT_ROOT` env var tells the MCP server where to find `.gobp/` data. The package code is shared, the data is isolated.

### Properties of Pattern A

**Pros:**
- Clean separation — Project A decisions never leak to Project B
- Privacy by default — no cross-project data exposure
- Simple mental model — one folder per project, like git
- Independent failure — corruption in A doesn't affect B
- Concurrent safe — multiple clients per project OK, different projects fully independent

**Cons:**
- No cross-project memory — Lessons from A don't auto-apply to B
- Shared concepts must be duplicated (or imported) per project
- AI working across projects needs separate queries per project

**This is the v1 default.** Simpler, privacy-preserving, no scoping complexity.

### Shared workspace (Pattern B — v2 consideration, NOT in v1)

A future pattern could enable cross-project memory by using a single shared data folder with project scoping.

```
C:\Users\CEO\gobp-shared\
  ├── nodes\
  │   ├── mihos\*.md
  │   ├── project-b\*.md
  │   └── _global\*.md       # concepts/lessons applicable to all projects
  └── edges\
      └── relations.yaml
```

Each client connects with a `project_scope` filter:

```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["-m", "gobp.mcp.server"],
      "env": {
        "GOBP_PROJECT_ROOT": "C:\\Users\\CEO\\gobp-shared",
        "GOBP_PROJECT_SCOPE": "mihos"
      }
    }
  }
}
```

MCP server filters all queries by `project_scope`. Queries see current project + `_global/` folder.

**Why deferred to v2:**
- Requires scoping logic in every tool
- Privacy leakage risk if scope filter has bug
- Write concurrency across projects is tricky
- Adds complexity without clear v1 benefit
- Pattern A sufficient for CEO's current use case (1-2 projects)

### Middle ground — Shared lessons (optional v1.5)

A compromise between A and B: each project uses Pattern A for main data, but shares a read-only `_lessons/` collection.

```
~/.gobp-lessons/                      # global, read-only
  └── *.md                            # generic lessons applicable everywhere

D:\project-a\.gobp\lessons\           # local lessons specific to project A
D:\project-b\.gobp\lessons\           # local lessons specific to project B
```

On startup, each project's MCP server loads:
1. Its own `.gobp/` data (full access)
2. `~/.gobp-lessons/` as read-only Lesson nodes

Result: cross-project lessons visible, but not other project's decisions/ideas/sessions.

This is the **recommended upgrade path** after v1, if cross-project lessons become valuable.

### What a new AI client sees

When an MCP client (Cursor, Claude Desktop, etc.) connects to a project's GoBP instance:

1. **MCP handshake** — client discovers available tools (via MCP protocol)
2. **First tool call** — client calls `gobp_overview()` to understand project scope
3. **Discovery** — client calls `gobp_find()`, `gobp_decisions_for()`, etc., using keywords (no IDs needed)
4. **Deep dive** — client uses IDs from search results for `gobp_context()`, `gobp_signature()`

This flow works identically for any MCP-capable client. The client does not need to know anything about the project beforehand.

### Which pattern is running?

The MCP server reports which pattern it's in via `gobp_overview()`:

```json
{
  "project": {
    "name": "MIHOS",
    "pattern": "per_project",  // or "shared_workspace"
    ...
  }
}
```

For v1, this is always `"per_project"`.

### Resource usage

Each MCP server instance:
- One Python subprocess
- Loads all nodes + edges into memory dicts
- Memory footprint: ~50-200 MB for 1K-10K nodes
- Startup time: 300ms-1s depending on node count
- Lifetime: same as MCP client (spawned on client open, killed on client close)

Running 3-5 projects simultaneously is fine on a modern dev machine. Each is isolated.

### Client-side concurrency

Multiple MCP clients connecting to the **same project** at the same time:
- Each client spawns its own server subprocess
- Each subprocess reads same files from disk
- Each subprocess has its own in-memory index
- Writes go through mutator (Wave 5) with file locking + 1-second debounce
- Last-write-wins for concurrent edits

Cursor + Claude Desktop both open on `D:\project-a\` → 2 independent subprocess instances, both seeing same data on disk, no coordination needed between subprocesses (they don't talk to each other).

---

# PLACEMENT GUIDANCE

## For MCP_TOOLS.md

Insert the `gobp_overview` section:
- **Before** the existing `gobp_find()` section
- **As the first tool** in the tool list
- **Add a note** at the top of the file: "When an AI client connects for the first time, it should call `gobp_overview()` first to understand project scope."

## For ARCHITECTURE.md

Insert the "Multi-Project Architecture" section:
- **After** the section describing `.gobp/` folder structure (sections on nodes/, edges/, history/)
- **Before** the scaling limits section
- **Add a cross-reference** in the intro: "See 'Multi-Project Architecture' section for multi-project support."

---

# COMMIT MESSAGE

After paste + verify:

```
Update foundational docs: gobp_overview tool + multi-project section

- docs/MCP_TOOLS.md: add gobp_overview() tool spec
  - First tool AI should call when connecting
  - Returns project metadata, stats, main topics, recent activity
  - Enables discovery without knowing node IDs
  - Clarifies: no tool should be ID-only (search-by-keyword required)

- docs/ARCHITECTURE.md: add "Multi-Project Architecture" section
  - Pattern A (per-project, v1 default): each project has own .gobp/
  - Pattern B (shared workspace, v2): deferred
  - Middle ground (v1.5): shared lessons folder
  - Clarifies client concurrency and resource usage

Addresses 2 design gaps found during Wave 1 review:
1. AI didn't have a way to discover IDs on first connection
2. Multi-project isolation pattern was unclear
```

---

*Foundational docs update package*
*For: Wave 3 preparation*
*Author: CTO Chat 2026-04-14*

◈
