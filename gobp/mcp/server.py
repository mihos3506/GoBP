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
import inspect
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
from gobp.mcp.tools import advanced as tools_advanced
from gobp.mcp.tools import import_ as tools_import
from gobp.mcp.tools import maintain as tools_maintain
from gobp.mcp.tools import read as tools_read
from gobp.mcp.tools import write as tools_write


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


# Tools that mutate the graph and require an index reload on success.
_WRITE_TOOLS: frozenset[str] = frozenset(
    {"node_upsert", "decision_lock", "session_log", "import_commit"}
)

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
        types.Tool(
            name="node_upsert",
            description="Create or update a node. Requires active session_id. Handles rename via supersedes pattern.",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "fields": {"type": "object"},
                    "session_id": {"type": "string"},
                },
                "required": ["type", "name", "fields", "session_id"],
            },
        ),
        types.Tool(
            name="decision_lock",
            description="Lock a decision with full verification. AI MUST verify with founder before calling.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "what": {"type": "string"},
                    "why": {"type": "string"},
                    "alternatives_considered": {"type": "array"},
                    "risks": {"type": "array"},
                    "related_ideas": {"type": "array"},
                    "session_id": {"type": "string"},
                    "locked_by": {"type": "array"},
                },
                "required": ["topic", "what", "why", "session_id", "locked_by"],
            },
        ),
        types.Tool(
            name="session_log",
            description="Start, update, or end a session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["start", "update", "end"]},
                    "session_id": {"type": "string"},
                    "actor": {"type": "string"},
                    "goal": {"type": "string"},
                    "outcome": {"type": "string"},
                    "pending": {"type": "array"},
                    "nodes_touched": {"type": "array"},
                    "decisions_locked": {"type": "array"},
                    "handoff_notes": {"type": "string"},
                },
                "required": ["action"],
            },
        ),
        types.Tool(
            name="import_proposal",
            description="AI proposes a batch import from an existing file. Founder reviews before commit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_path": {"type": "string"},
                    "proposal_type": {"type": "string", "enum": ["doc", "code", "spec"]},
                    "ai_notes": {"type": "string"},
                    "proposed_document": {"type": "object"},
                    "proposed_nodes": {"type": "array"},
                    "proposed_edges": {"type": "array"},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                    "session_id": {"type": "string"},
                },
                "required": [
                    "source_path",
                    "proposal_type",
                    "ai_notes",
                    "proposed_nodes",
                    "proposed_edges",
                    "confidence",
                    "session_id",
                ],
            },
        ),
        types.Tool(
            name="import_commit",
            description="Commit an approved import proposal atomically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "proposal_id": {"type": "string"},
                    "accept": {"type": "string", "enum": ["all", "partial", "reject"]},
                    "accepted_node_ids": {"type": "array"},
                    "accepted_edge_ids": {"type": "array"},
                    "overrides": {"type": "object"},
                    "session_id": {"type": "string"},
                },
                "required": ["proposal_id", "accept", "session_id"],
            },
        ),
        types.Tool(
            name="validate",
            description="Run full schema and constraint check on the entire graph.",
            inputSchema={
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["all", "nodes", "edges", "references"],
                        "default": "all",
                    },
                    "severity_filter": {
                        "type": "string",
                        "enum": ["all", "hard", "warning"],
                        "default": "all",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="lessons_extract",
            description=(
                "Scan project graph and session history for lesson candidates. "
                "Identifies 4 patterns: failed sessions (P1), recurring uncertainty (P2), "
                "premature decisions (P3), orphan nodes (P4). "
                "Returns proposals only — does not create Lesson nodes. "
                "Use node_upsert to create confirmed lessons."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "max_candidates": {
                        "type": "integer",
                        "default": 20,
                        "description": "Max candidates to return (hard cap: 50)",
                    },
                    "patterns": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
                        "default": ["P1", "P2", "P3", "P4"],
                        "description": "Which patterns to scan (default: all)",
                    },
                },
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Route incoming tool calls to the appropriate handler module."""
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
        "node_upsert": tools_write.node_upsert,
        "decision_lock": tools_write.decision_lock,
        "session_log": tools_write.session_log,
        "import_proposal": tools_import.import_proposal,
        "import_commit": tools_import.import_commit,
        "validate": tools_maintain.validate,
        "lessons_extract": tools_advanced.lessons_extract,
    }

    handler = dispatch.get(name)
    if not handler:
        result = {"ok": False, "error": f"Unknown tool: {name}"}
    else:
        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(_index, _project_root, arguments)
            else:
                result = handler(_index, _project_root, arguments)
            if name in _WRITE_TOOLS and isinstance(result, dict) and result.get("ok"):
                _index = _load_index(_project_root)
                logger.info(f"Index reloaded after {name}")
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
