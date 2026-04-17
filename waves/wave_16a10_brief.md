# WAVE 16A10 BRIEF — SMART TEMPLATE + COMPACT RESPONSES + AI QUERY RULES

**Wave:** 16A10
**Title:** Template with edges, compact/verbose flag, AI query rules
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-17
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 6 tasks
**Estimated effort:** 4-5 hours

---

## CONTEXT

Wave 16A09 done — batch/explore/suggest/template có. Nhưng:

**P1 — template: chỉ trả fields, không có edges**
```
Current:  template: Engine → {required: {name, description}}
Problem:  AI không biết Engine cần edge nào
          → Tạo node xong quên tạo edges
          → Graph thưa

Need:     template: Engine → fields + suggested_edges + batch example
          AI thấy ngay: "Engine cần implements Flow, depends_on Engine"
```

**P2 — template_batch: không có**
```
Current:  AI phải tự viết batch format
Problem:  Sai format → parse fail → waste calls

Need:     template_batch: Engine count=5
          → 5 frames trống, AI điền → submit
          → Không giới hạn nodes hay edges per node
          → Nếu vượt 50 ops → hướng dẫn chia batch
```

**P3 — Response quá nặng**
```
Current:  explore: trả full description + tất cả edges
          batch: trả full created list
Problem:  Token waste khi AI chỉ cần confirmation

Need:     compact=true flag
          explore: compact → id, name, type, edge_count only
          batch: compact → summary + errors only
```

**P4 — AI không có rules dùng GoBP hiệu quả**
```
Current:  Mỗi AI tự đoán cách query
Problem:  Query rộng, paste JSON thừa, gọi overview: mỗi lần

Need:     GoBP QUERY RULES trong PROTOCOL_GUIDE
          AI đọc 1 lần → biết workflow chuẩn
```

---

## DESIGN

### 1. template: with suggested edges

```
gobp(query="template: Engine")
→ {
    type: "Engine",
    group: "ops",
    frame: {
      required: {name, description},
      optional: {category, input, output}
    },
    suggested_edges: [
      {type: "implements", target_types: ["Flow"], note: "What flows does this engine power?"},
      {type: "depends_on", target_types: ["Engine", "Entity"], note: "What does this engine need?"},
      {type: "tested_by", target_types: ["TestCase"], note: "What tests validate this engine?"},
      {type: "enforces", target_types: ["Invariant"], note: "What rules does this engine enforce?"}
    ],
    batch_example:
      "create: Engine: TrustGate | Trust scoring\n"
      "edge+: TrustGate --implements--> Mi Hốt Standard\n"
      "edge+: TrustGate --depends_on--> CacheEngine"
  }
```

Edge suggestions come from `core_edges.yaml` — edges where this type is valid `from_type` or `to_type`.

### 2. template_batch: — Multi-node template

```
gobp(query="template_batch: Engine count=3")
→ {
    type: "Engine",
    count: 3,
    frame_per_node: {required: {name, description}, optional: {category}},
    batch_template:
      "create: Engine: {name_1} | {description_1}\n"
      "edge+: {name_1} --implements--> {flow_name}\n"
      "edge+: {name_1} --depends_on--> {engine_name}\n"
      "\n"
      "create: Engine: {name_2} | {description_2}\n"
      "edge+: {name_2} --implements--> {flow_name}\n"
      "edge+: {name_2} --depends_on--> {engine_name}\n"
      "\n"
      "create: Engine: {name_3} | {description_3}\n"
      "edge+: {name_3} --implements--> {flow_name}\n"
      "edge+: {name_3} --depends_on--> {engine_name}",
    instructions: [
      "Replace {placeholders} with actual values",
      "Add/remove edge+ lines as needed — no limit per node",
      "Remove entire edge+ line if not applicable",
      "Submit via: batch session_id='x' ops='<filled template>'",
      "Max 50 operations per batch call",
      "If more than 50 ops: split into multiple batch calls"
    ],
    note: "count is a suggestion — add or remove node blocks freely"
  }
```

### 3. compact=true flag

```
# explore compact
gobp(query="explore: TrustGate compact=true")
→ {
    node: {id, name, type},
    edges: ["--implements--> Mi Hốt Standard (Flow)", "--depends_on--> CacheEngine (Engine)"],
    edge_count: 5,
    also_found: ["trustgate.meta.53299456 (Node) — potential duplicate"]
  }
→ ~200 tokens vs ~800 tokens full

# explore full (default)
gobp(query="explore: TrustGate")
→ Full response with descriptions, priority, nested objects

# batch compact (default for batch)
gobp(query="batch ... ops='...'")
→ {summary: "create:5/6 edge+:8/10", errors: [...]}
→ ~100 tokens

# batch verbose
gobp(query="batch ... ops='...' verbose=true")
→ Full created/skipped/warnings lists
```

### 4. AI Query Rules in PROTOCOL_GUIDE

```python
QUERY_RULES = """
GoBP QUERY RULES — follow these to minimize tokens:

1. overview:        Call once at session start. Never call again same session.
2. template:        Call once per type before creating nodes of that type.
3. template_batch:  When creating multiple nodes of same type.
4. suggest:         Before creating any new node — check reusable nodes exist.
5. explore:         Instead of find+get+related. Use compact=true for quick check.
6. batch:           For ALL create/update/delete/edge operations. Never single create:.
7. find/get:        Default mode=summary. Only mode=full when debugging.
8. After getting IDs: Keep only id+name. Do NOT paste full JSON into next prompt.
9. 1 session = 1 goal. session:end when done.
10. Errors:         If batch returns errors, fix and retry only failed ops.
"""
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 548 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 548 tests
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/mcp/tools/read.py` | Update template + explore |
| 3 | `gobp/mcp/dispatcher.py` | Add template_batch routing |
| 4 | `gobp/mcp/parser.py` | PROTOCOL_GUIDE + QUERY_RULES |
| 5 | `gobp/schema/core_edges.yaml` | Read edge types for suggested_edges |
| 6 | `gobp/schema/core_nodes.yaml` | Read node types for template |

---

# TASKS

## TASK 1 — template: add suggested_edges

**Goal:** template: returns suggested edges based on core_edges.yaml.

**File to modify:** `gobp/mcp/tools/read.py`

Update `template_action()`:

```python
# After building frame, add suggested edges
edges_schema = index._edges_schema
suggested_edges = []

for edge_name, edge_def in edges_schema.get("edge_types", {}).items():
    if edge_name == "discovered_in":
        continue  # skip metadata edge
    
    from_types = edge_def.get("from_types", [])
    to_types = edge_def.get("to_types", [])
    
    # This type can be source
    if not from_types or node_type in from_types or "Node" in from_types:
        suggested_edges.append({
            "type": edge_name,
            "direction": "outgoing",
            "target_types": to_types if to_types else ["any"],
            "note": edge_def.get("description", ""),
        })
    
    # This type can be target
    if not to_types or node_type in to_types or "Node" in to_types:
        # Check if already added as outgoing
        if not any(s["type"] == edge_name and s["direction"] == "outgoing" for s in suggested_edges):
            suggested_edges.append({
                "type": edge_name,
                "direction": "incoming",
                "from_types": from_types if from_types else ["any"],
                "note": edge_def.get("description", ""),
            })

result["suggested_edges"] = suggested_edges

# Update batch_example to include edge lines
result["batch_example"] = (
    f"create: {node_type}: ExampleName | Short description\n"
    + "\n".join(
        f"edge+: ExampleName --{e['type']}--> TargetName"
        for e in suggested_edges[:3] if e["direction"] == "outgoing"
    )
)
```

**Commit message:**
```
Wave 16A10 Task 1: template: returns suggested_edges from core_edges.yaml

- Suggested edges based on edge schema from_types/to_types
- batch_example includes edge+ lines
- AI knows what edges to create with each node type
```

---

## TASK 2 — template_batch: action

**Goal:** Generate fillable batch template for N nodes of a type.

**File to modify:** `gobp/mcp/tools/read.py`

Add `template_batch_action()`:

```python
async def template_batch_action(index, project_root, args):
    """Generate batch template for N nodes of a type.
    
    Query: template_batch: Engine count=5
    Returns: fillable template with placeholders + instructions
    """
    node_type = args.get("query", "").strip() or args.get("type", "")
    count = int(args.get("count", 3))
    
    # Get template for this type first
    template_result = await template_action(index, project_root, {"query": node_type})
    if not template_result.get("ok"):
        return template_result
    
    suggested_edges = template_result.get("suggested_edges", [])
    outgoing_edges = [e for e in suggested_edges if e.get("direction") == "outgoing"]
    
    # Build template blocks
    blocks = []
    for i in range(1, count + 1):
        block_lines = [f"create: {node_type}: {{name_{i}}} | {{description_{i}}}"]
        for edge in outgoing_edges[:5]:  # show top 5 edge suggestions
            block_lines.append(
                f"edge+: {{name_{i}}} --{edge['type']}--> {{target_name}}"
            )
        blocks.append("\n".join(block_lines))
    
    batch_template = "\n\n".join(blocks)
    
    return {
        "ok": True,
        "type": node_type,
        "count": count,
        "frame_per_node": template_result.get("frame", {}),
        "batch_template": batch_template,
        "instructions": [
            "Replace {placeholders} with actual values",
            "Add or remove edge+ lines freely — no limit per node",
            "Remove entire edge+ line if not applicable",
            "Add or remove node blocks — count is a suggestion",
            f"Submit via: batch session_id='x' ops='<filled template>'",
            "Max 50 operations per batch call",
            "If more than 50 ops: split into multiple batch calls, each with own session_id",
        ],
        "note": f"Generated {count} blocks. Adjust freely — no hard limits on nodes or edges.",
    }
```

**Add dispatcher routing:**
```python
        elif action == "template_batch":
            result = await tools_read.template_batch_action(index, project_root, params)
```

**Update PROTOCOL_GUIDE:**
```python
"template_batch: Engine count=5":   "Fillable batch template for 5 engines with edge suggestions",
"template_batch: Flow":             "Fillable batch template for flows (default count=3)",
```

**Commit message:**
```
Wave 16A10 Task 2: template_batch: — fillable multi-node template

- Generates N node blocks with edge suggestions
- No hard limit on nodes or edges per node
- Instructions for splitting large batches
- AI fills placeholders → batch submit
```

---

## TASK 3 — compact=true flag for explore/batch/find/get

**Goal:** All read actions support compact=true for minimal token response.

**File to modify:** `gobp/mcp/tools/read.py`

**explore_action compact mode:**
```python
compact = args.get("compact", "false").lower() == "true"

if compact:
    return {
        "ok": True,
        "node": {"id": node_id, "name": best_node.get("name",""), "type": best_node.get("type","")},
        "edges": [
            f"--{e['type']}--> {e['node']['name']} ({e['node']['type']})" if e['dir'] == 'out'
            else f"<--{e['type']}-- {e['node']['name']} ({e['node']['type']})"
            for e in edges
        ],
        "edge_count": len(edges),
        "also_found": [
            f"{n['id']} ({n['type']}) — {n.get('note','')}" for n in also_found
        ],
    }
```

**batch_action default compact:**
```python
# batch already returns summary by default
# Add verbose=true for full details
verbose = args.get("verbose", "false").lower() == "true"

if not verbose:
    # Remove created list from response, keep only summary + errors + skipped
    result.pop("succeeded_details", None)
```

**find/get compact:**
```python
# find: compact=true → only id, name, type per match
# get: compact=true → only id, name, type, edge_count
```

**Commit message:**
```
Wave 16A10 Task 3: compact=true flag for explore/batch/find/get

- explore compact: edges as strings, ~200 tokens vs ~800
- batch: summary by default, verbose=true for full details
- find/get compact: id+name+type only
- AI uses compact=true for quick checks, full for deep analysis
```

---

## TASK 4 — AI Query Rules in PROTOCOL_GUIDE

**Goal:** Add QUERY_RULES to PROTOCOL_GUIDE so every AI reads them.

**File to modify:** `gobp/mcp/parser.py`

Add `QUERY_RULES` constant:

```python
QUERY_RULES = {
    "rules": [
        "1. overview: — call ONCE at session start. Never again same session.",
        "2. template: — call once per type BEFORE creating nodes.",
        "3. template_batch: — when creating multiple nodes of same type.",
        "4. suggest: — BEFORE creating any new node. Check reusable nodes.",
        "5. explore: — instead of find+get+related. Use compact=true for quick check.",
        "6. batch — for ALL write operations. Never single create:/update:/edge:.",
        "7. find/get — default mode=summary. Only mode=full when debugging.",
        "8. After getting IDs — keep only id+name in next prompt. No full JSON.",
        "9. 1 session = 1 goal. session:end when done.",
        "10. Errors — if batch returns errors, fix and retry ONLY failed ops.",
    ],
    "token_guide": {
        "explore compact": "~200 tokens",
        "explore full": "~800 tokens",
        "find mode=summary": "~400 tokens for 20 results",
        "find mode=full": "~2000 tokens for 20 results",
        "batch response": "~100 tokens (summary only)",
        "batch verbose": "~500+ tokens (full details)",
        "template": "~300 tokens",
        "suggest": "~400 tokens for 10 suggestions",
    },
}
```

**Include QUERY_RULES in overview: response:**
```python
# In gobp_overview(), add:
result["query_rules"] = QUERY_RULES["rules"]
# Only on first call or when AI explicitly requests
```

**Better: include in PROTOCOL_GUIDE so AI reads once:**
```python
PROTOCOL_GUIDE["query_rules"] = QUERY_RULES["rules"]
PROTOCOL_GUIDE["token_guide"] = QUERY_RULES["token_guide"]
```

**Commit message:**
```
Wave 16A10 Task 4: AI Query Rules in PROTOCOL_GUIDE

- 10 rules for efficient GoBP usage
- Token guide per action
- AI reads once via overview: or PROTOCOL_GUIDE
- Reduces token waste by 50-70%
```

---

## TASK 5 — Smoke test + Tests

**File to create:** `tests/test_wave16a10.py`

```python
"""Tests for Wave 16A10: smart template, compact, query rules."""

# Template with edges (3):
#   template_has_suggested_edges
#   template_edges_from_schema
#   template_batch_example_has_edge_lines

# Template batch (3):
#   template_batch_returns_blocks
#   template_batch_custom_count
#   template_batch_has_instructions

# Compact mode (4):
#   explore_compact_returns_strings
#   explore_compact_smaller_than_full
#   find_compact_minimal_fields
#   get_compact_minimal_fields

# Query rules (2):
#   protocol_guide_has_query_rules
#   protocol_guide_has_token_guide

# Integration (2):
#   template_then_batch_create
#   template_batch_fill_and_submit

# Total: ~14 tests
```

**Commit message:**
```
Wave 16A10 Task 5: tests/test_wave16a10.py — 14 tests + smoke

- Template edges: 3, Template batch: 3, Compact: 4
- Query rules: 2, Integration: 2
```

---

## TASK 6 — CHANGELOG + full suite

**Update CHANGELOG.md:**

```markdown
## [Wave 16A10] — Smart Template + Compact + AI Query Rules — 2026-04-17

### Added
- **template: suggested_edges** — edge suggestions from schema per node type
  - AI sees: "Engine needs implements Flow, depends_on Engine"
  - batch_example includes edge+ lines
  
- **template_batch:** — fillable multi-node template
  - template_batch: Engine count=5 → 5 blocks with edge suggestions
  - No hard limit on nodes or edges per node
  - Instructions for splitting large batches

- **compact=true flag** — minimal token responses
  - explore compact: ~200 tokens (vs ~800 full)
  - batch: summary by default (~100 tokens)
  - find/get compact: id+name+type only

- **AI Query Rules** — 10 rules in PROTOCOL_GUIDE
  - Token guide per action type
  - "Never single create:, always batch"
  - "explore compact=true for quick checks"

### Impact
- Template with edges: AI creates nodes with correct relationships
- Compact: ~60% token reduction for read operations
- Query rules: consistent, efficient AI behavior

### Total: 562+ tests
```

**Commit message:**
```
Wave 16A10 Task 6: CHANGELOG + full suite 562+ tests
```

---

# CEO DISPATCH

## Cursor
```
Read .cursorrules and waves/wave_16a10_brief.md.
Read gobp/mcp/tools/read.py, dispatcher.py, parser.py,
gobp/schema/core_edges.yaml, core_nodes.yaml.
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute 6 tasks. R9: 548 tests baseline. 1 task = 1 commit.
```

## Claude CLI audit
```
Audit Wave 16A10.
Task 1: template: has suggested_edges from core_edges.yaml
Task 2: template_batch: generates N blocks with edge suggestions + instructions
Task 3: compact=true on explore/find/get. batch summary by default
Task 4: QUERY_RULES in PROTOCOL_GUIDE (10 rules + token guide)
Task 5: test_wave16a10.py ~14 tests
Task 6: CHANGELOG, 562+ total
BLOCKING: Gặp vấn đề → DỪNG, báo CEO.
Expected: 562+ tests.
```

---

*Wave 16A10 Brief v1.0 — 2026-04-17*

◈
