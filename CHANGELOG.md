# CHANGELOG

All notable changes to GoBP are documented here.
Format: [Wave N — Title] with date, what was added/changed/fixed.

---

## [Wave G] — Code Refactor + Clean — 2026-04-19

### Removed

- `gobp/core/validator_v2.py` — merged into `gobp/core/validator.py` (`ValidatorV2`, `make_validator_v2`)
- `gobp/core/mutator.py` — replaced by `gobp/core/fs_mutator.py` (file-backed YAML nodes/edges)
- `update:` / `retype:` MCP query actions — use `edit:` instead
- `lifecycle` / `read_order` explicit defaults in `write.py` node_upsert path (validation still applies via `ValidatorV2.auto_fix` when schema is v2)
- Live `D:/GoBP` dependency tests from `tests/test_wave16a02.py`
- Orphaned CSS `.gobp-query` in viewer

### Fixed

- Viewer: `VISIBLE_LIFECYCLES` / `VISIBLE_READ_ORDERS` ReferenceError on CORE ONLY / SHOW ALL
- `validate: metadata` now routes to `metadata_lint` without requiring PostgreSQL v3

### Changed

- `.cursorrules` — v2 legacy section trimmed; module list updated
- `docs/README.md` — current state (Waves A–G, 764+ tests) + Wave G deprecated notes

---

## [Wave F] — Multi-Agent Coordination — 2026-04-19

### Added

- `gobp/core/import_lock.py`: PostgreSQL advisory lock for imports
  - `acquire_import_lock()`: non-blocking, context manager
  - `import_locks` table in schema v3
- `gobp/core/session_watchdog.py`: auto-close stale sessions > 24h
  - `close_stale_sessions()`: mark IN_PROGRESS → STALE_CLOSED
  - Runs automatically on `overview:` call
- `validate: v3`: schema v3 compatibility check (5 checks)
  - Required fields, ErrorCase severity, dangling edges, orphans, stale sessions
  - Score 0-100
- `ping:` action: health check with DB status + active_sessions + import_locks
- `tests/test_wave_f.py`: multi-agent coordination coverage

### Changed

- `overview: v3`: runs session watchdog, reports closed sessions
- `import_atomic:`: acquires import lock before executing
- `create_schema_v3()`: creates import_locks table

---

## [Wave E] — Viewer UI Improvements — 2026-04-19

### Changed (viewer)

- Sidebar: count column alignment (tabular-nums, flex layout)
- Sidebar: font hierarchy by depth level, active group highlight
- VIEW section: "Show all edges" label (was: "Show metadata edges")
- Node detail: added EDGES section (direction + name + reason)
- Node detail: added CODE section (shown when node has code)
- Node detail: added severity badge for ErrorCase nodes
- Node detail: removed gobp query string display
- Node detail: removed Debug: raw fields section
- Rendering order: breadcrumb → name → description → code → edges

---

## [Wave D] — MCP Read Actions v3 — 2026-04-19

### Added

- `find: v3`: BM25F weighted search + BFS expand depth 1 + pyramid modes
- `get_batch: v3`: pyramid modes + since= differential fetch (~70% token savings)
- `context: task=`: FTS + BFS depth 2 → bundled context (1 request)
- `session:resume`: load prev handoff + changes since last session
- `overview: v3`: active_sessions + correct v3 group stats
- `explore: v3`: no DISCOVERED_IN, desc_l2, group-based siblings
- `tests/test_wave_d.py`: read actions v3 coverage

---

## [Wave C] — Write Path v3 + Viewer UI Overhaul — 2026-04-19

### Added

- `gobp/core/mutator_v3.py`: full write path (validate→pyramid→PG→file→log)
- `gobp/core/db.py`: upsert_node_v3, delete_node_v3, upsert_edge_v3, etc.
- `gobp/core/cache.py`: invalidate_node() + invalidate_edge()
- `edit:` action: delete+create semantic, edge ops, history inherit
- Optimistic locking: conflict_warning on updated_at mismatch
- `tests/test_wave_c.py`: write path v3 coverage

### Viewer

- Removed: LIFECYCLE + READ ORDER sidebar filters
- Hidden: DISCOVERED_IN edges from relationships panel
- Hidden: empty reasons, lifecycle, read_order from detail panel
- Updated: node colors by top-level group
- Updated: font + hierarchy clarity

---

## [Wave B] — Cleanup + Viewer Dashboard — 2026-04-19

### Removed

- 7 deprecated docs superseded by v3 doc set
- `docs/GoBP_ARCHITECTURE.md`, `docs/MCP_TOOLS.md`, `docs/GoBP_AI_USER_GUIDE.md`
- `docs/GOBP_SCHEMA_REDESIGN_v2_1.md`, `docs/INPUT_MODEL.md`
- `docs/IMPORT_MODEL.md`, `docs/IMPORT_CHECKLIST.md`

### Added

- `gobp/viewer/dashboard.html` — stats dashboard page (Page 2)
- `gobp/viewer/server.py`: `/dashboard` route + `/api/dashboard` endpoint
- `tests/test_wave_b.py`: 12+ tests

### Changed

- `gobp/viewer/index.html`: dashboard nav link
- `.cursorrules`: schema v3 section added
- `docs/README.md`: current state + deprecated list updated

### Total after wave: 705+ tests passing

---

## [Wave A] — Database Foundation — 2026-04-19

### Added

- `gobp/core/pyramid.py` — description pyramid extractor (L1/L2/full)
- `gobp/core/validator_v3.py` — schema v3 validator (2 templates)
- `gobp/core/file_format_v3.py` — schema v3 serialize/deserialize
- `gobp/core/db.py`: `create_schema_v3()`, `get_schema_version()`
- `tests/test_wave_a.py`: 35+ tests
- `waves/wave_a_brief.md`

### Changed

- `gobp/core/id_generator.py`: verified v2 format (group_slug.name_slug.8hex)

### PostgreSQL Schema v3

- `nodes`: desc_l1/l2/full pyramid, BM25F search_vec, no typed fields
- `edges`: from/to/reason only (no type field), reason_vec index
- `node_history`: append-only per node

### Total after wave: 705+ tests passing

---

## [Wave 17A06] — Self-Upgrade Loop + Incident History — 2026-04-19

### Changed — LessonSkill schema v2

- **`sub_type`**: `ai_self` | `work_quality` | `product` (required).
- **`procedure`**: when non-empty, missing `HOW` / `EVALUATE` / `EVOLVE_TRIGGER` markers emit **warnings** only (empty procedure allowed for backward compatibility).
- **`supersedes`**, **`versions`**, **`applies_to`**, **`evolve_count`** optional fields; **`ValidatorV2.validate_node_full`** / **`SchemaV2.validate_node_warnings`**.

### Added — `incident_history` on six infra node types

- **Vulnerability** — `incident_history`, `cve_id`, `cvss_score`, `patched_in`.
- **Migration** — `incident_history`, `rollback_plan`, `tested_on`, `duration_min`.
- **AuthFlow**, **Engine**, **APIEndpoint**, **Encryption** — `incident_history` (append-only convention).

### Added — Reflection node type

- **`Meta > Reflection`**: `trigger`, `wave_ref`, `findings`; optional `skills_upgraded`, `skills_created`, `next_focus`, `actor`.

### Added — `evolve:` MCP action (read-only)

- **`gobp(query="evolve: wave='…'")`** — checklist + up to 20 LessonSkill summaries.
- **`gobp(query="evolve: wave='…' status='complete'")`** — lookup Reflection by `wave_ref`.

### Changed — write path

- **`TYPE_DEFAULTS`**: LessonSkill (`evolve_count`, `applies_to`, `versions`); Reflection (`actor`, `skills_upgraded`, `skills_created`).
- **`LessonSkill.supersedes`**: deprecate old skill, append new id to `versions`, create **`supersedes`** edge (idempotent via `create_edge`).

### Tests

- **`tests/test_wave17a06.py`** — 26 tests; full suite **730** passed.

---

## [Docs] — Project snapshot refresh — 2026-04-19

### Changed

- **`docs/README.md`** — Bilingual index + table: schema v2 (93/15), MCP, storage, batch, viewer, tests.
- **`docs/VISION.md`**, **`docs/ARCHITECTURE.md`**, **`docs/GoBP_ARCHITECTURE.md`**, **`docs/SCHEMA.md`**, **`docs/MCP_TOOLS.md`**, **`docs/GoBP_PRODUCT.md`**, **`docs/INPUT_MODEL.md`**, **`docs/IMPORT_MODEL.md`**, **`docs/INSTALL.md`**, **`docs/GoBP_INSTALL.md`**, **`docs/IMPORT_CHECKLIST.md`**, **`docs/GoBP_AI_USER_GUIDE.md`**, **`docs/GOBP_SCHEMA_REDESIGN_v2.1.md`**, **`docs/wave_17a_series_plan.md`** — Aligned with current repo (v2 taxonomy, single `gobp` tool, optional PostgreSQL, viewer v2, Wave 17A05 batch behavior).
- **`docs/wave_14_brief.md`** — Archive pointer to current docs.

---

## [Wave 17A05] — Bug Fixes + Viewer v2 — 2026-04-19

### Fixed

- **Batch parser** — `create: Type: Name | key="value"` named params merged into the op; plain text before first `key=` remains `description`.
- **Batch parser** — newlines inside quoted values no longer split ops; unknown `word:` lines start a new logical op (strict parse errors preserved).
- **`create:` / `node_upsert`** — auto-generate `id` via `generate_id(name, group)` when missing (`Session` / `TestCase` keep `generate_external_id` formats).
- **`TYPE_DEFAULTS`** — `Concept.definition` and `ErrorDomain.fix_guide` / `domain` align with `description` `{info, code}`.

### Changed

- **Viewer** — panel v2: group breadcrumb, lifecycle + read_order, description info + code, RELATIONSHIPS with reason, raw fields under collapsed Debug; ErrorCase and Invariant layouts; sidebar: group tree, lifecycle, read order filters.
- **`gobp/viewer/server.py`** — `/api/graph` nodes pass full YAML payloads; edges include `reason`.

### Tests

- **`tests/test_wave17a05.py`** — 15 tests (batch, write path, panel HTML helpers).

---

## [Wave 17A04] — Docs + Agents + Backfill — 2026-04-19

### Changed

- **`.cursorrules` v9** — Lessons from implementation review of Waves 17A01–17A03 (prefix/`exact` semantics, `get:` default churn, `suggest` merge, `auto_fill_description` types, schema cache); not a duplicate of the Query v2 cheat sheet.
- **`docs/GoBP_AI_USER_GUIDE.md`** — v2: 93-type table, `find:` group filters, `get:` brief/full/debug, `explore:` breadcrumb/siblings/relationships, `suggest:` group-aware, ID format v2, query rules 14–17, import workflow.
- **`docs/IMPORT_CHECKLIST.md`** — Schema v2 pre-import, ErrorCase / Invariant sections, post-import verify with `explore:`.

### Added

- **`scripts/wave17a04_task5_backfill.py`** — Reproducible `session:start` → `batch` (Wave 17A01–17A03 nodes + edges to `dec:d004` / `dec:d006`) → `session:end` (reload `GraphIndex` after `session:start` before `batch`).
- **GoBP graph:** Wave nodes **Wave 17A01**, **Wave 17A02**, **Wave 17A03** with `references` to decision nodes (dec:d005 backfill).

### Tests

- **690+** expected unchanged (docs-only wave); full suite run at end of wave.

---

## [Wave 17A03] — Query Engine — 2026-04-19

### Added

- **`find:`** — `group="..."` top-down group filter; `group contains "..."` substring filter; combined with `type=` and keyword search; `group_filter` in response; **`find_by_group(..., exact=True)`** now returns only nodes whose `group` equals the path (prefix index no longer over-matches).
- **`explore:`** — resolve **node ID** first; **`breadcrumb`**, **`siblings`**, **`relationships`** (edges include **`reason`** when present).
- **`get:` / `context()`** — **`mode=brief`** (default), **`full`**, **`debug`**; brief shows **`description.info`** and **`relationships`**; full/debug per Wave 17A03.
- **`suggest:`** — group-aware ordering, **`match_score`**, **`HIGH SIMILARITY`** warning, **`recommendation`** (UPDATE vs CREATE); merges **`suggest_related`** overlap with **`search_nodes`** hits.

### Changed

- **`GraphIndex`**: `_group_index` prefix map; **`find_by_group`**, **`find_siblings`**, **`get_group_tree`**.
- **`.cursorrules` v8** — Query protocol v2 + display modes + suggest/explore workflow (v7 rules retained).

### Tests

- **`tests/test_wave17a03.py`** — 20 tests (group index, find, explore, get modes, suggest).

---

## [Wave 17A02] — Validator bridge + schema v2 cutover — 2026-04-19

### Added

- **`gobp/core/validator_v2.py`** — `ValidatorV2` / `make_validator_v2()` for `schema_name: gobp_core_v2`; `validate_node`, `validate_edge`, `auto_fix()` (description wrap, group/lifecycle/read_order).
- **`gobp/schema/core_nodes_v1.yaml`**, **`gobp/schema/core_edges_v1.yaml`** — backups of pre-cutover v1 schema files.

### Changed

- **`gobp/schema/core_nodes.yaml`**, **`core_edges.yaml`** — promoted from v2 sources; production taxonomy is v2 (`gobp_core_v2` / `gobp_core_edges_v2`).
- **`gobp/core/schema_loader.py`** — `SchemaV2` loads `core_nodes_v2.yaml` when present, else **`core_nodes.yaml`** when `schema_name` is v2.
- **`gobp/core/mutator.py`**, **`gobp/mcp/tools/write.py`**, **`gobp/mcp/tools/maintain.py`**, **`gobp/mcp/tools/import_.py`**, **`gobp/core/graph.py`** — `coerce_and_validate_node()` uses Validator v2 when schema is v2.
- **`gobp/core/init.py`** — `seed_universal_nodes()` enriched with v2 **group**, **lifecycle**, **read_order**, **`description` `{info, code}`**.
- **`gobp/mcp/hooks.py`** — optional Validator v2 pre-check on create/upsert.
- **`gobp/mcp/tools/read.py`** — `template:` response may include **`v2_template`** (group, lifecycle, read_order, description shape).
- **`gobp/core/search.py`**, **`gobp/core/indexes.py`**, **`gobp/viewer/server.py`** — tolerate **`description`** as `{info, code}` dict.
- **`.cursorrules` v7** — schema v2 rules, ErrorCase naming, cutover notes, import hints for ErrorCase.

### Tests

- **670** tests passing in full suite (`pytest tests/ --override-ini="addopts="`).

---

## [Docs] — GoBP AI User Guide refresh — 2026-04-18

### Changed

- **`docs/GoBP_AI_USER_GUIDE.md`** — aligned with current MCP behavior:
  - Batch ops: internal chunking (200 ops); removed obsolete “max 50” client cap.
  - **Rule 6 / 13:** prefer `batch` / `quick:`; **Lesson** nodes follow **dec:d011** (suggest → update over duplicate).
  - **Hooks:** pre-write checks; errors may include **`suggestion`**.
  - Added **`quick:`**, extra actions table (`version:`, `validate:`, `get_batch:`, …), pointers to **`docs/MCP_TOOLS.md`** and **`docs/SCHEMA.md`**.
  - Appendix: `_protocol` + `_dispatch`; shortened TestKind/TestCase table (detail in SCHEMA §2.8–2.9).

---

## [Schema] — MIHOS extension 1.1 — 2026-04-18

### Changed

- **`gobp/schema/extensions/mihos.yaml`** — version **1.1**: optional `description`, `session_id`, `tags` on **Imprint** / **Provider** (align with core `Node` when merged); header notes for syncing after **core `Node`** edits.
- **`gobp/mcp/parser.py`** — canonical types **`Imprint`**, **`Provider`** for `create:` / queries.

### Tests

- `tests/test_seed_universal.py::test_parse_create_mihos_extension_types`

---

## [Wave 16A17] — Remove xdist + Test Organization — 2026-04-18

### Changed

- **pytest-xdist removed** — parallel workers used too much CPU on dev machines.
- **Default suite** — `pytest tests/` uses the fast profile (skips `@pytest.mark.slow` via `addopts`).
- **Full suite** — `pytest tests/ --override-ini="addopts="` (or `pytest tests/ -m ''` in bash) runs all tests including slow.
- **`@pytest.mark.slow`** — batch 100+ node tests and `tests/test_performance.py` (benchmarks).
- **`.cursorrules` R9** — testing strategy updated (no xdist; MIHOS data rule for tests).

### Tests

- **633** tests in full suite (serial; no `-n auto`).

---

## [Wave 16A16] — Test Performance + Graph Hygiene + Hooks — 2026-04-18

### Changed

- **pytest-xdist** — parallel execution (`-n auto` default)
  - Full suite: ~14 min → ~3 min target
  - `@pytest.mark.slow` on batch heavy tests
  - Fast dev suite: `pytest -m "not slow"` under 1 min

- **`.cursorrules`** — dec:d011 graph hygiene rule added
  - Lessons learned = update existing node over create new
  - suggest: before creating Lesson nodes

- **`CLAUDE.md`** — dec:d011 rule added (Claude CLI Task 4)

### Added

- **Hooks layer** — `gobp/mcp/hooks.py`
  - `before_write()`: type validation + session check
  - `on_error()`: actionable error suggestions
  - "Node not found" → similar node suggestions
  - AI detects errors at the earliest possible stage

### Tests

- `tests/test_wave16a16.py` — pytest config, xdist, hooks
- **633+** tests (full suite with parallel execution)

---

## [Wave 16A15] — Thin Harness + Fat Skills Setup — 2026-04-18

### Added

- **`docs/IMPORT_CHECKLIST.md`** — AI-facing import protocol checklist (template → plan → CEO review → batch), derived from Decision `dec:d002`.

### Changed

- **`.cursorrules` (v6)** — Cursor-authored standing rules: role per agent model, **R9** split into doc/data vs code vs end-of-wave full suite, **R10** GoBP MCP session capture, import protocol (**dec:d002**), graph linkage (**dec:d006**), sequential tasks / one commit per task.
- **`docs/GoBP_AI_USER_GUIDE.md`** — Rules 11–12, link to import checklist, Wave 16A14 indexing note.
- **GoBP MCP graph** — Wave nodes for history **Wave 0–16A14** (plus Wave 16A15); architecture decisions **`dec:d008`–`dec:d010`** backfilled with `discovered_in` sessions; **MIHOS** drill adds **`enforces`** edges from MCP Runtime Engine to three core Invariants (import protocol validation on real data).

### Tests

- **626+** tests (full suite; no new Python feature tests in this wave).

---

## [Wave 16A14] — Read Performance Indexes + Cycle Validation — 2026-04-18

### Added

- **`gobp/core/indexes.py`** — `InvertedIndex` (keyword → node ids, AND then OR search) and `AdjacencyIndex` (outgoing/incoming edge lists, `exclude_types`, write-time updates).
- **`gobp/core/graph_algorithms.py`** — `detect_cycles()` (DFS WHITE/GRAY/BLACK on `depends_on` / `supersedes` by default).
- **`scripts/wave16a14_bench.py`** — median ms for `find` / `explore` / `suggest` / `validate` on a 500-node / 400-edge in-memory graph.

### Changed

- **`GraphIndex`** — builds `_inverted` + `_adjacency` at load; updates on `add_node_in_memory`, `add_edge_in_memory`, `remove_node` / `remove_node_in_memory`.
- **`search_nodes` / `suggest_related`** — use inverted index when present, full scan fallback.
- **`find` / `explore` / `node_related`** — use inverted/adjacency with fallback; `explore` skips `discovered_in` via adjacency.
- **`validate`** — appends cycle warnings when `scope` is `all` or `edges`.

### Tests

- `tests/test_wave16a14.py` — 21 tests (inverted, adjacency, GraphIndex, read paths, cycles).
- **626+** tests (full suite).

---

## [Wave 16A13] — Batch Fixes + Quick Capture + Auto Chunking — 2026-04-18

### Fixed

- **Batch newline parsing** — `parse_batch_ops` normalizes literal `\\n` / double-escaped sequences before splitting lines (MCP JSON transport).

### Added

- **`TYPE_DEFAULTS` + `_auto_fill_defaults()`** — Idea and TestCase get safe defaults when fields are missing; used in `node_upsert` and `_batch_build_create_node`.
- **`quick:`** — `parse_quick()` + `quick_action()`; pipe-separated lines delegated to batch.
- **`INTERNAL_CHUNK_SIZE` (200)** — large batch op lists are processed in chunks; no fixed external op cap.

### Changed

- **Batch** — removed per-call maximum op count; docs and template hints refer to internal chunking instead of “max 500”.

### Tests

- `tests/test_wave16a13.py` — 16 tests; `scripts/wave16a13_smoke.py` smoke runner.
- **604** tests (full suite).

---

## [Wave 16A12] — MCP Server Cache — 2026-04-18

### Changed

- **MCP server in-memory GraphIndex cache** — `get_cached_index()` keeps the index in RAM; read-heavy actions reuse it instead of reloading all `.gobp/nodes` on every `gobp()` call.
- **Write path** — after mutations, the graph cache is invalidated so the next read reloads from disk; **`batch`** flushes through `update_cache(working_index)` so the warm cache stays aligned without a full reload.
- **`refresh:`** — reloads the graph from disk and refreshes the server cache (manual edits, schema work).

### Performance

- Cold load remains proportional to repo size; warm `find` / `explore` / `suggest` avoid per-call full disk scans when served from the MCP process.

### Tests

- `tests/test_wave16a12.py` — cache singleton, invalidate, update, refresh dispatch, perf sanity, `WRITE_ACTIONS`, PROTOCOL_GUIDE.
- **588** tests (full suite).

---

## [Wave 16A11] — Batch Performance Fix — 2026-04-18

### Changed

- **batch: single-load/single-save** — eliminated per-op disk reload for create / `edge+` paths; flush pending writes before ops that need disk consistency, then reload.
  - **GraphIndex:** `add_node_in_memory()`, `add_edge_in_memory()`, `remove_node_in_memory()`, `save_new_nodes_to_disk()`, `save_new_edges_to_disk()`, `flush_pending_writes()`
  - **mutator / history:** batched node file writes and batched edge append + history lines where applicable

- **Batch limit raised** from 50 to **500** ops per call (`MAX_BATCH_OPS` in `gobp/mcp/tools/write.py`). PROTOCOL_GUIDE and template_batch instructions updated.

### Impact

- Large imports (e.g. hundreds of nodes + edges) complete in one batch call without reloading the full index every op.

### Tests

- `tests/test_wave16a11.py` — in-memory GraphIndex helpers, batch limit, mixed create+edge, PROTOCOL_GUIDE batch limit text.
- **581** tests (full suite).

---

## [Wave 16A10] — Smart Template + Compact + AI Query Rules — 2026-04-17

### Added

- **template: suggested_edges** — edge suggestions from schema per node type
  - AI sees which edge types commonly apply (from `core_edges.yaml` `allowed_node_types`)
  - `batch_example` includes sample `edge+:` lines

- **template_batch:** — fillable multi-node template
  - `template_batch: Engine count=5` → repeated blocks with placeholders and edge hints
  - No hard limit on nodes or edges per node in the template text; executor still caps ops per call
  - Instructions for splitting large batches

- **compact=true flag** — minimal token responses
  - `explore` compact: string edge lines + slim `node` / `also_found`
  - `batch`: summary by default; `verbose=true` restores full `skipped` / `warnings` lists
  - `find` / `get` (`context`) compact: `id` + `name` + `type` (and `edge_count` on get)

- **AI Query Rules** — 10 rules + `token_guide` on `PROTOCOL_GUIDE` (`gobp/mcp/parser.py`)
  - Covers overview once, template before create, batch for writes, compact explore, error retry discipline

### Tests

- `tests/test_wave16a10.py` — template edges, template_batch, compact modes, protocol guide, integration.
- **562+** tests passing (full suite).

---

## [Wave 16A09] — Batch Ops + Explore + Suggest + Template — 2026-04-17

### Added

- **template:** — schema-driven input frame per node type (`required` / `optional`), plus `batch_format` hint.
- **explore:** — best match + incident edges (skips `discovered_in`) + `also_found` close matches.
- **suggest:** — `suggest_related()` keyword overlap; excludes Session/Document by default.
- **batch** — unified executor (max 50 ops): `create`, `update`, `replace`, `delete`, `retype`, `merge`, `edge+`, `edge-`, `edge~`, `edge*` (see `gobp/mcp/batch_parser.py`).
- **remove_edge_from_disk()** in mutator — removes a triple from any `.gobp/edges/**/*.yaml` bundle.
- **scripts/wave16a09_smoke.py** — smoke check for template, batch, explore, suggest, dedupe.

### Changed

- **parse_query** — special-case `batch` so colons inside `ops='…'` do not split the action.
- **parse_query** — multi-word `suggest:` / `explore:` queries join bare tokens into one `query`.

### Tests

- `tests/test_wave16a09.py` — template, explore, suggest, batch parse/execute, merge, protocol.
- **548** tests passing (full suite).

---

## [Wave 16A08] — Proper Text Normalization — 2026-04-17

### Changed
- **normalize_text()** upgraded from unicodedata to unidecode
  - 'đăng nhập' → 'dang nhap' (consistent romanization)
  - 'dang nhap' == 'đăng nhập' in search ✓
  - Handles all Vietnamese diacritics correctly
  - Graceful fallback if unidecode not installed

- **Session strict exclusion** in find()
  - find: session → no Session nodes (keyword ≠ type)
  - find:Session → Session nodes only (explicit type filter)
  - include_sessions=true to opt-in

### Added
- unidecode to requirements

### Total: 520+ tests

---

## [Wave 16A07] — Search Quality + Edge Types + Duplicate Detection — 2026-04-17

### Added

- **gobp/core/search.py** — Vietnamese-aware search module
  - normalize_text(): strips diacritics ("mi hốt" == "mihot" == "Mi Hot")
  - search_score(): relevance ranking (exact name=100, contains=60, desc=20); space-insensitive name match for queries like "mihot"
  - search_nodes(): type filter by field, Session excluded by default
  - find_similar_nodes(): duplicate detection helper

- **depends_on edge type** — Engine/Flow requires another node
- **tested_by edge type** — Flow/Engine validated by TestCase
- **covers edge type** — extended (many-to-many) TestCase covers Flow/Engine/Feature

- **Duplicate detection** — warning when creating a node with similar name

### Changed

- find() in read.py: uses search.py instead of substring-only match
  - find: mihot → finds "Mi Hốt Standard Online" ✓
  - find:Engine → only Engine nodes (exact type filter) ✓
  - Session nodes excluded by default ✓
  - Results sorted by relevance score ✓
- dispatcher find: type prefix (e.g. find:Engine) sets type filter, not search text

### Tests

- `tests/test_wave16a07.py` — normalization, ranking, edges, duplicates, find sessions
- **507** tests passing (full suite).

---

## [Wave 16A06] — Delete + Retype nodes — 2026-04-17

### Added

- **delete: action** — remove a node file and strip edges that reference it from edge YAML lists.
  - Protected types: **Session**, **Document** cannot be deleted.
  - Usage: `delete: {node_id} session_id='x'`

- **retype: action** — change node type by hard-deleting the old node and creating a new node with a new ID in the correct group, then re-adding edges.
  - Usage: `retype: id='{id}' new_type='Engine' session_id='x'`

### Why

- Nodes created with the wrong type keep a wrong group segment in the ID; retype fixes tier/priority without manual file surgery.

### Tests

- `tests/test_wave16a06.py` — delete, protected session, retype group change, edge migration, PROTOCOL_GUIDE.
- **486** tests passing (full suite).

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

