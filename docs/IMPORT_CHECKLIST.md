# Import checklist — AI agents (GoBP)

**Purpose:** Enforce Decision **dec:d002** — *template → full read → plan (nodes + edges) → CEO review → batch*.  
**Audience:** Any AI importing external documents, specs, or spreadsheets into the GoBP graph.

**Schema v2:** Nodes carry **`group`** (breadcrumb), **`description`** as `{info, code}`, **`lifecycle`**, **`read_order`** — see `docs/SCHEMA.md` and `docs/GoBP_AI_USER_GUIDE.md`.

---

## Before you start

- [ ] You have an active **`session:start`** (writes require `session_id`).
- [ ] You called **`template:`** or **`template_batch:`** for each node type you will create — note **default `group`** and **required** fields (`description.info`, type-specific `required` in YAML).
- [ ] You ran **`suggest: name group="…"`** (or `find:`) so new content can **relate to existing** nodes and avoid duplicates **within the same group** (skip only for the **first** substantive node in an empty project).
- [ ] You have a written plan: **nodes** (type, name, **group** if not default) + **edges** — before any `batch:`.

---

## Steps (in order)

1. **Read the entire source**  
   Read the **whole** document (or the whole agreed section), not fragments. Query Rule 12 in `GoBP_AI_USER_GUIDE.md`.

2. **List nodes and edges first (plan)**  
   - Every **node**: type, proposed name, **`group`** (if not inferrable from type), minimal fields, intended **id** if fixed.  
   - Every **edge**: `from`, `to`, `type` — must be valid per `core_edges.yaml`.  
   - Do **not** create nodes first and “figure out edges later.”

3. **CEO review of the plan**  
   When the Brief or CEO requires it: stop and get approval before **`batch:`**.

4. **Batch execute**  
   Use **`batch:`** (or **`quick:`** delegating to batch). One batch should create nodes **and** edges together where possible.

5. **Relate new nodes (when graph already has data)**  
   Each new substantive node must have at least one edge to an **existing** node (or an edge path through a new node that itself connects back), except the **first** node in a greenfield graph. See Query Rule 11 in the AI User Guide.

6. **Verify**  
   **`explore:`** (breadcrumb + siblings + relationships), **`find:`**, **`validate:`** as appropriate.

---

## Node creation (schema v2)

- [ ] **`group`:** If omitted, tooling may **infer** from type via Validator **`auto_fix()`** — still verify in **`explore:`** that the group matches intent.
- [ ] **`description.info`:** REQUIRED human-readable meaning; do not ship empty info.
- [ ] **`lifecycle`:** Use **`draft`** until the artifact is specified/implemented per project convention.
- [ ] **`read_order`:** Defaults from schema per type if unset; override when the Brief requires emphasis (foundational vs background).

---

## ErrorCase import

- [ ] Read **ErrorDomain** (and related taxonomy) in the graph first: e.g. **`find: group="Error > ErrorDomain"`** or domain keyword.
- [ ] **`code`** format: **`{DOMAIN}_{SEVERITY}_{SEQ}`** — e.g. `GPS_E_001`, `AUTH_F_001` (see SCHEMA + AI User Guide).
- [ ] **`context`** (features, flows, engines) should be filled so retrieval matches real incidents.
- [ ] **`trigger`** must be concrete enough for later **`find:`** / **`explore:`**.
- [ ] Remediation / fix path documented per schema (e.g. **`fix`** or project-required fields) — do not leave “orphan” error rows with no actionable fix.

---

## Invariant import

- [ ] **`rule`** field is **REQUIRED** — must be a **boolean expression** over graph facts (see SCHEMA).
- [ ] Do **not** use **Invariant** for pure policy phrasing like “must never do X” — use **BusinessRule** (or the Brief’s designated type).
- [ ] Prefer explicit **`scope`** (`class` | `object` | `system`), **`enforcement`** (`hard` | `soft`), **`violation_action`** (`reject` | `devalue` | `flag` | `log`) when the schema asks for them.

---

## Post-import verify (schema v2)

- [ ] **`explore: node_id`** — **breadcrumb** matches intended **group** path.
- [ ] **`explore:`** — **siblings** in same group look reasonable (no accidental duplicates).
- [ ] **Relationships** show **`reason`** on edges where your process recorded it.
- [ ] **`validate:`** (metadata / all) — **zero** unexpected hard errors before handoff.

---

## Rules (non-negotiable)

| Rule | Detail |
|------|--------|
| No orphan-first | Do not bulk-create nodes and defer edges to a later step. |
| Relate when possible | If the graph is non-empty, new nodes must **relate** to existing ones (dec:d002). |
| First node exception | In a new project with no nodes yet, the first node may have no peer to attach to. |
| Template before volume | Use **`template_batch:`** when creating many similar nodes; fill placeholders, then batch. |
| Sequential discipline | Prefer clear ordering (e.g. decisions before dependents) to avoid dangling references. |

---

## Suggested batch shape (example)

Một `batch` có thể chứa **nhiều** dòng `create:` **khác type** (Engine, Flow, Decision, …) + `edge+:` — không bắt buộc mỗi lần chỉ một loại node. Xem `docs/GoBP_AI_USER_GUIDE.md` (mục *Template + batch đa loại*).

```text
batch session_id='…' ops='
  create: …
  create: …
  edge+: A --relates_to--> B
  …
'
```

---

## Related

- Locked decision: **dec:d002** (`topic: import.protocol`) in the GoBP graph.  
- AI query rules: **`docs/GoBP_AI_USER_GUIDE.md`**

◈
