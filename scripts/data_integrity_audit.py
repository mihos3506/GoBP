"""Read-only data integrity audit for GoBP projects (PostgreSQL v3 only).

This script does **not** modify project data. It requires ``GOBP_DB_URL`` and a
v3 schema, then generates a JSON report with:

- ``validate_v3`` summary (required fields, Error severity, dangling edges, etc.)
- Node / edge counts from the database
- Potential duplicate display names within the same ``group_path``
- Edge duplicate section: v3 edges use ``PRIMARY KEY (from_id, to_id)``, so
  duplicate triple analysis is not applicable (documented in the report).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gobp.core.db import ensure_v3_connection
from gobp.core.search import normalize_text
from gobp.mcp.tools.read_v3 import validate_v3


def edge_duplicate_stats_v3(edge_count: int) -> dict[str, Any]:
    """v3 edges cannot duplicate the same (from_id, to_id) pair."""
    return {
        "model": "postgresql_v3",
        "note": (
            "Edges table uses PRIMARY KEY (from_id, to_id); "
            "no duplicate edge triples are possible."
        ),
        "total_edges": edge_count,
        "unique_edge_triples": edge_count,
        "duplicate_edge_triples": 0,
        "duplicate_instances": 0,
        "top_duplicates": [],
    }


def potential_node_duplicates_v3(conn: Any) -> dict[str, Any]:
    """Flag nodes that share normalized name within the same group_path."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, group_path FROM nodes")
        for row in cur.fetchall():
            nid, name, gp = row[0], str(row[1] or "").strip(), str(row[2] or "")
            if not name:
                continue
            key = (gp, normalize_text(name).replace(" ", ""))
            groups[key].append({"id": nid, "name": name, "group_path": gp})

    dup_groups: list[dict[str, Any]] = []
    for (gp, norm), nodes in groups.items():
        if len(nodes) <= 1:
            continue
        dup_groups.append(
            {
                "group_path": gp,
                "normalized_name_key": norm,
                "count": len(nodes),
                "nodes": [{"id": n["id"], "name": n["name"]} for n in nodes],
            }
        )
    dup_groups.sort(key=lambda x: x["count"], reverse=True)
    return {"duplicate_name_groups": len(dup_groups), "top_groups": dup_groups[:30]}


def run_audit(project_root: Path) -> dict[str, Any]:
    conn = ensure_v3_connection(project_root)
    try:
        validation = validate_v3(conn)
        issues: list[dict[str, Any]] = list(validation.get("issues", []))
        err_count = sum(1 for i in issues if i.get("severity") == "error")

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM nodes")
            node_count = int(cur.fetchone()[0])
            cur.execute("SELECT COUNT(*) FROM edges")
            edge_count = int(cur.fetchone()[0])
            cur.execute(
                "SELECT COUNT(*) FROM nodes WHERE group_path = 'Meta > Session'"
            )
            session_count = int(cur.fetchone()[0])
            cur.execute("SELECT group_path, COUNT(*) FROM nodes GROUP BY group_path")
            by_group = Counter()
            for gp, c in cur.fetchall():
                top = str(gp or "").split(" > ")[0] or "(empty)"
                by_group[top] += int(c)

        v3_ok = err_count == 0

        return {
            "ok": v3_ok,
            "backend": "postgresql_v3",
            "project_root": str(project_root),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "node_count": node_count,
            "edge_count": edge_count,
            "session_ratio_pct": round((session_count / node_count) * 100, 2)
            if node_count
            else 0.0,
            "nodes_by_top_level_group": dict(by_group),
            "index_load_errors": [],
            "validation": validation,
            "validation_error_count": err_count,
            "edge_duplicates": edge_duplicate_stats_v3(edge_count),
            "potential_node_duplicates": potential_node_duplicates_v3(conn),
        }
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Project root containing .gobp")
    parser.add_argument("--json-out", required=True, help="Output JSON path")
    args = parser.parse_args()

    root = Path(args.root)
    out = Path(args.json_out)
    try:
        report = run_audit(root)
    except RuntimeError as e:
        raise SystemExit(f"ERROR: {e}") from e
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSaved report: {out}")

    if not report["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
