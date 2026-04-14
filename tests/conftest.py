"""Shared pytest fixtures for GoBP test suite.

Key fixture: gobp_root - creates a tmp .gobp/ structure with schema files
provisioned. Any test that calls GraphIndex.load_from_disk() must use this
fixture instead of a local _make_gobp_root helper.

Background: GraphIndex.load_from_disk() requires gobp/schema/core_nodes.yaml
and gobp/schema/core_edges.yaml relative to the project root. Tests that
create a tmp root without these files will fail with FileNotFoundError.
This fixture provisions them automatically from the repo's schema files.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest


@pytest.fixture
def gobp_root(tmp_path: Path) -> Path:
    """Create a minimal .gobp/ project root for testing.

    Provisions:
    - .gobp/nodes/
    - .gobp/edges/
    - .gobp/history/
    - gobp/schema/core_nodes.yaml  (copied from repo)
    - gobp/schema/core_edges.yaml  (copied from repo)

    Returns:
        Path to the tmp project root, ready for GraphIndex.load_from_disk().
    """
    # Create .gobp structure
    (tmp_path / ".gobp" / "nodes").mkdir(parents=True)
    (tmp_path / ".gobp" / "edges").mkdir(parents=True)
    (tmp_path / ".gobp" / "history").mkdir(parents=True)

    # Provision schema files required by GraphIndex.load_from_disk()
    repo_schema = Path(__file__).parent.parent / "gobp" / "schema"
    dest_schema = tmp_path / "gobp" / "schema"
    dest_schema.mkdir(parents=True)
    shutil.copy(repo_schema / "core_nodes.yaml", dest_schema / "core_nodes.yaml")
    shutil.copy(repo_schema / "core_edges.yaml", dest_schema / "core_edges.yaml")

    return tmp_path
