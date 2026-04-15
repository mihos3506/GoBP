# GoBP Installation Guide

## Requirements

- Python 3.10+
- Git
- One of: Cursor IDE, Claude Desktop, Claude CLI

---

## 1. Clone and install

```bash
git clone https://github.com/mihos3506/GoBP.git
cd GoBP
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -e .
```

Verify:

```bash
python -c "import gobp; print(gobp.__version__)"
# Expected: 0.1.0
```

---

## 2. Initialize a project

Navigate to your project root and run:

```bash
python -m gobp.cli init
```

This creates a `.gobp/` folder with the required structure:

```
.gobp/
  nodes/       # Node markdown files
  edges/       # Edge YAML files
  history/     # Append-only event log
  archive/     # Pruned nodes (created on first prune)
  config.yaml  # Project config and schema version
```

---

## 3. Connect an MCP client

### Cursor IDE

Create or edit `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["PATH_TO_GOBP/gobp/mcp/server.py"],
      "env": {
        "GOBP_PROJECT_ROOT": "PATH_TO_YOUR_PROJECT"
      }
    }
  }
}
```

Replace `PATH_TO_GOBP` with the full path to your GoBP clone (e.g. `D:/GoBP`).
Replace `PATH_TO_YOUR_PROJECT` with the project you want GoBP to track.

Restart Cursor after saving. GoBP tools will appear in the AI tool panel.

### Claude Desktop

Edit `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["PATH_TO_GOBP/gobp/mcp/server.py"],
      "env": {
        "GOBP_PROJECT_ROOT": "PATH_TO_YOUR_PROJECT"
      }
    }
  }
}
```

Restart Claude Desktop after saving.

### Claude CLI

```bash
claude mcp add gobp -- python PATH_TO_GOBP/gobp/mcp/server.py
```

Set the project root via environment variable before running Claude CLI:

```bash
export GOBP_PROJECT_ROOT=PATH_TO_YOUR_PROJECT  # macOS/Linux
set GOBP_PROJECT_ROOT=PATH_TO_YOUR_PROJECT     # Windows
claude
```

---

## 4. Verify connection

Once your MCP client is connected, ask the AI:

```
Call gobp_overview and tell me what you see.
```

Expected response includes: project name, node count (0 if new), available tools (14).

---

## 5. Available MCP tools (14)

| Tool | Purpose |
|---|---|
| `gobp_overview` | Project orientation — call first |
| `find` | Fuzzy search nodes by keyword |
| `signature` | Minimal summary of a node |
| `context` | Full node + edges + decisions bundle |
| `session_recent` | Latest N sessions |
| `decisions_for` | Locked decisions by topic or node |
| `doc_sections` | Sections of a Document node |
| `node_upsert` | Create or update any node |
| `decision_lock` | Lock a Decision with verification |
| `session_log` | Start / update / end a session |
| `import_proposal` | AI proposes batch import |
| `import_commit` | Commit approved import |
| `validate` | Full schema + constraint check |
| `lessons_extract` | Scan for lesson candidates |

Full specs: `docs/MCP_TOOLS.md`.

---

## 6. Troubleshooting

**`ModuleNotFoundError: No module named 'gobp'`**
→ Activate venv before running: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (macOS/Linux).

**MCP client shows no GoBP tools**
→ Check paths in config have no typos. Use absolute paths (not `~` or relative paths).
→ Restart the MCP client after config change.

**`GOBP_PROJECT_ROOT` not set error**
→ Set the env variable in the MCP client config, not in the shell.

**Schema validation errors on startup**
→ Run `python -m gobp.cli validate` to see what's wrong.
→ Usually caused by manually edited node files with missing required fields.

## PostgreSQL Setup (Recommended for scale)

GoBP uses PostgreSQL as persistent index for projects with 1,000+ nodes.

### Install PostgreSQL

Download from https://www.postgresql.org/download/windows/
Install version 18.x or later.

### Create databases

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE gobp;"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE gobp_mihos;"
```

### Configure environment

Set environment variables (passwords with @ must use %40):

```powershell
[System.Environment]::SetEnvironmentVariable("GOBP_DB_URL", "postgresql://postgres:YOUR%40PASSWORD@localhost/gobp", "User")
[System.Environment]::SetEnvironmentVariable("GOBP_MIHOS_DB_URL", "postgresql://postgres:YOUR%40PASSWORD@localhost/gobp_mihos", "User")
```

Restart PowerShell after setting variables.

### Install Python driver

```powershell
pip install psycopg2-binary
```

### Verify

```powershell
python -m gobp.cli validate --reindex
```

### Note

If GOBP_DB_URL is not set, GoBP falls back to in-memory index (no persistence between restarts). PostgreSQL is optional but recommended for MIHOS-scale projects.
