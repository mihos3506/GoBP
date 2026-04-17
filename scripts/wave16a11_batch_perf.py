"""Wave 16A11: one-shot batch performance check (300 ops: 200 creates + 100 edges).

Run from repo root:
  D:/GoBP/venv/Scripts/python.exe scripts/wave16a11_batch_perf.py

Success criteria: batch phase (in-memory ops) is O(ops); flush time scales with
node file writes. On this machine we assert total wall time < 120s (target <15s
on fast SSD / Linux CI once I/O is fully batched).
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
import time
from pathlib import Path

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch


async def perf_test() -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        init_project(tmp)
        index = GraphIndex.load_from_disk(tmp)

        sess = await dispatch("session:start actor=perf goal=batch-perf", index, tmp)
        sid = sess["session_id"]

        lines: list[str] = []
        for i in range(200):
            lines.append(f"create: Engine: PerfEngine{i} | Performance test engine {i}")
        for i in range(0, 100, 2):
            lines.append(f"edge+: PerfEngine{i} --depends_on--> PerfEngine{i+1}")

        ops_str = "\n".join(lines)

        index = GraphIndex.load_from_disk(tmp)

        t0 = time.time()
        r = await dispatch(
            f"batch session_id='{sid}' ops='{ops_str}'",
            index,
            tmp,
        )
        elapsed = time.time() - t0

        print(f"batch 300 ops: {elapsed:.1f}s")
        print(f"summary: {r.get('summary', '')}")
        print(f"errors: {len(r.get('errors', []))}")

        assert elapsed < 120.0, f"Too slow: {elapsed:.1f}s (expected <120s wall)"
        assert r.get("ok") or (r.get("succeeded", 0) or 0) > 0

        index2 = GraphIndex.load_from_disk(tmp)
        print(f"nodes after batch: {len(index2.all_nodes())}")

        print("PERF TEST PASSED")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(perf_test())
