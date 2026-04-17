# WAVE 16A08 BRIEF — PROPER TEXT NORMALIZATION

**Wave:** 16A08
**Title:** Vietnamese text normalization với unidecode + search intent fix
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-17
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 4 tasks
**Estimated effort:** 1-2 hours

---

## CONTEXT

Wave 16A07 fix Vietnamese search nhưng dùng unicodedata — chưa đủ:

```
Problem:
  "dang nhap" → 0 results
  "đăng nhập" → 1 result
  
  Root cause: unicodedata.NFD chỉ strip combining chars
  "ă" (U+0103) decomposes → "a" + combining breve
  Nhưng search "dang nhap" không khớp vì normalization
  không nhất quán giữa query và node name

Fix:
  Dùng unidecode library — chuẩn công nghiệp
  unidecode("đăng nhập") → "dang nhap" ✓
  unidecode("Mi Hốt")    → "Mi Hot"    ✓
  unidecode("Hà Nội")    → "Ha Noi"    ✓
  → Consistent, battle-tested, handles edge cases
```

**P2 — find: session vẫn ra Session nodes**
```
Current: find: session → Session nodes appear (text match)
Expected: find: session intent = search knowledge, not metadata
Fix: Session excluded unless type_filter='Session' explicitly
     (include_sessions param already exists but not default)
```

---

## DESIGN

### normalize_text() update

```python
# Before (Wave 16A07):
def normalize_text(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

# After (Wave 16A08):
def normalize_text(text: str) -> str:
    try:
        from unidecode import unidecode
        return unidecode(text).lower().strip()
    except ImportError:
        # Fallback to unicodedata if unidecode not installed
        import unicodedata
        nfd = unicodedata.normalize("NFD", text.lower())
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")
```

### Session exclusion — strict default

```python
# find: session → excludes Session (keyword matches text, not type)
# find:Session  → includes Session (explicit type filter)
# find: session include_sessions=true → includes Session

# Rule: Session excluded unless:
#   1. type_filter == "Session" (explicit)
#   2. include_sessions=true (explicit opt-in)
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 507 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 507 tests passing

# Install unidecode
D:/GoBP/venv/Scripts/pip.exe install unidecode
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/core/search.py` | Update normalize_text() |
| 3 | `gobp/mcp/tools/read.py` | Session exclusion fix |
| 4 | `waves/wave_16a08_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Update normalize_text() with unidecode

**File to modify:** `gobp/core/search.py`

**Re-read in full.**

Step 1 — Install unidecode:
```powershell
D:/GoBP/venv/Scripts/pip.exe install unidecode
```

Step 2 — Add to `requirements.txt` or `pyproject.toml`:
```
unidecode>=1.3.0
```

Step 3 — Update `normalize_text()`:

```python
def normalize_text(text: str) -> str:
    """Normalize text for Vietnamese-aware search.
    
    Uses unidecode for consistent romanization:
        'đăng nhập' → 'dang nhap'
        'Mi Hốt'    → 'Mi Hot'
        'Hà Nội'    → 'Ha Noi'
        'TrustGate' → 'TrustGate' (ASCII unchanged)
    
    Falls back to unicodedata if unidecode not installed.
    """
    try:
        from unidecode import unidecode
        return unidecode(text).lower().strip()
    except ImportError:
        import unicodedata as _uc
        nfd = _uc.normalize("NFD", text.lower())
        return "".join(c for c in nfd if _uc.category(c) != "Mn")
```

**Verify:**
```powershell
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.search import normalize_text
assert normalize_text('đăng nhập') == 'dang nhap', normalize_text('đăng nhập')
assert normalize_text('Mi Hốt') == 'mi hot', normalize_text('Mi Hốt')
assert normalize_text('Hà Nội') == 'ha noi', normalize_text('Hà Nội')
assert normalize_text('TrustGate') == 'trustgate'
assert normalize_text('dang nhap') == 'dang nhap'
print('normalize_text OK')
"
```

**Commit message:**
```
Wave 16A08 Task 1: upgrade normalize_text() to use unidecode

- unidecode: battle-tested Vietnamese romanization library
- 'đăng nhập' → 'dang nhap' (consistent with user input)
- 'Mi Hốt' → 'mi hot'
- Graceful fallback to unicodedata if unidecode not installed
- Add unidecode to requirements
```

---

## TASK 2 — Fix Session strict exclusion in find()

**Goal:** `find: session` does NOT return Session nodes (text search intent ≠ type filter).

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read find() in full.**

Session exclusion logic:

```python
# Determine if sessions should be included
# Sessions included ONLY when:
#   1. Explicit type_filter = "Session"
#   2. User passes include_sessions=true

explicit_session_filter = (type_filter == "Session")
include_sessions_param = args.get("include_sessions", "false").lower() == "true"
include_sessions = explicit_session_filter or include_sessions_param

exclude_types = [] if include_sessions else ["Session"]
```

**Acceptance criteria:**
```
find: session      → no Session nodes (text search)
find: session include_sessions=true → Session nodes included
find:Session       → Session nodes only (explicit type filter)
find:Session test  → Session nodes matching "test"
```

**Commit message:**
```
Wave 16A08 Task 2: Session strict exclusion in find()

- find: session → no Session nodes (keyword ≠ type intent)
- find:Session → Session only (explicit type filter)
- include_sessions=true to opt-in
- Reduces metadata noise in knowledge search
```

---

## TASK 3 — Smoke test on MIHOS

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp_mihos"

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.core.search import normalize_text
from gobp.mcp.dispatcher import dispatch

# Test normalize
assert normalize_text('đăng nhập') == 'dang nhap'
assert normalize_text('Mi Hốt') == 'mi hot'
assert normalize_text('dang nhap') == 'dang nhap'
# Both normalize to same
assert normalize_text('đăng nhập') == normalize_text('dang nhap')
print('normalize OK')

async def test():
    root = Path('D:/MIHOS-v1')
    index = GraphIndex.load_from_disk(root)
    
    # Test dang nhap search
    r1 = await dispatch('find: dang nhap mode=summary', index, root)
    r2 = await dispatch('find: đăng nhập mode=summary', index, root)
    print(f'find dang nhap: {len(r1[\"matches\"])} results')
    print(f'find đăng nhập: {len(r2[\"matches\"])} results')
    # Both should return same count
    
    # Test mihot
    r3 = await dispatch('find: mihot mode=summary', index, root)
    r4 = await dispatch('find: mi hốt mode=summary', index, root)
    print(f'find mihot: {len(r3[\"matches\"])} results')
    print(f'find mi hốt: {len(r4[\"matches\"])} results')
    
    # Test session exclusion
    r5 = await dispatch('find: session mode=summary', index, root)
    types5 = {m.get('type') for m in r5.get('matches', [])}
    has_session = 'Session' in types5
    print(f'find session (no Session expected): has_session={has_session}')
    assert not has_session, f'Session nodes leaked into results: {types5}'
    
    # find:Session should work
    r6 = await dispatch('find:Session mode=summary', index, root)
    types6 = {m.get('type') for m in r6.get('matches', [])}
    print(f'find:Session types: {types6}')
    
    print('SMOKE TESTS PASSED')

asyncio.run(test())
"

# Save smoke script as permanent artifact
# (not deleted after run — for audit trail)
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 507 tests passing
```

**Save smoke results to file:**
```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp_mihos"
D:/GoBP/venv/Scripts/python.exe scripts/wave16a07_search_replay.py > .gobp/history/w16a08_smoke.txt 2>&1
```

**Commit message:**
```
Wave 16A08 Task 3: smoke test — dang nhap == đăng nhập + session strict

- normalize('dang nhap') == normalize('đăng nhập') verified
- find: session → no Session nodes
- find:Session → Session nodes only
- Smoke results saved to .gobp/history/w16a08_smoke.txt
- 507 tests passing
```

---

## TASK 4 — Update tests + CHANGELOG

**File to modify:** `tests/test_wave16a07.py`

Update existing Vietnamese normalization tests to use unidecode behavior:

```python
def test_normalize_removes_vietnamese_diacritics():
    # unidecode: full romanization
    assert normalize_text("Mi Hốt") == "mi hot"
    assert normalize_text("Hà Nội") == "ha noi"
    assert normalize_text("đăng nhập") == "dang nhap"
    assert normalize_text("Bàn Cờ") == "ban co"


def test_normalize_equivalence():
    """Vietnamese and ASCII versions normalize to same string."""
    assert normalize_text("Mi Hốt") == normalize_text("mi hot")
    assert normalize_text("đăng nhập") == normalize_text("dang nhap")
    assert normalize_text("Hà Nội") == normalize_text("ha noi")
```

**File to create:** `tests/test_wave16a08.py`

```python
"""Tests for Wave 16A08: unidecode normalization + Session strict exclusion."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gobp.core.search import normalize_text, search_nodes
from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch


# ── unidecode normalization tests ─────────────────────────────────────────────

def test_unidecode_dang_nhap():
    assert normalize_text("đăng nhập") == "dang nhap"


def test_unidecode_mi_hot():
    assert normalize_text("Mi Hốt") == "mi hot"


def test_unidecode_ha_noi():
    assert normalize_text("Hà Nội") == "ha noi"


def test_unidecode_ban_co():
    assert normalize_text("Bàn Cờ") == "ban co"


def test_unidecode_ascii_unchanged():
    assert normalize_text("TrustGate") == "trustgate"
    assert normalize_text("MIHOS") == "mihos"


def test_normalize_dang_nhap_equivalence():
    """User typing 'dang nhap' finds 'đăng nhập' nodes."""
    assert normalize_text("đăng nhập") == normalize_text("dang nhap")


def test_normalize_mi_hot_equivalence():
    assert normalize_text("Mi Hốt") == normalize_text("mi hot")
    assert normalize_text("Mi Hốt") == normalize_text("mihot")


def test_normalize_ha_noi_equivalence():
    assert normalize_text("Hà Nội") == normalize_text("ha noi")


# ── Session strict exclusion tests ───────────────────────────────────────────

def test_find_session_keyword_excludes_sessions(tmp_path):
    """find: session (keyword) should NOT return Session nodes."""
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    # Create a session
    asyncio.run(dispatch(
        "session:start actor='test' goal='session exclusion strict test'",
        index, tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    r = asyncio.run(dispatch("find: session mode=summary", index, tmp_path))
    types = {m.get("type") for m in r.get("matches", [])}
    assert "Session" not in types, f"Session leaked into keyword search: {types}"


def test_find_session_type_filter_includes_sessions(tmp_path):
    """find:Session (type filter) SHOULD return Session nodes."""
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    asyncio.run(dispatch(
        "session:start actor='test' goal='explicit session type test'",
        index, tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    r = asyncio.run(dispatch("find:Session mode=summary", index, tmp_path))
    types = {m.get("type") for m in r.get("matches", [])}
    assert "Session" in types, f"Expected Session nodes with explicit type filter"


def test_find_include_sessions_param(tmp_path):
    """find: session include_sessions=true should include Session nodes."""
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    asyncio.run(dispatch(
        "session:start actor='test' goal='include sessions param test'",
        index, tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    r = asyncio.run(dispatch(
        "find: session include_sessions=true mode=summary", index, tmp_path
    ))
    types = {m.get("type") for m in r.get("matches", [])}
    assert "Session" in types


# ── Integration: diacritics search finds nodes ───────────────────────────────

def test_search_dang_nhap_finds_node(tmp_path):
    """'dang nhap' should find node named 'Đăng Nhập'."""
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='dang nhap test'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    asyncio.run(dispatch(
        f"create:Flow name='Đăng Nhập Flow' session_id={sid}", index, tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    results = search_nodes(index, "dang nhap", exclude_types=[])
    names = [n.get("name", "") for _, n in results]
    assert any("Đăng Nhập" in n or "dang nhap" in normalize_text(n) for n in names), \
        f"Expected 'Đăng Nhập Flow' in results, got: {names}"


def test_search_unicode_and_ascii_same_results(tmp_path):
    """find: đăng nhập and find: dang nhap return same results."""
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch(
        "session:start actor='test' goal='unicode ascii parity'", index, tmp_path
    ))["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    asyncio.run(dispatch(
        f"create:Flow name='Đăng Nhập Flow' session_id={sid}", index, tmp_path
    ))

    index = GraphIndex.load_from_disk(tmp_path)
    r1 = search_nodes(index, "dang nhap", exclude_types=[])
    r2 = search_nodes(index, "đăng nhập", exclude_types=[])

    ids1 = {n.get("id") for _, n in r1}
    ids2 = {n.get("id") for _, n in r2}
    assert ids1 == ids2, f"ASCII vs Unicode gave different results: {ids1} vs {ids2}"
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A08] — Proper Text Normalization — 2026-04-17

### Changed
- **normalize_text()** upgraded from unicodedata to unidecode
  - 'đăng nhập' → 'dang nhap' (consistent romanization)
  - 'dang nhap' == 'đăng nhập' in search ✓
  - Handles all Vietnamese diacritics correctly
  - Graceful fallback if unidecode not installed

- **Session strict exclusion** in find()
  - find: session → no Session nodes (keyword ≠ type)
  - find:Session → Session nodes only (explicit type filter)
  - include_sessions=true to opt-in

### Added
- unidecode to requirements

### Total: 520+ tests
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave16a08.py -v
# Expected: ~13 tests

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 520+ tests
```

**Commit message:**
```
Wave 16A08 Task 4: tests/test_wave16a08.py + CHANGELOG

- 13 tests: unidecode normalization, Session strict exclusion, integration
- Update test_wave16a07.py normalization assertions for unidecode
- 520+ tests passing
- CHANGELOG: Wave 16A08 entry
```

---

# POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp_mihos"

D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.search import normalize_text
print('dang nhap:', normalize_text('dang nhap'))
print('đăng nhập:', normalize_text('đăng nhập'))
print('equal:', normalize_text('dang nhap') == normalize_text('đăng nhập'))
print('mi hot:', normalize_text('mi hot'))
print('mi hốt:', normalize_text('mi hốt'))
"
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Save Brief

```powershell
cd D:\GoBP
# Save to D:\GoBP\waves\wave_16a08_brief.md
git add waves/wave_16a08_brief.md
git commit -m "Add Wave 16A08 Brief — unidecode normalization + Session strict exclusion"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_16a08_brief.md first.
Also read gobp/core/search.py, gobp/mcp/tools/read.py.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Install first:
  D:/GoBP/venv/Scripts/pip.exe install unidecode

Execute ALL 4 tasks sequentially.
R9: all 507 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 16A08. Read CLAUDE.md and waves/wave_16a08_brief.md.
Set env: $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: normalize_text('đăng nhập') == 'dang nhap'
          normalize_text('dang nhap') == normalize_text('đăng nhập')
          unidecode in requirements
- Task 2: find: session → no Session nodes
          find:Session → Session nodes only
- Task 3: Smoke on MIHOS — dang nhap == đăng nhập results
          w16a08_smoke.txt saved in .gobp/history/
- Task 4: test_wave16a08.py 13 tests, 520+ total, CHANGELOG

BLOCKING RULE: Gặp vấn đề → DỪNG ngay, báo CEO.

Expected: 520+ tests. Report WAVE 16A08 AUDIT COMPLETE.
```

---

*Wave 16A08 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-17*

◈
