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

# Valid TestKind values for TestCase IDs
VALID_TESTKINDS: frozenset[str] = frozenset({
    "unit", "integration", "e2e", "smoke", "performance",
    "security", "acceptance", "regression", "compatibility",
    "contract", "exploratory", "accessibility",
})


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


def make_id_slug(name: str) -> str:
    """Convert node name to slug for external ID.

    Rules:
    - Strip flow prefixes: "F1:", "F2:", "F10:" etc.
    - Strip doc prefixes: "DOC-07", "DOC-07:"
    - Strip wave prefixes: "WAVE 0", "Wave 16A03 -"
    - Lowercase + replace non-alphanumeric with underscore
    - Max 40 chars, no trailing underscores
    """
    import re as _re

    if not name:
        return ""
    name = _re.sub(r"^F\d+:\s*", "", name)
    name = _re.sub(r"^DOC-\d+[:\s]*", "", name)
    name = _re.sub(r"^WAVE?\s*[\w]+\s*[—\-]+\s*", "", name, flags=_re.IGNORECASE)
    slug = _re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug[:40].rstrip("_")


def generate_external_id(
    node_type: str,
    name: str = "",
    testkind: str = "",
    gobp_root: Path | None = None,
    groups: dict | None = None,
) -> str:
    """Generate external ID in new format: {slug}.{group}.{8digits}.

    Special formats:
      Session:  meta.session.YYYY-MM-DD.XXXXXXXXX
      TestCase: {slug}.test.{testkind}.{8digits}
    """
    from gobp.core.snowflake import generate_snowflake

    if groups is None and gobp_root is not None:
        groups = load_groups(gobp_root)
    if groups is None:
        groups = DEFAULT_GROUPS

    slug = make_id_slug(name) if name else get_type_prefix(node_type)

    if node_type == "Session":
        from datetime import datetime, timezone

        import uuid as _uuid

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        short_hash = _uuid.uuid4().hex[:9]
        return f"meta.session.{date_str}.{short_hash}"

    group = get_group_for_type(node_type, groups)
    sf = generate_snowflake()
    number = f"{sf % 100_000_000:08d}"

    if node_type == "TestCase":
        kind = testkind.lower()
        if kind not in VALID_TESTKINDS:
            kind = "unit"
        return f"{slug}.test.{kind}.{number}"

    return f"{slug}.{group}.{number}"


def parse_external_id(external_id: str) -> dict[str, str]:
    """Parse any ID format into components.

    Returns dict with: slug, group, testkind, number, format.
    """
    result = {"slug": "", "group": "", "testkind": "", "number": "", "format": "legacy"}

    if ":" in external_id:
        parts = external_id.split(":", 1)
        result["slug"] = parts[1] if len(parts) > 1 else ""
        result["group"] = parts[0]
        return result

    parts = external_id.split(".")
    result["format"] = "new"

    if len(parts) == 3:
        result["slug"] = parts[0]
        result["group"] = parts[1]
        result["number"] = parts[2]
    elif len(parts) == 4:
        if parts[1] == "test" and parts[2] in VALID_TESTKINDS:
            result["slug"] = parts[0]
            result["group"] = "test"
            result["testkind"] = parts[2]
            result["number"] = parts[3]
        elif parts[0] == "meta" and parts[1] == "session":
            result["slug"] = "session"
            result["group"] = "meta"
            result["number"] = parts[3]
        else:
            result["slug"] = parts[0]
            result["group"] = parts[1]
            result["number"] = parts[-1]
    elif len(parts) >= 2:
        result["slug"] = parts[0]
        result["group"] = parts[1]

    return result


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
