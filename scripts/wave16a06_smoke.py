"""Wave 16A06 smoke: delete: + retype: (run manually or via CI)."""

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

        sess = await dispatch("session:start actor=test goal=delete-test", index, tmp)
        assert sess.get("ok"), sess
        sid = sess["session_id"]
        index = GraphIndex.load_from_disk(tmp)

        r1 = await dispatch(
            f"create:Node name='TrustGate Engine' session_id='{sid}'",
            index,
            tmp,
        )
        assert r1["ok"], f"create failed: {r1}"
        node_id = r1["node_id"]
        print(f"Created: {node_id}")
        assert ".meta." in node_id

        index = GraphIndex.load_from_disk(tmp)
        r2 = await dispatch(
            f"retype: id='{node_id}' new_type=Engine session_id='{sid}'",
            index,
            tmp,
        )
        assert r2["ok"], f"retype failed: {r2}"
        new_id = r2["new_id"]
        print(f"Retyped: {node_id} -> {new_id}")
        assert ".ops." in new_id
        assert node_id != new_id

        index = GraphIndex.load_from_disk(tmp)
        old = index.get_node(node_id)
        assert old is None, f"Old node still exists: {old}"

        new = index.get_node(new_id)
        assert new is not None
        assert new.get("type") == "Engine"
        print("retype: OK")

        r3 = await dispatch(f"delete: {new_id} session_id='{sid}'", index, tmp)
        assert r3["ok"], f"delete failed: {r3}"
        print(f"Deleted: {new_id}")

        index = GraphIndex.load_from_disk(tmp)
        gone = index.get_node(new_id)
        assert gone is None
        print("delete: OK")

        print("ALL SMOKE TESTS PASSED")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(test())
