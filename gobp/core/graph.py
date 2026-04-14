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

        # Load schemas (required)
        package_root = gobp_root / "gobp"
        schema_dir = package_root / "schema"
        index._nodes_schema = load_schema(schema_dir / "core_nodes.yaml")
        index._edges_schema = load_schema(schema_dir / "core_edges.yaml")

        # Load node files (optional - .gobp/nodes/ may not exist yet)
        data_dir = gobp_root / ".gobp"
        nodes_dir = data_dir / "nodes"
        if nodes_dir.exists() and nodes_dir.is_dir():
            for node_file in nodes_dir.glob("**/*.md"):
                try:
                    node = load_node_file(node_file)
                    result = validate_node(node, index._nodes_schema)
                    if result.ok:
                        node_id = node.get("id")
                        if node_id:
                            index._nodes[node_id] = node
                        else:
                            index._load_errors.append(f"{node_file}: node has no 'id' field")
                    else:
                        index._load_errors.append(f"{node_file}: validation failed: {result.errors}")
                except (ValueError, FileNotFoundError) as e:
                    index._load_errors.append(f"{node_file}: {e}")

        # Load edge files (optional)
        edges_dir = data_dir / "edges"
        if edges_dir.exists() and edges_dir.is_dir():
            for edge_file in edges_dir.glob("**/*.yaml"):
                try:
                    edges = load_edge_file(edge_file)
                    for edge in edges:
                        result = validate_edge(edge, index._edges_schema)
                        if result.ok:
                            index._edges.append(edge)
                        else:
                            index._load_errors.append(
                                f"{edge_file}: edge validation failed: {result.errors}"
                            )
                except (ValueError, FileNotFoundError) as e:
                    index._load_errors.append(f"{edge_file}: {e}")

        return index

    @property
    def load_errors(self) -> list[str]:
        """Return list of errors encountered during load (non-fatal)."""
        return list(self._load_errors)

    def __len__(self) -> int:
        """Return total node count."""
        return len(self._nodes)
