# GoBP — chỉ mục tài liệu / documentation index

Tài liệu trong `docs/` mô tả **GoBP (Graph of Brainstorm Project)** — lớp bộ nhớ có cấu trúc cho AI làm việc trên một repo. Đọc kèm charter ở gốc repo: [`CHARTER.md`](../CHARTER.md), [`CLAUDE.md`](../CLAUDE.md) (quy trình audit), [`AGENTS.md`](../AGENTS.md) (vai trò agent).

---

## Trạng thái dự án (2026-04) — tóm tắt

| Khía cạnh | Mô tả ngắn |
|-----------|------------|
| **Mục đích** | Lưu ý tưởng, quyết định, bài học, spec, test, lỗi… dưới dạng **đồ thị** (node + edge), truy vấn qua **một** MCP tool `gobp(query="…")`. |
| **Schema** | **v2** — `gobp/schema/core_nodes.yaml` có **93** loại node; `core_edges.yaml` có **15** loại edge (có **`reason`**). Taxonomy: **group** (breadcrumb), **lifecycle**, **read_order**, **description** `{info, code}`. |
| **Validation** | `ValidatorV2` / `coerce_and_validate_node()` khi `schema_name` là v2 — xem `gobp/core/validator_v2.py`. |
| **ID** | Đa số node mới: `generate_id(name, group)` → `{group_slug}.{name_slug}.{8hex}`. **Session** / **TestCase** giữ định dạng đặc biệt qua `generate_external_id`. |
| **Lưu trữ** | **File-first**: `.gobp/nodes/*.md`, `.gobp/edges/relations.yaml`, `history/` append-only. **PostgreSQL** tùy chọn (`GOBP_DB_URL`) để index / MCP nhanh — không thay thế file là source of truth. |
| **MCP** | Một tool: `gobp` — `find:` / `explore:` / `get:` (brief\|full\|debug), `suggest:`, `batch:` (chunk 200 ops), `session:start|end`, v.v. — [`MCP_TOOLS.md`](./MCP_TOOLS.md). |
| **Batch `create:`** | `create: Type: Name \| mô tả` hoặc thêm **tham số đặt tên** sau `|`: `what="…"`, `fix_guide="…"`; chuỗi nhiều dòng trong dấu ngoặc không bị tách nhầm thành op mới; **thiếu `id`** → engine tự sinh (Wave 17A05). |
| **Viewer** | `python -m gobp.viewer` — đồ thị 3D + panel **v2**: breadcrumb nhóm, lifecycle/read_order, RELATIONSHIPS + **reason**, layout riêng ErrorCase — `gobp/viewer/index.html`. |
| **Tests** | ~**705+** test trong `tests/`; chạy: `pytest tests/ --override-ini="addopts="`. |

Chi tiết thay đổi theo wave: [`CHANGELOG.md`](../CHANGELOG.md).

---

## English — reading order (new contributors)

1. [`VISION.md`](./VISION.md) — intent and pains  
2. [`GoBP_ARCHITECTURE.md`](./GoBP_ARCHITECTURE.md) — system shape (layered: MCP → core → `.gobp/`)  
3. [`ARCHITECTURE.md`](./ARCHITECTURE.md) — deltas and historical update blocks (read the **Current runtime** box first)  
4. [`SCHEMA.md`](./SCHEMA.md) — formal node/edge contracts (align with YAML packs)  
5. [`MCP_TOOLS.md`](./MCP_TOOLS.md) — `gobp()` query protocol (read §0 first)  
6. [`INPUT_MODEL.md`](./INPUT_MODEL.md) / [`IMPORT_MODEL.md`](./IMPORT_MODEL.md) — how knowledge enters the graph  
7. [`IMPORT_CHECKLIST.md`](./IMPORT_CHECKLIST.md) — import workflow (dec:d002, schema v2 fields)  

**Operator-facing (Vietnamese-heavy):** [`GoBP_AI_USER_GUIDE.md`](./GoBP_AI_USER_GUIDE.md) — query cheat sheet, batch patterns, rules.

**Product one-pager:** [`GoBP_PRODUCT.md`](./GoBP_PRODUCT.md).

**Install:** [`INSTALL.md`](./INSTALL.md) or [`GoBP_INSTALL.md`](./GoBP_INSTALL.md) (PostgreSQL optional).

**Schema redesign rationale:** [`GOBP_SCHEMA_REDESIGN_v2.1.md`](./GOBP_SCHEMA_REDESIGN_v2.1.md).

---

## Source-of-truth table

| Topic | Where |
|--------|--------|
| MCP wire API | Single tool `gobp` + `query` string — [`MCP_TOOLS.md`](./MCP_TOOLS.md), code: `gobp/mcp/server.py`, `gobp/mcp/parser.py` (`PROTOCOL_GUIDE`), `gobp/mcp/dispatcher.py` |
| Batch line parsing | `gobp/mcp/batch_parser.py` (`create:` named params, quote-aware op split) |
| Writes / IDs / defaults | `gobp/mcp/tools/write.py` |
| Node / edge YAML packs | `gobp/schema/core_nodes.yaml`, `gobp/schema/core_edges.yaml` |
| Project schema version | `.gobp/config.yaml` — integer baseline **2** (`gobp.core.init.INIT_SCHEMA_VERSION`) |

---

## Legacy vs v2

Older text that lists many separate MCP tool names (`gobp_find`, `gobp_overview`, …) describes **capabilities** now reached only through **`gobp(query="…")`**. Prefer the v2 sections at the top of [`MCP_TOOLS.md`](./MCP_TOOLS.md) when implementing clients.
