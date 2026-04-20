# GoBP testing

## Modes

### Default (no `GOBP_DB_URL`)

```powershell
cd D:\GoBP
.\venv\Scripts\python.exe -m pytest tests\ -q
```

Most tests use temporary project roots and file-backed `.gobp/` data.

### PostgreSQL schema v3

Point `GOBP_DB_URL` at a database that already has **v3** layout (see `gobp.core.db.create_schema_v3`).

```powershell
$env:GOBP_DB_URL = "postgresql://user:pass@localhost/gobp"
.\venv\Scripts\python.exe -m pytest tests\ -q
```

Tests marked `@pytest.mark.postgres_v3` exercise `upsert_node_v3`, `upsert_edge_v3`, and related APIs. They **skip** automatically if the URL is missing or the schema is not v3.

### Destructive: `rebuild_index`

`rebuild_index` runs `TRUNCATE` on `nodes` and `edges`. The test `test_v3_rebuild_index_from_file_graph` is **skipped** unless:

```powershell
$env:GOBP_TEST_ALLOW_TRUNCATE = "1"
```

Use **only** on a disposable database, never on shared production data.

## Markers

| Marker | Meaning |
|--------|---------|
| `slow` | Long-running or large-graph tests (see `pyproject.toml` default `-m "not slow"`) |
| `postgres_v3` | Needs live PostgreSQL v3 |
| `file_only` | Reserved for tests that must not assume a DB (optional; not all file tests use it) |

## Schema notes (v3)

Authoritative source: `gobp/core/db.py` — `create_schema_v3`.

- `nodes`: `id`, `name`, `group_path`, `desc_l1`, `desc_l2`, `desc_full`, `code`, `severity`, `updated_at`
- `edges`: `from_id`, `to_id`, `reason`, `code`, `created_at` — primary key `(from_id, to_id)`

Legacy helpers `init_schema`, `upsert_node`, `upsert_edge` (v2-style columns) are **not** valid against a v3 database.
