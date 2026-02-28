"""Tests for Shipping API module."""

import pytest
from tests.conftest import make_response


class TestShippingAPI:
    """Tests for ShippingAPI."""

    def test_get_rates(self, client, mock_session):
        """Test getting shipping rates."""
        mock_session.set_response(200, {"payload": {
            "rates": [
                {
                    "rateId": "rate-001",
                    "carrierId": "AMZN_US",
                    "carrierName": "Amazon Shipping",
                    "serviceType": "Standard",
                    "totalCharge": {"value": 5.99, "unit": "USD"},
                },
            ],
            "requestToken": "token-xyz",
        }})

        ship_from = {
            "name": "Seller",
            "addressLine1": "123 Main St",
            "city": "Seattle",
            "stateOrRegion": "WA",
            "postalCode": "98101",
            "countryCode": "US",
        }
        ship_to = {
            "name": "Buyer",
            "addressLine1": "456 Oak Ave",
            "city": "Portland",
            "stateOrRegion": "OR",
            "postalCode": "97201",
            "countryCode": "US",
        }
        packages = [{
            "dimensions": {"length": 10, "width": 8, "height": 6, "unit": "IN"},
            "weight": {"value": 2.5, "unit": "LB"},
        }]

        result = client.get_rates(ship_from, ship_to, packages)
        assert "payload" in result

    def test_purchase_shipment(self, client, mock_session):
        """Test purchasing a shipment."""
        mock_session.set_response(200, {"payload": {
            "shipmentId": "ship-001",
            "label": {"labelStream": "base64data", "format": "PDF"},
        }})
        result = client.purchase_shipment("token-xyz", "rate-001")
        assert "payload" in result

    def test_get_shipment(self, client, mock_session):
        """Test getting shipment details."""
        mock_session.set_response(200, {"payload": {
            "shipmentId": "ship-001",
            "status": "PURCHASED",
        }})
        result = client.get_shipment("ship-001")
        assert "payload" in result

    def test_cancel_shipment(self, client, mock_session):
        """Test cancelling a shipment."""
        mock_session.set_response(200, {"payload": {"status": "CANCELLED"}})
        result = client.cancel_shipment("ship-001")
        assert "payload" in result

    def test_get_tracking(self, client, mock_session):
        """Test getting tracking info."""
        mock_session.set_response(200, {"payload": {
            "trackingId": "TRK123",
            "summary": {"status": "IN_TRANSIT"},
            "eventHistory": [
                {"eventCode": "PICKED_UP", "eventTime": "2026-02-28T10:00:00Z"},
            ],
        }})
        result = client.get_tracking("TRK123", "AMZN_US")
        assert "payload" in result

    def test_get_access_points(self, client, mock_session):
        """Test getting access points."""
        mock_session.set_response(200, {"payload": {
            "accessPoints": [
                {"accessPointId": "AP-001", "name": "Amazon Locker - Downtown"},
            ],
        }})
        result = client.get_access_points(["HELIX"], "US", "98101")
        assert "payload" in result
