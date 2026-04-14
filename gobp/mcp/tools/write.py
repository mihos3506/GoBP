"""GoBP MCP write tools.

Implementations for node_upsert, decision_lock, session_log.
All write tools require an active session_id.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex


def node_upsert(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "node_upsert not yet implemented"}


def decision_lock(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "decision_lock not yet implemented"}


def session_log(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "session_log not yet implemented"}
