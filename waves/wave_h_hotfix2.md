# WAVE H HOTFIX 2 — PostgreSQL 18 Compatibility + Write Path Sync

**Wave:** H-Hotfix-2  
**Title:** Fix ts_rank_cd PG18 incompatibility + sync batch: writes to PostgreSQL  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-20  
**For:** Cursor  
**Status:** READY FOR EXECUTION  
**Task count:** 2 atomic tasks  

---

## VẤN ĐỀ

```
Bug 1: ts_rank_cd ARRAY form removed trong PostgreSQL 17+
  Error: function ts_rank_cd(tsvector, tsquery, numeric[]) does not exist
  PostgreSQL version: 18.3
  Tất cả find: actions fail với lỗi này

Bug 2: batch: creates không sync vào PostgreSQL
  batch: trả về ok:true nhưng nodes chỉ ghi vào files
  overview: → total_nodes: 0 dù đã tạo 35 nodes
  Write path v2 (file-based) không call upsert_node_v3()
```

---

## REQUIRED READING

| # | File |
|---|---|
| 1 | `gobp/core/db.py` — tìm tất cả `ts_rank_cd` |
| 2 | `gobp/mcp/tools/write.py` — node_upsert, batch handler |
| 3 | `gobp/mcp/dispatcher.py` — batch routing |

---

## TASK 1 — Fix ts_rank_cd: PG 18 compatibility

**File to modify:** `gobp/core/db.py` (và bất kỳ file nào có `ts_rank_cd`)

**Re-read toàn bộ db.py trước. Tìm tất cả occurrences của `ts_rank_cd`.**

```bash
# Tìm tất cả chỗ dùng ts_rank_cd trong codebase
Select-String -Path "gobp\**\*.py" -Pattern "ts_rank_cd" -Recurse
```

**Fix:** Thay ARRAY form bằng simple form:

```python
# CŨ — không hoạt động trên PG 17+:
ts_rank_cd(search_vec, query, ARRAY[0.5, 1.0, 2.0, 3.0])

# MỚI — hoạt động trên mọi PG version:
ts_rank_cd(search_vec, query)
```

Nếu cần weighted ranking vẫn dùng được:
```python
# Alternative với weights riêng biệt:
ts_rank(ARRAY[0.5, 1.0, 2.0, 3.0]::float4[], search_vec, query)
```

**Acceptance criteria:**
- `find: payment` không còn lỗi ts_rank_cd
- Search results trả về đúng nodes
- Tất cả search actions hoạt động (find:, explore:, context:, suggest:)

**Commit message:**
```
Wave H Hotfix2 Task 1: fix ts_rank_cd — PG 17+ removed ARRAY form
```

---

## TASK 2 — Fix batch: write path sync to PostgreSQL

**Goal:** Khi `GOBP_DB_URL` được set và schema v3 active, `batch:` / `create:` operations phải upsert vào PostgreSQL, không chỉ ghi files.

**Re-read `gobp/mcp/tools/write.py` và `gobp/mcp/server.py` trước.**

**Vấn đề:**

```python
# Hiện tại: write path v2 chỉ ghi files
def node_upsert(index, project_root, args):
    # ... validate, generate id ...
    # Chỉ ghi .gobp/nodes/{id}.md
    # KHÔNG call upsert_node_v3(conn, node)
```

**Fix — wire PostgreSQL connection vào write path:**

```python
# Trong gobp/mcp/server.py, expose PG connection:
# _pg_conn là biến global được set trong _init_postgresql_backend()

# Trong gobp/mcp/tools/write.py:
def node_upsert(index, project_root, args):
    # ... validate, generate id, extract pyramid ...

    # Ghi file (backup)
    _write_node_file(project_root, node)

    # Ghi PostgreSQL nếu available
    from gobp.mcp import server as _server
    conn = getattr(_server, '_pg_conn', None)
    if conn is not None:
        try:
            from gobp.core.db import upsert_node_v3
            upsert_node_v3(conn, node)
        except Exception as e:
            logger.warning(f"PG upsert failed (non-blocking): {e}")

    return {'ok': True, 'id': node['id'], ...}
```

**Tương tự cho edge writes:**

```python
def edge_create(index, project_root, args):
    # ... build edge ...
    
    # Ghi file
    _write_edge_file(project_root, edge)
    
    # Ghi PostgreSQL nếu available
    from gobp.mcp import server as _server
    conn = getattr(_server, '_pg_conn', None)
    if conn is not None:
        try:
            from gobp.core.db import upsert_edge_v3
            upsert_edge_v3(conn, edge['from'], edge['to'],
                          edge.get('reason', ''))
        except Exception as e:
            logger.warning(f"PG edge upsert failed: {e}")
```

**Acceptance criteria:**
- `batch:` create nodes → `overview:` total_nodes > 0
- `find: payment` trả về nodes vừa tạo
- File backup vẫn tồn tại trong `.gobp/nodes/`
- PG failure là non-blocking (không crash, chỉ log warning)

**Commit message:**
```
Wave H Hotfix2 Task 2: wire batch:/create: writes to PostgreSQL v3
```

---

## POST-HOTFIX VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# Restart MCP server, then:
# gobp(query="session:start actor='test' goal='verify PG sync'")
# gobp(query="batch session_id='...' ops='create: Spec: Test Node | Test description for PG sync verification.'")
# gobp(query="find: Test Node")       → phải thấy node
# gobp(query="overview:")             → total_nodes > 0

# Fast suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

## CEO DISPATCH

### Cursor
```
Read gobp/core/db.py (tìm ts_rank_cd).
Read gobp/mcp/tools/write.py (node_upsert, edge handlers).
Read gobp/mcp/server.py (_pg_conn variable).
Read waves/wave_h_hotfix2.md (this file).

Execute Tasks 1 → 2 sequentially.
R9-B: verify find: works + overview nodes > 0 after batch.
End: pytest tests/ -q --tb=no
```

### Push sau khi pass
```powershell
cd D:\GoBP
git add waves/wave_h_hotfix2.md
git commit -m "Wave H Hotfix2: PG18 ts_rank_cd fix + batch write path sync — 2 tasks"
git push origin main
```

---

*Wave H Hotfix 2 — 2026-04-20 — CTO Chat*  
◈
