"""Tests for sp_api.rate_limiter — RateLimiter."""

import time
import pytest
from sp_api.rate_limiter import RateLimiter


class TestRateLimiter:
    """RateLimiter test suite."""

    def test_first_request_no_wait(self):
        rl = RateLimiter(default_rate=10.0, burst=1)
        wait = rl.acquire("/test/path")
        assert wait == 0.0

    def test_burst_allows_multiple_immediate(self):
        rl = RateLimiter(default_rate=1.0, burst=5)
        for _ in range(5):
            wait = rl.acquire("/test/path")
            assert wait == 0.0

    def test_rate_limit_causes_wait(self):
        rl = RateLimiter(default_rate=100.0, burst=1)
        rl.acquire("/test/path")
        start = time.monotonic()
        rl.acquire("/test/path")
        elapsed = time.monotonic() - start
        # Should have waited ~0.01s (1/100)
        assert elapsed < 0.5  # Reasonable upper bound

    def test_custom_limits_applied(self):
        rl = RateLimiter(custom_limits={"/custom/": 1000.0}, burst=1)
        wait = rl.acquire("/custom/endpoint")
        assert wait == 0.0

    def test_default_limits_for_known_paths(self):
        rl = RateLimiter()
        # Should use the orders rate
        key = rl._bucket_key("/orders/v0/orders")
        assert key == "/orders/"

    def test_bucket_key_matching(self):
        rl = RateLimiter()
        assert rl._bucket_key("/catalog/2022-04-01/items") == "/catalog/"
        assert rl._bucket_key("/finances/v0/events") == "/finances/"
        assert rl._bucket_key("/unknown/path") == "__default__"

    def test_reset_clears_state(self):
        rl = RateLimiter(default_rate=10.0, burst=1)
        rl.acquire("/test/path")
        rl.reset()
        # After reset, should get a fresh bucket
        wait = rl.acquire("/test/path")
        assert wait == 0.0

    def test_different_paths_independent(self):
        rl = RateLimiter(default_rate=1.0, burst=1)
        rl.acquire("/orders/v0/orders")
        wait = rl.acquire("/catalog/2022/items")
        assert wait == 0.0  # Different bucket
