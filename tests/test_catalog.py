"""Tests for sp_api.catalog — CatalogAPI."""

import pytest
from tests.conftest import make_response


class TestCatalogAPI:
    """CatalogAPI test suite."""

    def test_search_catalog_basic(self, client, mock_session):
        mock_session.request.return_value = make_response({"items": []})
        result = client.search_catalog("wireless earbuds")
        assert "items" in result
        params = mock_session.request.call_args.kwargs.get("params") or mock_session.request.call_args[1].get("params")
        assert params["keywords"] == "wireless earbuds"

    def test_search_catalog_page_size(self, client, mock_session):
        mock_session.request.return_value = make_response({"items": []})
        client.search_catalog("test", page_size=5)
        params = mock_session.request.call_args.kwargs.get("params") or mock_session.request.call_args[1].get("params")
        assert params["pageSize"] == 5

    def test_search_catalog_max_page_size(self, client, mock_session):
        mock_session.request.return_value = make_response({"items": []})
        client.search_catalog("test", page_size=100)
        params = mock_session.request.call_args.kwargs.get("params") or mock_session.request.call_args[1].get("params")
        assert params["pageSize"] == 20  # Capped at 20

    def test_get_catalog_item(self, client, mock_session):
        mock_session.request.return_value = make_response({"asin": "B123"})
        result = client.get_catalog_item("B123456789")
        assert "asin" in result
        assert "B123456789" in str(mock_session.request.call_args)

    def test_get_catalog_item_custom_data(self, client, mock_session):
        mock_session.request.return_value = make_response({})
        client.get_catalog_item("B123", included_data="summaries")
        params = mock_session.request.call_args.kwargs.get("params") or mock_session.request.call_args[1].get("params")
        assert params["includedData"] == "summaries"

    def test_search_by_identifier(self, client, mock_session):
        mock_session.request.return_value = make_response({"items": []})
        client.search_catalog_by_identifier(["B123", "B456"], identifiers_type="ASIN")
        params = mock_session.request.call_args.kwargs.get("params") or mock_session.request.call_args[1].get("params")
        assert "B123,B456" in str(params.get("identifiers", ""))
