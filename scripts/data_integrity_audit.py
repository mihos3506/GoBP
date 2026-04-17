"""Read-only data integrity audit for GoBP projects.

This script does NOT modify project data. It generates a JSON report with:
- Schema/reference validation summary
- Edge duplicate analysis
- Potential duplicate node names
- Index load errors
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.search import normalize_text
from gobp.mcp.tools.maintain import validate


def edge_duplicate_stats(index: GraphIndex) -> dict[str, Any]:
    triples = [
        (e.get("from", ""), e.get("type", ""), e.get("to", ""))
        for e in index.all_edges()
    ]
    counts = Counter(triples)
    duplicates = [
        {"from": f, "type": t, "to": to, "count": c}
        for (f, t, to), c in counts.items()
        if c > 1
    ]
    duplicates.sort(key=lambda x: x["count"], reverse=True)
    return {
        "total_edges": len(triples),
        "unique_edge_triples": len(counts),
        "duplicate_edge_triples": len(duplicates),
        "duplicate_instances": sum(d["count"] - 1 for d in duplicates),
        "top_duplicates": duplicates[:20],
    }


def potential_node_duplicates(index: GraphIndex) -> dict[str, Any]:
    # Group by (type, normalized_name_no_spaces)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for node in index.all_nodes():
        node_type = str(node.get("type", ""))
        name = str(node.get("name", "")).strip()
        if not name:
            continue
        key = (node_type, normalize_text(name).replace(" ", ""))
        groups[key].append(node)

    dup_groups = []
    for (node_type, norm), nodes in groups.items():
        if len(nodes) <= 1:
            continue
        dup_groups.append(
            {
                "type": node_type,
                "normalized_name_key": norm,
                "count": len(nodes),
                "nodes": [
                    {"id": n.get("id"), "name": n.get("name"), "status": n.get("status")}
                    for n in nodes
                ],
            }
        )
    dup_groups.sort(key=lambda x: x["count"], reverse=True)
    return {"duplicate_name_groups": len(dup_groups), "top_groups": dup_groups[:30]}


def run_audit(project_root: Path) -> dict[str, Any]:
    index = GraphIndex.load_from_disk(project_root)

    validation = validate(index, project_root, {"scope": "all", "severity_filter": "all"})
    load_errors = list(index.load_errors)

    type_counts = Counter(n.get("type", "Unknown") for n in index.all_nodes())
    session_count = int(type_counts.get("Session", 0))
    node_count = len(index.all_nodes())

    return {
        "ok": bool(validation.get("ok", False) and not load_errors),
        "project_root": str(project_root),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "node_count": node_count,
        "edge_count": len(index.all_edges()),
        "session_ratio_pct": round((session_count / node_count) * 100, 2) if node_count else 0.0,
        "nodes_by_type": dict(type_counts),
        "index_load_errors": load_errors[:50],
        "validation": validation,
        "edge_duplicates": edge_duplicate_stats(index),
        "potential_node_duplicates": potential_node_duplicates(index),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Project root containing .gobp")
    parser.add_argument("--json-out", required=True, help="Output JSON path")
    args = parser.parse_args()

    root = Path(args.root)
    out = Path(args.json_out)
    report = run_audit(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSaved report: {out}")

    # non-zero to make CI/manual gate obvious
    if not report["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
