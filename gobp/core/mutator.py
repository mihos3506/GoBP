"""GoBP mutator - create/update/delete operations.

Performs atomic file writes to .gobp/nodes/ and .gobp/edges/.
Every mutation also writes one entry to the append-only history log.

Mutator does NOT manage the in-memory GraphIndex. Callers are
responsible for reloading the index after mutation if they need
fresh state. This keeps mutator stateless and simple.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from gobp.core.history import append_event
from gobp.core.validator import validate_edge, validate_node


def _atomic_write(target_path: Path, content: str) -> None:
    """Write content to target_path atomically.

    Uses temp-file + rename pattern:
    1. Write to a temp file in the same folder as target
    2. fsync the temp file
    3. Atomically rename temp over target

    This prevents corrupted target file if the process crashes mid-write.

    Args:
        target_path: Final destination path.
        content: File content as string (UTF-8).

    Raises:
        OSError: If folder cannot be created or write fails.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same folder (ensures atomic rename works)
    fd, temp_path_str = tempfile.mkstemp(
        prefix=f".{target_path.name}.",
        suffix=".tmp",
        dir=str(target_path.parent),
    )
    temp_path = Path(temp_path_str)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename (replaces target if exists)
        os.replace(str(temp_path), str(target_path))
    except Exception:
        # Clean up temp file on any error
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def create_node(
    gobp_root: Path,
    node: dict[str, Any],
    schema: dict[str, Any],
    actor: str = "unknown",
) -> Path:
    """Create a new node file on disk.

    Validates the node against schema, writes markdown file with YAML
    frontmatter, and appends creation event to history log.

    Args:
        gobp_root: Project root.
        node: Node data dict (must have 'id' and 'type').
        schema: Nodes schema dict (from loader.load_schema).
        actor: Who is creating this node.

    Returns:
        Path to the created node file.

    Raises:
        ValueError: If node fails validation or lacks 'id'.
        FileExistsError: If node file already exists (use update_node instead).
    """
    # Validate first
    result = validate_node(node, schema)
    if not result.ok:
        raise ValueError(f"Node validation failed: {result.errors}")

    node_id = node.get("id")
    if not node_id:
        raise ValueError("Node missing 'id' field")

    # Derive filename from ID (replace ':' with '_' for filesystem safety)
    safe_name = node_id.replace(":", "_").replace("/", "_")
    node_file = gobp_root / ".gobp" / "nodes" / f"{safe_name}.md"

    if node_file.exists():
        raise FileExistsError(
            f"Node file already exists: {node_file}. Use update_node instead."
        )

    # Build markdown content with YAML frontmatter
    frontmatter_yaml = yaml.safe_dump(node, default_flow_style=False, sort_keys=False)
    content = (
        f"---\n{frontmatter_yaml}---\n\n"
        "(Auto-generated node file. Edit the YAML above or add body content below.)\n"
    )

    _atomic_write(node_file, content)

    # Log to history
    append_event(
        gobp_root=gobp_root,
        event_type="node.created",
        payload={"id": node_id, "type": node.get("type"), "file": str(node_file)},
        actor=actor,
    )

    return node_file
