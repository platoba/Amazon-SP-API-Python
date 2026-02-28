"""Tests for sp_api.listings — ListingsAPI."""

import pytest


class TestListingsAPI:

    def test_get_listings_item(self, client, mock_session):
        mock_session.set_response(200, {"sku": "TEST-SKU", "summaries": [{"title": "Test Product"}]})
        result = client.get_listings_item("SELLER123", "TEST-SKU")
        assert result["sku"] == "TEST-SKU"

    def test_put_listings_item(self, client, mock_session):
        mock_session.set_response(200, {"status": "ACCEPTED"})
        result = client.put_listings_item("SELLER123", "TEST-SKU", {"productType": "PRODUCT"})
        assert result["status"] == "ACCEPTED"

    def test_patch_listings_item(self, client, mock_session):
        mock_session.set_response(200, {"status": "ACCEPTED"})
        patches = [{"op": "replace", "path": "/attributes/item_name", "value": [{"value": "New Name"}]}]
        result = client.patch_listings_item("SELLER123", "TEST-SKU", patches)
        assert result["status"] == "ACCEPTED"

    def test_delete_listings_item(self, client, mock_session):
        mock_session.set_response(200, {"status": "ACCEPTED"})
        result = client.delete_listings_item("SELLER123", "TEST-SKU")
        assert result["status"] == "ACCEPTED"

    def test_get_listings_special_chars(self, client, mock_session):
        mock_session.set_response(200, {"sku": "TEST/SKU+1"})
        result = client.get_listings_item("SELLER123", "TEST/SKU+1")
        assert "sku" in result
