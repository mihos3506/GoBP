"""GoBP file loader.

Reads schema YAML, node markdown files, and edge YAML files from disk.
Pure parsing - no validation here (see validator.py).
"""

from pathlib import Path
from typing import Any

import yaml


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Split markdown content into YAML frontmatter and body.

    Frontmatter is delimited by lines containing only ``---``.
    Handles CRLF line endings (Windows compatibility).

    Args:
        content: Full file content as string.

    Returns:
        Tuple of (frontmatter_dict, body_string).
        If no frontmatter, returns ({}, content).

    Raises:
        ValueError: If frontmatter is malformed (missing closing ---).
    """
    # Normalize line endings for Windows
    content = content.replace("\r\n", "\n")

    if not content.startswith("---\n"):
        return {}, content

    # Find closing ---
    lines = content.split("\n")
    closing_index = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = i
            break

    if closing_index is None:
        raise ValueError("Frontmatter missing closing '---' marker")

    frontmatter_text = "\n".join(lines[1:closing_index])
    body_lines = lines[closing_index + 1 :]
    body = "\n".join(body_lines)

    frontmatter_dict = yaml.safe_load(frontmatter_text) or {}

    if not isinstance(frontmatter_dict, dict):
        raise ValueError(f"Frontmatter must be a YAML mapping, got {type(frontmatter_dict).__name__}")

    return frontmatter_dict, body


def load_schema(schema_path: Path) -> dict[str, Any]:
    """Load a schema YAML file (core_nodes.yaml or core_edges.yaml).

    Args:
        schema_path: Path to schema YAML file.

    Returns:
        Parsed YAML as dict.

    Raises:
        FileNotFoundError: If schema file does not exist.
        yaml.YAMLError: If YAML is malformed.
        ValueError: If schema is missing required top-level keys.
    """
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Schema must be a YAML mapping, got {type(data).__name__}")

    if "schema_version" not in data:
        raise ValueError(f"Schema missing 'schema_version' key: {schema_path}")

    return data


def load_node_file(file_path: Path) -> dict[str, Any]:
    """Load a single node markdown file and return its frontmatter as dict.

    The node file has YAML frontmatter followed by markdown body.
    This function returns only the frontmatter dict (the structured data).
    The body is discarded (it's for humans to read, not for the graph).

    Args:
        file_path: Path to node markdown file (.md).

    Returns:
        Node data dict from frontmatter.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file has no frontmatter or malformed frontmatter.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Node file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    frontmatter, _body = parse_frontmatter(content)

    if not frontmatter:
        raise ValueError(f"Node file has no frontmatter: {file_path}")

    return frontmatter


def load_edge_file(file_path: Path) -> list[dict[str, Any]]:
    """Load an edge YAML file and return list of edge dicts.

    Edge files contain a YAML list where each item is one edge.

    Args:
        file_path: Path to edge YAML file.

    Returns:
        List of edge dicts. Empty list if file contains empty list.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If YAML content is not a list.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Edge file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return []

    if not isinstance(data, list):
        raise ValueError(f"Edge file must contain a YAML list, got {type(data).__name__}: {file_path}")

    return data
