# ◈ GoBP AI USER GUIDE

Document này dành cho AI agents. Đọc trước khi tương tác với GoBP MCP server.

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
6. batch:             Cho MỌI write operations. Không create/update đơn lẻ.
7. find/get:          Default mode=summary. Chỉ mode=full khi cần debug.
8. Sau khi có IDs:    Chỉ giữ id+name. Không paste full JSON vào prompt sau.
9. 1 session = 1 mục tiêu. session:end khi xong.
10. Lỗi batch:        Chỉ retry ops bị fail, không retry toàn bộ.
```

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

## Write actions — Luôn dùng batch

### batch — Tất cả write operations trong 1 call

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

### Limits
```
Max 50 operations per batch call.
Vượt 50 → chia thành nhiều calls.
```

### Response
```
Default: summary only (~100 tokens)
  "create:5/6 edge+:8/10 merge:1/1"
  + skipped list + errors

verbose=true: full details
```

---

## Node types

| Type | Group | Tier | Dùng để |
|------|-------|------|---------|
| Decision | core | 20 | Quyết định kiến trúc đã lock |
| Invariant | core | 20 | Ràng buộc không thay đổi |
| Entity | domain | 10 | Domain objects |
| Flow | ops | 8 | User flows |
| Engine | ops | 8 | Business logic engines |
| Feature | ops | 8 | Product features |
| Screen | ops | 8 | UI screens |
| APIEndpoint | ops | 8 | API endpoints |
| TestCase | test | 2 | Test cases |
| Task | meta | 5 | Work items cho AI queue |
| Document | meta | 0 | Spec docs |
| Session | meta | 0 | Working sessions |

---

## Edge types

| Type | Ý nghĩa |
|------|---------|
| `implements` | Node thực hiện Flow/Protocol |
| `depends_on` | Node cần node kia hoạt động |
| `enforces` | Node enforce Invariant/Decision |
| `tested_by` | Node được test bởi TestCase |
| `covers` | TestCase covers Flow/Engine |
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

trustgate_engine.ops.00000002        ← Engine (ops group)
traveller_identity.domain.00000001   ← Entity (domain group)
use_otp_for_auth.core.00000001       ← Decision (core group)
auth_otp_valid.test.unit.00000001    ← TestCase (test group + kind)
meta.session.2026-04-17.a3f7c2abc    ← Session
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
❌ Dùng create: đơn lẻ → dùng batch
❌ find: keyword rộng → find:Type keyword mode=summary
❌ Paste full JSON response vào prompt sau → chỉ giữ id+name
❌ Tạo node mới mà không suggest: trước → duplicate risk
❌ Ghi mà không có session_id → bị reject
```

---

## Phụ lục — Bổ sung kỹ thuật (không thay thế nội dung CTO phía trên)

Các mục sau làm rõ **triển khai** trong repo; giữ nguyên tinh thần và thứ tự mục của CTO.

- **Tài liệu tham chiếu:** `docs/MCP_TOOLS.md` (hợp đồng tool), `docs/SCHEMA.md` (field/enum), `docs/ARCHITECTURE.md` (khái niệm).
- **Response:** JSON thường có `_dispatch` (action đã route nội bộ) để audit.
- **Read-only:** `GOBP_READ_ONLY=true` → mọi write bị từ chối.
- **`session:end`:** Server yêu cầu `session_id` và `outcome` (đúng như ví dụ lifecycle). Có thể thêm tham số như `handoff='...'` theo `PROTOCOL_GUIDE` trong `gobp/mcp/parser.py`.
- **Query Rules dòng 2 (`template`):** Chuỗi điều khiển đầy đủ nằm trong `gobp/mcp/parser.py` (`QUERY_RULES`). Ý vận hành: có khung `template: <Type>` trước khi tạo từng type; có thể gọi lại khi cần xem lại field (không đổi mục đích rule CTO).
- **Batch — đếm operation:** Mỗi **dòng** trong `ops` là một operation. Một batch có thể gồm **một** `create:` và **nhiều** `edge+:` cho cùng node mới — hợp lệ; giới hạn 50 là **tổng số dòng** mỗi lần gọi `batch`.
- **`find` phân trang:** Thêm `page_size`, `cursor`; gợi ý nằm trong `pagination_hint` của `overview:`.
- **`get_batch`:** `gobp(query="get_batch: ids='id1,id2' mode=brief")` — đọc nhiều node theo id trong một call.
- **Import nhiều file:** Mỗi file một `import: <đường_dẫn> session_id='<id>'` (cùng `session_id`).
- **Node types còn lại:** Bảng CTO liệt kê tầng hay dùng; đủ **21** type trong `gobp/schema/core_nodes.yaml` (ví dụ Node, Idea, Lesson, Concept, TestKind, Repository, Wave, CtoDevHandoff, QaCodeDevHandoff, …).
- **Edge types trong schema:** Ngoài bảng trên, `gobp/schema/core_edges.yaml` còn định nghĩa `of_kind` (TestCase → TestKind). Trên node `TestCase` có field `kind_id` trỏ tới node `TestKind`.
- **Khi graph/schema lỗi hoặc MCP cũ:** `python -m gobp.cli validate --scope all`; repair seed: `python -m gobp.cli seed-universal`; sau khi nâng package hoặc sửa schema, **Reload Window** hoặc restart Cursor để process MCP tải lại.

◈
