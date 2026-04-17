"""GoBP project initialization.

Creates .gobp/ folder structure for a new GoBP project.
Called by `python -m gobp.cli init`.

After init, project root can be used as GOBP_PROJECT_ROOT
for MCP server connections.
"""

from __future__ import annotations

import copy
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from gobp.core.id_config import DEFAULT_GROUPS

INIT_SCHEMA_VERSION = 2  # Wave 4 introduces schema v2


def sync_config_schema_version(project_root: Path) -> dict[str, Any]:
    """Raise ``.gobp/config.yaml`` ``schema_version`` to ``INIT_SCHEMA_VERSION`` if lower or missing.

    Use after pulling new core schema or running ``seed-universal`` repair so tooling
    agrees with packaged init baseline.

    Args:
        project_root: GoBP project root.

    Returns:
        ``ok``, ``changed``, and version details.
    """
    config_path = project_root / ".gobp" / "config.yaml"
    if not config_path.exists():
        return {"ok": False, "error": f"Missing {config_path}", "changed": False}
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    raw_version = raw.get("schema_version", 0)
    try:
        current = int(raw_version)
    except (TypeError, ValueError):
        current = 0
    if current < INIT_SCHEMA_VERSION:
        previous = raw.get("schema_version")
        raw["schema_version"] = INIT_SCHEMA_VERSION
        with open(config_path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(
                raw,
                fh,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        return {
            "ok": True,
            "changed": True,
            "previous": previous,
            "set_to": INIT_SCHEMA_VERSION,
        }
    return {"ok": True, "changed": False, "schema_version": raw.get("schema_version")}


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
    project_id = name.lower().replace(" ", "-")
    config = {
        "project_name": name,
        "project_id": project_id,
        "project_description": "",
        "schema_version": INIT_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "gobp_version": "0.1.0",
        # Multi-user placeholders — null/inactive in v1, ready for v2 upgrade
        "owner": None,
        "collaborators": [],
        "access_model": "open",
        "id_groups": copy.deepcopy(DEFAULT_GROUPS),
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
        if src.exists() and src.resolve() != dst.resolve():
            shutil.copy(src, dst)
            created.append(str(dst.relative_to(project_root)))

    # Seed universal TestKind + Concept nodes (fresh tree: write all)
    seed_out = seed_universal_nodes(project_root, only_missing=False)

    return {
        "ok": True,
        "message": f"Initialized GoBP project '{name}' at {project_root}",
        "created": created,
        "seeded_nodes": seed_out.get("created", []),
        "already_exists": False,
    }


def seed_universal_nodes(project_root: Path, *, only_missing: bool = False) -> dict[str, Any]:
    """Seed 16 universal TestKind nodes + 1 Concept node (canonical taxonomy).

    Args:
        project_root: GoBP project root (contains ``.gobp/nodes/``).
        only_missing: If True, skip node files that already exist (safe repair).
            If False, overwrite or create every seed file (``init`` behavior).

    Returns:
        Dict with ``ok``, ``created`` (ids written this run), ``skipped`` (ids skipped).
    """
    now = datetime.now(timezone.utc).isoformat()
    nodes_dir = project_root / ".gobp" / "nodes"

    seeds = [
        # --- FUNCTIONAL GROUP (6 kinds) ---
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
        },
        # --- NON-FUNCTIONAL GROUP (3 kinds) ---
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
        },
        # --- PROCESS GROUP (2 kinds) ---
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
        },
        # --- SECURITY GROUP (5 sub-kinds) ---
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
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
            ],            "extensible": True,
            "created": now,
            "updated": now,
        },
        # --- CONCEPT NODE ---
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
            "created": now,
            "updated": now,
        },
    ]

    created_ids: list[str] = []
    skipped_ids: list[str] = []
    for node in seeds:
        node_id = node["id"]
        slug = node_id.replace(":", "_")
        node_path = nodes_dir / f"{slug}.md"
        import yaml as _yaml

        if only_missing and node_path.exists():
            skipped_ids.append(node_id)
            continue

        fm = _yaml.dump(node, allow_unicode=True, default_flow_style=False)
        node_path.write_text(f"---\n{fm}---\n", encoding="utf-8")
        created_ids.append(node_id)

    return {"ok": True, "created": created_ids, "skipped": skipped_ids}



