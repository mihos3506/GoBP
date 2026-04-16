# WAVE 16A01 BRIEF — RESPONSE TIERS + METADATA LINTER + PERF FIX + PRIORITY SYSTEM

**Wave:** 16A01
**Title:** Response tier standardization, metadata linter, perf test stability, numeric priority system
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-16
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 10 atomic tasks
**Estimated effort:** 5-6 hours

---

## CONTEXT

Production testing by Cursor identified 6 improvement areas:

**I1 — Response tiers not standardized**
```
Current: find/get/related return varying payload sizes
Problem: AI loads full 500-token node when only needs name + type
Need: mode=summary|brief|full for all read actions
      summary: id, name, type, priority (~50 tokens)
      brief:   + description, key fields, edge count (~150 tokens)
      full:    full context + all edges (current behavior, ~500 tokens)
```

**I2 — Batch detail missing**
```
Current: get: one node at a time
Problem: AI needs detail on 5 nodes → 5 sequential calls
Need: get_batch: ids='a,b,c' mode=brief
```

**I3 — No metadata linter**
```
Current: nodes can be created without description/tags/spec_source
Problem: Graph degrades silently — orphan nodes with no metadata
Need: validate: metadata → score per node type, flag missing fields
```

**I4 — Performance test flaky**
```
Current: single hard cutoff (500ms) → fails under CPU contention
Evidence: node_upsert 502ms fail, rerun 3763ms (I/O spike)
Need: median of 3 runs strategy, or higher threshold with margin
```

**I5 — Numeric priority system**
```
Current: enum (critical/high/medium/low) — static, manually assigned
Problem: AI assigns priority subjectively, no graph topology signal
Need: priority = edge_count + tier_weight (0-20+ numeric scale)
      Tier weights: Protocol/Invariant=+20, Engine/Flow/Entity=+10,
                    Feature/Screen=+5, Document/TestCase=+2, Meta=+0
      Threshold: 0-4=low, 5-9=medium, 10-19=high, 20+=critical
```

**I6 — No server hints in summary**
```
Current: summary returns data but no metadata about what else is available
Need: detail_available, estimated_payload_size, edge_count in summary
      AI knows when to upgrade to brief/full
```

---

## DESIGN DECISIONS

### Response mode system

```
mode param added to: find, get, related, tests, code, invariants
Default: standard (current behavior preserved)

summary:
  Node: {id, type, name, status, priority, edge_count, detail_available}
  ~50 tokens per node
  
brief:
  Node: summary + description, tags, key fields (3-5)
  ~150 tokens per node

full:
  Node: all fields + edges + decisions (current get: behavior)
  ~500 tokens per node

Query syntax:
  find: login mode=summary
  get: node:x mode=brief
  related: node:x mode=summary page_size=20
  get_batch: ids='node:a,node:b,node:c' mode=brief
```

### Numeric priority

```python
TIER_WEIGHTS = {
    "Invariant": 20, "Decision": 15,
    "Engine": 10, "Flow": 10, "Entity": 10,
    "Feature": 5, "Screen": 5, "APIEndpoint": 5,
    "Document": 2, "TestCase": 2, "Lesson": 2,
    "Session": 0, "Wave": 0, "Repository": 0,
    "Node": 3, "Idea": 3, "Concept": 3, "TestKind": 1,
}

def compute_priority_score(node_id, index) -> int:
    incoming = len(index.get_edges_to(node_id))
    node_type = index.get_node(node_id).get("type", "Node")
    tier_weight = TIER_WEIGHTS.get(node_type, 0)
    return incoming + tier_weight

def priority_label(score: int) -> str:
    if score >= 20: return "critical"
    if score >= 10: return "high"
    if score >= 5:  return "medium"
    return "low"
```

New action: `gobp(query="recompute: priorities")` — recalculate all node priorities from graph.

### Metadata linter

```
validate: metadata checks per node:
  Required fields by type:
    Flow, Engine, Entity, Feature: description, spec_source
    Document: source_path, content_hash
    Decision: what, why, locked_by
    TestCase: kind_id, covers (edge)
    
  Returns:
    score: 0-100
    missing: [{node_id, node_type, missing_fields[]}]
    by_type: {Flow: {total:5, complete:3, score:60}, ...}
```

### Performance test strategy

```python
def _measure_median(fn, runs=3):
    """Run fn 3 times, return median latency."""
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000)
    times.sort()
    return times[len(times) // 2]
```

Thresholds bumped with 40% margin:
```
node_upsert:    500ms → 700ms
session_log:    300ms → 400ms  (already done)
gobp_overview:  100ms → 150ms
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 348 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 348 tests passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/mcp/tools/read.py` | Add mode param + batch |
| 3 | `gobp/mcp/dispatcher.py` | Add mode + get_batch + recompute |
| 4 | `gobp/core/graph.py` | Add compute_priority_score() |
| 5 | `tests/test_performance.py` | Fix flaky thresholds |
| 6 | `waves/wave_16a01_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Fix flaky performance tests

**Goal:** Stable thresholds + median strategy for node_upsert.

**File to modify:** `tests/test_performance.py`

**Re-read file in full.**

**Update MAX_MS thresholds:**

```python
MAX_MS = {
    "gobp_overview": 150.0,    # was 100ms, +50% margin
    "find": 50.0,
    "signature": 30.0,
    "context": 100.0,
    "session_recent": 50.0,
    "decisions_for": 50.0,
    "doc_sections": 30.0,
    "node_upsert": 700.0,      # was 500ms, +40% margin for I/O spikes
    "decision_lock": 200.0,
    "session_log": 400.0,      # was 300ms, already bumped
    "lessons_extract": 2000.0,
    "validate": 5000.0,
}
```

**Add median helper:**

```python
def _measure_median(call_fn, runs: int = 3) -> float:
    """Run call_fn N times, return median latency in ms."""
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        call_fn()
        times.append((time.perf_counter() - start) * 1000)
    times.sort()
    return times[len(times) // 2]
```

**Update `test_perf_node_upsert_v2` to use median:**

```python
def test_perf_node_upsert_v2(mihos_perf_root_v2: Path) -> None:
    index = _load(mihos_perf_root_v2)
    sess = tools_write.session_log(index, mihos_perf_root_v2,
        {"action": "start", "actor": "perf-test-v2", "goal": "node_upsert benchmark"})
    assert sess.get("ok") is True
    index = _load(mihos_perf_root_v2)
    session_id = str(sess["session_id"])

    def do_upsert():
        tools_write.node_upsert(index, mihos_perf_root_v2, {
            "type": "Idea",
            "name": "Performance v2 idea",
            "fields": {
                "subject": "perf:v2",
                "raw_quote": "perf test",
                "interpretation": "v2 performance benchmark node",
                "maturity": "RAW",
                "confidence": "low",
            },
            "session_id": session_id,
        })

    elapsed = _measure_median(do_upsert, runs=3)
    _assert_under_target("node_upsert", elapsed)
```

**Acceptance criteria:**
- `node_upsert` threshold = 700ms
- `gobp_overview` threshold = 150ms
- `test_perf_node_upsert_v2` uses median of 3 runs
- All 10 perf tests pass consistently

**Commit message:**
```
Wave 16A01 Task 1: fix flaky perf tests — median strategy + higher thresholds

- node_upsert: 500ms → 700ms (+40% margin for I/O spikes)
- gobp_overview: 100ms → 150ms (+50% margin)
- session_log: already 400ms — unchanged
- _measure_median(): run 3x, return median latency
- test_perf_node_upsert_v2: uses median instead of single run
```

---

## TASK 2 — Add mode param to find() and _node_summary() helper

**Goal:** `find: login mode=summary` returns lightweight nodes.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `read.py` in full.**

**Add helper functions:**

```python
def _node_summary(node: dict[str, Any], index: GraphIndex | None = None) -> dict[str, Any]:
    """Return lightweight node summary (~50 tokens)."""
    node_id = node.get("id", "")
    edge_count = len(index.get_edges_from(node_id)) + len(index.get_edges_to(node_id)) if index else 0
    return {
        "id": node_id,
        "type": node.get("type", ""),
        "name": node.get("name", ""),
        "status": node.get("status", ""),
        "priority": node.get("priority", "medium"),
        "edge_count": edge_count,
        "detail_available": True,
    }


def _node_brief(node: dict[str, Any], index: GraphIndex | None = None) -> dict[str, Any]:
    """Return brief node (~150 tokens)."""
    base = _node_summary(node, index)
    skip = {"id", "type", "name", "status", "priority", "created", "updated",
            "session_id", "x", "y", "z", "vx", "vy", "vz"}
    # Add up to 5 key fields
    extra_fields = {k: v for k, v in node.items() if k not in skip and v}
    base.update({k: v for k, v in list(extra_fields.items())[:5]})
    # Add edge count by type
    if index:
        out_types = {}
        for e in index.get_edges_from(node.get("id", "")):
            t = e.get("type", "")
            out_types[t] = out_types.get(t, 0) + 1
        if out_types:
            base["outgoing_edges"] = out_types
    return base
```

**Update `find()` to support mode:**

```python
def find(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    # ... existing search logic ...
    mode = args.get("mode", "standard")

    # Apply mode to results
    if mode == "summary":
        page = [_node_summary(n, index) for n in page]
    elif mode == "brief":
        page = [_node_brief(n, index) for n in page]
    # mode == "standard" or "full" → return full node (current behavior)

    return {
        "ok": True,
        "matches": page,
        "count": len(page),
        "mode": mode,
        "page_info": page_info,
    }
```

**Acceptance criteria:**
- `find: login mode=summary` → each match has only id/type/name/status/priority/edge_count
- `find: login mode=brief` → summary + up to 5 key fields + outgoing_edges
- `find: login` (no mode) → unchanged behavior (full node)
- `mode` field in response

**Commit message:**
```
Wave 16A01 Task 2: add mode=summary|brief|full to find()

- _node_summary(): id/type/name/status/priority/edge_count (~50 tokens)
- _node_brief(): summary + 5 key fields + edge types (~150 tokens)
- find(): mode param, default=standard (backward compatible)
- mode field in response
```

---

## TASK 3 — Add mode to get/related/tests + dispatcher

**Goal:** All list/detail read actions support mode param.

**File to modify:** `gobp/mcp/tools/read.py`

Update `context()` (get:) to support mode:

```python
def context(index, project_root, args):
    mode = args.get("mode", "full")  # get: defaults to full
    # ... existing logic ...

    if mode == "summary":
        return {"ok": True, "node": _node_summary(node, index), "mode": mode}
    elif mode == "brief":
        return {"ok": True, "node": _node_brief(node, index), "mode": mode,
                "edge_count": len(outgoing) + len(incoming)}
    # full = existing behavior
```

Update `node_related()`:

```python
def node_related(index, project_root, args):
    mode = args.get("mode", "summary")  # related: defaults to summary
    # ... existing logic ...

    def _format(neighbor_node, edge_type):
        if mode == "summary" or neighbor_node is None:
            return {"id": nid, "name": name, "type": ntype, "edge_type": edge_type}
        elif mode == "brief":
            return {**_node_summary(neighbor_node, index), "edge_type": edge_type}
        else:
            return {**neighbor_node, "edge_type": edge_type}
```

**File to modify:** `gobp/mcp/dispatcher.py`

Add `mode` param to handlers:

```python
        elif action == "find":
            # ... existing ...
            if "mode" in params:
                args["mode"] = params["mode"]

        elif action in ("get", "context"):
            node_id = params.get("query") or params.get("node_id", "")
            args = {"node_id": node_id}
            if "mode" in params:
                args["mode"] = params["mode"]
            result = tools_read.context(index, project_root, args)

        elif action == "related":
            # ... existing ...
            if "mode" in params:
                args["mode"] = params["mode"]
```

**Update PROTOCOL_GUIDE:**
```python
"find: <keyword> mode=summary":     "Lightweight results (~50 tokens/node)",
"find: <keyword> mode=brief":       "Medium results (~150 tokens/node)",
"get: <node_id> mode=brief":        "Brief node detail",
"related: <node_id> mode=summary":  "Lightweight neighbors",
```

**Commit message:**
```
Wave 16A01 Task 3: mode param for get/related + dispatcher wiring

- context(): mode=summary|brief|full (default: full)
- node_related(): mode param (default: summary)
- dispatcher: pass mode from query params to handlers
- PROTOCOL_GUIDE: 4 mode examples
```

---

## TASK 4 — Add get_batch: action

**Goal:** Fetch detail for multiple nodes in one call.

**File to modify:** `gobp/mcp/tools/read.py`

Add `get_batch()` function:

```python
def get_batch(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Fetch multiple nodes in one call.

    Args:
        ids: comma-separated node IDs or list
        mode: summary|brief|full (default: brief)
        max: max nodes to return (default: 20, max: 50)

    Returns:
        ok, nodes[], found, not_found[], mode
    """
    raw_ids = args.get("ids", args.get("query", ""))
    if isinstance(raw_ids, str):
        ids = [i.strip() for i in raw_ids.split(",") if i.strip()]
    else:
        ids = list(raw_ids)

    mode = args.get("mode", "brief")
    max_nodes = min(int(args.get("max", 20)), 50)
    ids = ids[:max_nodes]

    nodes = []
    not_found = []

    for node_id in ids:
        node = index.get_node(node_id)
        if node:
            if mode == "summary":
                nodes.append(_node_summary(node, index))
            elif mode == "brief":
                nodes.append(_node_brief(node, index))
            else:
                nodes.append(node)
        else:
            not_found.append(node_id)

    return {
        "ok": True,
        "nodes": nodes,
        "found": len(nodes),
        "not_found": not_found,
        "mode": mode,
    }
```

**File to modify:** `gobp/mcp/dispatcher.py`

Add `get_batch:` action:

```python
        elif action == "get_batch":
            raw_ids = params.get("ids") or params.get("query", "")
            args = {
                "ids": raw_ids,
                "mode": params.get("mode", "brief"),
                "max": params.get("max", 20),
            }
            result = tools_read.get_batch(index, project_root, args)
```

**Update PROTOCOL_GUIDE:**
```python
"get_batch: ids='node:a,node:b,node:c'":            "Fetch multiple nodes (mode=brief)",
"get_batch: ids='node:a,node:b' mode=summary":      "Lightweight batch fetch",
```

**Commit message:**
```
Wave 16A01 Task 4: add get_batch: action

- read.py: get_batch() fetches up to 50 nodes in one call
- mode=summary|brief|full support
- Returns: nodes[], found count, not_found list
- dispatcher.py: get_batch: action routing
- PROTOCOL_GUIDE: 2 entries
```

---

## TASK 5 — Add metadata linter: validate: metadata

**Goal:** `gobp(query="validate: metadata")` flags nodes missing required fields.

**File to modify:** `gobp/mcp/tools/read.py`

Add `metadata_lint()` function:

```python
# Required metadata fields per NodeType
_METADATA_REQUIREMENTS: dict[str, list[str]] = {
    "Flow":        ["description", "spec_source"],
    "Engine":      ["description", "spec_source"],
    "Entity":      ["description", "spec_source"],
    "Feature":     ["description", "spec_source"],
    "Invariant":   ["description", "rule"],
    "Screen":      ["description"],
    "APIEndpoint": ["description", "spec_source"],
    "Document":    ["source_path"],
    "Decision":    ["what", "why"],
    "Lesson":      ["description"],
    "Node":        ["description"],
    "Idea":        ["description"],
}


def metadata_lint(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Check all nodes for missing required metadata fields.

    Returns score 0-100, missing fields per node, summary by type.
    """
    node_type_filter = args.get("type") or args.get("query") or None
    all_nodes = index.all_nodes()

    if node_type_filter:
        all_nodes = [n for n in all_nodes if n.get("type") == node_type_filter]

    missing_list = []
    by_type: dict[str, dict] = {}
    total_checked = 0
    total_complete = 0

    for node in all_nodes:
        node_type = node.get("type", "Node")
        required = _METADATA_REQUIREMENTS.get(node_type)
        if not required:
            continue

        total_checked += 1
        missing_fields = [f for f in required if not node.get(f)]

        type_stats = by_type.setdefault(node_type, {"total": 0, "complete": 0, "missing": []})
        type_stats["total"] += 1

        if missing_fields:
            missing_list.append({
                "node_id": node.get("id"),
                "node_type": node_type,
                "node_name": node.get("name", ""),
                "missing_fields": missing_fields,
            })
            type_stats["missing"].append(node.get("id"))
        else:
            total_complete += 1
            type_stats["complete"] += 1

    # Compute scores
    for t, stats in by_type.items():
        stats["score"] = round(stats["complete"] / stats["total"] * 100) if stats["total"] else 100
        del stats["missing"]  # too verbose in summary

    overall_score = round(total_complete / total_checked * 100) if total_checked else 100

    return {
        "ok": True,
        "score": overall_score,
        "total_checked": total_checked,
        "total_complete": total_complete,
        "missing_count": len(missing_list),
        "missing": missing_list[:20],  # cap at 20
        "by_type": by_type,
        "summary": (
            f"Metadata score: {overall_score}/100. "
            f"{len(missing_list)} nodes missing required fields."
        ),
    }
```

**File to modify:** `gobp/mcp/dispatcher.py`

Update `validate:` routing to handle `metadata` scope:

```python
        elif action == "validate":
            scope = params.get("scope") or params.get("action_filter") or params.get("query", "all")
            if scope in ("schema-docs", "schema-tests", "schema"):
                result = tools_read.schema_governance(index, project_root, {"scope": scope})
            elif scope == "metadata":
                result = tools_read.metadata_lint(index, project_root, params)
            else:
                result = tools_maintain.validate(
                    index, project_root, {"scope": scope, "severity_filter": "all"}
                )
```

**Update PROTOCOL_GUIDE:**
```python
"validate: metadata":           "Check all nodes for missing required fields",
"validate: metadata type=Flow": "Check only Flow nodes",
```

**Commit message:**
```
Wave 16A01 Task 5: metadata linter — validate: metadata

- read.py: _METADATA_REQUIREMENTS per NodeType
- read.py: metadata_lint() — score, missing fields, by_type summary
- dispatcher.py: validate: metadata routing
- Returns: score 0-100, missing[], by_type{}
- PROTOCOL_GUIDE: 2 entries
```

---

## TASK 6 — Add numeric priority system

**Goal:** Numeric priority (0-20+) computed from edge_count + tier_weight.

**File to modify:** `gobp/core/graph.py`

**Re-read `graph.py` in full.**

Add priority computation:

```python
# Tier weights per NodeType
TIER_WEIGHTS: dict[str, int] = {
    "Invariant": 20, "Decision": 15,
    "Engine": 10, "Flow": 10, "Entity": 10,
    "Feature": 5, "Screen": 5, "APIEndpoint": 5,
    "Document": 2, "TestCase": 2, "Lesson": 2,
    "Session": 0, "Wave": 0, "Repository": 0,
    "Node": 3, "Idea": 3, "Concept": 3, "TestKind": 1,
}

PRIORITY_THRESHOLDS = [
    (20, "critical"),
    (10, "high"),
    (5,  "medium"),
    (0,  "low"),
]


def priority_label(score: int) -> str:
    """Convert numeric score to label."""
    for threshold, label in PRIORITY_THRESHOLDS:
        if score >= threshold:
            return label
    return "low"


def compute_priority_score(self, node_id: str) -> int:
    """Compute numeric priority: edge_count + tier_weight.

    Args:
        node_id: Node to compute priority for

    Returns:
        Integer score (0-40+)
    """
    node = self.get_node(node_id)
    if not node:
        return 0
    incoming = len(self.get_edges_to(node_id))
    outgoing = len(self.get_edges_from(node_id))
    node_type = node.get("type", "Node")
    tier_weight = TIER_WEIGHTS.get(node_type, 0)
    return incoming + outgoing + tier_weight
```

Add as method to `GraphIndex` class.

**File to modify:** `gobp/mcp/tools/read.py`

Add `recompute_priorities()`:

```python
def recompute_priorities(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Recompute numeric priority for all nodes based on graph topology.

    priority_score = incoming_edges + outgoing_edges + tier_weight
    Stores both numeric score and label back to node files.

    Args:
        dry_run: bool — preview without writing
        type: NodeType filter (optional)

    Returns:
        ok, updated, skipped, summary by priority label
    """
    from gobp.mcp.tools.write import node_upsert
    from gobp.core.graph import priority_label

    dry_run = args.get("dry_run", False)
    type_filter = args.get("type") or args.get("query") or None
    session_id = args.get("session_id", "")

    all_nodes = index.all_nodes()
    if type_filter:
        all_nodes = [n for n in all_nodes if n.get("type") == type_filter]

    updated = 0
    skipped = 0
    label_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for node in all_nodes:
        node_id = node.get("id", "")
        if not node_id:
            continue

        score = index.compute_priority_score(node_id)
        label = priority_label(score)
        label_counts[label] = label_counts.get(label, 0) + 1

        current_score = node.get("priority_score", -1)
        if current_score == score:
            skipped += 1
            continue

        if not dry_run and session_id:
            node_upsert(index, project_root, {
                "node_id": node_id,
                "type": node.get("type", "Node"),
                "name": node.get("name", ""),
                "fields": {
                    "priority_score": score,
                    "priority": label,
                },
                "session_id": session_id,
            })
        updated += 1

    return {
        "ok": True,
        "updated": updated,
        "skipped": skipped,
        "dry_run": dry_run,
        "priority_distribution": label_counts,
        "summary": f"Recomputed {updated} nodes. {label_counts}",
    }
```

**File to modify:** `gobp/mcp/dispatcher.py`

Add `recompute:` action:

```python
        elif action == "recompute":
            scope = params.get("query", params.get("scope", "priorities"))
            if scope == "priorities":
                args = {
                    "dry_run": params.get("dry_run", False),
                    "type": params.get("type", ""),
                    "session_id": params.get("session_id", ""),
                }
                result = tools_read.recompute_priorities(index, project_root, args)
            else:
                result = {"ok": False, "error": f"recompute: unknown scope '{scope}'"}
```

**Update PROTOCOL_GUIDE:**
```python
"recompute: priorities session_id='x'":          "Recompute all node priorities from graph",
"recompute: priorities dry_run=true":             "Preview priority changes without writing",
"recompute: priorities type=Flow session_id='x'": "Recompute only Flow nodes",
```

**Acceptance criteria:**
- `compute_priority_score("node:pop_protocol")` → tier_weight(Invariant=20) + edges
- `priority_label(25)` → "critical"
- `priority_label(7)` → "medium"
- `recompute: priorities dry_run=true` → shows distribution without writing
- `recompute: priorities session_id='x'` → updates priority_score + priority fields

**Commit message:**
```
Wave 16A01 Task 6: numeric priority system — score + tier weights + recompute:

- graph.py: TIER_WEIGHTS, PRIORITY_THRESHOLDS, priority_label(), compute_priority_score()
- read.py: recompute_priorities() — batch update from graph topology
- dispatcher.py: recompute: priorities action
- priority_score = incoming + outgoing + tier_weight
- Threshold: 0-4=low, 5-9=medium, 10-19=high, 20+=critical
- PROTOCOL_GUIDE: 3 recompute examples
```

---

## TASK 7 — Add server hints to summary responses

**Goal:** Summary nodes include `detail_available`, `estimated_payload_size`.

**File to modify:** `gobp/mcp/tools/read.py`

Update `_node_summary()`:

```python
def _node_summary(node: dict[str, Any], index: GraphIndex | None = None) -> dict[str, Any]:
    node_id = node.get("id", "")
    edge_count = 0
    if index:
        edge_count = len(index.get_edges_from(node_id)) + len(index.get_edges_to(node_id))

    # Estimate full payload size
    import sys
    estimated_size = sys.getsizeof(str(node)) // 10  # rough token estimate

    return {
        "id": node_id,
        "type": node.get("type", ""),
        "name": node.get("name", ""),
        "status": node.get("status", ""),
        "priority": node.get("priority", "medium"),
        "priority_score": node.get("priority_score"),
        "edge_count": edge_count,
        "detail_available": True,
        "estimated_tokens": max(50, estimated_size),
        "hint": f"gobp(query=\"get: {node_id} mode=brief\") for more detail",
    }
```

**Commit message:**
```
Wave 16A01 Task 7: server hints in summary — estimated_tokens + detail hint

- _node_summary(): add priority_score, estimated_tokens, hint field
- AI knows payload size before requesting full detail
- Additive change — no breaking changes
```

---

## TASK 8 — Smoke test all new features

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex, compute_priority_score, priority_label
from gobp.mcp.dispatcher import dispatch
import tempfile
from gobp.core.init import init_project

async def test():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        init_project(root, force=True)
        index = GraphIndex.load_from_disk(root)

        # Test 1: find mode=summary
        r = await dispatch('find: unit mode=summary', index, root)
        assert r['ok'] and r['mode'] == 'summary'
        if r['matches']:
            assert 'edge_count' in r['matches'][0]
            assert 'estimated_tokens' in r['matches'][0]
        print(f'mode=summary OK: {r[\"count\"]} results')

        # Test 2: find mode=brief
        r2 = await dispatch('find: unit mode=brief', index, root)
        assert r2['ok'] and r2['mode'] == 'brief'
        print(f'mode=brief OK: {r2[\"count\"]} results')

        # Test 3: get_batch
        nodes = index.all_nodes()[:3]
        ids = ','.join(n['id'] for n in nodes)
        r3 = await dispatch(f\"get_batch: ids='{ids}' mode=summary\", index, root)
        assert r3['ok'] and r3['found'] == len(nodes)
        print(f'get_batch OK: {r3[\"found\"]} nodes fetched')

        # Test 4: validate: metadata
        r4 = await dispatch('validate: metadata', index, root)
        assert r4['ok'] and 'score' in r4
        print(f'metadata lint OK: score={r4[\"score\"]}')

        # Test 5: priority score
        for node in nodes:
            score = index.compute_priority_score(node['id'])
            label = priority_label(score)
            assert label in ('low', 'medium', 'high', 'critical')
        print('priority score OK')

        # Test 6: recompute dry_run
        r5 = await dispatch('recompute: priorities dry_run=true', index, root)
        assert r5['ok'] and r5['dry_run'] == True
        print(f'recompute dry_run OK: {r5[\"priority_distribution\"]}')

    print('All smoke tests passed')

asyncio.run(test())
"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 348 tests passing
```

**Commit message:**
```
Wave 16A01 Task 8: smoke test — all new features verified

- mode=summary/brief working for find
- get_batch fetches multiple nodes
- validate: metadata returns score
- priority_score computed correctly
- recompute: dry_run previews changes
- 348 existing tests passing
```

---

## TASK 9 — Create tests/test_wave16a01.py

**File to create:** `tests/test_wave16a01.py`

```python
"""Tests for Wave 16A01: response modes, get_batch, metadata lint, numeric priority."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.init import init_project
from gobp.core.graph import GraphIndex, priority_label, TIER_WEIGHTS
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.tools import read as tools_read


@pytest.fixture
def seeded_root(gobp_root: Path) -> Path:
    init_project(gobp_root, force=True)
    return gobp_root


# ── Response mode tests ───────────────────────────────────────────────────────

def test_find_mode_summary_has_edge_count(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.find(index, seeded_root, {"query": "", "mode": "summary"})
    assert r["ok"] is True
    assert r["mode"] == "summary"
    for match in r["matches"]:
        assert "edge_count" in match
        assert "detail_available" in match


def test_find_mode_summary_no_heavy_fields(seeded_root: Path):
    """summary mode should not have description or code_refs."""
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.find(index, seeded_root, {"query": "", "mode": "summary"})
    for match in r["matches"]:
        # summary should be lightweight
        assert "code_refs" not in match or match.get("code_refs") is None


def test_find_mode_brief_has_extra_fields(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.find(index, seeded_root, {"query": "", "mode": "brief"})
    assert r["mode"] == "brief"
    assert r["ok"] is True


def test_find_default_mode_backward_compat(seeded_root: Path):
    """Default mode should not break existing behavior."""
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.find(index, seeded_root, {"query": "unit"})
    assert r["ok"] is True
    assert "matches" in r


def test_dispatch_find_mode_summary(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("find: unit mode=summary", index, seeded_root))
    assert r["ok"] is True
    assert r.get("mode") == "summary"


def test_dispatch_find_mode_brief(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("find: unit mode=brief", index, seeded_root))
    assert r["ok"] is True
    assert r.get("mode") == "brief"


# ── get_batch tests ───────────────────────────────────────────────────────────

def test_get_batch_fetches_multiple(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    nodes = index.all_nodes()[:3]
    ids = ",".join(n["id"] for n in nodes)
    r = tools_read.get_batch(index, seeded_root, {"ids": ids, "mode": "summary"})
    assert r["ok"] is True
    assert r["found"] == 3
    assert r["not_found"] == []


def test_get_batch_handles_missing_ids(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.get_batch(index, seeded_root, {
        "ids": "node:real_node,node:nonexistent",
        "mode": "summary"
    })
    assert r["ok"] is True
    assert "nonexistent" in str(r["not_found"])


def test_get_batch_max_50(seeded_root: Path):
    """get_batch respects max 50 limit."""
    index = GraphIndex.load_from_disk(seeded_root)
    ids = ",".join(n["id"] for n in index.all_nodes())
    r = tools_read.get_batch(index, seeded_root, {"ids": ids, "max": 200})
    assert r["found"] <= 50


def test_dispatch_get_batch(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    nodes = index.all_nodes()[:2]
    ids = ",".join(n["id"] for n in nodes)
    r = asyncio.run(dispatch(f"get_batch: ids='{ids}'", index, seeded_root))
    assert r["ok"] is True
    assert r["_dispatch"]["action"] == "get_batch"


# ── Metadata linter tests ─────────────────────────────────────────────────────

def test_metadata_lint_returns_score(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.metadata_lint(index, seeded_root, {})
    assert r["ok"] is True
    assert "score" in r
    assert 0 <= r["score"] <= 100


def test_metadata_lint_returns_by_type(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.metadata_lint(index, seeded_root, {})
    assert "by_type" in r
    assert isinstance(r["by_type"], dict)


def test_dispatch_validate_metadata(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("validate: metadata", index, seeded_root))
    assert r["ok"] is True
    assert "score" in r


def test_dispatch_validate_metadata_type_filter(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("validate: metadata type=TestKind", index, seeded_root))
    assert r["ok"] is True


# ── Numeric priority tests ────────────────────────────────────────────────────

def test_priority_label_thresholds():
    assert priority_label(25) == "critical"
    assert priority_label(20) == "critical"
    assert priority_label(19) == "high"
    assert priority_label(10) == "high"
    assert priority_label(9) == "medium"
    assert priority_label(5) == "medium"
    assert priority_label(4) == "low"
    assert priority_label(0) == "low"


def test_tier_weights_defined():
    assert "Decision" in TIER_WEIGHTS
    assert "Engine" in TIER_WEIGHTS
    assert TIER_WEIGHTS["Invariant"] >= TIER_WEIGHTS["Feature"]
    assert TIER_WEIGHTS["Decision"] >= TIER_WEIGHTS["Document"]


def test_compute_priority_score(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    nodes = index.all_nodes()
    if nodes:
        node_id = nodes[0]["id"]
        score = index.compute_priority_score(node_id)
        assert isinstance(score, int)
        assert score >= 0


def test_dispatch_recompute_dry_run(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("recompute: priorities dry_run=true", index, seeded_root))
    assert r["ok"] is True
    assert r["dry_run"] is True
    assert "priority_distribution" in r


def test_recompute_no_write_when_dry_run(seeded_root: Path):
    """dry_run=true should not change any nodes."""
    index = GraphIndex.load_from_disk(seeded_root)
    node_before = dict(index.all_nodes()[0]) if index.all_nodes() else {}

    asyncio.run(dispatch("recompute: priorities dry_run=true", index, seeded_root))

    index2 = GraphIndex.load_from_disk(seeded_root)
    node_after = index2.all_nodes()[0] if index2.all_nodes() else {}
    # priority_score should not have been written
    assert node_after.get("priority_score") == node_before.get("priority_score")
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave16a01.py -v
# Expected: ~25 tests passing

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 373+ tests
```

**Commit message:**
```
Wave 16A01 Task 9: create tests/test_wave16a01.py — ~25 tests

- Response modes: summary/brief/default (6)
- get_batch: multiple nodes, missing, max limit, dispatch (4)
- Metadata lint: score, by_type, dispatch, type filter (4)
- Numeric priority: thresholds, tier weights, compute, recompute dry_run (5)
```

---

## TASK 10 — Update MCP_TOOLS.md + full suite + CHANGELOG

**File to modify:** `docs/MCP_TOOLS.md`

Add to quick reference table:

```markdown
| `find: <keyword> mode=summary` | Lightweight results (~50 tokens/node) |
| `find: <keyword> mode=brief` | Medium results (~150 tokens/node) |
| `get: <node_id> mode=brief` | Brief node detail |
| `get_batch: ids='a,b,c' mode=brief` | Fetch multiple nodes |
| `validate: metadata` | Check nodes for missing required fields |
| `validate: metadata type=Flow` | Check specific node type |
| `recompute: priorities session_id='x'` | Recompute priorities from graph |
| `recompute: priorities dry_run=true` | Preview priority changes |
```

**Run full suite:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 373+ tests
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A01] — Response Tiers + Metadata Linter + Perf Fix + Priority System — 2026-04-16

### Improvements (from Cursor production feedback)

- **I1 — Response tiers**: mode=summary|brief|full for find/get/related
  - summary: id/type/name/status/priority/edge_count (~50 tokens)
  - brief: summary + key fields + edge types (~150 tokens)
  - full: unchanged (current behavior)
  
- **I2 — Batch detail**: get_batch: ids='a,b,c' mode=brief
  - Fetch up to 50 nodes in one call
  
- **I3 — Metadata linter**: validate: metadata
  - Score 0-100 per node type
  - Flags missing description/spec_source/rule etc.
  
- **I4 — Perf test stability**:
  - node_upsert: 500ms → 700ms
  - gobp_overview: 100ms → 150ms
  - test_perf_node_upsert_v2: median of 3 runs
  
- **I5 — Numeric priority**:
  - priority_score = edge_count + tier_weight
  - TIER_WEIGHTS: Invariant=20, Decision=15, Engine/Flow/Entity=10...
  - Threshold: 0-4=low, 5-9=medium, 10-19=high, 20+=critical
  - recompute: priorities → batch update from graph topology
  
- **I6 — Server hints**: estimated_tokens + detail_available in summary

### Changed
- tests/test_performance.py: thresholds + median strategy
- gobp/mcp/tools/read.py: _node_summary, _node_brief, get_batch,
  metadata_lint, recompute_priorities, mode param on find/get/related
- gobp/core/graph.py: TIER_WEIGHTS, priority_label, compute_priority_score
- gobp/mcp/dispatcher.py: mode params, get_batch:, recompute:, validate: metadata

### Total: 1 MCP tool, 32 actions, 373+ tests
```

**Commit message:**
```
Wave 16A01 Task 10: MCP_TOOLS.md + full suite green + CHANGELOG

- 8 new query patterns documented
- 373+ tests passing
- CHANGELOG: Wave 16A01 entry
```

---

# POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex, priority_label
from gobp.mcp.dispatcher import dispatch

root = Path('D:/GoBP')
index = GraphIndex.load_from_disk(root)

async def verify():
    # Mode test
    r = await dispatch('find: test mode=summary', index, root)
    print('mode=summary:', r.get('mode'), r.get('count'), 'results')

    # Metadata lint
    r2 = await dispatch('validate: metadata', index, root)
    print('metadata score:', r2.get('score'))

    # Priority
    nodes = index.all_nodes()[:3]
    for n in nodes:
        score = index.compute_priority_score(n['id'])
        print(f'priority: {n[\"id\"]} → {score} ({priority_label(score)})')

asyncio.run(verify())
"

git log --oneline | Select-Object -First 12
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief

```powershell
cd D:\GoBP
# Save to D:\GoBP\waves\wave_16a01_brief.md
git add waves/wave_16a01_brief.md
git commit -m "Add Wave 16A01 Brief — response tiers + metadata linter + perf fix + priority"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_16a01_brief.md first.
Also read gobp/mcp/tools/read.py, gobp/mcp/dispatcher.py,
gobp/core/graph.py, tests/test_performance.py.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 10 tasks sequentially.
R9: all 348 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 16A01. Read CLAUDE.md and waves/wave_16a01_brief.md.
Set env: $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: node_upsert=700ms, gobp_overview=150ms, median strategy in node_upsert test
- Task 2: _node_summary() + _node_brief() in read.py, find() mode param
- Task 3: context()/node_related() support mode, dispatcher passes mode
- Task 4: get_batch() in read.py, get_batch: in dispatcher, max=50
- Task 5: metadata_lint() in read.py, validate: metadata routing
- Task 6: TIER_WEIGHTS/priority_label/compute_priority_score in graph.py,
          recompute_priorities() in read.py, recompute: action
- Task 7: _node_summary() has estimated_tokens + hint fields
- Task 8: smoke test passed, 348 tests passing
- Task 9: test_wave16a01.py ~25 tests passing
- Task 10: 373+ tests, MCP_TOOLS.md updated, CHANGELOG updated

BLOCKING RULE: Gặp vấn đề không tự xử lý → DỪNG, báo CEO ngay.

Expected: 373+ tests. Report WAVE 16A01 AUDIT COMPLETE.
```

---

# WHAT COMES NEXT

```
Wave 16A01 done
    ↓
Wave 8B — MIHOS import
  recompute: priorities sau khi import
  validate: metadata để check quality
  find: mode=summary để browse nodes nhẹ
  get_batch: để fetch nhiều nodes cùng lúc
    ↓
Wave 16A02 — next maintenance batch (if needed)
Wave 17A01 — A2A interview protocol
Wave 17B01 — capabilities: manifest
Wave 17C01 — pgvector semantic search
```

---

*Wave 16A01 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-16*

◈
