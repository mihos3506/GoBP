"""Wave 16A08 smoke checks on MIHOS dataset."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from gobp.core.graph import GraphIndex
from gobp.core.search import normalize_text
from gobp.mcp.dispatcher import dispatch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


async def test() -> None:
    root = Path("D:/MIHOS-v1")
    index = GraphIndex.load_from_disk(root)

    # Test dang nhap search
    r1 = await dispatch("find: dang nhap mode=summary", index, root)
    r2 = await dispatch("find: đăng nhập mode=summary", index, root)
    print(f"find dang nhap: {len(r1['matches'])} results")
    print(f"find đăng nhập: {len(r2['matches'])} results")

    # Test mihot
    r3 = await dispatch("find: mihot mode=summary", index, root)
    r4 = await dispatch("find: mi hốt mode=summary", index, root)
    print(f"find mihot: {len(r3['matches'])} results")
    print(f"find mi hốt: {len(r4['matches'])} results")

    # Test session exclusion
    r5 = await dispatch("find: session mode=summary", index, root)
    types5 = {m.get("type") for m in r5.get("matches", [])}
    has_session = "Session" in types5
    print(f"find session (no Session expected): has_session={has_session}")
    assert not has_session, f"Session nodes leaked into results: {types5}"

    # find:Session should work
    r6 = await dispatch("find:Session mode=summary", index, root)
    types6 = {m.get("type") for m in r6.get("matches", [])}
    print(f"find:Session types: {types6}")

    print("SMOKE TESTS PASSED")


def main() -> None:
    # Test normalize
    assert normalize_text("đăng nhập") == "dang nhap"
    assert normalize_text("Mi Hốt") == "mi hot"
    assert normalize_text("dang nhap") == "dang nhap"
    assert normalize_text("đăng nhập") == normalize_text("dang nhap")
    print("normalize OK")
    asyncio.run(test())


if __name__ == "__main__":
    main()
