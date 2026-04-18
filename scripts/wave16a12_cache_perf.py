"""Wave 16A12: warm-cache read latency smoke (get_cached_index + dispatch).

Run from repo root:
  $env:GOBP_PROJECT_ROOT = 'D:/GoBP'
  D:/GoBP/venv/Scripts/python.exe scripts/wave16a12_cache_perf.py

Thresholds are conservative for large workspaces and Windows I/O variance.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from gobp.mcp.dispatcher import dispatch
from gobp.mcp.server import get_cached_index, invalidate_cache


async def perf_test() -> None:
    root = Path(os.environ.get("GOBP_PROJECT_ROOT", "D:/GoBP")).resolve()

    invalidate_cache()
    t0 = time.time()
    index = get_cached_index(root)
    cold_ms = (time.time() - t0) * 1000
    print(f"Cold load: {cold_ms:.0f}ms ({len(index.all_nodes())} nodes)")

    times: list[float] = []
    for _ in range(10):
        t0 = time.time()
        idx = get_cached_index(root)
        await dispatch("find: engine mode=summary", idx, root)
        elapsed = (time.time() - t0) * 1000
        times.append(elapsed)

    avg = sum(times) / len(times)
    print(f"Warm find: avg {avg:.0f}ms (10 calls)")
    assert avg < 200.0, f"Too slow: {avg:.0f}ms (expected <200ms warm find)"

    times2: list[float] = []
    for _ in range(5):
        t0 = time.time()
        idx = get_cached_index(root)
        await dispatch("explore: engine compact=true", idx, root)
        times2.append((time.time() - t0) * 1000)

    avg2 = sum(times2) / len(times2)
    print(f"Warm explore: avg {avg2:.0f}ms (5 calls)")

    t0 = time.time()
    idx = get_cached_index(root)
    await dispatch("suggest: payment flow", idx, root)
    suggest_ms = (time.time() - t0) * 1000
    print(f"Warm suggest: {suggest_ms:.0f}ms")

    print("PERF TEST PASSED")


if __name__ == "__main__":
    asyncio.run(perf_test())
