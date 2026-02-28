"""
Rate limiter for SP-API calls.
Token-bucket algorithm with per-endpoint limits.
"""

import time
import threading
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token-bucket rate limiter.

    SP-API enforces per-endpoint rate limits. This class tracks tokens
    per (method, path_prefix) and blocks until a token is available.
    """

    # Default SP-API rate limits (requests per second)
    DEFAULT_LIMITS = {
        "/orders/": 0.0167,        # 1 per 60s burst, effectively ~1/min
        "/catalog/": 2.0,           # 2 per second
        "/products/pricing/": 0.5,  # 1 per 2s
        "/reports/": 0.0222,        # ~1 per 45s
        "/fba/inventory/": 2.0,     # 2 per second
        "/finances/": 0.5,          # 1 per 2s
        "/listings/": 5.0,          # 5 per second
        "/feeds/": 0.0222,          # ~1 per 45s
        "/notifications/": 1.0,     # 1 per second
    }

    def __init__(self, default_rate=1.0, burst=1, custom_limits=None):
        """
        Args:
            default_rate: Default requests per second.
            burst: Max burst tokens.
            custom_limits: Dict mapping path prefix → rate (req/s).
        """
        self.default_rate = default_rate
        self.burst = burst
        self.limits = {**self.DEFAULT_LIMITS, **(custom_limits or {})}
        self._buckets = defaultdict(lambda: {"tokens": burst, "last": time.monotonic()})
        self._lock = threading.Lock()

    def _get_rate(self, path):
        for prefix, rate in self.limits.items():
            if path.startswith(prefix):
                return rate
        return self.default_rate

    def acquire(self, path):
        """
        Block until a request token is available for the given path.
        Returns the wait time in seconds (0 if no wait needed).
        """
        rate = self._get_rate(path)
        key = self._bucket_key(path)

        with self._lock:
            bucket = self._buckets[key]
            now = time.monotonic()
            elapsed = now - bucket["last"]
            bucket["tokens"] = min(self.burst, bucket["tokens"] + elapsed * rate)
            bucket["last"] = now

            if bucket["tokens"] >= 1.0:
                bucket["tokens"] -= 1.0
                return 0.0

            wait = (1.0 - bucket["tokens"]) / rate
            bucket["tokens"] = 0.0

        logger.debug("Rate limit: waiting %.2fs for %s", wait, path)
        time.sleep(wait)

        with self._lock:
            bucket = self._buckets[key]
            bucket["last"] = time.monotonic()

        return wait

    def _bucket_key(self, path):
        for prefix in self.limits:
            if path.startswith(prefix):
                return prefix
        return "__default__"

    def reset(self):
        """Reset all rate limit buckets."""
        with self._lock:
            self._buckets.clear()
