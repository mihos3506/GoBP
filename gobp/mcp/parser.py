"""GoBP query parser.

Parses gobp() query strings into (action, node_type, params).
Separated from dispatcher for clarity and testability.
"""

from __future__ import annotations

import re
from typing import Any

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
    "task": "Task",
    "ctodevhandoff": "CtoDevHandoff",
    "qacodedevhandoff": "QaCodeDevHandoff",
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


# -- Query parser --------------------------------------------------------------

_POSITIONAL_KEY: dict[str, str] = {
    "batch": "query",
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
    quote_char: str | None = None

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

    # ``batch`` payloads embed colons (e.g. ``create: Engine:`` inside ``ops='...'``),
    # so we must not split on the first colon of the whole string.
    if query.lower().startswith("batch"):
        rest = query[5:].strip()
        if rest.startswith(":"):
            rest = rest[1:].strip()
        if not rest:
            return "batch", "", {}
        params: dict[str, Any] = {}
        tokens = _tokenize_rest(rest)
        positional_key = _POSITIONAL_KEY.get("batch", "query")
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
                    params["query"] = value
                positional_consumed = True
        return "batch", "", params

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
        if first_value != "Session" and first_value.casefold() == "session":
            # Keep lowercase "session" as keyword text, not a type filter.
            # This preserves "find: session" search intent while "find:Session" stays explicit.
            pass
        else:
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

    if action in ("suggest", "explore") and tokens:
        bare = [t.strip("'\"") for t in tokens if "=" not in t]
        if bare:
            params["query"] = " ".join(bare)

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

# -- Protocol guide (optional full copy via overview: full_interface=true) -----

QUERY_RULES: dict[str, Any] = {
    "rules": [
        "1. overview: — call ONCE at session start. Never again same session.",
        "2. template: — BEFORE first create of a NodeType, fetch template: ThatType (repeat anytime; not a single-call cap).",
        "3. template_batch: — when creating multiple nodes of same type.",
        "4. suggest: — BEFORE creating any new node. Check reusable nodes.",
        "5. explore: — instead of find+get+related. Use compact=true for quick check.",
        "6. batch — for ALL write operations. Never single create:/update:/edge:.",
        "7. find/get — default mode=summary. Only mode=full when debugging.",
        "8. After getting IDs — keep only id+name in next prompt. No full JSON.",
        "9. 1 session = 1 goal. session:end when done.",
        "10. Errors — if batch returns errors, fix and retry ONLY failed ops.",
    ],
    "token_guide": {
        "explore compact": "~200 tokens",
        "explore full": "~800 tokens",
        "find mode=summary": "~400 tokens for 20 results",
        "find mode=full": "~2000 tokens for 20 results",
        "batch response": "~100 tokens (summary only)",
        "batch verbose": "~500+ tokens (full details)",
        "template": "~300 tokens",
        "suggest": "~400 tokens for 10 suggestions",
    },
}

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
        "explore: TrustGate": "Best-matching node + edges + also_found in one call (skips discovered_in)",
        "explore: Mi Hốt": "Vietnamese-aware search + neighborhood context in one call",
        "suggest: Payment Flow": "Keyword overlap — surfaces existing engines/entities to reuse",
        "suggest: auth login": "Finds related nodes from short context text",
        "batch session_id='x' ops='create: Engine: A | desc\\nedge+: A --implements--> B'": (
            "Unified batch: create/update/delete/retype/merge/edge ops (max 500 ops per call)"
        ),
        "template: Engine": "Input frame for Engine type (required/optional fields from schema)",
        "template: Flow": "Input frame for Flow type (required/optional fields from schema)",
        "template: Entity": "Input frame for Entity type",
        "template:": "Catalog of node types; use template: <Type> for schema-driven input frame",
        "template_batch: Engine count=5": (
            "Fillable batch template for 5 engines with edge suggestions"
        ),
        "template_batch: Flow": (
            "Fillable batch template for flows (default count=3)"
        ),
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
        "edge: engine_a --depends_on--> engine_b": "Engine dependency",
        "edge: flow_a --tested_by--> testcase_b": "Flow test coverage",
        "edge: testcase_a --covers--> flow_b": "TestCase coverage",
        "import: path/to/doc.md session_id='x'": "Propose doc import",
        "commit: imp:proposal-id": "Commit approved proposal",
        "validate: <scope>": "Validate graph (all|nodes|edges)",
        "dedupe: edges": "Remove duplicate edges from file storage",
        "recompute: priorities session_id='x'": "Recompute all node priorities from graph",
        "recompute: priorities dry_run=true": "Preview priority changes without writing",
        "recompute: priorities type=Flow session_id='x'": "Recompute only Flow nodes",
        "extract: lessons": "Extract lesson candidates",
        "delete: {node_id} session_id='x'": "Delete node + edges",
        "retype: id='{id}' new_type='Engine' session_id='x'": (
            "Change node type (delete + recreate with correct ID)"
        ),
        "tasks:": "Pending tasks for cursor",
        "tasks: assignee='haiku'": "Pending tasks for haiku",
        "tasks: status='ALL'": "All tasks",
        "create:Task name='...' assignee='cursor' wave='8B' brief_path='waves/...' session_id='x'": (
            "Create task"
        ),
    },
    "tip": "Always start with overview: to see project state",
    "query_rules": QUERY_RULES["rules"],
    "token_guide": QUERY_RULES["token_guide"],
}
