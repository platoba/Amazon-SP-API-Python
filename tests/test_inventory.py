"""Tests for sp_api.inventory — InventoryAPI."""

import pytest
from tests.conftest import make_response


class TestInventoryAPI:
    """InventoryAPI test suite."""

    def test_get_inventory_summaries(self, client, mock_session):
        mock_session.request.return_value = make_response(
            {"payload": {"inventorySummaries": []}}
        )
        result = client.get_inventory_summaries()
        assert "payload" in result

    def test_inventory_marketplace_params(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {"inventorySummaries": []}})
        client.get_inventory_summaries()
        params = mock_session.request.call_args.kwargs.get("params") or mock_session.request.call_args[1].get("params")
        assert params["granularityType"] == "Marketplace"
        assert params["marketplaceIds"] == "ATVPDKIKX0DER"

    def test_inventory_with_skus(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {"inventorySummaries": []}})
        client.get_inventory_summaries(seller_skus=["SKU1", "SKU2"])
        params = mock_session.request.call_args.kwargs.get("params") or mock_session.request.call_args[1].get("params")
        assert "SKU1,SKU2" in str(params)

    def test_get_inventory_by_sku(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {"inventorySummaries": []}})
        client.get_inventory_summary_by_sku("TEST-SKU")
        params = mock_session.request.call_args.kwargs.get("params") or mock_session.request.call_args[1].get("params")
        assert params["granularityType"] == "SingleSku"
