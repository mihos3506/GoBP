"""Replay common search queries for Wave 16A07 audit hardening.

Usage:
  set GOBP_DB_URL=postgresql://...
  python scripts/wave16a07_search_replay.py --root D:/MIHOS-v1 --mode summary
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


def load_queries(path: Path) -> list[str]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [line for line in lines if line and not line.startswith("#")]


async def run_query(index: GraphIndex, root: Path, query: str, mode: str) -> dict:
    start = time.perf_counter()
    result = await dispatch(f"find: {query} mode={mode}", index, root)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    matches = result.get("matches", [])
    top = matches[0] if matches else {}
    return {
        "query": query,
        "ok": result.get("ok"),
        "count": result.get("count", len(matches)),
        "elapsed_ms": round(elapsed_ms, 2),
        "top_id": top.get("id"),
        "top_name": top.get("name"),
        "top_type": top.get("type"),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="D:/MIHOS-v1")
    parser.add_argument("--queries", default="scripts/wave16a07_queries.txt")
    parser.add_argument("--mode", default="summary", choices=["summary", "brief", "standard"])
    parser.add_argument("--json", dest="json_out", default="")
    args = parser.parse_args()

    root = Path(args.root)
    queries_file = Path(args.queries)
    queries = load_queries(queries_file)

    index = GraphIndex.load_from_disk(root)
    rows: list[dict] = []
    for query in queries:
        rows.append(await run_query(index, root, query, args.mode))

    print("query | count | elapsed_ms | top_type | top_name")
    print("-" * 72)
    for row in rows:
        print(
            f"{row['query']:<12} | {row['count']:<5} | {row['elapsed_ms']:<10} | "
            f"{(row['top_type'] or ''):<10} | {row['top_name'] or ''}"
        )

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nSaved JSON report: {args.json_out}")


if __name__ == "__main__":
    asyncio.run(main())
