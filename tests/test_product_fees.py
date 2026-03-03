"""Tests for Product Fees API module."""

import pytest
from sp_api.product_fees import ProductFeesAPI


class TestProductFeesAPI:
    """Tests for ProductFeesAPI."""

    def test_get_fees_estimate_for_asin(self, client, mock_session):
        """Test fee estimate for an ASIN."""
        mock_session.set_response(200, {"payload": {
            "FeesEstimateResult": {
                "Status": "Success",
                "FeesEstimate": {
                    "TotalFeesEstimate": {"CurrencyCode": "USD", "Amount": 5.25},
                    "FeeDetailList": [
                        {"FeeType": "ReferralFee", "FeeAmount": {"CurrencyCode": "USD", "Amount": 3.00}},
                        {"FeeType": "FBAFees", "FeeAmount": {"CurrencyCode": "USD", "Amount": 2.25}},
                    ],
                },
            }
        }})
        result = client.get_my_fees_estimate_for_asin("B09XYZ1234", 29.99)
        assert "payload" in result

    def test_get_fees_estimate_for_sku(self, client, mock_session):
        """Test fee estimate for a seller SKU."""
        mock_session.set_response(200, {"payload": {
            "FeesEstimateResult": {
                "Status": "Success",
                "FeesEstimate": {
                    "TotalFeesEstimate": {"CurrencyCode": "USD", "Amount": 4.50},
                    "FeeDetailList": [],
                },
            }
        }})
        result = client.get_my_fees_estimate_for_sku("SKU-001", 19.99)
        assert "payload" in result

    def test_get_fees_with_shipping(self, client, mock_session):
        """Test fee estimate including shipping cost."""
        mock_session.set_response(200, {"payload": {
            "FeesEstimateResult": {
                "Status": "Success",
                "FeesEstimate": {
                    "TotalFeesEstimate": {"CurrencyCode": "USD", "Amount": 6.00},
                    "FeeDetailList": [],
                },
            }
        }})
        result = client.get_my_fees_estimate_for_asin(
            "B09XYZ1234", 29.99, shipping=4.99, is_fba=False
        )
        assert "payload" in result

    def test_extract_total_fees(self):
        """Test fee extraction helper."""
        response = {
            "payload": {
                "FeesEstimateResult": {
                    "FeesEstimate": {
                        "TotalFeesEstimate": {"CurrencyCode": "USD", "Amount": 5.25},
                        "FeeDetailList": [
                            {"FeeType": "ReferralFee", "FeeAmount": {"CurrencyCode": "USD", "Amount": 3.00}},
                            {"FeeType": "FBAFees", "FeeAmount": {"CurrencyCode": "USD", "Amount": 2.25}},
                        ],
                    }
                }
            }
        }
        fees = ProductFeesAPI.extract_total_fees(response)
        assert fees["total_amount"] == 5.25
        assert fees["currency"] == "USD"
        assert "ReferralFee" in fees["breakdown"]
        assert fees["breakdown"]["ReferralFee"]["amount"] == 3.00

    def test_extract_total_fees_empty(self):
        """Test fee extraction with empty response."""
        fees = ProductFeesAPI.extract_total_fees({})
        assert fees["total_amount"] == 0
        assert fees["breakdown"] == {}

    def test_get_my_fees_estimates_batch(self, client, mock_session):
        """Test batch fee estimates."""
        mock_session.set_response(200, {"payload": {
            "FeesEstimateResult": {
                "Status": "Success",
                "FeesEstimate": {
                    "TotalFeesEstimate": {"CurrencyCode": "USD", "Amount": 3.00},
                    "FeeDetailList": [],
                },
            }
        }})
        items = [
            {"asin": "B09XYZ1234", "price": 29.99},
            {"asin": "B08ABC5678", "price": 49.99},
        ]
        results = client.get_my_fees_estimates(items)
        assert len(results) == 2

    def test_get_my_fees_estimates_missing_id(self, client):
        """Test batch fee estimates with missing identifier."""
        with pytest.raises(ValueError, match="asin.*seller_sku"):
            client.get_my_fees_estimates([{"price": 29.99}])
