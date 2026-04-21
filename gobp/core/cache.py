"""GoBP in-memory LRU cache with TTL.

Caches expensive operations like gobp_overview and GraphIndex loads.
Thread-safe via threading.Lock.

Usage:
    cache = GoBPCache(max_size=500, default_ttl=60)
    cache.set("gobp_overview", result, ttl=60)
    result = cache.get("gobp_overview")  # None if expired/missing
    cache.invalidate("gobp_overview")
    cache.invalidate_all()
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any


class GoBPCache:
    """In-memory LRU cache with per-entry TTL.

    **Invalidation policy:** See ``docs/ARCHITECTURE.md`` Section 9.4.

    - Scope: in-process only (each Python process has its own cache / singleton).
    - Default: ``max_size=500``, ``default_ttl`` seconds per entry (LRU eviction when full).
    - Writes: MCP / file mutator paths typically call ``invalidate_all()`` after mutations.
    - Multi-process: not coordinated — two MCP instances may see different cached views
      until TTL expiry or explicit refresh.

    Example:

        >>> cache = GoBPCache()
        >>> cache.set("key", {"value": 42})
        >>> cache.get("key")
        {'value': 42}
        >>> cache.invalidate_all()
        >>> cache.get("key")
        None
    """

    def __init__(self, max_size: int = 500, default_ttl: float = 60.0) -> None:
        """Initialize cache.

        Args:
            max_size: Maximum number of entries (LRU eviction beyond this).
            default_ttl: Default TTL in seconds for entries without explicit TTL.
        """
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """Get cached value. Returns None if missing or expired.

        Args:
            key: Cache key.

        Returns:
            Cached value or None.
        """
        with self._lock:
            if key not in self._cache:
                return None
            value, expire_at = self._cache[key]
            if time.monotonic() > expire_at:
                del self._cache[key]
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: TTL in seconds. Uses default_ttl if None.
        """
        expire_at = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, expire_at)
            # Evict LRU if over max_size
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def invalidate(self, key: str) -> None:
        """Remove a specific key from cache.

        Args:
            key: Cache key to remove.
        """
        with self._lock:
            self._cache.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """Remove all keys starting with prefix.

        Args:
            prefix: Key prefix to match.
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]

    def invalidate_node(self, node_id: str) -> None:
        """Invalidate cache entries whose keys mention this node id."""
        with self._lock:
            keys_to_delete = [k for k in self._cache if node_id in k]
            for key in keys_to_delete:
                del self._cache[key]

    def invalidate_edge(self, from_id: str, to_id: str) -> None:
        """Invalidate cache entries affected by an edge (either endpoint)."""
        with self._lock:
            keys_to_delete = [
                k
                for k in self._cache
                if (from_id in k) or (to_id in k)
            ]
            for key in keys_to_delete:
                del self._cache[key]

    def invalidate_all(self) -> None:
        """Clear all cache entries.

        Called after graph-affecting writes so read paths do not serve stale results.
        See ``docs/ARCHITECTURE.md`` Section 9.4.
        """
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        """Return number of entries (including possibly expired)."""
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        with self._lock:
            now = time.monotonic()
            active = sum(1 for _, (_, exp) in self._cache.items() if exp > now)
            return {
                "total_entries": len(self._cache),
                "active_entries": active,
                "max_size": self._max_size,
                "default_ttl": self._default_ttl,
            }


# Module-level singleton for MCP server use
_cache: GoBPCache | None = None


def get_cache() -> GoBPCache:
    """Get or create the module-level cache singleton."""
    global _cache
    if _cache is None:
        _cache = GoBPCache(max_size=500, default_ttl=60.0)
    return _cache


def reset_cache() -> None:
    """Reset the module-level cache singleton (for testing)."""
    global _cache
    _cache = None
