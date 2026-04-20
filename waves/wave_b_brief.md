# Wave B — Fix test suite for PostgreSQL v3 (consolidated)

**Status:** In progress — **Tasks 1, 2, 8 (partial) done** in repo (`tests/fixtures/db_v3.py`, `test_db_cache.py` v3 path, markers, `TESTING.md`). Tasks 3–7 (dispatcher, wave13/16a01/17a03, performance, integration) remain.

**Goal:** When `GOBP_DB_URL` points at a PostgreSQL database with **schema v3**, `pytest tests/` should pass without v2-only assumptions.

## Errata — v3 schema (authoritative: `gobp/core/db.py` `create_schema_v3`)

The `nodes` table includes: `id`, `name`, `group_path`, `desc_l1`, `desc_l2`, `desc_full`, `code`, `severity`, `updated_at`.  
There is **no** `type` or `node_type` column on the v3 `nodes` table.

The `edges` table includes: `from_id`, `to_id`, `reason`, `code`, `created_at`, `PRIMARY KEY (from_id, to_id)`.  
There is **no** `edge_type` / `type` column on v3 edges (relationship type is carried in `reason` / elsewhere as per product).

Legacy helpers `init_schema`, `upsert_node`, `upsert_edge`, `query_nodes_by_type`, etc. target the **older** PG layout and must not be used against a v3 database.

**Danger:** `rebuild_index()` runs `TRUNCATE` on `nodes` / `edges`. Destructive tests must be gated (e.g. `GOBP_TEST_ALLOW_TRUNCATE=1`) or run only against a disposable database.

## Tasks (8)

1. **Fixtures** — `tests/fixtures/db_v3.py`: skip-if-not-v3 helpers, minimal node dicts for `upsert_node_v3`, safe id prefixes, cleanup helpers.
2. **`test_db_cache.py`** — Keep pure cache tests always-on; replace legacy PG tests with v3 API tests (`ensure_v3_connection`, `upsert_node_v3`, `upsert_edge_v3`, …); gate any `rebuild_index` test.
3. **`test_find.py`** — N/A in repo; equivalent failures live under dispatcher / wave tests — track as follow-up tasks.
4. **`test_dispatcher.py`** — Align expectations with v3 `find` / `get` payloads when DB is active (follow-up).
5. **Wave tests** — `test_wave13.py`, `test_wave16a01.py`, `test_wave17a03.py` (follow-up).
6. **`test_performance.py`** — (follow-up).
7. **`test_integration.py`** — (follow-up).
8. **Markers + docs** — `postgres_v3`, `file_only` in `pyproject.toml`; `TESTING.md`.

## Acceptance (incremental)

- `pytest tests/test_db_cache.py -v` passes with or without `GOBP_DB_URL` (cache always; v3 tests skip if no v3).
- Full suite 808/0 is the **end state** after follow-up tasks 3–7.

## Commits (squash or per-task as CEO prefers)

Use prefix `Wave B Task N:` as in original brief.
