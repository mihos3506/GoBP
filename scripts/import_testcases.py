"""
Import all TestCase nodes across waves into GoBP.
Usage: GOBP_DB_URL=... PYTHONUTF8=1 python scripts/import_testcases.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch

ROOT = Path("D:/GoBP")
SID = ""  # will be set after session:start

ok_count = 0
fail_count = 0


async def q(query: str, index: GraphIndex) -> dict:
    return await dispatch(query, index, ROOT)


def reload() -> GraphIndex:
    return GraphIndex.load_from_disk(ROOT)


async def create_node(type_: str, fields: dict, index: GraphIndex, explicit_id: str = "") -> tuple[str, GraphIndex]:
    """Create/upsert a node. explicit_id sets the id field directly."""
    global ok_count, fail_count

    # If explicit_id given, check if node already exists
    if explicit_id:
        existing = index.get_node(explicit_id)
        if existing:
            ok_count += 1
            print(f"    EXISTS {type_} {explicit_id}: {existing.get('name','')[:55]}")
            return explicit_id, index
        # Use create: with explicit id
        id_field = f"id='{explicit_id}' "
        field_str = id_field + " ".join(f"{k}='{v}'" for k, v in fields.items())
        query = f"create:{type_} {field_str} session_id='{SID}'"
    else:
        field_str = " ".join(f"{k}='{v}'" for k, v in fields.items())
        query = f"upsert:{type_} dedupe_key='name' {field_str} session_id='{SID}'"

    r = await q(query, index)
    index = reload()
    if r.get("ok"):
        node_id = r.get("id") or r.get("node_id") or explicit_id or "?"
        ok_count += 1
        print(f"    OK {type_} {node_id}: {fields.get('name','')[:55]}")
        return node_id, index
    else:
        fail_count += 1
        errs = r.get("errors") or r.get("error") or "unknown"
        print(f"    FAIL {type_} '{fields.get('name','')}': {errs}")
        return "", index


async def add_edge(from_id: str, etype: str, to_id: str, reason: str, index: GraphIndex) -> GraphIndex:
    global ok_count, fail_count
    r = await q(f"edge: {from_id} --{etype}--> {to_id} reason='{reason}' session_id='{SID}'", index)
    index = reload()
    if r.get("ok"):
        ok_count += 1
    else:
        fail_count += 1
        print(f"    EDGE FAIL {from_id}--{etype}-->{to_id}: {r.get('error','?')}")
    return index


async def create_testcase(
    tc_name: str,
    description: str,
    kind_id: str,
    covers_id: str,
    wave_id: str,
    priority: str,
    index: GraphIndex,
) -> GraphIndex:
    tc_id, index = await create_node("TestCase", {
        "name": tc_name,
        "status": "READY",
        "kind_id": kind_id,
        "covers": covers_id,
        "description": description[:120],
        "priority": priority,
    }, index)
    if not tc_id:
        return index
    index = await add_edge(tc_id, "of_kind", kind_id, "testcase belongs to test kind", index)
    index = await add_edge(tc_id, "covers", covers_id, "testcase validates target behavior", index)
    index = await add_edge(tc_id, "relates_to", wave_id, "testcase belongs to wave", index)
    return index


# ── CATALOG ───────────────────────────────────────────────────────────────────
# (wave, feature_key, feature_name, feature_desc,
#  tc_name, tc_desc, tc_kind, priority)

CATALOG = [
    # WAVE 4
    ("4","init_project_structure",
     "init_project creates directory structure",
     "init_project() creates nodes/ edges/ config.yaml with schema_version=2",
     "Project initialization",
     "init_project creates .gobp dirs and schema_version=2","unit","high"),

    ("4","init_seeded_nodes",
     "Initialization with 17 seeded nodes",
     "gobp init seeds 17 nodes: 16 TestKind + 1 Concept with all groups and scope",
     "Init seeded nodes",
     "init seeds 17 nodes with all groups and universal scope","unit","high"),

    ("4","init_idempotency",
     "Initialization idempotency guard",
     "init_project raises on existing .gobp/; force=True reinitializes",
     "Init idempotency",
     "init fails on existing project; force=True reinitializes","unit","medium"),

    ("4","find_type_filter",
     "find() type filtering",
     "find() action filters results by node type via type= parameter",
     "find type filter",
     "find() returns only nodes matching requested type","unit","high"),

    ("4","gobp_overview_concepts",
     "gobp_overview concepts and test_coverage",
     "gobp_overview returns concepts array and test_coverage with kinds by category",
     "overview concepts and coverage",
     "overview returns concepts array and test_coverage breakdown","unit","medium"),

    ("4","cli_commands",
     "CLI commands init status validate",
     "CLI gobp init/status/validate commands run correctly via subprocess",
     "CLI commands",
     "CLI init status validate commands produce correct output","integration","medium"),

    # WAVE 10B
    ("10b","session_id_generation",
     "Session ID generation",
     "_generate_session_id() produces 28-char IDs with session:20 prefix",
     "Session ID generation",
     "_generate_session_id creates unique 28-char IDs","unit","medium"),

    ("10b","unicode_handling",
     "Unicode text handling in YAML",
     "Node YAML files store unicode as UTF-8 without escape sequences",
     "Unicode YAML encoding",
     "Node files store unicode as UTF-8 not escaped","unit","medium"),

    ("10b","priority_field",
     "Priority field in node schema",
     "Node and Decision types have optional priority field; create: accepts it",
     "Priority field",
     "schema has priority field; create: stores it","unit","high"),

    ("10b","document_priority_classification",
     "Document priority auto-classification",
     "_classify_doc_priority() detects critical/high/low from content and filename",
     "Document priority classification",
     "_classify_doc_priority detects priority from content","unit","high"),

    ("10b","auto_id_generation",
     "Auto-generated node IDs",
     "create: auto-generates collision-proof IDs when id not provided",
     "Auto-generated node IDs",
     "create: auto-generates IDs when not provided","unit","medium"),

    ("10b","edge_creation",
     "edge: action with arrow syntax",
     "edge: creates edges using node:a --type--> node:b syntax with optional reason",
     "edge: action",
     "edge: creates edges with arrow syntax and reason","integration","high"),

    ("10b","import_document",
     "import: creates Document node with priority",
     "import: creates Document node with sections and priority classification",
     "import: document creation",
     "import: creates Document node with priority and sections","integration","high"),

    # WAVE 11A
    ("11a","code_refs_field",
     "code_refs field in schema",
     "Node and Decision types have optional code_refs list for code location links",
     "code_refs schema field",
     "schema has code_refs list field on Node and Decision","unit","medium"),

    ("11a","invariants_field",
     "invariants field in schema",
     "Node and Decision types have optional invariants list for system constraints",
     "invariants schema field",
     "schema has invariants list field","unit","medium"),

    ("11a","lazy_query_parsing",
     "Lazy query actions parsing",
     "parse_query handles code: invariants: tests: related: actions",
     "Lazy query actions parsing",
     "parse_query routes code/invariants/tests/related actions","unit","high"),

    ("11a","code_refs_read",
     "code: read action",
     "code() returns code references with path description language for a node",
     "code: read action",
     "code() returns code_refs list for a node","unit","high"),

    ("11a","invariants_read",
     "invariants: read action",
     "node_invariants() returns system constraints and business rules",
     "invariants: read action",
     "invariants() returns invariants list for a node","unit","medium"),

    ("11a","node_tests_read",
     "tests: read action",
     "node_tests() returns test coverage summary with passing/failing counts",
     "tests: read action",
     "tests() returns test coverage summary for a node","unit","medium"),

    ("11a","node_related_read",
     "related: read action",
     "node_related() returns incoming/outgoing edges with direction filter",
     "related: read action",
     "related() returns edges with direction filter support","unit","high"),

    ("11a","lazy_actions_dispatch",
     "Lazy actions dispatch integration",
     "dispatch integrates code: invariants: tests: related: from read tools",
     "Lazy actions dispatch",
     "dispatch routes code/invariants/tests/related to read tools","integration","high"),

    # WAVE 14
    ("14","protocol_version_action",
     "version: protocol version action",
     "version: returns protocol_version=2.0 gobp_version schema_version changelog",
     "version: action",
     "version: returns protocol_version=2.0 with changelog","unit","high"),

    ("14","schema_governance_score",
     "Schema governance scoring",
     "schema_governance() returns score 0-100 with issues list and summary",
     "Schema governance score",
     "validate: schema-docs returns score 0-100 with issues","unit","high"),

    ("14","validate_schema_docs",
     "validate: schema-docs dispatch",
     "validate: schema-docs routes to schema_governance(); validate: all unchanged",
     "validate: schema-docs",
     "validate: schema-docs cross-checks schema vs SCHEMA.md","integration","high"),

    ("14","session_role_field",
     "Session role field storage",
     "session:start accepts role observer/contributor/admin stored in session node",
     "Session role field",
     "session:start stores role field for audit trail","integration","medium"),

    ("14","read_only_mode_flag",
     "Read-only mode flag enforcement",
     "_READ_ONLY blocks write actions when GOBP_READ_ONLY=true",
     "Read-only mode flag",
     "GOBP_READ_ONLY=true blocks write actions with clear error","unit","high"),

    ("14","template_action",
     "template: NodeType declaration template",
     "template: returns required_edges and optional_edges per NodeType",
     "template: action",
     "template: returns required/optional edges per NodeType","unit","medium"),

    # WAVE 15
    ("15","parse_query_positional",
     "parse_query positional argument handling",
     "parse_query extracts positional arg for find: related: tests: code: actions",
     "parse_query positional args",
     "parse_query handles positional args for read actions","unit","high"),

    ("15","value_coercion",
     "Value coercion in parse_query",
     "_coerce_value converts string literals to bool/int/None",
     "Value coercion",
     "_coerce_value converts true/false/null/int strings","unit","high"),

    ("15","import_unique_docids",
     "import: generates unique document IDs",
     "import: creates different Document nodes for same filename in different directories",
     "Unique import doc IDs",
     "import: generates collision-proof doc IDs per path","integration","medium"),

    ("15","edge_deduplication",
     "Edge deduplication and idempotency",
     "create_edge is idempotent; deduplicate_edges removes duplicates; dedupe: works",
     "Edge deduplication",
     "create_edge is idempotent; dedupe: removes duplicates","integration","high"),

    ("15","parser_smoke_matrix",
     "Parser mixed format handling",
     "parse_query handles combinations of positional args type suffixes named params",
     "Parser smoke matrix",
     "parse_query handles all mixed format combinations","unit","medium"),

    # CORE
    ("core","graph_index_construction",
     "GraphIndex construction and loading",
     "GraphIndex loads nodes/edges from disk with error collection",
     "GraphIndex loading",
     "GraphIndex loads nodes and edges from disk correctly","unit","high"),

    ("core","graph_index_queries",
     "GraphIndex query methods",
     "GraphIndex: get_node all_nodes nodes_by_type get_edges_from/to get_edges_by_type",
     "GraphIndex queries",
     "GraphIndex query methods return correct results","unit","high"),

    ("core","event_history",
     "Event history JSONL logging",
     "append_event logs to daily JSONL; read_events retrieves with date filter",
     "Event history logging",
     "append_event writes JSONL; read_events retrieves correctly","unit","medium"),

    ("core","create_node_mutation",
     "create_node write mutation",
     "create_node writes file logs history validates schema prevents duplicates",
     "create_node mutation",
     "create_node writes validates and prevents duplicates","unit","high"),

    ("core","update_node_mutation",
     "update_node write mutation",
     "update_node overwrites file logs history validates changes",
     "update_node mutation",
     "update_node overwrites file and logs history","unit","high"),

    ("core","delete_node_mutation",
     "delete_node soft-delete",
     "delete_node sets status=ARCHIVED (soft delete) logs history preserves file",
     "delete_node soft-delete",
     "delete_node sets ARCHIVED status not hard delete","unit","medium"),

    ("core","edge_mutations",
     "Edge create and delete mutations",
     "create_edge appends to relations.yaml; delete_edge removes matching; both log history",
     "Edge mutations",
     "create_edge and delete_edge work correctly with history","unit","high"),

    ("core","atomic_writes",
     "Atomic file write operations",
     "Mutations use atomic writes with no .tmp files left behind",
     "Atomic writes",
     "mutations leave no partial/tmp files on disk","unit","medium"),

    ("core","frontmatter_parsing",
     "Frontmatter YAML parsing",
     "parse_frontmatter extracts YAML frontmatter from markdown files correctly",
     "Frontmatter parsing",
     "parse_frontmatter handles various formats and errors","unit","high"),

    ("core","schema_loading",
     "Schema YAML loading",
     "load_schema loads YAML with version check; core schemas are v2.0",
     "Schema loading",
     "load_schema validates version and loads node/edge schemas","unit","high"),

    ("core","node_validation",
     "Node schema validation",
     "validate_node checks required fields enum values patterns types",
     "Node validation",
     "validate_node catches missing/invalid/unknown fields","unit","high"),

    ("core","edge_validation",
     "Edge schema validation",
     "validate_edge checks required from/to fields and edge type",
     "Edge validation",
     "validate_edge checks from to and type fields","unit","medium"),

    ("core","dispatcher_parse_query",
     "dispatcher parse_query routing",
     "parse_query handles action:subtype query params style for all actions",
     "parse_query routing",
     "parse_query correctly parses all action:type param combos","unit","high"),

    ("core","dispatcher_routing",
     "dispatch action routing",
     "dispatch routes all actions to handlers and returns _dispatch metadata",
     "dispatch routing",
     "dispatch routes actions to handlers with _dispatch metadata","integration","high"),

    ("core","gobp_overview_read",
     "gobp_overview read tool",
     "gobp_overview returns project charter stats topics recent decisions interface",
     "gobp_overview tool",
     "overview returns complete project state snapshot","unit","high"),

    ("core","find_read_tool",
     "find() read tool",
     "find() searches nodes by ID name substring with match type and pagination",
     "find() read tool",
     "find searches by id/name/substring with pagination","unit","high"),

    ("core","signature_read_tool",
     "signature() read tool",
     "signature() returns node metadata: id type name status timestamps",
     "signature() tool",
     "signature returns node metadata fields","unit","medium"),

    ("core","context_read_tool",
     "context() read tool",
     "context() returns node with edges invariants references; brief mode reduces payload",
     "context() tool",
     "context returns node plus edges invariants references","unit","medium"),

    ("core","session_recent_tool",
     "session_recent() read tool",
     "session_recent() returns n most recent sessions with actor filtering",
     "session_recent() tool",
     "session_recent returns recent sessions with actor filter","unit","medium"),

    ("core","decisions_for_tool",
     "decisions_for() read tool",
     "decisions_for() finds decisions by topic or node with status filter",
     "decisions_for() tool",
     "decisions_for finds decisions by topic or node id","unit","medium"),

    ("core","doc_sections_tool",
     "doc_sections() read tool",
     "doc_sections() returns Document node with sections list (heading lines tags)",
     "doc_sections() tool",
     "doc_sections returns document sections list","unit","medium"),

    ("core","node_upsert_write",
     "node_upsert() write tool",
     "node_upsert() creates nodes with validation and session tracking",
     "node_upsert() tool",
     "node_upsert creates/updates with validation","unit","high"),

    ("core","decision_lock_write",
     "decision_lock() write tool",
     "decision_lock() creates locked decisions with alternatives and 2+ locked_by check",
     "decision_lock() tool",
     "decision_lock creates locked decision with warnings","unit","high"),

    ("core","session_log_write",
     "session_log() write tool",
     "session_log() handles start/end/update actions for session lifecycle",
     "session_log() tool",
     "session_log handles start end update actions","unit","high"),

    ("core","import_proposal",
     "import_proposal() tool",
     "import_proposal() creates .pending.yaml files with node/edge proposals",
     "import_proposal() tool",
     "import_proposal creates pending proposal files","unit","medium"),

    ("core","import_commit",
     "import_commit() tool",
     "import_commit() accepts/rejects proposals to .committed/.rejected files",
     "import_commit() tool",
     "import_commit accepts/rejects proposals correctly","unit","medium"),

    ("core","validate_tool",
     "validate() maintain tool",
     "validate() checks graph integrity: orphan edges scope filters severity levels",
     "validate() tool",
     "validate detects orphan edges with scope and severity filter","unit","high"),

    ("core","ai_session_workflow",
     "Full AI session workflow",
     "End-to-end: overview to find context decisions session upsert lock validate",
     "Full AI session workflow",
     "complete AI workflow from overview to validation passes","integration","high"),

    ("core","smoke_tests",
     "Package and schema smoke tests",
     "gobp package importable; schemas parseable; templates have YAML frontmatter",
     "Smoke tests",
     "package imports and schema files are valid","smoke","high"),

    ("core","lessons_extraction",
     "Lessons extraction patterns",
     "extract_candidates finds P1 P2 P3 P4 patterns in sessions and decisions",
     "Lessons extraction",
     "extract_candidates finds failed sessions premature decisions orphans","unit","medium"),

    ("core","prune_operations",
     "Prune dry-run and execution",
     "dry_run identifies WITHDRAWN nodes; run_prune archives and logs pruned nodes",
     "Prune operations",
     "prune dry-run finds withdrawn; run_prune archives them","unit","medium"),

    ("core","cache_ttl_lru",
     "GoBP cache with TTL and LRU",
     "GoBPCache supports get/set/invalidate with TTL expiry and LRU eviction",
     "Cache TTL and LRU",
     "GoBPCache enforces TTL expiry and LRU eviction correctly","unit","medium"),

    ("core","db_operations",
     "Database node and edge operations",
     "db module upserts nodes/edges queries by type/substring supports type filtering",
     "DB operations",
     "db upsert query delete operations work correctly","unit","high"),

    ("core","performance_read",
     "Performance of read tools",
     "Read tools: overview find signature context stay under latency targets",
     "Performance: read tools",
     "overview find signature context under latency targets","performance","high"),

    ("core","performance_write",
     "Performance of write tools",
     "Write tools: session_log node_upsert stay under latency targets",
     "Performance: write tools",
     "session_log and node_upsert under latency targets","performance","high"),

    ("core","viewer_graph_data",
     "Viewer graph data export",
     "_load_graph_data returns nodes links meta in 3d-force-graph format",
     "Viewer graph data",
     "_load_graph_data returns 3d-force-graph format correctly","unit","medium"),

    ("core","viewer_http_server",
     "Viewer HTTP server",
     "Viewer serves /api/graph / /api/projects endpoints correctly",
     "Viewer HTTP server",
     "viewer HTTP server routes respond with correct data","integration","medium"),

    ("core","viewer_multi_project",
     "Viewer multi-project support",
     "Viewer /api/projects lists multiple roots; /api/graph?root= filter works",
     "Viewer multi-project",
     "viewer multi-project listing and root filter works","integration","medium"),

    ("core","migration_check",
     "Schema version migration check",
     "check_version detects outdated schema; needs_migration flag set correctly",
     "Migration version check",
     "check_version detects when migration is needed","unit","medium"),

    ("core","migration_execution",
     "Schema migration execution",
     "run_migration is idempotent and no-op when schema is current",
     "Migration execution",
     "run_migration no-ops when current; idempotent","unit","medium"),
]


async def main():
    global SID
    index = reload()

    # ── 0. Start a fresh session ──────────────────────────────────────────────
    print("\n── Starting session ──")
    r = await q("session:start actor='claude-cli' goal='Import all TestCase nodes across waves' role='contributor'", index)
    index = reload()
    if not r.get("ok"):
        print(f"FATAL: Cannot start session: {r}")
        return
    SID = r["session_id"]
    print(f"  Session: {SID}")

    # ── 1. Create missing Wave nodes ──────────────────────────────────────────
    print("\n── Wave nodes ──")
    missing_waves = [
        ("wave:4",    "Wave 4 TestKind Seeding Init Overview CLI"),
        ("wave:14",   "Wave 14 Schema Governance Protocol Versioning Access Model"),
        ("wave:15",   "Wave 15 Parser Positional Args Value Coercion Edge Dedup"),
        ("wave:core", "Core Infrastructure Graph History Mutator Validator Dispatcher"),
    ]
    wnode_map: dict[str, str] = {}
    for wid, wname in missing_waves:
        nid, index = await create_node("Wave", {"name": wname, "status": "DONE"}, index, explicit_id=wid)
        wnode_map[wid] = nid if nid else wid

    # label → resolved wave node id
    wmap = {
        "4":    wnode_map.get("wave:4", "wave:10a"),
        "10b":  "wave:10b",
        "11a":  "wave:11a",
        "13":   "wave:13",
        "14":   wnode_map.get("wave:14", "wave:13"),
        "15":   wnode_map.get("wave:15", "wave:13"),
        "core": wnode_map.get("wave:core", "wave:10a"),
    }

    kmap = {
        "unit":        "testkind:unit",
        "integration": "testkind:integration",
        "performance": "testkind:performance",
        "smoke":       "testkind:smoke",
    }

    # ── 2. Process each wave ──────────────────────────────────────────────────
    feat_ids: dict[str, str] = {}

    for wave_label in ["4", "10b", "11a", "14", "15", "core"]:
        wave_id = wmap[wave_label]
        entries = [e for e in CATALOG if e[0] == wave_label]
        print(f"\n── Wave {wave_label} ({wave_id}): {len(entries)} entries ──")

        for (wl, fkey, fname, fdesc, tc_name, tc_desc, tc_kind, priority) in entries:
            # a) Feature node — use explicit feat: prefixed ID
            feat_key_full = f"wave{wl}_{fkey}"
            feat_explicit_id = f"feat:w{wl}_{fkey}"
            if feat_key_full in feat_ids:
                feat_id = feat_ids[feat_key_full]
                print(f"  REUSE feat: {feat_id}")
            else:
                feat_id, index = await create_node("Feature", {
                    "name": fname,
                    "status": "ACTIVE",
                    "description": fdesc[:120],
                    "priority": priority,
                }, index, explicit_id=feat_explicit_id)
                if feat_id:
                    index = await add_edge(feat_id, "relates_to", wave_id,
                                           "feature belongs to wave", index)
                    feat_ids[feat_key_full] = feat_id

            # b) TestCase node
            covers_id = feat_id if feat_id else "api:gobp_query"
            kind_id = kmap.get(tc_kind, "testkind:unit")
            index = await create_testcase(
                tc_name, tc_desc, kind_id, covers_id, wave_id, priority, index
            )

    # ── 3. End session + Summary ──────────────────────────────────────────────
    index = reload()
    tc_count = len(index.nodes_by_type("TestCase"))
    feat_count = len(index.nodes_by_type("Feature"))

    r_end = await q(
        f"session:end session_id='{SID}' "
        f"outcome='Imported {tc_count} TestCase nodes and {feat_count} Feature nodes across all waves' "
        f"handoff='All wave TestCases captured in GoBP'",
        index,
    )

    print(f"\n{'='*60}")
    print(f"DONE: {ok_count} OK, {fail_count} FAIL")
    print(f"TestCase nodes total: {tc_count}")
    print(f"Feature nodes total:  {feat_count}")
    print(f"Wave nodes total:     {len(index.nodes_by_type('Wave'))}")
    print(f"Session end: {'OK' if r_end.get('ok') else r_end.get('error')}")


asyncio.run(main())
