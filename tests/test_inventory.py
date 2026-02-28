"""Tests for sp_api.inventory — InventoryAPI."""

import pytest


class TestInventoryAPI:

    def test_get_inventory_summaries(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"inventorySummaries": []}})
        result = client.get_inventory_summaries()
        assert "payload" in result

    def test_get_inventory_by_sku(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"inventorySummaries": [{"sku": "TEST"}]}})
        result = client.get_inventory_summary_by_sku("TEST")
        assert "payload" in result

    def test_get_inventory_with_date(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"inventorySummaries": []}})
        result = client.get_inventory_summaries(start_date="2026-01-01T00:00:00Z")
        assert "payload" in result

    def test_get_inventory_with_skus(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"inventorySummaries": []}})
        result = client.get_inventory_summaries(seller_skus=["SKU1", "SKU2"])
        assert "payload" in result
