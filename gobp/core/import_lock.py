"""
GoBP Import Lock.

Dùng PostgreSQL Advisory Lock để đảm bảo chỉ 1 agent
import 1 document tại 1 thời điểm.

Nếu không có PostgreSQL (chạy local/test), bỏ qua lock (coordinated import only on PG).

Usage:
    with acquire_import_lock(conn, doc_id) as lock:
        if lock.acquired:
            # do import
        else:
            return {'ok': False, 'blocked': True, 'owner': lock.owner, 'hint': lock.hint}
"""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generator

__all__ = [
    "ImportLockResult",
    "acquire_import_lock",
    "create_import_locks_table",
]


@dataclass
class ImportLockResult:
    """Outcome of attempting to acquire the import lock."""

    acquired: bool
    doc_id: str
    owner: str = ""
    hint: str = ""


def _doc_id_to_lock_key(doc_id: str) -> int:
    """Convert doc_id string → int32 cho pg_advisory_lock."""
    h = hashlib.md5(doc_id.encode()).digest()
    return int.from_bytes(h[:4], "big", signed=True)


def create_import_locks_table(conn: Any) -> None:
    """Tạo bảng import_locks nếu chưa có."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS import_locks (
                doc_id      TEXT PRIMARY KEY,
                session_id  TEXT NOT NULL DEFAULT '',
                acquired_at BIGINT NOT NULL
            )
            """
        )
    conn.commit()


def _register_lock(conn: Any, doc_id: str, session_id: str) -> None:
    """Ghi lock metadata vào bảng import_locks."""
    try:
        create_import_locks_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO import_locks (doc_id, session_id, acquired_at)
                VALUES (%s, %s, extract(epoch from now())::BIGINT)
                ON CONFLICT (doc_id) DO UPDATE SET
                    session_id  = EXCLUDED.session_id,
                    acquired_at = EXCLUDED.acquired_at
                """,
                (doc_id, session_id),
            )
        conn.commit()
    except Exception:
        pass


def _unregister_lock(conn: Any, doc_id: str) -> None:
    """Xóa lock metadata."""
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM import_locks WHERE doc_id = %s", (doc_id,))
        conn.commit()
    except Exception:
        pass


def _get_lock_owner(conn: Any, doc_id: str) -> str:
    """Lấy session_id đang giữ lock (metadata table)."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT session_id FROM import_locks WHERE doc_id = %s",
                (doc_id,),
            )
            row = cur.fetchone()
            return str(row[0]) if row and row[0] is not None else "unknown"
    except Exception:
        return "unknown"


@contextmanager
def acquire_import_lock(
    conn: Any,
    doc_id: str,
    session_id: str = "",
    timeout_ms: int = 0,
) -> Generator[ImportLockResult, None, None]:
    """
    PostgreSQL Advisory Lock cho import operations.

    timeout_ms=0: non-blocking (thử ngay, fail fast nếu bị lock)
    timeout_ms>0: wait tối đa N ms (best-effort; may fall back to non-blocking on error)

    Nếu conn is None (no DB), acquired=True (no cross-process lock).
    """
    if conn is None:
        yield ImportLockResult(
            acquired=True,
            doc_id=doc_id,
            owner=session_id,
            hint="",
        )
        return

    lock_key = _doc_id_to_lock_key(doc_id)
    acquired = False
    hint_fail = (
        f"Document '{doc_id}' đang được import bởi agent khác. "
        f"Thử lại sau vài phút hoặc dùng session:resume."
    )

    try:
        create_import_locks_table(conn)
        with conn.cursor() as cur:
            if timeout_ms == 0:
                cur.execute("SELECT pg_try_advisory_lock(%s)", (lock_key,))
                row = cur.fetchone()
                acquired = bool(row and row[0])
            else:
                cur.execute("SET LOCAL lock_timeout = %s", (f"{timeout_ms}ms",))
                try:
                    cur.execute("SELECT pg_advisory_lock(%s)", (lock_key,))
                    acquired = True
                except Exception:
                    acquired = False
        conn.commit()

        if acquired:
            _register_lock(conn, doc_id, session_id)

        owner = session_id if acquired else _get_lock_owner(conn, doc_id)
        result = ImportLockResult(
            acquired=acquired,
            doc_id=doc_id,
            owner=owner,
            hint="" if acquired else hint_fail,
        )
        yield result
    finally:
        if acquired:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
                conn.commit()
            except Exception:
                pass
            _unregister_lock(conn, doc_id)
