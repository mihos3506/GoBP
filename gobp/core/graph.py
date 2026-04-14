"""GoBP graph index.

In-memory index of nodes and edges loaded from .gobp/ folder.
File-first: source of truth is markdown/YAML files on disk.
This class provides fast lookup via Python dicts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gobp.core.loader import load_edge_file, load_node_file, load_schema
from gobp.core.validator import ValidationResult, validate_edge, validate_node


class GraphIndex:
    """In-memory index of GoBP nodes and edges.

    Loads from .gobp/ folder at startup. Provides read-only query methods.
    Write operations go through mutator.py (Wave 5).
    """

    def __init__(self) -> None:
        """Initialize empty index."""
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []
        self._nodes_schema: dict[str, Any] = {}
        self._edges_schema: dict[str, Any] = {}
        self._load_errors: list[str] = []

    @classmethod
    def load_from_disk(cls, gobp_root: Path) -> GraphIndex:
        """Load nodes, edges, and schemas from a GoBP project root.

        Expected folder structure:
            <gobp_root>/
                gobp/schema/core_nodes.yaml
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

        package_root = gobp_root / "gobp"
        schema_dir = package_root / "schema"
        index._nodes_schema = load_schema(schema_dir / "core_nodes.yaml")
        index._edges_schema = load_schema(schema_dir / "core_edges.yaml")

        data_dir = gobp_root / ".gobp"
        index._load_nodes(data_dir / "nodes")
        index._load_edges(data_dir / "edges")

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
                    else:
                        self._load_errors.append(f"{node_file}: node has no 'id' field")
                else:
                    self._load_errors.append(f"{node_file}: validation failed: {result.errors}")
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
        """Get a node by ID.

        Args:
            node_id: Node ID (e.g., "node:user_login").

        Returns:
            Node dict or None if not found.
        """
        return self._nodes.get(node_id)

    def all_nodes(self) -> list[dict[str, Any]]:
        """Return all nodes as a list.

        Returns:
            List of node dicts (copies not shared with index).
        """
        return list(self._nodes.values())

    def all_edges(self) -> list[dict[str, Any]]:
        """Return all edges as a list.

        Returns:
            List of edge dicts.
        """
        return list(self._edges)

    def nodes_by_type(self, type_name: str) -> list[dict[str, Any]]:
        """Return all nodes of a given type.

        Args:
            type_name: Node type (e.g., "Idea", "Decision").

        Returns:
            List of nodes matching type. Empty list if none.
        """
        return [n for n in self._nodes.values() if n.get("type") == type_name]

    def get_edges_from(self, node_id: str) -> list[dict[str, Any]]:
        """Get all edges where `from` is the given node ID.

        Args:
            node_id: Source node ID.

        Returns:
            List of edges.
        """
        return [e for e in self._edges if e.get("from") == node_id]

    def get_edges_to(self, node_id: str) -> list[dict[str, Any]]:
        """Get all edges where `to` is the given node ID.

        Args:
            node_id: Target node ID.

        Returns:
            List of edges.
        """
        return [e for e in self._edges if e.get("to") == node_id]

    def get_edges_by_type(self, edge_type: str) -> list[dict[str, Any]]:
        """Get all edges of a given type.

        Args:
            edge_type: Edge type (e.g., "supersedes", "implements").

        Returns:
            List of edges matching type.
        """
        return [e for e in self._edges if e.get("type") == edge_type]
