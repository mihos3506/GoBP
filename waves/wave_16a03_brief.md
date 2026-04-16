# WAVE 16A03 BRIEF — NEW ID FORMAT: slug.group.number

**Wave:** 16A03
**Title:** New external ID format: {slug}.{group}.{8digits} — name-first, human-readable
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-16
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 8 atomic tasks
**Estimated effort:** 3-4 hours

---

## CONTEXT

Current external ID format (Wave 16A02):
```
ops.flow:000001        → opaque, must query to find out what this is
core.dec:0007          → same problem
```

**New format:**
```
{slug}.{group}.{8digits}                    ← all node types
{slug}.{group}.{testkind}.{8digits}         ← TestCase only

Examples:
  verify_gate.ops.00000002
  registration_flow.ops.00000001
  trustgate_engine.ops.00000001
  traveller_identity.domain.00000001
  use_otp_for_auth.core.00000001
  wave_16a03.meta.00000001
  
  TestCase (with kind):
  auth_otp_valid.test.unit.00000001
  verify_gate_flow.test.e2e.00000002
  trustgate_response.test.performance.00000001
```

**Why name-first:**
```
AI sees: verify_gate.ops.00000002  → instantly knows: Verify Gate, ops group
vs old:  ops.flow:000001           → must query to find out
```

**Why 8 digits:**
```
99,999,999 records per group — enough for MIHOS at scale
TestCase: MIHOS will have millions of tests
```

**Why testkind in TestCase ID:**
```
Enables group queries:
  find: test.unit           → all unit tests
  find: test.e2e            → all e2e tests
  find: auth.test.unit      → unit tests about auth
  find: verify_gate.test    → all tests for verify gate
```

---

## DESIGN

### ID format rules

```
Standard nodes:
  {slug}.{group}.{8digits}
  
  verify_gate.ops.00000002
  trustgate_engine.ops.00000001
  traveller_identity.domain.00000001
  use_otp_for_auth.core.00000001
  wave_16a03.meta.00000001
  
TestCase only:
  {slug}.{group}.{testkind}.{8digits}
  
  auth_otp_valid.test.unit.00000001
  verify_gate_e2e.test.e2e.00000001
  trustgate_perf.test.performance.00000001

Session (special, unchanged):
  meta.session.2026-04-16.a3f7c2abc
  → Changed from meta.session:YYYY-MM-DD_XXXXXXXXX to dot-separated

Document (special):
  {slug}.meta.{md5_6chars}
  doc_07_core_user_flows.meta.8f9a1b
```

### Valid groups
```
core    → Decision, Invariant, Concept
domain  → Entity (+ future: Traveller, Place, Moment)
ops     → Flow, Engine, Feature, Screen, APIEndpoint
test    → TestKind, TestCase
meta    → Session, Wave, Document, Lesson, Node, Repository, Idea
```

### Valid TestKind values
```
unit, integration, e2e, smoke, performance,
security, acceptance, regression, compatibility,
contract, exploratory, accessibility
```

### Slug rules
```python
def make_id_slug(name: str) -> str:
    """Convert name to URL-safe slug for ID.
    
    - Strip prefixes: "F1:", "F2:", "DOC-07:", "WAVE 0 —"
    - Lowercase + replace non-alphanumeric with underscore
    - Max 40 chars
    - Empty name → empty slug (fallback to type_prefix)
    
    Examples:
    "F2: Verify Gate"          → "verify_gate"
    "F1: Registration Flow"    → "registration_flow"
    "TrustGate Engine"         → "trustgate_engine"
    "Traveller Identity"       → "traveller_identity"
    "Use OTP for Auth"         → "use_otp_for_auth"
    "WAVE 16A03 — New IDs"     → "new_ids"
    "DOC-07 Core User Flows"   → "core_user_flows"
    "auth_otp_valid"           → "auth_otp_valid"
    ""                         → ""
    """
```

### generate_external_id() signature
```python
def generate_external_id(
    node_type: str,
    name: str = "",
    testkind: str = "",     # Only for TestCase
    gobp_root: Path | None = None,
    groups: dict | None = None,
) -> str:
```

### parse_external_id() returns
```python
def parse_external_id(external_id: str) -> dict[str, str]:
    """Parse any ID format.
    
    Returns:
        {
          "slug": str,
          "group": str,
          "testkind": str,  # only for TestCase IDs
          "number": str,
          "format": "new" | "legacy"
        }
    
    Examples:
      "verify_gate.ops.00000002"
      → {"slug": "verify_gate", "group": "ops", "testkind": "", "number": "00000002", "format": "new"}
      
      "auth_otp_valid.test.unit.00000001"
      → {"slug": "auth_otp_valid", "group": "test", "testkind": "unit", "number": "00000001", "format": "new"}
      
      "flow:verify_gate"  (legacy)
      → {"slug": "verify_gate", "group": "", "testkind": "", "number": "", "format": "legacy"}
    """
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 397 existing tests must pass after every task.

**CRITICAL:**
- Task 6 re-migrates ALL existing nodes to new format
- Run dry-run first, verify output
- Backup must be done before starting

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 397 tests passing

# Backup
Copy-Item -Recurse D:\GoBP\.gobp D:\GoBP\.gobp_backup_pre_16a03 -Force
Copy-Item -Recurse D:\MIHOS-v1\.gobp D:\MIHOS-v1\.gobp_backup_pre_16a03 -Force
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/core/id_config.py` | Full rewrite of generate/parse |
| 3 | `gobp/core/migrate_ids.py` | Update for new format |
| 4 | `gobp/mcp/dispatcher.py` | Pass name + testkind to ID gen |
| 5 | `gobp/mcp/tools/write.py` | Pass name to ID gen |
| 6 | `gobp/mcp/tools/read.py` | Update FTS for new format |
| 7 | `waves/wave_16a03_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Rewrite id_config.py with new format

**Goal:** New format `slug.group.number` with TestCase variant.

**File to modify:** `gobp/core/id_config.py`

**Re-read in full before editing.**

**Replace `make_id_slug()`:**

```python
def make_id_slug(name: str) -> str:
    """Convert node name to slug for external ID.

    Rules:
    - Strip flow prefixes: "F1:", "F2:", "F10:" etc.
    - Strip doc prefixes: "DOC-07", "DOC-07:"
    - Strip wave prefixes: "WAVE 0", "Wave 16A03 —"
    - Lowercase + replace non-alphanumeric with underscore
    - Max 40 chars, no trailing underscores

    Examples:
        "F2: Verify Gate"        → "verify_gate"
        "Registration Flow"      → "registration_flow"
        "TrustGate Engine"       → "trustgate_engine"
        "Traveller Identity"     → "traveller_identity"
        "WAVE 16A03 — New IDs"   → "new_ids"
        "DOC-07 Core User Flows" → "core_user_flows"
        ""                       → ""
    """
    import re as _re
    if not name:
        return ""
    # Strip flow prefixes: "F1:", "F2:", "F10:" etc.
    name = _re.sub(r'^F\d+:\s*', '', name)
    # Strip doc prefixes: "DOC-07", "DOC-07 ", "DOC-07:"
    name = _re.sub(r'^DOC-\d+[:\s]*', '', name)
    # Strip wave prefixes: "WAVE 16A03 —", "Wave 0 —"
    name = _re.sub(r'^WAVE?\s*[\w]+\s*[—\-]+\s*', '', name, flags=_re.IGNORECASE)
    # Lowercase + replace non-alphanumeric
    slug = _re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
    # Max 40 chars
    return slug[:40].rstrip('_')
```

**Replace `generate_external_id()`:**

```python
# Valid TestKind values
VALID_TESTKINDS: frozenset[str] = frozenset({
    "unit", "integration", "e2e", "smoke", "performance",
    "security", "acceptance", "regression", "compatibility",
    "contract", "exploratory", "accessibility",
})


def generate_external_id(
    node_type: str,
    name: str = "",
    testkind: str = "",
    gobp_root: Path | None = None,
    groups: dict | None = None,
) -> str:
    """Generate external ID in new format: {slug}.{group}.{8digits}

    Special formats:
      Session:  meta.session.YYYY-MM-DD.XXXXXXXXX
      Document: {slug}.meta.{md5_6chars}
      TestCase: {slug}.test.{testkind}.{8digits}

    Args:
        node_type: NodeType string
        name: Human-readable name → becomes slug
        testkind: Required for TestCase (unit/e2e/integration etc.)
        gobp_root: Project root for loading group config
        groups: Pre-loaded groups dict
    """
    from gobp.core.snowflake import generate_snowflake

    if groups is None and gobp_root is not None:
        groups = load_groups(gobp_root)
    if groups is None:
        groups = DEFAULT_GROUPS

    slug = make_id_slug(name) if name else get_type_prefix(node_type)

    # Session: special format
    if node_type == "Session":
        from datetime import datetime, timezone
        import uuid as _uuid
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        short_hash = _uuid.uuid4().hex[:9]
        return f"meta.session.{date_str}.{short_hash}"

    # Document: slug + md5 hash of path (handled by caller for path-based docs)
    # For non-path documents, use standard format

    group = get_group_for_type(node_type, groups)

    # Generate 8-digit number from Snowflake
    sf = generate_snowflake()
    number = f"{sf % 100_000_000:08d}"

    # TestCase: include testkind
    if node_type == "TestCase":
        kind = testkind.lower() if testkind in VALID_TESTKINDS else "unit"
        return f"{slug}.test.{kind}.{number}"

    return f"{slug}.{group}.{number}"
```

**Replace `parse_external_id()`:**

```python
def parse_external_id(external_id: str) -> dict[str, str]:
    """Parse any ID format into components.

    New format:  slug.group.number
                 slug.test.testkind.number  (TestCase)
                 meta.session.YYYY-MM-DD.hash (Session)
    Legacy:      type:name  (old format)

    Returns:
        {slug, group, testkind, number, format}
    """
    result = {"slug": "", "group": "", "testkind": "", "number": "", "format": "legacy"}

    # Legacy format: contains ":" but not new dot format
    if ":" in external_id and "." not in external_id.split(":")[0]:
        parts = external_id.split(":", 1)
        result["slug"] = parts[1] if len(parts) > 1 else ""
        result["group"] = parts[0]
        return result

    # New format: dot-separated
    parts = external_id.split(".")
    result["format"] = "new"

    if len(parts) == 3:
        # slug.group.number
        result["slug"] = parts[0]
        result["group"] = parts[1]
        result["number"] = parts[2]

    elif len(parts) == 4:
        # Could be: slug.test.testkind.number OR meta.session.YYYY-MM-DD.hash
        if parts[1] == "test" and parts[2] in VALID_TESTKINDS:
            # TestCase: slug.test.kind.number
            result["slug"] = parts[0]
            result["group"] = "test"
            result["testkind"] = parts[2]
            result["number"] = parts[3]
        elif parts[0] == "meta" and parts[1] == "session":
            # Session: meta.session.YYYY-MM-DD.hash
            result["slug"] = "session"
            result["group"] = "meta"
            result["number"] = parts[3]
        else:
            # Fallback
            result["slug"] = parts[0]
            result["group"] = parts[1]
            result["number"] = parts[-1]

    elif len(parts) >= 2:
        result["slug"] = parts[0]
        result["group"] = parts[1]

    return result
```

**Acceptance criteria:**
- `make_id_slug("F2: Verify Gate")` → `"verify_gate"`
- `generate_external_id("Flow", "Verify Gate")` → `"verify_gate.ops.XXXXXXXX"`
- `generate_external_id("TestCase", "Auth OTP Valid", "unit")` → `"auth_otp_valid.test.unit.XXXXXXXX"`
- `generate_external_id("Session")` → `"meta.session.YYYY-MM-DD.XXXXXXXXX"`
- `parse_external_id("verify_gate.ops.00000002")` → `{slug:"verify_gate", group:"ops", number:"00000002"}`
- `parse_external_id("auth_otp_valid.test.unit.00000001")` → `{testkind:"unit"}`

**Commit message:**
```
Wave 16A03 Task 1: rewrite id_config.py — new slug.group.number format

- make_id_slug(): max 40 chars, strips F1:/DOC-07:/WAVE prefixes
- generate_external_id(): name.group.8digits format
- TestCase: name.test.testkind.8digits
- Session: meta.session.YYYY-MM-DD.hash
- VALID_TESTKINDS: frozenset of 12 test types
- parse_external_id(): returns dict {slug, group, testkind, number, format}
```

---

## TASK 2 — Update dispatcher.py to pass name + testkind

**Goal:** `create:TestCase` passes testkind to ID generation.

**File to modify:** `gobp/mcp/dispatcher.py`

**Re-read create/upsert handlers in full.**

Update create: handler to pass name AND testkind:

```python
        elif action in ("create", "update", "upsert"):
            node_type_arg = _normalize_type(node_type or params.pop("type", "Node"))
            name = params.get("name", "")
            testkind = params.get("kind_id", params.get("testkind", ""))

            if action == "create":
                from gobp.core.id_config import generate_external_id as _gen_id
                node_id = params.get("node_id") or _gen_id(
                    node_type_arg,
                    name=name,
                    testkind=testkind,
                    gobp_root=project_root,
                )
```

**Update upsert: handler similarly.**

**Acceptance criteria:**
- `create:Flow name='Verify Gate'` → ID contains `verify_gate.ops.`
- `create:TestCase name='Auth OTP Valid' kind_id='unit'` → ID contains `.test.unit.`
- `create:Node` (no name) → ID uses type prefix as slug

**Commit message:**
```
Wave 16A03 Task 2: dispatcher passes name + testkind to ID generation

- create: passes name + kind_id/testkind params
- upsert: passes name + kind_id/testkind params
- TestCase IDs include testkind: auth_otp_valid.test.unit.00000001
```

---

## TASK 3 — Update write.py to pass name to ID generation

**File to modify:** `gobp/mcp/tools/write.py`

**Re-read `node_upsert()` and `node_upsert_smart()` in full.**

Where node_id is auto-generated, pass name and testkind:

```python
    if not node_id:
        from gobp.core.id_config import generate_external_id as _gen_id
        testkind = fields.get("kind_id", "")
        node_id = _gen_id(
            node_type,
            name=name,
            testkind=testkind,
            gobp_root=project_root,
        )
```

**Commit message:**
```
Wave 16A03 Task 3: write.py passes name + testkind to ID generation

- node_upsert(): new nodes get slug.group.number IDs
- node_upsert_smart(): same
- TestCase: extracts kind_id from fields for testkind
```

---

## TASK 4 — Update find() FTS for new ID format

**Goal:** `find: verify_gate` matches `verify_gate.ops.00000002`.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read find() and FTS content building in full.**

Add slug extraction to FTS content:

```python
from gobp.core.id_config import parse_external_id as _parse_id

def _extract_fts_slug(node_id: str) -> str:
    """Extract slug from external ID for FTS indexing."""
    parsed = _parse_id(node_id)
    return parsed.get("slug", "")

# In _build_fts_content() or wherever FTS content is assembled:
fts_parts = [
    node.get("id", ""),
    node.get("name", ""),
    node.get("legacy_id", ""),
    _extract_fts_slug(node.get("id", "")),  # slug from new ID
    node.get("description", ""),
    ...
]
```

Also update `_node_summary()` to show group badge:

```python
def _node_summary(node, index=None):
    node_id = node.get("id", "")
    parsed = parse_external_id(node_id)
    
    return {
        "id": node_id,
        "type": node.get("type", ""),
        "name": node.get("name", ""),
        "group": parsed.get("group", ""),       # NEW
        "testkind": parsed.get("testkind", ""), # NEW (for TestCase)
        "status": node.get("status", ""),
        "priority": node.get("priority", "medium"),
        "edge_count": ...,
        "detail_available": True,
    }
```

**Commit message:**
```
Wave 16A03 Task 4: find() FTS indexes slug from new ID format

- _extract_fts_slug(): extracts slug part from new dot-format ID
- FTS content includes extracted slug for searchability
- _node_summary(): includes group + testkind fields
- find: verify_gate matches verify_gate.ops.00000002
```

---

## TASK 5 — Update migrate_ids.py for new format

**File to modify:** `gobp/core/migrate_ids.py`

**Re-read in full.**

Update `_needs_migration()`:

```python
def _needs_migration(node_id: str, node_name: str = "", node_type: str = "") -> bool:
    """Check if ID needs migration to new format.

    Needs migration if:
    - Old colon format: flow:verify_gate, dec:d001
    - Wave 16A02 dot-colon format: ops.flow:000001
    - New dot format without slug when name available
    """
    from gobp.core.id_config import parse_external_id

    # Old colon format
    if ":" in node_id:
        return True

    # Already new dot format — check if has slug
    parsed = parse_external_id(node_id)
    if parsed["format"] == "new":
        # Has proper slug already
        if parsed["slug"] and parsed["slug"] != get_type_prefix(node_type or "Node"):
            return False
        # No meaningful slug but name available
        if node_name:
            from gobp.core.id_config import make_id_slug
            expected_slug = make_id_slug(node_name)
            if expected_slug and expected_slug != parsed["slug"]:
                return True

    return False
```

Update migration to pass name + testkind:

```python
            node_name = node.get("name", "")
            node_type_val = node.get("type", "Node")
            testkind = node.get("kind_id", "")

            new_id = generate_external_id(
                node_type_val,
                name=node_name,
                testkind=testkind,
                gobp_root=gobp_root,
                groups=groups,
            )
```

**Commit message:**
```
Wave 16A03 Task 5: migrate_ids.py for new slug.group.number format

- _needs_migration(): detects old colon format AND 16A02 dot-colon format
- Migration passes name + testkind to generate_external_id()
- TestCase nodes get testkind in ID: auth_otp_valid.test.unit.00000001
```

---

## TASK 6 — Run re-migration + verify

```powershell
# Dry run first — verify slugs look correct
D:/GoBP/venv/Scripts/python.exe -m gobp.core.migrate_ids --root D:/GoBP --dry-run

# Check output — should see new format:
#   verify_gate.ops.00000002
#   trustgate_engine.ops.00000001
#   auth_otp_valid.test.unit.00000001

# Run actual migration
D:/GoBP/venv/Scripts/python.exe -m gobp.core.migrate_ids --root D:/GoBP

# Migrate MIHOS
D:/GoBP/venv/Scripts/python.exe -m gobp.core.migrate_ids --root D:/MIHOS-v1 --dry-run
D:/GoBP/venv/Scripts/python.exe -m gobp.core.migrate_ids --root D:/MIHOS-v1

# Verify sample nodes
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.graph import GraphIndex
from pathlib import Path

root = Path('D:/GoBP')
index = GraphIndex.load_from_disk(root)
nodes = index.all_nodes()

print(f'Total nodes: {len(nodes)}')
print()
print('Sample IDs (new format):')
for n in sorted(nodes, key=lambda x: x.get('type',''))[:15]:
    print(f'  {n[\"id\"]:50s} ({n[\"type\"]})')
"
```

**Commit message:**
```
Wave 16A03 Task 6: re-migrate all nodes to slug.group.number format

- GoBP project: all nodes migrated
- MIHOS project: all nodes migrated
- verify_gate.ops.00000002, trustgate_engine.ops.00000001
- auth_otp_valid.test.unit.00000001 (TestCase with kind)
- id_mapping.json updated
```

---

## TASK 7 — Smoke test

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.id_config import make_id_slug, generate_external_id, parse_external_id, VALID_TESTKINDS

print('=== Slug tests ===')
cases = [
    ('F2: Verify Gate',        'verify_gate'),
    ('Registration Flow',      'registration_flow'),
    ('TrustGate Engine',       'trustgate_engine'),
    ('Traveller Identity',     'traveller_identity'),
    ('Use OTP for Auth',       'use_otp_for_auth'),
    ('WAVE 16A03 — New IDs',   'new_ids'),
    ('DOC-07 Core User Flows', 'core_user_flows'),
    ('',                       ''),
]
for name, expected in cases:
    result = make_id_slug(name)
    assert result == expected, f'{name!r} → {result!r} != {expected!r}'
    print(f'  OK: {name!r} → {result!r}')

print()
print('=== ID generation tests ===')
eid = generate_external_id('Flow', 'Verify Gate')
assert 'verify_gate' in eid and '.ops.' in eid
print(f'  Flow:     {eid}')

eid2 = generate_external_id('TestCase', 'Auth OTP Valid', 'unit')
assert 'auth_otp_valid' in eid2 and '.test.unit.' in eid2
print(f'  TestCase: {eid2}')

eid3 = generate_external_id('Session')
assert 'meta.session.' in eid3
print(f'  Session:  {eid3}')

print()
print('=== Parse tests ===')
p = parse_external_id('verify_gate.ops.00000002')
assert p['slug'] == 'verify_gate' and p['group'] == 'ops' and p['number'] == '00000002'
print(f'  Standard: {p}')

p2 = parse_external_id('auth_otp_valid.test.unit.00000001')
assert p2['slug'] == 'auth_otp_valid' and p2['testkind'] == 'unit'
print(f'  TestCase: {p2}')

print()
print('All smoke tests passed')
"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 397 tests passing
```

**Commit message:**
```
Wave 16A03 Task 7: smoke test — new ID format verified

- make_id_slug() handles all MIHOS naming conventions
- generate_external_id() produces slug.group.number
- TestCase gets slug.test.testkind.number
- parse_external_id() returns correct components
- 397 existing tests passing
```

---

## TASK 8 — Tests + CHANGELOG

**File to create:** `tests/test_wave16a03.py`

```python
"""Tests for Wave 16A03: new slug.group.number ID format."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.id_config import (
    make_id_slug, generate_external_id, parse_external_id,
    VALID_TESTKINDS,
)
from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch


# ── make_id_slug tests ────────────────────────────────────────────────────────

def test_slug_flow_prefix_f2():
    assert make_id_slug("F2: Verify Gate") == "verify_gate"

def test_slug_flow_prefix_f10():
    assert make_id_slug("F10: Homecoming") == "homecoming"

def test_slug_plain_name():
    assert make_id_slug("TrustGate Engine") == "trustgate_engine"

def test_slug_traveller():
    assert make_id_slug("Traveller Identity") == "traveller_identity"

def test_slug_doc_prefix():
    result = make_id_slug("DOC-07 Core User Flows")
    assert "core_user_flows" in result

def test_slug_wave_prefix():
    result = make_id_slug("WAVE 16A03 — New IDs")
    assert "new_ids" in result

def test_slug_empty():
    assert make_id_slug("") == ""

def test_slug_max_40_chars():
    result = make_id_slug("This Is A Very Long Name That Exceeds Forty Characters Easily Here")
    assert len(result) <= 40

def test_slug_special_chars():
    result = make_id_slug("Use OTP (Email) for Auth!")
    assert result == "use_otp_email_for_auth"


# ── generate_external_id tests ────────────────────────────────────────────────

def test_flow_id_format():
    eid = generate_external_id("Flow", "Verify Gate")
    assert eid.startswith("verify_gate.ops.")
    parts = eid.split(".")
    assert len(parts) == 3
    assert len(parts[2]) == 8  # 8-digit number

def test_decision_id_format():
    eid = generate_external_id("Decision", "Use OTP for Auth")
    assert eid.startswith("use_otp_for_auth.core.")

def test_entity_id_format():
    eid = generate_external_id("Entity", "Traveller Identity")
    assert eid.startswith("traveller_identity.domain.")

def test_testcase_id_with_kind():
    eid = generate_external_id("TestCase", "Auth OTP Valid", "unit")
    assert "auth_otp_valid.test.unit." in eid
    parts = eid.split(".")
    assert len(parts) == 4
    assert parts[2] == "unit"
    assert len(parts[3]) == 8

def test_testcase_invalid_kind_defaults_to_unit():
    eid = generate_external_id("TestCase", "My Test", "invalid_kind")
    assert ".test.unit." in eid

def test_session_id_format():
    eid = generate_external_id("Session")
    assert eid.startswith("meta.session.")
    parts = eid.split(".")
    assert len(parts) == 4  # meta.session.YYYY-MM-DD.hash

def test_id_without_name_uses_prefix():
    eid = generate_external_id("Flow")
    # Without name, uses type prefix as slug
    assert ".ops." in eid

def test_valid_testkinds_complete():
    assert "unit" in VALID_TESTKINDS
    assert "e2e" in VALID_TESTKINDS
    assert "performance" in VALID_TESTKINDS
    assert "security" in VALID_TESTKINDS
    assert len(VALID_TESTKINDS) >= 10


# ── parse_external_id tests ───────────────────────────────────────────────────

def test_parse_standard_new_format():
    p = parse_external_id("verify_gate.ops.00000002")
    assert p["slug"] == "verify_gate"
    assert p["group"] == "ops"
    assert p["number"] == "00000002"
    assert p["testkind"] == ""
    assert p["format"] == "new"

def test_parse_testcase_format():
    p = parse_external_id("auth_otp_valid.test.unit.00000001")
    assert p["slug"] == "auth_otp_valid"
    assert p["group"] == "test"
    assert p["testkind"] == "unit"
    assert p["number"] == "00000001"

def test_parse_session_format():
    p = parse_external_id("meta.session.2026-04-16.a3f7c2abc")
    assert p["group"] == "meta"

def test_parse_legacy_colon_format():
    p = parse_external_id("flow:verify_gate")
    assert p["format"] == "legacy"
    assert p["slug"] == "verify_gate"


# ── Dispatcher integration tests ──────────────────────────────────────────────

def test_create_flow_gets_slug_id(gobp_root: Path):
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='slug test'", index, gobp_root
    ))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch(
        f"create:Flow name='Verify Gate' priority='critical' session_id='{sid}'",
        index, gobp_root
    ))
    assert r["ok"] is True
    node_id = r.get("node_id", "")
    assert "verify_gate" in node_id
    assert ".ops." in node_id


def test_create_testcase_gets_kind_in_id(gobp_root: Path):
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='testcase slug'", index, gobp_root
    ))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch(
        f"create:TestCase name='Auth OTP Valid' kind_id='unit' session_id='{sid}'",
        index, gobp_root
    ))
    assert r["ok"] is True
    node_id = r.get("node_id", "")
    assert ".test.unit." in node_id


def test_find_by_slug_in_id(gobp_root: Path):
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='find slug'", index, gobp_root
    ))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    asyncio.run(dispatch(
        f"create:Flow name='Verify Gate' session_id='{sid}'",
        index, gobp_root
    ))
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch("find: verify_gate", index, gobp_root))
    assert r["ok"] is True
    ids = [m["id"] for m in r["matches"]]
    assert any("verify_gate" in nid for nid in ids)
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave16a03.py -v
# Expected: ~25 tests

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 422+ tests
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A03] — New ID Format: slug.group.number — 2026-04-16

### Why
External IDs like ops.flow:000001 are opaque.
AI and humans can't tell what a node is from its ID alone.

### New format
```
Standard:  {slug}.{group}.{8digits}
TestCase:  {slug}.test.{testkind}.{8digits}
Session:   meta.session.{date}.{hash}

Examples:
  verify_gate.ops.00000002
  registration_flow.ops.00000001
  trustgate_engine.ops.00000001
  traveller_identity.domain.00000001
  use_otp_for_auth.core.00000001
  auth_otp_valid.test.unit.00000001
  verify_gate_e2e.test.e2e.00000001
```

### TestCase kinds
unit, integration, e2e, smoke, performance, security,
acceptance, regression, compatibility, contract, exploratory, accessibility

### Query benefits
```
find: verify_gate          → verify_gate.ops.00000002
find: test.unit            → all unit tests
find: auth.test.unit       → unit tests about auth
find: verify_gate.test     → all tests for verify gate
```

### Changed
- id_config.py: make_id_slug(), generate_external_id(), parse_external_id()
- dispatcher.py: passes name + testkind to ID generation
- write.py: passes name + testkind to ID generation
- read.py: FTS indexes slug from new ID format
- migrate_ids.py: re-migration with name slugs
- All existing nodes re-migrated

### Total: 422+ tests
```

**Commit message:**
```
Wave 16A03 Task 8: tests/test_wave16a03.py + full suite + CHANGELOG

- ~25 tests: slug, generate, parse, dispatcher integration
- 422+ tests passing
- CHANGELOG: Wave 16A03 entry
```

---

# POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.graph import GraphIndex
from pathlib import Path

root = Path('D:/GoBP')
index = GraphIndex.load_from_disk(root)
nodes = sorted(index.all_nodes(), key=lambda n: n.get('type',''))

print(f'Total: {len(nodes)} nodes')
print()
for n in nodes[:20]:
    print(f'  {n[\"id\"]:55s} ({n[\"type\"]})')
"

git log --oneline | Select-Object -First 10
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. STOP CURSOR TASK 1 IMMEDIATELY

Cursor đang chạy Task 1 theo Brief cũ. Paste ngay vào Cursor:

```
STOP. Brief đã được viết lại hoàn toàn.
Read waves/wave_16a03_brief.md again from the beginning.
The ID format has changed to: {slug}.{group}.{8digits}
NOT the old format.
Restart from Task 1 with the new brief.
```

## 2. Backup

```powershell
Copy-Item -Recurse D:\GoBP\.gobp D:\GoBP\.gobp_backup_pre_16a03 -Force
Copy-Item -Recurse D:\MIHOS-v1\.gobp D:\MIHOS-v1\.gobp_backup_pre_16a03 -Force
```

## 3. Copy Brief vào repo

```powershell
cd D:\GoBP
# Save wave_16a03_brief.md to D:\GoBP\waves\wave_16a03_brief.md
git add waves/wave_16a03_brief.md
git commit -m "Add Wave 16A03 Brief — new ID format slug.group.number"
git push origin main
```

## 4. Dispatch Cursor

```
STOP current work. Read waves/wave_16a03_brief.md from the beginning.
ID format changed to: {slug}.{group}.{8digits}
Also read gobp/core/id_config.py, gobp/core/migrate_ids.py,
gobp/mcp/dispatcher.py, gobp/mcp/tools/write.py, gobp/mcp/tools/read.py.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 8 tasks sequentially.
R9: all 397 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 5. Audit Claude CLI

```
Audit Wave 16A03. Read CLAUDE.md and waves/wave_16a03_brief.md.
Set env: $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: make_id_slug(), generate_external_id(name, testkind), parse_external_id() returns dict
          Format: verify_gate.ops.00000002, auth_otp_valid.test.unit.00000001
- Task 2: dispatcher passes name + kind_id to ID generation
- Task 3: write.py passes name + testkind
- Task 4: find() FTS includes extracted slug
- Task 5: migrate_ids.py handles new format + testkind
- Task 6: migration ran, nodes have new format with slugs
- Task 7: smoke test passed, 397 tests
- Task 8: test_wave16a03.py ~25 tests, 422+ total, CHANGELOG

Expected: 422+ tests. Report WAVE 16A03 AUDIT COMPLETE.
```

---

*Wave 16A03 Brief v2.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-16*
*v2.0: Changed format from group.prefix:seq_slug to slug.group.8digits*

◈
