# WAVE 16A09 BRIEF — BATCH IMPORT + EXPLORE + SUGGEST + INPUT FRAMES

**Wave:** 16A09
**Title:** Batch import, explore action, suggest action, standardized input frames
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-17
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 7 tasks
**Estimated effort:** 5-6 hours

---

## CONTEXT

4 problems blocking efficient GoBP data entry:

**P1 — Nhập liệu tốn quá nhiều token**
```
Current: 30 engines = 60+ MCP calls = 30,000+ tokens
  find: check duplicate
  create: tạo node
  × 30 nodes

Need: 1 call tạo 30 nodes, auto dedupe
  batch_import → created: 28, skipped: 2 (duplicate)
  ~2000 tokens total
```

**P2 — Không có frame chuẩn cho input**
```
Current: AI tự đoán fields cần điền
  create:Engine name='X' → thiếu description, category, dependencies
  
Need: template: Engine → frame đầy đủ required + optional fields
  AI điền frame → batch submit → validated input
```

**P3 — Query 1 lần = 1 node, không thấy relationships**
```
Current: find → get → related → get target → 4+ calls
Need: explore: keyword → node + edges + neighbor summaries = 1 call
```

**P4 — AI không tìm được node reusable**
```
Current: AI build Payment Flow → không biết EmberEngine tồn tại
  → Tạo duplicate
Need: suggest: Payment Flow → keyword overlap → EmberEngine, EarningLedger
```

---

## DESIGN

### 1. template: action — Input frame per type

```
gobp(query="template: Engine")

Response:
{
  "ok": true,
  "type": "Engine",
  "group": "ops",
  "frame": {
    "required": {
      "name": {"type": "string", "example": "TrustGate Engine"},
      "description": {"type": "string", "example": "Trust scoring for all write operations"}
    },
    "optional": {
      "category": {"type": "enum", "values": ["identity", "core", "intelligence", "business", "infrastructure", "hardware"]},
      "input": {"type": "string", "example": "raw_score: float, context: dict"},
      "output": {"type": "string", "example": "trust_level: float, actions: list"},
      "depends_on": {"type": "list[string]", "description": "Names of engines this depends on"},
      "implements": {"type": "list[string]", "description": "Names of flows this implements"}
    }
  },
  "batch_format": "Engine: {name} | {description}",
  "hint": "Use batch_import to create multiple nodes at once"
}
```

Implementation: read from `core_nodes.yaml` schema + add examples per type.

### 2. batch_import action — Multi-node + multi-edge in 1 call

```
gobp(query="batch_import session_id='x'
  nodes:
    Engine: TrustGate | Trust scoring for write operations
    Engine: AuthEngine | Authentication and authorization
    Engine: EmberEngine | Revenue and payment
    Flow: Verify Gate | GPS verification at heritage sites
    Entity: Moment | Captured presence at a Place
  edges:
    TrustGate --depends_on--> CacheEngine
    AuthEngine --depends_on--> EncryptionEngine
    TrustGate --implements--> Mi Hốt Standard
")
```

Processing pipeline:

```
For each node in nodes:
  1. Parse: "Type: Name | Description"
  2. normalize_text(name)
  3. find_similar_nodes(name, threshold=80)
     Score >= 80 → SKIP + report duplicate_of: existing_id
     Score 60-79 → CREATE + WARNING similar_to: existing_id
     Score < 60  → CREATE clean
  4. If create: validate required fields per schema
  5. Generate ID (slug.group.number)
  6. Write to disk

For each edge in edges:
  1. Parse: "FromName --type--> ToName"
  2. Resolve names to IDs (from existing + just-created nodes)
  3. Check edge doesn't already exist
  4. Check edge type valid in schema
  5. Create edge

Response:
{
  "ok": true,
  "nodes_created": [
    {"id": "authengine.ops.00000001", "name": "AuthEngine", "type": "Engine"},
    {"id": "emberengine.ops.00000002", "name": "EmberEngine", "type": "Engine"},
    ...
  ],
  "nodes_skipped": [
    {"name": "TrustGate", "reason": "duplicate", "existing_id": "trustgate_engine.ops.06043392", "score": 95}
  ],
  "edges_created": [
    {"from": "authengine.ops.00000001", "to": "encryption_engine.ops.00000001", "type": "depends_on"}
  ],
  "edges_skipped": [
    {"from": "TrustGate", "to": "CacheEngine", "reason": "already exists"}
  ],
  "warnings": [],
  "summary": "nodes: 4 created, 1 skipped | edges: 2 created, 1 skipped"
}
```

### 3. explore: action — Node + edges + neighbors in 1 call

```
gobp(query="explore: TrustGate")

Response:
{
  "ok": true,
  "node": {
    "id": "trustgate_engine.ops.06043392",
    "type": "Engine",
    "name": "TrustGate Engine",
    "description": "Trust scoring engine for all write operations",
    "priority": "high",
    "edge_count": 12
  },
  "edges": [
    {
      "direction": "outgoing",
      "type": "implements",
      "target": {"id": "...", "name": "Mi Hốt Standard", "type": "Flow"}
    },
    {
      "direction": "outgoing",
      "type": "depends_on",
      "target": {"id": "...", "name": "GeoIntelligenceEngine", "type": "Engine"}
    },
    {
      "direction": "incoming",
      "type": "depends_on",
      "source": {"id": "...", "name": "EmberEngine", "type": "Engine"}
    }
  ],
  "also_found": [
    {"id": "trustgate.meta.53299456", "type": "Node", "name": "TrustGate", "edge_count": 0, "note": "potential duplicate"}
  ],
  "hint": "Use retype: or delete: to clean up duplicates"
}
```

Logic:
```
1. Search keyword → find best match (highest score)
2. Get that node's full edges
3. For each edge target/source: include mini summary (id, name, type)
4. also_found: other nodes matching keyword (potential duplicates)
5. 1 call replaces: find + get + related
```

### 4. suggest: action — Find reusable nodes by context

```
gobp(query="suggest: Payment Flow")

Response:
{
  "ok": true,
  "context": "Payment Flow",
  "suggestions": [
    {
      "id": "ember_engine.ops.00000001",
      "type": "Engine",
      "name": "EmberEngine",
      "why": "keyword: payment, revenue, ember",
      "relevance": "high"
    },
    {
      "id": "earning_ledger.domain.00000001",
      "type": "Entity",
      "name": "EarningLedger",
      "why": "keyword: ledger, earning, payment",
      "relevance": "high"
    },
    {
      "id": "sponsor_contract.domain.00000001",
      "type": "Entity",
      "name": "SponsorContract",
      "why": "keyword: contract, payment",
      "relevance": "medium"
    }
  ],
  "hint": "Consider creating edges to these existing nodes instead of new ones"
}
```

Logic:
```
1. Extract keywords from context: "Payment Flow" → ["payment", "flow"]
2. For each node in graph:
   - normalize_text(name + description)
   - Count keyword overlaps
   - Exclude exact matches (AI already knows about those)
3. Score by keyword overlap count
4. Return top 10 suggestions with "why" explanation
5. Exclude Session, Document types (metadata noise)
```

---

## CURSOR EXECUTION RULES

R1-R9 standard. R9: All 520 existing tests must pass after every task.

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status   # clean
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 520 tests passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Rules |
| 2 | `gobp/core/search.py` | Extend with suggest logic |
| 3 | `gobp/mcp/dispatcher.py` | Add explore/suggest/batch_import |
| 4 | `gobp/mcp/tools/read.py` | explore + suggest actions |
| 5 | `gobp/mcp/tools/write.py` | batch_import action |
| 6 | `gobp/mcp/parser.py` | Parse batch_import format |
| 7 | `gobp/schema/core_nodes.yaml` | template: reads from here |
| 8 | `waves/wave_16a09_brief.md` | This file |

---

# TASKS

---

## TASK 1 — template: action

**Goal:** Return input frame per node type with required/optional fields.

**File to modify:** `gobp/mcp/tools/read.py`

Add `template_action()`:

```python
async def template_action(index, project_root, args):
    """Return input frame for a node type.
    
    Query: template: Engine
    """
    node_type = args.get("query", "").strip() or args.get("type", "")
    
    # Read from schema
    schema = index._nodes_schema
    type_def = schema.get("node_types", {}).get(node_type)
    
    if not type_def:
        return {"ok": False, "error": f"Unknown type: {node_type}",
                "available": list(schema.get("node_types", {}).keys())}
    
    required = {}
    for field, spec in type_def.get("required", {}).items():
        if field in ("id", "type", "created", "updated", "status"):
            continue  # auto-generated
        required[field] = {
            "type": spec.get("type", "string"),
        }
        if spec.get("enum_values"):
            required[field]["values"] = spec["enum_values"]
        if spec.get("description"):
            required[field]["description"] = spec["description"]
    
    optional = {}
    for field, spec in type_def.get("optional", {}).items():
        optional[field] = {
            "type": spec.get("type", "string"),
        }
        if spec.get("enum_values"):
            optional[field]["values"] = spec["enum_values"]
        if spec.get("description"):
            optional[field]["description"] = spec["description"]
        if spec.get("default") is not None:
            optional[field]["default"] = spec["default"]
    
    # Get group info
    from gobp.core.id_config import DEFAULT_GROUPS
    group = "meta"
    for g, info in DEFAULT_GROUPS.items():
        if node_type in info.get("types", []):
            group = g
            break
    
    return {
        "ok": True,
        "type": node_type,
        "group": group,
        "frame": {
            "required": required,
            "optional": optional,
        },
        "batch_format": f"{node_type}: {{name}} | {{description}}",
        "batch_example": f"{node_type}: ExampleName | Short description of what this does",
        "hint": "Use batch_import to create multiple nodes. Use explore: to check existing nodes first.",
    }
```

**File to modify:** `gobp/mcp/dispatcher.py`

Add routing:
```python
        elif action == "template":
            result = await tools_read.template_action(index, project_root, params)
```

**Update PROTOCOL_GUIDE:**
```python
"template: Engine":          "Input frame for Engine type (required/optional fields)",
"template: Flow":            "Input frame for Flow type",
"template: Entity":          "Input frame for Entity type",
```

**Commit message:**
```
Wave 16A09 Task 1: template: action — input frame per node type

- read.py: template_action() reads schema, returns required/optional fields
- dispatcher.py: template: routing
- PROTOCOL_GUIDE: template: examples
- AI knows exactly what fields to fill before creating nodes
```

---

## TASK 2 — explore: action

**Goal:** 1 request → node + all edges + neighbor summaries + duplicates.

**File to modify:** `gobp/mcp/tools/read.py`

Add `explore_action()`:

```python
async def explore_action(index, project_root, args):
    """Explore a node: details + all edges + neighbors in 1 call.
    
    Query: explore: TrustGate
    Replaces: find + get + related (3 calls → 1 call)
    """
    query = args.get("query", "").strip()
    if not query:
        return {"ok": False, "error": "Query required"}
    
    from gobp.core.search import search_nodes, normalize_text
    
    # Find best match
    results = search_nodes(index, query, exclude_types=["Session"], limit=10)
    if not results:
        return {"ok": False, "error": f"No nodes found for: {query}",
                "hint": "Try different keywords or use find: for broader search"}
    
    # Best match = highest score
    best_score, best_node = results[0]
    node_id = best_node.get("id")
    
    # Get edges for best node
    all_edges = index.all_edges() if hasattr(index, 'all_edges') else []
    edges_out = []
    edges_in = []
    
    for edge in all_edges:
        edge_type = edge.get("type", "relates_to")
        if edge_type == "discovered_in":
            continue  # skip metadata edges
        
        if edge.get("from") == node_id:
            target = index.get_node(edge.get("to"))
            if target:
                edges_out.append({
                    "direction": "outgoing",
                    "type": edge_type,
                    "target": {
                        "id": target.get("id"),
                        "name": target.get("name", ""),
                        "type": target.get("type", ""),
                    }
                })
        elif edge.get("to") == node_id:
            source = index.get_node(edge.get("from"))
            if source:
                edges_in.append({
                    "direction": "incoming",
                    "type": edge_type,
                    "source": {
                        "id": source.get("id"),
                        "name": source.get("name", ""),
                        "type": source.get("type", ""),
                    }
                })
    
    # Also found (other matches = potential duplicates)
    also_found = []
    for score, node in results[1:5]:
        also_found.append({
            "id": node.get("id"),
            "type": node.get("type", ""),
            "name": node.get("name", ""),
            "edge_count": node.get("edge_count", 0),
            "note": "potential duplicate" if score >= 80 else "related",
        })
    
    return {
        "ok": True,
        "node": {
            "id": node_id,
            "type": best_node.get("type", ""),
            "name": best_node.get("name", ""),
            "description": best_node.get("description", ""),
            "priority": best_node.get("priority", ""),
        },
        "edges": edges_out + edges_in,
        "edge_count": len(edges_out) + len(edges_in),
        "also_found": also_found,
        "hint": "Use retype: or delete: to clean duplicates. Use edge: to add relationships.",
    }
```

**Add routing in dispatcher.py:**
```python
        elif action == "explore":
            result = await tools_read.explore_action(index, project_root, params)
```

**Update PROTOCOL_GUIDE:**
```python
"explore: TrustGate":      "Node + edges + neighbors in 1 call (replaces find+get+related)",
"explore: Mi Hốt":         "Vietnamese search + full context in 1 call",
```

**Commit message:**
```
Wave 16A09 Task 2: explore: action — node + edges + neighbors in 1 call

- read.py: explore_action() replaces find + get + related
- Skips discovered_in edges (metadata noise)
- also_found: shows potential duplicates
- 1 call, ~800 tokens vs 3+ calls, ~3000 tokens
```

---

## TASK 3 — suggest: action

**Goal:** Find reusable nodes by keyword overlap from context.

**File to modify:** `gobp/core/search.py`

Add `suggest_related()`:

```python
def suggest_related(
    index: "GraphIndex",
    context: str,
    exclude_types: list[str] | None = None,
    limit: int = 10,
) -> list[dict]:
    """Find nodes that might be related to a context/task.
    
    Extracts keywords from context, scores nodes by keyword overlap.
    Helps AI discover existing nodes to reuse instead of creating duplicates.
    
    Args:
        index: GraphIndex
        context: Task description or node name (e.g. "Payment Flow")
        exclude_types: Types to exclude (default: Session, Document)
        limit: Max suggestions
    
    Returns:
        List of {id, type, name, why, relevance} dicts
    """
    if exclude_types is None:
        exclude_types = ["Session", "Document"]
    
    exclude_set = set(exclude_types)
    
    # Extract keywords from context
    context_norm = normalize_text(context)
    # Split into words, filter short words
    keywords = [w for w in context_norm.split() if len(w) >= 3]
    
    if not keywords:
        return []
    
    suggestions = []
    
    for node in index.all_nodes():
        node_type = node.get("type", "")
        if node_type in exclude_set:
            continue
        
        name = node.get("name", "")
        desc = node.get("description", "")
        node_text = normalize_text(f"{name} {desc}")
        
        # Count keyword overlaps
        matched_keywords = [kw for kw in keywords if kw in node_text]
        
        if not matched_keywords:
            continue
        
        # Score: more keywords matched = more relevant
        overlap_score = len(matched_keywords) / len(keywords)
        
        # Boost if keyword in name (not just description)
        name_norm = normalize_text(name)
        name_matches = [kw for kw in keywords if kw in name_norm]
        if name_matches:
            overlap_score += 0.3
        
        relevance = "high" if overlap_score >= 0.6 else "medium" if overlap_score >= 0.3 else "low"
        
        suggestions.append({
            "id": node.get("id"),
            "type": node_type,
            "name": name,
            "why": f"keyword: {', '.join(matched_keywords)}",
            "relevance": relevance,
            "_score": overlap_score,
        })
    
    # Sort by score descending
    suggestions.sort(key=lambda s: -s["_score"])
    
    # Remove internal score
    for s in suggestions:
        del s["_score"]
    
    return suggestions[:limit]
```

**File to modify:** `gobp/mcp/tools/read.py`

Add `suggest_action()`:

```python
async def suggest_action(index, project_root, args):
    """Suggest reusable nodes based on context keywords.
    
    Query: suggest: Payment Flow
    """
    context = args.get("query", "").strip()
    if not context:
        return {"ok": False, "error": "Context required. Example: suggest: Payment Flow"}
    
    from gobp.core.search import suggest_related
    
    suggestions = suggest_related(index, context, limit=10)
    
    return {
        "ok": True,
        "context": context,
        "suggestions": suggestions,
        "count": len(suggestions),
        "hint": "Consider creating edges to these nodes. Use explore: {name} for details.",
    }
```

**Add routing + PROTOCOL_GUIDE.**

**Commit message:**
```
Wave 16A09 Task 3: suggest: action — find reusable nodes by context

- search.py: suggest_related() keyword overlap scoring
- read.py: suggest_action() returns reusable node suggestions
- suggest: Payment Flow → EmberEngine, EarningLedger
- Prevents duplicate creation by showing existing related nodes
```

---

## TASK 4 — batch_import action

**Goal:** Create many nodes + edges in 1 request with auto dedupe.

**File to modify:** `gobp/mcp/tools/write.py`

Add `batch_import_action()`:

```python
async def batch_import_action(index, project_root, args):
    """Create multiple nodes and edges in 1 request.
    
    Input format (in params):
      nodes: list of "Type: Name | Description"
      edges: list of "FromName --type--> ToName"
      session_id: required
    
    Auto duplicate detection per node.
    Auto edge validation (both endpoints exist, type valid).
    """
    session_id = args.get("session_id", "")
    if not session_id:
        return {"ok": False, "error": "session_id required"}
    
    # Verify session
    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}
    
    nodes_raw = args.get("nodes", "")
    edges_raw = args.get("edges", "")
    
    # Parse nodes: "Type: Name | Description"
    node_lines = [l.strip() for l in nodes_raw.split("\n") if l.strip() and ":" in l]
    edge_lines = [l.strip() for l in edges_raw.split("\n") if l.strip() and "--" in l]
    
    from gobp.core.search import find_similar_nodes, normalize_text
    from gobp.core.graph import GraphIndex
    
    nodes_created = []
    nodes_skipped = []
    warnings = []
    
    # Track names → IDs for edge resolution
    name_to_id = {}
    
    for line in node_lines:
        try:
            # Parse "Type: Name | Description"
            type_part, rest = line.split(":", 1)
            node_type = type_part.strip()
            
            if "|" in rest:
                name_part, desc_part = rest.split("|", 1)
            else:
                name_part = rest
                desc_part = ""
            
            name = name_part.strip()
            description = desc_part.strip()
            
            if not name:
                warnings.append({"line": line, "error": "empty name"})
                continue
            
            # Dedupe check
            similar = find_similar_nodes(index, name, node_type, threshold=80)
            
            if similar:
                best = similar[0]
                nodes_skipped.append({
                    "name": name,
                    "reason": "duplicate",
                    "existing_id": best.get("id"),
                    "existing_name": best.get("name"),
                })
                # Map name to existing ID for edges
                name_to_id[normalize_text(name)] = best.get("id")
                continue
            
            # Create node
            from gobp.mcp.dispatcher import dispatch
            query = f"create:{node_type} name='{name}' description='{description}' session_id='{session_id}'"
            
            # Reload index for each create to get latest state
            fresh_index = GraphIndex.load_from_disk(project_root)
            result = await dispatch(query, fresh_index, project_root)
            
            if result.get("ok"):
                node_id = result.get("node_id")
                nodes_created.append({
                    "id": node_id,
                    "name": name,
                    "type": node_type,
                })
                name_to_id[normalize_text(name)] = node_id
            else:
                warnings.append({"line": line, "error": result.get("error", "create failed")})
                
        except Exception as e:
            warnings.append({"line": line, "error": str(e)})
    
    # Reload index after all nodes created
    index = GraphIndex.load_from_disk(project_root)
    
    # Build full name→id map from all nodes
    for node in index.all_nodes():
        name_norm = normalize_text(node.get("name", ""))
        if name_norm and name_norm not in name_to_id:
            name_to_id[name_norm] = node.get("id")
    
    edges_created = []
    edges_skipped = []
    
    for line in edge_lines:
        try:
            # Parse "FromName --type--> ToName"
            import re
            match = re.match(r'(.+?)\s*--(\w+)-->\s*(.+)', line)
            if not match:
                warnings.append({"line": line, "error": "invalid edge format"})
                continue
            
            from_name = match.group(1).strip()
            edge_type = match.group(2).strip()
            to_name = match.group(3).strip()
            
            # Resolve names to IDs
            from_norm = normalize_text(from_name)
            to_norm = normalize_text(to_name)
            
            from_id = name_to_id.get(from_norm)
            to_id = name_to_id.get(to_norm)
            
            if not from_id:
                warnings.append({"line": line, "error": f"from node not found: {from_name}"})
                continue
            if not to_id:
                warnings.append({"line": line, "error": f"to node not found: {to_name}"})
                continue
            
            # Create edge
            edge_query = f"edge: {from_id} --{edge_type}--> {to_id}"
            fresh_index = GraphIndex.load_from_disk(project_root)
            result = await dispatch(edge_query, fresh_index, project_root)
            
            if result.get("ok"):
                edges_created.append({
                    "from": from_id,
                    "to": to_id,
                    "type": edge_type,
                })
            elif "already exists" in str(result.get("error", "")).lower() or \
                 "idempotent" in str(result.get("action", "")).lower():
                edges_skipped.append({
                    "from": from_name,
                    "to": to_name,
                    "reason": "already exists",
                })
            else:
                warnings.append({"line": line, "error": result.get("error", "edge create failed")})
                
        except Exception as e:
            warnings.append({"line": line, "error": str(e)})
    
    summary = f"nodes: {len(nodes_created)} created, {len(nodes_skipped)} skipped | edges: {len(edges_created)} created, {len(edges_skipped)} skipped"
    
    return {
        "ok": True,
        "nodes_created": nodes_created,
        "nodes_skipped": nodes_skipped,
        "edges_created": edges_created,
        "edges_skipped": edges_skipped,
        "warnings": warnings,
        "summary": summary,
    }
```

**File to modify:** `gobp/mcp/parser.py`

Add batch_import parsing — the `nodes:` and `edges:` params need to be parsed as multi-line blocks:

```python
# In parse_query, handle batch_import params:
# batch_import session_id='x' nodes='...' edges='...'
# Or: nodes and edges passed as separate params
```

**File to modify:** `gobp/mcp/dispatcher.py`

Add routing:
```python
        elif action == "batch_import":
            result = await tools_write.batch_import_action(index, project_root, params)
```

**Update PROTOCOL_GUIDE:**
```python
"batch_import session_id='x' nodes='Engine: TrustGate | Trust scoring\\nFlow: Verify Gate | GPS verification' edges='TrustGate --implements--> Mi Hốt Standard'":
    "Create multiple nodes + edges in 1 call with auto dedupe",
```

**Commit message:**
```
Wave 16A09 Task 4: batch_import action — multi-node + multi-edge in 1 call

- write.py: batch_import_action() parses Type: Name | Desc format
- Auto dedupe: score >= 80 → skip + report existing
- Edge resolution by name (not ID) — resolves from existing + just-created
- 1 call replaces 60+ individual calls
```

---

## TASK 5 — Smoke test

```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from pathlib import Path
from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch
import tempfile, shutil

async def test():
    tmp = Path(tempfile.mkdtemp())
    try:
        init_project(tmp)
        index = GraphIndex.load_from_disk(tmp)
        
        # Start session
        sess = await dispatch('session:start actor=test goal=batch-test', index, tmp)
        sid = sess['session_id']
        
        # Test template:
        index = GraphIndex.load_from_disk(tmp)
        r1 = await dispatch('template: Engine', index, tmp)
        assert r1['ok'], f'template failed: {r1}'
        assert 'frame' in r1
        assert 'required' in r1['frame']
        print(f'template: Engine OK — {len(r1[\"frame\"][\"required\"])} required fields')
        
        # Test batch_import
        index = GraphIndex.load_from_disk(tmp)
        r2 = await dispatch(
            f\"batch_import session_id='{sid}' nodes='Engine: TestEngine | A test engine\\nFlow: TestFlow | A test flow' edges='TestEngine --implements--> TestFlow'\",
            index, tmp
        )
        assert r2['ok'], f'batch_import failed: {r2}'
        print(f'batch_import: {r2[\"summary\"]}')
        
        # Test explore:
        index = GraphIndex.load_from_disk(tmp)
        r3 = await dispatch('explore: TestEngine', index, tmp)
        assert r3['ok'], f'explore failed: {r3}'
        print(f'explore: found {r3[\"edge_count\"]} edges')
        
        # Test suggest:
        index = GraphIndex.load_from_disk(tmp)
        r4 = await dispatch('suggest: test engine flow', index, tmp)
        assert r4['ok'], f'suggest failed: {r4}'
        print(f'suggest: {r4[\"count\"]} suggestions')
        
        # Test dedupe in batch_import
        index = GraphIndex.load_from_disk(tmp)
        r5 = await dispatch(
            f\"batch_import session_id='{sid}' nodes='Engine: TestEngine | Duplicate test'\",
            index, tmp
        )
        assert r5['ok']
        assert len(r5['nodes_skipped']) > 0, f'Expected duplicate skip, got: {r5}'
        print(f'dedupe: {len(r5[\"nodes_skipped\"])} skipped')
        
        print('ALL SMOKE TESTS PASSED')
    finally:
        shutil.rmtree(tmp)

asyncio.run(test())
"

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 520 tests passing
```

**Commit message:**
```
Wave 16A09 Task 5: smoke test — template + batch_import + explore + suggest

- template: Engine returns frame with required/optional fields
- batch_import: 2 nodes + 1 edge in 1 call
- explore: node + edges in 1 call
- suggest: keyword overlap suggestions
- batch_import dedupe: skips duplicate nodes
- 520 tests passing
```

---

## TASK 6 — Tests

**File to create:** `tests/test_wave16a09.py`

```python
"""Tests for Wave 16A09: batch_import, explore, suggest, template."""

from __future__ import annotations
import asyncio
from pathlib import Path
import pytest

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.core.search import suggest_related
from gobp.mcp.dispatcher import dispatch


@pytest.fixture
def proj(tmp_path):
    init_project(tmp_path)
    return tmp_path


def _sid(proj):
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("session:start actor='t' goal='t'", index, proj))
    return r["session_id"]


# ── template: tests ───────────────────────────────────────────────────────────

def test_template_returns_frame(proj):
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template: Engine", index, proj))
    assert r["ok"]
    assert "frame" in r
    assert "required" in r["frame"]
    assert "name" in r["frame"]["required"]


def test_template_invalid_type(proj):
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template: FakeType", index, proj))
    assert not r["ok"]
    assert "available" in r


def test_template_has_batch_format(proj):
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("template: Flow", index, proj))
    assert "batch_format" in r


# ── explore: tests ────────────────────────────────────────────────────────────

def test_explore_returns_node_and_edges(proj):
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(dispatch(f"create:Engine name='EngA' session_id={sid}", index, proj))
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(dispatch(f"create:Flow name='FlowB' session_id={sid}", index, proj))
    index = GraphIndex.load_from_disk(proj)
    
    # Get IDs
    r1 = asyncio.run(dispatch("find: EngA mode=summary", index, proj))
    r2 = asyncio.run(dispatch("find: FlowB mode=summary", index, proj))
    if r1["matches"] and r2["matches"]:
        id_a = r1["matches"][0]["id"]
        id_b = r2["matches"][0]["id"]
        asyncio.run(dispatch(f"edge: {id_a} --implements--> {id_b}", index, proj))
    
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("explore: EngA", index, proj))
    assert r["ok"]
    assert "node" in r
    assert "edges" in r


def test_explore_not_found(proj):
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("explore: NonExistent", index, proj))
    assert not r["ok"]


def test_explore_shows_duplicates(proj):
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(dispatch(f"create:Engine name='TrustGate' session_id={sid}", index, proj))
    asyncio.run(dispatch(f"create:Node name='TrustGate Copy' session_id={sid}", index, proj))
    
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("explore: TrustGate", index, proj))
    assert r["ok"]
    assert len(r.get("also_found", [])) >= 1


# ── suggest: tests ────────────────────────────────────────────────────────────

def test_suggest_finds_related(proj):
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(dispatch(
        f"create:Engine name='EmberEngine' description='payment and revenue processing' session_id={sid}",
        index, proj
    ))
    
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("suggest: payment flow", index, proj))
    assert r["ok"]
    assert r["count"] >= 1
    names = [s["name"] for s in r["suggestions"]]
    assert any("Ember" in n for n in names)


def test_suggest_empty(proj):
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("suggest: xyznonexistent", index, proj))
    assert r["ok"]
    assert r["count"] == 0


def test_suggest_excludes_sessions(proj):
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch("suggest: test session", index, proj))
    types = {s["type"] for s in r.get("suggestions", [])}
    assert "Session" not in types


# ── batch_import tests ────────────────────────────────────────────────────────

def test_batch_import_creates_nodes(proj):
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch(
        f"batch_import session_id='{sid}' nodes='Engine: BatchEng1 | Test engine one\\nFlow: BatchFlow1 | Test flow one'",
        index, proj
    ))
    assert r["ok"]
    assert len(r["nodes_created"]) == 2


def test_batch_import_skips_duplicates(proj):
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(dispatch(f"create:Engine name='ExistingEng' session_id={sid}", index, proj))
    
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch(
        f"batch_import session_id='{sid}' nodes='Engine: ExistingEng | Should be skipped'",
        index, proj
    ))
    assert r["ok"]
    assert len(r["nodes_skipped"]) >= 1


def test_batch_import_creates_edges(proj):
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch(
        f"batch_import session_id='{sid}' nodes='Engine: EdgeTestA | Eng A\\nFlow: EdgeTestB | Flow B' edges='EdgeTestA --implements--> EdgeTestB'",
        index, proj
    ))
    assert r["ok"]
    assert len(r["edges_created"]) >= 1


def test_batch_import_no_session_fails(proj):
    index = GraphIndex.load_from_disk(proj)
    r = asyncio.run(dispatch(
        "batch_import nodes='Engine: NoSession | Test'",
        index, proj
    ))
    assert not r["ok"]
    assert "session" in r["error"].lower()


# ── suggest_related unit tests ────────────────────────────────────────────────

def test_suggest_related_keyword_overlap(proj):
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    asyncio.run(dispatch(
        f"create:Entity name='EarningLedger' description='tracks payment earnings' session_id={sid}",
        index, proj
    ))
    
    index = GraphIndex.load_from_disk(proj)
    results = suggest_related(index, "payment ledger tracking")
    assert len(results) >= 1
    names = [r["name"] for r in results]
    assert any("Earning" in n or "Ledger" in n for n in names)


def test_suggest_related_excludes_session(proj):
    sid = _sid(proj)
    index = GraphIndex.load_from_disk(proj)
    results = suggest_related(index, "test session goal")
    types = {r["type"] for r in results}
    assert "Session" not in types


# ── PROTOCOL_GUIDE tests ──────────────────────────────────────────────────────

def test_protocol_guide_has_new_actions():
    from gobp.mcp.parser import PROTOCOL_GUIDE
    actions = PROTOCOL_GUIDE.get("actions", {})
    assert any("template:" in k for k in actions)
    assert any("explore:" in k for k in actions)
    assert any("suggest:" in k for k in actions)
    assert any("batch_import" in k for k in actions)
```

**Commit message:**
```
Wave 16A09 Task 6: tests/test_wave16a09.py — 18 tests

- template: 3 tests (frame, invalid type, batch_format)
- explore: 3 tests (node+edges, not found, duplicates)
- suggest: 3 tests (related, empty, session exclusion)
- batch_import: 4 tests (create, dedupe, edges, no session)
- suggest_related: 2 tests (keyword, session exclude)
- PROTOCOL_GUIDE: 1 test
- 538+ tests total
```

---

## TASK 7 — CHANGELOG + full suite

**Update CHANGELOG.md:**

```markdown
## [Wave 16A09] — Batch Import + Explore + Suggest + Input Frames — 2026-04-17

### Added
- **template: action** — input frame per node type
  - Returns required/optional fields from schema
  - Shows batch_format for batch_import
  - AI knows exactly what to fill before creating

- **explore: action** — 1 call replaces find + get + related
  - Node details + all edges + neighbor summaries
  - Skips discovered_in metadata edges
  - Shows potential duplicates (also_found)
  - Saves ~70% tokens vs 3 separate calls

- **suggest: action** — find reusable nodes by context
  - Keyword overlap scoring from context description
  - Prevents duplicate creation
  - "suggest: Payment Flow" → EmberEngine, EarningLedger

- **batch_import action** — create N nodes + M edges in 1 call
  - Format: "Type: Name | Description" per line
  - Auto dedupe: score >= 80 → skip + report existing
  - Edge resolution by name (not ID)
  - 1 call replaces 60+ individual calls

### Changed
- search.py: suggest_related() function
- dispatcher.py: template/explore/suggest/batch_import routing
- parser.py: PROTOCOL_GUIDE entries

### Total: 538+ tests
```

**Run:**
```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 538+ tests
```

**Commit message:**
```
Wave 16A09 Task 7: CHANGELOG + full suite 538+ tests

- CHANGELOG: Wave 16A09 entry
- All 538+ tests passing
```

---

# CEO DISPATCH INSTRUCTIONS

## 1. Save Brief

```powershell
cd D:\GoBP
# Save to D:\GoBP\waves\wave_16a09_brief.md
git add waves/wave_16a09_brief.md
git commit -m "Add Wave 16A09 Brief — batch import + explore + suggest + input frames"
git push origin main
```

## 2. Dispatch Cursor

```
Read .cursorrules and waves/wave_16a09_brief.md first.
Also read gobp/core/search.py, gobp/mcp/tools/read.py,
gobp/mcp/tools/write.py, gobp/mcp/dispatcher.py,
gobp/mcp/parser.py, gobp/schema/core_nodes.yaml.

Set env:
  $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute ALL 7 tasks sequentially.
R9: all 520 existing tests must pass after every task.
1 task = 1 commit, exact message.
Begin Task 1.
```

## 3. Audit Claude CLI

```
Audit Wave 16A09. Read CLAUDE.md and waves/wave_16a09_brief.md.
Set env: $env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Critical verification:
- Task 1: template: Engine returns frame with required/optional fields
- Task 2: explore: TrustGate → node + edges + also_found in 1 call
          discovered_in edges excluded
- Task 3: suggest: Payment Flow → EmberEngine, EarningLedger (keyword overlap)
          Session/Document excluded
- Task 4: batch_import: Type: Name | Desc format
          Auto dedupe score >= 80 → skip
          Edge resolution by name
- Task 5: Smoke test on temp project — all 4 actions work
- Task 6: test_wave16a09.py 18 tests
- Task 7: CHANGELOG, 538+ total tests

BLOCKING RULE: Gặp vấn đề → DỪNG ngay, báo CEO.

Expected: 538+ tests. Report WAVE 16A09 AUDIT COMPLETE.
```

---

*Wave 16A09 Brief v1.0*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-17*

◈
