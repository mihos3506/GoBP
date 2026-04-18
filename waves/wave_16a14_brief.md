# WAVE 16A14 BRIEF — READ PERFORMANCE ALGORITHMS

**Wave:** 16A14
**Title:** Inverted Index, Adjacency List, Write-time Indexing, DFS Cycle Detection
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-18
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 7 tasks
**Estimated effort:** 6-8 hours

---

## CONTEXT

Server cache (Wave 16A12) eliminated disk reload — warm read avg 2ms. But search and traversal still O(N) inside RAM.

```
find: keyword       → O(N) scan all node names/descriptions
related: node_id    → O(E) scan all edges
explore:            → O(N + E)
suggest: context    → O(N × K)
validate:           → No cycle detection
```

**After this wave:**
```
find: keyword       → O(K) inverted index lookup
related: node_id    → O(1) adjacency list lookup
explore:            → O(1) + O(1)
suggest:            → O(K) inverted index
validate:           → DFS cycle detection O(V + E)
All indexes built at write time → reads are pure lookup
```

---

## DESIGN

### 1. InvertedIndex — keyword → node_ids

```
Build at load: normalize_text(name + description) → split → index each word
Search: query keywords → intersect(index[kw1], index[kw2]) → AND logic
Fallback: union if intersection empty → OR logic
Write-time: add_node/remove_node updates index
```

### 2. AdjacencyIndex — node → edges

```
Build at load: for each edge → outgoing[from] += edge, incoming[to] += edge
Lookup: get_outgoing(node_id) → O(1) dict access
Filter: exclude_types={"discovered_in"} → skip metadata
Write-time: add_edge/remove_edge updates lists
```

### 3. Write-time Indexing

```
GraphIndex.load_from_disk() → build InvertedIndex + AdjacencyIndex
GraphIndex.add_node_in_memory() → inverted.add_node()
GraphIndex.add_edge_in_memory() → adjacency.add_edge()
GraphIndex.remove_node_in_memory() → inverted.remove_node() + adjacency.remove_node()
→ Reads = pure lookup, zero processing
```

### 4. DFS Cycle Detection

```
detect_cycles(index, edge_types=["depends_on", "supersedes"])
→ DFS with WHITE/GRAY/BLACK coloring
→ GRAY→GRAY = cycle found
→ Returns list of cycle paths
→ O(V + E)
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 605 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 605 tests
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/core/graph.py` | Integrate indexes |
| 3 | `gobp/core/search.py` | Use inverted index |
| 4 | `gobp/mcp/tools/read.py` | Use adjacency in explore/related |
| 5 | `gobp/mcp/tools/maintain.py` | Add cycle detection |

---

# TASKS

## TASK 1 — InvertedIndex class

**File to create:** `gobp/core/indexes.py`

`InvertedIndex` with: `build(nodes)`, `search(query, limit)`, `add_node(node)`, `remove_node(node_id)`, `update_node(node)`.

- Use `normalize_text()` from search.py
- Minimum keyword length: 2 chars
- search: AND logic, OR fallback if empty

**Commit:** `Wave 16A14 Task 1: InvertedIndex class — keyword to node_id lookup`

---

## TASK 2 — AdjacencyIndex class

**File to modify:** `gobp/core/indexes.py`

`AdjacencyIndex` with: `build(edges)`, `get_outgoing(node_id, exclude_types)`, `get_incoming(node_id, exclude_types)`, `get_all(node_id, exclude_types)`, `add_edge(from, to, type)`, `remove_edge(from, to, type)`, `remove_node(node_id)`, `edge_count(node_id, exclude_types)`.

**Commit:** `Wave 16A14 Task 2: AdjacencyIndex class — node-centric edge lookup`

---

## TASK 3 — Integrate indexes into GraphIndex

**File to modify:** `gobp/core/graph.py`

- Build both in `load_from_disk()`
- Update in `add_node_in_memory()`, `add_edge_in_memory()`, `remove_node_in_memory()`
- Expose as `index._inverted`, `index._adjacency`

**Commit:** `Wave 16A14 Task 3: integrate indexes into GraphIndex — build at load, update at write`

---

## TASK 4 — Read actions use indexes

**File to modify:** `gobp/core/search.py` — use inverted index in search_nodes, suggest_related
**File to modify:** `gobp/mcp/tools/read.py` — use adjacency in explore, related

Fallback to full scan if index not available.

**Commit:** `Wave 16A14 Task 4: read actions use inverted index + adjacency list`

---

## TASK 5 — DFS Cycle Detection

**File to create:** `gobp/core/graph_algorithms.py`

`detect_cycles(index, edge_types)` — DFS coloring, returns cycle paths.

**File to modify:** `gobp/mcp/tools/maintain.py` — add to validate.

**Commit:** `Wave 16A14 Task 5: DFS cycle detection in validate`

---

## TASK 6 — Performance benchmark

Create `scripts/wave16a14_bench.py`:
- 500 nodes + 400 edges
- Benchmark find/explore/suggest/validate on indexed graph
- Print avg ms per action

**Commit:** `Wave 16A14 Task 6: performance benchmark — indexed reads on 500 nodes`

---

## TASK 7 — Tests + CHANGELOG

**File to create:** `tests/test_wave16a14.py` (~21 tests):
- InvertedIndex: 5 tests
- AdjacencyIndex: 5 tests
- GraphIndex integration: 3 tests
- Read action performance: 4 tests
- Cycle detection: 4 tests

**CHANGELOG:** Wave 16A14 entry. Expected: 626+ tests.

**Commit:** `Wave 16A14 Task 7: tests + CHANGELOG — 626+ tests`

---

# CEO DISPATCH

## Cursor
```
Read .cursorrules and waves/wave_16a14_brief.md.
Read gobp/core/graph.py, gobp/core/search.py,
gobp/mcp/tools/read.py, gobp/mcp/tools/maintain.py.
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute 7 tasks. R9: 605 tests baseline. 1 task = 1 commit.
```

## Claude CLI audit
```
Audit Wave 16A14.
Task 1: InvertedIndex in indexes.py — build/search/add/remove
Task 2: AdjacencyIndex — outgoing/incoming/get_all/edge_count
Task 3: GraphIndex integrates both — build at load, update at write
Task 4: find/explore/suggest/related use indexes with fallback
Task 5: detect_cycles() + validate reports cycles
Task 6: Benchmark 500 nodes
Task 7: 21 tests, 626+ total, CHANGELOG
BLOCKING: Gặp vấn đề → DỪNG, báo CEO.
Expected: 626+ tests.
```

---

*Wave 16A14 Brief v1.0 — 2026-04-18*

◈
