# WAVE 7 BRIEF — DOCUMENTATION POLISH

**Wave:** 7
**Title:** Documentation Polish — Install Guide, CONTRIBUTING, Docstring Audit, CHANGELOG, Test Helper
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 6 atomic tasks
**Estimated effort:** 2-3 hours

---

## CONTEXT

Waves 0–6 shipped a fully functional GoBP v1: 14 MCP tools, 166 tests passing, schema-validated graph storage. The codebase is production-quality but documentation is uneven — README has basic content, but there is no install guide for real MCP clients, no contributor guide, no CHANGELOG, and docstrings are inconsistent across modules.

Wave 7 fixes this. After Wave 7, GoBP is ready to hand to another developer or founder without a verbal walkthrough.

**In scope:**
- `docs/INSTALL.md` — step-by-step install + MCP client config for Cursor, Claude Desktop, Claude CLI
- `CONTRIBUTING.md` — how to run tests, submit fixes, write Wave Briefs
- `CHANGELOG.md` — full version history from Wave 0 to Wave 6
- Docstring audit — fill missing docstrings on all public functions across `gobp/core/` and `gobp/mcp/`
- `tests/conftest.py` — shared `gobp_root` fixture that provisions schema files (fixes F19 pattern permanently)
- Update existing test files to use `conftest.py` fixture instead of local `_make_gobp_root`/`_make_root` helpers

**NOT in scope:**
- CLI commands (Wave 4, permanently dropped)
- Web UI or hosted documentation
- PyPI packaging
- Any new features or tools

---

## CURSOR EXECUTION RULES (READ FIRST — NON-NEGOTIABLE)

### R1 — Sequential execution
Execute Task 1 → Task 2 → ... → Task 6 in order. Do NOT skip, reorder, or parallelize.

### R2 — Discovery before creation
Use explorer subagent before creating any new file. If file exists, read it first.

### R3 — 1 task = 1 commit
After each task passes verification → commit immediately with exact message from Brief.

### R4 — MCP_TOOLS.md is supreme authority
If any content conflicts with `docs/MCP_TOOLS.md` → docs win, STOP and report.

### R5 — Document disagreement = STOP and suggest
If you believe a foundational doc has an error → STOP, report observation, wait for instruction.

### R6 — 3 retries = STOP and report
Test or verification fails 3 times → STOP, file stop report, wait for CEO relay to CTO.

### R7 — No scope creep
Write EXACTLY what Brief specifies. No extra sections, no extra fixtures, no new tools.

### R8 — Brief content blocks are authoritative
If you disagree with content in this Brief → STOP and escalate. Do not substitute.

---

## STOP REPORT FORMAT

```
STOP — Wave 7 Task <N>

Rule triggered: R<N> — <rule name>

Completed so far: Tasks 1–<N-1> (committed)
Current task: Task <N> — <title>

What I was doing: <description>
What went wrong: <exact error or conflict>
What I tried: <list of attempts if R6>
Why I cannot proceed: <reason>

Conflict details (if R4 or R5):
  Brief says: <quote>
  Doc says: <quote from docs/X.md §N.N>

Current git state:
  Staged: <list>
  Unstaged: <list>

What I need from CEO/CTO: <specific question>
```

---

## AUTHORITATIVE SOURCE

- `docs/MCP_TOOLS.md` — tool names, descriptions, all 14 tools
- `docs/SCHEMA.md` — node/edge types for CHANGELOG and INSTALL accuracy
- `docs/ARCHITECTURE.md` — folder structure for INSTALL and CONTRIBUTING
- `README.md` — existing content to cross-reference (do not duplicate)

---

## SCOPE DISCIPLINE RULE

Implement EXACTLY what this Brief specifies. Documentation tasks: write the content specified, no extra sections. Test refactor task: touch only the files listed.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
# Expected: clean (only untracked .claude/, .gobp/, files.zip)

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: 166 tests passing
```

---

## REQUIRED READING — WAVE START (before Task 1)

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Execution rules |
| 2 | `README.md` | Existing content — do not duplicate |
| 3 | `docs/ARCHITECTURE.md` | Folder structure, design decisions |
| 4 | `docs/MCP_TOOLS.md` | All 14 tools for INSTALL and CHANGELOG |
| 5 | `docs/SCHEMA.md` | Node/edge types for accuracy |
| 6 | `waves/wave_7_brief.md` | This file |

**Per-task reading:**

| Task | Must re-read before starting |
|---|---|
| Task 1 (INSTALL.md) | `README.md`, `docs/ARCHITECTURE.md` |
| Task 2 (CONTRIBUTING.md) | `README.md`, `.cursorrules`, `CLAUDE.md` |
| Task 3 (CHANGELOG.md) | All wave briefs in `waves/`, `git log --oneline` |
| Task 4 (docstring audit) | Each module file before editing it |
| Task 5 (conftest.py) | All test files to understand current fixture patterns |
| Task 6 (refactor tests) | `tests/conftest.py` just created, each test file being refactored |

---

# TASKS

---

## TASK 1 — Create docs/INSTALL.md

**Goal:** Step-by-step install and MCP client configuration guide.

**File to create:** `docs/INSTALL.md`

**Content:**

```markdown
# GoBP Installation Guide

## Requirements

- Python 3.10+
- Git
- One of: Cursor IDE, Claude Desktop, Claude CLI

---

## 1. Clone and install

```bash
git clone https://github.com/mihos3506/GoBP.git
cd GoBP
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -e .
```

Verify:

```bash
python -c "import gobp; print(gobp.__version__)"
# Expected: 0.1.0
```

---

## 2. Initialize a project

Navigate to your project root and run:

```bash
python -m gobp.cli init
```

This creates a `.gobp/` folder with the required structure:

```
.gobp/
  nodes/       # Node markdown files
  edges/       # Edge YAML files
  history/     # Append-only event log
  archive/     # Pruned nodes (created on first prune)
  config.yaml  # Project config and schema version
```

---

## 3. Connect an MCP client

### Cursor IDE

Create or edit `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["PATH_TO_GOBP/gobp/mcp/server.py"],
      "env": {
        "GOBP_PROJECT_ROOT": "PATH_TO_YOUR_PROJECT"
      }
    }
  }
}
```

Replace `PATH_TO_GOBP` with the full path to your GoBP clone (e.g. `D:/GoBP`).
Replace `PATH_TO_YOUR_PROJECT` with the project you want GoBP to track.

Restart Cursor after saving. GoBP tools will appear in the AI tool panel.

### Claude Desktop

Edit `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["PATH_TO_GOBP/gobp/mcp/server.py"],
      "env": {
        "GOBP_PROJECT_ROOT": "PATH_TO_YOUR_PROJECT"
      }
    }
  }
}
```

Restart Claude Desktop after saving.

### Claude CLI

```bash
claude mcp add gobp -- python PATH_TO_GOBP/gobp/mcp/server.py
```

Set the project root via environment variable before running Claude CLI:

```bash
export GOBP_PROJECT_ROOT=PATH_TO_YOUR_PROJECT  # macOS/Linux
set GOBP_PROJECT_ROOT=PATH_TO_YOUR_PROJECT     # Windows
claude
```

---

## 4. Verify connection

Once your MCP client is connected, ask the AI:

```
Call gobp_overview and tell me what you see.
```

Expected response includes: project name, node count (0 if new), available tools (14).

---

## 5. Available MCP tools (14)

| Tool | Purpose |
|---|---|
| `gobp_overview` | Project orientation — call first |
| `find` | Fuzzy search nodes by keyword |
| `signature` | Minimal summary of a node |
| `context` | Full node + edges + decisions bundle |
| `session_recent` | Latest N sessions |
| `decisions_for` | Locked decisions by topic or node |
| `doc_sections` | Sections of a Document node |
| `node_upsert` | Create or update any node |
| `decision_lock` | Lock a Decision with verification |
| `session_log` | Start / update / end a session |
| `import_proposal` | AI proposes batch import |
| `import_commit` | Commit approved import |
| `validate` | Full schema + constraint check |
| `lessons_extract` | Scan for lesson candidates |

Full specs: `docs/MCP_TOOLS.md`.

---

## 6. Troubleshooting

**`ModuleNotFoundError: No module named 'gobp'`**
→ Activate venv before running: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (macOS/Linux).

**MCP client shows no GoBP tools**
→ Check paths in config have no typos. Use absolute paths (not `~` or relative paths).
→ Restart the MCP client after config change.

**`GOBP_PROJECT_ROOT` not set error**
→ Set the env variable in the MCP client config, not in the shell.

**Schema validation errors on startup**
→ Run `python -m gobp.cli validate` to see what's wrong.
→ Usually caused by manually edited node files with missing required fields.
```

**Acceptance criteria:**
- File created at `docs/INSTALL.md`
- Covers: clone/install, init, Cursor config, Claude Desktop config, Claude CLI config, tool list, troubleshooting
- All 14 tools listed in tool table
- Paths use `PATH_TO_GOBP` placeholder (not hardcoded)

**Commit message:**
```
Wave 7 Task 1: create docs/INSTALL.md

- Step-by-step install guide
- MCP client config for Cursor, Claude Desktop, Claude CLI
- All 14 tools listed
- Troubleshooting section
```

---

## TASK 2 — Create CONTRIBUTING.md

**Goal:** Contributor guide for developers and future CTO instances.

**File to create:** `CONTRIBUTING.md`

**Content:**

```markdown
# Contributing to GoBP

## Who this is for

- Developers extending GoBP
- Future CTO instances starting in a new tab
- Anyone submitting a bug fix or wave

---

## Setup

```bash
git clone https://github.com/mihos3506/GoBP.git
cd GoBP
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -e ".[dev]"
```

---

## Running tests

```bash
# Full suite
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v

# Single module
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_lessons.py -v

# With coverage
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --cov=gobp
```

Expected baseline: 166 tests passing after Wave 6.

---

## Project structure

```
gobp/
  core/         # Engine: loader, validator, graph, mutator, history
                #         migrate, prune, lessons
  mcp/
    tools/      # Tool handlers: read, write, import_, maintain, advanced
    server.py   # MCP server + dispatch
  schema/       # core_nodes.yaml, core_edges.yaml
  templates/    # Node/edge file templates
docs/           # Foundational docs (source of truth)
waves/          # Wave Briefs (history of build decisions)
tests/          # All tests — 1 file per module
```

---

## How waves work

GoBP is built using a 4-actor pipeline:

```
CEO → CTO Chat (writes Brief) → Cursor (executes) → Claude CLI (audits)
```

1. CTO Chat writes a Wave Brief in `waves/wave_N_brief.md`
2. CEO uploads Brief, dispatches Cursor with one paste
3. Cursor executes all tasks sequentially, 1 commit per task
4. Claude CLI audits sequentially with fail-stop
5. CEO pushes after audit passes

**Rules Cursor follows (R1–R8) are in every Brief.** Read them before touching a wave.

---

## Submitting a fix

1. Branch from `main`: `git checkout -b fix/your-fix-name`
2. Fix the issue
3. Run full test suite — must pass
4. Commit with clear message: `Fix: <what> — <why>`
5. Open PR against `main`

**Do not modify foundational docs** (`docs/SCHEMA.md`, `docs/MCP_TOOLS.md`, `docs/ARCHITECTURE.md`) without CTO approval. These are source of truth — changes break existing behavior.

---

## Writing a new wave

1. CTO Chat writes `waves/wave_N_brief.md` using the template in `.cursorrules`
2. Brief must include: CURSOR EXECUTION RULES (R1–R8), REQUIRED READING table, per-task doc cross-reference, STOP REPORT FORMAT, POST-WAVE VERIFICATION, CEO DISPATCH INSTRUCTIONS
3. CEO uploads and dispatches per `CEO DISPATCH INSTRUCTIONS` section in Brief

See `waves/wave_6_brief.md` as the most complete example.

---

## Adding a new MCP tool

1. Add tool spec to `docs/MCP_TOOLS.md` first (source of truth)
2. Implement handler in `gobp/mcp/tools/<module>.py`
3. Register in `gobp/mcp/server.py` — `list_tools()` + `call_tool()` dispatch
4. Write tests in `tests/test_tool_<name>.py`
5. Update README tool count

Pattern to follow: `gobp/mcp/tools/advanced.py` (lessons_extract).

---

## Adding a new node type

1. Add type spec to `docs/SCHEMA.md` first
2. Add to `gobp/schema/core_nodes.yaml`
3. Update validator if new constraints
4. Write tests

---

## Code standards

- Python 3.10+
- Type hints on all public functions
- Docstrings on all public functions
- `pathlib.Path`, not `os.path`
- Specific exceptions, not bare `except`
- No web frameworks, no ORMs, no cloud SDKs (see `.cursorrules` forbidden deps)

---

## Test standards

- Every public function has at least one test
- Use `tmp_path` pytest fixture for isolation
- Use `gobp_root` fixture from `tests/conftest.py` for any test calling `GraphIndex.load_from_disk()`
- Tests verify spec compliance, not just "does not crash"
```

**Acceptance criteria:**
- File created at `CONTRIBUTING.md`
- Covers: setup, running tests, project structure, wave workflow, fix submission, new tool guide, code standards, test standards
- References `tests/conftest.py` gobp_root fixture

**Commit message:**
```
Wave 7 Task 2: create CONTRIBUTING.md

- Setup, test commands, project structure
- Wave workflow explanation (4-actor pipeline)
- Fix submission and new tool/node guides
- Code and test standards
- References conftest.py gobp_root fixture
```

---

## TASK 3 — Create CHANGELOG.md

**Goal:** Full version history from Wave 0 to Wave 6.

**File to create:** `CHANGELOG.md`

**Re-read `git log --oneline` and all wave briefs in `waves/` before writing.**

**Content structure:**

```markdown
# CHANGELOG

All notable changes to GoBP are documented here.
Format: [Wave N — Title] with date, what was added/changed/fixed.

---

## [Wave 6] — Advanced Features — 2026-04-15

### Added
- `gobp/core/lessons.py` — `extract_candidates()` with 4 pattern scanners (P1–P4)
- `gobp/core/migrate.py` — `check_version()`, `run_migration()`, schema version management
- `gobp/core/prune.py` — `dry_run()`, `run_prune()` — archive WITHDRAWN+unconnected nodes
- `gobp/mcp/tools/advanced.py` — `lessons_extract` MCP tool handler
- MCP tool `lessons_extract` (tool #14) registered in server
- Tests: `test_lessons.py`, `test_migrate.py`, `test_prune.py`, `test_tool_lessons_extract.py`

### Fixed
- `prune.py`: node slug now uses `_` (underscore) to match `mutator._node_file_path`
- `server.py`: async handlers are now properly `await`-ed in `call_tool()` dispatch

### Total after wave: 14 MCP tools, 166 tests passing

---

## [Wave 5] — Write Tools + Import Tools + Validate — 2026-04-14

### Added
- `gobp/mcp/tools/write.py` — `node_upsert`, `decision_lock`, `session_log`
- `gobp/mcp/tools/import_.py` — `import_proposal`, `import_commit`
- `gobp/mcp/tools/maintain.py` — `validate`
- 6 new tools registered in MCP server (total: 13)
- Tests for all 6 new tools
- README: "What Works After Wave 5" section

### Total after wave: 13 MCP tools, 137 tests passing

---

## [Wave 3] — MCP Server + Read Tools — 2026-04-14

### Added
- `gobp/mcp/server.py` — MCP server with stdio transport
- `gobp/mcp/tools/read.py` — 7 read tools: `gobp_overview`, `find`, `signature`, `context`, `session_recent`, `decisions_for`, `doc_sections`
- Example client configs: Cursor, Claude Desktop, Claude CLI, Continue.dev
- Tests for all 7 read tools

### Total after wave: 7 MCP tools, 109 tests passing

---

## [Wave 2] — File Storage + Mutator — 2026-04-14

### Added
- `gobp/core/history.py` — append-only JSONL event log
- `gobp/core/mutator.py` — atomic file writes, `create_node`, `update_node`, `create_edge`, `delete_node`, `delete_edge`
- `.gobp/history/YYYY-MM-DD.jsonl` log format
- Tests: `test_history.py` (10 tests), `test_mutator.py` (20 tests)

### Total after wave: 66 tests passing

---

## [Wave 1] — Core Engine — 2026-04-14

### Added
- `gobp/core/loader.py` — markdown + YAML front-matter parser
- `gobp/core/validator.py` — schema validation for nodes and edges
- `gobp/core/graph.py` — `GraphIndex` in-memory graph with load, query, error collection
- Tests: loader/validator (26 tests), graph (11 tests)

### Total after wave: 50 tests passing

---

## [Wave 0] — Repository Init — 2026-04-14

### Added
- Repository structure: `gobp/`, `docs/`, `waves/`, `tests/`, `_templates/`
- `gobp/schema/core_nodes.yaml` — 6 node types: Node, Idea, Decision, Session, Document, Lesson
- `gobp/schema/core_edges.yaml` — 5 edge types: relates_to, supersedes, implements, discovered_in, references
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`
- `LICENSE` (MIT)
- 6 node/edge templates in `gobp/templates/`
- Smoke tests (13 tests)

### Total after wave: 13 tests passing

---

## Foundational docs (pre-Wave 0)

Written before any code:
- `CHARTER.md` — mission, non-goals, principles
- `VISION.md` — 4 pain points, target state
- `docs/ARCHITECTURE.md` — file-first design, GraphIndex, lifecycle
- `docs/SCHEMA.md` — 6 node types, 5 edge types, validation rules
- `docs/MCP_TOOLS.md` — all tool specs (source of truth)
- `docs/INPUT_MODEL.md` — how founders speak, capture patterns
- `docs/IMPORT_MODEL.md` — import flow, proposal state machine
```

**Acceptance criteria:**
- File created at `CHANGELOG.md`
- Covers all waves 0–6 with accurate tool counts and test counts
- Wave 6 fix entries (prune slug, async await) present
- Dates match actual build date (2026-04-14 for waves 0–5, 2026-04-15 for wave 6)

**Commit message:**
```
Wave 7 Task 3: create CHANGELOG.md

- Full history from pre-Wave 0 foundational docs through Wave 6
- Tool counts and test counts per wave
- Wave 6 fix entries included
```

---

## TASK 4 — Docstring audit across gobp/core/ and gobp/mcp/

**Goal:** Every public function in `gobp/core/` and `gobp/mcp/tools/` has a docstring. Fill gaps only — do not rewrite existing docstrings.

**Files to audit (in order):**
1. `gobp/core/lessons.py` — check `extract_candidates` + 4 private scanners
2. `gobp/core/migrate.py` — check `check_version`, `run_migration`, `_update_config_version`
3. `gobp/core/prune.py` — check `dry_run`, `run_prune`, `_find_prunable`
4. `gobp/mcp/tools/advanced.py` — check `lessons_extract`
5. `gobp/mcp/server.py` — check module docstring, `list_tools`, `call_tool`

**For each file:**
- Read file in full
- Identify any public function (no `_` prefix) missing a docstring
- Add minimal one-line docstring if missing: `"""<What it does and what it returns>."""`
- Do NOT rewrite existing docstrings
- Do NOT change any logic

**Acceptance criteria:**
- All public functions in listed files have at least a one-line docstring
- No logic changes
- `pytest tests/ -v` still passes (166 tests)

**Commit message:**
```
Wave 7 Task 4: docstring audit — fill missing docstrings in core/ and mcp/tools/

- lessons.py, migrate.py, prune.py, advanced.py, server.py
- Added missing one-line docstrings only
- No logic changes
```

---

## TASK 5 — Create tests/conftest.py with shared gobp_root fixture

**Goal:** Create a shared pytest fixture that provisions schema files correctly — permanent fix for the F19 pattern discovered in Wave 6.

**File to create:** `tests/conftest.py`

**Content:**

```python
"""Shared pytest fixtures for GoBP test suite.

Key fixture: gobp_root — creates a tmp .gobp/ structure with schema files
provisioned. Any test that calls GraphIndex.load_from_disk() must use this
fixture instead of a local _make_gobp_root helper.

Background: GraphIndex.load_from_disk() requires gobp/schema/core_nodes.yaml
and gobp/schema/core_edges.yaml relative to the project root. Tests that
create a tmp root without these files will fail with FileNotFoundError.
This fixture provisions them automatically from the repo's schema files.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest


@pytest.fixture
def gobp_root(tmp_path: Path) -> Path:
    """Create a minimal .gobp/ project root for testing.

    Provisions:
    - .gobp/nodes/
    - .gobp/edges/
    - .gobp/history/
    - gobp/schema/core_nodes.yaml  (copied from repo)
    - gobp/schema/core_edges.yaml  (copied from repo)

    Returns:
        Path to the tmp project root, ready for GraphIndex.load_from_disk().
    """
    # Create .gobp structure
    (tmp_path / ".gobp" / "nodes").mkdir(parents=True)
    (tmp_path / ".gobp" / "edges").mkdir(parents=True)
    (tmp_path / ".gobp" / "history").mkdir(parents=True)

    # Provision schema files required by GraphIndex.load_from_disk()
    repo_schema = Path(__file__).parent.parent / "gobp" / "schema"
    dest_schema = tmp_path / "gobp" / "schema"
    dest_schema.mkdir(parents=True)
    shutil.copy(repo_schema / "core_nodes.yaml", dest_schema / "core_nodes.yaml")
    shutil.copy(repo_schema / "core_edges.yaml", dest_schema / "core_edges.yaml")

    return tmp_path
```

**Acceptance criteria:**
- File created at `tests/conftest.py`
- `gobp_root` fixture provisions both schema files
- Fixture uses `tmp_path` (pytest built-in) for isolation
- Module docstring explains F19 background
- `pytest tests/ -v` still passes (166 tests)

**Commit message:**
```
Wave 7 Task 5: create tests/conftest.py with shared gobp_root fixture

- gobp_root fixture: tmp .gobp/ + schema files provisioned
- Permanent fix for F19 pattern (GraphIndex requires schema files)
- All 166 tests still passing
```

---

## TASK 6 — Refactor test files to use conftest gobp_root fixture

**Goal:** Remove local `_make_gobp_root` / `_make_root` helpers from Wave 6 test files and use the shared `gobp_root` fixture instead.

**Files to refactor:**
- `tests/test_lessons.py`
- `tests/test_prune.py`
- `tests/test_tool_lessons_extract.py`

**For each file:**
1. Read the file in full
2. Remove the local `_make_gobp_root` or `_make_root` helper function
3. Replace all test function signatures that use `tmp_path` with `gobp_root`
4. Remove the `import shutil` that was only used by the local helper (if no longer needed)
5. Run `pytest <file> -v` — must pass before moving to next file

**Pattern change:**

Before:
```python
def _make_gobp_root(tmp_path: Path) -> Path:
    # ... local helper with schema copy ...

def test_something(tmp_path: Path):
    root = _make_gobp_root(tmp_path)
```

After:
```python
# no local helper

def test_something(gobp_root: Path):
    root = gobp_root
```

**Acceptance criteria:**
- 3 test files refactored
- No local `_make_gobp_root` or `_make_root` helper remains in these files
- All tests use `gobp_root` fixture from conftest
- `pytest tests/ -v` passes (166 tests — count must not change)

**Commit message:**
```
Wave 7 Task 6: refactor Wave 6 tests to use conftest gobp_root fixture

- test_lessons.py: remove _make_gobp_root, use gobp_root fixture
- test_prune.py: remove _make_root, use gobp_root fixture
- test_tool_lessons_extract.py: remove _make_root, use gobp_root fixture
- All 166 tests passing
```

---

# POST-WAVE VERIFICATION

After all 6 tasks:

```powershell
# All tests pass
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: 166 tests passing

# New docs exist
Test-Path docs/INSTALL.md     # True
Test-Path CONTRIBUTING.md     # True
Test-Path CHANGELOG.md        # True
Test-Path tests/conftest.py   # True

# Git log
git log --oneline | Select-Object -First 8
# Expected: 6 Wave 7 commits
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief vào repo

```powershell
cd D:\GoBP
# Save wave_7_brief.md to D:\GoBP\waves\wave_7_brief.md

git add waves/wave_7_brief.md
git commit -m "Add Wave 7 Brief"
git push origin main
```

## 2. Dispatch Cursor

Cursor IDE → Ctrl+L → paste:

```
Read .cursorrules and waves/wave_7_brief.md first.
Also read README.md, docs/ARCHITECTURE.md, docs/MCP_TOOLS.md, docs/SCHEMA.md.
Also read CLAUDE.md and all wave briefs in waves/ (for CHANGELOG accuracy).

Execute ALL 6 tasks of Wave 7 sequentially:
- Use explorer subagent before creating any new file
- Re-read per-task docs listed in REQUIRED READING before each task
- If any content conflicts with docs/MCP_TOOLS.md → docs win, STOP and report (R4)
- If you believe a foundational doc has an error → STOP and report (R5)
- If verification fails 3 times → STOP and report (R6)
- 1 task = 1 commit, message must match Brief exactly
- Report full wave summary only after Task 6 is committed

Begin Task 1.
```

## 3. Audit Claude CLI

```powershell
cd D:\GoBP
claude
```

Paste vào Claude CLI:

```
Audit Wave 7. Read CLAUDE.md and waves/wave_7_brief.md.

Sequentially audit Task 1 through Task 6.

Critical verification per task:
- Task 1: docs/INSTALL.md exists, has all 14 tools listed, has Cursor/Desktop/CLI configs
- Task 2: CONTRIBUTING.md exists, references conftest.py gobp_root fixture
- Task 3: CHANGELOG.md exists, covers Wave 0–6, tool counts accurate
- Task 4: all public functions in gobp/core/lessons.py, migrate.py, prune.py, advanced.py, server.py have docstrings
- Task 5: tests/conftest.py exists, gobp_root fixture provisions schema files
- Task 6: test_lessons.py, test_prune.py, test_tool_lessons_extract.py use gobp_root fixture, no local helpers

Use venv Python:
  D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v

Expected: 166 tests passing throughout.

Stop on first failure. Report full wave audit summary when done.
```

## 4. Push

```powershell
cd D:\GoBP
git push origin main
```

---

# WHAT COMES NEXT

After Wave 7 pushed:
- **Wave 8** — MIHOS integration test: import 31 MIHOS docs, stress test all 14 tools with real data, extract lessons, benchmark against `MCP_TOOLS.md §10` performance targets.

---

*Wave 7 Brief v0.1*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
