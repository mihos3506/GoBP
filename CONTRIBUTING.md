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

## CLI commands

```bash
# Initialize a new GoBP project (seeds 16 TestKind + 1 Concept)
python -m gobp.cli init [--name NAME] [--force]

# Validate graph schema
python -m gobp.cli validate [--scope all|nodes|edges|references]

# Show project summary
python -m gobp.cli status
```

Uses `GOBP_PROJECT_ROOT` env var or current directory.

On `init`, GoBP seeds 16 universal TestKind nodes:
- **Functional** (6): Unit, Integration, E2E, Contract, Regression, Acceptance
- **Non-functional** (3): Performance, Accessibility, Compatibility
- **Process** (2): Smoke, Exploratory
- **Security** (5): Auth, Input Validation, Network, Encryption, API Security, Dependency

## Adding a platform-specific TestKind

```
node_upsert(type="TestKind", name="Widget Test", group="functional",
            scope="platform", platform="flutter", ...)
```

## Adding a TestCase

```
node_upsert(type="TestCase", name="Login returns token on valid credentials",
            kind_id="testkind:unit", covers="node:feat_login",
            status="DRAFT", priority="high",
            given="Valid email+password in system",
            when="loginService.login(email, password) called",
            then="Returns AuthToken with non-null accessToken")
```

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
