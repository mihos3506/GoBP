# ◈ GoBP ID DESIGN SPECIFICATION

**Version:** 1.0
**Date:** 2026-04-16
**Author:** CTO Chat (Claude Sonnet 4.6)
**Status:** IMPLEMENTED in Wave 16A02

---

## CONTEXT

MIHOS is a social network. A single MIHOS project will have:

```
Traveller nodes:       millions
Place nodes:           millions
Moment/Imprint nodes:  hundreds of millions
Story nodes:           tens of millions
Interaction edges:     billions+
```

Current GoBP ID design (`flow:verify_gate`, `dec:d001`) works for dev knowledge graphs (~10K nodes) but will not scale to millions of nodes per type.

This spec defines the ID strategy that works from day 1 to billion-scale.

---

## DESIGN PRINCIPLES

1. **Internal ID** — for database operations (fast joins, compact storage)
2. **External ID** — for human + AI reference (readable, queryable, grouped)
3. **Group namespace** — logical grouping of node types (flexible per domain)
4. **Sequence** — deterministic, sortable, collision-proof at scale

---

## INTERNAL ID (Database Key)

### Format
```
BIGINT AUTO_INCREMENT (unsigned, 8 bytes)
Range: 1 → 9,223,372,036,854,775,807 (9.2 × 10^18)
```

### Why BIGINT not UUID
```
UUID (16 bytes):
  ✅ Globally unique
  ❌ Random → index fragmentation at scale
  ❌ 16 bytes vs 8 bytes → 2x storage for FK references
  ❌ Not sortable by creation time

BIGINT (8 bytes):
  ✅ Sequential → excellent index performance
  ✅ Compact → 8 bytes, fast joins
  ✅ Sortable by creation time
  ✅ Human-debuggable
  ❌ Not globally unique (fine for single DB, use snowflake for distributed)
```

### For distributed scale (future)
```
Snowflake ID (64-bit):
  - 41 bits timestamp (milliseconds since epoch)
  - 10 bits machine/shard ID
  - 12 bits sequence per millisecond
  → 4096 IDs/ms per shard
  → Sortable, globally unique, 8 bytes
  → Used by Twitter, Discord, Instagram
```

### PostgreSQL schema
```sql
CREATE TABLE nodes (
    internal_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id  TEXT NOT NULL,           -- human-readable reference
    project_id   UUID NOT NULL,           -- tenant isolation
    group_ns     TEXT NOT NULL,           -- group namespace
    type         TEXT NOT NULL,           -- NodeType
    name         TEXT NOT NULL DEFAULT '',
    status       TEXT DEFAULT 'ACTIVE',
    priority     TEXT DEFAULT 'medium',
    priority_score INTEGER DEFAULT 0,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    revision     INTEGER DEFAULT 1,
    data         JSONB,                   -- all other fields
    fts_vector   tsvector GENERATED ALWAYS AS (
        to_tsvector('english',
            coalesce(external_id,'') || ' ' ||
            coalesce(name,'') || ' ' ||
            coalesce(data::text,''))
    ) STORED
);

-- Indexes
CREATE UNIQUE INDEX idx_nodes_external ON nodes(project_id, external_id);
CREATE INDEX idx_nodes_type ON nodes(project_id, type);
CREATE INDEX idx_nodes_group ON nodes(project_id, group_ns);
CREATE INDEX idx_nodes_priority ON nodes(project_id, priority_score DESC);
CREATE INDEX idx_nodes_fts ON nodes USING GIN(fts_vector);
CREATE INDEX idx_nodes_created ON nodes(project_id, created_at DESC);

CREATE TABLE edges (
    internal_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id   UUID NOT NULL,
    from_internal BIGINT NOT NULL REFERENCES nodes(internal_id),
    to_internal   BIGINT NOT NULL REFERENCES nodes(internal_id),
    from_external TEXT NOT NULL,          -- denormalized for fast lookup
    to_external   TEXT NOT NULL,          -- denormalized for fast lookup
    type         TEXT NOT NULL,
    reason       TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (project_id, from_internal, type, to_internal)
);

CREATE INDEX idx_edges_from ON edges(project_id, from_internal);
CREATE INDEX idx_edges_to ON edges(project_id, to_internal);
CREATE INDEX idx_edges_type ON edges(project_id, type);
```

---

## EXTERNAL ID (Human + AI Reference)

### Format
```
{group}.{type_prefix}:{sequence}

Examples:
  core.dec:0001
  core.inv:0023
  domain.traveller:000001
  domain.place:000087
  domain.moment:00000001
  ops.flow:0007
  ops.engine:0003
  infra.api:0042
  meta.session:20260416_a3f7c2
  meta.doc:DOC-07_8f9a1b
```

### Rules
```
1. group    — lowercase, alphanumeric, 3-8 chars
2. type_prefix — lowercase, 2-12 chars (from schema)
3. sequence — zero-padded based on expected scale:
   < 10K items:    4 digits (0001-9999)
   < 1M items:     6 digits (000001-999999)
   < 100M items:   8 digits (00000001-99999999)
   < 10B items:    10 digits (0000000001-9999999999)

Special formats:
  Session: meta.session:YYYYMMDD_XXXXXX (date + 6-char hash)
  Document: meta.doc:{slug}_{md5[:6]}
  Wave: meta.wave:YYYYMMDD_NNN
```

### Sequence generation
```python
def generate_external_id(group: str, type_prefix: str, scale: str = "medium") -> str:
    """Generate collision-proof external ID.
    
    scale options:
      small:  4 digits  (< 10K)
      medium: 6 digits  (< 1M)  ← default
      large:  8 digits  (< 100M)
      huge:   10 digits (< 10B)
    """
    import uuid
    padding = {"small": 4, "medium": 6, "large": 8, "huge": 10}[scale]
    # Use random component for collision-proof generation
    # In production: use DB sequence or Snowflake ID
    seq = int(uuid.uuid4().hex[:padding], 16) % (10 ** padding)
    return f"{group}.{type_prefix}:{seq:0{padding}d}"
```

---

## GROUP NAMESPACES

Groups are domain-specific. Default groups for MIHOS:

### core — System fundamentals
```
Types: Decision, Invariant, Concept
Prefix mapping:
  Decision  → core.dec
  Invariant → core.inv
  Concept   → core.con

Examples:
  core.dec:0001  — "Use Email OTP for authentication"
  core.inv:0001  — "OTP expires after 5 minutes"
  core.con:0001  — "Test taxonomy"

Scale: hundreds (< 10K), 4-digit sequence
```

### domain — Business entities
```
Types: Traveller, Place, Moment, Story, Heritage (MIHOS-specific)
       Entity (generic)
Prefix mapping:
  Traveller → domain.traveller
  Place     → domain.place
  Moment    → domain.moment
  Story     → domain.story
  Entity    → domain.entity

Examples:
  domain.traveller:000001
  domain.place:000087
  domain.moment:00000001

Scale: millions to hundreds of millions, 6-10 digit sequence
```

### ops — Product operations
```
Types: Flow, Engine, Feature, Screen
Prefix mapping:
  Flow    → ops.flow
  Engine  → ops.engine
  Feature → ops.feat
  Screen  → ops.screen

Examples:
  ops.flow:0007   — "F7: TrustGate"
  ops.engine:0003 — "EmberEngine"
  ops.feat:0042   — "Proof of Presence"

Scale: hundreds to thousands, 4-digit sequence
```

### infra — Technical infrastructure
```
Types: APIEndpoint, Repository, DBTable, Config
Prefix mapping:
  APIEndpoint → infra.api
  Repository  → infra.repo
  DBTable     → infra.db
  Config      → infra.cfg

Examples:
  infra.api:0015
  infra.repo:0003

Scale: hundreds, 4-digit sequence
```

### test — Quality assurance
```
Types: TestKind, TestCase
Prefix mapping:
  TestKind → test.kind
  TestCase → test.case

Examples:
  test.kind:0001  — "Unit"
  test.case:0042  — "auth_otp_valid"

Scale: thousands, 4-digit sequence
```

### meta — Metadata and process
```
Types: Session, Wave, Document, Lesson
Prefix mapping:
  Session  → meta.session
  Wave     → meta.wave
  Document → meta.doc
  Lesson   → meta.lesson
  Idea     → meta.idea
  Node     → meta.node (generic)

Examples:
  meta.session:20260416_a3f7c2
  meta.wave:20260415_001
  meta.doc:DOC-07_8f9a1b
  meta.lesson:0023

Scale: thousands, special format for session/doc
```

---

## GROUP CONFIG IN .gobp/config.yaml

Projects can customize groups — not hard-coded:

```yaml
# .gobp/config.yaml
schema_version: "3.0"
project_name: "MIHOS"

id_groups:
  core:
    description: "Architectural decisions and hard constraints"
    types: [Decision, Invariant, Concept]
    sequence_scale: small    # 4 digits
    tier_weight: 20

  domain:
    description: "Business domain entities"
    types: [Traveller, Place, Moment, Story, Entity]
    sequence_scale: huge     # 10 digits
    tier_weight: 10

  ops:
    description: "Product operations — flows, engines, features"
    types: [Flow, Engine, Feature, Screen]
    sequence_scale: small    # 4 digits
    tier_weight: 8

  infra:
    description: "Technical infrastructure"
    types: [APIEndpoint, Repository, DBTable]
    sequence_scale: small
    tier_weight: 3

  test:
    description: "Quality assurance"
    types: [TestKind, TestCase]
    sequence_scale: medium   # 6 digits
    tier_weight: 2

  meta:
    description: "Process metadata"
    types: [Session, Wave, Document, Lesson, Idea, Node]
    sequence_scale: medium
    tier_weight: 0
```

---

## QUERY IMPROVEMENTS WITH GROUPS

```
Current:
  find:Decision auth       → search all Decision nodes
  find:Flow verify         → search all Flow nodes

With groups:
  find:core.* auth         → search all core group nodes
  find:core.dec auth       → search only Decisions
  find:ops.* verify        → search all ops group nodes
  find:domain.place hanoi  → search Places named "hanoi"

Group-level stats:
  gobp(query="overview: group=domain")
  → stats only for domain group
  → {traveller: 1M, place: 500K, moment: 50M}

Group-level priority:
  recompute: priorities group=ops
  → only recompute ops nodes
```

---

## MIGRATION PLAN (Updated after Wave 16A02)

### Phase 1 — Legacy (Wave 0-16A01)
```
Legacy text IDs were used:
  "flow:verify_gate", "dec:d001", "session:YYYY-MM-DD_xxx"
```

### Phase 2 — Implemented in Wave 16A02
```
- Added Snowflake-based ID generator (`gobp/core/snowflake.py`)
- Added group namespace config and external ID generation (`gobp/core/id_config.py`)
- Added migration script (`gobp/core/migrate_ids.py`)
- Migrated existing .gobp nodes/edges to new ID format
- Saved `.gobp/id_mapping.json` for backward compatibility
- Legacy IDs still resolve via GraphIndex lookup
```

### Phase 3 — Production MIHOS (next)
```
Full migration to new ID format
Old IDs deprecated (warn in responses)
domain.* nodes for MIHOS runtime data
Snowflake IDs for distributed writes
```

---

## IMPLEMENTATION NOTES

### parse_query() update needed
```python
# New external ID format in queries:
"get: core.dec:0001"          → node_id="core.dec:0001"
"find:domain.place hanoi"     → group="domain", type="place", query="hanoi"
"edge: ops.flow:0007 --implements--> core.inv:0001"

# Backward compat: old format still works
"get: node:pop_protocol"      → resolves via legacy lookup
"find:Decision auth"          → type="Decision", no group filter
```

### _normalize_type() update
```python
# Add group-aware normalization:
def normalize_ref(ref: str) -> tuple[str, str, str]:
    """Parse 'group.type:seq' → (group, type, seq)"""
    if "." in ref and ":" in ref:
        group, rest = ref.split(".", 1)
        type_prefix, seq = rest.split(":", 1)
        return group, type_prefix, seq
    # Legacy format
    return "", ref.split(":")[0], ref.split(":", 1)[1] if ":" in ref else ref
```

### gobp_overview update
```python
# Group-based stats:
{
  "stats": {
    "total_nodes": 206,
    "by_group": {
      "core":   {"count": 15, "types": ["Decision", "Invariant"]},
      "domain": {"count": 45, "types": ["Entity", "Flow"]},
      "ops":    {"count": 28, "types": ["Flow", "Engine", "Feature"]},
      "meta":   {"count": 118, "types": ["Session", "Document"]}
    }
  }
}
```

---

## IMPLEMENTATION DECISIONS (Resolved)

Wave 16A02 implementation chose:

- Snowflake for internal sequence generation in external IDs
- Group config in `.gobp/config.yaml` (`id_groups`)
- Migration of existing `.gobp` nodes and edges
- Backward compatibility via `legacy_id` and `.gobp/id_mapping.json`

---

*ID Design Spec v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-16*
*Status: IMPLEMENTED in Wave 16A02*

◈
