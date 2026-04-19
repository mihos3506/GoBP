# ◈ GoBP COOKBOOK v1
**Status:** AUTHORITATIVE  
**Date:** 2026-04-19  
**Read after:** SCHEMA.md, MCP_PROTOCOL.md  
**Audience:** Cursor (primary), CTO Chat, Claude CLI

---

## SAU KHI ĐỌC FILE NÀY, AI BIẾT

Cách thực hiện các task phổ biến — step by step, copy-paste ready.  
Không giải thích concept — xem SCHEMA.md và ARCHITECTURE.md.

---

## RECIPE 01 — BẮT ĐẦU SESSION MỚI

```
gobp(query="overview:")

gobp(query="session:start actor='cursor' goal='implement checkout flow'")
→ Lấy session_id từ response
→ Dùng session_id này cho tất cả writes
```

---

## RECIPE 02 — TIẾP TỤC SESSION CŨ

```
gobp(query="session:resume id='meta.session.2026-04-19.abc12345'")
→ Nhận: pending_handoff + graph_changes
→ Không cần overview: + recent: riêng
→ Tiết kiệm ~700 tokens
```

---

## RECIPE 03 — LẤY CONTEXT CHO 1 TASK

```
Cursor nhận task → khai báo intent, server lo phần còn lại:

gobp(query="context: task='implement user authentication'")
gobp(query="context: task='fix payment timeout error'")
gobp(query="context: task='write database migration for orders'")

→ 1 request = đủ context: Flow + Engine + Table + Invariant + ErrorCase
→ Không cần biết graph topology
```

---

## RECIPE 04 — TÌM NODE KHI CHƯA BIẾT ID

```
gobp(query="find: payment mode=compact")
→ Nhận danh sách IDs nhanh (~10 tokens/node)

gobp(query="find: payment mode=summary")
→ + desc_l1 (~15 tokens/node)

gobp(query="find: payment group='Dev > Infrastructure > Engine'")
→ Filter theo group

→ Sau khi có IDs: dùng get_batch: để lấy detail
```

---

## RECIPE 05 — LẤY NHIỀU NODES CÙNG LÚC

```
gobp(query="get_batch: ids='
  dev.infrastructure.engine.paymentservice.a1b2,
  dev.infrastructure.database.table.orders.c3d4,
  constraint.invariant.balance_positive.e5f6
' mode=brief")

→ 1 request, ~120 tokens (3 nodes × 40)
→ KHÔNG dùng 3 lần get: riêng lẻ
```

---

## RECIPE 06 — LẤY NODES CHỈ KHI CÓ THAY ĐỔI

```
gobp(query="get_batch: ids='a,b,c,d,e' since='1713529200'")

→ Node không đổi: {id, unchanged: true} (~5 tokens)
→ Node đã đổi: full data (~40 tokens)
→ Tiết kiệm 90% khi data ổn định
```

---

## RECIPE 07 — TẠO ENGINE NODE

```
gobp(query="suggest: PaymentService")
→ Không tìm thấy → tạo mới

gobp(query="batch session_id='{sid}' ops='
  create: Engine: PaymentService |
    Handles financial transactions between users. Validates balance
    before debit. Executes atomic credit/debit. Exposes REST API
    for payment initiation and status queries. SLA: p99 < 300ms.
'")
```

---

## RECIPE 08 — TẠO TABLE + COLUMNS

```
gobp(query="batch session_id='{sid}' ops='
  create: Table: orders |
    Stores all customer orders. Each order belongs to one user,
    contains multiple items, has total amount and status lifecycle.
    Primary key: id (UUID). Owned by OrderService engine.
    Soft delete via deleted_at column.

  create: Column: orders.id |
    UUID primary key. Server-generated, never from client.

  create: Column: orders.user_id |
    FK to users.id. PII field — mask in logs.

  create: Column: orders.total_amount |
    Decimal(10,2). Must be >= 0 — validated before insert.

  create: Column: orders.status |
    Enum: pending|confirmed|shipped|delivered|cancelled.
    State machine — only specific transitions allowed.

  edge+: dev.infrastructure.database.column.orders_id.{id}
    -- dev.infrastructure.database.table.orders.{id}
    reason="id is primary key of orders table"
'")
```

---

## RECIPE 09 — TẠO API ENDPOINT

```
gobp(query="batch session_id='{sid}' ops='
  create: APIEndpoint: POST /orders |
    Creates a new order. Requires valid JWT. Validates inventory
    before confirm. Returns 201 with order_id on success.
    Rate limit: 10/min per user. Idempotency key: client_order_id.
    Error responses: 401 (expired token), 422 (validation fail),
    429 (rate limit), 503 (inventory service unavailable).

  create: APIRequest: POST /orders request |
    Body: {user_id: UUID, items: [{product_id, qty, price}],
    client_order_id: string (idempotency key)}

  create: APIResponse: POST /orders 201 |
    Body: {order_id: UUID, status: "pending", created_at: ISO8601}

  edge+: dev.infrastructure.api.apiendpoint.post_orders.{id}
    -- dev.infrastructure.engine.orderservice.{id}
    reason="POST /orders is handled by OrderService"
'")
```

---

## RECIPE 10 — TẠO AUTH FLOW

```
gobp(query="batch session_id='{sid}' ops='
  create: AuthFlow: Email OTP Login |
    User enters email → system sends 6-digit OTP valid 10min →
    user enters OTP → system verifies → issues JWT + refresh token.
    Rate limit: 5 attempts per 15min per email+IP combination.
    Lockout: 15min after 5 failed attempts.
    OTP delivery: transactional email service, not SMS.

  create: Token: JWT Access Token |
    JWT signed with RS256. Expiry: 24h. Contains: user_id, email,
    issued_at. Stored in memory (not localStorage). Refresh via
    refresh token which expires in 30d with rotation.

  edge+: dev.infrastructure.security.authflow.email_otp.{id}
    -- dev.infrastructure.security.token.jwt.{id}
    reason="Email OTP flow issues JWT on successful verification"
'")
```

---

## RECIPE 11 — TẠO INVARIANT

```
gobp(query="batch session_id='{sid}' ops='
  create: Invariant: Order Total Non-Negative |
    order.total_amount >= 0 AND order.total_amount = SUM(items.price * items.qty)
    Enforcement: hard. Scope: object.
    Validated before insert and on any item update.

  edge+: constraint.invariant.order_total.{id}
    -- dev.infrastructure.database.table.orders.{id}
    reason="This invariant applies to every orders row"
'")
```

---

## RECIPE 12 — TẠO ERROR CASE

```
gobp(query="batch session_id='{sid}' ops='
  create: ErrorCase: Payment Timeout |
    group="Error > Payment"
    severity=error
    Payment processor did not respond within 10s. Triggered when
    external payment API call exceeds timeout threshold. System
    response: mark order as payment_pending, schedule retry after
    30s up to 3 times. After 3 failures: mark as payment_failed,
    notify user. User sees: "Payment is taking longer than expected.
    We will retry automatically." Do not charge user twice — check
    idempotency key before retry.

  edge+: error.errorcase.payment_timeout.{id}
    -- dev.infrastructure.engine.paymentservice.{id}
    reason="This error originates from PaymentService timeout handling"
'")
```

---

## RECIPE 13 — TẠO EXTERNAL SERVICE

```
gobp(query="batch session_id='{sid}' ops='
  create: ExternalService: Stripe |
    Payment processing service. Base URL: api.stripe.com/v1.
    Auth: Bearer API key (stored in Secret vault, not env var).
    Rate limit: 100 req/s per account. Webhook for async events.
    Fallback: if unavailable → queue payment for retry, show
    "payment temporarily unavailable" to user. SLA: 99.99%.

  create: SDK: stripe-node v14 |
    Official Stripe SDK for Node/Deno. Handles webhook signature
    verification, retry logic, idempotency keys automatically.
    Version: ^14.0.0. Update quarterly.

  edge+: dev.infrastructure.thirdparty.sdk.stripe_node.{id}
    -- dev.infrastructure.thirdparty.externalservice.stripe.{id}
    reason="stripe-node SDK wraps Stripe REST API"
'")
```

---

## RECIPE 14 — IMPORT DOCUMENT IDEMPOTENT

```
Đọc document → extract nodes → dùng import_atomic:

gobp(query="session:start actor='cto_chat' goal='import API spec doc'")

gobp(query="import_atomic: session_id='{sid}' ops='
  ensure: APIContract: Payment API v1 |
    REST API for payment operations. Base path: /api/v1/payments.
    Auth: Bearer JWT required for all endpoints.
    Versioning: URL-based (/v1, /v2). Current: v1 active, v2 planned.

  ensure: APIEndpoint: POST /payments/charge |
    Charges payment method. Idempotent via client_reference_id.
    Returns 202 Accepted with transaction_id for async processing.

  edge+: payment_api_v1 -- post_payments_charge
    reason="POST /payments/charge belongs to Payment API v1"
'")

→ Chạy nhiều lần = an toàn (idempotent)
→ ensure: = create nếu chưa có, skip nếu đã có
```

---

## RECIPE 15 — THÊM HISTORY ENTRY

```
gobp(query="update: id='dev.infrastructure.engine.paymentservice.a1b2'
  history=[{description: 'Added idempotency key support to prevent
  duplicate charges on network retry. Root cause: mobile clients
  retry on timeout without checking if original request succeeded.
  Wave: 12B'}]
  session_id='{sid}'")
```

---

## RECIPE 16 — TẠO TEST CASE

```
gobp(query="batch session_id='{sid}' ops='
  create: TestCase: POST /orders returns 201 on valid request |
    Given: authenticated user, valid product IDs in inventory.
    When: POST /orders with valid body and client_order_id.
    Then: response 201, order_id in body, order status=pending
    in database, OrderCreated event published to queue.
    Kind: integration. Priority: must_pass.

  edge+: test.testcase.post_orders_201.{id}
    -- dev.infrastructure.api.apiendpoint.post_orders.{id}
    reason="This test case covers POST /orders endpoint"
'")
```

---

## RECIPE 17 — TẠO SLO

```
gobp(query="batch session_id='{sid}' ops='
  create: Metric: api.request.duration_ms |
    HTTP request duration in milliseconds. Type: histogram.
    Labels: endpoint (path), method (GET/POST/...), status_code.
    Emitted by API Gateway middleware on every request.

  create: SLO: API Latency p99 < 200ms |
    99th percentile API latency must stay under 200ms in rolling
    30-day window. Error budget: 0.1% = 43.2min/month.
    Alert when burn rate exceeds 5x in 1 hour.
    Source metric: api.request.duration_ms p99.

  edge+: dev.infrastructure.observability.slo.api_latency.{id}
    -- dev.infrastructure.observability.metric.api_request_duration.{id}
    reason="SLO is measured using api.request.duration_ms metric"
'")
```

---

## RECIPE 18 — TẠO DEPLOYMENT ENVIRONMENT

```
gobp(query="batch session_id='{sid}' ops='
  create: Environment: Production |
    Base URL: api.myapp.com. PostgreSQL: managed RDS.
    All external services use live credentials.
    Feature flags: payments=enabled, new_checkout=10%_rollout.
    Monitoring: Datadog APM + PagerDuty alerts.
    Deploy: blue-green with automated rollback on error spike.

  create: ServiceDefinition: API Service |
    Main API service. Runtime: Deno 2.x. Port: 8080.
    Min replicas: 2, max: 20 (auto-scale on CPU > 70%).
    Health: GET /health → 200 within 5s.
    Memory limit: 512Mi, CPU limit: 500m.
    Graceful shutdown: 30s drain.
'")
```

---

## RECIPE 19 — KẾT THÚC SESSION ĐÚNG CÁCH

```
gobp(query="validate: metadata")
→ Phải trả về score 100/100 trước khi end

gobp(query="session:end
  outcome='Imported API spec: 3 APIContract, 8 APIEndpoint,
  5 APIRequest, 5 APIResponse nodes. 12 edges created.
  All validate: metadata passed.'
  handoff='Còn thiếu: error responses chưa map sang ErrorCase nodes.
  Next: Recipe 12 cho timeout, rate_limit, auth errors.'")
```

---

## RECIPE 20 — VALIDATE SAU IMPORT LỚN

```
gobp(query="validate: metadata")
→ score phải 100/100

gobp(query="dedupe: edges")
→ Remove duplicate edges nếu batch chạy nhiều lần

gobp(query="validate: all")
→ Full check referential integrity
```

---

*GoBP COOKBOOK v1 — 2026-04-19*  
*20 recipes: session, find, create, import, validate*  
*Reference: SCHEMA.md (node types) · MCP_PROTOCOL.md (syntax)*  
◈
