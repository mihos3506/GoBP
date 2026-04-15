# WAVE 8 BRIEF — MIHOS INTEGRATION TEST

**Wave:** 8
**Title:** MIHOS Integration Test — Performance Benchmark + Real Import + Lessons Extraction
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 7 atomic tasks
**Estimated effort:** 3-4 hours

---

## CONTEXT

Waves 0–7 shipped GoBP v1: 14 MCP tools, 166 tests, full documentation. Wave 8 is the **final validation wave** — proving GoBP works against real MIHOS data, not just synthetic test fixtures.

Wave 8 has two distinct parts:

**Part A — Automated (Tasks 1–5, Cursor executes):**
- Performance benchmark test suite against `MCP_TOOLS.md §10` targets
- Schema extension test: MIHOS-specific node type as extension of GoBP core
- Integration test: all 14 tools called in sequence against a realistic populated graph
- Shared test fixture: `mihos_root` with ~30 nodes and ~40 edges (realistic scale)

**Part B — Manual (Tasks 6–7, CEO executes with AI):**
- Real MIHOS doc import session (31 docs → Document nodes)
- lessons_extract run on built graph → candidate Lessons logged

**Part B is NOT Cursor work.** It is a runtime session where CEO connects an MCP client to a real GoBP project and uses the tools as designed. Instructions for Part B are in Tasks 6–7 below.

**In scope:**
- `tests/test_performance.py` — latency benchmarks for all 14 tools
- `tests/test_integration.py` — end-to-end tool flow test
- `tests/fixtures/mihos_fixture.py` — realistic populated graph fixture (~30 nodes)
- MIHOS schema extension file: `gobp/schema/extensions/mihos.yaml`
- Manual import session guide (Task 6)
- Lessons extraction session guide (Task 7)
- `CHANGELOG.md` update for Wave 8

**NOT in scope:**
- Extracting all MIHOS nodes from all 31 docs (multi-session manual work)
- Modifying any foundational GoBP docs
- Adding new MCP tools
- CLI commands

---

## CURSOR EXECUTION RULES (READ FIRST — NON-NEGOTIABLE)

### R1 — Sequential execution
Execute Task 1 → Task 2 → ... → Task 5 in order. Tasks 6–7 are manual CEO instructions, not Cursor tasks.

### R2 — Discovery before creation
Use explorer subagent before creating any new file or directory.

### R3 — 1 task = 1 commit
After each task's tests pass → commit with exact message from Brief.

### R4 — MCP_TOOLS.md is supreme authority
If any code conflicts with `docs/MCP_TOOLS.md` (tool names, schemas, performance targets) → docs win, STOP and report.

### R5 — Document disagreement = STOP and suggest
If a foundational doc appears to have an error → STOP, report, wait.

### R6 — 3 retries = STOP and report
Test fails 3 times → STOP, file stop report, wait for CEO relay to CTO.

### R7 — No scope creep
Write exactly what Brief specifies. No extra tools, no extra node types beyond MIHOS extension.

### R8 — Brief code blocks are authoritative
Disagree with a code block → STOP and escalate. Do not substitute.

---

## STOP REPORT FORMAT

```
STOP — Wave 8 Task <N>

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

- `docs/MCP_TOOLS.md §10` — performance targets (source of truth for benchmarks)
- `docs/SCHEMA.md` — node/edge types (source of truth for extension schema)
- `docs/IMPORT_MODEL.md §7` — MIHOS import scope (source of truth for fixture design)
- `tests/conftest.py` — `gobp_root` fixture pattern to follow

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
# Expected: clean (untracked .claude/, .gobp/, files.zip OK)

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: 166 tests passing
```

---

## REQUIRED READING — WAVE START (before Task 1)

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Execution rules |
| 2 | `docs/MCP_TOOLS.md §10` | Performance targets for benchmarks |
| 3 | `docs/SCHEMA.md` | Node/edge types for extension + fixture |
| 4 | `docs/IMPORT_MODEL.md §7` | MIHOS import scope for fixture design |
| 5 | `tests/conftest.py` | gobp_root fixture pattern |
| 6 | `gobp/mcp/server.py` | How tools are called (for integration test) |
| 7 | `waves/wave_8_brief.md` | This file |

**Per-task reading:**

| Task | Must re-read before starting |
|---|---|
| Task 1 (fixture) | `docs/SCHEMA.md`, `docs/IMPORT_MODEL.md §7`, `tests/conftest.py` |
| Task 2 (extension) | `docs/SCHEMA.md §2`, `gobp/schema/core_nodes.yaml` |
| Task 3 (performance) | `docs/MCP_TOOLS.md §10`, `tests/fixtures/mihos_fixture.py` |
| Task 4 (integration) | `gobp/mcp/server.py`, all tool handlers, `tests/fixtures/mihos_fixture.py` |
| Task 5 (CHANGELOG) | `CHANGELOG.md`, `git log --oneline` |

---

# TASKS (Part A — Cursor executes)

---

## TASK 1 — Create tests/fixtures/mihos_fixture.py

**Goal:** Realistic populated graph fixture with MIHOS-scale data (~30 nodes, ~40 edges). Used by performance and integration tests.

**Files to create:**
- `tests/fixtures/__init__.py` (empty)
- `tests/fixtures/mihos_fixture.py`

**Content of `tests/fixtures/mihos_fixture.py`:**

```python
"""MIHOS-scale test fixture for GoBP Wave 8 integration tests.

Creates a realistic populated .gobp/ project with:
- 6 Document nodes (representing MIHOS docs)
- 8 Feature/Node nodes
- 6 Decision nodes (LOCKED)
- 4 Idea nodes
- 4 Session nodes
- 2 Lesson nodes
Total: ~30 nodes, ~40 edges

Scale matches MIHOS M1 baseline referenced in docs/MCP_TOOLS.md §10.
Used by test_performance.py and test_integration.py.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import yaml


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


def _write_node(root: Path, node: dict) -> None:
    """Write a node to .gobp/nodes/ as markdown with YAML front-matter."""
    node_id = node["id"].replace(":", "_")
    path = root / ".gobp" / "nodes" / f"{node_id}.md"
    fm = yaml.dump(node, allow_unicode=True, default_flow_style=False)
    path.write_text(f"---\n{fm}---\n", encoding="utf-8")


def _write_edge(root: Path, edge: dict) -> None:
    """Write an edge to .gobp/edges/ as YAML."""
    from_slug = edge["from"].replace(":", "_")
    to_slug = edge["to"].replace(":", "_")
    edge_type = edge["type"]
    path = root / ".gobp" / "edges" / f"{from_slug}__{edge_type}__{to_slug}.yaml"
    path.write_text(
        yaml.dump(edge, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


@pytest.fixture
def mihos_root(tmp_path: Path) -> Path:
    """Realistic MIHOS-scale populated GoBP project root.

    ~30 nodes, ~40 edges. Schema files provisioned.
    Returns project root ready for GraphIndex.load_from_disk().
    """
    # Create structure
    (tmp_path / ".gobp" / "nodes").mkdir(parents=True)
    (tmp_path / ".gobp" / "edges").mkdir(parents=True)
    (tmp_path / ".gobp" / "history").mkdir(parents=True)

    # Provision schema files
    repo_schema = Path(__file__).parent.parent.parent / "gobp" / "schema"
    dest_schema = tmp_path / "gobp" / "schema"
    dest_schema.mkdir(parents=True)
    shutil.copy(repo_schema / "core_nodes.yaml", dest_schema / "core_nodes.yaml")
    shutil.copy(repo_schema / "core_edges.yaml", dest_schema / "core_edges.yaml")

    # ── Sessions (4) ────────────────────────────────────────────────────────
    sessions = [
        {
            "id": "session:2026-04-14_foundation",
            "type": "Session",
            "actor": "Claude Opus 4.6",
            "started_at": _days_ago(3),
            "ended_at": _days_ago(3),
            "goal": "Import MIHOS foundational docs",
            "status": "COMPLETED",
            "outcome": "Imported 6 Document nodes, extracted core entities",
            "nodes_touched": [],
            "decisions_locked": [],
            "pending": [],
            "created": _days_ago(3),
            "updated": _days_ago(3),
        },
        {
            "id": "session:2026-04-14_features",
            "type": "Session",
            "actor": "Claude Opus 4.6",
            "started_at": _days_ago(2),
            "ended_at": _days_ago(2),
            "goal": "Extract Feature nodes from DOC-07",
            "status": "COMPLETED",
            "outcome": "8 Feature nodes created, linked to docs",
            "nodes_touched": [],
            "decisions_locked": [],
            "pending": [],
            "created": _days_ago(2),
            "updated": _days_ago(2),
        },
        {
            "id": "session:2026-04-15_decisions",
            "type": "Session",
            "actor": "Claude Opus 4.6",
            "started_at": _days_ago(1),
            "ended_at": _days_ago(1),
            "goal": "Lock core architectural decisions",
            "status": "COMPLETED",
            "outcome": "6 Decisions locked",
            "nodes_touched": [],
            "decisions_locked": [],
            "pending": [],
            "created": _days_ago(1),
            "updated": _days_ago(1),
        },
        {
            "id": "session:2026-04-15_current",
            "type": "Session",
            "actor": "Claude Opus 4.6",
            "started_at": _now(),
            "goal": "Wave 8 integration test session",
            "status": "IN_PROGRESS",
            "nodes_touched": [],
            "decisions_locked": [],
            "pending": [],
            "created": _now(),
            "updated": _now(),
        },
    ]

    # ── Documents (6) ────────────────────────────────────────────────────────
    documents = [
        {
            "id": "doc:DOC-01",
            "type": "Document",
            "name": "Soul — MIHOS Vision",
            "source_path": "mihos-shared/docs/DOC-01_soul.md",
            "content_hash": "sha256:" + "a" * 64,
            "registered_at": _days_ago(3),
            "last_verified": _days_ago(3),
            "sections": [{"heading": "Vision", "lines": [1, 50], "tags": ["vision"]}],
            "tags": ["vision", "soul"],
            "status": "ACTIVE",
            "created": _days_ago(3),
            "updated": _days_ago(3),
        },
        {
            "id": "doc:DOC-02",
            "type": "Document",
            "name": "Master Definitions",
            "source_path": "mihos-shared/docs/DOC-02_master_definitions.md",
            "content_hash": "sha256:" + "b" * 64,
            "registered_at": _days_ago(3),
            "last_verified": _days_ago(3),
            "sections": [
                {"heading": "Entities", "lines": [1, 100], "tags": ["entity"]},
                {"heading": "Invariants", "lines": [101, 200], "tags": ["invariant"]},
            ],
            "tags": ["definitions", "entities"],
            "status": "ACTIVE",
            "created": _days_ago(3),
            "updated": _days_ago(3),
        },
        {
            "id": "doc:DOC-07",
            "type": "Document",
            "name": "Core User Flows",
            "source_path": "mihos-shared/docs/DOC-07_core_user_flows.md",
            "content_hash": "sha256:" + "c" * 64,
            "registered_at": _days_ago(2),
            "last_verified": _days_ago(2),
            "sections": [
                {"heading": "F1 Register", "lines": [1, 80], "tags": ["auth"]},
                {"heading": "F2 Login", "lines": [81, 160], "tags": ["auth"]},
                {"heading": "F3 Mi Hot", "lines": [161, 280], "tags": ["core"]},
                {"heading": "F4 Provider Scan", "lines": [281, 380], "tags": ["core"]},
                {"heading": "F5 Imprint Capture", "lines": [381, 440], "tags": ["core"]},
                {"heading": "F6 Wallet", "lines": [441, 520], "tags": ["economy"]},
                {"heading": "F7 Memory Review", "lines": [521, 590], "tags": ["ui"]},
                {"heading": "F8 Settings", "lines": [591, 650], "tags": ["ui"]},
            ],
            "tags": ["flows", "core"],
            "status": "ACTIVE",
            "created": _days_ago(2),
            "updated": _days_ago(2),
        },
        {
            "id": "doc:DOC-16",
            "type": "Document",
            "name": "Engine Specifications",
            "source_path": "mihos-shared/docs/DOC-16_engine_specs.md",
            "content_hash": "sha256:" + "d" * 64,
            "registered_at": _days_ago(2),
            "last_verified": _days_ago(2),
            "sections": [
                {"heading": "PoP Engine", "lines": [1, 120], "tags": ["engine", "pop"]},
                {"heading": "Heritage Engine", "lines": [121, 220], "tags": ["engine"]},
            ],
            "tags": ["engines", "technical"],
            "status": "ACTIVE",
            "created": _days_ago(2),
            "updated": _days_ago(2),
        },
        {
            "id": "doc:DOC-03",
            "type": "Document",
            "name": "Identity System",
            "source_path": "mihos-shared/docs/DOC-03_identity.md",
            "content_hash": "sha256:" + "e" * 64,
            "registered_at": _days_ago(3),
            "last_verified": _days_ago(3),
            "sections": [
                {"heading": "DID Model", "lines": [1, 100], "tags": ["identity", "did"]},
            ],
            "tags": ["identity"],
            "status": "ACTIVE",
            "created": _days_ago(3),
            "updated": _days_ago(3),
        },
        {
            "id": "doc:DOC-15",
            "type": "Document",
            "name": "API Reference",
            "source_path": "mihos-shared/docs/DOC-15_api_reference.md",
            "content_hash": "sha256:" + "f" * 64,
            "registered_at": _days_ago(1),
            "last_verified": _days_ago(1),
            "sections": [
                {"heading": "Auth Endpoints", "lines": [1, 80], "tags": ["api", "auth"]},
                {"heading": "Presence Endpoints", "lines": [81, 160], "tags": ["api", "pop"]},
            ],
            "tags": ["api"],
            "status": "ACTIVE",
            "created": _days_ago(1),
            "updated": _days_ago(1),
        },
    ]

    # ── Feature/Node nodes (8) ───────────────────────────────────────────────
    features = [
        {"id": "node:feat_register", "type": "Node", "name": "Register",
         "status": "ACTIVE", "created": _days_ago(2), "updated": _days_ago(2)},
        {"id": "node:feat_login", "type": "Node", "name": "Login",
         "status": "ACTIVE", "created": _days_ago(2), "updated": _days_ago(2)},
        {"id": "node:feat_mi_hot", "type": "Node", "name": "Mi Hot (Harvest)",
         "status": "ACTIVE", "created": _days_ago(2), "updated": _days_ago(2)},
        {"id": "node:feat_provider_scan", "type": "Node", "name": "Provider Scan",
         "status": "ACTIVE", "created": _days_ago(2), "updated": _days_ago(2)},
        {"id": "node:feat_imprint", "type": "Node", "name": "Imprint Capture",
         "status": "ACTIVE", "created": _days_ago(2), "updated": _days_ago(2)},
        {"id": "node:feat_wallet", "type": "Node", "name": "Wallet",
         "status": "ACTIVE", "created": _days_ago(2), "updated": _days_ago(2)},
        {"id": "node:feat_memory_review", "type": "Node", "name": "Memory Review",
         "status": "ACTIVE", "created": _days_ago(2), "updated": _days_ago(2)},
        {"id": "node:feat_settings", "type": "Node", "name": "Settings",
         "status": "ACTIVE", "created": _days_ago(2), "updated": _days_ago(2)},
    ]

    # ── Decisions (6, LOCKED) ─────────────────────────────────────────────────
    decisions = [
        {
            "id": "dec:d001", "type": "Decision",
            "name": "auth:login.method",
            "topic": "auth:login.method",
            "what": "Use Email OTP for login authentication",
            "why": "Biometric device-dependent. SMS unreliable in VN.",
            "status": "LOCKED",
            "locked_at": _days_ago(1),
            "locked_by": ["CEO", "Claude-Opus-4.6"],
            "alternatives_considered": [
                {"option": "Face ID", "rejected_reason": "device dependency"},
                {"option": "SMS OTP", "rejected_reason": "VN spam filters"},
            ],
            "created": _days_ago(1), "updated": _days_ago(1),
        },
        {
            "id": "dec:d002", "type": "Decision",
            "name": "storage:backend",
            "topic": "storage:backend",
            "what": "File-first storage with YAML front-matter",
            "why": "Portable, git-friendly, no database dependency.",
            "status": "LOCKED",
            "locked_at": _days_ago(3),
            "locked_by": ["CEO", "Claude-Opus-4.6"],
            "alternatives_considered": [
                {"option": "SQLite", "rejected_reason": "adds complexity"},
            ],
            "created": _days_ago(3), "updated": _days_ago(3),
        },
        {
            "id": "dec:d003", "type": "Decision",
            "name": "presence:verification.method",
            "topic": "presence:verification.method",
            "what": "GPS + timestamp + photo as Proof of Presence",
            "why": "Cannot fake all three simultaneously in the field.",
            "status": "LOCKED",
            "locked_at": _days_ago(2),
            "locked_by": ["CEO", "Claude-Opus-4.6"],
            "alternatives_considered": [],
            "created": _days_ago(2), "updated": _days_ago(2),
        },
        {
            "id": "dec:d004", "type": "Decision",
            "name": "economy:revenue.model",
            "topic": "economy:revenue.model",
            "what": "No ads. Revenue sharing directly with Traveller.",
            "why": "Protocol 03 — Circular Economy. Ads violate Dissolving UI principle.",
            "status": "LOCKED",
            "locked_at": _days_ago(2),
            "locked_by": ["CEO", "Claude-Opus-4.6"],
            "alternatives_considered": [
                {"option": "Ad-based", "rejected_reason": "violates Protocol 02"},
            ],
            "created": _days_ago(2), "updated": _days_ago(2),
        },
        {
            "id": "dec:d005", "type": "Decision",
            "name": "identity:did.approach",
            "topic": "identity:did.approach",
            "what": "Decentralized Identity — imprints owned by user",
            "why": "Data sovereignty. User owns their heritage footprint.",
            "status": "LOCKED",
            "locked_at": _days_ago(3),
            "locked_by": ["CEO", "Claude-Opus-4.6"],
            "alternatives_considered": [],
            "created": _days_ago(3), "updated": _days_ago(3),
        },
        {
            "id": "dec:d006", "type": "Decision",
            "name": "ui:dissolving.principle",
            "topic": "ui:dissolving.principle",
            "what": "App fades after transaction — Protocol 02 Dissolving UI",
            "why": "Reduce screen dependency. Return user to physical reality.",
            "status": "LOCKED",
            "locked_at": _days_ago(2),
            "locked_by": ["CEO", "Claude-Opus-4.6"],
            "alternatives_considered": [],
            "created": _days_ago(2), "updated": _days_ago(2),
        },
    ]

    # ── Ideas (4) ────────────────────────────────────────────────────────────
    ideas = [
        {
            "id": "idea:i001", "type": "Idea",
            "name": "Offline mode for imprint capture",
            "subject": "presence:offline.mode",
            "raw_quote": "Nếu không có internet thì sao?",
            "interpretation": "Imprint capture should work offline, sync later",
            "maturity": "ROUGH", "confidence": "medium",
            "created": _days_ago(1), "updated": _days_ago(1),
        },
        {
            "id": "idea:i002", "type": "Idea",
            "name": "Provider reputation score",
            "subject": "provider:reputation",
            "raw_quote": "Provider nên có điểm uy tín",
            "interpretation": "Heritage providers need a trust/reputation system",
            "maturity": "REFINED", "confidence": "high",
            "created": _days_ago(2), "updated": _days_ago(1),
        },
        {
            "id": "idea:i003", "type": "Idea",
            "name": "Batch imprint upload for providers",
            "subject": "provider:batch.upload",
            "raw_quote": "Provider nên upload nhiều imprint một lúc",
            "interpretation": "Provider admin needs batch upload capability",
            "maturity": "ROUGH", "confidence": "low",
            "created": _days_ago(1), "updated": _days_ago(1),
        },
        {
            "id": "idea:i004", "type": "Idea",
            "name": "Wallet integration with VN payment gateways",
            "subject": "economy:payment.gateway",
            "raw_quote": "Cần tích hợp VNPay hoặc MoMo",
            "interpretation": "Wallet must support local VN payment methods",
            "maturity": "REFINED", "confidence": "high",
            "created": _days_ago(2), "updated": _days_ago(1),
        },
    ]

    # ── Lessons (2) ──────────────────────────────────────────────────────────
    lessons = [
        {
            "id": "lesson:ll001", "type": "Lesson",
            "title": "Schema-aware test fixtures required for GraphIndex",
            "trigger": "Writing tests that call GraphIndex.load_from_disk()",
            "what_happened": (
                "Wave 6 tests failed because tmp roots lacked schema files. "
                "GraphIndex.load_from_disk() requires gobp/schema/*.yaml."
            ),
            "why_it_matters": "Silent failure — FileNotFoundError only at test runtime.",
            "mitigation": "Always use gobp_root fixture from tests/conftest.py.",
            "severity": "high",
            "captured_in_session": "session:2026-04-15_decisions",
            "tags": ["testing", "fixtures", "F19"],
            "created": _days_ago(1), "updated": _days_ago(1),
        },
        {
            "id": "lesson:ll002", "type": "Lesson",
            "title": "Async handlers must be awaited in MCP server dispatch",
            "trigger": "Adding an async tool handler to server.py",
            "what_happened": (
                "lessons_extract was async but call_tool() dispatched without await. "
                "Returns coroutine object instead of result. json.dumps raises TypeError."
            ),
            "why_it_matters": "Silent in tests (called directly), crashes in production MCP connection.",
            "mitigation": "Use inspect.iscoroutinefunction() + await in call_tool() dispatch.",
            "severity": "critical",
            "captured_in_session": "session:2026-04-15_decisions",
            "tags": ["async", "mcp-server", "dispatch"],
            "created": _days_ago(1), "updated": _days_ago(1),
        },
    ]

    # ── Write all nodes ───────────────────────────────────────────────────────
    for node in sessions + documents + features + decisions + ideas + lessons:
        _write_node(tmp_path, node)

    # ── Write edges (~40) ─────────────────────────────────────────────────────
    edges = [
        # Features → DOC-07 (references)
        {"from": "node:feat_register", "to": "doc:DOC-07", "type": "references"},
        {"from": "node:feat_login", "to": "doc:DOC-07", "type": "references"},
        {"from": "node:feat_mi_hot", "to": "doc:DOC-07", "type": "references"},
        {"from": "node:feat_provider_scan", "to": "doc:DOC-07", "type": "references"},
        {"from": "node:feat_imprint", "to": "doc:DOC-07", "type": "references"},
        {"from": "node:feat_wallet", "to": "doc:DOC-07", "type": "references"},
        {"from": "node:feat_memory_review", "to": "doc:DOC-07", "type": "references"},
        {"from": "node:feat_settings", "to": "doc:DOC-07", "type": "references"},
        # Features → Decisions (implements)
        {"from": "node:feat_login", "to": "dec:d001", "type": "implements"},
        {"from": "node:feat_imprint", "to": "dec:d003", "type": "implements"},
        {"from": "node:feat_wallet", "to": "dec:d004", "type": "implements"},
        # Decisions → Docs (discovered_in via session)
        {"from": "dec:d001", "to": "session:2026-04-15_decisions", "type": "discovered_in"},
        {"from": "dec:d002", "to": "session:2026-04-14_foundation", "type": "discovered_in"},
        {"from": "dec:d003", "to": "session:2026-04-15_decisions", "type": "discovered_in"},
        {"from": "dec:d004", "to": "session:2026-04-15_decisions", "type": "discovered_in"},
        {"from": "dec:d005", "to": "session:2026-04-14_foundation", "type": "discovered_in"},
        {"from": "dec:d006", "to": "session:2026-04-15_decisions", "type": "discovered_in"},
        # Ideas → Sessions (discovered_in)
        {"from": "idea:i001", "to": "session:2026-04-15_current", "type": "discovered_in"},
        {"from": "idea:i002", "to": "session:2026-04-15_decisions", "type": "discovered_in"},
        {"from": "idea:i003", "to": "session:2026-04-15_current", "type": "discovered_in"},
        {"from": "idea:i004", "to": "session:2026-04-15_decisions", "type": "discovered_in"},
        # Docs → Docs (relates_to)
        {"from": "doc:DOC-02", "to": "doc:DOC-07", "type": "relates_to"},
        {"from": "doc:DOC-03", "to": "doc:DOC-02", "type": "relates_to"},
        {"from": "doc:DOC-15", "to": "doc:DOC-07", "type": "relates_to"},
        {"from": "doc:DOC-16", "to": "doc:DOC-07", "type": "relates_to"},
        # Features → Features (relates_to)
        {"from": "node:feat_register", "to": "node:feat_login", "type": "relates_to"},
        {"from": "node:feat_mi_hot", "to": "node:feat_imprint", "type": "relates_to"},
        {"from": "node:feat_wallet", "to": "node:feat_mi_hot", "type": "relates_to"},
        # Lessons → Sessions (discovered_in)
        {"from": "lesson:ll001", "to": "session:2026-04-15_decisions", "type": "discovered_in"},
        {"from": "lesson:ll002", "to": "session:2026-04-15_decisions", "type": "discovered_in"},
    ]

    for edge in edges:
        _write_edge(tmp_path, edge)

    return tmp_path
```

**Acceptance criteria:**
- `tests/fixtures/__init__.py` created (empty)
- `tests/fixtures/mihos_fixture.py` created
- `mihos_root` fixture: ~30 nodes, ~30 edges written to disk
- `GraphIndex.load_from_disk(mihos_root)` succeeds with no load errors
- Verify: `pytest tests/fixtures/ -v` (no tests yet, just import check)

**Commit message:**
```
Wave 8 Task 1: create tests/fixtures/mihos_fixture.py

- mihos_root fixture: ~30 nodes (6 docs, 8 features, 6 decisions,
  4 ideas, 4 sessions, 2 lessons), ~30 edges
- MIHOS-scale data matching IMPORT_MODEL.md §7 scope
- Schema files provisioned — GraphIndex.load_from_disk() compatible
```

---

## TASK 2 — Create gobp/schema/extensions/mihos.yaml

**Goal:** MIHOS-specific schema extension demonstrating GoBP's domain-agnostic extensibility.

**Files to create:**
- `gobp/schema/extensions/__init__.py` (empty — makes it a Python package for future loader)
- `gobp/schema/extensions/mihos.yaml`

**Content of `gobp/schema/extensions/mihos.yaml`:**

```yaml
# MIHOS Schema Extension for GoBP
# Extends GoBP core schema with MIHOS-specific node types.
# Core types (Node, Idea, Decision, Session, Document, Lesson) remain unchanged.
#
# To use: reference this file in .gobp/config.yaml as:
#   schema_extensions:
#     - gobp/schema/extensions/mihos.yaml

extension_name: mihos
version: "1.0"
extends: gobp_core_v1

node_types:

  Imprint:
    description: A verified heritage presence record — the core MIHOS asset
    id_prefix: "imprint"
    parent: Node  # extends Node

    required:
      id:
        type: str
        pattern: "^imprint:.+$"
      type:
        type: str
        enum_values: [Imprint]
      name:
        type: str
        description: Short description of the imprint
      traveller_id:
        type: str
        description: DID of the Traveller who created the imprint
      provider_id:
        type: str
        description: ID of the heritage Provider
      gps_lat:
        type: float
        description: GPS latitude at capture time
      gps_lng:
        type: float
        description: GPS longitude at capture time
      captured_at:
        type: timestamp
      proof_type:
        type: enum
        enum_values: [GPS_PHOTO, GPS_ONLY, PROVIDER_VERIFIED]
      status:
        type: enum
        enum_values: [PENDING, VERIFIED, DISPUTED, WITHDRAWN]
      created:
        type: timestamp
      updated:
        type: timestamp

    optional:
      photo_hash:
        type: str
        description: SHA-256 of the capture photo
      value_points:
        type: int
        default: 0
        description: Economic value assigned to this imprint
      heritage_tags:
        type: list[str]
        default: []
        description: Heritage category tags (e.g. ["temple", "buddhist"])

  Provider:
    description: A heritage site or experience provider in the MIHOS network
    id_prefix: "provider"
    parent: Node

    required:
      id:
        type: str
        pattern: "^provider:.+$"
      type:
        type: str
        enum_values: [Provider]
      name:
        type: str
      location_name:
        type: str
        description: Human-readable location (e.g. "Hoi An Ancient Town")
      gps_lat:
        type: float
      gps_lng:
        type: float
      status:
        type: enum
        enum_values: [ACTIVE, SUSPENDED, PENDING_REVIEW]
      created:
        type: timestamp
      updated:
        type: timestamp

    optional:
      reputation_score:
        type: float
        default: 0.0
        description: Aggregated trust score (0.0–5.0)
      heritage_category:
        type: list[str]
        default: []
      verified_by:
        type: str
        description: Authority that verified this provider
```

**Acceptance criteria:**
- `gobp/schema/extensions/__init__.py` created (empty)
- `gobp/schema/extensions/mihos.yaml` created with Imprint and Provider types
- Valid YAML: `python -c "import yaml; yaml.safe_load(open('gobp/schema/extensions/mihos.yaml'))"`
- Demonstrates id_prefix pattern, required/optional structure matching core schema style

**Commit message:**
```
Wave 8 Task 2: create gobp/schema/extensions/mihos.yaml

- MIHOS schema extension: Imprint + Provider node types
- Demonstrates GoBP domain-agnostic extensibility
- gobp/schema/extensions/__init__.py placeholder
- Valid YAML, follows core_nodes.yaml structure conventions
```

---

## TASK 3 — Create tests/test_performance.py

**Goal:** Benchmark all 14 MCP tools against `docs/MCP_TOOLS.md §10` max latency targets.

**Re-read `docs/MCP_TOOLS.md §10` before writing this test.**

**File to create:** `tests/test_performance.py`

**Content:**

```python
"""Performance benchmarks for GoBP MCP tools.

Tests all 14 tools against max latency targets from docs/MCP_TOOLS.md §10.
Uses mihos_root fixture (~30 nodes) for realistic scale.

MAX LATENCY TARGETS (from MCP_TOOLS.md §10):
  gobp_overview:  100ms    find:          50ms
  signature:       30ms    context:      100ms
  session_recent:  50ms    decisions_for: 50ms
  doc_sections:    30ms    node_upsert:  200ms
  decision_lock:  200ms    session_log:  100ms
  import_proposal:500ms    import_commit:1000ms
  validate:       5000ms   lessons_extract: (no target, use 2000ms)
"""

import asyncio
import time
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import read as tools_read
from gobp.mcp.tools import write as tools_write
from gobp.mcp.tools.advanced import lessons_extract

# Import fixture
from tests.fixtures.mihos_fixture import mihos_root  # noqa: F401


# ── Max latency targets (ms) from MCP_TOOLS.md §10 ───────────────────────────
MAX_MS = {
    "gobp_overview": 100,
    "find": 50,
    "signature": 30,
    "context": 100,
    "session_recent": 50,
    "decisions_for": 50,
    "doc_sections": 30,
    "node_upsert": 200,
    "decision_lock": 200,
    "session_log": 100,
    "lessons_extract": 2000,  # no official target, conservative
    "validate": 5000,
}


def _load(root: Path):
    return GraphIndex.load_from_disk(root)


def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


# ── Read tools ────────────────────────────────────────────────────────────────

def test_perf_gobp_overview(mihos_root: Path):
    index = _load(mihos_root)
    start = time.perf_counter()
    result = tools_read.gobp_overview(index, mihos_root, {})
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["gobp_overview"], (
        f"gobp_overview: {elapsed:.1f}ms > {MAX_MS['gobp_overview']}ms"
    )


def test_perf_find(mihos_root: Path):
    index = _load(mihos_root)
    start = time.perf_counter()
    result = tools_read.find(index, mihos_root, {"query": "login"})
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["find"], f"find: {elapsed:.1f}ms > {MAX_MS['find']}ms"


def test_perf_signature(mihos_root: Path):
    index = _load(mihos_root)
    start = time.perf_counter()
    result = tools_read.signature(index, mihos_root, {"node_id": "node:feat_login"})
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["signature"], (
        f"signature: {elapsed:.1f}ms > {MAX_MS['signature']}ms"
    )


def test_perf_context(mihos_root: Path):
    index = _load(mihos_root)
    start = time.perf_counter()
    result = tools_read.context(index, mihos_root, {"node_id": "node:feat_login"})
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["context"], (
        f"context: {elapsed:.1f}ms > {MAX_MS['context']}ms"
    )


def test_perf_session_recent(mihos_root: Path):
    index = _load(mihos_root)
    start = time.perf_counter()
    result = tools_read.session_recent(index, mihos_root, {"n": 3})
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["session_recent"], (
        f"session_recent: {elapsed:.1f}ms > {MAX_MS['session_recent']}ms"
    )


def test_perf_decisions_for(mihos_root: Path):
    index = _load(mihos_root)
    start = time.perf_counter()
    result = tools_read.decisions_for(
        index, mihos_root, {"topic": "auth:login.method"}
    )
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["decisions_for"], (
        f"decisions_for: {elapsed:.1f}ms > {MAX_MS['decisions_for']}ms"
    )


def test_perf_doc_sections(mihos_root: Path):
    index = _load(mihos_root)
    start = time.perf_counter()
    result = tools_read.doc_sections(index, mihos_root, {"doc_id": "doc:DOC-07"})
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["doc_sections"], (
        f"doc_sections: {elapsed:.1f}ms > {MAX_MS['doc_sections']}ms"
    )


# ── Write tools ───────────────────────────────────────────────────────────────

def test_perf_session_log_start(mihos_root: Path):
    index = _load(mihos_root)
    start = time.perf_counter()
    result = tools_write.session_log(index, mihos_root, {
        "action": "start",
        "actor": "perf-test",
        "goal": "Performance benchmark session",
    })
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["session_log"], (
        f"session_log: {elapsed:.1f}ms > {MAX_MS['session_log']}ms"
    )


def test_perf_node_upsert(mihos_root: Path):
    index = _load(mihos_root)
    # Need active session first
    sess_result = tools_write.session_log(index, mihos_root, {
        "action": "start",
        "actor": "perf-test",
        "goal": "node_upsert perf test",
    })
    index = GraphIndex.load_from_disk(mihos_root)  # reload after write
    session_id = sess_result["session_id"]

    start = time.perf_counter()
    result = tools_write.node_upsert(index, mihos_root, {
        "type": "Idea",
        "name": "Performance test idea",
        "fields": {
            "subject": "perf:test",
            "raw_quote": "test",
            "interpretation": "perf test node",
            "maturity": "ROUGH",
            "confidence": "low",
        },
        "session_id": session_id,
    })
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["node_upsert"], (
        f"node_upsert: {elapsed:.1f}ms > {MAX_MS['node_upsert']}ms"
    )


# ── Advanced tools ────────────────────────────────────────────────────────────

def test_perf_lessons_extract(mihos_root: Path):
    index = _load(mihos_root)
    start = time.perf_counter()
    result = asyncio.run(lessons_extract(index, mihos_root, {}))
    elapsed = _ms(start)
    assert result["ok"] is True
    assert elapsed < MAX_MS["lessons_extract"], (
        f"lessons_extract: {elapsed:.1f}ms > {MAX_MS['lessons_extract']}ms"
    )
```

**Acceptance criteria:**
- File `tests/test_performance.py` created
- 10 benchmark tests covering read tools, write tools, advanced tools
- All tests pass AND within max latency targets
- If any test exceeds max latency → test fails with clear message showing actual vs target

**Commit message:**
```
Wave 8 Task 3: create tests/test_performance.py

- 10 latency benchmarks against MCP_TOOLS.md §10 targets
- mihos_root fixture (~30 nodes) for realistic scale
- Covers gobp_overview, find, signature, context, session_recent,
  decisions_for, doc_sections, session_log, node_upsert, lessons_extract
```

---

## TASK 4 — Create tests/test_integration.py

**Goal:** End-to-end test: AI session workflow using all major tool categories in sequence.

**File to create:** `tests/test_integration.py`

**Content:**

```python
"""End-to-end integration test for GoBP v1.

Simulates a complete AI session workflow:
1. gobp_overview → orient
2. find → discover nodes
3. context → deep dive
4. decisions_for → get locked decisions
5. session_log (start) → begin session
6. node_upsert → capture idea
7. decision_lock → lock decision
8. session_log (end) → close session
9. validate → verify graph integrity
10. lessons_extract → scan for lessons

Uses mihos_root fixture (~30 nodes) as starting state.
"""

import asyncio
from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import read as tools_read
from gobp.mcp.tools import write as tools_write
from gobp.mcp.tools.advanced import lessons_extract

try:
    from gobp.mcp.tools import maintain as tools_maintain
    HAS_VALIDATE = True
except ImportError:
    HAS_VALIDATE = False

from tests.fixtures.mihos_fixture import mihos_root  # noqa: F401


def _load(root: Path) -> GraphIndex:
    return GraphIndex.load_from_disk(root)


def test_full_ai_session_workflow(mihos_root: Path):
    """Complete AI session: orient → discover → capture → lock → close → validate."""

    root = mihos_root
    index = _load(root)

    # 1. gobp_overview — orient
    overview = tools_read.gobp_overview(index, root, {})
    assert overview["ok"] is True
    assert overview["stats"]["total_nodes"] >= 25

    # 2. find — discover login feature
    found = tools_read.find(index, root, {"query": "login", "limit": 5})
    assert found["ok"] is True
    assert found["count"] >= 1
    login_node = next(
        (n for n in found["nodes"] if "login" in n["id"].lower()), None
    )
    assert login_node is not None

    # 3. context — deep dive on login feature
    ctx = tools_read.context(index, root, {"node_id": login_node["id"]})
    assert ctx["ok"] is True
    assert "node" in ctx

    # 4. decisions_for — get locked decisions on auth
    decisions = tools_read.decisions_for(
        index, root, {"topic": "auth:login.method"}
    )
    assert decisions["ok"] is True
    assert decisions["count"] >= 1
    assert decisions["decisions"][0]["status"] == "LOCKED"

    # 5. session_log start
    sess = tools_write.session_log(index, root, {
        "action": "start",
        "actor": "integration-test",
        "goal": "Test full AI session workflow",
    })
    assert sess["ok"] is True
    session_id = sess["session_id"]
    assert session_id.startswith("session:")

    # Reload index after write
    index = _load(root)

    # 6. node_upsert — capture a new idea
    idea = tools_write.node_upsert(index, root, {
        "type": "Idea",
        "name": "Integration test idea",
        "fields": {
            "subject": "integration:test.subject",
            "raw_quote": "Testing the full workflow",
            "interpretation": "End-to-end test of GoBP session workflow",
            "maturity": "ROUGH",
            "confidence": "high",
        },
        "session_id": session_id,
    })
    assert idea["ok"] is True
    idea_id = idea["node_id"]
    index = _load(root)

    # 7. decision_lock — lock a new decision
    dec = tools_write.decision_lock(index, root, {
        "topic": "integration:test.decision",
        "what": "Use integration tests to verify GoBP end-to-end",
        "why": "Automated verification catches regressions before push",
        "alternatives_considered": [
            {"option": "Manual testing only", "rejected_reason": "Not scalable"},
        ],
        "related_ideas": [idea_id],
        "session_id": session_id,
        "locked_by": ["CEO", "integration-test"],
    })
    assert dec["ok"] is True
    dec_id = dec["decision_id"]
    index = _load(root)

    # 8. session_log end
    end = tools_write.session_log(index, root, {
        "action": "end",
        "session_id": session_id,
        "outcome": "Integration test workflow completed successfully",
        "pending": [],
        "nodes_touched": [idea_id, dec_id],
        "decisions_locked": [dec_id],
    })
    assert end["ok"] is True
    index = _load(root)

    # 9. validate — graph integrity check
    if HAS_VALIDATE:
        from gobp.mcp.tools import maintain as tools_maintain
        val = tools_maintain.validate(index, root, {"scope": "all"})
        assert val["ok"] is True
        hard_errors = [i for i in val.get("issues", []) if i.get("severity") == "hard"]
        assert len(hard_errors) == 0, f"Hard validation errors: {hard_errors}"

    # 10. lessons_extract — scan for candidates
    lessons = asyncio.run(lessons_extract(index, root, {}))
    assert lessons["ok"] is True
    assert "candidates" in lessons
    assert "note" in lessons


def test_session_recent_after_writes(mihos_root: Path):
    """session_recent returns new session after session_log start."""
    root = mihos_root
    index = _load(root)

    sess = tools_write.session_log(index, root, {
        "action": "start",
        "actor": "recency-test",
        "goal": "Test recency",
    })
    assert sess["ok"] is True
    session_id = sess["session_id"]
    index = _load(root)

    recent = tools_read.session_recent(index, root, {"n": 5})
    assert recent["ok"] is True
    session_ids = [s["id"] for s in recent["sessions"]]
    assert session_id in session_ids


def test_find_returns_newly_created_node(mihos_root: Path):
    """find() discovers a node created via node_upsert in same session."""
    root = mihos_root
    index = _load(root)

    sess = tools_write.session_log(index, root, {
        "action": "start",
        "actor": "find-test",
        "goal": "Test find after upsert",
    })
    session_id = sess["session_id"]
    index = _load(root)

    tools_write.node_upsert(index, root, {
        "type": "Idea",
        "name": "Uniquely named xyzzy idea for find test",
        "fields": {
            "subject": "find:test",
            "raw_quote": "xyzzy",
            "interpretation": "test",
            "maturity": "ROUGH",
            "confidence": "low",
        },
        "session_id": session_id,
    })
    index = _load(root)

    found = tools_read.find(index, root, {"query": "xyzzy"})
    assert found["ok"] is True
    assert found["count"] >= 1
```

**Acceptance criteria:**
- File `tests/test_integration.py` created
- 3 integration tests
- All tests pass
- `test_full_ai_session_workflow` exercises all 10 steps

**Commit message:**
```
Wave 8 Task 4: create tests/test_integration.py

- 3 end-to-end integration tests using mihos_root fixture
- test_full_ai_session_workflow: 10-step session (orient→capture→lock→validate)
- test_session_recent_after_writes: recency verified after session_log
- test_find_returns_newly_created_node: find() discovers node_upsert result
```

---

## TASK 5 — Update CHANGELOG.md for Wave 8

**Goal:** Add Wave 8 entry to CHANGELOG.md.

**File to modify:** `CHANGELOG.md`

**Prepend this section** at the top (after `# CHANGELOG` header, before Wave 6 entry):

```markdown
## [Wave 8] — MIHOS Integration Test — 2026-04-15

### Added
- `tests/fixtures/mihos_fixture.py` — MIHOS-scale fixture (~30 nodes, ~30 edges)
- `tests/fixtures/__init__.py`
- `gobp/schema/extensions/mihos.yaml` — MIHOS schema extension (Imprint + Provider types)
- `gobp/schema/extensions/__init__.py`
- `tests/test_performance.py` — 10 latency benchmarks vs MCP_TOOLS.md §10 targets
- `tests/test_integration.py` — 3 end-to-end session workflow tests

### Verified
- All 14 MCP tools within max latency targets on MIHOS-scale data (~30 nodes)
- Full session workflow (orient → capture → lock → close → validate → extract) passes
- GoBP schema extension pattern demonstrated (mihos.yaml)

### Total after wave: 14 MCP tools, 179 tests passing
```

**Run full test suite after update:**

```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: 179 tests passing (166 + 10 perf + 3 integration)
```

**Commit message:**
```
Wave 8 Task 5: update CHANGELOG.md for Wave 8

- Wave 8 entry: fixtures, extension schema, perf tests, integration tests
- Total: 179 tests passing
```

---

# TASKS (Part B — Manual CEO session)

> **These are NOT Cursor tasks.** Cursor stops after Task 5.
> Part B is a runtime session where CEO connects an MCP client to a real GoBP project.

---

## TASK 6 — Real MIHOS doc import session (Manual — CEO)

**Goal:** Import 31 MIHOS docs into a real GoBP project as Document nodes.

**Prerequisites:**
- Wave 8 Tasks 1–5 pushed to GitHub
- A real project folder where MIHOS docs live (e.g. `D:\MIHOS\`)
- GoBP MCP server connected to that project (see `docs/INSTALL.md §3`)

**Steps:**

### 6.1 Initialize GoBP in MIHOS project

```powershell
cd D:\MIHOS
python -m gobp.cli init
```

### 6.2 Connect MCP client

Configure Cursor or Claude Desktop with:
```json
"GOBP_PROJECT_ROOT": "D:/MIHOS"
```

Restart client.

### 6.3 Bulk register 31 docs

Ask AI in MCP session:

```
Start a GoBP session. Goal: "Bulk register 31 MIHOS docs as Document nodes".

Then scan mihos-shared/docs/ and register ALL .md files as Document nodes.
For each file: read it, compute metadata, build node_upsert call.
Use import_proposal for bulk, then import_commit if I approve.

Show me the proposal before committing.
```

Review proposal → approve → commit.

### 6.4 Verify

Ask AI:
```
Call gobp_overview. How many Document nodes are registered?
```

Expected: 31 Document nodes.

---

## TASK 7 — Lessons extraction session (Manual — CEO)

**Goal:** Run `lessons_extract` on the populated GoBP project, review candidates, create confirmed Lesson nodes.

**Steps:**

### 7.1 Run extraction

Ask AI in MCP session:
```
Call lessons_extract with all patterns (P1, P2, P3, P4).
Show me all candidates.
```

### 7.2 Review candidates

For each candidate:
- Read `title`, `what_happened`, `mitigation`
- If valuable → ask AI to create as Lesson node: `node_upsert(type='Lesson', ...)`
- If not relevant → skip

### 7.3 Log session

Ask AI to end session:
```
End the current GoBP session. Outcome: "Extracted and confirmed N lessons from MIHOS project".
```

### 7.4 Verify

```
Call gobp_overview. Show Lesson nodes count.
```

---

# POST-WAVE VERIFICATION (Part A only — Cursor)

```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: 179 tests passing

# New files exist
Test-Path tests/fixtures/mihos_fixture.py     # True
Test-Path gobp/schema/extensions/mihos.yaml   # True
Test-Path tests/test_performance.py           # True
Test-Path tests/test_integration.py           # True

# Extension YAML valid
D:/GoBP/venv/Scripts/python.exe -c "import yaml; yaml.safe_load(open('gobp/schema/extensions/mihos.yaml')); print('YAML OK')"

# Git log
git log --oneline | Select-Object -First 7
# Expected: 5 Wave 8 commits
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Copy Brief vào repo

```powershell
cd D:\GoBP
# Save wave_8_brief.md to D:\GoBP\waves\wave_8_brief.md

git add waves/wave_8_brief.md
git commit -m "Add Wave 8 Brief"
git push origin main
```

## 2. Dispatch Cursor

Cursor IDE → Ctrl+L → paste:

```
Read .cursorrules and waves/wave_8_brief.md first.
Also read docs/MCP_TOOLS.md §10 (performance targets).
Also read docs/SCHEMA.md (node types for extension).
Also read docs/IMPORT_MODEL.md §7 (MIHOS import scope).
Also read tests/conftest.py (fixture pattern).
Also read gobp/mcp/server.py and all tool handlers.

Execute Tasks 1 through 5 of Wave 8 sequentially.
Tasks 6 and 7 are manual CEO instructions — do NOT execute them.
Rules:
- Use explorer subagent before creating any new file or directory
- Re-read per-task docs listed in REQUIRED READING before each task
- If performance tests fail latency targets → report actual ms vs target (R6)
- If Brief conflicts with docs/MCP_TOOLS.md → docs win, STOP and report (R4)
- If you believe a doc has an error → STOP and report (R5)
- 1 task = 1 commit, message must match Brief exactly
- Report full wave summary only after Task 5 is committed

Begin Task 1.
```

## 3. Audit Claude CLI

```powershell
cd D:\GoBP
claude
```

Paste vào Claude CLI:

```
Audit Wave 8 (Tasks 1–5 only). Read CLAUDE.md and waves/wave_8_brief.md.
Also read docs/MCP_TOOLS.md §10 for performance targets.

Sequentially audit Task 1 through Task 5.

Critical verification per task:
- Task 1: tests/fixtures/mihos_fixture.py exists, mihos_root fixture has ~30 nodes
- Task 2: gobp/schema/extensions/mihos.yaml valid YAML, has Imprint + Provider types
- Task 3: tests/test_performance.py exists, 10 tests, all pass within latency targets
- Task 4: tests/test_integration.py exists, 3 tests, all pass
- Task 5: CHANGELOG.md has Wave 8 entry, test count accurate

Use venv Python:
  D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v

Expected: 179 tests passing.

Stop on first failure. Report full wave audit summary when done.
```

## 4. Push

```powershell
cd D:\GoBP
git push origin main
```

## 5. Part B (after push)

Sau khi push xong → thực hiện Task 6 và Task 7 theo hướng dẫn trong Brief.

---

# WHAT COMES NEXT

After Wave 8 pushed and Part B complete:
- **GoBP v1 is DONE.** All 8 waves shipped.
- Begin MIHOS integration: connect GoBP to MIHOS project, start live capture
- Review lessons extracted from GoBP build → apply to MIHOS workflow v2
- Consider: public release prep (PyPI, docs site) — CEO decision

---

*Wave 8 Brief v0.1*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
