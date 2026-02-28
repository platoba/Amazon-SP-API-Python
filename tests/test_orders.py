"""Tests for sp_api.orders — OrdersAPI."""

import pytest
from unittest.mock import MagicMock, call
from tests.conftest import make_response


class TestOrdersAPI:
    """OrdersAPI test suite."""

    def test_get_orders_default(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {"Orders": []}})
        result = client.get_orders()
        assert "payload" in result
        args = mock_session.request.call_args
        assert "/orders/v0/orders" in args[0][1] or "/orders/v0/orders" in str(args)

    def test_get_orders_with_statuses(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {"Orders": []}})
        client.get_orders(order_statuses=["Shipped", "Unshipped"])
        call_kwargs = mock_session.request.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert "Shipped,Unshipped" in str(params)

    def test_get_orders_custom_date(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {"Orders": []}})
        client.get_orders(created_after="2024-01-01T00:00:00Z")
        call_kwargs = mock_session.request.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert "2024-01-01" in str(params)

    def test_get_order_by_id(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {"AmazonOrderId": "111"}})
        result = client.get_order("111-222-333")
        assert mock_session.request.call_count == 1

    def test_get_order_items(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {"OrderItems": []}})
        result = client.get_order_items("111-222-333")
        args_str = str(mock_session.request.call_args)
        assert "orderItems" in args_str

    def test_get_order_address(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {}})
        client.get_order_address("111-222-333")
        assert "address" in str(mock_session.request.call_args)

    def test_get_order_buyer_info(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {}})
        client.get_order_buyer_info("111-222-333")
        assert "buyerInfo" in str(mock_session.request.call_args)
