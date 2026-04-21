"""GoBP MCP read tools.

Implementations in Tasks 2-8 of Wave 3.
"""

from __future__ import annotations

import re
from collections import defaultdict
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

    # Wave D — enrich from PostgreSQL schema v3 when available.
    # Primary stats stay file-first (GraphIndex); mirror may lag behind → confusing UX if we
    # replaced totals with PG counts (see mirror_sync).
    file_node_count = len(all_nodes)
    file_edge_count = len(all_edges)
    from gobp.mcp.tools import read_v3 as _read_v3

    conn_ov, is_v3_ov = _read_v3._conn_v3(project_root)
    if conn_ov is not None and is_v3_ov:
        try:
            v3 = _read_v3.overview_v3(conn_ov, project_root, full_interface)
            base["project"]["schema_version"] = v3["project"].get("schema_version", "v3")
            if v3["project"].get("name"):
                base["project"]["name"] = v3["project"]["name"]
            if v3["project"].get("id") is not None:
                base["project"]["id"] = v3["project"]["id"]
            base["stats"]["total_nodes"] = file_node_count
            base["stats"]["total_edges"] = file_edge_count
            base["stats"]["postgresql_mirror"] = {
                "total_nodes": v3["stats"]["total_nodes"],
                "total_edges": v3["stats"]["total_edges"],
                "nodes_by_group": v3["stats"].get("nodes_by_group", {}),
            }
            pg_n = int(v3["stats"]["total_nodes"])
            pg_e = int(v3["stats"]["total_edges"])
            if pg_n != file_node_count or pg_e != file_edge_count:
                base["mirror_sync"] = {
                    "aligned": False,
                    "hint": (
                        "Totals above are from the file-backed graph (source of truth). "
                        "PostgreSQL mirror counts differ — search/find may use FTS on the mirror "
                        "until sync completes; use refresh: after disk writes, or run your "
                        "file→PG sync script. find: falls back to the file index when FTS returns "
                        "no rows but nodes exist on disk."
                    ),
                }
            else:
                base["mirror_sync"] = {"aligned": True}
            base["active_sessions"] = v3["active_sessions"]
            base["hint_v3"] = v3.get("hint", "")
        finally:
            conn_ov.close()
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


_READ_ORDER_RANK: dict[str, int] = {
    "foundational": 0,
    "important": 1,
    "reference": 2,
    "background": 3,
}

_RAW_META_FIELDS: frozenset[str] = frozenset(
    {"_dispatch", "_protocol", "revision", "content_hash"}
)


def _parse_find_inline_params(query_str: str) -> dict[str, Any]:
    """Extract group / type tokens from find: query string (Wave 17A03)."""
    out: dict[str, Any] = {"keyword": query_str}
    if not query_str.strip():
        out["keyword"] = ""
        return out
    s = query_str
    m = re.search(r'group\s*=\s*["\']([^"\']+)["\']', s, re.I)
    if m:
        out["group"] = m.group(1).strip()
        s = re.sub(r'group\s*=\s*["\'][^"\']+["\']', " ", s, flags=re.I)
    m2 = re.search(r"group\s+contains\s+[\"']([^\"']+)[\"']", s, re.I)
    if m2:
        out["group_contains"] = m2.group(1).strip()
        s = re.sub(r"group\s+contains\s+[\"'][^\"']+[\"']", " ", s, flags=re.I)
    tm = re.search(r"(?<![\w])type=(\w+)", s)
    if tm:
        out["type_inline"] = tm.group(1)
        s = re.sub(r"(?<![\w])type=\w+", " ", s)
    out["keyword"] = " ".join(s.split()).strip()
    return out


def _get_info_from_node(node: dict[str, Any]) -> str:
    """Return description.info or plain string description."""
    desc = node.get("description", "")
    if isinstance(desc, dict):
        return str(desc.get("info", "") or "")
    if isinstance(desc, str):
        return desc
    return ""


def _description_preview(node: dict[str, Any], max_chars: int = 200) -> str:
    return _truncate(_get_info_from_node(node), max_chars)


def _build_breadcrumb(group: str) -> list[dict[str, str]]:
    """Navigable segments from schema v2 ``group`` path."""
    if not group or not str(group).strip():
        return []
    parts = [p.strip() for p in str(group).split(">") if p.strip()]
    crumbs: list[dict[str, str]] = []
    for i in range(len(parts)):
        path = " > ".join(parts[: i + 1])
        crumbs.append({"label": parts[i], "path": path})
    return crumbs


def _get_relationships(index: GraphIndex, node_id: str) -> list[dict[str, Any]]:
    """Edges with ``reason`` and peer group/name (Wave 17A03)."""
    out: list[dict[str, Any]] = []
    for edge in index.get_edges_from(node_id):
        target_id = str(edge.get("to", "") or "")
        target = index.get_node(target_id)
        out.append(
            {
                "target_id": target_id,
                "target_name": target.get("name", "") if target else "",
                "target_group": str(target.get("group", "") or "") if target else "",
                "type": str(edge.get("type", "") or ""),
                "reason": str(edge.get("reason", "") or ""),
                "direction": "outgoing",
            }
        )
    for edge in index.get_edges_to(node_id):
        source_id = str(edge.get("from", "") or "")
        source = index.get_node(source_id)
        out.append(
            {
                "source_id": source_id,
                "source_name": source.get("name", "") if source else "",
                "source_group": str(source.get("group", "") or "") if source else "",
                "type": str(edge.get("type", "") or ""),
                "reason": str(edge.get("reason", "") or ""),
                "direction": "incoming",
            }
        )
    return out


def _get_type_important_fields(node: dict[str, Any]) -> dict[str, Any]:
    """Type-specific fields for get/context brief mode."""
    node_type = str(node.get("type", "") or "")
    result: dict[str, Any] = {}
    if node_type == "Invariant":
        for f in ("rule", "scope", "enforcement", "violation_action"):
            if node.get(f) is not None:
                result[f] = node[f]
    elif node_type == "ErrorCase":
        for f in ("code", "severity", "trigger"):
            if node.get(f) is not None:
                result[f] = node[f]
    elif node_type == "Decision":
        for f in ("what", "why"):
            if node.get(f):
                result[f] = _truncate(str(node[f]), 200)
    elif node_type == "Concept":
        if node.get("definition"):
            result["definition"] = _truncate(str(node["definition"]), 300)
    return result


def _node_for_context_brief(node: dict[str, Any]) -> dict[str, Any]:
    """Slim node payload for get/context mode=brief (Wave 17A03)."""
    desc_info = _get_info_from_node(node)
    out: dict[str, Any] = {
        "id": node.get("id"),
        "name": node.get("name"),
        "type": node.get("type"),
        "group": str(node.get("group", "") or ""),
        "lifecycle": str(node.get("lifecycle", "draft") or "draft"),
        "read_order": str(node.get("read_order", "reference") or "reference"),
        "description": {"info": desc_info, "code": ""},
    }
    out.update(_get_type_important_fields(node))
    return out


def _normalize_description_for_full(node: dict[str, Any]) -> dict[str, str]:
    """description as {info, code} for full mode."""
    raw = node.get("description")
    if isinstance(raw, dict):
        return {
            "info": str(raw.get("info", "") or ""),
            "code": str(raw.get("code", "") or ""),
        }
    if isinstance(raw, str):
        return {"info": raw, "code": ""}
    return {"info": "", "code": ""}


def _match_score_float(query: str, node: dict[str, Any]) -> float:
    """0.0–1.0 similarity from search_score."""
    qn = normalize_text(query.strip())
    if not qn:
        return 0.0
    return min(1.0, float(search_score(qn, node)) / 100.0)


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
    query_str = str(args.get("query", "") or "")
    if "query" not in args:
        return {"ok": False, "error": "Missing required field: query"}
    inline = _parse_find_inline_params(query_str)
    query_str = str(inline.get("keyword") or "")
    if args.get("group") is None and inline.get("group"):
        args = {**args, "group": inline["group"]}
    if args.get("group_contains") is None and inline.get("group_contains"):
        args = {**args, "group_contains": inline["group_contains"]}
    type_filter = args.get("type_filter") or args.get("type") or inline.get("type_inline")
    page_size = min(int(args.get("page_size", args.get("limit", 20))), 100)
    cursor_raw = args.get("cursor")
    if cursor_raw is not None and str(cursor_raw).strip() != "":
        cursor: str | None = str(cursor_raw).strip()
    else:
        cursor = None

    from gobp.mcp.tools import read_v3 as _read_v3

    file_fallback_after_pg = False
    conn_f, is_v3_f = _read_v3._conn_v3(project_root)
    if conn_f is not None and is_v3_f:
        try:
            if not query_str.strip():
                return {"ok": False, "error": "find: requires a keyword"}
            gf_raw = args.get("group")
            gf_s = str(gf_raw).strip() if gf_raw is not None else None
            if gf_s == "":
                gf_s = None
            mode_v3 = str(args.get("mode", "summary")).lower()
            if mode_v3 in ("standard", ""):
                mode_v3 = "summary"
            out_pg = _read_v3.find_v3(conn_f, query_str, gf_s, mode_v3, page_size, cursor)
            if (
                out_pg.get("ok")
                and int(out_pg.get("count", 0)) == 0
                and len(index.all_nodes()) > 0
            ):
                file_fallback_after_pg = True
            else:
                out_pg["sessions_excluded"] = True
                out_pg["type_filter"] = type_filter
                return out_pg
        finally:
            conn_f.close()

    sort_field = args.get("sort", "id")
    direction = str(args.get("direction", "asc")).lower()
    include_sessions_param = str(args.get("include_sessions", "false")).lower() == "true"

    if page_size < 1:
        page_size = 1

    explicit_session_filter = type_filter == "Session"
    include_sessions = explicit_session_filter or include_sessions_param
    exclude_types: list[str] = [] if include_sessions else ["Session"]

    group_ids: set[str] | None = None
    group_meta: str | None = None
    if args.get("group"):
        exact = _truthy(args.get("group_exact"))
        group_ids = set(index.find_by_group(str(args["group"]).strip(), exact=exact))
        group_meta = str(args["group"]).strip()
    elif args.get("group_contains"):
        needle = str(args["group_contains"]).lower()
        group_ids = set()
        for node in index.all_nodes():
            nid = node.get("id")
            if nid and needle in str(node.get("group", "")).lower():
                group_ids.add(str(nid))
        group_meta = f'contains "{args["group_contains"]}"'

    candidates: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def _passes_base_filters(node: dict[str, Any]) -> bool:
        nid = str(node.get("id", "") or "")
        if group_ids is not None and nid not in group_ids:
            return False
        if type_filter and node.get("type") != type_filter:
            return False
        if node.get("type", "") in exclude_types:
            return False
        return True

    if not query_str.strip():
        # Empty keyword: list all (legacy) or group-filtered nodes.
        for node in index.all_nodes():
            if not _passes_base_filters(node):
                continue
            node_id = node.get("id", "")
            if node_id in seen_ids:
                continue
            seen_ids.add(node_id)
            enriched = dict(node)
            enriched["match"] = "substring"
            enriched["_score"] = 0
            candidates.append(enriched)

        candidates.sort(
            key=lambda n: (
                _READ_ORDER_RANK.get(str(n.get("read_order", "reference")), 2),
                str(n.get("name", "")),
                str(n.get("id", "")),
            ),
        )
        reverse = direction == "desc"
        candidates.sort(
            key=lambda n: (
                _FIND_PRIORITY.get(str(n.get("match", "")), 99),
                str(n.get(sort_field, n.get("id", ""))),
                str(n.get("id", "")),
            ),
            reverse=reverse,
        )
    else:
        # Vietnamese-aware relevance + legacy wide fields (topic, title, …).
        query_norm = normalize_text(query_str.strip())
        query_lower = query_str.lower()

        scored_map: dict[str, tuple[int, dict[str, Any]]] = {}
        inv = getattr(index, "_inverted", None)
        cand_ids: set[str] | None = None
        if inv is not None:
            cand_ids = set(inv.search(query_str, max(page_size * 100, 200)))
            if not cand_ids:
                cand_ids = None
        if cand_ids is not None:
            nodes_iter = [index.get_node(nid) for nid in cand_ids]
            nodes_to_score = [n for n in nodes_iter if n]
            if not nodes_to_score:
                nodes_to_score = list(index.all_nodes())
        else:
            nodes_to_score = list(index.all_nodes())

        for node in nodes_to_score:
            if not _passes_base_filters(node):
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

        if cand_ids is not None:
            for node in index.all_nodes():
                node_id = str(node.get("id", "") or "")
                if not node_id or node_id in scored_map:
                    continue
                if not _passes_base_filters(node):
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

        candidates.sort(
            key=lambda n: (
                str(n.get(sort_field, n.get("id", ""))),
                str(n.get("id", "")),
            ),
            reverse=(direction == "desc"),
        )
        candidates.sort(
            key=lambda n: (
                _FIND_PRIORITY.get(str(n.get("match", "")), 99),
                -int(n.get("_score", 0)),
            ),
        )
        if group_ids is not None:
            candidates.sort(
                key=lambda n: (
                    _READ_ORDER_RANK.get(str(n.get("read_order", "reference")), 2),
                    str(n.get("name", "")),
                ),
            )

    # Apply cursor (keyset pagination)
    total_estimate = len(candidates)
    if cursor:
        try:
            cursor_idx = next(
                i for i, n in enumerate(candidates) if str(n.get("id", "")) == cursor
            )
            candidates = candidates[cursor_idx + 1:]
        except StopIteration:
            candidates = []

    remaining_after_cursor = len(candidates)
    # Page
    page = candidates[:page_size]
    has_more = len(candidates) > page_size
    next_raw = page[-1].get("id") if has_more and page else None
    next_cursor = str(next_raw) if next_raw is not None else None

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
        # Backward compatible default payload + v2 group fields.
        matches = [
            {
                "id": n.get("id"),
                "type": n.get("type"),
                "name": n.get("name", ""),
                "group": n.get("group", ""),
                "read_order": n.get("read_order", "reference"),
                "status": n.get("status", ""),
                "priority": n.get("priority", "medium"),
                "description_preview": _description_preview(n),
                "match": n.get("match", "substring"),
                "_score": n.get("_score", 0),
            }
            for n in page
        ]

    if _truthy(args.get("compact")):
        matches = [
            {"id": m.get("id"), "name": m.get("name", ""), "type": m.get("type", "")}
            for m in matches
        ]

    out: dict[str, Any] = {
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
            "Use type_filter for exact type match. "
            'Use group="Dev > Infra" or group_contains="Security" for schema v2 groups.'
        ),
        "page_info": {
            "next_cursor": next_cursor,
            "has_more": has_more,
            "total_estimate": total_estimate,
            "remaining_after_cursor": remaining_after_cursor,
            "page_size": page_size,
        },
    }
    if file_fallback_after_pg:
        out["search_source"] = "file_index"
        out["postgresql_fts_empty"] = True
        out["hint"] = (
            "PostgreSQL FTS returned no matches; results are from the file-backed graph index. "
            "Sync the mirror (file→PostgreSQL) so search matches on-disk nodes, or use refresh: "
            "after writes. "
            + out["hint"]
        )
    if group_meta is not None:
        out["group_filter"] = group_meta
    return out


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
        mode: summary | brief | full | debug (default brief; Wave 17A03)
        brief: legacy alias; explicit true/false still maps to brief/full when mode omitted.
        edge_limit: max edges per direction when building legacy outgoing/incoming (full mode).

    Returns:
        Node payload and edges per mode; brief uses relationships with reason.
    """
    from gobp.mcp.tools import read_v3 as _read_v3

    task_raw = args.get("task") or args.get("task_description")
    if task_raw and str(task_raw).strip():
        conn_t, is_v3_t = _read_v3._conn_v3(project_root)
        if conn_t is not None and is_v3_t:
            try:
                max_n = int(args.get("max_nodes", 15))
                return _read_v3.context_action(conn_t, str(task_raw).strip(), max_n)
            finally:
                conn_t.close()
        return {
            "ok": False,
            "error": "context: task= requires PostgreSQL schema v3",
        }

    mcp_action = str(args.get("_mcp_action", "") or "")
    node_id = args.get("node_id")
    if mcp_action == "get" and node_id and str(node_id).strip():
        mode_g = str(args.get("mode", "brief")).lower()
        if mode_g not in ("brief", "full"):
            mode_g = "brief"
        conn_g, is_v3_g = _read_v3._conn_v3(project_root)
        if conn_g is not None and is_v3_g:
            try:
                return _read_v3.get_v3(conn_g, str(node_id), mode_g)
            finally:
                conn_g.close()

    if not node_id:
        return {"ok": False, "error": "node_id parameter required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    if _truthy(args.get("compact")):
        nid = str(node_id)
        ec = len(index.get_edges_from(nid)) + len(index.get_edges_to(nid))
        return {
            "ok": True,
            "node": {
                "id": node.get("id"),
                "name": node.get("name", ""),
                "type": node.get("type", ""),
            },
            "edge_count": ec,
        }

    mode = str(args.get("mode", "") or "").strip().lower()
    if not mode:
        if str(args.get("brief", "")).lower() == "false":
            mode = "full"
        elif _truthy(args.get("brief")):
            mode = "brief"
        else:
            mode = "brief"
    if mode not in {"summary", "brief", "full", "debug"}:
        mode = "brief"

    use_full_edges = mode == "full"
    if mode == "brief":
        edge_limit = int(args.get("edge_limit", 30))
        edge_limit = max(1, min(edge_limit, 200))
    elif use_full_edges:
        edge_limit = int(args.get("edge_limit", 10_000))
        edge_limit = max(1, min(edge_limit, 10_000))
    else:
        edge_limit = None

    outgoing_raw = index.get_edges_from(node_id)
    incoming_raw = index.get_edges_to(node_id)
    relationships = _get_relationships(index, str(node_id))

    out_slice = outgoing_raw if edge_limit is None else outgoing_raw[:edge_limit]
    outgoing: list[dict[str, Any]] = []
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

    in_slice = incoming_raw if edge_limit is None else incoming_raw[:edge_limit]
    incoming: list[dict[str, Any]] = []
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

    decisions: list[dict[str, Any]] = []
    seen_decision_ids: set[str] = set()
    brief_mode = mode == "brief"
    for edge in outgoing_raw:
        target = index.get_node(edge.get("to", ""))
        if target and target.get("type") == "Decision":
            dec_id = target.get("id")
            if dec_id not in seen_decision_ids:
                what_txt = target.get("what", "")
                why_txt = target.get("why", "")
                if brief_mode:
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

    references: list[dict[str, Any]] = []
    ref_cap = 15 if brief_mode else None
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

    if mode == "summary":
        return {
            "ok": True,
            "node": _node_summary(node, index),
            "mode": mode,
        }

    if mode == "brief":
        return {
            "ok": True,
            "node": _node_for_context_brief(node),
            "mode": mode,
            "brief": True,
            "relationships": relationships,
            "edge_count": len(outgoing_raw) + len(incoming_raw),
            "outgoing_total": len(outgoing_raw),
            "incoming_total": len(incoming_raw),
            "outgoing_truncated": len(outgoing_raw) > len(outgoing),
            "incoming_truncated": len(incoming_raw) > len(incoming),
            "hint": (
                "Default mode=brief: use mode=full for legacy outgoing/incoming lists "
                "or mode=debug for raw storage fields."
            ),
        }

    if mode == "debug":
        out_dbg: dict[str, Any] = {
            "ok": True,
            "mode": "debug",
            "node": dict(node),
            "relationships": relationships,
            "outgoing_total": len(outgoing_raw),
            "incoming_total": len(incoming_raw),
        }
        return out_dbg

    # full
    node_out: dict[str, Any] = {}
    for k, v in node.items():
        if k in _RAW_META_FIELDS:
            continue
        node_out[k] = v
    node_out["description"] = _normalize_description_for_full(node)

    out: dict[str, Any] = {
        "ok": True,
        "node": node_out,
        "outgoing": outgoing,
        "incoming": incoming,
        "relationships": relationships,
        "decisions": decisions,
        "invariants": [],
        "references": references,
        "mode": "full",
    }
    out["outgoing_total"] = len(outgoing_raw)
    out["incoming_total"] = len(incoming_raw)
    out["outgoing_truncated"] = len(outgoing_raw) > len(outgoing)
    out["incoming_truncated"] = len(incoming_raw) > len(incoming)
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
    adj = getattr(index, "_adjacency", None)
    if direction in ("outgoing", "both"):
        out_edges = (
            adj.get_outgoing(node_id) if adj is not None else index.get_edges_from(node_id)
        )
        for edge in out_edges:
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
        in_edges = (
            adj.get_incoming(node_id) if adj is not None else index.get_edges_to(node_id)
        )
        for edge in in_edges:
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

    from gobp.mcp.tools import read_v3 as _read_v3

    conn_b, is_v3_b = _read_v3._conn_v3(project_root)
    if conn_b is not None and is_v3_b:
        try:
            since_raw = args.get("since")
            since_i: int | None
            if since_raw is None or since_raw == "":
                since_i = None
            else:
                try:
                    since_i = int(since_raw)
                except (TypeError, ValueError):
                    since_i = None
            gb_mode = "brief" if mode in ("brief", "standard") else mode
            if gb_mode == "summary":
                gb_mode = "brief"
            out = _read_v3.get_batch_v3(conn_b, ids, gb_mode, since_i)
            if out.get("ok"):
                out["not_found"] = []
                out["found"] = out["summary"].get("fetched", len(ids))
            return out
        finally:
            conn_b.close()

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


def _schema_token_matches_node(actual_type: str, token: str) -> bool:
    """Return whether ``actual_type`` satisfies an ``allowed_node_types`` token."""
    tok = token.strip()
    if tok == "all":
        return True
    if tok == "Node":
        return actual_type not in ("Session", "Document")
    return actual_type == tok


def _allowed_pairs_from_edge_def(edge_def: dict[str, Any]) -> list[tuple[str, str]]:
    """Expand ``allowed_node_types`` into (from_token, to_token) pairs."""
    raw = edge_def.get("allowed_node_types")
    if raw is None:
        return []
    items = [raw.strip()] if isinstance(raw, str) else [str(x).strip() for x in raw if str(x).strip()]
    if not items:
        return []
    pairs: list[tuple[str, str]] = []
    plain = [x for x in items if "->" not in x]
    for x in items:
        if "->" in x:
            a, b = x.split("->", 1)
            pairs.append((a.strip(), b.strip()))
    if plain:
        for f in plain:
            for t in plain:
                pairs.append((f, t))
    return pairs


def _normalize_target_types(tokens: set[str]) -> list[str]:
    """Turn internal type tokens into a stable list for API output."""
    if not tokens:
        return ["any"]
    mapped = [("any" if t == "all" else t) for t in tokens]
    return sorted(set(mapped), key=lambda x: (x == "any", x.casefold()))


def suggested_edges_from_schema(node_type: str, edges_schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Build edge suggestions from ``core_edges.yaml`` for ``template:`` / ``template_batch:``."""
    edge_types = edges_schema.get("edge_types", {}) if isinstance(edges_schema, dict) else {}
    aggregated_out: dict[str, set[str]] = defaultdict(set)
    aggregated_in: dict[str, set[str]] = defaultdict(set)
    notes: dict[str, str] = {}

    for edge_name, edge_def in edge_types.items():
        if not isinstance(edge_def, dict):
            continue
        if edge_name == "discovered_in":
            continue
        notes[edge_name] = str(edge_def.get("description", "") or "")
        directional = bool(edge_def.get("directional", True))
        pairs = _allowed_pairs_from_edge_def(edge_def)
        if not pairs:
            continue
        for from_tok, to_tok in pairs:
            if _schema_token_matches_node(node_type, from_tok):
                aggregated_out[edge_name].add(to_tok)
            if directional and _schema_token_matches_node(node_type, to_tok):
                aggregated_in[edge_name].add(from_tok)

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()

    for ename in sorted(aggregated_out.keys()):
        tlist = _normalize_target_types(aggregated_out[ename])
        key = (ename, "outgoing", tuple(tlist))
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "type": ename,
                "direction": "outgoing",
                "target_types": tlist,
                "note": notes.get(ename, ""),
            }
        )

    for ename in sorted(aggregated_in.keys()):
        edge_def = edge_types.get(ename, {})
        if not bool(edge_def.get("directional", True)):
            continue
        slist = _normalize_target_types(aggregated_in[ename])
        key = (ename, "incoming", tuple(slist))
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "type": ename,
                "direction": "incoming",
                "from_types": slist,
                "note": notes.get(ename, ""),
            }
        )

    return out


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

    edges_schema = getattr(index, "_edges_schema", None) or {}
    suggested_edges = suggested_edges_from_schema(node_type, edges_schema if isinstance(edges_schema, dict) else {})

    batch_format = f"create: {node_type}: {{name}} | {{description}}"
    batch_example = f"create: {node_type}: ExampleName | Short description of what this does"
    edge_lines_out: list[str] = []
    for sug in suggested_edges:
        if sug.get("direction") != "outgoing":
            continue
        et = str(sug.get("type", "relates_to"))
        edge_lines_out.append(f"edge+: ExampleName --{et}--> TargetName")
        if len(edge_lines_out) >= 3:
            break
    if edge_lines_out:
        batch_example = batch_example + "\n" + "\n".join(edge_lines_out)

    out: dict[str, Any] = {
        "ok": True,
        "type": node_type,
        "group": group,
        "frame": {"required": required, "optional": optional},
        "batch_format": batch_format,
        "batch_example": batch_example,
        "suggested_edges": suggested_edges,
        "hint": (
            "Use batch session_id='…' ops='…' for many creates/updates in one call. "
            "Use explore: before creating to avoid duplicates."
        ),
    }

    if isinstance(schema, dict) and str(schema.get("schema_name", "")) == "gobp_core_v2":
        from gobp.core.loader import package_schema_dir
        from gobp.core.schema_loader import load_schema_v2

        sd = project_root / "gobp" / "schema"
        if not sd.exists():
            sd = package_schema_dir()
        try:
            sv2 = load_schema_v2(sd)
            out["v2_template"] = {
                "group": sv2.get_group(node_type),
                "lifecycle": "draft",
                "read_order": sv2.get_default_read_order(node_type),
                "description": {"info": "(required, non-empty)", "code": ""},
            }
        except Exception:
            pass

    return out


def template_batch_action(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Return a fillable batch template for ``count`` nodes of one type (``template_batch: Engine``)."""
    node_type = str(
        args.get("query", args.get("type", args.get("node_type", "")))
    ).strip()
    count = int(args.get("count", 3))
    count = max(1, min(count, 50))

    template_result = template_action(
        index,
        project_root,
        {
            "query": node_type,
            "node_type": node_type,
            **{k: v for k, v in args.items() if k != "count"},
        },
    )
    if not template_result.get("ok"):
        return template_result

    suggested_edges = template_result.get("suggested_edges", [])
    outgoing_edges = [e for e in suggested_edges if e.get("direction") == "outgoing"]

    blocks: list[str] = []
    for i in range(1, count + 1):
        block_lines = [f"create: {node_type}: {{name_{i}}} | {{description_{i}}}"]
        for edge in outgoing_edges[:5]:
            et = str(edge.get("type", "relates_to"))
            block_lines.append(f"edge+: {{name_{i}}} --{et}--> {{target_name}}")
        blocks.append("\n".join(block_lines))

    batch_template = "\n\n".join(blocks)

    return {
        "ok": True,
        "type": node_type,
        "count": count,
        "frame_per_node": template_result.get("frame", {}),
        "suggested_edges": suggested_edges,
        "batch_template": batch_template,
        "instructions": [
            "Replace {placeholders} with actual values",
            "Add or remove edge+ lines freely — no limit per node",
            "Remove entire edge+ line if not applicable",
            "Add or remove node blocks — count is a suggestion",
            "Submit via: batch session_id='x' ops='<filled template>'",
            "Very large batch ops lists are auto-chunked internally",
            "Prefer one batch or quick: call per logical import; splitting is optional",
        ],
        "note": (
            f"Generated {count} blocks. Adjust freely — no hard limits on nodes or edges."
        ),
    }


def _sibling_entries(index: GraphIndex, node_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Peers in the same schema v2 group (excluding self)."""
    sids = index.find_siblings(node_id)[:limit]
    rows: list[dict[str, Any]] = []
    for sid in sids:
        sn = index.get_node(sid)
        if not sn:
            continue
        rows.append(
            {
                "id": sid,
                "name": sn.get("name", ""),
                "type": sn.get("type", ""),
                "read_order": sn.get("read_order", "reference"),
                "description_preview": _description_preview(sn),
            }
        )
    return rows


def explore_action(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Return best-matching node plus edges and close matches (explore: keyword)."""
    query = str(args.get("query", "")).strip()
    if not query:
        return {"ok": False, "error": "Query required"}

    from gobp.mcp.tools import read_v3 as _read_v3

    conn_x, is_v3_x = _read_v3._conn_v3(project_root)
    if conn_x is not None and is_v3_x:
        try:
            return _read_v3.explore_v3(conn_x, query)
        finally:
            conn_x.close()

    results: list[tuple[int, dict[str, Any]]] = []
    direct = index.get_node(query)
    if direct:
        best_score = 100
        best_node = direct
    else:
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

    ex_meta = {"discovered_in"}
    adj_ex = getattr(index, "_adjacency", None)
    if adj_ex is not None:
        for edge in adj_ex.get_outgoing(node_id, exclude_types=ex_meta):
            edge_type = str(edge.get("type", "relates_to"))
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
        for edge in adj_ex.get_incoming(node_id, exclude_types=ex_meta):
            edge_type = str(edge.get("type", "relates_to"))
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
    else:
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
    adj_ct = getattr(index, "_adjacency", None)
    if results:
        for score, node in results[1:6]:
            nid = str(node.get("id", ""))
            if adj_ct is not None:
                ec = adj_ct.edge_count(nid)
            else:
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

    group_path = str(best_node.get("group", "") or "")
    breadcrumb = _build_breadcrumb(group_path)
    sibling_ids = index.find_siblings(node_id)
    siblings = _sibling_entries(index, node_id)
    relationships = _get_relationships(index, node_id)

    if _truthy(args.get("compact")):
        edge_lines: list[str] = []
        for e in all_edges:
            other = e.get("node") or {}
            nm = other.get("name", "")
            typ = other.get("type", "")
            et = str(e.get("type", "relates_to"))
            if e.get("dir") == "out":
                edge_lines.append(f"--{et}--> {nm} ({typ})")
            else:
                edge_lines.append(f"<--{et}-- {nm} ({typ})")
        also_lines = [
            f"{n.get('id')} ({n.get('type')}) — {n.get('note', '')}" for n in also_found
        ]
        return {
            "ok": True,
            "node": {
                "id": node_id,
                "name": best_node.get("name", ""),
                "type": best_node.get("type", ""),
            },
            "breadcrumb": [c["label"] for c in breadcrumb],
            "edges": edge_lines,
            "edge_count": len(all_edges),
            "also_found": also_lines,
        }

    node_payload: dict[str, Any] = {**_node_for_context_brief(best_node), "match_score": best_score}

    return {
        "ok": True,
        "node": node_payload,
        "breadcrumb": breadcrumb,
        "group": group_path,
        "siblings": siblings,
        "siblings_count": len(sibling_ids),
        "relationships": relationships,
        "edges": all_edges,
        "edge_count": len(all_edges),
        "also_found": also_found,
        "hint": (
            "Use retype: or delete: to clean duplicates. Use edge: or batch ops to add relationships. "
            "Call suggest: before create (dec:d011); relationships include edge reason when present."
        ),
    }


def suggest_action(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Suggest reusable nodes from a short natural-language context."""
    del project_root
    qtext = str(args.get("query", "")).strip()
    if not qtext:
        return {
            "ok": False,
            "error": "Context required. Example: suggest: Payment Flow",
        }

    group_filter = str(args.get("group", "") or "").strip()
    type_filter = str(args.get("type", "") or args.get("node_type", "") or "").strip()
    lim = max(1, min(int(args.get("limit", 10)), 50))

    candidates: dict[str, dict[str, Any]] = {}
    for _sc, node in search_nodes(
        index,
        qtext,
        type_filter=type_filter or None,
        exclude_types=["Session", "Document"],
        limit=max(lim * 5, 20),
    ):
        nid = str(node.get("id", "") or "")
        if nid:
            candidates[nid] = node
    for row in suggest_related(
        index, qtext, exclude_types=["Session", "Document"], limit=max(lim * 3, 15)
    ):
        nid = str(row.get("id", "") or "")
        if nid and nid not in candidates:
            n = index.get_node(nid)
            if n:
                candidates[nid] = n

    rows: list[dict[str, Any]] = []
    for node in candidates.values():
        match_score = _match_score_float(qtext, node)
        g = str(node.get("group", "") or "")
        same_group = bool(group_filter and g.startswith(group_filter))
        same_type = bool(type_filter and str(node.get("type", "") or "") == type_filter)
        warning = ""
        if match_score > 0.8 and (same_group or same_type):
            warning = "HIGH SIMILARITY — consider updating instead of creating"
        rel = "high" if match_score >= 0.6 else "medium" if match_score >= 0.3 else "low"
        preview = _truncate(_get_info_from_node(node), 100)
        rows.append(
            {
                "id": node.get("id"),
                "type": str(node.get("type", "") or ""),
                "name": str(node.get("name", "") or ""),
                "group": g,
                "match_score": round(match_score, 4),
                "same_group": same_group,
                "same_type": same_type,
                "description_preview": preview,
                "warning": warning,
                "why": warning or f"match_score={match_score:.2f}",
                "relevance": rel,
            }
        )

    rows.sort(
        key=lambda r: (
            -int(r["same_group"] and r["same_type"]),
            -int(r["same_group"]),
            -int(r["same_type"]),
            -float(r["match_score"]),
        )
    )
    top = rows[:lim]
    rec = "UPDATE existing node" if top and float(top[0]["match_score"]) > 0.8 else "CREATE new node"
    out: dict[str, Any] = {
        "ok": True,
        "context": qtext,
        "suggestions": top,
        "count": len(top),
        "recommendation": rec,
        "hint": (
            "Call suggest: with group=\"...\" before create (dec:d011). "
            "Prefer edge: / batch link when recommendation is UPDATE."
        ),
    }
    if group_filter:
        out["group_filter"] = group_filter
    return out


def evolve_action(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Read-only evolve-cycle helper: Reflection checklist or lookup by ``wave_ref``.

    ``gobp(query="evolve: wave='17A05'")`` returns a template + existing LessonSkill summary.
    ``gobp(query="evolve: wave='17A05' status='complete'")`` returns an existing Reflection
    for that wave when present.
    """
    del project_root  # read-only; kept for signature parity with other actions
    wave_ref = str(args.get("wave") or args.get("query") or "").strip()
    status = str(args.get("status") or "").strip().lower()

    if not wave_ref:
        return {
            "ok": False,
            "error": "wave is required (e.g. evolve: wave='17A05')",
        }

    if status == "complete":
        matches = [
            n
            for n in index.all_nodes()
            if n.get("type") == "Reflection"
            and str(n.get("wave_ref", "")).strip() == wave_ref
        ]
        if matches:
            return {"ok": True, "reflection": matches[0]}
        return {
            "ok": False,
            "message": f"No Reflection found for wave '{wave_ref}'",
        }

    skills = index.nodes_by_type("LessonSkill")
    skill_summary = [
        {
            "id": s.get("id"),
            "name": s.get("name"),
            "sub_type": s.get("sub_type", ""),
            "evolve_count": s.get("evolve_count", 0),
        }
        for s in skills[:20]
    ]

    checklist = {
        "wave_ref": wave_ref,
        "instruction": (
            "Tạo Reflection node với:\n"
            "  trigger: wave_complete\n"
            f"  wave_ref: '{wave_ref}'\n"
            "  findings: list of [KEEP|UPGRADE|CREATE] <skill_name> — <reason>\n"
            "Sau đó dùng batch: để upgrade/create LessonSkill nodes."
        ),
        "existing_skills": skill_summary,
        "template": {
            "type": "Reflection",
            "group": "Meta > Reflection",
            "trigger": "wave_complete",
            "wave_ref": wave_ref,
            "findings": [],
            "next_focus": "",
        },
    }
    return {"ok": True, "checklist": checklist}

