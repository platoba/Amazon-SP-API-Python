"""Tests for sp_api.client — SPAPIClient core."""

import pytest
from unittest.mock import patch, MagicMock
from sp_api.client import SPAPIClient
from sp_api.exceptions import SPAPIError, SPAPIThrottleError, SPAPINotFoundError, SPAPIValidationError
from tests.conftest import make_response


class TestSPAPIClient:

    def test_init_valid_marketplace(self, client):
        assert client.marketplace == "US"
        assert client.marketplace_id == "ATVPDKIKX0DER"

    def test_init_invalid_marketplace(self, mock_session):
        with patch("sp_api.auth.requests.post") as mp:
            resp = MagicMock()
            resp.json.return_value = {"access_token": "t", "expires_in": 3600}
            resp.raise_for_status = MagicMock()
            mp.return_value = resp
            with pytest.raises(ValueError, match="Unknown marketplace"):
                SPAPIClient("r", "c", "s", marketplace="INVALID")

    def test_get_request(self, client, mock_session):
        mock_session.set_response(200, {"data": "test"})
        result = client.get("/test/path")
        assert result["data"] == "test"

    def test_post_request(self, client, mock_session):
        mock_session.set_response(200, {"created": True})
        result = client.post("/test/path", body={"key": "val"})
        assert result["created"] is True

    def test_put_request(self, client, mock_session):
        mock_session.set_response(200, {})
        result = client.put("/test/path", body={"update": True})
        assert result == {}

    def test_delete_request(self, client, mock_session):
        mock_session.set_response(200, {})
        result = client.delete("/test/path")
        assert result == {}

    def test_stats(self, client, mock_session):
        mock_session.set_response(200, {"ok": True})
        client.get("/test")
        client.get("/test2")
        assert client.stats["total_requests"] == 2
        assert client.stats["marketplace"] == "US"

    def test_repr(self, client):
        r = repr(client)
        assert "SPAPIClient" in r
        assert "US" in r

    def test_version(self, client):
        assert client.VERSION == "3.0.0"
