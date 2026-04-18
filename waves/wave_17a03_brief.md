# WAVE 17A03 BRIEF — QUERY ENGINE

**Wave:** 17A03
**Title:** find: group filter, explore: siblings, get: display modes, relationships with reason
**Author:** CTO Chat
**Date:** 2026-04-19
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 7 tasks
**Estimated effort:** 4-6 hours

---

## REFERENCED GOBP NODES

| Node ID | Topic |
|---|---|
| `dec:d004` | GoBP update obligation |
| `dec:d006` | Brief reference nodes |
| `dec:d011` | Graph hygiene |

---

## CONTEXT

Wave 17A01-02 đã hoàn thành schema v2 foundation.
Wave 17A03 là Query Engine — làm cho AI thực sự dùng được schema v2.

**Mục tiêu:**
```
1. find: group filter — top-down + bottom-up
2. explore: hiển thị group path + siblings
3. get: mode=brief/full/debug
4. relationships: hiển thị với reason thay vì outgoing/incoming
5. suggest: group-aware
```

**2 hướng query theo group:**

```
TOP-DOWN (CEO/CTO đặt câu hỏi):
  find: group="Dev"
  → Tất cả nodes thuộc Dev
  find: group="Dev > Infrastructure"
  → Tất cả infrastructure nodes
  find: group="Dev > Infrastructure > Security"
  → Tất cả security nodes

BOTTOM-UP (AI đang build feature):
  explore: authflow.otp.a1b2c3d4
  → Node + group path + siblings (cùng group)
  → "Cùng Security group: Token, Policy, Permission..."
```

---

## CURSOR EXECUTION RULES

R1-R12 (.cursorrules v7).

**Testing:**
- Tasks 1-5: R9-B (module tests only)
- Task 6: R9-A (docs)
- Task 7: R9-C full suite (670+ baseline)

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 591 fast suite passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `gobp/schema/core_nodes.yaml` | v2 schema — group paths |
| 2 | `gobp/mcp/tools/read.py` | Current find/explore/get |
| 3 | `gobp/core/graph.py` | GraphIndex — current query |
| 4 | `gobp/core/indexes.py` | InvertedIndex, AdjacencyIndex |
| 5 | `.cursorrules` v7 | Current rules |

---

# TASKS

---

## TASK 1 — GraphIndex: group indexing

**Goal:** GraphIndex build và query group index khi load.

**File:** `gobp/core/graph.py`

Thêm `_group_index` vào GraphIndex:

```python
class GraphIndex:
    def __init__(self):
        # ... existing ...
        self._group_index: dict[str, list[str]] = {}
        # key = group path (full + prefixes)
        # value = list of node_ids

    def _build_group_index(self) -> None:
        """Build group index for top-down queries."""
        self._group_index.clear()
        for node_id, node in self._nodes.items():
            group = node.get('group', '')
            if not group:
                continue
            # Index full path + all prefixes
            # "Dev > Infrastructure > Security > AuthFlow"
            # → index "Dev", "Dev > Infrastructure",
            #         "Dev > Infrastructure > Security",
            #         "Dev > Infrastructure > Security > AuthFlow"
            parts = [p.strip() for p in group.split('>')]
            for i in range(1, len(parts) + 1):
                prefix = ' > '.join(parts[:i])
                self._group_index.setdefault(prefix, [])
                if node_id not in self._group_index[prefix]:
                    self._group_index[prefix].append(node_id)

    def find_by_group(self, group_path: str,
                      exact: bool = False) -> list[str]:
        """Find node IDs by group path.

        Args:
            group_path: Full or partial group path
            exact: If True, only exact match. If False, prefix match.

        Returns:
            List of node IDs matching the group path.

        Examples:
            find_by_group("Dev > Infrastructure")
            → all nodes with group starting with "Dev > Infrastructure"

            find_by_group("Dev > Infrastructure", exact=True)
            → only nodes with group = "Dev > Infrastructure"
        """
        if exact:
            return list(self._group_index.get(group_path, []))

        # Prefix match — find all groups that start with group_path
        result = []
        normalized = group_path.strip()
        for indexed_path, node_ids in self._group_index.items():
            if (indexed_path == normalized or
                    indexed_path.startswith(normalized + ' >')):
                for nid in node_ids:
                    if nid not in result:
                        result.append(nid)
        return result

    def find_siblings(self, node_id: str) -> list[str]:
        """Find nodes in the same immediate group as node_id."""
        node = self._nodes.get(node_id)
        if not node:
            return []
        group = node.get('group', '')
        if not group:
            return []
        # Get nodes with exact same group, excluding self
        return [
            nid for nid in self._group_index.get(group, [])
            if nid != node_id
        ]

    def get_group_tree(self) -> dict:
        """Get hierarchy of all groups with counts."""
        tree = {}
        for group_path, node_ids in self._group_index.items():
            # Only top-level keys (no >) or direct children
            depth = group_path.count('>')
            if depth == 0:
                tree[group_path] = len(node_ids)
        return tree
```

Update `load_from_disk()` và `add_node()` để build/update group index:
```python
def load_from_disk(self, root: Path) -> 'GraphIndex':
    # ... existing load ...
    self._build_group_index()  # Build after load
    return self

def add_node(self, node: dict) -> None:
    # ... existing add ...
    # Update group index
    group = node.get('group', '')
    node_id = node.get('id', '')
    if group and node_id:
        parts = [p.strip() for p in group.split('>')]
        for i in range(1, len(parts) + 1):
            prefix = ' > '.join(parts[:i])
            self._group_index.setdefault(prefix, [])
            if node_id not in self._group_index[prefix]:
                self._group_index[prefix].append(node_id)
```

**Commit:**
```
Wave 17A03 Task 1: GraphIndex group indexing

- _group_index: prefix-based group path index
- find_by_group(): top-down group queries
- find_siblings(): bottom-up sibling discovery
- get_group_tree(): hierarchy overview
- Index updated on add_node() + rebuilt on load
```

---

## TASK 2 — find: group filter

**Goal:** `find:` action hỗ trợ group filter.

**File:** `gobp/mcp/tools/read.py`

Update `find` handler để parse group filter:

```python
# Supported find: formats:
# find: group="Dev > Infrastructure"
# find: group="Dev" type=Entity
# find: group contains "Security"
# find: type=AuthFlow  (backward compat — still works)
# find: keyword group="Error"  (combined)

def _parse_find_params(query: str) -> dict:
    """Parse find: query params including group filter."""
    params = {}

    # group="..." extract
    group_match = re.search(r'group=["\']([^"\']+)["\']', query)
    if group_match:
        params['group'] = group_match.group(1)
        params['group_exact'] = False

    # group contains "..."
    group_contains = re.search(r'group\s+contains\s+["\']([^"\']+)["\']', query)
    if group_contains:
        params['group_contains'] = group_contains.group(1)

    # type=...
    type_match = re.search(r'type=(\w+)', query)
    if type_match:
        params['type_filter'] = type_match.group(1)

    # Remaining text = keyword search
    clean = re.sub(r'group=["\'][^"\']+["\']', '', query)
    clean = re.sub(r'group\s+contains\s+["\'][^"\']+["\']', '', clean)
    clean = re.sub(r'type=\w+', '', clean).strip()
    if clean:
        params['keyword'] = clean

    return params


def find_nodes(index: GraphIndex, query: str, limit: int = 20) -> dict:
    """Enhanced find with group filter support."""
    params = _parse_find_params(query)
    candidate_ids = None

    # Group filter (top-down)
    if 'group' in params:
        candidate_ids = set(
            index.find_by_group(params['group'],
                               exact=params.get('group_exact', False))
        )

    # Group contains filter
    elif 'group_contains' in params:
        contains = params['group_contains'].lower()
        candidate_ids = set()
        for node_id, node in index.all_nodes_with_id():
            group = node.get('group', '').lower()
            if contains in group:
                candidate_ids.add(node_id)

    # Apply type filter on top of group filter
    if 'type_filter' in params and candidate_ids is not None:
        type_f = params['type_filter']
        candidate_ids = {
            nid for nid in candidate_ids
            if index.get_node(nid, {}).get('type') == type_f
        }

    # Keyword search
    if 'keyword' in params:
        keyword_results = set(index.search_nodes(params['keyword']))
        if candidate_ids is not None:
            candidate_ids = candidate_ids & keyword_results
        else:
            candidate_ids = keyword_results

    # If no filter → return all (with limit)
    if candidate_ids is None:
        candidate_ids = set(index.all_node_ids())

    # Sort by read_order priority
    _PRIORITY = {'foundational': 0, 'important': 1,
                 'reference': 2, 'background': 3}
    nodes = []
    for nid in list(candidate_ids)[:MAX_NODES_SCANNED_PER_QUERY]:
        node = index.get_node(nid)
        if node:
            nodes.append(node)

    nodes.sort(key=lambda n: (
        _PRIORITY.get(n.get('read_order', 'reference'), 2),
        n.get('name', '')
    ))

    return {
        "ok": True,
        "matches": nodes[:limit],
        "count": len(nodes),
        "truncated": len(nodes) > limit,
        "group_filter": params.get('group', params.get('group_contains')),
    }
```

**Response format update:**
```json
{
  "ok": true,
  "group_filter": "Dev > Infrastructure > Security",
  "count": 10,
  "matches": [
    {
      "id": "dev.infra.sec.authflow.otp.a1b2c3d4",
      "name": "OTP Auth Flow",
      "type": "AuthFlow",
      "group": "Dev > Infrastructure > Security > AuthFlow",
      "read_order": "foundational",
      "description_preview": "OTP authentication flow for MIHOS..."
    }
  ]
}
```

**Commit:**
```
Wave 17A03 Task 2: find: group filter support

- find: group="Dev > Infrastructure" → top-down query
- find: group contains "Security" → substring match
- find: group="Dev" type=Entity → combined filter
- Results sorted by read_order priority
- Backward compat: find: keyword still works
```

---

## TASK 3 — explore: group context + siblings

**Goal:** `explore:` trả về group path + siblings.

**File:** `gobp/mcp/tools/read.py`

Update explore response:

```python
def explore_node(index: GraphIndex, node_id: str) -> dict:
    """Explore node with group context and siblings."""
    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    group = node.get('group', '')

    # Get siblings (same group)
    sibling_ids = index.find_siblings(node_id)
    siblings = []
    for sid in sibling_ids[:10]:  # max 10 siblings
        snode = index.get_node(sid)
        if snode:
            siblings.append({
                "id": sid,
                "name": snode.get('name', ''),
                "type": snode.get('type', ''),
                "read_order": snode.get('read_order', ''),
                "description_preview": _get_description_preview(snode)
            })

    # Get relationships with reason
    relationships = _get_relationships(index, node_id)

    # Build group breadcrumb
    breadcrumb = _build_breadcrumb(group)

    return {
        "ok": True,
        "node": _format_node_brief(node),
        "breadcrumb": breadcrumb,
        "group": group,
        "siblings": siblings,
        "siblings_count": len(sibling_ids),
        "relationships": relationships,
    }


def _build_breadcrumb(group: str) -> list[dict]:
    """Build navigable breadcrumb from group path."""
    if not group:
        return []
    parts = [p.strip() for p in group.split('>')]
    crumbs = []
    for i, part in enumerate(parts):
        path = ' > '.join(parts[:i+1])
        crumbs.append({"label": part, "path": path})
    return crumbs
```

**Response format:**
```json
{
  "ok": true,
  "node": {
    "id": "dev.infra.sec.authflow.otp.a1b2c3d4",
    "name": "OTP Auth Flow",
    "type": "AuthFlow",
    "group": "Dev > Infrastructure > Security > AuthFlow",
    "lifecycle": "specified",
    "read_order": "foundational",
    "description": {"info": "OTP auth flow...", "code": ""}
  },
  "breadcrumb": [
    {"label": "Dev",            "path": "Dev"},
    {"label": "Infrastructure", "path": "Dev > Infrastructure"},
    {"label": "Security",       "path": "Dev > Infrastructure > Security"},
    {"label": "AuthFlow",       "path": "Dev > Infrastructure > Security > AuthFlow"}
  ],
  "group": "Dev > Infrastructure > Security > AuthFlow",
  "siblings": [
    {"id": "...", "name": "VNeID Auth Flow", "type": "AuthFlow", ...},
    {"id": "...", "name": "OAuth Flow", "type": "AuthFlow", ...}
  ],
  "siblings_count": 3,
  "relationships": [...]
}
```

**Commit:**
```
Wave 17A03 Task 3: explore: group context + siblings

- breadcrumb: navigable group path
- siblings: nodes in same immediate group
- relationships: with reason field
- Replaces raw outgoing/incoming lists
```

---

## TASK 4 — get: display modes (brief/full/debug)

**Goal:** `get: mode=brief/full/debug` ẩn/hiện fields đúng.

**File:** `gobp/mcp/tools/read.py`

```python
# RAW FIELDS — ẩn trong brief + full
_RAW_FIELDS = {
    '_dispatch', '_protocol', 'revision',
    'content_hash',  # internal only
}

# BRIEF FIELDS — chỉ hiển thị trong brief
_BRIEF_FIELDS = {
    'id', 'name', 'type', 'group',
    'lifecycle', 'read_order',
    'description',  # chỉ description.info
    'relationships',
}


def get_node(index: GraphIndex, node_id: str,
             mode: str = 'brief') -> dict:
    """Get node with display mode.

    Modes:
        brief: name, group, description.info, relationships
        full:  all meaningful fields
        debug: everything including raw
    """
    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    relationships = _get_relationships(index, node_id)

    if mode == 'brief':
        result = {
            "ok": True,
            "mode": "brief",
            "id": node.get('id'),
            "name": node.get('name'),
            "type": node.get('type'),
            "group": node.get('group', ''),
            "lifecycle": node.get('lifecycle', 'draft'),
            "read_order": node.get('read_order', 'reference'),
            "description": {
                "info": _get_info(node),
                # code omitted in brief
            },
            "relationships": relationships,
        }
        # Add type-specific important fields
        result.update(_get_type_important_fields(node))
        return result

    elif mode == 'full':
        result = {"ok": True, "mode": "full"}
        for k, v in node.items():
            if k not in _RAW_FIELDS:
                result[k] = v
        result['relationships'] = relationships
        # Replace description with clean version
        if 'description' in result:
            result['description'] = {
                "info": _get_info(node),
                "code": node.get('description', {}).get('code', '')
                        if isinstance(node.get('description'), dict) else ''
            }
        return result

    else:  # debug
        result = {"ok": True, "mode": "debug"}
        result.update(node)
        result['relationships'] = relationships
        return result


def _get_info(node: dict) -> str:
    """Extract description.info from node."""
    desc = node.get('description', '')
    if isinstance(desc, dict):
        return desc.get('info', '')
    if isinstance(desc, str):
        return desc
    return ''


def _get_type_important_fields(node: dict) -> dict:
    """Get type-specific important fields for brief mode."""
    node_type = node.get('type', '')
    result = {}

    if node_type == 'Invariant':
        for f in ['rule', 'scope', 'enforcement', 'violation_action']:
            if node.get(f):
                result[f] = node[f]

    elif node_type == 'ErrorCase':
        for f in ['code', 'severity', 'trigger']:
            if node.get(f):
                result[f] = node[f]

    elif node_type == 'Decision':
        for f in ['what', 'why']:
            if node.get(f):
                result[f] = node[f][:200]  # truncate

    elif node_type == 'Concept':
        if node.get('definition'):
            result['definition'] = node['definition'][:300]

    return result


def _get_relationships(index: GraphIndex, node_id: str) -> list[dict]:
    """Get relationships with reason field."""
    relationships = []

    # Outgoing edges
    for edge in index.get_outgoing_edges(node_id):
        target_id = edge.get('to', '')
        target = index.get_node(target_id)
        rel = {
            "target_id": target_id,
            "target_name": target.get('name', '') if target else '',
            "target_group": target.get('group', '') if target else '',
            "type": edge.get('type', ''),
            "reason": edge.get('reason', ''),
            "direction": "outgoing",
        }
        relationships.append(rel)

    # Incoming edges
    for edge in index.get_incoming_edges(node_id):
        source_id = edge.get('from', '')
        source = index.get_node(source_id)
        rel = {
            "source_id": source_id,
            "source_name": source.get('name', '') if source else '',
            "source_group": source.get('group', '') if source else '',
            "type": edge.get('type', ''),
            "reason": edge.get('reason', ''),
            "direction": "incoming",
        }
        relationships.append(rel)

    return relationships
```

**Commit:**
```
Wave 17A03 Task 4: get: display modes brief/full/debug

- brief: name, group, description.info, relationships, type-fields
- full: all meaningful fields, no raw metadata
- debug: everything
- relationships: with reason + target/source group
- Type-specific important fields in brief (Invariant.rule, ErrorCase.code...)
```

---

## TASK 5 — suggest: group-aware

**Goal:** `suggest:` aware của group — tránh duplicate trong cùng group.

**File:** `gobp/mcp/tools/read.py`

Update suggest response để thêm group info:

```python
def suggest_nodes(index: GraphIndex, name: str,
                  node_type: str = '', group: str = '') -> dict:
    """Suggest existing nodes before create.

    Group-aware: prioritizes matches in same group.
    """
    candidates = index.search_nodes(name, limit=10)

    results = []
    for node_id, node in candidates:
        match_score = _compute_similarity(name, node.get('name', ''))
        same_group = (group and
                      node.get('group', '').startswith(group))
        same_type = (node_type and
                     node.get('type', '') == node_type)

        results.append({
            "id": node_id,
            "name": node.get('name', ''),
            "type": node.get('type', ''),
            "group": node.get('group', ''),
            "match_score": match_score,
            "same_group": same_group,
            "same_type": same_type,
            "description_preview": _get_info(node)[:100],
            "warning": (
                "HIGH SIMILARITY — consider updating instead of creating"
                if match_score > 0.8 and (same_group or same_type)
                else ""
            )
        })

    # Sort: same group + same type first
    results.sort(key=lambda r: (
        -int(r['same_group'] and r['same_type']),
        -int(r['same_group']),
        -int(r['same_type']),
        -r['match_score']
    ))

    return {
        "ok": True,
        "query": name,
        "group_filter": group,
        "suggestions": results[:5],
        "recommendation": (
            "UPDATE existing node"
            if results and results[0]['match_score'] > 0.8
            else "CREATE new node"
        )
    }
```

**Commit:**
```
Wave 17A03 Task 5: suggest: group-aware dedup

- Prioritizes matches in same group + same type
- HIGH SIMILARITY warning khi score > 0.8
- Recommendation: UPDATE vs CREATE
- Sorted: same-group + same-type first
```

---

## TASK 6 — Cursor tự update .cursorrules v8

**CTO requirements — PHẢI có:**

```
1. Query v2 section (thêm mới):
   find: group="Dev > Infrastructure" → top-down
   find: group contains "Security" → substring
   find: group="Dev" type=Entity → combined
   explore: node_id → breadcrumb + siblings + relationships

2. get: mode section (thêm mới):
   get: node_id mode=brief → name/group/description.info/relationships
   get: node_id mode=full → tất cả fields có nghĩa
   get: node_id mode=debug → tất cả (chỉ debug)
   DEFAULT mode = brief

3. suggest: section (update):
   suggest: name group="Dev > Domain" → group-aware
   Nếu score > 0.8 → UPDATE thay vì CREATE

4. Workflow update:
   Trước khi create node → suggest: với group
   explore: sau khi create → verify siblings/relationships
```

**KHÔNG xóa:** R9-R12, dec:d004, schema v2, ErrorCase naming, v7 rules.

Cursor tự viết nội dung. Báo cáo changes cho CEO.

**Commit:**
```
Wave 17A03 Task 6: .cursorrules v8 — query v2 + display modes
```

---

## TASK 7 — Tests + CHANGELOG + Full Suite

**File:** `tests/test_wave17a03.py` — 20 tests:

```python
# GraphIndex group indexing (6):
#   test_build_group_index()
#   test_find_by_group_prefix()
#   test_find_by_group_exact()
#   test_find_by_group_contains_security()
#   test_find_siblings()
#   test_get_group_tree()

# find: group filter (5):
#   test_find_group_top_down()
#   test_find_group_combined_type()
#   test_find_group_contains()
#   test_find_group_sorted_by_read_order()
#   test_find_backward_compat()

# explore: siblings (3):
#   test_explore_breadcrumb()
#   test_explore_siblings()
#   test_explore_relationships_with_reason()

# get: display modes (4):
#   test_get_mode_brief_hides_raw()
#   test_get_mode_brief_shows_description_info_only()
#   test_get_mode_full_shows_all_meaningful()
#   test_get_mode_debug_shows_everything()

# suggest: group-aware (2):
#   test_suggest_group_aware_same_group_first()
#   test_suggest_high_similarity_warning()
```

**CHANGELOG:**
```markdown
## [Wave 17A03] — Query Engine — 2026-04-19

### Added
- find: group="Dev > Infrastructure" — top-down group queries
- find: group contains "Security" — substring group filter
- find: group + type combined filter
- explore: breadcrumb + siblings + relationships with reason
- get: mode=brief/full/debug display modes
- suggest: group-aware with HIGH SIMILARITY warning

### Changed
- GraphIndex: _group_index for O(1) group queries
- explore: replaces raw outgoing/incoming with relationships
- get: defaults to mode=brief (hides raw fields)
- suggest: sorted by same-group + same-type priority

### Tests: 690+ (670 + 20 new)
```

**Full suite:**
```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --override-ini="addopts=" -q --tb=no
# Expected: 690+ tests
```

**GoBP MCP:**
```
gobp(query="session:start actor='cursor' goal='Wave 17A03 complete'")
gobp(query="session:end outcome='Query engine: group filter, display modes, relationships. 690+ tests.'")
```

**Commit:**
```
Wave 17A03 Task 7: tests + CHANGELOG + full suite — 690+ tests
```

---

# CEO DISPATCH

## Cursor
```
Read gobp/mcp/tools/read.py + gobp/core/graph.py trước.
Read .cursorrules v7 + waves/wave_17a03_brief.md.
Read GoBP MCP: gobp(query="find:Decision mode=summary")

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute Tasks 1-7.
R9-B Tasks 1-5, R9-A Task 6, R9-C Task 7.

KEY GOALS:
  find: group queries — top-down + bottom-up BOTH work
  get: brief = default, hides raw fields
  explore: shows breadcrumb + siblings + reason on edges
  suggest: group-aware, warns high similarity

670 baseline tests PHẢI pass.
GoBP MCP sau mỗi task (dec:d004).
Lesson: suggest: trước khi tạo (dec:d011).
```

## Claude CLI
```
Audit Wave 17A03.
Verify:
  - find: group="Dev > Infrastructure" returns correct nodes
  - find: group contains "Security" works
  - explore: breadcrumb + siblings correct
  - get: mode=brief hides raw fields, shows description.info only
  - get: mode=debug shows everything
  - suggest: group-aware, similarity warning
  - .cursorrules v8: query v2 section, display modes section
  - 690+ tests passing

GoBP MCP session capture. Không cần Lesson node.
```

## Push
```powershell
cd D:\GoBP
git add waves/wave_17a03_brief.md
git commit -m "Add Wave 17A03 Brief — query engine + display modes"
git push origin main
```

---

*Wave 17A03 Brief v1.0 — 2026-04-19*
*References: dec:d004, dec:d006, dec:d011*
*Part of: Wave 17A Series (7 waves)*
◈
