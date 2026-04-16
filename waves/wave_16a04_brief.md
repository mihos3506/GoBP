# WAVE 16A04 BRIEF — FULL TEST + REFACTOR GoBP

**Wave:** 16A04
**Title:** Full test coverage audit + code refactor
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-16
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 10 atomic tasks
**Estimated effort:** 6-8 hours

---

## CONTEXT

Current state after Wave 16A03:
```
421 tests passing
read.py:       1647 lines — too large, multiple concerns
dispatcher.py:  971 lines — parse logic + dispatch logic mixed
mutator.py:     524 lines — OK, minor cleanup needed
db.py:          441 lines — review needed
write.py:       427 lines — OK
```

**Goals:**
1. Split `read.py` into focused modules
2. Split `dispatcher.py` — separate parser from dispatcher
3. Fix `_generate_session_id()` format inconsistency
4. Dead code removal
5. Type hints audit
6. Test coverage gaps filled
7. Naming consistency with new ID format

---

## DESIGN

### read.py split
```
gobp/mcp/tools/read.py (1647 lines) → split into:

  gobp/mcp/tools/read.py          — core read: find, get, context, related
  gobp/mcp/tools/read_governance.py — validate:, schema_governance, metadata_lint
  gobp/mcp/tools/read_priority.py  — recompute_priorities, priority helpers
  gobp/mcp/tools/read_interview.py — node_template, node_interview
```

### dispatcher.py split
```
gobp/mcp/dispatcher.py (971 lines) → split into:

  gobp/mcp/parser.py     — parse_query(), _coerce_value(), _tokenize_rest(),
                            _normalize_type(), _POSITIONAL_KEY, _TYPE_CANONICAL
  gobp/mcp/dispatcher.py — dispatch() only, imports from parser.py
```

### Session ID fix
```
mutator.py _generate_session_id():
  OLD: session:2026-04-16_a3f7c2abc
  NEW: meta.session.2026-04-16.a3f7c2abc
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 421 existing tests must pass after every task.

**CRITICAL:**
- Each split must maintain 100% backward compatibility
- All imports must be updated everywhere
- No functional changes — refactor only
- Run full suite after EACH task

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 421 tests passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/mcp/tools/read.py` | Split target |
| 3 | `gobp/mcp/dispatcher.py` | Split target |
| 4 | `gobp/core/mutator.py` | Session ID fix |
| 5 | `gobp/mcp/server.py` | Import update |
| 6 | `waves/wave_16a04_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Fix _generate_session_id() format

**Goal:** Session IDs use new `meta.session.YYYY-MM-DD.hash` format.

**File to modify:** `gobp/core/mutator.py`

**Re-read `_generate_session_id()` in full.**

```python
def _generate_session_id(goal: str = "") -> str:
    """Generate session ID in new format.
    Format: meta.session.YYYY-MM-DD.XXXXXXXXX
    """
    from datetime import datetime, timezone
    import uuid as _uuid
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    short_hash = _uuid.uuid4().hex[:9]
    return f"meta.session.{date_str}.{short_hash}"
```

**Run full suite after:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 421 tests passing
```

**Commit message:**
```
Wave 16A04 Task 1: fix _generate_session_id() — meta.session.YYYY-MM-DD.hash format

- mutator.py: session IDs now use new dot-format
- Consistent with Wave 16A03 ID design
- Old sessions in .gobp/ still resolve via legacy_id_map
```

---

## TASK 2 — Extract parser to gobp/mcp/parser.py

**Goal:** Separate parse logic from dispatch logic in dispatcher.py.

**File to create:** `gobp/mcp/parser.py`

Move these from `dispatcher.py` to `parser.py`:
- `_POSITIONAL_KEY` dict
- `_TYPE_CANONICAL` dict
- `VALID_TESTKINDS` (import from id_config)
- `_coerce_value()`
- `_tokenize_rest()`
- `_parse_edge_rest()`
- `parse_query()`
- `_normalize_type()`

```python
"""GoBP query parser.

Parses gobp() query strings into (action, node_type, params).
Separated from dispatcher for clarity and testability.
"""

from __future__ import annotations
from typing import Any

# Action → positional param key mapping
_POSITIONAL_KEY: dict[str, str] = {
    "find":       "query",
    "get":        "node_id",
    # ... full dict from dispatcher.py
}

# ... rest of parse functions
```

**File to modify:** `gobp/mcp/dispatcher.py`

Replace moved code with imports:
```python
from gobp.mcp.parser import (
    parse_query, _normalize_type, _POSITIONAL_KEY, PROTOCOL_GUIDE
)
```

**Verify imports work:**
```powershell
D:/GoBP/venv/Scripts/python.exe -c "from gobp.mcp.parser import parse_query; print(parse_query('find: login page_size=10'))"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
```

**Commit message:**
```
Wave 16A04 Task 2: extract parser to gobp/mcp/parser.py

- parser.py: parse_query, _normalize_type, _coerce_value, _tokenize_rest
- dispatcher.py: imports from parser.py
- No functional changes — pure refactor
- 421 tests passing
```

---

## TASK 3 — Extract governance to read_governance.py

**Goal:** Split validate/governance functions out of read.py.

**File to create:** `gobp/mcp/tools/read_governance.py`

Move from `read.py`:
- `_METADATA_REQUIREMENTS` dict
- `schema_governance()`
- `metadata_lint()`

```python
"""GoBP governance read tools.

Schema governance, metadata linting, validation.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex

_METADATA_REQUIREMENTS: dict[str, list[str]] = {
    # ... from read.py
}

def schema_governance(...): ...
def metadata_lint(...): ...
```

**File to modify:** `gobp/mcp/tools/read.py`

Replace with imports:
```python
from gobp.mcp.tools.read_governance import (
    schema_governance, metadata_lint, _METADATA_REQUIREMENTS
)
```

**Commit message:**
```
Wave 16A04 Task 3: extract governance to read_governance.py

- read_governance.py: schema_governance, metadata_lint, _METADATA_REQUIREMENTS
- read.py: imports from read_governance.py
- No functional changes
- 421 tests passing
```

---

## TASK 4 — Extract priority to read_priority.py

**Goal:** Split priority computation out of read.py.

**File to create:** `gobp/mcp/tools/read_priority.py`

Move from `read.py`:
- `recompute_priorities()`

```python
"""GoBP priority read tools.

Priority recomputation from graph topology.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex

def recompute_priorities(...): ...
```

**File to modify:** `gobp/mcp/tools/read.py`

Replace with import:
```python
from gobp.mcp.tools.read_priority import recompute_priorities
```

**Commit message:**
```
Wave 16A04 Task 4: extract priority to read_priority.py

- read_priority.py: recompute_priorities()
- read.py: imports from read_priority.py
- No functional changes
- 421 tests passing
```

---

## TASK 5 — Extract interview to read_interview.py

**Goal:** Split interview/template functions out of read.py.

**File to create:** `gobp/mcp/tools/read_interview.py`

Move from `read.py`:
- `_NODE_EDGE_REQUIREMENTS` dict
- `node_template()`
- `node_interview()`

```python
"""GoBP interview read tools.

Node template declarations and guided relationship interviews.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex

_NODE_EDGE_REQUIREMENTS: dict[str, dict] = {
    # ... from read.py
}

def node_template(...): ...
def node_interview(...): ...
```

**File to modify:** `gobp/mcp/tools/read.py`

Replace with imports:
```python
from gobp.mcp.tools.read_interview import (
    node_template, node_interview, _NODE_EDGE_REQUIREMENTS
)
```

**Commit message:**
```
Wave 16A04 Task 5: extract interview to read_interview.py

- read_interview.py: node_template, node_interview, _NODE_EDGE_REQUIREMENTS
- read.py: imports from read_interview.py
- No functional changes
- 421 tests passing
```

---

## TASK 6 — Dead code removal + naming cleanup

**Goal:** Remove unused code, fix naming inconsistencies.

**Files to audit:** All gobp/ Python files.

**Dead code checklist:**
```
1. Any functions not called anywhere
2. Commented-out code blocks (>5 lines)
3. Duplicate utility functions across files
4. Old _get_type_prefix() if still exists in dispatcher.py
5. Any TIER_WEIGHTS dict if still exists after id_config migration
6. Unused imports in each file
```

**Naming consistency:**
```
Check for old ID format references in:
  - Docstrings: "node:x" → "ops.flow:XXXXXXXX" or "slug.group.number"
  - Comments: update examples
  - Error messages: update ID format examples
```

**Run:**
```powershell
# Find unused imports
D:/GoBP/venv/Scripts/python.exe -m py_compile gobp/mcp/dispatcher.py
D:/GoBP/venv/Scripts/python.exe -m py_compile gobp/mcp/tools/read.py
D:/GoBP/venv/Scripts/python.exe -m py_compile gobp/core/mutator.py

# Check for old format in docstrings
Select-String -Path "D:\GoBP\gobp\**\*.py" -Pattern "node:[a-z]" -Recurse | Select-Object -First 20
```

**Commit message:**
```
Wave 16A04 Task 6: dead code removal + naming cleanup

- Remove unused functions/imports
- Update docstring examples to new ID format
- Remove old _get_type_prefix() if still present
- 421 tests passing
```

---

## TASK 7 — Type hints audit

**Goal:** All public functions have complete type hints.

**Priority files:**
```
gobp/core/graph.py       — add return types
gobp/core/mutator.py     — add param types
gobp/mcp/parser.py       — add full hints
gobp/mcp/tools/read.py   — add return types
```

**Standard:**
```python
# Before:
def find(index, project_root, args):

# After:
def find(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# 421 tests still passing
```

**Commit message:**
```
Wave 16A04 Task 7: type hints audit — all public functions annotated

- graph.py: complete return types
- mutator.py: complete param types
- parser.py: full type hints
- read.py: return types on all functions
- 421 tests passing
```

---

## TASK 8 — Test coverage gaps

**Goal:** Find and fill test coverage gaps.

**Run coverage:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --tb=short -q
D:/GoBP/venv/Scripts/python.exe -m pip install pytest-cov --break-system-packages -q
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --cov=gobp --cov-report=term-missing -q 2>&1 | Select-String "TOTAL|gobp/core|gobp/mcp" | Select-Object -First 20
```

**Cover gaps in these areas:**
```
1. parse_query() edge cases:
   - Empty query ""
   - Query with only whitespace
   - Malformed key=value pairs

2. generate_external_id() edge cases:
   - Very long names (>40 chars)
   - Names with only special chars
   - TestCase with invalid testkind

3. create_edge() edge cases:
   - Edge with missing from/to
   - Edge with empty type

4. migrate_ids.py:
   - Empty project (no nodes)
   - Project with only new-format nodes
```

**File to modify:** `tests/test_wave16a04.py` (new)

```python
"""Tests for Wave 16A04: coverage gaps, refactor verification."""

from __future__ import annotations
import asyncio
from pathlib import Path
import pytest

from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.parser import parse_query, _normalize_type
from gobp.mcp.dispatcher import dispatch
from gobp.core.id_config import generate_external_id, make_id_slug


# ── Parser edge cases ─────────────────────────────────────────────────────────

def test_parse_empty_query():
    a, t, p = parse_query("")
    assert a == "overview"

def test_parse_whitespace_only():
    a, t, p = parse_query("   ")
    assert a == "overview"

def test_parse_no_colon():
    a, t, p = parse_query("some query")
    assert a == "find"
    assert p.get("query") == "some query"

def test_normalize_type_all_variants():
    assert _normalize_type("decision") == "Decision"
    assert _normalize_type("DECISION") == "Decision"
    assert _normalize_type("DeciSion") == "Decision"
    assert _normalize_type("flow") == "Flow"
    assert _normalize_type("TESTCASE") == "TestCase"
    assert _normalize_type("unknown_type") == "unknown_type"


# ── ID generation edge cases ──────────────────────────────────────────────────

def test_slug_very_long_name():
    slug = make_id_slug("A" * 100)
    assert len(slug) <= 40

def test_slug_only_special_chars():
    slug = make_id_slug("!@#$%^&*()")
    assert slug == "" or slug.strip("_") == ""

def test_generate_id_invalid_testkind():
    eid = generate_external_id("TestCase", "My Test", "invalid_kind")
    assert ".test.unit." in eid  # defaults to unit

def test_generate_id_empty_name():
    eid = generate_external_id("Flow", "")
    assert ".ops." in eid
    assert len(eid.split(".")[-1]) == 8  # 8-digit number


# ── Session ID format ─────────────────────────────────────────────────────────

def test_session_id_new_format(gobp_root: Path):
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    r = asyncio.run(dispatch(
        "session:start actor='test' goal='format test'", index, gobp_root
    ))
    assert r["ok"] is True
    sid = r["session_id"]
    assert sid.startswith("meta.session."), f"Wrong format: {sid}"
    assert len(sid.split(".")) == 4  # meta.session.YYYY-MM-DD.hash


# ── Module split verification ─────────────────────────────────────────────────

def test_parser_module_importable():
    from gobp.mcp.parser import parse_query, _normalize_type
    assert callable(parse_query)
    assert callable(_normalize_type)

def test_read_governance_importable():
    from gobp.mcp.tools.read_governance import schema_governance, metadata_lint
    assert callable(schema_governance)
    assert callable(metadata_lint)

def test_read_priority_importable():
    from gobp.mcp.tools.read_priority import recompute_priorities
    assert callable(recompute_priorities)

def test_read_interview_importable():
    from gobp.mcp.tools.read_interview import node_template, node_interview
    assert callable(node_template)
    assert callable(node_interview)


# ── Edge creation edge cases ──────────────────────────────────────────────────

def test_create_edge_missing_from(gobp_root: Path):
    init_project(gobp_root, force=True)
    from gobp.core.mutator import create_edge
    import yaml
    schema = yaml.safe_load(
        open("gobp/schema/core_edges.yaml", encoding="utf-8")
    )
    r = create_edge(gobp_root, {"to": "node:b", "type": "relates_to"}, schema)
    assert r["ok"] is False

def test_create_edge_empty_type(gobp_root: Path):
    init_project(gobp_root, force=True)
    from gobp.core.mutator import create_edge
    import yaml
    schema = yaml.safe_load(
        open("gobp/schema/core_edges.yaml", encoding="utf-8")
    )
    r = create_edge(gobp_root, {"from": "node:a", "to": "node:b", "type": ""}, schema)
    assert r["ok"] is False
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave16a04.py -v
# Expected: ~20 tests

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 441+ tests
```

**Commit message:**
```
Wave 16A04 Task 8: test coverage gaps — parser, ID, session, modules

- test_wave16a04.py: ~20 tests
- Parser edge cases: empty, whitespace, no colon
- ID edge cases: long names, special chars, invalid testkind
- Session ID format verification
- Module split imports verified
- 441+ tests passing
```

---

## TASK 9 — Final read.py size check + docs update

**Goal:** Verify read.py is significantly reduced. Update module docs.

```powershell
# Check file sizes after refactor
Get-ChildItem D:\GoBP\gobp -Recurse -Filter "*.py" |
  Select-Object Name, @{N='Lines';E={(Get-Content $_.FullName).Count}} |
  Sort-Object Lines -Descending |
  Select-Object -First 15
```

**Expected after refactor:**
```
read.py:              ~700 lines  (down from 1647)
dispatcher.py:        ~500 lines  (down from 971)
parser.py:            ~250 lines  (new)
read_governance.py:   ~200 lines  (new)
read_priority.py:     ~100 lines  (new)
read_interview.py:    ~200 lines  (new)
```

**Update `docs/ARCHITECTURE.md`** — add module split diagram:

```markdown
## MCP Tools Structure

gobp/mcp/
  parser.py          — Query parsing (parse_query, _normalize_type)
  dispatcher.py      — Action dispatch routing
  server.py          — MCP server entry point
  tools/
    read.py          — Core reads: find, get, related, sections, context
    read_governance.py — Schema governance, metadata linting
    read_priority.py  — Priority recomputation
    read_interview.py — Node templates, guided interviews
    write.py         — Node upsert, session, decision lock
    maintain.py      — Validate, prune, stats
```

**Commit message:**
```
Wave 16A04 Task 9: verify refactor sizes + update ARCHITECTURE.md

- read.py: ~700 lines (down from 1647)
- dispatcher.py: ~500 lines (down from 971)
- ARCHITECTURE.md: module structure documented
```

---

## TASK 10 — Full suite + CHANGELOG

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 441+ tests passing
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A04] — Full Test + Refactor — 2026-04-16

### Refactor
- dispatcher.py (971 lines) → parser.py + dispatcher.py
  - parser.py: parse_query, _normalize_type, _coerce_value
  - dispatcher.py: dispatch() only
- read.py (1647 lines) → 4 focused modules:
  - read.py: core reads (find, get, related)
  - read_governance.py: schema_governance, metadata_lint
  - read_priority.py: recompute_priorities
  - read_interview.py: node_template, node_interview

### Fixes
- mutator.py: _generate_session_id() → meta.session.YYYY-MM-DD.hash format
- Dead code removed
- Type hints complete on all public functions
- Docstring examples updated to new ID format

### Tests
- ~20 new tests: parser edge cases, ID edge cases, module imports
- 441+ tests total
```

**Commit message:**
```
Wave 16A04 Task 10: full suite green + CHANGELOG

- 441+ tests passing
- CHANGELOG: Wave 16A04 entry
```

---

# POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

# Verify module structure
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.mcp.parser import parse_query
from gobp.mcp.tools.read_governance import schema_governance
from gobp.mcp.tools.read_priority import recompute_priorities
from gobp.mcp.tools.read_interview import node_template
print('All modules importable OK')

# Check file sizes
import os
files = [
    'gobp/mcp/parser.py',
    'gobp/mcp/dispatcher.py',
    'gobp/mcp/tools/read.py',
    'gobp/mcp/tools/read_governance.py',
    'gobp/mcp/tools/read_priority.py',
    'gobp/mcp/tools/read_interview.py',
]
for f in files:
    if os.path.exists(f):
        lines = len(open(f).readlines())
        print(f'{f}: {lines} lines')
"

git log --oneline | Select-Object -First 12
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief

```powershell
cd D:\GoBP
# Save to D:\GoBP\waves\wave_16a04_brief.md
git add waves/wave_16a04_brief.md
git commit -m "Add Wave 16A04 Brief — full test + refactor"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_16a04_brief.md first.
Also read gobp/mcp/tools/read.py, gobp/mcp/dispatcher.py,
gobp/core/mutator.py, gobp/mcp/server.py.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 10 tasks sequentially.
R9: all 421 existing tests must pass after every task.
1 task = 1 commit, exact message.

CRITICAL: Tasks 2-5 are refactor only — NO functional changes.
          Run full suite after each task to verify nothing broke.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 16A04. Read CLAUDE.md and waves/wave_16a04_brief.md.
Set env: $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: _generate_session_id() returns meta.session.YYYY-MM-DD.hash
- Task 2: gobp/mcp/parser.py exists, dispatcher.py imports from it
- Task 3: gobp/mcp/tools/read_governance.py exists
- Task 4: gobp/mcp/tools/read_priority.py exists
- Task 5: gobp/mcp/tools/read_interview.py exists
- Task 6: dead code removed, old format references cleaned
- Task 7: type hints on all public functions
- Task 8: test_wave16a04.py ~20 tests, all edge cases covered
- Task 9: read.py ~700 lines, dispatcher.py ~500 lines
- Task 10: 441+ tests passing, CHANGELOG updated

BLOCKING RULE: Gặp vấn đề không tự xử lý → DỪNG ngay, báo CEO.

Expected: 441+ tests. Report WAVE 16A04 AUDIT COMPLETE.
```

---

# WHAT COMES NEXT

```
Wave 16A04 done (GoBP fully refactored + tested)
    ↓
Wave 8B — MIHOS import
  Clean codebase → import MIHOS 32 docs
  verify_gate.ops.XXXXXXXX
  trustgate_engine.ops.XXXXXXXX
    ↓
GoBP AI Guide document
Wave 17A01 — A2A Interview
```

---

*Wave 16A04 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-16*

◈
