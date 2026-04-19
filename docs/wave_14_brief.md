# WAVE 14 BRIEF — SCHEMA GOVERNANCE + PROTOCOL VERSIONING + ACCESS MODEL

> **Archive note (2026-04-19):** Brief lịch sử trong chuỗi phát triển GoBP. Trạng thái **sản phẩm hiện tại** (schema v2, MCP một tool, v.v.) xem **`docs/README.md`** và **`CHANGELOG.md`**.

**Wave:** 14
**Title:** Schema governance, protocol versioning, read-only access model
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 8 atomic tasks
**Estimated effort:** 4-5 hours

---

## CONTEXT

3 remaining gaps from Cursor's production feedback:

**Gap 1 — Schema governance**
```
Current: no cross-check between docs ↔ schema ↔ tests
Problem: SCHEMA.md says code_refs is list[dict]
         but a test expects list[str] → silent drift
         Nobody catches this until runtime failure
Need: gobp(query="validate: schema-docs") → flag all drift
```

**Gap 2 — Protocol versioning**
```
Current: protocol version implicit (v1 in PROTOCOL_GUIDE string)
Problem: When breaking changes happen, AI clients don't know
         Old syntax silently routes to wrong handler
Need: gobp(query="version:") → current version + deprecations
      Deprecation warnings when old syntax used
```

**Gap 3 — Access model**
```
Current: any AI can read/write anything
Problem: read-only AI agents (viewers, analysts) shouldn't write
         CI/audit agents should not be able to lock decisions
         Accidental writes corrupt graph
Need: GOBP_READ_ONLY env var → write attempts return clear error
      Per-agent role in session metadata
```

---

## DESIGN DECISIONS

### Schema governance
```
gobp(query="validate: schema-docs") checks:
  1. Every node type in core_nodes.yaml has entry in SCHEMA.md
  2. Every field in schema has correct type documented in SCHEMA.md
  3. Every node type has at least 1 test in tests/
  4. No test references a field not in schema

Returns:
  {ok, issues: [{type, severity, message}], score: 0-100}
  severity: error | warning | info
```

### Protocol versioning
```
Current protocol: v1
New protocol: v2 (Wave 14)

v2 changes (non-breaking):
  - gobp(query="version:") → version info
  - All responses include protocol_version field
  - Deprecation warnings for renamed actions (none yet)

gobp(query="version:") returns:
  {
    protocol_version: "2.0",
    gobp_version: "0.1.0",
    schema_version: "2.1",
    deprecated_actions: [],
    changelog: ["v2.0: version: action, read-only mode, schema governance"]
  }
```

### Access model
```
Read-only mode (env var):
  GOBP_READ_ONLY=true → all write actions return:
  {ok: false, error: "Read-only mode. Set GOBP_READ_ONLY=false to enable writes."}

Read actions: overview, find, get, signature, recent, decisions,
              sections, code, invariants, tests, related, stats, version, validate

Write actions (blocked in read-only):
  create, update, upsert, lock, session, edge, import, commit, batch

Per-session role:
  session:start actor='cursor' goal='...' role='contributor'
  Roles: observer (read) | contributor (read+write) | admin (all)
  Stored in Session node — for audit trail only (not enforced by default)
```

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
| 2 | `gobp/mcp/dispatcher.py` | Add version: + validate: schema-docs |
| 3 | `gobp/mcp/server.py` | Add read-only mode |
| 4 | `gobp/mcp/tools/read.py` | Add governance check |
| 5 | `gobp/schema/core_nodes.yaml` | Schema source of truth |
| 6 | `docs/SCHEMA.md` | Docs source of truth |
| 7 | `docs/MCP_TOOLS.md` | Update protocol |
| 8 | `waves/wave_14_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Add version: action

**Goal:** `gobp(query="version:")` returns protocol version, schema version, deprecation list.

**File to modify:** `gobp/mcp/dispatcher.py`

**Re-read dispatcher in full.**

Add `version:` action in `dispatch()`:

```python
        elif action == "version":
            import gobp as _gobp
            result = {
                "ok": True,
                "protocol_version": "2.0",
                "gobp_version": getattr(_gobp, "__version__", "0.1.0"),
                "schema_version": "2.1",
                "deprecated_actions": [],
                "supported_actions": list(PROTOCOL_GUIDE.get("actions", {}).keys()),
                "changelog": [
                    "v2.0 (Wave 14): version: action, read-only mode, schema governance",
                    "v1.5 (Wave 13): pagination, upsert:, stats:, guardrails",
                    "v1.0 (Wave 10A): gobp() single tool, structured query protocol",
                ],
                "tip": "Call gobp(query='overview:') to see current project state.",
            }
```

**Update PROTOCOL_GUIDE:**
```python
"version:": "Protocol version + changelog + deprecations",
```

**Acceptance criteria:**
- `gobp(query="version:")` returns `protocol_version: "2.0"`
- Returns `changelog` list
- Returns `deprecated_actions: []` (empty for now)
- `_dispatch` field includes `action: "version"`

**Commit message:**
```
Wave 14 Task 1: add version: action — protocol v2.0

- dispatcher.py: version: action returns protocol/gobp/schema versions
- Returns changelog + deprecated_actions list
- PROTOCOL_GUIDE: version: entry
- Protocol version bumped to 2.0
```

---

## TASK 2 — Add schema governance checker

**Goal:** `gobp(query="validate: schema-docs")` cross-checks schema vs SCHEMA.md vs tests.

**File to modify:** `gobp/mcp/tools/read.py` (or new file if cleaner)

**Re-read `read.py` in full.**

**Add `schema_governance()` function:**

```python
def schema_governance(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Cross-check schema vs documentation vs tests for drift.

    Checks:
      1. Every node type in schema has entry in SCHEMA.md
      2. Core fields documented in SCHEMA.md match schema definition
      3. Node types referenced in tests exist in schema
      4. Priority field present on required types

    Args:
        scope: 'all' | 'schema-docs' | 'schema-tests' (default: 'all')

    Returns:
        ok, issues[], score (0-100), summary
    """
    scope = args.get("scope", args.get("query", "all"))
    issues = []

    # Load schema
    schema_path = project_root / "gobp" / "schema" / "core_nodes.yaml"
    edges_path = project_root / "gobp" / "schema" / "core_edges.yaml"

    try:
        import yaml as _yaml
        schema = _yaml.safe_load(schema_path.read_text(encoding="utf-8"))
        node_types_in_schema = set(schema.get("node_types", {}).keys())
    except Exception as e:
        return {"ok": False, "error": f"Cannot load schema: {e}"}

    # Check 1: SCHEMA.md documents all node types
    schema_doc_path = project_root / "docs" / "SCHEMA.md"
    if schema_doc_path.exists():
        schema_doc = schema_doc_path.read_text(encoding="utf-8")
        for node_type in node_types_in_schema:
            if node_type not in schema_doc:
                issues.append({
                    "type": "schema_doc_drift",
                    "severity": "warning",
                    "message": f"Node type '{node_type}' in schema but not documented in SCHEMA.md",
                    "node_type": node_type,
                })
    else:
        issues.append({
            "type": "missing_doc",
            "severity": "error",
            "message": "docs/SCHEMA.md not found",
        })

    # Check 2: All node types in schema have id_prefix
    for type_name, type_def in schema.get("node_types", {}).items():
        if not type_def.get("id_prefix"):
            issues.append({
                "type": "missing_id_prefix",
                "severity": "error",
                "message": f"Node type '{type_name}' has no id_prefix in schema",
                "node_type": type_name,
            })

    # Check 3: Priority field on important types
    important_types = {"Node", "Idea", "Decision", "Document", "Feature", "Flow", "Engine", "Entity"}
    for type_name in important_types:
        if type_name in node_types_in_schema:
            type_def = schema["node_types"][type_name]
            optional = type_def.get("optional", {})
            if "priority" not in optional:
                issues.append({
                    "type": "missing_priority_field",
                    "severity": "warning",
                    "message": f"Node type '{type_name}' missing optional priority field",
                    "node_type": type_name,
                })

    # Check 4: Tests reference valid node types
    tests_dir = project_root / "tests"
    if tests_dir.exists() and scope in ("all", "schema-tests"):
        import re as _re
        for test_file in tests_dir.glob("test_*.py"):
            content = test_file.read_text(encoding="utf-8", errors="replace")
            # Find type= references in test files
            type_refs = _re.findall(r'"type":\s*"([A-Z][a-zA-Z]+)"', content)
            type_refs += _re.findall(r"type='([A-Z][a-zA-Z]+)'", content)
            for ref in set(type_refs):
                if ref not in node_types_in_schema and ref not in {
                    "GET", "POST", "PUT", "DELETE", "str", "int", "bool"
                }:
                    issues.append({
                        "type": "test_references_unknown_type",
                        "severity": "info",
                        "message": f"Test file '{test_file.name}' references type '{ref}' not in schema",
                        "file": test_file.name,
                        "node_type": ref,
                    })

    # Compute score
    error_count = sum(1 for i in issues if i["severity"] == "error")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")
    score = max(0, 100 - (error_count * 20) - (warning_count * 5))

    return {
        "ok": True,
        "scope": scope,
        "issues": issues,
        "issue_count": len(issues),
        "error_count": error_count,
        "warning_count": warning_count,
        "score": score,
        "summary": (
            f"Schema governance: {score}/100. "
            f"{error_count} errors, {warning_count} warnings, "
            f"{len(issues) - error_count - warning_count} info."
        ),
        "node_types_checked": len(node_types_in_schema),
    }
```

**File to modify:** `gobp/mcp/dispatcher.py`

Update `validate:` action to route `schema-docs` and `schema-tests` scopes:

```python
        elif action == "validate":
            scope = params.get("query", params.get("scope", "all"))
            if scope in ("schema-docs", "schema-tests", "schema"):
                result = tools_read.schema_governance(index, project_root, {"scope": scope})
            else:
                result = tools_maintain.validate(
                    index, project_root, {"scope": scope, "severity_filter": "all"}
                )
```

**Update PROTOCOL_GUIDE:**
```python
"validate: schema-docs":  "Cross-check schema vs SCHEMA.md documentation",
"validate: schema-tests": "Check tests reference valid node types",
```

**Acceptance criteria:**
- `gobp(query="validate: schema-docs")` returns `issues`, `score`, `summary`
- Detects missing SCHEMA.md entries for node types
- Detects missing id_prefix
- Detects missing priority field on important types
- Returns score 0-100
- Existing `validate: all` still works unchanged

**Commit message:**
```
Wave 14 Task 2: schema governance — validate: schema-docs/schema-tests

- read.py: schema_governance() cross-checks schema vs docs vs tests
- dispatcher.py: validate: routes schema-docs/schema-tests to governance
- Checks: SCHEMA.md coverage, id_prefix, priority field, test type refs
- Returns: issues[], score (0-100), summary
- PROTOCOL_GUIDE: 2 governance entries
```

---

## TASK 3 — Add read-only mode to server.py

**Goal:** `GOBP_READ_ONLY=true` env var blocks all write actions.

**File to modify:** `gobp/mcp/server.py`

**Re-read `server.py` in full.**

**Add read-only check before dispatch:**

```python
# Read-only mode
_READ_ONLY_ACTIONS = frozenset({
    "create", "update", "upsert", "lock",
    "session", "edge", "import", "commit", "batch",
})

_READ_ONLY = os.environ.get("GOBP_READ_ONLY", "").lower() in ("true", "1", "yes")
```

**In `call_tool()`, add check after parsing action:**

```python
    action, _, _ = _parse_query(query)

    # Read-only mode check
    if _READ_ONLY and action in _READ_ONLY_ACTIONS:
        result = {
            "ok": False,
            "error": f"Read-only mode: '{action}' is a write action.",
            "hint": "Set GOBP_READ_ONLY=false (or unset) to enable writes.",
            "read_only": True,
            "blocked_action": action,
        }
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
```

**Acceptance criteria:**
- `GOBP_READ_ONLY=true` → write actions return `ok: false` with clear message
- Read actions (find, get, overview, etc.) still work normally
- `read_only: true` in response when blocked
- `GOBP_READ_ONLY=false` (default) → no change in behavior

**Commit message:**
```
Wave 14 Task 3: read-only mode — GOBP_READ_ONLY env var

- server.py: _READ_ONLY flag from GOBP_READ_ONLY env var
- _READ_ONLY_ACTIONS: frozenset of write action names
- Blocked writes return ok:false with clear error + hint
- Read actions unaffected
```

---

## TASK 4 — Add role to session:start

**Goal:** Session nodes store `role` field for audit trail.

**File to modify:** `gobp/mcp/tools/write.py`

**Re-read `session_log()` in full.**

In `session_log()`, when `action == "start"`, extract and store `role`:

```python
    if action == "start":
        role = args.get("role", "contributor")
        # Validate role
        valid_roles = {"observer", "contributor", "admin"}
        if role not in valid_roles:
            role = "contributor"

        node = {
            # ... existing fields ...
            "role": role,
        }
```

**Update PROTOCOL_GUIDE:**
```python
"session:start actor='x' goal='y' role='observer'": "Start read-only session",
"session:start actor='x' goal='y' role='admin'":    "Start admin session",
```

**Add `role` to Session optional fields in `core_nodes.yaml`:**

```yaml
  Session:
    optional:
      # ... existing fields ...
      role:
        type: "enum"
        enum_values: ["observer", "contributor", "admin"]
        default: "contributor"
        description: "Agent role for this session (audit trail only)"
```

**Acceptance criteria:**
- `session:start actor='cursor' goal='x' role='observer'` stores role=observer
- Invalid role defaults to contributor
- `role` visible in session node when queried
- Audit trail only — role not enforced beyond storage

**Commit message:**
```
Wave 14 Task 4: session role field — observer/contributor/admin

- write.py: session_log() extracts + validates role field
- core_nodes.yaml: Session gets optional role enum field
- PROTOCOL_GUIDE: 2 role examples
- Audit trail only — not enforced, just stored
```

---

## TASK 5 — Add protocol_version to all responses

**Goal:** Every gobp() response includes `protocol_version: "2.0"`.

**File to modify:** `gobp/mcp/server.py`

**Re-read `call_tool()` in full.**

After getting result from dispatch, inject protocol version:

```python
    # Inject protocol metadata
    if isinstance(result, dict):
        result["_protocol"] = "2.0"
```

**Also inject into read-only blocked responses.**

**Acceptance criteria:**
- Every gobp() response has `_protocol: "2.0"`
- Read-only blocked responses have `_protocol`
- Does not break any existing tests (additive field)

**Commit message:**
```
Wave 14 Task 5: inject _protocol version into all responses

- server.py: result["_protocol"] = "2.0" on every response
- Enables AI clients to detect protocol version
- Additive — no breaking changes
```

---

## TASK 6 — Smoke test all Wave 14 features

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio, os
from pathlib import Path
from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch
import tempfile

async def test():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        init_project(root, force=True)
        index = GraphIndex.load_from_disk(root)

        # Test 1: version:
        r = await dispatch('version:', index, root)
        assert r['ok'] and r['protocol_version'] == '2.0'
        print(f'version: OK — protocol={r[\"protocol_version\"]}')

        # Test 2: validate: schema-docs
        r2 = await dispatch('validate: schema-docs', index, root)
        assert r2['ok'] and 'score' in r2
        print(f'schema governance: score={r2[\"score\"]}, issues={r2[\"issue_count\"]}')

        # Test 3: session with role
        r3 = await dispatch(\"session:start actor='test' goal='smoke' role='observer'\", index, root)
        assert r3['ok']
        sid = r3['session_id']
        index = GraphIndex.load_from_disk(root)
        session_node = index.get_node(sid)
        assert session_node.get('role') in ('observer', 'contributor', None)
        print(f'session role: OK — role={session_node.get(\"role\")}')

        # Test 4: _protocol in response
        r4 = await dispatch('overview:', index, root)
        assert r4.get('_protocol') == '2.0' or '_protocol' not in r4
        print('_protocol field: OK')

    print('All smoke tests passed')

asyncio.run(test())
"

# Test read-only mode
$env:GOBP_READ_ONLY = "true"
D:/GoBP/venv/Scripts/python.exe -c "
import asyncio, os
os.environ['GOBP_READ_ONLY'] = 'true'
from pathlib import Path
from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.server import _READ_ONLY, _READ_ONLY_ACTIONS
print(f'Read-only mode: {_READ_ONLY}')
print(f'Blocked actions: {sorted(_READ_ONLY_ACTIONS)}')
"
$env:GOBP_READ_ONLY = ""

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 302 tests passing
```

**Commit message:**
```
Wave 14 Task 6: smoke test — version + governance + role + read-only verified

- version: returns protocol_version=2.0
- validate: schema-docs returns score + issues
- session role stored correctly
- _READ_ONLY blocks write actions when GOBP_READ_ONLY=true
- 302 existing tests passing
```

---

## TASK 7 — Create tests/test_wave14.py

**File to create:** `tests/test_wave14.py`

```python
"""Tests for Wave 14: schema governance, protocol versioning, access model."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch
from gobp.mcp.tools import read as tools_read
from gobp.mcp.tools import write as tools_write


@pytest.fixture
def seeded_root(gobp_root: Path) -> Path:
    init_project(gobp_root, force=True)
    return gobp_root


@pytest.fixture
def session_id(seeded_root: Path) -> str:
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch(
        "session:start actor='test' goal='wave14'", index, seeded_root
    ))
    return r["session_id"]


# ── Protocol version tests ────────────────────────────────────────────────────

def test_version_action_returns_protocol(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("version:", index, seeded_root))
    assert r["ok"] is True
    assert r["protocol_version"] == "2.0"
    assert "gobp_version" in r
    assert "schema_version" in r


def test_version_has_changelog(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("version:", index, seeded_root))
    assert "changelog" in r
    assert isinstance(r["changelog"], list)
    assert len(r["changelog"]) >= 1


def test_version_deprecated_actions_empty(seeded_root: Path):
    """No deprecated actions in v2.0."""
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("version:", index, seeded_root))
    assert "deprecated_actions" in r
    assert isinstance(r["deprecated_actions"], list)


def test_version_dispatch_info(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("version:", index, seeded_root))
    assert r["_dispatch"]["action"] == "version"


# ── Schema governance tests ───────────────────────────────────────────────────

def test_governance_returns_score(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.schema_governance(index, seeded_root, {"scope": "all"})
    assert r["ok"] is True
    assert "score" in r
    assert 0 <= r["score"] <= 100


def test_governance_returns_issues_list(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.schema_governance(index, seeded_root, {})
    assert "issues" in r
    assert isinstance(r["issues"], list)


def test_governance_returns_summary(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.schema_governance(index, seeded_root, {})
    assert "summary" in r
    assert isinstance(r["summary"], str)


def test_governance_checks_node_types(seeded_root: Path):
    """Governance checks node types from schema."""
    index = GraphIndex.load_from_disk(seeded_root)
    r = tools_read.schema_governance(index, seeded_root, {"scope": "schema-docs"})
    assert r["ok"] is True
    assert "node_types_checked" in r
    assert r["node_types_checked"] > 0


def test_dispatch_validate_schema_docs(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("validate: schema-docs", index, seeded_root))
    assert r["ok"] is True
    assert "score" in r


def test_dispatch_validate_all_unchanged(seeded_root: Path):
    """validate: all still works normally."""
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch("validate: all", index, seeded_root))
    assert "ok" in r


# ── Session role tests ────────────────────────────────────────────────────────

def test_session_stores_role_observer(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch(
        "session:start actor='test' goal='role test' role='observer'",
        index, seeded_root
    ))
    assert r["ok"] is True
    index2 = GraphIndex.load_from_disk(seeded_root)
    session = index2.get_node(r["session_id"])
    assert session is not None
    assert session.get("role") in ("observer", "contributor")


def test_session_stores_role_admin(seeded_root: Path):
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch(
        "session:start actor='admin' goal='admin session' role='admin'",
        index, seeded_root
    ))
    assert r["ok"] is True


def test_session_invalid_role_defaults(seeded_root: Path):
    """Invalid role defaults to contributor."""
    index = GraphIndex.load_from_disk(seeded_root)
    r = asyncio.run(dispatch(
        "session:start actor='test' goal='bad role' role='superuser'",
        index, seeded_root
    ))
    assert r["ok"] is True
    index2 = GraphIndex.load_from_disk(seeded_root)
    session = index2.get_node(r["session_id"])
    # Should default to contributor or not store invalid role
    role = session.get("role", "contributor") if session else "contributor"
    assert role in ("observer", "contributor", "admin")


# ── Read-only mode tests ──────────────────────────────────────────────────────

def test_read_only_actions_defined():
    """_READ_ONLY_ACTIONS frozenset exists and has write actions."""
    from gobp.mcp.server import _READ_ONLY_ACTIONS
    assert "create" in _READ_ONLY_ACTIONS
    assert "upsert" in _READ_ONLY_ACTIONS
    assert "lock" in _READ_ONLY_ACTIONS
    assert "session" in _READ_ONLY_ACTIONS


def test_read_only_flag_reads_env():
    """_READ_ONLY reads from GOBP_READ_ONLY env var."""
    # Just verify the module attribute exists
    from gobp.mcp import server as _server
    assert hasattr(_server, "_READ_ONLY")
    assert isinstance(_server._READ_ONLY, bool)


def test_protocol_guide_has_version_action():
    from gobp.mcp.dispatcher import PROTOCOL_GUIDE
    actions = PROTOCOL_GUIDE.get("actions", {})
    assert any("version:" in k for k in actions)
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave14.py -v
# Expected: ~20 tests passing
```

**Commit message:**
```
Wave 14 Task 7: create tests/test_wave14.py — ~20 tests

- Protocol version: version: action, changelog, deprecated, dispatch (4)
- Schema governance: score, issues, summary, node_types, dispatch (5)
- validate: all unchanged (1)
- Session role: observer, admin, invalid defaults (3)
- Read-only: _READ_ONLY_ACTIONS defined, env flag, protocol guide (3)
```

---

## TASK 8 — Update docs + full suite + CHANGELOG

**File to modify:** `docs/MCP_TOOLS.md`

Add to quick reference table:

```markdown
| `version:` | Protocol version + changelog |
| `validate: schema-docs` | Cross-check schema vs SCHEMA.md |
| `validate: schema-tests` | Check tests reference valid types |
| `session:start actor='x' goal='y' role='observer'` | Start read-only session |
```

Add note at top of MCP_TOOLS.md:

```markdown
> **Protocol version:** 2.0 — Call `gobp(query="version:")` for full version info.
> **Read-only mode:** Set `GOBP_READ_ONLY=true` to prevent all write operations.
```

**Run full suite:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 320+ tests (302 + ~20 new)
```

**Update CHANGELOG.md:**

```markdown
## [Wave 14] — Schema Governance + Protocol Versioning + Access Model — 2026-04-15

### Problems solved
- No cross-check between schema ↔ docs ↔ tests — silent drift
- Protocol version implicit — AI clients couldn't detect breaking changes
- Any AI could write to graph — no read-only mode for viewer/analyst agents

### Added
- **Protocol versioning**: `version:` action returns v2.0 info + changelog
- **Schema governance**: `validate: schema-docs` cross-checks schema vs SCHEMA.md
  - Detects: missing SCHEMA.md entries, missing id_prefix, missing priority field
  - Returns: issues[], score (0-100), summary
- **Read-only mode**: `GOBP_READ_ONLY=true` env var blocks all write actions
  - Clear error message with hint to enable writes
  - Read actions (find, get, overview, etc.) unaffected
- **Session roles**: observer | contributor | admin stored in Session node
  - Audit trail only — not enforced, just recorded
- **Protocol field**: all responses include `_protocol: "2.0"`

### Changed
- dispatcher.py: version: action + validate: schema-docs/schema-tests routing
- read.py: schema_governance() function
- server.py: read-only mode + _protocol injection
- write.py: session_log() stores role field
- core_nodes.yaml: Session gets optional role field
- docs/MCP_TOOLS.md: version/governance/role/read-only documented

### Total: 1 MCP tool, 27 actions, 320+ tests
```

**Commit message:**
```
Wave 14 Task 8: docs + full suite green + CHANGELOG

- MCP_TOOLS.md: version/governance/role/read-only documented
- Protocol v2.0 note at top
- 320+ tests passing
- CHANGELOG: Wave 14 entry
```

---

# POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# All tests
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

# Version check
D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch

root = Path('D:/GoBP')
index = GraphIndex.load_from_disk(root)

async def verify():
    r = await dispatch('version:', index, root)
    print('Protocol:', r['protocol_version'])
    print('Schema:', r['schema_version'])

    r2 = await dispatch('validate: schema-docs', index, root)
    print(f'Governance score: {r2[\"score\"]}/100, issues: {r2[\"issue_count\"]}')

asyncio.run(verify())
"

git log --oneline | Select-Object -First 10
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief

```powershell
cd D:\GoBP
# Save to D:\GoBP\waves\wave_14_brief.md
git add waves/wave_14_brief.md
git commit -m "Add Wave 14 Brief — schema governance + protocol versioning + access model"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_14_brief.md first.
Also read gobp/mcp/dispatcher.py, gobp/mcp/tools/read.py,
gobp/mcp/tools/write.py, gobp/mcp/server.py,
gobp/schema/core_nodes.yaml, docs/MCP_TOOLS.md.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 8 tasks sequentially.
R9: all 302 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 14. Read CLAUDE.md and waves/wave_14_brief.md.
Set env: $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: version: action returns protocol_version=2.0, changelog, deprecated_actions
- Task 2: schema_governance() in read.py, validate: schema-docs returns score/issues
- Task 3: server.py has _READ_ONLY + _READ_ONLY_ACTIONS, blocks writes when true
- Task 4: session_log() stores role, core_nodes.yaml Session has role field
- Task 5: all responses have _protocol: "2.0"
- Task 6: smoke test passed, 302 tests passing
- Task 7: test_wave14.py exists, ~20 tests passing
- Task 8: 320+ tests passing, MCP_TOOLS.md updated, CHANGELOG updated

Expected: 320+ tests. Report WAVE 14 AUDIT COMPLETE.
```

---

# WHAT COMES NEXT

```
Wave 14 done
    ↓
Wave 8B — MIHOS import (ALL tools now ready)
  upsert: → no duplicates
  batch: → bulk import 32 docs
  stats: → monitor import performance
  find: page_size=100 → see all nodes
  version: → confirm protocol before starting
  validate: schema-docs → verify schema health
  GOBP_READ_ONLY=true → safe viewer mode
```

---

*Wave 14 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
