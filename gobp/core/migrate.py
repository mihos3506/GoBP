"""GoBP schema migration.

Handles upgrades when gobp schema version bumps.
Migration is conservative: never deletes fields, only adds missing ones
with safe defaults.

Version format: integer (1, 2, 3, ...).
Current version: 1 (set by Wave 0).

Callers:
- validate tool calls check_version() and warns if mismatch
- node_upsert calls _ensure_node_compatible() before writing

Migration is idempotent: running twice produces same result.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CURRENT_SCHEMA_VERSION = 1


def check_version(gobp_root: Path) -> dict[str, Any]:
    """Check if .gobp/ schema version matches current version.

    Args:
        gobp_root: Project root containing .gobp/ folder.

    Returns:
        Dict with:
        - ok: bool
        - current_version: int (version on disk)
        - expected_version: int (this code's version)
        - needs_migration: bool
        - message: str
    """
    config_path = gobp_root / ".gobp" / "config.yaml"

    if not config_path.exists():
        return {
            "ok": False,
            "current_version": 0,
            "expected_version": CURRENT_SCHEMA_VERSION,
            "needs_migration": True,
            "message": "No config.yaml found. Run gobp init.",
        }

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        return {
            "ok": False,
            "current_version": 0,
            "expected_version": CURRENT_SCHEMA_VERSION,
            "needs_migration": False,
            "message": f"config.yaml parse error: {e}",
        }

    on_disk = config.get("schema_version", 1)

    if on_disk == CURRENT_SCHEMA_VERSION:
        return {
            "ok": True,
            "current_version": on_disk,
            "expected_version": CURRENT_SCHEMA_VERSION,
            "needs_migration": False,
            "message": "Schema version up to date.",
        }

    return {
        "ok": False,
        "current_version": on_disk,
        "expected_version": CURRENT_SCHEMA_VERSION,
        "needs_migration": on_disk < CURRENT_SCHEMA_VERSION,
        "message": (
            f"Schema mismatch: disk={on_disk}, code={CURRENT_SCHEMA_VERSION}. "
            "Run gobp migrate to upgrade."
        ),
    }


def run_migration(gobp_root: Path) -> dict[str, Any]:
    """Run all pending migrations on .gobp/ folder.

    Idempotent. Safe to run multiple times.

    Args:
        gobp_root: Project root containing .gobp/ folder.

    Returns:
        Dict with:
        - ok: bool
        - steps_run: list[str]
        - message: str
    """
    version_check = check_version(gobp_root)

    if not version_check["needs_migration"]:
        return {
            "ok": True,
            "steps_run": [],
            "message": "No migration needed.",
        }

    on_disk = version_check["current_version"]
    steps_run: list[str] = []

    # Migration chain: run each step in order
    migration_steps = {
        # Example: migrate from v0 to v1
        # ("v0_to_v1", _migrate_v0_to_v1),
    }

    for step_name, step_fn in migration_steps.items():
        try:
            step_fn(gobp_root)
            steps_run.append(step_name)
        except Exception as e:
            return {
                "ok": False,
                "steps_run": steps_run,
                "message": f"Migration failed at step '{step_name}': {e}",
            }

    # Update config version after all steps pass
    _update_config_version(gobp_root, CURRENT_SCHEMA_VERSION)
    steps_run.append(f"updated_config_to_v{CURRENT_SCHEMA_VERSION}")

    return {
        "ok": True,
        "steps_run": steps_run,
        "message": f"Migration complete. Schema now at v{CURRENT_SCHEMA_VERSION}.",
    }


def _update_config_version(gobp_root: Path, version: int) -> None:
    """Update schema_version in config.yaml."""
    config_path = gobp_root / ".gobp" / "config.yaml"

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    config["schema_version"] = version

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
