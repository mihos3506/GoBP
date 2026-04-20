# ◈ GoBP SCHEMA v3
**Status:** SOURCE OF TRUTH  
**Date:** 2026-04-19

---

## TEMPLATE 1 — MỌI NODE

```yaml
name:        {tên mô tả rõ ràng}
group:       {breadcrumb đầy đủ}
description: {plain text — mô tả đầy đủ}
code:        {optional — snippet kỹ thuật; lưu riêng description vs code trong PG (desc_* / code)}
history[]:   [{description, code}]   # append-only, không sửa không xóa
```

---

## TEMPLATE 2 — ERRORCASE

```yaml
name:        {tên mô tả rõ ràng}
group:       {Error > domain}
severity:    {fatal | error | warning | info}
description: {plain text — mô tả đầy đủ}
code:        {optional}
history[]:   [{description, code}]   # append-only, không sửa không xóa
```

---

## EDGE

```yaml
from:    {node}
to:      {node}
reason:  {plain text — tại sao kết nối này tồn tại}
code:    {optional — snippet kỹ thuật; lưu riêng reason trong DB/PG để AI chỉ đọc field cần}
```

PostgreSQL v3: bảng `edges` có hai cột **`reason`** và **`code`** (tách bạch; FTS `reason_vec` chỉ index `reason`).

Edge type do hệ thống tự xác định — người nhập không khai báo.

---

## NGUYÊN TẮC

```
1. Node = điểm kết nối — knowledge sống trong edges
2. name + group = unique identity trong graph
3. description chứa tất cả — không dùng fields nhỏ lẻ
4. history[] ghi khi node thay đổi ý nghĩa — không phải typo
5. Edge reason bắt buộc — mô tả tại sao kết nối tồn tại
6. Edge type do hệ thống infer — AI không khai báo
7. Ít fields = ít token khi nhập + ít token khi query
```

---

## NODE TAXONOMY

### DOCUMENT
```
Document
  ├── Idea        "Document > Idea"
  │               Ý tưởng thô, chưa chốt
  │               Flow: Idea → Spec → Document
  │
  ├── Spec        "Document > Spec"
  │               Đặc tả kỹ thuật — tập hợp ideas đã chốt
  │
  ├── Document    "Document > Document"
  │               Tài liệu hoàn chỉnh — tập hợp nhiều specs
  │
  └── Lesson      "Document > Lesson"
                  Tên cố định, self-updating
                  VD: "Cursor Rules", "CTO Architecture Rules", "QA Audit Rules"
```

### DEV > DOMAIN
```
  ├── Entity        "Dev > Domain > Entity"
  ├── ValueObject   "Dev > Domain > ValueObject"
  ├── DomainEvent   "Dev > Domain > DomainEvent"
  └── Aggregate     "Dev > Domain > Aggregate"
```

### DEV > APPLICATION
```
  ├── Flow       "Dev > Application > Flow"
  ├── Feature    "Dev > Application > Feature"
  ├── Command    "Dev > Application > Command"
  └── UseCase    "Dev > Application > UseCase"
```

### DEV > INFRASTRUCTURE
```
  ├── Engine          "Dev > Infrastructure > Engine"
  ├── Repository      "Dev > Infrastructure > Repository"
  │
  ├── API
  │   ├── APIContract   "Dev > Infrastructure > API > APIContract"
  │   ├── APIEndpoint   "Dev > Infrastructure > API > APIEndpoint"
  │   ├── APIRequest    "Dev > Infrastructure > API > APIRequest"
  │   ├── APIResponse   "Dev > Infrastructure > API > APIResponse"
  │   ├── APIMiddleware "Dev > Infrastructure > API > APIMiddleware"
  │   ├── APIVersion    "Dev > Infrastructure > API > APIVersion"
  │   └── Webhook       "Dev > Infrastructure > API > Webhook"
  │
  ├── Security
  │   ├── AuthFlow        "Dev > Infrastructure > Security > AuthFlow"
  │   ├── AuthZ           "Dev > Infrastructure > Security > AuthZ"
  │   ├── Permission      "Dev > Infrastructure > Security > Permission"
  │   ├── Policy          "Dev > Infrastructure > Security > Policy"
  │   ├── Token           "Dev > Infrastructure > Security > Token"
  │   ├── Encryption      "Dev > Infrastructure > Security > Encryption"
  │   ├── Secret          "Dev > Infrastructure > Security > Secret"
  │   ├── SecurityAudit   "Dev > Infrastructure > Security > Audit"
  │   ├── ThreatModel     "Dev > Infrastructure > Security > ThreatModel"
  │   ├── Vulnerability   "Dev > Infrastructure > Security > Vulnerability"
  │   └── RateLimitPolicy "Dev > Infrastructure > Security > RateLimitPolicy"
  │
  ├── Database
  │   ├── DBSchema       "Dev > Infrastructure > Database > Schema"
  │   ├── Table          "Dev > Infrastructure > Database > Table"
  │   ├── Column         "Dev > Infrastructure > Database > Column"
  │   ├── View           "Dev > Infrastructure > Database > View"
  │   ├── Migration      "Dev > Infrastructure > Database > Migration"
  │   ├── DBIndex        "Dev > Infrastructure > Database > Index"
  │   ├── NamedQuery     "Dev > Infrastructure > Database > Query"
  │   ├── ConnectionPool "Dev > Infrastructure > Database > ConnectionPool"
  │   └── Seed           "Dev > Infrastructure > Database > Seed"
  │
  ├── Messaging
  │   ├── EventBus        "Dev > Infrastructure > Messaging > EventBus"
  │   ├── Queue           "Dev > Infrastructure > Messaging > Queue"
  │   ├── Message         "Dev > Infrastructure > Messaging > Message"
  │   ├── DeadLetterQueue "Dev > Infrastructure > Messaging > DeadLetterQueue"
  │   ├── Topic           "Dev > Infrastructure > Messaging > Topic"
  │   └── Worker          "Dev > Infrastructure > Messaging > Worker"
  │
  ├── Observability
  │   ├── Metric    "Dev > Infrastructure > Observability > Metric"
  │   ├── SLO       "Dev > Infrastructure > Observability > SLO"
  │   ├── LogSpec   "Dev > Infrastructure > Observability > Log"
  │   ├── TraceSpec "Dev > Infrastructure > Observability > Trace"
  │   └── Alert     "Dev > Infrastructure > Observability > Alert"
  │
  ├── Cache
  │   ├── CacheLayer  "Dev > Infrastructure > Cache > CacheLayer"
  │   └── CacheKey    "Dev > Infrastructure > Cache > CacheKey"
  │
  ├── Storage
  │   ├── StorageBucket   "Dev > Infrastructure > Storage > Bucket"
  │   ├── MediaProcessing "Dev > Infrastructure > Storage > Media"
  │   └── CDN             "Dev > Infrastructure > Storage > CDN"
  │
  ├── Config
  │   ├── EnvConfig    "Dev > Infrastructure > Config > EnvConfig"
  │   └── FeatureFlag  "Dev > Infrastructure > Config > FeatureFlag"
  │
  ├── Deployment
  │   ├── Environment       "Dev > Infrastructure > Deployment > Environment"
  │   ├── ServiceDefinition "Dev > Infrastructure > Deployment > Service"
  │   └── Pipeline          "Dev > Infrastructure > Deployment > Pipeline"
  │
  ├── Network
  │   ├── LoadBalancer "Dev > Infrastructure > Network > LoadBalancer"
  │   ├── ServiceMesh  "Dev > Infrastructure > Network > ServiceMesh"
  │   └── DNSRecord    "Dev > Infrastructure > Network > DNS"
  │
  └── ThirdParty
      ├── ExternalService "Dev > Infrastructure > ThirdParty > ExternalService"
      └── SDK             "Dev > Infrastructure > ThirdParty > SDK"
```

### DEV > FRONTEND
```
  ├── Screen     "Dev > Frontend > Screen"
  └── Component  "Dev > Frontend > Component"
```

### DEV > CODE
```
  ├── Interface  "Dev > Code > Interface"
  ├── Enum       "Dev > Code > Enum"
  └── Module     "Dev > Code > Module"
```

### CONSTRAINT
```
  ├── Invariant     "Constraint > Invariant"
  │                 Boolean expression — ĐÚNG: "balance >= 0"
  │                 SAI: "không được X" → dùng BusinessRule
  │
  └── BusinessRule  "Constraint > BusinessRule"
                    Soft policy — prose, không phải boolean
```

### ERROR
```
  ├── ErrorDomain  "Error > ErrorDomain"
  └── ErrorCase    "Error > {domain}"    ← dùng Template 2
```

### TEST
```
  ├── TestSuite  "Test > TestSuite"
  ├── TestKind   "Test > TestKind"
  └── TestCase   "Test > TestCase"
```

### META
```
  ├── Session     "Meta > Session"
  ├── Wave        "Meta > Wave"
  ├── Task        "Meta > Task"
  └── Reflection  "Meta > Reflection"
```

---

*GoBP SCHEMA v3 — 2026-04-19*  
*2 templates. 1 edge format. ~75 node types.*  
◈
