# ◈ GoBP SCHEMA

**File:** `D:\GoBP\docs\SCHEMA.md`
**Version:** v0.1
**Status:** draft
**Depends on:** ARCHITECTURE.md / `GoBP_ARCHITECTURE.md` (must read first)
**Audience:** Cursor implementing schema, AI agents validating data

**Packaged schema files:** `gobp/schema/core_nodes.yaml` (**21** node types), `gobp/schema/core_edges.yaml` (**14** edge kinds). Validator loads YAML first; this document should stay aligned (use `gobp(query="validate: schema-docs")` to cross-check).

---

## 0. PURPOSE

SCHEMA.md documents the shapes enforced by the packaged YAML under `gobp/schema/`. Every node and edge must conform; the validator loads the YAML packs. Keep this file aligned with those files (see `validate: schema-docs`).

This doc is the source of truth for:
- What fields each node type requires
- What fields are optional
- What values are allowed (enums, patterns)
- How edges connect (from type, to type, cardinality)

If ARCHITECTURE.md describes nodes conceptually, SCHEMA.md describes them formally.

---

## 1. SCHEMA LANGUAGE

GoBP uses YAML-based schema definitions, inspired by JSON Schema but simpler.

### 1.1 Basic structure

```yaml
node_type:
  name: TypeName
  parent: null | ParentType
  description: str
  id_prefix: str          # e.g. "idea" for idea:i042
  required:
    field_name:
      type: str | int | bool | list | dict | timestamp | enum
      enum_values: [...]  # if type=enum
      pattern: regex      # if type=str and constrained
      description: str
  optional:
    field_name:
      type: ...
      default: ...
  constraints:
    - constraint_expression
```

### 1.2 Types supported

| Type | Description | Example |
|---|---|---|
| `str` | Plain string | `"Login"` |
| `int` | Integer | `42` |
| `bool` | Boolean | `true` |
| `timestamp` | ISO 8601 datetime | `"2026-04-14T14:30:00"` |
| `enum` | One of fixed values | `"LOCKED"` |
| `list[T]` | List of type T | `["a", "b", "c"]` |
| `dict` | Free-form object | `{key: value}` |
| `node_ref` | Reference to node ID | `"feat:login"` |
| `markdown` | Markdown string (rendered in UI) | `"## Heading"` |

### 1.3 Constraint expressions

Constraints are simple Python-like expressions evaluated at validation time:

```
- len(alternatives_considered) >= 1
- maturity != "LOCKED" or why is not None
- created <= updated
- status in ["DRAFT", "ACTIVE", "DEPRECATED"]
```

---

## 2. CORE NODE SCHEMAS

### 2.1 Node (generic)

```yaml
node_type:
  name: Node
  parent: null
  description: Generic container for any entity, feature, tool, concept
  id_prefix: "node"
  
  required:
    id:
      type: str
      pattern: "^node:[a-z][a-z0-9_]*$"
      description: Stable unique identifier
    
    type:
      type: str
      description: Schema type (Node or subtype from extensions)
    
    name:
      type: str
      description: Human-readable label
    
    status:
      type: enum
      enum_values: [DRAFT, ACTIVE, DEPRECATED, ARCHIVED]
      description: Lifecycle state
    
    created:
      type: timestamp
    
    updated:
      type: timestamp
  
  optional:
    subtype:
      type: str
      description: Project-specific categorization (e.g. Feature, Tool, Entity)
    
    description:
      type: str
      description: Short prose description
    
    tags:
      type: list[str]
      default: []
    
    custom_fields:
      type: dict
      default: {}
      description: Project-specific extension fields
    
    priority:
      type: enum
      enum_values: [critical, high, medium, low]
      default: medium
      description: Importance level.
  
  constraints:
    - created <= updated
    - status != "ARCHIVED" or updated is not None
```

### 2.2 Idea

```yaml
node_type:
  name: Idea
  parent: null
  description: Unstructured brainstorm captured from conversation
  id_prefix: "idea"
  
  required:
    id:
      type: str
      pattern: "^idea:i\\d{3,}$"
    
    type:
      type: str
      enum_values: [Idea]
    
    raw_quote:
      type: str
      description: Verbatim text from founder, never paraphrased
    
    interpretation:
      type: str
      description: AI's understanding of the raw quote
    
    subject:
      type: str
      description: Topic this idea is about (e.g. auth:login.method)
    
    maturity:
      type: enum
      enum_values: [RAW, REFINED, DISCUSSED, LOCKED, DEPRECATED]
      description: Lifecycle stage
    
    confidence:
      type: enum
      enum_values: [low, medium, high]
      description: AI confidence in interpretation
    
    session_id:
      type: node_ref
      description: Session where this idea was captured
    
    created:
      type: timestamp
    
    updated:
      type: timestamp
  
  optional:
    supersedes:
      type: node_ref
      description: Previous idea this replaces
    
    context_notes:
      type: str
      description: Surrounding conversation context
    
    ceo_verified:
      type: bool
      default: false
      description: Has founder explicitly confirmed interpretation?
    
    status:
      type: enum
      enum_values: [ACTIVE, SUPERSEDED]
      default: ACTIVE
    
    priority:
      type: enum
      enum_values: [critical, high, medium, low]
      default: medium
      description: Importance level.
  
  constraints:
    - len(raw_quote) > 0
    - len(interpretation) > 0
    - maturity != "LOCKED" or ceo_verified == true
```

### 2.3 Decision

```yaml
node_type:
  name: Decision
  parent: null
  description: Locked authoritative knowledge
  id_prefix: "dec"
  
  required:
    id:
      type: str
      pattern: "^dec:d\\d{3,}$"
    
    type:
      type: str
      enum_values: [Decision]
    
    topic:
      type: str
      description: What the decision is about
    
    what:
      type: str
      description: The decision in 1-2 sentences
    
    why:
      type: str
      description: Rationale
    
    status:
      type: enum
      enum_values: [LOCKED, SUPERSEDED, WITHDRAWN]
    
    locked_at:
      type: timestamp
    
    locked_by:
      type: list[str]
      description: Who confirmed (CEO + AI witness)
    
    session_id:
      type: node_ref
    
    created:
      type: timestamp
    
    updated:
      type: timestamp
  
  optional:
    alternatives_considered:
      type: list[dict]
      description: Rejected options with reasons
      item_schema:
        option: str
        rejected_reason: str
    
    risks:
      type: list[str]
      description: What could go wrong
    
    blocks:
      type: list[node_ref]
      description: What this decision enables or blocks
    
    supersedes:
      type: node_ref
      description: Previous decision this replaces
    
    related_ideas:
      type: list[node_ref]
      description: Ideas that led to this decision
    
    priority:
      type: enum
      enum_values: [critical, high, medium, low]
      default: medium
      description: Importance level.
  
  constraints:
    - len(what) > 0
    - len(why) > 0
    - len(locked_by) >= 1
    - status != "SUPERSEDED" or supersedes is not None
```

### 2.4 Session

```yaml
node_type:
  name: Session
  parent: null
  description: Record of one AI working session
  id_prefix: "session"
  
  required:
    id:
      type: str
      pattern: "^session:\\d{4}-\\d{2}-\\d{2}.*$"
    
    type:
      type: str
      enum_values: [Session]
    
    actor:
      type: str
      description: Which AI agent
    
    started_at:
      type: timestamp
    
    goal:
      type: str
      description: What this session aimed to accomplish
    
    status:
      type: enum
      enum_values: [IN_PROGRESS, COMPLETED, INTERRUPTED, FAILED]
    
    created:
      type: timestamp
    
    updated:
      type: timestamp
  
  optional:
    ended_at:
      type: timestamp
    
    outcome:
      type: str
      description: What actually happened
    
    nodes_touched:
      type: list[node_ref]
      default: []
    
    decisions_locked:
      type: list[node_ref]
      default: []
    
    pending:
      type: list[str]
      default: []
      description: What was not finished
    
    tokens_used:
      type: int
    
    human_present:
      type: bool
    
    handoff_notes:
      type: str
      description: Context for next session
  
  constraints:
    - started_at <= ended_at or ended_at is null
    - status != "COMPLETED" or ended_at is not None
    - status != "COMPLETED" or outcome is not None
```

### 2.5 Document

```yaml
node_type:
  name: Document
  parent: null
  description: Pointer to external doc file with metadata
  id_prefix: "doc"
  
  required:
    id:
      type: str
      pattern: "^doc:.+$"
    
    type:
      type: str
      enum_values: [Document]
    
    name:
      type: str
      description: Document title
    
    source_path:
      type: str
      description: Relative path to file
    
    content_hash:
      type: str
      pattern: "^sha256:[a-f0-9]{64}$"
      description: SHA-256 of file content
    
    registered_at:
      type: timestamp
    
    last_verified:
      type: timestamp
    
    created:
      type: timestamp
    
    updated:
      type: timestamp
  
  optional:
    sections:
      type: list[dict]
      default: []
      item_schema:
        heading: str
        lines: list[int]    # [start, end]
        tags: list[str]
    
    tags:
      type: list[str]
      default: []
    
    owned_by:
      type: str
    
    phase:
      type: int
    
    status:
      type: enum
      enum_values: [ACTIVE, STALE, MISSING, DEPRECATED]
      default: ACTIVE
    
    priority:
      type: enum
      enum_values: [critical, high, medium, low]
      default: medium
      description: Importance level.
  
  constraints:
    - content_hash is not null
    - last_verified >= registered_at
```

### 2.6 Lesson

```yaml
node_type:
  name: Lesson
  parent: null
  description: Something learned from experience
  id_prefix: "lesson"
  
  required:
    id:
      type: str
      pattern: "^lesson:ll\\d{3,}$"
    
    type:
      type: str
      enum_values: [Lesson]
    
    title:
      type: str
      description: Short headline
    
    trigger:
      type: str
      description: When this lesson applies
    
    what_happened:
      type: str
      description: The mistake or pattern observed
    
    why_it_matters:
      type: str
    
    mitigation:
      type: str
      description: How to avoid in future
    
    severity:
      type: enum
      enum_values: [low, medium, high, critical]
    
    captured_in_session:
      type: node_ref
    
    created:
      type: timestamp
    
    updated:
      type: timestamp
  
  optional:
    related_nodes:
      type: list[node_ref]
      default: []
    
    related_ideas:
      type: list[node_ref]
      default: []
    
    verified_count:
      type: int
      default: 1
      description: Times this lesson has been confirmed
    
    last_applied:
      type: timestamp
    
    tags:
      type: list[str]
      default: []
    
    priority:
      type: enum
      enum_values: [critical, high, medium, low]
      default: medium
      description: Importance level.
  
  constraints:
    - verified_count >= 1
```

### 2.7 Concept

Stores a defined concept or framework idea for AI orientation. When AI connects to a project, it discovers Concept nodes via `gobp(query="find:Concept …")` or project orientation (`gobp(query="overview:")`) to understand the project's vocabulary and thinking framework without CEO re-explanation.

**Required fields:**
- `id` — e.g. `concept:test_taxonomy`
- `type` — always `Concept`
- `name` — short concept name (e.g. "Test Taxonomy")
- `definition` — what this concept means in this project
- `usage_guide` — how AI should use or apply this concept
- `created`, `updated` — timestamps

**Optional fields:**
- `applies_to` — list of node types this concept applies to
- `seed_values` — default values or examples
- `extensible` — bool, default true
- `tags` — list of strings
- `priority` — enum: `critical | high | medium | low` (default: medium). Importance level.

**Example:** `concept:test_taxonomy` — explains GoBP's 3-level test taxonomy so AI understands how to create and link TestKind and TestCase nodes.

---

### 2.8 TestKind

A category of software test with a template and seed examples. GoBP seeds 16 universal TestKind nodes on `gobp init` covering all four `group` values.

**Field `group` (classification, not the same as `id` slug):**

| Value | Meaning | Typical TestKind rows (examples) |
|-------|---------|----------------------------------|
| `process` | **Phương pháp** — *how* the system is exercised | `testkind:unit`, `testkind:integration`, `testkind:e2e`, contract, regression, smoke, exploratory |
| `functional` | **Chủ đề chức năng / hành vi** — business acceptance | e.g. `testkind:acceptance` |
| `non_functional` | **Chủ đề phi chức năng** — quality attributes (performance, a11y, …). Not the `Invariant` node type; name nodes so they do not collide conceptually. | performance, accessibility, compatibility |
| `security` | **Chủ đề bảo mật** | `testkind:security_*`, encryption, API security, … |

Slugs such as **unit**, **e2e**, **integration** appear in **`id` / `name`**, not as `group` values. `group` is orthogonal: it classifies *what the row represents* (method vs subject).

**Required fields:**
- `id` — e.g. `testkind:unit`, `testkind:security_network`
- `type` — always `TestKind`
- `name` — short name (e.g. "Unit Test", "Network Security Test")
- `group` — enum: `functional | non_functional | security | process` (see table above)
- `scope` — enum: `universal | platform | project`
- `description` — what this kind of test verifies
- `template` — dict with template fields (given/when/then or scenario/threshold/tool etc.)
- `created`, `updated` — timestamps

**Optional fields:**
- `platform` — null (universal) or "flutter" | "deno" | "web" etc.
- `seed_examples` — list of example test case names
- `extensible` — bool, default true
- `tags` — list of strings

**3-level scope:**
- `universal` — pre-seeded on init, applies to all projects
- `platform` — added per project for specific stack (Flutter, Deno, etc.)
- `project` — custom kinds unique to this project

---

### 2.9 TestCase

A specific test instance linked to a TestKind and a feature/node being tested.

**Required fields:**
- `id` — e.g. `tc:login_unit_001`
- `type` — always `TestCase`
- `name` — short test case title
- `kind_id` — node_ref to the TestKind this test belongs to
- `covers` — node_ref to the Feature/Node being tested
- `status` — enum: `DRAFT | READY | PASSING | FAILING | SKIPPED | DEPRECATED`
- `priority` — enum: `low | medium | high | critical`
- `created`, `updated` — timestamps

**Optional fields:**
- `given` — preconditions (BDD Given)
- `when` — action being tested (BDD When)
- `then` — expected outcome (BDD Then)
- `scenario` — alternative to Given/When/Then for non-BDD kinds
- `automated` — bool, whether actual test code exists
- `code_ref` — path to test file + test name (e.g. `test/auth_test.dart#login_valid`)
- `tags` — list of strings

---

## 3. CORE EDGE SCHEMAS

### 3.1 relates_to

```yaml
edge_type:
  name: relates_to
  description: Generic connection
  directional: false
  
  required:
    from:
      type: node_ref
    to:
      type: node_ref
    type:
      type: str
      enum_values: [relates_to]
  
  optional:
    reason:
      type: str
      description: Why these two nodes are related
  
  constraints:
    - from != to
  
  cardinality: many_to_many
  allowed_node_types: [all]
```

### 3.2 supersedes

```yaml
edge_type:
  name: supersedes
  description: New version replaces old version
  directional: true  # new -> old
  
  required:
    from:
      type: node_ref
      description: New node (replacer)
    to:
      type: node_ref
      description: Old node (superseded)
    type:
      type: str
      enum_values: [supersedes]
  
  optional:
    reason:
      type: str
      description: Why superseded
    
    superseded_at:
      type: timestamp
  
  constraints:
    - from != to
    - type(from) == type(to)  # same node type required
  
  cardinality: one_to_one  # one new supersedes at most one old
  allowed_node_types: [Idea, Decision, Node]
```

### 3.3 implements

```yaml
edge_type:
  name: implements
  description: Concrete implementation of abstract spec
  directional: true  # implementation -> spec
  
  required:
    from:
      type: node_ref
      description: Concrete node
    to:
      type: node_ref
      description: Abstract node being implemented
    type:
      type: str
      enum_values: [implements]
  
  optional:
    partial:
      type: bool
      default: false
      description: Partial implementation?
    
    notes:
      type: str
  
  cardinality: many_to_many
  allowed_node_types: [Node -> Decision, Node -> Node]
```

### 3.4 discovered_in

```yaml
edge_type:
  name: discovered_in
  description: Node was created in this session
  directional: true  # node -> session
  
  required:
    from:
      type: node_ref
      description: Any node
    to:
      type: node_ref
      description: Session node
    type:
      type: str
      enum_values: [discovered_in]
  
  optional:
    position_in_session:
      type: int
      description: Ordinal position within session
  
  cardinality: many_to_one  # many nodes per session
  allowed_node_types: [all -> Session]
```

### 3.5 references

```yaml
edge_type:
  name: references
  description: Node points to document section for detail
  directional: true  # node -> document
  
  required:
    from:
      type: node_ref
    to:
      type: node_ref
      description: Must be Document node
    type:
      type: str
      enum_values: [references]
  
  optional:
    section:
      type: str
      description: Section heading within doc (e.g. "F2 Login")
    
    lines:
      type: list[int]
      description: Line range [start, end]
  
  cardinality: many_to_many
  allowed_node_types: [all -> Document]
```

### 3.6 covers

TestCase covers/validates a Feature or Node. The test validates that the target node works as intended.

**Usage:**
- `tc:login_unit_001` covers `node:feat_login`
- `tc:otp_security_001` covers `dec:d001`

**Rules:**
- Directed: TestCase → Node/Feature/Decision
- Many-to-one cardinality (many tests can cover one feature)
- Optional `coverage_type` field: `happy_path | error_path | boundary | security`

---

### 3.7 of_kind

TestCase belongs to a TestKind category.

**Usage:**
- `tc:login_unit_001` of_kind `testkind:unit`
- `tc:otp_security_001` of_kind `testkind:security_auth`

**Rules:**
- Directed: TestCase → TestKind
- Many-to-one cardinality (many tests belong to one kind)

---

## 4. VALIDATION RULES

### 4.1 Validation order

When a node or edge is written, validation runs in this order:

1. **Type check** — field values match declared types
2. **Required fields** — all required fields present and non-empty
3. **Pattern check** — string fields match regex patterns
4. **Enum check** — enum fields have allowed values
5. **Constraint check** — custom constraint expressions evaluated
6. **Referential check** — node_ref fields point to existing nodes
7. **Cardinality check** — edges respect cardinality rules

Any failure stops the write. No partial writes.

### 4.2 Validation errors format

```json
{
  "ok": false,
  "errors": [
    {
      "field": "maturity",
      "rule": "enum",
      "expected": ["RAW", "REFINED", "DISCUSSED", "LOCKED", "DEPRECATED"],
      "got": "FINALIZED",
      "message": "Field 'maturity' has invalid value 'FINALIZED'"
    }
  ]
}
```

Error messages must be actionable — tell AI exactly what to fix.

### 4.3 Soft warnings vs hard errors

**Hard errors (block write):**
- Missing required field
- Invalid type
- Invalid enum value
- Failed constraint
- Broken reference (node_ref points to non-existent node)

**Soft warnings (allow write, log warning):**
- Optional field missing (if considered best practice)
- Unusual value (outside typical range)
- Potential duplicate (similar node exists)

Writes with warnings succeed but include warnings in response.

---

## 5. SCHEMA EXTENSIONS

Projects can extend core schemas via `.gobp/schema/extensions.yaml`:

### 5.1 Extension structure

```yaml
extends: core-v1
extension_name: MIHOS
extension_version: 1.0

# Add new node types
node_types:
  
  Feature:
    parent: Node
    id_prefix: "feat"
    
    required:
      phase:
        type: int
        description: Which MIHOS phase (1-4)
      
      flow_ref:
        type: node_ref
        description: Parent flow
    
    constraints:
      - phase in [1, 2, 3, 4]
  
  Engine:
    parent: Node
    id_prefix: "eng"
    
    required:
      technology:
        type: str
        description: Tech stack used
      
      layer:
        type: int
        description: 6-layer engine architecture
    
    constraints:
      - layer in [1, 2, 3, 4, 5, 6]
  
  Invariant:
    parent: Node
    id_prefix: "inv"
    
    required:
      rule_text:
        type: str
        description: Formal rule statement
      
      severity:
        type: enum
        enum_values: [hard, soft, warning]
    
    constraints:
      - severity == "hard" implies enforced_by is not None

# Add new edge types
edge_types:
  
  enforces:
    description: Invariant enforces rule on target
    directional: true  # invariant -> target
    from_types: [Invariant]
    to_types: [Feature, Engine]
    cardinality: many_to_many
  
  belongs_to_phase:
    description: Node belongs to project phase
    directional: true
    from_types: [Node]
    to_types: [Phase]
    cardinality: many_to_one
```

### 5.2 Extension rules

- Extensions can **add** node types and edge types
- Extensions **cannot remove** or modify core types
- Extension node types must have `parent: Node` or `parent: null` (new root)
- Extension field names **cannot shadow** core field names
- Constraint expressions **can reference** core fields
- Extensions are **versioned** — migrations required for breaking changes

### 5.3 Loading extensions

GoBP loads extensions at startup:

```python
# Pseudocode
core_schema = load_schema("gobp/schema/core_nodes.yaml")
core_edges = load_schema("gobp/schema/core_edges.yaml")

if (project_root / ".gobp/schema/extensions.yaml").exists():
    ext = load_extension(project_root / ".gobp/schema/extensions.yaml")
    validate_extension_compatibility(ext, core_schema)
    merged_schema = merge_schemas(core_schema, ext)
else:
    merged_schema = core_schema

validator = Validator(merged_schema)
```

Extension conflicts with core are detected at load time, not runtime.

---

## 6. ID CONVENTIONS

IDs are stable identifiers. Once assigned, never change.

### 6.1 Format

```
<prefix>:<slug>
```

Examples:
- `node:feat_login`
- `idea:i042`
- `dec:d015`
- `session:2026-04-14_pm`
- `doc:DOC-07`
- `lesson:ll023`

### 6.2 Prefix rules

| Prefix | Node type |
|---|---|
| `node` | Generic Node (can have subtype) |
| `idea` | Idea |
| `dec` | Decision |
| `session` | Session |
| `doc` | Document |
| `lesson` | Lesson |

Extension prefixes (examples from MIHOS):
- `feat` — Feature subtype (but ID stored as `node:feat_X`)
- `eng` — Engine
- `ent` — Entity
- `inv` — Invariant
- `flow` — Flow

### 6.3 Slug rules

After prefix, the slug must:
- Start with letter
- Lowercase alphanumeric + underscore only
- No spaces, no special chars (except underscore)
- For numbered IDs: `i001`, `d015` (zero-padded, 3+ digits)
- For named IDs: `feat_login`, `DOC-07`

### 6.4 ID assignment

- **Numbered IDs:** GoBP auto-increments per type (next `idea:i043` after `idea:i042`)
- **Named IDs:** AI or human provides explicit name (e.g. `doc:DOC-07`, `node:feat_login`)
- **Session IDs:** Format `session:YYYY-MM-DD_slug` where slug is session purpose

### Session ID format (v2)
`session:YYYY-MM-DD_XXXXXX` where XXXXXX = 6-char UUID hex.
Always exactly 28 characters. Example: `session:2026-04-15_a3f7c2`

### 6.5 ID immutability

Once created, ID never changes. For rename scenarios:
- Create new node with new ID
- Old node supersedes new (or vice versa)
- `name` field on new node reflects new name
- All edges still point to stable IDs

**Example:** BKP renamed to GoBP
```
node:tool_bkp  (name: "BKP", status: SUPERSEDED)
  ↑ supersedes
node:tool_gobp  (name: "GoBP", status: ACTIVE)
```

All queries for `node:tool_bkp` still work and return the superseded node. Queries for `"GoBP"` by name return the new node.

---

## 7. VERSIONING

### 7.1 Schema version

Core schema has a version number in `core_nodes.yaml`:

```yaml
schema_version: 1.0
```

v1.x = backward-compatible changes (add optional fields, add new types)
v2.x = breaking changes (remove fields, change types)

### 7.2 Project data version

Each `.gobp/` folder has `.gobp-version` file:

```
gobp_version: 1.0
schema_version: 1.0
created_at: 2026-04-14T20:00:00
```

GoBP v1.x can read any .gobp with schema v1.x. Cross-version compatibility:

| .gobp schema | GoBP v1.0 | GoBP v1.5 | GoBP v2.0 |
|---|---|---|---|
| 1.0 | ✓ | ✓ | ✓ (with migration) |
| 1.5 | ✗ (too new) | ✓ | ✓ (with migration) |
| 2.0 | ✗ | ✗ | ✓ |

### 7.3 Migration

When schema bumps version, migration script in `gobp/migrations/`:

```
gobp/migrations/
├── v1_0_to_v1_1.py
├── v1_1_to_v1_2.py
└── v1_x_to_v2_0.py
```

Migration runs on `gobp migrate` command. Always backed up to `.gobp/backups/pre-migration-YYYYMMDD/` first.

---

## 8. RESERVED FIELDS

Some field names are reserved and cannot be used in custom fields:

**Global reserved:**
- `id`, `type`, `name`, `status`, `created`, `updated`

**Node-specific reserved:**
- `subtype`, `description`, `tags`, `custom_fields`

**Edge-specific reserved:**
- `from`, `to`

Using a reserved name in custom schema is a hard error at load time.

---

## 9. COMPLETE CORE SCHEMA FILES

Ship layout (core schema + optional extensions). **Authoritative counts:** 21 node types in `core_nodes.yaml`, 14 edge types in `core_edges.yaml`. Project config `.gobp/config.yaml` uses integer `schema_version` (baseline **2** — see `gobp.core.init.INIT_SCHEMA_VERSION`).

```
gobp/schema/
├── core_nodes.yaml       # all core node types (21)
├── core_edges.yaml       # all core edge types (14)
└── extensions/           # optional packs (e.g. mihos.yaml)
```

Cross-cutting validation rules are enforced in loader/graph code and via `gobp(query="validate: …")` (see `docs/MCP_TOOLS.md`); there is no separate `core_validation.yaml` file in the tree.

### 9.1 core_nodes.yaml (abbreviated)

```yaml
schema_version: "2.0"
node_types:
  Node:           {...}  # §2.1
  Idea:           {...}  # §2.2
  Decision:       {...}  # §2.3
  Session:        {...}  # §2.4
  Document:       {...}  # §2.5
  Lesson:         {...}  # §2.6
  Concept:        {...}  # §2.7
  TestKind:       {...}  # §2.8
  TestCase:       {...}  # §2.9
  Engine:         {...}
  Flow:           {...}
  Entity:         {...}
  Feature:        {...}
  Invariant:      {...}
  Screen:         {...}
  APIEndpoint:    {...}
  Repository:     {...}
  Wave:           {...}
  Task:           {...}
  CtoDevHandoff:  {...}
  QaCodeDevHandoff: {...}
```

### 9.2 core_edges.yaml (abbreviated)

```yaml
schema_version: "2.0"
edge_types:
  relates_to:     {...}  # §3.1
  supersedes:     {...}  # §3.2
  implements:     {...}  # §3.3
  discovered_in:  {...}  # §3.4
  references:     {...}  # §3.5
  covers:         {...}  # §3.6
  of_kind:        {...}  # §3.7
  depends_on:     {...}
  tested_by:      {...}
  enforces:       {...}
  triggers:       {...}
  validates:      {...}
  produces:       {...}
```

### 9.3 Validation (runtime)

Graph and schema checks run through the MCP query protocol, for example:

- `validate: all` — full graph check
- `validate: nodes` / `validate: edges` — scoped checks
- `validate: schema-docs` — documentation vs packaged YAML (when implemented)

Conceptual rules (examples): non-Session nodes should have `discovered_in`; edges must reference existing nodes; `supersedes` must not cycle; locked decisions should be attributable to a session. Exact behavior is defined in code and tests under `tests/`.

---

## 10. SCHEMA TESTING

Schema definitions are tested via test fixtures:

```
tests/fixtures/
├── valid/
│   ├── minimal_idea.yaml       # Just required fields
│   ├── full_decision.yaml      # All fields populated
│   └── session_with_handoff.yaml
│
└── invalid/
    ├── missing_required.yaml   # Should fail "required field"
    ├── wrong_enum.yaml         # Should fail "enum check"
    ├── bad_pattern.yaml        # Should fail "pattern match"
    └── orphan_edge.yaml        # Should fail "referential check"
```

Test command: `pytest tests/` — schema and graph behavior are covered by the test suite (see `tests/test_*.py`).

---

## 11. REFERENCES

- ARCHITECTURE.md — conceptual descriptions of node/edge types
- INPUT_MODEL.md — how fields get populated from conversation
- IMPORT_MODEL.md — how fields get populated from existing docs
- MCP_TOOLS.md — how tools validate input against schemas

---

*Written: 2026-04-14*
*Status: v0.1 draft*
*Next: MCP_TOOLS.md*

◈
