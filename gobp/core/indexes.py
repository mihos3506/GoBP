"""Secondary indexes for GraphIndex: inverted keyword + adjacency (Wave 16A14)."""

from __future__ import annotations

import re
from typing import Any

from gobp.core.search import normalize_text


def _tokenize_node_text(node: dict[str, Any]) -> set[str]:
    """Extract normalized tokens (length >= 2) from name + description."""
    desc = node.get("description", "")
    if isinstance(desc, dict):
        desc = f"{desc.get('info', '')} {desc.get('code', '')}"
    raw = f"{node.get('name', '')} {desc}"
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


class AdjacencyIndex:
    """Directed adjacency: outgoing[from] and incoming[to] lists of edge dicts."""

    def __init__(self) -> None:
        self._out: dict[str, list[dict[str, Any]]] = {}
        self._inc: dict[str, list[dict[str, Any]]] = {}

    def build(self, edges: list[dict[str, Any]]) -> None:
        """Rebuild from full edge list."""
        self._out.clear()
        self._inc.clear()
        for e in edges:
            self.add_edge(
                str(e.get("from", "")),
                str(e.get("to", "")),
                str(e.get("type", "")),
            )

    @staticmethod
    def _edge_key(e: dict[str, Any]) -> tuple[str, str, str]:
        return (str(e.get("from", "")), str(e.get("to", "")), str(e.get("type", "")))

    def add_edge(self, from_id: str, to_id: str, edge_type: str) -> None:
        """Add one edge; stores ``{"from", "to", "type"}``."""
        if not from_id or not to_id:
            return
        edge: dict[str, Any] = {"from": from_id, "to": to_id, "type": edge_type}
        ek = self._edge_key(edge)
        for bucket in (self._out.setdefault(from_id, []), self._inc.setdefault(to_id, [])):
            if not any(self._edge_key(x) == ek for x in bucket):
                bucket.append(dict(edge))

    def remove_edge(self, from_id: str, to_id: str, edge_type: str) -> None:
        """Remove edges matching the triple."""

        def _rm(bucket: dict[str, list[dict[str, Any]]], nid: str) -> None:
            lst = bucket.get(nid)
            if not lst:
                return
            kept = [
                e
                for e in lst
                if not (
                    str(e.get("from")) == from_id
                    and str(e.get("to")) == to_id
                    and str(e.get("type")) == edge_type
                )
            ]
            if kept:
                bucket[nid] = kept
            else:
                del bucket[nid]

        _rm(self._out, from_id)
        _rm(self._inc, to_id)

    def remove_node(self, node_id: str) -> None:
        """Drop all edges incident to node_id."""
        for e in list(self._out.pop(node_id, [])):
            tid = str(e.get("to", ""))
            lst = self._inc.get(tid)
            if lst:
                self._inc[tid] = [x for x in lst if str(x.get("from")) != node_id]
                if not self._inc[tid]:
                    del self._inc[tid]
        for e in list(self._inc.pop(node_id, [])):
            fid = str(e.get("from", ""))
            lst = self._out.get(fid)
            if lst:
                self._out[fid] = [x for x in lst if str(x.get("to")) != node_id]
                if not self._out[fid]:
                    del self._out[fid]

    def get_outgoing(
        self, node_id: str, exclude_types: set[str] | None = None
    ) -> list[dict[str, Any]]:
        ex = exclude_types or set()
        return [e for e in self._out.get(node_id, []) if str(e.get("type", "")) not in ex]

    def get_incoming(
        self, node_id: str, exclude_types: set[str] | None = None
    ) -> list[dict[str, Any]]:
        ex = exclude_types or set()
        return [e for e in self._inc.get(node_id, []) if str(e.get("type", "")) not in ex]

    def get_all(
        self, node_id: str, exclude_types: set[str] | None = None
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return (
            self.get_outgoing(node_id, exclude_types),
            self.get_incoming(node_id, exclude_types),
        )

    def edge_count(self, node_id: str, exclude_types: set[str] | None = None) -> int:
        o, i = self.get_all(node_id, exclude_types)
        return len(o) + len(i)
