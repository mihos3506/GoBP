"""GoBP MCP import tools.

Implementations for import_proposal and import_commit.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from gobp.core.graph import GraphIndex
from gobp.core.loader import load_schema, package_schema_dir
from gobp.core.mutator import _atomic_write, coerce_and_validate_node, create_edge, create_node
from gobp.core.validator import validate_edge


def import_proposal(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """AI proposes a batch import from a source file. Stored as pending proposal.

    Input: source_path, proposal_type, ai_notes, proposed_document (optional),
           proposed_nodes, proposed_edges, confidence, session_id
    Output: ok, proposal_id, summary, node_count, edge_count, warnings
    """
    required = [
        "source_path",
        "proposal_type",
        "ai_notes",
        "proposed_nodes",
        "proposed_edges",
        "confidence",
        "session_id",
    ]
    for field in required:
        if field not in args:
            return {"ok": False, "error": f"Missing required field: {field}"}

    source_path = args["source_path"]
    proposal_type = args["proposal_type"]
    if proposal_type not in ("doc", "code", "spec"):
        return {"ok": False, "error": "proposal_type must be doc, code, or spec"}

    confidence = args["confidence"]
    if confidence not in ("low", "medium", "high"):
        return {"ok": False, "error": "confidence must be low, medium, or high"}

    session_id = args["session_id"]
    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}
    if session.get("status") == "COMPLETED":
        return {"ok": False, "error": "Session already ended"}

    proposed_nodes = args["proposed_nodes"]
    proposed_edges = args["proposed_edges"]

    if not isinstance(proposed_nodes, list) or not isinstance(proposed_edges, list):
        return {"ok": False, "error": "proposed_nodes and proposed_edges must be lists"}

    # Generate proposal ID
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    source_stem = Path(source_path).stem.replace(" ", "_")[:40]
    proposal_id = f"imp:{date_str}_{source_stem}"

    # Avoid conflicts
    proposals_dir = project_root / ".gobp" / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    pending_file = proposals_dir / f"{proposal_id.replace(':', '_')}.pending.yaml"
    counter = 1
    while pending_file.exists():
        counter += 1
        numbered_id = f"{proposal_id}_{counter}"
        pending_file = proposals_dir / f"{numbered_id.replace(':', '_')}.pending.yaml"
        proposal_id = numbered_id

    # Build proposal content
    proposal = {
        "proposal_id": proposal_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": source_path,
        "proposal_type": proposal_type,
        "ai_notes": args["ai_notes"],
        "confidence": confidence,
        "session_id": session_id,
        "proposed_document": args.get("proposed_document"),
        "proposed_nodes": proposed_nodes,
        "proposed_edges": proposed_edges,
    }

    # Atomic write
    try:
        content = yaml.safe_dump(proposal, default_flow_style=False, sort_keys=False)
        _atomic_write(pending_file, content)
    except Exception as e:
        return {"ok": False, "error": f"Failed to write proposal: {e}"}

    # Summary
    doc_part = ""
    if args.get("proposed_document"):
        doc_part = "1 Document + "
    summary = f"Import {Path(source_path).name}: {doc_part}{len(proposed_nodes)} nodes + {len(proposed_edges)} edges. Confidence: {confidence}."

    total_node_count = len(proposed_nodes)
    if args.get("proposed_document"):
        total_node_count += 1

    return {
        "ok": True,
        "proposal_id": proposal_id,
        "summary": summary,
        "node_count": total_node_count,
        "edge_count": len(proposed_edges),
        "warnings": [],
    }


def import_commit(index: GraphIndex, project_root: Path, args: dict[str, Any]) -> dict[str, Any]:
    """Commit an approved import proposal atomically.

    Input: proposal_id, accept (all|partial|reject), accepted_node_ids (if partial),
           accepted_edge_ids (if partial), overrides (optional), session_id
    Output: ok, nodes_created, edges_created, errors

    Atomicity: if any validation fails, ALL rolled back, nothing written.
    """
    proposal_id = args.get("proposal_id")
    if not proposal_id:
        return {"ok": False, "error": "proposal_id required"}

    accept = args.get("accept")
    if accept not in ("all", "partial", "reject"):
        return {"ok": False, "error": "accept must be all, partial, or reject"}

    session_id = args.get("session_id")
    if not session_id:
        return {"ok": False, "error": "session_id required"}

    session = index.get_node(session_id)
    if not session:
        return {"ok": False, "error": f"Session not found: {session_id}"}

    # Load proposal
    proposals_dir = project_root / ".gobp" / "proposals"
    pending_file = proposals_dir / f"{proposal_id.replace(':', '_')}.pending.yaml"

    if not pending_file.exists():
        return {"ok": False, "error": f"Proposal not found: {proposal_id}"}

    try:
        with open(pending_file, "r", encoding="utf-8") as f:
            proposal = yaml.safe_load(f)
    except Exception as e:
        return {"ok": False, "error": f"Failed to load proposal: {e}"}

    if accept == "reject":
        # Move to rejected
        rejected_file = proposals_dir / f"{proposal_id.replace(':', '_')}.rejected.yaml"
        pending_file.rename(rejected_file)
        return {"ok": True, "nodes_created": 0, "edges_created": 0, "errors": []}

    doc_id = str(proposal.get("source_path") or proposal_id)

    def _execute_import_commit() -> dict[str, Any]:
        return _import_commit_body(
            project_root,
            proposal,
            proposal_id,
            pending_file,
            proposals_dir,
            accept,
            args,
        )

    from gobp.core import db as db_mod
    from gobp.core.import_lock import acquire_import_lock

    conn = db_mod._get_conn(project_root)
    if conn is not None:
        try:
            with acquire_import_lock(conn, doc_id, session_id) as lock:
                if not lock.acquired:
                    return {
                        "ok": False,
                        "blocked": True,
                        "owner": lock.owner,
                        "hint": lock.hint,
                    }
                return _execute_import_commit()
        finally:
            try:
                conn.close()
            except Exception:
                pass
    return _execute_import_commit()


def _import_commit_body(
    project_root: Path,
    proposal: dict[str, Any],
    proposal_id: str,
    pending_file: Path,
    proposals_dir: Path,
    accept: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Apply validated import proposal (nodes, edges, rename pending file)."""
    # Select nodes and edges based on accept mode
    all_nodes = list(proposal.get("proposed_nodes", []))
    if proposal.get("proposed_document"):
        all_nodes = [proposal["proposed_document"]] + all_nodes
    all_edges = list(proposal.get("proposed_edges", []))

    if accept == "partial":
        accepted_node_ids = set(args.get("accepted_node_ids", []))
        accepted_edge_ids = set(args.get("accepted_edge_ids", []))
        all_nodes = [n for n in all_nodes if n.get("id") in accepted_node_ids]
        all_edges = [
            e
            for i, e in enumerate(all_edges)
            if f"edge_{i}" in accepted_edge_ids or e.get("id") in accepted_edge_ids
        ]

    # Apply overrides
    overrides = args.get("overrides", {})
    for node in all_nodes:
        nid = node.get("id")
        if nid in overrides:
            for k, v in overrides[nid].items():
                node[k] = v

    # Load schemas
    try:
        schema_dir = package_schema_dir()
        nodes_schema = load_schema(schema_dir / "core_nodes.yaml")
        edges_schema = load_schema(schema_dir / "core_edges.yaml")
    except Exception as e:
        return {"ok": False, "error": f"Failed to load schemas: {e}"}

    # Validate everything first (no writes yet)
    errors: list[dict[str, Any]] = []
    for node in all_nodes:
        n = dict(node)
        result = coerce_and_validate_node(project_root, n, nodes_schema)
        if not result.ok:
            errors.append({"node_id": node.get("id"), "errors": result.errors})

    for edge in all_edges:
        result = validate_edge(edge, edges_schema)
        if not result.ok:
            errors.append({"edge": f"{edge.get('from')} -> {edge.get('to')}", "errors": result.errors})

    if errors:
        return {"ok": False, "nodes_created": 0, "edges_created": 0, "errors": errors}

    # All validation passed. Now write atomically.
    # If any write fails partway, we return partial success + errors.
    # Full rollback on partial failures is out of v1 scope.
    nodes_created = 0
    edges_created = 0
    write_errors: list[dict[str, Any]] = []

    for node in all_nodes:
        try:
            create_node(project_root, node, nodes_schema, actor="import_commit")
            nodes_created += 1
        except FileExistsError:
            write_errors.append({"node_id": node.get("id"), "error": "Already exists"})
        except Exception as e:
            write_errors.append({"node_id": node.get("id"), "error": str(e)})

    for edge in all_edges:
        try:
            create_edge(project_root, edge, edges_schema, actor="import_commit")
            edges_created += 1
        except Exception as e:
            write_errors.append({"edge": f"{edge.get('from')} -> {edge.get('to')}", "error": str(e)})

    # Move proposal to committed
    committed_file = proposals_dir / f"{proposal_id.replace(':', '_')}.committed.yaml"
    try:
        pending_file.rename(committed_file)
    except Exception as e:
        write_errors.append({"proposal": proposal_id, "error": f"Failed to move to committed: {e}"})

    return {
        "ok": len(write_errors) == 0,
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "errors": write_errors,
    }
