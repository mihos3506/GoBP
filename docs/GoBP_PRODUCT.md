# ◈ GoBP — Product Overview

**Version:** v1.0
**Date:** 2026-04-15

---

## What is GoBP?

GoBP (Graph of Brainstorm Project) is a **persistent AI memory layer** for software projects.

It stores project knowledge — ideas, decisions, features, sessions, lessons — as a structured graph. Any AI agent with MCP support can read and write to this graph, giving every AI agent in your workflow access to the same shared context.

```
Without GoBP:                    With GoBP:
  Claude tab 1 → forgets          Claude → GoBP → remembers
  Claude tab 2 → forgets          Cursor → GoBP → remembers
  Cursor → no context             Claude CLI → GoBP → remembers
  CEO re-explains everything      CEO explains once, AI remembers forever
```

---

## The Problem GoBP Solves

### Pain 1 — AI session amnesia
Every new AI session starts with zero context. A solo founder building with an AI team spends 1-2 hours per day re-explaining context that was already explained yesterday.

**Token cost without GoBP:**
- Paste DOC-07 Core Flows: ~4,500 tokens
- Paste DOC-02 Master Definitions: ~3,660 tokens
- Paste 5 docs per session = ~20,000 tokens just for context
- 5 sessions/day = ~100,000 tokens/day wasted

**Token cost with GoBP:**
- `gobp(query="overview:")` = ~800 tokens
- 3-4 targeted queries = ~1,200 tokens
- Total: ~2,000 tokens/day
- **Savings: ~98%**

### Pain 2 — Ideas drift
Ideas mentioned in one session get implemented differently in another. The original intent gets lost between brainstorm and build.

**GoBP fix:** Every idea is captured as an `Idea` node with `raw_quote` (founder's exact words) and `interpretation` (AI's understanding) stored separately. Nothing drifts.

### Pain 3 — Knowledge silos
Claude Desktop knows things Cursor doesn't. Cursor knows things Claude CLI doesn't. Each AI re-discovers the same context independently.

**GoBP fix:** One shared graph. Any MCP-capable AI reads the same data.

### Pain 4 — No decision history
"Why did we decide to use Email OTP instead of Face ID?" — nobody remembers. The rationale gets lost.

**GoBP fix:** `Decision` nodes store `what`, `why`, `alternatives_considered`, and `locked_by`. Full audit trail forever.

---

## Core Philosophy

### File-first
Markdown files with YAML front-matter are the source of truth. The database index is derived and rebuildable at any time. If the system crashes, your data is intact in plain text files committed to git.

### Human-free authoring
The founder never edits GoBP files directly. The founder talks to AI. AI writes to GoBP via MCP tools. This removes friction from knowledge capture.

### AI-agnostic
GoBP speaks MCP — the universal protocol for AI tool integration. Any AI that supports MCP can use GoBP: Claude, Cursor, Claude CLI, Continue.dev, Windsurf, and any future MCP client.

### One tool, all capabilities
GoBP exposes a single MCP tool: `gobp()`. Actions are listed in `gobp/mcp/parser.py` (`PROTOCOL_GUIDE`) and surfaced via `overview:` / `overview: full_interface=true`. This works even in MCP clients that limit tool count.

---

## What GoBP Stores

### Node Types (21 in packaged `core_nodes.yaml`)

| Type | Purpose | Example ID |
|---|---|---|
| Node | Generic container | `node:flow_auth` |
| Idea | Raw brainstorm from conversation | `idea:i001` |
| Decision | Locked architectural choice | `dec:d001` |
| Session | AI working session record | `meta.session.YYYY-MM-DD.*` |
| Document | Registered project document | `doc:…` |
| Lesson | Learned pattern from experience | `lesson:ll001` |
| Concept | Framework concept for AI orientation | `concept:test_taxonomy` |
| TestKind | Test category (16 kinds seeded on init); field `group` = process / functional / non_functional / security | `testkind:unit` |
| TestCase | Individual test instance; `kind_id` → TestKind | `tc:…` |
| Engine, Flow, Entity, Feature | Product graph | `engine:…`, `flow:…`, … |
| Invariant, Screen, APIEndpoint, Repository | Constraints, UI, API, repo metadata | … |
| Wave, Task | Sprint / AI queue work | … |
| CtoDevHandoff, QaCodeDevHandoff | Structured handoffs | … |

**Full field definitions:** `docs/SCHEMA.md`.

### Edge Types (14 in `core_edges.yaml`)

`relates_to`, `supersedes`, `implements`, `discovered_in`, `references`, `covers`, `depends_on`, `tested_by`, `of_kind`, `enforces`, `triggers`, `validates`, `produces` — plus any project extensions. **Details:** `docs/SCHEMA.md` section 3.

### Per-node fields
Every node can have:
- `priority` — critical / high / medium / low
- `code_refs` — list of code files implementing this node
- `invariants` — hard constraints that must always be true
- `status` — lifecycle state (ACTIVE, DEPRECATED, etc.)

---

## The gobp() Query Protocol

All interactions go through one tool with structured queries:

```
READ:
  gobp(query="overview:")                    → project state + protocol guide
  gobp(query="find: login")                  → search any node
  gobp(query="find:Decision auth")           → type-filtered search
  gobp(query="get: node:flow_auth")          → full context + edges
  gobp(query="code: node:flow_auth")         → code files only (~150 tokens)
  gobp(query="invariants: node:flow_auth")   → constraints only (~100 tokens)
  gobp(query="tests: node:flow_auth")        → linked test cases
  gobp(query="related: node:flow_auth")      → neighbor summary
  gobp(query="decisions: auth:login.method") → locked decisions for topic
  gobp(query="recent: 3")                    → latest 3 sessions

WRITE:
  gobp(query="session:start actor='cursor' goal='implement login'")
  gobp(query="create:Node name='Login' priority='critical' session_id='x'")
  gobp(query="create:Idea name='use OTP' subject='auth:login' session_id='x'")
  gobp(query="lock:Decision topic='auth:login' what='Email OTP' why='SMS unreliable'")
  gobp(query="session:end outcome='login done' handoff='next: write tests'")
  gobp(query="edge: node:flow_auth --implements--> node:pop_protocol")

IMPORT & MAINTENANCE:
  gobp(query="import: docs/DOC-07.md session_id='x'")  → Document node + auto-priority
  gobp(query="validate: all")
  gobp(query="extract: lessons")
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  AI Agents (Claude, Cursor, Claude CLI, etc.)   │
│  One tool: gobp(query="...")                    │
└────────────────────┬────────────────────────────┘
                     │ MCP Protocol
                     ▼
┌─────────────────────────────────────────────────┐
│  GoBP MCP Server (server.py + dispatcher.py)    │
│  22 actions via structured query protocol       │
└────────────────────┬────────────────────────────┘
                     │ Python function calls
                     ▼
┌─────────────────────────────────────────────────┐
│  Core Engine                                    │
│  graph.py — O(1) in-memory indexes              │
│  mutator.py — write-through to disk + DB        │
│  db.py — PostgreSQL persistent index            │
└────────────────────┬────────────────────────────┘
                     │ File I/O + SQL
                     ▼
┌─────────────────────────────────────────────────┐
│  Storage                                        │
│  .gobp/nodes/*.md     — node files (source of truth) │
│  .gobp/edges/*.yaml   — edge files              │
│  .gobp/history/*.jsonl — append-only audit log  │
│  PostgreSQL           — derived index           │
└─────────────────────────────────────────────────┘
```

---

## Performance

| Metric | Value |
|---|---|
| Server startup (load index) | ~560ms once |
| All queries after load | < 1ms |
| Write operation | ~200-300ms |
| Token cost per session with GoBP | ~2,000 tokens |
| Token cost per session without GoBP | ~20,000-100,000 tokens |
| Token savings | ~98% |

---

## Scale

| Scenario | Nodes | Recommendation |
|---|---|---|
| Small project (1 developer) | < 1,000 | In-memory mode OK |
| Medium project (solo founder + AI team) | 1,000-10,000 | PostgreSQL recommended |
| Large project (social network, team) | 10,000+ | PostgreSQL required |

---

## What GoBP Is Not

- **Not a chatbot** — GoBP has no UI. Founders interact via AI of choice.
- **Not a replacement for project docs** — Docs remain. GoBP references and indexes them.
- **Not a code intelligence tool** — GoBP stores knowledge about code, not the code itself.
- **Not a production database** — GoBP stores project knowledge, not user data.
- **Not generic LLM memory** — GoBP is project-scoped, not conversation-scoped.

---

## Origin Story

GoBP was born from a real pain. A solo non-developer founder was building MIHOS — a heritage-tech social network — with an AI team in 2026. Every day, 1-2 hours were lost re-explaining context to AI agents that had forgotten everything.

GoBP started as an internal tool to solve this problem. It proved itself by being used to build itself — GoBP's own development history is stored in GoBP.

**Goal:** Every step becomes a unit of exchangeable value. Every decision, idea, lesson — captured, searchable, available to any AI that joins the project.

---

*◈ GoBP — Where knowledge persists.*
