"""GoBP MCP import tools.

Implementations for import_proposal and import_commit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex


def import_proposal(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "import_proposal not yet implemented"}


def import_commit(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "import_commit not yet implemented"}
