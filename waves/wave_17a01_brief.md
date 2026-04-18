# WAVE 17A01 BRIEF — SCHEMA + FILE FORMAT REWRITE

**Wave:** 17A01
**Title:** core_nodes.yaml v2, core_edges.yaml v2, ID format, file format
**Author:** CTO Chat
**Date:** 2026-04-19
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 7 tasks
**Estimated effort:** 3-4 hours

---

## REFERENCED GOBP NODES

| Node ID | Topic |
|---|---|
| `dec:d004` | GoBP update obligation |
| `dec:d006` | Brief reference nodes |
| `dec:d011` | Graph hygiene |

**REQUIRED READING trước khi bắt đầu:**
- `docs/GOBP_SCHEMA_REDESIGN_v2.1.md` ← SPEC CHÍNH
- `docs/wave_17a_series_plan.md` ← SERIES CONTEXT
- `gobp/schema/core_nodes.yaml` ← CURRENT (sẽ rewrite)
- `gobp/schema/core_edges.yaml` ← CURRENT (sẽ rewrite)

---

## CONTEXT

GoBP v2 rewrite — Option B (giữ infra skeleton, rewrite core).
Wave 17A01 là foundation: schema + file format đúng.
Không đụng query engine (Wave 17A02+).

**Mục tiêu:**
```
1. core_nodes.yaml v2 — 65 types, group field, lifecycle, read_order
2. core_edges.yaml v2 — reason field
3. ID generator v2 — group-embedded human-readable
4. File serializer v2 — YAML với group, description.info/code
5. Schema loader v2 — load + validate schema v2
```

---

## CURSOR EXECUTION RULES

R1-R12 (.cursorrules v6).

**Testing:**
- Tasks 1-6: R9-B (module tests only)
- Task 7: R9-C full suite

**QUAN TRỌNG:**
- Wave này KHÔNG rewrite GraphIndex hay query engine
- Chỉ: schema YAML + Python serialization layer
- Existing 633 tests PHẢI vẫn pass

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 591 tests (fast suite)
```

---

# TASKS

---

## TASK 1 — Rewrite `core_nodes.yaml` v2

**File:** `gobp/schema/core_nodes.yaml`

Rewrite hoàn toàn theo spec `docs/GOBP_SCHEMA_REDESIGN_v2.1.md`.

**Structure:**
```yaml
version: "2.0"

base:
  id:         {type: str, required: true, pattern: "^[a-z0-9._-]+$"}
  name:       {type: str, required: true}
  type:       {type: str, required: true}
  group:      {type: str, required: true, description: "Breadcrumb path"}
  lifecycle:  {type: enum, values: [draft,specified,implemented,tested,deprecated], default: draft}
  read_order: {type: enum, values: [foundational,important,reference,background], default: reference}
  description:
    type: dict
    required: true
    fields:
      info: {type: str, required: true}
      code: {type: str, required: false, default: ""}
  tags:       {type: list[str], default: []}
  created_at: {type: timestamp}
  session_id: {type: str}

node_types:
  # Document group (5 types + 5 Lesson sub-types)
  Spec:        {group: "Document > Spec",           read_order: important}
  Decision:    {group: "Document > Decision",        read_order: foundational, required: {what: str, why: str}}
  Concept:     {group: "Document > Concept",         read_order: important, required: {definition: str, usage_guide: str}}
  Idea:        {group: "Document > Idea",            read_order: background}
  LessonRule:  {group: "Document > Lesson > Rule",   read_order: foundational}
  LessonSkill: {group: "Document > Lesson > Skill",  read_order: important}
  LessonDev:   {group: "Document > Lesson > Dev",    read_order: reference}
  LessonCTO:   {group: "Document > Lesson > CTO",    read_order: reference}
  LessonQA:    {group: "Document > Lesson > QA",     read_order: reference}

  # Dev > Domain (4 types)
  Entity:      {group: "Dev > Domain > Entity",      read_order: foundational}
  ValueObject: {group: "Dev > Domain > ValueObject", read_order: important}
  DomainEvent: {group: "Dev > Domain > DomainEvent", read_order: important}
  Aggregate:   {group: "Dev > Domain > Aggregate",   read_order: important}

  # Dev > Application (5 types)
  Flow:        {group: "Dev > Application > Flow",    read_order: important}
  Feature:     {group: "Dev > Application > Feature", read_order: important}
  Command:     {group: "Dev > Application > Command", read_order: reference}
  UseCase:     {group: "Dev > Application > UseCase", read_order: reference}
  DTO:         {group: "Dev > Application > DTO",     read_order: background}

  # Dev > Infrastructure > Engine/Repository
  Engine:      {group: "Dev > Infrastructure > Engine",     read_order: foundational}
  Repository:  {group: "Dev > Infrastructure > Repository", read_order: reference}

  # Dev > Infrastructure > API (6 types)
  APIContract:  {group: "Dev > Infrastructure > API > APIContract",  read_order: important}
  APIEndpoint:  {group: "Dev > Infrastructure > API > APIEndpoint",  read_order: reference}
  APIRequest:   {group: "Dev > Infrastructure > API > APIRequest",   read_order: reference}
  APIResponse:  {group: "Dev > Infrastructure > API > APIResponse",  read_order: reference}
  APIMiddleware:{group: "Dev > Infrastructure > API > APIMiddleware", read_order: reference}
  Webhook:      {group: "Dev > Infrastructure > API > Webhook",      read_order: background}

  # Dev > Infrastructure > Security (10 types)
  AuthFlow:      {group: "Dev > Infrastructure > Security > AuthFlow",      read_order: foundational}
  AuthZ:         {group: "Dev > Infrastructure > Security > AuthZ",         read_order: foundational}
  Permission:    {group: "Dev > Infrastructure > Security > Permission",    read_order: important}
  Policy:        {group: "Dev > Infrastructure > Security > Policy",        read_order: important}
  Token:         {group: "Dev > Infrastructure > Security > Token",         read_order: important}
  Encryption:    {group: "Dev > Infrastructure > Security > Encryption",    read_order: important}
  Secret:        {group: "Dev > Infrastructure > Security > Secret",        read_order: important}
  SecurityAudit: {group: "Dev > Infrastructure > Security > Audit",         read_order: reference}
  ThreatModel:   {group: "Dev > Infrastructure > Security > ThreatModel",   read_order: important}
  Vulnerability: {group: "Dev > Infrastructure > Security > Vulnerability", read_order: important}

  # Dev > Infrastructure > Database (5 types)
  DBSchema:   {group: "Dev > Infrastructure > Database > Schema",    read_order: important}
  Migration:  {group: "Dev > Infrastructure > Database > Migration", read_order: reference}
  DBIndex:    {group: "Dev > Infrastructure > Database > Index",     read_order: background}
  NamedQuery: {group: "Dev > Infrastructure > Database > Query",     read_order: reference}
  Seed:       {group: "Dev > Infrastructure > Database > Seed",      read_order: background}

  # Dev > Infrastructure > Messaging (4 types)
  EventBus: {group: "Dev > Infrastructure > Messaging > EventBus", read_order: important}
  Queue:    {group: "Dev > Infrastructure > Messaging > Queue",    read_order: reference}
  Topic:    {group: "Dev > Infrastructure > Messaging > Topic",    read_order: reference}
  Worker:   {group: "Dev > Infrastructure > Messaging > Worker",   read_order: reference}

  # Dev > Infrastructure > Observability (4 types)
  Metric:    {group: "Dev > Infrastructure > Observability > Metric", read_order: reference}
  LogSpec:   {group: "Dev > Infrastructure > Observability > Log",    read_order: reference}
  TraceSpec: {group: "Dev > Infrastructure > Observability > Trace",  read_order: reference}
  Alert:     {group: "Dev > Infrastructure > Observability > Alert",  read_order: reference}

  # Dev > Infrastructure > Cache/Storage/Config
  CacheStrategy: {group: "Dev > Infrastructure > Cache > CacheStrategy", read_order: reference}
  FileStorage:   {group: "Dev > Infrastructure > Storage > FileStorage", read_order: background}
  CDN:           {group: "Dev > Infrastructure > Storage > CDN",         read_order: background}
  EnvConfig:     {group: "Dev > Infrastructure > Config > EnvConfig",    read_order: reference}
  FeatureFlag:   {group: "Dev > Infrastructure > Config > FeatureFlag",  read_order: reference}

  # Dev > Frontend (6 types)
  Screen:    {group: "Dev > Frontend > Screen",    read_order: reference}
  Component: {group: "Dev > Frontend > Component", read_order: reference}
  Layout:    {group: "Dev > Frontend > Layout",    read_order: background}
  Theme:     {group: "Dev > Frontend > Theme",     read_order: background}
  Animation: {group: "Dev > Frontend > Animation", read_order: background}
  UIState:   {group: "Dev > Frontend > State",     read_order: reference}

  # Dev > Code (16 types)
  Interface:    {group: "Dev > Code > Interface",    read_order: important}
  AbstractClass:{group: "Dev > Code > AbstractClass",read_order: reference}
  Class:        {group: "Dev > Code > Class",        read_order: reference}
  Mixin:        {group: "Dev > Code > Mixin",        read_order: background}
  CodeEnum:     {group: "Dev > Code > Enum",         read_order: reference}
  TypeAlias:    {group: "Dev > Code > TypeAlias",    read_order: background}
  Generic:      {group: "Dev > Code > Generic",      read_order: reference}
  Function:     {group: "Dev > Code > Function",     read_order: reference}
  Method:       {group: "Dev > Code > Method",       read_order: background}
  Constructor:  {group: "Dev > Code > Constructor",  read_order: background}
  Extension:    {group: "Dev > Code > Extension",    read_order: background}
  Field:        {group: "Dev > Code > Field",        read_order: background}
  Variable:     {group: "Dev > Code > Variable",     read_order: background}
  Constant:     {group: "Dev > Code > Constant",     read_order: reference}
  Parameter:    {group: "Dev > Code > Parameter",    read_order: background}
  Module:       {group: "Dev > Code > Module",       read_order: reference}

  # Constraint group (4 types)
  Invariant:
    group: "Constraint > Invariant"
    read_order: foundational
    required:
      rule:             {type: str, description: "Boolean expression"}
      scope:            {type: enum, values: [class, object, system]}
      enforcement:      {type: enum, values: [hard, soft]}
      violation_action: {type: enum, values: [reject, devalue, flag, log]}
    optional:
      spec_source: {type: str}

  Precondition:  {group: "Constraint > Precondition",  read_order: important}
  Postcondition: {group: "Constraint > Postcondition", read_order: important}
  BusinessRule:  {group: "Constraint > BusinessRule",  read_order: important}

  # Error group (2 types)
  ErrorDomain:
    group: "Error > ErrorDomain"
    read_order: important
    required:
      domain:    {type: enum, values: [auth,gps,ember,trust,privacy,network,storage,sync]}
      fix_guide: {type: str}
    optional:
      affects: {type: list[node_ref]}

  ErrorCase:
    group: "Error > ErrorCase"
    read_order: reference
    required:
      code:     {type: str}
      trigger:  {type: str}
      severity: {type: enum, values: [fatal, error, warning, info]}
      handling: {type: str}
      fix:      {type: str}
    optional:
      domain:         {type: node_ref}
      user_message:   {type: str}
      dev_note:       {type: str}
      recovery:       {type: str}
      affects:        {type: list[node_ref]}
      related_errors: {type: list[node_ref]}
      fixes:          {type: list[dict], description: "Append-only fix history"}

  # Test group (3 types)
  TestSuite: {group: "Test > TestSuite", read_order: reference}
  TestKind:  {group: "Test > TestKind",  read_order: reference}
  TestCase:  {group: "Test > TestCase",  read_order: background}

  # Meta group (3 types)
  Session: {group: "Meta > Session", read_order: background}
  Wave:    {group: "Meta > Wave",    read_order: background}
  Task:    {group: "Meta > Task",    read_order: background}

  # Legacy compat
  Document: {group: "Document > Spec", read_order: important}
  Lesson:   {group: "Document > Lesson > Dev", read_order: reference}
```

**Commit:**
```
Wave 17A01 Task 1: rewrite core_nodes.yaml v2

- 65+ node types across 6 groups
- group field: breadcrumb path for all types
- lifecycle replaces status, read_order replaces priority
- description: info (required) + code (optional)
- Invariant: rule+scope+enforcement+violation_action required
- ErrorCase: fix history structure
```

---

## TASK 2 — Rewrite `core_edges.yaml` v2

**File:** `gobp/schema/core_edges.yaml`

```yaml
version: "2.0"

base:
  from:       {type: str, required: true}
  to:         {type: str, required: true}
  type:       {type: str, required: true}
  reason:     {type: str, required: false, default: ""}
  created_at: {type: timestamp}

edge_types:
  specified_in:  {description: "Node được đặc tả trong Document"}
  references:    {description: "Node tham chiếu đến node khác"}
  implements:    {description: "Node implement spec/interface"}
  depends_on:    {description: "Node phụ thuộc vào node khác"}
  relates_to:    {description: "Mối liên hệ chung"}
  enforces:      {description: "Constraint áp dụng cho node"}
  validated_by:  {description: "Node được validate bởi Engine/TestCase"}
  covers:        {description: "TestCase cover node"}
  belongs_to:    {description: "Node thuộc về group/suite"}
  of_kind:       {description: "TestCase thuộc TestKind"}
  supersedes:    {description: "Node mới thay thế node cũ"}
  discovered_in: {description: "Node được tạo trong Session"}
  affects:       {description: "Node ảnh hưởng đến node khác"}
  triggers:      {description: "Node trigger node khác"}
  produces:      {description: "Node produce output node"}
```

**Commit:**
```
Wave 17A01 Task 2: rewrite core_edges.yaml v2 — reason field added
```

---

## TASK 3 — ID Generator v2

**File:** `gobp/core/id_generator.py`

```python
"""GoBP ID Generator v2.
Format: {group_slug}.{name_slug}.{8hex}
"""
import hashlib, re, time
from typing import Optional

_ABBREV = {
    'infrastructure': 'infra', 'application': 'app',
    'document': 'doc', 'constraint': 'const',
    'frontend': 'fe', 'security': 'sec',
    'database': 'db', 'messaging': 'msg',
    'observability': 'obs',
}

def _slugify(text: str) -> str:
    try:
        from unidecode import unidecode
        text = unidecode(text)
    except ImportError:
        pass
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'[\s_]+', '_', text)
    return text[:30]

def _group_to_slug(group: str) -> str:
    parts = [p.strip().lower() for p in group.split('>')]
    slugs = [_ABBREV.get(p, _slugify(p)) for p in parts]
    return '.'.join(s for s in slugs if s)

def generate_id(name: str, group: str) -> str:
    group_slug = _group_to_slug(group)
    name_slug = _slugify(name)
    content = f"{group}:{name}:{time.time_ns()}"
    hex_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
    return f"{group_slug}.{name_slug}.{hex_suffix}"

def infer_group_from_type(node_type: str, schema: dict) -> str:
    return schema.get('node_types', {}).get(node_type, {}).get('group', '')
```

**Commit:**
```
Wave 17A01 Task 3: ID generator v2 — group-embedded IDs
```

---

## TASK 4 — File Format v2

**File:** `gobp/core/file_format.py`

```python
"""GoBP file format v2 — YAML node/edge serialization."""
from pathlib import Path
from typing import Any
import yaml
from datetime import datetime, timezone

FIELD_ORDER = ['id','name','type','group','lifecycle','read_order',
               'description','tags','created_at','session_id']

def auto_fill_description(desc: Any) -> dict:
    if isinstance(desc, str):
        return {"info": desc, "code": ""}
    if isinstance(desc, dict):
        return {"info": desc.get('info', desc.get('description', '')),
                "code": desc.get('code', "")}
    return {"info": "", "code": ""}

def serialize_node(node: dict) -> str:
    ordered = {f: node[f] for f in FIELD_ORDER if f in node}
    ordered.update({k: v for k, v in node.items() if k not in ordered})
    return yaml.dump(ordered, allow_unicode=True,
                     default_flow_style=False, sort_keys=False)

def deserialize_node(content: str) -> dict:
    return yaml.safe_load(content) or {}

def node_file_path(root: Path, node_id: str) -> Path:
    return root / '.gobp' / 'nodes' / f'{node_id}.yaml'

def write_node(root: Path, node: dict) -> None:
    path = node_file_path(root, node['id'])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_node(node), encoding='utf-8')

def read_node(root: Path, node_id: str) -> dict | None:
    path = node_file_path(root, node_id)
    if not path.exists():
        return None
    return deserialize_node(path.read_text(encoding='utf-8'))

def append_edge(root: Path, edge: dict) -> None:
    path = root / '.gobp' / 'edges' / 'relations.yaml'
    path.parent.mkdir(parents=True, exist_ok=True)
    edges = yaml.safe_load(path.read_text(encoding='utf-8')) if path.exists() else []
    edges = edges or []
    # Dedup
    for e in edges:
        if e['from']==edge['from'] and e['to']==edge['to'] and e['type']==edge['type']:
            return
    edge.setdefault('reason', '')
    edge.setdefault('created_at', datetime.now(timezone.utc).isoformat())
    edges.append(edge)
    path.write_text(yaml.dump(edges, allow_unicode=True,
                              default_flow_style=False), encoding='utf-8')
```

**Commit:**
```
Wave 17A01 Task 4: file format v2 — description.info/code, reason on edges
```

---

## TASK 5 — Schema Loader v2

**File:** `gobp/core/schema_loader.py`

```python
"""Schema loader v2."""
from pathlib import Path
import yaml
from functools import lru_cache

class SchemaV2:
    def __init__(self, schema_dir: Path):
        self._nodes = yaml.safe_load((schema_dir/'core_nodes.yaml').read_text()) or {}
        self._edges = yaml.safe_load((schema_dir/'core_edges.yaml').read_text()) or {}

    @property
    def node_types(self) -> dict:
        return self._nodes.get('node_types', {})

    def get_group(self, node_type: str) -> str:
        return self.node_types.get(node_type, {}).get('group', '')

    def get_default_read_order(self, node_type: str) -> str:
        return self.node_types.get(node_type, {}).get('read_order', 'reference')

    def is_valid_type(self, node_type: str) -> bool:
        return node_type in self.node_types

    def validate_node(self, node: dict) -> list[str]:
        errors = []
        for f in ['id', 'name', 'type', 'group']:
            if not node.get(f):
                errors.append(f"Missing required: {f}")
        desc = node.get('description', {})
        if isinstance(desc, dict) and not desc.get('info'):
            errors.append("description.info is required")
        node_type = node.get('type', '')
        for field in self.node_types.get(node_type, {}).get('required', {}):
            if field not in ('what','why','definition','usage_guide') and not node.get(field):
                errors.append(f"{node_type} requires: {field}")
        return errors

@lru_cache(maxsize=4)
def load_schema(schema_dir: Path) -> SchemaV2:
    return SchemaV2(schema_dir)
```

**Commit:**
```
Wave 17A01 Task 5: schema loader v2 with validation
```

---

## TASK 6 — Tests

**File:** `tests/test_wave17a01.py` — 20 tests

```python
"""Tests for Wave 17A01: schema v2, ID generator, file format, schema loader."""
import pytest
from pathlib import Path
from gobp.core.id_generator import generate_id, _group_to_slug, infer_group_from_type
from gobp.core.file_format import (auto_fill_description, serialize_node,
                                    deserialize_node, write_node, read_node, append_edge)
from gobp.core.schema_loader import SchemaV2

# ID Generator tests (6)
def test_generate_id_entity():
    id_ = generate_id("Traveller", "Dev > Domain > Entity")
    assert id_.startswith("dev.domain.entity.traveller.")
    assert len(id_.split('.')[-1]) == 8

def test_generate_id_security():
    id_ = generate_id("OTP Flow", "Dev > Infrastructure > Security > AuthFlow")
    assert "infra" in id_ or "sec" in id_

def test_generate_id_uniqueness():
    import time
    id1 = generate_id("Test", "Dev > Domain > Entity")
    time.sleep(0.001)
    id2 = generate_id("Test", "Dev > Domain > Entity")
    assert id1 != id2  # different time_ns

def test_group_to_slug_abbreviation():
    slug = _group_to_slug("Dev > Infrastructure > Security")
    assert "infra" in slug
    assert "sec" in slug

def test_generate_id_doc():
    id_ = generate_id("DOC-01 Soul", "Document > Spec")
    assert id_.startswith("doc.spec.")

def test_generate_id_constraint():
    id_ = generate_id("Balance Non-Negative", "Constraint > Invariant")
    assert id_.startswith("const.invariant.")

# File Format tests (7)
def test_auto_fill_description_string():
    result = auto_fill_description("Test description")
    assert result == {"info": "Test description", "code": ""}

def test_auto_fill_description_dict():
    result = auto_fill_description({"info": "Test", "code": "x = 1"})
    assert result["info"] == "Test"
    assert result["code"] == "x = 1"

def test_auto_fill_description_empty():
    result = auto_fill_description({})
    assert result["info"] == ""
    assert result["code"] == ""

def test_serialize_deserialize_node(tmp_path):
    node = {"id": "dev.domain.entity.test.a1b2c3d4", "name": "Test",
            "type": "Entity", "group": "Dev > Domain > Entity",
            "lifecycle": "draft", "read_order": "foundational",
            "description": {"info": "Test entity", "code": ""}}
    yaml_str = serialize_node(node)
    result = deserialize_node(yaml_str)
    assert result["name"] == "Test"
    assert result["description"]["info"] == "Test entity"

def test_write_read_node(tmp_path):
    node = {"id": "dev.domain.entity.test.a1b2c3d4", "name": "Test",
            "type": "Entity", "group": "Dev > Domain > Entity",
            "description": {"info": "Test", "code": ""}}
    write_node(tmp_path, node)
    result = read_node(tmp_path, "dev.domain.entity.test.a1b2c3d4")
    assert result is not None
    assert result["name"] == "Test"

def test_append_edge_with_reason(tmp_path):
    edge = {"from": "node_a", "to": "node_b", "type": "references",
            "reason": "Test reason"}
    append_edge(tmp_path, edge)
    import yaml
    edges = yaml.safe_load((tmp_path/'.gobp'/'edges'/'relations.yaml').read_text())
    assert len(edges) == 1
    assert edges[0]["reason"] == "Test reason"

def test_append_edge_dedup(tmp_path):
    edge = {"from": "node_a", "to": "node_b", "type": "references"}
    append_edge(tmp_path, edge)
    append_edge(tmp_path, edge)  # duplicate
    import yaml
    edges = yaml.safe_load((tmp_path/'.gobp'/'edges'/'relations.yaml').read_text())
    assert len(edges) == 1

# Schema Loader tests (7)
@pytest.fixture
def schema(tmp_path):
    import shutil
    schema_src = Path("gobp/schema")
    schema_dst = tmp_path / "schema"
    shutil.copytree(schema_src, schema_dst)
    return SchemaV2(schema_dst)

def test_schema_loads(schema):
    assert len(schema.node_types) >= 60

def test_all_types_have_group(schema):
    for type_name, type_def in schema.node_types.items():
        assert 'group' in type_def, f"{type_name} missing group field"

def test_get_group_entity(schema):
    assert schema.get_group("Entity") == "Dev > Domain > Entity"

def test_get_group_authflow(schema):
    assert "Security" in schema.get_group("AuthFlow")

def test_validate_node_missing_group(schema):
    node = {"id": "x", "name": "Test", "type": "Entity",
            "description": {"info": "Test"}}
    errors = schema.validate_node(node)
    assert any("group" in e for e in errors)

def test_validate_node_missing_description_info(schema):
    node = {"id": "x", "name": "Test", "type": "Entity",
            "group": "Dev > Domain > Entity",
            "description": {"code": "x = 1"}}
    errors = schema.validate_node(node)
    assert any("description.info" in e for e in errors)

def test_validate_invariant_missing_rule(schema):
    node = {"id": "x", "name": "Test", "type": "Invariant",
            "group": "Constraint > Invariant",
            "description": {"info": "Test"},
            "scope": "class", "enforcement": "hard",
            "violation_action": "reject"}
    errors = schema.validate_node(node)
    assert any("rule" in e for e in errors)
```

**Commit:**
```
Wave 17A01 Task 6: 20 tests for schema v2 components
```

---

## TASK 7 — CHANGELOG + GoBP MCP + Full Suite

**CHANGELOG:**
```markdown
## [Wave 17A01] — Schema + File Format Rewrite — 2026-04-19

### Rewritten
- core_nodes.yaml v2: 65+ node types, group breadcrumb
- core_edges.yaml v2: reason field on all edges
- gobp/core/id_generator.py: group-embedded IDs
- gobp/core/file_format.py: description.info/code handling
- gobp/core/schema_loader.py: SchemaV2 validation

### Schema changes
- group: "Dev > Infrastructure > Security" breadcrumb (REQUIRED)
- lifecycle replaces status
- read_order replaces priority
- description = {info: required, code: optional}
- Invariant: rule+scope+enforcement+violation_action required
- ErrorCase: fix history (append-only, runtime|dev_code)
- BusinessRule: new type for soft rules

### Tests: 653+ (633 baseline + 20 new)
```

**Full suite:**
```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --override-ini="addopts=" -q --tb=no
# Expected: 653+ tests
```

**GoBP MCP:**
```
gobp(query="session:start actor='cursor' goal='Wave 17A01 complete'")
gobp(query="session:end outcome='Schema v2 complete: 65 types, group field, lifecycle, read_order, description.info/code, ID generator, file format, schema loader. 653+ tests.'")
```

**Commit:**
```
Wave 17A01 Task 7: CHANGELOG + full suite — 653+ tests passing
```

---

# CEO DISPATCH

## Cursor
```
Read docs/GOBP_SCHEMA_REDESIGN_v2.1.md TRƯỚC.
Read docs/wave_17a_series_plan.md.
Read waves/wave_17a01_brief.md.
Read GoBP MCP: gobp(query="find:Decision mode=summary")

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute Tasks 1-7.
Testing: R9-B Tasks 1-6, R9-C Task 7.

QUAN TRỌNG:
  Không đụng GraphIndex hay query engine (Wave 17A02)
  633 baseline tests PHẢI pass
  group field = breadcrumb path REQUIRED trên mọi type
  description phải có .info và .code

GoBP MCP sau mỗi task (dec:d004).
Lesson: suggest: trước khi tạo (dec:d011).
```

## Claude CLI
```
Audit Wave 17A01.
Verify:
  - core_nodes.yaml: 65+ types, all have group
  - core_edges.yaml: reason field
  - id_generator.py: format correct
  - file_format.py: description handling
  - schema_loader.py: validation
  - 653+ tests passing

GoBP MCP session capture. Không cần Lesson node.
```

## Push
```powershell
cd D:\GoBP
git add waves/wave_17a01_brief.md docs/GOBP_SCHEMA_REDESIGN_v2.1.md docs/wave_17a_series_plan.md
git commit -m "Add Wave 17A01 Brief + Schema Redesign v2.1 + Series Plan"
git push origin main
```

---

*Wave 17A01 Brief v1.0 — 2026-04-19*
*References: dec:d004, dec:d006, dec:d011*
*Part of: Wave 17A Series (7 waves)*
◈
