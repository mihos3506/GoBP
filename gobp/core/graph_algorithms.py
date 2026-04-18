"""Graph algorithms on GraphIndex (Wave 16A14)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gobp.core.graph import GraphIndex


def detect_cycles(
    index: "GraphIndex",
    edge_types: list[str] | None = None,
) -> list[list[str]]:
    """Find directed cycles among edges of the given types (DFS WHITE/GRAY/BLACK).

    Args:
        index: Loaded graph index.
        edge_types: Edge ``type`` values to treat as directed dependency edges.
            Defaults to ``depends_on`` and ``supersedes``.

    Returns:
        List of cycles; each cycle is a list of node ids (closed path).
    """
    if edge_types is None:
        edge_types = ["depends_on", "supersedes"]
    allowed = set(edge_types)

    graph: dict[str, list[str]] = {}
    all_nodes: set[str] = set()
    for edge in index.all_edges():
        if str(edge.get("type", "")) not in allowed:
            continue
        u = str(edge.get("from", ""))
        v = str(edge.get("to", ""))
        if not u or not v:
            continue
        graph.setdefault(u, []).append(v)
        all_nodes.add(u)
        all_nodes.add(v)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    cycles: list[list[str]] = []
    path: list[str] = []

    def dfs(u: str) -> None:
        color[u] = GRAY
        path.append(u)
        for v in graph.get(u, ()):
            cv = color.get(v, WHITE)
            if cv == WHITE:
                dfs(v)
            elif cv == GRAY and v in path:
                i = path.index(v)
                cycles.append(path[i:] + [v])
        path.pop()
        color[u] = BLACK

    for n in sorted(all_nodes):
        if color.get(n, WHITE) == WHITE:
            dfs(n)

    return cycles
