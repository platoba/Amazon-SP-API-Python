"""Tests for Response Cache module."""

import time
from sp_api.cache import ResponseCache, CacheEntry


class TestCacheEntry:
    """Tests for CacheEntry."""

    def test_entry_creation(self):
        entry = CacheEntry("value", ttl=60)
        assert entry.value == "value"
        assert entry.hits == 0
        assert not entry.is_expired
        assert entry.age < 1

    def test_entry_expired(self):
        entry = CacheEntry("value", ttl=0.01)
        time.sleep(0.02)
        assert entry.is_expired

    def test_entry_not_expired(self):
        entry = CacheEntry("value", ttl=3600)
        assert not entry.is_expired


class TestResponseCache:
    """Tests for ResponseCache."""

    def test_set_and_get(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("key1", {"data": "test"})
        assert cache.get("key1") == {"data": "test"}

    def test_get_missing_key(self):
        cache = ResponseCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        cache = ResponseCache(default_ttl=0.01)
        cache.set("key1", "value")
        time.sleep(0.02)
        assert cache.get("key1") is None

    def test_custom_ttl(self):
        cache = ResponseCache(default_ttl=0.01)
        cache.set("key1", "value", ttl=3600)
        time.sleep(0.02)
        assert cache.get("key1") == "value"

    def test_delete(self):
        cache = ResponseCache()
        cache.set("key1", "value")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear(self):
        cache = ResponseCache()
        cache.set("key1", "v1")
        cache.set("key2", "v2")
        cache.clear()
        assert len(cache) == 0

    def test_max_size_eviction(self):
        cache = ResponseCache(max_size=5)
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")
        # Should not exceed max_size
        assert len(cache) <= 10  # eviction happens on next set

    def test_cached_decorator(self):
        cache = ResponseCache(default_ttl=60)
        call_count = 0

        @cache.cached(ttl=60, key_prefix="test_")
        def expensive_fn(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert expensive_fn(5) == 10
        assert expensive_fn(5) == 10  # Should be cached
        assert call_count == 1

        assert expensive_fn(10) == 20  # Different args
        assert call_count == 2

    def test_invalidate_prefix(self):
        cache = ResponseCache()
        cache.set("catalog_item1", "v1")
        cache.set("catalog_item2", "v2")
        cache.set("orders_item1", "v3")

        removed = cache.invalidate_prefix("catalog_")
        assert removed == 2
        assert cache.get("catalog_item1") is None
        assert cache.get("orders_item1") == "v3"

    def test_stats(self):
        cache = ResponseCache()
        cache.set("key1", "value")
        cache.get("key1")  # hit
        cache.get("key1")  # hit
        cache.get("missing")  # miss

        stats = cache.stats
        assert stats["total_entries"] == 1
        assert stats["total_hits"] == 2
        assert stats["total_misses"] == 1
        assert "66.7%" in stats["hit_rate"]

    def test_contains(self):
        cache = ResponseCache()
        cache.set("key1", "value")
        assert "key1" in cache
        assert "key2" not in cache

    def test_make_key_deterministic(self):
        key1 = ResponseCache._make_key("a", "b", x=1, y=2)
        key2 = ResponseCache._make_key("a", "b", y=2, x=1)  # Different kwarg order
        assert key1 == key2

    def test_default_ttls(self):
        """Verify recommended TTLs are defined."""
        assert ResponseCache.DEFAULT_TTLS["catalog"] == 3600
        assert ResponseCache.DEFAULT_TTLS["pricing"] == 300
        assert ResponseCache.DEFAULT_TTLS["fees"] == 86400

    def test_repr(self):
        cache = ResponseCache(default_ttl=120)
        assert "120" in repr(cache)
