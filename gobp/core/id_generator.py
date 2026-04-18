"""GoBP ID Generator v2.

Format: ``{group_slug}.{name_slug}.{8hex}`` (group-embedded, human-readable prefix).

See: ``docs/GOBP_SCHEMA_REDESIGN_v2.1.md``, ``waves/wave_17a01_brief.md`` Task 3.
"""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any

_ABBREV: dict[str, str] = {
    "infrastructure": "infra",
    "application": "app",
    "document": "doc",
    "constraint": "const",
    "frontend": "fe",
    "security": "sec",
    "database": "db",
    "messaging": "msg",
    "observability": "obs",
}


def _slugify(text: str) -> str:
    try:
        from unidecode import unidecode

        text = unidecode(text)
    except ImportError:
        pass
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    return text[:30] if text else "x"


def _group_to_slug(group: str) -> str:
    parts = [p.strip().lower() for p in group.split(">")]
    slugs: list[str] = []
    for p in parts:
        if not p:
            continue
        slugs.append(_ABBREV.get(p, _slugify(p)))
    return ".".join(s for s in slugs if s)


def generate_id(name: str, group: str) -> str:
    """Generate a new unique node id from display name and group breadcrumb."""
    group_slug = _group_to_slug(group)
    name_slug = _slugify(name)
    content = f"{group}:{name}:{time.time_ns()}"
    hex_suffix = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:8]
    return f"{group_slug}.{name_slug}.{hex_suffix}"


def infer_group_from_type(node_type: str, schema: dict[str, Any]) -> str:
    """Return default group breadcrumb for a node type from a loaded schema dict."""
    raw = schema.get("node_types") or {}
    entry = raw.get(node_type)
    if isinstance(entry, dict):
        g = entry.get("group")
        if isinstance(g, str):
            return g
    return ""
