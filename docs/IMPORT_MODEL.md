# ◈ GoBP IMPORT MODEL

**File:** `D:\GoBP\docs\IMPORT_MODEL.md`
**Version:** v0.1
**Status:** draft
**Depends on:** VISION.md, ARCHITECTURE.md, INPUT_MODEL.md
**Audience:** AI agents importing existing project content into GoBP

---

## 0. WHY IMPORT MATTERS

Most projects adopting GoBP are NOT greenfield. They have:
- Existing documentation (DOCs, specs, wikis)
- Existing code (features, entities already coded)
- Existing decisions (scattered in chat logs, emails, commits)
- Existing ideas (in founder's head, notes, sketches)

If GoBP only supports "start from zero", it cannot serve MIHOS (which has 31 DOCs) or most real projects. **Import is core, not optional.**

This doc defines how existing project content becomes GoBP knowledge without manual YAML editing.

---

## 1. THREE PROJECT STATES

A project adopting GoBP is in one of three states:

### State 1 — Greenfield (empty)
Project has no docs, no code, just an idea. Founder wants to start capturing thoughts immediately.

**Characteristics:**
- No existing files to import
- All knowledge will come from conversation
- INPUT_MODEL (capture patterns) is the only input source
- Starts with 0 nodes

**GoBP init:**
```bash
gobp init --empty
```

**Timeline:** Founder uses GoBP from day 1 of project. Every brainstorm, every decision captured live.

### State 2 — In-progress (docs exist, code partial)
Project has specification docs and some code. Founder wants GoBP to help organize and accelerate remaining work.

**Characteristics:**
- Existing docs need to become Document nodes + referenced sections
- Existing features/entities from docs become Node (type=Feature, type=Entity)
- Some decisions from chat history worth capturing
- Starts with 50-500 nodes after import

**GoBP init:**
```bash
gobp init --from-docs <docs_folder>
```

**Timeline:** One-time import (1-4 hours), then live capture going forward.

**This is MIHOS case.** 31 DOCs exist, code not yet built.

### State 3 — Legacy (mature project)
Project has full docs, full codebase, active development. Founder wants GoBP for ongoing knowledge accumulation.

**Characteristics:**
- Docs + code both need scanning
- Features/entities extracted from both sources
- Historical decisions reconstructed from git log, commit messages, PR descriptions
- Starts with 500-5000 nodes after import

**GoBP init:**
```bash
gobp init --from-docs <docs_folder> --scan-code <code_folder>
```

**Timeline:** Longer import (4-16 hours), mixing auto-extraction and AI-assisted proposal.

---

## 2. THE 3 IMPORT APPROACHES

For State 2 and State 3, there are 3 approaches to getting existing content into GoBP.

### Approach A — Manual entry via conversation

**How it works:** Founder reads existing doc alongside AI. AI captures relevant info as it goes using standard INPUT_MODEL patterns.

**Pros:**
- Highest quality — human verifies every capture
- Preserves nuance — AI can ask clarifying questions
- No need for import tooling

**Cons:**
- Slow — 30-60 minutes per doc
- Tedious — founder reads whole doc
- Scales poorly — 31 MIHOS DOCs = 15-30 hours

**When to use:** For 1-5 critical docs where quality matters more than speed.

### Approach B — Auto-parser scripts

**How it works:** Python script reads markdown files, extracts headers, lists, links, and code blocks. Creates Document nodes + skeleton Feature/Entity nodes based on heuristics.

**Pros:**
- Fast — 31 DOCs parsed in 30 seconds
- Deterministic — same input, same output
- No AI token cost

**Cons:**
- Low semantic understanding — can't tell "F1 Register is a feature, §Invariants is a rule list"
- Misses relationships between nodes
- Generates noisy nodes that need cleanup
- Wrong categorization ("heading level 2 = Feature" breaks when doc has other structure)

**When to use:** For basic skeleton (Document nodes only) or very structured docs where parsing rules are reliable.

### Approach C — AI-assisted proposal (RECOMMENDED)

**How it works:** AI reads doc with full context (GoBP schema + project type + existing nodes). AI proposes a batch of nodes and edges. Founder reviews proposal via conversation. Founder approves. Batch commits atomically.

**Pros:**
- Semantic understanding — AI knows "F1 Register is a Feature, §Invariants is an Invariant list"
- Handles relationships — AI proposes edges between nodes
- Human verification — founder catches mistakes
- Batch efficiency — 1 proposal per doc, not per node

**Cons:**
- Token cost per import
- Dependent on AI quality
- Requires founder attention during review

**When to use:** Default for State 2 and State 3 imports.

**GoBP v1 uses Approach C as primary, with Approach B as fallback for bulk Document pointer creation.**

---

## 3. APPROACH C IN DETAIL

### 3.1 Proposal structure

An import proposal is a single JSON blob with:

```json
{
  "proposal_id": "imp:2026-04-14_DOC-07",
  "source": {
    "path": "mihos-shared/docs/DOC-07_core_user_flows.md",
    "content_hash": "sha256:abc123...",
    "size_bytes": 48212,
    "ai_reader": "Claude Opus 4.6"
  },
  "proposed_document": {
    "type": "Document",
    "id": "doc:DOC-07",
    "name": "Core User Flows",
    "sections": [
      {"heading": "F1 Register", "lines": [15, 89]},
      {"heading": "F2 Login", "lines": [90, 156]},
      {"heading": "F3 Mi Hốt", "lines": [157, 278]},
      {"heading": "F4 Provider Scan", "lines": [279, 380]},
      {"heading": "F5 Imprint Capture", "lines": [381, 445]},
      {"heading": "F6 Wallet", "lines": [446, 520]},
      {"heading": "F7 Memory Review", "lines": [521, 590]},
      {"heading": "F8 Settings", "lines": [591, 650]}
    ]
  },
  "proposed_nodes": [
    {
      "type": "Node",
      "subtype": "Feature",
      "id": "node:feat_register",
      "name": "Register",
      "status": "DRAFT",
      "source": "doc:DOC-07#F1",
      "description": "New user onboarding flow: email → OTP → profile setup"
    },
    {
      "type": "Node",
      "subtype": "Feature", 
      "id": "node:feat_login",
      "name": "Login",
      "status": "DRAFT",
      "source": "doc:DOC-07#F2"
    },
    // ... 6 more features
  ],
  "proposed_edges": [
    {"from": "node:feat_register", "to": "doc:DOC-07", "type": "references", "section": "F1"},
    {"from": "node:feat_login", "to": "doc:DOC-07", "type": "references", "section": "F2"},
    // ... 6 more references
    {"from": "node:feat_register", "to": "node:feat_login", "type": "relates_to"},
    // ... optional relation edges
  ],
  "proposal_notes": "Extracted 8 features from DOC-07 based on F1-F8 section headers. Each feature links to its section. feat:register and feat:login marked as related since both are auth flows. Descriptions taken from first paragraph of each section.",
  "confidence": "high",
  "created_at": "2026-04-14T16:00:00"
}
```

### 3.2 Proposal flow (conversation example)

```
Founder: "Import DOC-07 vào GoBP đi"

AI internally:
  1. find(query="DOC-07") → not found
  2. Read file: mihos-shared/docs/DOC-07_core_user_flows.md
  3. Parse structure: H1 "Core User Flows", H2 F1-F8
  4. Compute hash
  5. Build proposal (section 3.1)
  6. Call import_proposal(...) → returns proposal_id

AI (to founder): 
  "Tôi đọc DOC-07 rồi. Đề xuất import như sau:
  
  1 Document node: DOC-07 (8 sections F1-F8)
  8 Feature nodes: Register, Login, Mi Hốt, Provider Scan, Imprint Capture, 
                   Wallet, Memory Review, Settings
  8 references edges: mỗi feature → section của nó
  2 relates_to edges: Register ↔ Login (cùng auth)
  
  Tất cả Feature status = DRAFT. Confidence: high.
  
  Anh duyệt nguyên batch, hay muốn xem từng node?"

Founder: "Duyệt nguyên batch, nhưng Provider Scan là engine, không phải feature"

AI:
  7. Revise proposal: node:feat_provider_scan → node:eng_provider_scan, subtype: Engine
  8. Show updated proposal

AI (to founder):
  "Sửa rồi: Provider Scan → Engine (eng:provider_scan). 7 Feature + 1 Engine.
  Duyệt không?"

Founder: "Ừ, duyệt"

AI:
  9. Call import_commit(proposal_id="imp:2026-04-14_DOC-07") → commits atomically
  10. Returns: 9 nodes created, 10 edges created

AI (to founder):
  "Import xong. 9 nodes + 10 edges. Tôi log session này. 
  Anh muốn import DOC nào tiếp theo?"
```

**Timing:** ~3-5 minutes per doc with AI Opus 4.6 quality. For 31 DOCs ≈ 2-3 hours total.

### 3.3 Proposal review patterns

Founder doesn't have to approve 100%. AI should accept partial feedback:

**Accept all:**
```
Founder: "OK, duyệt"
AI: [commit entire batch]
```

**Reject all:**
```
Founder: "Không, bỏ đi"
AI: [abandon proposal, no writes]
```

**Modify specific items:**
```
Founder: "Feature F3 Mi Hốt thực ra là flow, không phải feature"
AI: [update proposal, change subtype, show diff, re-confirm]
```

**Partial accept:**
```
Founder: "Duyệt F1, F2, F3. F4-F8 để sau"
AI: [commit F1-F3 only, save proposal for F4-F8 with status=deferred]
```

**Request more detail:**
```
Founder: "Cho tôi xem interpretation của feat:register"
AI: [show full node proposal with description, source excerpt]
```

### 3.4 Proposal storage

Proposals are saved in `.gobp/proposals/` as YAML files while pending:

```
.gobp/proposals/
├── imp_2026-04-14_DOC-07.pending.yaml
├── imp_2026-04-14_DOC-08.committed.yaml
└── imp_2026-04-14_DOC-09.rejected.yaml
```

States:
- `pending` — awaiting founder review
- `committed` — executed, nodes/edges created
- `rejected` — abandoned
- `deferred` — partial, rest awaits later

AI can resume a deferred proposal: `import_proposal_resume("imp:...")`.

---

## 4. IMPORT TOOLS (MCP)

Two MCP tools for import flow:

### 4.1 import_proposal

```
Input:
  source_path: str           # path to file to import
  proposal_type: "doc" | "code" | "spec"  # what kind of source
  ai_notes: str              # AI's analysis notes

Output:
  proposal_id: str
  proposed_document: dict    # the Document node spec
  proposed_nodes: list       # list of node specs
  proposed_edges: list       # list of edge specs
  summary: str               # human-readable summary
  confidence: "low" | "medium" | "high"
```

AI calls this after reading source file. GoBP stores proposal in `.gobp/proposals/`, returns summary.

### 4.2 import_commit

```
Input:
  proposal_id: str
  accept: "all" | "partial"
  accepted_node_ids: list    # if partial
  accepted_edge_ids: list    # if partial
  overrides: dict            # per-node field overrides from founder feedback

Output:
  nodes_created: int
  edges_created: int
  errors: list
  session_logged: bool
```

Commits the batch atomically. If any validation fails, NOTHING is written — all-or-nothing.

---

## 5. IMPORT FOR STATE 3 (LEGACY WITH CODE)

Importing a mature project adds a 4th source: existing code.

### 5.1 Code scanning approach

**v1 approach: minimal** — AI reads code only at a very high level:
- Folder structure → organizational hints
- Main entry points → Tool nodes
- README files → Document nodes  
- Package manifests (package.json, pyproject.toml, go.mod) → Dependency metadata
- Git log summary → recent activity context

**NOT in v1:** AST parsing, call graph analysis, dependency tracing. Those are code intelligence features (GitNexus, Sourcegraph territory). GoBP is not a code intelligence tool.

### 5.2 Code scan proposal example

```
Founder: "Scan codebase ở src/"

AI internally:
  1. Read src/ folder structure
  2. Read src/README.md if exists
  3. Read top-level package files
  4. Build proposal: Tool nodes for main modules + Document nodes for READMEs

AI (to founder):
  "Scan src/ xong. Đề xuất:
  
  3 Tool nodes:
  - tool:auth_module (src/auth/)
  - tool:api_server (src/api/)
  - tool:db_layer (src/db/)
  
  2 Document nodes:
  - doc:src_README (src/README.md)
  - doc:architecture_md (src/ARCHITECTURE.md)
  
  Tôi không scan chi tiết code — chỉ register structure. 
  Code intelligence deep-dive không phải việc của GoBP.
  
  Duyệt không?"
```

### 5.3 What GoBP NEVER imports from code

- Function signatures (that's LSP territory)
- Call graphs (that's static analysis)
- Type definitions (that's type checker territory)
- Variable usage (that's IDE territory)

GoBP imports **what the project is about**, not **how the code works**.

---

## 6. RE-IMPORT (when source changes)

Source files change. GoBP must handle re-import gracefully.

### 6.1 Stale detection

Every Document node has `content_hash`. When AI is about to query a Document, it can verify:

```python
current_hash = sha256(read_file(doc.source_path))
if current_hash != doc.content_hash:
    # Source changed since last import
    mark_stale(doc.id)
    suggest_reimport(doc.id)
```

### 6.2 Re-import flow

```
Founder: "DOC-07 vừa update, re-import đi"

AI:
  1. Read current file
  2. Compute new hash
  3. Diff sections:
     - Old: F1-F8 (8 sections)
     - New: F1-F9 (9 sections, added F9 "Delete Account")
  4. Build re-import proposal:
     - Update doc:DOC-07 with new hash + new sections list
     - Create new node: node:feat_delete_account (for F9)
     - Create new edge: node:feat_delete_account → doc:DOC-07#F9

AI (to founder):
  "Thay đổi trong DOC-07:
   - Section F9 'Delete Account' mới thêm
   - Các section F1-F8 không đổi
   
   Đề xuất tạo 1 Feature mới: feat:delete_account
   Các Feature khác giữ nguyên.
   
   Duyệt?"

Founder: "Ừ"

AI: [commit update + new node]
```

**Rule:** Re-import never deletes existing nodes. It adds new ones or marks old ones as `status: DEPRECATED` if section no longer exists in source.

### 6.3 Conflict with manual edits

What if founder (via AI conversation) modified a node's interpretation, then source doc changes?

**Rule:** Source doc update does NOT overwrite founder's manual edits. AI must show diff and ask:

```
AI: "Source updated section F1 Register. Current GoBP interpretation is:
     'New user signup with email OTP'
    
    Source now says:
    'New user signup with email OTP + optional referral code'
    
    Keep current GoBP interpretation? Or update to match source?"
```

Founder decides case-by-case.

---

## 7. IMPORT FOR MIHOS (CONCRETE PLAN)

MIHOS is the first State 2 test case. Concrete import plan:

### 7.1 Scope

**Import targets:**
- 31 DOCs in `mihos-shared/docs/` → 31 Document nodes
- Extract features from DOC-07 (Core Flows) → ~8 Feature nodes
- Extract engines from DOC-16 (Engine Specs) → ~14 Engine nodes
- Extract entities from DOC-02 (Master Definitions) → ~30 Entity nodes
- Extract invariants from DOC-02 + DOC-07 → ~15 Invariant nodes
- Extract decisions from SESSION_JOURNAL files → ~20 Decision nodes
- Create edges linking features ↔ engines ↔ entities ↔ invariants

**Total estimate:** ~118 nodes, ~250 edges after full import.

**Out of scope for initial import:**
- Governance files (5) — not knowledge, they are process docs
- rules/R* files — task-scoped guardrails, not project knowledge
- Existing code in mihos-flutter/, mihos-backend/ — Phase 1 not built yet

### 7.2 Import order

Import in dependency order (foundational first):

1. **DOC-01 soul** → 1 Document node (no extraction, just register)
2. **DOC-02 master definitions** → Entity nodes + Invariant nodes
3. **DOC-03 identity** → Entity nodes (User, Traveller, etc.)
4. **DOC-07 core flows** → Feature nodes
5. **DOC-13 entity dictionary** → verify + cross-link with DOC-02
6. **DOC-15 API reference** → Endpoint nodes (subset of Feature)
7. **DOC-16 engine specs** → Engine nodes
8. **DOC-22 test QA** → TestKind nodes
9. **DOC-08 to DOC-12** (various) → registered as Document, limited extraction
10. **DOC-04 to DOC-06** → registered, limited extraction
11. **DOC-17 to DOC-31** → registered as Document pointers, extraction optional

### 7.3 Import session structure

**Session 1: Foundation (1-2 hours)**
- Import DOC-01, DOC-02, DOC-03
- Review, verify, commit
- CEO explicit approval per doc

**Session 2: Core flows (1-2 hours)**
- Import DOC-07
- Extract 8 features
- Link features to DOC-02 invariants
- CEO approval

**Session 3: Engines & APIs (1-2 hours)**
- Import DOC-15, DOC-16
- Extract engines and endpoints
- Link to features

**Session 4: Bulk register (30-60 min)**
- Remaining 23 DOCs imported as pointers only
- No extraction
- Fast batch commit

**Session 5: Decisions from history (1 hour)**
- Parse SESSION_JOURNAL 2026-04-12 + 2026-04-14
- Extract locked decisions
- Link to related features/engines

**Total: 5-8 hours CEO engagement spread across 3-5 days.**

After this, MIHOS has full GoBP baseline. All subsequent work captures live via INPUT_MODEL patterns.

---

## 8. IMPORT QUALITY CHECKS

Before commit, AI should verify proposal quality:

### 8.1 Self-checks AI runs

- **No orphan edges** — every edge's from/to points to a proposed or existing node
- **No duplicate IDs** — proposed nodes don't collide with existing nodes
- **Schema valid** — each proposed node matches its type's schema
- **Hash matches** — source file hash is current
- **Reasonable count** — proposal has 1-50 nodes (more is suspicious)

### 8.2 Confidence scoring

AI assigns confidence to proposal:

| Confidence | Criteria |
|---|---|
| **high** | Clear structure (headers/sections), familiar domain, no ambiguity |
| **medium** | Some interpretation required, domain partially known |
| **low** | Ambiguous structure, unfamiliar domain, many assumptions |

Founder sees confidence score. Low confidence proposals should be reviewed more carefully.

### 8.3 Rejection signals

If founder repeatedly rejects proposals for same doc, AI should:
1. Ask what's wrong ("Feature vs Entity? Wrong section extraction? Something else?")
2. Offer manual walkthrough ("Anh đọc doc với tôi từng section?")
3. Skip and mark doc as "manual import only"

Don't keep retrying the same failed approach.

---

## 9. BULK OPERATIONS

Some imports are best done in bulk, skipping per-doc proposal flow.

### 9.1 Bulk Document registration

For State 2/3 projects with many docs where extraction isn't needed:

```
Founder: "Register hết docs trong mihos-shared/docs/ thành Document nodes, 
         không extract gì cả"

AI:
  1. List all *.md files in folder
  2. For each: read, hash, extract metadata (name, sections skeleton)
  3. Build single bulk proposal: 31 Document nodes, 0 other nodes, 0 edges
  4. Show count + confidence

AI (to founder):
  "31 files in mihos-shared/docs/. Đề xuất: 31 Document nodes, 0 extraction.
  Chỉ register pointers. Duyệt?"

Founder: "Ừ"

AI: [single commit, 31 Documents created]
```

Takes 30 seconds. Founder can extract individual docs later when needed.

### 9.2 Bulk edge linking

After nodes exist, creating semantic edges between them:

```
Founder: "Tất cả Feature nodes có edges implements tới flow tương ứng"

AI:
  1. Query find(type=Feature) → list of Feature nodes
  2. Query find(type=Flow) → list of Flow nodes
  3. Match by naming convention (feat:register → flow:F1 if "register" in F1 title)
  4. Propose edges
  5. Founder reviews

AI: "Tôi match được 8 Feature với 8 Flow. Cụ thể:
     feat:register ↔ flow:F1_register
     feat:login ↔ flow:F2_login
     ...
     Duyệt không?"
```

Accelerates bulk edge creation without 1-by-1 entry.

---

## 10. FAILURE MODES IN IMPORT

### 10.1 AI hallucinates content

**Problem:** AI "extracts" a feature that doesn't actually exist in source doc. Reads between the lines too much.

**Solution:** 
- AI must quote source text for each proposed node in `source_excerpt` field
- Founder can verify excerpt matches
- Confidence scoring should flag unfamiliar domains

### 10.2 AI misses important content

**Problem:** AI extracts 5 features when source doc has 8.

**Solution:**
- Show section count in proposal: "Doc has 8 H2 headings, proposed 5 features — you may want to review"
- Founder can request "all sections" mode
- Reviewing proposal before commit catches this

### 10.3 Wrong node type assignment

**Problem:** AI proposes "Provider Scan" as Feature, but it's actually Engine.

**Solution:** 
- Founder correction in conversation
- AI updates proposal
- Learn for next session via Lesson capture

### 10.4 Duplicate nodes from re-import

**Problem:** Importing DOC-07 twice creates feat:register twice.

**Solution:**
- `node_upsert` checks existing IDs, updates instead of creates
- Import commit uses upsert semantic for Document nodes
- New nodes with same (type, name) → AI prompts "existing node found, update or skip?"

### 10.5 Source file missing or moved

**Problem:** Document node points to file that no longer exists.

**Solution:**
- `validate()` tool detects broken references
- AI can propose: "File moved? Enter new path?" or "Delete Document node?"
- History log preserves original path for recovery

---

## 11. IMPORT AND PRIVACY

If source docs contain sensitive info (passwords, API keys, PII), import must be careful.

**v1 rule:** GoBP stores content hash and references, never content itself. Sensitive data stays in source file, not in GoBP.

**If source doc has secrets:** 
- GoBP Document node has `source_path` and `sections`, not content
- AI reads file on demand when founder queries
- AI should flag suspected secrets: "I noticed an API key in §Credentials, should this section be excluded from references?"

**Future (v2):** Explicit privacy markers — `privacy: secret` on sections, Access control per node.

---

## 12. NON-MARKDOWN SOURCES

v1 supports:
- `.md` files (primary)
- `.txt` files (limited parsing, treat as unstructured)

**Not supported in v1:**
- `.docx` (Microsoft Word)
- `.pdf`
- `.html`
- `.json` / `.yaml` project-specific formats
- Notion exports
- Confluence exports
- Google Docs

**Workaround:** Convert to `.md` first (pandoc, copy-paste, etc.), then import.

**v2 consideration:** Add plugin architecture for format-specific importers.

---

## 13. REFERENCES

- VISION.md — why GoBP exists (pain 2 about Cursor context bloat)
- ARCHITECTURE.md — Document node type, references edge
- INPUT_MODEL.md — how live conversation becomes GoBP data
- mihos-shared/docs/ — MIHOS 31 DOCs, first real import target
- SESSION_JOURNAL 2026-04-14.md — decisions to extract for MIHOS import

---

## 14. OPEN QUESTIONS (deferred to v2)

1. Automatic re-import on file watcher events? (v2)
2. Diff UI for source changes? (v2)
3. Multi-repo imports (monorepo, submodules)? (v2)
4. Import from URLs (GitHub wiki, public docs)? (v2)
5. Merge strategy when two AI agents import same doc simultaneously? (v2)

---

*Written: 2026-04-14*
*Status: v0.1 draft*
*Next: SCHEMA.md*

◈
