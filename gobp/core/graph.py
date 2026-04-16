"""GoBP graph index.

In-memory index of nodes and edges loaded from .gobp/ folder.
File-first: source of truth is markdown/YAML files on disk.
This class provides fast lookup via Python dicts.
"""

from __future__ import annotations

import json as _json
from collections import defaultdict
from pathlib import Path
from typing import Any

from gobp.core import db as _db
from gobp.core.loader import load_edge_file, load_node_file, load_schema
from gobp.core.validator import validate_edge, validate_node


PRIORITY_THRESHOLDS: list[tuple[int, str]] = [
    (20, "critical"),
    (10, "high"),
    (5, "medium"),
    (0, "low"),
]


def priority_label(score: int) -> str:
    """Convert numeric priority score to enum label."""
    for threshold, label in PRIORITY_THRESHOLDS:
        if score >= threshold:
            return label
    return "low"


class GraphIndex:
    """In-memory index of GoBP nodes and edges.

    Loads from .gobp/ folder at startup. Provides read-only query methods.
    Write operations go through mutator.py (Wave 5).

    Internal indexes for O(1) / O(k) lookups:
      _nodes          : id â†’ node dict
      _nodes_by_type  : type â†’ list[node dict]
      _edges          : flat list (source of truth)
      _edges_from     : node_id â†’ list[edge dict]
      _edges_to       : node_id â†’ list[edge dict]
      _edges_by_type  : edge_type â†’ list[edge dict]
    """

    def __init__(self) -> None:
        """Initialize empty index."""
        self._nodes: dict[str, dict[str, Any]] = {}
        self._nodes_by_type_idx: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._edges: list[dict[str, Any]] = []
        self._edges_from_idx: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._edges_to_idx: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._edges_by_type_idx: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._nodes_schema: dict[str, Any] = {}
        self._edges_schema: dict[str, Any] = {}
        self._load_errors: list[str] = []
        self._gobp_root: Path | None = None
        self._legacy_id_map: dict[str, str] = {}

    @classmethod
    def load_from_disk(cls, gobp_root: Path) -> "GraphIndex":
        """Load nodes, edges, and schemas from a GoBP project root.

        Expected folder structure:
            <gobp_root>/
                gobp/schema/core_nodes.yaml   (optional; if missing, uses installed package schema)
                gobp/schema/core_edges.yaml
            <gobp_root>/.gobp/
                nodes/*.md          (node files, optional)
                edges/*.yaml        (edge files, optional)

        Args:
            gobp_root: Project root folder (contains gobp/ package and .gobp/ data).

        Returns:
            Populated GraphIndex instance.

        Raises:
            FileNotFoundError: If schema files are missing.
        """
        index = cls()
        index._gobp_root = gobp_root

        mapping_file = gobp_root / ".gobp" / "id_mapping.json"
        if mapping_file.exists():
            try:
                mapping = _json.loads(mapping_file.read_text(encoding="utf-8"))
                index._legacy_id_map = {k: v for k, v in mapping.items() if k != v}
            except Exception:
                index._legacy_id_map = {}

        schema_dir = gobp_root / "gobp" / "schema"
        if not schema_dir.exists():
            from gobp.core.loader import package_schema_dir

            schema_dir = package_schema_dir()
        index._nodes_schema = load_schema(schema_dir / "core_nodes.yaml")
        index._edges_schema = load_schema(schema_dir / "core_edges.yaml")

        data_dir = gobp_root / ".gobp"
        index._load_nodes(data_dir / "nodes")
        index._load_edges(data_dir / "edges")

        # Build SQLite index if not exists
        try:
            _db.init_schema(gobp_root)
            if not _db.index_exists(gobp_root):
                _db.rebuild_index(gobp_root, index)
        except Exception:
            # SQLite failure is non-fatal â€” in-memory index still works
            pass

        return index

    def _load_nodes(self, nodes_dir: Path) -> None:
        """Load all node markdown files from nodes_dir into the index."""
        if not nodes_dir.exists() or not nodes_dir.is_dir():
            return
        for node_file in nodes_dir.glob("**/*.md"):
            try:
                node = load_node_file(node_file)
                result = validate_node(node, self._nodes_schema)
                if result.ok:
                    node_id = node.get("id")
                    if node_id:
                        self._nodes[node_id] = node
                        # Build type index
                        node_type = node.get("type", "Unknown")
                        self._nodes_by_type_idx[node_type].append(node)
                    else:
                        self._load_errors.append(f"{node_file}: node has no 'id' field")
                else:
                    self._load_errors.append(
                        f"{node_file}: validation failed: {result.errors}"
                    )
            except (ValueError, FileNotFoundError) as e:
                self._load_errors.append(f"{node_file}: {e}")

    def _load_edges(self, edges_dir: Path) -> None:
        """Load all edge YAML files from edges_dir into the index."""
        if not edges_dir.exists() or not edges_dir.is_dir():
            return
        for edge_file in edges_dir.glob("**/*.yaml"):
            try:
                edges = load_edge_file(edge_file)
                for edge in edges:
                    result = validate_edge(edge, self._edges_schema)
                    if result.ok:
                        self._edges.append(edge)
                        # Build edge indexes
                        from_id = edge.get("from", "")
                        to_id = edge.get("to", "")
                        edge_type = edge.get("type", "")
                        if from_id:
                            self._edges_from_idx[from_id].append(edge)
                        if to_id:
                            self._edges_to_idx[to_id].append(edge)
                        if edge_type:
                            self._edges_by_type_idx[edge_type].append(edge)
                    else:
                        self._load_errors.append(
                            f"{edge_file}: edge validation failed: {result.errors}"
                        )
            except (ValueError, FileNotFoundError) as e:
                self._load_errors.append(f"{edge_file}: {e}")

    @property
    def load_errors(self) -> list[str]:
        """Return list of errors encountered during load (non-fatal)."""
        return list(self._load_errors)

    def __len__(self) -> int:
        """Return total node count."""
        return len(self._nodes)

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        """Get node by ID. Supports both new and legacy IDs. O(1)."""
        node = self._nodes.get(node_id)
        if node:
            return node

        if self._legacy_id_map:
            new_id = self._legacy_id_map.get(node_id)
            if new_id:
                return self._nodes.get(new_id)

        return None

    def all_nodes(self) -> list[dict[str, Any]]:
        """Return all nodes as a list. O(n).

        Returns:
            List of node dicts.
        """
        return list(self._nodes.values())

    def all_edges(self) -> list[dict[str, Any]]:
        """Return all edges as a list. O(n).

        Returns:
            List of edge dicts.
        """
        return list(self._edges)

    def nodes_by_type(self, type_name: str) -> list[dict[str, Any]]:
        """Return all nodes of a given type. O(k) where k = nodes of that type.

        Args:
            type_name: Node type (e.g., "Idea", "Decision").

        Returns:
            List of nodes matching type. Empty list if none.
        """
        return list(self._nodes_by_type_idx.get(type_name, []))

    def get_edges_from(self, node_id: str) -> list[dict[str, Any]]:
        """Get all edges where `from` is the given node ID. O(k).

        Args:
            node_id: Source node ID.

        Returns:
            List of edges.
        """
        return list(self._edges_from_idx.get(node_id, []))

    def get_edges_to(self, node_id: str) -> list[dict[str, Any]]:
        """Get all edges where `to` is the given node ID. O(k).

        Args:
            node_id: Target node ID.

        Returns:
            List of edges.
        """
        return list(self._edges_to_idx.get(node_id, []))

    def get_edges_by_type(self, edge_type: str) -> list[dict[str, Any]]:
        """Get all edges of a given type. O(k).

        Args:
            edge_type: Edge type (e.g., "supersedes", "implements").

        Returns:
            List of edges matching type.
        """
        return list(self._edges_by_type_idx.get(edge_type, []))

    def compute_priority_score(self, node_id: str) -> int:
        """Compute numeric priority: edge_count + tier_weight from config."""
        from gobp.core.id_config import get_tier_weight, load_groups

        node = self.get_node(node_id)
        if not node:
            return 0

        groups = load_groups(self._gobp_root) if self._gobp_root else None
        incoming = len(self.get_edges_to(node_id))
        outgoing = len(self.get_edges_from(node_id))
        node_type = node.get("type", "Node")
        tier_weight = get_tier_weight(node_type, groups)
        return incoming + outgoing + tier_weight

