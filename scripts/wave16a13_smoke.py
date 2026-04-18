"""Wave 16A13 smoke: literal \\n in batch, quick:, large batch (300 ops)."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch


async def test() -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        init_project(tmp)
        index = GraphIndex.load_from_disk(tmp)

        sess = await dispatch("session:start actor=test goal=smoke-16a13", index, tmp)
        sid = str(sess["session_id"])

        index = GraphIndex.load_from_disk(tmp)
        r = await dispatch(
            f"batch session_id='{sid}' ops='create: Engine: EngA | Engine A\\ncreate: Engine: EngB | Engine B'",
            index,
            tmp,
        )
        print(f"batch \\\\n: succeeded={r.get('succeeded', 0)}")
        assert r.get("succeeded", 0) >= 2, f"batch newline failed: {r}"

        index = GraphIndex.load_from_disk(tmp)
        r = await dispatch(
            f"quick: session_id='{sid}' ops='Idea Alpha | perf | wave17 | fast search\\nIdea Beta | security | wave18 | auth token'",
            index,
            tmp,
        )
        print(f"quick: succeeded={r.get('succeeded', 0)}")
        assert r.get("succeeded", 0) >= 2, r

        lines = [f"create: Node: LargeNode{i} | Node number {i}" for i in range(300)]
        ops_str = "\\n".join(lines)
        index = GraphIndex.load_from_disk(tmp)
        r = await dispatch(f"batch session_id='{sid}' ops='{ops_str}'", index, tmp)
        print(f"large batch 300: succeeded={r.get('succeeded', 0)}")
        assert r.get("succeeded", 0) >= 250, r

        index = GraphIndex.load_from_disk(tmp)
        total = len(index.all_nodes())
        print(f"total nodes after all: {total}")

        print("ALL SMOKE TESTS PASSED")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(test())
