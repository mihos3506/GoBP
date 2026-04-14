"""GoBP MCP read tools.

Implementations in Tasks 2-8 of Wave 3.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import gobp

from gobp.core.graph import GraphIndex


def _truncate(text: str, max_chars: int = 100) -> str:
    """Truncate text to max_chars, appending '...' if truncated."""
    if text is None:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def gobp_overview(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Return project metadata, stats, main topics, and suggested next queries.

    First tool AI should call when connecting to a new GoBP instance.
    Takes no arguments.
    """
    all_nodes = index.all_nodes()
    all_edges = index.all_edges()

    # Project metadata from charter Document node if exists
    project_name = "Unknown"
    project_description = "GoBP-managed project"

    charter = index.get_node("doc:charter")
    if charter:
        project_name = charter.get("name", project_name)
        project_description = charter.get("description", project_description)
    else:
        # Try first Document node
        docs = index.nodes_by_type("Document")
        if docs:
            project_name = docs[0].get("name", project_name)

    # Stats
    nodes_by_type: dict[str, int] = {}
    for node in all_nodes:
        t = node.get("type", "Unknown")
        nodes_by_type[t] = nodes_by_type.get(t, 0) + 1

    edges_by_type: dict[str, int] = {}
    for edge in all_edges:
        t = edge.get("type", "Unknown")
        edges_by_type[t] = edges_by_type.get(t, 0) + 1

    # Main topics from Decision nodes (top by frequency)
    topic_counts: dict[str, int] = {}
    for node in index.nodes_by_type("Decision"):
        topic = node.get("topic")
        if topic:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

    main_topics = sorted(topic_counts.keys(), key=lambda k: -topic_counts[k])[:10]

    # Recent decisions (top 5 by locked_at, if available)
    decision_nodes = index.nodes_by_type("Decision")
    locked_decisions = [
        n for n in decision_nodes if n.get("status") == "LOCKED" and n.get("locked_at")
    ]
    locked_decisions.sort(key=lambda n: n.get("locked_at", ""), reverse=True)

    recent_decisions = [
        {
            "id": n.get("id"),
            "topic": n.get("topic", ""),
            "what": _truncate(n.get("what", "")),
            "locked_at": n.get("locked_at"),
        }
        for n in locked_decisions[:5]
    ]

    # Recent sessions (top 3 by started_at)
    session_nodes = index.nodes_by_type("Session")
    session_nodes.sort(key=lambda n: n.get("started_at", ""), reverse=True)

    recent_sessions = [
        {
            "id": n.get("id"),
            "goal": _truncate(n.get("goal", "")),
            "status": n.get("status", ""),
            "started_at": n.get("started_at"),
        }
        for n in session_nodes[:3]
    ]

    return {
        "ok": True,
        "project": {
            "name": project_name,
            "description": project_description,
            "gobp_version": getattr(gobp, "__version__", "0.1.0"),
            "schema_version": "1.0",
            "pattern": "per_project",
        },
        "stats": {
            "total_nodes": len(all_nodes),
            "total_edges": len(all_edges),
            "nodes_by_type": nodes_by_type,
            "edges_by_type": edges_by_type,
        },
        "main_topics": main_topics,
        "recent_decisions": recent_decisions,
        "recent_sessions": recent_sessions,
        "suggested_next_queries": [
            "find(query='<keyword>') to search nodes by keyword",
            "decisions_for(topic='<topic>') to find locked decisions on a topic",
            "session_recent(n=3) to see recent session history",
        ],
    }


def find(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "find not yet implemented"}


def signature(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "signature not yet implemented"}


def context(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "context not yet implemented"}


def session_recent(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "session_recent not yet implemented"}


def decisions_for(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "decisions_for not yet implemented"}


def doc_sections(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "error": "doc_sections not yet implemented"}
