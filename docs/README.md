# GoBP documentation index

Use this folder together with the repo root charter (`CHARTER.md`, `CLAUDE.md`).

## Current runtime snapshot

| Topic | Source of truth |
|--------|-----------------|
| **MCP wire API** | Single tool `gobp` + `query` string (protocol v2) — [`MCP_TOOLS.md`](./MCP_TOOLS.md), implementation `gobp/mcp/server.py`, `gobp/mcp/parser.py` (`PROTOCOL_GUIDE`). |
| **Node / edge types** | 21 core node types, 14 core edge types — [`SCHEMA.md`](./SCHEMA.md), YAML `gobp/schema/core_nodes.yaml`, `gobp/schema/core_edges.yaml`. |
| **Project schema version** | Integer in `.gobp/config.yaml` — baseline **2** (`gobp.core.init.INIT_SCHEMA_VERSION`). |

## Reading order (new contributors)

1. [`VISION.md`](./VISION.md) — intent  
2. [`ARCHITECTURE.md`](./ARCHITECTURE.md) — deltas + pointers (see “Current runtime” box at top)  
3. [`SCHEMA.md`](./SCHEMA.md) — graph model  
4. [`MCP_TOOLS.md`](./MCP_TOOLS.md) — `gobp()` contract (read §0 and the **gobp() - Primary Interface** section first)  
5. [`INPUT_MODEL.md`](./INPUT_MODEL.md) / [`IMPORT_MODEL.md`](./IMPORT_MODEL.md) — how knowledge enters the graph  

[`GoBP_AI_USER_GUIDE.md`](./GoBP_AI_USER_GUIDE.md) is a shorter operator-facing summary for AI clients.

## Legacy vs v2

Older sections that list many MCP tool names (`find`, `gobp_overview`, …) describe **capabilities** that are now invoked only through **`gobp(query="…")`**. Prefer the v2 sections at the top of `MCP_TOOLS.md` when implementing or testing clients.
