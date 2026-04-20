# WAVE H HOTFIX — GoBP MCP PostgreSQL Connection

**Wave:** H-Hotfix  
**Title:** server.py — detect GOBP_DB_URL và switch sang v3 path  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-19  
**For:** Cursor  
**Status:** READY FOR EXECUTION  
**Task count:** 2 atomic tasks  

---

## VẤN ĐỀ

```
GOBP_DB_URL được set trong claude_desktop_config.json
Nhưng MCP server vẫn report schema_version: 2.1 (file-based)

Root cause:
  gobp/mcp/server.py startup không check GOBP_DB_URL
  → Luôn dùng file-based path (v2)
  → PostgreSQL v3 code đã có nhưng không được activate
```

---

## REQUIRED READING

| # | File |
|---|---|
| 1 | `gobp/mcp/server.py` (full) |
| 2 | `gobp/core/db.py` (create_schema_v3, get_schema_version) |
| 3 | `.gobp/config.yaml` (schema_version field) |

---

## TASK 1 — server.py: detect GOBP_DB_URL on startup

**File to modify:** `gobp/mcp/server.py`

**Re-read server.py toàn bộ trước.**

Tìm phần startup/initialization. Thêm logic:

```python
import os

def _get_db_connection():
    """Get PostgreSQL connection nếu GOBP_DB_URL được set."""
    db_url = os.environ.get('GOBP_DB_URL')
    if not db_url:
        return None
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        logger.warning(f"GOBP_DB_URL set nhưng không connect được: {e}")
        return None


def _ensure_v3_schema(conn, gobp_root):
    """Ensure PostgreSQL schema v3 exists."""
    try:
        from gobp.core.db import create_schema_v3, get_schema_version
        version = get_schema_version(conn)
        if version != 'v3':
            create_schema_v3(conn)
            logger.info("PostgreSQL schema v3 initialized")
        return True
    except Exception as e:
        logger.warning(f"Cannot init v3 schema: {e}")
        return False
```

Trong startup sequence, sau khi load `gobp_root`:

```python
# Check PostgreSQL connection
_pg_conn = _get_db_connection()
if _pg_conn:
    v3_ok = _ensure_v3_schema(_pg_conn, gobp_root)
    if v3_ok:
        logger.info("GoBP running with PostgreSQL v3 backend")
        # Update config schema_version nếu cần
        _update_config_schema_version(gobp_root, 'v3')
    else:
        _pg_conn.close()
        _pg_conn = None
        logger.info("GoBP falling back to file-based backend")
else:
    logger.info("GoBP running with file-based backend (no GOBP_DB_URL)")
```

Thêm helper:

```python
def _update_config_schema_version(gobp_root, version: str):
    """Update .gobp/config.yaml schema_version."""
    try:
        import yaml
        config_path = gobp_root / '.gobp' / 'config.yaml'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            config['schema_version'] = version
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True)
    except Exception:
        pass
```

**Acceptance criteria:**
- Start server với `GOBP_DB_URL` set → log "GoBP running with PostgreSQL v3 backend"
- `version:` response → `schema_version` phản ánh đúng (v3 khi PG connected)
- Start server không có `GOBP_DB_URL` → fallback to file-based, không crash

**Commit message:**
```
Wave H Hotfix Task 1: server.py — detect GOBP_DB_URL, activate v3 PostgreSQL path
```

---

## TASK 2 — version: response update

**File to modify:** `gobp/mcp/tools/read.py` hoặc `gobp/mcp/dispatcher.py`

**Re-read `version:` handler trước.**

Update `version:` action trả về đúng `schema_version`:

```python
def get_version(index, project_root, params):
    import os
    pg_connected = bool(os.environ.get('GOBP_DB_URL'))
    
    # Check actual schema version
    schema_ver = "2.1"
    if pg_connected:
        try:
            from gobp.core.db import get_schema_version
            import psycopg2
            conn = psycopg2.connect(os.environ['GOBP_DB_URL'])
            schema_ver = get_schema_version(conn)  # 'v3' hoặc 'v2'
            conn.close()
        except Exception:
            schema_ver = "2.1"
    
    return {
        "ok": True,
        "schema_version": schema_ver,
        "postgresql_connected": pg_connected,
        # ... rest of version response
    }
```

**Acceptance criteria:**
- `version:` với PG connected → `schema_version: "v3"`, `postgresql_connected: true`
- `version:` không có PG → `schema_version: "2.1"`, `postgresql_connected: false`

**Commit message:**
```
Wave H Hotfix Task 2: version: — report actual schema_version + postgresql_connected
```

---

## POST-HOTFIX VERIFICATION

```powershell
# Start server với GOBP_DB_URL
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m gobp.mcp.server --root D:/GoBP
# Expected log: "GoBP running with PostgreSQL v3 backend"

# Sau khi restart Claude Desktop:
# gobp(query="version:") → schema_version: "v3", postgresql_connected: true
```

---

## CEO DISPATCH

### Cursor
```
Read gobp/mcp/server.py (full).
Read gobp/core/db.py.
Read waves/wave_h_hotfix.md (this file).
Execute Tasks 1 → 2.
R9-B: verify version: returns correct schema_version.
End: pytest tests/ -q --tb=no
```

### Push
```powershell
cd D:\GoBP
git add waves/wave_h_hotfix.md
git commit -m "Wave H Hotfix: server.py PostgreSQL v3 activation — 2 tasks"
git push origin main
```

---

*Wave H Hotfix — 2026-04-19 — CTO Chat*  
◈
