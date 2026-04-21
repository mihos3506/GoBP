#!/usr/bin/env python3
"""Refresh the machine-readable node-type block in ``docs/SCHEMA.md``.

``schema_governance`` checks that every key in ``gobp/schema/core_nodes.yaml``
appears as a substring of ``docs/SCHEMA.md``. This script writes one type name
per line inside HTML comment markers so governance passes without hand-editing
dozens of headings.

Usage (from repo root)::

    python scripts/generate_schema_governance_index.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

MARK_START = "<!-- SCHEMA_GOVERNANCE_NODE_TYPES_START -->"
MARK_END = "<!-- SCHEMA_GOVERNANCE_NODE_TYPES_END -->"

BLOCK_HEADER = f"""---

## Schema governance — node type index

{MARK_START}
**One line per ``node_types`` key from ``gobp/schema/core_nodes.yaml`` (substring check).**

"""

BLOCK_FOOTER = f"\n{MARK_END}\n"


def _build_block(node_types: list[str]) -> str:
    lines = [BLOCK_HEADER]
    for name in node_types:
        lines.append(f"{name}\n")
    lines.append(BLOCK_FOOTER)
    return "".join(lines)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    schema_path = root / "gobp" / "schema" / "core_nodes.yaml"
    doc_path = root / "docs" / "SCHEMA.md"

    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    node_types = sorted(schema.get("node_types", {}).keys())
    if not node_types:
        print("No node_types in schema", file=sys.stderr)
        return 1

    block = _build_block(node_types)
    text = doc_path.read_text(encoding="utf-8")

    pattern = re.compile(
        re.escape(MARK_START) + r".*?" + re.escape(MARK_END),
        re.DOTALL,
    )
    if MARK_START in text and MARK_END in text:
        new_text, n = pattern.subn(block.strip() + "\n", text, count=1)
        if n != 1:
            print("Could not replace governance block once", file=sys.stderr)
            return 1
        doc_path.write_text(new_text, encoding="utf-8")
    else:
        doc_path.write_text(text.rstrip() + "\n\n" + block, encoding="utf-8")

    print(f"Updated {doc_path} with {len(node_types)} node type lines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
