"""GoBP query dispatcher.

Parses structured query protocol and routes to correct tool handler.

Protocol:
    gobp(query="<action>:<type> <key>='<value>' ...")

Actions:
    overview    -> gobp_overview()
    find        -> find()
    get         -> context() or signature()
    create      -> node_upsert()
    update      -> node_upsert() with existing id
    lock        -> decision_lock()
    session     -> session_log()
    import      -> import_proposal()
    commit      -> import_commit()
    validate    -> validate()
    extract     -> lessons_extract()
    sections    -> doc_sections()
    recent      -> session_recent()
    decisions   -> decisions_for()
    signature   -> signature()

Examples:
    "overview:"
    "find: login"
    "find:Decision auth"
    "get: node:feat_login"
    "create:Idea name='use OTP' subject='auth:login' session_id='session:x'"
    "lock:Decision topic='auth:login' what='use OTP' why='SMS unreliable' locked_by='CEO,Claude'"
    "session:start actor='cursor' goal='implement login'"
    "session:end outcome='done' handoff='next: write tests'"
    "validate: nodes"
    "extract: lessons"
    "sections: doc:wave_4_brief"
    "recent: 3"
    "decisions: auth:login.method"
    "signature: node:feat_login"
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.id_config import generate_external_id


# Canonical NodeType mapping — case-insensitive input → PascalCase output
_TYPE_CANONICAL: dict[str, str] = {
    "node": "Node",
    "idea": "Idea",
    "decision": "Decision",
    "session": "Session",
    "document": "Document",
    "lesson": "Lesson",
    "concept": "Concept",
    "testkind": "TestKind",
    "testcase": "TestCase",
    "engine": "Engine",
    "flow": "Flow",
    "entity": "Entity",
    "feature": "Feature",
    "invariant": "Invariant",
    "screen": "Screen",
    "apiendpoint": "APIEndpoint",
    "repository": "Repository",
    "wave": "Wave",
}


def _normalize_type(raw: str) -> str:
    """Normalize NodeType to canonical PascalCase.

    Case-insensitive: "decision", "DECISION", "DeciSion" → "Decision"
    Unknown types passed through unchanged.
    """
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "", raw).casefold()
    if not cleaned:
        return raw
    return _TYPE_CANONICAL.get(cleaned, raw)


def _normalize_node_type(node_type: str) -> str:
    """Normalize user-provided node type to canonical schema casing."""
    return _normalize_type(node_type)


def _classify_doc_priority(content: str, path: str) -> str:
    """Auto-classify document priority based on content keywords.

    Rules (deterministic, no AI):
      critical: user flows, auth, payment, proof of presence, trust gate
      high:     entity, engine, architecture, API, database
      medium:   design, copy, admin, notification, map
      low:      mascot, growth, future, level system, campaign
    """
    content_lower = content.lower()
    path_lower = path.lower()
    combined = content_lower + " " + path_lower

    critical_keywords = [
        "user flow", "authentication", "proof of presence", "payment",
        "trust gate", "verify gate", "core flow", "master definition",
        "pop_protocol", "mihot", "homecoming", "registration flow",
    ]
    high_keywords = [
        "entity", "engine", "architecture", "api", "database",
        "engine spec", "adapter", "domain dictionary", "migration",
        "interface reference", "middleware", "scale",
    ]
    low_keywords = [
        "mascot", "growth", "launch", "campaign", "level system",
        "gamification", "future", "phase 2", "nice to have",
    ]

    critical_score = sum(1 for kw in critical_keywords if kw in combined)
    high_score = sum(1 for kw in high_keywords if kw in combined)
    low_score = sum(1 for kw in low_keywords if kw in combined)

    if critical_score >= 2:
        return "critical"
    elif critical_score >= 1 or high_score >= 3:
        return "high"
    elif low_score >= 2:
        return "low"
    else:
        return "medium"


# -- Query parser --------------------------------------------------------------

_POSITIONAL_KEY: dict[str, str] = {
    "find": "query",
    "get": "node_id",
    "context": "node_id",
    "signature": "node_id",
    "code": "node_id",
    "invariants": "node_id",
    "tests": "node_id",
    "related": "node_id",
    "sections": "doc_id",
    "decisions": "topic",
    "validate": "scope",
    "stats": "action_filter",
    "import": "source_path",
    "commit": "proposal_id",
    "recent": "n",
    "edge": "_edge_raw",
}


def _coerce_value(v: str) -> Any:
    """Coerce string values to appropriate Python types."""
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    if v.lower() in ("null", "none"):
        return None
    if v.isdigit():
        return int(v)
    return v


def _tokenize_rest(rest: str) -> list[str]:
    """Tokenize rest string while preserving quoted groups."""
    tokens: list[str] = []
    current: list[str] = []
    in_quote = False
    quote_char = None

    for char in rest:
        if not in_quote and char in ("'", '"'):
            in_quote = True
            quote_char = char
            current.append(char)
        elif in_quote and char == quote_char:
            in_quote = False
            quote_char = None
            current.append(char)
        elif not in_quote and char == " ":
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)

    if current:
        tokens.append("".join(current))

    return [t for t in tokens if t]


def _parse_edge_rest(rest: str) -> dict[str, Any]:
    """Parse edge arrow syntax: 'node:a --type--> node:b [key=val]'."""
    edge_pattern = re.compile(r"^([\w.:\-]+)\s+--(\w+)-->\s+([\w.:\-]+)(.*)?$")
    m = edge_pattern.match(rest)
    if m:
        params: dict[str, Any] = {
            "from": m.group(1).strip(),
            "edge_type": m.group(2).strip(),
            "to": m.group(3).strip(),
        }
        extra = m.group(4).strip() if m.group(4) else ""
        if extra:
            for km in re.finditer(r"(\w+)='([^']*)'|(\w+)=\"([^\"]*)\"|(\w+)=(\S+)", extra):
                if km.group(1):
                    params[km.group(1)] = km.group(2)
                elif km.group(3):
                    params[km.group(3)] = km.group(4)
                elif km.group(5):
                    params[km.group(5)] = _coerce_value(km.group(6))
        return params
    return {"_edge_raw": rest}


def parse_query(query: str) -> tuple[str, str, dict[str, Any]]:
    """Parse query string into (action, node_type, params)."""
    query = query.strip()
    if not query:
        return "overview", "", {}

    colon_idx = query.find(":")
    if colon_idx == -1:
        return "find", "", {"query": query}

    action_part = query[:colon_idx].strip().lower()
    rest = query[colon_idx + 1:].strip()

    action_tokens = action_part.split(None, 1)
    action = action_tokens[0]
    node_type = action_tokens[1] if len(action_tokens) > 1 else ""
    if node_type:
        node_type = _normalize_node_type(node_type)

    if not rest:
        return action, node_type, {}

    if action == "edge":
        return action, "", _parse_edge_rest(rest)

    params: dict[str, Any] = {}
    tokens = _tokenize_rest(rest)

    if action in ("create", "lock", "upsert") and node_type == "" and tokens:
        first = tokens[0]
        if "=" not in first:
            node_type = _normalize_node_type(first.strip("'\""))
            tokens = tokens[1:]

    if action == "find" and node_type == "" and tokens:
        first = tokens[0]
        first_value = first.strip("'\"")
        normalized_first = _normalize_node_type(first_value)
        if "=" not in first and ":" not in first and normalized_first in _TYPE_CANONICAL.values():
            node_type = normalized_first
            tokens = tokens[1:]

    positional_key = _POSITIONAL_KEY.get(action, "query")
    positional_consumed = False

    for token in tokens:
        if "=" in token:
            eq_idx = token.index("=")
            k = token[:eq_idx].strip()
            v = token[eq_idx + 1:].strip().strip("'\"")
            params[k] = _coerce_value(v)
        elif not positional_consumed:
            value = token.strip("'\"")
            params[positional_key] = value
            if positional_key != "query":
                # Backward compatibility for existing callers/tests.
                params["query"] = value
            positional_consumed = True

    return action, node_type, params


_a, _t, _p = parse_query("find: login page_size=10")
assert (_a, _t) == ("find", "")
assert _p.get("query") == "login" and _p.get("page_size") == 10
_a, _t, _p = parse_query("find:Decision auth page_size=5")
assert (_a, _t) == ("find", "Decision")
assert _p.get("query") == "auth" and _p.get("page_size") == 5
_a, _t, _p = parse_query("find:decision auth page_size=5")
assert (_a, _t) == ("find", "Decision")
assert _p.get("query") == "auth" and _p.get("page_size") == 5
_a, _t, _p = parse_query("related: node:x direction='outgoing' page_size=10")
assert (_a, _t) == ("related", "")
assert _p.get("node_id") == "node:x" and _p.get("direction") == "outgoing" and _p.get("page_size") == 10
_a, _t, _p = parse_query("tests: node:x page_size=20")
assert (_a, _t) == ("tests", "")
assert _p.get("node_id") == "node:x" and _p.get("page_size") == 20
assert parse_query("session:start actor='cursor' goal='test'")[2]["query"] == "start"
assert parse_query("create:Node name='Login' priority='critical'")[2]["name"] == "Login"
assert parse_query("create:Node automated=true")[2]["automated"] is True


# -- Dispatch router -----------------------------------------------------------

async def dispatch(
    query: str,
    index: GraphIndex,
    project_root: Path,
) -> dict[str, Any]:
    """Route parsed query to correct tool handler.

    Returns tool result dict with added _dispatch_info for audit.
    """
    from gobp.mcp.tools import import_ as tools_import
    from gobp.mcp.tools import maintain as tools_maintain
    from gobp.mcp.tools import read as tools_read
    from gobp.mcp.tools import write as tools_write
    from gobp.mcp.tools.advanced import lessons_extract

    action, node_type, params = parse_query(query)
    dispatch_info = {"action": action, "type": node_type, "params": params}

    try:
        def _is_dry_run(value: Any) -> bool:
            return value in ("true", "1", True)

        # -- Read actions ------------------------------------------------------
        if action == "overview":
            result = tools_read.gobp_overview(index, project_root, params)

        elif action == "version":
            import gobp as _gobp

            result = {
                "ok": True,
                "protocol_version": "2.0",
                "gobp_version": getattr(_gobp, "__version__", "0.1.0"),
                "schema_version": "2.1",
                "deprecated_actions": [],
                "supported_actions": list(PROTOCOL_GUIDE.get("actions", {}).keys()),
                "changelog": [
                    "v2.0 (Wave 14): version: action, read-only mode, schema governance",
                    "v1.5 (Wave 13): pagination, upsert:, stats:, guardrails",
                    "v1.0 (Wave 10A): gobp() single tool, structured query protocol",
                ],
                "tip": "Call gobp(query='overview:') to see current project state.",
            }

        elif action == "find":
            args: dict[str, Any] = {}
            if "query" in params:
                args["query"] = params["query"]
            elif node_type:
                args["query"] = node_type
                node_type = ""
            else:
                args["query"] = ""
            if node_type:
                args["type"] = node_type
            if "limit" in params:
                args["limit"] = int(params["limit"])
            if "page_size" in params:
                args["page_size"] = int(params["page_size"])
            if "cursor" in params:
                args["cursor"] = params["cursor"]
            if "sort" in params:
                args["sort"] = params["sort"]
            if "direction" in params:
                args["direction"] = params["direction"]
            if "mode" in params:
                args["mode"] = params["mode"]
            result = tools_read.find(index, project_root, args)

        elif action in ("get", "context"):
            node_id = params.get("query") or params.get("id") or params.get("node_id", "")
            ctx_args: dict[str, Any] = {"node_id": node_id}
            if "mode" in params:
                ctx_args["mode"] = params["mode"]
            if "brief" in params:
                ctx_args["brief"] = params["brief"]
            if "edge_limit" in params:
                ctx_args["edge_limit"] = params["edge_limit"]
            result = tools_read.context(index, project_root, ctx_args)

        elif action == "get_batch":
            raw_ids = params.get("ids") or params.get("query", "")
            args = {
                "ids": raw_ids,
                "mode": params.get("mode", "brief"),
                "max": params.get("max", 20),
            }
            result = tools_read.get_batch(index, project_root, args)

        elif action == "signature":
            node_id = params.get("query") or params.get("id") or params.get("node_id", "")
            result = tools_read.signature(index, project_root, {"node_id": node_id})

        elif action in ("recent", "sessions"):
            n = int(params.get("query", params.get("n", 3)))
            result = tools_read.session_recent(index, project_root, {"n": n})

        elif action == "decisions":
            topic = params.get("query") or params.get("topic", "")
            node_id = params.get("node_id", "")
            args = {}
            if topic:
                args["topic"] = topic
            if node_id:
                args["node_id"] = node_id
            result = tools_read.decisions_for(index, project_root, args)

        elif action == "sections":
            doc_id = params.get("query") or params.get("doc_id", "")
            result = tools_read.doc_sections(index, project_root, {"doc_id": doc_id})

        elif action == "code":
            node_id = params.get("query") or params.get("node_id", "")
            # Handle 'code: node:x path=... description=... language=...' add variant
            add_ref = None
            if params.get("path"):
                add_ref = {
                    "path": params.get("path", ""),
                    "description": params.get("description", ""),
                    "language": params.get("language", ""),
                }
            args = {"node_id": node_id}
            if add_ref:
                args["add"] = add_ref
            result = tools_read.code_refs(index, project_root, args)

        elif action == "invariants":
            node_id = params.get("query") or params.get("node_id", "")
            result = tools_read.node_invariants(index, project_root, {"node_id": node_id})

        elif action == "tests":
            node_id = params.get("query") or params.get("node_id", "")
            status = params.get("status")
            args = {"node_id": node_id}
            if status:
                args["status"] = status
            if "page_size" in params:
                args["page_size"] = params["page_size"]
            if "cursor" in params:
                args["cursor"] = params["cursor"]
            result = tools_read.node_tests(index, project_root, args)

        elif action == "related":
            node_id = params.get("query") or params.get("node_id", "")
            direction = params.get("direction", "both")
            edge_type = params.get("edge_type")
            args = {"node_id": node_id, "direction": direction}
            if edge_type:
                args["edge_type"] = edge_type
            if "mode" in params:
                args["mode"] = params["mode"]
            if "page_size" in params:
                args["page_size"] = params["page_size"]
            if "cursor" in params:
                args["cursor"] = params["cursor"]
            result = tools_read.node_related(index, project_root, args)

        elif action == "template":
            node_type_arg = _normalize_type(
                str(params.get("query") or params.get("node_type") or node_type or "")
            )
            result = tools_read.node_template(
                index, project_root, {"query": node_type_arg}
            )

        elif action == "interview":
            node_id = str(params.get("node_id") or params.get("query") or "")
            answered_raw = params.get("answered", "")
            if isinstance(answered_raw, list):
                answered_list = [str(a).strip() for a in answered_raw if str(a).strip()]
            elif answered_raw:
                answered_list = [a.strip() for a in str(answered_raw).split(",") if a.strip()]
            else:
                answered_list = []
            result = tools_read.node_interview(
                index,
                project_root,
                {"node_id": node_id, "answered": answered_list},
            )

        # -- Write actions -----------------------------------------------------
        elif action == "create":
            node_type = _normalize_type(node_type or params.pop("type", "Node"))

            # Auto-generate ID if not provided
            node_id = params.pop("id", params.pop("node_id", None))
            auto_generated_id = False
            if not node_id:
                node_id = generate_external_id(node_type, project_root)
                auto_generated_id = True

            create_fields = {
                k: v for k, v in params.items() if k not in ("name", "type", "session_id")
            }
            if node_type == "Idea":
                idea_name = params.get("name", "")
                create_fields.setdefault("raw_quote", idea_name or "Auto-generated idea")
                create_fields.setdefault("interpretation", idea_name or "Auto-generated idea")
                create_fields.setdefault("subject", "general")
                create_fields.setdefault("maturity", "RAW")
                create_fields.setdefault("confidence", "medium")

            args = {
                "id": node_id,
                "type": node_type,
                "name": params.get("name", ""),
                "fields": create_fields,
                "session_id": params.get("session_id", ""),
            }
            if _is_dry_run(params.get("dry_run")):
                existing = index.get_node(node_id) if node_id else None
                result = {
                    "ok": True,
                    "dry_run": True,
                    "would_action": "updated" if existing else "created",
                    "node_id": node_id or "(auto-generated)",
                    "name": args.get("name", ""),
                    "type": node_type,
                    "message": "dry_run=true: no changes made",
                }
            else:
                result = tools_write.node_upsert(index, project_root, args)
            if (
                isinstance(result, dict)
                and not result.get("ok")
                and auto_generated_id
                and node_type in ("Idea", "Decision", "Lesson")
            ):
                fallback_args = dict(args)
                fallback_args.pop("id", None)
                result = tools_write.node_upsert(index, project_root, fallback_args)
                if isinstance(result, dict) and result.get("ok"):
                    result["node_id"] = node_id

        elif action == "update":
            node_id = params.pop("id", params.pop("node_id", ""))
            raw_update_type = node_type or params.pop("type", "")
            update_type = _normalize_type(raw_update_type) if raw_update_type else ""
            args = {
                "id": node_id,
                "type": update_type,
                "name": params.get("name", ""),
                "fields": {k: v for k, v in params.items() if k not in ("name", "type")},
                "session_id": params.get("session_id", ""),
            }
            if _is_dry_run(params.get("dry_run")):
                existing = index.get_node(node_id) if node_id else None
                result = {
                    "ok": True,
                    "dry_run": True,
                    "would_action": "updated" if existing else "created",
                    "node_id": node_id or "(auto-generated)",
                    "name": args.get("name", ""),
                    "type": args.get("type", ""),
                    "message": "dry_run=true: no changes made",
                }
            else:
                result = tools_write.node_upsert(index, project_root, args)

        elif action == "upsert":
            node_type = _normalize_type(node_type or params.pop("type", "Node"))
            dedupe_key = params.pop("dedupe_key", "name")
            dedupe_value = params.get(dedupe_key, "")
            session_id = params.get("session_id", "")

            is_dry = _is_dry_run(params.get("dry_run"))

            existing_node = None
            if dedupe_value:
                candidates = index.nodes_by_type(node_type)
                existing_node = next(
                    (n for n in candidates if str(n.get(dedupe_key, "")) == str(dedupe_value)),
                    None,
                )

            if is_dry:
                result = {
                    "ok": True,
                    "dry_run": True,
                    "would_action": "updated" if existing_node else "created",
                    "dedupe_key": dedupe_key,
                    "dedupe_value": dedupe_value,
                    "existing_id": existing_node.get("id") if existing_node else None,
                    "message": "dry_run=true: no changes made",
                }
            else:
                node_id = existing_node.get("id") if existing_node else None
                if not node_id:
                    node_id = generate_external_id(node_type, project_root)
                args = {
                    "id": node_id,
                    "type": node_type,
                    "name": params.get("name", dedupe_value),
                    "fields": {
                        k: v
                        for k, v in params.items()
                        if k not in ("name", "type", "session_id", "dry_run")
                    },
                    "session_id": session_id,
                }
                result = tools_write.node_upsert(index, project_root, args)
                if result.get("ok"):
                    result["dedupe_key"] = dedupe_key
                    result["dedupe_value"] = dedupe_value
                    result["existing_id"] = existing_node.get("id") if existing_node else None
                    if not result.get("action"):
                        result["action"] = "updated" if existing_node else "created"

        elif action == "lock":
            locked_by_raw = params.get("locked_by", "CEO,Claude-CLI")
            locked_by = [s.strip() for s in locked_by_raw.split(",")]
            args = {
                "topic": params.get("topic", ""),
                "what": params.get("what", ""),
                "why": params.get("why", ""),
                "locked_by": locked_by,
                "session_id": params.get("session_id", ""),
                "alternatives_considered": [],
            }
            if _is_dry_run(params.get("dry_run")):
                result = {
                    "ok": True,
                    "dry_run": True,
                    "would_action": "created",
                    "type": "Decision",
                    "topic": args.get("topic", ""),
                    "message": "dry_run=true: no changes made",
                }
            else:
                result = tools_write.decision_lock(index, project_root, args)

        elif action == "session":
            sub = params.get("query", "start")
            args = {
                "action": sub,
                "actor": params.get("actor", "unknown"),
                "goal": params.get("goal", ""),
                "outcome": params.get("outcome", ""),
                "pending": params.get("pending", "").split(",") if params.get("pending") else [],
                "handoff_notes": params.get("handoff", params.get("handoff_notes", "")),
                "role": params.get("role", "contributor"),
            }
            if "session_id" in params:
                args["session_id"] = params["session_id"]
            if _is_dry_run(params.get("dry_run")):
                existing = index.get_node(args.get("session_id", "")) if args.get("session_id") else None
                result = {
                    "ok": True,
                    "dry_run": True,
                    "would_action": "updated" if existing else "created",
                    "action": sub,
                    "session_id": args.get("session_id", "(auto-generated)"),
                    "message": "dry_run=true: no changes made",
                }
            else:
                result = tools_write.session_log(index, project_root, args)

        elif action == "edge":
            from_id = params.get("from", "")
            to_id = params.get("to", "")
            edge_type = params.get("edge_type", "relates_to")
            reason = params.get("reason", "")

            if not from_id or not to_id:
                result = {
                    "ok": False,
                    "error": "edge: requires format: node:a --edge_type--> node:b",
                    "hint": "Example: gobp(query=\"edge: node:flow_auth --implements--> node:pop_protocol\")",
                }
            else:
                from gobp.core.loader import load_schema
                from gobp.core.mutator import create_edge
                from pathlib import Path as _Path

                schema_dir = project_root / "gobp" / "schema"
                edges_schema = load_schema(schema_dir / "core_edges.yaml")

                edge = {
                    "from": from_id,
                    "to": to_id,
                    "type": edge_type,
                }
                if reason:
                    edge["reason"] = reason

                # Validate both nodes exist
                from_node = index.get_node(from_id)
                to_node = index.get_node(to_id)
                if not from_node:
                    result = {"ok": False, "error": f"Node not found: {from_id}"}
                elif not to_node:
                    result = {"ok": False, "error": f"Node not found: {to_id}"}
                else:
                    try:
                        result = create_edge(
                            gobp_root=project_root,
                            edge=edge,
                            schema=edges_schema,
                            actor="gobp-dispatcher",
                            edge_file_name="semantic_edges.yaml",
                        )
                        if result.get("ok"):
                            result["edge_created"] = {
                                "from": from_id,
                                "from_name": from_node.get("name", ""),
                                "type": edge_type,
                                "to": to_id,
                                "to_name": to_node.get("name", ""),
                            }
                    except Exception as e:
                        result = {"ok": False, "error": str(e)}

        # -- Import actions ----------------------------------------------------
        elif action == "import":
            source_path_str = params.get("source_path") or params.get("query") or ""
            session_id = params.get("session_id", "")

            if not source_path_str:
                result = {
                    "ok": False,
                    "error": "import: requires source path",
                    "hint": "gobp(query=\"import: path/to/doc.md session_id='session:x'\")",
                }
            else:
                # Resolve path relative to project root
                source_path = project_root / source_path_str

                # Read file content for classification
                content = ""
                sections = []
                if source_path.exists():
                    content = source_path.read_text(encoding="utf-8", errors="replace")
                    # Extract markdown headings as sections
                    import re as _re
                    sections = [
                        {"heading": m.group(2).strip(), "level": len(m.group(1))}
                        for m in _re.finditer(r"^(#{1,3})\s+(.+)$", content, _re.MULTILINE)
                    ][:20]  # max 20 sections

                # Auto-classify priority
                priority = _classify_doc_priority(content, source_path_str)

                # Collision-proof doc_id: slug + md5(normalized path)
                import hashlib as _hashlib
                import re as _re3
                path_normalized = str(source_path).replace("\\", "/").lower()
                short_hash = _hashlib.md5(path_normalized.encode()).hexdigest()[:6]
                doc_slug = _re3.sub(r"[^a-z0-9]+", "_", source_path.stem.lower()).strip("_")
                doc_id = f"doc:{doc_slug}_{short_hash}"

                # Create Document node
                from datetime import datetime, timezone

                now_iso = datetime.now(timezone.utc).isoformat()
                content_hash = f"sha256:{_hashlib.sha256(content.encode()).hexdigest()}"

                doc_node = {
                    "id": doc_id,
                    "type": "Document",
                    "name": source_path.stem.replace("_", " ").title(),
                    "source_path": source_path_str,
                    "content_hash": content_hash,
                    "registered_at": now_iso,
                    "last_verified": now_iso,
                    "priority": priority,
                    "sections": sections,
                    "status": "ACTIVE",
                    "session_id": session_id,
                }

                doc_args = {
                    "id": doc_id,
                    "type": "Document",
                    "name": doc_node["name"],
                    "fields": {
                        k: v for k, v in doc_node.items()
                        if k not in ("id", "type", "name", "session_id")
                    },
                    "session_id": session_id,
                }

                upsert_result = tools_write.node_upsert(index, project_root, doc_args)

                if not upsert_result.get("ok"):
                    result = {
                        "ok": False,
                        "error": upsert_result.get("error", "Failed to create Document node"),
                        "source_path": source_path_str,
                        "file_exists": source_path.exists(),
                    }
                else:
                    result = {
                        "ok": True,
                        "document_node": doc_id,
                        "document_name": doc_node["name"],
                        "priority": priority,
                        "sections_found": len(sections),
                        "sections": sections[:5],  # show first 5
                        "content_hash": content_hash,
                        "file_exists": source_path.exists(),
                        "suggestion": (
                            f"Document node created with collision-proof ID. "
                            f"Now extract key concepts:\n"
                            f"  gobp(query=\"create:Node name='...' priority='{priority}' session_id='{session_id}'\")\n"
                            f"Then link:\n"
                            f"  gobp(query=\"edge: node:x --references--> {doc_id}\")"
                        ),
                    }

        elif action == "commit":
            proposal_id = params.get("query") or params.get("proposal_id", "")
            args = {
                "proposal_id": proposal_id,
                "accept": params.get("accept", "all"),
                "session_id": params.get("session_id", ""),
            }
            result = tools_import.import_commit(index, project_root, args)

        # -- Maintenance actions -----------------------------------------------
        elif action == "validate":
            scope = params.get("query", params.get("scope", "all"))
            if scope in ("schema-docs", "schema-tests", "schema"):
                result = tools_read.schema_governance(
                    index, project_root, {"scope": scope}
                )
            elif scope == "metadata":
                result = tools_read.metadata_lint(index, project_root, params)
            else:
                result = tools_maintain.validate(
                    index, project_root, {"scope": scope, "severity_filter": "all"}
                )

        elif action == "extract":
            result = await lessons_extract(index, project_root, {})

        elif action == "dedupe":
            scope = params.get("action_filter") or params.get("scope", "edges")
            if scope in ("edges", "all"):
                from gobp.core.mutator import deduplicate_edges

                result = deduplicate_edges(project_root)
            else:
                result = {
                    "ok": False,
                    "error": f"dedupe: scope '{scope}' not supported. Use 'edges' or 'all'.",
                }

        elif action == "recompute":
            scope = params.get("query", params.get("scope", "priorities"))
            if scope == "priorities":
                args = {
                    "dry_run": params.get("dry_run", False),
                    "type": params.get("type", ""),
                    "session_id": params.get("session_id", ""),
                }
                result = tools_read.recompute_priorities(index, project_root, args)
            else:
                result = {"ok": False, "error": f"recompute: unknown scope '{scope}'"}

        # -- Unknown action ----------------------------------------------------
        else:
            # Fallback: try find
            result = tools_read.find(index, project_root, {"query": query})
            dispatch_info["fallback"] = True

    except Exception as e:
        result = {
            "ok": False,
            "error": str(e),
            "hint": _get_hint(action, node_type),
        }

    # Add dispatch info for audit
    result["_dispatch"] = dispatch_info
    return result


def _get_hint(action: str, node_type: str) -> str:
    """Return helpful hint for failed action."""
    hints = {
        "create": "Usage: gobp(query=\"create:<NodeType> name='x' session_id='session:y'\")",
        "lock": "Usage: gobp(query=\"lock:Decision topic='x' what='y' why='z' locked_by='CEO,Claude'\")",
        "session": "Usage: gobp(query=\"session:start actor='x' goal='y'\") or session:end",
        "import": "Usage: gobp(query=\"import: path/to/file.md session_id='session:x'\")",
        "commit": "Usage: gobp(query=\"commit: imp:proposal-id accept=all session_id='session:x'\")",
    }
    return hints.get(action, "Call gobp(query='overview:') to see all available actions")


# -- Protocol guide (optional full copy via overview: full_interface=true) -----

PROTOCOL_GUIDE = {
    "protocol": "gobp query protocol v2",
    "format": "<action>:<NodeType> <key>='<value>' ...",
    "actions": {
        "version:": "Protocol version + changelog + deprecations",
        "validate: schema-docs": "Cross-check schema vs SCHEMA.md documentation",
        "validate: schema-tests": "Check tests reference valid node types",
        "validate: metadata": "Check all nodes for missing required fields",
        "validate: metadata type=Flow": "Check only Flow nodes",
        "overview:": "Project stats (slim); full_interface=true for full action catalog",
        "overview: full_interface=true": "Same as overview with full PROTOCOL_GUIDE (large JSON)",
        "find: <keyword>": "Search any node by keyword",
        "find: <keyword> mode=summary": "Lightweight results (~50 tokens/node)",
        "find: <keyword> mode=brief": "Medium results (~150 tokens/node)",
        "find:<NodeType> <keyword>": "Search by type + keyword",
        "get: <node_id>": "Full node + edges + decisions",
        "get: <node_id> mode=brief": "Brief node detail",
        "get_batch: ids='node:a,node:b,node:c'": "Fetch multiple nodes (mode=brief)",
        "get_batch: ids='node:a,node:b' mode=summary": "Lightweight batch fetch",
        "signature: <node_id>": "Minimal node summary",
        "recent: <n>": "Latest N sessions",
        "decisions: <topic>": "Locked decisions for topic",
        "sections: <doc_id>": "Document sections list",
        "code: <node_id>": "Code files for this node",
        "code: <node_id> path='x' description='y'": "Add code reference to node",
        "invariants: <node_id>": "Hard constraints for node",
        "tests: <node_id>": "Linked TestCase nodes",
        "tests: <node_id> status='FAILING'": "Filter tests by status",
        "related: <node_id>": "Neighbor nodes summary",
        "related: <node_id> mode=summary": "Lightweight neighbors",
        "related: <node_id> direction='outgoing'": "Only outgoing neighbors",
        "template: Flow": "Declaration template for Flow node",
        "template:": "All NodeType templates",
        "interview: node:flow_auth": "Interview questions for node relationships",
        "interview: node:x answered='implements,references'": (
            "Continue interview, skip declared edges"
        ),
        "create:<NodeType> name='x' session_id='y'": "Create a new node",
        "create:Node name='x' session_id='y' dry_run=true": "Preview without writing",
        "upsert:Node dedupe_key='name' name='x' session_id='y'": "Create or update by key",
        "stats:": "All action stats (calls, latency, errors)",
        "stats: <action>": "Stats for specific action (e.g. stats: find)",
        "stats: reset": "Reset all stat counters",
        "update: id='x' name='y' session_id='z'": "Update existing node",
        "lock:Decision topic='x' what='y' why='z'": "Lock a decision",
        "session:start actor='x' goal='y'": "Start a session",
        "session:start actor='x' goal='y' role='observer'": "Start read-only session",
        "session:start actor='x' goal='y' role='admin'": "Start admin session",
        "session:end outcome='x' handoff='y'": "End a session",
        "edge: node:a --relates_to--> node:b": "Create semantic edge",
        "edge: node:a --implements--> node:b reason='x'": "Create edge with reason",
        "import: path/to/doc.md session_id='x'": "Propose doc import",
        "commit: imp:proposal-id": "Commit approved proposal",
        "validate: <scope>": "Validate graph (all|nodes|edges)",
        "dedupe: edges": "Remove duplicate edges from file storage",
        "recompute: priorities session_id='x'": "Recompute all node priorities from graph",
        "recompute: priorities dry_run=true": "Preview priority changes without writing",
        "recompute: priorities type=Flow session_id='x'": "Recompute only Flow nodes",
        "extract: lessons": "Extract lesson candidates",
    },
    "tip": "Always start with overview: to see project state",
}
