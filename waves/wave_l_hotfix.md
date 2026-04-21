# WAVE L HOTFIX — Find / FTS Type Parity + Session Policy + PG Mirror

**Wave:** L-Hotfix  
**Date:** 2026-04-21  
**Status:** COMPLETED  
**Scope:** MCP query protocol, PostgreSQL v3 mirror schema, optional graph-session enforcement, overview drill-down UX.

---

## Why this hotfix exists

Trong vận hành MIHOS / gobp-mihos và review MCP:

1. **`find:` lẫn type** — FTS PostgreSQL không có metadata `type`; prefix `find:Module …` không được parser nhận (thiếu type trong map cứng); token keyword thứ hai bị mất; `type=…` trong query không được dispatcher đưa vào `args`.
2. **Drill-down** — Cần `overview:` có bucket theo group + hướng dẫn workflow khi FTS trộn loại.
3. **Session** — AI dùng `session_id` opaque thay vì `session:start`; cần chế độ siết policy khi muốn.
4. **PG mirror** — Muốn lọc type ngay trên FTS sau khi sync, không chỉ fallback file index.

Wave L gom các thay đổi tương thích ngược (migration PG additive, parser mở rộng).

---

## Applied fixes (shipped)

### 1. Parser + dispatcher (`gobp/mcp/parser.py`, `gobp/mcp/dispatcher.py`)

- **`find:<Type>`** nhận mọi **`node_types`** từ schema đóng gói: `gobp/schema/core_nodes.yaml` + `extensions/mihos.yaml` (cache), không giới hạn list `_TYPE_CANONICAL` cũ.
- **Nối token keyword còn lại** vào `query` (vd. `find:Module auth flow` → type `Module`, query `auth flow`).
- **`find: … type=Invariant`** (và `type_filter=`) — dispatcher gộp **`type` / `type_filter`** từ params vào `find()` khi không có prefix type.

### 2. `overview:` drill-down (`gobp/mcp/tools/read.py`)

- **`stats.nodes_by_top_level_group`** — đếm node theo segment đầu của `group` (trước ` > `), tối đa 50 bucket.
- **`search_drill_down`** — `context` + `workflow` (overview → `find:Type` / `type=` / `group=`).
- **`suggested_next_queries`** — thêm dòng gợi ý overview trước find.
- Merge v3: **`stats.postgresql_mirror.nodes_by_type`** (từ PG sau khi có cột, xem mục 4).

### 3. Graph session policy (`gobp/mcp/session_audit.py`, `gobp/mcp/server.py`, `gobp/mcp/tools/write.py`, `docs/MCP_PROTOCOL.md`)

- Biến **`GOBP_GRAPH_SESSION_ONLY=true`** — từ chối `session_id` opaque / không tự sinh `audit:…`; bắt buộc id node **`Session`** đang `IN_PROGRESS` từ **`session:start`** (hoặc **`GOBP_SESSION_ID`** trỏ đúng id đó).
- Mô tả tool MCP nhắc policy; `MCP_PROTOCOL.md` có dòng tiếng Việt.

### 4. PostgreSQL v3 — `node_type` + FTS (`gobp/core/db.py`, `gobp/mcp/tools/read_v3.py`, `gobp/core/graph.py`)

- Cột **`nodes.node_type`** (mirror field graph **`type`**); index **`idx_nodes_node_type`**.
- **`ensure_nodes_node_type_column(conn)`** — idempotent `ALTER` + index cho DB cũ; gọi từ **`rebuild_index`** và trước các read v3 liên quan.
- **`upsert_node_v3`** — ghi `node_type`.
- **`find_v3(..., type_filter=...)`** — lọc seed + expanded theo `node_type`; payload match có **`type`**.
- **`get_v3`** — trả **`type`** từ PG.
- **`overview_v3`** — **`stats.nodes_by_type`** khi cột tồn tại.
- **`find()`** (`read.py`) — có PG v3 thì dùng FTS kèm `type_filter` (không còn ép file index chỉ vì có type); **`search_source`: `postgresql_fts`**; không PG vẫn file index.
- **`GraphIndex._hydrate_metadata_node_from_pg`** — đọc `node_type` khi có cột.

### 5. Tests

- `tests/test_session_audit.py` — strict session policy.
- `tests/test_dispatcher.py` — `find:Module`, `type=`, dispatch type filter.
- `tests/test_mcp_tools.py` — overview fields / suggestion count.
- `tests/test_wave_d.py`, `tests/test_wave16a01.py` — mock PG / routing cập nhật.
- `tests/test_db_cache.py` — upsert `node_type`, `find_v3` type filter (marker **`postgres_v3`**).
- `tests/fixtures/db_v3.py` — `minimal_v3_node(..., node_type=...)`.

---

## Operational notes

- **Sau nâng code**, chạy **`scripts/sync_file_to_pg_v3.py --root <project> --execute`** (hoặc tương đương) để backfill **`node_type`** và đồng bộ FTS. Lần MCP/read đầu cũng có thể tự `ALTER` nếu thiếu cột; giá trị type đầy đủ sau sync/rebuild.
- **`GOBP_GRAPH_SESSION_ONLY`**: thêm vào env MCP server khi muốn bắt buộc graph session (vd. gobp-mihos).

---

## Files touched (summary)

| Area | Paths |
|------|--------|
| PG schema / upsert | `gobp/core/db.py` |
| Graph hydrate | `gobp/core/graph.py` |
| Parser / protocol doc | `gobp/mcp/parser.py`, `docs/MCP_PROTOCOL.md` |
| Dispatch | `gobp/mcp/dispatcher.py` |
| MCP tool copy | `gobp/mcp/server.py` |
| Session audit | `gobp/mcp/session_audit.py` |
| Overview / find | `gobp/mcp/tools/read.py` |
| PG reads / FTS | `gobp/mcp/tools/read_v3.py` |
| Write module doc | `gobp/mcp/tools/write.py` |
| Tests + fixture | `tests/*.py`, `tests/fixtures/db_v3.py` |

---

*Wave L Hotfix — find/FTS type parity, optional graph-only sessions, PG `node_type` mirror*  
◈
