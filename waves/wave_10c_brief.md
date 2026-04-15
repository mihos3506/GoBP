# WAVE 10C BRIEF — POSTGRESQL MIGRATION

**Wave:** 10C
**Title:** Migrate SQLite → PostgreSQL persistent index
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 8 atomic tasks
**Estimated effort:** 4-5 hours

---

## CONTEXT

GoBP currently uses SQLite as derived index. MIHOS is a social network — projected 10,000-15,000+ nodes over lifetime. SQLite will hit performance limits at scale. PostgreSQL provides:

- Unlimited scale
- Better concurrent writes (Cursor + Claude CLI simultaneously)
- pgvector support (semantic search, Wave 9B)
- Cloud-ready (team scale)
- Better FTS with tsvector + GIN indexes

**Architecture unchanged:** File-first principle preserved. Markdown files remain source of truth. PostgreSQL replaces SQLite as derived index only. Migration = drop SQLite → rebuild into PostgreSQL.

**Connection:** Read from `GOBP_DB_URL` environment variable.

```
Format: postgresql://postgres:Hieu%408283%40@localhost/gobp
Decode: urllib.parse.unquote() for password with special chars
```

**Per-project databases:**
```
GoBP project:   GOBP_DB_URL=postgresql://...@localhost/gobp
MIHOS project:  GOBP_MIHOS_DB_URL=postgresql://...@localhost/gobp_mihos
```

**PostgreSQL schema (equivalent to SQLite):**

```sql
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    status TEXT DEFAULT '',
    topic TEXT DEFAULT '',
    subject TEXT DEFAULT '',
    group_field TEXT DEFAULT '',
    scope TEXT DEFAULT '',
    priority TEXT DEFAULT 'medium',
    created TEXT DEFAULT '',
    updated TEXT DEFAULT '',
    fts_content TEXT DEFAULT '',
    fts_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(id,'') || ' ' ||
                               coalesce(name,'') || ' ' ||
                               coalesce(topic,'') || ' ' ||
                               coalesce(subject,'') || ' ' ||
                               coalesce(fts_content,''))
    ) STORED
);

CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status);
CREATE INDEX IF NOT EXISTS idx_nodes_topic ON nodes(topic);
CREATE INDEX IF NOT EXISTS idx_nodes_priority ON nodes(priority);
CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id);
CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id);
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
CREATE INDEX IF NOT EXISTS idx_nodes_fts ON nodes USING GIN(fts_vector);
```

**Key differences from SQLite:**
- FTS: SQLite FTS5 → PostgreSQL tsvector + GIN index
- FTS query: `MATCH ?` → `fts_vector @@ plainto_tsquery('english', ?)`
- Fallback: substring LIKE query unchanged
- Connection: file path → DSN URL
- Parameterization: `?` → `%s`

**In scope:**
- `gobp/core/db.py` — rewrite for PostgreSQL
- `gobp/core/db_config.py` — new: connection config reader
- `.gitignore` — add `.env`
- `requirements.txt` — add psycopg2-binary
- `tests/test_db_cache.py` — update for PostgreSQL
- `docs/INSTALL.md` — PostgreSQL setup guide

**NOT in scope:**
- pgvector (Wave 9B)
- Cloud deployment
- Multi-user auth
- Any changes to tool functions or dispatcher

---

## CURSOR EXECUTION RULES

### R1 — Sequential execution
### R2 — Discovery before creation
### R3 — 1 task = 1 commit
### R4 — Docs supreme authority
### R5 — Document disagreement = STOP
### R6 — 3 retries = STOP
### R7 — No scope creep
### R8 — Brief code authoritative
### R9 — All 253 existing tests must pass after every task

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 253 tests passing

# Verify PostgreSQL connection
D:/GoBP/venv/Scripts/python.exe -c "
import os, psycopg2
from urllib.parse import urlparse, unquote
url = os.environ.get('GOBP_DB_URL', '')
assert url, 'GOBP_DB_URL not set'
r = urlparse(url)
conn = psycopg2.connect(host=r.hostname, dbname=r.path[1:], user=r.username, password=unquote(r.password))
print('PostgreSQL connected:', conn.server_version)
conn.close()
"
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/core/db.py` | Current SQLite implementation to replace |
| 3 | `gobp/core/graph.py` | Uses db module |
| 4 | `gobp/core/mutator.py` | Uses db module |
| 5 | `gobp/mcp/server.py` | Uses db module |
| 6 | `tests/test_db_cache.py` | Tests to update |
| 7 | `waves/wave_10c_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Create gobp/core/db_config.py

**Goal:** Centralized database connection config. Reads from env var. Falls back to SQLite if no PostgreSQL URL.

**File to create:** `gobp/core/db_config.py`

```python
"""GoBP database connection configuration.

Reads GOBP_DB_URL environment variable for PostgreSQL connection.
Falls back to SQLite if not set.

Environment variable format:
    GOBP_DB_URL=postgresql://user:password@host/dbname

For passwords with special characters, URL-encode them:
    @ → %40
    Example: postgresql://postgres:Hieu%408283%40@localhost/gobp

Per-project configuration:
    GoBP project:   GOBP_DB_URL
    MIHOS project:  GOBP_MIHOS_DB_URL (set via GOBP_PROJECT_ROOT detection)
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Any


def get_db_url(gobp_root: Path | None = None) -> str | None:
    """Get PostgreSQL database URL from environment.
    
    Detection order:
    1. GOBP_DB_URL env var (explicit override)
    2. Auto-detect from GOBP_PROJECT_ROOT path
    3. None (fall back to SQLite)
    
    Args:
        gobp_root: Project root path for auto-detection.
    
    Returns:
        PostgreSQL URL string or None if not configured.
    """
    # Explicit override always wins
    url = os.environ.get("GOBP_DB_URL")
    if url:
        return url
    
    # Auto-detect from project root path
    if gobp_root is not None:
        root_str = str(gobp_root).lower()
        if "mihos" in root_str:
            url = os.environ.get("GOBP_MIHOS_DB_URL")
            if url:
                return url
    
    return None


def parse_db_url(url: str) -> dict[str, Any]:
    """Parse PostgreSQL URL into psycopg2 connection kwargs.
    
    Handles URL-encoded special characters in password.
    
    Args:
        url: PostgreSQL connection URL.
    
    Returns:
        Dict of kwargs for psycopg2.connect().
    
    Raises:
        ValueError: If URL is not a valid PostgreSQL URL.
    """
    if not url.startswith("postgresql://") and not url.startswith("postgres://"):
        raise ValueError(f"Not a PostgreSQL URL: {url}")
    
    r = urlparse(url)
    
    kwargs: dict[str, Any] = {
        "host": r.hostname or "localhost",
        "port": r.port or 5432,
        "dbname": r.path.lstrip("/") if r.path else "gobp",
        "user": r.username or "postgres",
    }
    
    if r.password:
        kwargs["password"] = unquote(r.password)
    
    return kwargs


def is_postgres_available(gobp_root: Path | None = None) -> bool:
    """Check if PostgreSQL is configured and reachable.
    
    Returns:
        True if PostgreSQL URL is set and connection succeeds.
    """
    url = get_db_url(gobp_root)
    if not url:
        return False
    
    try:
        import psycopg2
        kwargs = parse_db_url(url)
        conn = psycopg2.connect(**kwargs)
        conn.close()
        return True
    except Exception:
        return False
```

**Acceptance criteria:**
- `gobp/core/db_config.py` created
- `get_db_url()` reads GOBP_DB_URL env var
- Auto-detects MIHOS project from path
- `parse_db_url()` handles `%40` encoded passwords
- `is_postgres_available()` returns True/False without raising

**Commit message:**
```
Wave 10C Task 1: create gobp/core/db_config.py

- get_db_url(): reads GOBP_DB_URL, auto-detects MIHOS project
- parse_db_url(): handles URL-encoded passwords (%40 etc)
- is_postgres_available(): safe connection check
- Foundation for PostgreSQL-aware db.py
```

---

## TASK 2 — Rewrite gobp/core/db.py for PostgreSQL

**Goal:** Replace SQLite implementation with PostgreSQL. Maintain identical public API.

**File to modify:** `gobp/core/db.py`

**Re-read current `gobp/core/db.py` in full before editing.**

**Replace entire file with:**

```python
"""GoBP persistent index — PostgreSQL backend.

Replaces SQLite with PostgreSQL for scale and concurrent access.
Public API identical to SQLite version — callers unchanged.

Connection: reads GOBP_DB_URL environment variable.
Fallback: if PostgreSQL unavailable, operations are no-ops (in-memory index still works).

Schema:
  nodes  — searchable node metadata with tsvector FTS
  edges  — edge relationships with indexes
  meta   — key-value metadata
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("gobp.db")

DB_FILENAME = "index.db"  # kept for gitignore compatibility
SCHEMA_VERSION = 2  # v2 = PostgreSQL


def _get_conn(gobp_root: Path):
    """Get PostgreSQL connection for project root.
    
    Returns psycopg2 connection or None if PostgreSQL not available.
    """
    try:
        import psycopg2
        from gobp.core.db_config import get_db_url, parse_db_url
        url = get_db_url(gobp_root)
        if not url:
            return None
        kwargs = parse_db_url(url)
        conn = psycopg2.connect(**kwargs)
        return conn
    except Exception as e:
        logger.debug(f"PostgreSQL connection failed: {e}")
        return None


def init_schema(gobp_root: Path) -> None:
    """Create PostgreSQL schema if not exists. Idempotent."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return
    
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS nodes (
                        id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        name TEXT NOT NULL DEFAULT '',
                        status TEXT DEFAULT '',
                        topic TEXT DEFAULT '',
                        subject TEXT DEFAULT '',
                        group_field TEXT DEFAULT '',
                        scope TEXT DEFAULT '',
                        priority TEXT DEFAULT 'medium',
                        created TEXT DEFAULT '',
                        updated TEXT DEFAULT '',
                        fts_content TEXT DEFAULT '',
                        fts_vector tsvector GENERATED ALWAYS AS (
                            to_tsvector('english',
                                coalesce(id,'') || ' ' ||
                                coalesce(name,'') || ' ' ||
                                coalesce(topic,'') || ' ' ||
                                coalesce(subject,'') || ' ' ||
                                coalesce(fts_content,''))
                        ) STORED
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS edges (
                        id TEXT PRIMARY KEY,
                        from_id TEXT NOT NULL,
                        to_id TEXT NOT NULL,
                        type TEXT NOT NULL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS meta (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                # Indexes
                cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_topic ON nodes(topic)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_priority ON nodes(priority)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_nodes_fts ON nodes USING GIN(fts_vector)")
                
                cur.execute(
                    "INSERT INTO meta (key, value) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    ("schema_version", str(SCHEMA_VERSION))
                )
    finally:
        conn.close()


def _node_to_row(node: dict[str, Any]) -> dict[str, str]:
    """Convert node dict to DB row dict."""
    fts_parts = [
        node.get("id", ""),
        node.get("name", ""),
        node.get("topic", ""),
        node.get("subject", ""),
        node.get("description", ""),
        node.get("definition", ""),
        node.get("usage_guide", ""),
        node.get("group", ""),
    ]
    fts_content = " ".join(str(p) for p in fts_parts if p)
    
    return {
        "id": node.get("id", ""),
        "type": node.get("type", ""),
        "name": node.get("name", ""),
        "status": node.get("status", ""),
        "topic": node.get("topic", ""),
        "subject": node.get("subject", ""),
        "group_field": node.get("group", ""),
        "scope": node.get("scope", ""),
        "priority": node.get("priority", "medium"),
        "created": node.get("created", ""),
        "updated": node.get("updated", ""),
        "fts_content": fts_content,
    }


def upsert_node(gobp_root: Path, node: dict[str, Any]) -> None:
    """Insert or replace a node in the index."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return
    
    row = _node_to_row(node)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO nodes
                        (id, type, name, status, topic, subject, group_field,
                         scope, priority, created, updated, fts_content)
                    VALUES
                        (%(id)s, %(type)s, %(name)s, %(status)s, %(topic)s,
                         %(subject)s, %(group_field)s, %(scope)s, %(priority)s,
                         %(created)s, %(updated)s, %(fts_content)s)
                    ON CONFLICT (id) DO UPDATE SET
                        type=EXCLUDED.type, name=EXCLUDED.name,
                        status=EXCLUDED.status, topic=EXCLUDED.topic,
                        subject=EXCLUDED.subject, group_field=EXCLUDED.group_field,
                        scope=EXCLUDED.scope, priority=EXCLUDED.priority,
                        created=EXCLUDED.created, updated=EXCLUDED.updated,
                        fts_content=EXCLUDED.fts_content
                """, row)
    finally:
        conn.close()


def delete_node(gobp_root: Path, node_id: str) -> None:
    """Remove a node from the index."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM nodes WHERE id = %s", (node_id,))
    finally:
        conn.close()


def upsert_edge(gobp_root: Path, edge: dict[str, Any]) -> None:
    """Insert or replace an edge in the index."""
    from_id = edge.get("from", "")
    to_id = edge.get("to", "")
    edge_type = edge.get("type", "")
    edge_id = f"{from_id}__{edge_type}__{to_id}"
    
    conn = _get_conn(gobp_root)
    if conn is None:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO edges (id, from_id, to_id, type)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        from_id=EXCLUDED.from_id,
                        to_id=EXCLUDED.to_id,
                        type=EXCLUDED.type
                """, (edge_id, from_id, to_id, edge_type))
    finally:
        conn.close()


def delete_edges_for_node(gobp_root: Path, node_id: str) -> None:
    """Remove all edges where from_id or to_id matches node_id."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM edges WHERE from_id = %s OR to_id = %s",
                    (node_id, node_id)
                )
    finally:
        conn.close()


def query_nodes_by_type(gobp_root: Path, node_type: str) -> list[str]:
    """Return list of node IDs for a given type."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM nodes WHERE type = %s", (node_type,))
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def query_nodes_fts(
    gobp_root: Path,
    query: str,
    type_filter: str | None = None,
    limit: int = 20
) -> list[str]:
    """Full-text search nodes using PostgreSQL tsvector. Returns node IDs."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return []
    try:
        with conn.cursor() as cur:
            if type_filter:
                cur.execute("""
                    SELECT id FROM nodes
                    WHERE fts_vector @@ plainto_tsquery('english', %s)
                    AND type = %s
                    LIMIT %s
                """, (query, type_filter, limit))
            else:
                cur.execute("""
                    SELECT id FROM nodes
                    WHERE fts_vector @@ plainto_tsquery('english', %s)
                    LIMIT %s
                """, (query, limit))
            return [row[0] for row in cur.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()


def query_nodes_substring(
    gobp_root: Path,
    query: str,
    type_filter: str | None = None,
    limit: int = 20
) -> list[str]:
    """Substring search nodes (fallback). Returns node IDs."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return []
    try:
        q = f"%{query}%"
        with conn.cursor() as cur:
            if type_filter:
                cur.execute("""
                    SELECT id FROM nodes
                    WHERE (id ILIKE %s OR name ILIKE %s OR fts_content ILIKE %s)
                    AND type = %s
                    LIMIT %s
                """, (q, q, q, type_filter, limit))
            else:
                cur.execute("""
                    SELECT id FROM nodes
                    WHERE id ILIKE %s OR name ILIKE %s OR fts_content ILIKE %s
                    LIMIT %s
                """, (q, q, q, limit))
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def query_edges_from(gobp_root: Path, node_id: str) -> list[dict[str, str]]:
    """Get all edges where from_id = node_id."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT from_id, to_id, type FROM edges WHERE from_id = %s",
                (node_id,)
            )
            return [{"from": r[0], "to": r[1], "type": r[2]} for r in cur.fetchall()]
    finally:
        conn.close()


def query_edges_to(gobp_root: Path, node_id: str) -> list[dict[str, str]]:
    """Get all edges where to_id = node_id."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT from_id, to_id, type FROM edges WHERE to_id = %s",
                (node_id,)
            )
            return [{"from": r[0], "to": r[1], "type": r[2]} for r in cur.fetchall()]
    finally:
        conn.close()


def index_exists(gobp_root: Path) -> bool:
    """Return True if PostgreSQL schema exists and has nodes table."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'nodes'
                )
            """)
            return cur.fetchone()[0]
    except Exception:
        return False
    finally:
        conn.close()


def rebuild_index(gobp_root: Path, graph_index: Any) -> dict[str, Any]:
    """Rebuild PostgreSQL index from scratch using GraphIndex data."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return {
            "ok": False,
            "message": "PostgreSQL not available — set GOBP_DB_URL env var",
            "nodes_indexed": 0,
            "edges_indexed": 0,
        }
    
    try:
        with conn:
            with conn.cursor() as cur:
                # Clear existing data
                cur.execute("TRUNCATE TABLE nodes, edges RESTART IDENTITY CASCADE")
                
                # Insert all nodes
                nodes_indexed = 0
                for node in graph_index.all_nodes():
                    row = _node_to_row(node)
                    cur.execute("""
                        INSERT INTO nodes
                            (id, type, name, status, topic, subject, group_field,
                             scope, priority, created, updated, fts_content)
                        VALUES
                            (%(id)s, %(type)s, %(name)s, %(status)s, %(topic)s,
                             %(subject)s, %(group_field)s, %(scope)s, %(priority)s,
                             %(created)s, %(updated)s, %(fts_content)s)
                        ON CONFLICT (id) DO NOTHING
                    """, row)
                    nodes_indexed += 1
                
                # Insert all edges
                edges_indexed = 0
                for edge in graph_index.all_edges():
                    from_id = edge.get("from", "")
                    to_id = edge.get("to", "")
                    edge_type = edge.get("type", "")
                    edge_id = f"{from_id}__{edge_type}__{to_id}"
                    cur.execute("""
                        INSERT INTO edges (id, from_id, to_id, type)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (edge_id, from_id, to_id, edge_type))
                    edges_indexed += 1
        
        return {
            "ok": True,
            "nodes_indexed": nodes_indexed,
            "edges_indexed": edges_indexed,
            "message": f"Index rebuilt: {nodes_indexed} nodes, {edges_indexed} edges",
        }
    except Exception as e:
        return {
            "ok": False,
            "message": f"Rebuild failed: {e}",
            "nodes_indexed": 0,
            "edges_indexed": 0,
        }
    finally:
        conn.close()
```

**Acceptance criteria:**
- Public API identical to SQLite version
- All functions return empty/False gracefully if PostgreSQL unavailable
- No exceptions propagate to callers
- `?` placeholders replaced with `%s`
- `LIKE` → `ILIKE` (case-insensitive)
- FTS uses tsvector + plainto_tsquery
- `ON CONFLICT DO UPDATE` for upsert

**Commit message:**
```
Wave 10C Task 2: rewrite db.py for PostgreSQL

- _get_conn(): reads GOBP_DB_URL via db_config, returns None if unavailable
- init_schema(): PostgreSQL tables + GIN index for FTS
- All CRUD functions: ? → %s, LIKE → ILIKE
- FTS: SQLite FTS5 → tsvector + plainto_tsquery
- Graceful fallback: all functions return empty/False if no PostgreSQL
- rebuild_index(): TRUNCATE + re-insert all nodes/edges
```

---

## TASK 3 — Update requirements.txt + .gitignore

**Goal:** Document psycopg2 dependency. Ensure .env gitignored.

**File to modify:** `requirements.txt`

Add:
```
psycopg2-binary>=2.9.0
```

**File to modify:** `.gitignore`

Add after existing entries:
```
# Database
.gobp/index.db
.gobp/archive/

# Environment
.env
.env.local
```

**Commit message:**
```
Wave 10C Task 3: add psycopg2-binary to requirements + gitignore .env

- requirements.txt: psycopg2-binary>=2.9.0
- .gitignore: .env, .env.local (protect DB credentials)
```

---

## TASK 4 — Verify PostgreSQL integration with existing code

**Goal:** Confirm graph.py, mutator.py, server.py work unchanged with new db.py.

```powershell
# Test db_config reads env var
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.db_config import get_db_url, is_postgres_available
from pathlib import Path
url = get_db_url(Path('D:/GoBP'))
print('URL found:', bool(url))
print('PostgreSQL available:', is_postgres_available(Path('D:/GoBP')))
"

# Test init_schema creates tables
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core import db
from pathlib import Path
root = Path('D:/GoBP')
db.init_schema(root)
print('Schema created OK')
print('Index exists:', db.index_exists(root))
"

# Test upsert and query
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core import db
from pathlib import Path
root = Path('D:/GoBP')
db.init_schema(root)
node = {'id': 'node:test_pg', 'type': 'Node', 'name': 'PostgreSQL Test',
        'status': 'ACTIVE', 'created': '2026-04-15', 'updated': '2026-04-15'}
db.upsert_node(root, node)
ids = db.query_nodes_by_type(root, 'Node')
print('Node IDs:', ids[:3])
assert 'node:test_pg' in ids
print('Upsert + query OK')
"

# Full test suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 253 tests passing
```

**Commit message:**
```
Wave 10C Task 4: verify PostgreSQL integration — all existing code unchanged

- db_config reads GOBP_DB_URL correctly
- init_schema creates tables + GIN index
- upsert_node + query_nodes_by_type work
- 253 existing tests still passing
```

---

## TASK 5 — Update tests/test_db_cache.py for PostgreSQL

**Goal:** DB tests use PostgreSQL instead of SQLite path checks.

**File to modify:** `tests/test_db_cache.py`

**Re-read `tests/test_db_cache.py` in full.**

**Changes needed:**

1. Remove any `index.db` file existence checks
2. Add PostgreSQL availability check — skip DB tests if PostgreSQL not available:

```python
import pytest
from gobp.core.db_config import is_postgres_available
from pathlib import Path

# Skip all DB tests if PostgreSQL not configured
pytestmark = pytest.mark.skipif(
    not is_postgres_available(Path(".")),
    reason="PostgreSQL not available (GOBP_DB_URL not set)"
)
```

3. Update `test_db_init_schema_idempotent` — remove SQLite file check:

```python
def test_db_init_schema_idempotent(gobp_root: Path):
    """init_schema can be called twice without error."""
    db_module.init_schema(gobp_root)
    db_module.init_schema(gobp_root)
    assert db_module.index_exists(gobp_root)
```

4. Keep all other tests unchanged — they use public API which is identical.

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_db_cache.py -v
# Expected: all passing (or skipped if GOBP_DB_URL not set in test env)
```

**Commit message:**
```
Wave 10C Task 5: update test_db_cache.py for PostgreSQL

- Add pytestmark skipif when PostgreSQL not available
- Remove SQLite index.db file existence checks
- All other DB tests unchanged (public API identical)
```

---

## TASK 6 — Update gobp validate --reindex for PostgreSQL

**Goal:** `gobp validate --reindex` works with PostgreSQL.

**File to modify:** `gobp/cli/commands.py`

**Re-read `cmd_validate()` in full.**

Find `--reindex` block. Update to use PostgreSQL-aware rebuild:

```python
    if args.reindex:
        from gobp.core.db_config import is_postgres_available
        if is_postgres_available(root):
            print("Rebuilding PostgreSQL index...")
        else:
            print("Warning: PostgreSQL not available. Index rebuild skipped.")
            print("Set GOBP_DB_URL environment variable to enable PostgreSQL.")
```

**Acceptance criteria:**
- `gobp validate --reindex` shows PostgreSQL status
- Clear message if PostgreSQL not configured

**Commit message:**
```
Wave 10C Task 6: update validate --reindex for PostgreSQL

- Shows PostgreSQL availability status
- Clear warning if GOBP_DB_URL not set
```

---

## TASK 7 — Update docs/INSTALL.md with PostgreSQL setup

**Goal:** Document PostgreSQL setup for new developers.

**File to modify:** `docs/INSTALL.md`

**Add new section** after existing install steps:

```markdown
## PostgreSQL Setup (Recommended for scale)

GoBP uses PostgreSQL as persistent index for projects with 1,000+ nodes.

### Install PostgreSQL

Download from https://www.postgresql.org/download/windows/
Install version 18.x or later.

### Create databases

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE gobp;"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE gobp_mihos;"
```

### Configure environment

Set environment variables (passwords with @ must use %40):

```powershell
[System.Environment]::SetEnvironmentVariable("GOBP_DB_URL", "postgresql://postgres:YOUR%40PASSWORD@localhost/gobp", "User")
[System.Environment]::SetEnvironmentVariable("GOBP_MIHOS_DB_URL", "postgresql://postgres:YOUR%40PASSWORD@localhost/gobp_mihos", "User")
```

Restart PowerShell after setting variables.

### Install Python driver

```powershell
pip install psycopg2-binary
```

### Verify

```powershell
python -m gobp.cli validate --reindex
```

### Note

If GOBP_DB_URL is not set, GoBP falls back to in-memory index (no persistence between restarts). PostgreSQL is optional but recommended for MIHOS-scale projects.
```

**Commit message:**
```
Wave 10C Task 7: update INSTALL.md with PostgreSQL setup guide

- PostgreSQL install steps for Windows
- Database creation commands
- Environment variable configuration
- Password encoding for special characters
- Fallback behavior documented
```

---

## TASK 8 — Full suite + CHANGELOG + end-to-end test

**Goal:** All tests pass. CHANGELOG updated. End-to-end verify.

```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 253+ tests passing

# End-to-end: init project → load → rebuild PostgreSQL index
D:/GoBP/venv/Scripts/python.exe -c "
import tempfile, shutil
from pathlib import Path
from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.core import db

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    init_project(root, project_name='test_pg')
    index = GraphIndex.load_from_disk(root)
    print(f'Loaded: {len(index)} nodes')
    
    result = db.rebuild_index(root, index)
    print(f'Rebuild: {result}')
    
    ids = db.query_nodes_by_type(root, 'TestKind')
    print(f'TestKind nodes in PG: {len(ids)}')
    assert len(ids) == 16, f'Expected 16, got {len(ids)}'
    print('End-to-end OK')
"
```

**Update CHANGELOG.md:**

```markdown
## [Wave 10C] — PostgreSQL Migration — 2026-04-15

### Why
MIHOS is a social network — projected 10,000-15,000+ nodes. SQLite hits
performance limits at scale. PostgreSQL provides unlimited scale, better
concurrent writes, and pgvector support for semantic search (Wave 9B).

### Changed
- `gobp/core/db.py` — rewritten for PostgreSQL (identical public API)
- `gobp/core/db_config.py` — new: connection config from GOBP_DB_URL env var
- `gobp/core/mutator.py` — unchanged (uses db.py public API)
- `gobp/core/graph.py` — unchanged (uses db.py public API)
- `tests/test_db_cache.py` — skip marker when PostgreSQL not available
- `requirements.txt` — psycopg2-binary>=2.9.0
- `.gitignore` — .env files
- `docs/INSTALL.md` — PostgreSQL setup guide

### Architecture
File-first principle preserved. Markdown files remain source of truth.
PostgreSQL replaces SQLite as derived index only.

### Fallback
If GOBP_DB_URL not set → all db operations are no-ops.
In-memory GraphIndex still works for all queries.

### Connection
```
GOBP_DB_URL=postgresql://postgres:password@localhost/gobp
GOBP_MIHOS_DB_URL=postgresql://postgres:password@localhost/gobp_mihos
```
Passwords with @ must be URL-encoded: @ → %40

### Total after wave: 1 MCP tool, 253+ tests passing
```

**Commit message:**
```
Wave 10C Task 8: full suite green + CHANGELOG updated

- 253+ tests passing
- End-to-end PostgreSQL verify passed
- CHANGELOG: Wave 10C entry
```

---

# POST-WAVE VERIFICATION

```powershell
# All tests
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

# PostgreSQL has 17 seed nodes after gobp init
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core import db
from pathlib import Path
ids = db.query_nodes_by_type(Path('D:/GoBP'), 'TestKind')
print(f'TestKind in PostgreSQL: {len(ids)}')
"

# Git log
git log --oneline | Select-Object -First 10
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief vào repo

```powershell
cd D:\GoBP
# Save wave_10c_brief.md to D:\GoBP\waves\wave_10c_brief.md

git add waves/wave_10c_brief.md
git commit -m "Add Wave 10C Brief — PostgreSQL migration"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_10c_brief.md first.
Also read gobp/core/db.py, gobp/core/graph.py, gobp/core/mutator.py,
gobp/mcp/server.py, tests/test_db_cache.py, docs/INSTALL.md.

Execute ALL 8 tasks of Wave 10C sequentially.
Rules:
- R9: all 253 existing tests must pass after every task
- PostgreSQL must be available (GOBP_DB_URL env var set)
- Graceful fallback: all db functions return empty/False if no PostgreSQL
- Public API of db.py must remain identical to SQLite version
- 1 task = 1 commit, exact message
- Report full summary after Task 8

Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 10C. Read CLAUDE.md and waves/wave_10c_brief.md.
Also read docs/GoBP_ARCHITECTURE.md, docs/ARCHITECTURE.md, docs/MCP_TOOLS.md.

Critical verification:
- Task 1: db_config.py exists, get_db_url reads env var, parse_db_url handles %40
- Task 2: db.py uses psycopg2, %s placeholders, ILIKE, tsvector FTS, graceful fallback
- Task 3: requirements.txt has psycopg2-binary, .gitignore has .env
- Task 4: PostgreSQL init_schema works, upsert + query work, 253 tests passing
- Task 5: test_db_cache.py has skipif marker, no SQLite file checks
- Task 6: validate --reindex shows PostgreSQL status
- Task 7: INSTALL.md has PostgreSQL section
- Task 8: 253+ tests passing, end-to-end verify passed, CHANGELOG updated

Use venv:
  D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

Expected: 253+ tests passing.

Stop on first failure. Report WAVE 10C AUDIT COMPLETE when done.
```

## 4. Push

```powershell
cd D:\GoBP
git push origin main
```

---

# WHAT COMES NEXT

```
Wave 10C pushed
    ↓
Wave 11A — Lazy query actions
  code: node:x     → code references
  invariants: x    → constraints
  tests: node:x    → linked TestCases
  related: node:x  → neighbor summary
    ↓
Wave 8B — MIHOS re-import (enhanced)
  import: with Document nodes + priority
  edge: for semantic connections
    ↓
Wave 11B — 3D Graph Viewer
  Three.js + 3d-force-graph
  Per-project isolation
  Node: size=priority, color=type
```

---

*Wave 10C Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
