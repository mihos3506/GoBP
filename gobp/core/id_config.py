"""GoBP ID configuration — group namespaces and external ID generation.

Reads id_groups from .gobp/config.yaml.
Falls back to DEFAULT_GROUPS if not configured.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Default group configuration
DEFAULT_GROUPS: dict[str, dict[str, Any]] = {
    "core": {
        "types": ["Decision", "Invariant", "Concept"],
        "sequence_scale": "small",
        "tier_weight": 20,
        "tier_y": -300,
    },
    "domain": {
        "types": ["Entity"],
        "sequence_scale": "large",
        "tier_weight": 10,
        "tier_y": -150,
    },
    "ops": {
        "types": ["Flow", "Engine", "Feature", "Screen", "APIEndpoint"],
        "sequence_scale": "small",
        "tier_weight": 8,
        "tier_y": 0,
    },
    "test": {
        "types": ["TestKind", "TestCase"],
        "sequence_scale": "medium",
        "tier_weight": 2,
        "tier_y": 150,
    },
    "meta": {
        "types": [
            "Session",
            "Wave",
            "Document",
            "Lesson",
            "Node",
            "Repository",
            "Idea",
        ],
        "sequence_scale": "medium",
        "tier_weight": 0,
        "tier_y": 300,
    },
}

# Type prefix mapping
TYPE_PREFIXES: dict[str, str] = {
    "Decision": "dec",
    "Invariant": "inv",
    "Concept": "con",
    "Entity": "entity",
    "Flow": "flow",
    "Engine": "engine",
    "Feature": "feat",
    "Screen": "screen",
    "APIEndpoint": "api",
    "TestKind": "kind",
    "TestCase": "case",
    "Session": "session",
    "Wave": "wave",
    "Document": "doc",
    "Lesson": "lesson",
    "Node": "node",
    "Repository": "repo",
    "Idea": "idea",
}

SEQUENCE_PADDING: dict[str, int] = {
    "small": 4,  # 0001–9999
    "medium": 6,  # 000001–999999
    "large": 8,  # 00000001–99999999
    "huge": 10,  # 0000000001–9999999999
}

# Special ID formats (not sequence-based)
SPECIAL_ID_TYPES = {"Session", "Document"}


def load_groups(gobp_root: Path) -> dict[str, dict[str, Any]]:
    """Load id_groups from .gobp/config.yaml or return defaults."""
    config_path = gobp_root / ".gobp" / "config.yaml"
    if config_path.exists():
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if config and "id_groups" in config:
                return config["id_groups"]
        except Exception:
            pass
    return DEFAULT_GROUPS


def get_group_for_type(node_type: str, groups: dict | None = None) -> str:
    """Get group namespace for a NodeType."""
    if groups is None:
        groups = DEFAULT_GROUPS
    for group_name, group_config in groups.items():
        if node_type in group_config.get("types", []):
            return group_name
    return "meta"  # fallback


def get_type_prefix(node_type: str) -> str:
    """Get short prefix for NodeType."""
    return TYPE_PREFIXES.get(node_type, node_type.lower()[:6])


def generate_external_id(
    node_type: str,
    gobp_root: Path | None = None,
    groups: dict | None = None,
) -> str:
    """Generate external ID with group namespace.

    Format: {group}.{type_prefix}:{sequence}

    Special cases:
      Session → meta.session:YYYYMMDD_XXXXXXXXX
      Document → meta.doc:{slug}_{md5[:6]}

    Args:
        node_type: NodeType string
        gobp_root: Project root (for loading group config)
        groups: Pre-loaded groups dict (avoids re-reading config)

    Returns:
        External ID string like "core.dec:0001"
    """
    from gobp.core.snowflake import generate_snowflake

    if groups is None and gobp_root is not None:
        groups = load_groups(gobp_root)
    if groups is None:
        groups = DEFAULT_GROUPS

    # Special formats
    if node_type == "Session":
        from datetime import datetime, timezone

        import uuid as _uuid

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        short_hash = _uuid.uuid4().hex[:9]
        return f"meta.session:{date_str}_{short_hash}"

    group = get_group_for_type(node_type, groups)
    prefix = get_type_prefix(node_type)
    scale = groups.get(group, {}).get("sequence_scale", "medium")
    padding = SEQUENCE_PADDING.get(scale, 6)

    # Use Snowflake lower bits for sequence part (last N digits)
    sf = generate_snowflake()
    seq = sf % (10**padding)

    return f"{group}.{prefix}:{seq:0{padding}d}"


def parse_external_id(external_id: str) -> tuple[str, str, str]:
    """Parse external ID → (group, type_prefix, sequence).

    Handles:
      "core.dec:0001"           → ("core", "dec", "0001")
      "meta.session:2026-04-16_abc" → ("meta", "session", "2026-04-16_abc")
      "flow:verify_gate"        → ("", "flow", "verify_gate")  # legacy
      "dec:d001"                → ("", "dec", "d001")           # legacy
    """
    if "." in external_id and ":" in external_id:
        dot_idx = external_id.index(".")
        colon_idx = external_id.index(":")
        if dot_idx < colon_idx:
            group = external_id[:dot_idx]
            type_prefix = external_id[dot_idx + 1 : colon_idx]
            sequence = external_id[colon_idx + 1 :]
            return group, type_prefix, sequence

    # Legacy format: "type:name"
    if ":" in external_id:
        parts = external_id.split(":", 1)
        return "", parts[0], parts[1]

    return "", "", external_id


def get_tier_y(node_type: str, groups: dict | None = None) -> float:
    """Get Y position for hierarchical viewer layout."""
    if groups is None:
        groups = DEFAULT_GROUPS
    group = get_group_for_type(node_type, groups)
    return groups.get(group, {}).get("tier_y", 0)


def get_tier_weight(node_type: str, groups: dict | None = None) -> int:
    """Get tier weight for priority computation."""
    if groups is None:
        groups = DEFAULT_GROUPS
    group = get_group_for_type(node_type, groups)
    return groups.get(group, {}).get("tier_weight", 0)
