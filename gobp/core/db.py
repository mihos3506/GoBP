"""GoBP persistent index — PostgreSQL backend.

PostgreSQL schema v3 for scale and concurrent access.

Connection: reads GOBP_DB_URL environment variable.
Fallback: if PostgreSQL unavailable, operations are no-ops (in-memory index still works).

Schema:
  nodes  — searchable node metadata with tsvector FTS
  edges  — edge relationships with indexes
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Types only — ``pip install -e ".[postgres]"`` for IDE stubs; no runtime import.
    from psycopg2.extensions import connection as PgConnection
else:
    PgConnection = Any  # type: ignore[misc, assignment]

logger = logging.getLogger("gobp.db")


@contextmanager
def postgres_connection(gobp_root: Path) -> Iterator[Any]:
    """Yield a PostgreSQL connection with commit / rollback / close.

    Use for ad-hoc scripts. Low-level helpers such as :func:`upsert_node_v3`
    already call ``conn.commit()``; an extra commit at context exit is harmless.

    Yields:
        Open connection, or ``None`` if no URL / connect fails.
    """
    conn = _get_conn(gobp_root)
    if conn is None:
        yield None
        return
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _get_conn(gobp_root: Path) -> Any | None:
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


def create_schema_v3(conn: PgConnection) -> None:
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


def get_schema_version(conn: PgConnection) -> str:
    """Return 'v3' if nodes table has desc_l1 column, else 'v2'."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'nodes' AND column_name = 'desc_l1'
            """
        )
        return "v3" if cur.fetchone() else "v2"


def count_nodes_in_db(gobp_root: Path) -> int:
    """Return total node count from PostgreSQL schema v3.

    Returns ``0`` if PostgreSQL is unavailable, connection fails, or schema is not v3.
    Used for :class:`~gobp.core.graph.GraphIndex` tier detection at startup.

    See ``docs/ARCHITECTURE.md`` §2 for tier thresholds.
    """
    conn = _get_conn(gobp_root)
    if conn is None:
        return 0
    try:
        if get_schema_version(conn) != "v3":
            return 0
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM nodes")
            row = cur.fetchone()
            return int(row[0]) if row else 0
    except Exception as e:
        logger.debug("count_nodes_in_db failed: %s", e)
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


def ensure_v3_connection(gobp_root: Path) -> PgConnection:
    """Return an open PostgreSQL connection whose schema is v3.

    Intended for CLI / maintenance scripts that must not run in file-only
    mode. The caller **must** ``close()`` the connection when finished.

    Raises:
        RuntimeError: if ``GOBP_DB_URL`` is missing, the connection fails,
            or the database is not schema v3.
    """
    conn = _get_conn(gobp_root)
    if conn is None:
        raise RuntimeError(
            "PostgreSQL v3 required: set GOBP_DB_URL and ensure the server is "
            f"reachable (project root: {gobp_root})"
        )
    try:
        if get_schema_version(conn) != "v3":
            conn.close()
            raise RuntimeError(
                "PostgreSQL is reachable but schema is not v3 "
                "(expected desc_l1 on nodes). Initialize v3 before running this tool."
            )
        return conn
    except RuntimeError:
        raise
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        raise RuntimeError(f"PostgreSQL v3 connection check failed: {e}") from e


def _node_desc_full_v3(node: dict[str, Any]) -> str:
    """Full description text for schema v3 ``desc_full`` column."""
    if node.get("desc_full") is not None:
        return str(node.get("desc_full", ""))
    desc = node.get("description", "")
    if isinstance(desc, dict):
        return str(desc.get("info", "") or "")
    return str(desc or "")


def upsert_node_v3(conn: PgConnection, node: dict[str, Any]) -> None:
    """Upsert one node row into PostgreSQL schema v3 (database only).

    SQL uses ``%s`` placeholders only (no string interpolation of user data).

    This is a low-level primitive: it does **not** write ``.gobp/nodes/*.md``.
    The full write-through path (PG + file backup + history) lives in
    :mod:`gobp.core.mutator_v3` (e.g. :func:`~gobp.core.mutator_v3.write_node`)
    and in file-first flows that call :mod:`gobp.mcp.pg_sync` after disk writes.
    """
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


def delete_node_v3(conn: PgConnection, node_id: str) -> None:
    """Delete node (edges CASCADE)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM nodes WHERE id = %s", (node_id,))
    conn.commit()


def upsert_edge_v3(
    conn: PgConnection,
    from_id: str,
    to_id: str,
    reason: str = "",
    code: str = "",
) -> None:
    """Upsert edge — schema v3 has no edge type column.

    ``reason`` is the full prose for the relationship (same semantic role as
    :attr:`desc_full` on nodes). ``code`` matches node ``code`` (optional snippet).
    """
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


def delete_edge_v3(conn: PgConnection, from_id: str, to_id: str) -> None:
    """Delete one edge row."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM edges WHERE from_id=%s AND to_id=%s",
            (from_id, to_id),
        )
    conn.commit()


def append_history_v3(
    conn: PgConnection,
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


def get_node_updated_at(conn: PgConnection, node_id: str) -> int | None:
    """Return ``updated_at`` epoch seconds for optimistic locking."""
    with conn.cursor() as cur:
        cur.execute("SELECT updated_at FROM nodes WHERE id = %s", (node_id,))
        row = cur.fetchone()
        return int(row[0]) if row else None


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
    """Rebuild PostgreSQL index from GraphIndex (loaded from files).

    Uses schema v3: ``TRUNCATE`` ``node_history``, ``edges``, ``nodes``, then
    upsert from ``graph_index``. If the database is not yet v3,
    :func:`create_schema_v3` is applied first.

    Tables outside the v3 graph (e.g. import locks) are not dropped.
    """
    conn = _get_conn(gobp_root)
    if conn is None:
        return {
            "ok": False,
            "message": "No PostgreSQL connection - set GOBP_DB_URL",
            "nodes_indexed": 0,
            "edges_indexed": 0,
        }

    try:
        if get_schema_version(conn) != "v3":
            create_schema_v3(conn)

        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE node_history, edges, nodes RESTART IDENTITY CASCADE"
            )
        conn.commit()

        from gobp.core.pyramid import pyramid_from_node

        all_nodes_list = (
            graph_index.all_nodes()
            if hasattr(graph_index, "all_nodes")
            else []
        )
        nodes_count = 0
        for node in all_nodes_list:
            try:
                enriched = dict(node)
                if (
                    not str(enriched.get("desc_l1", "") or "").strip()
                    or not str(enriched.get("desc_l2", "") or "").strip()
                ):
                    l1, l2 = pyramid_from_node(enriched)
                    if not str(enriched.get("desc_l1", "") or "").strip():
                        enriched["desc_l1"] = l1
                    if not str(enriched.get("desc_l2", "") or "").strip():
                        enriched["desc_l2"] = l2
                upsert_node_v3(conn, enriched)
                nodes_count += 1
            except Exception as e:
                logger.warning(
                    "rebuild_index: skip node %s: %s",
                    node.get("id", "?"),
                    e,
                )

        all_edges_list = (
            graph_index.all_edges()
            if hasattr(graph_index, "all_edges")
            else []
        )
        edges_count = 0
        for edge in all_edges_list:
            try:
                from_id = str(edge.get("from") or edge.get("from_id", "") or "")
                to_id = str(edge.get("to") or edge.get("to_id", "") or "")
                reason = str(edge.get("reason", "") or "")
                code = str(edge.get("code", "") or "")
                if from_id and to_id:
                    upsert_edge_v3(conn, from_id, to_id, reason, code)
                    edges_count += 1
            except Exception as e:
                logger.warning("rebuild_index: skip edge %s: %s", edge, e)

        return {
            "ok": True,
            "message": f"Rebuilt {nodes_count} nodes, {edges_count} edges",
            "nodes_indexed": nodes_count,
            "edges_indexed": edges_count,
        }
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return {
            "ok": False,
            "message": f"Rebuild failed: {e}",
            "nodes_indexed": 0,
            "edges_indexed": 0,
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass
