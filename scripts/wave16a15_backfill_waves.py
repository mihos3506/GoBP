"""One-off backfill: Wave nodes for Wave 0,1,2,3,5 and 16A04–16A14 (Wave 16A15 Task 4).

Evidence: CHANGELOG.md section titles + dates. Does not invent facts beyond those headings.
Run from repo root:  python scripts/wave16a15_backfill_waves.py
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from gobp.core.graph import GraphIndex
from gobp.core.loader import load_schema, package_schema_dir
from gobp.core.fs_mutator import create_edge, create_node


def _meta8(slug: str) -> str:
    """8-digit suffix (schema requires [0-9]{8} after ``.meta.``)."""
    n = int(hashlib.sha256(f"wave:{slug}".encode()).hexdigest(), 16) % 100_000_000
    return f"{n:08d}"


# slug -> (display name, one-line description from CHANGELOG — no invention)
WAVES: list[tuple[str, str, str]] = [
    ("0", "Wave 0", "Repository Init — 2026-04-14 (CHANGELOG)."),
    ("1", "Wave 1", "Core Engine — 2026-04-14 (CHANGELOG)."),
    ("2", "Wave 2", "File Storage + Mutator — 2026-04-14 (CHANGELOG)."),
    ("3", "Wave 3", "MCP Server + Read Tools — 2026-04-14 (CHANGELOG)."),
    ("5", "Wave 5", "Write Tools + Import Tools + Validate — 2026-04-14 (CHANGELOG)."),
    ("16a04", "Wave 16A04", "Full test + refactor — 2026-04-16 (CHANGELOG)."),
    ("16a05", "Wave 16A05", "MCP Generator + Project Identity + Task Queue — 2026-04-16 (CHANGELOG)."),
    ("16a06", "Wave 16A06", "Delete + Retype nodes — 2026-04-17 (CHANGELOG)."),
    ("16a07", "Wave 16A07", "Search Quality + Edge Types + Duplicate Detection — 2026-04-17 (CHANGELOG)."),
    ("16a08", "Wave 16A08", "Proper Text Normalization — 2026-04-17 (CHANGELOG)."),
    ("16a09", "Wave 16A09", "Batch Ops + Explore + Suggest + Template — 2026-04-17 (CHANGELOG)."),
    ("16a10", "Wave 16A10", "Smart Template + Compact + AI Query Rules — 2026-04-17 (CHANGELOG)."),
    ("16a11", "Wave 16A11", "Batch Performance Fix — 2026-04-18 (CHANGELOG)."),
    ("16a12", "Wave 16A12", "MCP Server Cache — 2026-04-18 (CHANGELOG)."),
    ("16a13", "Wave 16A13", "Batch Fixes + Quick Capture + Auto Chunking — 2026-04-18 (CHANGELOG)."),
    ("16a14", "Wave 16A14", "Read Performance Indexes + Cycle Validation — 2026-04-18 (CHANGELOG)."),
]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / ".gobp"
    nodes_schema = load_schema(package_schema_dir() / "core_nodes.yaml")
    edges_schema = load_schema(package_schema_dir() / "core_edges.yaml")
    index = GraphIndex.load_from_disk(root)
    now = datetime.now(timezone.utc).isoformat()
    actor = "wave16a15_backfill_waves"

    created = 0
    for slug, title, desc in WAVES:
        suffix = _meta8(slug)
        wid = f"wave_{slug.replace('-', '_')}.meta.{suffix}"
        if index.get_node(wid):
            continue
        node = {
            "id": wid,
            "type": "Wave",
            "name": title,
            "status": "COMPLETED",
            "description": desc,
            "created": now,
            "updated": now,
        }
        create_node(root, node, nodes_schema, actor=actor)
        created += 1
        try:
            create_edge(
                root,
                {"from": wid, "to": "dec:d006", "type": "relates_to"},
                edges_schema,
                actor=actor,
            )
        except Exception:
            pass
        index = GraphIndex.load_from_disk(root)

    print(f"wave nodes created: {created}")


if __name__ == "__main__":
    main()
