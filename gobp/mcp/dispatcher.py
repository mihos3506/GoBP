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


def _get_type_prefix(node_type: str) -> str:
    """Get ID prefix for node type."""
    prefix_map = {
        "Node": "node",
        "Idea": "idea",
        "Decision": "dec",
        "Session": "session",
        "Document": "doc",
        "Lesson": "lesson",
        "Concept": "concept",
        "TestKind": "testkind",
        "TestCase": "tc",
    }
    return prefix_map.get(node_type, "node")


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

def parse_query(query: str) -> tuple[str, str, dict[str, Any]]:
    """Parse query string into (action, node_type, params).

    Format: "<action>:<type> <key>='<value>' ..."
    or:     "<action>: <bare_value>"

    Returns:
        (action, node_type, params)
        action: lowercase action string
        node_type: node type if specified, else ""
        params: dict of key=value pairs, or {"query": bare_value}
    """
    query = query.strip()
    if not query:
        return "overview", "", {}

    # Find action:type separator
    colon_idx = query.find(":")
    if colon_idx == -1:
        # No colon - treat as find query
        return "find", "", {"query": query}

    action_part = query[:colon_idx].strip().lower()
    rest = query[colon_idx + 1 :].strip()

    # Split action and node_type (e.g. "find:Decision" -> action="find", type="Decision")
    action_parts = action_part.split(None, 1)
    action = action_parts[0]
    node_type = action_parts[1] if len(action_parts) > 1 else ""

    if not rest:
        return action, node_type, {}

    # Typed actions: "create:Idea ..." or "lock:Decision ..."
    if action in ("create", "lock") and node_type == "":
        first_token, sep, remainder = rest.partition(" ")
        if first_token and "=" not in first_token:
            node_type = first_token
            rest = remainder if sep else ""
            if not rest:
                return action, node_type, {}

    # Action subcommand shorthand: "session:start actor=x" -> query=start
    if action == "session" and node_type == "" and " " in rest:
        maybe_sub, remainder = rest.split(" ", 1)
        if "=" not in maybe_sub:
            node_type = ""
            rest = remainder
            base_params: dict[str, Any] = {"query": maybe_sub}
        else:
            base_params = {}
    else:
        base_params = {}

    # Typed find shorthand: "find:Decision auth" -> type=Decision, query=auth
    if action == "find" and node_type == "" and " " in rest:
        maybe_type, remainder = rest.split(" ", 1)
        if "=" not in maybe_type:
            node_type = maybe_type
            return action, node_type, {"query": remainder.strip()}

    # Import shorthand: "import: path/to/file.md session_id='x'"
    if action == "import" and node_type == "":
        token_match = re.match(r"^(\S+)\s+(.*)$", rest)
        if token_match and "=" in token_match.group(2):
            params = dict(base_params)
            params["query"] = token_match.group(1)
            extra = token_match.group(2)
            for km in re.finditer(r"(\w+)='([^']*)'|(\w+)=\"([^\"]*)\"|(\w+)=(\S+)", extra):
                if km.group(1) is not None:
                    params[km.group(1)] = km.group(2)
                elif km.group(3) is not None:
                    params[km.group(3)] = km.group(4)
                elif km.group(5) is not None:
                    params[km.group(5)] = km.group(6)
            return action, "", params

    # Parse params: key='value' or key=value or bare value
    params: dict[str, Any] = dict(base_params)

    # Special case: edge: from_id --type--> to_id
    if action == "edge":
        edge_pattern = re.compile(
            r"^([\w:]+)\s+--(\w+)-->\s+([\w:]+)(.*)?$"
        )
        m = edge_pattern.match(rest)
        if m:
            params["from"] = m.group(1).strip()
            params["edge_type"] = m.group(2).strip()
            params["to"] = m.group(3).strip()
            # Parse remaining key=value pairs
            extra = m.group(4).strip() if m.group(4) else ""
            if extra:
                for km in re.finditer(r"(\w+)='([^']*)'|(\w+)=(\S+)", extra):
                    if km.group(1):
                        params[km.group(1)] = km.group(2)
                    elif km.group(3):
                        params[km.group(3)] = km.group(4)
        return action, "", params

    # Try key=value parsing first
    kv_pattern = re.compile(r"(\w+)='([^']*)'|(\w+)=\"([^\"]*)\"|(\w+)=(\S+)")
    matches = list(kv_pattern.finditer(rest))

    if matches:
        for m in matches:
            if m.group(1) is not None:
                params[m.group(1)] = m.group(2)
            elif m.group(3) is not None:
                params[m.group(3)] = m.group(4)
            elif m.group(5) is not None:
                params[m.group(5)] = m.group(6)
    else:
        # No key=value pairs - bare value
        params["query"] = rest

    return action, node_type, params


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
        # -- Read actions ------------------------------------------------------
        if action == "overview":
            result = tools_read.gobp_overview(index, project_root, params)

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
            result = tools_read.find(index, project_root, args)

        elif action in ("get", "context"):
            node_id = params.get("query") or params.get("id") or params.get("node_id", "")
            result = tools_read.context(index, project_root, {"node_id": node_id})

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

        # -- Write actions -----------------------------------------------------
        elif action == "create":
            node_type = node_type or params.pop("type", "Node")

            # Auto-generate ID if not provided
            node_id = params.pop("id", params.pop("node_id", None))
            auto_generated_id = False
            if not node_id:
                import uuid as _uuid

                type_prefix = _get_type_prefix(node_type)
                short_hash = _uuid.uuid4().hex[:6]
                if type_prefix == "node" and short_hash[0].isdigit():
                    short_hash = f"n{short_hash[:5]}"
                node_id = f"{type_prefix}:{short_hash}"
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
            args = {
                "id": node_id,
                "type": node_type or params.pop("type", ""),
                "name": params.get("name", ""),
                "fields": {k: v for k, v in params.items() if k not in ("name", "type")},
                "session_id": params.get("session_id", ""),
            }
            result = tools_write.node_upsert(index, project_root, args)

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
            }
            if "session_id" in params:
                args["session_id"] = params["session_id"]
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
                        create_edge(
                            gobp_root=project_root,
                            edge=edge,
                            schema=edges_schema,
                            actor="gobp-dispatcher",
                            edge_file_name="semantic_edges.yaml",
                        )
                        result = {
                            "ok": True,
                            "edge_created": {
                                "from": from_id,
                                "from_name": from_node.get("name", ""),
                                "type": edge_type,
                                "to": to_id,
                                "to_name": to_node.get("name", ""),
                            }
                        }
                    except Exception as e:
                        result = {"ok": False, "error": str(e)}

        # -- Import actions ----------------------------------------------------
        elif action == "import":
            source_path_str = params.get("query") or params.get("source_path", "")
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

                # Generate Document node ID from filename
                import re as _re
                doc_slug = _re.sub(r"[^a-z0-9_]", "_", source_path.stem.lower())
                doc_id = f"doc:{doc_slug}"

                # Create Document node
                import hashlib as _hashlib
                from datetime import datetime, timezone

                now_iso = datetime.now(timezone.utc).isoformat()
                content_hash = f"sha256:{_hashlib.sha256(content.encode()).hexdigest()}" if content else ""

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

                result = {
                    "ok": upsert_result.get("ok", False),
                    "document_node": doc_id,
                    "document_name": doc_node["name"],
                    "priority": priority,
                    "sections_found": len(sections),
                    "sections": sections[:5],  # show first 5
                    "content_hash": content_hash,
                    "file_exists": source_path.exists(),
                    "suggestion": (
                        f"Document node created. Now extract key concepts:\n"
                        f"  gobp(query=\"create:Node name='...' priority='{priority}' session_id='{session_id}'\")\n"
                        f"Then link with:\n"
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
            result = tools_maintain.validate(
                index, project_root, {"scope": scope, "severity_filter": "all"}
            )

        elif action == "extract":
            result = await lessons_extract(index, project_root, {})

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


# -- Protocol guide (included in gobp_overview response) ----------------------

PROTOCOL_GUIDE = {
    "protocol": "gobp query protocol v1",
    "format": "<action>:<NodeType> <key>='<value>' ...",
    "actions": {
        "overview:": "Project stats and orientation",
        "find: <keyword>": "Search any node by keyword",
        "find:<NodeType> <keyword>": "Search by type + keyword",
        "get: <node_id>": "Full node + edges + decisions",
        "signature: <node_id>": "Minimal node summary",
        "recent: <n>": "Latest N sessions",
        "decisions: <topic>": "Locked decisions for topic",
        "sections: <doc_id>": "Document sections list",
        "create:<NodeType> name='x' session_id='y'": "Create a new node",
        "update: id='x' name='y' session_id='z'": "Update existing node",
        "lock:Decision topic='x' what='y' why='z'": "Lock a decision",
        "session:start actor='x' goal='y'": "Start a session",
        "session:end outcome='x' handoff='y'": "End a session",
        "edge: node:a --relates_to--> node:b": "Create semantic edge",
        "edge: node:a --implements--> node:b reason='x'": "Create edge with reason",
        "import: path/to/doc.md session_id='x'": "Propose doc import",
        "commit: imp:proposal-id": "Commit approved proposal",
        "validate: <scope>": "Validate graph (all|nodes|edges)",
        "extract: lessons": "Extract lesson candidates",
    },
    "tip": "Always start with overview: to see project state",
}
