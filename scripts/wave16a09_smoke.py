"""Smoke verification for Wave 16A09 (template, batch, explore, suggest)."""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path


def _utf8_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


async def _main() -> None:
    _utf8_stdout()
    from gobp.core.graph import GraphIndex
    from gobp.core.init import init_project
    from gobp.mcp.dispatcher import dispatch

    tmp = Path(tempfile.mkdtemp())
    try:
        init_project(tmp)
        index = GraphIndex.load_from_disk(tmp)

        sess = await dispatch("session:start actor=test goal=batch-smoke", index, tmp)
        assert sess.get("ok"), sess
        sid = str(sess["session_id"])

        index = GraphIndex.load_from_disk(tmp)
        r1 = await dispatch("template: Engine", index, tmp)
        assert r1.get("ok"), r1
        assert "frame" in r1 and "required" in r1["frame"]
        print(f"template: Engine OK — {len(r1['frame']['required'])} required fields")

        index = GraphIndex.load_from_disk(tmp)
        ops = (
            "create: Engine: SmokeEngA | first engine\n"
            "create: Flow: SmokeFlowB | first flow\n"
            "edge+: SmokeEngA --implements--> SmokeFlowB"
        )
        r2 = await dispatch(
            f"batch session_id='{sid}' ops='{ops}'",
            index,
            tmp,
        )
        assert r2.get("ok"), r2
        print(f"batch: {r2.get('summary', r2)}")

        index = GraphIndex.load_from_disk(tmp)
        r3 = await dispatch("explore: SmokeEngA", index, tmp)
        assert r3.get("ok"), r3
        print(f"explore: found {r3.get('edge_count', 0)} edges")

        index = GraphIndex.load_from_disk(tmp)
        r4 = await dispatch("suggest: smoke engine flow", index, tmp)
        assert r4.get("ok"), r4
        print(f"suggest: {r4.get('count', 0)} suggestions")

        index = GraphIndex.load_from_disk(tmp)
        r5 = await dispatch(
            f"batch session_id='{sid}' ops='create: Engine: SmokeEngA | duplicate'",
            index,
            tmp,
        )
        assert r5.get("ok"), r5
        assert r5.get("skipped"), f"expected duplicate skip, got {r5}"
        print(f"dedupe: {len(r5['skipped'])} skipped")

        print("ALL SMOKE TESTS PASSED")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(_main())
