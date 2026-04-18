# Import checklist — AI agents (GoBP)

**Purpose:** Enforce Decision **dec:d002** — *template → full read → plan (nodes + edges) → CEO review → batch*.  
**Audience:** Any AI importing external documents, specs, or spreadsheets into the GoBP graph.

---

## Before you start

- [ ] You have an active **`session:start`** (writes require `session_id`).
- [ ] You called **`template:`** or **`template_batch:`** for each node type you will create (know required fields).
- [ ] You have **`suggest:`** / **`find:`** results so new content can **relate to existing** nodes (skip only for the **first** substantive node in an empty project).

---

## Steps (in order)

1. **Read the entire source**  
   Read the **whole** document (or the whole agreed section), not fragments. Query Rule 12 in `GoBP_AI_USER_GUIDE.md`.

2. **List nodes and edges first (plan)**  
   - Every **node**: type, proposed name, minimal fields, intended **id** if fixed.  
   - Every **edge**: `from`, `to`, `type` — must be valid per `core_edges.yaml`.  
   - Do **not** create nodes first and “figure out edges later.”

3. **CEO review of the plan**  
   When the Brief or CEO requires it: stop and get approval before **`batch:`**.

4. **Batch execute**  
   Use **`batch:`** (or **`quick:`** delegating to batch). One batch should create nodes **and** edges together where possible.

5. **Relate new nodes (when graph already has data)**  
   Each new substantive node must have at least one edge to an **existing** node (or an edge path through a new node that itself connects back), except the **first** node in a greenfield graph. See Query Rule 11 in the AI User Guide.

6. **Verify**  
   **`explore:`** / **`find:`** / **`validate:`** as appropriate.

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

```text
batch session_id='…' ops='
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
