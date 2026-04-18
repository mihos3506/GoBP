# WAVE 17A SERIES — GoBP v2 REWRITE PLAN

**Date:** 2026-04-19
**Author:** CTO Chat
**Status:** APPROVED

---

## TẠI SAO REWRITE

GoBP v1 schema được thiết kế từ brainstorm — không theo chuẩn phần mềm.
Migrate = technical debt chồng chất. Rewrite Option B = sạch, đúng chuẩn.

**Giữ lại (Option B):**
```
✅ File-first pattern (.gobp/ folder structure)
✅ YAML/Markdown format
✅ MCP server skeleton (server.py, dispatcher.py)
✅ CLI structure
✅ Batch parser pattern
✅ Session/history pattern (append-only)
✅ Wave Brief process
✅ AGENTS.md, .cursorrules, CLAUDE.md
```

**Rewrite hoàn toàn:**
```
❌ core_nodes.yaml → schema v2.1 (60+ types, group field)
❌ core_edges.yaml → thêm reason field
❌ Node/edge file format → group, description.info/code, lifecycle/read_order
❌ ID format → group-embedded human-readable
❌ GraphIndex → support group queries
❌ Query engine → top-down + bottom-up group queries
❌ Display engine → brief/full/debug modes
❌ Validation engine → Invariant rules, description.info required
❌ TYPE_DEFAULTS → schema mới
❌ All tests → rewrite cho schema mới
```

---

## ID FORMAT MỚI

```
Format: {group_slug}.{name_slug}.{8hex}

Ví dụ:
  dev.domain.entity.traveller.a1b2c3d4
  dev.infra.security.authflow.otp.b2c3d4e5
  dev.infra.api.endpoint.mihot_create.c3d4e5f6
  doc.spec.doc03.d4e5f6a7
  doc.decision.gps_proof.e5f6a7b8
  constraint.invariant.balance_nonneg.f6a7b8c9
  error.case.gps001.a7b8c9d0
  test.case.mihot_unit_001.b8c9d0e1
  meta.session.2026_04_19.c9d0e1f2
```

---

## NODE FILE FORMAT MỚI

```yaml
# .gobp/nodes/dev.domain.entity.traveller.a1b2c3d4.yaml
id: dev.domain.entity.traveller.a1b2c3d4
name: Traveller
type: Entity
group: "Dev > Domain > Entity"
lifecycle: specified
read_order: foundational

description:
  info: |
    Core user của MIHOS. Có identity, profile,
    GPS history, Ember balance, Moments collection.
    Traveller là người thực hiện MiHot action.
  code: |
    class Traveller {
      final String id;
      final GpsCoordinate lastLocation;
      final EmberAmount balance;
    }

relationships:
  - target: doc.spec.doc03.d4e5f6a7
    type: specified_in
    reason: "Traveller được định nghĩa đầy đủ trong DOC-03 section 2"
  - target: dev.domain.aggregate.place.e5f6a7b8
    type: relates_to
    reason: "Traveller MiHot tại Place — core relationship"

tags: []
created_at: 2026-04-19T00:00:00Z
session_id: meta.session.2026_04_19.c9d0e1f2
```

---

## EDGE FILE FORMAT MỚI

```yaml
# .gobp/edges/relations.yaml
- from: dev.domain.entity.traveller.a1b2c3d4
  to:   doc.spec.doc03.d4e5f6a7
  type: specified_in
  reason: "Traveller entity được mô tả đầy đủ trong DOC-03"
  created_at: 2026-04-19T00:00:00Z
```

---

## WAVE BREAKDOWN — 7 WAVES

```
17A01: Schema + File Format    (3-4 days)
17A02: Core Engine Rewrite     (4-5 days)
17A03: Query Engine            (3-4 days)
17A04: Display + Get Modes     (2-3 days)
17A05: Validation + Hooks      (3-4 days)
17A06: Tests Rewrite           (4-5 days)
17A07: Docs + Agents + MIHOS   (3-4 days)

Total: ~3-4 weeks
```

---

## WAVE 17A01: SCHEMA + FILE FORMAT

**Scope:**
- Rewrite `gobp/schema/core_nodes.yaml` — 60+ types, group field
- Rewrite `gobp/schema/core_edges.yaml` — reason field
- New node file format (YAML với group, description.info/code)
- New ID generator (group-embedded)
- Backward compat: old IDs still readable

**Key outputs:**
- `gobp/schema/core_nodes.yaml` v2
- `gobp/schema/core_edges.yaml` v2
- `gobp/core/id_generator.py` — new ID format
- `gobp/core/file_format.py` — new node/edge file serialization
- Tests: schema validation tests

---

## WAVE 17A02: CORE ENGINE REWRITE

**Scope:**
- Rewrite `gobp/core/graph.py` — GraphIndex v2
- Group-aware indexing: index by full group path
- Support top-down: `find group="Dev > Infrastructure"`
- Support bottom-up: `explore` returns group path + siblings
- AdjacencyIndex: keep, adapt for new ID format
- InvertedIndex: keep, add group field indexing

**Key outputs:**
- `gobp/core/graph.py` v2
- `gobp/core/indexes.py` v2 (adapted)
- Tests: group query tests

---

## WAVE 17A03: QUERY ENGINE

**Scope:**
- `find:` — thêm group filter (exact, prefix, contains)
- `explore:` — show group path + siblings
- `related:` — show relationships với reason
- `suggest:` — group-aware suggestions
- `template:` — templates theo schema mới

**find: group query examples:**
```
find: group="Dev"                      → all Dev nodes
find: group="Dev > Infrastructure"     → all infra nodes
find: group contains "Security"        → all security nodes
find: type=Entity                      → by type (backward compat)
find: group="Dev > Domain" type=Entity → combined filter
```

**Key outputs:**
- `gobp/mcp/tools/read.py` v2
- Tests: query tests

---

## WAVE 17A04: DISPLAY + GET MODES

**Scope:**
- `get: mode=brief` — name, group, description.info, relationships (với reason)
- `get: mode=full` — tất cả meaningful fields
- `get: mode=debug` — tất cả kể cả raw
- Ẩn raw fields trong brief/full
- `overview:` — show group hierarchy summary

**Key outputs:**
- `gobp/mcp/tools/read.py` — display modes
- Tests: display mode tests

---

## WAVE 17A05: VALIDATION + HOOKS

**Scope:**
- Rewrite validation engine cho schema v2.1
- Invariant: rule + scope + enforcement + violation_action REQUIRED
- description.info REQUIRED
- group REQUIRED (hoặc auto-infer từ type)
- Rewrite `gobp/mcp/hooks.py`
- before_write: validate group, description.info, Invariant fields
- on_error: actionable suggestions với schema v2.1

**Key outputs:**
- `gobp/core/validator.py` v2
- `gobp/mcp/hooks.py` v2
- Tests: validation tests

---

## WAVE 17A06: TESTS REWRITE

**Scope:**
- Rewrite tất cả tests cho schema v2.1
- Test file format mới
- Test group queries
- Test display modes
- Test validation rules
- Performance tests với schema mới
- Target: 600+ tests

**Key outputs:**
- `tests/` — full rewrite
- `tests/test_schema_v2.py`
- `tests/test_group_queries.py`
- `tests/test_display_modes.py`
- `tests/test_validation_v2.py`

---

## WAVE 17A07: DOCS + AGENTS + MIHOS

**Scope:**
- Cursor tự update `.cursorrules`
- Claude CLI tự update `CLAUDE.md`
- Update `GoBP_AI_USER_GUIDE.md`
- Update `IMPORT_CHECKLIST.md`
- MIHOS clean import với schema v2.1
- ~30 Invariants đúng chuẩn OCL
- Không import "KHÔNG được X" là Invariant

**Key outputs:**
- Updated agent docs
- MIHOS GoBP clean, đúng schema v2.1

---

*Wave 17A Series Plan v1.0 — 2026-04-19*
◈
