"""GoBP MCP Server.

Exposes GoBP graph data to MCP-capable AI clients (Cursor, Claude Desktop,
Claude CLI, Continue, etc.) via standard MCP protocol over stdio.

Server loads .gobp/ data on startup and serves read tools. Write tools
are added in Wave 5.

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
from pathlib import Path
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from gobp.core.graph import GraphIndex


logger = logging.getLogger("gobp.mcp.server")


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


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Register single gobp() tool."""
    return [
        types.Tool(
            name="gobp",
            description=(
                "GoBP knowledge graph — create, query, and manage project knowledge. "
                "Pass a structured query: '<action>:<NodeType> <key>=\\'<value>\\' ...'. "
                "Call gobp(query='overview:') first to see all actions and project state."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Structured query. Format: '<action>:<type> <key>=\\'<value>\\''. "
                            "Examples: 'overview:' | 'find: login' | 'find:Decision auth' | "
                            "'create:Idea name=\\'x\\' session_id=\\'y\\'' | "
                            "'lock:Decision topic=\\'x\\' what=\\'y\\' why=\\'z\\'' | "
                            "'session:start actor=\\'x\\' goal=\\'y\\'' | "
                            "'validate: nodes' | 'extract: lessons'"
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
        result = {"ok": False, "error": f"Unknown tool: {name}. Use gobp()."}
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    # Lazy load index
    if _index is None or _project_root is None:
        _project_root = _get_project_root()
        _index = _load_index(_project_root)

    query = arguments.get("query", "overview:")

    try:
        from gobp.mcp.dispatcher import dispatch, parse_query

        result = await dispatch(query, _index, _project_root)

        # Reload index after write operations
        action, _, _ = parse_query(query)
        if action in ("create", "update", "lock", "session", "commit"):
            _index = _load_index(_project_root)
            # Invalidate cache
            try:
                from gobp.core.cache import get_cache

                get_cache().invalidate_all()
            except Exception:
                pass
    except Exception as e:
        result = {
            "ok": False,
            "error": str(e),
            "hint": "Call gobp(query='overview:') to see available actions",
        }

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
