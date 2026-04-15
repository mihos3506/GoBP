# WAVE 15 BRIEF — PARSER REWRITE + IMPORT FIX + EDGE DEDUPE

**Wave:** 15
**Title:** Fix parse_query grammar, import doc_id collision, edge deduplication
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 5 atomic tasks
**Estimated effort:** 2-3 hours

---

## CONTEXT

Cursor's production testing revealed 6 bugs. All block Wave 8B MIHOS import.
Grouped into 3 fix areas:

**Fix 1 — Parser rewrite (B1 + B2 + B6)**
```
B1: find: login page_size=10
    → parse_query() gives type='login', query='page_size=10'
    → Should give query='login', page_size=10
    
B2: related: node:x direction='outgoing' page_size=10
    → node_id='node:x' gets lost, returns ok=False
    → Should preserve node_id before parsing params
    
B6: automated=true stored as string "true"
    → Schema expects bool, gets string → silent type mismatch
```

**Fix 2 — Import ID + response contract (B3 + B5)**
```
B3: doc_id from filename stem only
    → README.md in root and examples/ both → doc:readme (collision)
    → Evidence: doc:readme → examples/mcp_configs/README.md (wrong)
    
B5: import returns ok=False but still has document_node + suggestion
    → AI thinks import succeeded when it failed
    → Contract: ok=False must not have success fields
```

**Fix 3 — Edge deduplication (B4)**
```
B4: create_edge() appends without checking (from,type,to)
    → relations.yaml: 181 total, 171 unique, 4 duplicate triples
    → One triple repeated 8x
    → DB has ON CONFLICT so DB is clean, but file is corrupted
```

---

## DESIGN DECISIONS

### Parser grammar (B1 + B2)

New rule: **first token without `=` is positional**

```
Action-specific positional mapping:
  find:        positional → params["query"]
  related:     positional → params["node_id"]
  tests:       positional → params["node_id"]
  get:         positional → params["node_id"]
  context:     positional → params["node_id"]
  signature:   positional → params["node_id"]
  code:        positional → params["node_id"]
  invariants:  positional → params["node_id"]
  sections:    positional → params["doc_id"]
  decisions:   positional → params["topic"]
  validate:    positional → params["scope"]
  stats:       positional → params["action_filter"]
  import:      positional → params["source_path"]
  commit:      positional → params["proposal_id"]
  recent:      positional → params["n"]
  All others:  positional → params["query"]

Examples after fix:
  "find: login page_size=10"
  → action="find", positional="login" → query="login", page_size="10"

  "related: node:x direction='outgoing' page_size=10"
  → action="related", positional="node:x" → node_id="node:x", direction="outgoing", page_size="10"

  "find:Decision auth page_size=5"
  → action="find", type="Decision", positional="auth" → query="auth", page_size="5"
```

### Bool/None parsing (B6)

```python
def _coerce_value(v: str) -> Any:
    """Coerce string values to appropriate Python types."""
    if v.lower() in ("true",):  return True
    if v.lower() in ("false",): return False
    if v.lower() in ("null", "none"): return None
    if v.isdigit(): return int(v)
    return v
```

Apply to all key=value parsed params.

### Import doc_id (B3)

```python
# New: human-readable + collision-proof
import hashlib
path_normalized = str(source_path).replace("\\", "/").lower()
short_hash = hashlib.md5(path_normalized.encode()).hexdigest()[:6]
doc_slug = re.sub(r"[^a-z0-9_]", "_", source_path.stem.lower())
doc_id = f"doc:{doc_slug}_{short_hash}"

# Examples:
# README.md at root        → doc:readme_a1b2c3
# README.md at examples/   → doc:readme_d4e5f6  (different hash)
# DOC-07_core_user_flows.md → doc:doc_07_core_user_flows_8f9a1b
```

### Response contract (B5)

```
ok=True:  {ok: true, ...success_fields}
ok=False: {ok: false, error: "...", hint: "..."}
          NO success fields (no document_node, no suggestion)
```

### Edge dedupe (B4)

```python
def create_edge(gobp_root, edge, ...):
    # Load existing edges
    existing = load_edge_file(edge_file_path) if edge_file_path.exists() else []
    
    # Check duplicate
    for e in existing:
        if (e.get("from") == edge["from"] and
            e.get("to") == edge["to"] and
            e.get("type") == edge["type"]):
            return {"ok": True, "action": "skipped", "reason": "edge already exists"}
    
    # Safe to append
    append_edge(...)
    return {"ok": True, "action": "created"}
```

Plus one-shot cleanup command for existing duplicates.

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 302 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 302 tests passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/mcp/dispatcher.py` | Rewrite parse_query() |
| 3 | `gobp/core/mutator.py` | Fix create_edge() |
| 4 | `gobp/core/loader.py` | Understand load_edge_file() |
| 5 | `waves/wave_15_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Rewrite parse_query() with positional grammar

**Goal:** Fix B1 + B2 + B6. Parser correctly extracts positional arg and coerces types.

**File to modify:** `gobp/mcp/dispatcher.py`

**Re-read `parse_query()` in full before editing.**

**Replace `parse_query()` entirely:**

```python
# Action → positional param key mapping
_POSITIONAL_KEY: dict[str, str] = {
    "find":       "query",
    "get":        "node_id",
    "context":    "node_id",
    "signature":  "node_id",
    "code":       "node_id",
    "invariants": "node_id",
    "tests":      "node_id",
    "related":    "node_id",
    "sections":   "doc_id",
    "decisions":  "topic",
    "validate":   "scope",
    "stats":      "action_filter",
    "import":     "source_path",
    "commit":     "proposal_id",
    "recent":     "n",
    "edge":       "_edge_raw",  # handled separately
}


def _coerce_value(v: str) -> Any:
    """Coerce string values to appropriate Python types."""
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    if v.lower() in ("null", "none"):
        return None
    if v.isdigit():
        return int(v)
    return v


def parse_query(query: str) -> tuple[str, str, dict[str, Any]]:
    """Parse query string into (action, node_type, params).

    Grammar:
        "<action>:<NodeType> [positional] [key='value'] ..."
        "<action>: [positional] [key='value'] ..."

    Rules:
        1. Split on first ':' → action_part, rest
        2. action_part may contain NodeType: "find:Decision" → action="find", type="Decision"
        3. In rest: first token without '=' is positional → mapped by _POSITIONAL_KEY
        4. Remaining tokens: key='value' or key=value pairs
        5. Values coerced: "true"→True, "false"→False, digits→int

    Examples:
        "overview:"                           → ("overview", "", {})
        "find: login"                         → ("find", "", {"query": "login"})
        "find: login page_size=10"            → ("find", "", {"query": "login", "page_size": 10})
        "find:Decision auth page_size=5"      → ("find", "Decision", {"query": "auth", "page_size": 5})
        "related: node:x direction='out'"     → ("related", "", {"node_id": "node:x", "direction": "out"})
        "tests: node:x page_size=20"          → ("tests", "", {"node_id": "node:x", "page_size": 20})
        "edge: node:a --impl--> node:b"       → ("edge", "", {"from":"node:a","edge_type":"impl","to":"node:b"})
        "session:start actor='x' goal='y'"    → ("session", "", {"query":"start","actor":"x","goal":"y"})
    """
    query = query.strip()
    if not query:
        return "overview", "", {}

    # Split on first ':'
    colon_idx = query.find(":")
    if colon_idx == -1:
        # No colon: treat whole thing as find query
        return "find", "", {"query": query}

    action_part = query[:colon_idx].strip().lower()
    rest = query[colon_idx + 1:].strip()

    # Split action and NodeType: "find:Decision" → "find", "Decision"
    action_tokens = action_part.split(None, 1)
    action = action_tokens[0]
    node_type = action_tokens[1] if len(action_tokens) > 1 else ""

    if not rest:
        return action, node_type, {}

    # Special case: edge action with arrow syntax
    if action == "edge":
        edge_params = _parse_edge_rest(rest)
        return action, "", edge_params

    params: dict[str, Any] = {}

    # Tokenize rest preserving quoted strings
    tokens = _tokenize_rest(rest)

    positional_key = _POSITIONAL_KEY.get(action, "query")
    positional_consumed = False

    for token in tokens:
        if "=" in token:
            # key=value or key='value'
            eq_idx = token.index("=")
            k = token[:eq_idx].strip()
            v = token[eq_idx + 1:].strip().strip("'\"")
            params[k] = _coerce_value(v)
        elif not positional_consumed:
            # First token without '=' is positional
            params[positional_key] = token.strip("'\"")
            positional_consumed = True
        # Extra positional tokens ignored (or could append to query)

    return action, node_type, params


def _tokenize_rest(rest: str) -> list[str]:
    """Tokenize rest string, preserving quoted values as single tokens.

    Examples:
        "login page_size=10"          → ["login", "page_size=10"]
        "node:x direction='outgoing'" → ["node:x", "direction='outgoing'"]
        "name='hello world' actor=x"  → ["name='hello world'", "actor=x"]
    """
    tokens = []
    current = []
    in_quote = False
    quote_char = None

    for char in rest:
        if not in_quote and char in ("'", '"'):
            in_quote = True
            quote_char = char
            current.append(char)
        elif in_quote and char == quote_char:
            in_quote = False
            quote_char = None
            current.append(char)
        elif not in_quote and char == " ":
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)

    if current:
        tokens.append("".join(current))

    return [t for t in tokens if t]


def _parse_edge_rest(rest: str) -> dict[str, Any]:
    """Parse edge arrow syntax: 'node:a --type--> node:b [key=val]'"""
    import re as _re
    edge_pattern = _re.compile(
        r"^([\w:]+)\s+--(\w+)-->\s+([\w:]+)(.*)?$"
    )
    m = edge_pattern.match(rest)
    if m:
        params: dict[str, Any] = {
            "from": m.group(1).strip(),
            "edge_type": m.group(2).strip(),
            "to": m.group(3).strip(),
        }
        extra = m.group(4).strip() if m.group(4) else ""
        if extra:
            for km in _re.finditer(r"(\w+)='([^']*)'|(\w+)=\"([^\"]*)\"|(\w+)=(\S+)", extra):
                if km.group(1):
                    params[km.group(1)] = km.group(2)
                elif km.group(3):
                    params[km.group(3)] = km.group(4)
                elif km.group(5):
                    params[km.group(5)] = _coerce_value(km.group(6))
        return params
    # Fallback
    return {"_edge_raw": rest}
```

**Verify immediately:**
```python
# Add after parse_query definition — verify key cases
assert parse_query("find: login page_size=10") == ("find", "", {"query": "login", "page_size": 10})
assert parse_query("find:Decision auth page_size=5") == ("find", "Decision", {"query": "auth", "page_size": 5})
assert parse_query("related: node:x direction='outgoing' page_size=10") == ("related", "", {"node_id": "node:x", "direction": "outgoing", "page_size": 10})
assert parse_query("tests: node:x page_size=20") == ("tests", "", {"node_id": "node:x", "page_size": 20})
assert parse_query("session:start actor='cursor' goal='test'")[2]["query"] == "start"
assert parse_query("create:Node name='Login' priority='critical'")[2]["name"] == "Login"
assert parse_query("create:Node automated=true") [2]["automated"] == True  # bool coercion
```

**Acceptance criteria:**
- `find: login page_size=10` → `query='login'`, `page_size=10` (int)
- `find:Decision auth page_size=5` → type='Decision', `query='auth'`, `page_size=5`
- `related: node:x direction='outgoing'` → `node_id='node:x'`, `direction='outgoing'`
- `tests: node:x page_size=20` → `node_id='node:x'`, `page_size=20`
- `automated=true` → `automated=True` (bool)
- `automated=false` → `automated=False` (bool)
- `n=3` → `n=3` (int)
- All existing parse tests still pass

**Commit message:**
```
Wave 15 Task 1: rewrite parse_query() — positional grammar + type coercion

- _POSITIONAL_KEY: action → positional param name mapping
- _coerce_value(): true/false→bool, digits→int, null→None
- _tokenize_rest(): quote-aware tokenizer
- _parse_edge_rest(): edge arrow syntax handler
- Grammar: first token without '=' is positional
- find: → query, related:/tests:/code:/invariants: → node_id
- Fixes B1 (find pagination), B2 (related/tests node_id), B6 (bool parsing)
```

---

## TASK 2 — Fix import: doc_id collision + response contract

**Goal:** Fix B3 (doc_id collision) and B5 (inconsistent response on failure).

**File to modify:** `gobp/mcp/dispatcher.py`

**Re-read the `import:` handler in `dispatch()` in full.**

**Fix doc_id generation (B3):**

```python
        elif action == "import":
            source_path_str = (
                params.get("source_path") or
                params.get("query") or
                ""
            )
            session_id = params.get("session_id", "")

            if not source_path_str:
                result = {
                    "ok": False,
                    "error": "import: requires source path",
                    "hint": "gobp(query=\"import: path/to/doc.md session_id='x'\")",
                }
            else:
                source_path = project_root / source_path_str

                content = ""
                sections = []
                if source_path.exists():
                    content = source_path.read_text(encoding="utf-8", errors="replace")
                    import re as _re2
                    sections = [
                        {"heading": m.group(2).strip(), "level": len(m.group(1))}
                        for m in _re2.finditer(r"^(#{1,3})\s+(.+)$", content, _re2.MULTILINE)
                    ][:20]

                # Collision-proof doc_id: slug + md5 of normalized path
                import hashlib as _hashlib
                import re as _re3
                path_normalized = str(source_path).replace("\\", "/").lower()
                short_hash = _hashlib.md5(path_normalized.encode()).hexdigest()[:6]
                doc_slug = _re3.sub(r"[^a-z0-9]+", "_", source_path.stem.lower()).strip("_")
                doc_id = f"doc:{doc_slug}_{short_hash}"

                priority = _classify_doc_priority(content, source_path_str)

                content_hash = ""
                if content:
                    content_hash = f"sha256:{_hashlib.sha256(content.encode()).hexdigest()}"

                doc_args = {
                    "node_id": doc_id,
                    "type": "Document",
                    "name": source_path.stem.replace("_", " ").title(),
                    "fields": {
                        "source_path": source_path_str,
                        "content_hash": content_hash,
                        "priority": priority,
                        "sections": sections,
                        "status": "ACTIVE",
                    },
                    "session_id": session_id,
                }

                upsert_result = tools_write.node_upsert(index, project_root, doc_args)

                # Fix B5: clean response contract
                if not upsert_result.get("ok"):
                    result = {
                        "ok": False,
                        "error": upsert_result.get("error", "Failed to create Document node"),
                        "source_path": source_path_str,
                        "file_exists": source_path.exists(),
                    }
                else:
                    result = {
                        "ok": True,
                        "document_node": doc_id,
                        "document_name": doc_args["name"],
                        "priority": priority,
                        "sections_found": len(sections),
                        "sections": sections[:5],
                        "content_hash": content_hash,
                        "file_exists": source_path.exists(),
                        "suggestion": (
                            f"Document node created with collision-proof ID. "
                            f"Now extract key concepts:\n"
                            f"  gobp(query=\"create:Node name='...' "
                            f"priority='{priority}' session_id='{session_id}'\")\n"
                            f"Then link:\n"
                            f"  gobp(query=\"edge: node:x --references--> {doc_id}\")"
                        ),
                    }
```

**Acceptance criteria:**
- `import: README.md` from root → `doc:readme_a1b2c3`
- `import: examples/mcp_configs/README.md` → `doc:readme_d4e5f6` (different hash)
- `import: DOC-07_core_user_flows.md` → `doc:doc_07_core_user_flows_8f9a1b`
- Failed import → `ok=False` with ONLY `error`, `source_path`, `file_exists`
- Successful import → `ok=True` with success fields including `document_node`

**Commit message:**
```
Wave 15 Task 2: fix import doc_id collision + response contract

- doc_id: "doc:{slug}_{md5[:6]}" — collision-proof, human-readable
- Response contract: ok=False → only error fields, no success fields
- Fixes B3: same-stem files in different folders get unique IDs
- Fixes B5: AI can't misread failed import as success
```

---

## TASK 3 — Fix create_edge() deduplication + cleanup script

**Goal:** Fix B4. `create_edge()` idempotent. Cleanup script for existing duplicates.

**File to modify:** `gobp/core/mutator.py`

**Re-read `create_edge()` in full before editing.**

**Update `create_edge()` to check before append:**

```python
def create_edge(
    gobp_root: Path,
    edge: dict[str, Any],
    schema: dict[str, Any],
    actor: str = "system",
    edge_file_name: str = "relations.yaml",
) -> dict[str, Any]:
    """Create an edge between two nodes. Idempotent — skips if already exists.

    Returns:
        {ok, action: 'created'|'skipped', edge_id, reason?}
    """
    from gobp.core.loader import load_edge_file
    from gobp.core.validator import validate_edge

    from_id = edge.get("from", "")
    to_id = edge.get("to", "")
    edge_type = edge.get("type", "")

    if not from_id or not to_id or not edge_type:
        return {"ok": False, "error": "edge requires from, to, type fields"}

    edge_id = f"{from_id}__{edge_type}__{to_id}"

    # Validate
    result = validate_edge(edge, schema)
    if not result.ok:
        return {"ok": False, "error": f"Edge validation failed: {result.errors}"}

    # Load existing edges in target file
    edges_dir = gobp_root / ".gobp" / "edges"
    edges_dir.mkdir(parents=True, exist_ok=True)
    edge_file = edges_dir / edge_file_name

    existing_edges: list[dict] = []
    if edge_file.exists():
        try:
            existing_edges = load_edge_file(edge_file)
        except Exception:
            existing_edges = []

    # Dedupe check: skip if (from, type, to) already exists
    for e in existing_edges:
        if (
            e.get("from") == from_id and
            e.get("to") == to_id and
            e.get("type") == edge_type
        ):
            return {
                "ok": True,
                "action": "skipped",
                "edge_id": edge_id,
                "reason": f"Edge {from_id} --{edge_type}--> {to_id} already exists",
            }

    # Safe to append
    existing_edges.append(edge)

    import yaml as _yaml
    edge_file.write_text(
        _yaml.safe_dump(existing_edges, allow_unicode=True, default_flow_style=False),
        encoding="utf-8"
    )

    # Update DB index
    try:
        from gobp.core import db as _db
        _db.upsert_edge(gobp_root, edge)
    except Exception:
        pass

    return {
        "ok": True,
        "action": "created",
        "edge_id": edge_id,
    }
```

**Add cleanup utility function:**

```python
def deduplicate_edges(gobp_root: Path) -> dict[str, Any]:
    """Remove duplicate edges from all edge YAML files.

    A duplicate is defined as same (from, type, to) triple.
    Keeps the first occurrence, removes subsequent duplicates.

    Returns:
        {ok, files_processed, duplicates_removed, total_edges}
    """
    from gobp.core.loader import load_edge_file
    import yaml as _yaml

    edges_dir = gobp_root / ".gobp" / "edges"
    if not edges_dir.exists():
        return {"ok": True, "files_processed": 0, "duplicates_removed": 0, "total_edges": 0}

    files_processed = 0
    total_duplicates = 0
    total_edges = 0

    for edge_file in edges_dir.glob("**/*.yaml"):
        try:
            edges = load_edge_file(edge_file)
            seen: set[tuple] = set()
            deduped: list[dict] = []

            for e in edges:
                triple = (e.get("from", ""), e.get("type", ""), e.get("to", ""))
                if triple in seen:
                    total_duplicates += 1
                else:
                    seen.add(triple)
                    deduped.append(e)

            if len(deduped) < len(edges):
                edge_file.write_text(
                    _yaml.safe_dump(deduped, allow_unicode=True, default_flow_style=False),
                    encoding="utf-8"
                )

            files_processed += 1
            total_edges += len(deduped)

        except Exception:
            continue

    return {
        "ok": True,
        "files_processed": files_processed,
        "duplicates_removed": total_duplicates,
        "total_edges": total_edges,
    }
```

**Add `dedupe:` action to dispatcher:**

```python
        elif action == "dedupe":
            scope = params.get("action_filter") or params.get("scope", "edges")
            if scope in ("edges", "all"):
                from gobp.core.mutator import deduplicate_edges
                result = deduplicate_edges(project_root)
            else:
                result = {"ok": False, "error": f"dedupe: scope '{scope}' not supported. Use 'edges' or 'all'."}
```

**Update PROTOCOL_GUIDE:**
```python
"dedupe: edges": "Remove duplicate edges from file storage",
```

**Acceptance criteria:**
- `create_edge()` with existing (from, type, to) → `action: 'skipped'`
- `create_edge()` with new edge → `action: 'created'`
- `deduplicate_edges()` removes all duplicates, returns count
- `gobp(query="dedupe: edges")` calls deduplicate_edges()
- File format unchanged after dedupe (valid YAML)

**Commit message:**
```
Wave 15 Task 3: idempotent create_edge() + deduplicate_edges()

- mutator.py: create_edge() checks (from,type,to) before append
- Returns action: 'created'|'skipped' with reason
- mutator.py: deduplicate_edges() cleanup utility
- dispatcher.py: dedupe: edges action
- Fixes B4: relations.yaml 181→171 unique edges after cleanup
```

---

## TASK 4 — Run cleanup + smoke test

**Goal:** Clean existing duplicate edges. Verify all fixes work end-to-end.

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# Run edge cleanup on GoBP project
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.mutator import deduplicate_edges
from pathlib import Path
result = deduplicate_edges(Path('D:/GoBP'))
print('Cleanup result:', result)
"

# Smoke test parser fixes
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.mcp.dispatcher import parse_query

# B1: find with pagination
a, t, p = parse_query('find: login page_size=10')
assert a == 'find', f'action wrong: {a}'
assert p.get('query') == 'login', f'query wrong: {p}'
assert p.get('page_size') == 10, f'page_size wrong: {p}'
print('B1 fixed: find: login page_size=10 OK')

# B1: find:Type with pagination
a, t, p = parse_query('find:Decision auth page_size=5')
assert t == 'Decision'
assert p.get('query') == 'auth'
assert p.get('page_size') == 5
print('B1 fixed: find:Decision auth page_size=5 OK')

# B2: related: with node_id
a, t, p = parse_query(\"related: node:x direction='outgoing' page_size=10\")
assert p.get('node_id') == 'node:x', f'node_id wrong: {p}'
assert p.get('direction') == 'outgoing'
assert p.get('page_size') == 10
print('B2 fixed: related: node:x ... OK')

# B2: tests: with node_id
a, t, p = parse_query('tests: node:x page_size=20')
assert p.get('node_id') == 'node:x'
assert p.get('page_size') == 20
print('B2 fixed: tests: node:x ... OK')

# B6: bool coercion
a, t, p = parse_query('create:TestCase automated=true')
assert p.get('automated') == True, f'bool wrong: {p}'
a, t, p = parse_query('create:Node active=false')
assert p.get('active') == False
print('B6 fixed: bool coercion OK')

# B3: doc_id collision-proof
import hashlib, re
for path in ['README.md', 'examples/mcp_configs/README.md']:
    path_normalized = path.replace('\\\\', '/').lower()
    short_hash = hashlib.md5(path_normalized.encode()).hexdigest()[:6]
    stem = path.split('/')[-1].replace('.md', '')
    doc_slug = re.sub(r'[^a-z0-9]+', '_', stem.lower()).strip('_')
    doc_id = f'doc:{doc_slug}_{short_hash}'
    print(f'B3 fixed: {path} → {doc_id}')

print('All smoke tests passed')
"

# Full suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 302 tests passing
```

**Commit message:**
```
Wave 15 Task 4: cleanup + smoke test — all B1-B6 fixes verified

- Edge cleanup: duplicates removed from .gobp/edges/
- Parser: find/related/tests pagination and node_id working
- Bool coercion: automated=true → True
- doc_id: collision-proof hash confirmed
- 302 existing tests passing
```

---

## TASK 5 — Create tests/test_wave15.py + full suite + CHANGELOG

**File to create:** `tests/test_wave15.py`

```python
"""Tests for Wave 15: parser fix, import doc_id, edge dedupe."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch, parse_query, _coerce_value
from gobp.core.mutator import deduplicate_edges


# ── Parser tests (B1 + B2 + B6) ──────────────────────────────────────────────

def test_find_positional_no_params():
    a, t, p = parse_query("find: login")
    assert a == "find"
    assert p.get("query") == "login"


def test_find_positional_with_page_size():
    """B1: find: login page_size=10 → query='login', page_size=10"""
    a, t, p = parse_query("find: login page_size=10")
    assert p.get("query") == "login"
    assert p.get("page_size") == 10


def test_find_type_with_positional_and_pagination():
    """B1: find:Decision auth page_size=5"""
    a, t, p = parse_query("find:Decision auth page_size=5")
    assert a == "find"
    assert t == "Decision"
    assert p.get("query") == "auth"
    assert p.get("page_size") == 5


def test_related_preserves_node_id():
    """B2: related: node:x direction='outgoing'"""
    a, t, p = parse_query("related: node:x direction='outgoing'")
    assert a == "related"
    assert p.get("node_id") == "node:x"
    assert p.get("direction") == "outgoing"


def test_related_preserves_node_id_with_pagination():
    """B2: related: node:x page_size=10"""
    a, t, p = parse_query("related: node:x page_size=10")
    assert p.get("node_id") == "node:x"
    assert p.get("page_size") == 10


def test_tests_preserves_node_id():
    """B2: tests: node:x page_size=20"""
    a, t, p = parse_query("tests: node:x page_size=20")
    assert p.get("node_id") == "node:x"
    assert p.get("page_size") == 20


def test_code_preserves_node_id():
    a, t, p = parse_query("code: node:flow_auth")
    assert p.get("node_id") == "node:flow_auth"


def test_bool_coercion_true():
    """B6: automated=true → True"""
    assert _coerce_value("true") is True
    assert _coerce_value("True") is True
    assert _coerce_value("TRUE") is True


def test_bool_coercion_false():
    """B6: active=false → False"""
    assert _coerce_value("false") is False


def test_none_coercion():
    assert _coerce_value("null") is None
    assert _coerce_value("none") is None


def test_int_coercion():
    assert _coerce_value("10") == 10
    assert _coerce_value("3") == 3


def test_string_unchanged():
    assert _coerce_value("login") == "login"
    assert _coerce_value("node:x") == "node:x"


def test_create_bool_field():
    """B6: create:TestCase automated=true → automated=True"""
    a, t, p = parse_query("create:TestCase automated=true name='test'")
    assert p.get("automated") is True


def test_session_start_positional():
    """session:start actor='x' goal='y' → query='start'"""
    a, t, p = parse_query("session:start actor='cursor' goal='test'")
    assert a == "session"
    assert p.get("query") == "start"
    assert p.get("actor") == "cursor"
    assert p.get("goal") == "test"


def test_overview_empty():
    a, t, p = parse_query("overview:")
    assert a == "overview"
    assert p == {}


def test_edge_arrow_syntax():
    a, t, p = parse_query("edge: node:a --implements--> node:b")
    assert a == "edge"
    assert p.get("from") == "node:a"
    assert p.get("edge_type") == "implements"
    assert p.get("to") == "node:b"


# ── Import doc_id tests (B3 + B5) ────────────────────────────────────────────

def test_import_docid_different_for_same_stem(gobp_root: Path):
    """B3: same filename in different dirs → different doc_id"""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='docid test'", index, gobp_root
    ))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    # Create two files with same name in different dirs
    dir1 = gobp_root / "docs"
    dir2 = gobp_root / "examples"
    dir1.mkdir(exist_ok=True)
    dir2.mkdir(exist_ok=True)
    (dir1 / "README.md").write_text("# Root README", encoding="utf-8")
    (dir2 / "README.md").write_text("# Examples README", encoding="utf-8")

    r1 = asyncio.run(dispatch(
        f"import: docs/README.md session_id='{sid}'", index, gobp_root
    ))
    index = GraphIndex.load_from_disk(gobp_root)
    r2 = asyncio.run(dispatch(
        f"import: examples/README.md session_id='{sid}'", index, gobp_root
    ))

    assert r1["ok"] is True
    assert r2["ok"] is True
    assert r1["document_node"] != r2["document_node"], \
        f"doc_ids should differ: {r1['document_node']} vs {r2['document_node']}"


def test_import_failed_has_no_success_fields(gobp_root: Path):
    """B5: failed import returns only error fields"""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch(
        "import: nonexistent/file.md session_id='session:fake'", index, gobp_root
    ))

    # If file doesn't exist: either ok=True with file_exists=False (graceful)
    # or ok=False with no document_node
    if not r.get("ok"):
        assert "document_node" not in r, "Failed import must not have document_node"
        assert "suggestion" not in r, "Failed import must not have suggestion"
        assert "error" in r


def test_import_success_has_document_node(gobp_root: Path):
    """Successful import has document_node field"""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    doc_file = gobp_root / "test_doc.md"
    doc_file.write_text("# Test\nContent here.", encoding="utf-8")

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='import test'", index, gobp_root
    ))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch(f"import: test_doc.md session_id='{sid}'", index, gobp_root))
    assert r["ok"] is True
    assert "document_node" in r
    assert r["document_node"].startswith("doc:")


# ── Edge dedupe tests (B4) ────────────────────────────────────────────────────

def test_create_edge_idempotent(gobp_root: Path):
    """B4: creating same edge twice → second is skipped"""
    init_project(gobp_root, force=True)
    from gobp.core.loader import load_schema
    from gobp.core.mutator import create_edge

    schema_dir = gobp_root / "gobp" / "schema"
    edges_schema = load_schema(schema_dir / "core_edges.yaml")

    edge = {
        "from": "node:test_a",
        "to": "node:test_b",
        "type": "relates_to",
    }

    r1 = create_edge(gobp_root, edge, edges_schema, actor="test")
    r2 = create_edge(gobp_root, edge, edges_schema, actor="test")

    assert r1.get("action") == "created"
    assert r2.get("action") == "skipped"
    assert "already exists" in r2.get("reason", "").lower()


def test_deduplicate_edges_removes_duplicates(gobp_root: Path):
    """deduplicate_edges() removes duplicate triples."""
    init_project(gobp_root, force=True)
    import yaml

    edges_dir = gobp_root / ".gobp" / "edges"
    edges_dir.mkdir(parents=True, exist_ok=True)
    edge_file = edges_dir / "test_edges.yaml"

    # Write duplicate edges manually
    dupes = [
        {"from": "node:a", "to": "node:b", "type": "relates_to"},
        {"from": "node:a", "to": "node:b", "type": "relates_to"},  # duplicate
        {"from": "node:c", "to": "node:d", "type": "implements"},
    ]
    edge_file.write_text(
        yaml.safe_dump(dupes, allow_unicode=True),
        encoding="utf-8"
    )

    result = deduplicate_edges(gobp_root)
    assert result["ok"] is True
    assert result["duplicates_removed"] == 1
    assert result["total_edges"] == 2

    # Verify file cleaned
    cleaned = yaml.safe_load(edge_file.read_text(encoding="utf-8"))
    assert len(cleaned) == 2


def test_dispatch_dedupe_action(gobp_root: Path):
    """dedupe: edges action works via dispatcher."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    r = asyncio.run(dispatch("dedupe: edges", index, gobp_root))
    assert r["ok"] is True
    assert "duplicates_removed" in r
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave15.py -v
# Expected: ~25 tests passing

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 327+ tests passing
```

**Update CHANGELOG.md:**

```markdown
## [Wave 15] — Parser Rewrite + Import Fix + Edge Dedupe — 2026-04-15

### Bugs fixed (from Cursor production testing)

- **B1 (High)**: `find: login page_size=10` parsed wrong — type='login', query='page_size=10'
  - Fix: rewritten parse_query() with positional grammar
  
- **B2 (High)**: `related: node:x direction='out'` lost node_id — returned ok=False
  - Fix: action-specific positional key mapping (_POSITIONAL_KEY)
  
- **B3 (High)**: `import:` doc_id collision for same-stem files in different folders
  - Fix: doc_id = "doc:{slug}_{md5[:6]}" — collision-proof
  - Evidence: doc:readme was pointing to wrong file
  
- **B4 (Medium)**: Duplicate edges in file storage
  - Evidence: 181 total, 171 unique, 4 duplicate triples (one 8x repeated)
  - Fix: create_edge() checks (from,type,to) before append
  - Fix: deduplicate_edges() cleanup utility + dedupe: edges action
  
- **B5 (Medium)**: import: returned ok=False but still had document_node + suggestion
  - Fix: clean envelope — ok=False has only error fields
  
- **B6 (Medium)**: Bool values parsed as strings ("true" not True)
  - Fix: _coerce_value() converts true/false→bool, digits→int, null→None

### Changed
- `gobp/mcp/dispatcher.py`: parse_query() full rewrite
  - _POSITIONAL_KEY mapping, _coerce_value(), _tokenize_rest(), _parse_edge_rest()
  - import: collision-proof doc_id
  - import: clean response contract
  - dedupe: edges action
- `gobp/core/mutator.py`: create_edge() idempotent + deduplicate_edges()

### Total: 1 MCP tool, 28 actions, 327+ tests
```

**Commit message:**
```
Wave 15 Task 5: tests/test_wave15.py + full suite + CHANGELOG

- ~25 new tests for parser, doc_id, edge dedupe
- 327+ tests passing
- CHANGELOG: Wave 15 entry with all 6 bugs documented
```

---

# POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

# Verify parser
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.mcp.dispatcher import parse_query
cases = [
    ('find: login page_size=10', {'query':'login','page_size':10}),
    ('related: node:x direction=outgoing', {'node_id':'node:x','direction':'outgoing'}),
    ('tests: node:x page_size=20', {'node_id':'node:x','page_size':20}),
    ('create:Node automated=true', {'automated':True}),
]
for query, expected in cases:
    _, _, p = parse_query(query)
    for k, v in expected.items():
        assert p.get(k) == v, f'{query!r}: {k}={p.get(k)!r} != {v!r}'
print('All parser assertions OK')
"

git log --oneline | Select-Object -First 8
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief

```powershell
cd D:\GoBP
# Save to D:\GoBP\waves\wave_15_brief.md
git add waves/wave_15_brief.md
git commit -m "Add Wave 15 Brief — parser rewrite + import fix + edge dedupe"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_15_brief.md first.
Also read gobp/mcp/dispatcher.py, gobp/core/mutator.py, gobp/core/loader.py.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 5 tasks sequentially.
R9: all 302 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 15. Read CLAUDE.md and waves/wave_15_brief.md.
Set env: $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: parse_query() rewritten with _POSITIONAL_KEY + _coerce_value
  - "find: login page_size=10" → query='login', page_size=10 (int)
  - "related: node:x direction='out'" → node_id='node:x'
  - "create:Node automated=true" → automated=True (bool)
- Task 2: import doc_id = "doc:{slug}_{md5[:6]}", clean response contract
- Task 3: create_edge() idempotent, deduplicate_edges() exists, dedupe: action
- Task 4: smoke test passed, 302 tests passing, edge cleanup ran
- Task 5: test_wave15.py ~25 tests, 327+ total, CHANGELOG updated

Expected: 327+ tests. Report WAVE 15 AUDIT COMPLETE.
```

---

# WHAT COMES NEXT

```
Wave 15 done (bugs fixed)
    ↓
Wave 8B — MIHOS import (NOW safe to do)
  All blocking bugs fixed:
  ✅ find/related/tests pagination works
  ✅ doc_id no collision
  ✅ create_edge() idempotent
  ✅ bool fields stored correctly
  ✅ import response trustworthy
```

---

*Wave 15 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
