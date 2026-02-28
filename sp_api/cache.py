"""
Response cache with TTL support.
Reduces API calls for frequently accessed data (catalog, pricing, inventory).
"""

import time
import hashlib
import json
import threading
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class CacheEntry:
    """Single cache entry with expiry tracking."""

    __slots__ = ("value", "expires_at", "created_at", "hits")

    def __init__(self, value, ttl):
        self.value = value
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl
        self.hits = 0

    @property
    def is_expired(self):
        return time.time() >= self.expires_at

    @property
    def age(self):
        return time.time() - self.created_at


class ResponseCache:
    """
    Thread-safe TTL cache for SP-API responses.

    Usage:
        cache = ResponseCache(default_ttl=300)  # 5 min default

        # Manual use
        cache.set("key", data, ttl=600)
        data = cache.get("key")

        # As decorator
        @cache.cached(ttl=300)
        def get_catalog(keywords):
            return api.search_catalog(keywords)

    TTL Recommendations:
        - Catalog data: 3600s (1 hour) — rarely changes
        - Pricing: 300s (5 min) — changes frequently
        - Orders: 60s (1 min) — real-time needed
        - Inventory: 600s (10 min)
        - Fees: 86400s (24 hours) — fee structure stable
    """

    DEFAULT_TTLS = {
        "catalog": 3600,
        "pricing": 300,
        "orders": 60,
        "inventory": 600,
        "fees": 86400,
        "sellers": 86400,
        "reports": 120,
    }

    def __init__(self, default_ttl=300, max_size=1000):
        self._cache = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._total_hits = 0
        self._total_misses = 0

    @staticmethod
    def _make_key(*args, **kwargs):
        """Generate a deterministic cache key from arguments."""
        raw = json.dumps({"a": args, "k": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, key):
        """Get cached value if exists and not expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._total_misses += 1
                return None
            if entry.is_expired:
                del self._cache[key]
                self._total_misses += 1
                return None
            entry.hits += 1
            self._total_hits += 1
            return entry.value

    def set(self, key, value, ttl=None):
        """Store a value in cache with TTL."""
        with self._lock:
            if len(self._cache) >= self.max_size:
                self._evict()
            self._cache[key] = CacheEntry(value, ttl or self.default_ttl)

    def delete(self, key):
        """Remove a specific key from cache."""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        """Clear the entire cache."""
        with self._lock:
            self._cache.clear()

    def _evict(self):
        """Evict expired entries first, then oldest entries."""
        now = time.time()
        # Remove expired
        expired = [k for k, v in self._cache.items() if v.expires_at <= now]
        for k in expired:
            del self._cache[k]

        # If still too large, remove oldest 25%
        if len(self._cache) >= self.max_size:
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k].created_at,
            )
            remove_count = len(sorted_keys) // 4
            for k in sorted_keys[:remove_count]:
                del self._cache[k]

    def cached(self, ttl=None, key_prefix=""):
        """
        Decorator to cache function results.

        Args:
            ttl: Time-to-live in seconds.
            key_prefix: Prefix for cache keys (helps with invalidation).
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = key_prefix + self._make_key(func.__name__, *args, **kwargs)
                result = self.get(cache_key)
                if result is not None:
                    logger.debug("Cache HIT: %s", func.__name__)
                    return result
                logger.debug("Cache MISS: %s", func.__name__)
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            wrapper.cache_clear = lambda: self.invalidate_prefix(key_prefix)
            return wrapper
        return decorator

    def invalidate_prefix(self, prefix):
        """Remove all cache entries with a matching key prefix."""
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]
            return len(keys_to_remove)

    @property
    def stats(self):
        """Cache statistics."""
        with self._lock:
            now = time.time()
            active = sum(1 for v in self._cache.values() if v.expires_at > now)
            expired = len(self._cache) - active
            return {
                "total_entries": len(self._cache),
                "active": active,
                "expired": expired,
                "total_hits": self._total_hits,
                "total_misses": self._total_misses,
                "hit_rate": (
                    f"{self._total_hits / (self._total_hits + self._total_misses) * 100:.1f}%"
                    if (self._total_hits + self._total_misses) > 0
                    else "0.0%"
                ),
                "max_size": self.max_size,
            }

    def __len__(self):
        return len(self._cache)

    def __contains__(self, key):
        entry = self._cache.get(key)
        return entry is not None and not entry.is_expired

    def __repr__(self):
        return f"ResponseCache(entries={len(self._cache)}, ttl={self.default_ttl})"
