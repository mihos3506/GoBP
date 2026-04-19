# ◈ GoBP ARCHITECTURE

**File:** `D:\GoBP\docs\GoBP_ARCHITECTURE.md`
**Version:** v0.1
**Status:** draft, awaiting CEO approval
**Depends on:** VISION.md (must read first)
**Audience:** AI agents implementing GoBP + AI agents extending GoBP per project

---

## 0. HOW TO READ THIS DOC

ARCHITECTURE describes **how GoBP is built**. VISION describes **why**.

- If you are Cursor implementing GoBP code → read this fully
- If you are Claude Desktop orchestrating GoBP work → read sections 1, 2, 3, 8
- If you are an AI extending GoBP for a project → read sections 2, 4, 7

Every decision in this doc traces back to a principle in VISION. If you find a contradiction, VISION wins.

---

## 1. SYSTEM OVERVIEW

GoBP is a layered system with clear separation:

```
┌─────────────────────────────────────────────────────────┐
│  AI Agents (Cursor, Claude CLI, Claude Desktop, Qodo)   │
│  Speak: MCP protocol (JSON-RPC over stdio)              │
└────────────────────┬────────────────────────────────────┘
                     │ MCP tool calls
                     ▼
┌─────────────────────────────────────────────────────────┐
│  MCP Server (gobp/mcp/server.py)                        │
│  - Tool registration                                    │
│  - Input validation                                     │
│  - Dispatch to core                                     │
│  - Output serialization                                 │
└────────────────────┬────────────────────────────────────┘
                     │ Python function calls
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Core Engine (gobp/core/)                               │
│  - graph.py   : GraphIndex (in-memory; optional DB backing) │
│  - loader.py  : YAML/MD file loader                     │
│  - validator.py / validator_v2.py : Schema enforcement (v2 prod) │
│  - mutator.py : Write operations with history           │
└────────────────────┬────────────────────────────────────┘
                     │ File I/O
                     ▼
┌─────────────────────────────────────────────────────────┐
│  File Storage (project's .gobp/ folder)                 │
│  - nodes/    : node markdown files with YAML front-matter│
│  - edges/    : edge YAML files                            │
│  - history/  : append-only log                            │
│  - archive/  : pruned nodes (after prune)               │
└─────────────────────────────────────────────────────────┘
```

**Key architectural decisions:**
- Files are source of truth (P3 in VISION)
- Core is file-based; **PostgreSQL** is an optional index when `GOBP_DB_URL` is set (see `gobp/core/graph.py` / loader paths)
- MCP server is a thin adapter over core
- AI never touches files directly — always via MCP
- Humans can inspect files but don't edit them normally

---

## 2. NODE TYPES (packaged core schema)

Every piece of knowledge in GoBP is a node. The packaged file `gobp/schema/core_nodes.yaml` defines **93** core node types (schema **v2**)—covering product graph, security, persistence, frontend, code, constraints, errors, tests, meta, lessons, etc. **Authoritative field lists:** `docs/SCHEMA.md` and the YAML packs. Project-specific extensions may add types via additional schema files where supported.

The subsections below (2.1 onward) are a **narrative introduction** to an older subset; they do not enumerate every type. When in doubt, read `SCHEMA.md` and `core_nodes.yaml`.

### 2.1 Node (generic container)

The most flexible type. Used for anything that doesn't fit the specialized types.

**Purpose:** Represent entities, features, tools, concepts, engines, components — anything that is a "thing" in the project.

**Required fields:**
- `id` — stable unique identifier (e.g. `node:feat_login`, `node:tool_mcp_server`)
- `type` — schema type (e.g. `Feature`, `Tool`, `Entity`, `Component`)
- `name` — human-readable label (e.g. "Login", "MCP Server")
- `status` — lifecycle state (`DRAFT`, `ACTIVE`, `DEPRECATED`, `ARCHIVED`)
- `created` — ISO timestamp
- `updated` — ISO timestamp (last mutation)

**Optional fields:**
- `description` — short prose
- `tags` — list of strings for grouping
- `subtype` — project-specific categorization
- Any custom field per schema extension

**Example file** (`nodes/node_feat_login.md`):
```yaml
---
id: node:feat_login
type: Feature
subtype: auth
name: Login
status: ACTIVE
created: 2026-04-14T10:00:00
updated: 2026-04-14T14:30:00
description: Email OTP authentication for returning users
tags: [auth, phase1]
---

## Context
Returning user enters email, receives OTP code, enters code, session starts.

## Notes
- Phase 1 scope (Hội An MVP)
- Guest users can browse without login
- Soft-delete pattern: no hard account deletion
```

**Key rules:**
- `id` never changes after creation — even if `name` changes (BKP → GoBP rename case)
- `type` + `subtype` help AI filter queries
- Prose content in markdown body is for human debugging, AI reads front-matter primarily

### 2.2 Idea

Unstructured brainstorm, captured raw from conversation. Not yet decided, not yet verified.

**Purpose:** Preserve founder's original words and AI's interpretation separately, to prevent drift.

**Required fields:**
- `id` — e.g. `idea:i001`
- `type` — always `Idea`
- `raw_quote` — verbatim text from founder (exact words, do not paraphrase)
- `interpretation` — AI's understanding (clearly separate from raw_quote)
- `subject` — what this idea is about (e.g. `auth:login.method`, `ui:onboarding`)
- `maturity` — lifecycle: `RAW`, `REFINED`, `DISCUSSED`, `LOCKED`, `DEPRECATED`
- `confidence` — AI's confidence in interpretation: `low`, `medium`, `high`
- `session_id` — which session captured this
- `created` — timestamp

**Optional fields:**
- `supersedes` — previous idea this replaces (link)
- `context_notes` — surrounding conversation context
- `ceo_verified` — has founder explicitly confirmed interpretation?

**Example file** (`nodes/idea_i042.md`):
```yaml
---
id: idea:i042
type: Idea
subject: auth:login.method
raw_quote: "Thôi dùng OTP email đi"
interpretation: Founder changes auth method from Face ID to Email OTP
maturity: REFINED
confidence: high
session_id: session:2026-04-14_afternoon
created: 2026-04-14T14:30:00
supersedes: idea:i041
ceo_verified: true
---

## Context
Previously idea:i041 proposed Face ID. CTO Chat noted Face ID is device-dependent
and may not work on older phones. Founder responded with this change.

## Related
- idea:i041 (Face ID, superseded)
- Considered but not mentioned: SMS OTP (rejected by CTO due to VN spam)
```

**Key rules:**
- `raw_quote` is frozen — never edited. If founder says something new, create new Idea that `supersedes` this one.
- `interpretation` can be corrected if AI got it wrong, but with history log entry.
- Ideas flow upward: `RAW` → `REFINED` → `DISCUSSED` → `LOCKED` → matured into Decision.

### 2.3 Decision

Locked knowledge. Founder has confirmed. AI treats as authoritative.

**Purpose:** Capture what has been decided, with rationale and alternatives, so future AI sessions don't re-litigate.

**Required fields:**
- `id` — e.g. `dec:d001`
- `type` — always `Decision`
- `topic` — what the decision is about (e.g. `auth:login.method`)
- `what` — the decision in 1-2 sentences (e.g. "Use Email OTP")
- `why` — rationale (e.g. "Face ID device-dependent, SMS spam in VN")
- `status` — `LOCKED`, `SUPERSEDED`, `WITHDRAWN`
- `locked_at` — timestamp when founder confirmed
- `locked_by` — who confirmed (usually "CEO" + AI witness)

**Optional fields:**
- `alternatives_considered` — list of rejected options with reasons
- `risks` — what could go wrong
- `blocks` — what this decision enables or blocks
- `supersedes` — previous decision this replaces
- `related_ideas` — ideas that led to this decision

**Example file** (`nodes/dec_d015.md`):
```yaml
---
id: dec:d015
type: Decision
topic: auth:login.method
what: Use Email OTP for login authentication
why: Face ID is device-dependent and fails on older phones. SMS is unreliable in VN due to spam filters.
status: LOCKED
locked_at: 2026-04-14T14:35:00
locked_by: [CEO, CTO-Chat-Claude-Opus-4.6]
alternatives_considered:
  - Face ID (rejected: device dependency)
  - SMS OTP (rejected: VN spam filter issues)
  - Magic link (rejected: email deliverability)
  - Password (rejected: onboarding friction)
risks:
  - Email provider outage blocks all logins
  - OTP email delays due to ESP issues
blocks:
  - Phase 1 feature register flow
related_ideas: [idea:i041, idea:i042]
---

## Context
Decided during conversation on 2026-04-14 afternoon session. Founder initially 
proposed Face ID, CTO Chat raised device dependency concern, founder pivoted to 
Email OTP after considering SMS spam issue in VN market.

## Implementation notes
- Rate limit: 5 attempts per minute per IP
- OTP valid for 10 minutes
- 6-digit numeric code
```

**Key rules:**
- Decisions are LOCKED until explicitly SUPERSEDED or WITHDRAWN
- AI must query decisions at task start to avoid re-asking founder
- Superseding a decision requires new Decision node + `supersedes` edge, old one marked SUPERSEDED
- Every Decision should trace back to Idea(s) when possible — preserve origin

### 2.4 Session

A record of one AI working session. Enables cross-session continuity.

**Purpose:** Allow new AI sessions to load "where we left off" without re-explaining.

**Required fields:**
- `id` — e.g. `session:2026-04-14_afternoon`
- `type` — always `Session`
- `actor` — which AI (e.g. "Claude Opus 4.6 via Desktop", "Cursor 2.6.21", "Qodo")
- `started_at` — ISO timestamp
- `ended_at` — ISO timestamp (null if in progress)
- `goal` — what this session aimed to accomplish
- `outcome` — what actually happened
- `status` — `IN_PROGRESS`, `COMPLETED`, `INTERRUPTED`, `FAILED`

**Optional fields:**
- `nodes_touched` — list of node IDs created/modified during session
- `decisions_locked` — list of Decision IDs locked during session
- `pending` — what was not finished (for next session to pick up)
- `tokens_used` — rough estimate
- `human_present` — was founder actively engaged?
- `handoff_notes` — specific context for next session

**Example file** (`nodes/session_2026-04-14_pm.md`):
```yaml
---
id: session:2026-04-14_pm
type: Session
actor: Claude Opus 4.6 Desktop
started_at: 2026-04-14T14:00:00
ended_at: 2026-04-14T18:30:00
goal: Write GoBP foundational docs (VISION, ARCHITECTURE, INPUT_MODEL)
outcome: Shipped VISION.md v0.1 and ARCHITECTURE.md v0.1. INPUT_MODEL pending.
status: IN_PROGRESS
nodes_touched: []
decisions_locked:
  - dec:d020 (GoBP rename from BKP)
  - dec:d021 (License deferred)
  - dec:d022 (core node types in schema v2 — see SCHEMA.md; 21 types in packaged `core_nodes.yaml`)
pending:
  - INPUT_MODEL.md
  - IMPORT_MODEL.md
  - Wave 0 Brief for Cursor
tokens_used: ~200000
human_present: true
handoff_notes: |
  CEO chose "build from pain, don't overthink product". 
  Document type stays (CEO requirement for import mechanism).
  Next step: INPUT_MODEL.md explaining AI writes, human speaks.
---
```

**Key rules:**
- Sessions auto-created by AI at start, closed at end
- Each AI session is independent — multiple AI can have concurrent sessions
- `pending` is critical — new AI reads this to know what to continue
- Session ID format: `session:YYYY-MM-DD_<slug>` for sortability

### 2.5 Document

A pointer to an external document file with metadata. Does NOT duplicate content.

**Purpose:** Let AI know what documents exist in the project without loading them fully. Enable "follow reference to specific section" pattern.

**Required fields:**
- `id` — e.g. `doc:DOC-07`
- `type` — always `Document`
- `name` — document title
- `source_path` — relative path to file (e.g. `mihos-shared/docs/DOC-07_core_user_flows.md`)
- `content_hash` — SHA-256 of file content (detect changes)
- `registered_at` — when GoBP first learned about this doc
- `last_verified` — last time GoBP confirmed file still exists

**Optional fields:**
- `sections` — list of section headings with line ranges
- `tags` — topic tags
- `owned_by` — which project role owns this doc
- `phase` — project phase this doc belongs to

**Example file** (`nodes/doc_DOC-07.md`):
```yaml
---
id: doc:DOC-07
type: Document
name: Core User Flows
source_path: mihos-shared/docs/DOC-07_core_user_flows.md
content_hash: sha256:abc123def456...
registered_at: 2026-04-14T10:00:00
last_verified: 2026-04-14T15:00:00
sections:
  - heading: "F1 Register"
    lines: [15, 89]
    tags: [auth, onboarding]
  - heading: "F2 Login"
    lines: [90, 156]
    tags: [auth]
  - heading: "F3 Mi Hốt"
    lines: [157, 278]
    tags: [core, heritage]
tags: [core_flows, phase1]
phase: 1
---

## Purpose
Authoritative specification for user-facing flows in MIHOS.
CTO Chat and Cursor should reference specific sections, not load full doc.

## Related nodes
Referenced by: feat:register, feat:login, feat:mi_hot, flow:F1, flow:F2, flow:F3
```

**Key rules:**
- GoBP never copies document content. Always just a pointer.
- If source file changes (hash mismatch), GoBP flags the Document node as `stale` — AI should re-verify references
- Sections list enables precise "read DOC-07 §F2 lines 90-156" queries
- AI uses Document as map, reads actual file only when specific detail needed

### 2.6 Lesson

Something learned from experience that should be preserved across sessions.

**Purpose:** Accumulate knowledge about failure modes, patterns, gotchas, so future AI sessions don't repeat same mistakes.

**Required fields:**
- `id` — e.g. `lesson:ll001`
- `type` — always `Lesson`
- `title` — short headline (e.g. "Query before create — always")
- `trigger` — what situation this lesson applies to
- `what_happened` — the mistake or pattern observed
- `why_it_matters` — impact
- `mitigation` — how to avoid in future
- `severity` — `low`, `medium`, `high`, `critical`
- `captured_in_session` — which session learned this

**Optional fields:**
- `related_nodes` — nodes where this lesson applies
- `related_ideas` — ideas that led to lesson
- `verified_count` — how many times this lesson has been confirmed
- `last_applied` — when was this lesson last relevant

**Example file** (`nodes/lesson_ll023.md`):
```yaml
---
id: lesson:ll023
type: Lesson
title: Query project_knowledge before proposing new frameworks
trigger: User calls me CTO of a project I've worked on before
what_happened: |
  Session 2026-04-14 morning: I reflexively shipped M7 framework (74 files) 
  without querying project_knowledge first. Discovered mid-session that 
  workflow v2 already existed covering ~80% of what I shipped. Had to scrap
  most of it. Wasted ~300K tokens.
why_it_matters: |
  Reflexive creation without discovery violates the core Discovery > Creation
  principle and wastes enormous token budget. Also damages CEO trust when 
  they see the same mistake they corrected before.
mitigation: |
  Skill v3 Protocol 0 now mandates 3 queries at session start:
  1. governance search
  2. existing tools search
  3. latest session journal search
  Before proposing ANY framework, check what exists.
severity: critical
captured_in_session: session:2026-04-14_morning
verified_count: 2  # Same lesson appeared in 2026-04-12 session too
last_applied: 2026-04-14T18:00:00
---

## Context
This is the MIHOS failure that led to creating skill v3 and then GoBP itself.
GoBP exists because journal-based lessons weren't preventing repeats.
Structured lessons in a queryable store are the next iteration.

## Anti-pattern to recognize
- CEO says "you are the CTO"
- AI thinks "I must ship framework"
- AI skips project_knowledge_search
- Framework is a duplicate of existing work
```

**Key rules:**
- Lessons are accumulated over time, not purged
- High-severity lessons should be queried at session start as part of Protocol 0
- `verified_count` increments when same lesson observed again — high count = systemic issue
- Lessons can link to each other (e.g. "this lesson is a specific case of another lesson")

---

## 3. EDGE TYPES (packaged core schema)

Edges connect nodes. `gobp/schema/core_edges.yaml` defines **14** edge kinds (e.g. `relates_to`, `implements`, `depends_on`, `tested_by`, `covers`, `of_kind`, `enforces`, …). **Full list:** `docs/SCHEMA.md` section 3.

The subsections below (3.1–3.5) describe an illustrative subset only.

### 3.1 relates_to

Generic "these two things are connected somehow". Use when more specific edge doesn't apply.

**Usage:**
- `feat:login` relates_to `feat:register`
- `idea:i042` relates_to `idea:i043` (both in same brainstorm session)
- `dec:d015` relates_to `feat:login`

**Rules:**
- Undirected (conceptually bidirectional, stored as single edge)
- Weakest semantic — prefer specific edge types when possible
- Many-to-many allowed

### 3.2 supersedes

New version replaces old version. Preserves history.

**Usage:**
- `idea:i042` supersedes `idea:i041` (OTP idea replaces Face ID idea)
- `dec:d020` supersedes `dec:d012` (name GoBP replaces name BKP)
- `node:tool_gobp` supersedes `node:tool_bkp` (tool renamed)

**Rules:**
- Directed: new → old
- Creates a chain (can supersede something that already supersedes something)
- Old node is NOT deleted — marked `status: SUPERSEDED`
- AI queries default to current (non-superseded) unless `--history` flag
- Allows rename, refactor, evolution without losing trace

### 3.3 implements

Idea or spec has been turned into reality.

**Usage:**
- `dec:d015` implements_in `node:feat_login` (decision shows up in feature)
- `node:feat_login` implements `flow:F2` (feature implements user flow)
- `node:tool_jwt_signer` implements `dec:d018` (tool realizes decision)

**Rules:**
- Directed: concrete → abstract (implementation → spec)
- Creates traceability: every built thing traces to its spec
- When querying "what implements X?", returns all nodes that realize X

### 3.4 discovered_in

Links a node to the session where it was created or first identified.

**Usage:**
- `idea:i042` discovered_in `session:2026-04-14_pm`
- `lesson:ll023` discovered_in `session:2026-04-14_morning`
- `dec:d015` discovered_in `session:2026-04-14_pm`

**Rules:**
- Directed: node → session
- Every node should have at least one discovered_in edge
- Enables "what did we learn/decide in session X?" queries
- Creates temporal layer on top of semantic graph

### 3.5 references

A node points to a document section for detail.

**Usage:**
- `feat:register` references `doc:DOC-07#F1`
- `dec:d015` references `doc:DOC-02#auth_invariants`
- `node:tool_mcp_server` references `doc:MCP_TOOLS.md#find`

**Rules:**
- Directed: node → document section
- Used to avoid duplicating document content in GoBP
- AI follows reference only when specific detail needed
- Reference format: `doc:<DOC_ID>#<section_slug>` or `doc:<DOC_ID>:<line_range>`

---

## 4. PROJECT FILE STRUCTURE

Inside a GoBP-enabled project, the knowledge lives in a `.gobp/` folder at project root:

```
<project-root>/
├── .gobp/                          ← GoBP data for this project
│   ├── config.yaml                 ← project config, schema version, multi-user placeholders
│   ├── index.db                    ← derived SQLite index (gitignored, rebuildable)
│   │
│   ├── nodes/                      ← all nodes, one markdown file per node
│   │   ├── node_feat_login.md
│   │   ├── idea_i001.md
│   │   ├── dec_d001.md
│   │   ├── session_2026-04-14_pm.md
│   │   ├── doc_DOC-07.md
│   │   ├── lesson_ll001.md
│   │   ├── testkind_unit.md        ← seeded on init (16 TestKind)
│   │   ├── concept_test_taxonomy.md ← seeded on init (1 Concept)
│   │   └── tc_login_unit_001.md
│   │
│   ├── edges/                      ← edges, one YAML file per edge or group
│   │   └── *.yaml
│   │
│   ├── history/                    ← append-only event log
│   │   ├── 2026-04-12.jsonl
│   │   └── 2026-04-14.jsonl
│   │
│   └── archive/                    ← pruned nodes (created by gobp prune)
│       └── YYYY-MM-DD/
│
├── gobp/                           ← schema files (copied from package on init)
│   └── schema/
│       ├── core_nodes.yaml         ← 21 core node type definitions (schema v2)
│       └── core_edges.yaml         ← 14 core edge type definitions (schema v2)
│
├── src/                            ← project's actual code (not GoBP)
├── docs/                           ← project's actual docs (referenced by GoBP)
└── ...
```

**Note:** `gobp/schema/` is at project root (not inside `.gobp/`) because
`GraphIndex.load_from_disk()` expects schemas at `{project_root}/gobp/schema/`.
This is by design — schema files are part of the GoBP package contract,
not project-specific data.

**Key decisions:**
- `.gobp/` is at project root, like `.git/`
- One markdown file per node for git-friendliness and easy human inspection
- Edges live as YAML files under `.gobp/edges/` (typically one file per edge or small groups), not a mandatory single `edges.yaml`
- History as JSONL (one event per line, append-only)
- `archive/` holds pruned node files after `gobp prune`; optional until prune runs
- Core schema v2 defines **21 node types** and **14 edge kinds** (see `gobp/schema/*.yaml` and `docs/SCHEMA.md`)
- `config.yaml` holds `schema_version`, `gobp_version`, and multi-user placeholders — there is no separate `.gobp-version` file
- **Persistent SQLite index** (`index.db`) is derived from node/edge files, gitignored, rebuildable via `gobp validate --reindex`
- `gobp/schema/` at **project root** is required for `GraphIndex.load_from_disk()` (schemas copied on `gobp init`)
- `.gobp/` should be committed to git (it IS the project memory)

**Naming convention for node files:**
- `<type_prefix>_<id_without_prefix>.md`
- e.g. `node:feat_login` → `node_feat_login.md`
- e.g. `dec:d015` → `dec_d015.md`
- e.g. `session:2026-04-14_pm` → `session_2026-04-14_pm.md`

---

## 5. MCP SERVER DESIGN

### 5.1 Server lifecycle

MCP server is a long-running Python process started by AI agents via their config.

**Startup sequence:**
1. Read `.gobp/config.yaml` (project root detection)
2. Load all node files from `.gobp/nodes/` into memory
3. Load all edge YAML files from `.gobp/edges/` (each file is a YAML list of edges)
4. Build in-memory indexes:
   - `nodes_by_id`
   - `nodes_by_type`
   - `outgoing[node_id]` → list of edges
   - `incoming[node_id]` → list of edges
5. Verify schema consistency
6. Start JSON-RPC loop over stdio
7. Log: `[gobp] Loaded N nodes, M edges. Ready.`

**Cold start target:** < 500ms for 1K nodes.

**File change detection:**
- Option A (v1): Full reload on tool call if file mtime changed
- Option B (v2): File watcher for live updates
- v1 chooses simplicity: reload on demand

### 5.2 Tool dispatch pattern

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "find":
            result = index.find(arguments.get("query", ""))
        elif name == "context":
            result = index.context(arguments.get("node_id", ""))
        # ... dispatch to core methods
        else:
            result = {"error": f"Unknown tool: {name}"}
    except Exception as e:
        result = {"error": str(e), "tool": name}
    
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
```

Pattern inherited from MIHOS M1 `mcp_server.py`. Keep simple, explicit dispatch.

### 5.3 Tool output size enforcement

Every read tool has a token budget:

| Tool | Target size | Hard max |
|---|---|---|
| `find` | 200 tokens | 500 |
| `signature` | 100-300 tokens | 500 |
| `context` | 300-800 tokens | 1500 |
| `decisions_for` | 400-1000 tokens | 2000 |
| `session_recent` | 500-1500 tokens | 3000 |
| `doc_sections` | 200-500 tokens | 1000 |

Implementation: before returning, estimate token count (rough char_count/4). If over target, truncate with `"...<N more results>"` hint.

### 5.4 Tools inventory (12 for v1)

**Read tools (6):**

1. `find(query)` — fuzzy search by id, name, substring
2. `signature(node_id)` — quick summary of 1 node
3. `context(node_id)` — node + outgoing + incoming + decisions applying
4. `session_recent(n=3)` — latest N sessions for continuity
5. `decisions_for(node_id_or_topic)` — locked decisions for a topic
6. `doc_sections(doc_id)` — list sections of a Document node

**Write tools (3):**

7. `node_upsert(type, name, ...)` — create or update a node (handles rename via supersedes)
8. `decision_lock(topic, what, why, alternatives, related_ideas)` — lock a decision
9. `session_log(session_id, what_happened, pending)` — end-of-session log

**Import tools (2):**

10. `import_proposal(source_path, proposed_nodes, proposed_edges)` — AI proposes batch import from existing doc
11. `import_commit(proposal_id)` — CEO approved, commit the batch

**Maintenance tool (1):**

12. `validate()` — run schema check on entire graph, return issues list

These 12 are the v1 API surface. Additions in v2 require CEO approval per AUTHORITY_MATRIX pattern.

---

## 6. CORE ENGINE DESIGN

### 6.1 Module layout

```
gobp/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── graph.py          ← GraphIndex class
│   ├── loader.py         ← Load nodes + edges from files
│   ├── validator.py      ← Schema validation
│   ├── mutator.py        ← Write operations
│   └── history.py        ← Append-only log
├── schema/
│   ├── __init__.py
│   ├── core_nodes.yaml   ← 21 core node type definitions (schema v2)
│   ├── core_edges.yaml   ← 14 core edge type definitions (schema v2)
│   └── extensions.py     ← Load project-specific extensions
├── mcp/
│   ├── __init__.py
│   ├── server.py         ← MCP stdio entry
│   ├── dispatcher.py     ← routes `gobp(query=…)` actions
│   ├── batch_parser.py   ← batch op lines
│   └── tools/
│       ├── __init__.py
│       ├── read.py       ← find, get/context, overview, batch helpers, …
│       ├── write.py      ← upsert, sessions, decisions, batch executor
│       ├── import_.py    ← import proposal/commit
│       ├── maintain.py   ← validate, stats, …
│       ├── read_interview.py, read_priority.py, read_governance.py, advanced.py
└── cli/
    ├── __init__.py
    ├── __main__.py       ← `gobp` command entry
    └── commands.py       ← init, validate, rebuild commands
```

**Note:** Module count grows with waves; layout above is representative.

### 6.2 GraphIndex class (core data structure)

```python
class GraphIndex:
    """In-memory index over GoBP project knowledge."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.gobp_dir = project_root / ".gobp"
        
        # Indexes
        self.nodes_by_id: dict[str, dict] = {}
        self.nodes_by_type: dict[str, list[dict]] = defaultdict(list)
        self.outgoing: dict[str, list[dict]] = defaultdict(list)
        self.incoming: dict[str, list[dict]] = defaultdict(list)
        
        # Load
        self._load_nodes()
        self._load_edges()
        self._build_indexes()
    
    def find(self, query: str) -> list[dict]:
        """Fuzzy search, returns minimal match info."""
        ...
    
    def context(self, node_id: str) -> dict:
        """Node + edges + applicable decisions."""
        ...
    
    def upsert_node(self, node_data: dict) -> str:
        """Create or update. Returns node_id."""
        ...
    
    # ... etc
```

Class design matches MIHOS M1 pattern (proven to work with MCP SDK).

### 6.3 History log

Every mutation appends to `.gobp/history/YYYY-MM-DD.jsonl`:

```jsonl
{"ts":"2026-04-14T14:30:00","op":"node_create","actor":"Claude-Desktop","id":"idea:i042","payload":{...}}
{"ts":"2026-04-14T14:35:00","op":"decision_lock","actor":"Claude-Desktop","id":"dec:d015","payload":{...}}
{"ts":"2026-04-14T15:00:00","op":"edge_add","actor":"Cursor","id":"edge:e001","payload":{"from":"feat:login","to":"dec:d015","type":"implements"}}
```

One event per line, append-only, never modified. Enables:
- Audit trail
- Time-travel queries
- Recovery from corruption
- Debugging AI misbehavior

---

## 7. SCHEMA EXTENSIONS (per-project)

Core schema defines 6 node types. Projects add custom types via `schema/extensions.yaml`:

```yaml
# Example: MIHOS schema extension
extends: core-v1

node_types:
  Feature:
    parent: Node
    required_fields: [subtype, phase]
    constraints:
      - phase in [1, 2, 3, 4]
      - subtype matches "^(auth|ui|core|economy)$"
  
  Engine:
    parent: Node
    required_fields: [technology, layer]
    constraints:
      - layer in [1, 2, 3, 4, 5, 6]
  
  Invariant:
    parent: Node
    required_fields: [severity, rule_text]
    constraints:
      - severity in [hard, soft, warning]

edge_types:
  enforces:
    from: Invariant
    to: [Feature, Engine]
    cardinality: many_to_many
```

**Rules:**
- Extensions can only add types, not remove or modify core types
- Constraint violations block writes
- GoBP core ignores unknown custom fields (forward-compatible)

---

## 8. VALIDATION RULES

Core GoBP enforces:

### 8.1 Structural rules
- Every node has unique `id`
- Every node has `type`, `name`, `status`, `created`, `updated`
- Every edge has valid `from` and `to` node IDs
- `supersedes` chain has no cycles
- No orphan edges (both endpoints must exist)

### 8.2 Subgraph rules
- Ideas subgraph: cycles allowed (brainstorm can contradict itself)
- Decisions subgraph: no cycles in `supersedes` chain
- Sessions subgraph: append-only, no deletion

### 8.3 Referential integrity
- `Document` node `source_path` must resolve to actual file
- `content_hash` must match file content (or flag `stale`)
- `references` edge must point to valid Document section

### 8.4 Soft rules (warnings, not blocks)
- Node without `discovered_in` edge to any session
- Decision without `related_ideas` (every decision should trace back)
- Idea with `maturity: LOCKED` should have linked Decision

Validator runs on:
- Every write (via mutator)
- `gobp validate` command (full check)
- MCP tool `validate()` (on demand)

---

## 9. OPEN QUESTIONS — RESOLVED FROM VISION

VISION listed 8 open questions. Here's the resolution:

1. **Node types — 6 enough?** → Yes, v1. Extensions handle project specifics.
2. **Edge types — 5 enough?** → Yes, v1. Same as above.
3. **File layout?** → Section 4 above.
4. **MCP server lifecycle?** → Long-running daemon, per-session via MCP config.
5. **Conflict resolution?** → Last-write-wins with 1-second debounce. Single-project-owner assumption.
6. **Import mechanism?** → Section 10 below, detailed in INPUT_MODEL.md + IMPORT_MODEL.md.
7. **Backup/restore?** → Git (`.gobp/` is committed). No separate backup system in v1.
8. **Schema migration?** → Core schema versioned. Migration scripts per version bump.

---

## 10. IMPORT MECHANISM OVERVIEW

Full detail in `IMPORT_MODEL.md` (next doc to write). Summary:

**3 project state paths:**
- **Greenfield** → `gobp init --empty` → 0 nodes, start from conversation
- **In-progress** → `gobp init --from-docs docs/` → scan existing docs, propose initial structure
- **Legacy** → `gobp init --from-docs-and-code <path>` → scan docs + basic code structure

**AI-assisted import flow:**
1. AI reads existing doc with context of GoBP schema
2. AI proposes batch: nodes to create + edges to connect
3. Founder reviews proposal (via conversation with AI)
4. Founder approves → `import_commit()` executes batch atomically

**MIHOS is the in-progress test case:** 31 DOCs → Document nodes + Feature nodes + ~100 edges proposed, founder approves in batches.

---

## 11. PERFORMANCE TARGETS

| Metric | Target | Hard limit |
|---|---|---|
| Cold start (1K nodes) | 300ms | 500ms |
| `find()` query | 20ms | 50ms |
| `context()` query | 30ms | 100ms |
| `node_upsert()` write | 50ms | 200ms |
| Full rebuild index | 2s | 5s |
| Memory footprint (1K nodes) | 20MB | 50MB |
| Memory footprint (10K nodes) | 150MB | 500MB |

Benchmark runs as part of v1 ship criteria.

---

## 12. SCALING LIMITS (v1)

GoBP v1 is designed for:
- 1 project per GoBP instance
- 1 project owner (single human)
- Unlimited AI agents (within MCP client limits)
- 100-10,000 nodes
- 300-30,000 edges
- Single machine, no network

Beyond these limits → v2 considerations (not in scope for v1):
- Multi-project global search
- Team collaboration with auth
- Remote MCP server
- Distributed graph
- Real-time sync

---

## 13. REFERENCES

- VISION.md — why GoBP exists
- INPUT_MODEL.md — how AI captures from conversation (next doc)
- IMPORT_MODEL.md — how existing docs become GoBP nodes (next doc)
- MCP Protocol — https://modelcontextprotocol.io
- mcp_server.py M1 (MIHOS) — reference implementation pattern

---

*Written: 2026-04-14*
*Author: CTO Chat (Claude Opus 4.6) with CEO*
*Status: v0.1 draft, awaiting CEO review*
*Next: INPUT_MODEL.md*

◈
