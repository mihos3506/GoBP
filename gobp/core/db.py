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

DB_FILENAME = "index.db"
SCHEMA_VERSION = 2


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


def create_schema_v3(conn: Any) -> None:
    """
    Create GoBP schema v3 tables.

    Drop existing tables if present — only for fresh setup.
    Migration from v2 to v3 is Wave F.
    """
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS node_history CASCADE")
        cur.execute("DROP TABLE IF EXISTS edges CASCADE")
        cur.execute("DROP TABLE IF EXISTS nodes CASCADE")

        cur.execute(
            """
            CREATE TABLE nodes (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                group_path  TEXT NOT NULL,
                desc_l1     TEXT DEFAULT '',
                desc_l2     TEXT DEFAULT '',
                desc_full   TEXT DEFAULT '',
                code        TEXT DEFAULT '',
                severity    TEXT DEFAULT '',
                search_vec  tsvector GENERATED ALWAYS AS (
                    setweight(to_tsvector('simple', coalesce(name, '')), 'A') ||
                    setweight(to_tsvector('simple', coalesce(group_path, '')), 'B') ||
                    setweight(to_tsvector('simple', coalesce(desc_l2, '')), 'C')
                ) STORED,
                updated_at  BIGINT NOT NULL DEFAULT
                    extract(epoch from now())::BIGINT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE edges (
                from_id    TEXT NOT NULL REFERENCES nodes(id)
                           ON DELETE CASCADE,
                to_id      TEXT NOT NULL REFERENCES nodes(id)
                           ON DELETE CASCADE,
                reason     TEXT DEFAULT '',
                reason_vec tsvector GENERATED ALWAYS AS (
                    to_tsvector('simple', coalesce(reason, ''))
                ) STORED,
                code       TEXT DEFAULT '',
                created_at BIGINT NOT NULL DEFAULT
                    extract(epoch from now())::BIGINT,
                PRIMARY KEY (from_id, to_id)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE node_history (
                id          SERIAL PRIMARY KEY,
                node_id     TEXT NOT NULL REFERENCES nodes(id)
                            ON DELETE CASCADE,
                description TEXT NOT NULL,
                code        TEXT DEFAULT '',
                created_at  BIGINT NOT NULL DEFAULT
                    extract(epoch from now())::BIGINT
            )
            """
        )

        cur.execute(
            """
            CREATE INDEX idx_nodes_search
            ON nodes USING GIN(search_vec)
            """
        )
        cur.execute(
            """
            CREATE INDEX idx_nodes_group
            ON nodes(group_path text_pattern_ops)
            """
        )
        cur.execute(
            """
            CREATE INDEX idx_nodes_updated
            ON nodes(updated_at)
            """
        )
        cur.execute(
            """
            CREATE INDEX idx_edges_from
            ON edges(from_id)
            """
        )
        cur.execute(
            """
            CREATE INDEX idx_edges_to
            ON edges(to_id)
            """
        )
        cur.execute(
            """
            CREATE INDEX idx_edges_reason
            ON edges USING GIN(reason_vec)
            """
        )
        cur.execute(
            """
            CREATE INDEX idx_history_node
            ON node_history(node_id)
            """
        )

        conn.commit()

    from gobp.core.import_lock import create_import_locks_table

    create_import_locks_table(conn)


def get_schema_version(conn: Any) -> str:
    """Return 'v3' if nodes table has desc_l1 column, else 'v2'."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'nodes' AND column_name = 'desc_l1'
            """
        )
        return "v3" if cur.fetchone() else "v2"


def _node_desc_full_v3(node: dict[str, Any]) -> str:
    """Full description text for schema v3 ``desc_full`` column."""
    if node.get("desc_full") is not None:
        return str(node.get("desc_full", ""))
    desc = node.get("description", "")
    if isinstance(desc, dict):
        return str(desc.get("info", "") or "")
    return str(desc or "")


def upsert_node_v3(conn: Any, node: dict[str, Any]) -> None:
    """Upsert node into PostgreSQL schema v3."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO nodes
                (id, name, group_path, desc_l1, desc_l2, desc_full,
                 code, severity, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                    extract(epoch from now())::BIGINT)
            ON CONFLICT (id) DO UPDATE SET
                name       = EXCLUDED.name,
                group_path = EXCLUDED.group_path,
                desc_l1    = EXCLUDED.desc_l1,
                desc_l2    = EXCLUDED.desc_l2,
                desc_full  = EXCLUDED.desc_full,
                code       = EXCLUDED.code,
                severity   = EXCLUDED.severity,
                updated_at = extract(epoch from now())::BIGINT
            """,
            (
                node["id"],
                node["name"],
                str(node.get("group") or node.get("group_path", "") or ""),
                str(node.get("desc_l1", "") or ""),
                str(node.get("desc_l2", "") or ""),
                _node_desc_full_v3(node),
                str(node.get("code", "") or ""),
                str(node.get("severity", "") or ""),
            ),
        )
    conn.commit()


def delete_node_v3(conn: Any, node_id: str) -> None:
    """Delete node (edges CASCADE)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM nodes WHERE id = %s", (node_id,))
    conn.commit()


def upsert_edge_v3(
    conn: Any,
    from_id: str,
    to_id: str,
    reason: str = "",
    code: str = "",
) -> None:
    """Upsert edge — schema v3 has no edge type column."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO edges (from_id, to_id, reason, code, created_at)
            VALUES (%s, %s, %s, %s, extract(epoch from now())::BIGINT)
            ON CONFLICT (from_id, to_id) DO UPDATE SET
                reason = EXCLUDED.reason,
                code   = EXCLUDED.code
            """,
            (from_id, to_id, reason, code),
        )
    conn.commit()


def delete_edge_v3(conn: Any, from_id: str, to_id: str) -> None:
    """Delete one edge row."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM edges WHERE from_id=%s AND to_id=%s",
            (from_id, to_id),
        )
    conn.commit()


def append_history_v3(
    conn: Any,
    node_id: str,
    description: str,
    code: str = "",
) -> None:
    """Append history entry (append-only)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO node_history
                (node_id, description, code, created_at)
            VALUES (%s, %s, %s, extract(epoch from now())::BIGINT)
            """,
            (node_id, description, code),
        )
    conn.commit()


def get_node_updated_at(conn: Any, node_id: str) -> int | None:
    """Return ``updated_at`` epoch seconds for optimistic locking."""
    with conn.cursor() as cur:
        cur.execute("SELECT updated_at FROM nodes WHERE id = %s", (node_id,))
        row = cur.fetchone()
        return int(row[0]) if row else None


def init_schema(gobp_root: Path) -> None:
    """Create PostgreSQL schema if not exists. Idempotent."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
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
                """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS edges (
                        id TEXT PRIMARY KEY,
                        from_id TEXT NOT NULL,
                        to_id TEXT NOT NULL,
                        type TEXT NOT NULL
                    )
                """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS meta (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """
                )
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
                    ("schema_version", str(SCHEMA_VERSION)),
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
                cur.execute(
                    """
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
                """,
                    row,
                )
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
                cur.execute(
                    """
                    INSERT INTO edges (id, from_id, to_id, type)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        from_id=EXCLUDED.from_id,
                        to_id=EXCLUDED.to_id,
                        type=EXCLUDED.type
                """,
                    (edge_id, from_id, to_id, edge_type),
                )
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
                    (node_id, node_id),
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
    gobp_root: Path, query: str, type_filter: str | None = None, limit: int = 20
) -> list[str]:
    """Full-text search nodes using PostgreSQL tsvector. Returns node IDs."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return []
    try:
        with conn.cursor() as cur:
            if type_filter:
                cur.execute(
                    """
                    SELECT id FROM nodes
                    WHERE fts_vector @@ plainto_tsquery('english', %s)
                    AND type = %s
                    LIMIT %s
                """,
                    (query, type_filter, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id FROM nodes
                    WHERE fts_vector @@ plainto_tsquery('english', %s)
                    LIMIT %s
                """,
                    (query, limit),
                )
            return [row[0] for row in cur.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()


def query_nodes_substring(
    gobp_root: Path, query: str, type_filter: str | None = None, limit: int = 20
) -> list[str]:
    """Substring search nodes (fallback when FTS fails). Returns node IDs."""
    conn = _get_conn(gobp_root)
    if conn is None:
        return []
    try:
        q = f"%{query}%"
        with conn.cursor() as cur:
            if type_filter:
                cur.execute(
                    """
                    SELECT id FROM nodes
                    WHERE (id ILIKE %s OR name ILIKE %s OR fts_content ILIKE %s)
                    AND type = %s
                    LIMIT %s
                """,
                    (q, q, q, type_filter, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id FROM nodes
                    WHERE id ILIKE %s OR name ILIKE %s OR fts_content ILIKE %s
                    LIMIT %s
                """,
                    (q, q, q, limit),
                )
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
                (node_id,),
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
                (node_id,),
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
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'nodes'
                )
            """
            )
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
                    cur.execute(
                        """
                        INSERT INTO nodes
                            (id, type, name, status, topic, subject, group_field,
                             scope, priority, created, updated, fts_content)
                        VALUES
                            (%(id)s, %(type)s, %(name)s, %(status)s, %(topic)s,
                             %(subject)s, %(group_field)s, %(scope)s, %(priority)s,
                             %(created)s, %(updated)s, %(fts_content)s)
                        ON CONFLICT (id) DO NOTHING
                    """,
                        row,
                    )
                    nodes_indexed += 1

                # Insert all edges
                edges_indexed = 0
                for edge in graph_index.all_edges():
                    from_id = edge.get("from", "")
                    to_id = edge.get("to", "")
                    edge_type = edge.get("type", "")
                    edge_id = f"{from_id}__{edge_type}__{to_id}"
                    cur.execute(
                        """
                        INSERT INTO edges (id, from_id, to_id, type)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """,
                        (edge_id, from_id, to_id, edge_type),
                    )
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
