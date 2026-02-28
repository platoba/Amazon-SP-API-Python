"""Shared test fixtures."""

import pytest
from unittest.mock import patch, MagicMock
from sp_api.client import SPAPIClient
from sp_api.auth import AuthManager
from sp_api.rate_limiter import RateLimiter


TOKEN_RESPONSE = {
    "access_token": "test_access_token_123",
    "expires_in": 3600,
    "token_type": "bearer",
}


@pytest.fixture
def mock_token_response():
    """Mock the OAuth token endpoint."""
    with patch("sp_api.auth.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = TOKEN_RESPONSE.copy()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        yield mock_post


@pytest.fixture
def auth_manager(mock_token_response):
    """AuthManager with mocked token endpoint."""
    return AuthManager(
        refresh_token="test_refresh",
        client_id="test_client_id",
        client_secret="test_client_secret",
    )


@pytest.fixture
def rate_limiter():
    """A rate limiter for tests."""
    return RateLimiter(default_rate=1000.0, burst=100)


@pytest.fixture
def mock_session():
    """Mock requests.Session for SPAPIClient."""
    with patch("sp_api.client.requests.Session") as mock_cls:
        session = MagicMock()
        session.headers = {}
        session.headers.update = MagicMock()
        mock_cls.return_value = session
        yield session


@pytest.fixture
def client(mock_token_response, mock_session, rate_limiter):
    """SPAPIClient with all external I/O mocked."""
    c = SPAPIClient(
        refresh_token="test_refresh",
        client_id="test_client_id",
        client_secret="test_client_secret",
        marketplace="US",
        rate_limiter=rate_limiter,
    )
    return c


def make_response(json_data=None, status_code=200, text="", headers=None):
    """Helper to create mock HTTP responses."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text or (str(json_data) if json_data else "")
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp
