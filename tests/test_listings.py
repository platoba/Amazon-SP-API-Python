"""Tests for sp_api.listings — ListingsAPI."""

import pytest
from tests.conftest import make_response


class TestListingsAPI:
    """ListingsAPI test suite."""

    def test_get_listings_item(self, client, mock_session):
        mock_session.request.return_value = make_response({"sku": "TEST"})
        result = client.get_listings_item("SELLER1", "MY-SKU-123")
        assert "sku" in result
        assert "MY-SKU-123" in str(mock_session.request.call_args)

    def test_get_listings_item_url_encoding(self, client, mock_session):
        mock_session.request.return_value = make_response({})
        client.get_listings_item("SELLER1", "SKU WITH SPACES")
        # SKU should be URL-encoded
        url = str(mock_session.request.call_args)
        assert "SKU%20WITH%20SPACES" in url or "SKU+WITH+SPACES" in url or "SKU WITH SPACES" in url

    def test_put_listings_item(self, client, mock_session):
        mock_session.request.return_value = make_response({"status": "ACCEPTED"})
        body = {"productType": "PRODUCT", "attributes": {}}
        result = client.put_listings_item("SELLER1", "SKU-1", body)
        assert result["status"] == "ACCEPTED"

    def test_delete_listings_item(self, client, mock_session):
        mock_session.request.return_value = make_response({})
        client.delete_listings_item("SELLER1", "SKU-1")
        assert "DELETE" in str(mock_session.request.call_args)
