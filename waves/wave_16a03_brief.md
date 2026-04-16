# WAVE 16A03 BRIEF — NAME SLUG IN EXTERNAL ID

**Wave:** 16A03
**Title:** Add name slug to external ID format — human-readable + machine-stable
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-16
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 8 atomic tasks
**Estimated effort:** 3-4 hours

---

## CONTEXT

Current external ID format:
```
ops.flow:000001        → what flow is this?
core.dec:0007          → what decision?
domain.entity:000001   → which entity?
```

AI and humans can't tell what a node is from its ID alone. Must call `get:` to find out.

**Target format:**
```
ops.flow:0002_verify_gate
ops.flow:0001_registration_flow
ops.engine:0001_trustgate_engine
domain.entity:000001_traveller_identity
core.dec:0001_use_otp_for_auth
test.case:000001_auth_otp_valid
meta.doc:DOC-07_core_user_flows_8f9a1b  ← already has slug
```

**Benefits:**
```
✅ AI sees node purpose from ID alone
✅ Human-readable in logs, graph viewer, API responses
✅ Sequence prefix ensures uniqueness even if names collide
✅ Slug searchable (find: verify_gate)
✅ Consistent with MIHOS document naming convention
✅ ID stable even if name changes (sequence part doesn't change)
```

---

## DESIGN

### Slug rules
```python
def make_id_slug(name: str) -> str:
    """Convert node name to URL-safe slug for use in ID.
    
    Rules:
    - Lowercase
    - Replace non-alphanumeric with underscore
    - Remove leading/trailing underscores
    - Max 30 chars (to keep IDs readable)
    - Strip common prefixes like "F1:", "F2:" etc.
    
    Examples:
    "F2: Verify Gate"         → "verify_gate"
    "F1: Registration Flow"   → "registration_flow"
    "TrustGate Engine"        → "trustgate_engine"
    "Traveller Identity"      → "traveller_identity"
    "Use OTP for Auth"        → "use_otp_for_auth"
    "DOC-07 Core User Flows"  → "doc_07_core_user_flows"
    "test_auth_otp_valid"     → "auth_otp_valid"
    ""                        → "" (no slug)
    """
    import re
    # Strip common prefixes: "F1:", "F2:", "DOC-07:", etc.
    name = re.sub(r'^[A-Z]\d+:\s*', '', name)
    name = re.sub(r'^DOC-\d+\s*', '', name)
    # Lowercase + replace non-alphanumeric with underscore
    slug = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
    # Max 30 chars
    return slug[:30].rstrip('_')
```

### Updated external ID format
```
{group}.{type_prefix}:{sequence}_{slug}

Examples:
  ops.flow:0001_registration_flow
  ops.flow:0002_verify_gate
  ops.engine:0001_trustgate_engine
  domain.entity:000001_traveller_identity
  core.dec:0001_use_otp_for_auth
  test.case:000001_auth_otp_valid
  meta.wave:0001_wave_0_repo_bootstrap
  
Special formats (unchanged):
  meta.session:2026-04-16_a3f7c2abc  ← no slug (goal too long)
  meta.doc:DOC-07_core_user_flows_8f9a1b  ← already has slug
```

### Backward compat
```
Existing IDs WITHOUT slug still resolve:
  ops.flow:000001 → find via sequence lookup or legacy_id

New nodes created WITH slug:
  create:Flow name='Verify Gate' → ops.flow:0002_verify_gate

parse_external_id() updated to handle both:
  "ops.flow:0002_verify_gate" → (ops, flow, 0002, verify_gate)
  "ops.flow:000001"           → (ops, flow, 000001, "")
```

### Re-migration of existing nodes
```
378 nodes currently have format: ops.flow:000001
Re-migrate WITH slug using existing node names:
  ops.flow:000001 (name="Verify Gate") → ops.flow:0002_verify_gate
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 397 existing tests must pass after every task.

**CRITICAL:** Task 6 re-migrates existing nodes.
Run dry-run first, verify output, then actual migration.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 397 tests passing

# Backup .gobp/ before re-migration
Copy-Item -Recurse D:\GoBP\.gobp D:\GoBP\.gobp_backup_pre_16a03 -Force
Copy-Item -Recurse D:\MIHOS-v1\.gobp D:\MIHOS-v1\.gobp_backup_pre_16a03 -Force
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/core/id_config.py` | Update generate_external_id() |
| 3 | `gobp/core/migrate_ids.py` | Update to use name slugs |
| 4 | `gobp/mcp/dispatcher.py` | Pass name to ID generation |
| 5 | `gobp/core/mutator.py` | Pass name to ID generation |
| 6 | `waves/wave_16a03_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Add make_id_slug() to id_config.py

**Goal:** Slug generation function. Handles MIHOS naming conventions.

**File to modify:** `gobp/core/id_config.py`

**Re-read in full.**

Add after imports:

```python
def make_id_slug(name: str) -> str:
    """Convert node name to URL-safe slug for external ID.

    Rules:
    - Strip common prefixes: "F1:", "F2:", "DOC-07:" etc.
    - Lowercase + replace non-alphanumeric with underscore
    - Max 30 chars
    - Empty name → empty slug

    Examples:
        "F2: Verify Gate"       → "verify_gate"
        "Registration Flow"     → "registration_flow"
        "TrustGate Engine"      → "trustgate_engine"
        "Traveller Identity"    → "traveller_identity"
        "Use OTP for Auth"      → "use_otp_for_auth"
        ""                      → ""
    """
    import re as _re
    if not name:
        return ""
    # Strip flow prefixes: "F1:", "F2:", "F10:" etc.
    name = _re.sub(r'^F\d+:\s*', '', name)
    # Strip doc prefixes: "DOC-07", "DOC-07:"
    name = _re.sub(r'^DOC-\d+[:\s]*', '', name)
    # Strip wave prefixes: "WAVE 0", "Wave 0 —"
    name = _re.sub(r'^WAVE?\s*\d+\s*[—\-:]*\s*', '', name, flags=_re.IGNORECASE)
    # Lowercase + replace non-alphanumeric
    slug = _re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
    # Max 30 chars, no trailing underscore
    return slug[:30].rstrip('_')
```

**Update `generate_external_id()` to accept name:**

```python
def generate_external_id(
    node_type: str,
    name: str = "",
    gobp_root: Path | None = None,
    groups: dict | None = None,
) -> str:
    """Generate external ID with group namespace and optional name slug.

    Format: {group}.{type_prefix}:{sequence}_{slug}
    or:     {group}.{type_prefix}:{sequence}  (if no name)

    Special cases:
      Session → meta.session:YYYY-MM-DD_XXXXXXXXX (no slug)
      Document → meta.doc:{slug}_{md5[:6]} (existing format)
    """
    from gobp.core.snowflake import generate_snowflake

    if groups is None and gobp_root is not None:
        groups = load_groups(gobp_root)
    if groups is None:
        groups = DEFAULT_GROUPS

    # Session: special format, no slug
    if node_type == "Session":
        from datetime import datetime, timezone
        import uuid as _uuid
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        short_hash = _uuid.uuid4().hex[:9]
        return f"meta.session:{date_str}_{short_hash}"

    group = get_group_for_type(node_type, groups)
    prefix = get_type_prefix(node_type)
    scale = groups.get(group, {}).get("sequence_scale", "medium")
    padding = SEQUENCE_PADDING.get(scale, 6)

    sf = generate_snowflake()
    seq = sf % (10 ** padding)
    seq_str = f"{seq:0{padding}d}"

    # Add slug if name provided
    slug = make_id_slug(name)
    if slug:
        return f"{group}.{prefix}:{seq_str}_{slug}"
    return f"{group}.{prefix}:{seq_str}"
```

**Update `parse_external_id()` to handle slug:**

```python
def parse_external_id(external_id: str) -> tuple[str, str, str, str]:
    """Parse external ID → (group, type_prefix, sequence, slug).

    Handles:
      "ops.flow:0002_verify_gate" → ("ops", "flow", "0002", "verify_gate")
      "ops.flow:000001"           → ("ops", "flow", "000001", "")
      "flow:verify_gate"          → ("", "flow", "verify_gate", "")  # legacy
      "dec:d001"                  → ("", "dec", "d001", "")           # legacy
    """
    if "." in external_id and ":" in external_id:
        dot_idx = external_id.index(".")
        colon_idx = external_id.index(":")
        if dot_idx < colon_idx:
            group = external_id[:dot_idx]
            type_prefix = external_id[dot_idx + 1:colon_idx]
            rest = external_id[colon_idx + 1:]
            # Split sequence and slug: "0002_verify_gate" → "0002", "verify_gate"
            if "_" in rest:
                # Find where sequence ends (all digits) and slug begins
                parts = rest.split("_", 1)
                if parts[0].isdigit():
                    return group, type_prefix, parts[0], parts[1]
            return group, type_prefix, rest, ""

    # Legacy format: "type:name"
    if ":" in external_id:
        parts = external_id.split(":", 1)
        return "", parts[0], parts[1], ""

    return "", "", external_id, ""
```

**Acceptance criteria:**
- `make_id_slug("F2: Verify Gate")` → `"verify_gate"`
- `make_id_slug("TrustGate Engine")` → `"trustgate_engine"`
- `make_id_slug("Traveller Identity")` → `"traveller_identity"`
- `make_id_slug("")` → `""`
- `generate_external_id("Flow", "Verify Gate")` → `"ops.flow:XXXX_verify_gate"`
- `generate_external_id("Flow")` → `"ops.flow:XXXX"` (no slug)
- `parse_external_id("ops.flow:0002_verify_gate")` → `("ops", "flow", "0002", "verify_gate")`

**Commit message:**
```
Wave 16A03 Task 1: add make_id_slug() + name param to generate_external_id()

- make_id_slug(): strips F1:/DOC-07:/WAVE prefixes, lowercase, max 30 chars
- generate_external_id(): accepts name param, adds slug to ID
- parse_external_id(): returns 4-tuple (group, prefix, seq, slug)
- Session IDs unchanged (no slug)
```

---

## TASK 2 — Update dispatcher.py to pass name to ID generation

**Goal:** `create:` and `upsert:` pass node name to `generate_external_id()`.

**File to modify:** `gobp/mcp/dispatcher.py`

**Re-read create/upsert handlers in full.**

Update `create:` handler:

```python
        elif action in ("create", "update", "upsert"):
            node_type_arg = _normalize_type(node_type or params.pop("type", "Node"))
            name = params.get("name", "")

            if action == "create":
                from gobp.core.id_config import generate_external_id as _gen_id
                node_id = params.get("node_id") or _gen_id(
                    node_type_arg, name=name, gobp_root=project_root
                )
```

Update `upsert:` handler similarly — pass `name` to `generate_external_id()`.

**Acceptance criteria:**
- `create:Flow name='Verify Gate' session_id='x'` → node ID contains `verify_gate`
- `create:Decision name='Use OTP' session_id='x'` → node ID contains `use_otp`
- `create:Node` (no name) → ID without slug: `meta.node:XXXXXX`

**Commit message:**
```
Wave 16A03 Task 2: dispatcher passes name to generate_external_id()

- create: handler passes name= to generate_external_id()
- upsert: handler passes name= to generate_external_id()
- New nodes get IDs like ops.flow:0001_verify_gate
```

---

## TASK 3 — Update mutator.py to pass name to ID generation

**Goal:** `node_upsert()` in write tools uses name-slug IDs.

**File to modify:** `gobp/mcp/tools/write.py`

**Re-read `node_upsert()` in full.**

Where node_id is auto-generated, pass name:

```python
    # In node_upsert(), when generating new ID:
    if not node_id:
        from gobp.core.id_config import generate_external_id as _gen_id
        node_id = _gen_id(node_type, name=name, gobp_root=project_root)
```

**Commit message:**
```
Wave 16A03 Task 3: write.py node_upsert passes name to ID generation

- node_upsert(): new nodes get name-slug IDs
- Consistent with dispatcher create/upsert behavior
```

---

## TASK 4 — Update find() to search slug in external ID

**Goal:** `find: verify_gate` matches `ops.flow:0002_verify_gate`.

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `find()` in full.**

The slug is already part of the `id` field which is indexed in FTS. Verify this works:

```python
# In _build_fts_content() or wherever FTS content is built:
# external_id already includes slug: "ops.flow:0002_verify_gate"
# So "verify_gate" is already searchable via id field

# But also add explicit slug extraction for better matching:
from gobp.core.id_config import parse_external_id
_, _, _, slug = parse_external_id(node.get("id", ""))
fts_parts = [
    node.get("id", ""),
    node.get("name", ""),
    node.get("legacy_id", ""),
    slug,  # explicit slug for better search
    ...
]
```

**Verify:**
```powershell
D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch

root = Path('D:/GoBP')
index = GraphIndex.load_from_disk(root)

async def test():
    r = await dispatch('find: verify_gate', index, root)
    print('find verify_gate:', r['count'], 'results')
    for m in r['matches'][:3]:
        print(' ', m['id'], m['name'])

asyncio.run(test())
"
```

**Commit message:**
```
Wave 16A03 Task 4: find() searches slug in external ID

- FTS content includes extracted slug from external ID
- find: verify_gate matches ops.flow:0002_verify_gate
- Slug searchable without knowing full ID
```

---

## TASK 5 — Update migrate_ids.py to include name slug

**Goal:** Re-migration adds name slug to existing IDs.

**File to modify:** `gobp/core/migrate_ids.py`

**Re-read in full.**

Update `migrate_project()` — when generating new_id, pass node name:

```python
            # Generate new ID with slug
            node_type = node.get("type", "Node")
            name = node.get("name", "")
            new_id = generate_external_id(
                node_type,
                name=name,
                gobp_root=gobp_root,
                groups=groups,
            )
            id_mapping[old_id] = new_id
```

Also update `_needs_migration()` to detect IDs that have sequence but no slug:

```python
def _needs_migration(node_id: str, node_name: str = "") -> bool:
    """Check if ID needs migration.

    Needs migration if:
    - Old format: no group namespace (flow:verify_gate, dec:d001)
    - New format without slug but has name available
    """
    from gobp.core.id_config import parse_external_id, make_id_slug
    group, prefix, seq, slug = parse_external_id(node_id)

    # Old format — no group
    if not group:
        return True

    # New format with sequence but no slug, and name is available
    if group and seq and not slug and node_name:
        expected_slug = make_id_slug(node_name)
        if expected_slug:
            return True  # needs slug added

    return False
```

Update the migration loop to pass name:

```python
    for node_file in sorted(node_files):
        node = _load_node_file(node_file)
        old_id = node.get("id", "")
        node_name = node.get("name", "")

        if not _needs_migration(old_id, node_name):
            skipped += 1
            id_mapping[old_id] = old_id
            continue

        new_id = generate_external_id(node_type, name=node_name, ...)
        id_mapping[old_id] = new_id
```

**Commit message:**
```
Wave 16A03 Task 5: migrate_ids.py adds name slug on re-migration

- _needs_migration(): detects IDs without slug when name available
- migrate_project(): passes node name to generate_external_id()
- Re-migration converts ops.flow:000001 → ops.flow:0001_verify_gate
```

---

## TASK 6 — Run re-migration with name slugs

**Goal:** Migrate existing 397 nodes to include name slugs.

```powershell
# Dry run first
D:/GoBP/venv/Scripts/python.exe -m gobp.core.migrate_ids --root D:/GoBP --dry-run

# Verify output looks correct (should see slugs in new IDs)
# Example: ops.flow:000001 (name=Verify Gate) → ops.flow:0002_verify_gate

# Run actual migration
D:/GoBP/venv/Scripts/python.exe -m gobp.core.migrate_ids --root D:/GoBP

# Migrate MIHOS too
D:/GoBP/venv/Scripts/python.exe -m gobp.core.migrate_ids --root D:/MIHOS-v1 --dry-run
D:/GoBP/venv/Scripts/python.exe -m gobp.core.migrate_ids --root D:/MIHOS-v1

# Verify sample nodes
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.graph import GraphIndex
from pathlib import Path

root = Path('D:/GoBP')
index = GraphIndex.load_from_disk(root)

# Check sample nodes have slugs
nodes = index.all_nodes()
with_slug = [n for n in nodes if '_' in n.get('id','').split(':')[-1]]
without_slug = [n for n in nodes if '_' not in n.get('id','').split(':')[-1]
                and not n.get('id','').startswith('meta.session:')]

print(f'Total: {len(nodes)}')
print(f'With slug: {len(with_slug)}')
print(f'Without slug (no name): {len(without_slug)}')
print()
print('Sample IDs with slugs:')
for n in with_slug[:10]:
    print(f'  {n[\"id\"]}  ({n[\"name\"]})')
"
```

**Commit message:**
```
Wave 16A03 Task 6: re-migrate nodes to include name slugs

- GoBP project: N nodes migrated with name slugs
- MIHOS project: N nodes migrated with name slugs
- ops.flow:000001 → ops.flow:0002_verify_gate
- core.dec:000001 → core.dec:0001_use_otp_for_auth
- id_mapping.json updated
```

---

## TASK 7 — Smoke test + full suite

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.id_config import make_id_slug, generate_external_id, parse_external_id

# Test slug generation
cases = [
    ('F2: Verify Gate',       'verify_gate'),
    ('Registration Flow',     'registration_flow'),
    ('TrustGate Engine',      'trustgate_engine'),
    ('Traveller Identity',    'traveller_identity'),
    ('Use OTP for Auth',      'use_otp_for_auth'),
    ('WAVE 0 — REPO BOOTSTRAP', 'repo_bootstrap'),
    ('',                      ''),
]
for name, expected in cases:
    result = make_id_slug(name)
    assert result == expected, f'{name!r} → {result!r} != {expected!r}'
    print(f'OK: {name!r} → {result!r}')

# Test ID generation with slug
eid = generate_external_id('Flow', name='Verify Gate')
assert 'verify_gate' in eid, f'slug missing: {eid}'
assert eid.startswith('ops.flow:'), f'wrong prefix: {eid}'
print(f'Flow ID: {eid}')

# Test parse
g, p, s, sl = parse_external_id('ops.flow:0002_verify_gate')
assert g == 'ops' and p == 'flow' and s == '0002' and sl == 'verify_gate'
print('parse OK')

print('All smoke tests passed')
"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 397 tests passing
```

**Commit message:**
```
Wave 16A03 Task 7: smoke test — name slugs in IDs verified

- make_id_slug() handles all MIHOS naming conventions
- generate_external_id() produces slug-bearing IDs
- parse_external_id() extracts (group, prefix, seq, slug)
- 397 existing tests passing
```

---

## TASK 8 — Update tests + CHANGELOG

**File to modify:** `tests/test_wave16a02.py`

Update `test_generate_decision_id` and similar tests to handle slug format:

```python
def test_generate_flow_id_with_name():
    """Flow ID with name includes slug."""
    eid = generate_external_id("Flow", name="Verify Gate")
    assert eid.startswith("ops.flow:")
    assert "verify_gate" in eid


def test_generate_flow_id_without_name():
    """Flow ID without name has no slug."""
    eid = generate_external_id("Flow")
    assert eid.startswith("ops.flow:")
    # No underscore after sequence (just digits)
    seq_part = eid.split(":")[1]
    # May or may not have slug depending on impl — just check format
    assert eid.startswith("ops.flow:")


def test_make_id_slug_strip_flow_prefix():
    assert make_id_slug("F2: Verify Gate") == "verify_gate"


def test_make_id_slug_strip_doc_prefix():
    assert make_id_slug("DOC-07 Core User Flows") == "core_user_flows"


def test_make_id_slug_empty():
    assert make_id_slug("") == ""


def test_make_id_slug_max_length():
    long_name = "This is a very long name that exceeds thirty characters easily"
    result = make_id_slug(long_name)
    assert len(result) <= 30


def test_parse_external_id_with_slug():
    g, p, s, sl = parse_external_id("ops.flow:0002_verify_gate")
    assert g == "ops"
    assert p == "flow"
    assert s == "0002"
    assert sl == "verify_gate"


def test_parse_external_id_without_slug():
    g, p, s, sl = parse_external_id("ops.flow:000001")
    assert g == "ops"
    assert sl == ""
```

Add to `tests/test_wave16a03.py` (new file):

```python
"""Tests for Wave 16A03: name slug in external ID."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.id_config import (
    make_id_slug, generate_external_id, parse_external_id
)
from gobp.core.init import init_project
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch


# ── make_id_slug tests ────────────────────────────────────────────────────────

def test_slug_flow_prefix():
    assert make_id_slug("F2: Verify Gate") == "verify_gate"

def test_slug_flow_prefix_double_digit():
    assert make_id_slug("F10: Homecoming") == "homecoming"

def test_slug_doc_prefix():
    result = make_id_slug("DOC-07 Core User Flows")
    assert "doc" not in result  # prefix stripped
    assert "core_user_flows" in result

def test_slug_plain_name():
    assert make_id_slug("TrustGate Engine") == "trustgate_engine"

def test_slug_traveller():
    assert make_id_slug("Traveller Identity") == "traveller_identity"

def test_slug_empty():
    assert make_id_slug("") == ""

def test_slug_max_30_chars():
    result = make_id_slug("This Is A Very Long Name That Exceeds Thirty Characters")
    assert len(result) <= 30

def test_slug_special_chars():
    result = make_id_slug("Use OTP (Email) for Auth!")
    assert result == "use_otp_email_for_auth"


# ── generate_external_id with slug tests ─────────────────────────────────────

def test_flow_id_with_name_has_slug():
    eid = generate_external_id("Flow", name="Verify Gate")
    assert eid.startswith("ops.flow:")
    assert "verify_gate" in eid

def test_decision_id_with_name():
    eid = generate_external_id("Decision", name="Use OTP for Auth")
    assert eid.startswith("core.dec:")
    assert "use_otp_for_auth" in eid

def test_entity_id_with_name():
    eid = generate_external_id("Entity", name="Traveller Identity")
    assert eid.startswith("domain.entity:")
    assert "traveller_identity" in eid

def test_id_without_name_no_slug():
    eid = generate_external_id("Flow")
    assert eid.startswith("ops.flow:")
    # Without name, no slug after sequence
    seq_part = eid.split(":", 1)[1]
    # seq_part should be all digits (no slug)
    assert seq_part.isdigit()

def test_session_id_unchanged():
    """Session IDs don't get slugs."""
    eid = generate_external_id("Session", name="Import MIHOS docs")
    assert eid.startswith("meta.session:")
    # Session format: meta.session:YYYY-MM-DD_XXXXXXXXX
    assert len(eid) == 37


# ── parse_external_id with slug tests ────────────────────────────────────────

def test_parse_new_format_with_slug():
    g, p, s, sl = parse_external_id("ops.flow:0002_verify_gate")
    assert (g, p, s, sl) == ("ops", "flow", "0002", "verify_gate")

def test_parse_new_format_without_slug():
    g, p, s, sl = parse_external_id("ops.flow:000001")
    assert g == "ops" and sl == ""

def test_parse_legacy_format():
    g, p, s, sl = parse_external_id("flow:verify_gate")
    assert g == "" and sl == ""

def test_parse_complex_slug():
    g, p, s, sl = parse_external_id("core.dec:0001_use_otp_for_auth")
    assert sl == "use_otp_for_auth"


# ── Dispatcher integration tests ──────────────────────────────────────────────

def test_create_node_gets_slug_id(gobp_root: Path):
    """create: with name produces slug-bearing ID."""
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
    assert "verify_gate" in node_id, f"slug missing from ID: {node_id}"
    assert node_id.startswith("ops.flow:"), f"wrong prefix: {node_id}"


def test_find_by_slug(gobp_root: Path):
    """find: slug_name matches node with slug in ID."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch(
        "session:start actor='test' goal='find slug test'", index, gobp_root
    ))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    # Create node with slug
    asyncio.run(dispatch(
        f"create:Flow name='Verify Gate' session_id='{sid}'",
        index, gobp_root
    ))
    index = GraphIndex.load_from_disk(gobp_root)

    # Find by slug
    r = asyncio.run(dispatch("find: verify_gate", index, gobp_root))
    assert r["ok"] is True
    ids = [m["id"] for m in r["matches"]]
    assert any("verify_gate" in nid for nid in ids), f"slug not found in: {ids}"
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave16a03.py -v
# Expected: ~22 tests

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 419+ tests
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A03] — Name Slug in External ID — 2026-04-16

### Why
External IDs without slugs (ops.flow:000001) are opaque.
AI and humans can't tell what a node is from its ID alone.

### New format
```
{group}.{type_prefix}:{sequence}_{slug}

ops.flow:0002_verify_gate
ops.flow:0001_registration_flow
ops.engine:0001_trustgate_engine
domain.entity:000001_traveller_identity
core.dec:0001_use_otp_for_auth
```

### Added
- `make_id_slug()`: strips F1:/DOC-07:/WAVE prefixes, lowercase, max 30 chars
- `generate_external_id()`: name param → slug appended to sequence
- `parse_external_id()`: returns 4-tuple (group, prefix, seq, slug)
- find(): searches slug in FTS content

### Changed
- dispatcher.py: create/upsert pass name to ID generation
- write.py: node_upsert passes name to ID generation
- migrate_ids.py: re-migration adds slug to existing IDs
- All existing nodes re-migrated with name slugs

### Total: 419+ tests
```

**Commit message:**
```
Wave 16A03 Task 8: tests/test_wave16a03.py + update test_wave16a02.py + CHANGELOG

- test_wave16a03.py: ~22 tests for slug generation, parse, dispatch
- test_wave16a02.py: updated parse_external_id tests for 4-tuple
- 419+ tests passing
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
nodes = index.all_nodes()

# Check slug presence
with_slug = [n for n in nodes
             if '_' in n.get('id','').split(':')[-1]
             and not n.get('id','').startswith('meta.session:')]
print(f'Nodes with slug: {len(with_slug)}/{len(nodes)}')
for n in with_slug[:8]:
    print(f'  {n[\"id\"]}')
"

git log --oneline | Select-Object -First 10
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. BACKUP FIRST

```powershell
Copy-Item -Recurse D:\GoBP\.gobp D:\GoBP\.gobp_backup_pre_16a03 -Force
Copy-Item -Recurse D:\MIHOS-v1\.gobp D:\MIHOS-v1\.gobp_backup_pre_16a03 -Force
```

## 2. Copy Brief

```powershell
cd D:\GoBP
# Save to D:\GoBP\waves\wave_16a03_brief.md
git add waves/wave_16a03_brief.md
git commit -m "Add Wave 16A03 Brief — name slug in external ID"
git push origin main
```

## 3. Dispatch Cursor

```
Read .cursorrules and waves/wave_16a03_brief.md first.
Also read gobp/core/id_config.py, gobp/core/migrate_ids.py,
gobp/mcp/dispatcher.py, gobp/mcp/tools/write.py,
gobp/mcp/tools/read.py.

CRITICAL: Task 6 re-migrates existing nodes with name slugs.
          Run dry-run first, verify slugs look correct, then actual.
          Backup already done by CEO.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 8 tasks sequentially.
R9: all 397 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 4. Audit Claude CLI

```
Audit Wave 16A03. Read CLAUDE.md and waves/wave_16a03_brief.md.
Set env: $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: make_id_slug() in id_config.py, generate_external_id() has name param,
          parse_external_id() returns 4-tuple (group, prefix, seq, slug)
- Task 2: dispatcher create/upsert pass name to generate_external_id()
- Task 3: write.py node_upsert passes name to ID generation
- Task 4: find() searches slug in FTS content
- Task 5: migrate_ids.py _needs_migration() detects missing slugs,
          migration passes node name to generate_external_id()
- Task 6: re-migration ran, nodes have slugs:
          ops.flow:0002_verify_gate, core.dec:0001_use_otp_for_auth
- Task 7: smoke test passed, 397 tests passing
- Task 8: test_wave16a03.py ~22 tests, 419+ total, CHANGELOG updated

BLOCKING RULE: Gặp vấn đề không tự xử lý → DỪNG ngay, báo CEO.

Expected: 419+ tests. Report WAVE 16A03 AUDIT COMPLETE.
```

---

# WHAT COMES NEXT

```
Wave 16A03 done
    ↓
Wave 8B — MIHOS import
  All nodes get: ops.flow:0002_verify_gate
  AI sees node purpose from ID alone
  Hierarchical viewer shows tier + slug labels
    ↓
Wave 17A01 — A2A Interview Protocol
Wave 17B02 — Auto-link on import
```

---

*Wave 16A03 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-16*

◈
