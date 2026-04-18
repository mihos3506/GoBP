"""Wave 16A14: benchmark indexed find / explore / suggest / validate.

Creates a temporary graph with 500 nodes and 400 edges, then prints
median wall-clock ms per action (3 runs each).
"""

from __future__ import annotations

import shutil
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from gobp.core.graph import GraphIndex
from gobp.mcp.tools import maintain as tools_maintain
from gobp.mcp.tools import read as tools_read


def _median_ms(fn: Callable[[], Any], runs: int = 3) -> tuple[float, Any]:
    times: list[float] = []
    last: Any = None
    for _ in range(runs):
        t0 = time.perf_counter()
        last = fn()
        times.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(times), last


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    schema_src = repo / "gobp" / "schema"

    with tempfile.TemporaryDirectory(prefix="gobp_w16a14_bench_") as td:
        root = Path(td)
        (root / ".gobp" / "nodes").mkdir(parents=True)
        (root / ".gobp" / "edges").mkdir(parents=True)
        dest_schema = root / "gobp" / "schema"
        dest_schema.mkdir(parents=True)
        shutil.copy(schema_src / "core_nodes.yaml", dest_schema / "core_nodes.yaml")
        shutil.copy(schema_src / "core_edges.yaml", dest_schema / "core_edges.yaml")

        index = GraphIndex.load_from_disk(root)

        n_nodes = 500
        n_edges = 400
        ids: list[str] = []
        for i in range(n_nodes):
            nid = index.add_node_in_memory(
                {
                    "type": "Idea",
                    "name": f"Bench idea keyword{i} token shared",
                    "description": f"Description alpha{i} beta gamma for search",
                }
            )
            ids.append(nid)

        for j in range(n_edges):
            a = ids[j % n_nodes]
            b = ids[(j + 7) % n_nodes]
            index.add_edge_in_memory(a, b, "relates_to")

        q = "keyword250"
        ctx = "alpha250 beta shared token"

        ms_find, _ = _median_ms(
            lambda: tools_read.find(
                index, root, {"query": q, "page_size": 20}
            )
        )
        ms_explore, _ = _median_ms(
            lambda: tools_read.explore_action(index, root, {"query": q})
        )
        ms_suggest, _ = _median_ms(
            lambda: tools_read.suggest_action(
                index, root, {"query": ctx, "limit": 10}
            )
        )
        ms_val, _ = _median_ms(
            lambda: tools_maintain.validate(index, root, {"scope": "all"})
        )

        print(f"Wave 16A14 bench: {n_nodes} nodes, {n_edges} edges (in-memory index)")
        print(f"  find(query={q!r}):     {ms_find:.2f} ms (median of 3)")
        print(f"  explore({q!r}):      {ms_explore:.2f} ms (median of 3)")
        print(f"  suggest(context…):   {ms_suggest:.2f} ms (median of 3)")
        print(f"  validate(scope=all): {ms_val:.2f} ms (median of 3)")


if __name__ == "__main__":
    main()
