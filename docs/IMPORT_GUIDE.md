# ◈ GoBP IMPORT GUIDE v2
**Status:** AUTHORITATIVE  
**Date:** 2026-04-22  
**Read after:** `docs/SCHEMA.md`, `docs/MCP_PROTOCOL.md` (nếu có), `docs/edge_policy_v1.md` hoặc `gobp/schema/core_edges.yaml`  
**Audience:** Mọi AI agent khi nhập liệu vào GoBP  

**Mục lục nội dung v2:** PHẦN 0 (vận hành thật) → PHẦN 1 (chọn type + Spec vs Document + **§1.3 Entity prefix**) → PHẦN 2 (description + **§2.1 ErrorCase catalog vs `code`**) → PHẦN 3 (create/batch/…) → PHẦN 3.0 (bảng hành động MCP) → PHẦN 4–10 như trước, bổ sung lỗi & ví dụ Document.

---

## SAU KHI ĐỌC FILE NÀY, AI BIẾT

1. **Mô hình file-first + PostgreSQL tùy chọn** — không suy luận ngược từ “DB trống”
2. Chọn đúng node type; **phân biệt Spec vs Document** (group mặc định khác nhau trong schema)
3. Viết description đúng chuẩn không gây YAML lỗi
4. Chọn đúng phương pháp nhập (create / batch / quick / `import:` Document / `import_proposal`+`commit:` / upsert)
5. **Gọi đúng chuỗi `gobp(query="...")`** theo bảng hành động (§3.0)
6. Tạo edges đúng **edge policy** (Knowledge→Knowledge = `depends_on`, không đoán bừa `implements`)
7. **Ràng buộc ghi:** mọi lệnh ghi cần **chuỗi audit** `session_id` (có thể opaque / `GOBP_SESSION_ID` / id node `Session` — §0.4); thứ tự ops: node trước → cạnh sau
8. Dùng **`template:`** để lấy khung field theo schema, không đoán field bắt buộc
9. Query hiệu quả (find / get / context) và giới hạn **session:resume** (cần PG v3)
10. Nguyên tắc batch — gộp / tách / thứ tự ops
11. Ví dụ copy-paste: batch, edge+, **hai Document + depends_on** (§3.6I)
12. **Không suy luận** các mục trong §0.3–0.4; ErrorCase catalog vs `code` — **§2.1**

---

## PHẦN 0 — MÔ HÌNH VẬN HÀNH (ĐỌC TRƯỚC, KHÔNG BỎ QUA)

### 0.1 — File-first

- **Nguồn sự thật** cho graph trong repo là **file**: `.gobp/nodes/*.md`, `.gobp/edges/*.yaml`.
- **PostgreSQL** (`GOBP_DB_URL`) là **mirror / FTS / session resume** — có thể trống lúc mới khởi tạo project; không có nghĩa là “không tạo được node”.
- Đồng bộ file → DB (khi cần): script `scripts/sync_file_to_pg_v3.py` (xem README repo), hoặc luồng rebuild trong ops.

**Tránh nhầm “0 node” khi có file:** `overview:` trả **`stats.total_nodes` / `total_edges` từ graph trên đĩa** (GraphIndex). Nếu PostgreSQL mirror lệch, response có **`stats.postgresql_mirror`** và **`mirror_sync`** (kèm `hint` khi `aligned: false`). **`find:`** dùng FTS trên PG khi có kết nối v3; nếu FTS trả 0 trong khi vẫn có node trên file, runtime **tự tìm trên chỉ mục file** và gắn `search_source: file_index` + `postgresql_fts_empty: true` — không còn “im lặng trống” mà không giải thích.

**Lưu ý type-filter mới:** `find` có `type=` / `type_filter=` sẽ ưu tiên **file index** để giữ exact type match (mirror PG v3 không có cột `type` rõ ràng cho lọc chặt).

### 0.2 — Biến môi trường (Cursor / MCP)

| Biến | Vai trò |
|------|---------|
| `GOBP_PROJECT_ROOT` | Thư mục gốc project (chứa `.gobp/`, `gobp/schema/`). |
| `GOBP_SESSION_ID` | **Tùy chọn, khuyến nghị cho host.** Một chuỗi cố định mỗi run (ví dụ UUID) — lớp ghi dùng làm `session_id` khi query **không** truyền `session_id`; gom mọi node tạo trong run dưới cùng audit **không** cần node `Session` trên graph. |
| `GOBP_DB_URL` | Tùy chọn. Không set → chế độ file-only vẫn ghi node/edge lên đĩa. |

### 0.3 — Luật “KHÔNG suy luận”

1. **Không** kết luận “không tạo được Document→Document” vì DB trống — kiểm tra **đã có hai node**, **edge type đúng policy**, **session_id**.
2. **Không** dùng `implements` cho hai node cùng nhóm **Knowledge** (Document, Spec, Idea, …) trừ khi chấp nhận cảnh báo policy; chuẩn là **`depends_on`** (xem §5).
3. **Không** giả định `batch` line `edge+:` có `reason=` đầy đủ — nếu cần reason dài, dùng lệnh **`edge:`** đơn sau khi có `id` (§5 cuối).
4. **`session:resume`** chỉ hoạt động khi có **PostgreSQL schema v3** và session tồn tại trong DB — file-only thì dùng **`session:start`** mới.

### 0.4 — Ghi nhận phiên / audit (**không** đồng nhất với node `Session` trên graph)

**Nguyên tắc hệ thống:** Việc **theo dõi phiên làm việc / audit / vòng đời session** là phần **hạ tầng GoBP + host (MCP server, Cursor, script orchestrator, CLI)** — không phải nhiệm vụ cốt lõi của mô hình AI khi nhập tri thức (Engine, Spec, Flow, …).

**Hành vi code** (`gobp/mcp/session_audit.py`, dùng bởi `gobp/mcp/tools/write.py`): mọi ghi cần một **`session_id` audit** (chuỗi gắn vào node). Có ba khả năng: (1) id trỏ tới node **`Session`** trên graph — khi đó kiểm tra `status` và có thể tạo cạnh **`discovered_in`** tới session đó; (2) **opaque** (ví dụ `audit:…`, hoặc bất kỳ id không phải node `Session`) — **không** cần node Session, vẫn ghi được; (3) biến môi trường **`GOBP_SESSION_ID`** hoặc tự sinh `audit:{uuid}` khi không truyền gì (kèm cảnh báo gom nhóm audit). Đây là **log / attribution do hạ tầng quyết định**, không bắt AI tạo node Session để được phép ghi.

**Cách vận hành đúng:**

| Vai trò | Việc nên làm |
|--------|----------------|
| **Host / tooling** | **Ưu tiên:** set **`GOBP_SESSION_ID`** (một giá trị/run) hoặc truyền **`session_id`** opaque (ví dụ `audit:wave-17-fixed`) vào mọi tool call — **không** cần tạo node `Session`. **Tuỳ chọn** (khi cần **`discovered_in`** về một node Session hoặc vòng đời `IN_PROGRESS`/`COMPLETED`): gọi **`session:start`** một lần mỗi run và dùng **`session_id`** trả về; kết thúc: **`session:end`**. |
| **AI (nhập liệu)** | Dùng **`session_id`** host đưa trong ngữ cảnh; **không** coi bắt buộc phải **`session:start`** trước mỗi lần nhập. Nếu không có gì, runtime có thể tự sinh `audit:{uuid}` (kém gom nhóm — host nên set env). |

**Sai về nguyên tắc:** Bắt AI **lặp `session:start`** cho mỗi thao tác nhỏ → nhiều node **`Session`** trên graph (noise meta).

**Node `Session` trên graph:** chỉ cần khi bạn **chủ đích** theo dõi phiên như entity (goal, actor, `session:end`). Với **chỉ** audit “ai đã ghi gì”, dùng **`GOBP_SESSION_ID`** / opaque là đủ.

**`discovered_in`:** chỉ được tạo khi `session_id` trỏ tới **một node có `type: Session`** và session đó **chưa** `COMPLETED`. Với opaque audit, **không** có cạnh này — vẫn hợp lệ.

---

## PHẦN 1 — CHỌN NODE TYPE

### 1.1 — Spec vs Document (tránh nhầm UI / dropdown)

Trong `gobp/schema/core_nodes.yaml`:

| Type | `group` mặc định (breadcrumb) | Ý nghĩa |
|------|-------------------------------|--------|
| **Spec** | `Document > Spec` | Đặc tả kỹ thuật đã chốt. |
| **Document** | `Document > Document` | Tài liệu hoàn chỉnh (PRD tổng, pack nhiều spec…). |

Hai type **khác nhau**; không gộp “Spec” với “Document”. Khi gõ MCP, type chuẩn là **`Document`** (PascalCase); parser chấp nhận `document` → `Document` (xem `_TYPE_CANONICAL` trong `gobp/mcp/parser.py`).

### 1.2 — Nguyên tắc chọn

```
Câu hỏi                                  Node type
"Đây là ý tưởng chưa chốt?"              Idea
"Đây là đặc tả kỹ thuật đã chốt?"        Spec
"Đây là tài liệu hoàn chỉnh?"            Document
"Đây là bài học/rule cố định?"           LessonRule / LessonDev / LessonQA / LessonCTO
"Đây là luồng nghiệp vụ?"               Flow
"Đây là tính năng người dùng?"           Feature
"Đây là engine xử lý logic?"             Engine
"Đây là entity dữ liệu domain?"          Entity
"Đây là table database?"                 Table
"Đây là API endpoint cụ thể?"            APIEndpoint
"Đây là contract toàn bộ API?"           APIContract
"Đây là luật boolean bất biến?"          Invariant
"Đây là rule nghiệp vụ prose?"           BusinessRule
"Đây là lỗi cụ thể có code?"             ErrorCase
"Đây là nhóm lỗi 1 domain?"             ErrorDomain
"Đây là test case?"                      TestCase
"Đây là session làm việc?"              Session (auto)
"Đây là wave/task của AI?"              Wave / Task
```

### 1.3 — Entity MIHOS: tiền tố tên (`Place` vs `PlaceOwnership`)

**Đã xử trong code (`gobp/core/search.py`):** Khi tên normalize **dài hơn** query nhưng vẫn **bắt đầu bằng** query (vd. `placeownership` vs `place`), điểm prefix được **giới hạn 79** thay vì 80. Nhờ đó **`find_similar_nodes` ngưỡng 80** (batch `create:` + cảnh báo duplicate `node_upsert`) **không** coi hai entity là trùng chỉ vì tiền tố — tránh **batch bỏ sót** `create: Entity: Place` khi đã có `PlaceOwnership`.

**Hành vi còn lại:** `find:` / `suggest:` vẫn có thể liệt kê **`PlaceOwnership`** khi tìm `Place` (điểm 79 vẫn > chỉ mô tả / id); nếu cần đúng literal catalog, vẫn nên đối chiếu cột **`name`**.

**Thực hành tốt:** Trong `batch` / `edge+`, sau khi node đã có id, ưu tiên **`node:<id>`** cho cạnh để tránh mọi nhầm lẫn tên ngoài luồng search.

---

### Bảng node types đầy đủ

#### KNOWLEDGE GROUP (Document, Spec, Idea, Lesson)

| Type | Group | Mô tả | Khi nào dùng |
|------|-------|--------|--------------|
| Idea | Document > Idea | Ý tưởng thô | Chưa chốt, cần thảo luận |
| Spec | Document > Spec | Đặc tả kỹ thuật | Đã chốt, AI/dev đọc để implement |
| Document | Document > Document | Tài liệu hoàn chỉnh | Gồm nhiều Specs, có source file |
| LessonRule | Document > Lesson > Rule | Hard rules | Áp dụng mọi lúc, không ngoại lệ |
| LessonDev | Document > Lesson > Dev | Patterns cho Dev | Best practices coding |
| LessonQA | Document > Lesson > QA | Patterns cho QA | Best practices audit |
| LessonCTO | Document > Lesson > CTO | Patterns cho CTO | Architecture decisions |

#### CODE GROUP (Flow, Engine, Entity, API, DB, Security...)

| Type | Group | Mô tả | Khi nào dùng |
|------|-------|--------|--------------|
| Flow | Dev > Application > Flow | Luồng nghiệp vụ | End-to-end user journey |
| Feature | Dev > Application > Feature | Tính năng | Từ góc nhìn người dùng |
| UseCase | Dev > Application > UseCase | Use case | Scenario cụ thể trong Flow |
| Command | Dev > Application > Command | Command | CQRS write operation |
| Engine | Dev > Infrastructure > Engine | Service/Engine | Core business logic processor |
| Repository | Dev > Infrastructure > Repository | Data access | DB query abstraction |
| Entity | Dev > Domain > Entity | Domain entity | Có identity, có lifecycle |
| ValueObject | Dev > Domain > ValueObject | Value object | Immutable, no identity |
| Aggregate | Dev > Domain > Aggregate | Aggregate root | DDD aggregate |
| DomainEvent | Dev > Domain > DomainEvent | Domain event | Event từ domain action |
| APIContract | Dev > Infrastructure > API > APIContract | API contract | Toàn bộ API của 1 service |
| APIEndpoint | Dev > Infrastructure > API > APIEndpoint | Endpoint | 1 endpoint (method+path) |
| APIRequest | Dev > Infrastructure > API > APIRequest | Request schema | Body/params của endpoint |
| APIResponse | Dev > Infrastructure > API > APIResponse | Response schema | Response body |
| AuthFlow | Dev > Infrastructure > Security > AuthFlow | Auth flow | Authentication process |
| Token | Dev > Infrastructure > Security > Token | Token | JWT/session/refresh definition |
| Permission | Dev > Infrastructure > Security > Permission | Permission | Granular access right |
| Policy | Dev > Infrastructure > Security > Policy | Policy | Access control policy |
| DBSchema | Dev > Infrastructure > Database > Schema | DB schema | Database schema tổng |
| Table | Dev > Infrastructure > Database > Table | Table | Database table |
| Column | Dev > Infrastructure > Database > Column | Column | Table column |
| Migration | Dev > Infrastructure > Database > Migration | Migration | DB migration script |
| ExternalService | Dev > Infrastructure > ThirdParty > ExternalService | External API | Third-party service |
| SDK | Dev > Infrastructure > ThirdParty > SDK | SDK | External library/SDK |
| Module | Dev > Code > Module | Module | Code module/file |
| Interface | Dev > Code > Interface | Interface | Code interface/contract |
| ErrorDomain | Error > ErrorDomain | Error domain | Nhóm lỗi của 1 domain |
| ErrorCase | Error > {domain} | Error case | Lỗi cụ thể (Template 2) |

#### CONSTRAINT GROUP

| Type | Group | Mô tả | Ví dụ |
|------|-------|--------|-------|
| Invariant | Constraint > Invariant | Boolean expression | "balance >= 0" |
| BusinessRule | Constraint > BusinessRule | Rule prose | "User phải verify email trước khi đặt hàng" |

#### TEST GROUP

| Type | Group | Mô tả |
|------|-------|--------|
| TestSuite | Test > TestSuite | Bộ test cho 1 module |
| TestKind | Test > TestKind | Loại test (unit/integration/e2e) |
| TestCase | Test > TestCase | Test case cụ thể |

#### META GROUP — không có implemented field

| Type | Group | Mô tả |
|------|-------|--------|
| Session | Meta > Session | Work session của AI |
| Wave | Meta > Wave | Development wave |
| Task | Meta > Task | Task trong wave |
| Reflection | Meta > Reflection | Reflection sau wave |

---

## PHẦN 2 — VIẾT DESCRIPTION ĐÚNG CHUẨN

### Rules bắt buộc

```
R1: Plain text — tuyệt đối không dùng ký tự YAML đặc biệt
    SAI:  "Config: {key: value} | pipe | #comment"
    ĐÚNG: "Config with key-value format, pipe separator for options"

R2: Không dùng dấu : trong description value
    SAI:  "Role: Developer — execute: task"
    ĐÚNG: "Developer role responsible for executing tasks"

R3: Không dùng { } [ ] trong description
    SAI:  "Returns {id: uuid, status: string}"
    ĐÚNG: "Returns object containing id as UUID and status as string"

R4: Không dùng | # > ! * & trong description
    SAI:  "Options: A | B | C"
    ĐÚNG: "Options include A, B, or C"

R5: Không xuống dòng trong description — 1 đoạn liên tục
    SAI:  "Step 1: do X\nStep 2: do Y"
    ĐÚNG: "Process starts with X then proceeds to Y"

R6: Description đủ dài để AI hiểu không cần đọc thêm
    SAI:  "Payment handler"
    ĐÚNG: "Handles financial transactions between users. Validates
           balance before debit, executes atomic credit/debit pair.
           SLA p99 under 300ms. Exposes REST API."

R7: code field được dùng cho technical content
    code field ĐƯỢC phép chứa code syntax, file paths, JSON
    Khi implemented=true: code chứa file path đến implementation
```

### Mẫu description theo type

```
Engine:
  "{Tên} handles {domain}. {Core responsibility}. {Key behaviors}.
   {Constraints or SLA}."

Flow:
  "User {action}, system {step1}, then {step2}, resulting in {outcome}.
   {Error handling}. {Rate limits if any}."

Table:
  "Stores {what data}. Each row represents {one unit of data}.
   {Key relationships}. {Ownership}. {Lifecycle/soft delete}."

Invariant:
  "{Boolean expression stated simply}. {Why this must hold}.
   Enforced at {where}. Violation triggers {consequence}."

ErrorCase (name = catalog ID; field code = GoBP pattern only):
  name: AUTH_001 | MIHOS catalog — ngắn, stable; find theo mã tài liệu
  code: AUTH_W_001 | Bắt buộc ^[A-Z]+_[FEWI]_[0-9]{3}$ — map severity từ doc (vd. transient→W, fatal→F)
  description: "When session expired. HTTP 401 transient. User must re-authenticate."
  context: flows/features (không rỗng) — phân biệt cùng message ở nhiều flow

Spec:
  "{What this specifies and why}. {Key rules or constraints}.
   {How AI/dev uses this spec}."
```

### 2.1 — ErrorCase: catalog ngoài (`AUTH_001`) vs field `code` GoBP (`AUTH_W_001`)

Tài liệu bên ngoài (vd. MIHOS DOC-13) thường dùng mã **không** có ký tự severity (`AUTH_001`, `VAL_001`). Schema GoBP vẫn bắt buộc **`code`** theo pattern **`^[A-Z]+_[FEWI]_[0-9]{3}$`** — **không** nới schema để `code` = `AUTH_001` thuần (tránh trùng nghĩa giữa dự án, mất governance).

**Convention chốt (import / Layer 2):**

| Field | Giá trị | Lý do |
|--------|---------|--------|
| **`name`** | `AUTH_001`, `VAL_001`, … | ID catalog MIHOS — **unique trong graph**, ngắn; `find:` theo mã tài liệu. **Không** cần trùng `code`. |
| **`code`** | `AUTH_W_001`, `AUTH_F_002`, … | **Machine ID** GoBP; chữ **F/E/W/I** phải khớp **severity thật** (map từ mô tả doc). |
| **`description`** | Semantic + HTTP + hành vi | **Intent search** (vd. `session`, `401`); không nhét chuỗi tự do vào `code` nếu phá pattern. |
| **`context`** | `flows` / `features` / … | **Không để trống** — phân biệt khi cùng concept (vd. “Session expired”) ở nhiều flow/section. |

**Search:** `find: AUTH_001` → khớp **`name`**; từ khóa mơ hồ (vd. `session`) → chủ yếu **`description`** / context sau enrich — không kỳ vọng một `name` chứa hết semantic.

**Các field bắt buộc khác** (`trigger`, `severity`, `handling`, `fix`, …) — lấy đúng từ `template: ErrorCase` và `docs/SCHEMA.md`.

---

## PHẦN 3 — PHƯƠNG PHÁP NHẬP LIỆU

### 3.0 — Bảng hành động MCP (chuẩn gọi `gobp(query="...")`)

**Nguồn thật:** `gobp/mcp/parser.py` (`PROTOCOL_GUIDE`), `gobp/mcp/dispatcher.py`. Danh dưới đây là tập tối thiểu AI cần; catalog đầy đủ (rất dài): `gobp(query="overview: full_interface=true")` hoặc `gobp(query="version:")`.

| Nhóm | Action | Ghi chú ngắn |
|------|--------|----------------|
| Trạng thái | `overview:` | Thống kê project; `full_interface=true` trả JSON lớn. |
| | `version:` | Phiên bản protocol / GoBP / PostgreSQL. |
| | `refresh:` | Reload `GraphIndex` từ đĩa (sau khi sửa tay `.md`/schema). |
| | `ping:` | Kiểm tra PG v3 (cần `GOBP_DB_URL`). |
| Đọc | `find: …`, `find:Engine …` | Tìm theo từ khóa / type. |
| | `get: node:…`, `signature:`, `related:`, `context` | Chi tiết node / láng giềng. |
| | `template:`, `template: Engine` | Catalog types hoặc khung field theo schema (§3.0b). |
| | `template_batch: Engine count=5` | Mẫu batch nhiều node cùng type. |
| Ghi | `create:Type …` | Cần **`session_id` audit** (tham số, `GOBP_SESSION_ID`, hoặc tự sinh `audit:…` — §0.4). |
| | `upsert:`, `update:`, `delete:`, `retype:`, `edit:` | Idempotent / sửa / xóa / đổi type (xem MCP). |
| | `edge: node:a --type--> node:b reason='…'` | Một cạnh; hỗ trợ `reason=` dài; nếu root không có `gobp/schema`, runtime fallback sang package schema. |
| Batch | `batch session_id='…' ops='…'` | Nhiều dòng `create:` / `edge+:` / `edge-` / `edge*` / `edge~` (§3.2). |
| | `quick: session_id='…' ops='…'` | Mỗi dòng mặc định type **Node** (§3.3). |
| Session | `session:start …`, `session:end …` | Tuỳ chọn: mỗi `start` tạo **một** node `Session` — chỉ khi cần graph Session; audit thường dùng opaque / `GOBP_SESSION_ID` thay thế (§0.4). |
| | `session:resume id='meta.session.…'` | **Chỉ** khi có **PostgreSQL schema v3** + id là node Session trong DB (§0.3). |
| Import | `import: path/to.md session_id='…'` | **Đăng ký Document** từ file (upsert node), **không** phải `import_proposal()` đầy đủ (§3.4). |
| | `commit: imp:… accept=all session_id='…'` | Commit file `.gobp/proposals/*.pending.yaml` (§3.4). |
| Khác | `validate:`, `lock:Decision`, `stats:`, … | Bảo trì / governance — xem `PROTOCOL_GUIDE`. |

**Quy tắc thứ tự (áp dụng mọi luồng ghi):**

1. Có **chuỗi audit** cho write: tham số `session_id`, hoặc **`GOBP_SESSION_ID`**, hoặc (cuối cùng) tự sinh trong runtime — **không** bắt buộc là node `Session` trên graph (§0.4).
2. Tạo / cập nhật **node** (create / batch / upsert).
3. Tạo **cạnh** sau khi hai đầu đã có id hoặc tên đã resolve trong cùng batch.
4. Nếu đang dùng **node `Session`** (graph): `session:end` khi xong; nếu chỉ audit opaque/env — **không** bắt buộc `session:end`. `validate:` khi cần.

### 3.0b — `template:` và `template_batch:` (không đoán field)

**Catalog** — liệt kê mọi `node_types` trong schema đang load:

```
gobp(query="template:")
```

**Khung field** — required/optional theo `gobp/schema/core_nodes.yaml` (và `v2_template` nếu `schema_name: gobp_core_v2`):

```
gobp(query="template: Document")
gobp(query="template: ErrorCase")
```

Response gồm `frame.required` / `frame.optional`, `batch_format`, `batch_example`, `suggested_edges`. Dùng đúng các key đó trong `create:` hoặc trong `batch`, không bịa tên field.

**Batch mẫu** — nhiều chỗ trống cùng một type:

```
gobp(query="template_batch: Flow count=3")
```

### 3.1 — create: — 1 node đơn lẻ

```
Dùng khi: Test nhanh, 1 node đơn, không có nodes liên quan
Token cost: ~50 tokens

gobp(query="create:Engine name='PaymentService' session_id='...'")
```

### 3.2 — batch: — nhiều nodes + edges

```
Dùng khi: 2+ nodes liên quan nhau — đây là phương pháp chính
Format: nodes TRƯỚC edges
Token cost: ~100 tokens per batch call (summary only)
Auto-chunk: GoBP tự chia theo chunk nội bộ (mặc định ~200 ops/chunk)

gobp(query="batch session_id='...' ops='
  create: Engine: PaymentService | Handles payments. Validates balance
    before debit. SLA p99 300ms.
  create: Table: payments | Stores all payment transactions.
    Each row is 1 payment attempt. Owned by PaymentService.
  create: ErrorCase: Payment Timeout | When payment processor
    exceeds 10s timeout. group=Error > Payment severity=error

  edge+: PaymentService --depends_on--> payments
  edge+: Payment Timeout --affects--> PaymentService
'")
```

Trong `batch`, cạnh dùng tiền tố **`edge+:`** (không phải `edge:`). Endpoint là **tên node** (như trong `create:`) hoặc **id** (`node:…`, `doc:…`); resolver khớp tên sau khi các `create:` phía trên đã chạy trong cùng batch.

**Một node → nhiều cạnh cùng loại (fan-out):** tách target bằng dấu phẩy trên **một** dòng `edge+:`:

```
edge+: PaymentService --depends_on--> orders_audit, payments_archive
```

→ Mỗi target sau dấu phẩy là một cạnh `depends_on` riêng. `edge-:` cũng hỗ trợ nhiều target tương tự. `edge*:` (thay thế toàn bộ cạnh cùng type đi ra) vốn đã dùng danh sách phẩy; `edge~:` chỉ **một** target + hậu tố ` to=…`.

**Chuỗi `ops=` (batch / quick):** truyền `ops='…'` với **một** lớp quote bọc ngoài; mỗi dòng không rỗng là một op (`create:`, `edge+:`, … — danh sách prefix trong `gobp/mcp/batch_parser.py`). Tránh nháy đơn lồng nhau không khớp (parser có kiểm tra quote chưa đóng). Nội dung dài hoặc ký tự đặc biệt: ưu tiên mô tả ngắn trong batch, chi tiết bổ sung bằng `edit:` / file node sau.

### 3.3 — quick: — capture nhanh

```
Dùng khi: Capture nhanh nhiều ý tưởng, enrich sau
Format MCP: Name | mô tả (tối thiểu 2 phần); tùy chọn thêm category và wave —
  Name | category | wave | description (tối đa 4 phần, pipe-separated)
Mặc định mỗi dòng tạo node type **Node**; cột 2–3 (category, wave) được ghi vào nội dung,
không tự gán type schema — muốn đúng ErrorCase / Invariant / Flow thì dùng `create:` trong
`batch:` hoặc `retype:` / `edit:` sau quick.
Token cost: minimal

gobp(query="quick: session_id='...' ops='
  Payment Timeout | Error | Wave 3 | Timeout in payment processing
  Order Total Rule | Constraint | Wave 3 | Total must equal sum of items
  Checkout Flow | Application | Wave 3 | End-to-end checkout journey
'")

Sau quick: → dùng get: để enrich từng node
```

### 3.4 — `import:` (MCP) vs luồng `import_proposal` + `commit:`

Hai luồng **khác nhau** — đừng trộn:

#### A — `import:` qua MCP (đăng ký Document từ file)

**Hành vi thật** (`gobp/mcp/dispatcher.py`): đọc file (relative `project_root`), tính `doc:…` id, **upsert một node `Document`** (metadata, hash, sections). **Không** tạo file `.pending.yaml`, **không** trả `proposal_id` dạng `imp:…` để commit.

```
gobp(query="import: docs/SPEC.md session_id='audit:run-1'")
```

→ Kết quả: `document_node`, `sections`, gợi ý bước tiếp (`create:Node` / `edge:` nối tới `doc:…`). **`session_id`** là chuỗi audit (opaque hoặc id node `Session` — không còn yêu cầu “phải có Session trên graph”).

#### B — `import_proposal()` (Python) + `commit:` (proposal đã review)

Dùng khi cần **nhiều node + edge** trong một proposal YAML, review trước khi ghi: gọi **`gobp.mcp.tools.import_.import_proposal(...)`** với đủ field (`source_path`, `proposal_type`, `ai_notes`, `proposed_nodes`, `proposed_edges`, `confidence`, `session_id`) — không có chuỗi query MCP một dòng cho payload đầy đủ.

Sau khi có file `.gobp/proposals/<id>.pending.yaml`, **commit** qua MCP:

```
gobp(query="commit: imp:2026-04-21_my_doc accept=all session_id='audit:run-1'")
```

**Bắt buộc:** `proposal_id`, `accept` ∈ `{all, partial, reject}`, **`session_id`** (chuỗi audit — resolve giống mọi write khác, §0.4). Tuỳ chọn: `dry_run=true` để chỉ validate.

```
gobp(query="commit: imp:2026-04-21_my_doc accept=all session_id='audit:run-1' dry_run=true")
```

### 3.5 — upsert: — idempotent

```
Dùng khi: Không chắc node đã tồn tại, muốn create-or-update
Dùng trong: import scripts, automated pipelines

gobp(query="upsert:Engine dedupe_key='name' name='PaymentService'
            session_id='...'")
→ Tạo mới nếu chưa có
→ Update nếu đã có (theo dedupe_key)
```

### 3.6 — Ví dụ thêm (copy-paste)

**A — Fan-out: một `from`, nhiều `to`, cùng `edge_type`**

```
gobp(query="batch session_id='{SESSION}' ops='
create: Engine: BillingCore | Orchestrates invoicing and settlement
create: Table: invoices | Invoice header and line items
create: Table: payments | Payment attempts and settlement rows
create: Flow: MonthlyClose | Month-end billing close process
edge+: BillingCore --depends_on--> invoices, payments
edge+: MonthlyClose --implements--> BillingCore
'")
```

**B — Nối tới node đã tồn tại bằng id (prefix `doc:`, `node:`, …)**

```
gobp(query="batch session_id='{SESSION}' ops='
create: Entity: CustomerProfile | Customer master record and preferences
edge+: CustomerProfile --depends_on--> doc:docs_domain_model_v1
'")
```

**C — Hai bước: `suggest:` rồi mới `batch:` (tránh trùng dec:d011)**

```
gobp(query="suggest: NotificationService")
→ Đọc suggestions; nếu không trùng thì tạo:

gobp(query="batch session_id='{SESSION}' ops='
create: Engine: NotificationService | Outbound email and push dispatch
create: Feature: EmailDigest | Weekly digest subscription
edge+: NotificationService --depends_on--> EmailDigest
'")
```

**D — `quick:` tối thiểu 2 cột (chỉ Name + mô tả, type = Node)**

```
gobp(query="quick: session_id='{SESSION}' ops='
Idempotency keys for webhooks | Store and verify idempotency keys on inbound callbacks
'")
```

**E — Nhiều cạnh kiểu Test → Code (`covers`)**

```
gobp(query="batch session_id='{SESSION}' ops='
create: Flow: UserLogin | Username password and MFA login path
create: TestCase: LoginHappyPath | Successful login with valid credentials
create: TestCase: LoginMfaPath | Login with MFA challenge success
edge+: LoginHappyPath --covers--> UserLogin
edge+: LoginMfaPath --covers--> UserLogin
'")
```

**F — `edge*:` xóa mọi cạnh `implements` đi ra từ hub rồi gắn lại tập đích mới**

```
gobp(query="batch session_id='{SESSION}' ops='
create: Engine: BillingCore | Billing orchestration service
create: Spec: SpecBilling | Billing API and rate plans
create: Spec: SpecLedger | Ledger posting and reconciliation
edge*: BillingCore --implements--> SpecBilling, SpecLedger
'")
```
*(Trong cùng batch: tạo hub + spec trước dòng `edge*:`; `edge*` xóa mọi cạnh `implements` hiện có từ `BillingCore` rồi tạo đúng một cạnh tới mỗi target trong danh sách.)*

**G — `edge~:` đổi loại cạnh (một target)**

```
gobp(query="batch session_id='{SESSION}' ops='
edge~: OrderService --relates_to--> orders to=depends_on
'")
```

**H — `edge-:` gỡ nhiều cạnh cùng loại (danh sách phẩy)**

```
gobp(query="batch session_id='{SESSION}' ops='
edge-: BillingCore --depends_on--> legacy_audit, deprecated_cache
'")
```

**I — Hai Document + quan hệ Knowledge→Knowledge (`depends_on`)**

Hai tài liệu cùng nhóm Knowledge: **không** dùng `implements` giữa chúng (policy); dùng **`depends_on`** để “PRD tổng” phụ thuộc “Spec chi tiết”, hoặc ngược lại tùy nghiệp vụ.

```
gobp(query="batch session_id='{SESSION}' ops='
create: Document: PRD Checkout 2026 | Tổng quan sản phẩm checkout, scope và ưu tiên.
create: Document: Spec Payment Hooks | Chi tiết webhook, idempotency, retry.
edge+: PRD Checkout 2026 --depends_on--> Spec Payment Hooks
'")
```

*(Tên sau `create: Document:` phải khớp chính xác phần tên trong `edge+:`; hoặc dùng `doc:…` sau khi đã có id.)*

---

## PHẦN 4 — NGUYÊN TẮC BATCH

### Khi nào gộp vào 1 batch

```
GỘP khi các nodes:
  Thuộc cùng 1 domain hoặc feature
  Có edges kết nối nhau
  Được tạo trong cùng 1 session
  Tổng dưới 500 ops

VÍ DỤ đúng — gộp toàn bộ checkout domain:
  batch ops='
    create: Spec: SpecCheckout | Checkout requirements overview
    create: Flow: Checkout Flow | ...
    create: Engine: OrderService | ...
    create: Table: orders | ...
    create: Invariant: Order Total Non-Negative | ...
    create: ErrorCase: Checkout Failed | ...
    edge+: Checkout Flow --implements--> SpecCheckout
    edge+: OrderService --depends_on--> orders
    edge+: Order Total Non-Negative --enforces--> orders
  '
  (Tên bên phải `edge+:` phải khớp tên trong `create:` hoặc id có sẵn trên graph.)
```

### Khi nào tách batch

```
TÁCH khi:
  Nodes thuộc domains khác không liên quan
  Tổng ops vượt 500 (GoBP auto-chunk nhưng tốt hơn là tách chủ động)
  Cần verify kết quả trước khi tiếp tục
  Import từ nhiều documents riêng biệt

VÍ DỤ đúng — tách 2 domains:
  Batch 1: Payment domain (Flow + Engine + Table + Errors)
  Batch 2: Auth domain (AuthFlow + Token + Permission + Errors)
```

### Thứ tự BẮTBUỘC trong 1 batch

```
1. Document/Spec nodes (top-level knowledge)
2. Flow/Feature nodes (application layer)
3. Engine/Service nodes (infrastructure)
4. Table/Column/DB nodes (data layer)
5. Constraint nodes (Invariant, BusinessRule)
6. Error nodes (ErrorDomain, ErrorCase)
7. Test nodes (TestSuite, TestCase)
8. EDGES — luôn ở cuối, sau tất cả nodes

LÝ DO: `edge+:` resolve theo tên/id — các node đích phải đã được tạo ở các dòng
`create:` phía trên (cùng batch) hoặc đã có trên đĩa
```

---

## PHẦN 5 — EDGE RULES

### Chọn edge type theo role groups

```
Knowledge → Knowledge:   depends_on
  VD: Spec A depends on Spec B as foundation

Knowledge → Code:        implements
  VD: Engine implements Spec (code realizes spec)

Code → Code:             depends_on
  VD: Engine depends_on Table (needs table for data)

Constraint → Code:       enforces
  VD: Invariant enforces Table (rule applies to table data)

Test → Code:             covers
  VD: TestCase covers Flow (test verifies flow behavior)

Any → Meta:              discovered_in (auto — không khai báo)
```

### Viết reason đúng chuẩn

```
TEMPLATE:
  depends_on: "{A} cần {B} để {purpose cụ thể}"
  implements: "{A} hiện thực {behavior cụ thể} của {B}"
  enforces:   "{constraint} áp ràng buộc lên {B} — vi phạm gây {consequence}"
  covers:     "{test} kiểm chứng {behavior cụ thể} của {B}"

SAI — quá chung:
  reason="related to"
  reason="uses"
  reason="part of"

ĐÚNG — cụ thể:
  reason="PaymentEngine cần payments table để query transaction history"
  reason="CheckoutFlow hiện thực Feature PlaceOrder end-to-end"
  reason="OrderTotal invariant áp lên orders table — vi phạm reject INSERT"
  reason="TestCheckout kiểm chứng happy path của CheckoutFlow"
```

### Tạo edges — `edge:` (một lệnh MCP) vs `edge+:` (trong batch)

```
Một cạnh đơn, đã có sẵn id (ví dụ sau get:/find:):
  gobp(query="edge: node:engine_1 --depends_on--> node:table_2
              reason='PaymentEngine cần payments table để lưu giao dịch'")

Nhiều node + nhiều cạnh trong một lần gọi — dùng batch + edge+:
  gobp(query="batch session_id='...' ops='
    create: Engine: Alpha | ...
    create: Engine: Beta | ...
    edge+: Alpha --depends_on--> Beta
    edge+: Hub --implements--> SpecA, SpecB
  '")
```

Lưu ý:

- Trong batch chỉ dùng cú pháp dòng `edge+: From --type--> To` (hoặc `edge-:` / `edge*:` / `edge~:`).
- `edge+:` resolve theo tên hiển thị hoặc id; có thể nối node vừa tạo trong cùng `ops`.
- `reason=` trên cạnh chỉ có trên action `edge:` đơn; batch `edge+:` hiện không parse `reason` trên dòng
  (cần lý do chi tiết → dùng `edge:` từng cạnh sau khi đã có id, hoặc quy trình chỉnh sau).

Xem thêm **§3.6** cho ví dụ fan-out, `edge*:` / `edge~:` / `edge-:` và `quick:` tối giản.

---

## PHẦN 6 — QUERY GUIDE

### Session management

**Hai lớp (đừng trộn):**

1. **Audit write (mặc định):** `session_id` trên mọi lệnh ghi = chuỗi log — **opaque**, **`GOBP_SESSION_ID`**, hoặc id node **`Session`**. Không bắt buộc `session:start`. Xem §0.4.
2. **Node `Session` trên graph (tuỳ chọn):** khi cần entity phiên (goal, actor, `session:end`). Một lần **`session:start`** tạo **một** node; **host** nên gọi **ít lần**, không nhồi vào mỗi micro-bước AI.

```
Writes không cần graph Session (opaque hoặc GOBP_SESSION_ID):
  gobp(query="create:Idea name='Test' session_id='audit:pr-42'")
  # hoặc đặt GOBP_SESSION_ID=audit:pr-42; lớp ghi có thể dùng khi query không truyền session_id

Hoặc node Session (discovered_in + vòng đời):
  gobp(query="overview:")
  gobp(query="session:start actor='cursor' goal='implement X'")
  → dùng session_id trả về cho mọi write trong run (không start lại mỗi batch)

Tiếp tục phiên cũ (PostgreSQL v3):
  gobp(query="session:resume id='meta.session.YYYY-MM-DD.xxxxxxx'")

Kết thúc node Session (nếu dùng lớp 2):
  gobp(query="validate: metadata")
  gobp(query="session:end session_id='...' outcome='...' handoff='...'")
```

### Tìm kiếm

```
Tìm theo keyword:
  gobp(query="find: payment mode=compact")    → IDs (~10t/node)
  gobp(query="find: payment mode=summary")    → + desc_l1 (~15t/node)
  gobp(query="find: payment mode=brief")      → + edges (~40t/node)

Tìm theo type:
  gobp(query="find:Engine payment")
  gobp(query="find:Invariant order total")
  gobp(query="find:ErrorCase timeout")
  → exact type ưu tiên file index (ổn định hơn khi PG mirror connected nhưng thiếu type filter)

Suggest trước khi tạo:
  gobp(query="suggest: PaymentService")
  → PHẢI chạy trước mọi create: để tránh duplicate
```

### Đọc nodes

```
1 node:
  gobp(query="get: node_id mode=brief")

Nhiều nodes (KHÔNG dùng nhiều get: riêng lẻ):
  gobp(query="get_batch: ids='a,b,c' mode=brief")

Differential — chỉ lấy node đã thay đổi:
  gobp(query="get_batch: ids='a,b,c' since=1713529200")
  Nếu PG mirror thiếu id, runtime fallback file index
  (`source: hybrid_pg_file`, `mirror_fallback_count`)

Context cho task (1 request = full context):
  gobp(query="context: task='implement payment timeout'")
  → Server tự FTS + BFS + bundle
  → Dùng đầu mỗi task, tiết kiệm 60-80% so với manual
```

### Explore

```
Best match + neighborhood:
  gobp(query="explore: PaymentService")

Nodes liên quan:
  gobp(query="related: node_id mode=summary")

Decisions về topic:
  gobp(query="decisions: payment")
```

---

## PHẦN 7 — IMPORT PATTERNS THEO LOẠI TÀI LIỆU

### Từ Requirements/PRD

```
Thứ tự:
  1. Document node (tài liệu tổng)
  2. Feature nodes (từng tính năng lớn)
  3. Flow nodes (luồng của mỗi feature)
  4. Entity nodes (data entities đề cập)
  5. Constraint nodes (requirements/rules)
  6. Edges: Doc→Feature, Feature→Flow, Flow→Entity, Constraint→Entity
```

### Từ Technical Spec

```
Thứ tự:
  1. Spec/Document node (overview)
  2. Engine/Service nodes (components)
  3. Table/Schema nodes (data model)
  4. API nodes (endpoints, requests, responses)
  5. Error nodes (error domains + cases)
  6. Edges: Engine→Table, API→Engine, Error→Engine
```

### Từ Architecture Doc

```
Thứ tự:
  1. Spec node (architecture overview)
  2. Engine nodes (services/components)
  3. Infrastructure nodes (DB, Queue, Cache, CDN)
  4. External service nodes
  5. Edges: depends_on chain giữa components
  6. Invariants system-level
```

### Từ Wave Brief

```
Thứ tự:
  1. Wave node
  2. Task nodes (1 task = 1 node, implemented=false)
  3. Edges: Task depends_on Spec/Engine liên quan
  
Khi task complete:
  edit: Task → implemented=true + code = "path/to/implementation"
```

---

## PHẦN 8 — QUY TRÌNH NHẬP LIỆU CHUẨN

```
Bước 1 — Check existence trước:
  gobp(query="suggest: {concept name}")
  → Nếu có node tương tự → dùng lại
  → Nếu không có → tiến hành tạo mới

Bước 2 — Chuỗi audit cho mọi write (§0.4):
  Thứ tự ưu tiên: **`GOBP_SESSION_ID`** (host) → **`session_id`** trong query (opaque hoặc id Session) → runtime tự sinh `audit:…` nếu thiếu.
  **Không** bắt buộc `session:start`. Chỉ gọi `session:start` khi cần **node Session** + `discovered_in` / vòng đời — tối đa một lần mỗi run.
  gobp(query="session:start actor='...' goal='import ...'")   # tuỳ chọn

Bước 2b — (Tuỳ chọn) Đăng ký file .md làm node Document:
  gobp(query="import: docs/your.md session_id='audit:…'")
  → Một `doc:…` id; không phải luồng `imp:` + `commit:` (§3.4)

Bước 3 — Import nodes theo batch:
  Gộp các nodes liên quan vào 1 batch
  Thứ tự: Knowledge → Code → Constraint → Error → Test

Bước 4 — Tạo edges:
  Trong cùng batch: các dòng `edge+:` sau các `create:` (và fan-out bằng dấu phẩy nếu cần)
  Hoặc từng lệnh `edge:` riêng khi đã có id và cần `reason=` đầy đủ
  Theo đúng edge type từ EDGE_POLICY

Bước 5 — Verify:
  gobp(query="find: {keyword} mode=brief")
  → Confirm nodes đã vào graph với đúng content

Bước 6 — Validate + End:
  gobp(query="validate: metadata")
  → Score 100/100
  gobp(query="session:end session_id='...'
              outcome='...' handoff='...'")
```

---

## PHẦN 9 — LỖI THƯỜNG GẶP VÀ CÁCH FIX

| Lỗi | Nguyên nhân | Fix đúng |
|-----|-------------|----------|
| YAML corrupt khi rebuild | Description có `:`, `{`, `}` | Viết plain text, không dùng special chars (§2) |
| edge+ unresolved trong batch | Sai tên / chưa create node đích trước dòng edge | Đặt `create:` trước; khớp đúng tên hoặc dùng id; fan-out: `A --t--> B, C` |
| Policy edge: `implements` giữa hai Document/Spec | Sai ngữ nghĩa Knowledge→Knowledge | Dùng `depends_on` hoặc `references` theo `core_edges.yaml` / edge policy |
| `import:` không trả `imp:…` | Kỳ vọng nhầm luồng proposal | MCP `import:` chỉ upsert **một** Document; `imp:…` đến từ `import_proposal()` (§3.4) |
| `commit:` báo thiếu `session_id` / `accept` | Thiếu tham số bắt buộc | `commit: imp:… accept=all session_id='audit:…'` (hoặc id Session hợp lệ) |
| Ghi với id `Session` đã `COMPLETED` | Vẫn dùng id node Session đã đóng | Mở session mới hoặc dùng opaque / `GOBP_SESSION_ID` (§0.4) |
| `session:resume` failed | Không PG, schema ≠ v3, hoặc session không có trong DB | Set `GOBP_DB_URL`, schema v3; hoặc `session:start` mới (§0.3) |
| `find:` theo type trả lẫn node type khác | Mirror PG không có type column để lọc exact | Dùng `find:<Type> ...` / `type_filter=...`; runtime tự dùng file index cho exact type |
| `find:` không thấy node vừa tạo | Cache index chưa reload / chỉ tìm trên FTS DB | `refresh:` sau sửa tay; hoặc `get: node:…` bằng id từ kết quả `create` |
| `get_batch:` báo thiếu node dù `get:` thấy | PG mirror lệch, thiếu id trong batch | Runtime fallback file index (`source: hybrid_pg_file`); sync mirror để đồng nhất PG |
| `edit:` báo `Node not found` nhưng `get:` vẫn thấy | File node không nằm canonical path hoặc id/prefix không chuẩn | Runtime đã fallback scan theo `id`; ưu tiên id từ `get:`/`find:` + truyền `session_id` |
| `edge:` fail vì thiếu `gobp/schema/core_edges.yaml` ở root | Project external/legacy không có schema local | Runtime fallback package schema; nếu còn lỗi, kiểm tra node id + edge type policy |
| ErrorCase `code` bị reject (`AUTH_001`) | Catalog dùng id không có severity letter; schema bắt `^[A-Z]+_[FEWI]_[0-9]{3}$` | `name` = id catalog; `code` = id GoBP (`AUTH_W_001`); mô tả HTTP/behavior trong `description` — **§2.1** |
| Lo ngại **Entity `Place`** vs **`PlaceOwnership`** trong batch | Đã giới hạn điểm prefix (79) dưới ngưỡng duplicate (80) trong `search_score` | Vẫn kiểm `name` literal khi đọc `find:`; cạnh ưu tiên **`node:<id>`** — **§1.3** |
| Duplicate nodes | Không `suggest:` trước `create:` | Luôn `suggest:` trước khi tạo (dec:d011 Lessons) |
| Score < 100 khi validate | Nodes thiếu description | Thêm description cho mọi node |
| Session IN_PROGRESS tồn đọng | Quên session:end | `session:end` với outcome + handoff |
| implemented=true nhưng no code | Đánh dấu done nhưng không ghi path | Thêm `code=` path khi đánh implemented=true |

---

## PHẦN 10 — CHECKLIST TRƯỚC KHI SUBMIT

```
□ Đã suggest: trước mọi create:
□ Mọi write có audit: `session_id` trong query **hoặc** `GOBP_SESSION_ID` **hoặc** chấp nhận `audit:…` tự sinh (§0.4); `session:resume` chỉ khi PG v3 — §0.3
□ Description: plain text, không có :, {, }, |, #, >, !
□ Nodes trong batch: Knowledge → Code → Constraint → Error → Test → Edges
□ Edges: trong batch dùng `edge+:` (đủ tên/id); hoặc `edge:` riêng khi cần reason= chi tiết
□ `find` theo type dùng `find:<Type> ...` (hoặc `type_filter=`) để nhận exact type từ file index
□ implemented=false cho tất cả Spec/Feature chưa có code
□ validate: metadata → score 100/100
□ Nếu dùng **node `Session`** trên graph: `session:end` + handoff; nếu chỉ audit opaque/env — không bắt buộc
```

---

*GoBP IMPORT GUIDE v2 — 2026-04-22*  
*Generic — áp dụng cho mọi project, mọi AI agent; audit write: `gobp/mcp/session_audit.py`; đối chiếu `gobp/mcp/` khi nghi ngờ.*  
◈
