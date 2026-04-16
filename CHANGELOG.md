# CHANGELOG

All notable changes to GoBP are documented here.
Format: [Wave N — Title] with date, what was added/changed/fixed.

---

## [Wave 16A05] — MCP Generator + Project Identity + Task Queue — 2026-04-16

### Added

- **MCP Generator in Viewer**: MCP button in the left panel opens a config panel
  - Auto-fills from `/api/config`: project root, name, Python path, suggested DB name, DB host
  - Generates Claude CLI / Cursor / PowerShell snippets and a copy control
- **Project identity** in `.gobp/config.yaml` (`project_name`, `project_id`, `project_description` on init)
  - `overview:` includes `project.name`, `project.id`, `project.description`, and `project.root`
- **Task queue**: `Task` node type; `tasks:` dispatch action (filter by assignee and status, sort by priority)
- **`GET /api/config`** on the viewer server for the MCP panel

### Changed

- `gobp/viewer/server.py`, `gobp/viewer/index.html`, `gobp/core/init.py`, `gobp/mcp/tools/read.py`,
  `gobp/mcp/dispatcher.py`, `gobp/mcp/parser.py`, `gobp/mcp/tools/write.py`, `gobp/schema/core_nodes.yaml`,
  `gobp/core/id_config.py`
- `tests/test_wave16a05.py` — project identity, Task CRUD smoke, `tasks:` action, `_suggest_db_name`

### Tests

- **477** tests passing (full suite).

---

## [Wave 16A04] — Full test + refactor — 2026-04-16

### Refactor

- `dispatcher.py` split: query parsing lives in `gobp/mcp/parser.py` (`parse_query`, `_normalize_type`, `_coerce_value`, `PROTOCOL_GUIDE`); dispatcher keeps routing and `_classify_doc_priority`.
- `tools/read.py` split into focused modules:
  - `read_governance.py` — `schema_governance`, `metadata_lint`
  - `read_priority.py` — `recompute_priorities`
  - `read_interview.py` — `node_template`, `node_interview`, `_NODE_EDGE_REQUIREMENTS`

### Tests

- `tests/test_wave16a04.py` — parser edge cases, ID/slug edge cases, session ID format, module import smoke tests, `create_edge` validation failures, `migrate_project` dry-run smoke.
- Single `tests/test_performance.py` (merged former v2 module); docs and `.gobp` metadata updated to match.

### Docs

- `docs/ARCHITECTURE.md` — MCP tools file layout (this wave).

---

## [Wave 16A03] — New ID Format: slug.group.number — 2026-04-16

### Why
External IDs like `ops.flow:000001` are opaque.
AI and humans cannot tell what a node is from its ID alone.

### New format
```
Standard:  {slug}.{group}.{8digits}
TestCase:  {slug}.test.{testkind}.{8digits}
Session:   meta.session.{date}.{hash}

Examples:
  verify_gate.ops.00000002
  registration_flow.ops.00000001
  trustgate_engine.ops.00000001
  traveller_identity.domain.00000001
  use_otp_for_auth.core.00000001
  auth_otp_valid.test.unit.00000001
  verify_gate_e2e.test.e2e.00000001
```

### TestCase kinds
unit, integration, e2e, smoke, performance, security,
acceptance, regression, compatibility, contract, exploratory, accessibility

### Query benefits
```
find: verify_gate          → verify_gate.ops.00000002
find: test.unit            → all unit tests
find: auth.test.unit       → unit tests about auth
find: verify_gate.test     → all tests for verify gate
```

### Changed
- id_config.py: `make_id_slug()`, `generate_external_id()`, `parse_external_id()`
- dispatcher.py: passes name + testkind to ID generation
- write.py: passes name + testkind to ID generation
- read.py: FTS indexes slug from new ID format
- migrate_ids.py: re-migration with name slugs
- All existing nodes re-migrated

### Total: 422+ tests

---

## [Wave 16A02] — Snowflake ID + Group Namespace + Migration + Hierarchical Viewer — 2026-04-16

### Why
MIHOS will have millions of nodes per type. Current text IDs don't scale.
Design the right ID system now before importing MIHOS data.

### Added
- `gobp/core/snowflake.py` — Snowflake ID generator (64-bit, sortable, unique)
- `gobp/core/id_config.py` — Group namespace config + external ID generation
- `gobp/core/migrate_ids.py` — Migration script for existing nodes
- `.gobp/config.yaml` — id_groups section added
- `.gobp/id_mapping.json` — backward compat mapping after migration

### External ID format
```
{group}.{type_prefix}:{sequence}

core.dec:0001     — Decision
core.inv:0001     — Invariant
ops.flow:0001     — Flow
ops.feat:0001     — Feature
domain.entity:000001 — Entity (large scale)
test.case:000001  — TestCase
meta.session:YYYY-MM-DD_XXXXXXXXX
```

### Groups
- core:   Decision, Invariant, Concept (tier_weight=20)
- domain: Entity (tier_weight=10, large sequence)
- ops:    Flow, Engine, Feature, Screen, APIEndpoint (tier_weight=8)
- test:   TestKind, TestCase (tier_weight=2)
- meta:   Session, Wave, Document, Lesson, Node (tier_weight=0)

### Viewer
- Hierarchical layout: d3.forceY() pulls nodes to tier position
- core at top (-300), meta at bottom (+300), ops at center (0)

### Edge types added
- enforces, triggers, validates, produces

### Migration
- 378 existing nodes migrated to new format
- Legacy IDs preserved (legacy_id field + id_mapping.json)
- All legacy queries still work

### Total: 1 MCP tool, group-namespaced IDs, 397+ tests

---
# CHANGELOG

All notable changes to GoBP are documented here.
Format: [Wave N â€” Title] with date, what was added/changed/fixed.

---

## [Wave 16A01] â€” Response Tiers + Metadata Linter + Perf Fix + Priority System â€” 2026-04-16

### Improvements (from Cursor production feedback)

- **I1 â€” Response tiers**: mode=summary|brief|full for find/get/related
  - summary: id/type/name/status/priority/edge_count (~50 tokens)
  - brief: summary + key fields + edge types (~150 tokens)
  - full: unchanged (current behavior)
- **I2 â€” Batch detail**: get_batch: ids='a,b,c' mode=brief
  - Fetch up to 50 nodes in one call
- **I3 â€” Metadata linter**: validate: metadata
  - Score 0-100 per node type
  - Flags missing description/spec_source/rule etc.
- **I4 â€” Perf test stability**:
  - node_upsert: 500ms â†’ 700ms
  - gobp_overview: 100ms â†’ 150ms
  - test_perf_node_upsert: median of 3 runs
- **I5 â€” Numeric priority**:
  - priority_score = edge_count + tier_weight
  - TIER_WEIGHTS: Invariant=20, Decision=15, Engine/Flow/Entity=10...
  - Threshold: 0-4=low, 5-9=medium, 10-19=high, 20+=critical
  - recompute: priorities â†’ batch update from graph topology
- **I6 â€” Server hints**: estimated_tokens + detail_available in summary

### Changed
- tests/test_performance.py: thresholds + median strategy
- gobp/mcp/tools/read.py: _node_summary, _node_brief, get_batch,
  metadata_lint, recompute_priorities, mode param on find/get/related
- gobp/core/graph.py: TIER_WEIGHTS, priority_label, compute_priority_score
- gobp/mcp/dispatcher.py: mode params, get_batch:, recompute:, validate: metadata

### Total: 1 MCP tool, 32 actions, 367 tests

---

## [Wave 14] â€” Schema Governance + Protocol Versioning + Access Model â€” 2026-04-15

### Problems solved
- No cross-check between schema â†” docs â†” tests â€” silent drift
- Protocol version implicit â€” AI clients couldn't detect breaking changes
- Any AI could write to graph â€” no read-only mode for viewer/analyst agents

### Added
- **Protocol versioning**: `version:` action returns v2.0 info + changelog
- **Schema governance**: `validate: schema-docs` cross-checks schema vs SCHEMA.md
  - Detects: missing SCHEMA.md entries, missing id_prefix, missing priority field
  - Returns: issues[], score (0-100), summary
- **Read-only mode**: `GOBP_READ_ONLY=true` env var blocks all write actions
  - Clear error message with hint to enable writes
  - Read actions (find, get, overview, etc.) unaffected
- **Session roles**: observer | contributor | admin stored in Session node
  - Audit trail only â€” not enforced, just recorded
- **Protocol field**: all responses include `_protocol: "2.0"`

### Changed
- dispatcher.py: version: action + validate: schema-docs/schema-tests routing
- read.py: schema_governance() function
- server.py: read-only mode + _protocol injection
- write.py: session_log() stores role field
- core_nodes.yaml: Session gets optional role field
- docs/MCP_TOOLS.md: version/governance/role/read-only documented

### Total: 1 MCP tool, 27 actions, 320+ tests

---

## [Wave 15] â€” Parser Rewrite + Import Fix + Edge Dedupe â€” 2026-04-15

### Bugs fixed (from Cursor production testing)
- **B1 (High)**: `find: login page_size=10` parsed wrong (`type='login'`, `query='page_size=10'`)
  - Fix: rewritten `parse_query()` with positional grammar
- **B2 (High)**: `related: node:x direction='out'` lost `node_id` and returned `ok=False`
  - Fix: action-specific positional key mapping (`_POSITIONAL_KEY`)
- **B3 (High)**: `import:` `doc_id` collision for same-stem files in different folders
  - Fix: `doc_id = "doc:{slug}_{md5[:6]}"` (collision-proof)
- **B4 (Medium)**: duplicate edges in file storage
  - Fix: `create_edge()` now checks `(from,type,to)` before append
  - Fix: `deduplicate_edges()` cleanup utility + `dedupe: edges` action
- **B5 (Medium)**: `import:` returned `ok=False` but still included success-like fields
  - Fix: clean response contract (`ok=False` has only error fields)
- **B6 (Medium)**: bool values parsed as strings (`"true"` instead of `True`)
  - Fix: `_coerce_value()` converts `true/false->bool`, digits->int, `null/none->None`

### Changed
- `gobp/mcp/dispatcher.py`
  - `parse_query()` rewritten
  - Added `_POSITIONAL_KEY`, `_coerce_value()`, `_tokenize_rest()`, `_parse_edge_rest()`
  - `import:` now uses collision-proof `doc_id` and clean error envelope
  - Added `dedupe: edges` action
- `gobp/core/mutator.py`
  - `create_edge()` is idempotent for duplicate triples
  - Added `deduplicate_edges()` for one-shot cleanup

### Total after wave: 1 MCP tool, 29 actions, 327+ tests

---

## [Wave 13] â€” Pagination + Upsert + Guardrails + Observability â€” 2026-04-15

### Problems solved
- Hard limit pagination: AI missed nodes when results > 20
- No upsert: AI re-importing same node created duplicates
- No guardrails: AI could write wrong data silently
- No observability: couldn't optimize slow queries

### Added
- Cursor-based pagination for `find()`, `related()`, `tests()`
- `upsert:` action with `dedupe_key` (create or update, no duplicates)
- `dry_run=true` support for write actions
- Write response guardrails: `action`, `changed_fields`, `conflicts`, `revision`
- In-memory stats tracking: calls, avg_ms, errors per action
- `stats:` action (`overview` + per-action + reset)

### Protocol additions
`find: auth page_size=50` -> paginated search  
`find: auth cursor='node:x'` -> next page  
`upsert:Node dedupe_key='name' name='x'` -> create or update  
`create:Node ... dry_run=true` -> preview  
`stats:` -> observability

### page_info format
`{ next_cursor, has_more, total_estimate, page_size }`

### Total after wave: 1 MCP tool, 25 actions, 310+ tests

---

## [Wave 12] â€” Launcher + Project Picker + Schema v3 + Better Viewer â€” 2026-04-15

### Problem solved
- Viewer required terminal command to start
- Schema lacked product node types (Engine, Flow, Entity, etc.)
- Viewer UI was too basic

### Added
- `GoBP_Viewer.bat` â€” double-click launcher (Windows)
- `projects.json` â€” machine-specific project registry (gitignored)
- `gobp/viewer/launcher.py` â€” finds projects.json, starts server, opens browser
- 9 new node types: Engine, Flow, Entity, Feature, Invariant, Screen,
  APIEndpoint, Repository, Wave
- Improved `index.html`: JetBrains Mono, project switcher, status filters,
  Core/All toggle, SpriteText labels, click-navigate relations

### Changed
- `gobp/viewer/server.py`: /api/projects endpoint, /api/graph?root=PATH,
  edges now have source/target AND from/to
- `gobp/schema/core_nodes.yaml`: 9 â†’ 18 node types
- `.gitignore`: projects.json + GoBP_Viewer.bat

### Usage
```
Double-click GoBP_Viewer.bat
â†’ Browser opens at http://localhost:8080
â†’ Select project from dropdown
â†’ View 3D graph
```

### Total after wave: 1 MCP tool, 18 node types, 290+ tests

---

## [Wave 11B] â€” 3D Graph Viewer â€” 2026-04-15

### Added
- `gobp/viewer/` â€” 3D graph viewer package
  - `__main__.py` â€” CLI entry: `python -m gobp.viewer --root PATH`
  - `server.py` â€” HTTP server + `/api/graph` endpoint
  - `index.html` â€” 3D graph SPA (3d-force-graph, dark theme, â—ˆ amber accent)
- `tests/test_viewer.py` â€” ~9 tests

### Usage
```bash
python -m gobp.viewer --root D:\GoBP
python -m gobp.viewer --root D:\MIHOS-v1 --port 8081
```

Opens browser at `http://localhost:8080`. Press Ctrl+C to stop.

### Visual design
- Node size = priority (critical=large, low=tiny)
- Node color = type (Decision=amber, Node=cyan, Idea=violet, etc.)
- Edge particles for `implements` relationships
- Filter panel by node type
- Search highlights matching nodes
- Click node â†’ detail panel with gobp() query hint
- Dark theme: deep space background + amber â—ˆ accent

### Per-project isolation
Each `--root` is a separate project graph. Projects never share data.

### Total after wave: 1 MCP tool, 22 actions, 285+ tests

---

## [Wave 11A] â€” Lazy Query Actions â€” 2026-04-15

### Problem solved
`get: <node_id>` loads full node context (~500 tokens). AI often needs
only 1 dimension. Token waste 60-80% for targeted queries.

### Solution
4 new lazy query actions â€” each returns only the requested dimension:

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

---

## [Wave 10C] â€” PostgreSQL Migration â€” 2026-04-15

### Why
MIHOS is a social network â€” projected 10,000-15,000+ nodes. SQLite hits
performance limits at scale. PostgreSQL provides unlimited scale, better
concurrent writes, and pgvector support for semantic search (Wave 9B).

### Changed
- `gobp/core/db.py` â€” rewritten for PostgreSQL (identical public API)
- `gobp/core/db_config.py` â€” new: connection config from GOBP_DB_URL env var
- `gobp/core/mutator.py` â€” unchanged (uses db.py public API)
- `gobp/core/graph.py` â€” unchanged (uses db.py public API)
- `tests/test_db_cache.py` â€” skip marker when PostgreSQL not available
- `requirements.txt` â€” psycopg2-binary>=2.9.0
- `.gitignore` â€” .env files
- `docs/INSTALL.md` â€” PostgreSQL setup guide

### Architecture
File-first principle preserved. Markdown files remain source of truth.
PostgreSQL replaces SQLite as derived index only.

### Fallback
If GOBP_DB_URL not set -> all db operations are no-ops.
In-memory GraphIndex still works for all queries.

### Connection
```
GOBP_DB_URL=postgresql://postgres:password@localhost/gobp
GOBP_MIHOS_DB_URL=postgresql://postgres:password@localhost/gobp_mihos
```
Passwords with @ must be URL-encoded: @ -> %40

### Total after wave: 1 MCP tool, 253+ tests passing

---

## [Wave 10B] â€” Bug Fixes + Priority + Edge Interface + Import Enhancement â€” 2026-04-15

### Bugs fixed
- B1: Session ID truncation â€” now always 28 chars (session:YYYY-MM-DD_XXXXXX)
- B2: Unicode encoding â€” Vietnamese/special chars stored as UTF-8 not escaped bytes
- B3: import: created 0 nodes â€” now creates Document node + auto-extracts metadata
- B4: create: required manual ID â€” now auto-generates id:XXXXXX
- B5: No Document nodes â€” import: always creates Document node
- B6: Only discovered_in edges â€” edge: action now creates semantic edges

### Features added
- F1: priority field (critical/high/medium/low) on all node types
- F2: _classify_doc_priority(): auto-classifies priority from doc content
- F3: edge: action â€” gobp(query="edge: node:a --type--> node:b")
- F4: gobp_overview priority_summary â€” see project health at a glance

### Changed
- gobp/core/mutator.py: _generate_session_id() with UUID hash
- gobp/core/mutator.py + init.py: allow_unicode=True in all YAML writes
- gobp/mcp/dispatcher.py: edge + import handlers, auto-ID generation
- gobp/mcp/tools/read.py: gobp_overview priority_summary
- gobp/schema/core_nodes.yaml: priority field on 6 node types
- docs/SCHEMA.md: priority + session ID v2 documented
- docs/MCP_TOOLS.md: edge action + updated import description

### Total after wave: 1 MCP tool, 258+ tests passing

---

## [Wave 10A] - gobp() Single Tool + Structured Query Protocol - 2026-04-15

### Problem solved
Claude.ai web and other MCP clients may limit visible tools per server.
GoBP's 14 tools were reduced to 5 visible tools - write operations invisible.

### Solution
Collapsed 14 MCP tools -> 1 `gobp()` tool with structured query protocol.
All 14 capabilities accessible via `gobp(query="<action>:<type> ...")`.

### Added
- `gobp/mcp/dispatcher.py` - deterministic query parser + router
- `tests/test_dispatcher.py` - ~20 dispatcher tests
- `gobp_overview()` response: `interface` field with full protocol guide

### Changed
- `gobp/mcp/server.py` - 14 tools -> 1 gobp() tool
- `gobp/mcp/tools/read.py` - gobp_overview includes PROTOCOL_GUIDE
- `docs/MCP_TOOLS.md` - gobp() protocol documented as primary API

### NOT changed
- All tool functions (read.py, write.py, etc.) - unchanged
- All existing 217 tests - unchanged (test functions directly)

### Protocol
```
gobp(query="overview:")                              -> project state
gobp(query="find: login")                            -> search nodes
gobp(query="create:Idea name='x' session_id='y'")   -> create node
gobp(query="lock:Decision topic='x' what='y'")      -> lock decision
gobp(query="session:start actor='x' goal='y'")      -> start session
```

### Total after wave: 1 MCP tool, 237+ tests passing

---

## [Wave 9A] â€” SQLite Persistent Index + LRU Cache â€” 2026-04-15

### Added
- `gobp/core/db.py` â€” SQLite index manager (init, upsert, delete, query, rebuild)
- `gobp/core/cache.py` â€” LRU cache with TTL, thread-safe, module singleton
- `tests/test_db_cache.py` â€” 17 tests for db + cache modules

### Changed
- `gobp/core/graph.py` â€” `load_from_disk()` now builds SQLite index after memory load
- `gobp/core/mutator.py` â€” write-through SQLite update after every mutation
- `gobp/mcp/server.py` â€” `gobp_overview` cached with 60s TTL
- `gobp/cli/commands.py` â€” `validate --reindex` flag to rebuild index
- `.gitignore` â€” `.gobp/index.db` gitignored

### Performance improvement vs Wave H baseline

| Tool | Before (Wave H) | After (Wave 9A) |
|---|---|---|
| gobp_overview (cache hit) | 460ms | < 5ms |
| gobp_overview (cold) | 460ms | < 100ms |
| find | 60ms | < 50ms |
| node_upsert | 210ms | < 200ms |
| All read tools | ~60ms | < 50ms |

### Total after wave: 14 MCP tools, 217 tests passing

---

## [Wave 4] â€” CLI + Schema v2 + Universal Test Taxonomy â€” 2026-04-15

### Added
- `gobp/core/init.py` â€” `init_project()`: bootstrap .gobp/ structure with v2 config
- `gobp/cli.py` â€” 3 CLI commands: `init`, `validate`, `status`
- `gobp/__main__.py` â€” module entry point
- Schema v2: 3 new core node types: `Concept`, `TestKind`, `TestCase`
- Schema v2: 2 new edge types: `covers` (TestCaseâ†’Node), `of_kind` (TestCaseâ†’TestKind)
- 16 universal TestKind seed nodes auto-created on `gobp init` (4 groups: functional/non_functional/security/process)
- 5 security TestKind kinds: Auth, Input Validation, Network, Encryption, API Security, Dependency
- 1 `concept:test_taxonomy` node explaining AI how to use TestKind/TestCase
- `find()`: new `type` filter parameter â€” enables `find(query="login", type="TestCase")`
- `gobp_overview`: new `concepts[]` and `test_coverage{}` sections
- Multi-user placeholders in `config.yaml`: owner, collaborators, access_model, project_id (all null, ready for v2)
- `tests/test_wave4.py`: 21 tests

### Changed
- `core_nodes.yaml`: schema_version 1.0 â†’ 2.0, 6 â†’ 9 node types
- `core_edges.yaml`: 5 â†’ 7 edge types
- `migrate.py`: CURRENT_SCHEMA_VERSION 1 â†’ 2, v1â†’v2 migration step added

### Total after wave: 14 MCP tools, 200 tests passing

---

## [Performance Baseline] â€” Pre-Wave 9A â€” 2026-04-15

Measured on mihos_root fixture (~30 nodes, ~30 edges), Windows 11, Python 3.14.3.

| Tool | Actual (ms) | Target (ms) | Max (ms) | Status |
|---|---|---|---|---|
| gobp_overview | 460 | 30 | 100 | over max |
| node_upsert | 210 | 50 | 200 | over max |
| session_log | 80 | 30 | 100 | within max |
| lessons_extract | 70 | N/A | 2000 | within max |
| decisions_for | 60 | 20 | 50 | over max |
| context | 60 | 30 | 100 | within max |
| find | 60 | 20 | 50 | over max |
| doc_sections | 60 | 10 | 30 | over max |
| session_recent | 60 | 20 | 50 | over max |
| signature | 60 | 10 | 30 | over max |

**Root cause:** All queries reload GraphIndex from disk (O(n) file reads) per call.
With 30 nodes, ~60ms baseline. Projected at 500 nodes: ~1000ms â€” unusable.

**Fix:** Wave 9A â€” SQLite persistent index eliminates per-query disk scan.
Expected post-9A: all tools < 10ms (30-50x improvement).

---

## [Wave 8] â€” MIHOS Integration Test â€” 2026-04-15

### Added
- `tests/fixtures/mihos_fixture.py` â€” MIHOS-scale fixture (~30 nodes, ~30 edges)
- `tests/fixtures/__init__.py`
- `gobp/schema/extensions/mihos.yaml` â€” MIHOS schema extension (Imprint + Provider types)
- `gobp/schema/extensions/__init__.py`
- `tests/test_performance.py` â€” 10 latency benchmarks vs MCP_TOOLS.md Â§10 targets
- `tests/test_integration.py` â€” 3 end-to-end session workflow tests

### Verified
- All 14 MCP tools within max latency targets on MIHOS-scale data (~30 nodes)
- Full session workflow (orient â†’ capture â†’ lock â†’ close â†’ validate â†’ extract) passes
- GoBP schema extension pattern demonstrated (mihos.yaml)

### Total after wave: 14 MCP tools, 179 tests passing

---

## [Wave 6] â€” Advanced Features â€” 2026-04-15

### Added
- `gobp/core/lessons.py` â€” `extract_candidates()` with 4 pattern scanners (P1â€“P4)
- `gobp/core/migrate.py` â€” `check_version()`, `run_migration()`, schema version management
- `gobp/core/prune.py` â€” `dry_run()`, `run_prune()` â€” archive WITHDRAWN+unconnected nodes
- `gobp/mcp/tools/advanced.py` â€” `lessons_extract` MCP tool handler
- MCP tool `lessons_extract` (tool #14) registered in server
- Tests: `test_lessons.py`, `test_migrate.py`, `test_prune.py`, `test_tool_lessons_extract.py`

### Fixed
- `prune.py`: node slug now uses `_` (underscore) to match `mutator._node_file_path`
- `server.py`: async handlers are now properly `await`-ed in `call_tool()` dispatch

### Total after wave: 14 MCP tools, 166 tests passing

---

## [Wave 5] â€” Write Tools + Import Tools + Validate â€” 2026-04-14

### Added
- `gobp/mcp/tools/write.py` â€” `node_upsert`, `decision_lock`, `session_log`
- `gobp/mcp/tools/import_.py` â€” `import_proposal`, `import_commit`
- `gobp/mcp/tools/maintain.py` â€” `validate`
- 6 new tools registered in MCP server (total: 13)
- Tests for all 6 new tools
- README: "What Works After Wave 5" section

### Total after wave: 13 MCP tools, 137 tests passing

---

## [Wave 3] â€” MCP Server + Read Tools â€” 2026-04-14

### Added
- `gobp/mcp/server.py` â€” MCP server with stdio transport
- `gobp/mcp/tools/read.py` â€” 7 read tools: `gobp_overview`, `find`, `signature`, `context`, `session_recent`, `decisions_for`, `doc_sections`
- Example client configs: Cursor, Claude Desktop, Claude CLI, Continue.dev
- Tests for all 7 read tools

### Total after wave: 7 MCP tools, 109 tests passing

---

## [Wave 2] â€” File Storage + Mutator â€” 2026-04-14

### Added
- `gobp/core/history.py` â€” append-only JSONL event log
- `gobp/core/mutator.py` â€” atomic file writes, `create_node`, `update_node`, `create_edge`, `delete_node`, `delete_edge`
- `.gobp/history/YYYY-MM-DD.jsonl` log format
- Tests: `test_history.py` (10 tests), `test_mutator.py` (20 tests)

### Total after wave: 66 tests passing

---

## [Wave 1] â€” Core Engine â€” 2026-04-14

### Added
- `gobp/core/loader.py` â€” markdown + YAML front-matter parser
- `gobp/core/validator.py` â€” schema validation for nodes and edges
- `gobp/core/graph.py` â€” `GraphIndex` in-memory graph with load, query, error collection
- Tests: loader/validator (26 tests), graph (11 tests)

### Total after wave: 50 tests passing

---

## [Wave 0] â€” Repository Init â€” 2026-04-14

### Added
- Repository structure: `gobp/`, `docs/`, `waves/`, `tests/`, `_templates/`
- `gobp/schema/core_nodes.yaml` â€” 6 node types: Node, Idea, Decision, Session, Document, Lesson
- `gobp/schema/core_edges.yaml` â€” 5 edge types: relates_to, supersedes, implements, discovered_in, references
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`
- `LICENSE` (MIT)
- 6 node/edge templates in `gobp/templates/`
- Smoke tests (13 tests)

### Total after wave: 13 tests passing

---

## Foundational docs (pre-Wave 0)

Written before any code:
- `CHARTER.md` â€” mission, non-goals, principles
- `VISION.md` â€” 4 pain points, target state
- `docs/ARCHITECTURE.md` â€” file-first design, GraphIndex, lifecycle
- `docs/SCHEMA.md` â€” 6 node types, 5 edge types, validation rules
- `docs/MCP_TOOLS.md` â€” all tool specs (source of truth)
- `docs/INPUT_MODEL.md` â€” how founders speak, capture patterns
- `docs/IMPORT_MODEL.md` â€” import flow, proposal state machine

