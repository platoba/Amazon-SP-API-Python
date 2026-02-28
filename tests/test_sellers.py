"""Tests for Sellers API module."""

import pytest
from tests.conftest import make_response


class TestSellersAPI:
    """Tests for SellersAPI."""

    def test_get_marketplace_participations(self, client, mock_session):
        """Test getting marketplace participations."""
        mock_session.set_response(200, {"payload": [
            {
                "marketplace": {
                    "id": "ATVPDKIKX0DER",
                    "name": "Amazon.com",
                    "countryCode": "US",
                    "defaultCurrencyCode": "USD",
                    "defaultLanguageCode": "en_US",
                    "domainName": "www.amazon.com",
                },
                "participation": {
                    "isParticipating": True,
                    "hasSuspendedListings": False,
                },
            },
            {
                "marketplace": {
                    "id": "A2EUQ1WTGCTBG2",
                    "name": "Amazon.ca",
                    "countryCode": "CA",
                    "defaultCurrencyCode": "CAD",
                    "defaultLanguageCode": "en_CA",
                    "domainName": "www.amazon.ca",
                },
                "participation": {
                    "isParticipating": True,
                    "hasSuspendedListings": False,
                },
            },
        ]})
        result = client.get_marketplace_participations()
        assert "payload" in result
        assert len(result["payload"]) == 2

    def test_get_account_info(self, client, mock_session):
        """Test extracting account info from participations."""
        mock_session.set_response(200, {"payload": [
            {
                "marketplace": {
                    "id": "ATVPDKIKX0DER",
                    "name": "Amazon.com",
                    "countryCode": "US",
                    "defaultCurrencyCode": "USD",
                    "defaultLanguageCode": "en_US",
                    "domainName": "www.amazon.com",
                },
                "participation": {
                    "isParticipating": True,
                    "hasSuspendedListings": False,
                },
            },
        ]})
        info = client.get_account_info()
        assert "ATVPDKIKX0DER" in info
        assert info["ATVPDKIKX0DER"]["name"] == "Amazon.com"
        assert info["ATVPDKIKX0DER"]["country_code"] == "US"
        assert info["ATVPDKIKX0DER"]["is_participating"] is True
        assert info["ATVPDKIKX0DER"]["has_suspended_listings"] is False

    def test_get_active_marketplaces(self, client, mock_session):
        """Test filtering active marketplaces."""
        mock_session.set_response(200, {"payload": [
            {
                "marketplace": {
                    "id": "ATVPDKIKX0DER",
                    "name": "Amazon.com",
                    "countryCode": "US",
                    "defaultCurrencyCode": "USD",
                    "defaultLanguageCode": "en_US",
                    "domainName": "www.amazon.com",
                },
                "participation": {
                    "isParticipating": True,
                    "hasSuspendedListings": False,
                },
            },
            {
                "marketplace": {
                    "id": "A2EUQ1WTGCTBG2",
                    "name": "Amazon.ca",
                    "countryCode": "CA",
                    "defaultCurrencyCode": "CAD",
                    "defaultLanguageCode": "en_CA",
                    "domainName": "www.amazon.ca",
                },
                "participation": {
                    "isParticipating": False,
                    "hasSuspendedListings": True,
                },
            },
        ]})
        active = client.get_active_marketplaces()
        assert len(active) == 1
        assert active[0]["marketplace_id"] == "ATVPDKIKX0DER"

    def test_get_account_info_empty(self, client, mock_session):
        """Test account info with empty participations."""
        mock_session.set_response(200, {"payload": []})
        info = client.get_account_info()
        assert info == {}
