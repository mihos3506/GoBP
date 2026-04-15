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

    # Parse params: key='value' or key=value or bare value
    params: dict[str, Any] = dict(base_params)

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
            if not node_id:
                import uuid as _uuid
                from datetime import datetime, timezone

                type_prefix = _get_type_prefix(node_type)
                short_hash = _uuid.uuid4().hex[:6]
                node_id = f"{type_prefix}:{short_hash}"

            args = {
                "node_id": node_id,
                "type": node_type,
                "name": params.get("name", ""),
                "fields": {k: v for k, v in params.items() if k not in ("name", "type", "session_id")},
                "session_id": params.get("session_id", ""),
            }
            result = tools_write.node_upsert(index, project_root, args)

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

        # -- Import actions ----------------------------------------------------
        elif action == "import":
            source_path = params.get("query") or params.get("source_path", "")
            args = {
                "source_path": source_path,
                "session_id": params.get("session_id", ""),
                "proposal_type": params.get("type", "doc"),
                "ai_notes": params.get("notes", ""),
                "proposed_nodes": [],
                "proposed_edges": [],
                "confidence": params.get("confidence", "medium"),
            }
            result = tools_import.import_proposal(index, project_root, args)

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
        "import: path/to/doc.md session_id='x'": "Propose doc import",
        "commit: imp:proposal-id": "Commit approved proposal",
        "validate: <scope>": "Validate graph (all|nodes|edges)",
        "extract: lessons": "Extract lesson candidates",
    },
    "tip": "Always start with overview: to see project state",
}
