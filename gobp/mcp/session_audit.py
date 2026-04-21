"""Audit session resolution for MCP writes.

Graph ``Session`` nodes (Meta > Session) are optional for attribution: a write may
use an **opaque audit id** (host / ``GOBP_SESSION_ID`` / auto ``audit:…``) that does
not correspond to a node on the graph. Only when ``session_id`` resolves to an
existing node with ``type == "Session"`` do we enforce ``COMPLETED`` and attach
``discovered_in`` edges to that node.

Set ``GOBP_GRAPH_SESSION_ONLY=true`` to **reject** opaque ids and auto-``audit:…``:
every write must use an ``IN_PROGRESS`` Session id from ``session:start`` (or set
``GOBP_SESSION_ID`` to that same id). Use this when agents invent random
``session_id`` strings instead of starting a graph session.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from gobp.core.graph import GraphIndex


def graph_session_only_enforced() -> bool:
    """True when env requests graph-backed sessions only (no opaque audit ids)."""
    v = os.environ.get("GOBP_GRAPH_SESSION_ONLY", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def resolve_write_session(
    index: GraphIndex,
    session_id: str | None,
    *,
    allow_auto_audit: bool = True,
) -> tuple[str, dict[str, Any] | None, str | None, bool]:
    """Resolve the audit ``session_id`` for a write operation.

    Args:
        index: Current graph index.
        session_id: Caller-supplied id, or empty.
        allow_auto_audit: If True and no id is available, generate ``audit:{uuid}``.

    Returns:
        Tuple ``(effective_id, session_node_or_none, error_or_none, auto_generated)``.
        ``session_node_or_none`` is set only when ``effective_id`` names an existing
        ``Session`` node (then ``discovered_in`` may link to it).
        ``auto_generated`` is True only when this function invented ``audit:…``.
    """
    raw = (session_id or "").strip()
    audit_auto = False
    if not raw:
        raw = os.environ.get("GOBP_SESSION_ID", "").strip()

    strict = graph_session_only_enforced()
    if not raw:
        if strict:
            return (
                "",
                None,
                "Graph session required: call session:start and pass the returned "
                "session_id on writes, or set GOBP_SESSION_ID to that Session node id "
                "(GOBP_GRAPH_SESSION_ONLY is enabled).",
                False,
            )
        if allow_auto_audit:
            raw = f"audit:{uuid.uuid4().hex}"
            audit_auto = True
    if not raw:
        return "", None, "Missing session_id (set GOBP_SESSION_ID or pass session_id)", False

    node = index.get_node(raw)
    if node is not None and str(node.get("type", "")) == "Session":
        if str(node.get("status", "")).strip().upper() == "COMPLETED":
            return "", None, "Session already ended, start new one", False
        return raw, node, None, False

    if strict:
        return (
            "",
            None,
            "GOBP_GRAPH_SESSION_ONLY: session_id must be an active Session node id from "
            "session:start (or set GOBP_SESSION_ID to that id). "
            f"Refusing opaque or unknown id: {raw!r}.",
            False,
        )

    return raw, None, None, audit_auto


def session_id_is_graph_session(index: GraphIndex, session_id: str) -> bool:
    """Return True if ``session_id`` names an existing ``Session`` node."""
    n = index.get_node(session_id.strip())
    return n is not None and str(n.get("type", "")) == "Session"
