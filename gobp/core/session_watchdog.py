"""
GoBP Session Watchdog.

Tự động close stale sessions (IN_PROGRESS > 24h).
Gọi từ: overview: action, hoặc MCP startup.
"""

from __future__ import annotations

import time
from typing import Any

STALE_THRESHOLD_HOURS = 24


def close_stale_sessions(conn: Any) -> list[str]:
    """
    Tìm và close sessions IN_PROGRESS > STALE_THRESHOLD_HOURS.

    Returns: list of closed session IDs.
    """
    threshold = int(time.time()) - (STALE_THRESHOLD_HOURS * 3600)
    closed: list[str] = []

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, desc_full, updated_at
            FROM nodes
            WHERE group_path = 'Meta > Session'
              AND desc_full LIKE %s
              AND updated_at < %s
            """,
            ("%IN_PROGRESS%", threshold),
        )
        stale = cur.fetchall()

    for session_id, desc_full, updated_at in stale:
        new_desc = (desc_full or "").replace("IN_PROGRESS", "STALE_CLOSED")
        hours_stale = (int(time.time()) - int(updated_at)) // 3600

        new_desc += (
            f"\n\n[WATCHDOG CLOSED: session was IN_PROGRESS "
            f"for {hours_stale}h — auto-closed]"
        )

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE nodes
                SET desc_full  = %s,
                    updated_at = extract(epoch from now())::BIGINT
                WHERE id = %s
                """,
                (new_desc, session_id),
            )
            conn.commit()

        closed.append(session_id)

    return closed


def run_watchdog_in_overview(conn: Any) -> dict[str, Any]:
    """
    Hook để gọi từ overview: action.
    Trả về summary để include trong overview response.
    """
    closed = close_stale_sessions(conn)
    if closed:
        return {
            "watchdog_closed": len(closed),
            "closed_ids": closed,
            "hint": f"Auto-closed {len(closed)} stale session(s) > {STALE_THRESHOLD_HOURS}h",
        }
    return {}
