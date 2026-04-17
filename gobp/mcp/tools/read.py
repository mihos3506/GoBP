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
from gobp.core.id_config import get_group_for_type, load_groups, parse_external_id
from gobp.core.search import normalize_text, search_nodes, search_score, suggest_related
from gobp.mcp.tools.read_governance import metadata_lint, schema_governance
from gobp.mcp.tools.read_priority import recompute_priorities
from gobp.mcp.tools.read_interview import node_interview, node_template


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
    import sys

    node_id = node.get("id", "")
    parsed = parse_external_id(node_id)
    edge_count = 0
    if index and node_id:
        edge_count = len(index.get_edges_from(node_id)) + len(index.get_edges_to(node_id))
    estimated_size = sys.getsizeof(str(node)) // 10
    return {
        "id": node_id,
        "type": node.get("type", ""),
        "name": node.get("name", ""),
        "group": parsed.get("group", ""),
        "testkind": parsed.get("testkind", ""),
        "status": node.get("status", ""),
        "priority": node.get("priority", "medium"),
        "priority_score": node.get("priority_score"),
        "edge_count": edge_count,
        "detail_available": True,
        "estimated_tokens": max(50, estimated_size),
        "hint": f"gobp(query=\"get: {node_id} mode=brief\") for more detail",
    }


def _extract_fts_slug(node_id: str) -> str:
    """Extract slug from external ID for search indexing."""
    parsed = parse_external_id(node_id)
    return parsed.get("slug", "")


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
        (PROTOCOL_GUIDE â€” large). Default is false: only ``interface_summary``
        plus a hint to load the full catalog when needed.
    """
    from gobp.mcp.parser import PROTOCOL_GUIDE

    full_interface = _truthy(args.get("full_interface")) or _truthy(
        args.get("include_interface")
    )

    all_nodes = index.all_nodes()
    all_edges = index.all_edges()

    # Project metadata: .gobp/config.yaml overrides charter / first Document
    cfg: dict[str, Any] = {}
    cfg_path = project_root / ".gobp" / "config.yaml"
    if cfg_path.exists():
        try:
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except Exception:
            cfg = {}

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

    resolved_name = cfg["project_name"] if "project_name" in cfg else project_name
    resolved_description = (
        cfg["project_description"] if "project_description" in cfg else project_description
    )
    project_id = str(cfg.get("project_id", "") or "")

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

    # Concepts â€” for AI orientation
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
            "name": resolved_name,
            "id": project_id,
            "description": resolved_description,
            "root": str(project_root),
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


def _legacy_substring_hit(query_lower: str, node: dict[str, Any]) -> bool:
    """True if legacy wide substring search would match (topic, title, etc.)."""
    node_id = node.get("id", "")
    node_name = node.get("name", "")
    legacy_id = node.get("legacy_id", "")
    fts_slug = _extract_fts_slug(node_id)
    searchable = f"{node_id} {node_name} {legacy_id} {fts_slug}".lower()
    for field in ("topic", "subject", "title", "description", "definition", "group"):
        val = node.get(field, "")
        if val:
            searchable += f" {str(val).lower()}"
    return query_lower in searchable


def _find_match_label(node: dict[str, Any], query_str: str, query_norm: str, score: int) -> str:
    """Map search hit to legacy match labels (exact_id / exact_name / substring)."""
    node_id = node.get("id", "")
    if node_id == query_str:
        return "exact_id"
    if node.get("name", "").lower() == query_str.lower():
        return "exact_name"
    if score == 100 or normalize_text(node.get("name", "")) == query_norm:
        return "exact_name"
    return "substring"


def find(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Search nodes by keyword with cursor-based pagination.

    Args:
        query: Search keyword (optional; empty means all nodes)
        type / type_filter: Node type filter (optional, exact field match)
        include_sessions: If true, include Session nodes (default false)
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
    type_filter = args.get("type_filter") or args.get("type")
    page_size = min(int(args.get("page_size", args.get("limit", 20))), 100)
    cursor = args.get("cursor")
    sort_field = args.get("sort", "id")
    direction = str(args.get("direction", "asc")).lower()
    include_sessions_param = str(args.get("include_sessions", "false")).lower() == "true"

    if page_size < 1:
        page_size = 1

    explicit_session_filter = type_filter == "Session"
    include_sessions = explicit_session_filter or include_sessions_param
    exclude_types: list[str] = [] if include_sessions else ["Session"]

    candidates: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    if not query_str.strip():
        # Empty query: list all matching nodes (legacy), with optional session exclusion.
        for node in index.all_nodes():
            if type_filter and node.get("type") != type_filter:
                continue
            if node.get("type", "") in exclude_types:
                continue

            node_id = node.get("id", "")
            if node_id in seen_ids:
                continue

            seen_ids.add(node_id)
            enriched = dict(node)
            enriched["match"] = "substring"
            enriched["_score"] = 0
            candidates.append(enriched)

        reverse = direction == "desc"
        candidates.sort(
            key=lambda n: (
                _FIND_PRIORITY.get(str(n.get("match", "")), 99),
                str(n.get(sort_field, n.get("id", ""))),
            ),
            reverse=reverse,
        )
    else:
        # Vietnamese-aware relevance + legacy wide fields (topic, title, …).
        query_norm = normalize_text(query_str.strip())
        query_lower = query_str.lower()

        scored_map: dict[str, tuple[int, dict[str, Any]]] = {}
        for node in index.all_nodes():
            if type_filter and node.get("type") != type_filter:
                continue
            if node.get("type", "") in exclude_types:
                continue
            node_id = node.get("id", "")
            if not node_id:
                continue
            base = search_score(query_norm, node)
            if base == 0 and _legacy_substring_hit(query_lower, node):
                base = 20
            if base == 0:
                continue
            prev = scored_map.get(node_id)
            if prev is None or base > prev[0]:
                scored_map[node_id] = (base, node)

        scored = sorted(scored_map.values(), key=lambda x: -x[0])

        for score, node in scored:
            node_id = node.get("id", "")
            if node_id in seen_ids:
                continue
            seen_ids.add(node_id)
            enriched = dict(node)
            enriched["match"] = _find_match_label(enriched, query_str, query_norm, score)
            enriched["_score"] = score
            candidates.append(enriched)

        # Stable sort: tie-break by sort_field/direction, then exact_id / exact_name / substring + score.
        candidates.sort(
            key=lambda n: str(n.get(sort_field, n.get("id", ""))),
            reverse=(direction == "desc"),
        )
        candidates.sort(
            key=lambda n: (
                _FIND_PRIORITY.get(str(n.get("match", "")), 99),
                -int(n.get("_score", 0)),
            ),
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
        matches = []
        for n in page:
            entry = _node_summary(n, index)
            entry["_score"] = n.get("_score", 0)
            matches.append(entry)
    elif mode == "brief":
        matches = []
        for n in page:
            entry = _node_brief(n, index)
            entry["_score"] = n.get("_score", 0)
            matches.append(entry)
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
                "_score": n.get("_score", 0),
            }
            for n in page
        ]

    return {
        "ok": True,
        "matches": matches,
        "count": len(matches),
        "mode": mode,
        "truncated": has_more,
        "query": query_str,
        "type_filter": type_filter,
        "sessions_excluded": bool(exclude_types),
        "hint": (
            "Use include_sessions=true to include Session nodes. "
            "Use type_filter for exact type match."
        ),
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
    Only returns code_refs field â€” much cheaper than full context().

    Args:
        node_id: str (required)
        add: dict (optional) â€” add a new code ref
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

    Returns list of invariant strings â€” constraints that must always be true.
    Only returns invariants field â€” much cheaper than full context().

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
    No schema change needed â€” uses existing covers edges.

    Args:
        node_id: str (required)
        status: str (optional) â€” filter by status: PASSING, FAILING, DRAFT, etc.

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
    """Get related nodes summary â€” neighbor names without full data.

    Returns lightweight list of connected nodes.
    Much cheaper than context() which loads full node data.

    Args:
        node_id: str (required)
        direction: str (optional) â€” 'outgoing', 'incoming', 'both' (default: 'both')
        edge_type: str (optional) â€” filter by edge type

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


_TEMPLATE_SKIP_FIELDS = frozenset(
    {"id", "type", "created", "updated"},
)


def _schema_field_entry(spec: Any) -> dict[str, Any]:
    """Normalize a core_nodes.yaml field spec to a JSON-serializable frame entry."""
    if isinstance(spec, dict):
        entry: dict[str, Any] = {}
        raw_type = spec.get("type", "string")
        entry["type"] = str(raw_type) if raw_type is not None else "string"
        if "enum_values" in spec and spec["enum_values"] is not None:
            entry["values"] = list(spec["enum_values"])
        desc = spec.get("description")
        if desc:
            entry["description"] = str(desc)
        if "default" in spec:
            entry["default"] = spec["default"]
        return entry
    if isinstance(spec, str):
        return {"type": spec}
    return {"type": "string"}


def template_action(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Return schema-driven input frame for a node type (template: Engine).

    Skips auto-managed identity/timestamp fields so the frame focuses on
    values callers typically supply before ``create:``.
    """
    node_type = str(
        args.get("query", args.get("type", args.get("node_type", "")))
    ).strip()
    schema = getattr(index, "_nodes_schema", None) or {}
    node_types = schema.get("node_types", {}) if isinstance(schema, dict) else {}

    if not node_type:
        names = sorted(str(k) for k in node_types.keys())
        return {
            "ok": True,
            "catalog": True,
            "node_types": names,
            "hint": "Use template: <NodeType> for required/optional fields from schema.",
        }

    type_def = node_types.get(node_type)
    if not type_def:
        return {
            "ok": False,
            "error": f"Unknown type: {node_type}",
            "available": sorted(str(k) for k in node_types.keys()),
        }

    required: dict[str, Any] = {}
    for field, spec in (type_def.get("required") or {}).items():
        if field in _TEMPLATE_SKIP_FIELDS:
            continue
        required[field] = _schema_field_entry(spec)

    optional: dict[str, Any] = {}
    for field, spec in (type_def.get("optional") or {}).items():
        if field in _TEMPLATE_SKIP_FIELDS:
            continue
        optional[field] = _schema_field_entry(spec)

    groups = load_groups(project_root)
    group = get_group_for_type(node_type, groups)

    batch_format = f"create: {node_type}: {{name}} | {{description}}"
    batch_example = f"create: {node_type}: ExampleName | Short description of what this does"

    return {
        "ok": True,
        "type": node_type,
        "group": group,
        "frame": {"required": required, "optional": optional},
        "batch_format": batch_format,
        "batch_example": batch_example,
        "hint": (
            "Use batch session_id='…' ops='…' for many creates/updates in one call. "
            "Use explore: before creating to avoid duplicates."
        ),
    }


def explore_action(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Return best-matching node plus edges and close matches (explore: keyword)."""
    del project_root
    query = str(args.get("query", "")).strip()
    if not query:
        return {"ok": False, "error": "Query required"}

    results = search_nodes(index, query, exclude_types=["Session"], limit=10)
    if not results:
        return {
            "ok": False,
            "error": f"No nodes found for: {query}",
            "hint": "Try different keywords or use find: for broader search",
        }

    best_score, best_node = results[0]
    node_id = str(best_node.get("id", ""))

    edges_out: list[dict[str, Any]] = []
    edges_in: list[dict[str, Any]] = []

    for edge in index.all_edges():
        edge_type = str(edge.get("type", "relates_to"))
        if edge_type == "discovered_in":
            continue
        if edge.get("from") == node_id:
            target = index.get_node(str(edge.get("to", "")))
            if target:
                edges_out.append(
                    {
                        "dir": "out",
                        "type": edge_type,
                        "node": {
                            "id": target.get("id"),
                            "name": target.get("name", ""),
                            "type": target.get("type", ""),
                        },
                    }
                )
        elif edge.get("to") == node_id:
            source = index.get_node(str(edge.get("from", "")))
            if source:
                edges_in.append(
                    {
                        "dir": "in",
                        "type": edge_type,
                        "node": {
                            "id": source.get("id"),
                            "name": source.get("name", ""),
                            "type": source.get("type", ""),
                        },
                    }
                )

    all_edges = edges_out + edges_in
    also_found: list[dict[str, Any]] = []
    for score, node in results[1:6]:
        nid = str(node.get("id", ""))
        ec = len(index.get_edges_from(nid)) + len(index.get_edges_to(nid))
        note = "potential duplicate" if score >= 80 else "related"
        also_found.append(
            {
                "id": node.get("id"),
                "type": node.get("type", ""),
                "name": node.get("name", ""),
                "edge_count": ec,
                "note": note,
            }
        )

    return {
        "ok": True,
        "node": {
            "id": node_id,
            "type": best_node.get("type", ""),
            "name": best_node.get("name", ""),
            "description": best_node.get("description", ""),
            "priority": best_node.get("priority", ""),
            "match_score": best_score,
        },
        "edges": all_edges,
        "edge_count": len(all_edges),
        "also_found": also_found,
        "hint": (
            "Use retype: or delete: to clean duplicates. Use edge: or batch ops to add relationships."
        ),
    }


def suggest_action(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Suggest reusable nodes from a short natural-language context."""
    del project_root
    context = str(args.get("query", "")).strip()
    if not context:
        return {
            "ok": False,
            "error": "Context required. Example: suggest: Payment Flow",
        }

    lim = int(args.get("limit", 10))
    suggestions = suggest_related(index, context, limit=lim)

    return {
        "ok": True,
        "context": context,
        "suggestions": suggestions,
        "count": len(suggestions),
        "hint": "Consider linking to these nodes with edge: or batch ops instead of creating new ones.",
    }


