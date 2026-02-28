"""Tests for sp_api.auth — AuthManager."""

import time
import pytest
from unittest.mock import patch, MagicMock
from sp_api.auth import AuthManager
from sp_api.exceptions import SPAPIAuthError


class TestAuthManager:
    """AuthManager test suite."""

    def test_access_token_fetched_on_first_call(self, auth_manager, mock_token_response):
        token = auth_manager.access_token
        assert token == "test_access_token_123"
        mock_token_response.assert_called_once()

    def test_token_cached_on_subsequent_calls(self, auth_manager, mock_token_response):
        t1 = auth_manager.access_token
        t2 = auth_manager.access_token
        assert t1 == t2
        assert mock_token_response.call_count == 1  # Only one HTTP call

    def test_token_refresh_on_expiry(self, auth_manager, mock_token_response):
        _ = auth_manager.access_token
        # Simulate token expiry
        auth_manager._token_expires = time.time() - 10
        _ = auth_manager.access_token
        assert mock_token_response.call_count == 2

    def test_force_refresh(self, auth_manager, mock_token_response):
        _ = auth_manager.access_token
        auth_manager.force_refresh()
        assert mock_token_response.call_count == 2

    def test_invalidate_clears_token(self, auth_manager, mock_token_response):
        _ = auth_manager.access_token
        auth_manager.invalidate()
        assert auth_manager._access_token is None
        assert auth_manager._token_expires == 0.0

    def test_on_refresh_callback(self, auth_manager, mock_token_response):
        captured = []
        auth_manager.on_refresh(lambda t: captured.append(t))
        _ = auth_manager.access_token
        assert captured == ["test_access_token_123"]

    def test_auth_error_on_http_failure(self):
        with patch("sp_api.auth.requests.post") as mock_post:
            from requests.exceptions import ConnectionError
            mock_post.side_effect = ConnectionError("Connection refused")
            mgr = AuthManager("tok", "cid", "sec")
            with pytest.raises(SPAPIAuthError):
                _ = mgr.access_token

    def test_auth_error_on_invalid_response(self):
        with patch("sp_api.auth.requests.post") as mock_post:
            resp = MagicMock()
            resp.json.return_value = {"error": "invalid_grant"}
            resp.raise_for_status = MagicMock()
            mock_post.return_value = resp
            mgr = AuthManager("tok", "cid", "sec")
            with pytest.raises(SPAPIAuthError):
                _ = mgr.access_token

    def test_refresh_buffer_respected(self, mock_token_response):
        mgr = AuthManager("tok", "cid", "sec", refresh_buffer=120)
        _ = mgr.access_token
        # Token should expire in 3600s, but with 120s buffer, set expiry to now+100
        mgr._token_expires = time.time() + 100  # Within 120s buffer
        _ = mgr.access_token
        assert mock_token_response.call_count == 2
