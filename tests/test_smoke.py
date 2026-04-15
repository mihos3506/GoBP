"""Smoke tests for GoBP Wave 0 deliverables.

These tests verify:
1. The gobp package can be imported
2. All stub modules exist
3. Schema YAML files are valid and complete
4. Templates exist with correct frontmatter

They do NOT test business logic - that begins in Wave 1.
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
    """CLI module can be imported and has main function."""
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
    """core_nodes.yaml exists."""
    schema_file = get_schema_dir() / "core_nodes.yaml"
    assert schema_file.exists(), f"Missing: {schema_file}"


def test_core_edges_yaml_exists():
    """core_edges.yaml exists."""
    schema_file = get_schema_dir() / "core_edges.yaml"
    assert schema_file.exists(), f"Missing: {schema_file}"


def test_core_nodes_yaml_valid():
    """core_nodes.yaml is valid YAML with correct structure."""
    schema_file = get_schema_dir() / "core_nodes.yaml"
    with open(schema_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "schema_version" in data
    assert data["schema_version"] == "2.0"
    assert "node_types" in data

    expected_types = {
        "Node",
        "Idea",
        "Decision",
        "Session",
        "Document",
        "Lesson",
        "Concept",
        "TestKind",
        "TestCase",
    }
    actual_types = set(data["node_types"].keys())
    assert expected_types.issubset(actual_types), (
        f"Missing core types: {expected_types - actual_types}"
    )


def test_core_edges_yaml_valid():
    """core_edges.yaml is valid YAML with correct structure."""
    schema_file = get_schema_dir() / "core_edges.yaml"
    with open(schema_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "schema_version" in data
    assert data["schema_version"] == "2.0"
    assert "edge_types" in data

    expected_types = {
        "relates_to",
        "supersedes",
        "implements",
        "discovered_in",
        "references",
        "covers",
        "of_kind",
    }
    actual_types = set(data["edge_types"].keys())
    assert actual_types == expected_types, f"Expected {expected_types}, got {actual_types}"


def test_every_node_type_has_required_fields():
    """Each node type declares required fields."""
    schema_file = get_schema_dir() / "core_nodes.yaml"
    with open(schema_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for type_name, type_def in data["node_types"].items():
        assert "required" in type_def, f"{type_name} missing 'required' section"
        assert "id" in type_def["required"], f"{type_name} missing required 'id'"
        assert "created" in type_def["required"], f"{type_name} missing required 'created'"


def test_every_edge_type_has_from_to():
    """Each edge type has from and to fields."""
    schema_file = get_schema_dir() / "core_edges.yaml"
    with open(schema_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for type_name, type_def in data["edge_types"].items():
        assert "required" in type_def, f"{type_name} missing 'required' section"
        assert "from" in type_def["required"], f"{type_name} missing 'from'"
        assert "to" in type_def["required"], f"{type_name} missing 'to'"


# =============================================================================
# Template file tests
# =============================================================================


def get_templates_dir() -> Path:
    """Return the path to the gobp/templates/ folder."""
    import gobp

    return Path(gobp.__file__).parent / "templates"


def test_all_templates_exist():
    """All 9 template files exist."""
    expected = [
        "node.md",
        "idea.md",
        "decision.md",
        "session.md",
        "document.md",
        "lesson.md",
        "concept.md",
        "testkind.md",
        "testcase.md",
    ]
    templates_dir = get_templates_dir()

    for template_name in expected:
        template_file = templates_dir / template_name
        assert template_file.exists(), f"Missing template: {template_file}"


def test_templates_have_yaml_frontmatter():
    """Each template starts and ends YAML frontmatter correctly."""
    templates_dir = get_templates_dir()

    for template_file in templates_dir.glob("*.md"):
        content = template_file.read_text(encoding="utf-8")
        # Normalize CRLF to LF for Windows compatibility
        content = content.replace("\r\n", "\n")
        assert content.startswith("---\n"), f"{template_file.name} missing frontmatter start"
        lines = content.split("\n")
        closing_found = False
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                closing_found = True
                break
        assert closing_found, f"{template_file.name} missing frontmatter end"


def test_templates_frontmatter_parseable():
    """Each template's frontmatter is valid YAML."""
    templates_dir = get_templates_dir()

    for template_file in templates_dir.glob("*.md"):
        content = template_file.read_text(encoding="utf-8")
        # Normalize CRLF to LF for Windows compatibility
        content = content.replace("\r\n", "\n")
        parts = content.split("---\n", 2)
        assert len(parts) >= 3, f"{template_file.name} frontmatter malformed"
        frontmatter_text = parts[1]
        data = yaml.safe_load(frontmatter_text)
        assert data is not None
        assert "id" in data, f"{template_file.name} frontmatter missing 'id'"
        assert "type" in data, f"{template_file.name} frontmatter missing 'type'"
