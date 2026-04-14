# ◈ GoBP — GRAPH OF BRAINSTORM PROJECT
## Project Charter v0.2

**Project name:** Graph of Brainstorm Project (GoBP)
**Path:** `D:\GoBP\`
**Git:** standalone repo (to be init)
**Owner:** CEO
**Started:** 2026-04-14
**Supersedes:** BKP_CHARTER.md v0.1
**Predecessor context:** MIHOS workflow v2 rebuild sessions (2026-04-12 → 2026-04-14)

---

## 1. WHY GoBP EXISTS

4 nỗi đau được phát hiện khi CEO build MIHOS cùng AI team:

### Pain 1 — Ideas drift
Ý tưởng CEO nêu ra được AI ghi nhận trong session, nhưng khi build vào document hoặc dev thì cả CEO và AI đều quên đi. Sản phẩm ra không đúng ý gốc. Không có nơi lưu **structured ideas** có thể truy xuất và trace back.

### Pain 2 — AI session amnesia về tools
Mỗi tab mới, AI mất ~40-50% kiến thức về tools đã build, lý do build, cách hoạt động. Journal giúp ~50-60% nhưng phần hồn (rationale, known issues, patterns) mất. Mỗi session mới mất 1-2 giờ học lại.

### Pain 3 — Session log chỉ ghi "phần xác"
Journal markdown ghi "shipped X, Y, Z" nhưng không structure quyết định, bài học, pattern, errors. Knowledge mờ dần, không cộng dồn.

### Pain 4 — AI-specific, không portable
Knowledge hiện chỉ Claude project knowledge truy cập. Cursor, Qodo, Claude CLI, Copilot, Gemini, Aider không share với nhau. CEO phải re-explain cho mỗi AI.

---

## 2. WHAT GoBP IS

GoBP là **framework generic** cho việc lưu trữ, truy vấn, và cập nhật knowledge của bất kỳ project nào. Brainstorm (ideas, decisions, lessons, patterns) được capture thành graph structured, query được bởi mọi AI qua MCP, human qua CLI.

GoBP cung cấp:

1. **Schema** — node types + edge types + validation rules
2. **Storage** — file-first (YAML + Markdown) + optional SQLite index
3. **Core engine** — Python library load, query, mutate knowledge graph
4. **MCP server** — expose knowledge qua Model Context Protocol cho any AI
5. **CLI tools** — command-line cho human + scripts
6. **Templates** — starter cho ideas, decisions, tools, lessons, patterns, sessions
7. **Documentation** — install, configure, extend

**Tên "Graph of Brainstorm":**
- **Graph** — structured relationships, queryable
- **Brainstorm** — capture tất cả forms of thinking (ideas, decisions, lessons, patterns, sessions) không phân biệt "formal vs informal"
- **Project** — scoped to 1 project, không phải global knowledge base

---

## 3. WHAT GoBP IS NOT

- **Not MIHOS-specific.** GoBP không biết về MIHOS. MIHOS sẽ **use** GoBP, không phải ngược lại.
- **Not replacement for project DOCs.** DOCs còn nguyên, GoBP parse DOCs thành graph.
- **Not chat interface.** GoBP không có UI chat. AI agents dùng MCP, humans dùng CLI.
- **Not production database.** Optimize cho project < 10K nodes. Không replace Neo4j/Postgres.
- **Not code intelligence tool.** GoBP parse **spec + brainstorm**, không parse code.

---

## 4. CORE PRINCIPLES

### P1 — File-first, MCP-equal
Source of truth = markdown/YAML files. MCP là cửa tra cứu nhanh, ngang hàng với file access. Mất MCP vẫn đọc được file.

### P2 — Domain-agnostic schema
Core không hardcode MIHOS concepts. Core có generic types (Idea, Decision, Tool, Session, Lesson, Pattern, Document, Concept). Projects extend qua schema extension file.

### P3 — AI-agnostic access
Cursor, Qodo, Claude CLI, Windsurf, Cline, Continue.dev (MCP) + Aider, Copilot (file fallback).

### P4 — Discovery > Creation
GoBP enforces query-before-act. Tool `check_exists(type, name)` phải gọi trước khi create. Match skill v3 Protocol 0.

### P5 — Structured over prose
Ideas, decisions, lessons, patterns với YAML front-matter structured, không free-form.

### P6 — Append-only history
Mọi mutation log vào `history/` append-only. Không delete/overwrite. Allow time-travel queries.

### P7 — Self-hosted
Không external API. Không cần internet. Mọi data + logic local.

### P8 — Lightweight
Core deps: Python stdlib + `mcp` SDK + `pyyaml`. Không heavy frameworks. Install < 50MB.

### P9 — Public quality from Wave 0
Code viết như production. Type hints. Docstrings. Error messages clear. Examples in docs. Không "quick and dirty".

### P10 — API stability mindset
Tool signatures, CLI names, schema structure thiết kế như contracts. Changes sẽ break users ngay từ v0.1.

---

## 5. SCOPE BOUNDARIES

### In-scope (v1)

**Knowledge representation:**
- 8 core node types (Idea, Tool, Decision, Lesson, Pattern, Session, Document, Concept)
- 10 core edge types (relates_to, refines, supersedes, implements, derived_from, discovered_in, matured_into, contradicts, applies_to, references)
- YAML schema definitions
- Validation rules

**Storage:**
- Markdown with YAML front-matter
- Directory structure convention
- Optional SQLite index (derived)
- History log append-only

**Core engine:**
- Python library: load, parse, validate, query, mutate
- Graph index in-memory
- File watcher live reload (optional)

**MCP server:**
- Read: find, signature, context, impact, invariants_for, search, check_exists
- Write: add_node, add_edge, update_node
- Lifecycle: session_start, session_end, promote

**CLI:**
- `gobp init/add/edit/query/validate/rebuild`
- `gobp session start/end`
- `gobp idea add/promote`
- `gobp decision add/supersede`

**Templates:** 8 file templates trong `_templates/`

**Documentation:** README, ARCHITECTURE, SCHEMA, INSTALL, EXTEND, CHANGELOG

### Out-of-scope (v1)

- UI web interface
- Multi-user collaboration
- Authentication/permissions
- Real-time sync
- Cloud storage integration
- Auto-extraction from arbitrary DOCs (v2)
- Visual graph browser (v2)
- LLM-powered suggestions (v2)
- Plugin system (v2)

---

## 6. SUCCESS CRITERIA

GoBP v1 ship successfully when:

### Technical
- [ ] `gobp init` initializes new project với 1 command
- [ ] Can add idea, query, promote → decision via CLI hoặc MCP
- [ ] Session start/log/end/query works
- [ ] MCP server runs với Cursor + Claude CLI confirmed
- [ ] 0 orphans, 0 cycles in implement subgraph (cycles allowed in ideas)
- [ ] Schema validation catches invalid
- [ ] History log append-only verified
- [ ] < 50MB install, < 500ms cold start, < 50ms query response (1K nodes)

### Experience
- [ ] Fresh AI session hiểu GoBP structure trong < 10 MCP calls
- [ ] CEO brain dump idea không cần edit Python
- [ ] CTO Chat propose decision với `gobp decision add` không cần markdown editing
- [ ] Session journal auto-generated from session node

### MIHOS applicability
- [ ] GoBP import MIHOS graph v2.4 as data
- [ ] MIHOS-specific node types extend GoBP core
- [ ] Lessons từ build GoBP applied to MIHOS workflow v2

---

## 7. LESSONS TO EXTRACT FOR MIHOS

GoBP là sandbox. Mỗi decision build GoBP log như **potential lesson for MIHOS**. Sau GoBP v1 ship, CEO + CTO review → decide lesson nào apply.

Expected lessons:

1. **Folder structure conventions**
2. **Schema evolution pattern**
3. **MCP tool naming conventions**
4. **Session log granularity**
5. **Idea lifecycle** (brain dump → matured → implemented)
6. **Decision format** (DEC-NNN with alternatives)
7. **Tool documentation pattern** (auto vs manual)
8. **Test strategy cho MCP server**
9. **CLI UX patterns**
10. **Git hooks vs manual validation**

---

## 8. WORKFLOW — SIMPLER THAN MIHOS V2

GoBP không copy workflow v2. GoBP thử workflow mới đơn giản.

### Roles
- **CEO** — product authority, priorities, Pain validation
- **CTO Chat** — design, brief writing, review, orchestration
- **Cursor** — code implementation
- **Qodo** — test generation
- **Claude CLI** — verification

### Process per task
1. CEO states requirement
2. CTO Chat writes Brief
3. CEO approves
4. Cursor implements
5. Qodo generates tests
6. Claude CLI verifies
7. CTO marks done
8. Session ends với journal auto-generated (via `gobp session end`)

### Wave structure
- Wave 0 — Repo init + schema + templates + license + quality bar
- Wave 1 — Core engine (Python library)
- Wave 2 — File storage + parser
- Wave 3 — MCP server (read tools)
- Wave 4 — CLI (basic)
- Wave 5 — MCP server (write tools)
- Wave 6 — CLI (advanced)
- Wave 7 — Documentation + install guides
- Wave 8 — MIHOS integration test + lessons extraction

8 waves, adjust khi build. Không locked như MIHOS.

### QA standards
- Every public function has test
- MCP tool response < 500 tokens (query tools)
- No hardcoded paths (config-driven)
- Python type hints everywhere
- `gobp validate` passes on every commit

---

## 9. PROPOSED FILE STRUCTURE

```
D:\GoBP\
├── .git/
├── .gitignore
├── README.md
├── CHARTER.md                    ← this file
├── LICENSE                       ← MIT (CEO to confirm)
├── CHANGELOG.md
├── pyproject.toml
├── requirements.txt
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SCHEMA.md
│   ├── INSTALL.md
│   ├── EXTEND.md
│   ├── CONTRIBUTING.md           ← for potential contributors
│   └── lessons_for_mihos.md
│
├── gobp/                         ← Python package
│   ├── __init__.py
│   ├── core/
│   │   ├── graph.py
│   │   ├── loader.py
│   │   ├── validator.py
│   │   └── mutator.py
│   ├── schema/
│   │   ├── nodes.yaml
│   │   ├── edges.yaml
│   │   └── extensions/
│   ├── mcp/
│   │   ├── server.py
│   │   └── tools/
│   │       ├── read.py
│   │       ├── write.py
│   │       └── lifecycle.py
│   ├── cli/
│   │   ├── __main__.py           ← `gobp` command
│   │   ├── commands.py
│   │   └── prompts.py
│   └── templates/
│       ├── idea.md
│       ├── decision.md
│       ├── lesson.md
│       ├── pattern.md
│       ├── tool.md
│       ├── session.md
│       └── document.md
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── examples/
│   └── minimal_project/          ← sample GoBP project data
│       ├── ideas/
│       ├── decisions/
│       └── tools/
│
└── knowledge/                    ← GoBP's own dogfood data
    ├── ideas/
    ├── decisions/
    ├── lessons/
    ├── sessions/
    ├── tools/
    └── history/
```

**Dogfood pattern:** `knowledge/` folder trong GoBP repo sử dụng chính GoBP để track development của GoBP. Validation real-time: nếu GoBP không đủ cho chính nó, không đủ cho MIHOS.

---

## 10. PRODUCT-READINESS DECISIONS

CEO confirmed: GoBP có khả năng thành product nếu build thành công. Approach **Cách B** (internal-first, product-ready later).

### D10.1 — License: MIT (Wave 0 lock)
- Maximum reach
- Low management overhead
- Anyone can use (personal, commercial, modified)
- Can add commercial license later if needed

### D10.2 — Public quality bar from Wave 0 (lock)
- Type hints mandatory
- Docstrings for all public functions
- Clear error messages
- Examples in documentation
- Không "quick and dirty cleanup later"

### D10.3 — API stability mindset (lock)
- Tool signatures as contracts
- CLI command names as contracts
- Schema structure as contracts
- Breaking changes require version bump + migration guide

### D10.4 — Target persona v1: solo dev + solo non-dev founder
- Assume Python + git + terminal comfort (dev persona)
- Docs detailed enough for non-dev founders to follow (CEO persona)
- CLI-driven (works for both)
- Web UI deferred (post-v1)

### D10.5 — Deferred product decisions
- Naming beyond "GoBP" — decide before public release
- Distribution (PyPI, GitHub releases, documentation site) — post-v1
- Monetization (free, donations, paid support, SaaS) — post-v1
- Plugin system — v2 if needed, hardcoded 8 types for v1

---

## 11. RISKS

### R1 — Scope creep
Tempt to add MIHOS-specific. Mitigation: reject if concept only in MIHOS.

### R2 — Over-engineering
Tempt to add enterprise features. Mitigation: 8 node types limit, 10 edge types limit, < 50MB install.

### R3 — MCP SDK drift
`mcp` Python SDK may change. Mitigation: Pin version in requirements.txt.

### R4 — CEO attention split
GoBP + MIHOS both need CEO. Mitigation: GoBP decisions smaller scope, faster turnaround.

### R5 — Lessons not applied to MIHOS
GoBP ship but MIHOS unchanged. Mitigation: explicit review session post-GoBP-v1.

### R6 — Product pressure leads to premature optimization
Building for "thousands of users" when CEO needs internal tool. Mitigation: **Cách B** — internal-first, ship for CEO, validate Pain resolution, then polish for public.

---

## 12. DECISIONS LOCKED

| # | Decision | Rationale |
|---|---|---|
| D1 | Standalone `D:\GoBP\` | Sandbox separate from MIHOS |
| D2 | Scope C — generic framework | Reusable library, not MIHOS-specific |
| D3 | File-first, MCP-equal | CEO architecture vision |
| D4 | Domain-agnostic schema | GoBP doesn't know MIHOS |
| D5 | 8 core node types | Minimum viable, extensible |
| D6 | Python + MCP SDK + pyyaml | Match existing env |
| D7 | Simpler workflow than MIHOS v2 | Experiment, not production |
| D8 | GoBP dogfoods itself | `knowledge/` folder uses GoBP |
| D9 | Name: GoBP (Graph of Brainstorm Project) | CEO chosen 2026-04-14 |
| D10 | Approach Cách B — internal-first, product-ready later | Balance speed + quality |
| D11 | License MIT | Max reach, CEO confirmed direction |
| D12 | Public quality from Wave 0 | Không "cleanup later" |

---

## 13. CURRENT STATUS

- ✅ Charter v0.2 (this file, renamed from BKP)
- ✅ Folder `D:\GoBP\` to be created (CEO can `mv D:\BKP D:\GoBP`)
- ❌ Git repo init
- ❌ LICENSE file
- ❌ Schema definition
- ❌ Core engine
- ❌ MCP server
- ❌ CLI
- ❌ Templates
- ❌ Tests
- ❌ Documentation

---

## 14. NEXT STEPS

1. **CEO reviews Charter v0.2**
2. **CEO confirms remaining uncertainties:**
   - Rename `D:\BKP\` → `D:\GoBP\`? (Yes, assume based on rename)
   - MIT license confirmed?
   - Any changes to Pain list or scope?
3. **CTO Chat writes Wave 0 Brief** — repo init + LICENSE + schema + templates + quality gates
4. **CEO approves Brief**
5. **Cursor implements Wave 0**
6. **Claude CLI verifies**
7. **Wave 0 complete → Wave 1 planning**

Target: 8 waves, 2-3 waves/week, GoBP v1 ship in 3-4 weeks.

---

*Charter v0.2 written 2026-04-14*
*By: CTO Chat (Claude Opus 4.6)*
*For: CEO review before Wave 0*
*Path: D:\GoBP\CHARTER.md*
*Supersedes: BKP_CHARTER.md v0.1*

◈
