"""PostgreSQL schema v3 read helpers (Wave D — find/get/context/overview/explore)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import yaml

TRAVERSE_PRIORITY: dict[str, str] = {
    "depends_on": "tier_1",
    "implements": "tier_1",
    "enforces": "tier_2",
    "covers": "tier_2",
    "discovered_in": "skip",
    "references": "tier_2",
}


def _conn_v3(project_root: Path) -> tuple[Any, bool]:
    """Return ``(connection, is_v3)`` or ``(None, False)`` if unavailable."""
    from gobp.core import db as db_mod

    conn = db_mod._get_conn(project_root)
    if conn is None:
        return None, False
    try:
        ver = db_mod.get_schema_version(conn)
        if ver != "v3":
            conn.close()
            return None, False
        return conn, True
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return None, False


def _format_find_nodes(rows: list[tuple[Any, ...]], mode: str) -> list[dict[str, Any]]:
    """Format SQL rows per pyramid mode (find: v3)."""
    result: list[dict[str, Any]] = []
    for row in rows:
        if len(row) >= 7 and mode == "full":
            node_id, name, group_path, desc_l1, desc_l2, desc_full, rank = row[:7]
        else:
            node_id, name, group_path, desc_l1, desc_l2, rank = row[:6]
            desc_full = None
        if mode == "compact":
            result.append(
                {"id": node_id, "name": name, "group": group_path}
            )
        elif mode == "summary":
            result.append(
                {
                    "id": node_id,
                    "name": name,
                    "group": group_path,
                    "desc": desc_l1 or "",
                }
            )
        elif mode == "full":
            result.append(
                {
                    "id": node_id,
                    "name": name,
                    "group": group_path,
                    "desc": (desc_full or desc_l2 or desc_l1 or ""),
                    "_rank": round(float(rank or 0), 4),
                }
            )
        else:  # brief (default)
            result.append(
                {
                    "id": node_id,
                    "name": name,
                    "group": group_path,
                    "desc": desc_l2 or desc_l1 or "",
                    "_rank": round(float(rank or 0), 4),
                }
            )
    return result


def find_v3(
    conn: Any,
    query_text: str,
    group_filter: str | None = None,
    mode: str = "summary",
    page_size: int = 20,
    cursor: str | None = None,
) -> dict[str, Any]:
    """find: v3 — BM25F-style ranking + BFS expand depth 1 + pyramid modes."""
    if not query_text.strip():
        return {"ok": False, "error": "find: requires a keyword"}

    mode_l = (mode or "summary").lower()
    if mode_l not in ("compact", "summary", "brief", "full"):
        mode_l = "summary"

    extra_col = ", n.desc_full" if mode_l == "full" else ""
    sel_cols = f"n.id, n.name, n.group_path, n.desc_l1, n.desc_l2{extra_col}"

    sql = f"""
    WITH q AS (SELECT plainto_tsquery('simple', %s) AS query),
    seed AS (
        SELECT {sel_cols},
               ts_rank_cd(n.search_vec, q.query) AS rank
        FROM nodes n, q
        WHERE n.search_vec @@ q.query
          AND (%s::text IS NULL OR n.group_path LIKE %s)
          AND (%s::text IS NULL OR n.id::text > %s::text)
        ORDER BY rank DESC
        LIMIT %s
    ),
    expanded AS (
        SELECT DISTINCT n.id, n.name, n.group_path, n.desc_l1, n.desc_l2{extra_col},
                        0.5::float8 AS rank
        FROM seed s
        JOIN edges e ON e.from_id = s.id OR e.to_id = s.id
        JOIN nodes n ON n.id = CASE
            WHEN e.from_id = s.id THEN e.to_id
            ELSE e.from_id END
        WHERE NOT EXISTS (SELECT 1 FROM seed s2 WHERE s2.id = n.id)
          AND e.from_id IS DISTINCT FROM e.to_id
    )
    SELECT * FROM (
        SELECT * FROM seed
        UNION ALL
        SELECT * FROM expanded
    ) u
    ORDER BY rank DESC
    LIMIT %s
    """

    gf = (group_filter or "").strip() or None
    like_pat = f"{gf}%" if gf else "%"
    cur_val = cursor.strip() if cursor else None
    fetch_limit = page_size + 15

    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                query_text.strip(),
                gf,
                like_pat,
                cur_val,
                cur_val,
                fetch_limit,
                fetch_limit,
            ),
        )
        rows = cur.fetchall()

    if not rows:
        return {
            "ok": True,
            "query": query_text,
            "mode": mode_l,
            "count": 0,
            "matches": [],
            "next_cursor": None,
            "page_info": {
                "next_cursor": None,
                "has_more": False,
                "page_size": page_size,
            },
            "hint": "Use mode=brief for edges context. mode=compact for large result sets.",
        }

    has_more = len(rows) > page_size
    page_rows = rows[:page_size]
    next_cursor = str(page_rows[-1][0]) if has_more else None

    nodes = _format_find_nodes(page_rows, mode_l)

    return {
        "ok": True,
        "query": query_text,
        "mode": mode_l,
        "count": len(nodes),
        "matches": nodes,
        "next_cursor": next_cursor,
        "page_info": {
            "next_cursor": next_cursor,
            "has_more": has_more,
            "page_size": page_size,
        },
        "hint": "Use mode=brief for edges context. mode=compact for large result sets.",
    }


def get_v3(conn: Any, node_id: str, mode: str = "brief") -> dict[str, Any]:
    """get: v3 — pyramid modes from PostgreSQL nodes + edges."""
    mode_l = (mode or "brief").lower()
    if mode_l not in ("brief", "full"):
        mode_l = "brief"

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, group_path, desc_l1, desc_l2,
                   desc_full, code, severity, updated_at
            FROM nodes WHERE id = %s
            """,
            (node_id,),
        )
        row = cur.fetchone()

    if not row:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    _nid, name, group_path, _l1, l2, full, code, severity, updated_at = row

    desc = l2 if mode_l == "brief" else full
    lim = 5 if mode_l == "brief" else 50

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.from_id, e.to_id, e.reason,
                   nf.name, nt.name
            FROM edges e
            LEFT JOIN nodes nf ON nf.id = e.from_id
            LEFT JOIN nodes nt ON nt.id = e.to_id
            WHERE (e.from_id = %s OR e.to_id = %s)
            LIMIT %s
            """,
            (node_id, node_id, lim),
        )
        edge_rows = cur.fetchall()

    edges = [
        {
            "from": r[0],
            "to": r[1],
            "reason": r[2] or "",
            "label": f"{r[3]} → {r[4]}",
        }
        for r in edge_rows
        if r[2]
    ]

    result: dict[str, Any] = {
        "ok": True,
        "id": node_id,
        "name": name,
        "group": group_path,
        "description": desc,
        "updated_at": updated_at,
        "edges": edges,
    }
    if code:
        result["code"] = code
    if severity:
        result["severity"] = severity
    return result


def get_batch_v3(
    conn: Any,
    ids: list[str],
    mode: str = "brief",
    since: int | None = None,
) -> dict[str, Any]:
    """get_batch: v3 — optional ``since=`` differential fetch."""
    if not ids:
        return {"ok": False, "error": "ids is required"}

    results: dict[str, Any] = {}
    fetch_ids = list(ids)

    if since is not None:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, updated_at FROM nodes WHERE id = ANY(%s)",
                (ids,),
            )
            ts_map = {r[0]: r[1] for r in cur.fetchall()}

        changed_ids: list[str] = []
        for node_id in ids:
            ts = ts_map.get(node_id)
            if ts is None or int(ts) <= int(since):
                results[node_id] = {"id": node_id, "unchanged": True}
            else:
                changed_ids.append(node_id)
        fetch_ids = changed_ids

    for node_id in fetch_ids:
        results[node_id] = get_v3(conn, node_id, mode)

    unchanged_n = sum(1 for v in results.values() if v.get("unchanged"))
    return {
        "ok": True,
        "mode": mode,
        "since": since,
        "nodes": results,
        "summary": {
            "total": len(results),
            "unchanged": unchanged_n,
            "fetched": len(fetch_ids),
        },
    }


def context_action(
    conn: Any,
    task_description: str,
    max_nodes: int = 15,
) -> dict[str, Any]:
    """context: task= — FTS seed + priority BFS with token budget."""
    if not task_description.strip():
        return {"ok": False, "error": "task description is required"}

    td = task_description.strip()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT n.id, n.name, n.group_path, n.desc_l2,
                   ts_rank_cd(n.search_vec, sq.q) AS rank
            FROM nodes n,
                 (SELECT plainto_tsquery('simple', %s) AS q) sq
            WHERE n.search_vec @@ sq.q
            ORDER BY rank DESC
            LIMIT 10
            """,
            (td,),
        )
        seed_rows = cur.fetchall()

    if not seed_rows:
        return {
            "ok": True,
            "task": task_description,
            "nodes": [],
            "hint": "No matching context found. Try broader keywords.",
        }

    seed_ids = [str(r[0]) for r in seed_rows]
    seed_nodes: list[dict[str, Any]] = [
        {
            "id": row[0],
            "name": row[1],
            "group": row[2],
            "desc": row[3],
            "relevance": "seed",
        }
        for row in seed_rows
    ]
    cap = max(0, max_nodes - len(seed_rows))
    related_nodes = _bfs_context(conn, seed_ids, cap, budget_tokens=500)
    nodes = seed_nodes + related_nodes

    return {
        "ok": True,
        "task": task_description,
        "nodes": nodes[:max_nodes],
        "summary": {
            "seed": len(seed_rows),
            "related": len(related_nodes),
            "total": min(len(nodes), max_nodes),
        },
        "hint": (
            "Context loaded. Seed nodes are direct matches. "
            "Related nodes are discovered via edges."
        ),
    }


def _infer_edge_type_from_reason(reason: str) -> str:
    """Best-effort edge type inference when DB edge type column is absent."""
    txt = str(reason or "").lower()
    if "hien thuc" in txt or "implements" in txt:
        return "implements"
    if "rang buoc" in txt or "enforces" in txt:
        return "enforces"
    if "kiem chung" in txt or "covers" in txt:
        return "covers"
    if "discovered_in" in txt or "session" in txt:
        return "discovered_in"
    if "depends_on" in txt or "phu thuoc" in txt:
        return "depends_on"
    return "references"


def _fetch_node_for_context(conn: Any, node_id: str) -> dict[str, Any] | None:
    """Load lightweight node payload used by context BFS."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, group_path, desc_l2
            FROM nodes
            WHERE id = %s
            """,
            (node_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "group": row[2],
        "desc": row[3] or "",
        "relevance": "related",
    }


def _fetch_edges_for_context(conn: Any, node_id: str) -> list[dict[str, str]]:
    """Fetch incident edges for BFS; supports schemas with/without ``type`` column."""
    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                SELECT from_id, to_id, type, reason
                FROM edges
                WHERE from_id = %s OR to_id = %s
                """,
                (node_id, node_id),
            )
            rows = cur.fetchall()
            out: list[dict[str, str]] = []
            for r in rows:
                out.append(
                    {
                        "from": str(r[0]),
                        "to": str(r[1]),
                        "type": str(r[2] or ""),
                        "reason": str(r[3] or ""),
                    }
                )
            return out
        except Exception:
            cur.execute(
                """
                SELECT from_id, to_id, reason
                FROM edges
                WHERE from_id = %s OR to_id = %s
                """,
                (node_id, node_id),
            )
            rows = cur.fetchall()
            out2: list[dict[str, str]] = []
            for r in rows:
                reason = str(r[2] or "")
                out2.append(
                    {
                        "from": str(r[0]),
                        "to": str(r[1]),
                        "type": _infer_edge_type_from_reason(reason),
                        "reason": reason,
                    }
                )
            return out2


def _bfs_context(
    conn: Any,
    seed_ids: list[str],
    max_related: int,
    budget_tokens: int = 500,
) -> list[dict[str, Any]]:
    """Priority BFS expansion from seed nodes following traverse policy."""
    if max_related <= 0:
        return []
    visited = set(seed_ids)
    queue = list(seed_ids)
    related: list[dict[str, Any]] = []
    tokens_used = 0

    while queue and len(related) < max_related and tokens_used < budget_tokens:
        current = queue.pop(0)
        for edge in _fetch_edges_for_context(conn, current):
            priority = TRAVERSE_PRIORITY.get(str(edge.get("type", "")), "skip")
            if priority == "skip":
                continue
            other_id = edge.get("to") if edge.get("from") == current else edge.get("from")
            if not other_id or other_id in visited:
                continue
            node = _fetch_node_for_context(conn, other_id)
            visited.add(other_id)
            if node is None:
                continue
            tokens_used += len(str(node.get("desc", ""))) // 4 + 20
            if tokens_used > budget_tokens:
                break
            related.append(node)
            if priority == "tier_1":
                queue.insert(0, other_id)
            else:
                if tokens_used < int(budget_tokens * 0.7):
                    queue.append(other_id)
        if tokens_used >= budget_tokens:
            break
    return related


def overview_v3(conn: Any, project_root: Path, full_interface: bool = False) -> dict[str, Any]:
    """overview: v3 — stats + active sessions (schema v3)."""
    del full_interface

    from gobp.core.session_watchdog import run_watchdog_in_overview

    watchdog_result = run_watchdog_in_overview(conn)

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM nodes")
        total_nodes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM edges")
        total_edges = cur.fetchone()[0]

        cur.execute(
            """
            SELECT split_part(group_path, ' > ', 1) AS top_group,
                   COUNT(*) AS cnt
            FROM nodes
            GROUP BY top_group
            ORDER BY cnt DESC
            """
        )
        nodes_by_group = {r[0]: r[1] for r in cur.fetchall()}

        cur.execute(
            """
            SELECT id, name, desc_l1, updated_at
            FROM nodes
            WHERE group_path = 'Meta > Session'
              AND coalesce(desc_full, '') LIKE %s
            ORDER BY updated_at DESC
            LIMIT 5
            """,
            ("%IN_PROGRESS%",),
        )
        active_rows = cur.fetchall()

    active_sessions = [
        {
            "session_id": r[0],
            "goal": (r[1] or "")[:80],
            "started": r[3],
        }
        for r in active_rows
    ]

    config_path = project_root / ".gobp" / "config.yaml"
    config: dict[str, Any] = {}
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        except Exception:
            config = {}

    out: dict[str, Any] = {
        "ok": True,
        "project": {
            "name": config.get("project_name", project_root.name),
            "id": config.get("project_id", ""),
            "root": str(project_root),
            "schema_version": "v3",
        },
        "stats": {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_by_group": nodes_by_group,
        },
        "active_sessions": active_sessions,
        "hint": (
            "Use session:start to begin. "
            "Use session:resume id='...' to continue a previous session."
        ),
    }
    if watchdog_result:
        out["watchdog"] = watchdog_result
    return out


def explore_v3(conn: Any, keyword: str) -> dict[str, Any]:
    """explore: v3 — best FTS match + reasonful edges + same-group siblings."""
    if not keyword.strip():
        return {"ok": False, "error": "Query required"}

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT n.id, n.name, n.group_path, n.desc_l2, n.desc_full, n.code, n.severity
            FROM nodes n,
                 (SELECT plainto_tsquery('simple', %s) AS q) sq
            WHERE n.search_vec @@ sq.q
            ORDER BY ts_rank_cd(n.search_vec, sq.q) DESC
            LIMIT 1
            """,
            (keyword.strip(),),
        )
        row = cur.fetchone()

    if not row:
        return {"ok": False, "error": f"No match for: {keyword}"}

    node_id, name, group_path, desc_l2, _desc_full, code, severity = row

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.from_id, e.to_id, e.reason, nf.name, nt.name
            FROM edges e
            LEFT JOIN nodes nf ON nf.id = e.from_id
            LEFT JOIN nodes nt ON nt.id = e.to_id
            WHERE (e.from_id = %s OR e.to_id = %s)
              AND coalesce(e.reason, '') <> ''
            LIMIT 20
            """,
            (node_id, node_id),
        )
        edge_rows = cur.fetchall()

    edges = [
        {
            "direction": "→" if r[0] == node_id else "←",
            "other_id": r[1] if r[0] == node_id else r[0],
            "other_name": r[4] if r[0] == node_id else r[3],
            "reason": r[2],
        }
        for r in edge_rows
    ]

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, desc_l1
            FROM nodes
            WHERE group_path = %s AND id <> %s
            LIMIT 5
            """,
            (group_path, node_id),
        )
        sibling_rows = cur.fetchall()

    siblings = [{"id": r[0], "name": r[1], "desc": r[2]} for r in sibling_rows]

    result: dict[str, Any] = {
        "ok": True,
        "id": node_id,
        "name": name,
        "group": group_path,
        "desc": desc_l2,
        "edges": edges,
        "siblings": siblings,
    }
    if code:
        result["code"] = code
    if severity:
        result["severity"] = severity
    return result


def validate_v3(conn: Any) -> dict[str, Any]:
    """
    validate: metadata — schema v3 compatibility check.

    Checks:
      1. Nodes có đủ required fields (name, group_path, desc_full không rỗng)
      2. ErrorCase nodes có severity hợp lệ (fatal/error/warning/info)
      3. Edges có from_id và to_id tồn tại (FK integrity)
      4. Không có orphan nodes (nodes không có edges và group != Meta)
      5. Sessions không có IN_PROGRESS quá 24h (stale)
    """
    issues: list[dict[str, Any]] = []

    with conn.cursor() as cur:
        # Check 1: Required fields
        cur.execute(
            """
            SELECT id, name, group_path, desc_full
            FROM nodes
            WHERE name IS NULL OR name = ''
               OR group_path IS NULL OR group_path = ''
               OR desc_full IS NULL OR desc_full = ''
            """
        )
        for row in cur.fetchall():
            node_id, name, group, desc = row
            missing: list[str] = []
            if not name:
                missing.append("name")
            if not group:
                missing.append("group_path")
            if not desc:
                missing.append("description")
            issues.append(
                {
                    "node_id": node_id,
                    "issue": f"Missing required fields: {', '.join(missing)}",
                    "severity": "error",
                }
            )

        # Check 2: ErrorCase severity
        cur.execute(
            """
            SELECT id, severity FROM nodes
            WHERE group_path LIKE 'Error%%'
              AND (severity IS NULL OR severity = ''
                   OR severity NOT IN ('fatal', 'error', 'warning', 'info'))
            """
        )
        for row in cur.fetchall():
            issues.append(
                {
                    "node_id": row[0],
                    "issue": f"ErrorCase has invalid severity: '{row[1]}'",
                    "severity": "error",
                }
            )

        # Check 3: Dangling edges (FK)
        cur.execute(
            """
            SELECT e.from_id, e.to_id
            FROM edges e
            WHERE NOT EXISTS (SELECT 1 FROM nodes WHERE id = e.from_id)
               OR NOT EXISTS (SELECT 1 FROM nodes WHERE id = e.to_id)
            """
        )
        for row in cur.fetchall():
            issues.append(
                {
                    "node_id": f"{row[0]} → {row[1]}",
                    "issue": "Dangling edge — node không tồn tại",
                    "severity": "warning",
                }
            )

        # Check 4: Orphan nodes (không có edges, không phải Meta)
        cur.execute(
            """
            SELECT n.id, n.name, n.group_path
            FROM nodes n
            WHERE n.group_path NOT LIKE 'Meta%%'
              AND NOT EXISTS (
                  SELECT 1 FROM edges e
                  WHERE e.from_id = n.id OR e.to_id = n.id
              )
            """
        )
        for row in cur.fetchall():
            issues.append(
                {
                    "node_id": row[0],
                    "issue": f"Orphan node '{row[1]}' — không có edges",
                    "severity": "info",
                }
            )

        # Check 5: Stale sessions
        stale_threshold = int(time.time()) - (24 * 3600)
        cur.execute(
            """
            SELECT id, name, updated_at
            FROM nodes
            WHERE group_path = 'Meta > Session'
              AND desc_full LIKE %s
              AND updated_at < %s
            """,
            ("%IN_PROGRESS%", stale_threshold),
        )
        for row in cur.fetchall():
            issues.append(
                {
                    "node_id": row[0],
                    "issue": f"Stale session '{row[1]}' — IN_PROGRESS > 24h",
                    "severity": "warning",
                }
            )

        cur.execute("SELECT COUNT(*) FROM nodes")
        total = cur.fetchone()[0]

    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    infos = sum(1 for i in issues if i["severity"] == "info")

    score = max(0, 100 - (errors * 10) - (warnings * 3))

    return {
        "ok": True,
        "score": score,
        "total": total,
        "issues": issues,
        "summary": (
            f"{total} nodes, score {score}/100. "
            f"{errors} errors, {warnings} warnings, "
            f"{infos} info."
        ),
    }


def ping_action(conn: Any, project_root: Path) -> dict[str, Any]:
    """
    ping: — health check.

    Returns:
      ok:              bool
      db:              connected | error
      active_sessions: count
      schema_version:  v3 | v2 | unknown
      import_locks:    {doc_id: session_id} nếu có
    """
    del project_root
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        return {"ok": False, "db": str(e)}

    try:
        from gobp.core import db as db_mod

        schema_version = db_mod.get_schema_version(conn)
    except Exception:
        schema_version = "unknown"

    active_sessions = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM nodes
                WHERE group_path = 'Meta > Session'
                  AND desc_full LIKE %s
                """,
                ("%IN_PROGRESS%",),
            )
            row = cur.fetchone()
            active_sessions = int(row[0]) if row and row[0] is not None else 0
    except Exception:
        active_sessions = 0

    import_locks: dict[str, str] = {}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT doc_id, session_id FROM import_locks")
            import_locks = {str(r[0]): str(r[1]) for r in cur.fetchall()}
    except Exception:
        pass

    n_locks = len(import_locks)
    hint = (
        "GoBP is healthy."
        if not n_locks
        else f"{n_locks} import(s) in progress."
    )

    return {
        "ok": True,
        "db": db_status,
        "schema_version": schema_version,
        "active_sessions": active_sessions,
        "import_locks": import_locks,
        "hint": hint,
    }
