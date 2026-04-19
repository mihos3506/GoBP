# WAVE A BRIEF — DATABASE FOUNDATION

**Wave:** A  
**Title:** PostgreSQL Schema v3 + Validator v3 + Description Pyramid  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-19  
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)  
**Status:** READY FOR EXECUTION  
**Task count:** 6 atomic tasks  
**Estimated effort:** 4-5 hours  

---

## CONTEXT

GoBP đang chạy schema v2.1 với 93 node types, typed edges, và nhiều typed fields. Document set v3 đã được CEO approve với thiết kế hoàn toàn mới:

```
Schema v3:
  - 2 templates: base node + ErrorCase
  - description (plain text) + code (optional)
  - history[] append-only (description only)
  - Edge: from + to + reason (no type field)
  - ~75 node types qua group breadcrumb taxonomy

Thay đổi cốt lõi:
  - Không còn 93 typed fields riêng lẻ
  - Edge type do hệ thống infer (không khai báo)
  - description pyramid: desc_l1 / desc_l2 / desc_full
  - PostgreSQL là primary, files là backup
```

Wave A xây dựng foundation: PostgreSQL schema mới, validator đơn giản, pyramid extractor, file format mới. Các wave tiếp theo (B, C, D, E, F) sẽ build trên nền này.

**KHÔNG thay đổi logic hiện tại** — Wave A chỉ tạo các modules mới song song. Migration data cũ sẽ là Wave F.

---

## REFERENCED DOCUMENTS

| Doc | Mục đích |
|---|---|
| `docs/SCHEMA.md` | Source of truth — 2 templates, taxonomy |
| `docs/ARCHITECTURE.md` | PostgreSQL schema, pyramid algorithm, tiers |
| `docs/MCP_PROTOCOL.md` | Validator rules, edit: semantics |

---

## CURSOR EXECUTION RULES (READ FIRST — NON-NEGOTIABLE)

### R1 — Sequential execution
Tasks 1 → 6 in order. No skipping, no reordering.

### R2 — Discovery before creation
Read existing files before creating or modifying anything.

### R3 — 1 task = 1 commit
Tests pass → commit immediately with exact message from Brief.

### R4 — Docs are supreme authority
Conflict with `docs/SCHEMA.md`, `docs/ARCHITECTURE.md`, `docs/MCP_PROTOCOL.md` → docs win, STOP and report.

### R5 — Document disagreement = STOP
Believe a doc has error → STOP, report, wait.

### R6 — 3 retries = STOP
Test fails 3 times → STOP, report, wait.

### R7 — No scope creep
Implement exactly what Brief specifies. No extra features, no early optimization.

### R8 — Brief code blocks are authoritative
Disagree → STOP and escalate. Never substitute silently.

---

## REQUIRED READING — BEFORE TASK 1

| # | File | Focus |
|---|---|---|
| 1 | `docs/SCHEMA.md` | 2 templates, edge format, nguyên tắc |
| 2 | `docs/ARCHITECTURE.md` | Section 5 (PostgreSQL schema), Section 8 (pyramid), Section 11 (validator) |
| 3 | `gobp/core/db.py` | Existing PostgreSQL connection pattern |
| 4 | `gobp/core/id_generator.py` | Existing ID generation |
| 5 | `gobp/core/validator_v2.py` | Pattern để so sánh với v3 |

---

## TASKS

---

## TASK 1 — PostgreSQL Schema v3

**Goal:** Drop và recreate PostgreSQL schema với structure mới theo ARCHITECTURE.md Section 5.

**File to modify:** `gobp/core/db.py`

**Re-read toàn bộ `db.py` trước khi sửa.**

Thêm function `create_schema_v3()`:

```python
def create_schema_v3(conn) -> None:
    """
    Create GoBP schema v3 tables.
    Drop existing tables nếu có — chỉ dùng cho fresh setup.
    Migration từ v2 → v3 là Wave F.
    """
    with conn.cursor() as cur:

        # Drop existing v3 tables (nếu có từ previous attempt)
        cur.execute("DROP TABLE IF EXISTS node_history CASCADE")
        cur.execute("DROP TABLE IF EXISTS edges CASCADE")
        cur.execute("DROP TABLE IF EXISTS nodes CASCADE")

        # Nodes table
        cur.execute("""
            CREATE TABLE nodes (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                group_path  TEXT NOT NULL,
                desc_l1     TEXT DEFAULT '',
                desc_l2     TEXT DEFAULT '',
                desc_full   TEXT DEFAULT '',
                code        TEXT DEFAULT '',
                severity    TEXT DEFAULT '',
                search_vec  tsvector GENERATED ALWAYS AS (
                    setweight(to_tsvector('simple', coalesce(name, '')), 'A') ||
                    setweight(to_tsvector('simple', coalesce(group_path, '')), 'B') ||
                    setweight(to_tsvector('simple', coalesce(desc_l2, '')), 'C')
                ) STORED,
                updated_at  BIGINT NOT NULL DEFAULT
                    extract(epoch from now())::BIGINT
            )
        """)

        # Edges table — NO type field (inferred by system)
        cur.execute("""
            CREATE TABLE edges (
                from_id    TEXT NOT NULL REFERENCES nodes(id)
                           ON DELETE CASCADE,
                to_id      TEXT NOT NULL REFERENCES nodes(id)
                           ON DELETE CASCADE,
                reason     TEXT DEFAULT '',
                reason_vec tsvector GENERATED ALWAYS AS (
                    to_tsvector('simple', coalesce(reason, ''))
                ) STORED,
                code       TEXT DEFAULT '',
                created_at BIGINT NOT NULL DEFAULT
                    extract(epoch from now())::BIGINT,
                PRIMARY KEY (from_id, to_id)
            )
        """)

        # History table — append-only
        cur.execute("""
            CREATE TABLE node_history (
                id          SERIAL PRIMARY KEY,
                node_id     TEXT NOT NULL REFERENCES nodes(id)
                            ON DELETE CASCADE,
                description TEXT NOT NULL,
                code        TEXT DEFAULT '',
                created_at  BIGINT NOT NULL DEFAULT
                    extract(epoch from now())::BIGINT
            )
        """)

        # Indexes
        cur.execute("""
            CREATE INDEX idx_nodes_search
            ON nodes USING GIN(search_vec)
        """)
        cur.execute("""
            CREATE INDEX idx_nodes_group
            ON nodes(group_path text_pattern_ops)
        """)
        cur.execute("""
            CREATE INDEX idx_nodes_updated
            ON nodes(updated_at)
        """)
        cur.execute("""
            CREATE INDEX idx_edges_from
            ON edges(from_id)
        """)
        cur.execute("""
            CREATE INDEX idx_edges_to
            ON edges(to_id)
        """)
        cur.execute("""
            CREATE INDEX idx_edges_reason
            ON edges USING GIN(reason_vec)
        """)
        cur.execute("""
            CREATE INDEX idx_history_node
            ON node_history(node_id)
        """)

        conn.commit()
```

Thêm function `get_schema_version(conn) -> str`:

```python
def get_schema_version(conn) -> str:
    """Returns 'v3' nếu nodes table có desc_l1 column, 'v2' nếu không."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'nodes' AND column_name = 'desc_l1'
        """)
        return 'v3' if cur.fetchone() else 'v2'
```

**Acceptance criteria:**
- `create_schema_v3(conn)` tạo 3 tables: nodes, edges, node_history
- nodes có columns: id, name, group_path, desc_l1, desc_l2, desc_full, code, severity, search_vec, updated_at
- edges có columns: from_id, to_id, reason, reason_vec, code, created_at — KHÔNG có type column
- node_history có columns: id, node_id, description, code, created_at
- `get_schema_version()` trả về đúng version

**Commit message:**
```
Wave A Task 1: PostgreSQL schema v3 — nodes/edges/history

- create_schema_v3(): drops + recreates 3 tables
- nodes: desc_l1/l2/full pyramid, BM25F search_vec, no typed fields
- edges: from/to/reason only — no type field
- node_history: append-only per node
- get_schema_version(): detect v2 vs v3
```

---

## TASK 2 — Description Pyramid Extractor

**Goal:** Tạo module mới `gobp/core/pyramid.py` với hàm extract description pyramid.

**File to create:** `gobp/core/pyramid.py`

```python
"""
GoBP Description Pyramid.

Auto-extracts L1/L2 from full description text khi import node.
AI không cần làm gì — system tự extract.

L1 (~15 tokens): câu đầu tiên, max 100 chars
L2 (~40 tokens): 2-3 câu đầu, max 300 chars
L3: full text (không extract — lưu nguyên)
"""

from __future__ import annotations
import re


def extract_pyramid(full_text: str) -> tuple[str, str]:
    """
    Extract L1 và L2 từ full description text.

    Args:
        full_text: Full description string

    Returns:
        (l1, l2) tuple
        l1: headline — câu đầu tiên, max 100 chars
        l2: context  — 2-3 câu đầu, max 300 chars

    Examples:
        >>> extract_pyramid("PaymentService handles transactions. Validates balance. SLA: p99 < 300ms.")
        ("PaymentService handles transactions.", "PaymentService handles transactions. Validates balance.")
    """
    if not full_text or not full_text.strip():
        return "", ""

    text = full_text.strip()

    # Tách theo câu (., !, ?)
    sentences = [
        s.strip()
        for s in re.split(r'(?<=[.!?])\s+', text)
        if s.strip()
    ]

    if not sentences:
        # Không có câu hoàn chỉnh — dùng toàn bộ text (cắt ngắn)
        l1 = text[:100]
        l2 = text[:300]
        return l1, l2

    # L1: câu đầu tiên, max 100 chars
    l1 = sentences[0][:100]

    # L2: 2-3 câu đầu, max 300 chars
    l2 = " ".join(sentences[:3])[:300]

    return l1, l2


def pyramid_from_node(node: dict) -> tuple[str, str]:
    """
    Extract pyramid từ node dict.
    Handles cả plain text và {info, code} format cũ.

    Args:
        node: Node dict với description field

    Returns:
        (l1, l2) tuple
    """
    desc = node.get('description', '')

    # Schema v3: description là plain text
    if isinstance(desc, str):
        return extract_pyramid(desc)

    # Schema v2 compat: description = {info, code}
    if isinstance(desc, dict):
        info = desc.get('info', '') or ''
        return extract_pyramid(info)

    return "", ""
```

**Acceptance criteria:**
- `extract_pyramid("A. B. C.")` → `("A.", "A. B.")`
- Empty string → `("", "")`
- Text dài hơn 100 chars ở câu đầu → truncate L1 đúng
- `pyramid_from_node(node)` xử lý cả plain text và dict format

**Commit message:**
```
Wave A Task 2: gobp/core/pyramid.py — description pyramid extractor

- extract_pyramid(): L1 (100 chars) + L2 (300 chars) từ full text
- Sentence-aware splitting (., !, ?)
- pyramid_from_node(): handles v3 plain text + v2 {info,code} format
```

---

## TASK 3 — ID Generator v2 Verification

**Goal:** Verify ID generator hiện tại đã đúng format v2. Update nếu cần.

**File to modify:** `gobp/core/id_generator.py`

**Re-read toàn bộ `id_generator.py` trước.**

ID format v2: `{group_slug}.{name_slug}.{8hex}`

```
group_slug: "Dev > Infrastructure > Engine" → "dev.infrastructure.engine"
name_slug:  "PaymentService" → "paymentservice"
8hex:       MD5(name + group)[:8] — deterministic
```

Nếu file đã có đúng format này → chỉ thêm unit test, không sửa.

Nếu chưa đúng → implement:

```python
import hashlib
import re


def generate_id(name: str, group: str) -> str:
    """
    Generate deterministic node ID v2.

    Format: {group_slug}.{name_slug}.{8hex}

    Args:
        name:  Node name, e.g. "PaymentService"
        group: Group breadcrumb, e.g. "Dev > Infrastructure > Engine"

    Returns:
        ID string, e.g. "dev.infrastructure.engine.paymentservice.a1b2c3d4"

    Examples:
        >>> generate_id("PaymentService", "Dev > Infrastructure > Engine")
        "dev.infrastructure.engine.paymentservice.a1b2c3d4"
    """
    # group_slug: lowercase, spaces và " > " → "."
    group_slug = group.lower()
    group_slug = re.sub(r'\s*>\s*', '.', group_slug)
    group_slug = re.sub(r'[^a-z0-9.]', '', group_slug)
    group_slug = group_slug.strip('.')

    # name_slug: lowercase, spaces → "_", non-alphanumeric → ""
    name_slug = name.lower()
    name_slug = re.sub(r'\s+', '_', name_slug)
    name_slug = re.sub(r'[^a-z0-9_]', '', name_slug)
    name_slug = name_slug.strip('_')

    # 8hex: deterministic from name + group
    hash_input = f"{name}{group}".encode('utf-8')
    hex_suffix = hashlib.md5(hash_input).hexdigest()[:8]

    return f"{group_slug}.{name_slug}.{hex_suffix}"


def generate_session_id(date_str: str = None) -> str:
    """
    Generate session ID.

    Format: meta.session.YYYY-MM-DD.{8hex}

    Args:
        date_str: ISO date string, defaults to today

    Returns:
        Session ID, e.g. "meta.session.2026-04-19.a1b2c3d4"
    """
    import datetime, uuid
    if date_str is None:
        date_str = datetime.date.today().isoformat()
    hex_suffix = uuid.uuid4().hex[:8]
    return f"meta.session.{date_str}.{hex_suffix}"
```

**Acceptance criteria:**
- `generate_id("PaymentService", "Dev > Infrastructure > Engine")` → format đúng
- Cùng input → cùng output (deterministic)
- Special chars trong name/group được xử lý đúng
- `generate_session_id()` trả về format đúng

**Commit message:**
```
Wave A Task 3: id_generator.py v2 — group_slug.name_slug.8hex

- generate_id(): deterministic từ MD5(name+group)[:8]
- generate_session_id(): meta.session.YYYY-MM-DD.8hex
- Verified format matches ARCHITECTURE.md Section 4
```

---

## TASK 4 — Validator v3

**Goal:** Tạo `gobp/core/validator_v3.py` — simple 2-template validator theo SCHEMA.md.

**File to create:** `gobp/core/validator_v3.py`

```python
"""
GoBP Validator v3.

Schema v3 có 2 templates:
  Template 1 — Mọi node: name + group + description + code + history[]
  Template 2 — ErrorCase: thêm severity field

Validator đơn giản hơn v2 vì không có typed fields.
"""

from __future__ import annotations
from typing import Any


# Group taxonomy từ SCHEMA.md
# Dùng để infer group khi không có
_DEFAULT_GROUPS: dict[str, str] = {
    "Idea":             "Document > Idea",
    "Spec":             "Document > Spec",
    "Document":         "Document > Document",
    "Lesson":           "Document > Lesson",
    "Entity":           "Dev > Domain > Entity",
    "ValueObject":      "Dev > Domain > ValueObject",
    "DomainEvent":      "Dev > Domain > DomainEvent",
    "Aggregate":        "Dev > Domain > Aggregate",
    "Flow":             "Dev > Application > Flow",
    "Feature":          "Dev > Application > Feature",
    "Command":          "Dev > Application > Command",
    "UseCase":          "Dev > Application > UseCase",
    "Engine":           "Dev > Infrastructure > Engine",
    "Repository":       "Dev > Infrastructure > Repository",
    "APIContract":      "Dev > Infrastructure > API > APIContract",
    "APIEndpoint":      "Dev > Infrastructure > API > APIEndpoint",
    "APIRequest":       "Dev > Infrastructure > API > APIRequest",
    "APIResponse":      "Dev > Infrastructure > API > APIResponse",
    "APIMiddleware":    "Dev > Infrastructure > API > APIMiddleware",
    "APIVersion":       "Dev > Infrastructure > API > APIVersion",
    "Webhook":          "Dev > Infrastructure > API > Webhook",
    "AuthFlow":         "Dev > Infrastructure > Security > AuthFlow",
    "AuthZ":            "Dev > Infrastructure > Security > AuthZ",
    "Permission":       "Dev > Infrastructure > Security > Permission",
    "Policy":           "Dev > Infrastructure > Security > Policy",
    "Token":            "Dev > Infrastructure > Security > Token",
    "Encryption":       "Dev > Infrastructure > Security > Encryption",
    "Secret":           "Dev > Infrastructure > Security > Secret",
    "SecurityAudit":    "Dev > Infrastructure > Security > Audit",
    "ThreatModel":      "Dev > Infrastructure > Security > ThreatModel",
    "Vulnerability":    "Dev > Infrastructure > Security > Vulnerability",
    "RateLimitPolicy":  "Dev > Infrastructure > Security > RateLimitPolicy",
    "DBSchema":         "Dev > Infrastructure > Database > Schema",
    "Table":            "Dev > Infrastructure > Database > Table",
    "Column":           "Dev > Infrastructure > Database > Column",
    "View":             "Dev > Infrastructure > Database > View",
    "Migration":        "Dev > Infrastructure > Database > Migration",
    "DBIndex":          "Dev > Infrastructure > Database > Index",
    "NamedQuery":       "Dev > Infrastructure > Database > Query",
    "ConnectionPool":   "Dev > Infrastructure > Database > ConnectionPool",
    "Seed":             "Dev > Infrastructure > Database > Seed",
    "EventBus":         "Dev > Infrastructure > Messaging > EventBus",
    "Queue":            "Dev > Infrastructure > Messaging > Queue",
    "Message":          "Dev > Infrastructure > Messaging > Message",
    "DeadLetterQueue":  "Dev > Infrastructure > Messaging > DeadLetterQueue",
    "Topic":            "Dev > Infrastructure > Messaging > Topic",
    "Worker":           "Dev > Infrastructure > Messaging > Worker",
    "Metric":           "Dev > Infrastructure > Observability > Metric",
    "SLO":              "Dev > Infrastructure > Observability > SLO",
    "LogSpec":          "Dev > Infrastructure > Observability > Log",
    "TraceSpec":        "Dev > Infrastructure > Observability > Trace",
    "Alert":            "Dev > Infrastructure > Observability > Alert",
    "CacheLayer":       "Dev > Infrastructure > Cache > CacheLayer",
    "CacheKey":         "Dev > Infrastructure > Cache > CacheKey",
    "StorageBucket":    "Dev > Infrastructure > Storage > Bucket",
    "MediaProcessing":  "Dev > Infrastructure > Storage > Media",
    "CDN":              "Dev > Infrastructure > Storage > CDN",
    "EnvConfig":        "Dev > Infrastructure > Config > EnvConfig",
    "FeatureFlag":      "Dev > Infrastructure > Config > FeatureFlag",
    "Environment":      "Dev > Infrastructure > Deployment > Environment",
    "ServiceDefinition":"Dev > Infrastructure > Deployment > Service",
    "Pipeline":         "Dev > Infrastructure > Deployment > Pipeline",
    "LoadBalancer":     "Dev > Infrastructure > Network > LoadBalancer",
    "ServiceMesh":      "Dev > Infrastructure > Network > ServiceMesh",
    "DNSRecord":        "Dev > Infrastructure > Network > DNS",
    "ExternalService":  "Dev > Infrastructure > ThirdParty > ExternalService",
    "SDK":              "Dev > Infrastructure > ThirdParty > SDK",
    "Screen":           "Dev > Frontend > Screen",
    "Component":        "Dev > Frontend > Component",
    "Interface":        "Dev > Code > Interface",
    "Enum":             "Dev > Code > Enum",
    "Module":           "Dev > Code > Module",
    "Invariant":        "Constraint > Invariant",
    "BusinessRule":     "Constraint > BusinessRule",
    "ErrorDomain":      "Error > ErrorDomain",
    "ErrorCase":        "Error > ErrorCase",
    "TestSuite":        "Test > TestSuite",
    "TestKind":         "Test > TestKind",
    "TestCase":         "Test > TestCase",
    "Session":          "Meta > Session",
    "Wave":             "Meta > Wave",
    "Task":             "Meta > Task",
    "Reflection":       "Meta > Reflection",
}

_VALID_SEVERITIES = {"fatal", "error", "warning", "info"}


class ValidatorV3:
    """
    Schema v3 validator — 2 templates.

    Template 1 (mọi node):
        name (required)
        group (required)
        description (required, not empty)
        code (optional)
        history[] (optional, append-only)

    Template 2 (ErrorCase only):
        + severity: fatal|error|warning|info
    """

    def validate(self, node: dict[str, Any]) -> list[str]:
        """
        Validate node theo schema v3.

        Returns:
            List of error strings. Empty list = valid.
        """
        errors: list[str] = []

        # Template 1: base fields
        if not node.get('name', '').strip():
            errors.append("name is required and cannot be empty")

        if not node.get('group', '').strip():
            errors.append("group is required and cannot be empty")

        desc = node.get('description', '')
        if isinstance(desc, dict):
            # v2 compat: {info, code}
            desc = desc.get('info', '') or ''
        if not str(desc).strip():
            errors.append("description is required and cannot be empty")

        # history[] validation (nếu có)
        history = node.get('history', [])
        if history is not None:
            if not isinstance(history, list):
                errors.append("history must be a list")
            else:
                for i, entry in enumerate(history):
                    if not isinstance(entry, dict):
                        errors.append(f"history[{i}] must be a dict")
                    elif not entry.get('description', '').strip():
                        errors.append(
                            f"history[{i}].description is required"
                        )

        # Template 2: ErrorCase additional field
        node_type = node.get('type', '')
        if node_type == 'ErrorCase':
            severity = node.get('severity', '')
            if severity not in _VALID_SEVERITIES:
                errors.append(
                    f"ErrorCase.severity must be one of: "
                    f"{sorted(_VALID_SEVERITIES)}, got: '{severity}'"
                )

        return errors

    def auto_fix(self, node: dict[str, Any]) -> dict[str, Any]:
        """
        Auto-fix những lỗi có thể fix mà không cần human.

        Fixes:
        - Infer group từ type nếu thiếu
        - Convert description dict → plain text
        - Set empty defaults cho code, history
        """
        node = dict(node)

        # Infer group từ type
        if not node.get('group') and node.get('type'):
            default_group = _DEFAULT_GROUPS.get(node['type'])
            if default_group:
                node['group'] = default_group

        # Convert v2 description {info, code} → v3 plain text
        desc = node.get('description')
        if isinstance(desc, dict):
            info = desc.get('info', '') or ''
            code = desc.get('code', '') or ''
            node['description'] = info
            if code and not node.get('code'):
                node['code'] = code

        # Set defaults
        if 'code' not in node:
            node['code'] = ''
        if 'history' not in node:
            node['history'] = []

        return node

    def is_valid(self, node: dict[str, Any]) -> bool:
        """Convenience method — True nếu không có errors."""
        return len(self.validate(node)) == 0


# Module-level instance
validator_v3 = ValidatorV3()
```

**Acceptance criteria:**
- `validate({})` → errors về name, group, description
- `validate({"name": "X", "group": "Y", "description": "Z"})` → `[]`
- `validate({"name":"X","group":"Y","description":"Z","type":"ErrorCase","severity":"bad"})` → error về severity
- `validate({"name":"X","group":"Y","description":"Z","type":"ErrorCase","severity":"error"})` → `[]`
- `auto_fix({"type": "Engine"})` → group được infer
- `auto_fix({"description": {"info": "text", "code": "code"}})` → description = "text", code = "code"

**Commit message:**
```
Wave A Task 4: gobp/core/validator_v3.py — schema v3 validator

- ValidatorV3.validate(): 2 templates — base node + ErrorCase
- ValidatorV3.auto_fix(): infer group, convert v2 description
- _DEFAULT_GROUPS: full taxonomy từ SCHEMA.md
- module-level validator_v3 instance
```

---

## TASK 5 — File Format v3

**Goal:** Tạo `gobp/core/file_format_v3.py` — serialize/deserialize node files theo schema v3.

**File to create:** `gobp/core/file_format_v3.py`

```python
"""
GoBP File Format v3.

Node file format:
---
id: dev.infrastructure.engine.paymentservice.a1b2c3d4
name: PaymentService
group: Dev > Infrastructure > Engine
description: |
  Plain text description.
code: |
  optional code snippet
history:
  - description: "change log entry"
    code: ""
created_at: 2026-04-19T10:00:00Z
session_id: meta.session.2026-04-19.abc12345
---

Edge file format (relations.yaml):
- from: node_id_1
  to:   node_id_2
  reason: "why this connection exists"
  code: ""
  created_at: 2026-04-19T10:00:00Z
"""

from __future__ import annotations
import yaml
from pathlib import Path
from typing import Any
import datetime


def serialize_node(node: dict[str, Any]) -> str:
    """
    Serialize node dict → YAML frontmatter markdown string.

    Returns:
        String với YAML frontmatter (---...---) chứa node data.
    """
    # Build frontmatter dict — chỉ những fields cần thiết
    fm: dict[str, Any] = {
        'id':          node.get('id', ''),
        'name':        node.get('name', ''),
        'group':       node.get('group', ''),
        'description': node.get('description', ''),
    }

    # Optional fields
    if node.get('code'):
        fm['code'] = node['code']

    # ErrorCase severity
    if node.get('type') == 'ErrorCase' and node.get('severity'):
        fm['severity'] = node['severity']

    # History
    history = node.get('history', [])
    if history:
        fm['history'] = history

    # Metadata
    if node.get('created_at'):
        fm['created_at'] = node['created_at']
    if node.get('session_id'):
        fm['session_id'] = node['session_id']

    yaml_str = yaml.dump(
        fm,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False
    )
    return f"---\n{yaml_str}---\n"


def deserialize_node(content: str) -> dict[str, Any]:
    """
    Deserialize YAML frontmatter markdown → node dict.

    Args:
        content: File content string

    Returns:
        Node dict. Empty dict nếu parse fail.
    """
    if not content.startswith('---'):
        return {}

    # Extract frontmatter
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}

    try:
        node = yaml.safe_load(parts[1]) or {}
        return node
    except yaml.YAMLError:
        return {}


def serialize_edges(edges: list[dict[str, Any]]) -> str:
    """
    Serialize list of edges → YAML string cho relations.yaml.

    Edge format: from, to, reason, code, created_at
    Không có type field.
    """
    if not edges:
        return ""

    edge_list = []
    for edge in edges:
        e: dict[str, Any] = {
            'from':       edge.get('from_id') or edge.get('from', ''),
            'to':         edge.get('to_id') or edge.get('to', ''),
            'reason':     edge.get('reason', ''),
        }
        if edge.get('code'):
            e['code'] = edge['code']
        if edge.get('created_at'):
            e['created_at'] = edge['created_at']
        edge_list.append(e)

    return yaml.dump(
        edge_list,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False
    )


def deserialize_edges(content: str) -> list[dict[str, Any]]:
    """
    Deserialize YAML string → list of edge dicts.

    Returns:
        List of edge dicts. Empty list nếu parse fail.
    """
    if not content.strip():
        return []
    try:
        result = yaml.safe_load(content)
        if isinstance(result, list):
            return result
        return []
    except yaml.YAMLError:
        return []


def node_file_path(gobp_dir: Path, node_id: str) -> Path:
    """Return path cho node file: .gobp/nodes/{node_id}.md"""
    safe_id = node_id.replace('/', '_').replace(':', '_')
    return gobp_dir / 'nodes' / f"{safe_id}.md"


def edges_file_path(gobp_dir: Path) -> Path:
    """Return path cho edges file: .gobp/edges/relations.yaml"""
    return gobp_dir / 'edges' / 'relations.yaml'
```

**Acceptance criteria:**
- `serialize_node(node)` → valid YAML frontmatter string bắt đầu bằng `---`
- `deserialize_node(serialize_node(node))` → roundtrip đúng
- Không có type field trong serialized output (trừ ErrorCase severity)
- `serialize_edges([])` → empty string
- `deserialize_edges(serialize_edges(edges))` → roundtrip đúng

**Commit message:**
```
Wave A Task 5: gobp/core/file_format_v3.py — schema v3 serializer

- serialize_node(): YAML frontmatter, no typed fields
- deserialize_node(): parse frontmatter → node dict
- serialize_edges(): from/to/reason only (no type field)
- deserialize_edges(): parse YAML edge list
- node_file_path() + edges_file_path() helpers
```

---

## TASK 6 — Tests Wave A

**Goal:** Tests cho tất cả modules Wave A.

**File to create:** `tests/test_wave_a.py`

```python
"""Tests for GoBP Wave A — Database Foundation."""

import pytest
import hashlib
from gobp.core.pyramid import extract_pyramid, pyramid_from_node
from gobp.core.id_generator import generate_id, generate_session_id
from gobp.core.validator_v3 import ValidatorV3, validator_v3
from gobp.core.file_format_v3 import (
    serialize_node, deserialize_node,
    serialize_edges, deserialize_edges,
)


# ── Pyramid tests ─────────────────────────────────────────────────────────────

def test_pyramid_simple():
    l1, l2 = extract_pyramid("PaymentService handles transactions. Validates balance. SLA: p99 < 300ms.")
    assert l1 == "PaymentService handles transactions."
    assert "Validates balance" in l2

def test_pyramid_empty():
    assert extract_pyramid("") == ("", "")
    assert extract_pyramid("   ") == ("", "")

def test_pyramid_single_sentence():
    l1, l2 = extract_pyramid("Single sentence only.")
    assert l1 == "Single sentence only."
    assert l2 == "Single sentence only."

def test_pyramid_long_first_sentence():
    long = "A" * 150 + "."
    l1, l2 = extract_pyramid(long)
    assert len(l1) <= 100

def test_pyramid_from_node_plain():
    node = {"description": "First sentence. Second sentence."}
    l1, l2 = pyramid_from_node(node)
    assert l1 == "First sentence."

def test_pyramid_from_node_v2_dict():
    node = {"description": {"info": "First sentence. Second.", "code": ""}}
    l1, l2 = pyramid_from_node(node)
    assert l1 == "First sentence."

def test_pyramid_l2_max_300():
    text = ". ".join(["Sentence " + str(i) for i in range(20)]) + "."
    _, l2 = extract_pyramid(text)
    assert len(l2) <= 300


# ── ID Generator tests ────────────────────────────────────────────────────────

def test_generate_id_format():
    id_ = generate_id("PaymentService", "Dev > Infrastructure > Engine")
    parts = id_.split('.')
    assert parts[0] == 'dev'
    assert 'paymentservice' in id_
    assert len(parts[-1]) == 8  # 8hex suffix

def test_generate_id_deterministic():
    id1 = generate_id("PaymentService", "Dev > Infrastructure > Engine")
    id2 = generate_id("PaymentService", "Dev > Infrastructure > Engine")
    assert id1 == id2

def test_generate_id_different_names():
    id1 = generate_id("ServiceA", "Dev > Infrastructure > Engine")
    id2 = generate_id("ServiceB", "Dev > Infrastructure > Engine")
    assert id1 != id2

def test_generate_id_special_chars():
    id_ = generate_id("My Service (v2)", "Dev > Infrastructure")
    assert id_  # không có lỗi, trả về string

def test_generate_session_id_format():
    sid = generate_session_id("2026-04-19")
    assert sid.startswith("meta.session.2026-04-19.")
    assert len(sid.split('.')[-1]) == 8


# ── Validator v3 tests ────────────────────────────────────────────────────────

def test_validator_valid_base_node():
    v = ValidatorV3()
    errors = v.validate({
        "name": "PaymentService",
        "group": "Dev > Infrastructure > Engine",
        "description": "Handles payments.",
    })
    assert errors == []

def test_validator_missing_name():
    v = ValidatorV3()
    errors = v.validate({"group": "Dev > Engine", "description": "text"})
    assert any("name" in e for e in errors)

def test_validator_missing_group():
    v = ValidatorV3()
    errors = v.validate({"name": "X", "description": "text"})
    assert any("group" in e for e in errors)

def test_validator_missing_description():
    v = ValidatorV3()
    errors = v.validate({"name": "X", "group": "Y"})
    assert any("description" in e for e in errors)

def test_validator_empty_description():
    v = ValidatorV3()
    errors = v.validate({"name": "X", "group": "Y", "description": ""})
    assert any("description" in e for e in errors)

def test_validator_errorcase_valid():
    v = ValidatorV3()
    errors = v.validate({
        "name": "Payment Timeout",
        "group": "Error > Payment",
        "description": "Timeout error.",
        "type": "ErrorCase",
        "severity": "error",
    })
    assert errors == []

def test_validator_errorcase_invalid_severity():
    v = ValidatorV3()
    errors = v.validate({
        "name": "X", "group": "Y", "description": "Z",
        "type": "ErrorCase", "severity": "CRITICAL",
    })
    assert any("severity" in e for e in errors)

def test_validator_errorcase_missing_severity():
    v = ValidatorV3()
    errors = v.validate({
        "name": "X", "group": "Y", "description": "Z",
        "type": "ErrorCase",
    })
    assert any("severity" in e for e in errors)

def test_validator_auto_fix_infer_group():
    v = ValidatorV3()
    fixed = v.auto_fix({"name": "X", "type": "Engine", "description": "Y"})
    assert fixed["group"] == "Dev > Infrastructure > Engine"

def test_validator_auto_fix_v2_description():
    v = ValidatorV3()
    fixed = v.auto_fix({
        "name": "X", "group": "Y",
        "description": {"info": "plain text", "code": "snippet"},
    })
    assert fixed["description"] == "plain text"
    assert fixed["code"] == "snippet"

def test_validator_history_valid():
    v = ValidatorV3()
    errors = v.validate({
        "name": "X", "group": "Y", "description": "Z",
        "history": [{"description": "change log"}],
    })
    assert errors == []

def test_validator_history_invalid_entry():
    v = ValidatorV3()
    errors = v.validate({
        "name": "X", "group": "Y", "description": "Z",
        "history": [{"description": ""}],
    })
    assert any("history" in e for e in errors)


# ── File format v3 tests ──────────────────────────────────────────────────────

def test_serialize_deserialize_roundtrip():
    node = {
        "id": "dev.engine.payment.a1b2c3d4",
        "name": "PaymentService",
        "group": "Dev > Infrastructure > Engine",
        "description": "Handles payments.",
        "code": "def pay(): pass",
    }
    serialized = serialize_node(node)
    recovered = deserialize_node(serialized)
    assert recovered["name"] == "PaymentService"
    assert recovered["description"] == "Handles payments."

def test_serialize_no_type_field():
    node = {
        "id": "x", "name": "Y", "group": "Z",
        "description": "desc", "type": "Engine",
    }
    serialized = serialize_node(node)
    # type field không được serialize (trừ ErrorCase severity)
    assert "type: Engine" not in serialized

def test_serialize_errorcase_severity():
    node = {
        "id": "x", "name": "Y", "group": "Error > Payment",
        "description": "desc", "type": "ErrorCase", "severity": "error",
    }
    serialized = serialize_node(node)
    assert "severity: error" in serialized

def test_serialize_edges_roundtrip():
    edges = [
        {"from_id": "a", "to_id": "b", "reason": "because"},
        {"from_id": "c", "to_id": "d", "reason": "another reason"},
    ]
    serialized = serialize_edges(edges)
    recovered = deserialize_edges(serialized)
    assert len(recovered) == 2
    assert recovered[0]["reason"] == "because"

def test_serialize_edges_no_type():
    edges = [{"from_id": "a", "to_id": "b", "reason": "r", "type": "depends_on"}]
    serialized = serialize_edges(edges)
    assert "type: depends_on" not in serialized

def test_deserialize_empty_edges():
    assert deserialize_edges("") == []
    assert deserialize_edges("   ") == []

def test_deserialize_invalid_yaml():
    assert deserialize_node("not yaml") == {}
```

**Acceptance criteria:**
- Tất cả tests pass
- Tổng số tests mới: 35+
- Không break tests hiện tại

**Commit message:**
```
Wave A Task 6: tests/test_wave_a.py — 35+ tests

- Pyramid: extract + pyramid_from_node (7 tests)
- ID generator: format + deterministic + special chars (5 tests)
- Validator v3: base + ErrorCase + auto_fix + history (13 tests)
- File format v3: serialize/deserialize roundtrip (10 tests)
- All existing tests still pass
```

---

## POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave_a.py -v
# Expected: 35+ tests passing

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --override-ini="addopts=" -q
# Expected: tất cả tests cũ + Wave A tests pass

# Verify modules import đúng
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.pyramid import extract_pyramid
from gobp.core.id_generator import generate_id
from gobp.core.validator_v3 import validator_v3
from gobp.core.file_format_v3 import serialize_node
print('All Wave A modules import OK')
"
```

---

## CEO DISPATCH INSTRUCTIONS

### 1. Cursor

```
Read docs/SCHEMA.md, docs/ARCHITECTURE.md, docs/MCP_PROTOCOL.md.
Read gobp/core/db.py, gobp/core/id_generator.py, gobp/core/validator_v2.py.
Read waves/wave_a_brief.md (this file).

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute Tasks 1 → 6 sequentially.
R9: All existing tests must pass after each task.
1 task = 1 commit with exact message from Brief.
```

### 2. Claude CLI audit

```
Audit Wave A.
Task 1: create_schema_v3() tạo đúng 3 tables, edges không có type column
Task 2: extract_pyramid() đúng L1/L2, pyramid_from_node() xử lý v2 compat
Task 3: generate_id() deterministic, format đúng
Task 4: ValidatorV3.validate() đúng 2 templates, auto_fix() đúng
Task 5: serialize/deserialize roundtrip, không có type field trong edges
Task 6: 35+ tests pass, không break tests cũ
BLOCKING: Bất kỳ fail → STOP, báo CEO.
```

---

*Wave A Brief — GoBP Database Foundation*  
*2026-04-19 — CTO Chat*  
◈
