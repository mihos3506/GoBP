"""GoBP database connection configuration.

Reads GOBP_DB_URL environment variable for PostgreSQL connection.
Falls back to SQLite if not set.

Environment variable format:
    GOBP_DB_URL=postgresql://user:password@host/dbname

For passwords with special characters, URL-encode them:
    @ -> %40
    Example: postgresql://postgres:Hieu%408283%40@localhost/gobp

Per-project configuration:
    GoBP project:   GOBP_DB_URL
    MIHOS project:  GOBP_MIHOS_DB_URL (set via GOBP_PROJECT_ROOT detection)
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Any


def get_db_url(gobp_root: Path | None = None) -> str | None:
    """Get PostgreSQL database URL from environment.

    Detection order:
    1. GOBP_DB_URL env var (explicit override)
    2. Auto-detect from GOBP_PROJECT_ROOT path
    3. None (fall back to SQLite)

    Args:
        gobp_root: Project root path for auto-detection.

    Returns:
        PostgreSQL URL string or None if not configured.
    """
    # Explicit override always wins
    url = os.environ.get("GOBP_DB_URL")
    if url:
        return url

    # Auto-detect from project root path
    if gobp_root is not None:
        root_str = str(gobp_root).lower()
        if "mihos" in root_str:
            url = os.environ.get("GOBP_MIHOS_DB_URL")
            if url:
                return url

    return None


def parse_db_url(url: str) -> dict[str, Any]:
    """Parse PostgreSQL URL into psycopg2 connection kwargs.

    Handles URL-encoded special characters in password.

    Args:
        url: PostgreSQL connection URL.

    Returns:
        Dict of kwargs for psycopg2.connect().

    Raises:
        ValueError: If URL is not a valid PostgreSQL URL.
    """
    if not url.startswith("postgresql://") and not url.startswith("postgres://"):
        raise ValueError(f"Not a PostgreSQL URL: {url}")

    r = urlparse(url)

    kwargs: dict[str, Any] = {
        "host": r.hostname or "localhost",
        "port": r.port or 5432,
        "dbname": r.path.lstrip("/") if r.path else "gobp",
        "user": r.username or "postgres",
    }

    if r.password:
        kwargs["password"] = unquote(r.password)

    return kwargs


def is_postgres_available(gobp_root: Path | None = None) -> bool:
    """Check if PostgreSQL is configured and reachable.

    Returns:
        True if PostgreSQL URL is set and connection succeeds.
    """
    url = get_db_url(gobp_root)
    if not url:
        return False

    try:
        import psycopg2

        kwargs = parse_db_url(url)
        conn = psycopg2.connect(**kwargs)
        conn.close()
        return True
    except Exception:
        return False
