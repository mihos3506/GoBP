"""Mirror successful file mutations to PostgreSQL v3 when MCP holds ``server._pg_conn``.

File-backed writes (:mod:`gobp.core.fs_mutator`) are the source of truth; PG sync is
best-effort and must never fail the mutation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("gobp.mcp.pg_sync")


def maybe_upsert_node_v3(gobp_root: Path, node: dict[str, Any]) -> None:
    """Upsert node into PG v3 if the MCP process has an open v3 connection."""
    _ = gobp_root
    try:
        from gobp.mcp import server as mcp_server

        conn = getattr(mcp_server, "_pg_conn", None)
        if conn is None:
            return
        from gobp.core.db import get_schema_version, upsert_node_v3

        if get_schema_version(conn) != "v3":
            return

        from gobp.core.pyramid import pyramid_from_node

        enriched = dict(node)
        l1, l2 = pyramid_from_node(enriched)
        if not str(enriched.get("desc_l1", "") or "").strip():
            enriched["desc_l1"] = l1
        if not str(enriched.get("desc_l2", "") or "").strip():
            enriched["desc_l2"] = l2

        upsert_node_v3(conn, enriched)
    except Exception as e:
        logger.warning("PostgreSQL node upsert skipped (non-fatal): %s", e)


def maybe_upsert_edge_v3(gobp_root: Path, edge: dict[str, Any]) -> None:
    """Upsert edge into PG v3 if the MCP process has an open v3 connection."""
    _ = gobp_root
    try:
        from gobp.mcp import server as mcp_server

        conn = getattr(mcp_server, "_pg_conn", None)
        if conn is None:
            return
        from gobp.core.db import get_schema_version, upsert_edge_v3

        if get_schema_version(conn) != "v3":
            return

        fid = str(edge.get("from", "") or "")
        tid = str(edge.get("to", "") or "")
        reason = str(edge.get("reason", "") or "")
        code = str(edge.get("code", "") or "")
        upsert_edge_v3(conn, fid, tid, reason, code)
    except Exception as e:
        logger.warning("PostgreSQL edge upsert skipped (non-fatal): %s", e)
