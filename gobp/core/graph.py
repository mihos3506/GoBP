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
from gobp.core.id_config import generate_external_id
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
        self._new_nodes: dict[str, dict[str, Any]] = {}
        self._new_edges: list[dict[str, Any]] = []

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

    def remove_node(self, node_id: str) -> bool:
        """Remove node from in-memory index and drop all edges touching it.

        Returns:
            True if the node existed and was removed.
        """
        if node_id not in self._nodes:
            return False
        node = self._nodes.pop(node_id)
        ntype = node.get("type", "Unknown")
        if ntype in self._nodes_by_type_idx:
            self._nodes_by_type_idx[ntype] = [
                n for n in self._nodes_by_type_idx[ntype] if n.get("id") != node_id
            ]
            if not self._nodes_by_type_idx[ntype]:
                del self._nodes_by_type_idx[ntype]

        self._edges = [
            e for e in self._edges
            if e.get("from") != node_id and e.get("to") != node_id
        ]
        self._edges_from_idx.clear()
        self._edges_to_idx.clear()
        self._edges_by_type_idx.clear()
        for edge in self._edges:
            from_id = edge.get("from", "")
            to_id = edge.get("to", "")
            edge_type = edge.get("type", "")
            if from_id:
                self._edges_from_idx[from_id].append(edge)
            if to_id:
                self._edges_to_idx[to_id].append(edge)
            if edge_type:
                self._edges_by_type_idx[edge_type].append(edge)
        return True

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

    def has_pending_writes(self) -> bool:
        """True if in-memory batch added nodes/edges not yet flushed to disk."""
        return bool(self._new_nodes or self._new_edges)

    def add_node_in_memory(self, node: dict[str, Any]) -> str:
        """Add a validated node to the index without writing disk.

        Generates ``id`` when missing (same rules as :func:`gobp.core.id_config.generate_external_id`).
        Tracks the node in ``_new_nodes`` until :meth:`save_new_nodes_to_disk`.

        Args:
            node: Node dict; must include ``type`` and ``name``.

        Returns:
            Assigned node id.

        Raises:
            ValueError: If schema missing, validation fails, or id already exists.
        """
        if not self._nodes_schema:
            raise ValueError("GraphIndex has no nodes schema; load_from_disk first")
        data = dict(node)
        node_type = str(data.get("type", "Node"))
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("add_node_in_memory requires non-empty name")

        testkind = str(data.get("kind_id", ""))

        node_id = str(data.get("id", "")).strip()
        if not node_id:
            root = self._gobp_root
            if root is None:
                raise ValueError("gobp_root required to generate id")
            node_id = generate_external_id(
                node_type,
                name=name,
                testkind=testkind,
                gobp_root=root,
            )
        if node_id in self._nodes:
            raise ValueError(f"Node id already in index: {node_id}")

        data["id"] = node_id
        data["type"] = node_type
        data["name"] = name

        result = validate_node(data, self._nodes_schema)
        if not result.ok:
            raise ValueError(f"Node validation failed: {result.errors}")

        self._nodes[node_id] = data
        self._nodes_by_type_idx[node_type].append(data)
        self._new_nodes[node_id] = data
        return node_id

    def add_edge_in_memory(self, from_id: str, to_id: str, edge_type: str) -> bool:
        """Append edge to in-memory index; track for :meth:`save_new_edges_to_disk`.

        Returns:
            ``False`` if an identical edge already exists.
        """
        if not self._edges_schema:
            raise ValueError("GraphIndex has no edges schema; load_from_disk first")
        edge: dict[str, Any] = {"from": from_id, "to": to_id, "type": edge_type}
        result = validate_edge(edge, self._edges_schema)
        if not result.ok:
            raise ValueError(f"Edge validation failed: {result.errors}")

        for existing in self._edges:
            if (
                existing.get("from") == from_id
                and existing.get("to") == to_id
                and existing.get("type") == edge_type
            ):
                return False

        self._edges.append(edge)
        self._new_edges.append(edge)
        if from_id:
            self._edges_from_idx[from_id].append(edge)
        if to_id:
            self._edges_to_idx[to_id].append(edge)
        if edge_type:
            self._edges_by_type_idx[edge_type].append(edge)
        return True

    def remove_node_in_memory(self, node_id: str) -> bool:
        """Remove node from index; drop pending new-node entry if present."""
        self._new_nodes.pop(node_id, None)
        self._new_edges = [
            e
            for e in self._new_edges
            if e.get("from") != node_id and e.get("to") != node_id
        ]
        return self.remove_node(node_id)

    def save_new_nodes_to_disk(self, gobp_root: Path) -> dict[str, Any]:
        """Write only nodes in ``_new_nodes`` using :func:`gobp.core.mutator.create_node`."""
        from gobp.core.mutator import create_node

        nodes_written = 0
        for _node_id, node in list(self._new_nodes.items()):
            create_node(gobp_root, dict(node), self._nodes_schema, actor="GraphIndex.save_new_nodes")
            nodes_written += 1
        self._new_nodes.clear()
        return {"nodes_written": nodes_written}

    def save_new_edges_to_disk(self, gobp_root: Path) -> dict[str, Any]:
        """Append edges in ``_new_edges`` via :func:`gobp.core.mutator.create_edge`."""
        from gobp.core.mutator import create_edge

        edges_written = 0
        pending = list(self._new_edges)
        self._new_edges.clear()
        for edge in pending:
            out = create_edge(
                gobp_root,
                dict(edge),
                self._edges_schema,
                actor="GraphIndex.save_new_edges",
            )
            if out.get("action") == "created":
                edges_written += 1
        return {"edges_written": edges_written}

    def flush_pending_writes(self, gobp_root: Path) -> dict[str, Any]:
        """Persist ``_new_nodes`` then ``_new_edges`` (nodes first)."""
        n = self.save_new_nodes_to_disk(gobp_root)
        e = self.save_new_edges_to_disk(gobp_root)
        return {"nodes_written": n.get("nodes_written", 0), "edges_written": e.get("edges_written", 0)}

