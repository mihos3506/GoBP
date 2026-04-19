# GoBP SCHEMA REDESIGN — COMPLETE TAXONOMY
**Version:** 2.1
**Date:** 2026-04-19
**Author:** CTO Chat
**Status:** APPROVED — **Implemented** in repo (schema v2 cutover, query engine, validator v2, viewer v2 panels — see `CHANGELOG.md` Waves 17A01–17A05 and `docs/README.md`).

---

## CORE PRINCIPLES

```
1. Chuẩn thế giới trước, MIHOS đi theo chuẩn
2. Node = 1 khái niệm rõ ràng, không mập mờ
3. Group = breadcrumb path thể hiện hierarchy đầy đủ
4. Description = info (bắt buộc) + code (tùy chọn)
5. Edge = mối liên hệ có reason, không phải outgoing/incoming list
6. Display = ẩn raw fields, chỉ hiển thị knowledge
7. Lesson = phân theo role (Rule/Skill/Dev/CTO/QA)
8. ErrorCase fixes = append-only history
```

---

## GROUP / BREADCRUMB SYSTEM

Mỗi node PHẢI có `group` field thể hiện đầy đủ path trong hierarchy.
Node ở lớp dưới phải thể hiện tất cả lớp trên.

```
Format: TopGroup > SubGroup > ... > Type

Ví dụ:
  group: "Dev > Infrastructure > Security"
  type:  AuthFlow
  → AI đọc ngay: AuthFlow thuộc Security, thuộc Infrastructure, thuộc Dev

  group: "Document > Lesson"
  type:  Rule
  → AI đọc ngay: Rule là Lesson thuộc Document group

  group: "Error > ErrorCase"
  type:  ErrorCase
  → AI đọc ngay: ErrorCase thuộc Error group
```

---

## TAXONOMY — 6 NHÓM LỚN

---

### NHÓM 1: DOCUMENT

```
Document
  ├── Spec
  │   group: "Document > Spec"
  │   → Tài liệu đặc tả chính thức (DOC-XX files)
  │   → Source of truth cho feature/engine/entity
  │
  ├── Decision
  │   group: "Document > Decision"
  │   → Architecture Decision Record (ADR chuẩn)
  │   → Fields: context, what, why, consequences, alternatives
  │   → Locked = không thay đổi
  │
  ├── Concept
  │   group: "Document > Concept"
  │   → Ubiquitous Language — thuật ngữ domain
  │   → Fields: definition, usage_guide, applies_to
  │
  ├── Idea
  │   group: "Document > Idea"
  │   → Ý tưởng chưa thành hình, chưa được quyết định
  │   → Fields: description, maturity (RAW/REFINED/DISCUSSED)
  │
  └── Lesson (5 sub-types)
      ├── Rule
      │   group: "Document > Lesson > Rule"
      │   → Quy tắc bất biến, mọi role phải tuân theo
      │   → VD: "suggest: trước khi tạo node"
      │   → Áp dụng: tất cả agents
      │
      ├── Skill
      │   group: "Document > Lesson > Skill"
      │   → Reusable procedure/program cho AI agent
      │   → Dạng: step-by-step có input/output
      │   → VD: "Cách import Invariant đúng chuẩn"
      │
      ├── Dev
      │   group: "Document > Lesson > Dev"
      │   → Bài học từ implementation (Cursor)
      │   → VD: "batch edge+ với IDs có ':' bị parse sai"
      │
      ├── CTO
      │   group: "Document > Lesson > CTO"
      │   → Bài học từ architecture + product (CTO Chat)
      │   → VD: "Invariant ≠ mọi câu KHÔNG được X"
      │
      └── QA
          group: "Document > Lesson > QA"
          → Bài học từ audit + quality gate (Claude CLI)
          → VD: "Full suite chỉ cuối wave, không mỗi task"
```

---

### NHÓM 2: DEV

```
Dev
  ├── Domain
  │   group: "Dev > Domain"
  │   ├── Entity
  │   │   group: "Dev > Domain > Entity"
  │   │   → Domain objects với identity + lifecycle
  │   │   → VD: Traveller, Place, Moment, EmberWallet
  │   │
  │   ├── ValueObject
  │   │   group: "Dev > Domain > ValueObject"
  │   │   → Immutable, no identity
  │   │   → VD: GpsCoordinate, EmberAmount, OtpCode
  │   │
  │   ├── DomainEvent
  │   │   group: "Dev > Domain > DomainEvent"
  │   │   → Sự kiện domain đã xảy ra (past tense)
  │   │   → VD: MomentCreated, PlaceNamed, EmberEarned
  │   │
  │   └── Aggregate
  │       group: "Dev > Domain > Aggregate"
  │       → Cluster entities với 1 aggregate root
  │       → VD: Place (root) + Moments + LiveSignals
  │
  ├── Application
  │   group: "Dev > Application"
  │   ├── Flow
  │   │   group: "Dev > Application > Flow"
  │   │   → User journeys / Use cases
  │   │   → VD: Mi Hốt Flow, Login Flow, Register Flow
  │   │
  │   ├── Feature
  │   │   group: "Dev > Application > Feature"
  │   │   → User-facing capabilities
  │   │   → VD: Story Creation, Map Discovery
  │   │
  │   ├── Command
  │   │   group: "Dev > Application > Command"
  │   │   → User intentions / actions
  │   │   → VD: MiHotCommand, CreateStoryCommand
  │   │
  │   ├── UseCase
  │   │   group: "Dev > Application > UseCase"
  │   │   → Application logic orchestration
  │   │
  │   └── DTO
  │       group: "Dev > Application > DTO"
  │       → Data Transfer Objects giữa layers
  │
  ├── Infrastructure
  │   group: "Dev > Infrastructure"
  │   │
  │   ├── Engine
  │   │   group: "Dev > Infrastructure > Engine"
  │   │   → Backend business logic services
  │   │   → VD: TrustGate, AuthEngine, EmberEngine
  │   │
  │   ├── Repository
  │   │   group: "Dev > Infrastructure > Repository"
  │   │   → Data access layer
  │   │   → VD: MomentRepository, PlaceRepository
  │   │
  │   ├── API
  │   │   group: "Dev > Infrastructure > API"
  │   │   ├── APIContract
  │   │   │   group: "Dev > Infrastructure > API > APIContract"
  │   │   │   → Full API spec (OpenAPI level)
  │   │   ├── APIEndpoint
  │   │   │   group: "Dev > Infrastructure > API > APIEndpoint"
  │   │   │   → Single route (GET /moments/:id)
  │   │   ├── APIRequest
  │   │   │   group: "Dev > Infrastructure > API > APIRequest"
  │   │   │   → Request shape + validation rules
  │   │   ├── APIResponse
  │   │   │   group: "Dev > Infrastructure > API > APIResponse"
  │   │   │   → Response shape + status codes
  │   │   ├── APIMiddleware
  │   │   │   group: "Dev > Infrastructure > API > APIMiddleware"
  │   │   │   → Cross-cutting (auth, rate limit, logging)
  │   │   └── Webhook
  │   │       group: "Dev > Infrastructure > API > Webhook"
  │   │       → Outbound event notifications
  │   │
  │   ├── Security
  │   │   group: "Dev > Infrastructure > Security"
  │   │   ├── AuthFlow
  │   │   │   group: "Dev > Infrastructure > Security > AuthFlow"
  │   │   │   → Authentication flows
  │   │   │   → VD: OTP Flow, VNeID Flow, OAuth
  │   │   ├── AuthZ
  │   │   │   group: "Dev > Infrastructure > Security > AuthZ"
  │   │   │   → Authorization / RBAC / ABAC rules
  │   │   ├── Permission
  │   │   │   group: "Dev > Infrastructure > Security > Permission"
  │   │   │   → Access control definitions
  │   │   ├── Policy
  │   │   │   group: "Dev > Infrastructure > Security > Policy"
  │   │   │   → Security policies (Zero-trust, CORS, CSP)
  │   │   ├── Token
  │   │   │   group: "Dev > Infrastructure > Security > Token"
  │   │   │   → JWT, refresh token, API key specs
  │   │   ├── Encryption
  │   │   │   group: "Dev > Infrastructure > Security > Encryption"
  │   │   │   → At-rest, in-transit encryption specs
  │   │   ├── Secret
  │   │   │   group: "Dev > Infrastructure > Security > Secret"
  │   │   │   → Secret management (Vault, env vars, key rotation)
  │   │   ├── Audit
  │   │   │   group: "Dev > Infrastructure > Security > Audit"
  │   │   │   → Audit trail, compliance logging
  │   │   ├── ThreatModel
  │   │   │   group: "Dev > Infrastructure > Security > ThreatModel"
  │   │   │   → Attack vectors + mitigations
  │   │   └── Vulnerability
  │   │       group: "Dev > Infrastructure > Security > Vulnerability"
  │   │       → CVE tracking, patch notes
  │   │
  │   ├── Database
  │   │   group: "Dev > Infrastructure > Database"
  │   │   ├── Schema
  │   │   │   group: "Dev > Infrastructure > Database > Schema"
  │   │   ├── Migration
  │   │   │   group: "Dev > Infrastructure > Database > Migration"
  │   │   ├── Index
  │   │   │   group: "Dev > Infrastructure > Database > Index"
  │   │   ├── Query
  │   │   │   group: "Dev > Infrastructure > Database > Query"
  │   │   └── Seed
  │   │       group: "Dev > Infrastructure > Database > Seed"
  │   │
  │   ├── Messaging
  │   │   group: "Dev > Infrastructure > Messaging"
  │   │   ├── EventBus
  │   │   │   group: "Dev > Infrastructure > Messaging > EventBus"
  │   │   ├── Queue
  │   │   │   group: "Dev > Infrastructure > Messaging > Queue"
  │   │   ├── Topic
  │   │   │   group: "Dev > Infrastructure > Messaging > Topic"
  │   │   └── Worker
  │   │       group: "Dev > Infrastructure > Messaging > Worker"
  │   │
  │   ├── Observability
  │   │   group: "Dev > Infrastructure > Observability"
  │   │   ├── Metric
  │   │   │   group: "Dev > Infrastructure > Observability > Metric"
  │   │   ├── Log
  │   │   │   group: "Dev > Infrastructure > Observability > Log"
  │   │   ├── Trace
  │   │   │   group: "Dev > Infrastructure > Observability > Trace"
  │   │   └── Alert
  │   │       group: "Dev > Infrastructure > Observability > Alert"
  │   │
  │   ├── Cache
  │   │   group: "Dev > Infrastructure > Cache"
  │   │   └── CacheStrategy
  │   │       group: "Dev > Infrastructure > Cache > CacheStrategy"
  │   │
  │   ├── Storage
  │   │   group: "Dev > Infrastructure > Storage"
  │   │   ├── FileStorage
  │   │   │   group: "Dev > Infrastructure > Storage > FileStorage"
  │   │   └── CDN
  │   │       group: "Dev > Infrastructure > Storage > CDN"
  │   │
  │   └── Config
  │       group: "Dev > Infrastructure > Config"
  │       ├── EnvConfig
  │       │   group: "Dev > Infrastructure > Config > EnvConfig"
  │       └── FeatureFlag
  │           group: "Dev > Infrastructure > Config > FeatureFlag"
  │
  ├── Frontend
  │   group: "Dev > Frontend"
  │   ├── Screen       group: "Dev > Frontend > Screen"
  │   ├── Component    group: "Dev > Frontend > Component"
  │   ├── Layout       group: "Dev > Frontend > Layout"
  │   ├── Theme        group: "Dev > Frontend > Theme"
  │   ├── Animation    group: "Dev > Frontend > Animation"
  │   └── State        group: "Dev > Frontend > State"
  │
  └── Code
      group: "Dev > Code"
      ├── Interface    group: "Dev > Code > Interface"
      ├── AbstractClass group: "Dev > Code > AbstractClass"
      ├── Class        group: "Dev > Code > Class"
      ├── Mixin        group: "Dev > Code > Mixin"
      ├── Enum         group: "Dev > Code > Enum"
      ├── TypeAlias    group: "Dev > Code > TypeAlias"
      ├── Generic      group: "Dev > Code > Generic"
      ├── Function     group: "Dev > Code > Function"
      ├── Method       group: "Dev > Code > Method"
      ├── Constructor  group: "Dev > Code > Constructor"
      ├── Extension    group: "Dev > Code > Extension"
      ├── Field        group: "Dev > Code > Field"
      ├── Variable     group: "Dev > Code > Variable"
      ├── Constant     group: "Dev > Code > Constant"
      ├── Parameter    group: "Dev > Code > Parameter"
      └── Module       group: "Dev > Code > Module"
```

---

### NHÓM 3: CONSTRAINT

```
Constraint
  ├── Invariant
  │   group: "Constraint > Invariant"
  │   → Boolean expression PHẢI luôn true (OCL chuẩn)
  │   → REQUIRED fields: rule, scope, enforcement, violation_action
  │   → rule: Boolean expression rõ ràng
  │           VD: "balance >= 0"
  │           VD: "captured_at IS IMMUTABLE after status = PUBLISHED"
  │   → scope: class | object | system
  │   → enforcement: hard | soft
  │   → violation_action: reject | devalue | flag | log
  │
  │   ĐÚNG: "balance = SUM(entries) >= 0"
  │   SAI:  "KHÔNG follower counts" → đó là BusinessRule
  │
  ├── Precondition
  │   group: "Constraint > Precondition"
  │   → Điều kiện PHẢI true TRƯỚC khi action được phép
  │   → VD: "GPS signal = TRUE before MiHot"
  │
  ├── Postcondition
  │   group: "Constraint > Postcondition"
  │   → Điều kiện PHẢI true SAU khi action hoàn thành
  │   → VD: "Moment.captured_at immutable after creation"
  │
  └── BusinessRule
      group: "Constraint > BusinessRule"
      → Soft policies, không phải formal Boolean
      → VD: "KHÔNG follower counts"
      → VD: "Revenue >= 50% to contributor"
```

---

### NHÓM 4: ERROR

```
Error
  ├── ErrorDomain
  │   group: "Error > ErrorDomain"
  │   Fields:
  │     name:        GPS Domain
  │     domain:      gps | auth | ember | trust | privacy | network | storage | sync
  │     description:
  │       info: |
  │         Mô tả đầy đủ domain lỗi này bao gồm gì,
  │         khi nào xảy ra, ai bị ảnh hưởng
  │     fix_guide: |
  │       Checklist debug chung cho domain này
  │       Hướng dẫn từng bước tìm và fix lỗi
  │     affects: → [nodes bị ảnh hưởng bởi domain này]
  │
  └── ErrorCase
      group: "Error > ErrorCase"
      Fields:

        # IDENTITY
        name:     GPS Signal Lost
        code:     GPS_001
        domain:   → ref ErrorDomain:GPS

        # DESCRIPTION
        description:
          info: |
            Mô tả đầy đủ lỗi này là gì,
            tại sao xảy ra, khi nào xảy ra,
            ai bị ảnh hưởng, impact như thế nào

        # TRIGGER
        trigger: |
          Điều kiện chính xác gây ra lỗi này
          VD: GPS accuracy > 50m hoặc signal = null
          Thường xảy ra khi: user ở trong nhà, tầng hầm

        # SEVERITY
        severity: fatal | error | warning | info

        # SYSTEM RESPONSE
        handling: |
          Hệ thống phản ứng thế nào khi lỗi xảy ra
          Step by step system behavior

        # USER FACING
        user_message: |
          Message hiển thị cho user
          Phải rõ ràng, hữu ích, không technical

        # DEV NOTES
        dev_note: |
          Notes quan trọng cho developer khi implement
          Gotchas, edge cases, common mistakes

        # RECOVERY
        recovery: |
          Cách hệ thống hoặc user recover sau lỗi

        # RELATIONSHIPS
        affects:        → [nodes bị ảnh hưởng trực tiếp]
        related_errors: → [lỗi liên quan hoặc thường đi kèm]

        # FIX HISTORY — append-only, không xóa
        fixes:
          - type:       runtime | dev_code
            fixed_at:   2026-04-18
            fixed_by:   cursor / wave 17A05

            symptom: |
              Biểu hiện lỗi — AI hoặc user thấy gì

            root_cause: |
              Nguyên nhân gốc rễ sau khi điều tra

            fix_description: |
              Mô tả cách fix — logic, approach

            code: |
              // Code trước khi fix (wrong):
              ...

              // Code sau khi fix (correct):
              ...

            files_changed:
              - path:   path/to/file.dart
                change: "mô tả thay đổi"

            # Chỉ có trong type: dev_code
            test_result: |
              Before: N failed
              After:  all passed

            verified_by: claude-cli / wave XX
```

---

### NHÓM 5: TEST

```
Test
  ├── TestSuite
  │   group: "Test > TestSuite"
  │   → Nhóm tests theo domain/feature
  │   → VD: AuthSuite, MiHotSuite, EmberSuite
  │
  ├── TestKind
  │   group: "Test > TestKind"
  │   → Loại test: Unit | Integration | E2E | Security |
  │                Performance | Contract | Regression
  │
  └── TestCase
      group: "Test > TestCase"
      Fields:
        given:  Precondition / initial state
        when:   Action / trigger
        then:   Expected outcome
        covers: → ref Node được test
        kind:   → ref TestKind
```

---

### NHÓM 6: META

```
Meta
  ├── Session  group: "Meta > Session"
  ├── Wave     group: "Meta > Wave"
  └── Task     group: "Meta > Task"
```

---

## DESCRIPTION STANDARD

```yaml
description:
  info: |
    [BẮT BUỘC — không giới hạn độ dài]
    Mô tả đầy đủ:
    - Mục đích, behavior, context
    - Edge cases, ai dùng, dùng thế nào
    - Liên quan đến gì trong hệ thống

  code: |
    [TÙY CHỌN — để trống nếu không có]
    # Pseudo-code, actual code, SQL, config
    # Dart, TypeScript, Python tùy context
```

---

## EDGE STANDARD

```yaml
# Thay vì outgoing/incoming lists:
relationships:
  - target: "doc:DOC-07"
    type:   "specified_in"
    reason: "Flow này được mô tả đầy đủ trong DOC-07 section F3"

  - target: "engine:trust_gate"
    type:   "validated_by"
    reason: "TrustGate kiểm tra GPS signal trước khi allow MiHot"
```

---

## DISPLAY STANDARD

```
get: mode=brief  → name, group, description.info, relationships (với reason)
                   Ẩn: id, revision, timestamps, _dispatch, raw fields

get: mode=full   → tất cả fields có nghĩa
                   Ẩn: raw technical metadata

get: mode=debug  → tất cả kể cả raw fields
                   Chỉ dùng khi debug
```

---

## FIELDS THAY THẾ

```
status   → lifecycle: draft | specified | implemented | tested | deprecated
priority → read_order: foundational | important | reference | background
```

---

*GoBP Schema Redesign v2.1 — 2026-04-19*
*Approved — Wave 17A01 ready to brief*
◈
