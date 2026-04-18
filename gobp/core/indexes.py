"""Secondary indexes for GraphIndex: inverted keyword index (Wave 16A14)."""

from __future__ import annotations

import re
from typing import Any

from gobp.core.search import normalize_text


def _tokenize_node_text(node: dict[str, Any]) -> set[str]:
    """Extract normalized tokens (length >= 2) from name + description."""
    raw = f"{node.get('name', '')} {node.get('description', '')}"
    norm = normalize_text(raw)
    tokens = re.findall(r"[a-z0-9]+", norm)
    return {t for t in tokens if len(t) >= 2}


class InvertedIndex:
    """Maps normalized keywords to sets of node ids."""

    def __init__(self) -> None:
        self._kw_to_nodes: dict[str, set[str]] = {}
        self._node_to_tokens: dict[str, set[str]] = {}

    def build(self, nodes: list[dict[str, Any]]) -> None:
        """Rebuild index from a list of node dicts."""
        self._kw_to_nodes.clear()
        self._node_to_tokens.clear()
        for node in nodes:
            self.add_node(node)

    def add_node(self, node: dict[str, Any]) -> None:
        """Index one node (id required)."""
        nid = str(node.get("id", "")).strip()
        if not nid:
            return
        self.remove_node(nid)
        tokens = _tokenize_node_text(node)
        self._node_to_tokens[nid] = tokens
        for tok in tokens:
            self._kw_to_nodes.setdefault(tok, set()).add(nid)

    def remove_node(self, node_id: str) -> None:
        """Remove a node from the index."""
        tokens = self._node_to_tokens.pop(node_id, set())
        for tok in tokens:
            bucket = self._kw_to_nodes.get(tok)
            if not bucket:
                continue
            bucket.discard(node_id)
            if not bucket:
                del self._kw_to_nodes[tok]

    def update_node(self, node: dict[str, Any]) -> None:
        """Re-index a node after fields change."""
        self.add_node(node)

    def search(self, query: str, limit: int) -> list[str]:
        """Return node ids matching query using AND, then OR fallback.

        Results are unordered; caller should re-rank with :func:`search_score`.
        """
        q = normalize_text(query.strip())
        kws = [w for w in re.findall(r"[a-z0-9]+", q) if len(w) >= 2]
        if not kws:
            return []

        sets_list: list[set[str]] = []
        for kw in kws:
            s = self._kw_to_nodes.get(kw)
            if s:
                sets_list.append(set(s))

        if not sets_list:
            return []

        inter: set[str] = set.intersection(*sets_list)
        if inter:
            out = list(inter)
        else:
            out = list(set.union(*sets_list))

        cap = max(limit * 20, limit)
        return out[:cap]
