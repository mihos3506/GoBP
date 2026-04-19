# ◈ GoBP INSTALL

**Snapshot (2026-04):** Schema **v2** (**93** node types in packaged YAML), single MCP tool **`gobp`**, file-first **`.gobp/`** + optional **`GOBP_DB_URL`**. Index of all docs: **`docs/README.md`**.

## Requirements

```
Python 3.10+
PostgreSQL 14+ (optional — file-only mode works without DB)
Git
```

## Install

```bash
git clone https://github.com/mihos3506/GoBP.git
cd GoBP
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -e .
# or: pip install -r requirements.txt
```

**Docs:** same repo — see `docs/SCHEMA.md`, `docs/MCP_TOOLS.md`, `docs/GoBP_AI_USER_GUIDE.md`.

## Init a project

```bash
cd /path/to/your-project

# Init GoBP in project root
python -m gobp.cli init

# Set project identity
python -m gobp.cli project --name "YourProject" --description "What this project does"
```

Creates `.gobp/` folder:
```
your-project/
  .gobp/
    config.yaml       ← project_name, project_id
    nodes/             ← node markdown files
    edges/             ← edge yaml files
    history/           ← session logs
```

## PostgreSQL (optional)

```bash
createdb gobp_yourproject

# Set env
export GOBP_DB_URL="postgresql://user:pass@localhost/gobp_yourproject"
```

Without `GOBP_DB_URL` → file-only mode (`.gobp/` folder).

## Connect MCP — Claude CLI

Add to `~/.claude.json` under `projects."<your-project-path>".mcpServers`:

```json
{
  "gobp": {
    "type": "stdio",
    "command": "/path/to/gobp/venv/bin/python",
    "args": ["-m", "gobp.mcp.server"],
    "env": {
      "GOBP_PROJECT_ROOT": "/path/to/your-project",
      "GOBP_DB_URL": "postgresql://user:pass@localhost/gobp_yourproject"
    }
  }
}
```

Windows paths: use `/` not `\`. Password special chars: URL-encode (`@` → `%40`).

Restart Claude CLI. Verify: `/mcp` → should show `gobp · √ connected`.

## Connect MCP — Cursor

Add to `.cursor/mcp.json` in project root:

```json
{
  "mcpServers": {
    "gobp": {
      "command": "/path/to/gobp/venv/bin/python",
      "args": ["-m", "gobp.mcp.server"],
      "env": {
        "GOBP_PROJECT_ROOT": "/path/to/your-project",
        "GOBP_DB_URL": "postgresql://user:pass@localhost/gobp_yourproject"
      }
    }
  }
}
```

## Connect MCP — Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gobp": {
      "command": "/path/to/gobp/venv/bin/python",
      "args": ["-m", "gobp.mcp.server"],
      "env": {
        "GOBP_PROJECT_ROOT": "/path/to/your-project",
        "GOBP_DB_URL": "postgresql://user:pass@localhost/gobp_yourproject"
      }
    }
  }
}
```

## MCP Generator (visual)

Start viewer → click ⚙ MCP → auto-generates config for all platforms.

```bash
cd /path/to/gobp
python -m gobp.viewer.server --root /path/to/your-project
# Open http://localhost:8080
# Click ⚙ MCP button
```

## Verify

```bash
# In Claude CLI or any MCP client:
gobp(query="overview:")
# Should return project name + node/edge counts
```

## Multiple projects

Each project gets its own MCP server with different `GOBP_PROJECT_ROOT` and `GOBP_DB_URL`:

```json
{
  "gobp-mihos": {
    "env": {
      "GOBP_PROJECT_ROOT": "D:/MIHOS-v1",
      "GOBP_DB_URL": "postgresql://...localhost/gobp_mihos"
    }
  },
  "gobp-other": {
    "env": {
      "GOBP_PROJECT_ROOT": "D:/OtherProject",
      "GOBP_DB_URL": "postgresql://...localhost/gobp_other"
    }
  }
}
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| MCP not in `/mcp` | Check GOBP_PROJECT_ROOT path exists. Restart CLI. |
| Session not found | Copy schema: `cp gobp/schema/core_*.yaml your-project/gobp/schema/` |
| 0 nodes loaded / validate errors | Copy `gobp/schema/core_nodes.yaml` and `core_edges.yaml` from the installed GoBP package into the project’s `gobp/schema/`. Packaged schema: **21** node types, **14** edge kinds (`docs/SCHEMA.md`). |
| Password error | URL-encode special chars: `@` → `%40` |

◈
