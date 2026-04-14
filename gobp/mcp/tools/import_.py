"""GoBP MCP import tools.

Implementations for import_proposal and import_commit.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from gobp.core.graph import GraphIndex
from gobp.core.mutator import _atomic_write


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
    return {"ok": False, "error": "import_commit not yet implemented"}
