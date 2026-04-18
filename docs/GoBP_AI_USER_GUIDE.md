# ◈ GoBP AI USER GUIDE

Document này dành cho AI agents. Đọc trước khi tương tác với GoBP MCP server.

**Bổ sung:** catalog đầy đủ query → [`docs/MCP_TOOLS.md`](MCP_TOOLS.md); field type chi tiết → [`docs/SCHEMA.md`](SCHEMA.md). Trong MCP, gọi `gobp(query="version:")` hoặc `overview: full_interface=true` để xem gợi ý cập nhật theo build.

---

## Query format

```
gobp(query="{action}: {params}")
gobp(query="{action} {params}")
```

---

## Query Rules (bắt buộc)

```
1. overview:          Gọi 1 lần đầu session. Không gọi lại.
2. template:          Gọi 1 lần per type trước khi tạo nodes.
3. template_batch:    Khi tạo nhiều nodes cùng type.
4. suggest:           Trước khi tạo node mới — tìm node tái sử dụng.
5. explore:           Thay cho find+get+related. Dùng compact=true.
6. batch:             Cho **hầu hết** write operations — **ưu tiên** `batch` / `quick:` (gom nhiều op một lần). Protocol vẫn có `create:` / `upsert:` đơn lẻ cho tool/script; AI nên gom vào batch để ít round-trip và dễ audit.
7. find/get:          Default mode=summary. Chỉ mode=full khi cần debug.
8. Sau khi có IDs:    Chỉ giữ id+name. Không paste full JSON vào prompt sau.
9. 1 session = 1 mục tiêu. session:end khi xong.
10. Lỗi batch:        Chỉ retry ops bị fail, không retry toàn bộ.
11. Node mới + graph có data:  Node mới (có ý nghĩa) PHẢI **relate** tới ít nhất một node đã tồn tại qua edge hợp lệ — xem **dec:d002** và checklist đầy đủ tại [`docs/IMPORT_CHECKLIST.md`](IMPORT_CHECKLIST.md). Ngoại lệ: node **đầu tiên** trong project chưa có dữ liệu.
12. Import tài liệu:   Đọc **toàn bộ** doc (hoặc toàn bộ section đã thống nhất với CEO) **trước** khi liệt kê plan nodes/edges — không đọc lướt rồi tạo nodes rồi mới nối edges sau.
13. Lesson (dec:d011): Trước khi tạo **Lesson** mới — `suggest:` / `find:` cùng **topic**. Nếu đã có Lesson phù hợp → **cập nhật** node đó (thêm takeaway, giữ nội dung còn giá trị), **không** tạo Lesson trùng topic. Quy tắc này **chỉ** cho type **Lesson** (không áp dụng kiểu “gộp” cho Engine/Flow/Task…).
```

### Import protocol (chi tiết)

Quy trình **template → đọc hết → plan (nodes+edges) → review → batch** nằm trong [`docs/IMPORT_CHECKLIST.md`](IMPORT_CHECKLIST.md).

---

## Session lifecycle

```
# Bắt đầu — bắt buộc trước mọi write
gobp(query="session:start actor='tên_ai' goal='mô tả mục tiêu'")
→ Nhận session_id — dùng cho mọi write

# Kết thúc
gobp(query="session:end outcome='kết quả' session_id='<id>'")
```

---

## Read actions

### overview: — Project state (1 lần/session)
```
gobp(query="overview:")
```

### explore: — Node + edges + duplicates = 1 call
```
gobp(query="explore: TrustGate")
gobp(query="explore: TrustGate compact=true")    ← nhẹ hơn
```

### find: — Tìm kiếm
```
gobp(query="find: mi hốt mode=summary")          ← Vietnamese OK
gobp(query="find:Engine mode=summary")            ← filter exact type
gobp(query="find: keyword mode=summary")          ← Session excluded mặc định
```

### get: — Chi tiết 1 node
```
gobp(query="get: node_id mode=brief")
gobp(query="get: node_id compact=true")           ← id+name+type only
```

### suggest: — Tìm node tái sử dụng
```
gobp(query="suggest: Payment Flow")
→ EmberEngine (keyword: payment), EarningLedger (keyword: ledger)
```

### related: — Relationships
```
gobp(query="related: node_id")
```

### template: — Frame nhập liệu
```
gobp(query="template: Engine")
→ required fields + optional fields + suggested edges + batch format
```

### template_batch: — Frame cho nhiều nodes
```
gobp(query="template_batch: Engine count=10")
→ 10 frames trống với edge suggestions
→ Điền → batch submit
→ Không giới hạn nodes hay edges per node
```

---

## Write actions — Ưu tiên batch / quick

### batch — Nhiều write operations trong một call

```
gobp(query="batch session_id='<id>' ops='
  create: Engine: TrustGate | Trust scoring engine
  create: Engine: AuthEngine | Authentication
  create: Flow: Verify Gate | GPS verification
  update: trustgate.ops.00000001 description=Updated desc
  delete: garbage.meta.00000003
  retype: wrong.meta.00000002 new_type=Engine
  merge: keep=trustgate.ops.06043392 absorb=trustgate.meta.53299456
  edge+: TrustGate --implements--> Mi Hốt Standard
  edge+: TrustGate --depends_on--> CacheEngine
  edge-: TrustGate --relates_to--> CacheEngine
  edge~: TrustGate --relates_to--> GeoIntel to=depends_on
  edge*: TrustGate --implements--> Mi Hốt Standard, Mi Hốt GPS Jitter
'")
```

### Operation reference

| Prefix | Format | Ý nghĩa |
|--------|--------|---------|
| `create:` | `Type: Name \| Description` | Tạo node — auto dedupe |
| `update:` | `id field=value` | Sửa fields — giữ fields khác |
| `replace:` | `id field=value` | Ghi đè toàn bộ — destructive |
| `retype:` | `id new_type=X` | Đổi type — ID mới, migrate edges |
| `delete:` | `id` | Xóa node + cascade edges |
| `merge:` | `keep=id absorb=id` | Gộp 2 nodes — edges migrated |
| `edge+:` | `From --type--> To` | Thêm edge — skip nếu đã có |
| `edge-:` | `From --type--> To` | Xóa edge |
| `edge~:` | `From --old--> To to=new` | Đổi type edge |
| `edge*:` | `From --type--> A, B, C` | Replace tất cả edges loại đó |

### Batch size (đúng với server hiện tại)

- **Không** còn giới hạn cố định kiểu “tối đa 50/500 ops” phía client. Danh sách ops **dài** được server xử lý theo **chunk nội bộ** (200 ops/chunk — implementation trong `gobp/mcp/tools/write.py`).
- Vẫn nên **gom logic** trong một `batch` khi có thể; chỉ chia **nhiều lệnh** `gobp()` khi payload quá lớn cho MCP/JSON hoặc cần tách theo mục tiêu (không phải vì “max 50”).

### quick: — Ghi nhanh nhiều dòng (pipe), delegate sang batch

```
gobp(query="quick: session_id='<id>' ops='Name1 | w1 | d1 | desc1\\nName2 | w2 | d2 | desc2'")
```

Một dòng = một node tối giản; engine xử lý giống batch (cũng chunk nội bộ khi dài).

### Response
```
Default: summary only (~100 tokens)
  "create:5/6 edge+:8/10 merge:1/1"
  + skipped list + errors

verbose=true: full details
```

### Hooks & lỗi (MCP server)

Trước khi ghi, server có thể **chặn sớm** (ví dụ: type không có trong schema; thiếu `session_id` cho một số thao tác). Khi lỗi, response thường có `ok: false`, `error`, và có thể có **`suggestion`** (gợi ý sửa: type hợp lệ, `session:start`, node tương tự…). Đọc `suggestion` trước khi retry.

---

## Các action đọc / bảo trì khác (tham chiếu nhanh)

| Khi cần | Ví dụ |
|--------|--------|
| Protocol / version | `gobp(query="version:")` |
| Nhiều node theo id | `gobp(query="get_batch: ids='node:a,node:b' mode=brief")` |
| Kiểm tra graph / metadata | `gobp(query="validate: metadata")`, `validate: all`, … |
| Tái tính priority | `gobp(query="recompute: priorities dry_run=true")` |
| Import file → graph | `gobp(query="import: path/to/doc.md session_id='…'")` |
| Reload sau sửa tay ngoài MCP | `gobp(query="refresh:")` |
| Thống kê latency MCP | `gobp(query="stats:")` |

Bảng đầy đủ: [`docs/MCP_TOOLS.md`](MCP_TOOLS.md). `overview:` (có thể `full_interface=true`) liệt kê catalog gợi ý.

---

## Core node types (21)

Nguồn: `gobp/schema/core_nodes.yaml` (định nghĩa field đầy đủ: `docs/SCHEMA.md`).

| Type | Mô tả ngắn |
|------|------------|
| **Node** | Container generic (entity/feature/tool trong graph) |
| **Idea** | Ý tưởng thô từ hội thoại (quote + độ chín) |
| **Decision** | Quyết định đã lock (kiến trúc / sản phẩm) |
| **Session** | Phiên làm việc (goal, actor, trạng thái) |
| **Document** | Tài liệu / spec đã import hoặc soạn |
| **Lesson** | Bài học rút ra sau sự kiện |
| **Concept** | Khái niệm / thuật ngữ (glossary) |
| **TestKind** | Loại kiểm thử (vd. unit / e2e / …) — **một node = một kind**; chi tiết field `group`, `scope`: [`docs/SCHEMA.md`](SCHEMA.md) §2.8 |
| **TestCase** | Một ca kiểm thử cụ thể; `kind_id` → TestKind; cạnh `covers` / `tested_by` — xem SCHEMA §2.8–2.9 |
| **Engine** | Engine nghiệp vụ (TrustEngine, …) |
| **Flow** | Luồng người dùng / quy trình |
| **Entity** | Thực thể domain |
| **Feature** | Tính năng sản phẩm (user-facing) |
| **Invariant** | Ràng buộc cứng phải luôn đúng |
| **Screen** | Màn hình / trang UI |
| **APIEndpoint** | Endpoint HTTP/RPC |
| **Repository** | Repo mã nguồn (metadata) |
| **Wave** | Đợt / sóng triển khai |
| **Task** | Việc trong hàng đợi AI |
| **CtoDevHandoff** | Bàn giao lane CTO → dev |
| **QaCodeDevHandoff** | Bàn giao lane QA-code → dev |

**Đọc thêm (index + validate chu trình):** `find` / `explore` / `suggest` / `related` dùng index trong RAM khi có; `validate:` có thể cảnh báo chu trình trên `depends_on` / `supersedes` — xem `gobp/core/indexes.py`, `graph_algorithms.py`.

**Nhóm id** (`id_groups` trong `.gobp/config.yaml`): `core` / `domain` / `ops` / `test` / `meta` là namespace sinh id — xem mục ID format bên dưới và SCHEMA.

---

## Edge types

| Type | Ý nghĩa |
|------|---------|
| `implements` | Node thực hiện Flow/Protocol |
| `depends_on` | Node cần node kia hoạt động |
| `enforces` | Node enforce Invariant/Decision |
| `tested_by` | Node được test bởi TestCase |
| `covers` | TestCase covers Flow/Engine |
| `of_kind` | TestCase thuộc node TestKind (bổ sung cho field `kind_id`) |
| `references` | Tham chiếu Document |
| `triggers` | Node trigger node kia |
| `validates` | Node validate node kia |
| `produces` | Node tạo ra node kia |
| `relates_to` | Quan hệ chung |
| `supersedes` | Thay thế node cũ |
| `discovered_in` | Metadata: tạo trong session nào |

---

## ID format

```
{slug}.{group}.{8digits}

trustgate_engine.ops.00000002        ← Engine (nhóm ops — ví dụ id thường)
traveller_identity.domain.00000001   ← Entity (nhóm domain)
use_otp_for_auth.core.00000001       ← Decision (nhóm core)
auth_otp_valid.test.unit.00000001    ← TestCase: {slug}.test.{kind}.{8digits} (nhóm test + loại kind)
meta.session.2026-04-17.a3f7c2abc    ← Session (định dạng đặc biệt)
```

---

## Workflow chuẩn

### Import data mới
```
1. overview:                         ← hiểu project
2. session:start                     ← bắt đầu
3. template_batch: Engine count=10   ← lấy frame
4. Điền placeholders
5. batch session_id='x' ops='...'    ← submit
6. explore: EngineA compact=true     ← verify
7. session:end                       ← kết thúc
```

### Tìm và sử dụng node
```
1. suggest: Payment Flow             ← tìm reusable
2. explore: EmberEngine              ← xem chi tiết + edges
3. Nếu cần → batch edge+            ← tạo relationship
```

### Sửa data sai
```
1. explore: TrustGate                ← thấy 3 duplicates
2. batch:
     merge: keep=id_a absorb=id_b
     merge: keep=id_a absorb=id_c
     edge~: id_a --relates_to--> X to=depends_on
```

---

## Token guide

| Action | Tokens ước tính |
|--------|:-:|
| overview: | ~800 |
| explore: compact | ~200 |
| explore: full | ~800 |
| find: mode=summary (20 results) | ~400 |
| find: mode=full (20 results) | ~2000 |
| suggest: (10 results) | ~400 |
| template: | ~300 |
| batch response (summary) | ~100 |
| batch response (verbose) | ~500+ |

---

## Những điều KHÔNG làm

```
❌ Gọi overview: mỗi lần cần data → gọi 1 lần
❌ Nhiều write mà không gom **batch** / **quick:** → tách nhóm logic / dùng quick khi format pipe
❌ find: keyword rộng → find:Type keyword mode=summary
❌ Paste full JSON response vào prompt sau → chỉ giữ id+name
❌ Tạo node mới mà không suggest: trước → duplicate risk (với **Lesson** bắt buộc tuân **dec:d011** ở rule 13)
❌ Ghi mà không có session_id → bị reject hoặc hook chặn sớm
```

---

## Phụ lục (tối thiểu)

Response thường có `_protocol` (phiên bản protocol) và có thể có `_dispatch` (audit route). Read-only: `GOBP_READ_ONLY=true`. Field / cạnh đầy đủ: `docs/SCHEMA.md`, `gobp/schema/core_nodes.yaml`, `gobp/schema/core_edges.yaml`. Import vào graph: [`docs/IMPORT_CHECKLIST.md`](IMPORT_CHECKLIST.md). Lỗi graph hoặc MCP cũ: `python -m gobp.cli validate --scope all`, `seed-universal` nếu cần, Reload Window / restart Cursor.

◈
