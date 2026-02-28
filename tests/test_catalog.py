"""Tests for sp_api.catalog — CatalogAPI."""

import pytest


class TestCatalogAPI:

    def test_search_catalog(self, client, mock_session):
        mock_session.set_response(200, {"items": [{"asin": "B09TEST"}]})
        result = client.search_catalog("wireless earbuds")
        assert "items" in result

    def test_search_catalog_page_size(self, client, mock_session):
        mock_session.set_response(200, {"items": []})
        result = client.search_catalog("test", page_size=5)
        assert "items" in result

    def test_get_catalog_item(self, client, mock_session):
        mock_session.set_response(200, {"asin": "B09DETAIL", "summaries": [{"title": "Test"}]})
        result = client.get_catalog_item("B09DETAIL")
        assert result["asin"] == "B09DETAIL"

    def test_search_by_identifier(self, client, mock_session):
        mock_session.set_response(200, {"items": [{"asin": "B09ID"}]})
        result = client.search_catalog_by_identifier(["B09ID"], identifiers_type="ASIN")
        assert "items" in result

    def test_search_by_upc(self, client, mock_session):
        mock_session.set_response(200, {"items": []})
        result = client.search_catalog_by_identifier(["012345678901"], identifiers_type="UPC")
        assert "items" in result
