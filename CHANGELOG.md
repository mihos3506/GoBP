# CHANGELOG

All notable changes to GoBP are documented here.
Format: [Wave N — Title] with date, what was added/changed/fixed.

---

## [Wave 4] — CLI + Schema v2 + Universal Test Taxonomy — 2026-04-15

### Added
- `gobp/core/init.py` — `init_project()`: bootstrap .gobp/ structure with v2 config
- `gobp/cli.py` — 3 CLI commands: `init`, `validate`, `status`
- `gobp/__main__.py` — module entry point
- Schema v2: 3 new core node types: `Concept`, `TestKind`, `TestCase`
- Schema v2: 2 new edge types: `covers` (TestCase→Node), `of_kind` (TestCase→TestKind)
- 16 universal TestKind seed nodes auto-created on `gobp init` (4 groups: functional/non_functional/security/process)
- 5 security TestKind kinds: Auth, Input Validation, Network, Encryption, API Security, Dependency
- 1 `concept:test_taxonomy` node explaining AI how to use TestKind/TestCase
- `find()`: new `type` filter parameter — enables `find(query="login", type="TestCase")`
- `gobp_overview`: new `concepts[]` and `test_coverage{}` sections
- Multi-user placeholders in `config.yaml`: owner, collaborators, access_model, project_id (all null, ready for v2)
- `tests/test_wave4.py`: 21 tests

### Changed
- `core_nodes.yaml`: schema_version 1.0 → 2.0, 6 → 9 node types
- `core_edges.yaml`: 5 → 7 edge types
- `migrate.py`: CURRENT_SCHEMA_VERSION 1 → 2, v1→v2 migration step added

### Total after wave: 14 MCP tools, 188 tests passing

---

## [Wave 8] — MIHOS Integration Test — 2026-04-15

### Added
- `tests/fixtures/mihos_fixture.py` — MIHOS-scale fixture (~30 nodes, ~30 edges)
- `tests/fixtures/__init__.py`
- `gobp/schema/extensions/mihos.yaml` — MIHOS schema extension (Imprint + Provider types)
- `gobp/schema/extensions/__init__.py`
- `tests/test_performance.py` — 10 latency benchmarks vs MCP_TOOLS.md §10 targets
- `tests/test_integration.py` — 3 end-to-end session workflow tests

### Verified
- All 14 MCP tools within max latency targets on MIHOS-scale data (~30 nodes)
- Full session workflow (orient → capture → lock → close → validate → extract) passes
- GoBP schema extension pattern demonstrated (mihos.yaml)

### Total after wave: 14 MCP tools, 179 tests passing

---

## [Wave 6] — Advanced Features — 2026-04-15

### Added
- `gobp/core/lessons.py` — `extract_candidates()` with 4 pattern scanners (P1–P4)
- `gobp/core/migrate.py` — `check_version()`, `run_migration()`, schema version management
- `gobp/core/prune.py` — `dry_run()`, `run_prune()` — archive WITHDRAWN+unconnected nodes
- `gobp/mcp/tools/advanced.py` — `lessons_extract` MCP tool handler
- MCP tool `lessons_extract` (tool #14) registered in server
- Tests: `test_lessons.py`, `test_migrate.py`, `test_prune.py`, `test_tool_lessons_extract.py`

### Fixed
- `prune.py`: node slug now uses `_` (underscore) to match `mutator._node_file_path`
- `server.py`: async handlers are now properly `await`-ed in `call_tool()` dispatch

### Total after wave: 14 MCP tools, 166 tests passing

---

## [Wave 5] — Write Tools + Import Tools + Validate — 2026-04-14

### Added
- `gobp/mcp/tools/write.py` — `node_upsert`, `decision_lock`, `session_log`
- `gobp/mcp/tools/import_.py` — `import_proposal`, `import_commit`
- `gobp/mcp/tools/maintain.py` — `validate`
- 6 new tools registered in MCP server (total: 13)
- Tests for all 6 new tools
- README: "What Works After Wave 5" section

### Total after wave: 13 MCP tools, 137 tests passing

---

## [Wave 3] — MCP Server + Read Tools — 2026-04-14

### Added
- `gobp/mcp/server.py` — MCP server with stdio transport
- `gobp/mcp/tools/read.py` — 7 read tools: `gobp_overview`, `find`, `signature`, `context`, `session_recent`, `decisions_for`, `doc_sections`
- Example client configs: Cursor, Claude Desktop, Claude CLI, Continue.dev
- Tests for all 7 read tools

### Total after wave: 7 MCP tools, 109 tests passing

---

## [Wave 2] — File Storage + Mutator — 2026-04-14

### Added
- `gobp/core/history.py` — append-only JSONL event log
- `gobp/core/mutator.py` — atomic file writes, `create_node`, `update_node`, `create_edge`, `delete_node`, `delete_edge`
- `.gobp/history/YYYY-MM-DD.jsonl` log format
- Tests: `test_history.py` (10 tests), `test_mutator.py` (20 tests)

### Total after wave: 66 tests passing

---

## [Wave 1] — Core Engine — 2026-04-14

### Added
- `gobp/core/loader.py` — markdown + YAML front-matter parser
- `gobp/core/validator.py` — schema validation for nodes and edges
- `gobp/core/graph.py` — `GraphIndex` in-memory graph with load, query, error collection
- Tests: loader/validator (26 tests), graph (11 tests)

### Total after wave: 50 tests passing

---

## [Wave 0] — Repository Init — 2026-04-14

### Added
- Repository structure: `gobp/`, `docs/`, `waves/`, `tests/`, `_templates/`
- `gobp/schema/core_nodes.yaml` — 6 node types: Node, Idea, Decision, Session, Document, Lesson
- `gobp/schema/core_edges.yaml` — 5 edge types: relates_to, supersedes, implements, discovered_in, references
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`
- `LICENSE` (MIT)
- 6 node/edge templates in `gobp/templates/`
- Smoke tests (13 tests)

### Total after wave: 13 tests passing

---

## Foundational docs (pre-Wave 0)

Written before any code:
- `CHARTER.md` — mission, non-goals, principles
- `VISION.md` — 4 pain points, target state
- `docs/ARCHITECTURE.md` — file-first design, GraphIndex, lifecycle
- `docs/SCHEMA.md` — 6 node types, 5 edge types, validation rules
- `docs/MCP_TOOLS.md` — all tool specs (source of truth)
- `docs/INPUT_MODEL.md` — how founders speak, capture patterns
- `docs/IMPORT_MODEL.md` — import flow, proposal state machine
