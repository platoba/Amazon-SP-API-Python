"""Tests for async client module."""

import pytest
from unittest.mock import MagicMock, patch

# Test without aiohttp dependency
from sp_api.async_client import AsyncAuthManager, AsyncSPAPI


class TestAsyncAuthManager:
    """Tests for AsyncAuthManager."""

    def test_init(self):
        auth = AsyncAuthManager("token", "id", "secret")
        assert auth.refresh_token == "token"
        assert auth.client_id == "id"
        assert auth.client_secret == "secret"
        assert not auth.is_valid

    def test_is_valid_no_token(self):
        auth = AsyncAuthManager("token", "id", "secret")
        assert not auth.is_valid

    def test_is_valid_with_token(self):
        import time
        auth = AsyncAuthManager("token", "id", "secret")
        auth._access_token = "test_token"
        auth._token_expires = time.time() + 3600
        assert auth.is_valid

    def test_is_valid_expired_token(self):
        import time
        auth = AsyncAuthManager("token", "id", "secret")
        auth._access_token = "test_token"
        auth._token_expires = time.time() - 100
        assert not auth.is_valid

    @pytest.mark.asyncio
    async def test_get_token_returns_cached(self):
        import time
        auth = AsyncAuthManager("token", "id", "secret")
        auth._access_token = "cached_token"
        auth._token_expires = time.time() + 3600
        session = MagicMock()
        result = await auth.get_token(session)
        assert result == "cached_token"


class TestAsyncSPAPI:
    """Tests for AsyncSPAPI."""

    def test_init_valid_marketplace(self):
        with patch("sp_api.async_client.aiohttp", MagicMock()):
            api = AsyncSPAPI("token", "id", "secret", marketplace="US")
            assert api.marketplace == "US"
            assert api.max_retries == 3
            assert api.max_concurrent == 10

    def test_init_invalid_marketplace(self):
        with patch("sp_api.async_client.aiohttp", MagicMock()):
            with pytest.raises(ValueError, match="Unknown marketplace"):
                AsyncSPAPI("token", "id", "secret", marketplace="INVALID")

    def test_init_no_aiohttp(self):
        with patch("sp_api.async_client.aiohttp", None):
            with pytest.raises(ImportError, match="aiohttp is required"):
                AsyncSPAPI("token", "id", "secret")

    def test_stats(self):
        with patch("sp_api.async_client.aiohttp", MagicMock()):
            api = AsyncSPAPI("token", "id", "secret")
            stats = api.stats
            assert stats["total_requests"] == 0
            assert stats["total_errors"] == 0
            assert stats["marketplace"] == "US"
            assert stats["max_concurrent"] == 10

    def test_repr(self):
        with patch("sp_api.async_client.aiohttp", MagicMock()):
            api = AsyncSPAPI("token", "id", "secret")
            r = repr(api)
            assert "AsyncSPAPI" in r
            assert "US" in r

    @pytest.mark.asyncio
    async def test_request_without_context_raises(self):
        with patch("sp_api.async_client.aiohttp", MagicMock()):
            api = AsyncSPAPI("token", "id", "secret")
            with pytest.raises(RuntimeError, match="context manager"):
                await api._request("GET", "/test")

    def test_custom_params(self):
        with patch("sp_api.async_client.aiohttp", MagicMock()):
            api = AsyncSPAPI(
                "token", "id", "secret",
                marketplace="DE",
                max_retries=5,
                timeout=60,
                max_concurrent=20,
            )
            assert api.marketplace == "DE"
            assert api.max_retries == 5
            assert api.timeout == 60
            assert api.max_concurrent == 20
