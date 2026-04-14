# ◈ GoBP — Graph of Brainstorm Project

**GoBP là bộ nhớ dài hạn cho AI agents khi làm việc trên 1 project.**

---

## Vấn đề

Khi solo founder build project với AI team:

1. **AI quên:** Mỗi session mới, AI mất 40-50% context. Founder phải explain lại mỗi lần.
2. **Context bloat:** AI đọc hàng loạt docs để hiểu 1 feature, tốn 60K tokens cho việc nên chỉ tốn 500.
3. **Ideas drift:** Ý tưởng nói với AI session này, session sau bị quên, sản phẩm ra không đúng ý gốc.
4. **Knowledge silos:** Mỗi AI (Claude, Cursor, Qodo) có memory riêng, không share được.

## Giải pháp

GoBP là một knowledge store shared giữa mọi AI agents trong project:

- **File-first:** Markdown + YAML, git-friendly, human-readable
- **MCP-based:** Bất kỳ AI nào hỗ trợ MCP đều đọc/ghi được
- **Human-free authoring:** Founder chỉ chat với AI, AI tự ghi vào GoBP
- **Structured:** 6 node types + 5 edge types, validated schema

## Ai dùng GoBP?

**Primary:** AI agents (Cursor, Claude CLI, Claude Desktop, Qodo, bất kỳ MCP client nào)

**Secondary:** Human (founder) — chỉ gián tiếp qua AI chat, không edit file

## Ai xây GoBP?

GoBP được build vì nỗi đau thực tế của founder MIHOS (solo non-dev founder, 2026). Không phải product commercial. Open folder `D:\GoBP\`, code theo docs, ship khi đủ dùng.

---

## 🗂️ Documentation Navigation

GoBP có 7 foundational docs. Đọc theo thứ tự nếu bạn là AI mới:

### 1. [CHARTER.md](./CHARTER.md) — Why this exists
- 4 pains GoBP giải quyết
- Scope (in/out)
- Principles (8 locked)
- Risks
- Build approach (Cách B: internal-first)

### 2. [VISION.md](./docs/VISION.md) — What GoBP is, in detail
- One-liner definition
- 2 use cases với token numbers cụ thể
- What GoBP IS (6 đặc trưng)
- What GoBP IS NOT (7 điều avoid)
- 8 core principles non-negotiable
- Success criteria

### 3. [ARCHITECTURE.md](./docs/ARCHITECTURE.md) — How it's built
- System overview (4 layers)
- 6 node types với full YAML examples
- 5 edge types
- File structure `.gobp/` pattern
- MCP server design
- Core engine modules (12 Python files)
- Performance targets
- Scaling limits

### 4. [INPUT_MODEL.md](./docs/INPUT_MODEL.md) — How AI captures from conversation
- Core principle: human speaks, AI writes
- 5 capture patterns (brain dump, refinement, confirmation, observation, reference)
- Verification protocol for decisions
- Conversation state tracking
- Multi-AI coordination
- Failure modes to avoid
- System prompt snippet for AI integration

### 5. [IMPORT_MODEL.md](./docs/IMPORT_MODEL.md) — How existing docs become GoBP data
- 3 project states (greenfield, in-progress, legacy)
- 3 import approaches (manual, auto-parser, AI-assisted)
- Proposal flow with examples
- MIHOS import plan (31 DOCs)
- Failure modes in import
- Privacy considerations

### 6. [SCHEMA.md](./docs/SCHEMA.md) — Formal schema definitions
- YAML schema language
- 6 core node type schemas
- 5 core edge type schemas
- Validation rules (hard vs soft)
- Schema extensions (per-project)
- ID conventions
- Versioning

### 7. [MCP_TOOLS.md](./docs/MCP_TOOLS.md) — API contract
- 12 MCP tools specification
- Input/output schemas
- Token budgets
- Error handling
- Tool dependencies
- Protocol 0 checklist
- Performance targets

---

## 🚀 Quick Start

### For AI agents new to GoBP

```
1. Read CHARTER.md (5 min) — understand why
2. Read VISION.md (10 min) — understand what
3. Skim ARCHITECTURE.md sections 1-3 (10 min) — node types + edge types
4. Read INPUT_MODEL.md sections 1-3 (10 min) — capture patterns
5. Read MCP_TOOLS.md section 1 + 9 (5 min) — tool inventory + Protocol 0
6. Start session: call session_log(action=start)
7. Load recent context: call session_recent(n=3)
8. Participate in conversation using capture patterns
```

Total onboarding: ~40 minutes of reading, then ready.

### For Cursor implementing GoBP

```
1. Read CHARTER.md — scope boundaries
2. Read ARCHITECTURE.md full — implementation guidance
3. Read SCHEMA.md full — validation requirements
4. Read MCP_TOOLS.md full — API contract
5. Read IMPORT_MODEL.md if working on import tools
6. Start Wave 0 Brief implementation (CTO Chat provides)
```

### For founder using GoBP through AI

No reading required. Just talk to your AI agent. If your AI has GoBP MCP access, it will:

- Remember past sessions
- Recall decisions you've made
- Preserve your ideas with their original wording
- Reference existing docs without re-reading them
- Work across Claude/Cursor/Qodo/etc. with shared memory

---

## 📐 Core Concepts in 60 Seconds

### Node
A unit of knowledge. Can be a feature, an idea, a decision, a session record, a document pointer, or a lesson.

### Edge
A connection between 2 nodes. 5 types: `relates_to`, `supersedes`, `implements`, `discovered_in`, `references`.

### Layer
GoBP has no layers. Everything is 1 graph. Some node types are "ideas" (brainstorm), some are "knowledge" (locked), some are "memory" (sessions/lessons). They all live together and link to each other.

### Storage
Files in `.gobp/` folder at project root. One markdown file per node, with YAML front-matter. Committed to git like `.git/`.

### API
MCP server exposes 12 tools. AI agents call these tools via JSON-RPC over stdio. Tools are typed, validated, and size-bounded.

### Writes
Human doesn't write. AI writes on human's behalf. Decisions require verification. Ideas are auto-captured from conversation. History is append-only.

---

## 🛠️ Project Status

**Current:** Pre-Wave 0. Foundational docs written. Repo to be initialized. Code not yet started.

**Wave 0 target:** Repo init + schema files + templates + first commit.

**v1 ship target:** 8 waves, 2-3 weeks, functional MCP server + CLI + import for MIHOS test case.

**Milestones:**
- [ ] Wave 0: Repo init, schema, templates
- [ ] Wave 1: Core engine (Python lib)
- [ ] Wave 2: File storage + parser
- [ ] Wave 3: MCP server (read tools)
- [ ] Wave 4: CLI basics
- [ ] Wave 5: MCP server (write tools)
- [ ] Wave 6: CLI advanced
- [ ] Wave 7: Documentation + install
- [ ] Wave 8: MIHOS integration test

---

## 🔌 Integration Examples

### Cursor

Add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["path/to/gobp/mcp/server.py"],
      "env": {
        "GOBP_PROJECT_ROOT": "path/to/your/project"
      }
    }
  }
}
```

### Claude CLI

```bash
claude mcp add gobp -- python path/to/gobp/mcp/server.py
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent:
```json
{
  "mcpServers": {
    "gobp": {
      "command": "python",
      "args": ["path/to/gobp/mcp/server.py"]
    }
  }
}
```

---

## 📖 Design Decisions

Key decisions locked for v1:

| # | Decision | Why |
|---|---|---|
| 1 | File-first, not database | Portability, git-friendly, AI-agnostic |
| 2 | 6 node types, 5 edge types | Minimum viable, extensible |
| 3 | 12 MCP tools | Cover 4 pains without bloat |
| 4 | Python + mcp SDK + pyyaml | Match existing MCP ecosystem |
| 5 | Human doesn't write, AI writes | Remove friction from capture |
| 6 | Append-only history | Prevent knowledge loss |
| 7 | Domain-agnostic core + extensions | Reusable across projects |
| 8 | Single-project scope | Not global knowledge base |
| 9 | Cách B — internal-first, product later | Ship for founder, polish public later |

Details in each doc.

---

## 🧠 Philosophy

GoBP is built on a simple observation:

> The most expensive resource in a solo-founder AI-augmented project is **founder attention**. Every minute spent re-explaining context to AI is a minute not building. GoBP eliminates re-explanation.

Secondary observation:

> AI context windows are cheap but not infinite. Loading 60K tokens of docs to code 1 feature is wasteful. GoBP reduces context cost by 50-100x.

Everything in GoBP serves these two truths.

---

## ❓ FAQ

**Q: Is GoBP a replacement for Notion/Obsidian/Roam?**
A: No. Those are for humans. GoBP is for AI. Humans don't read GoBP directly.

**Q: Does GoBP store code?**
A: No. GoBP stores **spec, ideas, decisions, sessions, lessons**. Code lives in src/. GoBP references code via Document nodes pointing to README files.

**Q: Can I use GoBP with ChatGPT?**
A: Only if ChatGPT has MCP support (as of 2026-04-14, unclear). Otherwise, you need an MCP-capable AI (Claude, Cursor, etc.).

**Q: Is it multi-user?**
A: No, v1 is single-project-owner. Multi-AI OK, multi-human not yet.

**Q: What if I want to edit a node manually?**
A: You can open the markdown file and edit. GoBP will pick up changes. But AI won't know you changed it — you might get conflicts next write. Better to ask AI to make the change for you.

**Q: How do I debug when AI writes wrong info to GoBP?**
A: Open the node file in `.gobp/nodes/`. Read the YAML front-matter. History log in `.gobp/history/` shows who wrote what when.

**Q: Can I export GoBP data?**
A: It's already exported — files are in `.gobp/`. Copy the folder, it's portable.

**Q: What's the license?**
A: Not decided yet. Repo is private or pre-release until founder decides.

---

## 🗺️ Roadmap

**v1 (current):**
- 6 node types
- 5 edge types
- 12 MCP tools
- File-first storage
- SQLite index
- Python + CLI + MCP server
- MIHOS integration

**v2 (maybe, if v1 useful):**
- File watcher for live reload
- Web UI for visualization
- LLM-powered node suggestions
- Plugin system for custom types
- Multi-project support
- Export formats (GraphML, JSON, etc.)

**v3+ (speculative):**
- Multi-user collaboration
- Cloud sync
- Real-time co-editing
- Public knowledge sharing

---

## 📝 License

TBD. See CHARTER.md for current status.

---

## 🙏 Credits

- **MIHOS project** — first real test case, source of pain discovery
- **MCP Protocol** (Anthropic) — the foundation enabling AI-agnostic knowledge access
- **mcp_server.py M1** — reference implementation pattern
- Lessons from MIHOS workflow v2 rebuild sessions (2026-04-12 to 2026-04-14)

---

*GoBP — Graph of Brainstorm Project*
*Built for solo founders who use AI to build things*
*2026-04-14*

◈
