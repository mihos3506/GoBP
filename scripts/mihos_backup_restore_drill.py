"""Backup/restore drill for GoBP file store.

Creates a backup of <root>/.gobp, restores to a temp project, then verifies graph load.
This is a non-destructive drill for operational readiness.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from gobp.core.graph import GraphIndex


def count_graph(root: Path) -> tuple[int, int]:
    idx = GraphIndex.load_from_disk(root)
    return len(idx.all_nodes()), len(idx.all_edges())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="D:/MIHOS-v1")
    parser.add_argument("--backup-dir", default="D:/MIHOS-backups")
    parser.add_argument("--json-out", default=".gobp/history/mihos_backup_restore_drill.json")
    args = parser.parse_args()

    root = Path(args.root)
    gobp_dir = root / ".gobp"
    if not gobp_dir.exists():
        raise SystemExit(f"Missing .gobp directory: {gobp_dir}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path(args.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"mihos_gobp_{ts}"
    restore_root = backup_dir / f"mihos_restore_{ts}"
    restore_gobp = restore_root / ".gobp"

    src_nodes, src_edges = count_graph(root)
    shutil.copytree(gobp_dir, backup_path)
    shutil.copytree(backup_path, restore_gobp)
    dst_nodes, dst_edges = count_graph(restore_root)

    ok = src_nodes == dst_nodes and src_edges == dst_edges
    report = {
        "ok": ok,
        "source_root": str(root),
        "backup_path": str(backup_path),
        "restore_root": str(restore_root),
        "source_nodes": src_nodes,
        "source_edges": src_edges,
        "restore_nodes": dst_nodes,
        "restore_edges": dst_edges,
    }

    out = Path(args.json_out)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSaved report: {args.json_out}")

    if not ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
