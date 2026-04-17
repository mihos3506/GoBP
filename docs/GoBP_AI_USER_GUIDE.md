# GoBP — AI User Guide

**Audience:** Any AI using the GoBP MCP tool `gobp(query=...)`.  
**Goal:** Correct protocol, minimal tokens, valid graph writes.  
**Authority:** Behavior follows `gobp/schema/core_nodes.yaml`, `core_edges.yaml`, and dispatcher/parser in repo.

---

## 1. Mental model

- **Source of truth:** Markdown + YAML under `.gobp/` (file-first). MCP is a façade.
- **One tool string:** `gobp(query="<action> ...")` — parsed to `(action, node_type_hint, params)`.
- **Writes require an open `Session`:** obtain `session_id` from `session:start`, pass on every mutating call / batch.

---

## 2. Mandatory workflow (QUERY_RULES)

1. **`overview:`** — once per AI session at start; do not spam.
2. **`template:`** — once per **node type** before bulk creates (fields + `suggested_edges` + `batch_example`).
3. **`template_batch:`** — many nodes of the same type (fill placeholders → `batch`).
4. **`suggest:`** — before creating anything new (reuse / dedupe).
5. **`explore:`** — prefer over `find` + `get` + `related` for neighborhood; use **`compact=true`** for quick checks.
6. **`batch`** — all creates / updates / deletes / edges in production use; avoid one-off `create:` in loops.
7. **`find` / `get`** — default **`mode=summary`**; **`mode=full`** only for deep debug.
8. **After reads:** carry forward **id + name** only; do not paste full JSON into the next user message.
9. **One session ≈ one goal** — `session:end` when the unit of work finishes.
10. **`batch` errors:** fix and resubmit **only failed ops**, not the whole batch.

**Token guide (order of magnitude):** see `PROTOCOL_GUIDE["token_guide"]` via `overview: full_interface=true` (large payload).

---

## 3. Session lifecycle (writes)

```text
session:start actor='<ai_or_tool>' goal='<short goal>'
→ session_id

… all writes include session_id=…

session:end outcome='<result>' handoff='<optional next>' session_id=…
```

Without a live session, mutators return an error.

---

## 4. Core node types (canonical list)

Each row is one **`type`** value (PascalCase). Many **nodes** per type. IDs are generated or use `testkind:slug` / `node:slug` patterns per schema.

| Type | Role (one line) |
|------|-----------------|
| **Node** | Generic graph vertex when no finer type fits. |
| **Idea** | Raw capture / quote / interpretation toward a decision. |
| **Decision** | Lockable choice (`lock:Decision …`). |
| **Session** | Audit unit for work (actor, goal, lifecycle). |
| **Document** | External spec / doc anchor (`references` target). |
| **Lesson** | Captured learning. |
| **Concept** | Defined term or pattern (taxonomy / glossary). |
| **TestKind** | Test **category** (many nodes: unit, integration, project-specific names). |
| **TestCase** | Single test instance; `kind_id` → TestKind; `covers` → subject node. |
| **Engine** | Executable business capability. |
| **Flow** | User- or system-level flow. |
| **Entity** | Domain object / aggregate. |
| **Feature** | Product-facing capability slice. |
| **Invariant** | Hard rule / constraint. |
| **Screen** | UI surface. |
| **APIEndpoint** | HTTP/RPC surface. |
| **Repository** | Code / VCS grouping (when used). |
| **Wave** | Delivery wave / batch of work. |
| **Task** | Assignable work item for agents. |

**Schema field truth:** required/optional per type live in `gobp/schema/core_nodes.yaml` — use **`template: <Type>`** instead of guessing.

**Two different “group” words:**

- **`id_groups` in `.gobp/config.yaml`** — namespace for **IDs** (`slug.ops.12345678`, `.test.unit.…`). Repair drift: CLI `python -m gobp.cli seed-universal` (merges defaults additively; `--rewrite --confirm CEO` overwrites seeds).
- **`TestKind.group` field** — enum `functional | non_functional | security | process` (taxonomy), **not** the same as `id_groups`. MCP create fills safe defaults if omitted.

---

## 5. Read cheat sheet

| Need | Query pattern |
|------|----------------|
| Project snapshot (slim) | `overview:` |
| Full action catalog | `overview: full_interface=true` (heavy) |
| Search | `find: <keyword> mode=summary` or `find:<Type> <keyword>` |
| Pagination | Same query + `cursor=<page_info.next_cursor>` until `has_more` is false — do **not** loop on `total_estimate` alone. |
| One node + edges + near-dupes | `explore: <keyword>` — skips `discovered_in`; add `compact=true` for strings-only edges. |
| Reuse candidates | `suggest: <short context>` |
| One node detail | `get: <node_id> mode=brief` or `compact=true` for id/name/type + `edge_count` |
| Many nodes by id | `get_batch: ids='a,b,c' mode=summary` |
| Neighbors | `related: <node_id> mode=summary` |
| Schema frame | `template: Engine` / `template:` (catalog) |
| Multi-node frame | `template_batch: Engine count=5` |

---

## 6. Writes — `batch` only (production)

**Envelope:**

```text
batch session_id='<sid>' ops='<multiline block>'
```

**Line grammar (representative):**

- `create: <Type>: Name \| Description`
- `update: <node_id> field=value …`
- `replace: <node_id> …` (destructive merge path — treat as dangerous)
- `delete: <node_id>`
- `retype: <node_id> new_type=<Type>`
- `merge: keep=<id> absorb=<id>`
- `edge+: FromName --edge_type--> ToName` (names or ids per parser rules)
- `edge-:`, `edge~:` (retype edge), `edge*:` (fan-out replace)

**Limits:** max **50** ops per `ops` block — split batches.

**Response:**

- Default: **summary** + truncated `skipped`/`warnings`; **`verbose=true`** for full lists.

---

## 7. Edges (high-signal)

Use only types declared in `core_edges.yaml`. Common ones:

`relates_to` · `implements` · `depends_on` · `references` · `supersedes` · `discovered_in` (auto/metadata) · `covers` · `of_kind` (TestCase→TestKind) · `tested_by` · `enforces` · `triggers` · `validates` · `produces`

**Template:** `template: <Type>` returns **`suggested_edges`** derived from schema — prefer those over inventing edge types.

---

## 8. ID shapes (read-only intuition)

- Most structured nodes: `{slug}.{id_group}.{8digits}` (group from `id_groups`, not free text).
- **TestCase:** `{slug}.test.<kind>.{8digits}` with `<kind>` from a known test-kind slug family.
- **Session:** `meta.session.<date>.<hash>`
- Legacy / colon ids still appear (`testkind:unit`, `node:foo`) — valid per patterns in schema.

Do **not** hand-craft snowflake digits; use auto `create:` / `batch` or follow schema patterns.

---

## 9. Anti-patterns (hard)

- Calling **`overview:`** every turn.
- **`create:` / `update:` / `edge:`** in tight loops instead of **`batch`**.
- Broad **`find:`** without `mode=summary` or type filter when the graph is large.
- Ignoring **`suggested_edges`** then orphan nodes (no relationships).
- Assuming **`total_estimate`** equals “items left to fetch” on a single page — use **`has_more`** + **`next_cursor`**.
- Creating **new `id_groups` layers** or **new node `type`s** without schema extension — out of scope for MCP-only agents.

---

## 10. Human repair hooks (not MCP-gated)

- **`python -m gobp.cli seed-universal`** — restore canonical **TestKind + Concept** files and merge missing **`id_groups`** types (additive).  
- **`--rewrite --confirm CEO`** — overwrite all built-in seed files (destructive; human gate).

---

## 11. Where to read more

| Doc | Use |
|-----|-----|
| `docs/SCHEMA.md` | Human narrative of nodes/edges |
| `docs/MCP_TOOLS.md` | Tool surface details |
| `docs/INPUT_MODEL.md` / `IMPORT_MODEL.md` | Import / field contracts |
| `gobp/mcp/parser.py` | `PROTOCOL_GUIDE`, `QUERY_RULES` literals |

When in doubt: **`validate: metadata`**, **`template:`**, and **`explore:` compact=true** before writing.
