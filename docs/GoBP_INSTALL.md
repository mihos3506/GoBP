# ◈ GoBP — Installation Guide

**Version:** v1.0
**Date:** 2026-04-15
**Time required:** 15-30 minutes

---

## Prerequisites

- Python 3.10 or higher
- Git
- At least one MCP-capable AI client:
  - Claude Desktop
  - Claude Code CLI
  - Cursor IDE
  - Continue.dev / Windsurf

---

## Step 1 — Clone and Install

```bash
git clone https://github.com/mihos3506/GoBP.git
cd GoBP

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install
pip install -e .
```

**Verify:**
```bash
python -c "import gobp; print(gobp.__version__)"
# Expected: 0.1.0

python -m gobp.cli --help
# Expected: GoBP CLI with init/validate/status commands
```

---

## Step 2 — PostgreSQL Setup (Recommended)

GoBP works without PostgreSQL (in-memory only), but PostgreSQL is strongly recommended for any project with 1,000+ nodes.

### Install PostgreSQL

Download from: https://www.postgresql.org/download/

Install with default settings. Remember your `postgres` superuser password.

### Create databases

```bash
# Windows
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE gobp;"

# macOS/Linux
psql -U postgres -c "CREATE DATABASE gobp;"
```

Create one database per project:
```bash
psql -U postgres -c "CREATE DATABASE gobp_myproject;"
```

### Install Python driver

```bash
pip install psycopg2-binary
```

### Configure environment variables

**Windows (PowerShell):**
```powershell
# Encode @ in password as %40
[System.Environment]::SetEnvironmentVariable(
    "GOBP_DB_URL",
    "postgresql://postgres:YOUR%40PASSWORD@localhost/gobp",
    "User"
)
```

**macOS/Linux (.bashrc or .zshrc):**
```bash
export GOBP_DB_URL="postgresql://postgres:YOUR_PASSWORD@localhost/gobp"
```

Restart terminal after setting variables.

**Verify connection:**
```bash
python -c "
from gobp.core.db_config import is_postgres_available
from pathlib import Path
print('PostgreSQL available:', is_postgres_available(Path('.')))
"
# Expected: PostgreSQL available: True
```

---

## Step 3 — Initialize Your Project

Navigate to your project root and run:

```bash
cd /path/to/your-project
python -m gobp.cli init --name "My Project"
```

This creates:
```
your-project/
├── .gobp/
│   ├── config.yaml    ← project config
│   ├── nodes/         ← node markdown files
│   ├── edges/         ← edge YAML files
│   └── history/       ← append-only event log
└── gobp/
    └── schema/
        ├── core_nodes.yaml
        └── core_edges.yaml
```

And seeds 17 universal nodes:
- 16 TestKind nodes (test taxonomy for all projects)
- 1 Concept node (explains test taxonomy to AI)

**Verify:**
```bash
python -m gobp.cli status
# Expected: 17 nodes, schema v2
```

---

## Step 4 — Connect an AI Client

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "gobp": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "gobp.mcp.server"],
      "env": {
        "GOBP_PROJECT_ROOT": "/path/to/your-project",
        "GOBP_DB_URL": "postgresql://postgres:password@localhost/gobp"
      }
    }
  }
}
```

### Claude Code CLI

```bash
claude mcp add gobp -- python -m gobp.mcp.server
```

Set environment:
```bash
export GOBP_PROJECT_ROOT=/path/to/your-project
export GOBP_DB_URL=postgresql://postgres:password@localhost/gobp
```

### Cursor IDE

Create `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "gobp": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "gobp.mcp.server"],
      "cwd": "/path/to/your-project",
      "env": {
        "GOBP_PROJECT_ROOT": "/path/to/your-project",
        "GOBP_DB_URL": "postgresql://postgres:password@localhost/gobp"
      }
    }
  }
}
```

### Multiple projects

Add a separate MCP server entry per project:

```json
{
  "mcpServers": {
    "gobp-project-a": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "gobp.mcp.server"],
      "env": {
        "GOBP_PROJECT_ROOT": "/path/to/project-a",
        "GOBP_DB_URL": "postgresql://postgres:password@localhost/gobp_project_a"
      }
    },
    "gobp-project-b": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "gobp.mcp.server"],
      "env": {
        "GOBP_PROJECT_ROOT": "/path/to/project-b",
        "GOBP_DB_URL": "postgresql://postgres:password@localhost/gobp_project_b"
      }
    }
  }
}
```

---

## Step 5 — First Session

Open a new AI chat with GoBP connected. Run:

```
gobp(query="overview:")
```

You should see:
- Project name and stats
- Current node count (17 seed nodes)
- Interface guide with all 22 available actions

**Start your first session:**
```
gobp(query="session:start actor='claude' goal='Initial project setup'")
```

**Create your first node:**
```
gobp(query="create:Node name='My First Feature' priority='high' session_id='<id from above>'")
```

---

## Step 6 — Import Existing Documentation (Optional)

If you have existing project docs:

```
gobp(query="import: docs/my-spec.md session_id='<session_id>'")
```

GoBP will:
1. Create a Document node tracking the file
2. Auto-classify priority (critical/high/medium/low) from content
3. Return a suggestion for extracting key nodes

---

## CLI Reference

```bash
# Initialize project
python -m gobp.cli init [--name NAME] [--force]

# Show project status
python -m gobp.cli status

# Validate graph
python -m gobp.cli validate [--scope all|nodes|edges|references]

# Rebuild PostgreSQL index
python -m gobp.cli validate --reindex
```

---

## Troubleshooting

### "SameFileError" during init in GoBP repo
If you run `gobp init` inside the GoBP repo itself, schema copy is skipped automatically. This is expected behavior.

### PostgreSQL connection fails
1. Verify PostgreSQL service is running
2. Check password encoding — `@` in password must be `%40` in URL
3. Restart terminal after setting environment variables
4. Test connection: `python -c "from gobp.core.db_config import is_postgres_available; from pathlib import Path; print(is_postgres_available(Path('.')))"`

### Only 5 tools visible in Claude.ai web
This is expected — Claude.ai limits visible tools per MCP server. GoBP's single `gobp()` tool provides all 22 capabilities via structured query protocol. You are not missing any functionality.

### Session ID looks truncated
Session IDs are always exactly 28 characters: `session:YYYY-MM-DD_XXXXXXXXX`. If you see shorter IDs, you may be on an older version — update GoBP.

---

## Upgrading

```bash
cd /path/to/GoBP
git pull origin main
pip install -e .

# Rebuild PostgreSQL index after upgrade
python -m gobp.cli validate --reindex
```

---

## Uninstalling

```bash
# Remove GoBP data from a project
rm -rf /path/to/your-project/.gobp
rm -rf /path/to/your-project/gobp/schema

# Uninstall Python package
pip uninstall gobp

# Drop PostgreSQL database (optional)
psql -U postgres -c "DROP DATABASE gobp_myproject;"
```

---

*◈ GoBP — Installation complete. Start with `gobp(query="overview:")`*
