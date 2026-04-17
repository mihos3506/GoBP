# WAVE 16A09 BRIEF — BATCH OPS + EXPLORE + SUGGEST + TEMPLATE

**Wave:** 16A09
**Title:** batch action, explore, suggest, template — unified data ops
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-17
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 8 tasks
**Estimated effort:** 6-8 hours

---

## CONTEXT

GoBP nhập liệu quá tốn token, query quá nhiều bước, AI không tìm được node reusable, không có chuẩn sửa/xóa hàng loạt.

**Trước Wave 16A09:**
```
Import 30 engines:  60+ calls, 30,000+ tokens
Query 1 node:       3+ calls (find + get + related)
Tìm node reusable:  Không thể
Sửa 10 nodes:       10 calls riêng lẻ
Xóa edge sai type:  Không có action
```

**Sau Wave 16A09:**
```
Import 30 engines:  1 call, ~2,000 tokens
Query 1 node:       1 call (explore)
Tìm node reusable:  1 call (suggest)
Sửa 10 + xóa 5:    1 call (batch)
Đổi edge type:      1 line trong batch
```

---

## DESIGN

### 1. template: — Input frame per type

```
gobp(query="template: Engine")
→ {
    type: "Engine", group: "ops",
    frame: {required: {name, description}, optional: {category, input, output}},
    batch_format: "create: Engine: {name} | {description}",
    hint: "Use batch to create multiple"
  }
```

### 2. explore: — Node + edges + duplicates, 1 call

```
gobp(query="explore: TrustGate")
→ {
    node: {id, type, name, description, priority},
    edges: [
      {dir:"out", type:"implements", node:{id,name,type}},
      {dir:"in",  type:"depends_on", node:{id,name,type}}
    ],
    also_found: [{id, name, note:"potential duplicate"}]
  }
```

### 3. suggest: — Find reusable nodes by context

```
gobp(query="suggest: Payment Flow")
→ {
    suggestions: [
      {id, type:"Engine", name:"EmberEngine", why:"keyword: payment", relevance:"high"},
      {id, type:"Entity", name:"EarningLedger", why:"keyword: payment, ledger", relevance:"high"}
    ]
  }
```

### 4. batch — Unified data operations (10 op types)

**Format:**
```
batch session_id='x' ops='
  create: Engine: TrustGate | Trust scoring
  create: Flow: Verify Gate | GPS verification
  update: trustgate.ops.00000001 description=Updated
  update: trustgate.ops.00000001 category=identity
  replace: old.meta.00000001 type=Engine name=New description=Full replace
  retype: wrong.meta.00000002 new_type=Engine
  delete: garbage.meta.00000003
  merge: keep=trustgate.ops.06043392 absorb=trustgate.meta.53299456
  edge+: TrustGate --depends_on--> CacheEngine
  edge-: TrustGate --relates_to--> CacheEngine
  edge~: TrustGate --relates_to--> GeoIntel to=depends_on
  edge*: TrustGate --implements--> Mi Hốt Standard, Mi Hốt GPS Jitter
'
```

**Operation reference:**

| Prefix | What | Validation |
|--------|------|------------|
| `create:` | `Type: Name \| Desc` — new node | Dedupe score>=80 → skip |
| `update:` | `id field=val` — partial update | Node exists, field valid |
| `replace:` | `id field=val` — full replace | Node exists, WARNING destructive |
| `retype:` | `id new_type=X` — new ID + migrate edges | Type valid, node exists |
| `delete:` | `id` — remove + cascade edges | Session/Document protected |
| `merge:` | `keep=id absorb=id` — gộp 2 nodes | Both exist, edges migrated |
| `edge+:` | `From --type--> To` — add | Both exist, type valid, idempotent |
| `edge-:` | `From --type--> To` — remove | Warning if not found |
| `edge~:` | `From --old--> To to=new` — change type | Old exists, new type valid |
| `edge*:` | `From --type--> A, B, C` — replace all | Delete old, create new |

**Limits:** Max 50 ops per call.

**Response:**
```json
{
  "ok": true,
  "summary": "create:5/6 update:3/3 edge+:8/10 merge:1/1",
  "total_ops": 22, "succeeded": 20,
  "skipped": [{"op":"create", "reason":"duplicate of trustgate.ops.06043392"}],
  "errors": [],
  "warnings": [{"op":"merge", "note":"types differ: Engine vs Node"}]
}
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 520 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 520 tests
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/core/search.py` | Add suggest_related |
| 3 | `gobp/mcp/tools/read.py` | template + explore + suggest |
| 4 | `gobp/mcp/tools/write.py` | batch executor |
| 5 | `gobp/mcp/dispatcher.py` | Routing |
| 6 | `gobp/mcp/parser.py` | PROTOCOL_GUIDE |
| 7 | `gobp/core/mutator.py` | remove_edge_from_disk, merge logic |
| 8 | `gobp/schema/core_nodes.yaml` | template reads schema |

---

# TASKS

## TASK 1 — template: action
Read schema → return required/optional fields + batch format.
File: `read.py` + `dispatcher.py` + `parser.py` PROTOCOL_GUIDE.
Commit: `Wave 16A09 Task 1: template: action — input frame per node type`

## TASK 2 — explore: action
1 call = node + edges (skip discovered_in) + also_found.
File: `read.py` + `dispatcher.py` + `parser.py`.
Commit: `Wave 16A09 Task 2: explore: action — node + edges + duplicates in 1 call`

## TASK 3 — suggest: action + suggest_related()
Keyword overlap scoring. Session/Document excluded.
File: `search.py` + `read.py` + `dispatcher.py` + `parser.py`.
Commit: `Wave 16A09 Task 3: suggest: action — find reusable nodes by context`

## TASK 4 — batch_parser.py
Parse 10 op types: create/update/replace/delete/retype/merge/edge+/-/~/\*.
File: `gobp/mcp/batch_parser.py` (new).
Commit: `Wave 16A09 Task 4: batch_parser.py — parse all batch operation formats`

## TASK 5 — batch executor + remove_edge_from_disk
Execute parsed ops with validation + dedupe.
File: `write.py` + `mutator.py` (remove_edge_from_disk) + `dispatcher.py` + `parser.py`.
Commit: `Wave 16A09 Task 5: batch action — 10 op types unified executor`

## TASK 6 — Smoke test
Template + batch create/dedupe/edge + explore + suggest + update + delete + merge.
All on temp project.
Commit: `Wave 16A09 Task 6: smoke test — all 4 new actions verified`

## TASK 7 — Tests
File: `tests/test_wave16a09.py` (~26 tests).
Template(3) + Explore(3) + Suggest(3) + Parser(5) + Executor(6) + Edge ops(3) + Integration(2) + Protocol(1).
Commit: `Wave 16A09 Task 7: tests/test_wave16a09.py — 26 tests`

## TASK 8 — CHANGELOG + full suite
CHANGELOG Wave 16A09 entry. Expected: 546+ tests.
Commit: `Wave 16A09 Task 8: CHANGELOG + full suite 546+ tests`

---

# CEO DISPATCH

## Cursor
```
Read .cursorrules and waves/wave_16a09_brief.md.
Read gobp/core/search.py, gobp/mcp/tools/read.py, write.py, dispatcher.py, parser.py, mutator.py.
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute 8 tasks. R9: 520 tests baseline. 1 task = 1 commit.
```

## Claude CLI audit
```
Audit Wave 16A09.
Task 1: template: returns frame + batch_format
Task 2: explore: node + edges + also_found, no discovered_in
Task 3: suggest: keyword overlap, excludes Session/Document
Task 4: batch_parser.py: 10 op types parsed
Task 5: batch: create+dedupe, update, delete, merge, edge+/-/~/*, remove_edge_from_disk
Task 6: Smoke passes
Task 7: ~26 tests
Task 8: CHANGELOG, 546+ total
BLOCKING: Gặp vấn đề → DỪNG, báo CEO.
Expected: 546+ tests.
```

---

*Wave 16A09 Brief v2.0 — 2026-04-17*

◈
