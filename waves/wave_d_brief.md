# WAVE D BRIEF — MCP ACTIONS v3

**Wave:** D  
**Title:** Read Actions v3 — find, get_batch, context:, session:resume, overview:  
**Author:** CTO Chat (Claude Sonnet 4.6)  
**Date:** 2026-04-19  
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)  
**Status:** READY FOR EXECUTION  
**Task count:** 8 atomic tasks  
**Estimated effort:** 6-8 hours  

---

## CONTEXT

Wave A-C đã build foundation + write path. Wave D implements read actions v3:

```
find: v3     — BM25F weighted + BFS depth 1 + inverted group index
get_batch: v3 — description pyramid modes + since= mechanism
context:     — 1 request = full task context (FTS → BFS → bundle)
session:resume — load handoff + changes since prev session
overview: v3 — active_sessions + correct v3 stats
explore: v3  — no DISCOVERED_IN, uses desc_l2
```

Đây là những actions tạo ra giá trị thực sự cho AI:
`context: task=` thay thế 3-5 requests thủ công.
`session:resume` thay thế `overview:` + `recent:` mỗi session mới.

---

## REFERENCED DOCUMENTS

| Doc | Focus |
|---|---|
| `docs/ARCHITECTURE.md` | Section 6 (GraphIndex), BM25F, BFS, Since=, Inverted Group Index |
| `docs/MCP_PROTOCOL.md` | find:, get_batch:, context:, session:resume, overview: |
| `docs/SCHEMA.md` | Description pyramid L1/L2/full |

---

## CURSOR EXECUTION RULES

### R1-R8: Standard (xem `.cursorrules` — QR1-QR7)

### R9 — Testing strategy
- Code tasks: R9-B — module tests only
- Task 7 (tests): R9-B — `pytest tests/test_wave_d.py -v --tb=short`
- End of wave: `pytest tests/ -q --tb=no` (fast suite, NO slow)

### R10: Session start/end (skip graph writes per CEO)
### R11: Report doc changes
### R12: Docs scope

---

## REQUIRED READING — BEFORE TASK 1

| # | File |
|---|---|
| 1 | `.cursorrules` (full — QR1-QR7) |
| 2 | `docs/ARCHITECTURE.md` (Sections 6, 8 — GraphIndex, Pyramid) |
| 3 | `docs/MCP_PROTOCOL.md` (find:, context:, session:resume) |
| 4 | `docs/SCHEMA.md` |
| 5 | `gobp/mcp/tools/read.py` |
| 6 | `gobp/mcp/dispatcher.py` |
| 7 | `gobp/core/graph.py` |
| 8 | `gobp/core/db.py` |
| 9 | `gobp/core/cache.py` |

---

## TASKS

---

## TASK 1 — find: v3

**Goal:** Update `find:` action — BM25F weighted search + BFS expand depth 1 + inverted group index.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `find:` handler và `gobp/core/graph.py` trước.**

### BM25F weighted query

```python
def find_v3(conn, query_text: str, group_filter: str = None,
            mode: str = 'summary', page_size: int = 20,
            cursor: str = None) -> dict:
    """
    find: v3 — BM25F + BFS depth 1 + pyramid response modes.

    Modes:
      compact:  id + name + group             (~10 tokens/node)
      summary:  + desc_l1                     (~15 tokens/node)
      brief:    + desc_l2 + top 3 edges       (~40 tokens/node)
      full:     + desc_full + all edges       (~200+ tokens/node)
    """
    if not query_text.strip():
        return {'ok': False, 'error': 'find: requires a keyword'}

    # BM25F weighted tsvector query
    # Weights: A(name)=3.0, B(group)=2.0, C(desc_l2)=1.0
    sql = """
    WITH seed AS (
        SELECT id, name, group_path, desc_l1, desc_l2,
               ts_rank_cd(search_vec, query,
                          ARRAY[0.5, 1.0, 2.0, 3.0]) AS rank
        FROM nodes,
             plainto_tsquery('simple', %s) AS query
        WHERE search_vec @@ query
          AND (%s IS NULL OR group_path LIKE %s || '%%')
          AND (%s IS NULL OR id > %s)
        ORDER BY rank DESC
        LIMIT %s
    ),
    expanded AS (
        SELECT DISTINCT n.id, n.name, n.group_path,
                        n.desc_l1, n.desc_l2, 0.5 AS rank
        FROM seed s
        JOIN edges e ON e.from_id = s.id OR e.to_id = s.id
        JOIN nodes n ON n.id = CASE
            WHEN e.from_id = s.id THEN e.to_id
            ELSE e.from_id END
        WHERE NOT EXISTS (SELECT 1 FROM seed WHERE id = n.id)
          AND e.from_id != e.to_id
    )
    SELECT id, name, group_path, desc_l1, desc_l2, rank
    FROM seed
    UNION ALL
    SELECT id, name, group_path, desc_l1, desc_l2, rank
    FROM expanded
    ORDER BY rank DESC
    LIMIT %s
    """

    with conn.cursor() as cur:
        cur.execute(sql, (
            query_text, group_filter, group_filter,
            cursor, cursor,
            page_size, page_size + 10
        ))
        rows = cur.fetchall()

    nodes = _format_nodes(rows, mode)
    next_cursor = rows[-1][0] if len(rows) > page_size else None

    return {
        'ok':         True,
        'query':      query_text,
        'mode':       mode,
        'count':      len(nodes[:page_size]),
        'nodes':      nodes[:page_size],
        'next_cursor': next_cursor,
        'hint':       'Use mode=brief for edges context. mode=compact for large result sets.'
    }


def _format_nodes(rows, mode: str) -> list[dict]:
    """Format nodes theo pyramid mode."""
    result = []
    for row in rows:
        node_id, name, group_path, desc_l1, desc_l2, rank = row
        if mode == 'compact':
            result.append({
                'id':    node_id,
                'name':  name,
                'group': group_path,
            })
        elif mode == 'summary':
            result.append({
                'id':    node_id,
                'name':  name,
                'group': group_path,
                'desc':  desc_l1,
            })
        else:  # brief or full — caller handles full desc fetch
            result.append({
                'id':    node_id,
                'name':  name,
                'group': group_path,
                'desc':  desc_l2 if mode == 'brief' else desc_l1,
                '_rank': round(rank, 4),
            })
    return result
```

**Acceptance criteria:**
- `find: PaymentService` → BM25F ranked results, seed + BFS expanded
- `find: payment group='Dev > Infrastructure'` → filtered by group
- `find: auth mode=compact` → id+name+group only (~10 tokens/node)
- `find: auth mode=summary` → + desc_l1
- `find: auth mode=brief` → + desc_l2
- Blank query → error response
- Pagination: `next_cursor` khi có thêm kết quả

**Commit message:**
```
Wave D Task 1: find: v3 — BM25F weighted + BFS expand + pyramid modes
```

---

## TASK 2 — get: + get_batch: v3

**Goal:** Update `get:` và `get_batch:` — description pyramid modes + `since=` mechanism.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `get:` và `get_batch:` handlers trước.**

### get: v3

```python
def get_v3(conn, node_id: str, mode: str = 'brief') -> dict:
    """
    get: v3 với pyramid modes.

    Modes:
      brief:  name + group + desc_l2 + top edges  (~40 tokens)
      full:   name + group + desc_full + all edges (~200+ tokens)
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, group_path, desc_l1, desc_l2,
                   desc_full, code, severity, updated_at
            FROM nodes WHERE id = %s
        """, (node_id,))
        row = cur.fetchone()

    if not row:
        return {'ok': False, 'error': f'Node not found: {node_id}'}

    node_id, name, group_path, l1, l2, full, code, severity, updated_at = row

    desc = l2 if mode == 'brief' else full

    # Fetch edges (filter DISCOVERED_IN)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e.from_id, e.to_id, e.reason,
                   nf.name as from_name, nt.name as to_name
            FROM edges e
            LEFT JOIN nodes nf ON nf.id = e.from_id
            LEFT JOIN nodes nt ON nt.id = e.to_id
            WHERE (e.from_id = %s OR e.to_id = %s)
            LIMIT %s
        """, (node_id, node_id, 5 if mode == 'brief' else 50))
        edge_rows = cur.fetchall()

    edges = [
        {
            'from':   r[0], 'to': r[1],
            'reason': r[2] or '',
            'label':  f"{r[3]} → {r[4]}",
        }
        for r in edge_rows
        if r[2]  # chỉ edges có reason
    ]

    result = {
        'ok':         True,
        'id':         node_id,
        'name':       name,
        'group':      group_path,
        'description': desc,
        'updated_at': updated_at,
        'edges':      edges,
    }
    if code:
        result['code'] = code
    if severity:
        result['severity'] = severity

    return result
```

### get_batch: v3 với since=

```python
def get_batch_v3(conn, ids: list[str],
                 mode: str = 'brief',
                 since: int | None = None) -> dict:
    """
    get_batch: v3 với since= differential fetch.

    since= (unix timestamp): unchanged nodes = {id, unchanged: true}
    → Tiết kiệm ~70% tokens trên session thứ 2+
    """
    if not ids:
        return {'ok': False, 'error': 'ids is required'}

    results = {}

    if since is not None:
        # Differential fetch: check updated_at first
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, updated_at FROM nodes WHERE id = ANY(%s)",
                (ids,)
            )
            ts_map = {r[0]: r[1] for r in cur.fetchall()}

        changed_ids = []
        for node_id in ids:
            ts = ts_map.get(node_id)
            if ts is None or ts <= since:
                results[node_id] = {'id': node_id, 'unchanged': True}
            else:
                changed_ids.append(node_id)
        ids = changed_ids

    # Fetch changed nodes
    for node_id in ids:
        results[node_id] = get_v3(conn, node_id, mode)

    return {
        'ok':      True,
        'mode':    mode,
        'since':   since,
        'nodes':   results,
        'summary': {
            'total':     len(results),
            'unchanged': sum(1 for v in results.values()
                             if v.get('unchanged')),
            'fetched':   len(ids),
        }
    }
```

**Acceptance criteria:**
- `get: id mode=brief` → desc_l2, top 5 edges với reason, no DISCOVERED_IN
- `get: id mode=full` → desc_full, all edges
- `get_batch: ids='a,b,c'` → 3 nodes
- `get_batch: ids='a,b,c' since=1234567890` → unchanged nodes = `{unchanged: true}`
- Summary shows total/unchanged/fetched counts
- Non-existent node → `{ok: false, error: ...}`

**Commit message:**
```
Wave D Task 2: get: + get_batch: v3 — pyramid modes + since= differential fetch
```

---

## TASK 3 — context: task= action

**Goal:** Implement `context:` action — 1 request = full task context.

**File to modify:** `gobp/mcp/tools/read.py`

**Đây là action quan trọng nhất — thay thế 3-5 requests thủ công.**

```python
def context_action(conn, task_description: str,
                   max_nodes: int = 15) -> dict:
    """
    context: task='...' — bundle full task context trong 1 request.

    Server tự làm:
      1. FTS search với task description
      2. BFS expand depth 2
      3. Deduplicate + rank
      4. Return bundled context

    Thay thế: find: + get_batch: + related: = 3-5 requests
    Token cost: ~400-600 (đủ context cho 1 task)
    """
    if not task_description.strip():
        return {'ok': False, 'error': 'task description is required'}

    # Step 1: FTS seed nodes
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, group_path, desc_l2,
                   ts_rank_cd(search_vec,
                              plainto_tsquery('simple', %s),
                              ARRAY[0.5, 1.0, 2.0, 3.0]) AS rank
            FROM nodes,
                 plainto_tsquery('simple', %s) AS query
            WHERE search_vec @@ query
            ORDER BY rank DESC
            LIMIT 10
        """, (task_description, task_description))
        seed_rows = cur.fetchall()

    if not seed_rows:
        return {
            'ok':    True,
            'task':  task_description,
            'nodes': [],
            'hint':  'No matching context found. Try broader keywords.'
        }

    seed_ids = [r[0] for r in seed_rows]

    # Step 2: BFS expand depth 2
    with conn.cursor() as cur:
        cur.execute("""
            WITH depth1 AS (
                SELECT DISTINCT
                    CASE WHEN e.from_id = ANY(%s) THEN e.to_id
                         ELSE e.from_id END AS id,
                    e.reason
                FROM edges e
                WHERE (e.from_id = ANY(%s) OR e.to_id = ANY(%s))
                  AND e.reason IS NOT NULL AND e.reason != ''
            ),
            depth2 AS (
                SELECT DISTINCT
                    CASE WHEN e.from_id = d.id THEN e.to_id
                         ELSE e.from_id END AS id,
                    e.reason
                FROM edges e
                JOIN depth1 d ON e.from_id = d.id OR e.to_id = d.id
                WHERE e.reason IS NOT NULL AND e.reason != ''
            )
            SELECT DISTINCT n.id, n.name, n.group_path, n.desc_l2
            FROM nodes n
            WHERE n.id IN (SELECT id FROM depth1
                           UNION SELECT id FROM depth2)
              AND n.id != ALL(%s)
            LIMIT %s
        """, (seed_ids, seed_ids, seed_ids, seed_ids, max_nodes - len(seed_ids)))
        expanded_rows = cur.fetchall()

    # Step 3: Build context bundle
    nodes = []

    # Seed nodes (higher relevance)
    for row in seed_rows:
        nodes.append({
            'id':       row[0],
            'name':     row[1],
            'group':    row[2],
            'desc':     row[3],
            'relevance': 'seed',
        })

    # Expanded nodes (related context)
    for row in expanded_rows:
        nodes.append({
            'id':       row[0],
            'name':     row[1],
            'group':    row[2],
            'desc':     row[3],
            'relevance': 'related',
        })

    return {
        'ok':    True,
        'task':  task_description,
        'nodes': nodes[:max_nodes],
        'summary': {
            'seed':    len(seed_rows),
            'related': len(expanded_rows),
            'total':   min(len(nodes), max_nodes),
        },
        'hint': (
            'Context loaded. Seed nodes are direct matches. '
            'Related nodes are discovered via edges.'
        )
    }
```

**Acceptance criteria:**
- `context: task='implement payment flow'` → returns seed + related nodes
- Seed nodes = FTS matches
- Related nodes = BFS depth 2 qua edges có reason
- Không include nodes không có edges (isolated)
- Empty task → error
- No matches → `{ok: true, nodes: [], hint: ...}`

**Commit message:**
```
Wave D Task 3: context: action — FTS + BFS depth 2 bundled context
```

---

## TASK 4 — session:resume

**Goal:** Implement `session:resume` — load prev session handoff + changes since.

**File to modify:** `gobp/mcp/tools/write.py`

**Re-read `session:` handler trước.**

```python
def session_resume(conn, session_id: str) -> dict:
    """
    session:resume id='...'

    Thay thế: overview: + recent: = ~1,500 tokens
    Token savings: ~70%

    Returns:
      - prev session outcome + handoff
      - nodes changed since prev session ended
      - new session_id để tiếp tục
    """
    # Load prev session
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, desc_full, updated_at
            FROM nodes
            WHERE id = %s AND group_path LIKE 'Meta > Session%%'
        """, (session_id,))
        row = cur.fetchone()

    if not row:
        return {
            'ok':    False,
            'error': f'Session not found: {session_id}',
            'hint':  'Use overview: to start a new session'
        }

    prev_id, prev_name, prev_desc, prev_updated_at = row

    # Find nodes changed since prev session
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, group_path, desc_l1
            FROM nodes
            WHERE updated_at > %s
              AND group_path NOT LIKE 'Meta > Session%%'
            ORDER BY updated_at DESC
            LIMIT 20
        """, (prev_updated_at,))
        changed_rows = cur.fetchall()

    changed_nodes = [
        {'id': r[0], 'name': r[1], 'group': r[2], 'desc': r[3]}
        for r in changed_rows
    ]

    return {
        'ok':          True,
        'resumed_from': session_id,
        'prev_outcome': prev_desc or '(no outcome recorded)',
        'changes_since': changed_nodes,
        'changes_count': len(changed_nodes),
        'hint': (
            'Start new session with session:start. '
            'Changes since your last session are listed above.'
        )
    }
```

**Acceptance criteria:**
- `session:resume id='meta.session.2026-04-19.xxx'` → prev outcome + changed nodes
- Non-existent session → error + hint to use `overview:`
- Returns nodes changed since prev session ended
- Session nodes filtered out from changes list

**Commit message:**
```
Wave D Task 4: session:resume — load prev handoff + changes since last session
```

---

## TASK 5 — overview: v3

**Goal:** Update `overview:` — active sessions + correct v3 stats.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `gobp_overview()` trước.**

Update overview response:

```python
def overview_v3(conn, project_root, full_interface: bool = False) -> dict:
    """overview: v3 — correct stats + active sessions."""

    # Node stats from v3 schema
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM nodes")
        total_nodes = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM edges")
        total_edges = cur.fetchone()[0]

        # Nodes by top-level group
        cur.execute("""
            SELECT split_part(group_path, ' > ', 1) AS top_group,
                   COUNT(*) AS cnt
            FROM nodes
            GROUP BY top_group
            ORDER BY cnt DESC
        """)
        nodes_by_group = {r[0]: r[1] for r in cur.fetchall()}

        # Active sessions (IN_PROGRESS)
        cur.execute("""
            SELECT id, name, desc_l1, updated_at
            FROM nodes
            WHERE group_path = 'Meta > Session'
              AND desc_full LIKE '%%IN_PROGRESS%%'
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        active_rows = cur.fetchall()

    active_sessions = [
        {
            'session_id': r[0],
            'goal':       r[1][:80],
            'started':    r[3],
        }
        for r in active_rows
    ]

    # Load project config
    import yaml
    config_path = project_root / '.gobp' / 'config.yaml'
    config = {}
    if config_path.exists():
        with open(config_path, encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

    result = {
        'ok': True,
        'project': {
            'name':           config.get('project_name', project_root.name),
            'id':             config.get('project_id', ''),
            'root':           str(project_root),
            'schema_version': 'v3',
        },
        'stats': {
            'total_nodes':    total_nodes,
            'total_edges':    total_edges,
            'nodes_by_group': nodes_by_group,
        },
        'active_sessions': active_sessions,
        'hint': (
            'Use session:start to begin. '
            'Use session:resume id=\'...\' to continue a previous session.'
        )
    }

    return result
```

**Acceptance criteria:**
- `overview:` → project name, schema_version: v3, node/edge counts
- `nodes_by_group` dùng top-level group breadcrumb (không phải type)
- `active_sessions` hiển thị IN_PROGRESS sessions
- Không có legacy fields: lifecycle, read_order, priority

**Commit message:**
```
Wave D Task 5: overview: v3 — active_sessions + v3 schema stats
```

---

## TASK 6 — explore: v3

**Goal:** Update `explore:` — dùng desc_l2, filter DISCOVERED_IN, sử dụng v3 schema.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `explore:` handler trước.**

Thay đổi cần thiết:
1. Description: dùng `desc_l2` thay vì legacy field
2. Edges: filter DISCOVERED_IN
3. Chỉ hiển thị edges có `reason` không rỗng
4. Siblings: tìm theo `group_path` (không phải `type`)

```python
def explore_v3(conn, keyword: str) -> dict:
    """
    explore: v3 — best-match node + edges + siblings.
    Filters: no DISCOVERED_IN, no empty reasons.
    """
    # Find best match
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, group_path, desc_l2, desc_full, code, severity
            FROM nodes,
                 plainto_tsquery('simple', %s) AS query
            WHERE search_vec @@ query
            ORDER BY ts_rank_cd(search_vec, query,
                                ARRAY[0.5, 1.0, 2.0, 3.0]) DESC
            LIMIT 1
        """, (keyword,))
        row = cur.fetchone()

    if not row:
        return {'ok': False, 'error': f'No match for: {keyword}'}

    node_id, name, group_path, desc_l2, desc_full, code, severity = row

    # Edges — filter DISCOVERED_IN + empty reasons
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e.from_id, e.to_id, e.reason,
                   nf.name, nt.name
            FROM edges e
            LEFT JOIN nodes nf ON nf.id = e.from_id
            LEFT JOIN nodes nt ON nt.id = e.to_id
            WHERE (e.from_id = %s OR e.to_id = %s)
              AND e.reason IS NOT NULL
              AND e.reason != ''
            LIMIT 20
        """, (node_id, node_id))
        edge_rows = cur.fetchall()

    edges = [
        {
            'direction': '→' if r[0] == node_id else '←',
            'other_id':  r[1] if r[0] == node_id else r[0],
            'other_name': r[4] if r[0] == node_id else r[3],
            'reason':    r[2],
        }
        for r in edge_rows
    ]

    # Siblings (same group)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, desc_l1
            FROM nodes
            WHERE group_path = %s AND id != %s
            LIMIT 5
        """, (group_path, node_id))
        sibling_rows = cur.fetchall()

    siblings = [
        {'id': r[0], 'name': r[1], 'desc': r[2]}
        for r in sibling_rows
    ]

    result = {
        'ok':       True,
        'id':       node_id,
        'name':     name,
        'group':    group_path,
        'desc':     desc_l2,
        'edges':    edges,
        'siblings': siblings,
    }
    if code:
        result['code'] = code
    if severity:
        result['severity'] = severity

    return result
```

**Acceptance criteria:**
- `explore: PaymentService` → node + edges (no DISCOVERED_IN, no empty reasons)
- Siblings = nodes với cùng `group_path`
- Edges chỉ hiển thị khi có `reason`
- desc dùng `desc_l2` (không phải legacy description.info)

**Commit message:**
```
Wave D Task 6: explore: v3 — no DISCOVERED_IN, desc_l2, group-based siblings
```

---

## TASK 7 — Tests Wave D

**Goal:** Tests cover find:, get_batch:, context:, session:resume, overview:, explore:.

**File to create:** `tests/test_wave_d.py`

Tests phải cover:

**find: v3:**
- BM25F kết quả: name match rank cao hơn description match
- BFS expand: related nodes được include
- Group filter hoạt động
- mode=compact/summary/brief trả về đúng fields
- Blank query → error
- Pagination: next_cursor có khi có thêm kết quả

**get_batch: v3:**
- mode=brief → desc_l2, filtered edges
- since= unchanged → `{unchanged: true}`
- since= changed → full data
- Summary counts đúng

**context: task=:**
- Trả về seed + related nodes
- Không include isolated nodes
- Empty task → error

**session:resume:**
- Trả về prev outcome + changed nodes
- Non-existent → error + hint

**overview: v3:**
- nodes_by_group dùng top-level group
- active_sessions có IN_PROGRESS sessions
- project.schema_version = 'v3'

**explore: v3:**
- Không có DISCOVERED_IN edges
- Không có empty reasons
- Siblings có cùng group_path

**Acceptance criteria:**
- Tất cả behaviors trên có test coverage
- Tests dùng `tmp_path` + synthetic data (không dùng live DB)
- Existing tests không bị regression

**Commit message:**
```
Wave D Task 7: tests/test_wave_d.py — read actions v3 coverage
```

---

## TASK 8 — CHANGELOG Update

**Goal:** Update `CHANGELOG.md` với Wave C + Wave D entries.

**File to modify:** `CHANGELOG.md`

**Re-read CHANGELOG.md trước.**

Prepend:

```markdown
## [Wave D] — MCP Read Actions v3 — 2026-04-19

### Added
- `find: v3`: BM25F weighted search + BFS expand depth 1 + pyramid modes
- `get_batch: v3`: pyramid modes + since= differential fetch (~70% token savings)
- `context: task=`: FTS + BFS depth 2 → bundled context (1 request)
- `session:resume`: load prev handoff + changes since last session
- `overview: v3`: active_sessions + correct v3 group stats
- `explore: v3`: no DISCOVERED_IN, desc_l2, group-based siblings
- `tests/test_wave_d.py`: read actions v3 coverage

---

## [Wave C] — Write Path v3 + Viewer UI Overhaul — 2026-04-19

### Added
- `gobp/core/mutator_v3.py`: full write path (validate→pyramid→PG→file→log)
- `gobp/core/db.py`: upsert_node_v3, delete_node_v3, upsert_edge_v3, etc.
- `gobp/core/cache.py`: invalidate_node() + invalidate_edge()
- `edit:` action: delete+create semantic, edge ops, history inherit
- Optimistic locking: conflict_warning on updated_at mismatch
- `tests/test_wave_c.py`: write path v3 coverage

### Viewer
- Removed: LIFECYCLE + READ ORDER sidebar filters
- Hidden: DISCOVERED_IN edges from relationships panel
- Hidden: empty reasons, lifecycle, read_order from detail panel
- Updated: node colors by top-level group
- Updated: font + hierarchy clarity

---
```

**Verification (R9-A):**
- CHANGELOG.md có Wave D + Wave C entries ở đầu file

**Commit message:**
```
Wave D Task 8: CHANGELOG.md — Wave C + Wave D entries
```

---

## POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# Test new actions
python -c "
from gobp.mcp.tools.read import context_action, find_v3
print('context: action available')
print('find: v3 available')
"

# Fast suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

---

## CEO DISPATCH INSTRUCTIONS

### 1. Cursor

```
Read .cursorrules (full).
Read docs/ARCHITECTURE.md (Sections 6, 8), docs/MCP_PROTOCOL.md, docs/SCHEMA.md.
Read gobp/mcp/tools/read.py, gobp/mcp/tools/write.py, gobp/mcp/dispatcher.py.
Read gobp/core/graph.py, gobp/core/db.py, gobp/core/cache.py.
Read waves/wave_d_brief.md (this file).

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
Execute Tasks 1 → 8 sequentially.
R9-B: module tests only per task.
Task 7: pytest tests/test_wave_d.py -v --tb=short
End: pytest tests/ -q --tb=no (fast suite, NO slow)
```

### 2. Claude CLI audit

```
Audit Wave D.
Task 1: find: BM25F ranked, BFS expanded, modes correct
Task 2: get_batch: since= differential, unchanged nodes = {unchanged:true}
Task 3: context: bundles seed + related, 1 request
Task 4: session:resume returns prev outcome + changed nodes
Task 5: overview: has active_sessions + v3 group stats
Task 6: explore: no DISCOVERED_IN, no empty reasons
Task 7: all behaviors covered, no regression
Task 8: CHANGELOG has Wave C + D entries
BLOCKING: Bất kỳ fail → STOP, báo CEO.
```

### 3. Push (sau khi audit PASS)

```powershell
cd D:\GoBP
git add waves/wave_d_brief.md
git commit -m "Wave D Brief: MCP Read Actions v3 — 8 tasks"
git push origin main
```

---

*Wave D Brief — MCP Read Actions v3*  
*2026-04-19 — CTO Chat*  
◈
