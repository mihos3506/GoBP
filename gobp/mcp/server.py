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
from gobp.mcp.tools import read as tools_read


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
    """Return the list of available tools for MCP discovery."""
    return [
        types.Tool(
            name="gobp_overview",
            description="Orientation tool for AI clients. Returns project metadata, stats, main topics, and recent activity. Call this first when connecting.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="find",
            description="Fuzzy search GoBP nodes by id, name, or keyword.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="signature",
            description="Get minimal node summary (id, type, name, status, key fields).",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                },
                "required": ["node_id"],
            },
        ),
        types.Tool(
            name="context",
            description="Get node + outgoing/incoming edges + applicable decisions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "depth": {"type": "integer", "default": 1},
                },
                "required": ["node_id"],
            },
        ),
        types.Tool(
            name="session_recent",
            description="Get the latest N sessions for continuity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "n": {"type": "integer", "default": 3},
                    "before": {"type": "string"},
                    "actor": {"type": "string"},
                },
                "required": [],
            },
        ),
        types.Tool(
            name="decisions_for",
            description="Get locked decisions for a topic or node.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "node_id": {"type": "string"},
                    "status": {"type": "string", "default": "LOCKED"},
                },
                "required": [],
            },
        ),
        types.Tool(
            name="doc_sections",
            description="List sections of a Document node without loading content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string"},
                },
                "required": ["doc_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Route tool calls to handlers in tools_read module."""
    global _index, _project_root

    if _index is None or _project_root is None:
        result = {"ok": False, "error": "GoBP index not loaded"}
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    dispatch = {
        "gobp_overview": tools_read.gobp_overview,
        "find": tools_read.find,
        "signature": tools_read.signature,
        "context": tools_read.context,
        "session_recent": tools_read.session_recent,
        "decisions_for": tools_read.decisions_for,
        "doc_sections": tools_read.doc_sections,
    }

    handler = dispatch.get(name)
    if not handler:
        result = {"ok": False, "error": f"Unknown tool: {name}"}
    else:
        try:
            result = handler(_index, _project_root, arguments)
        except Exception as e:
            logger.exception(f"Tool '{name}' raised exception")
            result = {"ok": False, "error": str(e), "tool": name}

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
