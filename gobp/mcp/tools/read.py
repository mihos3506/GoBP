"""GoBP MCP read tools.

Implementations in Tasks 2-8 of Wave 3.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import gobp
import yaml

from gobp.core.graph import GraphIndex


_FIND_PRIORITY: dict[str, int] = {"exact_id": 0, "exact_name": 1, "substring": 2}


def _truthy(val: Any) -> bool:
    """Coerce MCP/query args to bool for feature flags."""
    if val is True:
        return True
    if val is False or val is None:
        return False
    return str(val).strip().lower() in ("true", "1", "yes", "on")


def _truncate(text: str | None, max_chars: int = 100) -> str:
    """Truncate text to max_chars, appending '...' if truncated."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _node_summary(node: dict[str, Any], index: GraphIndex | None = None) -> dict[str, Any]:
    """Return lightweight node summary (~50 tokens)."""
    node_id = node.get("id", "")
    edge_count = 0
    if index and node_id:
        edge_count = len(index.get_edges_from(node_id)) + len(index.get_edges_to(node_id))
    return {
        "id": node_id,
        "type": node.get("type", ""),
        "name": node.get("name", ""),
        "status": node.get("status", ""),
        "priority": node.get("priority", "medium"),
        "edge_count": edge_count,
        "detail_available": True,
    }


def _node_brief(node: dict[str, Any], index: GraphIndex | None = None) -> dict[str, Any]:
    """Return brief node payload (~150 tokens)."""
    base = _node_summary(node, index)
    skip = {
        "id", "type", "name", "status", "priority", "created", "updated",
        "session_id", "x", "y", "z", "vx", "vy", "vz",
    }
    extra_fields = {k: v for k, v in node.items() if k not in skip and v}
    base.update({k: v for k, v in list(extra_fields.items())[:5]})
    if index:
        out_types: dict[str, int] = {}
        for edge in index.get_edges_from(node.get("id", "")):
            t = edge.get("type", "")
            out_types[t] = out_types.get(t, 0) + 1
        if out_types:
            base["outgoing_edges"] = out_types
    return base


def gobp_overview(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Return project metadata, stats, main topics, and suggested next queries.

    First tool AI should call when connecting to a new GoBP instance.

    Args:
        full_interface / include_interface: if true, include full ``interface``
        (PROTOCOL_GUIDE — large). Default is false: only ``interface_summary``
        plus a hint to load the full catalog when needed.
    """
    from gobp.mcp.dispatcher import PROTOCOL_GUIDE

    full_interface = _truthy(args.get("full_interface")) or _truthy(
        args.get("include_interface")
    )

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

    base: dict[str, Any] = {
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
            "gobp(query='overview: full_interface=true') for full action catalog (large)",
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
    }
    if full_interface:
        base["interface"] = PROTOCOL_GUIDE
    else:
        actions = PROTOCOL_GUIDE.get("actions", {})
        base["interface_summary"] = {
            "protocol": PROTOCOL_GUIDE.get("protocol", ""),
            "format": PROTOCOL_GUIDE.get("format", ""),
            "documented_actions": len(actions),
            "tip": PROTOCOL_GUIDE.get("tip", ""),
            "load_full_protocol": 'gobp(query="overview: full_interface=true")',
        }
        base["pagination_hint"] = (
            "List reads use page_info: use next_cursor with same query for next page "
            "(find / related / tests)."
        )
    return base


def find(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Search nodes by keyword with cursor-based pagination.

    Args:
        query: Search keyword (optional; empty means all nodes)
        type: Node type filter (optional)
        limit: Deprecated alias for page_size
        page_size: Max results per page (default 20, max 100)
        cursor: Opaque pagination cursor (node id of last item)
        sort: Sort field (default: 'id')
        direction: 'asc' or 'desc' (default: 'asc')
    """
    del project_root
    query_str = str(args.get("query", "") or "")
    if "query" not in args:
        return {"ok": False, "error": "Missing required field: query"}
    type_filter = args.get("type")
    page_size = min(int(args.get("page_size", args.get("limit", 20))), 100)
    cursor = args.get("cursor")
    sort_field = args.get("sort", "id")
    direction = str(args.get("direction", "asc")).lower()

    if page_size < 1:
        page_size = 1

    q = query_str.lower()
    candidates: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for node in index.all_nodes():
        if type_filter and node.get("type") != type_filter:
            continue

        node_id = node.get("id", "")
        node_name = node.get("name", "")
        node_name_lower = node_name.lower()

        searchable = f"{node_id} {node_name}".lower()
        for field in ("topic", "subject", "title", "description", "definition", "group"):
            val = node.get(field, "")
            if val:
                searchable += f" {str(val).lower()}"

        match_type = ""
        if not query_str:
            match_type = "substring"
        elif node_id == query_str:
            match_type = "exact_id"
        elif node_name_lower == q:
            match_type = "exact_name"
        elif q in searchable:
            match_type = "substring"

        if not match_type:
            continue
        if node_id in seen_ids:
            continue

        seen_ids.add(node_id)
        enriched = dict(node)
        enriched["match"] = match_type
        candidates.append(enriched)

    # Sort: keep relevance first, then stable field sort.
    reverse = direction == "desc"
    candidates.sort(
        key=lambda n: (
            _FIND_PRIORITY.get(str(n.get("match", "")), 99),
            str(n.get(sort_field, n.get("id", ""))),
        ),
        reverse=reverse,
    )

    # Apply cursor (keyset pagination)
    total_estimate = len(candidates)
    if cursor:
        try:
            cursor_idx = next(i for i, n in enumerate(candidates) if n.get("id") == cursor)
            candidates = candidates[cursor_idx + 1:]
        except StopIteration:
            candidates = []

    # Page
    page = candidates[:page_size]
    has_more = len(candidates) > page_size
    next_cursor = page[-1].get("id") if has_more and page else None

    mode = str(args.get("mode", "standard")).lower()
    if mode == "summary":
        matches = [_node_summary(n, index) for n in page]
    elif mode == "brief":
        matches = [_node_brief(n, index) for n in page]
    else:
        # Backward compatible default payload.
        matches = [
            {
                "id": n.get("id"),
                "type": n.get("type"),
                "name": n.get("name", ""),
                "status": n.get("status", ""),
                "priority": n.get("priority", "medium"),
                "match": n.get("match", "substring"),
            }
            for n in page
        ]

    return {
        "ok": True,
        "matches": matches,
        "count": len(matches),
        "mode": mode,
        "truncated": has_more,
        "page_info": {
            "next_cursor": next_cursor,
            "has_more": has_more,
            "total_estimate": total_estimate,
            "page_size": page_size,
        },
    }


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
        brief: if true, return a smaller node payload and cap edges per direction
            (default cap 30 each; override with edge_limit, max 200).
        edge_limit: max edges per direction when brief is true.

    Returns:
        Full node, edges, decisions, references (or slimmed when brief).
    """
    del project_root
    node_id = args.get("node_id")
    if not node_id:
        return {"ok": False, "error": "node_id parameter required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    mode = str(args.get("mode", "")).lower()
    if not mode:
        mode = "brief" if _truthy(args.get("brief")) else "full"
    if mode not in {"summary", "brief", "full"}:
        mode = "full"

    brief = mode == "brief"
    if brief:
        edge_limit = int(args.get("edge_limit", 30))
        edge_limit = max(1, min(edge_limit, 200))
    else:
        edge_limit = None

    # Outgoing edges
    outgoing_raw = index.get_edges_from(node_id)
    out_slice = outgoing_raw if edge_limit is None else outgoing_raw[:edge_limit]
    outgoing = []
    for edge in out_slice:
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
    in_slice = incoming_raw if edge_limit is None else incoming_raw[:edge_limit]
    incoming = []
    for edge in in_slice:
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
                what_txt = target.get("what", "")
                why_txt = target.get("why", "")
                if brief:
                    what_txt = _truncate(str(what_txt), 240)
                    why_txt = _truncate(str(why_txt), 240)
                decisions.append(
                    {
                        "id": dec_id,
                        "what": what_txt,
                        "why": why_txt,
                        "status": target.get("status", ""),
                    }
                )
                seen_decision_ids.add(dec_id)

    # References (via 'references' edges to Document nodes)
    references = []
    ref_cap = 15 if brief else None
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
            if ref_cap is not None and len(references) >= ref_cap:
                break

    node_out: dict[str, Any] = dict(node)
    if brief:
        slim: dict[str, Any] = {}
        for k in (
            "id", "type", "name", "status", "priority", "topic", "subject",
            "group", "session_id", "dedupe_key", "maturity", "confidence",
        ):
            if k in node and node[k] not in (None, ""):
                slim[k] = node[k]
        for tk in (
            "description", "definition", "goal", "what", "why",
            "raw_quote", "interpretation", "handoff_notes", "outcome",
        ):
            if tk in node and node[tk]:
                slim[tk] = _truncate(str(node[tk]), 400)
        node_out = slim

    if mode == "summary":
        return {
            "ok": True,
            "node": _node_summary(node, index),
            "mode": mode,
        }

    if mode == "brief":
        return {
            "ok": True,
            "node": _node_brief(node, index),
            "mode": mode,
            "brief": True,
            "edge_count": len(outgoing_raw) + len(incoming_raw),
            "outgoing_total": len(outgoing_raw),
            "incoming_total": len(incoming_raw),
            "outgoing_truncated": len(outgoing_raw) > len(outgoing),
            "incoming_truncated": len(incoming_raw) > len(incoming),
        }

    out: dict[str, Any] = {
        "ok": True,
        "node": node_out,
        "outgoing": outgoing,
        "incoming": incoming,
        "decisions": decisions,
        "invariants": [],  # Extension schemas; empty in core v1
        "references": references,
        "mode": mode,
    }
    if brief:
        out["brief"] = True
        out["outgoing_total"] = len(outgoing_raw)
        out["incoming_total"] = len(incoming_raw)
        out["outgoing_truncated"] = len(outgoing_raw) > len(outgoing)
        out["incoming_truncated"] = len(incoming_raw) > len(incoming)
        out["hint"] = (
            "Slim context: omit brief= or use brief=false for full node body and all edges."
        )
    return out


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


def code_refs(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get code references for a node.

    Returns list of code files implementing or related to this node.
    Only returns code_refs field — much cheaper than full context().

    Args:
        node_id: str (required)
        add: dict (optional) — add a new code ref
             {path, description, language}

    Returns:
        ok, node_id, node_name, code_refs, count
    """
    node_id = args.get("node_id", "")
    if not node_id:
        return {"ok": False, "error": "node_id required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    refs = node.get("code_refs", [])

    return {
        "ok": True,
        "node_id": node_id,
        "node_name": node.get("name", ""),
        "node_type": node.get("type", ""),
        "code_refs": refs,
        "count": len(refs),
        "hint": (
            "To add a code ref: "
            f"gobp(query=\"code: {node_id} path='lib/x.dart' description='x' language='dart'\")"
        ) if not refs else "",
    }


def node_invariants(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get invariants (hard constraints) for a node.

    Returns list of invariant strings — constraints that must always be true.
    Only returns invariants field — much cheaper than full context().

    Args:
        node_id: str (required)

    Returns:
        ok, node_id, node_name, invariants, count
    """
    node_id = args.get("node_id", "")
    if not node_id:
        return {"ok": False, "error": "node_id required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    invs = node.get("invariants", [])

    return {
        "ok": True,
        "node_id": node_id,
        "node_name": node.get("name", ""),
        "node_type": node.get("type", ""),
        "invariants": invs,
        "count": len(invs),
        "hint": (
            "To add an invariant: use update: or create: with invariants field"
        ) if not invs else "",
    }


def node_tests(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get TestCase nodes linked to this node.

    Finds TestCase nodes where covers field = node_id.
    No schema change needed — uses existing covers edges.

    Args:
        node_id: str (required)
        status: str (optional) — filter by status: PASSING, FAILING, DRAFT, etc.

    Returns:
        ok, node_id, node_name, test_cases, count
    """
    node_id = args.get("node_id", "")
    if not node_id:
        return {"ok": False, "error": "node_id required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    status_filter = args.get("status")

    # Find TestCase nodes that cover this node via 'covers' edges
    covering_edges = index.get_edges_to(node_id)
    test_cases = []
    for edge in covering_edges:
        if edge.get("type") != "covers":
            continue
        tc_node = index.get_node(edge.get("from", ""))
        if tc_node and tc_node.get("type") == "TestCase":
            if status_filter and tc_node.get("status") != status_filter:
                continue
            test_cases.append({
                "id": tc_node.get("id"),
                "name": tc_node.get("name", ""),
                "status": tc_node.get("status", "DRAFT"),
                "priority": tc_node.get("priority", "medium"),
                "automated": tc_node.get("automated", False),
                "kind_id": tc_node.get("kind_id", ""),
            })

    # Sort: FAILING first, then DRAFT, then PASSING
    status_order = {"FAILING": 0, "DRAFT": 1, "READY": 2, "PASSING": 3, "SKIPPED": 4, "DEPRECATED": 5}
    test_cases.sort(key=lambda t: status_order.get(t["status"], 99))

    page_size = min(int(args.get("page_size", 50)), 200)
    if page_size < 1:
        page_size = 1
    cursor = args.get("cursor")

    total_estimate = len(test_cases)

    if cursor:
        try:
            idx = next(i for i, t in enumerate(test_cases) if t.get("id") == cursor)
            test_cases = test_cases[idx + 1:]
        except StopIteration:
            test_cases = []

    page = test_cases[:page_size]
    has_more = len(test_cases) > page_size
    next_cursor = page[-1].get("id") if has_more and page else None

    passing = sum(1 for t in page if t["status"] == "PASSING")
    failing = sum(1 for t in page if t["status"] == "FAILING")

    return {
        "ok": True,
        "node_id": node_id,
        "node_name": node.get("name", ""),
        "node_type": node.get("type", ""),
        "test_cases": page,
        "count": len(page),
        "summary": {
            "passing": passing,
            "failing": failing,
            "draft": len(page) - passing - failing,
        },
        "coverage": "none" if not page else (
            "full" if failing == 0 and passing > 0 else
            "partial" if passing > 0 else
            "draft"
        ),
        "page_info": {
            "next_cursor": next_cursor,
            "has_more": has_more,
            "total_estimate": total_estimate,
            "page_size": page_size,
        },
    }


def node_related(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Get related nodes summary — neighbor names without full data.

    Returns lightweight list of connected nodes.
    Much cheaper than context() which loads full node data.

    Args:
        node_id: str (required)
        direction: str (optional) — 'outgoing', 'incoming', 'both' (default: 'both')
        edge_type: str (optional) — filter by edge type

    Returns:
        ok, node_id, node_name, outgoing, incoming, count
    """
    node_id = args.get("node_id", "")
    if not node_id:
        return {"ok": False, "error": "node_id required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    direction = args.get("direction", "both")
    mode = str(args.get("mode", "summary")).lower()
    if mode not in {"summary", "brief", "full"}:
        mode = "summary"
    edge_type_filter = args.get("edge_type")

    outgoing = []
    if direction in ("outgoing", "both"):
        for edge in index.get_edges_from(node_id):
            if edge_type_filter and edge.get("type") != edge_type_filter:
                continue
            neighbor = index.get_node(edge.get("to", ""))
            if mode == "summary" or neighbor is None:
                outgoing.append({
                    "edge_type": edge.get("type", ""),
                    "node_id": edge.get("to", ""),
                    "node_name": neighbor.get("name", "") if neighbor else "",
                    "node_type": neighbor.get("type", "") if neighbor else "",
                    "priority": neighbor.get("priority", "medium") if neighbor else "medium",
                })
            elif mode == "brief":
                brief_neighbor = _node_summary(neighbor, index)
                brief_neighbor["edge_type"] = edge.get("type", "")
                outgoing.append(brief_neighbor)
            else:
                full_neighbor = dict(neighbor)
                full_neighbor["edge_type"] = edge.get("type", "")
                outgoing.append(full_neighbor)

    incoming = []
    if direction in ("incoming", "both"):
        for edge in index.get_edges_to(node_id):
            if edge_type_filter and edge.get("type") != edge_type_filter:
                continue
            neighbor = index.get_node(edge.get("from", ""))
            if mode == "summary" or neighbor is None:
                incoming.append({
                    "edge_type": edge.get("type", ""),
                    "node_id": edge.get("from", ""),
                    "node_name": neighbor.get("name", "") if neighbor else "",
                    "node_type": neighbor.get("type", "") if neighbor else "",
                    "priority": neighbor.get("priority", "medium") if neighbor else "medium",
                })
            elif mode == "brief":
                brief_neighbor = _node_summary(neighbor, index)
                brief_neighbor["edge_type"] = edge.get("type", "")
                incoming.append(brief_neighbor)
            else:
                full_neighbor = dict(neighbor)
                full_neighbor["edge_type"] = edge.get("type", "")
                incoming.append(full_neighbor)

    page_size = min(int(args.get("page_size", 50)), 200)
    if page_size < 1:
        page_size = 1
    cursor = args.get("cursor")
    direction_filter = args.get("direction", "both")

    all_items: list[dict[str, Any]] = []
    if direction_filter in ("outgoing", "both"):
        all_items.extend([{**item, "_dir": "outgoing"} for item in outgoing])
    if direction_filter in ("incoming", "both"):
        all_items.extend([{**item, "_dir": "incoming"} for item in incoming])

    total_estimate = len(all_items)

    if cursor:
        try:
            idx = next(i for i, item in enumerate(all_items) if item.get("node_id") == cursor)
            all_items = all_items[idx + 1:]
        except StopIteration:
            all_items = []

    page = all_items[:page_size]
    has_more = len(all_items) > page_size
    next_cursor = page[-1].get("node_id") if has_more and page else None

    page_outgoing = [i for i in page if i.get("_dir") == "outgoing"]
    page_incoming = [i for i in page if i.get("_dir") == "incoming"]
    for i in page_outgoing + page_incoming:
        i.pop("_dir", None)

    return {
        "ok": True,
        "mode": mode,
        "node_id": node_id,
        "node_name": node.get("name", ""),
        "node_type": node.get("type", ""),
        "outgoing": page_outgoing,
        "incoming": page_incoming,
        "count": len(page),
        "page_info": {
            "next_cursor": next_cursor,
            "has_more": has_more,
            "total_estimate": total_estimate,
            "page_size": page_size,
        },
    }


def get_batch(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Fetch multiple nodes in one call.

    Args:
        ids: comma-separated node IDs or list
        mode: summary|brief|full (default: brief)
        max: max nodes to return (default: 20, max: 50)

    Returns:
        ok, nodes[], found, not_found[], mode
    """
    del project_root
    raw_ids = args.get("ids", args.get("query", ""))
    if isinstance(raw_ids, str):
        ids = [i.strip() for i in raw_ids.split(",") if i.strip()]
    else:
        ids = [str(i).strip() for i in list(raw_ids) if str(i).strip()]

    mode = str(args.get("mode", "brief")).lower()
    if mode not in {"summary", "brief", "full", "standard"}:
        mode = "brief"
    max_nodes = min(int(args.get("max", 20)), 50)
    ids = ids[:max_nodes]

    nodes: list[dict[str, Any]] = []
    not_found: list[str] = []

    for node_id in ids:
        node = index.get_node(node_id)
        if node:
            if mode == "summary":
                nodes.append(_node_summary(node, index))
            elif mode == "brief":
                nodes.append(_node_brief(node, index))
            else:
                nodes.append(dict(node))
        else:
            not_found.append(node_id)

    return {
        "ok": True,
        "nodes": nodes,
        "found": len(nodes),
        "not_found": not_found,
        "mode": mode,
    }


# Required and optional edges per NodeType (AI declaration guide)
_NODE_EDGE_REQUIREMENTS: dict[str, dict[str, list[dict[str, str]]]] = {
    "Flow": {
        "required_edges": [
            {
                "type": "implements",
                "target": "Protocol or Node",
                "description": "Protocol này Flow thực hiện",
            },
            {
                "type": "references",
                "target": "Document",
                "description": "DOC source của Flow",
            },
        ],
        "optional_edges": [
            {
                "type": "depends_on",
                "target": "Entity or Node",
                "description": "Dependencies",
            },
            {
                "type": "tested_by",
                "target": "TestCase",
                "description": "Test coverage",
            },
        ],
    },
    "Engine": {
        "required_edges": [
            {
                "type": "implements",
                "target": "Flow or Node",
                "description": "Flow Engine này phục vụ",
            },
        ],
        "optional_edges": [
            {
                "type": "depends_on",
                "target": "Entity",
                "description": "Entity Engine cần",
            },
            {
                "type": "references",
                "target": "Document",
                "description": "Spec document",
            },
        ],
    },
    "Entity": {
        "required_edges": [
            {
                "type": "references",
                "target": "Document",
                "description": "DOC định nghĩa Entity",
            },
        ],
        "optional_edges": [
            {
                "type": "relates_to",
                "target": "Entity",
                "description": "Entities liên quan",
            },
        ],
    },
    "Feature": {
        "required_edges": [
            {
                "type": "implements",
                "target": "Flow or Node",
                "description": "Flow Feature này thuộc về",
            },
        ],
        "optional_edges": [
            {
                "type": "references",
                "target": "Document",
                "description": "Spec source",
            },
            {
                "type": "depends_on",
                "target": "Entity or Feature",
                "description": "Dependencies",
            },
            {
                "type": "tested_by",
                "target": "TestCase",
                "description": "Test coverage",
            },
        ],
    },
    "Decision": {
        "required_edges": [],
        "optional_edges": [
            {
                "type": "references",
                "target": "Document",
                "description": "Source document",
            },
            {
                "type": "supersedes",
                "target": "Decision",
                "description": "Decision cũ bị thay thế",
            },
        ],
    },
    "Document": {
        "required_edges": [],
        "optional_edges": [
            {
                "type": "references",
                "target": "Document",
                "description": "Docs liên quan",
            },
        ],
    },
    "TestCase": {
        "required_edges": [
            {
                "type": "covers",
                "target": "Node or Flow or Feature",
                "description": "Node này test covers",
            },
            {
                "type": "of_kind",
                "target": "TestKind",
                "description": "Loại test",
            },
        ],
        "optional_edges": [],
    },
}


def node_template(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Return declaration template for a NodeType.

    Shows required + optional edges AI should declare when creating this type.

    Args:
        query: NodeType name (e.g. "Flow", "Engine", "Entity")

    Returns:
        ok, node_type, required_edges[], optional_edges[], example_queries[]
    """
    del index, project_root  # Signature parity with other read tools.
    node_type = str(args.get("query", args.get("node_type", ""))).strip()
    if not node_type:
        return {
            "ok": True,
            "templates": {k: dict(v) for k, v in _NODE_EDGE_REQUIREMENTS.items()},
            "hint": "gobp(query='template: Flow') to see Flow-specific template",
        }

    reqs = _NODE_EDGE_REQUIREMENTS.get(node_type, {})
    required = list(reqs.get("required_edges", []))
    optional = list(reqs.get("optional_edges", []))

    examples = [
        f"gobp(query=\"create:{node_type} name='My {node_type}' priority='high' session_id='x'\")",
    ]
    for edge in required:
        et = edge["type"]
        examples.append(
            f"gobp(query=\"edge: {node_type.lower()}:my_id --{et}--> target:id\")"
            f"  # {edge['description']}"
        )

    return {
        "ok": True,
        "node_type": node_type,
        "required_edges": required,
        "optional_edges": optional,
        "required_count": len(required),
        "optional_count": len(optional),
        "example_queries": examples,
        "hint": (
            f"After creating {node_type} node, declare {len(required)} required edge(s). "
            "Use interview: to be guided through all relationships."
        )
        if required
        else f"No required edges for {node_type}.",
    }


def node_interview(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Generate interview questions for declaring a node's relationships.

    AI uses this after creating a node to discover all relationships.
    Returns structured questions — AI answers each, then creates edges.

    Args:
        node_id: str — node to interview about
        answered: list[str] (optional) — edge types already declared

    Returns:
        ok, node_id, node_name, questions[], next_question, completion_pct
    """
    del project_root
    node_id = str(args.get("node_id") or args.get("query", "")).strip()
    if not node_id:
        return {"ok": False, "error": "node_id required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    node_type = str(node.get("type", "Node"))
    reqs = _NODE_EDGE_REQUIREMENTS.get(node_type, {})
    required_edges = list(reqs.get("required_edges", []))
    optional_edges = list(reqs.get("optional_edges", []))

    existing_edge_types = {e.get("type") for e in index.get_edges_from(node_id) if e.get("type")}
    answered_raw = args.get("answered", [])
    if isinstance(answered_raw, str):
        answered_list = [a.strip() for a in answered_raw.split(",") if a.strip()]
    else:
        answered_list = [str(a).strip() for a in answered_raw if str(a).strip()]
    answered: set[str] = set(answered_list) | existing_edge_types

    questions: list[dict[str, Any]] = []

    for edge in required_edges:
        if edge["type"] not in answered:
            et = edge["type"]
            questions.append({
                "edge_type": et,
                "required": True,
                "question": (
                    f"[REQUIRED] {node.get('name', node_id)} {et} which {edge['target']}?"
                ),
                "description": edge["description"],
                "example": f"gobp(query=\"edge: {node_id} --{et}--> target:id\")",
            })

    for edge in optional_edges:
        if edge["type"] not in answered:
            et = edge["type"]
            questions.append({
                "edge_type": et,
                "required": False,
                "question": (
                    f"[OPTIONAL] Does {node.get('name', node_id)} {et} any {edge['target']}?"
                ),
                "description": edge["description"],
                "example": f"gobp(query=\"edge: {node_id} --{et}--> target:id\")",
            })

    if not questions or all(q["required"] is False for q in questions):
        questions.append({
            "edge_type": "_catch_all",
            "required": False,
            "question": f"Are there any other nodes that relate to {node.get('name', node_id)}?",
            "description": "Catch-all: any relationship not covered above",
            "example": f"gobp(query=\"edge: {node_id} --relates_to--> other:id\")",
        })

    total = len(required_edges) + len(optional_edges) + 1
    answered_count = len(answered)
    completion_pct = min(100, round(answered_count / total * 100)) if total else 100

    next_q = questions[0] if questions else None

    return {
        "ok": True,
        "node_id": node_id,
        "node_name": node.get("name", ""),
        "node_type": node_type,
        "questions": questions,
        "next_question": next_q,
        "answered_edge_types": sorted(answered),
        "completion_pct": completion_pct,
        "done": len(questions) == 0 or (
            len(questions) == 1 and questions[0]["edge_type"] == "_catch_all"
        ),
        "hint": (
            "Answer each question by creating edges, then call interview: again to continue."
            if questions
            else f"All relationships declared for {node.get('name', node_id)}."
        ),
    }


def schema_governance(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Cross-check schema vs documentation vs tests for drift.

    Checks:
      1. Every node type in schema has entry in SCHEMA.md
      2. Every node type has id_prefix in schema
      3. Priority field present on important types
      4. Node types referenced in tests exist in schema (when scope allows)

    Args:
        scope: 'all' | 'schema-docs' | 'schema-tests' | 'schema' (default: 'all')

    Returns:
        ok, issues[], score (0-100), summary
    """
    del index  # Unused; signature kept for consistency with other read tools.
    scope = args.get("scope", args.get("query", "all"))
    issues: list[dict[str, Any]] = []

    schema_path = project_root / "gobp" / "schema" / "core_nodes.yaml"

    try:
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
        node_types_in_schema = set(schema.get("node_types", {}).keys())
    except Exception as e:
        return {"ok": False, "error": f"Cannot load schema: {e}"}

    schema_doc_path = project_root / "docs" / "SCHEMA.md"
    if schema_doc_path.exists():
        schema_doc = schema_doc_path.read_text(encoding="utf-8")
        for node_type in node_types_in_schema:
            if node_type not in schema_doc:
                issues.append({
                    "type": "schema_doc_drift",
                    "severity": "warning",
                    "message": f"Node type '{node_type}' in schema but not documented in SCHEMA.md",
                    "node_type": node_type,
                })
    else:
        issues.append({
            "type": "missing_doc",
            "severity": "error",
            "message": "docs/SCHEMA.md not found",
        })

    for type_name, type_def in schema.get("node_types", {}).items():
        if not type_def.get("id_prefix"):
            issues.append({
                "type": "missing_id_prefix",
                "severity": "error",
                "message": f"Node type '{type_name}' has no id_prefix in schema",
                "node_type": type_name,
            })

    important_types = {"Node", "Idea", "Decision", "Document", "Feature", "Flow", "Engine", "Entity"}
    for type_name in important_types:
        if type_name in node_types_in_schema:
            type_def = schema["node_types"][type_name]
            optional = type_def.get("optional", {})
            if "priority" not in optional:
                issues.append({
                    "type": "missing_priority_field",
                    "severity": "warning",
                    "message": f"Node type '{type_name}' missing optional priority field",
                    "node_type": type_name,
                })

    scan_tests = scope in ("all", "schema-tests", "schema")
    tests_dir = project_root / "tests"
    if tests_dir.exists() and scan_tests:
        for test_file in tests_dir.glob("test_*.py"):
            content = test_file.read_text(encoding="utf-8", errors="replace")
            type_refs = re.findall(r'"type":\s*"([A-Z][a-zA-Z]+)"', content)
            type_refs += re.findall(r"type='([A-Z][a-zA-Z]+)'", content)
            for ref in set(type_refs):
                if ref not in node_types_in_schema and ref not in {
                    "GET", "POST", "PUT", "DELETE", "str", "int", "bool",
                }:
                    issues.append({
                        "type": "test_references_unknown_type",
                        "severity": "info",
                        "message": f"Test file '{test_file.name}' references type '{ref}' not in schema",
                        "file": test_file.name,
                        "node_type": ref,
                    })

    error_count = sum(1 for i in issues if i["severity"] == "error")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")
    score = max(0, 100 - (error_count * 20) - (warning_count * 5))

    return {
        "ok": True,
        "scope": scope,
        "issues": issues,
        "issue_count": len(issues),
        "error_count": error_count,
        "warning_count": warning_count,
        "score": score,
        "summary": (
            f"Schema governance: {score}/100. "
            f"{error_count} errors, {warning_count} warnings, "
            f"{len(issues) - error_count - warning_count} info."
        ),
        "node_types_checked": len(node_types_in_schema),
    }
