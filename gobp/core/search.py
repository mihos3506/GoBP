"""Search utilities with Vietnamese normalization and relevance ranking."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gobp.core.graph import GraphIndex


def normalize_text(text: str) -> str:
    """Normalize text for Vietnamese-aware search.

    Uses unidecode for consistent romanization:
        'đăng nhập' -> 'dang nhap'
        'Mi Hốt' -> 'Mi Hot'
        'Hà Nội' -> 'Ha Noi'
        'TrustGate' -> 'TrustGate' (ASCII unchanged)

    Falls back to unicodedata if unidecode not installed.
    """
    try:
        from unidecode import unidecode

        return unidecode(text).lower().strip()
    except ImportError:
        import unicodedata as _uc

        nfd = _uc.normalize("NFD", text.lower())
        return "".join(c for c in nfd if _uc.category(c) != "Mn")


def search_score(query_norm: str, node: dict[str, Any]) -> int:
    """Score a node's relevance to a normalized query.

    Scoring:
        Name exact match:      100
        Name starts with query: 80
        Name contains query:    60
        ID contains query:      40
        Description match:      20
        No match:                0
    """
    name_norm = normalize_text(node.get("name", ""))
    id_norm = normalize_text(node.get("id", ""))
    desc_norm = normalize_text(node.get("description", ""))

    if name_norm == query_norm:
        return 100
    if name_norm.startswith(query_norm):
        return 80
    if query_norm in name_norm:
        return 60
    if query_norm in id_norm:
        return 40
    if query_norm in desc_norm:
        return 20
    # Space-insensitive match: "mihot" vs name "Mi Hốt Standard" → "mi hot standard" vs "mihot"
    qc = query_norm.replace(" ", "")
    if len(qc) >= 3:
        name_c = name_norm.replace(" ", "")
        id_c = id_norm.replace(" ", "")
        desc_c = desc_norm.replace(" ", "")
        if name_c == qc:
            return 100
        if name_c.startswith(qc):
            return 80
        if len(qc) >= 4 and qc in name_c:
            return 60
        if len(qc) >= 4 and qc in id_c:
            return 40
        if len(qc) >= 4 and qc in desc_c:
            return 20
    return 0


def search_nodes(
    index: "GraphIndex",
    query: str,
    type_filter: str | None = None,
    exclude_types: list[str] | None = None,
    limit: int = 20,
) -> list[tuple[int, dict]]:
    """Search nodes with Vietnamese normalization and relevance ranking.

    Args:
        index: GraphIndex to search
        query: Search term (Vietnamese-aware)
        type_filter: Only return nodes of this exact type
        exclude_types: Exclude these node types (default: Session excluded)
        limit: Max results

    Returns:
        List of (score, node) tuples, sorted by score descending
    """
    if exclude_types is None:
        exclude_types = ["Session"]

    query_norm = normalize_text(query.strip())
    if not query_norm:
        return []

    exclude_set = set(exclude_types)
    results: list[tuple[int, dict]] = []

    for node in index.all_nodes():
        node_type = node.get("type", "")

        # Exact type filter (field match, not text search)
        if type_filter and node_type != type_filter:
            continue

        # Exclude types
        if node_type in exclude_set:
            continue

        score = search_score(query_norm, node)
        if score > 0:
            results.append((score, node))

    results.sort(key=lambda x: -x[0])
    return results[:limit]


def find_similar_nodes(
    index: "GraphIndex",
    name: str,
    node_type: str | None = None,
    threshold: int = 60,
) -> list[dict]:
    """Find nodes with similar names for duplicate detection.

    Returns nodes with search_score >= threshold against the name.
    Used to warn before creating potential duplicates.
    """
    results = search_nodes(
        index,
        name,
        type_filter=node_type,
        exclude_types=[],  # Include all types for duplicate check
        limit=5,
    )
    return [node for score, node in results if score >= threshold]
