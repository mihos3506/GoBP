# ◈ GoBP IMPORT GUIDE v1
**Status:** AUTHORITATIVE  
**Date:** 2026-04-20  
**Read after:** SCHEMA.md, MCP_PROTOCOL.md, EDGE_POLICY.md  
**Audience:** Mọi AI agent khi nhập liệu vào GoBP  

---

## SAU KHI ĐỌC FILE NÀY, AI BIẾT

1. Chọn đúng node type cho từng loại thông tin
2. Viết description đúng chuẩn không gây YAML lỗi
3. Chọn đúng phương pháp nhập (create/batch/quick/import)
4. Tạo edges đúng semantic theo edge policy
5. Query hiệu quả ở từng tình huống
6. Nguyên tắc batch — khi nào gộp, khi nào tách

---

## PHẦN 1 — CHỌN NODE TYPE

### Nguyên tắc chọn

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

ErrorCase (use code field for technical detail):
  description: "When {trigger condition}. System responds by {action}.
                User sees {message}. Auto-recovery: {yes/no, how}."
  code: "HTTP 408. Retry 3x with 30s backoff. Idempotency key required."

Spec:
  "{What this specifies and why}. {Key rules or constraints}.
   {How AI/dev uses this spec}."
```

---

## PHẦN 3 — PHƯƠNG PHÁP NHẬP LIỆU

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
Auto-chunk: GoBP tự chia nếu >50 ops

gobp(query="batch session_id='...' ops='
  create: Engine: PaymentService | Handles payments. Validates balance
    before debit. SLA p99 300ms.
  create: Table: payments | Stores all payment transactions.
    Each row is 1 payment attempt. Owned by PaymentService.
  create: ErrorCase: Payment Timeout | When payment processor
    exceeds 10s timeout. group=Error > Payment severity=error
  
  edge: engine_id --depends_on--> table_id reason=reason
  edge: errorcase_id --affects--> engine_id reason=reason
'")
```

### 3.3 — quick: — capture nhanh

```
Dùng khi: Capture nhanh nhiều ý tưởng, enrich sau
Format: "Name | type | context | description"
Token cost: minimal

gobp(query="quick: session_id='...' ops='
  Payment Timeout | ErrorCase | Wave 3 | Timeout in payment processing
  Order Total Rule | Invariant | Wave 3 | Total must equal sum of items
  Checkout Flow | Flow | Wave 3 | End-to-end checkout journey
'")

Sau quick: → dùng get: để enrich từng node
```

### 3.4 — import: + commit: — từ file doc

```
Dùng khi: Import từ .md file có sẵn trong repo, cần review trước
Workflow: propose → human review → commit

gobp(query="import: docs/SPEC.md session_id='...'")
→ Nhận proposal_id

Review proposal content

gobp(query="commit: {proposal_id}")
→ Nodes được tạo chính thức
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
    create: Flow: Checkout Flow | ...
    create: Engine: OrderService | ...
    create: Table: orders | ...
    create: Invariant: Order Total Non-Negative | ...
    create: ErrorCase: Checkout Failed | ...
    edge: flow --implements--> spec
    edge: engine --depends_on--> table
    edge: invariant --enforces--> table
  '
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

LÝ DO: edge: cần node tồn tại để resolve ID
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

### Tạo edges — luôn dùng edge: riêng lẻ

```
ĐÚNG:
  gobp(query="edge: from_id --depends_on--> to_id
              reason='reason text'")

SAI — batch edge+ không resolve IDs:
  batch ops='
    edge+: from_id --depends_on--> to_id   ← không hoạt động
  '
```

---

## PHẦN 6 — QUERY GUIDE

### Session management

```
Session mới:
  gobp(query="overview:")
  gobp(query="session:start actor='cursor' goal='implement X'")
  → Lấy session_id, dùng cho tất cả writes

Tiếp tục session cũ (tiết kiệm 70% tokens):
  gobp(query="session:resume id='meta.session.YYYY-MM-DD.xxxxxxx'")

Kết thúc session:
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

Bước 2 — Start session:
  gobp(query="session:start actor='...' goal='import ...'")
  → Lấy session_id

Bước 3 — Import nodes theo batch:
  Gộp các nodes liên quan vào 1 batch
  Thứ tự: Knowledge → Code → Constraint → Error → Test

Bước 4 — Tạo edges:
  Dùng edge: riêng lẻ (không batch edge+)
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
| YAML corrupt khi rebuild | Description có `:`, `{`, `}` | Viết plain text, không dùng special chars |
| edge+ không resolve ID | Dùng edge+ trong batch ops | Dùng edge: action riêng lẻ |
| Duplicate nodes | Không suggest: trước create: | Luôn suggest: trước khi tạo |
| Score < 100 khi validate | Nodes thiếu description | Thêm description cho mọi node |
| Session IN_PROGRESS tồn đọng | Quên session:end | session:end với outcome + handoff |
| implemented=true nhưng no code | Đánh dấu done nhưng không ghi path | Thêm code=path/to/file khi đánh implemented=true |

---

## PHẦN 10 — CHECKLIST TRƯỚC KHI SUBMIT

```
□ Đã suggest: trước mọi create:
□ Có session_id (session:start hoặc session:resume)
□ Description: plain text, không có :, {, }, |, #, >, !
□ Nodes trong batch: Knowledge → Code → Constraint → Error → Test → Edges
□ Edges: dùng edge: riêng lẻ, có reason cụ thể
□ implemented=false cho tất cả Spec/Feature chưa có code
□ validate: metadata → score 100/100
□ session:end với outcome đầy đủ + handoff cho session tiếp theo
```

---

*GoBP IMPORT GUIDE v1 — 2026-04-20*  
*Generic — áp dụng cho mọi project, mọi AI agent.*  
◈
