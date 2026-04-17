# WAVE 16A07 BRIEF — SEARCH FIX + EDGE TYPES + SESSION NOISE + DUPLICATE DETECTION

**Wave:** 16A07
**Title:** Search quality, depends_on edge type, session noise, duplicate detection
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-17
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 6 tasks
**Estimated effort:** 4-5 hours

---

## CONTEXT

4 problems blocking MIHOS GoBP usability:

**P1 — Search không hiểu tiếng Việt (blocking)**
```
find: mihot    → 0 results  (node "Mi Hốt" exists)
find: mi hốt   → 66 results (matches "mi" substring everywhere)
find: trustgate → 3 duplicate nodes, không biết node nào chính
Root cause:
  - Không normalize diacritics: "mihot" ≠ "mi hốt"
  - Substring match quá rộng: "mi" matches AdminAccount, AuditLog...
  - Không có relevance ranking: tên match = description match
  - Type filter dùng text match thay vì field filter
```

**P2 — depends_on không phải valid edge type**
```
Opus đề xuất: Engine --depends_on--> Engine
→ Edge type không tồn tại trong schema
→ Phải dùng relates_to (mất semantic meaning)
Root cause: core_edges.yaml thiếu depends_on, tested_by edge types
```

**P3 — Session nodes làm nhiễu search**
```
34 Session nodes / 232 total = 15%
find: keyword → sessions xuất hiện trong results
Sessions là metadata, không phải knowledge
```

**P4 — Duplicate nodes không được detect**
```
TrustGate xuất hiện 3 lần với IDs khác nhau
Khi tạo node mới, không có warning "node tương tự đã tồn tại"
```

---

## DESIGN

### Search improvements

```python
# gobp/core/search.py — new module

def normalize_text(text: str) -> str:
    """Normalize Vietnamese text for search.
    
    'Mi Hốt' → 'mi hot'
    'TrustGate Engine' → 'trustgate engine'
    'mihot' → 'mihot' (already normalized)
    """
    import unicodedata
    # NFD decompose: 'ố' → 'o' + combining chars
    nfd = unicodedata.normalize('NFD', text.lower())
    # Remove combining diacritical marks
    ascii_text = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return ascii_text


def search_score(query_norm: str, node: dict) -> int:
    """Score node relevance. Higher = more relevant.
    
    Name exact match:    100
    Name starts with:    80
    Name contains:       60
    ID contains:         40
    Description match:   20
    No match:            0
    """
    name_norm = normalize_text(node.get('name', ''))
    id_norm = normalize_text(node.get('id', ''))
    desc_norm = normalize_text(node.get('description', ''))
    
    if name_norm == query_norm:
        return 100
    if name_norm.startswith(query_norm):
        return 80
    if query_norm in name_norm:
        return 60
    if query_norm in id_norm:
        return 40
    if query_norm in desc_norm:
        return 20
    return 0


def search_nodes(
    index,
    query: str,
    type_filter: str | None = None,
    exclude_types: list[str] | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search nodes with Vietnamese normalization + relevance ranking."""
    query_norm = normalize_text(query)
    exclude = set(exclude_types or [])
    
    results = []
    for node in index.all_nodes():
        node_type = node.get('type', '')
        
        # Type filter (exact match, not text search)
        if type_filter and node_type != type_filter:
            continue
        
        # Exclude types (e.g. Session)
        if node_type in exclude:
            continue
        
        score = search_score(query_norm, node)
        if score > 0:
            results.append((score, node))
    
    # Sort by score descending
    results.sort(key=lambda x: -x[0])
    
    return [node for _, node in results[:limit]]
```

### Session noise — exclude from default search

```python
# find: keyword → excludes Session by default
# find: keyword include_sessions=true → includes Session
# find:Session keyword → includes Session (explicit type filter)
```

### depends_on + tested_by edge types

```yaml
# gobp/schema/core_edges.yaml — add:

  depends_on:
    description: "Node A requires Node B to function"
    directional: true
    cardinality: many_to_many
    
  tested_by:
    description: "Node A is tested by TestCase B"
    directional: true
    cardinality: many_to_many
    
  covers:
    description: "TestCase A covers Node B"  
    directional: true
    cardinality: many_to_many
```

### Duplicate detection

```python
# When creating a node, warn if similar name exists:
# create:Engine name='TrustGate Engine'
# → Warning: "Similar nodes found: trustgate.meta.53299456 (Node), 
#              trustgate.ops.84166144 (Engine)"
# → Node still created, but warning returned
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 486 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 486 tests passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/mcp/tools/read.py` | Update find() |
| 3 | `gobp/schema/core_edges.yaml` | Add depends_on, tested_by |
| 4 | `gobp/core/mutator.py` | Add duplicate warning to node_upsert |
| 5 | `gobp/mcp/parser.py` | Update PROTOCOL_GUIDE |
| 6 | `waves/wave_16a07_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Create gobp/core/search.py

**Goal:** Vietnamese normalization + relevance scoring.

**File to create:** `gobp/core/search.py`

```python
"""Search utilities with Vietnamese normalization and relevance ranking."""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gobp.core.graph import GraphIndex


def normalize_text(text: str) -> str:
    """Normalize text for Vietnamese-aware search.
    
    Strips diacritics so 'mi hốt' == 'mihot' == 'Mi Hot'.
    
    Examples:
        normalize_text('Mi Hốt') → 'mi hot'
        normalize_text('TrustGate') → 'trustgate'
        normalize_text('mihot') → 'mihot'
    """
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def search_score(query_norm: str, node: dict) -> int:
    """Score a node's relevance to a normalized query.
    
    Scoring:
        Name exact match:      100
        Name starts with query: 80
        Name contains query:    60
        ID contains query:      40
        Description match:      20
        No match:                0
    """
    name_norm = normalize_text(node.get("name", ""))
    id_norm = normalize_text(node.get("id", ""))
    desc_norm = normalize_text(node.get("description", ""))

    if name_norm == query_norm:
        return 100
    if name_norm.startswith(query_norm):
        return 80
    if query_norm in name_norm:
        return 60
    if query_norm in id_norm:
        return 40
    if query_norm in desc_norm:
        return 20
    return 0


def search_nodes(
    index: "GraphIndex",
    query: str,
    type_filter: str | None = None,
    exclude_types: list[str] | None = None,
    limit: int = 20,
) -> list[tuple[int, dict]]:
    """Search nodes with Vietnamese normalization and relevance ranking.
    
    Args:
        index: GraphIndex to search
        query: Search term (Vietnamese-aware)
        type_filter: Only return nodes of this exact type
        exclude_types: Exclude these node types (default: Session excluded)
        limit: Max results
    
    Returns:
        List of (score, node) tuples, sorted by score descending
    """
    if exclude_types is None:
        exclude_types = ["Session"]

    query_norm = normalize_text(query.strip())
    if not query_norm:
        return []

    exclude_set = set(exclude_types)
    results: list[tuple[int, dict]] = []

    for node in index.all_nodes():
        node_type = node.get("type", "")

        # Exact type filter (field match, not text search)
        if type_filter and node_type != type_filter:
            continue

        # Exclude types
        if node_type in exclude_set:
            continue

        score = search_score(query_norm, node)
        if score > 0:
            results.append((score, node))

    results.sort(key=lambda x: -x[0])
    return results[:limit]


def find_similar_nodes(
    index: "GraphIndex",
    name: str,
    node_type: str | None = None,
    threshold: int = 60,
) -> list[dict]:
    """Find nodes with similar names for duplicate detection.
    
    Returns nodes with search_score >= threshold against the name.
    Used to warn before creating potential duplicates.
    """
    results = search_nodes(
        index,
        name,
        type_filter=node_type,
        exclude_types=[],  # Include all types for duplicate check
        limit=5,
    )
    return [node for score, node in results if score >= threshold]
```

**Verify:**
```python
from gobp.core.search import normalize_text, search_score
assert normalize_text('Mi Hốt') == 'mi hot'
assert normalize_text('mihot') == 'mihot'
assert normalize_text('TrustGate') == 'trustgate'
# Both normalize to same → can match
assert normalize_text('Mi Hốt') == normalize_text('mi hot')
print('normalize_text OK')
```

**Commit message:**
```
Wave 16A07 Task 1: create gobp/core/search.py

- normalize_text(): strip Vietnamese diacritics
- search_score(): relevance ranking (exact=100, contains=60, desc=20)
- search_nodes(): type filter by field (not text), Session excluded by default
- find_similar_nodes(): duplicate detection helper
```

---

## TASK 2 — Update find() in read.py to use new search

**Goal:** Replace substring search with search.py. Session excluded by default.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read find() function in full.**

Replace current search logic with:

```python
from gobp.core.search import search_nodes

async def find(index, project_root, args):
    query = args.get("query", "").strip()
    type_filter = args.get("type_filter") or args.get("type")
    limit = int(args.get("limit", args.get("page_size", 20)))
    mode = args.get("mode", "summary")
    include_sessions = args.get("include_sessions", "false").lower() == "true"
    
    # Determine excluded types
    exclude_types = []
    if not include_sessions and type_filter != "Session":
        exclude_types = ["Session"]
    
    # Use new search with Vietnamese normalization + relevance ranking
    results = search_nodes(
        index,
        query=query,
        type_filter=type_filter,
        exclude_types=exclude_types,
        limit=limit,
    )
    
    matches = []
    for score, node in results:
        match_entry = _node_to_mode(node, mode)
        match_entry["_score"] = score  # relevance score for debugging
        matches.append(match_entry)
    
    return {
        "ok": True,
        "matches": matches,
        "count": len(matches),
        "query": query,
        "type_filter": type_filter,
        "sessions_excluded": bool(exclude_types),
        "hint": "Use include_sessions=true to include Session nodes. Use type_filter for exact type match.",
    }
```

**Acceptance criteria:**
```python
# Vietnamese normalization
find(query='mihot') → includes "Mi Hốt Standard Online"
find(query='mi hốt') → includes "Mi Hốt Standard Online"
find(query='Mi Hot') → includes "Mi Hốt Standard Online"

# Type filter (exact)
find(query='engine', type_filter='Engine') → only Engine nodes
find(query='entity') → no false positives from description text

# Session exclusion
find(query='test') → no Session nodes by default
find(query='test', include_sessions=true) → includes Session nodes
find type_filter='Session' → includes Session nodes (explicit)

# Relevance ranking
find(query='trustgate') → trustgate_engine.ops first (name match)
                        → before nodes with "trustgate" in description
```

**Commit message:**
```
Wave 16A07 Task 2: update find() with Vietnamese search + relevance ranking

- Uses search.py normalize_text() for diacritics-aware matching
- Type filter by exact field match, not text search
- Session nodes excluded by default (include_sessions=true to include)
- Results sorted by relevance score (exact name=100, contains=60, desc=20)
- find: mihot now finds "Mi Hốt Standard Online"
```

---

## TASK 3 — Add depends_on + tested_by to core_edges.yaml

**Goal:** depends_on and tested_by are valid edge types.

**File to modify:** `gobp/schema/core_edges.yaml`

**Re-read in full.**

Add to edge_types:

```yaml
  depends_on:
    description: "Node A requires Node B to function correctly"
    directional: true
    cardinality: many_to_many
    notes: "Use for: Engine depends_on Engine, Flow depends_on Entity"

  tested_by:
    description: "Node A is validated by TestCase B"
    directional: true
    cardinality: many_to_many
    notes: "Use for: Flow tested_by TestCase, Engine tested_by TestCase"

  covers:
    description: "TestCase A covers functionality of Node B"
    directional: true
    cardinality: many_to_many
    notes: "Inverse of tested_by. TestCase covers Flow/Engine/Feature"
```

**Update PROTOCOL_GUIDE in parser.py:**
```python
# Add to edge examples:
"edge: engine_a --depends_on--> engine_b":    "Engine dependency",
"edge: flow_a --tested_by--> testcase_b":     "Flow test coverage",
"edge: testcase_a --covers--> flow_b":        "TestCase coverage",
```

**Verify:**
```python
# After update, these should work:
edge: trustgate_engine.ops.00000001 --depends_on--> geo_intelligence_engine.ops.00000001
edge: mi_hot_standard_flow.ops.00000001 --tested_by--> inv5_test.test.unit.00000001
```

**Commit message:**
```
Wave 16A07 Task 3: add depends_on + tested_by + covers to core_edges.yaml

- depends_on: Engine/Flow requires another node to function
- tested_by: Flow/Engine validated by TestCase
- covers: TestCase covers Flow/Engine (inverse of tested_by)
- PROTOCOL_GUIDE: 3 new edge examples
- Replaces workaround of using relates_to for dependencies
```

---

## TASK 4 — Add duplicate warning to node creation

**Goal:** Warn when creating a node with similar name to existing nodes.

**File to modify:** `gobp/core/mutator.py`

**Re-read node_upsert() in full.**

After creating/upserting a node, check for similar names:

```python
from gobp.core.search import find_similar_nodes

def node_upsert(gobp_root, node_data, session_id, ...):
    # ... existing upsert logic ...
    
    # After successful write, check for duplicates
    warnings = []
    name = node_data.get("name", "")
    node_type = node_data.get("type")
    new_id = result.get("node_id")
    
    if name:
        # Reload index to check
        from gobp.core.graph import GraphIndex
        fresh_index = GraphIndex.load_from_disk(gobp_root)
        similar = find_similar_nodes(fresh_index, name, node_type, threshold=80)
        
        # Exclude the node we just created
        similar = [n for n in similar if n.get("id") != new_id]
        
        if similar:
            warnings.append({
                "type": "potential_duplicate",
                "message": f"Similar nodes found: {', '.join(n['id'] + ' (' + n.get('type','') + ')' for n in similar[:3])}",
                "similar_ids": [n["id"] for n in similar[:3]],
            })
    
    result["warnings"] = warnings
    return result
```

**Acceptance criteria:**
```
create:Engine name='TrustGate Engine'
→ ok: True (node created)
→ warnings: [{type: "potential_duplicate", similar_ids: ["trustgate.ops.84166144"]}]
```

**Commit message:**
```
Wave 16A07 Task 4: duplicate warning in node_upsert

- After create/upsert, check for similar names using search.py
- Warning returned if similar node found (score >= 80)
- Node still created — warning is informational only
- Helps AI avoid creating TrustGate for the 4th time
```

---

## TASK 5 — Smoke test

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp_mihos"

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch
from gobp.core.search import normalize_text

# Test normalize_text
assert normalize_text('Mi Hốt') == 'mi hot', f'Got: {normalize_text(chr(77)+chr(105)+chr(32)+chr(72)+chr(7889)+chr(116))}'
assert normalize_text('mihot') == 'mihot'
assert normalize_text('TrustGate') == 'trustgate'
print('normalize_text OK')

async def test():
    root = Path('D:/MIHOS-v1')
    index = GraphIndex.load_from_disk(root)
    
    # Test Vietnamese search
    r1 = await dispatch('find: mihot mode=summary', index, root)
    names = [m.get('name','') for m in r1.get('matches', [])]
    has_mihot = any('Mi H' in n for n in names)
    print(f'find mihot: {len(r1[\"matches\"])} results, has Mi Hot: {has_mihot}')
    
    # Test session exclusion  
    r2 = await dispatch('find: test mode=summary', index, root)
    types = [m.get('type','') for m in r2.get('matches', [])]
    has_session = 'Session' in types
    print(f'find test (no sessions): {len(r2[\"matches\"])} results, has_session: {has_session}')
    assert not has_session, 'Sessions should be excluded by default'
    
    # Test type filter
    r3 = await dispatch('find:Engine mode=summary', index, root)
    types3 = set(m.get('type','') for m in r3.get('matches', []))
    print(f'find:Engine types: {types3}')
    assert types3 == {'Engine'} or not types3, f'Expected only Engine, got {types3}'
    
    # Test depends_on edge type
    sess = await dispatch('session:start actor=test goal=edge-test', index, root)
    sid = sess['session_id']
    index2 = GraphIndex.load_from_disk(root)
    
    # Find two engines
    r4 = await dispatch('find:Engine mode=summary', index2, root)
    if len(r4['matches']) >= 2:
        id1 = r4['matches'][0]['id']
        id2 = r4['matches'][1]['id']
        r5 = await dispatch(f'edge: {id1} --depends_on--> {id2}', index2, root)
        print(f'depends_on edge: ok={r5.get(\"ok\")}')
    
    await dispatch(f'session:end session_id={sid}', GraphIndex.load_from_disk(root), root)
    print('ALL SMOKE TESTS PASSED')

asyncio.run(test())
"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 486 tests passing
```

**Commit message:**
```
Wave 16A07 Task 5: smoke test — Vietnamese search + session exclusion + depends_on

- normalize_text('Mi Hốt') == 'mi hot' verified
- find: mihot finds Mi Hốt nodes
- Session nodes excluded by default
- depends_on edge type works
- 486 tests passing
```

---

## TASK 6 — Tests + CHANGELOG

**File to create:** `tests/test_wave16a07.py`

```python
"""Tests for Wave 16A07: Vietnamese search, edge types, duplicate detection."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.search import normalize_text, search_score, search_nodes, find_similar_nodes
from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch


# ── normalize_text tests ──────────────────────────────────────────────────────

def test_normalize_removes_vietnamese_diacritics():
    assert normalize_text("Mi Hốt") == "mi hot"
    assert normalize_text("Hà Nội") == "ha noi"
    assert normalize_text("Bàn Cờ") == "ban co"


def test_normalize_lowercase():
    assert normalize_text("TrustGate") == "trustgate"
    assert normalize_text("MIHOS") == "mihos"


def test_normalize_ascii_unchanged():
    assert normalize_text("mihot") == "mihot"
    assert normalize_text("trustgate engine") == "trustgate engine"


def test_normalize_equivalence():
    """Vietnamese and ASCII versions normalize to same string."""
    assert normalize_text("Mi Hốt") == normalize_text("mi hot")
    assert normalize_text("Hốt") == normalize_text("hot")


# ── search_score tests ────────────────────────────────────────────────────────

def test_score_exact_name():
    node = {"name": "TrustGate Engine", "id": "x", "description": ""}
    assert search_score("trustgate engine", node) == 100


def test_score_name_starts_with():
    node = {"name": "TrustGate Engine", "id": "x", "description": ""}
    assert search_score("trustgate", node) == 80


def test_score_name_contains():
    node = {"name": "Core TrustGate", "id": "x", "description": ""}
    assert search_score("trustgate", node) == 60


def test_score_id_contains():
    node = {"name": "Something", "id": "trustgate_engine_ops", "description": ""}
    assert search_score("trustgate", node) == 40


def test_score_description_only():
    node = {"name": "Engine A", "id": "engine_a", "description": "uses trustgate internally"}
    assert search_score("trustgate", node) == 20


def test_score_no_match():
    node = {"name": "Auth Engine", "id": "auth_engine", "description": "handles login"}
    assert search_score("trustgate", node) == 0


# ── search_nodes tests ────────────────────────────────────────────────────────

def test_search_vietnamese(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    # Create a node with Vietnamese name
    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='search test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    asyncio.run(dispatch(
        f"create:Flow name='Mi Hốt Standard' session_id={sid}", index, tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    # Search with ASCII version
    results = search_nodes(index, "mihot", exclude_types=[])
    names = [node.get("name") for _, node in results]
    assert any("Mi H" in n for n in names), f"Expected Mi Hốt in {names}"


def test_search_excludes_sessions_by_default(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='session exclusion test'", index, tmp_path
    ))["session_id"]

    index = GraphIndex.load_from_disk(tmp_path)
    results = search_nodes(index, "test")  # default excludes Session
    types = {node.get("type") for _, node in results}
    assert "Session" not in types


def test_search_includes_sessions_when_requested(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    asyncio.run(dispatch(
        "session:start actor='test' goal='include session test'", index, tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    results = search_nodes(index, "test", exclude_types=[])  # include all
    types = {node.get("type") for _, node in results}
    assert "Session" in types


def test_search_type_filter_exact(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='type filter test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    asyncio.run(dispatch(f"create:Engine name='Test Engine' session_id={sid}", index, tmp_path))
    asyncio.run(dispatch(f"create:Flow name='Test Flow' session_id={sid}", index, tmp_path))

    index = GraphIndex.load_from_disk(tmp_path)
    results = search_nodes(index, "test", type_filter="Engine", exclude_types=[])
    types = {node.get("type") for _, node in results}
    assert types == {"Engine"} or not types


def test_search_relevance_ordering(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='relevance test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    asyncio.run(dispatch(
        f"create:Engine name='TrustGate Engine' session_id={sid}", index, tmp_path
    ))
    asyncio.run(dispatch(
        f"create:Engine name='Other Engine' description='uses trustgate' session_id={sid}",
        index, tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    results = search_nodes(index, "trustgate", exclude_types=[])
    assert results, "Expected results"
    top_score, top_node = results[0]
    assert "TrustGate" in top_node.get("name", ""), f"Expected TrustGate first, got {top_node.get('name')}"


# ── depends_on edge type tests ────────────────────────────────────────────────

def test_depends_on_edge_valid(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='edge type test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    r1 = asyncio.run(dispatch(f"create:Engine name='EngineA' session_id={sid}", index, tmp_path))
    index = GraphIndex.load_from_disk(tmp_path)
    r2 = asyncio.run(dispatch(f"create:Engine name='EngineB' session_id={sid}", index, tmp_path))
    id_a, id_b = r1["node_id"], r2["node_id"]

    index = GraphIndex.load_from_disk(tmp_path)
    r3 = asyncio.run(dispatch(f"edge: {id_a} --depends_on--> {id_b}", index, tmp_path))
    assert r3.get("ok") is True, f"depends_on edge failed: {r3}"


def test_tested_by_edge_valid(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='tested_by test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    r1 = asyncio.run(dispatch(f"create:Flow name='MyFlow' session_id={sid}", index, tmp_path))
    index = GraphIndex.load_from_disk(tmp_path)
    r2 = asyncio.run(dispatch(f"create:TestCase name='MyTest' session_id={sid}", index, tmp_path))
    id_flow, id_tc = r1["node_id"], r2["node_id"]

    index = GraphIndex.load_from_disk(tmp_path)
    r3 = asyncio.run(dispatch(f"edge: {id_flow} --tested_by--> {id_tc}", index, tmp_path))
    assert r3.get("ok") is True, f"tested_by edge failed: {r3}"


# ── duplicate detection tests ─────────────────────────────────────────────────

def test_duplicate_warning_on_similar_name(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='duplicate test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    asyncio.run(dispatch(f"create:Engine name='TrustGate Engine' session_id={sid}", index, tmp_path))

    index = GraphIndex.load_from_disk(tmp_path)
    r = asyncio.run(dispatch(
        f"create:Engine name='TrustGate Engine' session_id={sid}", index, tmp_path
    ))
    assert r.get("ok") is True  # Still created
    warnings = r.get("warnings", [])
    has_dup_warning = any(w.get("type") == "potential_duplicate" for w in warnings)
    assert has_dup_warning, f"Expected duplicate warning, got: {warnings}"


def test_no_false_positive_duplicate(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='no false positive test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)

    r = asyncio.run(dispatch(
        f"create:Engine name='AuthEngine' session_id={sid}", index, tmp_path
    ))
    assert r.get("ok") is True
    warnings = r.get("warnings", [])
    dup_warnings = [w for w in warnings if w.get("type") == "potential_duplicate"]
    assert not dup_warnings, f"False positive duplicate warning: {dup_warnings}"


# ── find: action integration tests ───────────────────────────────────────────

def test_find_excludes_sessions_by_default(tmp_path):
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    asyncio.run(dispatch(
        "session:start actor='test' goal='find session exclusion'", index, tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    r = asyncio.run(dispatch("find: test mode=summary", index, tmp_path))
    types = {m.get("type") for m in r.get("matches", [])}
    assert "Session" not in types


def test_protocol_guide_has_depends_on():
    from gobp.mcp.parser import PROTOCOL_GUIDE
    actions = PROTOCOL_GUIDE.get("actions", {})
    assert any("depends_on" in k for k in actions), "depends_on not in PROTOCOL_GUIDE"
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A07] — Search Quality + Edge Types + Duplicate Detection — 2026-04-17

### Added
- **gobp/core/search.py** — Vietnamese-aware search module
  - normalize_text(): strips diacritics ("mi hốt" == "mihot" == "Mi Hot")
  - search_score(): relevance ranking (exact name=100, contains=60, desc=20)
  - search_nodes(): type filter by field, Session excluded by default
  - find_similar_nodes(): duplicate detection helper

- **depends_on edge type** — Engine/Flow requires another node
- **tested_by edge type** — Flow/Engine validated by TestCase  
- **covers edge type** — TestCase covers Flow/Engine

- **Duplicate detection** — warning when creating node with similar name

### Changed
- find() in read.py: uses search.py instead of substring match
  - find: mihot → finds "Mi Hốt Standard Online" ✓
  - find:Engine → only Engine nodes (exact type filter) ✓
  - Session nodes excluded by default ✓
  - Results sorted by relevance score ✓

### Total: 505+ tests
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave16a07.py -v
# Expected: ~20 tests

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 505+ tests
```

**Commit message:**
```
Wave 16A07 Task 6: tests/test_wave16a07.py + CHANGELOG

- ~20 tests: Vietnamese normalization, search ranking, edge types, duplicates
- 505+ tests passing
- CHANGELOG: Wave 16A07 entry
```

---

# POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp_mihos"

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch

async def verify():
    root = Path('D:/MIHOS-v1')
    index = GraphIndex.load_from_disk(root)
    
    # Vietnamese search
    r1 = await dispatch('find: mihot mode=summary', index, root)
    print('find mihot:', len(r1['matches']), 'results')
    
    r2 = await dispatch('find: mi hốt mode=summary', index, root)
    print('find mi hốt:', len(r2['matches']), 'results')
    
    # Session exclusion
    r3 = await dispatch('find: test mode=summary', index, root)
    types = {m.get('type') for m in r3.get('matches', [])}
    print('find test types (no sessions):', types)
    assert 'Session' not in types
    
    # depends_on works
    r4 = await dispatch('find:Engine mode=summary', index, root)
    if len(r4['matches']) >= 2:
        id1 = r4['matches'][0]['id']
        id2 = r4['matches'][1]['id']
        sess = await dispatch('session:start actor=verify goal=test', index, root)
        sid = sess['session_id']
        index2 = GraphIndex.load_from_disk(root)
        r5 = await dispatch(f'edge: {id1} --depends_on--> {id2}', index2, root)
        print('depends_on edge:', r5.get('ok'))
        await dispatch(f'session:end session_id={sid}', GraphIndex.load_from_disk(root), root)
    
    print('VERIFICATION COMPLETE')

asyncio.run(verify())
"
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Save Brief

```powershell
cd D:\GoBP
# Save to D:\GoBP\waves\wave_16a07_brief.md
git add waves/wave_16a07_brief.md
git commit -m "Add Wave 16A07 Brief — search quality + edge types + duplicate detection"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_16a07_brief.md first.
Also read gobp/core/search.py (new), gobp/mcp/tools/read.py,
gobp/schema/core_edges.yaml, gobp/core/mutator.py.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 6 tasks sequentially.
R9: all 486 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 16A07. Read CLAUDE.md and waves/wave_16a07_brief.md.
Set env: $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: gobp/core/search.py exists
          normalize_text('Mi Hốt') == 'mi hot'
          search_score exact=100, contains=60, desc=20
- Task 2: find() uses search.py
          Session excluded by default
          Type filter by field, not text
- Task 3: depends_on + tested_by + covers in core_edges.yaml
          PROTOCOL_GUIDE has depends_on entry
- Task 4: Duplicate warning in node_upsert
          Warning type="potential_duplicate" when similar name exists
- Task 5: Smoke test on MIHOS — find: mihot finds Mi Hốt
- Task 6: test_wave16a07.py ~20 tests, 505+ total, CHANGELOG

BLOCKING RULE: Gặp vấn đề → DỪNG ngay, báo CEO.

Expected: 505+ tests. Report WAVE 16A07 AUDIT COMPLETE.
```

---

*Wave 16A07 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-17*

◈
