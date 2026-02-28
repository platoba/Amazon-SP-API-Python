"""Tests for sp_api.client — SPAPIClient core."""

import pytest
from unittest.mock import MagicMock
from sp_api.client import SPAPIClient
from sp_api.exceptions import (
    SPAPIError,
    SPAPIThrottleError,
    SPAPINotFoundError,
    SPAPIValidationError,
)
from tests.conftest import make_response


class TestSPAPIClientInit:
    """Client initialization tests."""

    def test_valid_marketplace(self, mock_token_response, mock_session, rate_limiter):
        c = SPAPIClient("tok", "cid", "sec", marketplace="US", rate_limiter=rate_limiter)
        assert c.marketplace == "US"
        assert c.marketplace_id == "ATVPDKIKX0DER"
        assert "na.amazon.com" in c.endpoint

    def test_eu_marketplace(self, mock_token_response, mock_session, rate_limiter):
        c = SPAPIClient("tok", "cid", "sec", marketplace="DE", rate_limiter=rate_limiter)
        assert c.marketplace_id == "A1PA6795UKMFR9"
        assert "eu.amazon.com" in c.endpoint

    def test_fe_marketplace(self, mock_token_response, mock_session, rate_limiter):
        c = SPAPIClient("tok", "cid", "sec", marketplace="JP", rate_limiter=rate_limiter)
        assert c.marketplace_id == "A1VC38T7YXB528"
        assert "fe.amazon.com" in c.endpoint

    def test_invalid_marketplace_raises(self, mock_token_response, mock_session, rate_limiter):
        with pytest.raises(ValueError, match="Unknown marketplace"):
            SPAPIClient("tok", "cid", "sec", marketplace="ZZ", rate_limiter=rate_limiter)


class TestSPAPIClientRequest:
    """HTTP request handling tests."""

    def test_get_success(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": "ok"})
        result = client.get("/test")
        assert result == {"payload": "ok"}
        mock_session.request.assert_called_once()

    def test_post_with_body(self, client, mock_session):
        mock_session.request.return_value = make_response({"id": "123"})
        result = client.post("/test", body={"key": "val"})
        assert result == {"id": "123"}
        call_kwargs = mock_session.request.call_args
        assert call_kwargs.kwargs.get("json") == {"key": "val"} or call_kwargs[1].get("json") == {"key": "val"}

    def test_404_raises_not_found(self, client, mock_session):
        mock_session.request.return_value = make_response(
            status_code=404, text="Not found"
        )
        with pytest.raises(SPAPINotFoundError):
            client.get("/missing")

    def test_400_raises_validation(self, client, mock_session):
        mock_session.request.return_value = make_response(
            status_code=400, text="Bad request"
        )
        with pytest.raises(SPAPIValidationError):
            client.get("/bad")

    def test_500_raises_generic_error(self, client, mock_session):
        mock_session.request.return_value = make_response(
            status_code=500, text="Server error"
        )
        with pytest.raises(SPAPIError):
            client.get("/fail")

    def test_429_retries(self, client, mock_session):
        throttle_resp = make_response(status_code=429, headers={"Retry-After": "0"})
        ok_resp = make_response({"data": "ok"})
        mock_session.request.side_effect = [throttle_resp, ok_resp]
        result = client.get("/orders/v0/orders")
        assert result == {"data": "ok"}
        assert mock_session.request.call_count == 2

    def test_429_exhausted_raises_throttle(self, client, mock_session):
        throttle_resp = make_response(status_code=429, headers={"Retry-After": "0"})
        mock_session.request.return_value = throttle_resp
        with pytest.raises(SPAPIThrottleError):
            client.get("/orders/v0/orders")

    def test_empty_response_returns_dict(self, client, mock_session):
        resp = make_response()
        resp.text = "   "
        mock_session.request.return_value = resp
        result = client.get("/test")
        assert result == {}
