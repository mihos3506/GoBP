# WAVE H HOTFIX 3 — rebuild_index v3 Fix

**Wave:** H-Hotfix-3  
**Title:** Fix rebuild_index() — dùng upsert_node_v3 thay vì v2 columns  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-20  
**For:** Cursor  
**Status:** READY FOR EXECUTION  
**Task count:** 1 atomic task  

---

## VẤN ĐỀ

```
rebuild_index(gobp_root, graph_index) trong gobp/core/db.py
  → INSERT v2 columns: (id, type, name, status, topic, ...)
  → PostgreSQL đang có schema v3: (id, name, group_path, desc_l1, ...)
  → Error: column "type" of relation "nodes" does not exist

Root cause:
  rebuild_index() chưa được update khi schema v3 được implement
  Wave C/D implement upsert_node_v3() nhưng rebuild_index() vẫn dùng v2 INSERT
```

---

## REQUIRED READING

| # | File |
|---|---|
| 1 | `gobp/core/db.py` — rebuild_index() function hiện tại |
| 2 | `gobp/core/db.py` — upsert_node_v3(), upsert_edge_v3() |
| 3 | `gobp/core/graph.py` — all_nodes(), all_edges() return format |

---

## TASK 1 — Fix rebuild_index() cho schema v3

**File to modify:** `gobp/core/db.py`

**Re-read `rebuild_index()` và `upsert_node_v3()` trước.**

**Replace toàn bộ `rebuild_index()` function:**

```python
def rebuild_index(gobp_root: Path, graph_index) -> dict:
    """
    Rebuild PostgreSQL index từ GraphIndex (loaded từ files).
    
    Dùng schema v3: TRUNCATE node_history/edges/nodes,
    rồi upsert lại từ graph_index.
    
    Non-destructive với data ngoài nodes/edges tables.
    """
    conn = _get_conn()
    if conn is None:
        return {
            'ok': False,
            'message': 'No PostgreSQL connection — set GOBP_DB_URL',
            'nodes_indexed': 0,
            'edges_indexed': 0,
        }

    try:
        # Truncate v3 tables (CASCADE xóa node_history + edges)
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE node_history, edges, nodes RESTART IDENTITY CASCADE"
            )
        conn.commit()

        # Re-insert nodes
        nodes_count = 0
        all_nodes = graph_index.all_nodes() if hasattr(graph_index, 'all_nodes') else []
        for node in all_nodes:
            try:
                upsert_node_v3(conn, node)
                nodes_count += 1
            except Exception as e:
                logger.warning(f"rebuild_index: skip node {node.get('id', '?')}: {e}")

        # Re-insert edges
        edges_count = 0
        all_edges = graph_index.all_edges() if hasattr(graph_index, 'all_edges') else []
        for edge in all_edges:
            try:
                from_id = edge.get('from') or edge.get('from_id', '')
                to_id   = edge.get('to')   or edge.get('to_id', '')
                reason  = edge.get('reason', '')
                code    = edge.get('code', '')
                if from_id and to_id:
                    upsert_edge_v3(conn, from_id, to_id, reason, code)
                    edges_count += 1
            except Exception as e:
                logger.warning(f"rebuild_index: skip edge {edge}: {e}")

        return {
            'ok': True,
            'message': f'Rebuilt {nodes_count} nodes, {edges_count} edges',
            'nodes_indexed': nodes_count,
            'edges_indexed': edges_count,
        }

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return {
            'ok': False,
            'message': f'Rebuild failed: {e}',
            'nodes_indexed': 0,
            'edges_indexed': 0,
        }
```

**Acceptance criteria:**
- `rebuild_index(Path(r'D:\GoBP'), GraphIndex.load_from_disk(Path(r'D:\GoBP')))` → `{'ok': True, 'nodes_indexed': N, 'edges_indexed': M}`
- Không còn `column "type" does not exist` error
- Sau rebuild: `find: Schema` trả về nodes đúng
- `overview:` → `total_nodes > 0`

**Commit message:**
```
Wave H Hotfix3 Task 1: fix rebuild_index() — use upsert_node_v3 for schema v3
```

---

## POST-HOTFIX VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# Rebuild
D:/GoBP/venv/Scripts/python.exe -c "
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.core.db import rebuild_index
r = Path(r'D:\GoBP')
result = rebuild_index(r, GraphIndex.load_from_disk(r))
print(result)
"
# Expected: {'ok': True, 'nodes_indexed': 35, 'edges_indexed': 35+}

# Fast suite (không set GOBP_DB_URL khi chạy tests)
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

## CEO DISPATCH

### Cursor
```
Read gobp/core/db.py — rebuild_index() và upsert_node_v3().
Read gobp/core/graph.py — all_nodes() return format.
Read waves/wave_h_hotfix3.md (this file).

Execute Task 1.
Verify: python -c "rebuild_index(...)" → ok: True
End: pytest tests/ -q --tb=no (WITHOUT GOBP_DB_URL)
```

### Push
```powershell
cd D:\GoBP
git add waves/wave_h_hotfix3.md
git commit -m "Wave H Hotfix3: rebuild_index v3 — 1 task"
git push origin main
```

---

*Wave H Hotfix 3 — 2026-04-20 — CTO Chat*  
◈
