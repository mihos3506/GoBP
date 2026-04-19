"""GoBP ID Generator v2.

Format: ``{group_slug}.{name_slug}.{8hex}`` (group-embedded, human-readable prefix).

See: ``docs/ARCHITECTURE.md`` Section 4, ``waves/wave_a_brief.md`` Task 3.
"""

from __future__ import annotations

import datetime
import hashlib
import re
import uuid
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
    """
    Generate deterministic node ID v2.

    Format: {group_slug}.{name_slug}.{8hex}

    Args:
        name:  Node name, e.g. "PaymentService"
        group: Group breadcrumb, e.g. "Dev > Infrastructure > Engine"

    Returns:
        ID string, e.g. "dev.infrastructure.engine.paymentservice.a1b2c3d4"

    Examples:
        >>> generate_id("PaymentService", "Dev > Infrastructure > Engine")
        "dev.infrastructure.engine.paymentservice.a1b2c3d4"
    """
    group_slug = group.lower()
    group_slug = re.sub(r"\s*>\s*", ".", group_slug)
    group_slug = re.sub(r"[^a-z0-9.]", "", group_slug)
    group_slug = group_slug.strip(".")

    name_slug = name.lower()
    name_slug = re.sub(r"\s+", "_", name_slug)
    name_slug = re.sub(r"[^a-z0-9_]", "", name_slug)
    name_slug = name_slug.strip("_")

    hash_input = f"{name}{group}".encode("utf-8")
    hex_suffix = hashlib.md5(hash_input, usedforsecurity=False).hexdigest()[:8]

    return f"{group_slug}.{name_slug}.{hex_suffix}"


def generate_session_id(date_str: str | None = None) -> str:
    """
    Generate session ID.

    Format: meta.session.YYYY-MM-DD.{8hex}

    Args:
        date_str: ISO date string, defaults to today

    Returns:
        Session ID, e.g. "meta.session.2026-04-19.a1b2c3d4"
    """
    if date_str is None:
        date_str = datetime.date.today().isoformat()
    hex_suffix = uuid.uuid4().hex[:8]
    return f"meta.session.{date_str}.{hex_suffix}"


def infer_group_from_type(node_type: str, schema: dict[str, Any]) -> str:
    """Return default group breadcrumb for a node type from a loaded schema dict."""
    raw = schema.get("node_types") or {}
    entry = raw.get(node_type)
    if isinstance(entry, dict):
        g = entry.get("group")
        if isinstance(g, str):
            return g
    return ""
