# WAVE 1 BRIEF — CORE ENGINE

**Wave:** 1
**Title:** Core Engine — GraphIndex + Loader + Validator
**Author:** CTO Chat (Claude Opus 4.6)
**Date:** 2026-04-14
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 8 atomic tasks
**Estimated effort:** 3-4 hours

---

## CONTEXT

Wave 0 established the skeleton (package structure, schemas, templates, smoke tests). Wave 1 implements the **core engine** that reads nodes and edges from disk, validates them against schema, and indexes them in memory for fast query.

By end of Wave 1, GoBP can:
- Load schema definitions from YAML
- Validate any node/edge against schema
- Read nodes from `.gobp/nodes/*.md` files (if they exist)
- Read edges from `.gobp/edges/*.yaml` files
- Build in-memory index for fast lookup

**NOT in Wave 1:**
- MCP server (Wave 3)
- CLI commands (Wave 4)
- Write operations (Wave 5)
- Import operations (Wave 5)
- Actual `.gobp/` data folder (that's created by `gobp init` in Wave 4)

---

## ARCHITECTURE RECAP (read docs/ARCHITECTURE.md for full detail)

The core engine has 3 modules:

1. **`loader.py`** — Read YAML/Markdown files, parse to Python dicts
   - `load_schema(path) -> dict` — load core_nodes.yaml or core_edges.yaml
   - `load_node_file(path) -> dict` — parse markdown with YAML frontmatter
   - `load_edge_file(path) -> list[dict]` — parse YAML list of edges
   - `parse_frontmatter(content: str) -> tuple[dict, str]` — split `---` frontmatter from body

2. **`validator.py`** — Validate dicts against schema
   - `validate_node(node: dict, schema: dict) -> ValidationResult`
   - `validate_edge(edge: dict, schema: dict) -> ValidationResult`
   - `ValidationResult` dataclass with `ok: bool`, `errors: list[str]`, `warnings: list[str]`

3. **`graph.py`** — `GraphIndex` class, the main entry point
   - `GraphIndex.load_from_disk(gobp_path: Path) -> GraphIndex`
   - `get_node(node_id: str) -> dict | None`
   - `get_edges_from(node_id: str) -> list[dict]`
   - `get_edges_to(node_id: str) -> list[dict]`
   - `all_nodes() -> list[dict]`
   - `all_edges() -> list[dict]`
   - `nodes_by_type(type_name: str) -> list[dict]`

No SQLite in v1. Pure in-memory dict-based index. Reload from disk on startup.

---

## PREREQUISITES

Before Task 1:

```powershell
cd D:\GoBP
git status              # Expected: clean
git log --oneline -1    # Expected: Wave 0 Task 9 commit
pytest tests/test_smoke.py -v   # Expected: 13 passed
```

If any check fails, STOP.

Also verify Wave 0 stubs exist:
```powershell
Test-Path gobp/core/graph.py       # True
Test-Path gobp/core/loader.py      # True
Test-Path gobp/core/validator.py   # True
```

All should return `True`. Wave 1 will replace these stubs with implementations.

---

# TASKS

## TASK 1 — Implement loader.py frontmatter parser

**Goal:** Create function to parse markdown frontmatter (YAML block between `---` markers).

**File to modify:** `gobp/core/loader.py`

**Replace stub content with:**

```python
"""GoBP file loader.

Reads schema YAML, node markdown files, and edge YAML files from disk.
Pure parsing — no validation here (see validator.py).
"""

from pathlib import Path
from typing import Any

import yaml


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Split markdown content into YAML frontmatter and body.

    Frontmatter is delimited by lines containing only ``---``.
    Handles CRLF line endings (Windows compatibility).

    Args:
        content: Full file content as string.

    Returns:
        Tuple of (frontmatter_dict, body_string).
        If no frontmatter, returns ({}, content).

    Raises:
        ValueError: If frontmatter is malformed (missing closing ---).
    """
    # Normalize line endings for Windows
    content = content.replace("\r\n", "\n")

    if not content.startswith("---\n"):
        return {}, content

    # Find closing ---
    lines = content.split("\n")
    closing_index = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = i
            break

    if closing_index is None:
        raise ValueError("Frontmatter missing closing '---' marker")

    frontmatter_text = "\n".join(lines[1:closing_index])
    body_lines = lines[closing_index + 1:]
    body = "\n".join(body_lines)

    frontmatter_dict = yaml.safe_load(frontmatter_text) or {}

    if not isinstance(frontmatter_dict, dict):
        raise ValueError(f"Frontmatter must be a YAML mapping, got {type(frontmatter_dict).__name__}")

    return frontmatter_dict, body
```

**Acceptance criteria:**
- `gobp/core/loader.py` replaces previous stub
- Function `parse_frontmatter(content)` exists
- Has type hints and docstring
- Handles CRLF normalization
- Raises ValueError on malformed frontmatter

**Commit message:**
```
Wave 1 Task 1: implement loader.parse_frontmatter

- gobp/core/loader.py: parse_frontmatter function
- Splits YAML frontmatter from markdown body
- Normalizes CRLF line endings
- Raises ValueError on malformed frontmatter

Foundation for node file loading.
```

---

## TASK 2 — Implement loader.py file loading functions

**Goal:** Add functions to load schema, node files, and edge files.

**File to modify:** `gobp/core/loader.py`

**Add these functions AFTER `parse_frontmatter`:**

```python
def load_schema(schema_path: Path) -> dict[str, Any]:
    """Load a schema YAML file (core_nodes.yaml or core_edges.yaml).

    Args:
        schema_path: Path to schema YAML file.

    Returns:
        Parsed YAML as dict.

    Raises:
        FileNotFoundError: If schema file does not exist.
        yaml.YAMLError: If YAML is malformed.
        ValueError: If schema is missing required top-level keys.
    """
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Schema must be a YAML mapping, got {type(data).__name__}")

    if "schema_version" not in data:
        raise ValueError(f"Schema missing 'schema_version' key: {schema_path}")

    return data


def load_node_file(file_path: Path) -> dict[str, Any]:
    """Load a single node markdown file and return its frontmatter as dict.

    The node file has YAML frontmatter followed by markdown body.
    This function returns only the frontmatter dict (the structured data).
    The body is discarded (it's for humans to read, not for the graph).

    Args:
        file_path: Path to node markdown file (.md).

    Returns:
        Node data dict from frontmatter.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file has no frontmatter or malformed frontmatter.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Node file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    frontmatter, _body = parse_frontmatter(content)

    if not frontmatter:
        raise ValueError(f"Node file has no frontmatter: {file_path}")

    return frontmatter


def load_edge_file(file_path: Path) -> list[dict[str, Any]]:
    """Load an edge YAML file and return list of edge dicts.

    Edge files contain a YAML list where each item is one edge.

    Args:
        file_path: Path to edge YAML file.

    Returns:
        List of edge dicts. Empty list if file contains empty list.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If YAML content is not a list.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Edge file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return []

    if not isinstance(data, list):
        raise ValueError(f"Edge file must contain a YAML list, got {type(data).__name__}: {file_path}")

    return data
```

**Acceptance criteria:**
- 3 new functions added: `load_schema`, `load_node_file`, `load_edge_file`
- Each has type hints and docstring
- Each raises specific exceptions with descriptive messages
- `load_schema` requires `schema_version` key

**Commit message:**
```
Wave 1 Task 2: implement loader file loading functions

- gobp/core/loader.py: 3 new functions
  - load_schema(path): load YAML schema with schema_version check
  - load_node_file(path): load markdown node, return frontmatter dict
  - load_edge_file(path): load YAML edge list

Handles missing files, malformed YAML, type mismatches.
```

---

## TASK 3 — Implement validator.py ValidationResult and core validation

**Goal:** Create validation result dataclass and node validation function.

**File to modify:** `gobp/core/validator.py`

**Replace stub content with:**

```python
"""GoBP schema validator.

Validates node and edge dicts against schemas loaded by loader.py.
Returns structured ValidationResult with errors and warnings.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ValidationResult:
    """Result of validating a node or edge against a schema.

    Attributes:
        ok: True if no errors (warnings are allowed).
        errors: List of error messages. Non-empty means validation failed.
        warnings: List of warning messages. Non-blocking.
    """

    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok


def _check_type(value: Any, expected_type: str, field_name: str) -> list[str]:
    """Check if value matches the expected type string from schema.

    Returns:
        List of error messages (empty if OK).
    """
    errors: list[str] = []

    if expected_type == "str":
        if not isinstance(value, str):
            errors.append(f"{field_name}: expected str, got {type(value).__name__}")
    elif expected_type == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{field_name}: expected int, got {type(value).__name__}")
    elif expected_type == "bool":
        if not isinstance(value, bool):
            errors.append(f"{field_name}: expected bool, got {type(value).__name__}")
    elif expected_type == "timestamp":
        if not isinstance(value, (str, datetime)):
            errors.append(f"{field_name}: expected timestamp (str or datetime), got {type(value).__name__}")
    elif expected_type == "node_ref":
        if not isinstance(value, str):
            errors.append(f"{field_name}: expected node_ref (str), got {type(value).__name__}")
    elif expected_type == "list[str]":
        if not isinstance(value, list):
            errors.append(f"{field_name}: expected list, got {type(value).__name__}")
        elif not all(isinstance(x, str) for x in value):
            errors.append(f"{field_name}: all items must be str")
    elif expected_type == "list[node_ref]":
        if not isinstance(value, list):
            errors.append(f"{field_name}: expected list, got {type(value).__name__}")
        elif not all(isinstance(x, str) for x in value):
            errors.append(f"{field_name}: all node_refs must be str")
    elif expected_type == "list[dict]":
        if not isinstance(value, list):
            errors.append(f"{field_name}: expected list, got {type(value).__name__}")
        elif not all(isinstance(x, dict) for x in value):
            errors.append(f"{field_name}: all items must be dict")
    elif expected_type == "list[int]":
        if not isinstance(value, list):
            errors.append(f"{field_name}: expected list, got {type(value).__name__}")
        elif not all(isinstance(x, int) for x in value):
            errors.append(f"{field_name}: all items must be int")
    elif expected_type == "dict":
        if not isinstance(value, dict):
            errors.append(f"{field_name}: expected dict, got {type(value).__name__}")
    elif expected_type == "enum":
        # enum validation handled separately via enum_values
        pass

    return errors


def _check_field(
    data: dict[str, Any],
    field_name: str,
    field_spec: dict[str, Any],
    is_required: bool,
) -> list[str]:
    """Check a single field against its schema spec.

    Returns:
        List of error messages (empty if OK).
    """
    errors: list[str] = []

    if field_name not in data:
        if is_required:
            errors.append(f"missing required field: {field_name}")
        return errors

    value = data[field_name]
    field_type = field_spec.get("type", "str")

    # Enum check
    if field_type == "enum":
        enum_values = field_spec.get("enum_values", [])
        if value not in enum_values:
            errors.append(
                f"{field_name}: value '{value}' not in allowed enum {enum_values}"
            )
    else:
        errors.extend(_check_type(value, field_type, field_name))

    # Pattern check (for str fields)
    if "pattern" in field_spec and isinstance(value, str):
        pattern = field_spec["pattern"]
        if not re.match(pattern, value):
            errors.append(f"{field_name}: value '{value}' does not match pattern {pattern}")

    return errors


def validate_node(node: dict[str, Any], schema: dict[str, Any]) -> ValidationResult:
    """Validate a node dict against the core_nodes schema.

    Args:
        node: Node data dict (from loader.load_node_file).
        schema: Schema dict (from loader.load_schema on core_nodes.yaml).

    Returns:
        ValidationResult with ok=True if valid.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Determine node type
    node_type = node.get("type")
    if not node_type:
        return ValidationResult(
            ok=False,
            errors=["node missing 'type' field"],
        )

    # Find type definition in schema
    node_types = schema.get("node_types", {})
    if node_type not in node_types:
        return ValidationResult(
            ok=False,
            errors=[f"unknown node type: {node_type}. Known: {list(node_types.keys())}"],
        )

    type_def = node_types[node_type]

    # Check required fields
    required = type_def.get("required", {})
    for field_name, field_spec in required.items():
        errors.extend(_check_field(node, field_name, field_spec, is_required=True))

    # Check optional fields (only if present)
    optional = type_def.get("optional", {})
    for field_name, field_spec in optional.items():
        errors.extend(_check_field(node, field_name, field_spec, is_required=False))

    # Warn about unknown fields
    known_fields = set(required.keys()) | set(optional.keys())
    unknown_fields = set(node.keys()) - known_fields
    for unknown in unknown_fields:
        warnings.append(f"unknown field: {unknown}")

    return ValidationResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
```

**Acceptance criteria:**
- `ValidationResult` dataclass with `ok`, `errors`, `warnings` fields
- `validate_node` function with type hints and docstring
- Helper functions `_check_type` and `_check_field`
- Handles: missing required, wrong type, wrong enum value, pattern mismatch, unknown fields (warning)
- Returns structured result, not raising

**Commit message:**
```
Wave 1 Task 3: implement validator ValidationResult and validate_node

- gobp/core/validator.py: core validation logic
- ValidationResult dataclass (ok, errors, warnings)
- validate_node(node, schema) -> ValidationResult
- Checks: required fields, types, enums, patterns
- Warns on unknown fields (non-blocking)

Returns structured result; does not raise on validation failure.
```

---

## TASK 4 — Implement validator.py validate_edge

**Goal:** Add edge validation function.

**File to modify:** `gobp/core/validator.py`

**Add AFTER `validate_node`:**

```python
def validate_edge(edge: dict[str, Any], schema: dict[str, Any]) -> ValidationResult:
    """Validate an edge dict against the core_edges schema.

    Args:
        edge: Edge data dict.
        schema: Schema dict (from loader.load_schema on core_edges.yaml).

    Returns:
        ValidationResult.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Determine edge type
    edge_type = edge.get("type")
    if not edge_type:
        return ValidationResult(
            ok=False,
            errors=["edge missing 'type' field"],
        )

    # Find type definition
    edge_types = schema.get("edge_types", {})
    if edge_type not in edge_types:
        return ValidationResult(
            ok=False,
            errors=[f"unknown edge type: {edge_type}. Known: {list(edge_types.keys())}"],
        )

    type_def = edge_types[edge_type]

    # Check required fields (from, to, type at minimum)
    required = type_def.get("required", {})
    for field_name, field_spec in required.items():
        errors.extend(_check_field(edge, field_name, field_spec, is_required=True))

    # Check optional fields
    optional = type_def.get("optional", {})
    for field_name, field_spec in optional.items():
        errors.extend(_check_field(edge, field_name, field_spec, is_required=False))

    # Unknown field warnings
    known_fields = set(required.keys()) | set(optional.keys())
    unknown_fields = set(edge.keys()) - known_fields
    for unknown in unknown_fields:
        warnings.append(f"unknown field: {unknown}")

    return ValidationResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
```

**Acceptance criteria:**
- `validate_edge` function added
- Same signature pattern as `validate_node`
- Reuses `_check_field` helper
- Validates type, required fields, optional fields

**Commit message:**
```
Wave 1 Task 4: implement validator validate_edge

- gobp/core/validator.py: validate_edge function
- Same pattern as validate_node
- Validates edge type, required/optional fields
- Returns ValidationResult
```

---

## TASK 5 — Implement graph.py GraphIndex class (load)

**Goal:** Create GraphIndex class with load_from_disk method.

**File to modify:** `gobp/core/graph.py`

**Replace stub content with:**

```python
"""GoBP graph index.

In-memory index of nodes and edges loaded from .gobp/ folder.
File-first: source of truth is markdown/YAML files on disk.
This class provides fast lookup via Python dicts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gobp.core.loader import load_edge_file, load_node_file, load_schema
from gobp.core.validator import validate_edge, validate_node, ValidationResult


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

        # Load node files (optional — .gobp/nodes/ may not exist yet)
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
                        index._load_errors.append(
                            f"{node_file}: validation failed: {result.errors}"
                        )
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
```

**Acceptance criteria:**
- `GraphIndex` class with `__init__`, `load_from_disk`, `load_errors`, `__len__`
- Type hints everywhere, docstrings on all public members
- Handles missing `.gobp/` folder gracefully (empty index)
- Handles missing `nodes/` or `edges/` gracefully
- Collects load errors instead of crashing on individual file failures
- Validates every node/edge on load

**Commit message:**
```
Wave 1 Task 5: implement GraphIndex.load_from_disk

- gobp/core/graph.py: GraphIndex class
- load_from_disk(gobp_root) classmethod
- Loads schemas (required)
- Loads nodes and edges from .gobp/ (optional)
- Validates on load, collects errors in load_errors property
- Gracefully handles missing folders

In-memory index foundation. Query methods in Task 6.
```

---

## TASK 6 — Implement graph.py query methods

**Goal:** Add read-only query methods to GraphIndex.

**File to modify:** `gobp/core/graph.py`

**Add these methods to `GraphIndex` class (after `__len__`):**

```python
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
```

**Acceptance criteria:**
- 6 query methods added
- All have type hints and docstrings
- All return copies/lists, not internal references
- `get_node` returns None (not raises) for missing

**Commit message:**
```
Wave 1 Task 6: implement GraphIndex query methods

- gobp/core/graph.py: 6 query methods
  - get_node(id)
  - all_nodes()
  - all_edges()
  - nodes_by_type(type_name)
  - get_edges_from(node_id)
  - get_edges_to(node_id)
  - get_edges_by_type(edge_type)

Read-only access to loaded data. No write methods (Wave 5).
```

---

## TASK 7 — Write loader and validator tests

**Goal:** Test loader.py and validator.py functions.

**File to create:** `tests/test_loader_validator.py`

**Content:**

```python
"""Tests for loader.py and validator.py."""

from pathlib import Path

import pytest
import yaml

from gobp.core.loader import (
    load_edge_file,
    load_node_file,
    load_schema,
    parse_frontmatter,
)
from gobp.core.validator import ValidationResult, validate_edge, validate_node


# =============================================================================
# parse_frontmatter tests
# =============================================================================


def test_parse_frontmatter_basic():
    content = "---\nid: test\ntype: Node\n---\nBody here"
    fm, body = parse_frontmatter(content)
    assert fm == {"id": "test", "type": "Node"}
    assert body == "Body here"


def test_parse_frontmatter_crlf():
    content = "---\r\nid: test\r\ntype: Node\r\n---\r\nBody"
    fm, body = parse_frontmatter(content)
    assert fm["id"] == "test"
    assert "Body" in body


def test_parse_frontmatter_empty_body():
    content = "---\nid: test\n---\n"
    fm, body = parse_frontmatter(content)
    assert fm == {"id": "test"}


def test_parse_frontmatter_no_frontmatter():
    content = "Just plain text without frontmatter"
    fm, body = parse_frontmatter(content)
    assert fm == {}
    assert body == content


def test_parse_frontmatter_malformed_raises():
    content = "---\nid: test\nno closing marker"
    with pytest.raises(ValueError, match="missing closing"):
        parse_frontmatter(content)


# =============================================================================
# load_schema tests
# =============================================================================


def test_load_schema_nodes(tmp_path: Path):
    schema_content = {
        "schema_version": "1.0",
        "node_types": {"Node": {"required": {"id": {"type": "str"}}}},
    }
    schema_file = tmp_path / "schema.yaml"
    schema_file.write_text(yaml.dump(schema_content))

    loaded = load_schema(schema_file)
    assert loaded["schema_version"] == "1.0"
    assert "Node" in loaded["node_types"]


def test_load_schema_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_schema(tmp_path / "nonexistent.yaml")


def test_load_schema_missing_version_raises(tmp_path: Path):
    schema_file = tmp_path / "bad.yaml"
    schema_file.write_text("node_types: {}")

    with pytest.raises(ValueError, match="schema_version"):
        load_schema(schema_file)


def test_load_core_schemas_actual():
    """Load the actual GoBP core schemas."""
    import gobp
    schema_dir = Path(gobp.__file__).parent / "schema"

    nodes_schema = load_schema(schema_dir / "core_nodes.yaml")
    edges_schema = load_schema(schema_dir / "core_edges.yaml")

    assert nodes_schema["schema_version"] == "1.0"
    assert edges_schema["schema_version"] == "1.0"
    assert "node_types" in nodes_schema
    assert "edge_types" in edges_schema


# =============================================================================
# load_node_file tests
# =============================================================================


def test_load_node_file(tmp_path: Path):
    node_content = """---
id: node:test
type: Node
name: Test Node
status: ACTIVE
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
---

Body content here.
"""
    node_file = tmp_path / "test_node.md"
    node_file.write_text(node_content)

    data = load_node_file(node_file)
    assert data["id"] == "node:test"
    assert data["type"] == "Node"


def test_load_node_file_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_node_file(tmp_path / "nope.md")


def test_load_node_file_no_frontmatter_raises(tmp_path: Path):
    bad_file = tmp_path / "bad.md"
    bad_file.write_text("Just content, no frontmatter")

    with pytest.raises(ValueError, match="no frontmatter"):
        load_node_file(bad_file)


# =============================================================================
# load_edge_file tests
# =============================================================================


def test_load_edge_file_list(tmp_path: Path):
    edge_content = """
- from: node:a
  to: node:b
  type: relates_to
- from: node:b
  to: node:c
  type: implements
"""
    edge_file = tmp_path / "edges.yaml"
    edge_file.write_text(edge_content)

    edges = load_edge_file(edge_file)
    assert len(edges) == 2
    assert edges[0]["type"] == "relates_to"


def test_load_edge_file_empty(tmp_path: Path):
    edge_file = tmp_path / "empty.yaml"
    edge_file.write_text("")

    edges = load_edge_file(edge_file)
    assert edges == []


def test_load_edge_file_not_list_raises(tmp_path: Path):
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("not_a_list: true")

    with pytest.raises(ValueError, match="must contain a YAML list"):
        load_edge_file(bad_file)


# =============================================================================
# validate_node tests
# =============================================================================


@pytest.fixture
def sample_nodes_schema():
    return {
        "schema_version": "1.0",
        "node_types": {
            "Node": {
                "required": {
                    "id": {"type": "str", "pattern": r"^node:[a-z][a-z0-9_]*$"},
                    "type": {"type": "str"},
                    "name": {"type": "str"},
                    "status": {
                        "type": "enum",
                        "enum_values": ["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"],
                    },
                    "created": {"type": "timestamp"},
                    "updated": {"type": "timestamp"},
                },
                "optional": {
                    "tags": {"type": "list[str]"},
                },
            }
        },
    }


def test_validate_node_valid(sample_nodes_schema):
    node = {
        "id": "node:test",
        "type": "Node",
        "name": "Test",
        "status": "ACTIVE",
        "created": "2026-04-14T00:00:00",
        "updated": "2026-04-14T00:00:00",
    }
    result = validate_node(node, sample_nodes_schema)
    assert result.ok
    assert result.errors == []


def test_validate_node_missing_required(sample_nodes_schema):
    node = {"id": "node:test", "type": "Node"}  # missing name, status, etc.
    result = validate_node(node, sample_nodes_schema)
    assert not result.ok
    assert any("name" in e for e in result.errors)


def test_validate_node_invalid_enum(sample_nodes_schema):
    node = {
        "id": "node:test",
        "type": "Node",
        "name": "Test",
        "status": "INVALID_STATUS",
        "created": "2026-04-14T00:00:00",
        "updated": "2026-04-14T00:00:00",
    }
    result = validate_node(node, sample_nodes_schema)
    assert not result.ok
    assert any("enum" in e for e in result.errors)


def test_validate_node_pattern_fail(sample_nodes_schema):
    node = {
        "id": "BAD_ID",  # doesn't match pattern
        "type": "Node",
        "name": "Test",
        "status": "ACTIVE",
        "created": "2026-04-14T00:00:00",
        "updated": "2026-04-14T00:00:00",
    }
    result = validate_node(node, sample_nodes_schema)
    assert not result.ok
    assert any("pattern" in e for e in result.errors)


def test_validate_node_unknown_type(sample_nodes_schema):
    node = {"id": "x:1", "type": "UnknownType"}
    result = validate_node(node, sample_nodes_schema)
    assert not result.ok
    assert any("unknown node type" in e for e in result.errors)


def test_validate_node_missing_type(sample_nodes_schema):
    node = {"id": "x:1"}
    result = validate_node(node, sample_nodes_schema)
    assert not result.ok
    assert any("type" in e for e in result.errors)


def test_validate_node_unknown_field_warns(sample_nodes_schema):
    node = {
        "id": "node:test",
        "type": "Node",
        "name": "Test",
        "status": "ACTIVE",
        "created": "2026-04-14T00:00:00",
        "updated": "2026-04-14T00:00:00",
        "extra_unknown_field": "hello",
    }
    result = validate_node(node, sample_nodes_schema)
    assert result.ok  # warnings don't fail
    assert any("extra_unknown_field" in w for w in result.warnings)


# =============================================================================
# validate_edge tests
# =============================================================================


@pytest.fixture
def sample_edges_schema():
    return {
        "schema_version": "1.0",
        "edge_types": {
            "relates_to": {
                "required": {
                    "from": {"type": "node_ref"},
                    "to": {"type": "node_ref"},
                    "type": {"type": "str", "enum_values": ["relates_to"]},
                },
                "optional": {
                    "reason": {"type": "str"},
                },
            }
        },
    }


def test_validate_edge_valid(sample_edges_schema):
    edge = {"from": "node:a", "to": "node:b", "type": "relates_to"}
    result = validate_edge(edge, sample_edges_schema)
    assert result.ok


def test_validate_edge_missing_from(sample_edges_schema):
    edge = {"to": "node:b", "type": "relates_to"}
    result = validate_edge(edge, sample_edges_schema)
    assert not result.ok
    assert any("from" in e for e in result.errors)


def test_validate_edge_unknown_type(sample_edges_schema):
    edge = {"from": "node:a", "to": "node:b", "type": "unknown_edge"}
    result = validate_edge(edge, sample_edges_schema)
    assert not result.ok


# =============================================================================
# ValidationResult tests
# =============================================================================


def test_validation_result_truthy():
    ok_result = ValidationResult(ok=True)
    assert bool(ok_result) is True

    fail_result = ValidationResult(ok=False, errors=["e"])
    assert bool(fail_result) is False
```

**Acceptance criteria:**
- File `tests/test_loader_validator.py` created
- At least 22 test functions
- All tests pass
- Uses pytest fixtures for schemas
- Tests both success and failure paths
- Tests CRLF, empty files, missing files, malformed data

**Commit message:**
```
Wave 1 Task 7: write loader and validator tests

- tests/test_loader_validator.py: 22+ tests
  - parse_frontmatter: 5 tests (basic, CRLF, empty, no FM, malformed)
  - load_schema: 4 tests (valid, missing file, missing version, actual GoBP schemas)
  - load_node_file: 3 tests
  - load_edge_file: 3 tests
  - validate_node: 7 tests (valid, missing, enum, pattern, unknown type, warnings)
  - validate_edge: 3 tests
  - ValidationResult: 1 test

All tests cover happy path + error paths + edge cases.
```

---

## TASK 8 — Write GraphIndex tests

**Goal:** Test GraphIndex class integration.

**File to create:** `tests/test_graph.py`

**Content:**

```python
"""Tests for GraphIndex class."""

from pathlib import Path

import pytest

from gobp.core.graph import GraphIndex


@pytest.fixture
def empty_gobp_root(tmp_path: Path) -> Path:
    """Create minimal GoBP root with schemas but no data."""
    # Copy actual schemas
    import gobp
    actual_schema_dir = Path(gobp.__file__).parent / "schema"

    # Create structure
    pkg_dir = tmp_path / "gobp"
    schema_dir = pkg_dir / "schema"
    schema_dir.mkdir(parents=True)

    # Copy schemas
    (schema_dir / "core_nodes.yaml").write_text(
        (actual_schema_dir / "core_nodes.yaml").read_text(encoding="utf-8"),
        encoding="utf-8"
    )
    (schema_dir / "core_edges.yaml").write_text(
        (actual_schema_dir / "core_edges.yaml").read_text(encoding="utf-8"),
        encoding="utf-8"
    )

    return tmp_path


@pytest.fixture
def populated_gobp_root(empty_gobp_root: Path) -> Path:
    """Create GoBP root with sample nodes and edges."""
    data_dir = empty_gobp_root / ".gobp"
    nodes_dir = data_dir / "nodes"
    edges_dir = data_dir / "edges"
    nodes_dir.mkdir(parents=True)
    edges_dir.mkdir(parents=True)

    # Create 2 nodes
    (nodes_dir / "node1.md").write_text(
        """---
id: node:first
type: Node
name: First
status: ACTIVE
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
---

Body.
""",
        encoding="utf-8"
    )

    (nodes_dir / "node2.md").write_text(
        """---
id: node:second
type: Node
name: Second
status: ACTIVE
created: 2026-04-14T00:00:00
updated: 2026-04-14T00:00:00
---

Body.
""",
        encoding="utf-8"
    )

    # Create edges
    (edges_dir / "rels.yaml").write_text(
        """- from: node:first
  to: node:second
  type: relates_to
""",
        encoding="utf-8"
    )

    return empty_gobp_root


def test_empty_index_has_zero_len():
    index = GraphIndex()
    assert len(index) == 0
    assert index.all_nodes() == []
    assert index.all_edges() == []


def test_load_empty_gobp_root(empty_gobp_root: Path):
    """Loading a root with schemas but no data yields empty index."""
    index = GraphIndex.load_from_disk(empty_gobp_root)
    assert len(index) == 0
    assert index.load_errors == []


def test_load_populated_gobp_root(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    assert len(index) == 2
    assert index.load_errors == []


def test_get_node(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)

    node = index.get_node("node:first")
    assert node is not None
    assert node["name"] == "First"

    missing = index.get_node("node:nonexistent")
    assert missing is None


def test_all_nodes(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    nodes = index.all_nodes()
    assert len(nodes) == 2
    names = {n["name"] for n in nodes}
    assert names == {"First", "Second"}


def test_all_edges(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    edges = index.all_edges()
    assert len(edges) == 1
    assert edges[0]["type"] == "relates_to"


def test_nodes_by_type(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    nodes = index.nodes_by_type("Node")
    assert len(nodes) == 2

    ideas = index.nodes_by_type("Idea")
    assert ideas == []


def test_get_edges_from(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    edges = index.get_edges_from("node:first")
    assert len(edges) == 1
    assert edges[0]["to"] == "node:second"

    none_edges = index.get_edges_from("node:nonexistent")
    assert none_edges == []


def test_get_edges_to(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    edges = index.get_edges_to("node:second")
    assert len(edges) == 1
    assert edges[0]["from"] == "node:first"


def test_get_edges_by_type(populated_gobp_root: Path):
    index = GraphIndex.load_from_disk(populated_gobp_root)
    edges = index.get_edges_by_type("relates_to")
    assert len(edges) == 1

    none = index.get_edges_by_type("implements")
    assert none == []


def test_load_errors_collected_not_raised(empty_gobp_root: Path):
    """Bad node files should add to load_errors, not crash."""
    nodes_dir = empty_gobp_root / ".gobp" / "nodes"
    nodes_dir.mkdir(parents=True)

    # Invalid node file (missing frontmatter)
    (nodes_dir / "bad.md").write_text("Just text, no frontmatter", encoding="utf-8")

    index = GraphIndex.load_from_disk(empty_gobp_root)
    assert len(index) == 0
    assert len(index.load_errors) > 0
    assert "bad.md" in index.load_errors[0]
```

**Run both test files:**
```powershell
pytest tests/ -v
```

**Acceptance criteria:**
- File `tests/test_graph.py` created
- At least 11 test functions
- All tests pass (including Wave 0 smoke tests + Wave 1 tests)
- Uses tmp_path fixtures for isolation
- Tests empty, populated, and error scenarios

**Commit message:**
```
Wave 1 Task 8: write GraphIndex integration tests

- tests/test_graph.py: 11 tests
  - Empty index behavior
  - Load from empty and populated roots
  - get_node (found + missing)
  - all_nodes / all_edges
  - nodes_by_type / get_edges_by_type
  - get_edges_from / get_edges_to
  - Load error collection (non-fatal)

Verifies GraphIndex works end-to-end with real loader + validator.
All Wave 0 + Wave 1 tests now passing.
```

---

# POST-WAVE VERIFICATION

After all 8 tasks committed:

```powershell
# All tests pass
pytest tests/ -v
# Expected: 13 (Wave 0) + 22+ (Task 7) + 11 (Task 8) = 46+ tests passing

# Smoke test GraphIndex manually
python -c "from gobp.core.graph import GraphIndex; from pathlib import Path; g = GraphIndex.load_from_disk(Path('.')); print(f'Loaded {len(g)} nodes, {len(g.all_edges())} edges')"
# Expected: "Loaded 0 nodes, 0 edges" (no .gobp/ data folder yet)

# Git log
git log --oneline | Select-Object -First 8
# Expected: 8 Task commits
```

---

# ESCALATION TRIGGERS

Stop and escalate if:
- pytest fails and Cursor cannot fix after 3 retries
- Schema structure doesn't match code expectations (may need CTO to revise)
- Validation logic ambiguous for a specific field type

---

# WHAT COMES NEXT

After Wave 1 pushed:
- **Wave 2** — File storage patterns, history log, mutator skeleton
- **Wave 3** — MCP server + 6 read tools
- **Wave 4** — CLI commands
- **Wave 5** — Write and import tools

---

*Wave 1 Brief v0.1*
*Author: CTO Chat (Claude Opus 4.6)*
*Date: 2026-04-14*

◈
