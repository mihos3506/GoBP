# WAVE 10B BRIEF — FIX + PRIORITY + EDGE INTERFACE + IMPORT ENHANCEMENT

**Wave:** 10B
**Title:** Bug fixes + priority field + semantic edges + import enhancement + auto-classify
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 10 atomic tasks
**Estimated effort:** 5-6 hours

---

## CONTEXT

Wave 8B Phase 2 exposed 6 bugs and 4 missing features. This wave fixes all of them.

**Bugs found in Phase 2:**

| # | Bug | Impact |
|---|---|---|
| B1 | Session ID truncated at 40 chars | Sessions not queryable by full ID |
| B2 | Unicode in descriptions stored as escaped (`\xE2...`) instead of UTF-8 | Unreadable content |
| B3 | `import:` creates 0 nodes — no auto-extraction | Manual work required |
| B4 | `create:` requires AI to specify ID manually | Error-prone, inconsistent IDs |
| B5 | No Document nodes created during import | Docs not tracked in graph |
| B6 | All edges are `discovered_in` only — no semantic edges | Graph not connected semantically |

**Missing features:**

| # | Feature | Value |
|---|---|---|
| F1 | `priority` field on all nodes | Know what's critical vs low |
| F2 | Auto-classify priority on import | AI assigns priority from content |
| F3 | Edge creation via `gobp()` interface | Connect nodes semantically |
| F4 | `gobp_overview` priority summary | See project health at a glance |

---

## DESIGN DECISIONS (locked)

### Session ID format
```
Old: session:<YYYY-MM-DD>_<slug> (slug truncated at 40 chars total)
New: session:<YYYY-MM-DD>_<6-char-hash> (always exactly 28 chars)
Example: session:2026-04-15_a3f7c2
```
Hash from first 6 chars of UUID. Short, unique, never truncated.

### Unicode encoding
All string fields written with `ensure_ascii=False` in YAML dump.
Vietnamese text stored as UTF-8, not escaped.

### Priority field
```yaml
priority:
  type: enum
  values: [critical, high, medium, low]
  default: medium
  description: "Importance level for this node"
```
Added as optional field to all Node types in schema v2.

### Auto-classify rules (deterministic, no AI)
```
Document contains: user flows, auth, payment, proof of presence → critical
Document contains: entities, engines, architecture, API → high
Document contains: design, copy, admin, analytics → medium
Document contains: mascot, growth, future phase → low
```

### Edge creation protocol
```
gobp(query="edge: node:a --relates_to--> node:b")
gobp(query="edge: node:flow_auth --implements--> node:pop_protocol")
gobp(query="edge: node:engine_trustgate --implements--> node:flow_trustgate")
```

### Import enhancement
`import:` now:
1. Creates Document node for the file
2. Reads file content
3. Auto-classifies priority
4. Returns structured proposal with extracted sections
5. AI can then `create:` nodes from proposal

---

## CURSOR EXECUTION RULES

### R1 — Sequential execution
Tasks 1 → 10 in order.

### R2 — Discovery before creation
Explorer subagent before any file creation/modification.

### R3 — 1 task = 1 commit
Tests pass → commit with exact message.

### R4 — Docs are supreme authority
Conflict with `docs/MCP_TOOLS.md` → docs win, STOP.

### R5 — Document disagreement = STOP

### R6 — 3 retries = STOP

### R7 — No scope creep
Fix exactly what Brief specifies.

### R8 — Brief code is authoritative

### R9 — Backward compatibility mandatory
All 236 existing tests must pass after every task.

---

## STOP REPORT FORMAT

```
STOP — Wave 10B Task <N>
Rule triggered: R<N>
Completed: Tasks 1–<N-1>
Current: Task <N> — <title>
What went wrong: <exact error>
Git state: staged=<list> unstaged=<list>
Need: <question>
```

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 236 tests passing
```

---

## REQUIRED READING — WAVE START

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/core/mutator.py` | Session ID generation (B1 fix) |
| 3 | `gobp/core/init.py` | Seed node encoding (B2 fix) |
| 4 | `gobp/mcp/dispatcher.py` | Add edge + import enhancement |
| 5 | `gobp/schema/core_nodes.yaml` | Add priority field |
| 6 | `gobp/mcp/tools/read.py` | gobp_overview priority summary |
| 7 | `docs/MCP_TOOLS.md` | Update with edge protocol |
| 8 | `waves/wave_10b_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Fix B1: Session ID truncation

**Goal:** Session IDs never truncated. Use short hash format.

**File to modify:** `gobp/core/mutator.py`

**Re-read `mutator.py` in full before editing.**

Find `session_log()` or wherever session ID is generated. Replace slug generation with:

```python
import uuid as _uuid

def _generate_session_id(goal: str = "") -> str:
    """Generate short, unique session ID.
    
    Format: session:YYYY-MM-DD_XXXXXX
    where XXXXXX = first 6 chars of UUID4 hex
    Never truncated, always exactly 28 chars.
    """
    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    short_hash = _uuid.uuid4().hex[:6]
    return f"session:{date_str}_{short_hash}"
```

Replace all places where session ID slug is derived from goal string.

**Verify:**
```powershell
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.mutator import _generate_session_id
for _ in range(5):
    sid = _generate_session_id('MIHOS Phase 2: import all 32 docs from mihos-shared/doc')
    assert len(sid) == 28, f'Wrong length: {len(sid)} — {sid}'
    print(sid)
"
```

**Acceptance criteria:**
- Session IDs always exactly 28 chars: `session:YYYY-MM-DD_XXXXXX`
- Never truncated regardless of goal length
- Unique (UUID-based)

**Commit message:**
```
Wave 10B Task 1: fix session ID truncation — use UUID hash format

- _generate_session_id(): session:YYYY-MM-DD_XXXXXX (always 28 chars)
- UUID4 hex[:6] ensures uniqueness without length dependency on goal
- Fixes B1: session IDs truncated when goal string was long
```

---

## TASK 2 — Fix B2: Unicode encoding in node files

**Goal:** Vietnamese and special characters stored as UTF-8, not escaped.

**Files to modify:** `gobp/core/mutator.py`, `gobp/core/init.py`

**Re-read both files in full.**

**In `mutator.py`:** Find all `yaml.dump()` or `yaml.safe_dump()` calls. Ensure `allow_unicode=True`:

```python
# Wrong:
yaml.safe_dump(node, default_flow_style=False)

# Correct:
yaml.safe_dump(node, default_flow_style=False, allow_unicode=True)
```

**In `init.py`:** Same fix for `_seed_universal_nodes()` YAML writes.

**Also fix file writes:** Ensure all `.write_text()` calls use `encoding="utf-8"`.

**Verify:**
```powershell
D:/GoBP/venv/Scripts/python.exe -c "
import yaml, tempfile
from pathlib import Path

node = {
    'id': 'node:test',
    'type': 'Node',
    'name': 'Test',
    'description': 'Xây dựng cơ chế xác thực hiện diện không thể làm giả.',
}
fm = yaml.safe_dump(node, allow_unicode=True, default_flow_style=False)
print(fm)
assert 'Xây dựng' in fm, 'Vietnamese text should be readable'
print('Unicode OK')
"
```

**Acceptance criteria:**
- Vietnamese text in description stored as `Xây dựng...` not `\xE2\x1EF1...`
- All YAML writes use `allow_unicode=True`
- All file writes use `encoding='utf-8'`

**Commit message:**
```
Wave 10B Task 2: fix Unicode encoding — allow_unicode=True in all YAML writes

- mutator.py: all yaml.safe_dump() calls use allow_unicode=True
- init.py: seed nodes use allow_unicode=True
- All file writes use encoding='utf-8'
- Fixes B2: Vietnamese text stored as escaped bytes
```

---

## TASK 3 — Fix B4: Auto-generate node ID in create action

**Goal:** `create:` action auto-generates node ID if not provided by AI.

**File to modify:** `gobp/mcp/dispatcher.py`

**Re-read `dispatcher.py` create handler in full.**

Find `elif action == "create":` block. Add ID generation:

```python
elif action == "create":
    node_type = node_type or params.pop("type", "Node")
    
    # Auto-generate ID if not provided
    node_id = params.pop("id", params.pop("node_id", None))
    if not node_id:
        import uuid as _uuid
        from datetime import datetime, timezone
        type_prefix = _get_type_prefix(node_type)
        short_hash = _uuid.uuid4().hex[:6]
        node_id = f"{type_prefix}:{short_hash}"
    
    args = {
        "node_id": node_id,
        "type": node_type,
        "name": params.get("name", ""),
        "fields": {k: v for k, v in params.items() if k not in ("name", "type", "session_id")},
        "session_id": params.get("session_id", ""),
    }
    result = tools_write.node_upsert(index, project_root, args)
```

**Add helper function:**

```python
def _get_type_prefix(node_type: str) -> str:
    """Get ID prefix for node type."""
    prefix_map = {
        "Node": "node",
        "Idea": "idea",
        "Decision": "dec",
        "Session": "session",
        "Document": "doc",
        "Lesson": "lesson",
        "Concept": "concept",
        "TestKind": "testkind",
        "TestCase": "tc",
    }
    return prefix_map.get(node_type, "node")
```

**Acceptance criteria:**
- `create:Idea name='test' session_id='x'` works without specifying ID
- Auto-generated ID format: `idea:a3f7c2` (type-prefix + 6-char hash)
- Explicit ID still works if provided: `create:Idea id='idea:my_idea' name='test'`

**Commit message:**
```
Wave 10B Task 3: dispatcher create action auto-generates node ID

- _get_type_prefix(): maps NodeType to id prefix
- create: action: auto-generates id:XXXXXX if not provided
- Explicit id= still respected if provided
- Fixes B4: AI had to manually specify IDs
```

---

## TASK 4 — Add priority field to schema

**Goal:** All nodes can have optional `priority` field.

**File to modify:** `gobp/schema/core_nodes.yaml`

**Re-read `core_nodes.yaml` in full.**

In the `Node` type definition, add to `optional` fields:

```yaml
      priority:
        type: "enum"
        enum_values: ["critical", "high", "medium", "low"]
        default: "medium"
        description: "Importance level: critical=must have, high=important, medium=standard, low=nice to have"
```

Add same `priority` optional field to: `Idea`, `Decision`, `Document`, `Lesson`, `Concept`.

**Verify:**
```powershell
D:/GoBP/venv/Scripts/python.exe -c "
import yaml
schema = yaml.safe_load(open('gobp/schema/core_nodes.yaml', encoding='utf-8'))
node_type = schema['node_types']['Node']
assert 'priority' in node_type['optional'], 'priority field missing from Node'
print('Priority field added to schema')
"
```

**Commit message:**
```
Wave 10B Task 4: add priority field to schema

- Node, Idea, Decision, Document, Lesson, Concept: add optional priority field
- Enum: critical | high | medium | low (default: medium)
- Enables: create:Node name='x' priority='critical'
```

---

## TASK 5 — Add edge creation to dispatcher

**Goal:** `edge:` action creates semantic edges between nodes.

**File to modify:** `gobp/mcp/dispatcher.py`

**Protocol:**
```
gobp(query="edge: node:a --relates_to--> node:b")
gobp(query="edge: node:flow_auth --implements--> node:pop_protocol reason='auth flow implements PoP'")
gobp(query="edge: node:engine_trustgate --implements--> node:flow_trustgate")
```

**Add to `parse_query()`** — handle `edge:` format:

The `--edge_type-->` pattern needs special parsing. Add before generic kv parsing:

```python
    # Special case: edge: from_id --type--> to_id
    if action == "edge":
        edge_pattern = re.compile(
            r"^([\w:]+)\s+--(\w+)-->\s+([\w:]+)(.*)?$"
        )
        m = edge_pattern.match(rest)
        if m:
            params["from"] = m.group(1).strip()
            params["edge_type"] = m.group(2).strip()
            params["to"] = m.group(3).strip()
            # Parse remaining key=value pairs
            extra = m.group(4).strip() if m.group(4) else ""
            if extra:
                for km in re.finditer(r"(\w+)='([^']*)'|(\w+)=(\S+)", extra):
                    if km.group(1):
                        params[km.group(1)] = km.group(2)
                    elif km.group(3):
                        params[km.group(3)] = km.group(4)
        return action, "", params
```

**Add to `dispatch()`** — handle `edge` action:

```python
        elif action == "edge":
            from_id = params.get("from", "")
            to_id = params.get("to", "")
            edge_type = params.get("edge_type", "relates_to")
            reason = params.get("reason", "")
            
            if not from_id or not to_id:
                result = {
                    "ok": False,
                    "error": "edge: requires format: node:a --edge_type--> node:b",
                    "hint": "Example: gobp(query=\"edge: node:flow_auth --implements--> node:pop_protocol\")",
                }
            else:
                from gobp.core.mutator import create_edge
                from gobp.core.loader import load_schema
                from pathlib import Path as _Path
                schema_dir = project_root / "gobp" / "schema"
                edges_schema = load_schema(schema_dir / "core_edges.yaml")
                
                edge = {
                    "from": from_id,
                    "to": to_id,
                    "type": edge_type,
                }
                if reason:
                    edge["reason"] = reason
                
                # Validate both nodes exist
                from_node = index.get_node(from_id)
                to_node = index.get_node(to_id)
                if not from_node:
                    result = {"ok": False, "error": f"Node not found: {from_id}"}
                elif not to_node:
                    result = {"ok": False, "error": f"Node not found: {to_id}"}
                else:
                    try:
                        create_edge(
                            gobp_root=project_root,
                            edge=edge,
                            schema=edges_schema,
                            actor="gobp-dispatcher",
                            edge_file_name="semantic_edges.yaml",
                        )
                        result = {
                            "ok": True,
                            "edge_created": {
                                "from": from_id,
                                "from_name": from_node.get("name", ""),
                                "type": edge_type,
                                "to": to_id,
                                "to_name": to_node.get("name", ""),
                            }
                        }
                    except Exception as e:
                        result = {"ok": False, "error": str(e)}
```

**Update PROTOCOL_GUIDE** — add edge action:

```python
"edge: node:a --relates_to--> node:b":          "Create semantic edge",
"edge: node:a --implements--> node:b reason='x'": "Create edge with reason",
```

**Acceptance criteria:**
- `edge: node:flow_auth --implements--> node:pop_protocol` works
- Validates both nodes exist before creating edge
- Returns `edge_created` with from/to names
- Error if node not found
- All edge types in `core_edges.yaml` supported

**Commit message:**
```
Wave 10B Task 5: add edge creation to dispatcher

- parse_query(): handle 'edge: from --type--> to' format
- dispatch(): edge action validates nodes + creates semantic edge
- Edges stored in .gobp/edges/semantic_edges.yaml
- PROTOCOL_GUIDE updated with edge examples
- Fixes B6: only discovered_in edges, now full semantic edges supported
```

---

## TASK 6 — Enhance import action with Document node + priority

**Goal:** `import:` creates Document node + auto-classifies priority + returns structured proposal.

**File to modify:** `gobp/mcp/dispatcher.py`

**Re-read import handler in `dispatch()`.**

Replace current import handler with:

```python
        elif action == "import":
            source_path_str = params.get("query") or params.get("source_path", "")
            session_id = params.get("session_id", "")
            
            if not source_path_str:
                result = {
                    "ok": False,
                    "error": "import: requires source path",
                    "hint": "gobp(query=\"import: path/to/doc.md session_id='session:x'\")",
                }
            else:
                # Resolve path relative to project root
                source_path = project_root / source_path_str
                
                # Read file content for classification
                content = ""
                sections = []
                if source_path.exists():
                    content = source_path.read_text(encoding="utf-8", errors="replace")
                    # Extract markdown headings as sections
                    import re as _re
                    sections = [
                        {"heading": m.group(2).strip(), "level": len(m.group(1))}
                        for m in _re.finditer(r"^(#{1,3})\s+(.+)$", content, _re.MULTILINE)
                    ][:20]  # max 20 sections
                
                # Auto-classify priority
                priority = _classify_doc_priority(content, source_path_str)
                
                # Generate Document node ID from filename
                import re as _re
                doc_slug = _re.sub(r"[^a-z0-9_]", "_", source_path.stem.lower())
                doc_id = f"doc:{doc_slug}"
                
                # Create Document node
                import hashlib as _hashlib
                content_hash = f"sha256:{_hashlib.sha256(content.encode()).hexdigest()[:16]}" if content else ""
                
                doc_node = {
                    "id": doc_id,
                    "type": "Document",
                    "name": source_path.stem.replace("_", " ").title(),
                    "source_path": source_path_str,
                    "content_hash": content_hash,
                    "priority": priority,
                    "sections": sections,
                    "status": "ACTIVE",
                    "session_id": session_id,
                }
                
                doc_args = {
                    "node_id": doc_id,
                    "type": "Document",
                    "name": doc_node["name"],
                    "fields": {
                        k: v for k, v in doc_node.items()
                        if k not in ("id", "type", "name", "session_id")
                    },
                    "session_id": session_id,
                }
                
                upsert_result = tools_write.node_upsert(index, project_root, doc_args)
                
                result = {
                    "ok": upsert_result.get("ok", False),
                    "document_node": doc_id,
                    "document_name": doc_node["name"],
                    "priority": priority,
                    "sections_found": len(sections),
                    "sections": sections[:5],  # show first 5
                    "content_hash": content_hash,
                    "file_exists": source_path.exists(),
                    "suggestion": (
                        f"Document node created. Now extract key concepts:\n"
                        f"  gobp(query=\"create:Node name='...' priority='{priority}' session_id='{session_id}'\")\n"
                        f"Then link with:\n"
                        f"  gobp(query=\"edge: node:x --references--> {doc_id}\")"
                    ),
                }
```

**Add priority classifier:**

```python
def _classify_doc_priority(content: str, path: str) -> str:
    """Auto-classify document priority based on content keywords.
    
    Rules (deterministic, no AI):
      critical: user flows, auth, payment, proof of presence, trust gate
      high:     entity, engine, architecture, API, database
      medium:   design, copy, admin, notification, map
      low:      mascot, growth, future, level system, campaign
    """
    content_lower = content.lower()
    path_lower = path.lower()
    combined = content_lower + " " + path_lower
    
    critical_keywords = [
        "user flow", "authentication", "proof of presence", "payment",
        "trust gate", "verify gate", "core flow", "master definition",
        "pop_protocol", "mihot", "homecoming", "registration flow",
    ]
    high_keywords = [
        "entity", "engine", "architecture", "api", "database",
        "engine spec", "adapter", "domain dictionary", "migration",
        "interface reference", "middleware", "scale",
    ]
    low_keywords = [
        "mascot", "growth", "launch", "campaign", "level system",
        "gamification", "future", "phase 2", "nice to have",
    ]
    
    critical_score = sum(1 for kw in critical_keywords if kw in combined)
    high_score = sum(1 for kw in high_keywords if kw in combined)
    low_score = sum(1 for kw in low_keywords if kw in combined)
    
    if critical_score >= 2:
        return "critical"
    elif critical_score >= 1 or high_score >= 3:
        return "high"
    elif low_score >= 2:
        return "low"
    else:
        return "medium"
```

**Acceptance criteria:**
- `import: mihos-shared/doc/DOC-07.md session_id='x'` creates Document node
- Document node has: id, name, source_path, content_hash, priority, sections
- Priority auto-classified from content
- Returns structured proposal with suggestion for next steps
- File not found → ok=False with clear error
- Fixes B3 (0 nodes) and B5 (no Document nodes)

**Commit message:**
```
Wave 10B Task 6: enhance import action — Document node + priority auto-classify

- import: creates Document node with source_path, content_hash, sections
- _classify_doc_priority(): deterministic keyword-based priority assignment
- Returns suggestion for creating related nodes
- Fixes B3: import created 0 nodes
- Fixes B5: no Document nodes in graph
```

---

## TASK 7 — Add priority_summary to gobp_overview

**Goal:** `gobp_overview` shows priority distribution so AI knows what's critical.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `gobp_overview()` in full.**

Add before the `return` statement:

```python
    # Priority summary
    priority_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for node in all_nodes:
        p = node.get("priority", "medium")
        if p in priority_counts:
            priority_counts[p] += 1
        else:
            priority_counts["medium"] += 1

    critical_nodes = [
        {"id": n.get("id"), "type": n.get("type"), "name": n.get("name", "")}
        for n in all_nodes
        if n.get("priority") == "critical"
    ][:10]
```

**Add to return dict:**

```python
        "priority_summary": {
            "critical": priority_counts["critical"],
            "high": priority_counts["high"],
            "medium": priority_counts["medium"],
            "low": priority_counts["low"],
            "critical_nodes": critical_nodes,
        },
```

**Acceptance criteria:**
- `gobp_overview` returns `priority_summary` with counts
- `critical_nodes` list shows up to 10 critical nodes
- Works when no nodes have priority field (defaults to medium)

**Commit message:**
```
Wave 10B Task 7: gobp_overview adds priority_summary

- priority_counts: critical/high/medium/low node counts
- critical_nodes: list of up to 10 critical nodes
- Nodes without priority field default to medium
- AI sees project health at a glance
```

---

## TASK 8 — Update SCHEMA.md and MCP_TOOLS.md

**Goal:** Document all changes.

**Files to modify:** `docs/SCHEMA.md`, `docs/MCP_TOOLS.md`

**In `docs/SCHEMA.md`:**

Find each node type section (Node, Idea, Decision, Document, Lesson, Concept). Add to optional fields:

```markdown
- `priority` — enum: `critical | high | medium | low` (default: medium). Importance level.
```

Also add Session ID format note:

```markdown
### Session ID format (v2)
`session:YYYY-MM-DD_XXXXXX` where XXXXXX = 6-char UUID hex.
Always exactly 28 characters. Example: `session:2026-04-15_a3f7c2`
```

**In `docs/MCP_TOOLS.md`:**

Add to gobp() quick reference table:

```markdown
| `edge: node:a --<type>--> node:b` | Create semantic edge |
| `edge: node:a --implements--> node:b reason='x'` | Edge with reason |
```

Update import row:

```markdown
| `import: path/to/doc.md session_id='x'` | Import doc → creates Document node + priority |
```

**Commit message:**
```
Wave 10B Task 8: update SCHEMA.md + MCP_TOOLS.md

- SCHEMA.md: priority field documented for all node types
- SCHEMA.md: session ID v2 format documented
- MCP_TOOLS.md: edge: action added to quick reference
- MCP_TOOLS.md: import: description updated
```

---

## TASK 9 — Write tests

**Goal:** Tests for all Wave 10B changes.

**File to create:** `tests/test_wave10b.py`

```python
"""Tests for Wave 10B: session ID, unicode, priority, edge creation, import enhancement."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml

from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch, parse_query, _classify_doc_priority


# ── Session ID tests ──────────────────────────────────────────────────────────

def test_session_id_length():
    from gobp.core.mutator import _generate_session_id
    for _ in range(10):
        sid = _generate_session_id("Very long goal string that used to cause truncation issues in MIHOS Phase 2 import session")
        assert len(sid) == 28, f"Wrong length: {len(sid)}"
        assert sid.startswith("session:20")


def test_session_id_unique():
    from gobp.core.mutator import _generate_session_id
    ids = {_generate_session_id() for _ in range(20)}
    assert len(ids) == 20  # all unique


# ── Unicode encoding tests ────────────────────────────────────────────────────

def test_unicode_in_node_yaml(gobp_root: Path):
    """Vietnamese text stored as UTF-8, not escaped."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        "session:start actor='test' goal='Xây dựng cơ chế xác thực'",
        index, gobp_root
    ))
    assert result["ok"] is True

    # Reload index and check session node
    index2 = GraphIndex.load_from_disk(gobp_root)
    session_id = result["session_id"]
    session = index2.get_node(session_id)
    assert session is not None
    assert "Xây dựng" in session.get("goal", ""), "Vietnamese text should be readable"


def test_node_file_no_escaped_unicode(gobp_root: Path):
    """Node files should not contain \\xNN escape sequences."""
    init_project(gobp_root, force=True)
    for node_file in (gobp_root / ".gobp" / "nodes").glob("*.md"):
        content = node_file.read_text(encoding="utf-8")
        assert "\\xe2" not in content, f"Escaped unicode in {node_file.name}"
        assert "\\u1" not in content, f"Escaped unicode in {node_file.name}"


# ── Priority field tests ──────────────────────────────────────────────────────

def test_priority_field_in_schema():
    """priority field exists in Node schema."""
    schema = yaml.safe_load(
        open("gobp/schema/core_nodes.yaml", encoding="utf-8")
    )
    node_optional = schema["node_types"]["Node"].get("optional", {})
    assert "priority" in node_optional


def test_create_node_with_priority(gobp_root: Path):
    """create: action accepts priority field."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    # Start session first
    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='priority test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        f"create:Node name='Core Login' priority='critical' session_id='{session_id}'",
        index, gobp_root
    ))
    assert result["ok"] is True

    index2 = GraphIndex.load_from_disk(gobp_root)
    node_id = result.get("node_id", "")
    node = index2.get_node(node_id)
    assert node is not None
    assert node.get("priority") == "critical"


def test_priority_classify_critical():
    content = "Core user flows authentication proof of presence trust gate verification"
    assert _classify_doc_priority(content, "DOC-07_core_user_flows.md") == "critical"


def test_priority_classify_high():
    content = "Engine architecture entity domain database migration API interface"
    assert _classify_doc_priority(content, "DOC-16_engine_specs.md") in ("high", "critical")


def test_priority_classify_low():
    content = "Mascot character design growth campaign level system gamification"
    assert _classify_doc_priority(content, "DOC-17_mascot.md") == "low"


# ── Auto-generate ID tests ────────────────────────────────────────────────────

def test_create_without_id(gobp_root: Path):
    """create: auto-generates ID if not provided."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='id test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        f"create:Idea name='Auto ID test' session_id='{session_id}'",
        index, gobp_root
    ))
    assert result["ok"] is True
    node_id = result.get("node_id", "")
    assert node_id.startswith("idea:"), f"Wrong ID format: {node_id}"
    assert len(node_id) == len("idea:") + 6


# ── Edge creation tests ───────────────────────────────────────────────────────

def test_parse_edge_query():
    action, ntype, params = parse_query("edge: node:a --implements--> node:b")
    assert action == "edge"
    assert params["from"] == "node:a"
    assert params["edge_type"] == "implements"
    assert params["to"] == "node:b"


def test_parse_edge_with_reason():
    action, ntype, params = parse_query(
        "edge: node:flow_auth --implements--> node:pop_protocol reason='auth implements PoP'"
    )
    assert params["from"] == "node:flow_auth"
    assert params["reason"] == "auth implements PoP"


def test_dispatch_edge_creation(gobp_root: Path):
    """edge: creates semantic edge between existing nodes."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='edge test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    # Create 2 nodes
    r1 = asyncio.run(dispatch(
        f"create:Node name='Node A' session_id='{session_id}'", index, gobp_root
    ))
    r2 = asyncio.run(dispatch(
        f"create:Node name='Node B' session_id='{session_id}'", index, gobp_root
    ))
    id_a = r1["node_id"]
    id_b = r2["node_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    # Create edge
    result = asyncio.run(dispatch(
        f"edge: {id_a} --relates_to--> {id_b}",
        index, gobp_root
    ))
    assert result["ok"] is True
    assert result["edge_created"]["from"] == id_a
    assert result["edge_created"]["to"] == id_b
    assert result["edge_created"]["type"] == "relates_to"


def test_dispatch_edge_node_not_found(gobp_root: Path):
    """edge: returns error if node not found."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        "edge: node:nonexistent --relates_to--> node:also_nonexistent",
        index, gobp_root
    ))
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


# ── Import enhancement tests ──────────────────────────────────────────────────

def test_import_creates_document_node(gobp_root: Path, tmp_path: Path):
    """import: creates Document node."""
    # Create a test doc file
    doc_file = tmp_path / "test_doc.md"
    doc_file.write_text(
        "# Test Document\n\nUser flows authentication proof of presence.\n\n## Section 1\nContent here.",
        encoding="utf-8"
    )

    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='import test'", index, gobp_root
    ))
    session_id = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        f"import: {doc_file} session_id='{session_id}'",
        index, gobp_root
    ))
    assert result["ok"] is True
    assert result["document_node"].startswith("doc:")
    assert result["sections_found"] >= 1
    assert result["priority"] in ("critical", "high", "medium", "low")


def test_import_file_not_found(gobp_root: Path):
    """import: returns error if file not found."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch(
        "import: nonexistent/file.md session_id='session:x'",
        index, gobp_root
    ))
    # Should still create Document node but with file_exists=False
    assert "file_exists" in result
    assert result["file_exists"] is False


# ── gobp_overview priority summary tests ─────────────────────────────────────

def test_gobp_overview_priority_summary(gobp_root: Path):
    """gobp_overview returns priority_summary."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    result = asyncio.run(dispatch("overview:", index, gobp_root))
    assert result["ok"] is True
    assert "priority_summary" in result
    ps = result["priority_summary"]
    assert "critical" in ps
    assert "high" in ps
    assert "medium" in ps
    assert "low" in ps
    assert "critical_nodes" in ps
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave10b.py -v
# Expected: ~22 tests passing
```

**Commit message:**
```
Wave 10B Task 9: create tests/test_wave10b.py — ~22 tests

- session ID length + uniqueness (2)
- unicode encoding in nodes (2)
- priority field in schema (1)
- create with priority (1)
- priority auto-classify (3)
- create without ID (1)
- parse edge query (2)
- dispatch edge creation + node not found (2)
- import creates document node + file not found (2)
- gobp_overview priority summary (1)
```

---

## TASK 10 — Full suite + CHANGELOG

```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 258+ tests passing (236 + ~22 new)
```

**Update CHANGELOG.md:**

```markdown
## [Wave 10B] — Bug Fixes + Priority + Edge Interface + Import Enhancement — 2026-04-15

### Bugs fixed
- B1: Session ID truncation — now always 28 chars (session:YYYY-MM-DD_XXXXXX)
- B2: Unicode encoding — Vietnamese/special chars stored as UTF-8 not escaped bytes
- B3: import: created 0 nodes — now creates Document node + auto-extracts metadata
- B4: create: required manual ID — now auto-generates id:XXXXXX
- B5: No Document nodes — import: always creates Document node
- B6: Only discovered_in edges — edge: action now creates semantic edges

### Features added
- F1: priority field (critical/high/medium/low) on all node types
- F2: _classify_doc_priority(): auto-classifies priority from doc content
- F3: edge: action — gobp(query="edge: node:a --type--> node:b")
- F4: gobp_overview priority_summary — see project health at a glance

### Changed
- gobp/core/mutator.py: _generate_session_id() with UUID hash
- gobp/core/mutator.py + init.py: allow_unicode=True in all YAML writes
- gobp/mcp/dispatcher.py: edge + import handlers, auto-ID generation
- gobp/mcp/tools/read.py: gobp_overview priority_summary
- gobp/schema/core_nodes.yaml: priority field on 6 node types
- docs/SCHEMA.md: priority + session ID v2 documented
- docs/MCP_TOOLS.md: edge action + updated import description

### Total after wave: 1 MCP tool, 258+ tests passing
```

**Commit message:**
```
Wave 10B Task 10: full suite green + CHANGELOG updated

- 258+ tests passing
- All 6 bugs fixed
- 4 features added
```

---

# POST-WAVE VERIFICATION

```powershell
# All tests
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

# Session ID never truncated
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.mutator import _generate_session_id
for goal in ['short', 'MIHOS Phase 2: import all 32 docs from mihos-shared/doc']:
    sid = _generate_session_id(goal)
    assert len(sid) == 28, f'{len(sid)}: {sid}'
    print(f'OK: {sid}')
"

# Edge creation works
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.mcp.dispatcher import parse_query
action, _, params = parse_query('edge: node:a --implements--> node:b reason=test')
assert action == 'edge'
assert params['from'] == 'node:a'
assert params['edge_type'] == 'implements'
print('Edge parsing OK')
"

# Priority classify
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.mcp.dispatcher import _classify_doc_priority
assert _classify_doc_priority('user flows authentication proof of presence', 'DOC-07.md') == 'critical'
assert _classify_doc_priority('mascot gamification level system', 'DOC-17.md') == 'low'
print('Priority classify OK')
"
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief vào repo

```powershell
cd D:\GoBP
# Save wave_10b_brief.md to D:\GoBP\waves\wave_10b_brief.md

git add waves/wave_10b_brief.md
git commit -m "Add Wave 10B Brief — bug fixes + priority + edge + import enhancement"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_10b_brief.md first.
Also read gobp/core/mutator.py, gobp/core/init.py, gobp/mcp/dispatcher.py,
gobp/mcp/tools/read.py, gobp/schema/core_nodes.yaml, docs/MCP_TOOLS.md.

Execute ALL 10 tasks of Wave 10B sequentially.
Rules:
- R9: all 236 existing tests must pass after every task
- R8: Brief code is authoritative
- 1 task = 1 commit, exact message
- Report full summary after Task 10

Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 10B. Read CLAUDE.md and waves/wave_10b_brief.md.
Also read docs/GoBP_ARCHITECTURE.md, docs/ARCHITECTURE.md, docs/MCP_TOOLS.md.

Critical verification:
- Task 1: _generate_session_id() always 28 chars, UUID-based
- Task 2: all YAML writes use allow_unicode=True, no escaped unicode in node files
- Task 3: create: auto-generates id:XXXXXX when no id provided
- Task 4: priority field in core_nodes.yaml for Node/Idea/Decision/Document/Lesson/Concept
- Task 5: edge: action parses 'node:a --type--> node:b', validates nodes, creates edge
- Task 6: import: creates Document node + priority + sections + suggestion
- Task 7: gobp_overview returns priority_summary with counts + critical_nodes
- Task 8: SCHEMA.md + MCP_TOOLS.md updated
- Task 9: test_wave10b.py exists, ~22 tests passing
- Task 10: 258+ tests passing, CHANGELOG updated

Use venv:
  D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

Expected: 258+ tests passing.

Stop on first failure. Report WAVE 10B AUDIT COMPLETE when done.
```

## 4. Push

```powershell
cd D:\GoBP
git push origin main
```

---

# WHAT COMES NEXT

```
Wave 10B pushed
    ↓
Re-import MIHOS docs với enhanced import:
  - Document nodes created automatically
  - Priority auto-classified
  - Use edge: to connect nodes semantically
    ↓
Wave 11 — GoBP 3D Graph Viewer
  - Three.js + 3d-force-graph
  - Node size = priority
  - Node color = type
  - Per-project isolation
```

---

*Wave 10B Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
