"""Wave 17A04 Task 5: backfill Wave nodes for 17A01-17A03 into the local graph (dec:d005)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch


async def _run() -> int:
    root = Path(__file__).resolve().parents[1]
    idx = GraphIndex.load_from_disk(root)
    r0 = await dispatch(
        "session:start actor='cursor' goal='Wave 17A04 Task 5 backfill waves 17A01-17A03'",
        idx,
        root,
    )
    print("start:", r0)
    if not r0.get("ok"):
        return 1
    sid = str(r0["session_id"])
    idx = GraphIndex.load_from_disk(root)
    ops = "\n".join(
        [
            "create: Wave: Wave 17A01 | Schema v2 sources, id_generator v2, file_format v2, schema_loader v2.",
            "edge+: Wave 17A01 --references--> dec:d004",
            "edge+: Wave 17A01 --references--> dec:d006",
            "create: Wave: Wave 17A02 | ValidatorV2, cutover core_nodes to v2, seed, MCP hooks, cursorrules v7.",
            "edge+: Wave 17A02 --references--> dec:d004",
            "create: Wave: Wave 17A03 | Query engine: find group, explore, get modes, suggest. cursorrules v8.",
            "edge+: Wave 17A03 --references--> dec:d004",
        ]
    )
    r1 = await dispatch(f"batch session_id='{sid}' ops='{ops}'", idx, root)
    print("batch:", r1)
    idx2 = GraphIndex.load_from_disk(root)
    r2 = await dispatch(
        f"session:end session_id='{sid}' outcome='Waves 17A01-17A03 backfilled'",
        idx2,
        root,
    )
    print("end:", r2)
    return 0 if r1.get("ok") and r2.get("ok") else 1


def main() -> None:
    sys.exit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
