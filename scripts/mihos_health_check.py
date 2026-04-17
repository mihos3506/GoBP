"""Health check + basic alert hook for MIHOS GoBP.

Checks:
  1) Graph loads from disk
  2) find path works
  3) Session exclusion behavior works

Optional alert hook:
  ALERT_WEBHOOK_URL=https://... (POST JSON)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import urllib.request
from pathlib import Path

from gobp.core.graph import GraphIndex
from gobp.mcp.dispatcher import dispatch


async def run_checks(root: Path) -> dict[str, object]:
    started = time.time()
    index = GraphIndex.load_from_disk(root)
    total_nodes = len(index.all_nodes())

    r_find = await dispatch("find: trustgate mode=summary", index, root)
    if not r_find.get("ok"):
        raise RuntimeError(f"find failed: {r_find}")

    r_session = await dispatch("find: session mode=summary", index, root)
    leaked_session = any(m.get("type") == "Session" for m in r_session.get("matches", []))
    if leaked_session:
        raise RuntimeError("Session leaked into keyword search")

    r_explicit = await dispatch("find:Session mode=summary", index, root)
    explicit_has_session = any(
        m.get("type") == "Session" for m in r_explicit.get("matches", [])
    )
    if not explicit_has_session:
        raise RuntimeError("find:Session did not return Session nodes")

    return {
        "ok": True,
        "project_root": str(root),
        "total_nodes": total_nodes,
        "find_count": r_find.get("count", 0),
        "session_keyword_count": r_session.get("count", 0),
        "explicit_session_count": r_explicit.get("count", 0),
        "elapsed_ms": round((time.time() - started) * 1000.0, 2),
    }


def maybe_alert(payload: dict[str, object]) -> None:
    url = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    if not url:
        return
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
        resp.read()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="D:/MIHOS-v1")
    parser.add_argument("--json-out", default=".gobp/history/mihos_health_check.json")
    args = parser.parse_args()

    root = Path(args.root)
    try:
        report = asyncio.run(run_checks(root))
        status = 0
    except Exception as exc:
        report = {"ok": False, "project_root": str(root), "error": str(exc)}
        status = 2

    Path(args.json_out).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSaved report: {args.json_out}")

    if not report.get("ok"):
        maybe_alert(report)
        raise SystemExit(status)


if __name__ == "__main__":
    main()
