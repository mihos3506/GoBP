# GoBP MCP Client Configurations

Example configs for connecting MCP-capable AI clients to GoBP.

## Prerequisites

- GoBP installed: `pip install -e .` in a GoBP repo clone
- Python 3.10+ available in PATH
- GOBP_PROJECT_ROOT set to the folder containing `.gobp/` data

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

After connecting, the AI client should be able to call:
- `gobp_overview()` to see project info
- `find(query='...')` to search nodes
- Other read tools listed in `docs/MCP_TOOLS.md`

## Notes

- Per-project isolation: each project needs its own config pointing at its `.gobp/` folder
- Multiple projects: one config per project, each spawns its own MCP server subprocess
- See `docs/ARCHITECTURE.md` multi-project section for details
