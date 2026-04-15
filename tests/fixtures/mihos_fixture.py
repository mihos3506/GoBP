"""MIHOS-scale test fixture for GoBP Wave 8 integration tests.

Creates a realistic populated .gobp/ project with:
- 6 Document nodes (representing MIHOS docs)
- 8 Feature/Node nodes
- 6 Decision nodes (LOCKED)
- 4 Idea nodes
- 4 Session nodes
- 2 Lesson nodes
Total: ~30 nodes, ~30 edges

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
    path.write_text(f"---\n{fm.rstrip()}\n---\n", encoding="utf-8")


def _write_edge(root: Path, edge: dict) -> None:
    """Write an edge to .gobp/edges/ as YAML."""
    from_slug = edge["from"].replace(":", "_")
    to_slug = edge["to"].replace(":", "_")
    edge_type = edge["type"]
    path = root / ".gobp" / "edges" / f"{from_slug}__{edge_type}__{to_slug}.yaml"
    path.write_text(
        yaml.dump([edge], allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


def _populate_mihos_project(root: Path) -> None:
    """Populate ``root`` with MIHOS-scale .gobp graph data and schema copies."""
    # Create structure
    (root / ".gobp" / "nodes").mkdir(parents=True)
    (root / ".gobp" / "edges").mkdir(parents=True)
    (root / ".gobp" / "history").mkdir(parents=True)

    # Provision schema files
    repo_schema = Path(__file__).parent.parent.parent / "gobp" / "schema"
    dest_schema = root / "gobp" / "schema"
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
            "session_id": "session:2026-04-15_decisions",
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
            "session_id": "session:2026-04-14_foundation",
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
            "session_id": "session:2026-04-15_decisions",
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
            "session_id": "session:2026-04-15_decisions",
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
            "session_id": "session:2026-04-14_foundation",
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
            "session_id": "session:2026-04-15_decisions",
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
            "maturity": "RAW",
            "confidence": "medium",
            "session_id": "session:2026-04-15_current",
            "created": _days_ago(1), "updated": _days_ago(1),
        },
        {
            "id": "idea:i002", "type": "Idea",
            "name": "Provider reputation score",
            "subject": "provider:reputation",
            "raw_quote": "Provider nên có điểm uy tín",
            "interpretation": "Heritage providers need a trust/reputation system",
            "maturity": "REFINED",
            "confidence": "high",
            "session_id": "session:2026-04-15_decisions",
            "created": _days_ago(2), "updated": _days_ago(1),
        },
        {
            "id": "idea:i003", "type": "Idea",
            "name": "Batch imprint upload for providers",
            "subject": "provider:batch.upload",
            "raw_quote": "Provider nên upload nhiều imprint một lúc",
            "interpretation": "Provider admin needs batch upload capability",
            "maturity": "RAW",
            "confidence": "low",
            "session_id": "session:2026-04-15_current",
            "created": _days_ago(1), "updated": _days_ago(1),
        },
        {
            "id": "idea:i004", "type": "Idea",
            "name": "Wallet integration with VN payment gateways",
            "subject": "economy:payment.gateway",
            "raw_quote": "Cần tích hợp VNPay hoặc MoMo",
            "interpretation": "Wallet must support local VN payment methods",
            "maturity": "REFINED",
            "confidence": "high",
            "session_id": "session:2026-04-15_decisions",
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
        _write_node(root, node)

    # ── Write edges (~30) ─────────────────────────────────────────────────────
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
        _write_edge(root, edge)


@pytest.fixture
def mihos_root(tmp_path: Path) -> Path:
    """Realistic MIHOS-scale populated GoBP project root.

    ~30 nodes, ~30 edges. Schema files provisioned.
    Returns project root ready for GraphIndex.load_from_disk().
    """
    _populate_mihos_project(tmp_path)
    return tmp_path


if __name__ == "__main__":
    import tempfile

    from gobp.core.graph import GraphIndex

    _scratch = Path(tempfile.mkdtemp(prefix="gobp_mihos_"))
    _populate_mihos_project(_scratch)
    _idx = GraphIndex.load_from_disk(_scratch)
    print("nodes", len(_idx), "edges", len(_idx.all_edges()), "load_errors", _idx.load_errors)
