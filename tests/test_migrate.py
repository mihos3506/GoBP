"""Tests for gobp.core.migrate module."""

from pathlib import Path

import pytest
import yaml

from gobp.core.migrate import (
    CURRENT_SCHEMA_VERSION,
    check_version,
    run_migration,
)


def _make_gobp_with_version(tmp_path: Path, version: int) -> Path:
    gobp_dir = tmp_path / ".gobp"
    gobp_dir.mkdir()
    config = {"schema_version": version, "project_name": "test"}
    (gobp_dir / "config.yaml").write_text(
        yaml.dump(config, allow_unicode=True), encoding="utf-8"
    )
    return tmp_path


def test_check_version_current(tmp_path: Path):
    """check_version returns ok=True when version matches."""
    root = _make_gobp_with_version(tmp_path, CURRENT_SCHEMA_VERSION)
    result = check_version(root)
    assert result["ok"] is True
    assert result["needs_migration"] is False


def test_check_version_missing_config(tmp_path: Path):
    """check_version returns ok=False when no config.yaml."""
    (tmp_path / ".gobp").mkdir()
    result = check_version(tmp_path)
    assert result["ok"] is False
    assert result["needs_migration"] is True


def test_check_version_old_version(tmp_path: Path):
    """check_version detects outdated schema."""
    root = _make_gobp_with_version(tmp_path, 0)
    result = check_version(root)
    assert result["ok"] is False
    assert result["current_version"] == 0
    assert result["needs_migration"] is True


def test_run_migration_no_op_when_current(tmp_path: Path):
    """run_migration is no-op when version is current."""
    root = _make_gobp_with_version(tmp_path, CURRENT_SCHEMA_VERSION)
    result = run_migration(root)
    assert result["ok"] is True
    assert result["steps_run"] == []
    assert "No migration needed" in result["message"]


def test_run_migration_idempotent(tmp_path: Path):
    """run_migration can be called twice safely."""
    root = _make_gobp_with_version(tmp_path, CURRENT_SCHEMA_VERSION)
    run_migration(root)
    result = run_migration(root)
    assert result["ok"] is True


def test_check_version_returns_expected_version(tmp_path: Path):
    """check_version always reports CURRENT_SCHEMA_VERSION as expected."""
    root = _make_gobp_with_version(tmp_path, 99)
    result = check_version(root)
    assert result["expected_version"] == CURRENT_SCHEMA_VERSION
