"""Measure P95 latency for find queries on a GoBP project.

Usage:
  D:/GoBP/venv/Scripts/python.exe scripts/mihos_find_p95_check.py --root D:/MIHOS-v1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

DEFAULT_QUERIES = [
    "dang nhap",
    "đăng nhập",
    "mihot",
    "mi hốt",
    "trustgate",
    "engine",
    "flow",
    "auth",
]


async def run_once(index: GraphIndex, root: Path, query: str, mode: str) -> float:
    start = time.perf_counter()
    result = await dispatch(f"find: {query} mode={mode}", index, root)
    if not result.get("ok", False):
        raise RuntimeError(f"find failed for query={query!r}: {result}")
    return (time.perf_counter() - start) * 1000.0


async def benchmark(root: Path, queries: list[str], runs: int, mode: str) -> dict[str, object]:
    index = GraphIndex.load_from_disk(root)
    all_samples: list[float] = []
    per_query: dict[str, list[float]] = {q: [] for q in queries}

    for _ in range(runs):
        for query in queries:
            ms = await run_once(index, root, query, mode)
            per_query[query].append(ms)
            all_samples.append(ms)

    if not all_samples:
        raise RuntimeError("No samples collected")

    p95 = statistics.quantiles(all_samples, n=100)[94]
    p50 = statistics.median(all_samples)
    return {
        "samples": len(all_samples),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "max_ms": round(max(all_samples), 2),
        "per_query_avg_ms": {
            q: round(sum(v) / len(v), 2) for q, v in per_query.items() if v
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="D:/MIHOS-v1")
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--target-p95-ms", type=float, default=80.0)
    parser.add_argument("--mode", default="summary")
    parser.add_argument("--json-out", default=".gobp/history/mihos_find_p95.json")
    args = parser.parse_args()

    root = Path(args.root)
    report = asyncio.run(benchmark(root, DEFAULT_QUERIES, args.runs, args.mode))
    report["target_p95_ms"] = args.target_p95_ms
    report["ok"] = bool(report["p95_ms"] <= args.target_p95_ms)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    Path(args.json_out).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nSaved report: {args.json_out}")

    if not report["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
