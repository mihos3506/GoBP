"""Tests for GoBP Wave B — Cleanup + Dashboard."""

from __future__ import annotations

from pathlib import Path

import pytest

# ── Deprecated docs cleanup ───────────────────────────────────────────────────

DOCS_ROOT = Path(__file__).parent.parent / "docs"

DEPRECATED_DOCS = [
    "GoBP_ARCHITECTURE.md",
    "MCP_TOOLS.md",
    "GoBP_AI_USER_GUIDE.md",
    "GOBP_SCHEMA_REDESIGN_v2_1.md",
    "INPUT_MODEL.md",
    "IMPORT_MODEL.md",
    "IMPORT_CHECKLIST.md",
]

V3_DOCS = [
    "SCHEMA.md",
    "ARCHITECTURE.md",
    "MCP_PROTOCOL.md",
    "COOKBOOK.md",
    "AGENT_RULES.md",
    "HISTORY_SPEC.md",
    "README.md",
]


@pytest.mark.parametrize("filename", DEPRECATED_DOCS)
def test_deprecated_doc_removed(filename: str) -> None:
    """Deprecated docs phải không còn tồn tại."""
    path = DOCS_ROOT / filename
    if filename == "GOBP_SCHEMA_REDESIGN_v2_1.md":
        alt = DOCS_ROOT / "GOBP_SCHEMA_REDESIGN_v2.1.md"
        assert not path.exists() and not alt.exists(), (
            "Deprecated GOBP_SCHEMA_REDESIGN still exists (v2_1 or v2.1 filename)."
        )
    else:
        assert not path.exists(), (
            f"Deprecated doc still exists: {path}. "
            f"Should have been removed in Wave B Task 1."
        )


@pytest.mark.parametrize("filename", V3_DOCS)
def test_v3_doc_exists(filename: str) -> None:
    """V3 docs phải tồn tại."""
    path = DOCS_ROOT / filename
    assert path.exists(), f"V3 doc missing: {path}"


# ── Viewer files ──────────────────────────────────────────────────────────────

VIEWER_ROOT = Path(__file__).parent.parent / "gobp" / "viewer"


def test_dashboard_html_exists() -> None:
    """dashboard.html phải tồn tại."""
    assert (VIEWER_ROOT / "dashboard.html").exists()


def test_dashboard_html_has_api_call() -> None:
    """dashboard.html phải call /api/dashboard."""
    content = (VIEWER_ROOT / "dashboard.html").read_text(encoding="utf-8")
    assert "/api/dashboard" in content


def test_dashboard_html_has_nav_link() -> None:
    """dashboard.html phải có nav link về Graph View."""
    content = (VIEWER_ROOT / "dashboard.html").read_text(encoding="utf-8")
    assert 'href="/"' in content


def test_index_html_has_dashboard_link() -> None:
    """index.html phải có link tới /dashboard."""
    index = VIEWER_ROOT / "index.html"
    if index.exists():
        content = index.read_text(encoding="utf-8")
        assert "/dashboard" in content, "index.html should contain a link to /dashboard"


# ── .cursorrules ──────────────────────────────────────────────────────────────


def test_cursorrules_has_schema_v3() -> None:
    """.cursorrules phải có schema v3 section."""
    cursorrules = Path(__file__).parent.parent / ".cursorrules"
    assert cursorrules.exists(), ".cursorrules not found"
    content = cursorrules.read_text(encoding="utf-8")
    assert "Schema v3" in content, ".cursorrules missing Schema v3 section"


# ── Wave A modules still importable ──────────────────────────────────────────


def test_wave_a_modules_importable() -> None:
    """Wave A modules phải vẫn importable sau Wave B cleanup."""
    from gobp.core.file_format_v3 import serialize_node
    from gobp.core.pyramid import extract_pyramid
    from gobp.core.validator_v3 import ValidatorV3

    assert extract_pyramid("test.") == ("test.", "test.")
    assert ValidatorV3() is not None
    assert serialize_node({"name": "x", "group": "y", "description": "z"})
