"""Search utilities with Vietnamese normalization and relevance ranking."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gobp.core.graph import GraphIndex


def normalize_text(text: Any) -> str:
    """Normalize text for Vietnamese-aware search.

    Uses unidecode for consistent romanization:
        'đăng nhập' -> 'dang nhap'
        'Mi Hốt' -> 'Mi Hot'
        'Hà Nội' -> 'Ha Noi'
        'TrustGate' -> 'TrustGate' (ASCII unchanged)

    ``description`` may be a ``{info, code}`` dict (schema v2); it is flattened first.

    Falls back to unicodedata if unidecode not installed.
    """
    if isinstance(text, dict):
        text = f"{text.get('info', '')} {text.get('code', '')}"
    elif not isinstance(text, str):
        text = str(text if text is not None else "")
    if not text.strip():
        return ""
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
        Name starts with query: 79 (name longer than query after normalize)
        Name contains query:    60
        ID contains query:      40
        Description match:      20
        No match:                0

    After an exact name match fails, ``name_norm.startswith(query_norm)`` implies
    the name is strictly longer than the query. That score is **79** so callers
    using threshold **80** (batch duplicate guard, ``find_similar_nodes``) do not
    treat e.g. ``Place`` and ``PlaceOwnership`` as duplicates. Prefix hits still rank
    above substring-only (60) matches for ``find:``.
    """
    name_norm = normalize_text(node.get("name", ""))
    id_norm = normalize_text(node.get("id", ""))
    desc_norm = normalize_text(node.get("description", ""))

    if name_norm == query_norm:
        return 100
    if name_norm.startswith(query_norm):
        return 79
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
            return 79
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

    inv = getattr(index, "_inverted", None)
    if inv is not None:
        cand_ids = set(inv.search(query, max(limit * 20, 50)))
        if cand_ids:
            results_inv: list[tuple[int, dict]] = []
            for nid in cand_ids:
                node = index.get_node(nid)
                if not node:
                    continue
                node_type = node.get("type", "")
                if type_filter and node_type != type_filter:
                    continue
                if node_type in exclude_set:
                    continue
                score = search_score(query_norm, node)
                if score > 0:
                    results_inv.append((score, node))
            if results_inv:
                results_inv.sort(key=lambda x: -x[0])
                return results_inv[:limit]

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


def suggest_related(
    index: "GraphIndex",
    context: str,
    exclude_types: list[str] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Find nodes that might relate to a free-text task or feature name.

    Uses normalized keyword overlap between ``context`` and each node's
    ``name`` + ``description``. Intended to surface reusable graph nodes
    before creating duplicates.

    Args:
        index: Graph index.
        context: Short natural-language description (e.g. ``\"Payment Flow\"``).
        exclude_types: Node types to skip (defaults skip noisy metadata types).
        limit: Maximum suggestions to return.

    Returns:
        List of dicts with ``id``, ``type``, ``name``, ``why``, ``relevance``.
    """
    if exclude_types is None:
        exclude_types = ["Session", "Document"]

    exclude_set = set(exclude_types)
    context_norm = normalize_text(context)
    keywords = [w for w in context_norm.split() if len(w) >= 3]
    if not keywords:
        return []

    context_key = context_norm.replace(" ", "")
    suggestions: list[dict[str, Any]] = []

    def _score_suggestion(node: dict[str, Any]) -> dict[str, Any] | None:
        node_type = str(node.get("type", ""))
        if node_type in exclude_set:
            return None

        name = str(node.get("name", "") or "")
        desc = str(node.get("description", "") or "")
        name_norm = normalize_text(name).replace(" ", "")
        if context_key and name_norm == context_key:
            return None

        node_text = normalize_text(f"{name} {desc}")
        matched_keywords = [kw for kw in keywords if kw in node_text]
        if not matched_keywords:
            return None

        overlap_score = len(matched_keywords) / max(len(keywords), 1)
        name_norm_spaced = normalize_text(name)
        name_matches = [kw for kw in keywords if kw in name_norm_spaced]
        if name_matches:
            overlap_score += 0.3

        relevance = "high" if overlap_score >= 0.6 else "medium" if overlap_score >= 0.3 else "low"

        return {
            "id": node.get("id"),
            "type": node_type,
            "name": name,
            "why": f"keyword: {', '.join(matched_keywords)}",
            "relevance": relevance,
            "_score": overlap_score,
        }

    inv = getattr(index, "_inverted", None)
    if inv is not None:
        cand_ids = set(inv.search(context, max(limit * 50, 100)))
        if cand_ids:
            for nid in cand_ids:
                node = index.get_node(nid)
                if not node:
                    continue
                row = _score_suggestion(node)
                if row:
                    suggestions.append(row)
            if suggestions:
                suggestions.sort(key=lambda s: float(s.get("_score", 0.0)), reverse=True)
                for s in suggestions:
                    s.pop("_score", None)
                return suggestions[:limit]

    for node in index.all_nodes():
        row = _score_suggestion(node)
        if row:
            suggestions.append(row)

    suggestions.sort(key=lambda s: float(s.get("_score", 0.0)), reverse=True)
    for s in suggestions:
        s.pop("_score", None)

    return suggestions[:limit]
