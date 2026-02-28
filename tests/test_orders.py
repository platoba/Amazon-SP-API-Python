"""Tests for sp_api.orders — OrdersAPI."""

import pytest
from tests.conftest import make_response


class TestOrdersAPI:
    """OrdersAPI test suite."""

    def test_get_orders_default(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"Orders": []}})
        result = client.get_orders()
        assert "payload" in result

    def test_get_orders_with_statuses(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"Orders": []}})
        result = client.get_orders(order_statuses=["Shipped", "Unshipped"])
        assert "payload" in result

    def test_get_orders_custom_date(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"Orders": []}})
        result = client.get_orders(created_after="2024-01-01T00:00:00Z")
        assert "payload" in result

    def test_get_order_by_id(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"AmazonOrderId": "111-222-333"}})
        result = client.get_order("111-222-333")
        assert result["payload"]["AmazonOrderId"] == "111-222-333"

    def test_get_order_items(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"OrderItems": [{"ASIN": "B09TEST"}]}})
        result = client.get_order_items("111-222-333")
        assert len(result["payload"]["OrderItems"]) == 1

    def test_get_order_address(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"ShippingAddress": {}}})
        result = client.get_order_address("111-222-333")
        assert "payload" in result

    def test_get_order_buyer_info(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"BuyerEmail": "test@example.com"}})
        result = client.get_order_buyer_info("111-222-333")
        assert "payload" in result

    def test_get_order_regulated_info(self, client, mock_session):
        mock_session.set_response(200, {"payload": {}})
        result = client.get_order_regulated_info("111-222-333")
        assert result == {"payload": {}}
