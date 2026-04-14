"""GoBP MCP advanced tools.

Wave 6 additions:
- lessons_extract: scan graph + history for lesson candidates
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.lessons import extract_candidates


async def lessons_extract(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Scan graph + session history for lesson candidates.

    Identifies patterns that indicate learnable lessons.
    Does NOT create nodes. Returns proposals for AI/human review.

    Input:
        max_candidates: int (default 20, max 50)
        patterns: list[str] (default all: ["P1","P2","P3","P4"])

    Output:
        ok: bool
        candidates: list[dict] - each candidate has:
            pattern, title, trigger, what_happened,
            why_it_matters, mitigation, severity,
            evidence, suggested_tags
        count: int
        note: str - reminder that these are proposals, not created nodes
    """
    max_candidates = min(int(args.get("max_candidates", 20)), 50)
    requested_patterns = args.get("patterns", ["P1", "P2", "P3", "P4"])

    if not isinstance(requested_patterns, list):
        return {"ok": False, "error": "patterns must be a list of strings"}

    valid_patterns = {"P1", "P2", "P3", "P4"}
    for p in requested_patterns:
        if p not in valid_patterns:
            return {
                "ok": False,
                "error": f"Invalid pattern '{p}'. Valid: {sorted(valid_patterns)}",
            }

    all_candidates = extract_candidates(
        index=index,
        gobp_root=project_root,
        max_candidates=max_candidates,
    )

    # Filter by requested patterns
    filtered = [c for c in all_candidates if c.get("pattern") in requested_patterns]

    return {
        "ok": True,
        "candidates": filtered,
        "count": len(filtered),
        "note": (
            "These are proposals only. To create a Lesson node, "
            "review each candidate and call node_upsert with type='Lesson'."
        ),
    }
