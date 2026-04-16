"""GoBP MCP Server.

Exposes GoBP graph data to MCP-capable AI clients (Cursor, Claude Desktop,
Claude CLI, Continue, etc.) via standard MCP protocol over stdio.

Server loads .gobp/ data on startup. Single tool `gobp()` accepts the
query protocol (v2): reads/writes, `version:`, schema governance
(`validate: schema-docs` / `schema-tests` / `metadata`), response tiers
(`find`/`get`/`related` with `mode=summary|brief|full`), `get_batch:`,
`recompute: priorities`, `template:` / `interview:`,
and optional `GOBP_READ_ONLY=true` to block writes.

Usage:
    python -m gobp.mcp.server

The server reads GOBP_PROJECT_ROOT environment variable to locate the
project folder. Defaults to current working directory.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time as _time
from collections import defaultdict as _defaultdict
from pathlib import Path
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from gobp.core.graph import GraphIndex


logger = logging.getLogger("gobp.mcp.server")


def _query_truthy(val: Any) -> bool:
    """Coerce query param to bool (same semantics as read tools)."""
    if val is True:
        return True
    if val is False or val is None:
        return False
    return str(val).strip().lower() in ("true", "1", "yes", "on")

_READ_ONLY_ACTIONS: frozenset[str] = frozenset({
    "create", "update", "upsert", "lock",
    "session", "edge", "import", "commit", "batch",
})
_READ_ONLY: bool = os.environ.get("GOBP_READ_ONLY", "").lower() in ("true", "1", "yes")


def _inject_protocol(result: Any) -> Any:
    """Attach protocol version metadata for MCP clients."""
    if isinstance(result, dict):
        result["_protocol"] = "2.0"
    return result


def _get_project_root() -> Path:
    """Determine project root from env var or cwd."""
    env_root = os.environ.get("GOBP_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path.cwd().resolve()


def _load_index(project_root: Path) -> GraphIndex:
    """Load GraphIndex from disk, logging any errors."""
    logger.info(f"Loading GoBP index from {project_root}")
    index = GraphIndex.load_from_disk(project_root)
    if index.load_errors:
        logger.warning(f"Load errors encountered: {len(index.load_errors)} files")
        for err in index.load_errors[:5]:
            logger.warning(f"  {err}")
    logger.info(f"Index loaded: {len(index)} nodes, {len(index.all_edges())} edges")
    return index


# Global server instance and index (loaded on startup)
server: Server = Server("gobp")
_index: GraphIndex | None = None
_project_root: Path | None = None

# ── In-memory stats ───────────────────────────────────────────────────────────
_stats: dict[str, dict[str, Any]] = _defaultdict(
    lambda: {
        "calls": 0,
        "total_ms": 0.0,
        "errors": 0,
        "last_called": None,
        "recent_queries": [],
    }
)
_stats_session_start: float = _time.time()


def _record_stat(action: str, elapsed_ms: float, error: bool = False, query: str = "") -> None:
    """Record a tool call stat."""
    s = _stats[action]
    s["calls"] += 1
    s["total_ms"] += elapsed_ms
    if error:
        s["errors"] += 1
    s["last_called"] = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
    if query:
        s["recent_queries"] = ([query] + s["recent_queries"])[:5]


def _get_stats_summary(include_recent_queries: bool = False) -> dict[str, Any]:
    """Return stats summary for all actions."""
    result: dict[str, Any] = {}
    total_calls = 0
    for action, s in _stats.items():
        calls = s["calls"]
        total_calls += calls
        avg_ms = round(s["total_ms"] / calls, 1) if calls > 0 else 0
        result[action] = {
            "calls": calls,
            "avg_ms": avg_ms,
            "errors": s["errors"],
            "last_called": s["last_called"],
        }
        if include_recent_queries:
            result[action]["recent_queries"] = s["recent_queries"]
    return {
        "stats": result,
        "session": {
            "started": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime(_stats_session_start)),
            "total_calls": total_calls,
            "uptime_seconds": round(_time.time() - _stats_session_start),
        },
    }


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Register single gobp() tool."""
    return [
        types.Tool(
            name="gobp",
            description=(
                "GoBP knowledge graph (protocol v2) — query and update project knowledge. "
                "Structured query: '<action>:<NodeType> <key>=\\'<value>\\' ...'. "
                "Start with gobp(query='version:') for protocol/schema info or "
                "gobp(query='overview:') for project state. "
                "Response tiers: find/get/related support mode=summary|brief|full; "
                "get_batch: ids='a,b,c' mode=brief; validate: metadata; "
                "recompute: priorities (dry_run=true preview). "
                "Set env GOBP_READ_ONLY=true to block writes (viewer/analyst mode)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Structured query (gobp query protocol v2). "
                            "Format: '<action>:<NodeType> <key>=\\'<value>\\''. "
                            "Discovery: 'version:' | 'overview:' | 'validate: schema-docs' | "
                            "'validate: schema-tests' | 'validate: metadata' | "
                            "'validate: metadata type=Flow' | "
                            "'template:' | 'template: Flow' | "
                            "'interview: node:x' | 'interview: node:x answered=implements,references'. "
                            "Read: 'find: … mode=summary|brief' | "
                            "'get: node:… mode=brief|full' | 'get: node:… brief=true' (slim) | "
                            "'related: node:… mode=summary' | "
                            "'get_batch: ids=\\'node:a,node:b\\' mode=brief' | 'stats:'. "
                            "Overview defaults to slim (no full protocol dump); "
                            "'overview: full_interface=true' for full catalog. "
                            "Write (blocked when GOBP_READ_ONLY=true): "
                            "'session:start actor=\\'…\\' goal=\\'…\\' role=\\'observer|contributor|admin\\'' | "
                            "'create:…' | 'upsert:…' | 'edge: …' | 'import: …' | "
                            "'recompute: priorities session_id=\\'…\\'' (not dry_run). "
                            "Read-only still allows 'recompute: priorities dry_run=true'. "
                            "Other: 'validate: all' | 'extract: lessons'."
                        ),
                    }
                },
                "required": ["query"],
            },
        )
    ]


@server.call_tool()
async def call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent]:
    """Dispatch gobp() query to correct handler."""
    global _index, _project_root

    if name != "gobp":
        result = _inject_protocol({"ok": False, "error": f"Unknown tool: {name}. Use gobp()."})
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    # Lazy load index
    if _index is None or _project_root is None:
        _project_root = _get_project_root()
        _index = _load_index(_project_root)

    query = arguments.get("query", "overview:")

    from gobp.mcp.parser import parse_query

    action, _, params = parse_query(query)

    if _READ_ONLY and action in _READ_ONLY_ACTIONS:
        result = _inject_protocol({
            "ok": False,
            "error": f"Read-only mode: '{action}' is a write action.",
            "hint": "Set GOBP_READ_ONLY=false (or unset) to enable writes.",
            "read_only": True,
            "blocked_action": action,
        })
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    if _READ_ONLY and action == "recompute" and not _query_truthy(params.get("dry_run", False)):
        result = _inject_protocol({
            "ok": False,
            "error": "Read-only mode: 'recompute' without dry_run=true writes nodes.",
            "hint": "Use recompute: priorities dry_run=true to preview, or disable GOBP_READ_ONLY.",
            "read_only": True,
            "blocked_action": action,
        })
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    if action == "stats":
        parts = query.split(":", 1)
        sub = parts[1].strip() if len(parts) > 1 else ""
        if sub == "reset":
            _stats.clear()
            result = _inject_protocol({"ok": True, "message": "Stats reset"})
        elif sub:
            s = _stats.get(
                sub,
                {"calls": 0, "total_ms": 0.0, "errors": 0, "last_called": None, "recent_queries": []},
            )
            calls = s.get("calls", 0)
            result = _inject_protocol({
                "ok": True,
                "action": sub,
                "stats": {
                    "calls": calls,
                    "avg_ms": round(s.get("total_ms", 0.0) / calls, 1) if calls > 0 else 0,
                    "errors": s.get("errors", 0),
                    "last_called": s.get("last_called"),
                    "recent_queries": s.get("recent_queries", []),
                },
            })
        else:
            # Keep stats: lightweight for low-latency polling.
            result = _inject_protocol({"ok": True, **_get_stats_summary(include_recent_queries=False)})
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    start = _time.time()
    error = False
    try:
        from gobp.mcp.dispatcher import dispatch

        result = await dispatch(query, _index, _project_root)
        _inject_protocol(result)
        if not result.get("ok"):
            error = True

        # Reload index after write operations
        reload_writes = action in (
            "create", "update", "upsert", "lock", "session", "commit", "edge", "import",
        )
        reload_recompute = (
            action == "recompute"
            and isinstance(result, dict)
            and result.get("dry_run") is not True
        )
        if reload_writes or reload_recompute:
            _index = _load_index(_project_root)
            # Invalidate cache
            try:
                from gobp.core.cache import get_cache

                get_cache().invalidate_all()
            except Exception:
                pass
    except Exception as e:
        error = True
        result = _inject_protocol({
            "ok": False,
            "error": str(e),
            "hint": "Call gobp(query='overview:') to see available actions",
        })
    finally:
        elapsed = (_time.time() - start) * 1000
        _record_stat(action, elapsed, error, query[:100])

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def main() -> None:
    """MCP server entry point."""
    global _index, _project_root

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    _project_root = _get_project_root()
    _index = _load_index(_project_root)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
