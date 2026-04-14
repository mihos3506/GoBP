# WAVE 0 BRIEF — REPO BOOTSTRAP

**Wave:** 0
**Title:** Repo Bootstrap — Package Skeleton + Core Schemas + Templates
**Author:** CTO Chat (Claude Opus 4.6)
**Date:** 2026-04-14
**For:** Cursor (Tier 1 Dev), Claude CLI (Tier 3 Audit)
**Status:** READY FOR EXECUTION
**Task count:** 9 atomic tasks
**Estimated effort:** 1.5-2 hours total

---

## CONTEXT

This is the first wave of GoBP development. It establishes the repository skeleton: Python package structure, dependencies, core schema files, and templates. **No business logic yet** — code logic begins in Wave 1.

Wave 0 is intentionally small. It verifies the 3-tier pipeline (Cursor dev → Qodo test → Claude CLI audit) works before tackling harder waves.

**Pipeline rule:** Each task below is atomic. Each task = 1 git commit. Cursor executes, Claude CLI audits, commit only after audit passes. Do NOT batch tasks into single commit.

**Required reading before starting any task:**
- `CLAUDE.md`
- `.cursorrules`
- `CHARTER.md`
- `docs/VISION.md`
- `docs/ARCHITECTURE.md`
- `docs/SCHEMA.md` (heavy reference for Task 5 and 6)

---

## GOALS

By end of Wave 0:
1. Python package `gobp/` exists with stub modules
2. `pyproject.toml` + `requirements.txt` declare dependencies
3. Virtual environment works
4. Core schema YAML files valid
5. 6 node templates exist
6. Smoke tests pass
7. README install section added
8. 9 commits total (1 per task)

**NOT in Wave 0:**
- GraphIndex class implementation (Wave 1)
- MCP server implementation (Wave 3)
- CLI command implementation (Wave 4)
- Any business logic

---

## PREREQUISITES (verify before Task 1)

Run in PowerShell at `D:\GoBP\`:

```powershell
# Python 3.10+
python --version

# Git
git --version

# In correct folder
pwd
# Expected: D:\GoBP

# Remote correct
git remote -v
# Expected: origin https://github.com/mihos3506/GoBP.git

# On main branch
git branch --show-current
# Expected: main

# Clean tree
git status
# Expected: nothing to commit, working tree clean
```

If any check fails, STOP and escalate.

---

# TASKS

## TASK 1 — Create Python package skeleton

**Goal:** Create empty package structure with stub files.

**Scope:**
- Create folders: `gobp/`, `gobp/core/`, `gobp/schema/`, `gobp/mcp/`, `gobp/mcp/tools/`, `gobp/cli/`, `gobp/templates/`, `tests/`
- Create `__init__.py` in each package folder (8 files)
- Create stub files (docstring only, no code yet)

**Files to create:**

```
gobp/__init__.py
gobp/core/__init__.py
gobp/core/graph.py          (stub)
gobp/core/loader.py         (stub)
gobp/core/validator.py      (stub)
gobp/core/mutator.py        (stub)
gobp/core/history.py        (stub)
gobp/schema/__init__.py
gobp/mcp/__init__.py
gobp/mcp/server.py          (stub)
gobp/mcp/tools/__init__.py
gobp/mcp/tools/read.py      (stub)
gobp/mcp/tools/write.py     (stub)
gobp/mcp/tools/import_.py   (stub)
gobp/mcp/tools/maintain.py  (stub)
gobp/cli/__init__.py
gobp/cli/__main__.py        (basic entry)
gobp/cli/commands.py        (stub)
tests/__init__.py           (empty)
```

**Content patterns:**

Every `__init__.py`:
```python
"""<package name> — <short description>"""

__version__ = "0.1.0"
```

Every stub `.py` file (e.g., `graph.py`):
```python
"""GoBP core graph index.

This module will contain the GraphIndex class.
Implementation begins in Wave 1.
"""
```

Special `gobp/cli/__main__.py`:
```python
"""GoBP CLI entry point.

Implementation begins in Wave 4.
"""


def main() -> None:
    """Entry point for the gobp CLI command."""
    print("GoBP CLI — not yet implemented")


if __name__ == "__main__":
    main()
```

**Acceptance criteria:**
- All 19 files exist at specified paths
- All files are valid Python (no syntax errors)
- `python -c "import gobp"` runs without error (after Task 2 when dependencies installed)

**Commit message:**
```
Wave 0 Task 1: create Python package skeleton

- gobp/ package with 5 subpackages (core, schema, mcp, cli, templates)
- 8 __init__.py files
- 11 stub .py files with module docstrings
- tests/ folder with empty __init__.py

All files are empty stubs. Implementation begins in Wave 1+.
```

---

## TASK 2 — Create pyproject.toml

**Goal:** Define Python package metadata and dependencies.

**Scope:**
- Create `pyproject.toml` at repo root
- Declare dependencies: `mcp`, `pyyaml`
- Declare dev dependencies: `pytest`, `pytest-asyncio`
- Configure setuptools package discovery

**File to create:** `D:\GoBP\pyproject.toml`

**Content (exact):**

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "gobp"
version = "0.1.0"
description = "Graph of Brainstorm Project — long-term memory for AI agents"
readme = "README.md"
requires-python = ">=3.10"
authors = [
    { name = "GoBP Authors" }
]
keywords = ["mcp", "knowledge-graph", "ai-memory", "ai-agents"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Operating System :: OS Independent",
]

dependencies = [
    "mcp>=0.9.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
]

[project.scripts]
gobp = "gobp.cli.__main__:main"

[tool.setuptools.packages.find]
include = ["gobp*"]
exclude = ["tests*", "examples*"]

[tool.setuptools.package-data]
gobp = ["schema/*.yaml", "templates/*.md"]
```

**Acceptance criteria:**
- File exists at `D:\GoBP\pyproject.toml`
- Valid TOML (parseable)
- Verify: `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` (no errors)

**Commit message:**
```
Wave 0 Task 2: create pyproject.toml

- Package metadata: name, version, description, authors
- Dependencies: mcp>=0.9.0, pyyaml>=6.0
- Dev dependencies: pytest>=7.0, pytest-asyncio>=0.21
- Console script: gobp -> gobp.cli.__main__:main
- Package data: schema/*.yaml, templates/*.md

Sets dependency baseline for GoBP v1.
```

---

## TASK 3 — Create requirements files

**Goal:** Create pip-installable requirements files for quick install.

**Files to create:**

`D:\GoBP\requirements.txt`:
```
mcp>=0.9.0
pyyaml>=6.0
```

`D:\GoBP\requirements-dev.txt`:
```
-r requirements.txt
pytest>=7.0
pytest-asyncio>=0.21
```

**Acceptance criteria:**
- Both files exist
- Correct content
- `pip install --dry-run -r requirements.txt` would succeed (do not actually install yet)

**Commit message:**
```
Wave 0 Task 3: create requirements files

- requirements.txt: runtime deps (mcp, pyyaml)
- requirements-dev.txt: adds pytest, pytest-asyncio

Both files consistent with pyproject.toml dependencies.
```

---

## TASK 4 — Set up virtual environment and install

**Goal:** Create venv, install dependencies, verify imports work.

**Commands to run:**

```powershell
# Create venv
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# If ExecutionPolicy error, run once:
# Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Verify venv active (prompt should show (venv))

# Upgrade pip
python -m pip install --upgrade pip

# Install dev deps + package in editable mode
pip install -r requirements-dev.txt
pip install -e .

# Verify installations
python -c "import gobp; print(gobp.__version__)"
# Expected: 0.1.0

python -c "import yaml; print(yaml.__version__)"
# Expected: a version string

python -c "import mcp; print('mcp OK')"
# Expected: mcp OK

python -c "import pytest; print('pytest OK')"
# Expected: pytest OK
```

**Acceptance criteria:**
- `venv/` folder exists
- `gobp.__version__` returns "0.1.0"
- All 4 import checks succeed
- `pip list` shows `gobp 0.1.0` in editable mode

**No files to create, but the venv setup is the "artifact" of this task.**

**Commit message:**
```
Wave 0 Task 4: set up virtual environment

No files committed (venv/ is gitignored).

Actions performed:
- Created venv at venv/
- Upgraded pip
- Installed mcp, pyyaml, pytest, pytest-asyncio
- Installed gobp in editable mode
- Verified all imports work

Environment ready for development.
```

**Note:** This task has no files to stage. Commit is empty (`git commit --allow-empty`) for audit trail purposes.

---

## TASK 5 — Create core node schema YAML

**Goal:** Translate `docs/SCHEMA.md` node type definitions into machine-readable YAML.

**File to create:** `gobp/schema/core_nodes.yaml`

**Required reading:** `docs/SCHEMA.md` sections defining Node, Idea, Decision, Session, Document, Lesson.

**Content (exact — paste verbatim):**

```yaml
# GoBP Core Node Types
# Reference: docs/SCHEMA.md section 2
# Schema version: 1.0

schema_version: "1.0"
schema_name: "gobp_core"

node_types:

  Node:
    description: "Generic container for any entity, feature, tool, concept"
    id_prefix: "node"
    parent: null

    required:
      id:
        type: "str"
        pattern: "^node:[a-z][a-z0-9_]*$"
      type:
        type: "str"
      name:
        type: "str"
      status:
        type: "enum"
        enum_values: ["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"]
      created:
        type: "timestamp"
      updated:
        type: "timestamp"

    optional:
      subtype:
        type: "str"
      description:
        type: "str"
      tags:
        type: "list[str]"
        default: []
      custom_fields:
        type: "dict"
        default: {}

    constraints:
      - "created <= updated"

  Idea:
    description: "Unstructured brainstorm captured from conversation"
    id_prefix: "idea"
    parent: null

    required:
      id:
        type: "str"
        pattern: "^idea:i[0-9]{3,}$"
      type:
        type: "str"
        enum_values: ["Idea"]
      raw_quote:
        type: "str"
      interpretation:
        type: "str"
      subject:
        type: "str"
      maturity:
        type: "enum"
        enum_values: ["RAW", "REFINED", "DISCUSSED", "LOCKED", "DEPRECATED"]
      confidence:
        type: "enum"
        enum_values: ["low", "medium", "high"]
      session_id:
        type: "node_ref"
      created:
        type: "timestamp"
      updated:
        type: "timestamp"

    optional:
      supersedes:
        type: "node_ref"
      context_notes:
        type: "str"
      ceo_verified:
        type: "bool"
        default: false
      status:
        type: "enum"
        enum_values: ["ACTIVE", "SUPERSEDED"]
        default: "ACTIVE"

  Decision:
    description: "Locked authoritative knowledge"
    id_prefix: "dec"
    parent: null

    required:
      id:
        type: "str"
        pattern: "^dec:d[0-9]{3,}$"
      type:
        type: "str"
        enum_values: ["Decision"]
      topic:
        type: "str"
      what:
        type: "str"
      why:
        type: "str"
      status:
        type: "enum"
        enum_values: ["LOCKED", "SUPERSEDED", "WITHDRAWN"]
      locked_at:
        type: "timestamp"
      locked_by:
        type: "list[str]"
      session_id:
        type: "node_ref"
      created:
        type: "timestamp"
      updated:
        type: "timestamp"

    optional:
      alternatives_considered:
        type: "list[dict]"
        default: []
      risks:
        type: "list[str]"
      blocks:
        type: "list[node_ref]"
      supersedes:
        type: "node_ref"
      related_ideas:
        type: "list[node_ref]"

  Session:
    description: "Record of one AI working session"
    id_prefix: "session"
    parent: null

    required:
      id:
        type: "str"
        pattern: "^session:[0-9]{4}-[0-9]{2}-[0-9]{2}.*$"
      type:
        type: "str"
        enum_values: ["Session"]
      actor:
        type: "str"
      started_at:
        type: "timestamp"
      goal:
        type: "str"
      status:
        type: "enum"
        enum_values: ["IN_PROGRESS", "COMPLETED", "INTERRUPTED", "FAILED"]
      created:
        type: "timestamp"
      updated:
        type: "timestamp"

    optional:
      ended_at:
        type: "timestamp"
      outcome:
        type: "str"
      nodes_touched:
        type: "list[node_ref]"
        default: []
      decisions_locked:
        type: "list[node_ref]"
        default: []
      pending:
        type: "list[str]"
        default: []
      tokens_used:
        type: "int"
      human_present:
        type: "bool"
      handoff_notes:
        type: "str"

  Document:
    description: "Pointer to external doc file with metadata"
    id_prefix: "doc"
    parent: null

    required:
      id:
        type: "str"
        pattern: "^doc:.+$"
      type:
        type: "str"
        enum_values: ["Document"]
      name:
        type: "str"
      source_path:
        type: "str"
      content_hash:
        type: "str"
        pattern: "^sha256:[a-f0-9]{64}$"
      registered_at:
        type: "timestamp"
      last_verified:
        type: "timestamp"
      created:
        type: "timestamp"
      updated:
        type: "timestamp"

    optional:
      sections:
        type: "list[dict]"
        default: []
      tags:
        type: "list[str]"
        default: []
      owned_by:
        type: "str"
      phase:
        type: "int"
      status:
        type: "enum"
        enum_values: ["ACTIVE", "STALE", "MISSING", "DEPRECATED"]
        default: "ACTIVE"

  Lesson:
    description: "Something learned from experience"
    id_prefix: "lesson"
    parent: null

    required:
      id:
        type: "str"
        pattern: "^lesson:ll[0-9]{3,}$"
      type:
        type: "str"
        enum_values: ["Lesson"]
      title:
        type: "str"
      trigger:
        type: "str"
      what_happened:
        type: "str"
      why_it_matters:
        type: "str"
      mitigation:
        type: "str"
      severity:
        type: "enum"
        enum_values: ["low", "medium", "high", "critical"]
      captured_in_session:
        type: "node_ref"
      created:
        type: "timestamp"
      updated:
        type: "timestamp"

    optional:
      related_nodes:
        type: "list[node_ref]"
        default: []
      related_ideas:
        type: "list[node_ref]"
        default: []
      verified_count:
        type: "int"
        default: 1
      last_applied:
        type: "timestamp"
      tags:
        type: "list[str]"
        default: []
```

**Acceptance criteria:**
- File exists at `gobp/schema/core_nodes.yaml`
- Valid YAML: `python -c "import yaml; yaml.safe_load(open('gobp/schema/core_nodes.yaml'))"` (no errors)
- Contains exactly 6 node types: Node, Idea, Decision, Session, Document, Lesson
- Every type has `required` and (if applicable) `optional` sections

**Commit message:**
```
Wave 0 Task 5: create core node schema YAML

- gobp/schema/core_nodes.yaml: 6 node types defined
  - Node (generic container)
  - Idea (brainstorm capture)
  - Decision (locked knowledge)
  - Session (AI work session)
  - Document (external doc pointer)
  - Lesson (learned experience)

Translated from docs/SCHEMA.md. Used by loader/validator in Wave 1.
```

---

## TASK 6 — Create core edge schema YAML

**Goal:** Translate `docs/SCHEMA.md` edge type definitions into YAML.

**File to create:** `gobp/schema/core_edges.yaml`

**Content (exact):**

```yaml
# GoBP Core Edge Types
# Reference: docs/SCHEMA.md section 3
# Schema version: 1.0

schema_version: "1.0"
schema_name: "gobp_core"

edge_types:

  relates_to:
    description: "Generic connection between two nodes"
    directional: false
    cardinality: "many_to_many"
    allowed_node_types: ["all"]

    required:
      from:
        type: "node_ref"
      to:
        type: "node_ref"
      type:
        type: "str"
        enum_values: ["relates_to"]

    optional:
      reason:
        type: "str"

  supersedes:
    description: "New version replaces old version"
    directional: true
    cardinality: "one_to_one"
    allowed_node_types: ["Idea", "Decision", "Node"]

    required:
      from:
        type: "node_ref"
      to:
        type: "node_ref"
      type:
        type: "str"
        enum_values: ["supersedes"]

    optional:
      reason:
        type: "str"
      superseded_at:
        type: "timestamp"

  implements:
    description: "Concrete implementation of abstract spec"
    directional: true
    cardinality: "many_to_many"
    allowed_node_types: ["Node->Decision", "Node->Node"]

    required:
      from:
        type: "node_ref"
      to:
        type: "node_ref"
      type:
        type: "str"
        enum_values: ["implements"]

    optional:
      partial:
        type: "bool"
        default: false
      notes:
        type: "str"

  discovered_in:
    description: "Node was created in this session"
    directional: true
    cardinality: "many_to_one"
    allowed_node_types: ["all->Session"]

    required:
      from:
        type: "node_ref"
      to:
        type: "node_ref"
      type:
        type: "str"
        enum_values: ["discovered_in"]

    optional:
      position_in_session:
        type: "int"

  references:
    description: "Node points to document section for detail"
    directional: true
    cardinality: "many_to_many"
    allowed_node_types: ["all->Document"]

    required:
      from:
        type: "node_ref"
      to:
        type: "node_ref"
      type:
        type: "str"
        enum_values: ["references"]

    optional:
      section:
        type: "str"
      lines:
        type: "list[int]"
```

**Acceptance criteria:**
- File exists at `gobp/schema/core_edges.yaml`
- Valid YAML
- Contains exactly 5 edge types: relates_to, supersedes, implements, discovered_in, references

**Commit message:**
```
Wave 0 Task 6: create core edge schema YAML

- gobp/schema/core_edges.yaml: 5 edge types defined
  - relates_to (generic connection)
  - supersedes (versioning)
  - implements (concrete -> spec)
  - discovered_in (node -> session)
  - references (node -> document)

Translated from docs/SCHEMA.md. Used by validator in Wave 1.
```

---

## TASK 7 — Create 6 node templates

**Goal:** Create markdown templates for humans/AI to use when creating new nodes manually.

**Files to create (6 files):**

### `gobp/templates/node.md`

```markdown
---
id: node:CHANGEME
type: Node
subtype: ""
name: "CHANGEME"
status: DRAFT
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
description: ""
tags: []
---

## Context

(Describe what this node represents and why it exists.)

## Notes

(Any additional notes for human readers or AI agents.)
```

### `gobp/templates/idea.md`

```markdown
---
id: idea:iCHANGE
type: Idea
subject: "CHANGEME"
raw_quote: ""
interpretation: ""
maturity: RAW
confidence: low
session_id: session:CHANGEME
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
ceo_verified: false
---

## Context

(Surrounding conversation context if relevant.)

## Related

(Links to related ideas, decisions, or features.)
```

### `gobp/templates/decision.md`

```markdown
---
id: dec:dCHANGE
type: Decision
topic: "CHANGEME"
what: ""
why: ""
status: LOCKED
locked_at: 2026-04-14T00:00:00
locked_by: ["CEO", "AI-WITNESS"]
session_id: session:CHANGEME
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
alternatives_considered: []
risks: []
related_ideas: []
---

## Context

(How this decision came about.)

## Implementation notes

(Specifics relevant to building things based on this decision.)
```

### `gobp/templates/session.md`

```markdown
---
id: session:YYYY-MM-DD_slug
type: Session
actor: "CHANGEME"
goal: "CHANGEME"
status: IN_PROGRESS
started_at: 2026-04-14T00:00:00
ended_at: null
outcome: ""
nodes_touched: []
decisions_locked: []
pending: []
human_present: true
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
---

## Goal

(What this session aimed to accomplish.)

## Outcome

(What actually happened. Filled in at session end.)

## Handoff notes

(Context for the next session to pick up.)
```

### `gobp/templates/document.md`

```markdown
---
id: doc:CHANGEME
type: Document
name: "CHANGEME"
source_path: "path/to/file.md"
content_hash: "sha256:CHANGEME"
registered_at: 2026-04-14T00:00:00
last_verified: 2026-04-14T00:00:00
sections: []
tags: []
status: ACTIVE
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
---

## Purpose

(What this document is and why it is registered.)

## Related nodes

(Which nodes reference this document.)
```

### `gobp/templates/lesson.md`

```markdown
---
id: lesson:llCHANGE
type: Lesson
title: "CHANGEME"
trigger: ""
what_happened: ""
why_it_matters: ""
mitigation: ""
severity: medium
captured_in_session: session:CHANGEME
verified_count: 1
related_nodes: []
related_ideas: []
tags: []
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
---

## Context

(Background on when this lesson was learned.)

## Anti-pattern to recognize

(Specific signs that this lesson applies.)
```

**Acceptance criteria:**
- All 6 files exist
- Each has valid YAML frontmatter (between `---` lines)
- Frontmatter matches schema defined in `core_nodes.yaml`

**Commit message:**
```
Wave 0 Task 7: create 6 node templates

- gobp/templates/node.md
- gobp/templates/idea.md
- gobp/templates/decision.md
- gobp/templates/session.md
- gobp/templates/document.md
- gobp/templates/lesson.md

Each template has YAML frontmatter with all required fields + placeholder values.
Used by humans/AI when creating new nodes manually.
```

---

## TASK 8 — Write smoke tests

**Goal:** Create tests that verify Wave 0 deliverables exist and are valid. No business logic tests yet.

**File to create:** `tests/test_smoke.py`

**Content (exact):**

```python
"""Smoke tests for GoBP Wave 0 deliverables.

These tests verify:
1. The gobp package can be imported
2. All stub modules exist
3. Schema YAML files are valid and complete
4. Templates exist with correct frontmatter

They do NOT test business logic — that begins in Wave 1.
"""

import importlib
from pathlib import Path

import pytest
import yaml


# =============================================================================
# Package import tests
# =============================================================================


def test_gobp_package_importable():
    """The top-level gobp package can be imported."""
    import gobp
    assert gobp.__version__ == "0.1.0"


def test_core_modules_importable():
    """All core submodules can be imported."""
    modules = [
        "gobp.core.graph",
        "gobp.core.loader",
        "gobp.core.validator",
        "gobp.core.mutator",
        "gobp.core.history",
    ]
    for module_name in modules:
        importlib.import_module(module_name)


def test_mcp_modules_importable():
    """All MCP submodules can be imported."""
    modules = [
        "gobp.mcp.server",
        "gobp.mcp.tools.read",
        "gobp.mcp.tools.write",
        "gobp.mcp.tools.import_",
        "gobp.mcp.tools.maintain",
    ]
    for module_name in modules:
        importlib.import_module(module_name)


def test_cli_modules_importable():
    """CLI module can be imported and has main function."""
    import gobp.cli.__main__
    assert callable(gobp.cli.__main__.main)


# =============================================================================
# Schema file tests
# =============================================================================


def get_schema_dir() -> Path:
    """Return the path to the gobp/schema/ folder."""
    import gobp
    return Path(gobp.__file__).parent / "schema"


def test_core_nodes_yaml_exists():
    """core_nodes.yaml exists."""
    schema_file = get_schema_dir() / "core_nodes.yaml"
    assert schema_file.exists(), f"Missing: {schema_file}"


def test_core_edges_yaml_exists():
    """core_edges.yaml exists."""
    schema_file = get_schema_dir() / "core_edges.yaml"
    assert schema_file.exists(), f"Missing: {schema_file}"


def test_core_nodes_yaml_valid():
    """core_nodes.yaml is valid YAML with correct structure."""
    schema_file = get_schema_dir() / "core_nodes.yaml"
    with open(schema_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "schema_version" in data
    assert data["schema_version"] == "1.0"
    assert "node_types" in data

    expected_types = {"Node", "Idea", "Decision", "Session", "Document", "Lesson"}
    actual_types = set(data["node_types"].keys())
    assert actual_types == expected_types, f"Expected {expected_types}, got {actual_types}"


def test_core_edges_yaml_valid():
    """core_edges.yaml is valid YAML with correct structure."""
    schema_file = get_schema_dir() / "core_edges.yaml"
    with open(schema_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "schema_version" in data
    assert data["schema_version"] == "1.0"
    assert "edge_types" in data

    expected_types = {"relates_to", "supersedes", "implements", "discovered_in", "references"}
    actual_types = set(data["edge_types"].keys())
    assert actual_types == expected_types, f"Expected {expected_types}, got {actual_types}"


def test_every_node_type_has_required_fields():
    """Each node type declares required fields."""
    schema_file = get_schema_dir() / "core_nodes.yaml"
    with open(schema_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for type_name, type_def in data["node_types"].items():
        assert "required" in type_def, f"{type_name} missing 'required' section"
        assert "id" in type_def["required"], f"{type_name} missing required 'id'"
        assert "created" in type_def["required"], f"{type_name} missing required 'created'"


def test_every_edge_type_has_from_to():
    """Each edge type has from and to fields."""
    schema_file = get_schema_dir() / "core_edges.yaml"
    with open(schema_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for type_name, type_def in data["edge_types"].items():
        assert "required" in type_def, f"{type_name} missing 'required' section"
        assert "from" in type_def["required"], f"{type_name} missing 'from'"
        assert "to" in type_def["required"], f"{type_name} missing 'to'"


# =============================================================================
# Template file tests
# =============================================================================


def get_templates_dir() -> Path:
    """Return the path to the gobp/templates/ folder."""
    import gobp
    return Path(gobp.__file__).parent / "templates"


def test_all_templates_exist():
    """All 6 template files exist."""
    expected = ["node.md", "idea.md", "decision.md", "session.md", "document.md", "lesson.md"]
    templates_dir = get_templates_dir()

    for template_name in expected:
        template_file = templates_dir / template_name
        assert template_file.exists(), f"Missing template: {template_file}"


def test_templates_have_yaml_frontmatter():
    """Each template starts and ends YAML frontmatter correctly."""
    templates_dir = get_templates_dir()

    for template_file in templates_dir.glob("*.md"):
        content = template_file.read_text(encoding="utf-8")
        assert content.startswith("---\n"), f"{template_file.name} missing frontmatter start"
        # Find closing ---
        lines = content.split("\n")
        closing_found = False
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                closing_found = True
                break
        assert closing_found, f"{template_file.name} missing frontmatter end"


def test_templates_frontmatter_parseable():
    """Each template's frontmatter is valid YAML."""
    templates_dir = get_templates_dir()

    for template_file in templates_dir.glob("*.md"):
        content = template_file.read_text(encoding="utf-8")
        # Extract frontmatter between --- markers
        parts = content.split("---\n", 2)
        assert len(parts) >= 3, f"{template_file.name} frontmatter malformed"
        frontmatter_text = parts[1]
        # Should parse as YAML without error
        data = yaml.safe_load(frontmatter_text)
        assert data is not None
        assert "id" in data, f"{template_file.name} frontmatter missing 'id'"
        assert "type" in data, f"{template_file.name} frontmatter missing 'type'"
```

**Run tests:**
```powershell
# With venv activated
pytest tests/test_smoke.py -v
```

**Acceptance criteria:**
- All 13 tests pass
- 0 failures, 0 errors, 0 warnings

If any test fails, debug and fix per `.cursorrules` Phase 5.

**Commit message:**
```
Wave 0 Task 8: write smoke tests

- tests/test_smoke.py: 13 tests verifying Wave 0 deliverables
  - Package imports (4 tests)
  - Schema YAML existence + structure (4 tests)
  - Schema field requirements (2 tests)
  - Template existence + frontmatter (3 tests)

All tests pass. No business logic tested (that begins Wave 1).
```

---

## TASK 9 — Add install section to README

**Goal:** Document how to install GoBP for development.

**File to modify:** `README.md` (existing file at repo root)

**Rules:**
- Do NOT delete any existing content
- Do NOT modify existing sections
- ADD a new section in the correct location

**Where to insert:**
Find the section "## 🛠️ Quick Start" (or equivalent near the top). Insert the new "## 🛠️ Installation (Development)" section AFTER Quick Start but BEFORE any "Core Concepts" or similar section.

**Section to add:**

```markdown
## 🛠️ Installation (Development)

### Prerequisites
- Python 3.10 or higher
- Git
- A virtual environment tool (venv ships with Python)

### Setup

\`\`\`bash
git clone https://github.com/mihos3506/GoBP.git
cd GoBP

# Create and activate virtual environment
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e .
pip install -r requirements-dev.txt

# Verify
python -c "import gobp; print(gobp.__version__)"
# Should print: 0.1.0

# Run smoke tests
pytest tests/test_smoke.py -v
\`\`\`

After Wave 0, the package is importable but has no functionality yet. Functionality begins in Wave 1.
```

**Note:** In the markdown above, replace `\`\`\`bash` with triple backticks followed by `bash` (the backslashes are escapes for this Brief file only — in the actual README, use real backticks).

**Acceptance criteria:**
- README.md still has all original content (check with `git diff`)
- New "Installation (Development)" section added at correct position
- Code blocks render correctly
- `git diff README.md` shows only added lines, no deletions

**Commit message:**
```
Wave 0 Task 9: add install section to README

- README.md: added "Installation (Development)" section
  - Prerequisites list
  - Clone + venv + pip install commands
  - Verify import + run tests commands

No existing content modified. Section inserted after Quick Start.
```

---

# POST-WAVE VERIFICATION

After all 9 tasks committed, Claude CLI performs final wave audit:

## Checklist

- [ ] 9 commits exist in git log (one per task)
- [ ] `git status` clean
- [ ] `gobp/` package exists with all 19 files
- [ ] `pyproject.toml` valid
- [ ] `requirements.txt` + `requirements-dev.txt` exist
- [ ] `venv/` exists (not committed, gitignored)
- [ ] `gobp/schema/core_nodes.yaml` valid (6 node types)
- [ ] `gobp/schema/core_edges.yaml` valid (5 edge types)
- [ ] 6 templates in `gobp/templates/`
- [ ] 13 smoke tests pass: `pytest tests/test_smoke.py -v`
- [ ] `python -c "import gobp"` works
- [ ] README.md has Install section
- [ ] No foundational docs modified
- [ ] No files outside task scope created

## Push approval

After all checks pass, wait for CEO approval to push:

```
Push to GitHub? (y/n)
```

If CEO approves:
```powershell
git push origin main
```

## Wave complete summary

Print final summary:
```
═══════════════════════════════════════════════
WAVE 0 COMPLETE

Tasks: 9 / 9 done
Commits: 9
Files created: ~35
Tests passing: 13
Time: <duration>

Ready for Wave 1.
═══════════════════════════════════════════════
```

---

# ESCALATION TRIGGERS

Claude CLI escalates to CEO (→ CTO Chat) if:

- Cursor fails 3 retries on same task
- Audit fails repeatedly after Cursor fixes
- `pip install` fails due to environment issue
- Python version incompatible
- YAML validation fails despite Brief content being correct
- Any foundational doc appears wrong
- Task spec is ambiguous

Escalation format per `CLAUDE.md` section "ESCALATION PROCEDURE".

---

# WHAT COMES NEXT

After Wave 0 complete and pushed:

| Wave | Title | Effort |
|---|---|---|
| Wave 1 | Core engine — GraphIndex class | ~3-4 hours |
| Wave 2 | File loader + validator | ~3-4 hours |
| Wave 3 | MCP server + 6 read tools | ~4-6 hours |
| Wave 4 | CLI commands (init, validate, etc.) | ~2-3 hours |
| Wave 5 | Write tools + import tools | ~3-4 hours |
| Wave 6 | Advanced features | ~2-3 hours |
| Wave 7 | Documentation polish | ~2 hours |
| Wave 8 | MIHOS integration test | ~3-4 hours |

Wave 1-8 Briefs will be written by CTO Chat in separate sessions.

---

*Wave 0 Brief v0.2*
*Author: CTO Chat (Claude Opus 4.6)*
*Date: 2026-04-14*
*For: Cursor (dev) + Claude CLI (audit) in 3-tier pipeline*

◈
