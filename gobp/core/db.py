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
        conn.executescript(
            """
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
            """
        )

        try:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts
                USING fts5(
                    id, name, topic, subject, fts_content,
                    content='nodes', content_rowid='rowid'
                )
                """
            )
        except sqlite3.OperationalError:
            # FTS5 unavailable or cannot attach — queries fall back to substring only
            pass

        conn.execute(
            "INSERT OR IGNORE INTO meta VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        conn.commit()
    finally:
        conn.close()


def _fts_table_exists(conn: sqlite3.Connection) -> bool:
    """Return True if nodes_fts virtual table exists."""
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
    ).fetchone()
    return row is not None


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
        "status": str(node.get("status", "") or ""),
        "topic": str(node.get("topic", "") or ""),
        "subject": str(node.get("subject", "") or ""),
        "group_field": str(node.get("group", "") or ""),
        "scope": str(node.get("scope", "") or ""),
        "created": str(node.get("created", "") or ""),
        "updated": str(node.get("updated", "") or ""),
        "fts_content": fts_content,
    }


def _sync_fts_after_node_write(conn: sqlite3.Connection, node_id: str) -> None:
    """Notify FTS5 external content index of a nodes row change."""
    if not _fts_table_exists(conn):
        return
    row = conn.execute("SELECT rowid FROM nodes WHERE id = ?", (node_id,)).fetchone()
    if row is None:
        return
    rid = int(row["rowid"])
    try:
        conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('delete', ?)", (rid,))
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('insert', ?)", (rid,))
    except sqlite3.OperationalError:
        pass


def upsert_node(gobp_root: Path, node: dict[str, Any]) -> None:
    """Insert or replace a node in the index."""
    row = _node_to_row(node)
    conn = _connect(gobp_root)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO nodes
            (id, type, name, status, topic, subject, group_field, scope, created, updated, fts_content)
            VALUES (:id, :type, :name, :status, :topic, :subject, :group_field, :scope, :created, :updated, :fts_content)
            """,
            row,
        )
        _sync_fts_after_node_write(conn, row["id"])
        conn.commit()
    finally:
        conn.close()


def delete_node(gobp_root: Path, node_id: str) -> None:
    """Remove a node from the index."""
    conn = _connect(gobp_root)
    try:
        if _fts_table_exists(conn):
            row = conn.execute("SELECT rowid FROM nodes WHERE id = ?", (node_id,)).fetchone()
            if row is not None:
                try:
                    conn.execute(
                        "INSERT INTO nodes_fts(nodes_fts) VALUES('delete', ?)",
                        (int(row["rowid"]),),
                    )
                except sqlite3.OperationalError:
                    pass
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
        conn.execute(
            """
            INSERT OR REPLACE INTO edges (id, from_id, to_id, type)
            VALUES (?, ?, ?, ?)
            """,
            (edge_id, from_id, to_id, edge_type),
        )
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
        return [str(r["id"]) for r in rows]
    finally:
        conn.close()


def query_nodes_fts(
    gobp_root: Path, query: str, type_filter: str | None = None, limit: int = 20
) -> list[str]:
    """Full-text search nodes. Returns list of node IDs."""
    conn = _connect(gobp_root)
    try:
        if not _fts_table_exists(conn):
            return []
        if type_filter:
            rows = conn.execute(
                """
                SELECT n.id FROM nodes_fts AS f
                JOIN nodes AS n ON n.rowid = f.rowid
                WHERE f MATCH ? AND n.type = ?
                LIMIT ?
                """,
                (query, type_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT n.id FROM nodes_fts AS f
                JOIN nodes AS n ON n.rowid = f.rowid
                WHERE f MATCH ?
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        return [str(r["id"]) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def query_nodes_substring(
    gobp_root: Path, query: str, type_filter: str | None = None, limit: int = 20
) -> list[str]:
    """Substring search nodes (fallback when FTS fails). Returns node IDs."""
    conn = _connect(gobp_root)
    try:
        q = f"%{query}%"
        if type_filter:
            rows = conn.execute(
                """
                SELECT id FROM nodes
                WHERE (id LIKE ? OR name LIKE ? OR fts_content LIKE ?) AND type = ?
                LIMIT ?
                """,
                (q, q, q, type_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id FROM nodes
                WHERE id LIKE ? OR name LIKE ? OR fts_content LIKE ?
                LIMIT ?
                """,
                (q, q, q, limit),
            ).fetchall()
        return [str(r["id"]) for r in rows]
    finally:
        conn.close()


def query_edges_from(gobp_root: Path, node_id: str) -> list[dict[str, str]]:
    """Get all edges where from_id = node_id."""
    conn = _connect(gobp_root)
    try:
        rows = conn.execute(
            "SELECT from_id, to_id, type FROM edges WHERE from_id = ?", (node_id,)
        ).fetchall()
        return [
            {"from": str(r["from_id"]), "to": str(r["to_id"]), "type": str(r["type"])}
            for r in rows
        ]
    finally:
        conn.close()


def query_edges_to(gobp_root: Path, node_id: str) -> list[dict[str, str]]:
    """Get all edges where to_id = node_id."""
    conn = _connect(gobp_root)
    try:
        rows = conn.execute(
            "SELECT from_id, to_id, type FROM edges WHERE to_id = ?", (node_id,)
        ).fetchall()
        return [
            {"from": str(r["from_id"]), "to": str(r["to_id"]), "type": str(r["type"])}
            for r in rows
        ]
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

    if db_path.exists():
        db_path.unlink()

    init_schema(gobp_root)

    conn = _connect(gobp_root)
    try:
        nodes_indexed = 0
        for node in graph_index.all_nodes():
            row = _node_to_row(node)
            conn.execute(
                """
                INSERT OR REPLACE INTO nodes
                (id, type, name, status, topic, subject, group_field, scope, created, updated, fts_content)
                VALUES (:id, :type, :name, :status, :topic, :subject, :group_field, :scope, :created, :updated, :fts_content)
                """,
                row,
            )
            nodes_indexed += 1

        edges_indexed = 0
        for edge in graph_index.all_edges():
            from_id = edge.get("from", "")
            to_id = edge.get("to", "")
            edge_type = edge.get("type", "")
            edge_id = f"{from_id}__{edge_type}__{to_id}"
            conn.execute(
                "INSERT OR REPLACE INTO edges (id, from_id, to_id, type) VALUES (?, ?, ?, ?)",
                (edge_id, from_id, to_id, edge_type),
            )
            edges_indexed += 1

        if _fts_table_exists(conn):
            try:
                conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild')")
            except sqlite3.OperationalError:
                pass
        conn.commit()
    finally:
        conn.close()

    return {
        "ok": True,
        "nodes_indexed": nodes_indexed,
        "edges_indexed": edges_indexed,
        "message": f"Index rebuilt: {nodes_indexed} nodes, {edges_indexed} edges",
    }
