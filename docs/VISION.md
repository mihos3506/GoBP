# ◈ GoBP VISION

**File:** `D:\GoBP\docs\VISION.md`
**Version:** v0.1
**Status:** draft, awaiting CEO approval
**Audience:** Any AI agent that will read, write, or extend GoBP
**Must read:** YES — this is the first file any AI touching GoBP should read

**Related docs (same folder):** `SCHEMA.md` (data contract), `MCP_TOOLS.md` / `GoBP_AI_USER_GUIDE.md` (how to call `gobp()`), `GoBP_ARCHITECTURE.md` (system shape).

---

## ONE-LINER

**GoBP là bộ nhớ dài hạn cho AI agents khi làm việc trên 1 project.**

AI có bộ nhớ ngắn hạn (session) và không đầy đủ (mất context khi switch tab). GoBP cung cấp memory layer bên ngoài, structured, queryable qua MCP, shared giữa mọi AI cùng tham gia project.

Human không trực tiếp dùng GoBP. Human nói chuyện với AI. AI dùng GoBP để nhớ.

---

## WHY GoBP EXISTS

GoBP giải quyết 2 nỗi đau thực tế khi solo founder build project với AI team:

### Pain 1 — AI session amnesia

**Triệu chứng:**
- Founder mở Claude tab mới → Claude mất ~50% context từ session trước
- Founder chuyển sang Cursor → Cursor không biết những gì Claude đã decide
- Founder hỏi Qodo về một rule → Qodo không biết rule đó đã được Claude agree với founder 3 session trước
- Mỗi session mới, founder phải spend 15-30 phút re-explain context

**Tổn thất thực tế:**
- Founder time: 15-30 phút × N session/tuần = hàng giờ lãng phí
- Tokens: mỗi AI session đầu tốn ~50-100K tokens để re-establish context từ chat history cũ
- Decisions lost: quyết định từ sáng bị quên vào chiều
- Trust lost: founder mất niềm tin vào "AI nhớ được"

**GoBP giải quyết:**
- AI bất kỳ (Claude/Cursor/Qodo/Claude CLI) mở session mới → query GoBP → lấy được:
  - 3 session gần nhất đã làm gì
  - Decisions đã chốt
  - Ideas đang pending
  - Tools/files đã build
- Load context từ GoBP: < 10 MCP calls, < 5000 tokens, < 10 giây
- Founder không phải re-explain → founder chỉ tiếp tục conversation

### Pain 2 — Context bloat khi dev

**Triệu chứng:**
- Cursor cần code feature register → đọc DOC-07, DOC-13, DOC-15, DOC-22 → ~60K tokens
- 80% content trong đó không liên quan register
- Cursor confused vì quá nhiều info
- Hoặc Cursor grep code → 40K tokens còn lại không chính xác

**Tổn thất thực tế:**
- Context window của Cursor/Claude có giới hạn (200K-1M tokens)
- Mỗi task tốn 30-50% context cho "đọc docs" → còn ít cho actual code + reasoning
- Wave sau token budget cạn → phải summarize → mất chi tiết
- Code quality giảm vì AI không focus

**GoBP giải quyết:**
- Cursor query `context("feat:register")` → GoBP trả về:
  - Core feature info (status, type, description)
  - Applicable invariants (rules MUST follow)
  - Dependencies (what it needs)
  - References đến exact DOC sections khi cần detail
- Response: ~500 tokens thay vì 60K tokens
- Cursor có 99% context window cho code + reasoning
- Nếu Cursor cần detail hơn → follow reference → đọc đúng section → không phải full doc

**Token savings: ~100-120x** cho mỗi context query.

---

## WHAT GoBP IS

GoBP là **framework** để lưu trữ và truy xuất knowledge của 1 project, với các đặc trưng:

### 1. AI-first interface
- Primary API: **MCP server** (Model Context Protocol)
- AI-agnostic: Cursor, Claude CLI, Claude Desktop, Qodo, Windsurf, Cline, Continue.dev, bất kỳ AI nào hỗ trợ MCP
- Không cần SDK riêng cho từng AI — MCP là universal protocol

### 2. Human-free authoring
- Human (CEO/founder) **không edit file GoBP trực tiếp**
- Human nói chuyện với AI bình thường
- AI parse ý founder → gọi MCP tool → GoBP ghi structured data
- AI verify với founder trước commit quan trọng: "Anh vừa nói sẽ dùng OTP email, tôi ghi vào GoBP nhé?"

### 3. Structured knowledge
- Không phải free-form markdown
- Mỗi "đơn vị kiến thức" là 1 node có type + fields defined
- Edges connect nodes với semantic meaning (relates_to, supersedes, implements, etc.)
- Query trả về structured JSON, không phải prose

### 4. File-first storage
- Source of truth: markdown files với YAML front-matter
- MCP server đọc files + build in-memory index
- Lợi ích:
  - Git-friendly (diff, merge, blame)
  - Portable (copy folder = copy project)
  - Debuggable (AI bug → human mở file đọc)
  - AI-agnostic (AI không có MCP vẫn đọc được file)
- Không dùng database external (không MongoDB, không Postgres, không Neo4j)
- Optional SQLite index derived from files for fast queries

### 5. Project-scoped
- Mỗi project có 1 GoBP instance
- Không phải global knowledge base chia sẻ across projects
- MIHOS có GoBP riêng. Project khác có GoBP riêng.
- Founder có thể có N project → N GoBP instance

### 6. Append-only history
- Ideas và decisions có revision history
- Old version không xóa, mark `superseded_by`
- Allow time-travel: "founder đã nói gì về X tuần trước?"
- History log riêng file, append-only, crash-safe

---

## WHAT GoBP IS NOT

Quan trọng để không over-engineer:

### ❌ Not a chatbot interface
GoBP không có UI chat. Founder dùng Claude/Cursor/AI khác làm chat interface. GoBP là backend memory.

### ❌ Not a human note-taking app
GoBP không thay thế Notion, Obsidian, Roam. Founder không mở GoBP để đọc note. GoBP chỉ để AI dùng.

### ❌ Not a replacement for project DOCs
DOCs (formal specification) vẫn tồn tại. GoBP **references** DOCs + break down thành sections + link với features/entities. DOCs là source of detail. GoBP là map + index.

### ❌ Not a production database
GoBP optimize cho small-to-medium project (< 10K nodes, < 30K edges). Không replace Neo4j/Postgres cho big data.

### ❌ Not a code intelligence tool
GoBP không parse code (không phải ast-grep, không phải Language Server). GoBP parse **spec**, **ideas**, **decisions**, **sessions** — human knowledge, không phải code.

### ❌ Not an LLM memory layer (generic)
GoBP scope là 1 project knowledge, không phải conversation memory chung. Không compete với Mem0, Letta, Zep cho generic conversation context. GoBP focus narrow: project memory for building things.

### ❌ Not an enterprise knowledge management system
Không multi-tenant. Không auth/permissions. Không workflow approval. Solo founder + small team at most.

---

## TARGET USERS

### Primary user: AI agents
- Cursor working on code tasks
- Claude CLI verifying specs
- Qodo generating tests
- Claude Desktop (like CTO Chat) orchestrating work
- Any future MCP-compatible AI

### Secondary user: Human (founder)
- Indirect interaction via AI chat
- Occasional direct inspection: open file to debug when AI report "I wrote X to GoBP"
- Git commit/review when preparing release
- Never required to author YAML/markdown by hand

### Not target users
- Non-technical end users of the project (they interact with the product, not GoBP)
- Enterprise teams with existing knowledge infrastructure
- Researchers doing knowledge graph experiments

---

## CORE USE CASES (concrete examples)

### Use case 1 — CEO brain dump mid-conversation

**Scenario:** Founder chat với Claude về feature login.

```
Founder: "Login thì dùng Face ID cho tiện"
Claude: [calls GoBP: idea_add(
    subject="auth:login",
    raw_quote="Login thì dùng Face ID cho tiện",
    interpretation="Founder proposes Face ID as auth method for login",
    maturity="RAW"
  )]
Claude: "Ghi nhận rồi. Lưu ý Face ID phụ thuộc device, có thể không work 
        trên older phones hoặc Android non-biometric. Anh có backup method không?"
Founder: "À đúng rồi. Thôi dùng OTP email đi"
Claude: [calls GoBP: idea_add(
    subject="auth:login",
    raw_quote="Thôi dùng OTP email đi",
    interpretation="Founder changes auth method from Face ID to Email OTP",
    maturity="RAW",
    supersedes_idea="<previous_idea_id>"
  )]
Claude: "OK. Tôi liên kết idea OTP với idea Face ID cũ, mark Face ID là 
        superseded. Chốt luôn là OTP email không anh?"
Founder: "Ừ chốt"
Claude: [calls GoBP: decision_lock(
    topic="auth:login.method",
    what="Email OTP",
    why="Face ID device-dependent, SMS spam in VN",
    alternatives_considered=["Face ID", "SMS OTP", "Magic link"],
    maturity="LOCKED"
  )]
```

**Kết quả:** 4 MCP calls, ~800 tokens. Founder chỉ nói 3 câu. Decision logged, rationale preserved, history linked.

### Use case 2 — Cursor starting task

**Scenario:** Cursor nhận task "build login screen".

```
Cursor: [calls GoBP: find(query="login")]
→ Returns: [{id: "feat:login", type: "Feature", name: "Login"}, 
           {id: "flow:F2", type: "Flow", name: "Login Flow"}]

Cursor: [calls GoBP: context(node_id="feat:login")]
→ Returns: {
    node: {id, type, name, status, description},
    invariants: ["inv:trust_never_exposed", "inv:jwt_token_versioned"],
    decisions: [{topic: "auth:login.method", what: "Email OTP", locked: true}],
    references: ["doc:DOC-07#F2", "doc:DOC-15#login_api"],
    dependencies: ["eng:auth", "eng:email_otp"],
    related_tools: ["tool:email_sender", "tool:jwt_signer"]
  }
  
Cursor: [calls GoBP: decisions_for(node_id="feat:login")]
→ Returns: [
    {topic: "auth:login.method", what: "Email OTP", why: "..."},
    {topic: "auth:login.rate_limit", what: "5/min/IP", why: "..."},
    {topic: "auth:login.token_expiry", what: "24h", why: "..."}
  ]
```

**Kết quả:** 3 MCP calls, ~1500 tokens total. Cursor biết:
- Build cái gì (Login feature)
- Rules phải follow (invariants)
- Đã chốt gì (decisions với rationale)
- Dependencies (engines, tools)
- Nếu cần detail → read specific DOC sections

Without GoBP: Cursor phải đọc DOC-07, DOC-15, DOC-02 → ~40K tokens.
With GoBP: 1500 tokens.

**Savings: ~27x for this task.**

### Use case 3 — New AI session onboarding

**Scenario:** New Claude Desktop tab, founder says "tiếp tục từ hôm qua".

```
Claude: [Protocol 0 - mandatory skill v3 queries]
  [calls GoBP: session_recent(n=3)]
  → Returns: [
      {date: 2026-04-14, goal: "GoBP vision docs", 
       outcome: "shipped VISION.md draft", pending: ["ARCHITECTURE.md"]},
      {date: 2026-04-13, goal: "MCP server inventory", outcome: "..."},
      ...
    ]
    
  [calls GoBP: pending_decisions()]
  → Returns: [
      {topic: "folder structure", options: ["flat", "nested"], awaiting_ceo: true},
      ...
    ]
    
  [calls GoBP: recent_ideas(since=last_session_end)]
  → Returns: latest ideas from yesterday
```

Claude bây giờ có state đầy đủ từ session trước. Founder chỉ cần nói "tiếp tục" → Claude biết exactly where to continue.

**Without GoBP:** Founder phải paste lại context, explain lại decisions, ~2000 tokens + 10 phút conversation.
**With GoBP:** 3 MCP calls, ~1000 tokens, 30 giây.

---

## KEY PRINCIPLES (non-negotiable)

### P1 — AI writes, human speaks
Human không edit GoBP files. Human chỉ chat. AI parse → write. Nếu founder insist phải edit file bằng tay, đó là failure of design — revisit.

### P2 — MCP is the primary API
Mọi operation production qua MCP. CLI tools chỉ cho debugging, maintenance, bootstrap. Nếu feature không có MCP tool, feature không tồn tại cho AI.

### P3 — File is the source of truth
MCP server đọc files. Database/index là derived. Mất index → rebuild từ files. Mất files → mất project knowledge.

### P4 — Minimal token output
Tool responses ưu tiên < 500 tokens. Detail mode chỉ khi explicitly requested. AI không query GoBP để nhận back full doc dump.

### P5 — Append-only, never overwrite
History log + decision history + idea revisions. Nothing deleted. Use `superseded_by` / `deprecated_by` edges.

### P6 — Verify before commit (cho important writes)
AI phải verify với human trước khi `decision_lock()`. Idea draft thì auto-write. Decision lock thì confirm.

### P7 — Domain-agnostic core
Core schema không biết về MIHOS, không biết về bất kỳ project nào. Extensions per project qua schema extension files.

### P8 — Query before act
AI phải query GoBP để check existence trước khi create. Nguyên tắc "Discovery > Creation" inherited từ MIHOS workflow v2 lessons.

---

## SUCCESS CRITERIA

GoBP v1 thành công khi:

### Technical
- [ ] AI mới mở session load full context trong < 10 MCP calls, < 5K tokens
- [ ] Context query cho 1 feature trả về < 500 tokens (target: 200-400)
- [ ] Import 31 DOCs của MIHOS vào GoBP trong < 10 phút
- [ ] Schema validation catch invalid node/edge 100%
- [ ] History log append-only verified
- [ ] 3+ AI agents cùng đọc GoBP không conflict

### Experience
- [ ] Founder không edit file GoBP bằng tay trong suốt session
- [ ] Founder verify AI write đúng ý (via verification prompts)
- [ ] New Claude tab đầu session biết "đang làm gì" trong 30 giây
- [ ] Cursor start task với ~500 token context thay vì 40K

### MIHOS applicability
- [ ] MIHOS workflow v2 sử dụng GoBP làm memory layer
- [ ] MIHOS 31 DOCs imported làm Document nodes
- [ ] MIHOS pending Wave 0 split decision được log trong GoBP
- [ ] Founder test flow: "build wave 1 register" → Cursor không hỏi lại context → code correct

---

## CONSTRAINTS

- **Language:** Python 3.10+ (match MCP SDK ecosystem)
- **Dependencies:** stdlib + `mcp` SDK + `pyyaml`. No heavy frameworks.
- **Install size:** < 50MB
- **Cold start:** < 500ms for 1K-node graph
- **Query response:** < 50ms for typical read tools
- **Node count target:** 1K-10K nodes (MIHOS currently 625, will grow)
- **Multi-user:** Single project owner. Multiple AI agents OK.
- **Platform:** Windows, macOS, Linux (Python cross-platform)

---

## OPEN QUESTIONS (to resolve in ARCHITECTURE.md)

1. Exact node types — 6 enough? Do we need more?
2. Exact edge types — 5 enough?
3. File layout inside GoBP project folder
4. How MCP server starts/stops (daemon? per-session? lazy?)
5. Conflict resolution when multiple AI write simultaneously
6. Import mechanism for existing DOCs — how automated vs manual
7. Backup/restore strategy
8. Schema migration pattern (v1 → v2)

These are NOT decided in VISION. They are decided in ARCHITECTURE.md next.

---

## REFERENCES

- MIHOS CTO Session Journals (2026-04-12 to 2026-04-14) — origin of Pain discovery
- MIHOS workflow v2 governance docs — pattern to inherit
- MCP Protocol specification — https://modelcontextprotocol.io
- Existing mcp_server.py M1 from MIHOS project — reference implementation seed

---

*Written: 2026-04-14*
*Author: CTO Chat (Claude Opus 4.6) with CEO*
*Status: v0.1 draft, awaiting CEO review*
*Next: ARCHITECTURE.md (after VISION approved)*

◈
