# ◈ GoBP INPUT MODEL

**File:** `D:\GoBP\docs\INPUT_MODEL.md`
**Version:** v0.1
**Status:** draft, awaiting CEO approval
**Depends on:** VISION.md, ARCHITECTURE.md, SCHEMA.md (must read first)
**Audience:** AI agents that capture knowledge from conversation with human

**MCP entrypoint (v2):** the server exposes a single tool, `gobp`, with a structured `query` string (`overview:`, `find:…`, `create:…`, `batch …`, …). Prose below sometimes uses legacy names (`find()`, `node_upsert()`, `session_log`) for readability; implement them as the corresponding `gobp(query="…")` actions (see `docs/MCP_TOOLS.md`).

---

## 0. CORE PRINCIPLE

**Human speaks. AI writes. GoBP stores.**

Human (founder/CEO) never edits GoBP files directly. Human talks to an AI (Claude Desktop, Cursor, Claude CLI, Qodo, any MCP-compatible AI). AI listens, interprets, and writes structured data to GoBP via MCP tools.

This is the opposite of traditional knowledge management:
- **Traditional:** Human organizes → writes markdown → tool reads
- **GoBP:** Human speaks → AI organizes → AI writes structured → AI reads back

The responsibility for structure is on the AI, not the human. Human only has to think clearly and speak.

---

## 1. WHY THIS MATTERS

### 1.1 Friction kills knowledge capture

If founder has to stop and think "which template? which folder? which format?", they will not capture the idea. They will keep it in their head, forget it, and be upset when the implementation doesn't match what they meant.

Every friction point between "thought" and "stored" is a failure point.

### 1.2 Human cognitive budget is precious

Founder time is the most expensive resource in a solo-founder project. Every minute spent on "how to log this" is a minute not spent on "what should I build".

AI has unlimited patience for structure. AI can re-read 20 node types to find the right one. Human cannot.

### 1.3 Founders are not librarians

Solo founders are often non-technical. They think in stories, feelings, metaphors. They do not think in structured YAML. Forcing them to think in schemas breaks their creative flow.

GoBP's job is to let founders stay in creative mode while AI handles structured mode.

---

## 2. THE 5 CAPTURE PATTERNS

AI must recognize these patterns in human conversation and trigger corresponding GoBP writes.

### Pattern 1 — Brain dump (Idea capture)

**Human signals:**
- "I'm thinking..."
- "What if we..."
- "Tôi nghĩ là..."
- "Có một ý này..."
- "Maybe we should..."
- Any speculation, not yet firm

**AI action:**
1. Extract the core idea
2. Call `idea_add()` with:
   - `raw_quote`: verbatim what founder said
   - `interpretation`: AI's understanding
   - `subject`: what topic this is about
   - `maturity`: `RAW`
   - `confidence`: `low` to `medium` (AI is not sure yet)
3. Continue conversation normally
4. Later, when founder gets more specific, elevate maturity

**Example:**

```
Founder: "Tôi nghĩ login nên có biometric, vân tay hoặc Face ID cho tiện"

AI (internally):
  - topic: auth:login.method
  - raw: "login nên có biometric, vân tay hoặc Face ID cho tiện"
  - interpretation: Founder wants biometric authentication (fingerprint or Face ID) for login, prioritizing user convenience
  - maturity: RAW (just proposed, no discussion yet)
  - confidence: medium (clear intent, but details missing)

AI calls: idea_add(
  subject="auth:login.method",
  raw_quote="Tôi nghĩ login nên có biometric, vân tay hoặc Face ID cho tiện",
  interpretation="Biometric (fingerprint or Face ID) authentication for login, prioritizing convenience",
  maturity="RAW",
  confidence="medium"
)
→ Returns: idea:i042

AI (to founder): 
  "Ghi nhận rồi. Lưu ý biometric phụ thuộc device — nhiều Android non-biometric 
  hoặc iPhone cũ không có Face ID. Có cần fallback không anh?"
```

**Key rules:**
- `raw_quote` is verbatim, including typos and colloquial words. Never clean up.
- `interpretation` should be slightly more formal but preserve meaning.
- AI should not auto-lock or promote. Let conversation evolve.

### Pattern 2 — Refinement (Idea update)

**Human signals:**
- "À không..."
- "Thôi, đổi thành..."
- "On second thought..."
- "Wait, let me reconsider..."
- Explicit change of mind

**AI action:**
1. Recognize this supersedes a previous idea
2. Call `idea_add()` for NEW idea with:
   - `supersedes`: previous idea ID
   - `maturity`: `REFINED` (because there was thinking involved)
3. Old idea is automatically marked `status: SUPERSEDED` by the edge

**Example (continuing from Pattern 1):**

```
Founder: "À mà đúng, thôi dùng OTP email đi"

AI (internally):
  - This supersedes idea:i042 (biometric)
  - topic: same (auth:login.method)
  - new raw: "thôi dùng OTP email đi"
  - new interpretation: Founder changes from biometric to Email OTP due to device dependency concerns
  - maturity: REFINED (reconsidered after feedback)

AI calls: idea_add(
  subject="auth:login.method",
  raw_quote="à mà đúng, thôi dùng OTP email đi",
  interpretation="Changes auth method from biometric to Email OTP. Reason: biometric device dependency discussed just now.",
  maturity="REFINED",
  confidence="high",
  supersedes="idea:i042"
)
→ Returns: idea:i043

AI (to founder): 
  "OK, tôi linked idea OTP với idea biometric cũ, mark biometric là superseded.
  Anh chốt luôn hay còn cân nhắc?"
```

**Key rules:**
- Always link via `supersedes`, never overwrite
- Old idea stays queryable for history
- Interpretation should reference what triggered the change

### Pattern 3 — Confirmation (Decision lock)

**Human signals:**
- "Ừ chốt"
- "OK, let's do that"
- "Quyết luôn"
- "Final decision"
- "Make it so"
- Explicit finality signal

**AI action:**
1. Confirm interpretation matches founder intent (verification step)
2. Call `decision_lock()` with full context:
   - `topic`: the subject being decided
   - `what`: the decision
   - `why`: rationale (from conversation context)
   - `alternatives_considered`: other options discussed
   - `related_ideas`: chain of ideas leading here
3. Report back to founder with decision ID

**Example (continuing):**

```
Founder: "Ừ chốt OTP email"

AI (internally):
  - Verify I have all context:
    - topic: auth:login.method ✓
    - what: Email OTP ✓
    - why: biometric device-dependent (from conversation) ✓
    - alternatives: biometric, SMS (CEO mentioned VN spam earlier) ✓
    - related_ideas: idea:i042, idea:i043 ✓
  
  - Check with CEO before locking (verification required for decisions)

AI (to founder):
  "Trước khi chốt, xác nhận giúp tôi:
  - Quyết định: Email OTP cho login
  - Lý do: biometric phụ thuộc device, SMS VN nhiều spam
  - Đã cân nhắc: biometric (Face ID, vân tay), SMS OTP
  Đúng không anh?"

Founder: "Đúng"

AI calls: decision_lock(
  topic="auth:login.method",
  what="Use Email OTP for login authentication",
  why="Biometric is device-dependent and fails on older phones. SMS is unreliable in VN due to spam filters.",
  alternatives_considered=[
    {option: "Face ID", rejected_reason: "iPhone-only, device dependency"},
    {option: "Fingerprint", rejected_reason: "Android inconsistency"},
    {option: "SMS OTP", rejected_reason: "VN spam filter issues"}
  ],
  related_ideas=["idea:i042", "idea:i043"]
)
→ Returns: dec:d015

AI (to founder):
  "Chốt rồi. Decision dec:d015 — Email OTP. Rate limit, OTP expiry, digit count 
   mình bàn tiếp sau."
```

**Key rules:**
- ALWAYS verify with founder before `decision_lock()`. This is a hard requirement.
- Verification format: "Trước khi chốt, xác nhận X, Y, Z. Đúng không?"
- If founder says "chốt" but details are fuzzy, ask clarifying questions before locking
- Never lock on ambiguity

### Pattern 4 — Observation (Lesson capture)

**Human signals:**
- "Ghi nhớ đi"
- "Don't do X again"
- "Next time, remember to..."
- "This was a mistake"
- Or AI self-observation: failed approach, wasted effort, pattern recognition

**AI action:**
1. Extract the lesson
2. Identify trigger (what situation this applies to)
3. Call `node_upsert()` with type=Lesson
4. Link to session where observed

**Example:**

```
Founder: "Lần sau nhớ query GoBP trước khi đề xuất tool mới nhé, tôi mệt 
       lắm rồi vì cậu cứ xây trùng"

AI (internally):
  - This is a lesson to capture
  - Trigger: before proposing new tools
  - What: query GoBP first to check existing tools
  - Why: prevents reflexive creation of duplicates
  - Severity: high (founder is tired, repeat issue)

AI calls: node_upsert(
  type="Lesson",
  name="Query GoBP before proposing new tools",
  fields={
    "trigger": "Before any 'let me build tool X' proposal",
    "what_happened": "Reflexive creation of tools that duplicate existing ones, founder has to point it out",
    "why_it_matters": "Wastes tokens, wastes founder patience, violates Discovery > Creation principle",
    "mitigation": "Call find() or tool_list() before proposing. Show existing tools to founder first.",
    "severity": "high"
  }
)
→ Returns: lesson:ll024

AI (to founder):
  "Ghi vào rồi anh. Lesson ll024. Lần sau tôi sẽ query trước khi đề xuất."
```

**Key rules:**
- Lessons with high severity should be re-surfaced at session start (via Protocol 0)
- Don't over-capture — only real lessons, not every minor comment
- If same lesson already exists, increment `verified_count` instead of creating duplicate

### Pattern 5 — Reference (Document registration)

**Human signals:**
- "Đọc DOC-07 đi"
- "Có file X ở path Y"
- "Sử dụng spec trong file này"
- "Here's the document we need to follow"

**AI action:**
1. Check if document already registered (`find()` by source_path)
2. If not, read the file, compute hash, parse sections
3. Call `node_upsert()` with type=Document
4. Optionally propose related nodes (if doc contains features/entities to extract)

**Example:**

```
Founder: "Đọc DOC-07 trong mihos-shared/docs/ để hiểu các flow nhé"

AI (internally):
  - Check: find(query="DOC-07") → not found
  - Read file: mihos-shared/docs/DOC-07_core_user_flows.md
  - Parse sections: F1, F2, F3, F4, F5, F6, F7, F8 (8 flows)
  - Compute hash: sha256:abc123...
  - Extract metadata: name, tags, phase

AI calls: node_upsert(
  type="Document",
  name="Core User Flows",
  id="doc:DOC-07",
  fields={
    "source_path": "mihos-shared/docs/DOC-07_core_user_flows.md",
    "content_hash": "sha256:abc123...",
    "sections": [
      {heading: "F1 Register", lines: [15, 89], tags: ["auth", "onboarding"]},
      {heading: "F2 Login", lines: [90, 156], tags: ["auth"]},
      ...
    ],
    "tags": ["core_flows", "phase1"],
    "phase": 1
  }
)
→ Returns: doc:DOC-07

AI (to founder):
  "Đã register DOC-07 vào GoBP. Thấy 8 flows từ F1 đến F8. 
  Tôi có tạo Feature nodes cho mỗi flow không, hay anh muốn xem trước?"
```

**Key rules:**
- Never duplicate document content in GoBP — only pointer + metadata
- Section parsing enables "read DOC-07 §F2" precise queries
- Ask founder before auto-creating Feature/Entity nodes (they might want manual review)

---

## 3. VERIFICATION PROTOCOL

Not all writes are equal. Some writes are safe to auto-commit, others require verification.

### 3.1 Auto-commit (no verification needed)

- `idea_add()` with maturity=RAW — low stakes, can be edited later
- `session_log()` — factual record, AI knows what happened
- `node_upsert()` for Document — just registering existing file

### 3.2 Verify before commit (ask founder)

- `decision_lock()` — ALWAYS verify. Decisions are authoritative.
- `node_upsert()` for new Feature/Entity — founder should confirm
- `supersedes` relationships on existing Decisions — changing locked knowledge
- Any deletion or status change to ARCHIVED

### 3.3 Verification pattern

```
AI: "Trước khi [action], xác nhận giúp tôi:
     - [key fact 1]
     - [key fact 2]
     - [key fact 3]
     Đúng không anh?"

Founder: "Đúng" / "Sai, sửa X"

AI: [proceed or revise]
```

**Rules:**
- Keep verification short (3-5 bullets max)
- Focus on the LOCKED parts, not the entire context
- If founder says "sai", ask specifically what to revise, don't assume
- Don't verify twice — once is enough

### 3.4 When to skip verification

If founder has just said "chốt X vì Y, xem xét A B C rồi" — they already gave all the information. Verify anyway, but briefly:

```
AI: "OK, chốt X. Reason Y, alternatives A B C considered. Đúng không?"
Founder: "Đúng"
AI: [commit]
```

2 messages round-trip, minimal friction.

---

## 4. CONVERSATION STATE TRACKING

AI needs to track conversation state across turns to make correct capture decisions.

### 4.1 Topic tracking

Every 3-5 turns, AI should mentally note:
- **Current topic:** what is being discussed (auth? ui? strategy?)
- **Subject granularity:** high-level (feature) or detailed (specific rule)?
- **Mode:** brainstorming, deciding, reviewing, explaining?

Example:
```
Turn 1: "Login nên có Face ID"
  → topic: auth:login.method, mode: brainstorming

Turn 2: "À không, OTP email"  
  → same topic, mode: refining (supersedes trigger)

Turn 3: "Rate limit bao nhiêu?"
  → topic: auth:login.rate_limit (sub-topic), mode: detailing

Turn 4: "5/phút OK không?"
  → same sub-topic, mode: proposing

Turn 5: "Chốt"
  → mode: confirmation → decision_lock trigger
```

### 4.2 Maturity progression tracking

AI should recognize maturity signals:

| Signal | Maturity |
|---|---|
| "Tôi đang nghĩ..." / "What if..." | RAW |
| "OK nhưng phải có X" / "With condition Y" | REFINED |
| "Đã bàn với A rồi" / "We discussed this" | DISCUSSED |
| "Chốt" / "Final" / "Quyết" | LOCKED |

Upgrade maturity when signals change. Don't downgrade unless explicit retraction.

### 4.3 Context bundle for next capture

When AI prepares to call `decision_lock()`, it should gather:
- Current topic
- Related ideas (from same or recent turns)
- Alternatives discussed in conversation
- Any lessons that apply
- Any existing decisions being superseded

This bundle becomes the arguments to `decision_lock()`. AI should not re-ask founder for info already in conversation.

---

## 5. MULTI-AI COORDINATION

GoBP is shared memory across multiple AI agents. Coordination is important to avoid conflicts.

### 5.1 Session-based isolation

Each AI agent starts a Session at conversation start:

```python
session_id = session_log(
  actor="Claude-Opus-4.6-Desktop",
  goal="Discuss login feature with founder",
  started_at=now()
)
```

All writes during this session link back via `discovered_in: session_id`. This lets other AI know "Claude Desktop was working on login around time T".

### 5.2 Write conflict handling

If two AI try to write to same node simultaneously:

**v1 approach: last-write-wins with 1-second debounce**

- AI tries to write → GoBP checks `updated` timestamp
- If updated within last 1 second → wait 100ms, re-read, retry
- After 3 retries → error, AI must re-fetch and decide

This is OK for solo-founder projects where concurrent writes are rare. Not production-grade for teams.

### 5.3 Cross-AI visibility

AI A writes `idea:i042`. AI B (in different session) queries for login ideas 5 minutes later. B should see A's idea.

Implementation: MCP server reloads files on each query (or uses file watcher in v2). No caching that stales.

### 5.4 Session handoff

When founder says "tiếp tục session hôm qua" to a new AI:

```text
# New AI executes at session start (MCP: single tool gobp())
gobp(query="recent: 3")
→ Returns latest 3 sessions

# Narrow further (e.g. before a timestamp) by filtering client-side or
# using session fields from the response; optional filters may be added
# to the handler over time.

# New AI loads pending work from handoff
gobp(query="get: node:…")   # full context for the active node
```

Founder doesn't need to re-explain. New AI loads state from GoBP.

---

## 6. FAILURE MODES TO AVOID

### 6.1 Over-capture

**Problem:** AI writes every sentence to GoBP, clutters the graph.
**Solution:** Only capture when pattern matches (section 2). Casual chat is not knowledge.

### 6.2 Under-capture

**Problem:** AI forgets to write important decisions.
**Solution:** Protocol 0 at session start includes "am I missing recent decisions?". Periodic self-check.

### 6.3 Wrong interpretation

**Problem:** AI captures idea with wrong meaning, founder doesn't notice.
**Solution:** 
- Use `confidence: low` when unsure
- Ask clarifying question before locking
- Verification protocol for decisions

### 6.4 Duplicate capture

**Problem:** AI creates new idea/decision when similar one already exists.
**Solution:** 
- Always `find()` before `upsert()`
- If similar exists, update or supersede, don't duplicate

### 6.5 Lost raw_quote

**Problem:** AI paraphrases founder's words in raw_quote field.
**Solution:** 
- `raw_quote` is verbatim ONLY
- Include typos, colloquial words, mixed languages
- Never "clean up" raw quotes

### 6.6 Premature locking

**Problem:** AI locks decision when founder was still thinking.
**Solution:** 
- Verify before lock
- Require explicit "chốt" signal
- "Sounds good" ≠ "locked"

### 6.7 Cross-session pollution

**Problem:** AI writes to GoBP based on previous session context, creates wrong attribution.
**Solution:** 
- Always tag writes with current session_id
- Never write on behalf of past sessions

---

## 7. IMPLEMENTATION HINT FOR AI (system prompt snippet)

Projects using GoBP should include this in AI system prompts:

```
You have access to GoBP via MCP. The server exposes one tool: gobp(query="…").
GoBP is the project's persistent memory shared with other AI agents.

Session start protocol:
1. gobp(query="overview:") once per day (first session), then
2. gobp(query="recent: 3") to see what happened recently
3. gobp(query="session:start actor='…' goal='…'") to start your session
4. gobp(query="get: node:…") for the node you are continuing

During conversation:
- When founder brainstorms → create:Idea (or batch) with raw_quote verbatim
- When founder changes mind → link supersedes or update the idea
- When founder confirms "chốt" → VERIFY first, then lock:Decision …
- When founder mentions a file/doc → create:Document or import: …
- When you observe a lesson → create:Lesson

Always:
- Preserve raw_quote verbatim (no paraphrasing)
- Verify before decision lock — ask founder to confirm 3-5 key facts
- Query GoBP before proposing new nodes (find: … first)
- Link new nodes to current session (discovered_in)
- Prefer batch: for multi-step writes; keep responses concise (mode=summary)

Never:
- Edit GoBP files directly (always via gobp() / batch)
- Lock decisions without verification
- Auto-promote ideas to decisions without explicit "chốt" signal
- Duplicate existing nodes — update or supersede instead
- Paraphrase founder quotes in raw_quote field
```

This snippet can be injected into Cursor cursorrules, Claude CLI config, Claude Desktop system prompt, etc.

---

## 8. EXAMPLES OF GOOD AND BAD CAPTURE

### 8.1 Good capture

**Conversation:**
```
Founder: "Thôi mình dùng Postgres thay vì MongoDB đi, MongoDB phức tạp quá"
AI: "Anh chốt luôn hay còn cân nhắc?"
Founder: "Chốt, Postgres"
```

**AI actions:**
1. `idea_add(subject="db:primary", raw_quote="Thôi mình dùng Postgres thay vì MongoDB đi, MongoDB phức tạp quá", interpretation="Switch from MongoDB to Postgres due to complexity concerns", maturity="REFINED")`
2. Verify (already done — "anh chốt luôn hay còn cân nhắc?")
3. `decision_lock(topic="db:primary", what="Use PostgreSQL as primary database", why="MongoDB considered too complex", alternatives_considered=[{option: "MongoDB", rejected_reason: "complexity"}])`

Clean, minimal, preserves quote, confirms before lock.

### 8.2 Bad capture (wrong)

**Conversation:**
```
Founder: "Thôi mình dùng Postgres thay vì MongoDB đi, MongoDB phức tạp quá"
AI: [silently] decision_lock(what="PostgreSQL is the database", why="simpler than MongoDB")
```

**Problems:**
- Locked without verification
- No raw_quote preserved
- `why` is AI paraphrase, not founder words
- No alternatives considered list
- Rushed to conclusion

### 8.3 Bad capture (over-interpreting)

**Conversation:**
```
Founder: "Hmm, Postgres có ổn không nhỉ?"
AI: [silently] idea_add(subject="db:primary", raw_quote="Hmm, Postgres có ổn không nhỉ?", interpretation="Founder wants to use Postgres", maturity="LOCKED")
```

**Problems:**
- Question ≠ decision
- `maturity: LOCKED` is wrong, should be `RAW` at most
- Interpretation goes beyond what was said
- No verification

### 8.4 Bad capture (under-capture)

**Conversation:**
```
Founder: "Oh actually trust_level should never be exposed to client, period"
AI: "Got it."
[no GoBP write]
```

**Problems:**
- Founder stated an invariant — this is important knowledge
- AI didn't capture it
- Next session won't know this rule
- Will cause bugs later

**Correct action:**
- `node_upsert(type="Lesson" or "Invariant", name="trust_level never exposed to client", ...)`
- Link to relevant features/engines

---

## 9. COMPATIBILITY WITH NON-MCP AI

Some AI agents don't have MCP yet (e.g., older chat UI, email clients, voice assistants). For these:

**Fallback mode:** AI can read GoBP files directly (via filesystem) but should not write. Write operations MUST go through MCP to ensure validation and history log.

If founder is talking to a non-MCP AI:
1. AI can read/reference GoBP for context
2. Founder's important statements should be batched and later re-entered via an MCP-capable AI
3. Or: human can copy-paste the conversation to a Claude Desktop tab with MCP, which then captures

This is a known gap. Not a blocker for v1.

---

### 10.1 Why this matters

Each new Claude session starts with zero context. Without discipline, AI reloads the full graph every session — burning tokens on context that's already been loaded before.

Measured impact (MIHOS baseline, 5 sessions/day):

| Pattern | Tokens/session | Tokens/day | Tokens/month |
|---|---|---|---|
| Full reload every session | ~4,200 | ~21,000 | ~630,000 |
| Continuity pattern | ~800 | ~4,000 | ~120,000 |
| **Saving** | **~3,400** | **~17,000** | **~510,000** |

At scale (A2A multi-agent, team of 3), token waste multiplies by agent count. This pattern is not optional — it is a core operating discipline.

---

### 10.2 Session start checklist (Protocol 0)

**First session of the day** (no prior context):
□ 1. gobp(query="overview:")
→ full project orientation: node counts, recent decisions, topics
→ call ONCE per day, not every session
□ 2. gobp(query="recent: 3")
→ what happened in the last 3 sessions
→ read handoff_notes of the most recent session
□ 3. gobp(query="decisions: <current_topic>")
→ load locked decisions relevant to today's work
→ skip if no specific topic yet
□ 4. gobp(query="session:start actor='<my_name>' goal='<stated_goal>'")
→ register this session in GoBP
→ use founder's stated goal as-is, don't paraphrase
□ Ready to participate with full context loaded.

**Subsequent sessions same day** (already oriented):
□ 1. gobp(query="recent: 1")
→ fetch the last session only
→ read handoff_notes field carefully
□ 2. gobp(query="get: <node_id_from_handoff>")
→ load only the active node being worked on
→ do not load the full graph
□ 3. gobp(query="session:start actor='<my_name>' goal='continue: <handoff_summary>'")
→ register continuation session
□ Ready. DO NOT call gobp(query="overview:") again — wastes tokens you don't need.

Target: < 10 MCP calls · < 30 seconds · < 5K tokens loaded.

---

### 10.3 Mandatory session end

Every session MUST end with `session:end` via MCP, for example:

`gobp(query="session:end outcome='…' handoff='…' session_id='meta.session.…'")`

`outcome` is required. Use `handoff=` for `handoff_notes` (continuity for the next session). Optional: `pending=`, and other session fields supported by `gobp.mcp.tools.write.session_log` (see code / `docs/MCP_TOOLS.md`).

**This is the single most important call in a session.** Without it, the next AI session has no continuity — it must re-explore the full graph to understand where things stand.

If session ends abruptly (context window full, connection lost):
- Founder manually triggers: "End session, we were working on feat:login, next is the widget"
- AI captures immediately before context is lost

---

### 10.4 handoff_notes format

handoff_notes is a contract between this AI session and the next. Write it as if briefing a colleague who has never seen this conversation.

**Good** (next AI understands immediately, 0 re-exploration needed):
"Active node: feat:login (node:feat_login).
Decision locked: dec:d001 — OTP email chosen over Face ID.
Next action: implement LoginScreen widget in Flutter,
link to testkind:security_auth and testkind:unit.
Test cases needed: tc:login_otp_valid, tc:login_otp_expired.
Blocker: waiting for Figma spec from CEO — do not start widget until received."

**Bad** (next AI must re-explore everything):
"Working on login"
"Discussed auth stuff"
"Next: do the widget thing"

Rule of thumb: if a developer who just joined the project reads handoff_notes and understands exactly what to do next — it's good.

---

### 10.5 Reference-first principle

When passing context between sessions, agents, or CEO relays — **pass node_id references, not full content**.

**Wrong** (token waste):
"Here is the full spec for feat:login:
[name, description, status, edges, decisions, test cases... 2,000 tokens]"

**Right** (token efficient):
"Implement feat:login.
Call context('node:feat_login') for full spec."

The recipient queries GoBP directly and gets exactly what it needs. No duplication. No staleness. Always current.

This principle applies to:
- CEO relaying context to a new Claude tab
- Claude briefing Cursor on a task
- Cursor reporting back to Claude CLI
- Any agent handoff in A2A pipeline

---

### 10.6 Query discipline table

Before calling any GoBP tool, ask: "Do I already have this information in my context window?"

| Situation | Correct call | Wrong call |
|---|---|---|
| Brand new session, first of day | `gobp(query="overview:")` | — |
| Continuing same day | `gobp(query="recent: 1")` + `gobp(query="get: <node_id>")` | `gobp(query="overview:")` |
| Need a specific feature | `gobp(query="find:Node login")` | Loading all nodes |
| Need decisions on topic | `gobp(query="decisions: auth:login.method")` | `gobp(query="overview:")` |
| Deep dive on 1 node | `gobp(query="get: node_id")` | `gobp(query="overview:")` |
| Check test coverage | `gobp(query="find:TestCase login")` | — |
| Understand a concept | `gobp(query="find:Concept test taxonomy")` | — |
| **Never do** | `gobp(query="overview:")` if already oriented in same day | — |

---

### 10.7 Multi-agent token discipline (A2A ready)

When multiple AI agents work on the same project (Cursor + Claude Desktop + Claude CLI):

Each agent maintains its own session. Agents do NOT pass full context to each other. They pass node_id references.
Claude → Cursor:   "Execute Wave 4 Task 1. Spec: waves/wave_4_brief.md §Task1.
Active session: session:2026-04-15_wave4.
Read context('wave_4_task_1_spec') if exists."
Cursor → Claude:   "Task 1 done. Commit: abc123.
6 tests pass. Node created: node:init_module.
gobp(query=\"recent: 1\") for full report."
Claude → CLI:      "Audit Task 1. Brief: waves/wave_4_brief.md §Task1.
Cursor report: gobp(query=\"recent: 1\")."

Total tokens per task handoff: ~100 tokens instead of ~5,000.

This is the operating pattern for Wave 10 (A2A bridge). Establish the discipline now — the protocol just formalizes what's already working.

---

## 11. REFERENCES

- VISION.md — why GoBP exists (pain 1 and pain 2)
- ARCHITECTURE.md — 6 node types and 5 edge types used here
- IMPORT_MODEL.md — how existing docs get imported (next doc)
- mihos-cto-engineer-SKILL-v3.md — Protocol 0 query-first behavior
- MCP Protocol spec — how tools are called

---

## 12. OPEN QUESTIONS (for future docs)

1. How does AI know when to end a session vs just pause? → Session management rules needed
2. How do we handle multi-language conversations (Vietnamese + English mix)? → Mostly fine, raw_quote preserves language, interpretation can be in English for consistency
3. What if founder contradicts themselves in same conversation? → Create new idea supersedes old, both linked to same session
4. How to handle "offhand comments" that might be important? → Capture as RAW with low confidence, review in retrospective
5. Voice input accuracy — transcription errors in raw_quote? → v1: AI notes [likely transcription error] in interpretation field. v2: confidence scoring with ASR feedback.

---

*Written: 2026-04-14*
*Author: CTO Chat (Claude Opus 4.6) with CEO*
*Status: v0.1 draft, awaiting CEO review*
*Next: IMPORT_MODEL.md*

◈
