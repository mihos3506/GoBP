# GoBP MCP Client Configurations

Example configs for connecting MCP-capable AI clients to GoBP.

## Prerequisites

- GoBP installed: `pip install -e .` in a GoBP repo clone
- Python 3.10+ available in PATH
- `GOBP_PROJECT_ROOT` set to the folder containing `.gobp/` data (see `env` in each JSON example)

### Optional environment (Wave 14+)

- **`GOBP_READ_ONLY`** — examples set `"false"` (writes allowed). Set to `"true"` to block writes (`create`, `session`, `edge`, …); reads still work. Use for viewer/audit agents.
- **`GOBP_DB_URL`** — only if you use the optional PostgreSQL cache layer; not required for file-based `.gobp/`. Omit from `env` unless you need it.

## Cursor IDE

Copy `cursor_mcp.json` to `.cursor/mcp.json` in your project folder.
Edit `cwd` and `GOBP_PROJECT_ROOT` to match your project path.
Restart Cursor.

## Claude Desktop

Copy `claude_desktop_config.json` content into:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Edit `GOBP_PROJECT_ROOT` to your project path. Restart Claude Desktop.

## Claude Code CLI

Copy `claude_cli_config.json` content into your Claude CLI config file
(usually `.claude.json` in project or home directory).

## Continue.dev

Copy `continue_config.json` content into `~/.continue/config.json`
(merge with existing mcpServers section).

## Verification

After connecting, the client exposes a single tool **`gobp`** with a `query` string. Try:

- `gobp(query="version:")` — protocol v2, schema version, changelog
- `gobp(query="overview:")` — project stats and full action list
- `gobp(query="find: login")` — search nodes

Full syntax and actions: **`docs/MCP_TOOLS.md`**.

## Notes

- Per-project isolation: each project needs its own config pointing at its `.gobp/` folder
- Multiple projects: one config per project, each spawns its own MCP server subprocess
- See `docs/ARCHITECTURE.md` multi-project section for details
