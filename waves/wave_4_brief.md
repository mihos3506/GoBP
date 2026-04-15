# WAVE 4 BRIEF — CLI + SCHEMA V2 + CONCEPT + TEST TAXONOMY

**Wave:** 4
**Title:** CLI (init/validate/status) + Schema v2 (Concept, TestKind, TestCase) + Universal Test Taxonomy + find() type filter + gobp_overview concepts
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 12 atomic tasks
**Estimated effort:** 5-6 hours

---

## CONTEXT

Wave 4 ships two major capabilities:

**Part A — CLI (Tasks 1–3):**
- `python -m gobp.cli init` — bootstrap `.gobp/` project
- `python -m gobp.cli validate` — schema check
- `python -m gobp.cli status` — project summary
- Unblocks Wave 8 Part B (MIHOS real import session)

**Part B — Schema v2 (Tasks 4–10):**
- 3 new core node types: `Concept`, `TestKind`, `TestCase`
- Universal test taxonomy: 16 TestKind seed nodes + 1 Concept node pre-populated on `gobp init`
- `core_nodes.yaml` schema_version 1.0 → 2.0
- 2 new edge types: `covers`, `of_kind`
- Migration step v1→v2 in `migrate.py`
- `find()` gets `type` filter parameter
- `gobp_overview` response gains `concepts` + `test_coverage` sections
- Multi-user readiness placeholders in `config.yaml`

**Part C — Docs + Tests (Tasks 11–12):**
- Tests for all new functionality (22 tests)
- CHANGELOG + CONTRIBUTING updates

---

## DESIGN DECISIONS (locked)

### Test taxonomy — 3 levels

```
Level 1: Universal (scope=universal)
  → GoBP core, pre-populated on gobp init for every project
  → 16 seed TestKind nodes, 4 groups

Level 2: Platform-specific (scope=platform)
  → Added by project when needed via node_upsert
  → e.g. Flutter Widget Test, Deno API Test

Level 3: Project-specific (scope=project)
  → Custom kinds per project via node_upsert
  → e.g. MIHOS Proof of Presence Verification
```

### Concept node — AI self-learning mechanism

`Concept` node stores **what a concept is** and **how AI should use it**. `gobp_overview` returns all Concepts — AI new to project learns framework without CEO re-explaining.

### Multi-user placeholders

`config.yaml` gains `owner`, `collaborators`, `access_model`, `project_id` — all `null`/empty in v1. Zero logic. Structure ready for v2 upgrade without data migration.

### TestCase status lifecycle

```
DRAFT → READY → PASSING | FAILING | SKIPPED | DEPRECATED
```

`automated: bool` — whether actual test code exists.

---

## CURSOR EXECUTION RULES (READ FIRST — NON-NEGOTIABLE)

### R1 — Sequential execution
Tasks 1 → 12 in order. No skipping, no reordering.

### R2 — Discovery before creation
Explorer subagent before creating any file. Read existing files first.

### R3 — 1 task = 1 commit
Tests pass → commit immediately with exact message from Brief.

### R4 — Docs are supreme authority
Conflict with `docs/SCHEMA.md` or `docs/MCP_TOOLS.md` → docs win, STOP and report.

### R5 — Document disagreement = STOP
Believe a doc has error → STOP, report observation, wait.

### R6 — 3 retries = STOP
Test fails 3 times → STOP, file stop report, wait for CEO relay to CTO.

### R7 — No scope creep
Implement exactly what Brief specifies. No extra node types, no extra CLI commands.

### R8 — Brief code blocks are authoritative
Disagree → STOP and escalate. Never substitute silently.

---

## STOP REPORT FORMAT

```
STOP — Wave 4 Task <N>
Rule triggered: R<N> — <rule name>
Completed so far: Tasks 1–<N-1> (committed)
Current task: Task <N> — <title>
What I was doing: <description>
What went wrong: <exact error>
What I tried: <list if R6>
Why I cannot proceed: <reason>
Current git state:
  Staged: <list>
  Unstaged: <list>
What I need from CEO/CTO: <specific question>
```

---

## AUTHORITATIVE SOURCE

- `docs/SCHEMA.md` — node/edge type structure
- `docs/ARCHITECTURE.md` — folder layout
- `docs/MCP_TOOLS.md` — gobp_overview + find specs
- `gobp/mcp/tools/read.py` — existing implementations to extend
- `gobp/core/migrate.py` — migration pattern

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # Expected: clean

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: 166 tests passing
```

---

## REQUIRED READING — WAVE START

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Execution rules |
| 2 | `docs/SCHEMA.md` | Node structure, id conventions |
| 3 | `docs/MCP_TOOLS.md` | gobp_overview + find specs |
| 4 | `docs/ARCHITECTURE.md` | .gobp/ folder layout |
| 5 | `gobp/schema/core_nodes.yaml` | Current node types |
| 6 | `gobp/core/migrate.py` | Migration pattern |
| 7 | `gobp/mcp/tools/read.py` | gobp_overview + find implementations |
| 8 | `tests/conftest.py` | gobp_root fixture pattern |
| 9 | `waves/wave_4_brief.md` | This file |

**Per-task reading:**

| Task | Must re-read before starting |
|---|---|
| Task 1 (init.py) | `docs/ARCHITECTURE.md`, `gobp/schema/core_nodes.yaml` |
| Task 2 (cli.py) | `gobp/core/init.py` just created |
| Task 3 (verify) | `gobp/cli.py` just created |
| Task 4 (schema v2) | `docs/SCHEMA.md`, current `core_nodes.yaml` + `core_edges.yaml` |
| Task 5 (migration) | `gobp/core/migrate.py` current state |
| Task 6 (seed) | `core_nodes.yaml` v2, `gobp/core/init.py` |
| Task 7 (find filter) | `docs/MCP_TOOLS.md` find spec, `gobp/mcp/tools/read.py` |
| Task 8 (overview) | `docs/MCP_TOOLS.md` gobp_overview spec, `gobp/mcp/tools/read.py` |
| Task 9 (smoke fix) | `tests/test_smoke.py` |
| Tasks 10–11 (tests+suite) | All modules being tested |
| Task 12 (docs) | `CHANGELOG.md`, `CONTRIBUTING.md` |

---

# TASKS

---

## TASK 1 — Create gobp/core/init.py

**Goal:** Init logic — creates `.gobp/` structure, copies schema, writes config.yaml with v2 fields.

**File to create:** `gobp/core/init.py`

```python
"""GoBP project initialization.

Creates .gobp/ folder structure for a new GoBP project.
Called by `python -m gobp.cli init`.

After init, project root can be used as GOBP_PROJECT_ROOT
for MCP server connections.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

INIT_SCHEMA_VERSION = 2  # Wave 4 introduces schema v2


def init_project(
    project_root: Path,
    project_name: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Initialize a new GoBP project at project_root.

    Creates .gobp/ dirs, config.yaml, schema files, and seeds
    universal TestKind nodes + Concept node.

    Args:
        project_root: Path where the project will be initialized.
        project_name: Project name. Defaults to folder name.
        force: If True, re-init even if .gobp/ already exists.

    Returns:
        Dict with ok, message, created, seeded_nodes, already_exists.
    """
    gobp_dir = project_root / ".gobp"

    if gobp_dir.exists() and not force:
        return {
            "ok": False,
            "message": (
                f".gobp/ already exists at {project_root}. "
                "Use --force to re-initialize."
            ),
            "created": [],
            "seeded_nodes": [],
            "already_exists": True,
        }

    created: list[str] = []

    for subdir in ("nodes", "edges", "history"):
        target = gobp_dir / subdir
        target.mkdir(parents=True, exist_ok=True)
        created.append(str(target.relative_to(project_root)))

    # config.yaml with v2 multi-user placeholders
    name = project_name or project_root.name
    config = {
        "project_name": name,
        "schema_version": INIT_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "gobp_version": "0.1.0",
        # Multi-user placeholders — null/inactive in v1, ready for v2 upgrade
        "owner": None,
        "collaborators": [],
        "access_model": "open",
        "project_id": None,
    }
    config_path = gobp_dir / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    created.append(str(config_path.relative_to(project_root)))

    # Copy schema files from package
    package_schema = Path(__file__).parent.parent / "schema"
    dest_schema = project_root / "gobp" / "schema"
    dest_schema.mkdir(parents=True, exist_ok=True)
    for schema_file in ("core_nodes.yaml", "core_edges.yaml"):
        src = package_schema / schema_file
        dst = dest_schema / schema_file
        if src.exists():
            shutil.copy(src, dst)
            created.append(str(dst.relative_to(project_root)))

    # Seed universal TestKind + Concept nodes
    seeded = _seed_universal_nodes(project_root)

    return {
        "ok": True,
        "message": f"Initialized GoBP project '{name}' at {project_root}",
        "created": created,
        "seeded_nodes": seeded,
        "already_exists": False,
    }


def _seed_universal_nodes(project_root: Path) -> list[str]:
    """Seed 16 universal TestKind nodes + 1 Concept node on project init.

    These encode universal software test taxonomy so any AI connecting
    to any GoBP project immediately understands what kinds of tests exist.

    Returns list of created node IDs.
    """
    now = datetime.now(timezone.utc).isoformat()
    nodes_dir = project_root / ".gobp" / "nodes"

    seeds = [
        # ── FUNCTIONAL GROUP (6 kinds) ────────────────────────────────────
        {
            "id": "testkind:unit",
            "type": "TestKind",
            "name": "Unit Test",
            "group": "functional",
            "scope": "universal",
            "description": "Tests a single function, method, or class in isolation. Fast, no external dependencies.",
            "template": {
                "given": "Known input state",
                "when": "Function called with specific input",
                "then": "Expected output or state change",
            },
            "seed_examples": [
                "test happy path",
                "test null/empty input",
                "test boundary values",
                "test error handling",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:integration",
            "type": "TestKind",
            "name": "Integration Test",
            "group": "functional",
            "scope": "universal",
            "description": "Tests multiple modules or services working together. Includes DB, API, or service interactions.",
            "template": {
                "given": "Real dependencies available",
                "when": "Components interact",
                "then": "Integrated behavior matches spec",
            },
            "seed_examples": [
                "test service A calls service B correctly",
                "test DB read after write",
                "test API returns correct response shape",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:e2e",
            "type": "TestKind",
            "name": "End-to-End Test",
            "group": "functional",
            "scope": "universal",
            "description": "Tests a complete user flow from UI to backend on real device or browser.",
            "template": {
                "given": "App launched, preconditions met",
                "when": "User completes full flow",
                "then": "Final state matches expected",
            },
            "seed_examples": [
                "test complete registration flow",
                "test payment flow end-to-end",
                "test critical user journey",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:contract",
            "type": "TestKind",
            "name": "Contract Test",
            "group": "functional",
            "scope": "universal",
            "description": "Verifies consumer and provider agree on API shape, fields, and types. Prevents integration breaks.",
            "template": {
                "given": "Consumer expectation defined",
                "when": "Provider response received",
                "then": "Response matches consumer contract",
            },
            "seed_examples": [
                "test API response has required fields",
                "test field types match contract",
                "test error response format",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:regression",
            "type": "TestKind",
            "name": "Regression Test",
            "group": "functional",
            "scope": "universal",
            "description": "Verifies new changes do not break existing functionality. Run after every change.",
            "template": {
                "given": "Feature was working before change",
                "when": "Change is deployed",
                "then": "Feature still works as before",
            },
            "seed_examples": [
                "re-run all unit tests after refactor",
                "verify login still works after auth change",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:acceptance",
            "type": "TestKind",
            "name": "Acceptance Test",
            "group": "functional",
            "scope": "universal",
            "description": "Validates software meets business requirements from end-user perspective.",
            "template": {
                "given": "User story defined",
                "when": "User performs the action",
                "then": "Acceptance criteria met",
            },
            "seed_examples": [
                "verify feature matches user story",
                "stakeholder sign-off on flow",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        # ── NON-FUNCTIONAL GROUP (3 kinds) ────────────────────────────────
        {
            "id": "testkind:performance",
            "type": "TestKind",
            "name": "Performance Test",
            "group": "non_functional",
            "scope": "universal",
            "description": "Measures responsiveness, speed, throughput, and stability under load.",
            "template": {
                "scenario": "Load profile description",
                "threshold": "Acceptable latency/throughput target",
                "tool": "Tool used (k6, Locust, etc.)",
            },
            "seed_examples": [
                "test response < 200ms at 100 concurrent users",
                "test app startup < 2s",
                "test API throughput under load",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:accessibility",
            "type": "TestKind",
            "name": "Accessibility Test",
            "group": "non_functional",
            "scope": "universal",
            "description": "Ensures usability for people with disabilities. Follows WCAG 2.1 AA.",
            "template": {
                "component": "UI element being tested",
                "standard": "WCAG criterion",
                "criterion": "Specific requirement",
                "tool": "axe-core, VoiceOver, etc.",
            },
            "seed_examples": [
                "test color contrast >= 4.5:1",
                "test screen reader compatibility",
                "test keyboard navigation",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:compatibility",
            "type": "TestKind",
            "name": "Compatibility Test",
            "group": "non_functional",
            "scope": "universal",
            "description": "Tests across devices, OS versions, screen sizes, and configurations.",
            "template": {
                "given": "Target device/OS/browser",
                "when": "Feature is used",
                "then": "Works correctly on target",
            },
            "seed_examples": [
                "test on Android 10+",
                "test on iOS 15+",
                "test on small screen 320px width",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        # ── PROCESS GROUP (2 kinds) ────────────────────────────────────────
        {
            "id": "testkind:smoke",
            "type": "TestKind",
            "name": "Smoke Test",
            "group": "process",
            "scope": "universal",
            "description": "Basic sanity check after deploy. Verifies critical paths before full testing.",
            "template": {
                "feature": "Critical feature",
                "check": "Minimum viable check",
                "pass_condition": "What passing looks like",
            },
            "seed_examples": [
                "app launches without crash",
                "login endpoint responds 200",
                "home screen loads",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:exploratory",
            "type": "TestKind",
            "name": "Exploratory Test",
            "group": "process",
            "scope": "universal",
            "description": "Unscripted manual testing to discover unexpected behavior.",
            "template": {
                "area": "Feature or flow being explored",
                "session_goal": "What to look for",
                "findings": "What was discovered",
            },
            "seed_examples": [
                "explore registration edge cases",
                "try unexpected user inputs",
                "explore error states",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        # ── SECURITY GROUP (5 sub-kinds) ──────────────────────────────────
        {
            "id": "testkind:security_auth",
            "type": "TestKind",
            "name": "Auth Security Test",
            "group": "security",
            "scope": "universal",
            "description": "Tests authentication, authorization, session management. Verifies only authorized users access resources. Covers JWT, OAuth, RBAC, brute force protection.",
            "template": {
                "attack_vector": "Type of auth attack",
                "precondition": "Initial state",
                "steps": "Attack steps",
                "expected_defense": "How system should respond",
            },
            "seed_examples": [
                "test unauthorized access returns 401",
                "test expired token rejected",
                "test role-based access control",
                "test brute force lockout after N attempts",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:security_input",
            "type": "TestKind",
            "name": "Input Security Test",
            "group": "security",
            "scope": "universal",
            "description": "Tests input validation and injection resistance. SQL injection, XSS, fuzzing. Verifies system rejects malicious inputs safely.",
            "template": {
                "input_type": "Type of malicious input",
                "field": "Input field being tested",
                "payload": "Attack payload",
                "expected": "System rejects safely",
            },
            "seed_examples": [
                "test SQL injection in login field",
                "test XSS in text input",
                "test fuzz API with random data",
                "test oversized input rejected",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:security_network",
            "type": "TestKind",
            "name": "Network Security Test",
            "group": "security",
            "scope": "universal",
            "description": "Tests communication layer security: TLS/HTTPS enforcement, no cleartext HTTP, certificate pinning, MITM protection. Critical for mobile apps.",
            "template": {
                "protocol": "Network protocol being tested",
                "check": "Security property to verify",
                "tool": "Proxy/scanner (Burp Suite, ZAP, Wireshark)",
                "expected": "Encrypted, certificate valid, no cleartext",
            },
            "seed_examples": [
                "test all traffic uses HTTPS not HTTP",
                "test TLS 1.2+ enforced",
                "test certificate pinning prevents MITM",
                "test no sensitive data in URL params or headers",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:security_encryption",
            "type": "TestKind",
            "name": "Encryption Test",
            "group": "security",
            "scope": "universal",
            "description": "Tests data encryption at rest and in transit. Verifies sensitive data (tokens, PII, GPS, photos, payment info) is encrypted in storage and transmission.",
            "template": {
                "data_type": "Type of sensitive data",
                "storage_or_transit": "at_rest | in_transit",
                "encryption_standard": "AES-256 / TLS 1.3 / etc.",
                "check": "How to verify encryption is applied",
            },
            "seed_examples": [
                "test auth token encrypted in local storage",
                "test PII not stored plaintext",
                "test GPS coords encrypted before transmitting",
                "test encryption key not hardcoded in source",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:security_api",
            "type": "TestKind",
            "name": "API Security Test",
            "group": "security",
            "scope": "universal",
            "description": "Tests API endpoint security per OWASP API Top 10: broken access control, excessive data exposure, rate limiting, injection, security misconfiguration.",
            "template": {
                "endpoint": "API endpoint being tested",
                "owasp_category": "OWASP API risk category",
                "attack": "Test attack or check description",
                "expected": "API handles safely",
            },
            "seed_examples": [
                "test endpoint requires valid JWT",
                "test rate limiting after 100 req/min",
                "test no excessive data exposure in response",
                "test CORS policy restricts origins",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        {
            "id": "testkind:security_dependency",
            "type": "TestKind",
            "name": "Dependency Security Test",
            "group": "security",
            "scope": "universal",
            "description": "Scans third-party libraries for known CVEs. Supply chain security. Ensures no vulnerable dependencies ship to production.",
            "template": {
                "package_manager": "pub | npm | pip | cargo",
                "scan_tool": "Snyk / OSV-Scanner / audit command",
                "threshold": "Severity level to block on (critical/high)",
                "expected": "No critical CVEs in dependencies",
            },
            "seed_examples": [
                "run pub audit on Flutter deps",
                "scan Deno imports for known CVEs",
                "check for hardcoded secrets in third-party libs",
            ],
            "platform": None,
            "extensible": True,
            "created": now, "updated": now,
        },
        # ── CONCEPT NODE ──────────────────────────────────────────────────
        {
            "id": "concept:test_taxonomy",
            "type": "Concept",
            "name": "Test Taxonomy",
            "definition": (
                "GoBP organizes software tests into 3 levels: "
                "Level 1 (universal) — applies to all projects, pre-seeded on init; "
                "Level 2 (platform) — specific to Flutter, Deno, Web, etc., added by project; "
                "Level 3 (project) — custom kinds unique to this project. "
                "TestKind nodes define categories. TestCase nodes are individual test instances."
            ),
            "usage_guide": (
                "To plan tests: (1) find(type='TestKind') to see available kinds. "
                "(2) Create TestCase nodes linked via of_kind edge to TestKind "
                "and via covers edge to the Feature/Node being tested. "
                "(3) Add platform kinds: node_upsert(type='TestKind', scope='platform', platform='flutter'). "
                "(4) Check coverage: find(type='TestCase', covers='feat:X') "
                "to see all tests for a feature."
            ),
            "applies_to": ["TestKind", "TestCase"],
            "seed_values": ["functional", "non_functional", "security", "process"],
            "extensible": True,
            "created": now, "updated": now,
        },
    ]

    created_ids: list[str] = []
    for node in seeds:
        node_id = node["id"]
        slug = node_id.replace(":", "_")
        node_path = nodes_dir / f"{slug}.md"
        import yaml as _yaml
        fm = _yaml.dump(node, allow_unicode=True, default_flow_style=False)
        node_path.write_text(f"---\n{fm}---\n", encoding="utf-8")
        created_ids.append(node_id)

    return created_ids
```

**Acceptance criteria:**
- `gobp/core/init.py` created
- `INIT_SCHEMA_VERSION = 2`
- `init_project()` creates dirs + config.yaml + schema files + seeds 17 nodes
- `config.yaml` has multi-user placeholder fields (all null/empty)
- Returns `ok=False` if `.gobp/` exists and `force=False`
- Returns `seeded_nodes` list of 17 IDs

**Commit message:**
```
Wave 4 Task 1: create gobp/core/init.py

- init_project(root, name, force): creates .gobp/ structure
- config.yaml: schema_version=2, multi-user placeholders (owner, collaborators, access_model, project_id = null)
- Copies gobp/schema/*.yaml from package
- _seed_universal_nodes(): seeds 16 TestKind + 1 Concept = 17 nodes
- Returns seeded_nodes list
```

---

## TASK 2 — Create gobp/cli.py + gobp/__main__.py

**Goal:** CLI entry point with 3 subcommands.

**File to create:** `gobp/cli.py`

```python
"""GoBP command-line interface.

Usage:
    python -m gobp.cli init [--name NAME] [--force]
    python -m gobp.cli validate [--scope SCOPE]
    python -m gobp.cli status

Uses GOBP_PROJECT_ROOT env var or current directory.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _get_project_root() -> Path:
    """Get project root from env var or current directory."""
    env_root = os.environ.get("GOBP_PROJECT_ROOT")
    if env_root:
        return Path(env_root)
    return Path.cwd()


def cmd_init(args: argparse.Namespace) -> int:
    """Handle `gobp init` command."""
    from gobp.core.init import init_project

    root = _get_project_root()
    result = init_project(project_root=root, project_name=args.name, force=args.force)

    if result["ok"]:
        print(result["message"])
        seeded = result.get("seeded_nodes", [])
        print(f"Seeded {len(seeded)} universal nodes (TestKind + Concept)")
        print("\nCreated:")
        for path in result["created"]:
            print(f"  {path}")
        print(f"\nNext: set GOBP_PROJECT_ROOT={root} in your MCP client config.")
        return 0
    else:
        print(f"Error: {result['message']}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Handle `gobp validate` command."""
    from gobp.core.graph import GraphIndex
    from gobp.mcp.tools.maintain import validate

    root = _get_project_root()
    if not (root / ".gobp").exists():
        print(f"Error: No .gobp/ at {root}. Run `python -m gobp.cli init` first.", file=sys.stderr)
        return 1

    print(f"Validating {root}...")
    try:
        index = GraphIndex.load_from_disk(root)
    except Exception as e:
        print(f"Error loading graph: {e}", file=sys.stderr)
        return 1

    result = validate(index, root, {"scope": args.scope, "severity_filter": "all"})
    if not result["ok"]:
        print(f"Error: {result.get('error', 'unknown')}", file=sys.stderr)
        return 1

    issues = result.get("issues", [])
    hard = [i for i in issues if i.get("severity") == "hard"]
    warnings = [i for i in issues if i.get("severity") == "warning"]

    if not issues:
        print(f"Graph valid — {len(index.all_nodes())} nodes, {len(index.all_edges())} edges, 0 issues")
        return 0

    print(f"Found {len(hard)} hard errors, {len(warnings)} warnings:\n")
    for issue in hard:
        nid = issue.get("node_id", issue.get("edge", "?"))
        print(f"  [ERROR] {nid}: {issue['message']}")
    for issue in warnings:
        nid = issue.get("node_id", issue.get("edge", "?"))
        print(f"  [WARN]  {nid}: {issue['message']}")
    return 1 if hard else 0


def cmd_status(args: argparse.Namespace) -> int:
    """Handle `gobp status` command."""
    from gobp.core.graph import GraphIndex
    import yaml

    root = _get_project_root()
    if not (root / ".gobp").exists():
        print(f"Error: No .gobp/ at {root}. Run `python -m gobp.cli init` first.", file=sys.stderr)
        return 1

    config: dict = {}
    config_path = root / ".gobp" / "config.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    try:
        index = GraphIndex.load_from_disk(root)
        nodes = index.all_nodes()
        edges = index.all_edges()
    except Exception as e:
        print(f"Error loading graph: {e}", file=sys.stderr)
        return 1

    type_counts: dict[str, int] = {}
    for n in nodes:
        t = n.get("type", "Unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    sessions = sorted(
        [n for n in nodes if n.get("type") == "Session"],
        key=lambda s: s.get("updated", ""),
        reverse=True,
    )
    last = sessions[0] if sessions else None
    created_at = str(config.get("created_at", "?"))[:10]

    print(f"\nGoBP Project: {config.get('project_name', root.name)}")
    print(f"Root:         {root}")
    print(f"Schema:       v{config.get('schema_version', '?')}  |  Created: {created_at}")
    print(f"\nGraph: {len(nodes)} nodes, {len(edges)} edges")
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}")
    if last:
        print(f"\nLast session: {last.get('id', '?')}")
        print(f"  Goal:   {last.get('goal', '?')[:60]}")
        print(f"  Status: {last.get('status', '?')}  Actor: {last.get('actor', '?')}")
    else:
        print("\nNo sessions yet.")
    print()
    return 0


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(prog="gobp", description="GoBP CLI")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    p_init = sub.add_parser("init", help="Initialize a new GoBP project")
    p_init.add_argument("--name", default=None)
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_val = sub.add_parser("validate", help="Validate graph schema")
    p_val.add_argument("--scope", choices=["all", "nodes", "edges", "references"], default="all")
    p_val.set_defaults(func=cmd_validate)

    p_stat = sub.add_parser("status", help="Show project summary")
    p_stat.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

**File to create:** `gobp/__main__.py`

```python
"""Module entry point — allows `python -m gobp.cli`."""
from gobp.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
```

**Commit message:**
```
Wave 4 Task 2: create gobp/cli.py + gobp/__main__.py

- 3 subcommands: init, validate, status
- Uses GOBP_PROJECT_ROOT env var or cwd
- cmd_init prints seeded node count
```

---

## TASK 3 — Verify CLI and no regression

```powershell
D:/GoBP/venv/Scripts/python.exe -m gobp.cli --help
D:/GoBP/venv/Scripts/python.exe -m gobp.cli init --help
D:/GoBP/venv/Scripts/python.exe -m gobp.cli validate --help
D:/GoBP/venv/Scripts/python.exe -m gobp.cli status --help

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: 166 tests passing
```

**Commit message:**
```
Wave 4 Task 3: verify CLI help and no regression — 166 tests passing
```

---

## TASK 4 — Update core_nodes.yaml v2 + core_edges.yaml

**Goal:** Add Concept, TestKind, TestCase to node schema. Add covers, of_kind to edge schema.

**File to modify:** `gobp/schema/core_nodes.yaml`

**Step 1:** Change `schema_version: "1.0"` → `schema_version: "2.0"`

**Step 2:** Add these 3 types after the `Lesson` entry:

```yaml
  Concept:
    description: "A defined concept stored for AI orientation and framework understanding"
    id_prefix: "concept"
    parent: null

    required:
      id:
        type: "str"
        pattern: "^concept:.+$"
      type:
        type: "str"
        enum_values: ["Concept"]
      name:
        type: "str"
      definition:
        type: "str"
        description: "What this concept means"
      usage_guide:
        type: "str"
        description: "How AI should use this concept"
      created:
        type: "timestamp"
      updated:
        type: "timestamp"

    optional:
      applies_to:
        type: "list[str]"
        default: []
      seed_values:
        type: "list[str]"
        default: []
      extensible:
        type: "bool"
        default: true
      tags:
        type: "list[str]"
        default: []

  TestKind:
    description: "A category of software test with template and seed examples"
    id_prefix: "testkind"
    parent: null

    required:
      id:
        type: "str"
        pattern: "^testkind:.+$"
      type:
        type: "str"
        enum_values: ["TestKind"]
      name:
        type: "str"
      group:
        type: "enum"
        enum_values: ["functional", "non_functional", "security", "process"]
      scope:
        type: "enum"
        enum_values: ["universal", "platform", "project"]
      description:
        type: "str"
      template:
        type: "dict"
      created:
        type: "timestamp"
      updated:
        type: "timestamp"

    optional:
      platform:
        type: "str"
        default: null
      seed_examples:
        type: "list[str]"
        default: []
      extensible:
        type: "bool"
        default: true
      tags:
        type: "list[str]"
        default: []

  TestCase:
    description: "A specific test instance linked to a TestKind and a feature/node"
    id_prefix: "tc"
    parent: null

    required:
      id:
        type: "str"
        pattern: "^tc:.+$"
      type:
        type: "str"
        enum_values: ["TestCase"]
      name:
        type: "str"
      kind_id:
        type: "node_ref"
        description: "TestKind this test belongs to"
      covers:
        type: "node_ref"
        description: "Feature/Node being tested"
      status:
        type: "enum"
        enum_values: ["DRAFT", "READY", "PASSING", "FAILING", "SKIPPED", "DEPRECATED"]
      priority:
        type: "enum"
        enum_values: ["low", "medium", "high", "critical"]
      created:
        type: "timestamp"
      updated:
        type: "timestamp"

    optional:
      given:
        type: "str"
      when:
        type: "str"
      then:
        type: "str"
      scenario:
        type: "str"
        description: "Alternative to Given/When/Then for non-BDD kinds"
      automated:
        type: "bool"
        default: false
      code_ref:
        type: "str"
        description: "e.g. test/auth_test.dart#login_valid"
      tags:
        type: "list[str]"
        default: []
```

**File to modify:** `gobp/schema/core_edges.yaml`

Add these 2 edge types after `references`:

```yaml
  covers:
    description: "TestCase covers/validates a Feature or Node"
    directional: true
    cardinality: "many_to_one"
    allowed_node_types: ["TestCase->Node", "TestCase->Idea", "TestCase->Decision"]

    required:
      from:
        type: "node_ref"
      to:
        type: "node_ref"
      type:
        type: "str"
        enum_values: ["covers"]

    optional:
      coverage_type:
        type: "str"
        description: "happy_path | error_path | boundary | security"

  of_kind:
    description: "TestCase belongs to a TestKind"
    directional: true
    cardinality: "many_to_one"
    allowed_node_types: ["TestCase->TestKind"]

    required:
      from:
        type: "node_ref"
      to:
        type: "node_ref"
      type:
        type: "str"
        enum_values: ["of_kind"]
```

**Verify:**
```powershell
D:/GoBP/venv/Scripts/python.exe -c "
import yaml
n = yaml.safe_load(open('gobp/schema/core_nodes.yaml'))
e = yaml.safe_load(open('gobp/schema/core_edges.yaml'))
print('Nodes:', sorted(n['node_types'].keys()))
print('Edges:', sorted(e['edge_types'].keys()))
print('Version:', n['schema_version'])
"
# Expected nodes: 9 types including Concept, TestKind, TestCase
# Expected edges: 7 types including covers, of_kind
# Expected version: 2.0
```

**Commit message:**
```
Wave 4 Task 4: schema v2 — Concept + TestKind + TestCase + covers + of_kind

- core_nodes.yaml: version 1.0 → 2.0, add Concept/TestKind/TestCase (9 total types)
- core_edges.yaml: add covers (TestCase→Node) + of_kind (TestCase→TestKind) (7 total types)
- TestKind: group enum (functional/non_functional/security/process), scope enum (universal/platform/project)
- TestCase: kind_id, covers, status DRAFT→PASSING/FAILING, given/when/then, automated, code_ref
```

---

## TASK 5 — Update migrate.py v1→v2

**File to modify:** `gobp/core/migrate.py`

**Change 1:** `CURRENT_SCHEMA_VERSION = 1` → `CURRENT_SCHEMA_VERSION = 2`

**Change 2:** Add migration function before `run_migration()`:

```python
def _migrate_v1_to_v2(gobp_root: Path) -> None:
    """Migrate schema v1 → v2.

    v2 adds Concept, TestKind, TestCase node types and covers, of_kind edges.
    All changes are additive — no existing nodes need modification.
    Seed nodes are NOT added here (init does that for new projects).
    """
    pass  # Additive schema change — no data transformation needed
```

**Change 3:** Replace the empty `migration_steps = {}` with:

```python
    migration_steps = {
        "v1_to_v2": _migrate_v1_to_v2,
    }
```

**Also update `tests/test_migrate.py`** — find all assertions checking `CURRENT_SCHEMA_VERSION == 1` and change to `== 2`.

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_migrate.py -v
# Expected: 6 tests passing
```

**Commit message:**
```
Wave 4 Task 5: migrate.py v1→v2

- CURRENT_SCHEMA_VERSION: 1 → 2
- _migrate_v1_to_v2: additive, no data transform needed
- migration_steps dict now has v1_to_v2 entry
- test_migrate.py: updated version assertions to 2
```

---

## TASK 6 — Add type filter to find() tool

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `docs/MCP_TOOLS.md` find spec before modifying.**

Find the `find()` function and replace with:

```python
def find(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Search nodes by keyword with optional type filter.

    Input:
        query: str — search term (required)
        limit: int — max results (default 20)
        type: str — filter by node type, e.g. "TestCase", "TestKind" (optional)

    Output:
        ok, nodes, count
    """
    query = args.get("query", "")
    if not query:
        return {"ok": False, "error": "Missing required field: query"}

    limit = int(args.get("limit", 20))
    type_filter = args.get("type", None)

    query_lower = query.lower()
    matches = []

    for node in index.all_nodes():
        # Type filter first (cheap)
        if type_filter and node.get("type") != type_filter:
            continue

        # Text search across key fields
        node_id = node.get("id", "")
        node_name = node.get("name", "")
        searchable = f"{node_id} {node_name}".lower()
        for field in ("topic", "subject", "title", "description", "definition", "group"):
            val = node.get(field, "")
            if val:
                searchable += f" {str(val).lower()}"

        if query_lower in searchable:
            matches.append({
                "id": node_id,
                "type": node.get("type", ""),
                "name": node_name,
                "status": node.get("status", ""),
            })

        if len(matches) >= limit:
            break

    return {"ok": True, "matches": matches, "count": len(matches)}
```

**Also update `find` tool `inputSchema`** in `server.py` — add `type` to properties:

```python
"type": {
    "type": "string",
    "description": "Filter by node type, e.g. 'TestCase', 'TestKind', 'Decision'",
},
```

**Commit message:**
```
Wave 4 Task 6: add type filter to find() tool

- find() accepts optional 'type' param for structured queries
- Type filter applied before text search (efficient)
- Searchable fields extended: topic, subject, title, description, definition, group
- server.py find schema updated with type property
- Enables: find(query="security", type="TestKind")
```

---

## TASK 7 — Add concepts + test_coverage to gobp_overview

**File to modify:** `gobp/mcp/tools/read.py`

**Re-read `docs/MCP_TOOLS.md` gobp_overview spec before modifying.**

Find `gobp_overview()`. Before the `return` statement, add:

```python
    # Concepts — for AI orientation
    concept_nodes = [n for n in index.all_nodes() if n.get("type") == "Concept"]
    concepts = [
        {
            "id": n.get("id", ""),
            "name": n.get("name", ""),
            "definition": _truncate(n.get("definition", ""), 200),
            "usage_guide": _truncate(n.get("usage_guide", ""), 300),
            "applies_to": n.get("applies_to", []),
        }
        for n in concept_nodes[:10]
    ]

    # Test coverage summary
    test_kind_nodes = [n for n in index.all_nodes() if n.get("type") == "TestKind"]
    kinds_by_group: dict[str, int] = {}
    for tk in test_kind_nodes:
        g = tk.get("group", "unknown")
        kinds_by_group[g] = kinds_by_group.get(g, 0) + 1

    test_case_nodes = [n for n in index.all_nodes() if n.get("type") == "TestCase"]
    cases_by_status: dict[str, int] = {}
    for tc in test_case_nodes:
        s = tc.get("status", "DRAFT")
        cases_by_status[s] = cases_by_status.get(s, 0) + 1
```

**Add to the return dict** (after `suggested_next_queries`):

```python
        "concepts": concepts,
        "test_coverage": {
            "kinds_available": len(test_kind_nodes),
            "kinds_by_group": kinds_by_group,
            "test_cases_total": len(test_case_nodes),
            "test_cases_by_status": cases_by_status,
        },
```

**Commit message:**
```
Wave 4 Task 7: gobp_overview — add concepts + test_coverage sections

- concepts[]: max 10 Concept nodes with definition + usage_guide
- test_coverage: kinds_available, kinds_by_group, test_cases_total, test_cases_by_status
- AI connects → immediately sees framework concepts and test taxonomy
- No breaking changes to existing output fields
```

---

## TASK 8 — Update smoke tests for schema v2

**File to modify:** `tests/test_smoke.py`

Three changes:

1. Find `expected_types = {"Node", "Idea", ...}` in `test_core_nodes_yaml_valid` → add `"Concept", "TestKind", "TestCase"`

2. Find `expected_types = {"relates_to", ...}` in `test_core_edges_yaml_valid` → add `"covers", "of_kind"`

3. Find `assert data["schema_version"] == "1.0"` → change to `"2.0"`

```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_smoke.py -v
# Expected: all smoke tests passing
```

**Commit message:**
```
Wave 4 Task 8: update smoke tests for schema v2

- test_core_nodes_yaml_valid: expects 9 types (+ Concept, TestKind, TestCase)
- test_core_edges_yaml_valid: expects 7 types (+ covers, of_kind)
- schema_version check: "1.0" → "2.0"
```

---

## TASK 9 — Create tests/test_wave4.py

**File to create:** `tests/test_wave4.py`

```python
"""Tests for Wave 4: CLI, schema v2, TestKind/TestCase/Concept, find type filter, gobp_overview concepts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from gobp.core.init import init_project, INIT_SCHEMA_VERSION
from gobp.core.graph import GraphIndex
from gobp.mcp.tools import read as tools_read


# ── init_project tests ────────────────────────────────────────────────────────

def test_init_creates_structure(tmp_path: Path):
    """init_project creates all .gobp/ subdirs."""
    result = init_project(tmp_path)
    assert result["ok"] is True
    assert (tmp_path / ".gobp" / "nodes").is_dir()
    assert (tmp_path / ".gobp" / "edges").is_dir()
    assert (tmp_path / ".gobp" / "history").is_dir()


def test_init_config_schema_version_2(tmp_path: Path):
    """config.yaml has schema_version=2."""
    init_project(tmp_path)
    config = yaml.safe_load((tmp_path / ".gobp" / "config.yaml").read_text())
    assert config["schema_version"] == 2
    assert INIT_SCHEMA_VERSION == 2


def test_init_config_multiuser_placeholders(tmp_path: Path):
    """config.yaml has multi-user placeholder fields all null/empty."""
    init_project(tmp_path)
    config = yaml.safe_load((tmp_path / ".gobp" / "config.yaml").read_text())
    assert "owner" in config and config["owner"] is None
    assert "collaborators" in config and config["collaborators"] == []
    assert "access_model" in config and config["access_model"] == "open"
    assert "project_id" in config and config["project_id"] is None


def test_init_seeds_17_nodes(gobp_root: Path):
    """gobp init seeds 16 TestKind + 1 Concept = 17 nodes."""
    result = init_project(gobp_root, force=True)
    assert result["ok"] is True
    seeded = result.get("seeded_nodes", [])
    assert len(seeded) == 17
    assert len([s for s in seeded if s.startswith("testkind:")]) == 16
    assert len([s for s in seeded if s.startswith("concept:")]) == 1


def test_init_seeded_kinds_loadable(gobp_root: Path):
    """Seeded TestKind nodes load correctly via GraphIndex."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    kinds = [n for n in index.all_nodes() if n.get("type") == "TestKind"]
    assert len(kinds) == 16


def test_init_all_groups_present(gobp_root: Path):
    """All 4 groups present in seeded TestKind nodes."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    groups = {n.get("group") for n in index.all_nodes() if n.get("type") == "TestKind"}
    assert "functional" in groups
    assert "non_functional" in groups
    assert "security" in groups
    assert "process" in groups


def test_init_security_kinds_count(gobp_root: Path):
    """Security group has exactly 5 TestKind nodes."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    sec = [n for n in index.all_nodes() if n.get("type") == "TestKind" and n.get("group") == "security"]
    assert len(sec) == 5


def test_init_all_universal_scope(gobp_root: Path):
    """All seeded TestKind nodes have scope=universal."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    for n in index.all_nodes():
        if n.get("type") == "TestKind":
            assert n.get("scope") == "universal", f"{n['id']} has wrong scope: {n.get('scope')}"


def test_init_fails_if_exists(tmp_path: Path):
    """Second init without force returns ok=False."""
    init_project(tmp_path)
    result = init_project(tmp_path)
    assert result["ok"] is False
    assert result["already_exists"] is True


def test_init_force_reinits(tmp_path: Path):
    """Init with force=True succeeds even if .gobp/ exists."""
    init_project(tmp_path)
    result = init_project(tmp_path, force=True)
    assert result["ok"] is True


# ── find() type filter tests ──────────────────────────────────────────────────

def test_find_type_filter_testkind(gobp_root: Path):
    """find(type='TestKind') returns only TestKind nodes."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "test", "type": "TestKind"})
    assert result["ok"] is True
    for node in result["matches"]:
        assert node["type"] == "TestKind"


def test_find_type_filter_concept(gobp_root: Path):
    """find(type='Concept') returns only Concept nodes."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "taxonomy", "type": "Concept"})
    assert result["ok"] is True
    for node in result["matches"]:
        assert node["type"] == "Concept"


def test_find_type_filter_security_kinds(gobp_root: Path):
    """find(query='security', type='TestKind') returns security TestKind nodes."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "security", "type": "TestKind"})
    assert result["ok"] is True
    assert result["count"] >= 1


def test_find_type_filter_no_match(gobp_root: Path):
    """find(type='Session') returns empty when no sessions exist."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.find(index, gobp_root, {"query": "session", "type": "Session"})
    assert result["ok"] is True
    assert result["count"] == 0


# ── gobp_overview tests ───────────────────────────────────────────────────────

def test_gobp_overview_has_concepts(gobp_root: Path):
    """gobp_overview returns concepts array with at least 1 entry."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.gobp_overview(index, gobp_root, {})
    assert result["ok"] is True
    assert "concepts" in result
    assert len(result["concepts"]) >= 1


def test_gobp_overview_has_test_coverage(gobp_root: Path):
    """gobp_overview returns test_coverage with 16 kinds."""
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)
    result = tools_read.gobp_overview(index, gobp_root, {})
    assert result["ok"] is True
    assert "test_coverage" in result
    tc = result["test_coverage"]
    assert tc["kinds_available"] == 16
    assert "security" in tc["kinds_by_group"]
    assert "functional" in tc["kinds_by_group"]
    assert tc["kinds_by_group"]["security"] == 5


# ── CLI subprocess tests ──────────────────────────────────────────────────────

def _cli(args: list[str], env_root: str | None = None):
    import os
    env = os.environ.copy()
    if env_root:
        env["GOBP_PROJECT_ROOT"] = env_root
    r = subprocess.run([sys.executable, "-m", "gobp.cli"] + args, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


def test_cli_help():
    rc, out, _ = _cli(["--help"])
    assert rc == 0
    assert "init" in out and "validate" in out and "status" in out


def test_cli_init_creates_project(tmp_path: Path):
    rc, out, err = _cli(["init", "--name", "test"], env_root=str(tmp_path))
    assert rc == 0, f"err: {err}"
    assert (tmp_path / ".gobp" / "nodes").is_dir()


def test_cli_init_prints_seeded_count(tmp_path: Path):
    rc, out, _ = _cli(["init"], env_root=str(tmp_path))
    assert rc == 0
    assert "17" in out or "Seeded" in out


def test_cli_status_shows_nodes(tmp_path: Path):
    init_project(tmp_path)
    rc, out, err = _cli(["status"], env_root=str(tmp_path))
    assert rc == 0, f"err: {err}"
    assert "nodes" in out.lower() or "GoBP" in out


def test_cli_validate_clean_project(tmp_path: Path):
    init_project(tmp_path)
    rc, out, err = _cli(["validate"], env_root=str(tmp_path))
    assert rc == 0, f"err: {err}\nout: {out}"
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave4.py -v
# Expected: 22 tests passing
```

**Commit message:**
```
Wave 4 Task 9: create tests/test_wave4.py — 22 tests

- init: structure, schema_version=2, multi-user fields, seeds 17 nodes,
  all groups present, 5 security kinds, all scope=universal, force reinit
- find type filter: TestKind, Concept, security kinds, no-match Session
- gobp_overview: concepts[] present, test_coverage with 16 kinds + security=5
- CLI: help, init creates project, prints seeded count, status shows nodes, validate clean
```

---

## TASK 10 — Run full test suite + fix regressions

```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
```

If any existing test fails due to schema version change (e.g. `test_smoke.py` version checks) → fix expected values only. Each fix committed separately with message:
`Wave 4 Task 10 fix: update <test_name> for schema v2`

Final expected count: **166 + 22 = 188 tests passing**

**Commit message:**
```
Wave 4 Task 10: full suite green — 188 tests passing after schema v2
```

---

## TASK 11 — Update CONTRIBUTING.md + CHANGELOG.md

**CONTRIBUTING.md** — add after "Running tests" section:

```markdown
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
```

**CHANGELOG.md** — prepend after `# CHANGELOG` header:

```markdown
## [Wave 4] — CLI + Schema v2 + Universal Test Taxonomy — 2026-04-15

### Added
- `gobp/core/init.py` — `init_project()`: bootstrap .gobp/ structure with v2 config
- `gobp/cli.py` — 3 CLI commands: `init`, `validate`, `status`
- `gobp/__main__.py` — module entry point
- Schema v2: 3 new core node types: `Concept`, `TestKind`, `TestCase`
- Schema v2: 2 new edge types: `covers` (TestCase→Node), `of_kind` (TestCase→TestKind)
- 16 universal TestKind seed nodes auto-created on `gobp init` (4 groups: functional/non_functional/security/process)
- 5 security TestKind kinds: Auth, Input Validation, Network, Encryption, API Security, Dependency
- 1 `concept:test_taxonomy` node explaining AI how to use TestKind/TestCase
- `find()`: new `type` filter parameter — enables `find(query="login", type="TestCase")`
- `gobp_overview`: new `concepts[]` and `test_coverage{}` sections
- Multi-user placeholders in `config.yaml`: owner, collaborators, access_model, project_id (all null, ready for v2)
- `tests/test_wave4.py`: 22 tests

### Changed
- `core_nodes.yaml`: schema_version 1.0 → 2.0, 6 → 9 node types
- `core_edges.yaml`: 5 → 7 edge types
- `migrate.py`: CURRENT_SCHEMA_VERSION 1 → 2, v1→v2 migration step added

### Total after wave: 14 MCP tools, 188 tests passing
```

**Commit message:**
```
Wave 4 Task 11: update CONTRIBUTING.md + CHANGELOG.md

- CONTRIBUTING.md: CLI commands, TestKind/TestCase usage, seed list
- CHANGELOG.md: Wave 4 full entry
```

---

## TASK 12 — Final verification + update tracker

```powershell
# All tests pass
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: 188 tests passing

# Schema v2 correct
D:/GoBP/venv/Scripts/python.exe -c "
import yaml
n = yaml.safe_load(open('gobp/schema/core_nodes.yaml'))
e = yaml.safe_load(open('gobp/schema/core_edges.yaml'))
print('Node types:', len(n['node_types']), sorted(n['node_types'].keys()))
print('Edge types:', len(e['edge_types']), sorted(e['edge_types'].keys()))
print('Version:', n['schema_version'])
"

# CLI + init smoke test
$env:GOBP_PROJECT_ROOT = 'C:\tmp\wave4_final_test'
New-Item -ItemType Directory -Force -Path $env:GOBP_PROJECT_ROOT
D:/GoBP/venv/Scripts/python.exe -m gobp.cli init --name 'wave4-test'
D:/GoBP/venv/Scripts/python.exe -m gobp.cli status
# Expected: 17 nodes (16 TestKind + 1 Concept)

# Git log
git log --oneline | Select-Object -First 14
```

**Commit message:**
```
Wave 4 Task 12: final verification — 188 tests, schema v2, CLI functional
```

---

# POST-WAVE SUMMARY

After Wave 4:
- **14 MCP tools** (unchanged)
- **188 tests passing**
- **9 node types** (was 6: added Concept, TestKind, TestCase)
- **7 edge types** (was 5: added covers, of_kind)
- **`gobp init` seeds 17 nodes** every new project
- **`find(type=X)`** enables structured queries
- **`gobp_overview`** returns concepts + test taxonomy summary
- **Multi-user placeholders** ready for future v2

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief vào repo

```powershell
cd D:\GoBP
# Save wave_4_brief.md to D:\GoBP\waves\wave_4_brief.md

git add waves/wave_4_brief.md
git commit -m "Add Wave 4 Brief v2.0 — CLI + Schema v2 + Test Taxonomy"
git push origin main
```

## 2. Dispatch Cursor

Cursor IDE → Ctrl+L → paste:

```
Read .cursorrules and waves/wave_4_brief.md first.
Also read: docs/SCHEMA.md, docs/MCP_TOOLS.md, docs/ARCHITECTURE.md,
gobp/schema/core_nodes.yaml, gobp/schema/core_edges.yaml,
gobp/core/migrate.py, gobp/mcp/tools/read.py, tests/conftest.py.

Execute ALL 12 tasks of Wave 4 sequentially.
Rules:
- Use explorer subagent before creating any new file
- Re-read per-task docs (REQUIRED READING table) before each task
- If conflict with docs/SCHEMA.md or docs/MCP_TOOLS.md → docs win, STOP (R4)
- If doc appears to have error → STOP and report (R5)
- If tests fail 3 times → STOP and report (R6)
- 1 task = 1 commit, message must match Brief exactly
- Report full wave summary only after Task 12

Begin Task 1.
```

## 3. Audit Claude CLI

```powershell
cd D:\GoBP
claude
```

```
Audit Wave 4. Read CLAUDE.md, waves/wave_4_brief.md, docs/SCHEMA.md, docs/MCP_TOOLS.md.

Audit Tasks 1–12 sequentially.

Critical checks:
- Task 1: init.py exists, config.yaml has schema_version=2 + multi-user fields, seeds 17 nodes
- Task 2: cli.py + __main__.py exist, 3 subcommands
- Task 3: --help exits 0, no regression on 166 tests
- Task 4: core_nodes.yaml has 9 types + version 2.0, core_edges.yaml has 7 types
- Task 5: migrate.py CURRENT_SCHEMA_VERSION=2, v1_to_v2 step, test_migrate.py passes
- Task 6: find() accepts type param, filters correctly, server.py schema updated
- Task 7: gobp_overview returns concepts[] and test_coverage{}
- Task 8: smoke tests updated for 9 node types, 7 edge types, version 2.0
- Task 9: test_wave4.py exists, 22 tests passing
- Task 10: 188 total tests passing, no regressions
- Task 11: CONTRIBUTING.md + CHANGELOG.md updated
- Task 12: final verification passes

Use venv:
  D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
Expected: 188 tests passing.

Stop on first failure. Report WAVE 4 AUDIT COMPLETE when done.
```

## 4. Push

```powershell
cd D:\GoBP
git push origin main
```

---

# WHAT COMES NEXT

```
Wave 8  — MIHOS integration test (Part A: automated, Part B: gobp init + real import)
Wave 9A — SQLite persistent index + LRU cache (performance for 10k+ nodes)
```

---

*Wave 4 Brief v2.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
