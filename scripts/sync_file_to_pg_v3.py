#!/usr/bin/env python3
"""Rebuild PostgreSQL v3 mirror from the file-backed graph (TRUNCATE + upsert).

This wraps :func:`gobp.core.db.rebuild_index`, which **truncates** ``nodes``,
``edges``, and ``node_history`` then reloads from :class:`gobp.core.graph.GraphIndex`.

Usage::

    # Preview counts only (no DB writes)
    python scripts/sync_file_to_pg_v3.py --root D:/GoBP

    # Destructive: mirror files → PostgreSQL
    GOBP_DB_URL=... python scripts/sync_file_to_pg_v3.py --root D:/GoBP --execute
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gobp.core.db import count_nodes_in_db, rebuild_index
from gobp.core.graph import GraphIndex


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="GoBP project root (default: current directory)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run rebuild_index (truncates PG mirror). Without this, dry-run only.",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    index = GraphIndex.load_from_disk(root)
    n_file = len(index.nodes)
    n_edge = len(index.all_edges())
    n_db = count_nodes_in_db(root)

    print(f"Project root: {root}")
    print(f"Nodes (graph): {n_file}, edges (graph): {n_edge}")
    print(f"Nodes (PostgreSQL v3): {n_db}")

    if not args.execute:
        print(
            "\nDry run — no database changes. "
            "Pass --execute to TRUNCATE and reload the PG mirror from files."
        )
        return 0

    out = rebuild_index(root, index)
    print(out)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
