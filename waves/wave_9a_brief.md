# WAVE 9A BRIEF — SQLITE PERSISTENT INDEX + LRU CACHE

**Wave:** 9A
**Title:** SQLite Persistent Index + LRU Cache — Performance at Scale
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 9 atomic tasks
**Estimated effort:** 4-5 hours

---

## CONTEXT

**Performance problem (measured in Wave H):**

| Tool | Actual | Max target | Status |
|---|---|---|---|
| gobp_overview | 460ms | 100ms | 4.6x over |
| node_upsert | 210ms | 200ms | over |
| find, context, decisions_for, etc. | ~60ms | 30-50ms | over |

**Root cause:** Every MCP tool call calls `GraphIndex.load_from_disk()` — reads ALL node .md files and edge .yaml files from disk on every single query. With 30 nodes → 60ms. With 500 nodes → ~1000ms (unusable).

**Fix:** SQLite persistent index + LRU in-memory cache.

```
Before:  Tool call → load_from_disk() → scan all files → query → return
After:   Tool call → LRU cache hit OR SQLite query → return
```

**Architecture (3 layers):**

```
Layer 1: LRU cache (in-memory, TTL 60s)
  gobp_overview, hot nodes — < 1ms on hit

Layer 2: SQLite index (.gobp/index.db)
  All queries — < 10ms even at 100k nodes
  Write-through: mutations update SQLite immediately

Layer 3: Markdown files (.gobp/nodes/, .gobp/edges/)
  Source of truth — unchanged
  SQLite is derived, always rebuildable
```

**SQLite schema:**

```sql
CREATE TABLE nodes (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT,
  topic TEXT,
  subject TEXT,
  group_field TEXT,
  scope TEXT,
  updated TEXT,
  created TEXT,
  fts_content TEXT    -- concatenated searchable text
);

CREATE VIRTUAL TABLE nodes_fts USING fts5(
  id, name, topic, subject, fts_content,
  content='nodes', content_rowid='rowid'
);

CREATE TABLE edges (
  id TEXT PRIMARY KEY,   -- from__type__to
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  type TEXT NOT NULL
);

CREATE INDEX idx_nodes_type ON nodes(type);
CREATE INDEX idx_nodes_status ON nodes(status);
CREATE INDEX idx_nodes_topic ON nodes(topic);
CREATE INDEX idx_edges_from ON edges(from_id);
CREATE INDEX idx_edges_to ON edges(to_id);
CREATE INDEX idx_edges_type ON edges(type);
```

**Key design decisions:**
- `.gobp/index.db` is gitignored (derived, rebuildable)
- History log stays in JSONL files — NOT indexed in SQLite (avoids bloat)
- `GraphIndex` remains the public API — SQLite is internal implementation
- Existing tests must all pass unchanged (transparent upgrade)
- `gobp validate --reindex` rebuilds SQLite from scratch

**In scope:**
- `gobp/core/db.py` — SQLite index manager (build, query, update, rebuild)
- `gobp/core/cache.py` — LRU cache with TTL
- Modify `gobp/core/graph.py` — use SQLite for queries when available
- Modify `gobp/core/mutator.py` — write-through update SQLite after mutations
- Modify `gobp/mcp/server.py` — inject cache layer
- Add `gobp validate --reindex` CLI flag
- `.gitignore` update
- Performance tests must now pass within targets

**NOT in scope:**
- Vector search (Wave 9B)
- Hot/warm/cold tiering (Wave 9C)
- History log indexing
- Multi-project index sharing

---

## CURSOR EXECUTION RULES (READ FIRST — NON-NEGOTIABLE)

### R1 — Sequential execution
Tasks 1 → 9 in order. No skipping.

### R2 — Discovery before creation
Explorer subagent before creating any file.

### R3 — 1 task = 1 commit
Tests pass → commit with exact message from Brief.

### R4 — Docs are supreme authority
Conflict with `docs/MCP_TOOLS.md` → docs win, STOP and report.

### R5 — Document disagreement = STOP
Believe a doc has error → STOP, report, wait.

### R6 — 3 retries = STOP
Test fails 3 times → STOP, report.

### R7 — No scope creep
No vector search, no history indexing, no extra CLI commands.

### R8 — Brief code blocks are authoritative
Disagree → STOP and escalate. Never substitute.

### R9 — Backward compatibility is mandatory
All 200 existing tests must pass after every task. SQLite is internal — public API unchanged.

---

## STOP REPORT FORMAT

```
STOP — Wave 9A Task <N>
Rule triggered: R<N> — <rule name>
Completed so far: Tasks 1–<N-1> (committed)
Current task: Task <N> — <title>
What I was doing: <description>
What went wrong: <exact error>
Current git state:
  Staged: <list>
  Unstaged: <list>
What I need from CEO/CTO: <specific question>
```

---

## AUTHORITATIVE SOURCE

- `gobp/core/graph.py` — current GraphIndex implementation
- `gobp/core/mutator.py` — current mutation functions
- `gobp/mcp/server.py` — current MCP server
- `docs/MCP_TOOLS.md` — tool specs (unchanged)
- `tests/conftest.py` — gobp_root fixture pattern

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # Expected: clean

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 200 tests passing

D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_performance.py -v --durations=10
# Baseline: gobp_overview ~460ms, others ~60ms
```

---

## REQUIRED READING — WAVE START

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Execution rules |
| 2 | `gobp/core/graph.py` | Current GraphIndex — to extend |
| 3 | `gobp/core/mutator.py` | Mutation functions — to add write-through |
| 4 | `gobp/mcp/server.py` | MCP server — to inject cache |
| 5 | `docs/MCP_TOOLS.md` | Tool specs (unchanged) |
| 6 | `tests/conftest.py` | gobp_root fixture pattern |
| 7 | `waves/wave_9a_brief.md` | This file |

**Per-task reading:**

| Task | Must re-read before starting |
|---|---|
| Task 1 (db.py) | `gobp/core/graph.py` (current load_from_disk) |
| Task 2 (cache.py) | `gobp/mcp/server.py` (where cache will be injected) |
| Task 3 (graph.py) | `gobp/core/db.py` just created |
| Task 4 (mutator.py) | `gobp/core/db.py`, `gobp/core/mutator.py` current |
| Task 5 (server.py) | `gobp/core/cache.py`, `gobp/mcp/server.py` current |
| Task 6 (reindex CLI) | `gobp/cli/commands.py`, `gobp/core/db.py` |
| Task 7 (.gitignore) | `.gitignore` current content |
| Tasks 8-9 (tests) | All modules created in Tasks 1-7 |

---

# TASKS

---

## TASK 1 — Create gobp/core/db.py (SQLite index manager)

**Goal:** SQLite index manager — build, query, write-through update, rebuild.

**File to create:** `gobp/core/db.py`

```python
"""GoBP SQLite persistent index.

Derived index over .gobp/ data for fast queries.
Source of truth is still markdown/YAML files on disk.
SQLite is rebuilt from files at any time via rebuild_index().

Index file: .gobp/index.db (gitignored)

Schema:
  nodes table — searchable node metadata
  nodes_fts   — FTS5 virtual table for full-text search
  edges table — edge relationships with indexes
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DB_FILENAME = "index.db"
SCHEMA_VERSION = 1


def _db_path(gobp_root: Path) -> Path:
    """Return path to SQLite index file."""
    return gobp_root / ".gobp" / DB_FILENAME


def _connect(gobp_root: Path) -> sqlite3.Connection:
    """Open connection to SQLite index. Creates file if missing."""
    db_path = _db_path(gobp_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_schema(gobp_root: Path) -> None:
    """Create SQLite schema if not exists. Idempotent."""
    conn = _connect(gobp_root)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                status TEXT DEFAULT '',
                topic TEXT DEFAULT '',
                subject TEXT DEFAULT '',
                group_field TEXT DEFAULT '',
                scope TEXT DEFAULT '',
                created TEXT DEFAULT '',
                updated TEXT DEFAULT '',
                fts_content TEXT DEFAULT ''
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
            CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id);
            CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id);
            CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
        """)

        # FTS5 virtual table (separate statement — cannot be in executescript with IF NOT EXISTS on older SQLite)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts
            USING fts5(id, name, topic, subject, fts_content, content='nodes', content_rowid='rowid')
        """)

        conn.execute(
            "INSERT OR IGNORE INTO meta VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),)
        )
        conn.commit()
    finally:
        conn.close()


def _node_to_row(node: dict[str, Any]) -> dict[str, str]:
    """Convert node dict to SQLite row dict."""
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
        "created": node.get("created", ""),
        "updated": node.get("updated", ""),
        "fts_content": fts_content,
    }


def upsert_node(gobp_root: Path, node: dict[str, Any]) -> None:
    """Insert or replace a node in the index."""
    row = _node_to_row(node)
    conn = _connect(gobp_root)
    try:
        conn.execute("""
            INSERT OR REPLACE INTO nodes
            (id, type, name, status, topic, subject, group_field, scope, created, updated, fts_content)
            VALUES (:id, :type, :name, :status, :topic, :subject, :group_field, :scope, :created, :updated, :fts_content)
        """, row)
        # Update FTS index
        conn.execute("INSERT OR REPLACE INTO nodes_fts(rowid, id, name, topic, subject, fts_content) SELECT rowid, id, name, topic, subject, fts_content FROM nodes WHERE id = ?", (row["id"],))
        conn.commit()
    finally:
        conn.close()


def delete_node(gobp_root: Path, node_id: str) -> None:
    """Remove a node from the index."""
    conn = _connect(gobp_root)
    try:
        conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        conn.commit()
    finally:
        conn.close()


def upsert_edge(gobp_root: Path, edge: dict[str, Any]) -> None:
    """Insert or replace an edge in the index."""
    from_id = edge.get("from", "")
    to_id = edge.get("to", "")
    edge_type = edge.get("type", "")
    edge_id = f"{from_id}__{edge_type}__{to_id}"

    conn = _connect(gobp_root)
    try:
        conn.execute("""
            INSERT OR REPLACE INTO edges (id, from_id, to_id, type)
            VALUES (?, ?, ?, ?)
        """, (edge_id, from_id, to_id, edge_type))
        conn.commit()
    finally:
        conn.close()


def delete_edges_for_node(gobp_root: Path, node_id: str) -> None:
    """Remove all edges where from_id or to_id matches node_id."""
    conn = _connect(gobp_root)
    try:
        conn.execute("DELETE FROM edges WHERE from_id = ? OR to_id = ?", (node_id, node_id))
        conn.commit()
    finally:
        conn.close()


def query_nodes_by_type(gobp_root: Path, node_type: str) -> list[str]:
    """Return list of node IDs for a given type."""
    conn = _connect(gobp_root)
    try:
        rows = conn.execute("SELECT id FROM nodes WHERE type = ?", (node_type,)).fetchall()
        return [r["id"] for r in rows]
    finally:
        conn.close()


def query_nodes_fts(gobp_root: Path, query: str, type_filter: str | None = None, limit: int = 20) -> list[str]:
    """Full-text search nodes. Returns list of node IDs."""
    conn = _connect(gobp_root)
    try:
        if type_filter:
            rows = conn.execute("""
                SELECT n.id FROM nodes_fts f
                JOIN nodes n ON n.id = f.id
                WHERE nodes_fts MATCH ? AND n.type = ?
                LIMIT ?
            """, (query, type_filter, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT n.id FROM nodes_fts f
                JOIN nodes n ON n.id = f.id
                WHERE nodes_fts MATCH ?
                LIMIT ?
            """, (query, limit)).fetchall()
        return [r["id"] for r in rows]
    except sqlite3.OperationalError:
        # FTS query syntax error → fall back to empty
        return []
    finally:
        conn.close()


def query_nodes_substring(gobp_root: Path, query: str, type_filter: str | None = None, limit: int = 20) -> list[str]:
    """Substring search nodes (fallback when FTS fails). Returns node IDs."""
    conn = _connect(gobp_root)
    try:
        q = f"%{query}%"
        if type_filter:
            rows = conn.execute("""
                SELECT id FROM nodes
                WHERE (id LIKE ? OR name LIKE ? OR fts_content LIKE ?) AND type = ?
                LIMIT ?
            """, (q, q, q, type_filter, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT id FROM nodes
                WHERE id LIKE ? OR name LIKE ? OR fts_content LIKE ?
                LIMIT ?
            """, (q, q, q, limit)).fetchall()
        return [r["id"] for r in rows]
    finally:
        conn.close()


def query_edges_from(gobp_root: Path, node_id: str) -> list[dict[str, str]]:
    """Get all edges where from_id = node_id."""
    conn = _connect(gobp_root)
    try:
        rows = conn.execute(
            "SELECT from_id, to_id, type FROM edges WHERE from_id = ?", (node_id,)
        ).fetchall()
        return [{"from": r["from_id"], "to": r["to_id"], "type": r["type"]} for r in rows]
    finally:
        conn.close()


def query_edges_to(gobp_root: Path, node_id: str) -> list[dict[str, str]]:
    """Get all edges where to_id = node_id."""
    conn = _connect(gobp_root)
    try:
        rows = conn.execute(
            "SELECT from_id, to_id, type FROM edges WHERE to_id = ?", (node_id,)
        ).fetchall()
        return [{"from": r["from_id"], "to": r["to_id"], "type": r["type"]} for r in rows]
    finally:
        conn.close()


def index_exists(gobp_root: Path) -> bool:
    """Return True if SQLite index file exists."""
    return _db_path(gobp_root).exists()


def rebuild_index(gobp_root: Path, graph_index: Any) -> dict[str, Any]:
    """Rebuild SQLite index from scratch using GraphIndex data.

    Args:
        gobp_root: Project root.
        graph_index: Populated GraphIndex instance (source of truth).

    Returns:
        Dict with ok, nodes_indexed, edges_indexed, message.
    """
    db_path = _db_path(gobp_root)

    # Drop and recreate
    if db_path.exists():
        db_path.unlink()

    init_schema(gobp_root)

    conn = _connect(gobp_root)
    try:
        nodes_indexed = 0
        for node in graph_index.all_nodes():
            row = _node_to_row(node)
            conn.execute("""
                INSERT OR REPLACE INTO nodes
                (id, type, name, status, topic, subject, group_field, scope, created, updated, fts_content)
                VALUES (:id, :type, :name, :status, :topic, :subject, :group_field, :scope, :created, :updated, :fts_content)
            """, row)
            nodes_indexed += 1

        edges_indexed = 0
        for edge in graph_index.all_edges():
            from_id = edge.get("from", "")
            to_id = edge.get("to", "")
            edge_type = edge.get("type", "")
            edge_id = f"{from_id}__{edge_type}__{to_id}"
            conn.execute(
                "INSERT OR REPLACE INTO edges (id, from_id, to_id, type) VALUES (?, ?, ?, ?)",
                (edge_id, from_id, to_id, edge_type)
            )
            edges_indexed += 1

        # Rebuild FTS
        conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild')")
        conn.commit()
    finally:
        conn.close()

    return {
        "ok": True,
        "nodes_indexed": nodes_indexed,
        "edges_indexed": edges_indexed,
        "message": f"Index rebuilt: {nodes_indexed} nodes, {edges_indexed} edges",
    }
```

**Acceptance criteria:**
- `gobp/core/db.py` created
- All functions have type hints + docstrings
- `init_schema()` is idempotent
- `rebuild_index()` drops + recreates from GraphIndex data
- Valid Python, imports without error

**Commit message:**
```
Wave 9A Task 1: create gobp/core/db.py — SQLite index manager

- init_schema(): create nodes/edges/meta/nodes_fts tables + indexes
- upsert_node/edge, delete_node/edge: write-through operations
- query_nodes_by_type, query_nodes_fts, query_nodes_substring: read ops
- query_edges_from, query_edges_to: edge traversal
- rebuild_index(): drop + recreate from GraphIndex data
- index_exists(): check if index file present
- WAL mode + NORMAL sync for performance
```

---

## TASK 2 — Create gobp/core/cache.py (LRU cache with TTL)

**Goal:** Simple in-memory LRU cache for hot data.

**File to create:** `gobp/core/cache.py`

```python
"""GoBP in-memory LRU cache with TTL.

Caches expensive operations like gobp_overview and GraphIndex loads.
Thread-safe via threading.Lock.

Usage:
    cache = GoBPCache(max_size=500, default_ttl=60)
    cache.set("gobp_overview", result, ttl=60)
    result = cache.get("gobp_overview")  # None if expired/missing
    cache.invalidate("gobp_overview")
    cache.invalidate_all()
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any


class GoBPCache:
    """LRU cache with per-entry TTL.

    Evicts least-recently-used entries when max_size is reached.
    Entries expire after TTL seconds regardless of access.
    """

    def __init__(self, max_size: int = 500, default_ttl: float = 60.0) -> None:
        """Initialize cache.

        Args:
            max_size: Maximum number of entries (LRU eviction beyond this).
            default_ttl: Default TTL in seconds for entries without explicit TTL.
        """
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """Get cached value. Returns None if missing or expired.

        Args:
            key: Cache key.

        Returns:
            Cached value or None.
        """
        with self._lock:
            if key not in self._cache:
                return None
            value, expire_at = self._cache[key]
            if time.monotonic() > expire_at:
                del self._cache[key]
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: TTL in seconds. Uses default_ttl if None.
        """
        expire_at = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, expire_at)
            # Evict LRU if over max_size
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def invalidate(self, key: str) -> None:
        """Remove a specific key from cache.

        Args:
            key: Cache key to remove.
        """
        with self._lock:
            self._cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """Remove all keys starting with prefix.

        Args:
            prefix: Key prefix to match.
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]

    def invalidate_all(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        """Return number of entries (including possibly expired)."""
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        with self._lock:
            now = time.monotonic()
            active = sum(1 for _, (_, exp) in self._cache.items() if exp > now)
            return {
                "total_entries": len(self._cache),
                "active_entries": active,
                "max_size": self._max_size,
                "default_ttl": self._default_ttl,
            }


# Module-level singleton for MCP server use
_cache: GoBPCache | None = None


def get_cache() -> GoBPCache:
    """Get or create the module-level cache singleton."""
    global _cache
    if _cache is None:
        _cache = GoBPCache(max_size=500, default_ttl=60.0)
    return _cache


def reset_cache() -> None:
    """Reset the module-level cache singleton (for testing)."""
    global _cache
    _cache = None
```

**Acceptance criteria:**
- `gobp/core/cache.py` created
- `GoBPCache` class: `get`, `set`, `invalidate`, `invalidate_prefix`, `invalidate_all`, `stats`
- Thread-safe via `threading.Lock`
- LRU eviction when `max_size` reached
- TTL expiry on `get`
- Module-level singleton: `get_cache()`, `reset_cache()`

**Commit message:**
```
Wave 9A Task 2: create gobp/core/cache.py — LRU cache with TTL

- GoBPCache: OrderedDict-based LRU, per-entry TTL, thread-safe
- get/set/invalidate/invalidate_prefix/invalidate_all/stats
- Module singleton: get_cache() + reset_cache() for testing
```

---

## TASK 3 — Modify gobp/core/graph.py to use SQLite index

**Goal:** `GraphIndex.load_from_disk()` builds SQLite index on first load, uses it for subsequent queries.

**File to modify:** `gobp/core/graph.py`

**Re-read current `gobp/core/graph.py` in full before editing.**

**Changes needed:**

**1. Add imports at top:**
```python
from gobp.core import db as _db
```

**2. Modify `load_from_disk()` classmethod** — after loading nodes/edges into memory, also build/update SQLite index:

Add at the end of `load_from_disk()`, before `return index`:

```python
        # Build SQLite index if not exists or stale
        # (always rebuild on load for now — Wave 9A baseline)
        try:
            _db.init_schema(gobp_root)
            _db.rebuild_index(gobp_root, index)
        except Exception:
            # SQLite failure is non-fatal — in-memory index still works
            pass

        return index
```

**3. Add `gobp_root` attribute** — store it for write-through operations:

In `__init__`, add:
```python
        self._gobp_root: Path | None = None
```

In `load_from_disk()`, after `index = cls()`:
```python
        index._gobp_root = gobp_root
```

**Acceptance criteria:**
- `load_from_disk()` calls `db.rebuild_index()` after loading
- SQLite failure is non-fatal (try/except, index still works)
- `_gobp_root` stored on instance
- All 200 existing tests still pass

**Commit message:**
```
Wave 9A Task 3: graph.py — build SQLite index on load_from_disk()

- Import gobp.core.db
- load_from_disk(): calls db.rebuild_index() after memory load
- SQLite failure non-fatal (try/except)
- Store _gobp_root on instance for write-through
- All 200 existing tests pass
```

---

## TASK 4 — Add write-through SQLite update in mutator.py

**Goal:** After each successful mutation, update SQLite index immediately.

**File to modify:** `gobp/core/mutator.py`

**Re-read current `gobp/core/mutator.py` in full before editing.**

**Add import at top:**
```python
from gobp.core import db as _db
from gobp.core import cache as _cache_module
```

**Modify `create_node()`** — add after `_atomic_write(node_file, content)`:

```python
    # Write-through: update SQLite index
    try:
        _db.init_schema(gobp_root)
        _db.upsert_node(gobp_root, node)
    except Exception:
        pass  # SQLite failure non-fatal

    # Invalidate cache
    try:
        _cache_module.get_cache().invalidate_all()
    except Exception:
        pass
```

**Modify `update_node()`** — add same write-through block after file write.

**Modify `delete_node()`** — add after file deletion:

```python
    try:
        _db.delete_node(gobp_root, node_id)
        _db.delete_edges_for_node(gobp_root, node_id)
        _cache_module.get_cache().invalidate_all()
    except Exception:
        pass
```

**Modify `create_edge()`** — add after file write:

```python
    try:
        _db.init_schema(gobp_root)
        _db.upsert_edge(gobp_root, edge)
        _cache_module.get_cache().invalidate_all()
    except Exception:
        pass
```

**Acceptance criteria:**
- All 4 mutation functions have write-through SQLite update
- All SQLite operations wrapped in try/except (non-fatal)
- Cache invalidated after every mutation
- All 200 existing tests still pass

**Commit message:**
```
Wave 9A Task 4: mutator.py — write-through SQLite + cache invalidation

- create_node, update_node: upsert_node after file write
- delete_node: delete_node + delete_edges_for_node after file delete
- create_edge: upsert_edge after file write
- All wrapped in try/except — SQLite failure non-fatal
- Cache invalidated after every mutation
```

---

## TASK 5 — Modify gobp/mcp/server.py to use SQLite + cache for gobp_overview

**Goal:** `gobp_overview` uses LRU cache. Server reuses loaded GraphIndex instead of reloading per call.

**File to modify:** `gobp/mcp/server.py`

**Re-read current `gobp/mcp/server.py` in full before editing.**

**Changes:**

**1. Add imports:**
```python
from gobp.core.cache import get_cache
```

**2. Modify the `gobp_overview` dispatch** — wrap with cache:

Find where `gobp_overview` tool is handled in `call_tool()`. Wrap:

```python
        if name == "gobp_overview":
            cache = get_cache()
            cached = cache.get("gobp_overview")
            if cached is not None:
                return [types.TextContent(type="text", text=json.dumps(cached, ensure_ascii=False))]
            result = await handler(_index, _project_root, arguments)
            if isinstance(result, dict) and result.get("ok"):
                cache.set("gobp_overview", result, ttl=60)
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
```

**Note:** Only cache `gobp_overview` in Wave 9A. Other tools benefit from SQLite rebuild on load. Full per-tool caching can be added in Wave 9B if needed.

**Acceptance criteria:**
- `gobp_overview` cached with 60s TTL
- Cache hit returns immediately without reloading index
- Write tools (node_upsert, decision_lock, session_log, import_commit) invalidate cache after success
- All existing tests pass

**Add cache invalidation after write tools** — find the index reload block after write operations and add:

```python
            if name in ("node_upsert", "decision_lock", "session_log", "import_commit"):
                if isinstance(result, dict) and result.get("ok"):
                    get_cache().invalidate_all()
```

**Commit message:**
```
Wave 9A Task 5: server.py — cache gobp_overview with 60s TTL

- gobp_overview: LRU cache hit < 1ms vs 460ms cold
- Write tools: invalidate_all() on success
- Cache imported from gobp.core.cache
```

---

## TASK 6 — Add --reindex flag to gobp validate CLI command

**Goal:** `python -m gobp.cli validate --reindex` rebuilds SQLite from scratch.

**File to modify:** `gobp/cli/commands.py`

**Re-read `gobp/cli/commands.py` in full before editing.**

**1. Add `--reindex` argument to validate subcommand** in `main()`:

```python
    val_p.add_argument(
        "--reindex",
        action="store_true",
        help="Rebuild SQLite index from scratch before validating",
    )
```

**2. Modify `cmd_validate()`** — add reindex logic at the start:

```python
    if args.reindex:
        print("Rebuilding SQLite index...")
        try:
            from gobp.core import db as _db
            index_for_rebuild = GraphIndex.load_from_disk(root)
            result = _db.rebuild_index(root, index_for_rebuild)
            print(f"  {result['message']}")
        except Exception as e:
            print(f"  Warning: reindex failed: {e}", file=sys.stderr)
```

**Acceptance criteria:**
- `python -m gobp.cli validate --reindex` works
- Prints rebuild message
- Then runs normal validation
- Existing `validate` behavior unchanged when `--reindex` not passed

**Commit message:**
```
Wave 9A Task 6: add --reindex flag to gobp validate CLI

- cmd_validate: --reindex rebuilds SQLite from disk files
- Useful when index.db is corrupted or missing
- Normal validate behavior unchanged without flag
```

---

## TASK 7 — Update .gitignore for index.db

**Goal:** Ensure `.gobp/index.db` is gitignored in all projects.

**File to modify:** `.gitignore`

**Add to `.gitignore`** (after existing entries):

```
# GoBP derived files
.gobp/index.db
.gobp/archive/
```

**Also update `docs/GoBP_ARCHITECTURE.md`** — add note in §4 about `index.db` being gitignored:

Find the `.gobp/` tree and add:
```
│   └── index.db                    ← derived SQLite index (gitignored, rebuildable)
```

**Acceptance criteria:**
- `.gitignore` has `.gobp/index.db` entry
- `docs/GoBP_ARCHITECTURE.md` §4 mentions `index.db` as derived/gitignored

**Commit message:**
```
Wave 9A Task 7: gitignore .gobp/index.db + update architecture doc

- .gitignore: .gobp/index.db, .gobp/archive/
- GoBP_ARCHITECTURE.md §4: index.db noted as derived/gitignored
```

---

## TASK 8 — Write tests for db.py and cache.py

**Goal:** Test SQLite index and LRU cache modules.

**File to create:** `tests/test_db_cache.py`

```python
"""Tests for gobp/core/db.py and gobp/core/cache.py."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from gobp.core.cache import GoBPCache, get_cache, reset_cache
from gobp.core import db as db_module


# ── Cache tests ───────────────────────────────────────────────────────────────

def test_cache_get_miss():
    cache = GoBPCache()
    assert cache.get("missing") is None


def test_cache_set_and_get():
    cache = GoBPCache()
    cache.set("key", {"value": 42})
    result = cache.get("key")
    assert result == {"value": 42}


def test_cache_ttl_expiry():
    cache = GoBPCache(default_ttl=0.05)  # 50ms TTL
    cache.set("key", "value")
    time.sleep(0.1)
    assert cache.get("key") is None


def test_cache_lru_eviction():
    cache = GoBPCache(max_size=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)  # evicts "a" (LRU)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_cache_invalidate():
    cache = GoBPCache()
    cache.set("key", "value")
    cache.invalidate("key")
    assert cache.get("key") is None


def test_cache_invalidate_prefix():
    cache = GoBPCache()
    cache.set("node:a", 1)
    cache.set("node:b", 2)
    cache.set("edge:x", 3)
    cache.invalidate_prefix("node:")
    assert cache.get("node:a") is None
    assert cache.get("node:b") is None
    assert cache.get("edge:x") == 3


def test_cache_invalidate_all():
    cache = GoBPCache()
    cache.set("a", 1)
    cache.set("b", 2)
    cache.invalidate_all()
    assert len(cache) == 0


def test_cache_singleton():
    reset_cache()
    c1 = get_cache()
    c2 = get_cache()
    assert c1 is c2


def test_cache_stats():
    cache = GoBPCache()
    cache.set("a", 1)
    stats = cache.stats()
    assert stats["total_entries"] == 1
    assert stats["active_entries"] == 1


# ── SQLite db tests ───────────────────────────────────────────────────────────

def test_db_init_schema_idempotent(gobp_root: Path):
    """init_schema can be called twice without error."""
    db_module.init_schema(gobp_root)
    db_module.init_schema(gobp_root)
    assert db_module.index_exists(gobp_root)


def test_db_upsert_and_query_node(gobp_root: Path):
    """upsert_node + query_nodes_by_type roundtrip."""
    db_module.init_schema(gobp_root)
    node = {
        "id": "node:test001",
        "type": "Node",
        "name": "Test Node",
        "status": "ACTIVE",
        "created": "2026-04-15T00:00:00",
        "updated": "2026-04-15T00:00:00",
    }
    db_module.upsert_node(gobp_root, node)
    ids = db_module.query_nodes_by_type(gobp_root, "Node")
    assert "node:test001" in ids


def test_db_delete_node(gobp_root: Path):
    """delete_node removes from index."""
    db_module.init_schema(gobp_root)
    node = {"id": "node:del001", "type": "Node", "name": "Delete Me",
            "status": "ACTIVE", "created": "2026-04-15T00:00:00", "updated": "2026-04-15T00:00:00"}
    db_module.upsert_node(gobp_root, node)
    db_module.delete_node(gobp_root, "node:del001")
    ids = db_module.query_nodes_by_type(gobp_root, "Node")
    assert "node:del001" not in ids


def test_db_upsert_and_query_edges(gobp_root: Path):
    """upsert_edge + query_edges_from roundtrip."""
    db_module.init_schema(gobp_root)
    edge = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    db_module.upsert_edge(gobp_root, edge)
    edges = db_module.query_edges_from(gobp_root, "node:a")
    assert len(edges) == 1
    assert edges[0]["to"] == "node:b"


def test_db_query_edges_to(gobp_root: Path):
    """query_edges_to returns correct edges."""
    db_module.init_schema(gobp_root)
    edge = {"from": "node:x", "to": "node:y", "type": "implements"}
    db_module.upsert_edge(gobp_root, edge)
    edges = db_module.query_edges_to(gobp_root, "node:y")
    assert len(edges) == 1
    assert edges[0]["from"] == "node:x"


def test_db_substring_search(gobp_root: Path):
    """query_nodes_substring finds by name substring."""
    db_module.init_schema(gobp_root)
    node = {"id": "node:login001", "type": "Node", "name": "Login Feature",
            "status": "ACTIVE", "created": "2026-04-15T00:00:00", "updated": "2026-04-15T00:00:00"}
    db_module.upsert_node(gobp_root, node)
    ids = db_module.query_nodes_substring(gobp_root, "login")
    assert "node:login001" in ids


def test_db_type_filter_in_search(gobp_root: Path):
    """query_nodes_substring with type_filter."""
    db_module.init_schema(gobp_root)
    n1 = {"id": "node:f001", "type": "Node", "name": "auth feature",
          "status": "ACTIVE", "created": "2026-04-15T00:00:00", "updated": "2026-04-15T00:00:00"}
    n2 = {"id": "dec:d001", "type": "Decision", "name": "auth decision",
          "status": "LOCKED", "topic": "auth:method",
          "created": "2026-04-15T00:00:00", "updated": "2026-04-15T00:00:00"}
    db_module.upsert_node(gobp_root, n1)
    db_module.upsert_node(gobp_root, n2)

    node_ids = db_module.query_nodes_substring(gobp_root, "auth", type_filter="Node")
    assert "node:f001" in node_ids
    assert "dec:d001" not in node_ids


def test_db_rebuild_index(gobp_root: Path):
    """rebuild_index creates fresh index from GraphIndex."""
    from gobp.core.init import init_project
    from gobp.core.graph import GraphIndex

    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = db_module.rebuild_index(gobp_root, index)
    assert result["ok"] is True
    assert result["nodes_indexed"] >= 17  # seed nodes
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_db_cache.py -v
# Expected: ~19 tests passing
```

**Commit message:**
```
Wave 9A Task 8: create tests/test_db_cache.py

- 9 cache tests: miss, set/get, TTL expiry, LRU eviction,
  invalidate, invalidate_prefix, invalidate_all, singleton, stats
- 10 db tests: init idempotent, upsert/query node, delete node,
  upsert/query edges, query_edges_to, substring search,
  type filter search, rebuild_index
```

---

## TASK 9 — Performance verification + CHANGELOG update

**Goal:** Verify performance tests now meet targets. Update CHANGELOG.

**Run performance tests:**

```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_performance.py -v --durations=10
```

**Expected after Wave 9A:**

```
gobp_overview (cache hit):   < 5ms    (was 460ms)
gobp_overview (cold):        < 100ms  (index rebuilt on load)
find:                        < 50ms
context:                     < 100ms
node_upsert:                 < 200ms
All others:                  < 100ms
```

If any test fails latency target → report actual numbers, do NOT modify test thresholds.

**Run full suite:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 219+ tests passing (200 + ~19 new)
```

**Update CHANGELOG.md** — prepend after `# CHANGELOG`:

```markdown
## [Wave 9A] — SQLite Persistent Index + LRU Cache — 2026-04-15

### Added
- `gobp/core/db.py` — SQLite index manager (init, upsert, delete, query, rebuild)
- `gobp/core/cache.py` — LRU cache with TTL, thread-safe, module singleton
- `tests/test_db_cache.py` — 19 tests for db + cache modules

### Changed
- `gobp/core/graph.py` — `load_from_disk()` now builds SQLite index after memory load
- `gobp/core/mutator.py` — write-through SQLite update after every mutation
- `gobp/mcp/server.py` — `gobp_overview` cached with 60s TTL
- `gobp/cli/commands.py` — `validate --reindex` flag to rebuild index
- `.gitignore` — `.gobp/index.db` gitignored

### Performance improvement vs Wave H baseline

| Tool | Before (Wave H) | After (Wave 9A) |
|---|---|---|
| gobp_overview (cache hit) | 460ms | < 5ms |
| gobp_overview (cold) | 460ms | < 100ms |
| find | 60ms | < 50ms |
| node_upsert | 210ms | < 200ms |
| All read tools | ~60ms | < 50ms |

### Total after wave: 14 MCP tools, 219+ tests passing
```

**Commit message:**
```
Wave 9A Task 9: performance verified + CHANGELOG updated

- All performance tests passing within MCP_TOOLS.md §10 targets
- CHANGELOG.md: Wave 9A entry with before/after numbers
- 219+ total tests passing
```

---

# POST-WAVE VERIFICATION

```powershell
# All tests pass
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 219+ tests

# Performance within targets
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_performance.py -v --durations=10
# Expected: all < max latency targets

# SQLite index created on init
$env:GOBP_PROJECT_ROOT = "C:\tmp\gobp_9a_test"
New-Item -ItemType Directory -Force -Path $env:GOBP_PROJECT_ROOT
D:/GoBP/venv/Scripts/python.exe -m gobp.cli init --name "perf-test"
Test-Path "C:\tmp\gobp_9a_test\.gobp\index.db"
# Expected: True

# Reindex works
D:/GoBP/venv/Scripts/python.exe -m gobp.cli validate --reindex --scope nodes
# Expected: prints rebuild message + validation result

# Git log
git log --oneline | Select-Object -First 11
# Expected: 9 Wave 9A commits
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief vào repo

```powershell
cd D:\GoBP
# Save wave_9a_brief.md to D:\GoBP\waves\wave_9a_brief.md

git add waves/wave_9a_brief.md
git commit -m "Add Wave 9A Brief — SQLite index + LRU cache"
git push origin main
```

## 2. Dispatch Cursor

Cursor IDE → Ctrl+L → paste:

```
Read .cursorrules and waves/wave_9a_brief.md first.
Also read gobp/core/graph.py, gobp/core/mutator.py, gobp/mcp/server.py.
Also read tests/conftest.py and docs/MCP_TOOLS.md.

Execute ALL 9 tasks of Wave 9A sequentially.
Rules:
- Use explorer subagent before creating any file
- Re-read per-task files listed in REQUIRED READING before each task
- R9 is critical: all 200 existing tests must pass after EVERY task
- SQLite failures must always be non-fatal (try/except)
- If performance tests still fail targets → report actual numbers, do NOT change thresholds (R8)
- 1 task = 1 commit, message must match Brief exactly
- Report full wave summary after Task 9

Begin Task 1.
```

## 3. Audit Claude CLI

```powershell
cd D:\GoBP
claude
```

```
Audit Wave 9A. Read CLAUDE.md and waves/wave_9a_brief.md.
Also read docs/GoBP_ARCHITECTURE.md, docs/ARCHITECTURE.md, docs/MCP_TOOLS.md.

Audit Tasks 1–9 sequentially.

Critical verification:
- Task 1: gobp/core/db.py exists, all functions have type hints + docstrings, imports cleanly
- Task 2: gobp/core/cache.py exists, GoBPCache class + get_cache/reset_cache, thread-safe
- Task 3: graph.py load_from_disk() calls db.rebuild_index(), SQLite failure non-fatal, all 200 tests pass
- Task 4: mutator.py write-through in create/update/delete node + create edge, all non-fatal
- Task 5: server.py gobp_overview cached 60s TTL, write tools invalidate cache
- Task 6: gobp validate --reindex works, normal validate unchanged
- Task 7: .gitignore has .gobp/index.db, GoBP_ARCHITECTURE.md §4 mentions index.db
- Task 8: tests/test_db_cache.py exists, 19 tests passing
- Task 9: performance tests all within MCP_TOOLS.md §10 targets, CHANGELOG updated, 219+ tests

Use venv Python:
  D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

Expected: 219+ tests passing.

Stop on first failure. Report WAVE 9A AUDIT COMPLETE when done.
```

## 4. Push

```powershell
cd D:\GoBP
git push origin main
```

---

# WHAT COMES NEXT

```
Wave 9A pushed
    ↓
Wave 8B — MIHOS real import (2 phases):
  Phase 1: GoBP dogfood
    gobp init in D:\GoBP (dogfood)
    Import wave briefs as Document nodes
    Run lessons_extract()
    Connect Cursor → test efficiency
  Phase 2: MIHOS real import
    gobp init in D:\MIHOS
    Import 31 MIHOS docs
    Connect Cursor → build MIHOS features
```

---

*Wave 9A Brief v0.1*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
