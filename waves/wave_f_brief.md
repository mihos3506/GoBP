# WAVE F BRIEF — MULTI-AGENT COORDINATION

**Wave:** F  
**Title:** Import Lock + Validate v3 + Session Watchdog  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-19  
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)  
**Status:** READY FOR EXECUTION  
**Task count:** 7 atomic tasks  
**Estimated effort:** 5-6 hours  

---

## CONTEXT

Multi-agent coordination đã được thiết kế trong ARCHITECTURE.md Section 15.
Waves C+D đã implement:
```
✓ Optimistic locking    — expected_updated_at → conflict_warning (Wave C)
✓ Cache invalidation    — invalidate_node/edge (Wave C)
✓ Active sessions       — overview: v3 shows IN_PROGRESS sessions (Wave D)
```

Wave F implement phần còn lại:
```
→ Import lock           — chặn 2 agents import cùng document
→ validate: v3          — cập nhật validate action cho schema v3
→ Session watchdog      — tự động end stale sessions (> 24h IN_PROGRESS)
→ Concurrent write test — stress test multi-agent scenario
```

---

## REFERENCED DOCUMENTS

| Doc | Focus |
|---|---|
| `docs/ARCHITECTURE.md` | Section 15 — Multi-agent coordination |
| `docs/MCP_PROTOCOL.md` | validate:, ping:, import lock |
| `docs/SCHEMA.md` | Schema v3 node structure |

---

## CURSOR EXECUTION RULES

### R1-R8: Standard (xem `.cursorrules` — QR1-QR7)

### R9 — Testing strategy
- Tasks 1-5: R9-B — module tests only
- Task 6 (tests): R9-B — `pytest tests/test_wave_f.py -v --tb=short`
- End of wave: `pytest tests/ -q --tb=no` (fast suite, NO slow)

---

## REQUIRED READING — BEFORE TASK 1

| # | File |
|---|---|
| 1 | `.cursorrules` (full) |
| 2 | `docs/ARCHITECTURE.md` (Section 15) |
| 3 | `docs/MCP_PROTOCOL.md` |
| 4 | `gobp/mcp/tools/read.py` |
| 5 | `gobp/mcp/tools/write.py` |
| 6 | `gobp/mcp/dispatcher.py` |
| 7 | `gobp/core/db.py` |
| 8 | `gobp/core/cache.py` |

---

## TASKS

---

## TASK 1 — Import Lock

**Goal:** Chặn 2 agents import cùng document cùng lúc.

**File to create:** `gobp/core/import_lock.py`

```python
"""
GoBP Import Lock.

Dùng PostgreSQL Advisory Lock để đảm bảo chỉ 1 agent
import 1 document tại 1 thời điểm.

Nếu không có PostgreSQL (chạy local/test), dùng file lock.

Usage:
    with acquire_import_lock(conn, doc_id) as lock:
        if lock.acquired:
            # do import
        else:
            return {'ok': False, 'blocked_by': lock.owner, 'hint': '...'}
"""
from __future__ import annotations
import hashlib
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ImportLockResult:
    acquired: bool
    doc_id:   str
    owner:    str = ''   # session_id của agent đang giữ lock
    hint:     str = ''


@contextmanager
def acquire_import_lock(conn, doc_id: str, session_id: str = '',
                        timeout_ms: int = 0):
    """
    PostgreSQL Advisory Lock cho import operations.

    timeout_ms=0: non-blocking (thử ngay, fail fast nếu bị lock)
    timeout_ms>0: wait tối đa N ms

    Context manager:
        with acquire_import_lock(conn, doc_id, session_id) as lock:
            if lock.acquired:
                # import
    """
    # Convert doc_id → int32 key cho pg_advisory_lock
    lock_key = _doc_id_to_lock_key(doc_id)

    acquired = False
    try:
        with conn.cursor() as cur:
            if timeout_ms == 0:
                # Non-blocking
                cur.execute(
                    "SELECT pg_try_advisory_lock(%s)",
                    (lock_key,)
                )
                acquired = cur.fetchone()[0]
            else:
                # Set lock_timeout rồi try
                cur.execute(f"SET LOCAL lock_timeout = '{timeout_ms}ms'")
                try:
                    cur.execute("SELECT pg_advisory_lock(%s)", (lock_key,))
                    acquired = True
                except Exception:
                    acquired = False

        if acquired:
            _register_lock(conn, doc_id, session_id)

        result = ImportLockResult(
            acquired=acquired,
            doc_id=doc_id,
            owner=_get_lock_owner(conn, doc_id) if not acquired else session_id,
            hint='' if acquired else (
                f"Document '{doc_id}' đang được import bởi agent khác. "
                f"Thử lại sau vài phút hoặc dùng session:resume."
            )
        )
        yield result
    finally:
        if acquired:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
            _unregister_lock(conn, doc_id)
            conn.commit()


def _doc_id_to_lock_key(doc_id: str) -> int:
    """Convert doc_id string → int32 cho pg_advisory_lock."""
    h = hashlib.md5(doc_id.encode()).digest()
    # Lấy 4 bytes đầu → int32
    return int.from_bytes(h[:4], 'big', signed=True)


def _register_lock(conn, doc_id: str, session_id: str) -> None:
    """Ghi lock metadata vào bảng import_locks."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO import_locks (doc_id, session_id, acquired_at)
                VALUES (%s, %s, extract(epoch from now())::BIGINT)
                ON CONFLICT (doc_id) DO UPDATE SET
                    session_id  = EXCLUDED.session_id,
                    acquired_at = EXCLUDED.acquired_at
            """, (doc_id, session_id))
            conn.commit()
    except Exception:
        pass  # non-critical


def _unregister_lock(conn, doc_id: str) -> None:
    """Xóa lock metadata."""
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM import_locks WHERE doc_id = %s", (doc_id,))
            conn.commit()
    except Exception:
        pass


def _get_lock_owner(conn, doc_id: str) -> str:
    """Lấy session_id đang giữ lock."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT session_id FROM import_locks WHERE doc_id = %s",
                (doc_id,)
            )
            row = cur.fetchone()
            return row[0] if row else 'unknown'
    except Exception:
        return 'unknown'


def create_import_locks_table(conn) -> None:
    """Tạo bảng import_locks nếu chưa có."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS import_locks (
                doc_id      TEXT PRIMARY KEY,
                session_id  TEXT NOT NULL DEFAULT '',
                acquired_at BIGINT NOT NULL
            )
        """)
        conn.commit()
```

**File to modify:** `gobp/core/db.py`

Thêm call `create_import_locks_table(conn)` vào `create_schema_v3()`.

**Acceptance criteria:**
- `acquire_import_lock()` với PostgreSQL: non-blocking, trả về `acquired=True/False`
- Cùng doc_id từ 2 connections → chỉ 1 acquired
- Release khi exit context manager
- `hint` rõ ràng khi bị block

**Commit message:**
```
Wave F Task 1: gobp/core/import_lock.py — PostgreSQL advisory lock for imports
```

---

## TASK 2 — Validate: v3

**Goal:** Cập nhật `validate:` action cho schema v3. Không còn validate lifecycle/read_order.

**File to modify:** `gobp/mcp/tools/read.py` (hoặc file validate hiện tại)

**Re-read validate handler trước.**

```python
def validate_v3(conn) -> dict:
    """
    validate: metadata — schema v3 compatibility check.

    Checks:
      1. Nodes có đủ required fields (name, group_path, desc_full không rỗng)
      2. ErrorCase nodes có severity hợp lệ (fatal/error/warning/info)
      3. Edges có from_id và to_id tồn tại (FK integrity)
      4. Không có orphan nodes (nodes không có edges và group != Meta)
      5. Sessions không có IN_PROGRESS quá 24h (stale)

    Returns:
      score:    0-100
      total:    tổng số nodes
      issues:   list of {node_id, issue, severity}
      summary:  human-readable
    """
    issues = []

    with conn.cursor() as cur:
        # Check 1: Required fields
        cur.execute("""
            SELECT id, name, group_path, desc_full
            FROM nodes
            WHERE name IS NULL OR name = ''
               OR group_path IS NULL OR group_path = ''
               OR desc_full IS NULL OR desc_full = ''
        """)
        for row in cur.fetchall():
            node_id, name, group, desc = row
            missing = []
            if not name:     missing.append('name')
            if not group:    missing.append('group_path')
            if not desc:     missing.append('description')
            issues.append({
                'node_id':  node_id,
                'issue':    f"Missing required fields: {', '.join(missing)}",
                'severity': 'error',
            })

        # Check 2: ErrorCase severity
        cur.execute("""
            SELECT id, severity FROM nodes
            WHERE group_path LIKE 'Error%%'
              AND (severity IS NULL OR severity = ''
                   OR severity NOT IN ('fatal', 'error', 'warning', 'info'))
        """)
        for row in cur.fetchall():
            issues.append({
                'node_id':  row[0],
                'issue':    f"ErrorCase has invalid severity: '{row[1]}'",
                'severity': 'error',
            })

        # Check 3: Dangling edges (FK)
        cur.execute("""
            SELECT e.from_id, e.to_id
            FROM edges e
            WHERE NOT EXISTS (SELECT 1 FROM nodes WHERE id = e.from_id)
               OR NOT EXISTS (SELECT 1 FROM nodes WHERE id = e.to_id)
        """)
        for row in cur.fetchall():
            issues.append({
                'node_id':  f"{row[0]} → {row[1]}",
                'issue':    'Dangling edge — node không tồn tại',
                'severity': 'warning',
            })

        # Check 4: Orphan nodes (không có edges, không phải Meta)
        cur.execute("""
            SELECT n.id, n.name, n.group_path
            FROM nodes n
            WHERE n.group_path NOT LIKE 'Meta%%'
              AND NOT EXISTS (
                  SELECT 1 FROM edges e
                  WHERE e.from_id = n.id OR e.to_id = n.id
              )
        """)
        for row in cur.fetchall():
            issues.append({
                'node_id': row[0],
                'issue':   f"Orphan node '{row[1]}' — không có edges",
                'severity': 'info',
            })

        # Check 5: Stale sessions
        stale_threshold = int(time.time()) - (24 * 3600)
        cur.execute("""
            SELECT id, name, updated_at
            FROM nodes
            WHERE group_path = 'Meta > Session'
              AND desc_full LIKE '%%IN_PROGRESS%%'
              AND updated_at < %s
        """, (stale_threshold,))
        for row in cur.fetchall():
            issues.append({
                'node_id':  row[0],
                'issue':    f"Stale session '{row[1]}' — IN_PROGRESS > 24h",
                'severity': 'warning',
            })

        # Total nodes
        cur.execute("SELECT COUNT(*) FROM nodes")
        total = cur.fetchone()[0]

    # Score: 100 - deductions per severity
    errors   = sum(1 for i in issues if i['severity'] == 'error')
    warnings = sum(1 for i in issues if i['severity'] == 'warning')

    score = max(0, 100 - (errors * 10) - (warnings * 3))

    return {
        'ok':      True,
        'score':   score,
        'total':   total,
        'issues':  issues,
        'summary': (
            f"{total} nodes, score {score}/100. "
            f"{errors} errors, {warnings} warnings, "
            f"{sum(1 for i in issues if i['severity'] == 'info')} info."
        )
    }
```

Wire vào dispatcher:
```python
'validate': lambda ...: validate_v3(conn)
```

**Acceptance criteria:**
- `validate:` → score 0-100, issues list
- ErrorCase không có severity → error issue
- Stale sessions (> 24h IN_PROGRESS) → warning
- Orphan nodes → info
- Dangling edges → warning
- Perfect graph → score 100

**Commit message:**
```
Wave F Task 2: validate: v3 — schema v3 compatibility check (5 checks)
```

---

## TASK 3 — Session Watchdog

**Goal:** Auto-end stale sessions > 24h IN_PROGRESS.

**File to create:** `gobp/core/session_watchdog.py`

```python
"""
GoBP Session Watchdog.

Tự động close stale sessions (IN_PROGRESS > 24h).
Gọi từ: overview: action, hoặc MCP startup.
"""
from __future__ import annotations
import time


STALE_THRESHOLD_HOURS = 24


def close_stale_sessions(conn) -> list[str]:
    """
    Tìm và close sessions IN_PROGRESS > STALE_THRESHOLD_HOURS.

    Returns: list of closed session IDs.
    """
    threshold = int(time.time()) - (STALE_THRESHOLD_HOURS * 3600)
    closed = []

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, desc_full, updated_at
            FROM nodes
            WHERE group_path = 'Meta > Session'
              AND desc_full LIKE '%IN_PROGRESS%'
              AND updated_at < %s
        """, (threshold,))
        stale = cur.fetchall()

    for session_id, desc_full, updated_at in stale:
        # Update desc_full: replace IN_PROGRESS → STALE_CLOSED
        new_desc = (desc_full or '').replace(
            'IN_PROGRESS', 'STALE_CLOSED'
        )
        hours_stale = (int(time.time()) - updated_at) // 3600

        # Append closure note
        new_desc += (
            f"\n\n[WATCHDOG CLOSED: session was IN_PROGRESS "
            f"for {hours_stale}h — auto-closed]"
        )

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE nodes
                SET desc_full  = %s,
                    updated_at = extract(epoch from now())::BIGINT
                WHERE id = %s
            """, (new_desc, session_id))
            conn.commit()

        closed.append(session_id)

    return closed


def run_watchdog_in_overview(conn) -> dict:
    """
    Hook để gọi từ overview: action.
    Trả về summary để include trong overview response.
    """
    closed = close_stale_sessions(conn)
    if closed:
        return {
            'watchdog_closed': len(closed),
            'closed_ids': closed,
            'hint': f"Auto-closed {len(closed)} stale session(s) > {STALE_THRESHOLD_HOURS}h",
        }
    return {}
```

**File to modify:** `gobp/mcp/tools/read.py`

Thêm watchdog call vào `overview_v3()`:

```python
from gobp.core.session_watchdog import run_watchdog_in_overview

# Trong overview_v3(), trước khi return result:
watchdog_result = run_watchdog_in_overview(conn)
if watchdog_result:
    result['watchdog'] = watchdog_result
```

**Acceptance criteria:**
- Session IN_PROGRESS > 24h → tự động STALE_CLOSED
- `overview:` response có `watchdog` field khi có sessions bị close
- Sessions mới (< 24h) không bị ảnh hưởng
- Watchdog không crash nếu không có stale sessions

**Commit message:**
```
Wave F Task 3: session_watchdog.py — auto-close stale sessions > 24h
```

---

## TASK 4 — ping: Action

**Goal:** Implement `ping:` action — health check trả về active sessions + DB status.

**File to modify:** `gobp/mcp/tools/read.py`

```python
def ping_action(conn, project_root) -> dict:
    """
    ping: — health check.

    Returns:
      ok:              bool
      db:              connected | error
      active_sessions: count
      schema_version:  v3 | v2 | unknown
      import_locks:    {doc_id: session_id} nếu có
    """
    # DB check
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        db_status = 'connected'
    except Exception as e:
        return {'ok': False, 'db': str(e)}

    # Schema version
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'nodes' AND column_name = 'desc_l1'
            """)
            schema_version = 'v3' if cur.fetchone() else 'v2'
    except Exception:
        schema_version = 'unknown'

    # Active sessions
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM nodes
                WHERE group_path = 'Meta > Session'
                  AND desc_full LIKE '%IN_PROGRESS%'
            """)
            active_sessions = cur.fetchone()[0]
    except Exception:
        active_sessions = 0

    # Import locks
    import_locks = {}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT doc_id, session_id FROM import_locks")
            import_locks = {r[0]: r[1] for r in cur.fetchall()}
    except Exception:
        pass  # table may not exist yet

    return {
        'ok':              True,
        'db':              db_status,
        'schema_version':  schema_version,
        'active_sessions': active_sessions,
        'import_locks':    import_locks,
        'hint':            'GoBP is healthy.' if not import_locks else
                           f"{len(import_locks)} import(s) in progress.',",
    }
```

Wire vào dispatcher: `'ping': ping_action`

**Acceptance criteria:**
- `ping:` → ok=True khi DB connected, schema_version=v3
- `ping:` → ok=False khi DB down
- `active_sessions` đúng count
- `import_locks` hiển thị đúng locks đang active
- Response fast (< 100ms)

**Commit message:**
```
Wave F Task 4: ping: action — health check with active_sessions + import_locks
```

---

## TASK 5 — Wire Import Lock vào batch: + import actions

**Goal:** Import actions tự động acquire lock trước khi execute.

**File to modify:** `gobp/mcp/tools/write.py`

**Re-read write handlers trước.**

Thêm import lock vào bất kỳ action nào thực hiện bulk write với `doc_id`:

```python
from gobp.core.import_lock import acquire_import_lock

def handle_import_atomic(conn, gobp_dir, args):
    """import_atomic: với import lock."""
    doc_id     = args.get('doc_id', args.get('source', 'unknown'))
    session_id = args.get('session_id', '')

    with acquire_import_lock(conn, doc_id, session_id) as lock:
        if not lock.acquired:
            return {
                'ok':      False,
                'blocked': True,
                'owner':   lock.owner,
                'hint':    lock.hint,
            }

        # Proceed với import
        return _do_import_atomic(conn, gobp_dir, args)
```

**Acceptance criteria:**
- Import với cùng `doc_id` từ 2 agents: 1 thành công, 1 nhận `blocked: true`
- Lock được release sau import xong (kể cả khi raise exception)
- `hint` rõ ràng cho agent bị block

**Commit message:**
```
Wave F Task 5: wire import lock into import_atomic: — prevent concurrent imports
```

---

## TASK 6 — Tests Wave F

**Goal:** Tests cover import lock, validate v3, session watchdog, ping.

**File to create:** `tests/test_wave_f.py`

Tests phải cover:

**Import lock:**
- `acquire_import_lock()` với mock conn: acquired=True
- 2 calls cùng doc_id: chỉ 1 acquired
- Lock released sau context exit
- `locked: true` response khi bị block

**Validate v3:**
- Node thiếu description → error issue
- ErrorCase không có severity → error issue
- Stale session → warning issue
- Perfect graph → score 100
- Score giảm theo số errors/warnings

**Session watchdog:**
- Session IN_PROGRESS < 24h → không bị close
- Session IN_PROGRESS > 24h → STALE_CLOSED
- `close_stale_sessions()` trả về list đúng

**ping: action:**
- DB connected → ok=True, schema_version=v3
- active_sessions đúng count
- import_locks hiển thị đúng

**Acceptance criteria:**
- Tất cả behaviors trên có test coverage
- Tests dùng mock/tmp_path, không cần live DB
- Existing tests không bị regression

**Commit message:**
```
Wave F Task 6: tests/test_wave_f.py — import lock, validate v3, watchdog, ping
```

---

## TASK 7 — CHANGELOG Update

**Goal:** Update `CHANGELOG.md` với Wave F entry.

**File to modify:** `CHANGELOG.md`

**Re-read CHANGELOG.md trước.**

Prepend:

```markdown
## [Wave F] — Multi-Agent Coordination — 2026-04-19

### Added
- `gobp/core/import_lock.py`: PostgreSQL advisory lock for imports
  - `acquire_import_lock()`: non-blocking, context manager
  - `import_locks` table in schema v3
- `gobp/core/session_watchdog.py`: auto-close stale sessions > 24h
  - `close_stale_sessions()`: mark IN_PROGRESS → STALE_CLOSED
  - Runs automatically on `overview:` call
- `validate: v3`: schema v3 compatibility check (5 checks)
  - Required fields, ErrorCase severity, dangling edges, orphans, stale sessions
  - Score 0-100
- `ping:` action: health check with DB status + active_sessions + import_locks
- `tests/test_wave_f.py`: multi-agent coordination coverage

### Changed
- `overview: v3`: runs session watchdog, reports closed sessions
- `import_atomic:`: acquires import lock before executing
- `create_schema_v3()`: creates import_locks table

---
```

**Commit message:**
```
Wave F Task 7: CHANGELOG.md — Wave F multi-agent coordination
```

---

## POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# ping:
# gobp(query="ping:") → ok=true, schema_version=v3

# validate:
# gobp(query="validate:") → score 100 nếu data clean

# Fast suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

## CEO DISPATCH INSTRUCTIONS

### 1. Cursor

```
Read .cursorrules (full).
Read docs/ARCHITECTURE.md (Section 15).
Read gobp/mcp/tools/read.py, gobp/mcp/tools/write.py, gobp/mcp/dispatcher.py.
Read gobp/core/db.py, gobp/core/cache.py.
Read waves/wave_f_brief.md (this file).

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute Tasks 1 → 7 sequentially.
R9-B: module tests only per task.
Task 6: pytest tests/test_wave_f.py -v --tb=short
End: pytest tests/ -q --tb=no (fast suite, NO slow)
```

### 2. Claude CLI audit

```
Audit Wave F.
Task 1: import_lock.py — PG advisory lock, acquired/blocked, release on exit
Task 2: validate: v3 — 5 checks, score 0-100
Task 3: session_watchdog — close stale > 24h, overview: calls watchdog
Task 4: ping: — ok/error, schema_version, active_sessions, import_locks
Task 5: import_atomic: acquires lock, blocked response correct
Task 6: all behaviors covered, no regression
Task 7: CHANGELOG has Wave F entry
BLOCKING: Bất kỳ fail → STOP, báo CEO.
```

### 3. Push (sau khi audit PASS)

```powershell
cd D:\GoBP
git add waves/wave_f_brief.md
git commit -m "Wave F Brief: Multi-Agent Coordination — 7 tasks"
git push origin main
```

---

*Wave F Brief — Multi-Agent Coordination*  
*2026-04-19 — CTO Chat*  
◈
