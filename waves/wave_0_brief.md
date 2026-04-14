# ◈ GoBP WAVE 0 BRIEF — REPO BOOTSTRAP

**Wave:** 0
**Title:** Repo Bootstrap — Package Structure + Core Schemas + Templates
**Author:** CTO Chat (Claude Opus 4.6)
**Date:** 2026-04-14
**For:** Cursor (executor)
**Status:** READY FOR EXECUTION
**Estimated effort:** 1.5-2 hours
**Wave count:** This is the first of an estimated 8 waves to ship GoBP v1

---

## 0. CONTEXT

You are starting work on **GoBP — Graph of Brainstorm Project**. This is the first wave. Before you do anything, you must read the foundational docs as instructed in `.cursorrules` Phase 1.

GoBP is a knowledge store for AI agents. It is being built so AI sessions stop forgetting context, so dev tools stop loading 60K tokens of docs to code 1 feature, and so brainstorm ideas stop drifting into wrong implementations.

Wave 0 establishes the **skeleton** of the project: package structure, dependencies, core schema files, and templates. **No code logic yet.** Code logic begins in Wave 1.

This is intentional. Wave 0 is small and safe so we can verify the workflow (CTO writes Brief → Cursor executes → CEO reviews → wave closes) before tackling harder waves.

---

## 1. GOALS

By the end of this wave:
1. The Python package `gobp/` exists with proper structure but mostly empty modules
2. Dependencies are declared in `pyproject.toml` and `requirements.txt`
3. A virtual environment is set up and verified working
4. Core schema YAML files exist and are valid YAML
5. 6 markdown templates exist for the 6 node types
6. A basic test exists that verifies the package can be imported
7. Everything committed to git with proper commit message

**You are NOT:**
- Implementing GraphIndex class (Wave 1)
- Implementing MCP server (Wave 3)
- Implementing CLI (Wave 4)
- Loading any data into the schema
- Writing any business logic

---

## 2. PREREQUISITES (verify before starting)

Before Phase 1 (reading), confirm these prerequisites by running commands in PowerShell at `D:\GoBP\`:

```powershell
# Check Python is installed and version >= 3.10
python --version
# Expected: Python 3.10.x or higher

# Check Git is installed
git --version
# Expected: git version 2.x

# Check we are in the right folder
pwd
# Expected: D:\GoBP

# Check git is connected to the right remote
git remote -v
# Expected: origin https://github.com/mihos3506/GoBP.git ...

# Check current branch
git branch --show-current
# Expected: main
```

If any check fails, STOP and report to CTO. Do not proceed.

---

## 3. TASKS

You will execute these tasks in order. Each task is independent and verifiable.

### Task 0 — Read foundational docs

Per `.cursorrules` Phase 1. Read in order:
1. `CHARTER.md`
2. `README.md`
3. `docs/VISION.md`
4. `docs/ARCHITECTURE.md` (focus on sections 1, 2, 3, 4, 6)
5. `docs/SCHEMA.md` (full read — you will reference this heavily)

You can skim `INPUT_MODEL.md`, `IMPORT_MODEL.md`, `MCP_TOOLS.md` — these are for later waves.

**Acceptance:** Confirm in your Phase 7 report which docs you read.

---

### Task 1 — Create Python package skeleton

Create the following directory structure and empty files:

```
D:\GoBP\
└── gobp\
    ├── __init__.py
    ├── core\
    │   ├── __init__.py
    │   ├── graph.py          (empty stub, only docstring)
    │   ├── loader.py         (empty stub)
    │   ├── validator.py      (empty stub)
    │   ├── mutator.py        (empty stub)
    │   └── history.py        (empty stub)
    ├── schema\
    │   ├── __init__.py
    │   ├── core_nodes.yaml   (created in Task 4)
    │   └── core_edges.yaml   (created in Task 4)
    ├── mcp\
    │   ├── __init__.py
    │   ├── server.py         (empty stub)
    │   └── tools\
    │       ├── __init__.py
    │       ├── read.py       (empty stub)
    │       ├── write.py      (empty stub)
    │       ├── import_.py    (empty stub)
    │       └── maintain.py   (empty stub)
    ├── cli\
    │   ├── __init__.py
    │   ├── __main__.py       (basic entry point only)
    │   └── commands.py       (empty stub)
    └── templates\
        ├── node.md           (created in Task 5)
        ├── idea.md           (created in Task 5)
        ├── decision.md       (created in Task 5)
        ├── session.md        (created in Task 5)
        ├── document.md       (created in Task 5)
        └── lesson.md         (created in Task 5)
```

**Each `__init__.py` file content:**
```python
"""<package name> — short description"""

__version__ = "0.1.0"
```

**Each empty stub file content (e.g., graph.py):**
```python
"""GoBP core graph index.

This module will contain the GraphIndex class.
Implementation begins in Wave 1.
"""
```

**Special: `gobp/cli/__main__.py`:**
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

**Acceptance:**
- `python -c "import gobp"` runs without error
- `python -c "from gobp.core import graph"` runs without error
- All folders and files exist as listed

---

### Task 2 — Create `pyproject.toml`

Create `D:\GoBP\pyproject.toml`:

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

**Acceptance:**
- File exists at `D:\GoBP\pyproject.toml`
- Valid TOML syntax (verify by running any TOML parser or `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`)

---

### Task 3 — Create `requirements.txt`

Create `D:\GoBP\requirements.txt`:

```
mcp>=0.9.0
pyyaml>=6.0
```

Create `D:\GoBP\requirements-dev.txt`:

```
-r requirements.txt
pytest>=7.0
pytest-asyncio>=0.21
```

**Acceptance:**
- Both files exist
- `pip install -r requirements.txt` would work (do NOT actually install yet — that is Task 6)

---

### Task 4 — Create core schema YAML files

These define the 6 node types and 5 edge types. Reference `docs/SCHEMA.md` sections 2 and 3 for the full specifications. You will translate the schema descriptions in SCHEMA.md into the YAML format below.

**File: `gobp/schema/core_nodes.yaml`**

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

**File: `gobp/schema/core_edges.yaml`**

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

**Acceptance:**
- Both files exist at correct paths
- Both files are valid YAML (verify with `python -c "import yaml; yaml.safe_load(open('gobp/schema/core_nodes.yaml'))"`)
- 6 node types defined in core_nodes.yaml
- 5 edge types defined in core_edges.yaml

---

### Task 5 — Create node templates

Create 6 template files in `gobp/templates/`. Each template is a markdown file with YAML front-matter showing the structure of that node type, with placeholder values.

**File: `gobp/templates/node.md`**

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

**File: `gobp/templates/idea.md`**

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

**File: `gobp/templates/decision.md`**

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

**File: `gobp/templates/session.md`**

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

**File: `gobp/templates/document.md`**

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

**File: `gobp/templates/lesson.md`**

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

**Acceptance:**
- All 6 template files exist
- Each is valid YAML front-matter (the part between `---` lines)
- Each matches the schema defined in `core_nodes.yaml`

---

### Task 6 — Set up Python virtual environment

Run these commands in PowerShell at `D:\GoBP\`:

```powershell
# Create venv
python -m venv venv

# Activate venv
.\venv\Scripts\Activate.ps1

# If you get a script execution error, run this once:
# Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Verify activation (should show (venv) in prompt)

# Upgrade pip
python -m pip install --upgrade pip

# Install dev dependencies
pip install -r requirements-dev.txt

# Install the package itself in editable mode
pip install -e .

# Verify
python -c "import gobp; print(gobp.__version__)"
# Expected: 0.1.0

python -c "import yaml; print(yaml.__version__)"
# Expected: a version string

python -c "import mcp; print('mcp imported OK')"
# Expected: mcp imported OK
```

**Acceptance:**
- `venv/` folder exists
- All imports work
- `gobp.__version__` returns "0.1.0"

If `pip install` fails because Python version too low, STOP and report to CTO.

---

### Task 7 — Write smoke tests

Create `D:\GoBP\tests\__init__.py` (empty file).

Create `D:\GoBP\tests\test_smoke.py`:

```python
"""Smoke tests for GoBP package.

These tests verify the package can be imported and basic structure exists.
They do NOT test any business logic — that begins in Wave 1+.
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
    """CLI module can be imported."""
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
    """core_nodes.yaml exists in the schema folder."""
    schema_file = get_schema_dir() / "core_nodes.yaml"
    assert schema_file.exists(), f"Missing: {schema_file}"


def test_core_edges_yaml_exists():
    """core_edges.yaml exists in the schema folder."""
    schema_file = get_schema_dir() / "core_edges.yaml"
    assert schema_file.exists(), f"Missing: {schema_file}"


def test_core_nodes_yaml_valid():
    """core_nodes.yaml is valid YAML and has expected structure."""
    schema_file = get_schema_dir() / "core_nodes.yaml"
    with open(schema_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    assert "schema_version" in data
    assert "node_types" in data
    
    expected_types = {"Node", "Idea", "Decision", "Session", "Document", "Lesson"}
    actual_types = set(data["node_types"].keys())
    assert actual_types == expected_types, f"Expected {expected_types}, got {actual_types}"


def test_core_edges_yaml_valid():
    """core_edges.yaml is valid YAML and has expected structure."""
    schema_file = get_schema_dir() / "core_edges.yaml"
    with open(schema_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    assert "schema_version" in data
    assert "edge_types" in data
    
    expected_types = {"relates_to", "supersedes", "implements", "discovered_in", "references"}
    actual_types = set(data["edge_types"].keys())
    assert actual_types == expected_types, f"Expected {expected_types}, got {actual_types}"


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
    """Each template starts with YAML front-matter (--- delimited)."""
    templates_dir = get_templates_dir()
    
    for template_file in templates_dir.glob("*.md"):
        content = template_file.read_text(encoding="utf-8")
        assert content.startswith("---\n"), f"{template_file.name} missing front-matter start"
        assert "\n---\n" in content[4:], f"{template_file.name} missing front-matter end"
```

**Run the tests:**

```powershell
# With venv activated
pytest tests/ -v
```

**Acceptance:**
- All tests pass (11 tests total)
- No errors or warnings

If any test fails, debug and fix per Phase 5 of `.cursorrules`.

---

### Task 8 — Update README.md to add install instructions

Add a new section to `README.md` (do NOT edit existing sections, only ADD this section).

Insert this section AFTER the "Quick Start" section and BEFORE the "Core Concepts in 60 Seconds" section:

```markdown
## 🛠️ Installation (Development)

### Prerequisites
- Python 3.10 or higher
- Git
- A working virtual environment tool (venv ships with Python)

### Setup

```bash
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

# Run tests
pytest tests/ -v
```

After Wave 0, the package is importable but has no functionality yet. Functionality begins in Wave 1.
```

**Acceptance:**
- README.md still has all original content
- New "Installation (Development)" section added in the correct position
- Code block syntax is correct

---

### Task 9 — Commit and push

Run these commands in PowerShell at `D:\GoBP\`:

```powershell
# Check what changed
git status

# Stage everything
git add .

# Verify staging is correct (should NOT include venv/ or __pycache__/ — gitignore handles these)
git status

# Commit with proper message
git commit -m "Wave 0: bootstrap repo with package structure, schemas, and templates"

# Push to GitHub
git push origin main
```

**Acceptance:**
- Commit succeeds with no errors
- Push succeeds
- `git status` after push shows: `nothing to commit, working tree clean`

---

## 4. PHASE 7 REPORT

After all tasks complete, write your Phase 7 report following the format in `.cursorrules`. Save it to `waves/wave_0_report.md` (you create this file).

Include:
- Which docs you read
- Files created (with line counts)
- Tests written and results
- Discoveries (especially anything that suggests SCHEMA.md or ARCHITECTURE.md needs revision)
- Out-of-scope items deferred
- Issues encountered

---

## 5. ACCEPTANCE CRITERIA (CTO will check)

Wave 0 is complete when:

- [x] Foundational docs read (verified by Cursor's report)
- [ ] `gobp/` package exists with all required submodules
- [ ] `pyproject.toml` valid
- [ ] `requirements.txt` and `requirements-dev.txt` exist
- [ ] `gobp/schema/core_nodes.yaml` valid YAML, 6 node types
- [ ] `gobp/schema/core_edges.yaml` valid YAML, 5 edge types
- [ ] 6 templates in `gobp/templates/`
- [ ] `venv/` works, `pip install -e .` succeeds
- [ ] `python -c "import gobp"` works
- [ ] All 11 smoke tests pass
- [ ] README.md has Install section added
- [ ] Wave 0 report at `waves/wave_0_report.md`
- [ ] Everything committed and pushed to GitHub
- [ ] No files outside Brief scope created
- [ ] No foundational docs modified

---

## 6. WHAT IS DEFERRED TO LATER WAVES

For clarity, here is what is NOT in Wave 0:

| Wave | Deferred work |
|---|---|
| Wave 1 | Implement `GraphIndex` class — load from files, build indexes |
| Wave 2 | Implement `loader.py` and `validator.py` — file parsing, schema enforcement |
| Wave 3 | Implement MCP server with 6 read tools |
| Wave 4 | Implement CLI commands (`gobp init`, `gobp validate`, etc.) |
| Wave 5 | Implement 3 write tools and 2 import tools |
| Wave 6 | CLI advanced features |
| Wave 7 | Documentation, install guides, error handling polish |
| Wave 8 | MIHOS integration test, lessons extraction |

Do not start any of these in Wave 0.

---

## 7. IF YOU GET STUCK

Use the format from `.cursorrules` "Asking the CTO" section. Include:
- Wave 0 Task <N>
- What you tried
- What error you got
- Specific question

Common issues anticipated:
- `pip install` fails due to network — try again, or document and ask CTO
- `pytest` not found — make sure venv is activated
- `Set-ExecutionPolicy` needed for venv activation on Windows — that's normal
- `gobp` import fails — check `pyproject.toml` package discovery section

---

## 8. SIGN-OFF

When all tasks complete, all tests pass, everything pushed:

1. Update this Brief file: change `Status: READY FOR EXECUTION` to `Status: COMPLETED`
2. Add a line: `Completed: 2026-04-14 by Cursor`
3. Commit and push the Brief update
4. Notify CTO Chat in the next conversation: "Wave 0 complete"

---

*Wave 0 Brief v0.1*
*Author: CTO Chat (Claude Opus 4.6)*
*Date: 2026-04-14*
*Total estimated effort: 1.5-2 hours*

◈
