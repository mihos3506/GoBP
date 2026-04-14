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
