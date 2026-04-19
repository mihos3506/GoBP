# ◈ GoBP ARCHITECTURE v3
**Status:** AUTHORITATIVE  
**Date:** 2026-04-19  
**Supersedes:** GoBP_ARCHITECTURE.md v0.1  
**Read after:** SCHEMA.md  
**Audience:** Cursor (implement), Claude CLI (audit), CTO Chat (design)

---

## SAU KHI ĐỌC FILE NÀY, AI BIẾT

1. Hệ thống gồm những layers nào và layer nào làm gì
2. PostgreSQL là primary storage — không phải optional
3. File-first vẫn tồn tại nhưng vai trò thay đổi theo scale
4. GraphIndex hoạt động thế nào: metadata, LRU cache, PostgreSQL
5. Write path: validate → ID → PostgreSQL → file → history
6. Các cải tiến: description pyramid, graph-guided search, edge reason index
7. Multi-agent coordination: cache invalidation, conflict detection, session visibility

---

## 1. SYSTEM LAYERS

```
┌──────────────────────────────────────────────────────────┐
│  AI AGENTS                                               │
│  Cursor · Claude CLI · Claude Desktop · any MCP client   │
│  Single interface: gobp(query="...")                     │
└─────────────────────────┬────────────────────────────────┘
                          │ MCP / JSON-RPC over stdio
                          ▼
┌──────────────────────────────────────────────────────────┐
│  MCP LAYER  gobp/mcp/                                    │
│  server.py       — tool registration, stdio loop         │
│  dispatcher.py   — route query string → action handler   │
│  batch_parser.py — parse ops, named params, multiline    │
│  tools/read.py   — find, get, get_batch, explore, suggest│
│  tools/write.py  — create, upsert, session, batch exec   │
│  tools/maintain.py — validate, stats, dedupe, recompute  │
│  tools/import_.py  — import proposal + commit            │
└─────────────────────────┬────────────────────────────────┘
                          │ Python function calls
                          ▼
┌──────────────────────────────────────────────────────────┐
│  CORE LAYER  gobp/core/                                  │
│  graph.py        — GraphIndex: metadata + LRU + PG       │
│  loader.py       — load từ PostgreSQL + files            │
│  validator.py    — schema v3 validation                  │
│  mutator.py      — write-through: PG + file + history    │
│  id_generator.py — v2 ID format                          │
│  file_format.py  — serialize/deserialize YAML+MD         │
│  history.py      — append-only JSONL audit log           │
│  db.py           — PostgreSQL connection + queries       │
└──────────┬──────────────────────────┬────────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────┐      ┌──────────────────────────────┐
│  FILE STORAGE    │      │  POSTGRESQL (PRIMARY)         │
│  .gobp/          │      │  Required: GOBP_DB_URL        │
│  Audit trail     │      │  Source of truth at scale     │
│  Human inspect   │      │  tsvector + GIN index         │
│  Git backup      │      │  Recursive CTE traversal      │
└──────────────────┘      └──────────────────────────────┘
```

**Nguyên tắc cốt lõi:**
```
PostgreSQL = source of truth khi GOBP_DB_URL được set
File .gobp/ = audit trail + human inspection + git backup
Mất PostgreSQL → rebuild từ files (gobp validate --reindex)
Mất files → data vẫn an toàn trong PostgreSQL
AI không bao giờ đọc/ghi files trực tiếp — luôn qua MCP
```

---

## 2. STORAGE STRATEGY THEO SCALE

```
< 5,000 nodes (TIER 1):
  PostgreSQL: recommended nhưng optional
  Fallback: SQLite FTS5 (.gobp/index.db)
  In-memory GraphIndex: full metadata + adjacency lists
  File: source of truth (nếu không có PostgreSQL)

5,000 – 100,000 nodes (TIER 2):
  PostgreSQL: REQUIRED
  In-memory: chỉ metadata (name, group, desc_l1)
  Adjacency: từ PostgreSQL, không load vào memory
  LRU cache: 500 hot nodes

100,000+ nodes (TIER 3):
  PostgreSQL: REQUIRED + table partitioning
  In-memory: LRU 1,000 hot nodes only
  Graph traversal: PostgreSQL recursive CTE
  File: audit trail only (không phải source of truth)

Auto-detect tier:
  Startup → count nodes → set tier → configure accordingly
  Migration: gobp migrate --to-tier=2 khi vượt threshold
```

---

## 3. FILE STORAGE STRUCTURE

```
{project_root}/
├── .gobp/
│   ├── config.yaml          ← project identity, schema_version, tier
│   ├── nodes/               ← node files (source of truth khi Tier 1)
│   │   ├── {node_id}.md     ← 1 file per node
│   │   └── ...
│   ├── edges/
│   │   └── relations.yaml   ← edge YAML (backup)
│   └── history/             ← append-only audit log (tất cả tiers)
│       └── YYYY-MM-DD.jsonl
│
└── gobp/schema/             ← copy từ package khi init
    ├── core_nodes.yaml      ← node type registry
    └── core_edges.yaml      ← edge type registry (system reference)
```

### Node file format (schema v3)

```yaml
---
id: dev.infrastructure.engine.paymentservice.a1b2c3d4
name: PaymentService
group: Dev > Infrastructure > Engine
description: |
  Handles financial transactions between users. Validates balance
  before debit. Executes atomic credit/debit operations. Exposes
  REST API for payment initiation and status queries.
code: |
  async def transfer(from_id, to_id, amount):
      await validate_balance(from_id, amount)
      await db.atomic_transfer(from_id, to_id, amount)
history:
  - description: "Cursor Wave 12B: Added idempotency key support vì mobile
    client retry on timeout mà không check request gốc đã success chưa."
created_at: 2026-04-19T10:00:00Z
session_id: meta.session.2026-04-19.abc12345
---
```

### Edge file format (schema v3)

```yaml
- from: dev.infrastructure.engine.paymentservice.a1b2c3d4
  to:   dev.infrastructure.engine.authservice.b2c3d4e5
  reason: "PaymentService verifies auth token before executing any transaction"
  created_at: 2026-04-19T10:00:00Z
```

**Không có `type` field — edge type do hệ thống infer.**

### History log (audit — tự động)

```jsonl
{"ts":"2026-04-19T10:00:00Z","op":"node_create","actor":"cto_chat","id":"dev.infrastructure.engine.paymentservice.a1b2c3d4","session":"meta.session.2026-04-19.abc"}
{"ts":"2026-04-19T10:05:00Z","op":"node_update","actor":"cursor","id":"dev.infrastructure.engine.paymentservice.a1b2c3d4"}
{"ts":"2026-04-19T10:10:00Z","op":"edge_add","from":"paymentservice.x","to":"authservice.y"}
```

---

## 4. ID SYSTEM v2

```
Format: {group_slug}.{name_slug}.{8hex}

group_slug: breadcrumb path → lowercase, dots
  "Dev > Infrastructure > Engine" → "dev.infrastructure.engine"

name_slug: name → lowercase, underscores
  "PaymentService" → "paymentservice"

8hex: MD5(name + group)[:8]
  Deterministic — same name+group = same suffix

Ví dụ:
  Engine "PaymentService":
    dev.infrastructure.engine.paymentservice.a1b2c3d4

  Table "orders":
    dev.infrastructure.database.table.orders.b2c3d4e5

Special formats:
  Session:  meta.session.YYYY-MM-DD.{8hex}
  TestCase: {suite}.test.{kind}.{seq}

Rules:
  □ ID bất biến sau khi tạo
  □ Collision → extend 8hex thêm 2 chars
  □ Bỏ trống id khi create → auto-generate
```

---

## 5. POSTGRESQL SCHEMA

```sql
-- Core nodes table
CREATE TABLE nodes (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    group_path  TEXT NOT NULL,

    -- Description pyramid (auto-extracted khi import)
    desc_l1     TEXT,     -- Headline ~15 tokens: câu đầu tiên
    desc_l2     TEXT,     -- Context ~40 tokens: 2-3 câu đầu
    desc_full   TEXT,     -- Full description

    code        TEXT,     -- Optional code snippet

    -- ErrorCase only
    severity    TEXT,     -- fatal|error|warning|info

    -- Full-text search vector
    -- Bao gồm: name + desc_full + group + edge reasons
    search_vec  tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(desc_l2, '')), 'B') ||
        setweight(to_tsvector('simple', coalesce(group_path, '')), 'C')
    ) STORED,

    updated_at  BIGINT NOT NULL DEFAULT extract(epoch from now())
);

-- Edges table (no type field — inferred by system)
CREATE TABLE edges (
    from_id    TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    to_id      TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    reason     TEXT,
    reason_vec tsvector GENERATED ALWAYS AS (
        to_tsvector('simple', coalesce(reason, ''))
    ) STORED,
    code       TEXT,
    created_at BIGINT NOT NULL DEFAULT extract(epoch from now()),
    PRIMARY KEY (from_id, to_id)   -- auto dedup
);

-- History table
CREATE TABLE node_history (
    id          SERIAL PRIMARY KEY,
    node_id     TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    code        TEXT,
    created_at  BIGINT NOT NULL DEFAULT extract(epoch from now())
);

-- Indexes
CREATE INDEX idx_nodes_search    ON nodes USING GIN(search_vec);
CREATE INDEX idx_nodes_group     ON nodes(group_path text_pattern_ops);
CREATE INDEX idx_nodes_updated   ON nodes(updated_at);
CREATE INDEX idx_edges_from      ON edges(from_id);
CREATE INDEX idx_edges_to        ON edges(to_id);
CREATE INDEX idx_edges_reason    ON edges USING GIN(reason_vec);
CREATE INDEX idx_history_node    ON node_history(node_id);

-- Tier 3 partitioning (100K+ nodes)
-- Uncomment khi migrate sang Tier 3:
-- ALTER TABLE nodes PARTITION BY HASH(id);
-- CREATE TABLE nodes_0 PARTITION OF nodes FOR VALUES WITH (modulus 8, remainder 0);
-- ... nodes_1 đến nodes_7
```

**Edge reason trong search:**

Edge reasons được index riêng (`reason_vec`) và join vào node search khi query. Query "payment validation" có thể tìm ra `AuthService` nếu edge reason từ `PaymentService` → `AuthService` chứa "payment validation".

---

## 6. GRAPHINDEX

### Design

```
Tier 1 (< 5K):
  _meta:      dict[id → NodeMeta]    — full metadata in memory
  _outgoing:  dict[id → list[Edge]]  — full adjacency in memory
  _incoming:  dict[id → list[Edge]]

Tier 2+ (≥ 5K):
  _meta:      dict[id → NodeMeta]    — metadata only (name, group, desc_l1)
  _lru:       LRUCache(500-1000)     — full nodes cho hot queries
  _outgoing:  KHÔNG load vào memory — query từ PostgreSQL

NodeMeta fields:
  id, name, group_path, desc_l1, updated_at
```

### Inverted Group Index — O(1) Group Lookup

```python
class GraphIndex:
    def __init__(self):
        # Existing fields...
        self._group_index: dict[str, list[str]] = {}

    def _build_group_index(self):
        """Build tại startup. Index full path + tất cả prefixes."""
        for node_id, node in self._meta.items():
            group = node.group_path
            parts = [p.strip() for p in group.split('>')]
            for i in range(1, len(parts) + 1):
                prefix = ' > '.join(parts[:i])
                self._group_index.setdefault(prefix, [])
                if node_id not in self._group_index[prefix]:
                    self._group_index[prefix].append(node_id)

    def find_by_group(self, group_path: str) -> list[str]:
        """
        O(1) lookup thay vì O(N) scan.
        Prefix match: "Dev > Infrastructure" trả về tất cả
        nodes thuộc Dev > Infrastructure > * (Engine, API, DB...)
        """
        result = []
        normalized = group_path.strip()
        for indexed_path, node_ids in self._group_index.items():
            if (indexed_path == normalized or
                    indexed_path.startswith(normalized + ' >')):
                for nid in node_ids:
                    if nid not in result:
                        result.append(nid)
        return result
```

**Impact tại Tier 2/3:**
```
50K nodes × group filter O(N) = 50,000 comparisons per query
50K nodes × group filter O(1) = 1 dict lookup
→ 50,000x faster cho group-filtered queries
```

### Since= Mechanism — Differential Fetch

```python
def get_batch(ids: list[str], since: int = None) -> dict:
    """
    since = unix timestamp của lần fetch trước.
    Chỉ trả về full data cho nodes đã changed.
    Unchanged nodes = 5 tokens thay vì 40 tokens.
    """
    if since is None:
        # Full fetch — normal behavior
        return {id: get_node(id) for id in ids}

    # Check updated_at cho từng node
    rows = db.query(
        "SELECT id, updated_at FROM nodes WHERE id = ANY($1)",
        [ids]
    )
    updated_at_map = {r['id']: r['updated_at'] for r in rows}

    result = {}
    for node_id in ids:
        node_updated_at = updated_at_map.get(node_id, 0)
        if node_updated_at <= since:
            # Không đổi — trả về minimal token
            result[node_id] = {'id': node_id, 'unchanged': True}
        else:
            # Đã đổi — trả về full data
            result[node_id] = get_node(node_id)

    return result
```

**Impact:**
```
Session thứ 2 trở đi (80% nodes unchanged):
  Trước: 10 nodes × 40 tokens = 400 tokens
  Sau:   2 nodes × 40 + 8 nodes × 5 = 120 tokens
  Savings: 70%
```

```python
def startup(project_root, db_url=None):
    config = read_yaml(".gobp/config.yaml")
    tier   = detect_tier(db_url)

    if tier == 1:
        meta  = load_metadata_from_files(project_root)
        edges = load_edges_from_files(project_root)
    else:
        meta  = db.query("SELECT id,name,group_path,desc_l1,updated_at FROM nodes")

    # Target: < 200ms cho 50K nodes
```

### BM25F Weighted Search Vector

```sql
-- search_vec với trọng số BM25F
-- Name match quan trọng nhất, edge reason ít nhất
search_vec tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('simple', coalesce(name, '')), 'A')        -- weight 3.0
    || setweight(to_tsvector('simple', coalesce(group_path, '')), 'B') -- weight 2.0
    || setweight(to_tsvector('simple', coalesce(desc_l2, '')), 'C')    -- weight 1.0
) STORED

-- Edge reasons index riêng trên edges table
-- Joined vào node search khi query
reason_vec tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(reason, ''))                        -- weight 0.5
) STORED
```

**Ranking formula:**
```
final_rank = ts_rank_cd(search_vec, query, weights='{0.5, 1.0, 2.0, 3.0}')
             × (1.0 + log1p(edge_count) × 0.15)   -- graph boost
```

Kết quả: "PaymentService" trong name → rank cao hơn nhiều so với "PaymentService" chỉ xuất hiện trong description.

### find() — Graph-Guided Search

```python
def find(query, group_filter=None, depth=1):
    """
    Step 1: Full-text search với BM25F weighted fields
            → candidates từ name + group + description + edge reasons

    Step 2: BFS expand depth=1 qua PostgreSQL CTE
            → discover related nodes AI chưa biết cần hỏi

    Step 3: Group filter từ inverted index (O(1))

    Step 4: Rank: BM25F × graph_boost(edge_count)

    Step 5: Description pyramid
            → trả về desc_l1 (find) hoặc desc_l2 (get_batch)
    """
    sql = """
    WITH seed AS (
        SELECT id, name, group_path, desc_l1,
               ts_rank_cd(search_vec, query,
                          array[0.5, 1.0, 2.0, 3.0]) AS rank
        FROM nodes,
             to_tsquery('simple', $1) query
        WHERE search_vec @@ query
          AND ($2::text IS NULL OR group_path LIKE $2 || '%')
        ORDER BY rank DESC
        LIMIT 20
    ),
    expanded AS (
        SELECT DISTINCT n.id, n.name, n.group_path, n.desc_l1, 0.5 AS rank
        FROM seed s
        JOIN edges e ON e.from_id = s.id OR e.to_id = s.id
        JOIN nodes n ON n.id = CASE
            WHEN e.from_id = s.id THEN e.to_id ELSE e.from_id
        END
        WHERE NOT EXISTS (SELECT 1 FROM seed WHERE id = n.id)
    )
    SELECT id, name, group_path, desc_l1, rank FROM seed
    UNION ALL
    SELECT id, name, group_path, desc_l1, rank FROM expanded
    ORDER BY rank DESC
    LIMIT 30
    """
    return db.query(sql, [query, group_filter])
```

### Edge Type Inference

```python
def infer_edge_type(from_node, to_node, reason=""):
    """Hệ thống tự gán edge type — người dùng không khai báo."""
    from_depth = from_node.group_path.count('>')
    to_depth   = to_node.group_path.count('>')
    reason_lower = reason.lower()

    # RULE 1: Supersede
    if from_node.type == to_node.type:
        if any(w in reason_lower for w in ['replace', 'supersede', 'thay thế']):
            return 'supersedes'

    # RULE 2: Vertical (con → cha)
    if from_depth > to_depth:
        if to_node.group_path in from_node.group_path:
            return 'belongs_to'

    # RULE 3: Error/Test → target
    if 'error' in from_node.group_path.lower():
        return 'affects'
    if 'test' in from_node.group_path.lower():
        return 'covers'

    # RULE 4: Document/Spec target
    if 'document' in to_node.group_path.lower():
        return 'specified_in'

    # RULE 5: Fallback
    return 'relates_to'
```

---

## 7. WRITE PATH

```python
def node_upsert(node_data, session_id, expected_updated_at=None):
    """
    1. Validate: description không rỗng + group hợp lệ
    2. Auto-fix: group từ type nếu thiếu
    3. Generate ID nếu chưa có
    4. Extract description pyramid:
       desc_l1 = first sentence [:100 chars]
       desc_l2 = first 3 sentences [:300 chars]
       desc_full = full text
    5. Optimistic lock check (nếu expected_updated_at được gửi)
    6. Write PostgreSQL — ON CONFLICT DO UPDATE
    7. Write file .gobp/nodes/{id}.md (backup)
    8. Append history log
    9. Invalidate cache (node + group)
    10. Return: {ok, id, conflict_warning?}
    """
```

### Concurrency

```
PostgreSQL WAL + ON CONFLICT DO UPDATE:
  Nhiều agents write cùng lúc → PostgreSQL serialize tự động
  Không cần lock ở application level
  Last-write-wins với updated_at timestamp

File writes:
  Non-critical (backup only)
  Failure không block PostgreSQL write
  Retry async nếu fail
```

---

## 8. DESCRIPTION PYRAMID

```python
def extract_pyramid(full_text: str) -> tuple[str, str]:
    """Auto-extract khi import node. Không cần AI làm gì thêm."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_text)
                 if s.strip()]
    l1 = sentences[0][:100] if sentences else ""
    l2 = " ".join(sentences[:3])[:300] if sentences else ""
    return l1, l2
```

**Response modes:**

| Action | Returns | Tokens/node |
|---|---|---|
| `find:` | desc_l1 | ~15 |
| `get_batch: mode=summary` | desc_l1 | ~15 |
| `get_batch: mode=brief` | desc_l2 | ~40 |
| `get: mode=full` | desc_full | ~200+ |

---

## 9. QUERY RESULT CACHE

```python
class QueryCache:
    """Short-lived cache cho identical queries trong multi-agent env."""

    def __init__(self, ttl_seconds=30):
        self._cache = {}
        self._ttl = ttl_seconds

    def get(self, query_hash: str):
        entry = self._cache.get(query_hash)
        if entry and time.time() - entry['ts'] < self._ttl:
            return entry['result']
        return None

    def set(self, query_hash: str, result):
        self._cache[query_hash] = {'result': result, 'ts': time.time()}

    def invalidate_group(self, group_path: str):
        self._cache = {k: v for k, v in self._cache.items()
                      if group_path not in k}

    def invalidate_node(self, node_id: str):
        """Invalidate queries liên quan node này."""
        self._cache = {k: v for k, v in self._cache.items()
                      if node_id not in k}

    def invalidate_edge(self, from_id: str, to_id: str):
        """Edge write thay đổi graph context của cả 2 nodes."""
        self._cache = {k: v for k, v in self._cache.items()
                      if from_id not in k and to_id not in k}
```

---

## 10. MCP SERVER

### Lifecycle

```
Startup:
  1. Read GOBP_PROJECT_ROOT env var
  2. Connect PostgreSQL (GOBP_DB_URL) — required cho Tier 2+
  3. Detect tier từ node count
  4. Load metadata vào GraphIndex
  5. Init QueryCache + LRU
  6. Register 1 tool: gobp(query: string)
  7. Start JSON-RPC loop over stdio

Per request:
  gobp(query) → dispatcher → action handler
  Read:  QueryCache → LRU → PostgreSQL
  Write: validate → optimistic lock check → PostgreSQL
         → file → history → invalidate cache

Shutdown:
  Flush pending file writes
  Close PostgreSQL connection pool
```

### Response format

```python
MAX_RESPONSE_BYTES = 32_768  # 32KB stdio limit

def chunk_response(data, key='matches'):
    json_str = json.dumps(data, ensure_ascii=False)
    if len(json_str.encode()) <= MAX_RESPONSE_BYTES:
        return [json_str]
    items = data.get(key, [])
    chunk_size = max(1, 20)
    return [json.dumps({**data, key: items[i:i+chunk_size],
                        '_chunk': i//chunk_size})
            for i in range(0, len(items), chunk_size)]
```

---

## 11. VALIDATOR

```python
class Validator:
    """Schema v3: 2 templates → validation đơn giản."""

    def validate(self, node: dict) -> list[str]:
        errors = []
        if not node.get('name'):
            errors.append("name là required")
        if not node.get('group'):
            errors.append("group là required")
        if not (node.get('description') or '').strip():
            errors.append("description không được rỗng")
        if node.get('type') == 'ErrorCase':
            if node.get('severity') not in {'fatal','error','warning','info'}:
                errors.append("ErrorCase.severity phải là: fatal|error|warning|info")
        return errors

    def auto_fix(self, node: dict) -> dict:
        if not node.get('group') and node.get('type'):
            node['group'] = GROUP_BY_TYPE.get(node['type'], 'Unknown')
        return node
```

---

## 12. MODULE STRUCTURE

```
gobp/
├── mcp/
│   ├── server.py        ← stdio MCP server
│   ├── dispatcher.py    ← route query → handler
│   ├── batch_parser.py  ← parse batch ops
│   └── tools/
│       ├── read.py      ← find, get, explore, suggest
│       ├── write.py     ← create, upsert, session, batch
│       ├── maintain.py  ← validate, stats, dedupe
│       └── import_.py   ← import proposal + commit
├── core/
│   ├── graph.py         ← GraphIndex
│   ├── loader.py        ← load từ PG + files
│   ├── validator.py     ← schema v3 validation
│   ├── mutator.py       ← write-through
│   ├── id_generator.py  ← v2 ID format
│   ├── file_format.py   ← YAML+MD serialization
│   ├── history.py       ← JSONL audit log
│   ├── db.py            ← PostgreSQL connection + queries
│   └── cache.py         ← LRU + QueryCache
└── schema/
    ├── core_nodes.yaml  ← node type registry
    └── core_edges.yaml  ← edge type reference (system)

Dependency rules:
  mcp/tools/ → import core/ ✓
  core/      → KHÔNG import mcp/ (tránh circular)
  schema/    → pure YAML data
```

---

## 13. PERFORMANCE TARGETS

| Operation | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Cold start | < 100ms | < 200ms | < 500ms |
| find: (full-text) | < 5ms | < 10ms | < 20ms |
| get: (LRU hit) | < 1ms | < 1ms | < 1ms |
| get: (PG query) | < 5ms | < 10ms | < 15ms |
| get_batch: 10 nodes | < 20ms | < 30ms | < 50ms |
| node_upsert | < 50ms | < 100ms | < 150ms |
| batch: 50 ops | < 1s | < 2s | < 5s |
| Memory (metadata) | < 10MB | < 30MB | < 100MB |

---

## 14. KHÔNG THUỘC SCOPE

```
× Multi-tenant shared graph
× Real-time sync across machines
× Authentication / RBAC
× Code AST parsing
× Vector/semantic search (evaluate khi > 50K nodes)
× Enterprise knowledge management
```

---

## 15. MULTI-AGENT COORDINATION

Nhiều AI agents (Cursor, Claude CLI, CTO Chat) cùng làm việc trên 1 graph.
4 vấn đề và thuật toán giải quyết.

---

### 15.1 CACHE INVALIDATION TOÀN DIỆN

**Vấn đề:** Edge write không trigger cache invalidate → agents thấy graph cũ.

```python
# Write path update:

# Sau node write:
cache.invalidate_node(node_id)
cache.invalidate_group(node.group_path)

# Sau edge write:
cache.invalidate_edge(from_id, to_id)
# Vì: edge thay đổi graph context của cả 2 nodes
```

---

### 15.2 OPTIMISTIC LOCKING — CONFLICT DETECTION

**Vấn đề:** Last-write-wins im lặng → work của agent bị overwrite mà không biết.

```python
def node_upsert(node_data, session_id, expected_updated_at=None):
    if expected_updated_at:
        current = db.get_updated_at(node_data['id'])
        if current and current != expected_updated_at:
            # Warn nhưng không block — agent tự quyết
            result['conflict_warning'] = {
                'conflict':  True,
                'expected':  expected_updated_at,
                'actual':    current,
                'message':   'Node was modified by another agent'
            }
    # Continue với write bình thường
```

**Agent nhận conflict_warning:**
```
→ Đọc lại node (version mới nhất)
→ Merge manually nếu cần
→ Retry write với expected_updated_at mới
```

---

### 15.3 ACTIVE SESSION VISIBILITY

**Vấn đề:** Agents không biết agent khác đang làm gì → modify cùng nodes.

```python
def gobp_overview(...):
    # Thêm vào response:
    active_sessions = db.query("""
        SELECT id, actor, goal, started_at, nodes_touched
        FROM nodes
        WHERE type = 'Session' AND status = 'IN_PROGRESS'
        ORDER BY started_at DESC LIMIT 10
    """)
    result['active_sessions'] = [
        {
            'session_id':   s['id'],
            'actor':        s['actor'],
            'goal':         s['goal'][:80],
            'nodes_touched': s.get('nodes_touched', [])
        }
        for s in active_sessions
    ]
```

**Agent đọc active_sessions trước khi start:**
```
→ Thấy Cursor đang sửa [Feature X, Table Y]
→ Tránh modify cùng nodes
→ Soft coordination — không block, chỉ inform
```

---

### 15.4 IDEMPOTENT IMPORT — PREVENT DUPLICATE

**Vấn đề:** Nhiều agents cùng import 1 document → duplicate nodes.

```python
# In-memory import lock (MCP server là single process)
_import_locks: dict[str, str] = {}  # path → session_id

def handle_import(path, session_id):
    if path in _import_locks:
        holder = _import_locks[path]
        if holder != session_id:
            return {
                'ok': False,
                'importing_by': holder,
                'message': f'Import in progress by {holder}'
            }
    _import_locks[path] = session_id
    try:
        return do_import(path, session_id)  # dùng upsert, không create
    finally:
        _import_locks.pop(path, None)
```

**Rule:** Tất cả import ops dùng **upsert** không phải **create** → chạy lại lần 2 = safe.

---

### 15.5 SUMMARY

```
Vấn đề                  Thuật toán
────────────────────────────────────────────────────────────
Cache stale (edge)       invalidate_edge(from_id, to_id)
Conflict im lặng         Optimistic lock — expected_updated_at
Không biết nhau          active_sessions trong overview:
Import duplicate         Import lock + upsert
```

---

*GoBP ARCHITECTURE v3 — 2026-04-19*  
*PostgreSQL primary · File audit trail · Schema v3 aligned*  
*Tier 1 (<5K) · Tier 2 (5K-100K) · Tier 3 (100K+)*  
*Section 15: Multi-Agent Coordination*  
◈
