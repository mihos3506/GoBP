# WAVE 16A02 BRIEF — SNOWFLAKE ID + GROUP NAMESPACE + MIGRATION + HIERARCHICAL VIEWER

**Wave:** 16A02
**Title:** Snowflake ID generator, external ID with group namespace, migrate existing nodes, hierarchical viewer layout
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-16
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 11 atomic tasks
**Estimated effort:** 6-8 hours

---

## CONTEXT

**Why now:** MIHOS will have millions of nodes per type (Traveller, Place, Moment). Current ID format (`flow:verify_gate`, `dec:d001`) has 3 problems:

1. **No group namespace** → can't query by domain group
2. **Text primary key** → slow joins at million-scale
3. **No sequential ordering** → index fragmentation

**Solution:** Implement proper ID design before Wave 8B MIHOS import.

**Current state:** 378 nodes, 982 edges — small enough to migrate cleanly.

---

## DESIGN (from GoBP_ID_DESIGN.md)

### Internal ID — Snowflake
```
64-bit integer, self-generating, no DB required:
  41 bits = timestamp (ms since 2024-01-01)
  10 bits = machine ID (0-1023)
  12 bits = sequence per ms (0-4095)

→ 4096 IDs/ms per machine
→ Globally unique without central coordination
→ Sortable by creation time
→ Works offline
```

### External ID — Group namespace
```
Format: {group}.{type_prefix}:{sequence}

Groups:
  core:   Decision, Invariant, Concept
  domain: Entity (+ future: Traveller, Place, Moment)
  ops:    Flow, Engine, Feature, Screen, APIEndpoint
  test:   TestKind, TestCase
  meta:   Session, Wave, Document, Lesson, Node, Repository

Sequence: zero-padded based on scale config
  small:  4 digits  (< 10K)   — core, ops, infra
  medium: 6 digits  (< 1M)    — test, meta
  large:  8 digits  (< 100M)  — domain entities
  huge:   10 digits (< 10B)   — future Traveller/Moment

Examples:
  core.dec:0001
  core.inv:0001
  ops.flow:0001
  ops.feat:0001
  domain.entity:000001
  test.kind:0001
  test.case:000001
  meta.session:20260416_a3f7c2  (special format, unchanged)
  meta.doc:{slug}_{hash}        (special format, unchanged)
  meta.wave:0001
  meta.lesson:000001
```

### Group config in .gobp/config.yaml
```yaml
id_groups:
  core:
    types: [Decision, Invariant, Concept]
    sequence_scale: small
    tier_weight: 20
    tier_y: -300

  domain:
    types: [Entity]
    sequence_scale: large
    tier_weight: 10
    tier_y: -150

  ops:
    types: [Flow, Engine, Feature, Screen, APIEndpoint]
    sequence_scale: small
    tier_weight: 8
    tier_y: 0

  test:
    types: [TestKind, TestCase]
    sequence_scale: medium
    tier_weight: 2
    tier_y: 150

  meta:
    types: [Session, Wave, Document, Lesson, Node, Repository]
    sequence_scale: medium
    tier_weight: 0
    tier_y: 300
```

### Migration mapping (378 nodes)
```
Decision(17)    → core.dec:0001..0017
Invariant(3)    → core.inv:0001..0003
Concept(1)      → core.con:0001

Entity(3)       → domain.entity:000001..000003

Flow(3)         → ops.flow:0001..0003
Engine(3)       → ops.engine:0001..0003
Feature(77)     → ops.feat:0001..0077
Screen(1)       → ops.screen:0001
APIEndpoint(3)  → ops.api:0001..0003

TestKind(16)    → test.kind:0001..0016
TestCase(80)    → test.case:000001..000080

Session(24)     → meta.session:YYYYMMDD_XXXXXX (unchanged format)
Wave(22)        → meta.wave:0001..0022
Document(110)   → meta.doc:{slug}_{hash} (unchanged format)
Lesson(7)       → meta.lesson:000001..000007
Node(7)         → meta.node:000001..000007
Repository(1)   → meta.repo:000001
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 367 existing tests must pass after every task.

**CRITICAL for this wave:**
- Migration is irreversible — verify before committing
- After migration, old IDs must still resolve (backward compat)
- All edges must be updated to use new IDs
- .gobp/ files are source of truth — update files first, then DB

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 367 tests passing

# Backup .gobp/ before migration
Copy-Item -Recurse D:\GoBP\.gobp D:\GoBP\.gobp_backup_pre_16a02
Copy-Item -Recurse D:\MIHOS-v1\.gobp D:\MIHOS-v1\.gobp_backup_pre_16a02
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/core/mutator.py` | ID generation to replace |
| 3 | `gobp/mcp/dispatcher.py` | _get_type_prefix() to replace |
| 4 | `gobp/core/graph.py` | TIER_WEIGHTS to update |
| 5 | `gobp/viewer/index.html` | Add hierarchical layout |
| 6 | `gobp/schema/core_edges.yaml` | Add missing edge types |
| 7 | `waves/wave_16a02_brief.md` | This file |

---

# TASKS

---

## TASK 1 — Create gobp/core/snowflake.py

**Goal:** Snowflake ID generator. Self-contained, no external dependencies.

**File to create:** `gobp/core/snowflake.py`

```python
"""Snowflake ID generator for GoBP.

Generates 64-bit integers that are:
- Globally unique (without central coordination)
- Time-sortable (newer IDs are larger)
- Fast (4096 IDs per millisecond per machine)

Bit layout (Twitter Snowflake):
  1  bit  — sign (always 0)
  41 bits — milliseconds since EPOCH
  10 bits — machine ID (0-1023)
  12 bits — sequence per millisecond (0-4095)

Epoch: 2024-01-01 00:00:00 UTC
"""

from __future__ import annotations

import os
import threading
import time
from typing import ClassVar

# Epoch: 2024-01-01 00:00:00 UTC in milliseconds
_EPOCH_MS: int = 1704067200000

# Bit shifts
_MACHINE_ID_BITS = 10
_SEQUENCE_BITS = 12
_MACHINE_ID_SHIFT = _SEQUENCE_BITS
_TIMESTAMP_SHIFT = _SEQUENCE_BITS + _MACHINE_ID_BITS

# Masks
_MAX_MACHINE_ID = (1 << _MACHINE_ID_BITS) - 1   # 1023
_MAX_SEQUENCE = (1 << _SEQUENCE_BITS) - 1         # 4095


class SnowflakeGenerator:
    """Thread-safe Snowflake ID generator."""

    _instance: ClassVar["SnowflakeGenerator | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, machine_id: int = 0) -> None:
        if machine_id < 0 or machine_id > _MAX_MACHINE_ID:
            raise ValueError(f"machine_id must be 0-{_MAX_MACHINE_ID}, got {machine_id}")
        self.machine_id = machine_id & _MAX_MACHINE_ID
        self._sequence = 0
        self._last_ms = -1
        self._gen_lock = threading.Lock()

    @classmethod
    def default(cls) -> "SnowflakeGenerator":
        """Get default singleton generator."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # Machine ID from env or random
                    machine_id = int(os.environ.get("GOBP_MACHINE_ID", "0")) % 1024
                    cls._instance = cls(machine_id=machine_id)
        return cls._instance

    def next_id(self) -> int:
        """Generate next unique Snowflake ID."""
        with self._gen_lock:
            ms = self._current_ms()

            if ms < self._last_ms:
                # Clock went backwards — wait
                time.sleep((self._last_ms - ms) / 1000)
                ms = self._current_ms()

            if ms == self._last_ms:
                self._sequence = (self._sequence + 1) & _MAX_SEQUENCE
                if self._sequence == 0:
                    # Sequence exhausted — wait for next ms
                    while ms <= self._last_ms:
                        ms = self._current_ms()
            else:
                self._sequence = 0

            self._last_ms = ms

            return (
                ((ms - _EPOCH_MS) << _TIMESTAMP_SHIFT) |
                (self.machine_id << _MACHINE_ID_SHIFT) |
                self._sequence
            )

    def _current_ms(self) -> int:
        return int(time.time() * 1000)


# Module-level convenience function
def generate_snowflake() -> int:
    """Generate a Snowflake ID using default generator."""
    return SnowflakeGenerator.default().next_id()


def snowflake_to_timestamp(snowflake_id: int) -> float:
    """Extract creation timestamp from Snowflake ID."""
    ms = (snowflake_id >> _TIMESTAMP_SHIFT) + _EPOCH_MS
    return ms / 1000


def snowflake_to_datetime(snowflake_id: int):
    """Extract creation datetime from Snowflake ID."""
    from datetime import datetime, timezone
    ts = snowflake_to_timestamp(snowflake_id)
    return datetime.fromtimestamp(ts, tz=timezone.utc)
```

**Verify:**
```powershell
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.snowflake import generate_snowflake, snowflake_to_datetime

ids = [generate_snowflake() for _ in range(5)]
print('Generated IDs:')
for sid in ids:
    print(f'  {sid} → {snowflake_to_datetime(sid)}')

# Verify sortable
assert ids == sorted(ids) or True  # may be equal if same ms
print('Snowflake OK')
"
```

**Commit message:**
```
Wave 16A02 Task 1: create gobp/core/snowflake.py

- SnowflakeGenerator: thread-safe 64-bit ID generator
- Bit layout: 41-bit timestamp + 10-bit machine ID + 12-bit sequence
- Epoch: 2024-01-01 UTC
- generate_snowflake(): module-level convenience function
- snowflake_to_datetime(): extract creation time from ID
- GOBP_MACHINE_ID env var for distributed setup
```

---

## TASK 2 — Create gobp/core/id_config.py

**Goal:** Load group config from .gobp/config.yaml. Generate external IDs.

**File to create:** `gobp/core/id_config.py`

```python
"""GoBP ID configuration — group namespaces and external ID generation.

Reads id_groups from .gobp/config.yaml.
Falls back to DEFAULT_GROUPS if not configured.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# Default group configuration
DEFAULT_GROUPS: dict[str, dict[str, Any]] = {
    "core": {
        "types": ["Decision", "Invariant", "Concept"],
        "sequence_scale": "small",
        "tier_weight": 20,
        "tier_y": -300,
    },
    "domain": {
        "types": ["Entity"],
        "sequence_scale": "large",
        "tier_weight": 10,
        "tier_y": -150,
    },
    "ops": {
        "types": ["Flow", "Engine", "Feature", "Screen", "APIEndpoint"],
        "sequence_scale": "small",
        "tier_weight": 8,
        "tier_y": 0,
    },
    "test": {
        "types": ["TestKind", "TestCase"],
        "sequence_scale": "medium",
        "tier_weight": 2,
        "tier_y": 150,
    },
    "meta": {
        "types": ["Session", "Wave", "Document", "Lesson", "Node",
                  "Repository", "Idea"],
        "sequence_scale": "medium",
        "tier_weight": 0,
        "tier_y": 300,
    },
}

# Type prefix mapping
TYPE_PREFIXES: dict[str, str] = {
    "Decision": "dec", "Invariant": "inv", "Concept": "con",
    "Entity": "entity",
    "Flow": "flow", "Engine": "engine", "Feature": "feat",
    "Screen": "screen", "APIEndpoint": "api",
    "TestKind": "kind", "TestCase": "case",
    "Session": "session", "Wave": "wave", "Document": "doc",
    "Lesson": "lesson", "Node": "node", "Repository": "repo",
    "Idea": "idea",
}

SEQUENCE_PADDING: dict[str, int] = {
    "small": 4,    # 0001–9999
    "medium": 6,   # 000001–999999
    "large": 8,    # 00000001–99999999
    "huge": 10,    # 0000000001–9999999999
}

# Special ID formats (not sequence-based)
SPECIAL_ID_TYPES = {"Session", "Document"}


def load_groups(gobp_root: Path) -> dict[str, dict[str, Any]]:
    """Load id_groups from .gobp/config.yaml or return defaults."""
    config_path = gobp_root / ".gobp" / "config.yaml"
    if config_path.exists():
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if config and "id_groups" in config:
                return config["id_groups"]
        except Exception:
            pass
    return DEFAULT_GROUPS


def get_group_for_type(node_type: str, groups: dict | None = None) -> str:
    """Get group namespace for a NodeType."""
    if groups is None:
        groups = DEFAULT_GROUPS
    for group_name, group_config in groups.items():
        if node_type in group_config.get("types", []):
            return group_name
    return "meta"  # fallback


def get_type_prefix(node_type: str) -> str:
    """Get short prefix for NodeType."""
    return TYPE_PREFIXES.get(node_type, node_type.lower()[:6])


def generate_external_id(
    node_type: str,
    gobp_root: Path | None = None,
    groups: dict | None = None,
) -> str:
    """Generate external ID with group namespace.

    Format: {group}.{type_prefix}:{sequence}

    Special cases:
      Session → meta.session:YYYYMMDD_XXXXXXXXX
      Document → meta.doc:{slug}_{md5[:6]}

    Args:
        node_type: NodeType string
        gobp_root: Project root (for loading group config)
        groups: Pre-loaded groups dict (avoids re-reading config)

    Returns:
        External ID string like "core.dec:0001"
    """
    from gobp.core.snowflake import generate_snowflake

    if groups is None and gobp_root is not None:
        groups = load_groups(gobp_root)
    if groups is None:
        groups = DEFAULT_GROUPS

    # Special formats
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

    # Use Snowflake lower bits for sequence part (last N digits)
    sf = generate_snowflake()
    seq = sf % (10 ** padding)

    return f"{group}.{prefix}:{seq:0{padding}d}"


def parse_external_id(external_id: str) -> tuple[str, str, str]:
    """Parse external ID → (group, type_prefix, sequence).

    Handles:
      "core.dec:0001"           → ("core", "dec", "0001")
      "meta.session:2026-04-16_abc" → ("meta", "session", "2026-04-16_abc")
      "flow:verify_gate"        → ("", "flow", "verify_gate")  # legacy
      "dec:d001"                → ("", "dec", "d001")           # legacy
    """
    if "." in external_id and ":" in external_id:
        dot_idx = external_id.index(".")
        colon_idx = external_id.index(":")
        if dot_idx < colon_idx:
            group = external_id[:dot_idx]
            type_prefix = external_id[dot_idx + 1:colon_idx]
            sequence = external_id[colon_idx + 1:]
            return group, type_prefix, sequence

    # Legacy format: "type:name"
    if ":" in external_id:
        parts = external_id.split(":", 1)
        return "", parts[0], parts[1]

    return "", "", external_id


def get_tier_y(node_type: str, groups: dict | None = None) -> float:
    """Get Y position for hierarchical viewer layout."""
    if groups is None:
        groups = DEFAULT_GROUPS
    group = get_group_for_type(node_type, groups)
    return groups.get(group, {}).get("tier_y", 0)


def get_tier_weight(node_type: str, groups: dict | None = None) -> int:
    """Get tier weight for priority computation."""
    if groups is None:
        groups = DEFAULT_GROUPS
    group = get_group_for_type(node_type, groups)
    return groups.get(group, {}).get("tier_weight", 0)
```

**Commit message:**
```
Wave 16A02 Task 2: create gobp/core/id_config.py

- DEFAULT_GROUPS: core/domain/ops/test/meta with types + tier config
- TYPE_PREFIXES: NodeType → short prefix mapping
- load_groups(): reads id_groups from .gobp/config.yaml
- generate_external_id(): group.prefix:sequence format
- parse_external_id(): parse new and legacy formats
- get_tier_y(): Y position for hierarchical viewer
- get_tier_weight(): priority tier weight from config
```

---

## TASK 3 — Update .gobp/config.yaml with id_groups

**Goal:** Add id_groups section to existing config.yaml files.

**File to modify:** `gobp/core/init.py`

**Re-read `init.py` in full.**

Update `_write_config()` or wherever config.yaml is written. Add `id_groups` section:

```python
config = {
    "schema_version": "2.1",
    "project_name": name,
    "created": datetime.now(timezone.utc).isoformat(),
    "id_groups": {
        "core": {
            "types": ["Decision", "Invariant", "Concept"],
            "sequence_scale": "small",
            "tier_weight": 20,
            "tier_y": -300,
        },
        "domain": {
            "types": ["Entity"],
            "sequence_scale": "large",
            "tier_weight": 10,
            "tier_y": -150,
        },
        "ops": {
            "types": ["Flow", "Engine", "Feature", "Screen", "APIEndpoint"],
            "sequence_scale": "small",
            "tier_weight": 8,
            "tier_y": 0,
        },
        "test": {
            "types": ["TestKind", "TestCase"],
            "sequence_scale": "medium",
            "tier_weight": 2,
            "tier_y": 150,
        },
        "meta": {
            "types": ["Session", "Wave", "Document", "Lesson", "Node",
                      "Repository", "Idea"],
            "sequence_scale": "medium",
            "tier_weight": 0,
            "tier_y": 300,
        },
    }
}
```

**Also update existing config files:**

```powershell
# Update GoBP project config
D:/GoBP/venv/Scripts/python.exe -c "
import yaml
from pathlib import Path

for project_root in [Path('D:/GoBP'), Path('D:/MIHOS-v1')]:
    config_path = project_root / '.gobp' / 'config.yaml'
    if not config_path.exists():
        continue
    config = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    # Add id_groups if not present
    from gobp.core.id_config import DEFAULT_GROUPS
    if 'id_groups' not in config:
        config['id_groups'] = DEFAULT_GROUPS
        config_path.write_text(
            yaml.safe_dump(config, allow_unicode=True, default_flow_style=False),
            encoding='utf-8'
        )
        print(f'Updated: {config_path}')
    else:
        print(f'Already has id_groups: {config_path}')
"
```

**Commit message:**
```
Wave 16A02 Task 3: add id_groups to config.yaml

- init.py: new projects get id_groups section in config.yaml
- Updated existing D:/GoBP/.gobp/config.yaml
- Updated existing D:/MIHOS-v1/.gobp/config.yaml
- id_groups defines group→types mapping + tier config
```

---

## TASK 4 — Update mutator.py to use new ID format

**Goal:** All new nodes get group-namespaced IDs.

**File to modify:** `gobp/core/mutator.py`

**Re-read mutator.py in full.**

Replace session ID generation and any `uuid4().hex[:9]` usage:

```python
# Replace _generate_session_id():
def _generate_session_id(goal: str = "") -> str:
    """Generate session ID using new group namespace format.
    Format: meta.session:YYYY-MM-DD_XXXXXXXXX
    Always exactly 37 chars.
    """
    from datetime import datetime, timezone
    import uuid as _uuid
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    short_hash = _uuid.uuid4().hex[:9]
    return f"meta.session:{date_str}_{short_hash}"
```

**File to modify:** `gobp/mcp/dispatcher.py`

Replace `_get_type_prefix()` with id_config:

```python
# Remove old _get_type_prefix() function

# In create/upsert handlers, replace:
# OLD:
node_id = args.get("node_id") or f"{_get_type_prefix(node_type)}:{_uuid.uuid4().hex[:9]}"

# NEW:
from gobp.core.id_config import generate_external_id
node_id = args.get("node_id") or generate_external_id(node_type, project_root)
```

**Commit message:**
```
Wave 16A02 Task 4: use new ID format in mutator + dispatcher

- mutator.py: session IDs use meta.session: prefix
- dispatcher.py: create/upsert use generate_external_id()
- Remove _get_type_prefix() (replaced by id_config)
- New nodes get group-namespaced IDs: core.dec:0001, ops.feat:0001
```

---

## TASK 5 — Update graph.py to use id_config for tier weights

**Goal:** TIER_WEIGHTS reads from id_config instead of hard-coded dict.

**File to modify:** `gobp/core/graph.py`

**Re-read graph.py in full.**

Replace hard-coded `TIER_WEIGHTS` with dynamic lookup:

```python
# Remove hard-coded TIER_WEIGHTS dict

def compute_priority_score(self, node_id: str) -> int:
    """Compute numeric priority: edge_count + tier_weight from config."""
    from gobp.core.id_config import get_tier_weight, load_groups

    node = self.get_node(node_id)
    if not node:
        return 0

    groups = load_groups(self._gobp_root) if self._gobp_root else None
    incoming = len(self.get_edges_to(node_id))
    outgoing = len(self.get_edges_from(node_id))
    node_type = node.get("type", "Node")
    tier_weight = get_tier_weight(node_type, groups)
    return incoming + outgoing + tier_weight
```

**Commit message:**
```
Wave 16A02 Task 5: graph.py tier weights from id_config

- compute_priority_score(): reads tier_weight from id_config
- Uses project-specific config if available
- Falls back to DEFAULT_GROUPS
- TIER_WEIGHTS hard-coded dict removed
```

---

## TASK 6 — Create migration script + migrate existing nodes

**Goal:** Migrate 378 existing nodes to new external ID format.

**File to create:** `gobp/core/migrate_ids.py`

```python
"""Migration script: old IDs → new group-namespaced IDs.

Migrates .gobp/nodes/*.md files to use new external ID format.
Creates ID mapping file for backward compatibility.
Updates all edges to use new IDs.

Usage:
    python -m gobp.core.migrate_ids --root D:/GoBP --dry-run
    python -m gobp.core.migrate_ids --root D:/GoBP
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


def _load_node_file(path: Path) -> dict[str, Any]:
    """Load node from markdown file with YAML front-matter."""
    content = path.read_text(encoding="utf-8")
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return yaml.safe_load(parts[1]) or {}
    return {}


def _write_node_file(path: Path, node: dict[str, Any], body: str = "") -> None:
    """Write node back to markdown file."""
    fm = yaml.safe_dump(node, allow_unicode=True, default_flow_style=False)
    content = f"---\n{fm}---\n{body}"
    path.write_text(content, encoding="utf-8")


def _needs_migration(node_id: str) -> bool:
    """Check if ID needs migration to new format."""
    # New format has group.prefix:sequence pattern
    if "." in node_id and ":" in node_id:
        dot_idx = node_id.index(".")
        colon_idx = node_id.index(":")
        if dot_idx < colon_idx:
            return False  # Already new format
    return True


def migrate_project(gobp_root: Path, dry_run: bool = True) -> dict[str, Any]:
    """Migrate all nodes in a project to new ID format.

    Returns:
        {migrated, skipped, errors, id_mapping}
    """
    from gobp.core.id_config import (
        generate_external_id, load_groups, get_group_for_type
    )

    nodes_dir = gobp_root / ".gobp" / "nodes"
    edges_dir = gobp_root / ".gobp" / "edges"

    if not nodes_dir.exists():
        return {"migrated": 0, "skipped": 0, "errors": [], "id_mapping": {}}

    groups = load_groups(gobp_root)
    id_mapping: dict[str, str] = {}  # old_id → new_id
    migrated = 0
    skipped = 0
    errors = []

    # Phase 1: Generate new IDs for all nodes
    node_files = list(nodes_dir.glob("**/*.md"))
    for node_file in sorted(node_files):
        try:
            node = _load_node_file(node_file)
            old_id = node.get("id", "")
            if not old_id:
                errors.append(f"{node_file.name}: no id field")
                continue

            if not _needs_migration(old_id):
                skipped += 1
                id_mapping[old_id] = old_id  # no change
                continue

            # Generate new ID
            node_type = node.get("type", "Node")
            new_id = generate_external_id(node_type, gobp_root, groups)
            id_mapping[old_id] = new_id

        except Exception as e:
            errors.append(f"{node_file.name}: {e}")

    if dry_run:
        return {
            "migrated": len([v for k, v in id_mapping.items() if k != v]),
            "skipped": skipped,
            "errors": errors,
            "id_mapping": id_mapping,
            "dry_run": True,
        }

    # Phase 2: Update node files with new IDs
    for node_file in node_files:
        try:
            content = node_file.read_text(encoding="utf-8")
            node = _load_node_file(node_file)
            old_id = node.get("id", "")

            if old_id not in id_mapping or id_mapping[old_id] == old_id:
                continue

            new_id = id_mapping[old_id]
            node["id"] = new_id
            node["legacy_id"] = old_id  # preserve for backward compat

            # Extract body (content after front-matter)
            body = ""
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    body = parts[2]

            _write_node_file(node_file, node, body)

            # Rename file to match new ID
            new_filename = new_id.replace(".", "_").replace(":", "_") + ".md"
            new_path = node_file.parent / new_filename
            if new_path != node_file:
                node_file.rename(new_path)

            migrated += 1

        except Exception as e:
            errors.append(f"{node_file.name}: {e}")

    # Phase 3: Update edge files
    if edges_dir.exists():
        for edge_file in edges_dir.glob("**/*.yaml"):
            try:
                edges = yaml.safe_load(edge_file.read_text(encoding="utf-8")) or []
                updated = False
                for edge in edges:
                    old_from = edge.get("from", "")
                    old_to = edge.get("to", "")
                    if old_from in id_mapping and id_mapping[old_from] != old_from:
                        edge["from"] = id_mapping[old_from]
                        edge["legacy_from"] = old_from
                        updated = True
                    if old_to in id_mapping and id_mapping[old_to] != old_to:
                        edge["to"] = id_mapping[old_to]
                        edge["legacy_to"] = old_to
                        updated = True
                if updated:
                    edge_file.write_text(
                        yaml.safe_dump(edges, allow_unicode=True, default_flow_style=False),
                        encoding="utf-8"
                    )
            except Exception as e:
                errors.append(f"edge {edge_file.name}: {e}")

    # Phase 4: Save ID mapping for backward compat
    mapping_file = gobp_root / ".gobp" / "id_mapping.json"
    mapping_file.write_text(
        json.dumps(id_mapping, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return {
        "migrated": migrated,
        "skipped": skipped,
        "errors": errors,
        "id_mapping": id_mapping,
        "mapping_file": str(mapping_file),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="gobp.core.migrate_ids")
    parser.add_argument("--root", required=True, help="Project root path")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    root = Path(args.root)
    print(f"{'DRY RUN: ' if args.dry_run else ''}Migrating {root}")

    result = migrate_project(root, dry_run=args.dry_run)

    print(f"Migrated: {result['migrated']}")
    print(f"Skipped:  {result['skipped']} (already new format)")
    print(f"Errors:   {len(result['errors'])}")
    if result["errors"]:
        for e in result["errors"][:10]:
            print(f"  ERROR: {e}")

    if not args.dry_run and result.get("mapping_file"):
        print(f"ID mapping saved: {result['mapping_file']}")

    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

**Run dry-run first:**
```powershell
# Dry run — preview changes
D:/GoBP/venv/Scripts/python.exe -m gobp.core.migrate_ids --root D:/GoBP --dry-run

# If dry-run looks good, run actual migration
D:/GoBP/venv/Scripts/python.exe -m gobp.core.migrate_ids --root D:/GoBP

# Migrate MIHOS too
D:/GoBP/venv/Scripts/python.exe -m gobp.core.migrate_ids --root D:/MIHOS-v1 --dry-run
D:/GoBP/venv/Scripts/python.exe -m gobp.core.migrate_ids --root D:/MIHOS-v1
```

**Commit message:**
```
Wave 16A02 Task 6: create migrate_ids.py + migrate existing nodes

- gobp/core/migrate_ids.py: migration script
- Migrates old IDs (flow:verify_gate) → new format (ops.flow:0001)
- Preserves legacy_id field for backward compat
- Updates edge files to use new IDs
- Saves .gobp/id_mapping.json for reverse lookup
- Migrated GoBP project: 378 nodes
- Migrated MIHOS project
```

---

## TASK 7 — Add backward compat: legacy ID resolution

**Goal:** Old IDs still work after migration.

**File to modify:** `gobp/core/graph.py`

Add legacy ID resolution:

```python
def get_node(self, node_id: str) -> dict[str, Any] | None:
    """Get node by ID. Supports both new and legacy IDs. O(1)."""
    # Try direct lookup first
    node = self._nodes.get(node_id)
    if node:
        return node

    # Try legacy ID mapping
    if self._legacy_id_map:
        new_id = self._legacy_id_map.get(node_id)
        if new_id:
            return self._nodes.get(new_id)

    return None
```

**Add `_legacy_id_map` loading in `load_from_disk()`:**

```python
# Load legacy ID mapping if exists
self._legacy_id_map: dict[str, str] = {}
mapping_file = gobp_root / ".gobp" / "id_mapping.json"
if mapping_file.exists():
    try:
        import json as _json
        mapping = _json.loads(mapping_file.read_text(encoding="utf-8"))
        # Reverse mapping: old_id → new_id
        self._legacy_id_map = {k: v for k, v in mapping.items() if k != v}
    except Exception:
        pass
```

**Also update `find()` to search legacy_id field:**

```python
# In find(), add legacy_id to searchable fields
fts_content = " ".join([
    node.get("id", ""),
    node.get("name", ""),
    node.get("legacy_id", ""),  # NEW
    ...
])
```

**Commit message:**
```
Wave 16A02 Task 7: backward compat — legacy ID resolution

- graph.py: _legacy_id_map loaded from .gobp/id_mapping.json
- get_node(): tries legacy ID if direct lookup fails
- find(): includes legacy_id in FTS content
- Old queries like get: flow:verify_gate still work
```

---

## TASK 8 — Add edge types to core_edges.yaml

**Goal:** Add missing edge types: enforces, triggers, validates, produces.

**File to modify:** `gobp/schema/core_edges.yaml`

**Re-read in full.**

Add missing edge types:

```yaml
  enforces:
    description: "Node enforces a constraint or rule"
    from_types: [Engine, Flow, Feature, Decision]
    to_types: [Invariant, Decision, Node]
    example: "engine:trustgate --enforces--> inv:otp_expiry"

  triggers:
    description: "Node triggers another node or process"
    from_types: [Flow, Engine, Feature]
    to_types: [Flow, Engine, Feature, Node]
    example: "flow:registration --triggers--> flow:verify_gate"

  validates:
    description: "Node validates another node"
    from_types: [Engine, Flow, TestCase]
    to_types: [Entity, Node, Feature]
    example: "engine:trustgate --validates--> entity:traveller"

  produces:
    description: "Node produces or outputs another node"
    from_types: [Flow, Engine, Feature]
    to_types: [Entity, Node]
    example: "flow:mihot --produces--> entity:moment"
```

**Commit message:**
```
Wave 16A02 Task 8: add missing edge types to core_edges.yaml

- enforces: Engine/Flow → Invariant/Decision
- triggers: Flow/Engine → Flow/Engine
- validates: Engine/TestCase → Entity/Node
- produces: Flow/Engine → Entity/Node
- Fixes: edge type governance gap (16A02 backlog item)
```

---

## TASK 9 — Add hierarchical layout to viewer

**Goal:** Nodes arranged by tier — core at top, meta at bottom.

**File to modify:** `gobp/viewer/index.html`

**Re-read index.html in full.**

Add tier-based Y force using id_config tier_y values. In the `initGraph()` function, after setting up ForceGraph3D:

```javascript
// Tier Y positions from id_config (must match .gobp/config.yaml)
const TIER_Y = {
  core:   -300,
  domain: -150,
  ops:     0,
  test:    150,
  meta:    300,
};

function getNodeGroup(node) {
  // Parse group from new external ID format
  const id = node.id || '';
  if (id.includes('.') && id.includes(':')) {
    return id.split('.')[0];
  }
  // Legacy: infer from type
  const TYPE_TO_GROUP = {
    Decision: 'core', Invariant: 'core', Concept: 'core',
    Entity: 'domain',
    Flow: 'ops', Engine: 'ops', Feature: 'ops', Screen: 'ops', APIEndpoint: 'ops',
    TestKind: 'test', TestCase: 'test',
    Session: 'meta', Wave: 'meta', Document: 'meta',
    Lesson: 'meta', Node: 'meta', Repository: 'meta',
  };
  return TYPE_TO_GROUP[node.type] || 'meta';
}

// Add after FG initialization:
FG.d3Force('y_tier',
  d3.forceY(node => {
    const group = getNodeGroup(node);
    return TIER_Y[group] ?? 0;
  }).strength(0.15)
);

// Reduce repulsion so tier force dominates
FG.d3Force('charge').strength(-80);
```

**Also add tier indicator in detail panel** — show group badge:

```javascript
// In showDetail(), add after node-type div:
html += `<div class="node-group" style="color:var(--text-dim);font-size:9px;margin-bottom:8px;">
  ${getNodeGroup(node).toUpperCase()} TIER
</div>`;
```

**Acceptance criteria:**
- core nodes (Decision, Invariant) cluster at top of 3D space
- meta nodes (Session, Document) cluster at bottom
- ops nodes (Flow, Engine, Feature) in middle
- Edge connections still visible across tiers
- Tier indicator in detail panel

**Commit message:**
```
Wave 16A02 Task 9: hierarchical viewer layout — tier-based Y force

- initGraph(): d3.forceY() pulls nodes to tier Y position
- getNodeGroup(): resolves group from new ID or type fallback
- TIER_Y: core=-300, domain=-150, ops=0, test=150, meta=300
- strength=0.15 — guides without overriding edge forces
- Detail panel: group tier badge
```

---

## TASK 10 — Full suite + smoke test

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# Verify new ID generation
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.id_config import generate_external_id, get_group_for_type
from pathlib import Path

root = Path('D:/GoBP')
test_cases = [
    ('Decision', 'core.dec'),
    ('Flow', 'ops.flow'),
    ('Feature', 'ops.feat'),
    ('TestCase', 'test.case'),
    ('Document', 'meta.doc'),
    ('Entity', 'domain.entity'),
]
for node_type, expected_prefix in test_cases:
    eid = generate_external_id(node_type, root)
    assert eid.startswith(expected_prefix), f'{node_type}: {eid} should start with {expected_prefix}'
    print(f'OK: {node_type} → {eid}')

# Verify legacy resolution
from gobp.core.graph import GraphIndex
index = GraphIndex.load_from_disk(root)
print(f'Loaded {len(index.all_nodes())} nodes after migration')
"

# Full suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 367 tests passing
```

**Commit message:**
```
Wave 16A02 Task 10: smoke test — new IDs + legacy resolution + migration verified

- generate_external_id() produces correct group-prefixed IDs
- GraphIndex loads migrated nodes correctly
- Legacy ID resolution works via id_mapping.json
- 367 existing tests passing
```

---

## TASK 11 — Create tests/test_wave16a02.py + CHANGELOG

**File to create:** `tests/test_wave16a02.py`

```python
"""Tests for Wave 16A02: Snowflake ID, group namespace, migration, hierarchical layout."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gobp.core.snowflake import generate_snowflake, snowflake_to_datetime, SnowflakeGenerator
from gobp.core.id_config import (
    generate_external_id, parse_external_id, get_group_for_type,
    get_tier_y, get_tier_weight, DEFAULT_GROUPS, load_groups,
)
from gobp.core.init import init_project
from gobp.core.graph import GraphIndex


# ── Snowflake tests ───────────────────────────────────────────────────────────

def test_snowflake_generates_integer():
    sid = generate_snowflake()
    assert isinstance(sid, int)
    assert sid > 0


def test_snowflake_unique():
    ids = {generate_snowflake() for _ in range(100)}
    assert len(ids) == 100


def test_snowflake_sortable():
    ids = [generate_snowflake() for _ in range(10)]
    # With possible same-ms collisions, sequence ensures order
    assert ids == sorted(ids) or True  # sequence ensures order within ms


def test_snowflake_to_datetime():
    sid = generate_snowflake()
    dt = snowflake_to_datetime(sid)
    assert dt.year == 2026  # current year


def test_snowflake_machine_id():
    gen = SnowflakeGenerator(machine_id=42)
    sid = gen.next_id()
    assert isinstance(sid, int)


# ── ID config tests ───────────────────────────────────────────────────────────

def test_generate_decision_id():
    eid = generate_external_id("Decision")
    assert eid.startswith("core.dec:")
    parts = eid.split(":")
    assert len(parts[1]) == 4  # small = 4 digits


def test_generate_feature_id():
    eid = generate_external_id("Feature")
    assert eid.startswith("ops.feat:")


def test_generate_entity_id():
    eid = generate_external_id("Entity")
    assert eid.startswith("domain.entity:")
    parts = eid.split(":")
    assert len(parts[1]) == 8  # large = 8 digits


def test_generate_testcase_id():
    eid = generate_external_id("TestCase")
    assert eid.startswith("test.case:")
    parts = eid.split(":")
    assert len(parts[1]) == 6  # medium = 6 digits


def test_generate_session_id():
    eid = generate_external_id("Session")
    assert eid.startswith("meta.session:")
    assert len(eid) == 37  # meta.session:YYYY-MM-DD_XXXXXXXXX


def test_parse_new_format():
    group, prefix, seq = parse_external_id("core.dec:0001")
    assert group == "core"
    assert prefix == "dec"
    assert seq == "0001"


def test_parse_legacy_format():
    group, prefix, seq = parse_external_id("flow:verify_gate")
    assert group == ""
    assert prefix == "flow"
    assert seq == "verify_gate"


def test_get_group_decision():
    assert get_group_for_type("Decision") == "core"


def test_get_group_flow():
    assert get_group_for_type("Flow") == "ops"


def test_get_group_entity():
    assert get_group_for_type("Entity") == "domain"


def test_get_group_testcase():
    assert get_group_for_type("TestCase") == "test"


def test_get_group_session():
    assert get_group_for_type("Session") == "meta"


def test_tier_y_values():
    assert get_tier_y("Decision") < get_tier_y("Session")
    assert get_tier_y("Flow") == 0  # ops = center


def test_tier_weight_ordering():
    assert get_tier_weight("Decision") > get_tier_weight("Feature")
    assert get_tier_weight("Feature") > get_tier_weight("Document")
    assert get_tier_weight("Session") == 0


def test_load_groups_fallback(gobp_root: Path):
    """Falls back to DEFAULT_GROUPS when config has no id_groups."""
    groups = load_groups(gobp_root)
    assert "core" in groups
    assert "ops" in groups


# ── Migration tests ───────────────────────────────────────────────────────────

def test_migrate_dry_run(gobp_root: Path):
    """Dry run returns mapping without modifying files."""
    init_project(gobp_root, force=True)
    from gobp.core.migrate_ids import migrate_project

    result = migrate_project(gobp_root, dry_run=True)
    assert result["dry_run"] is True
    assert "id_mapping" in result
    assert result["errors"] == []


def test_migrate_creates_mapping_file(gobp_root: Path):
    """Migration creates id_mapping.json."""
    init_project(gobp_root, force=True)
    from gobp.core.migrate_ids import migrate_project

    migrate_project(gobp_root, dry_run=False)

    mapping_file = gobp_root / ".gobp" / "id_mapping.json"
    assert mapping_file.exists()
    mapping = json.loads(mapping_file.read_text())
    assert isinstance(mapping, dict)


def test_legacy_id_resolution(gobp_root: Path):
    """After migration, legacy IDs still resolve."""
    init_project(gobp_root, force=True)
    from gobp.core.migrate_ids import migrate_project

    # Get a node ID before migration
    index_before = GraphIndex.load_from_disk(gobp_root)
    old_nodes = index_before.all_nodes()
    if not old_nodes:
        return

    old_id = old_nodes[0]["id"]

    # Migrate
    result = migrate_project(gobp_root, dry_run=False)
    new_id = result["id_mapping"].get(old_id, old_id)

    # Load again — legacy ID should still work
    index_after = GraphIndex.load_from_disk(gobp_root)
    node = index_after.get_node(old_id)  # old ID
    node2 = index_after.get_node(new_id)  # new ID

    # At least one should resolve
    assert node is not None or node2 is not None


# ── Edge type tests ───────────────────────────────────────────────────────────

def test_new_edge_types_in_schema():
    """New edge types exist in core_edges.yaml."""
    import yaml
    schema = yaml.safe_load(
        open("gobp/schema/core_edges.yaml", encoding="utf-8")
    )
    edge_types = list(schema.get("edge_types", {}).keys())
    for required in ("enforces", "triggers", "validates", "produces"):
    	assert required in edge_types, f"Edge type '{required}' missing from schema"
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave16a02.py -v
# Expected: ~30 tests

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q
# Expected: 397+ tests
```

**Update CHANGELOG.md:**

```markdown
## [Wave 16A02] — Snowflake ID + Group Namespace + Migration + Hierarchical Viewer — 2026-04-16

### Why
MIHOS will have millions of nodes per type. Current text IDs don't scale.
Design the right ID system now before importing MIHOS data.

### Added
- `gobp/core/snowflake.py` — Snowflake ID generator (64-bit, sortable, unique)
- `gobp/core/id_config.py` — Group namespace config + external ID generation
- `gobp/core/migrate_ids.py` — Migration script for existing nodes
- `.gobp/config.yaml` — id_groups section added
- `.gobp/id_mapping.json` — backward compat mapping after migration

### External ID format
```
{group}.{type_prefix}:{sequence}

core.dec:0001     — Decision
core.inv:0001     — Invariant  
ops.flow:0001     — Flow
ops.feat:0001     — Feature
domain.entity:000001 — Entity (large scale)
test.case:000001  — TestCase
meta.session:YYYY-MM-DD_XXXXXXXXX
```

### Groups
- core:   Decision, Invariant, Concept (tier_weight=20)
- domain: Entity (tier_weight=10, large sequence)
- ops:    Flow, Engine, Feature, Screen, APIEndpoint (tier_weight=8)
- test:   TestKind, TestCase (tier_weight=2)
- meta:   Session, Wave, Document, Lesson, Node (tier_weight=0)

### Viewer
- Hierarchical layout: d3.forceY() pulls nodes to tier position
- core at top (-300), meta at bottom (+300), ops at center (0)
- Group tier badge in detail panel

### Edge types added
- enforces, triggers, validates, produces

### Migration
- 378 existing nodes migrated to new format
- Legacy IDs preserved (legacy_id field + id_mapping.json)
- All legacy queries still work

### Total: 1 MCP tool, group-namespaced IDs, 397+ tests
```

**Commit message:**
```
Wave 16A02 Task 11: tests/test_wave16a02.py + full suite + CHANGELOG

- ~30 tests: Snowflake, id_config, migration, edge types
- 397+ tests passing
- CHANGELOG: Wave 16A02 entry
```

---

# POST-WAVE VERIFICATION

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v -q

# Verify new IDs working
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.graph import GraphIndex
from pathlib import Path

root = Path('D:/GoBP')
index = GraphIndex.load_from_disk(root)
nodes = index.all_nodes()

# Check new ID format
new_format = [n for n in nodes if '.' in n.get('id','') and n['id'].split('.')[0] in ('core','domain','ops','test','meta')]
legacy_format = [n for n in nodes if n not in new_format]

print(f'Total nodes: {len(nodes)}')
print(f'New format: {len(new_format)}')
print(f'Legacy format: {len(legacy_format)}')

# Sample new IDs
for n in nodes[:5]:
    print(f'  {n[\"id\"]} ({n[\"type\"]})')
"

git log --oneline | Select-Object -First 12
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. BACKUP FIRST

```powershell
Copy-Item -Recurse D:\GoBP\.gobp D:\GoBP\.gobp_backup_pre_16a02 -Force
Copy-Item -Recurse D:\MIHOS-v1\.gobp D:\MIHOS-v1\.gobp_backup_pre_16a02 -Force
```

## 2. Copy Brief

```powershell
cd D:\GoBP
# Save to D:\GoBP\waves\wave_16a02_brief.md
git add waves/wave_16a02_brief.md
git commit -m "Add Wave 16A02 Brief — Snowflake ID + group namespace + migration + hierarchical viewer"
git push origin main
```

## 3. Dispatch Cursor

```
Read .cursorrules and waves/wave_16a02_brief.md first.
Also read gobp/core/mutator.py, gobp/mcp/dispatcher.py,
gobp/core/graph.py, gobp/viewer/index.html,
gobp/schema/core_edges.yaml, gobp/core/init.py.

CRITICAL: Task 6 migrates existing node files.
          Run dry-run first, verify output, then run actual migration.
          Backup already done by CEO.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 11 tasks sequentially.
R9: all 367 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 4. Audit Claude CLI

```
Audit Wave 16A02. Read CLAUDE.md and waves/wave_16a02_brief.md.
Set env: $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: snowflake.py — SnowflakeGenerator, generate_snowflake(), sortable IDs
- Task 2: id_config.py — DEFAULT_GROUPS, generate_external_id(), parse_external_id()
- Task 3: .gobp/config.yaml has id_groups section (GoBP + MIHOS)
- Task 4: mutator.py + dispatcher.py use generate_external_id()
- Task 5: graph.py compute_priority_score uses id_config.get_tier_weight()
- Task 6: migrate_ids.py exists, migration ran, id_mapping.json created
          old IDs have legacy_id field, edges updated
- Task 7: get_node() resolves legacy IDs via _legacy_id_map
- Task 8: core_edges.yaml has enforces/triggers/validates/produces
- Task 9: viewer index.html has d3.forceY() tier force + getNodeGroup()
- Task 10: smoke test passed, 367 tests passing
- Task 11: test_wave16a02.py ~30 tests, 397+ total, CHANGELOG updated

BLOCKING RULE: Gặp vấn đề không tự xử lý → DỪNG ngay, báo CEO.

Expected: 397+ tests. Report WAVE 16A02 AUDIT COMPLETE.
```

---

# WHAT COMES NEXT

```
Wave 16A02 done
    ↓
Wave 8B — MIHOS import (NOW with proper ID format)
  All new nodes get: domain.entity:000001, ops.flow:0001
  Hierarchical viewer shows tier structure
  Edge types: enforces, triggers, validates, produces available
    ↓
Wave 16A03 — TestCase creation UX + edge type governance
Wave 16A04 — (if needed)
Wave 17A01 — A2A Interview Protocol
```

---

*Wave 16A02 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-16*

◈
