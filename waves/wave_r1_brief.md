# Wave R1 — Storage & legacy cleanup

**Status:** COMPLETE (2026-04-20)  
**Goal:** Remove legacy PostgreSQL layout helpers from `gobp.core.db`, add typing, stop automatic DB init from `GraphIndex.load_from_disk`; keep v3 + file-only paths working.

## Context

After PostgreSQL v3 (`create_schema_v3`), `db.py` still contained an older **wide-row** layout (`init_schema`, `upsert_node`, `query_nodes_fts`, …) used only by legacy call paths. Runtime inventory showed **`gobp/core/fs_mutator.py`** (not only `graph.py`) called `init_schema` / `upsert_node` / `delete_node` / `upsert_edge` — those were removed and replaced with existing `maybe_upsert_*` / new `maybe_delete_node_v3` in `gobp/mcp/pg_sync.py`.

## Tasks (6)

| # | Deliverable |
|---|-------------|
| 1 | Inventory: confirm callers (`graph.py`, `fs_mutator.py`); no stray `init_schema` after merge. |
| 2 | `gobp/core/db.py`: `TYPE_CHECKING` + `PgConnection` aliases for v3 APIs; no runtime `psycopg2` import for typing. |
| 3 | Remove `DB_FILENAME`, `SCHEMA_VERSION`, `init_schema`, `_node_to_row`, `upsert_node`, `delete_node`, `upsert_edge`, `delete_edges_for_node`, `query_*` legacy helpers; keep `index_exists`, `rebuild_index`, all `*_v3` functions. Update **`fs_mutator.py`** + **`pg_sync.py`** accordingly. |
| 4 | `gobp/core/graph.py`: remove `load_from_disk` try/except that called `init_schema` / `index_exists` / `rebuild_index`; drop unused `db` import. |
| 5 | `tests/test_db_cache.py`: no v2-only tests remained — **empty commit** recorded. |
| 6 | `docs/ARCHITECTURE.md` (Tier 1 fallback text; §9.0 / §9.1), `CHANGELOG.md` Wave R1 entry. |

## Tests

- After Tasks 2–5: `pytest tests/test_db_cache.py -v`
- End state: `pytest tests/ -q` (fast suite)

## Commits (reference)

- `feat(db): add PostgreSQL typing with TYPE_CHECKING — Wave R1 Task 2`
- `refactor(db): remove SQLite v2 legacy functions — Wave R1 Task 3` *(includes `fs_mutator` + `pg_sync`)*
- `refactor(graph): remove SQLite v2 init from load_from_disk — Wave R1 Task 4`
- `test: confirm no SQLite v2 tests in test_db_cache — Wave R1 Task 5` *(empty)*
- `docs: document SQLite v2 removal in ARCHITECTURE + CHANGELOG — Wave R1 Task 6`

## Post-check

```text
rg "init_schema\(" --glob "*.py"   # expect 0 in code (CHANGELOG may mention text)
```

## Notes

- Naming in older docs said “SQLite”; legacy code was **PostgreSQL** with an older column layout, not `.gobp/index.sqlite` on disk.
- Automatic PG mirror on `load_from_disk` is gone; use CLI / `rebuild_index` when a disposable v3 DB must be refreshed from files.
