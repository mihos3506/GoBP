"""GoBP query dispatcher.

Parses structured query protocol and routes to correct tool handler.

Protocol:
    gobp(query="<action>:<type> <key>='<value>' ...")

Actions:
    overview    -> gobp_overview()
    find        -> find()
    get         -> context() or signature()
    create      -> node_upsert()
    edit        -> handle_edit() (v3 PG + file backup; replaces legacy update:/retype:)
    lock        -> decision_lock()
    session     -> session_log()
    import      -> import_proposal()
    commit      -> import_commit()
    validate    -> validate()
    extract     -> lessons_extract()
    sections    -> doc_sections()
    recent      -> session_recent()
    decisions   -> decisions_for()
    signature   -> signature()
    evolve      -> evolve_action()  # read-only: checklist or Reflection lookup by wave_ref

Examples:
    "overview:"
    "find: login"
    "find:Decision auth"
    "get: node:feat_login"
    "create:Idea name='use OTP' subject='auth:login' session_id='session:x'"
    "lock:Decision topic='auth:login' what='use OTP' why='SMS unreliable' locked_by='CEO,Claude'"
    "session:start actor='cursor' goal='implement login'"
    "session:end outcome='done' handoff='next: write tests'"
    "validate: nodes"
    "extract: lessons"
    "sections: doc:wave_4_brief"
    "recent: 3"
    "decisions: auth:login.method"
    "signature: node:feat_login"
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.id_config import generate_external_id


from gobp.mcp.parser import PROTOCOL_GUIDE, _normalize_type, parse_query


def _classify_doc_priority(content: str, path: str) -> str:
    """Auto-classify document priority based on content keywords.

    Rules (deterministic, no AI):
      critical: user flows, auth, payment, proof of presence, trust gate
      high:     entity, engine, architecture, API, database
      medium:   design, copy, admin, notification, map
      low:      mascot, growth, future, level system, campaign
    """
    content_lower = content.lower()
    path_lower = path.lower()
    combined = content_lower + " " + path_lower

    critical_keywords = [
        "user flow", "authentication", "proof of presence", "payment",
        "trust gate", "verify gate", "core flow", "master definition",
        "pop_protocol", "mihot", "homecoming", "registration flow",
    ]
    high_keywords = [
        "entity", "engine", "architecture", "api", "database",
        "engine spec", "adapter", "domain dictionary", "migration",
        "interface reference", "middleware", "scale",
    ]
    low_keywords = [
        "mascot", "growth", "launch", "campaign", "level system",
        "gamification", "future", "phase 2", "nice to have",
    ]

    critical_score = sum(1 for kw in critical_keywords if kw in combined)
    high_score = sum(1 for kw in high_keywords if kw in combined)
    low_score = sum(1 for kw in low_keywords if kw in combined)

    if critical_score >= 2:
        return "critical"
    elif critical_score >= 1 or high_score >= 3:
        return "high"
    elif low_score >= 2:
        return "low"
    else:
        return "medium"




# -- Dispatch router -----------------------------------------------------------

async def dispatch(
    query: str,
    index: GraphIndex,
    project_root: Path,
) -> dict[str, Any]:
    """Route parsed query to correct tool handler.

    Returns tool result dict with added _dispatch_info for audit.
    """
    from gobp.mcp.tools import import_ as tools_import
    from gobp.mcp.tools import maintain as tools_maintain
    from gobp.mcp.tools import read as tools_read
    from gobp.mcp.tools import write as tools_write
    from gobp.mcp.tools.advanced import lessons_extract

    action, node_type, params = parse_query(query)
    dispatch_info = {"action": action, "type": node_type, "params": params}

    try:
        def _is_dry_run(value: Any) -> bool:
            return value in ("true", "1", True)

        # -- Read actions ------------------------------------------------------
        if action == "overview":
            result = tools_read.gobp_overview(index, project_root, params)

        elif action == "ping":
            from gobp.mcp.tools import read_v3 as _read_v3

            conn_ping, is_v3_ping = _read_v3._conn_v3(project_root)
            if conn_ping is None or not is_v3_ping:
                result = {
                    "ok": False,
                    "db": "not_connected",
                    "hint": "Set GOBP_DB_URL and ensure PostgreSQL schema v3.",
                }
            else:
                try:
                    result = _read_v3.ping_action(conn_ping, project_root)
                finally:
                    conn_ping.close()

        elif action == "refresh":
            import time as _t

            t0 = _t.time()
            fresh = GraphIndex.load_from_disk(project_root)
            elapsed_ms = (_t.time() - t0) * 1000
            try:
                from gobp.mcp.server import update_cache

                update_cache(fresh, project_root)
            except ImportError:
                pass
            result = {
                "ok": True,
                "nodes_loaded": len(fresh.all_nodes()),
                "edges_loaded": len(fresh.all_edges()),
                "elapsed_ms": round(elapsed_ms, 2),
            }

        elif action == "version":
            import gobp as _gobp

            from gobp.core.db import _get_conn, get_schema_version

            postgresql_connected = False
            schema_version = "2.1"
            conn = _get_conn(project_root)
            if conn is not None:
                try:
                    postgresql_connected = True
                    schema_version = get_schema_version(conn)
                except Exception:
                    postgresql_connected = False
                    schema_version = "2.1"
                finally:
                    conn.close()

            result = {
                "ok": True,
                "protocol_version": "2.0",
                "gobp_version": getattr(_gobp, "__version__", "0.1.0"),
                "schema_version": schema_version,
                "postgresql_connected": postgresql_connected,
                "deprecated_actions": [],
                "supported_actions": list(PROTOCOL_GUIDE.get("actions", {}).keys()),
                "changelog": [
                    "v2.0 (Wave 14): version: action, read-only mode, schema governance",
                    "v1.5 (Wave 13): pagination, upsert:, stats:, guardrails",
                    "v1.0 (Wave 10A): gobp() single tool, structured query protocol",
                ],
                "tip": "Call gobp(query='overview:') to see current project state.",
            }

        elif action == "find":
            args: dict[str, Any] = {}
            if "query" in params:
                args["query"] = params["query"]
                if node_type:
                    args["type"] = node_type
            elif node_type:
                args["type"] = node_type
                args["query"] = ""
            else:
                args["query"] = ""
            if "limit" in params:
                args["limit"] = int(params["limit"])
            if "page_size" in params:
                args["page_size"] = int(params["page_size"])
            if "cursor" in params:
                args["cursor"] = params["cursor"]
            if "sort" in params:
                args["sort"] = params["sort"]
            if "direction" in params:
                args["direction"] = params["direction"]
            if "mode" in params:
                args["mode"] = params["mode"]
            if "include_sessions" in params:
                args["include_sessions"] = params["include_sessions"]
            if "compact" in params:
                args["compact"] = params["compact"]
            for _gk in ("group", "group_exact", "group_contains"):
                if _gk in params:
                    args[_gk] = params[_gk]
            result = tools_read.find(index, project_root, args)

        elif action == "get":
            node_id = params.get("query") or params.get("id") or params.get("node_id", "")
            ctx_args: dict[str, Any] = {
                "node_id": node_id,
                "_mcp_action": "get",
            }
            if "mode" in params:
                ctx_args["mode"] = params["mode"]
            if "brief" in params:
                ctx_args["brief"] = params["brief"]
            if "edge_limit" in params:
                ctx_args["edge_limit"] = params["edge_limit"]
            if "compact" in params:
                ctx_args["compact"] = params["compact"]
            result = tools_read.context(index, project_root, ctx_args)

        elif action == "context":
            task_ctx = params.get("task") or params.get("task_description")
            ctx_args2: dict[str, Any] = {"_mcp_action": "context"}
            if task_ctx:
                ctx_args2["task"] = task_ctx
                try:
                    ctx_args2["max_nodes"] = int(params.get("max_nodes", 15))
                except (TypeError, ValueError):
                    ctx_args2["max_nodes"] = 15
            else:
                node_id = params.get("query") or params.get("id") or params.get("node_id", "")
                ctx_args2["node_id"] = node_id
            if "mode" in params:
                ctx_args2["mode"] = params["mode"]
            if "brief" in params:
                ctx_args2["brief"] = params["brief"]
            if "edge_limit" in params:
                ctx_args2["edge_limit"] = params["edge_limit"]
            if "compact" in params:
                ctx_args2["compact"] = params["compact"]
            result = tools_read.context(index, project_root, ctx_args2)

        elif action == "get_batch":
            raw_ids = params.get("ids") or params.get("query", "")
            args = {
                "ids": raw_ids,
                "mode": params.get("mode", "brief"),
                "max": params.get("max", 20),
                "since": params.get("since"),
            }
            result = tools_read.get_batch(index, project_root, args)

        elif action == "signature":
            node_id = params.get("query") or params.get("id") or params.get("node_id", "")
            result = tools_read.signature(index, project_root, {"node_id": node_id})

        elif action in ("recent", "sessions"):
            n = int(params.get("query", params.get("n", 3)))
            result = tools_read.session_recent(index, project_root, {"n": n})

        elif action == "decisions":
            topic = params.get("query") or params.get("topic", "")
            node_id = params.get("node_id", "")
            args = {}
            if topic:
                args["topic"] = topic
            if node_id:
                args["node_id"] = node_id
            result = tools_read.decisions_for(index, project_root, args)

        elif action == "sections":
            doc_id = params.get("query") or params.get("doc_id", "")
            result = tools_read.doc_sections(index, project_root, {"doc_id": doc_id})

        elif action == "code":
            node_id = params.get("query") or params.get("node_id", "")
            # Handle 'code: node:x path=... description=... language=...' add variant
            add_ref = None
            if params.get("path"):
                add_ref = {
                    "path": params.get("path", ""),
                    "description": params.get("description", ""),
                    "language": params.get("language", ""),
                }
            args = {"node_id": node_id}
            if add_ref:
                args["add"] = add_ref
            result = tools_read.code_refs(index, project_root, args)

        elif action == "invariants":
            node_id = params.get("query") or params.get("node_id", "")
            result = tools_read.node_invariants(index, project_root, {"node_id": node_id})

        elif action == "tests":
            node_id = params.get("query") or params.get("node_id", "")
            status = params.get("status")
            args = {"node_id": node_id}
            if status:
                args["status"] = status
            if "page_size" in params:
                args["page_size"] = params["page_size"]
            if "cursor" in params:
                args["cursor"] = params["cursor"]
            result = tools_read.node_tests(index, project_root, args)

        elif action == "related":
            node_id = params.get("query") or params.get("node_id", "")
            direction = params.get("direction", "both")
            edge_type = params.get("edge_type")
            args = {"node_id": node_id, "direction": direction}
            if edge_type:
                args["edge_type"] = edge_type
            if "mode" in params:
                args["mode"] = params["mode"]
            if "page_size" in params:
                args["page_size"] = params["page_size"]
            if "cursor" in params:
                args["cursor"] = params["cursor"]
            result = tools_read.node_related(index, project_root, args)

        elif action == "explore":
            explore_q = str(
                params.get("query") or params.get("keyword") or node_type or ""
            ).strip()
            result = tools_read.explore_action(
                index, project_root, {"query": explore_q, **params}
            )

        elif action == "suggest":
            suggest_ctx = str(params.get("query", "")).strip()
            result = tools_read.suggest_action(
                index, project_root, {"query": suggest_ctx, **params}
            )

        elif action == "evolve":
            result = tools_read.evolve_action(index, project_root, params)

        elif action == "template":
            node_type_arg = _normalize_type(
                str(params.get("query") or params.get("node_type") or node_type or "")
            )
            result = tools_read.template_action(
                index,
                project_root,
                {"query": node_type_arg, "node_type": node_type_arg, **params},
            )

        elif action == "template_batch":
            node_type_arg = _normalize_type(
                str(params.get("query") or params.get("node_type") or node_type or "")
            )
            result = tools_read.template_batch_action(
                index,
                project_root,
                {"query": node_type_arg, "node_type": node_type_arg, **params},
            )

        elif action == "interview":
            node_id = str(params.get("node_id") or params.get("query") or "")
            answered_raw = params.get("answered", "")
            if isinstance(answered_raw, list):
                answered_list = [str(a).strip() for a in answered_raw if str(a).strip()]
            elif answered_raw:
                answered_list = [a.strip() for a in str(answered_raw).split(",") if a.strip()]
            else:
                answered_list = []
            result = tools_read.node_interview(
                index,
                project_root,
                {"node_id": node_id, "answered": answered_list},
            )

        # -- Write actions -----------------------------------------------------
        elif action == "batch":
            result = tools_write.batch_action(index, project_root, params)

        elif action == "quick":
            result = tools_write.quick_action(index, project_root, params)

        elif action == "create":
            node_type = _normalize_type(node_type or params.pop("type", "Node"))
            name = params.get("name", "")
            testkind = params.get("testkind", params.get("kind_id", ""))

            # Auto-generate ID if not provided
            node_id = params.pop("id", params.pop("node_id", None))
            auto_generated_id = False
            if not node_id:
                node_id = generate_external_id(
                    node_type,
                    name=name,
                    testkind=testkind,
                    gobp_root=project_root,
                )
                auto_generated_id = True

            create_fields = {
                k: v for k, v in params.items() if k not in ("name", "type", "session_id")
            }
            if node_type == "Idea":
                idea_name = params.get("name", "")
                create_fields.setdefault("raw_quote", idea_name or "Auto-generated idea")
                create_fields.setdefault("interpretation", idea_name or "Auto-generated idea")
                create_fields.setdefault("subject", "general")
                create_fields.setdefault("maturity", "RAW")
                create_fields.setdefault("confidence", "medium")

            args = {
                "id": node_id,
                "type": node_type,
                "name": params.get("name", ""),
                "fields": create_fields,
                "session_id": params.get("session_id", ""),
            }
            if _is_dry_run(params.get("dry_run")):
                existing = index.get_node(node_id) if node_id else None
                result = {
                    "ok": True,
                    "dry_run": True,
                    "would_action": "updated" if existing else "created",
                    "node_id": node_id or "(auto-generated)",
                    "name": args.get("name", ""),
                    "type": node_type,
                    "message": "dry_run=true: no changes made",
                }
            else:
                result = tools_write.node_upsert(index, project_root, args)
            if (
                isinstance(result, dict)
                and not result.get("ok")
                and auto_generated_id
                and node_type in ("Idea", "Decision", "Lesson")
            ):
                fallback_args = dict(args)
                fallback_args.pop("id", None)
                result = tools_write.node_upsert(index, project_root, fallback_args)
                if isinstance(result, dict) and result.get("ok"):
                    result["node_id"] = node_id

        elif action == "edit":
            if _is_dry_run(params.get("dry_run")):
                result = {
                    "ok": True,
                    "dry_run": True,
                    "message": "dry_run=true: no changes made",
                }
            else:
                result = tools_write.handle_edit(index, project_root, params)

        elif action in ("update", "retype"):
            result = {
                "ok": False,
                "error": (
                    f"Action '{action}' was removed in Wave G; use edit: for node changes."
                ),
                "hint": (
                    "Example: edit: id='node:x' type=Engine session_id='...' "
                    "(or batch line edit: id=... field=value ...)"
                ),
            }

        elif action == "upsert":
            node_type = _normalize_type(node_type or params.pop("type", "Node"))
            name = params.get("name", "")
            testkind = params.get("testkind", params.get("kind_id", ""))
            dedupe_key = params.pop("dedupe_key", "name")
            dedupe_value = params.get(dedupe_key, "")
            session_id = params.get("session_id", "")

            is_dry = _is_dry_run(params.get("dry_run"))

            existing_node = None
            if dedupe_value:
                candidates = index.nodes_by_type(node_type)
                existing_node = next(
                    (n for n in candidates if str(n.get(dedupe_key, "")) == str(dedupe_value)),
                    None,
                )

            if is_dry:
                result = {
                    "ok": True,
                    "dry_run": True,
                    "would_action": "updated" if existing_node else "created",
                    "dedupe_key": dedupe_key,
                    "dedupe_value": dedupe_value,
                    "existing_id": existing_node.get("id") if existing_node else None,
                    "message": "dry_run=true: no changes made",
                }
            else:
                node_id = existing_node.get("id") if existing_node else None
                if not node_id:
                    node_id = generate_external_id(
                        node_type,
                        name=name,
                        testkind=testkind,
                        gobp_root=project_root,
                    )
                args = {
                    "id": node_id,
                    "type": node_type,
                    "name": params.get("name", dedupe_value),
                    "fields": {
                        k: v
                        for k, v in params.items()
                        if k not in ("name", "type", "session_id", "dry_run")
                    },
                    "session_id": session_id,
                }
                result = tools_write.node_upsert(index, project_root, args)
                if result.get("ok"):
                    result["dedupe_key"] = dedupe_key
                    result["dedupe_value"] = dedupe_value
                    result["existing_id"] = existing_node.get("id") if existing_node else None
                    if not result.get("action"):
                        result["action"] = "updated" if existing_node else "created"

        elif action == "delete":
            result = tools_write.delete_node_action(index, project_root, params)

        elif action == "lock":
            locked_by_raw = params.get("locked_by", "CEO,Claude-CLI")
            locked_by = [s.strip() for s in locked_by_raw.split(",")]
            args = {
                "topic": params.get("topic", ""),
                "what": params.get("what", ""),
                "why": params.get("why", ""),
                "locked_by": locked_by,
                "session_id": params.get("session_id", ""),
                "alternatives_considered": [],
            }
            if _is_dry_run(params.get("dry_run")):
                result = {
                    "ok": True,
                    "dry_run": True,
                    "would_action": "created",
                    "type": "Decision",
                    "topic": args.get("topic", ""),
                    "message": "dry_run=true: no changes made",
                }
            else:
                result = tools_write.decision_lock(index, project_root, args)

        elif action == "tasks":
            assignee = params.get("assignee", params.get("query", "cursor"))
            status_filter = str(params.get("status", "PENDING"))

            all_nodes = index.all_nodes()
            tasks = [n for n in all_nodes if n.get("type") == "Task"]

            filtered: list[dict[str, Any]] = []
            for t in tasks:
                t_status = str(t.get("status", "PENDING"))
                t_assignee = str(t.get("assignee", "cursor"))
                status_ok = status_filter == "ALL" or t_status == status_filter
                assignee_ok = (
                    assignee == "any"
                    or t_assignee == assignee
                    or t_assignee == "any"
                )
                if status_ok and assignee_ok:
                    filtered.append(
                        {
                            "id": t.get("id"),
                            "name": t.get("name"),
                            "status": t_status,
                            "assignee": t_assignee,
                            "wave": t.get("wave", ""),
                            "brief_path": t.get("brief_path", ""),
                            "priority": t.get("priority", "medium"),
                        }
                    )

            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            filtered.sort(
                key=lambda item: priority_order.get(item.get("priority", "medium"), 2)
            )

            result = {
                "ok": True,
                "tasks": filtered,
                "count": len(filtered),
                "filter": {"assignee": assignee, "status": status_filter},
                "hint": (
                    "Use upsert: to update task status. Example: "
                    "upsert: id='task:x' status='RUNNING' session_id='y'"
                ),
            }

        elif action == "session":
            sub = params.get("query", "start")
            if sub == "resume":
                result = tools_write.session_resume(project_root, params)
            else:
                args = {
                    "action": sub,
                    "actor": params.get("actor", "unknown"),
                    "goal": params.get("goal", ""),
                    "outcome": params.get("outcome", ""),
                    "pending": params.get("pending", "").split(",")
                    if params.get("pending")
                    else [],
                    "handoff_notes": params.get("handoff", params.get("handoff_notes", "")),
                    "role": params.get("role", "contributor"),
                }
                if "session_id" in params:
                    args["session_id"] = params["session_id"]
                if _is_dry_run(params.get("dry_run")):
                    existing = (
                        index.get_node(args.get("session_id", ""))
                        if args.get("session_id")
                        else None
                    )
                    result = {
                        "ok": True,
                        "dry_run": True,
                        "would_action": "updated" if existing else "created",
                        "action": sub,
                        "session_id": args.get("session_id", "(auto-generated)"),
                        "message": "dry_run=true: no changes made",
                    }
                else:
                    result = tools_write.session_log(index, project_root, args)

        elif action == "edge":
            from_id = params.get("from", "")
            to_id = params.get("to", "")
            edge_type = params.get("edge_type", "depends_on")
            reason = params.get("reason", "")
            code = params.get("code", "")

            if not from_id or not to_id:
                result = {
                    "ok": False,
                    "error": "edge: requires format: node:a --edge_type--> node:b",
                    "hint": "Example: gobp(query=\"edge: node:flow_auth --implements--> node:pop_protocol\")",
                }
            else:
                from gobp.core.loader import load_schema
                from gobp.core.fs_mutator import create_edge
                from pathlib import Path as _Path

                schema_dir = project_root / "gobp" / "schema"
                edges_schema = load_schema(schema_dir / "core_edges.yaml")

                edge = {
                    "from": from_id,
                    "to": to_id,
                    "type": edge_type,
                }
                if reason:
                    edge["reason"] = reason

                # Validate both nodes exist
                from_node = index.get_node(from_id)
                to_node = index.get_node(to_id)
                if not from_node:
                    result = {"ok": False, "error": f"Node not found: {from_id}"}
                elif not to_node:
                    result = {"ok": False, "error": f"Node not found: {to_id}"}
                else:
                    from gobp.core.validator_v3 import auto_reason, validate_edge_type

                    reason_provided = bool(str(reason).strip())
                    validation = validate_edge_type(
                        str(from_node.get("type", "")),
                        str(to_node.get("type", "")),
                        str(edge_type),
                        reason=str(reason),
                    )
                    if not reason_provided:
                        reason = auto_reason(
                            str(from_node.get("name", from_id)),
                            str(to_node.get("name", to_id)),
                            str(edge_type),
                        )

                    try:
                        warnings: list[str] = []
                        if validation.get("warning"):
                            warnings.append(str(validation["warning"]))
                        if validation.get("needs_reason") and not reason_provided:
                            warnings.append(
                                "enforces from Constraint requires short reason; auto template applied"
                            )

                        result = create_edge(
                            gobp_root=project_root,
                            edge={
                                "from": from_id,
                                "to": to_id,
                                "type": edge_type,
                                "reason": reason,
                                "code": code,
                            },
                            schema=edges_schema,
                            actor="gobp-dispatcher",
                            edge_file_name="semantic_edges.yaml",
                        )
                        if result.get("ok"):
                            result["edge_created"] = {
                                "from": from_id,
                                "from_name": from_node.get("name", ""),
                                "type": edge_type,
                                "to": to_id,
                                "to_name": to_node.get("name", ""),
                                "reason": reason,
                            }
                            if warnings:
                                result["warning"] = "; ".join(warnings)
                    except Exception as e:
                        result = {"ok": False, "error": str(e)}

        # -- Import actions ----------------------------------------------------
        elif action == "import":
            source_path_str = params.get("source_path") or params.get("query") or ""
            session_id = params.get("session_id", "")

            if not source_path_str:
                result = {
                    "ok": False,
                    "error": "import: requires source path",
                    "hint": "gobp(query=\"import: path/to/doc.md session_id='session:x'\")",
                }
            else:
                # Resolve path relative to project root
                source_path = project_root / source_path_str

                # Read file content for classification
                content = ""
                sections = []
                if source_path.exists():
                    content = source_path.read_text(encoding="utf-8", errors="replace")
                    # Extract markdown headings as sections
                    import re as _re
                    sections = [
                        {"heading": m.group(2).strip(), "level": len(m.group(1))}
                        for m in _re.finditer(r"^(#{1,3})\s+(.+)$", content, _re.MULTILINE)
                    ][:20]  # max 20 sections

                # Auto-classify priority
                priority = _classify_doc_priority(content, source_path_str)

                # Collision-proof doc_id: slug + md5(normalized path)
                import hashlib as _hashlib
                import re as _re3
                path_normalized = str(source_path).replace("\\", "/").lower()
                short_hash = _hashlib.md5(path_normalized.encode()).hexdigest()[:6]
                doc_slug = _re3.sub(r"[^a-z0-9]+", "_", source_path.stem.lower()).strip("_")
                doc_id = f"doc:{doc_slug}_{short_hash}"

                # Create Document node
                from datetime import datetime, timezone

                now_iso = datetime.now(timezone.utc).isoformat()
                content_hash = f"sha256:{_hashlib.sha256(content.encode()).hexdigest()}"

                doc_node = {
                    "id": doc_id,
                    "type": "Document",
                    "name": source_path.stem.replace("_", " ").title(),
                    "source_path": source_path_str,
                    "content_hash": content_hash,
                    "registered_at": now_iso,
                    "last_verified": now_iso,
                    "priority": priority,
                    "sections": sections,
                    "status": "ACTIVE",
                    "session_id": session_id,
                }

                doc_args = {
                    "id": doc_id,
                    "type": "Document",
                    "name": doc_node["name"],
                    "fields": {
                        k: v for k, v in doc_node.items()
                        if k not in ("id", "type", "name", "session_id")
                    },
                    "session_id": session_id,
                }

                upsert_result = tools_write.node_upsert(index, project_root, doc_args)

                if not upsert_result.get("ok"):
                    result = {
                        "ok": False,
                        "error": upsert_result.get("error", "Failed to create Document node"),
                        "source_path": source_path_str,
                        "file_exists": source_path.exists(),
                    }
                else:
                    result = {
                        "ok": True,
                        "document_node": doc_id,
                        "document_name": doc_node["name"],
                        "priority": priority,
                        "sections_found": len(sections),
                        "sections": sections[:5],  # show first 5
                        "content_hash": content_hash,
                        "file_exists": source_path.exists(),
                        "suggestion": (
                            f"Document node created with collision-proof ID. "
                            f"Now extract key concepts:\n"
                            f"  gobp(query=\"create:Node name='...' priority='{priority}' session_id='{session_id}'\")\n"
                            f"Then link:\n"
                            f"  gobp(query=\"edge: node:x --references--> {doc_id}\")"
                        ),
                    }

        elif action == "commit":
            proposal_id = params.get("query") or params.get("proposal_id", "")
            args = {
                "proposal_id": proposal_id,
                "accept": params.get("accept", "all"),
                "session_id": params.get("session_id", ""),
            }
            result = tools_import.import_commit(index, project_root, args)

        # -- Maintenance actions -----------------------------------------------
        elif action == "validate":
            scope = params.get("query", params.get("scope", ""))
            scope_primary = str(params.get("scope") or params.get("query") or scope or "").strip()
            if scope in ("schema-docs", "schema-tests", "schema"):
                result = tools_read.schema_governance(
                    index, project_root, {"scope": scope, **params}
                )
            elif scope_primary == "metadata":
                result = tools_read.metadata_lint(index, project_root, params)
            else:
                from gobp.mcp.tools import read_v3 as _read_v3

                conn_v, is_v3 = _read_v3._conn_v3(project_root)
                if conn_v is not None and is_v3:
                    try:
                        result = _read_v3.validate_v3(conn_v)
                    finally:
                        conn_v.close()
                else:
                    result = tools_maintain.validate(
                        index, project_root, {"scope": scope or "all", **params}
                    )

        elif action == "extract":
            result = await lessons_extract(index, project_root, {})

        elif action == "dedupe":
            scope = params.get("action_filter") or params.get("scope", "edges")
            if scope in ("edges", "all"):
                from gobp.core.fs_mutator import deduplicate_edges

                result = deduplicate_edges(project_root)
            else:
                result = {
                    "ok": False,
                    "error": f"dedupe: scope '{scope}' not supported. Use 'edges' or 'all'.",
                }

        elif action == "recompute":
            scope = params.get("query", params.get("scope", "priorities"))
            if scope == "priorities":
                args = {
                    "dry_run": params.get("dry_run", False),
                    "type": params.get("type", ""),
                    "session_id": params.get("session_id", ""),
                }
                result = tools_read.recompute_priorities(index, project_root, args)
            else:
                result = {"ok": False, "error": f"recompute: unknown scope '{scope}'"}

        # -- Unknown action ----------------------------------------------------
        else:
            # Fallback: try find
            result = tools_read.find(index, project_root, {"query": query})
            dispatch_info["fallback"] = True

    except Exception as e:
        result = {
            "ok": False,
            "error": str(e),
            "hint": _get_hint(action, node_type),
        }

    # Add dispatch info for audit
    result["_dispatch"] = dispatch_info
    return result


def _get_hint(action: str, node_type: str) -> str:
    """Return helpful hint for failed action."""
    hints = {
        "create": "Usage: gobp(query=\"create:<NodeType> name='x' session_id='session:y'\")",
        "lock": "Usage: gobp(query=\"lock:Decision topic='x' what='y' why='z' locked_by='CEO,Claude'\")",
        "session": "Usage: gobp(query=\"session:start actor='x' goal='y'\") or session:end",
        "import": "Usage: gobp(query=\"import: path/to/file.md session_id='session:x'\")",
        "commit": "Usage: gobp(query=\"commit: imp:proposal-id accept=all session_id='session:x'\")",
    }
    return hints.get(action, "Call gobp(query='overview:') to see all available actions")

