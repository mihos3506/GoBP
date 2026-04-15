"""GoBP MCP read tools.

Implementations in Tasks 2-8 of Wave 3.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import gobp

from gobp.core.graph import GraphIndex


_FIND_PRIORITY: dict[str, int] = {"exact_id": 0, "exact_name": 1, "substring": 2}


def _truncate(text: str | None, max_chars: int = 100) -> str:
    """Truncate text to max_chars, appending '...' if truncated."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def gobp_overview(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Return project metadata, stats, main topics, and suggested next queries.

    First tool AI should call when connecting to a new GoBP instance.
    Takes no arguments.
    """
    from gobp.mcp.dispatcher import PROTOCOL_GUIDE

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

    # Concepts — for AI orientation
    concept_nodes = [n for n in index.all_nodes() if n.get("type") == "Concept"]
    concepts = [
        {
            "id": n.get("id", ""),
            "name": n.get("name", ""),
            "definition": _truncate(n.get("definition", ""), 200),
            "usage_guide": _truncate(n.get("usage_guide", ""), 300),
            "applies_to": n.get("applies_to", []),
        }
        for n in concept_nodes[:10]
    ]

    # Test coverage summary
    test_kind_nodes = [n for n in index.all_nodes() if n.get("type") == "TestKind"]
    kinds_by_group: dict[str, int] = {}
    for tk in test_kind_nodes:
        g = tk.get("group", "unknown")
        kinds_by_group[g] = kinds_by_group.get(g, 0) + 1

    test_case_nodes = [n for n in index.all_nodes() if n.get("type") == "TestCase"]
    cases_by_status: dict[str, int] = {}
    for tc in test_case_nodes:
        s = tc.get("status", "DRAFT")
        cases_by_status[s] = cases_by_status.get(s, 0) + 1

    # Priority summary
    priority_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for node in all_nodes:
        p = node.get("priority", "medium")
        if p in priority_counts:
            priority_counts[p] += 1
        else:
            priority_counts["medium"] += 1

    critical_nodes = [
        {"id": n.get("id"), "type": n.get("type"), "name": n.get("name", "")}
        for n in all_nodes
        if n.get("priority") == "critical"
    ][:10]

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
            "gobp(query='find: <keyword>') to search nodes",
            "gobp(query='find:Decision <topic>') to find decisions",
            "gobp(query='session:start actor=<name> goal=<goal>') to start session",
        ],
        "concepts": concepts,
        "test_coverage": {
            "kinds_available": len(test_kind_nodes),
            "kinds_by_group": kinds_by_group,
            "test_cases_total": len(test_case_nodes),
            "test_cases_by_status": cases_by_status,
        },
        "priority_summary": {
            "critical": priority_counts["critical"],
            "high": priority_counts["high"],
            "medium": priority_counts["medium"],
            "low": priority_counts["low"],
            "critical_nodes": critical_nodes,
        },
        "interface": PROTOCOL_GUIDE,
    }


def find(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Search nodes by keyword with optional type filter.

    Input:
        query: str — search term (required)
        limit: int — max results (default 20)
        type: str — filter by node type, e.g. "TestCase", "TestKind" (optional)

    Output:
        ok, nodes, count
    """
    query = args.get("query", "")
    if not query:
        return {"ok": False, "error": "Missing required field: query"}

    limit = int(args.get("limit", 20))
    type_filter = args.get("type", None)

    query_lower = query.lower()
    matches: list[dict[str, Any]] = []

    # Exact ID match (highest priority)
    exact_id_node = index.get_node(query)
    if exact_id_node and (not type_filter or exact_id_node.get("type") == type_filter):
        matches.append(
            {
                "id": exact_id_node.get("id", ""),
                "type": exact_id_node.get("type", ""),
                "name": exact_id_node.get("name", ""),
                "status": exact_id_node.get("status", ""),
                "match": "exact_id",
            }
        )

    # Exact name + substring matches
    for node in index.all_nodes():
        # Type filter first (cheap)
        if type_filter and node.get("type") != type_filter:
            continue

        node_id = node.get("id", "")
        if node_id == query:
            continue  # Already added as exact_id

        node_name = node.get("name", "")
        node_name_lower = node_name.lower()

        # Text search across key fields
        searchable = f"{node_id} {node_name}".lower()
        for field in ("topic", "subject", "title", "description", "definition", "group"):
            val = node.get(field, "")
            if val:
                searchable += f" {str(val).lower()}"

        if node_name_lower == query_lower:
            match_type = "exact_name"
        elif query_lower in searchable:
            match_type = "substring"
        else:
            continue

        matches.append(
            {
                "id": node_id,
                "type": node.get("type", ""),
                "name": node_name,
                "status": node.get("status", ""),
                "match": match_type,
            }
        )

    matches.sort(key=lambda m: _FIND_PRIORITY.get(m["match"], 99))
    total = len(matches)
    truncated = total > limit
    matches = matches[:limit]

    return {"ok": True, "matches": matches, "count": len(matches), "truncated": truncated}


def signature(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get minimal node summary.

    Args:
        node_id: str (required)

    Returns:
        Basic node fields without edges or decisions.
    """
    node_id = args.get("node_id")
    if not node_id:
        return {"ok": False, "error": "node_id parameter required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    # Copy key fields
    signature_fields = {
        "id": node.get("id"),
        "type": node.get("type"),
        "name": node.get("name", ""),
        "status": node.get("status", ""),
    }

    # Add common optional fields if present
    for field in ["subtype", "description", "tags", "topic", "what", "why", "goal"]:
        if field in node:
            signature_fields[field] = node[field]

    return {
        "ok": True,
        "signature": signature_fields,
    }


def context(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get node + outgoing/incoming edges + applicable decisions.

    Args:
        node_id: str (required)
        depth: int (optional, default 1) - hop depth, v1 max 2

    Returns:
        Full node, edges, decisions, references.
    """
    node_id = args.get("node_id")
    if not node_id:
        return {"ok": False, "error": "node_id parameter required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    # Outgoing edges
    outgoing_raw = index.get_edges_from(node_id)
    outgoing = []
    for edge in outgoing_raw:
        to_node = index.get_node(edge.get("to", ""))
        outgoing.append(
            {
                "type": edge.get("type"),
                "to": edge.get("to"),
                "to_name": to_node.get("name", "") if to_node else "",
                "to_type": to_node.get("type", "") if to_node else "",
            }
        )

    # Incoming edges
    incoming_raw = index.get_edges_to(node_id)
    incoming = []
    for edge in incoming_raw:
        from_node = index.get_node(edge.get("from", ""))
        incoming.append(
            {
                "type": edge.get("type"),
                "from": edge.get("from"),
                "from_name": from_node.get("name", "") if from_node else "",
                "from_type": from_node.get("type", "") if from_node else "",
            }
        )

    # Applicable decisions: via 'implements' edges + topic match
    decisions: list[dict[str, Any]] = []
    seen_decision_ids: set[str] = set()

    # Decisions via edges
    for edge in outgoing_raw:
        target = index.get_node(edge.get("to", ""))
        if target and target.get("type") == "Decision":
            dec_id = target.get("id")
            if dec_id not in seen_decision_ids:
                decisions.append(
                    {
                        "id": dec_id,
                        "what": target.get("what", ""),
                        "why": target.get("why", ""),
                        "status": target.get("status", ""),
                    }
                )
                seen_decision_ids.add(dec_id)

    # References (via 'references' edges to Document nodes)
    references = []
    for edge in outgoing_raw:
        if edge.get("type") != "references":
            continue
        target = index.get_node(edge.get("to", ""))
        if target and target.get("type") == "Document":
            references.append(
                {
                    "doc_id": target.get("id"),
                    "section": edge.get("section", ""),
                    "lines": edge.get("lines", []),
                }
            )

    return {
        "ok": True,
        "node": node,
        "outgoing": outgoing,
        "incoming": incoming,
        "decisions": decisions,
        "invariants": [],  # Extension schemas; empty in core v1
        "references": references,
    }


def session_recent(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get the latest N sessions for continuity.

    Args:
        n: int (optional, default 3, max 10)
        before: str (optional) - ISO timestamp filter
        actor: str (optional) - filter by actor
    """
    n = min(int(args.get("n", 3)), 10)
    before = args.get("before")
    actor_filter = args.get("actor")

    sessions = index.nodes_by_type("Session")

    # Filter by actor
    if actor_filter:
        sessions = [s for s in sessions if s.get("actor") == actor_filter]

    # Filter by before timestamp
    if before:
        sessions = [s for s in sessions if s.get("started_at", "") < before]

    # Sort by started_at descending
    sessions.sort(key=lambda s: s.get("started_at", ""), reverse=True)
    sessions = sessions[:n]

    session_list = [
        {
            "id": s.get("id"),
            "actor": s.get("actor", ""),
            "started_at": s.get("started_at"),
            "ended_at": s.get("ended_at"),
            "goal": s.get("goal", ""),
            "outcome": s.get("outcome", ""),
            "status": s.get("status", ""),
            "pending": s.get("pending", []),
            "handoff_notes": s.get("handoff_notes", ""),
        }
        for s in sessions
    ]

    return {
        "ok": True,
        "sessions": session_list,
        "count": len(session_list),
    }


def decisions_for(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get locked decisions for a topic or node.

    Args:
        topic: str (optional) - topic filter
        node_id: str (optional) - get decisions related to this node
        status: str (optional, default LOCKED) - LOCKED | SUPERSEDED | WITHDRAWN | ALL

    One of topic or node_id must be provided.
    """
    topic = args.get("topic")
    node_id = args.get("node_id")
    status_filter = args.get("status", "LOCKED")

    if not topic and not node_id:
        return {"ok": False, "error": "Either 'topic' or 'node_id' must be provided"}

    all_decisions = index.nodes_by_type("Decision")

    # Status filter
    if status_filter != "ALL":
        all_decisions = [d for d in all_decisions if d.get("status") == status_filter]

    # Topic filter
    if topic:
        matching = [d for d in all_decisions if d.get("topic") == topic]
    else:
        # node_id filter: decisions that have an edge pointing to/from this node
        matching = []
        seen: set[str] = set()
        # Decisions where this node is referenced via edges
        for edge in index.all_edges():
            if edge.get("type") not in ("implements", "relates_to"):
                continue
            dec_id = None
            if edge.get("from") == node_id:
                dec_id = edge.get("to")
            elif edge.get("to") == node_id:
                dec_id = edge.get("from")
            if dec_id and dec_id not in seen:
                dec = index.get_node(dec_id)
                if dec and dec.get("type") == "Decision":
                    if status_filter == "ALL" or dec.get("status") == status_filter:
                        matching.append(dec)
                        seen.add(dec_id)

    decisions_out = [
        {
            "id": d.get("id"),
            "topic": d.get("topic", ""),
            "what": d.get("what", ""),
            "why": d.get("why", ""),
            "status": d.get("status", ""),
            "locked_at": d.get("locked_at"),
            "alternatives_considered": d.get("alternatives_considered", []),
        }
        for d in matching
    ]

    return {
        "ok": True,
        "decisions": decisions_out,
        "count": len(decisions_out),
    }


def doc_sections(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """List sections of a Document node without loading content.

    Args:
        doc_id: str (required)
    """
    doc_id = args.get("doc_id")
    if not doc_id:
        return {"ok": False, "error": "doc_id parameter required"}

    doc = index.get_node(doc_id)
    if not doc:
        return {"ok": False, "error": f"Document not found: {doc_id}"}

    if doc.get("type") != "Document":
        return {"ok": False, "error": f"Node {doc_id} is not a Document (type={doc.get('type')})"}

    sections = doc.get("sections", [])

    return {
        "ok": True,
        "document": {
            "id": doc.get("id"),
            "name": doc.get("name", ""),
            "source_path": doc.get("source_path", ""),
            "last_verified": doc.get("last_verified"),
        },
        "sections": sections,
        "count": len(sections),
    }
