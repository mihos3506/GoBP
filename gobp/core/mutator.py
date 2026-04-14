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
