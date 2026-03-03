"""Tests for Product Pricing API module."""



class TestPricingAPI:
    """Test PricingAPI methods."""

    def test_get_competitive_pricing_asins(self, client, mock_session):
        mock_session.set_response(200, {"payload": [{"ASIN": "B09TEST"}]})
        result = client.get_competitive_pricing(asins=["B09TEST", "B08TEST2"])
        assert "payload" in result

    def test_get_competitive_pricing_single_asin(self, client, mock_session):
        mock_session.set_response(200, {"payload": [{"ASIN": "B09SINGLE"}]})
        result = client.get_competitive_pricing(asins="B09SINGLE")
        assert "payload" in result

    def test_get_competitive_pricing_skus(self, client, mock_session):
        mock_session.set_response(200, {"payload": [{"SKU": "TEST-SKU"}]})
        result = client.get_competitive_pricing(skus=["TEST-SKU-1", "TEST-SKU-2"])
        assert "payload" in result

    def test_get_item_offers(self, client, mock_session):
        mock_session.set_response(200, {
            "payload": {
                "ASIN": "B09OFFER",
                "Offers": [{"price": {"amount": 29.99}}],
            }
        })
        result = client.get_item_offers("B09OFFER")
        assert result["payload"]["ASIN"] == "B09OFFER"

    def test_get_item_offers_used(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"Offers": []}})
        result = client.get_item_offers("B09USED", item_condition="Used")
        assert "payload" in result

    def test_get_listing_offers(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"Offers": []}})
        result = client.get_listing_offers("MY-SKU-001")
        assert "payload" in result

    def test_get_pricing(self, client, mock_session):
        mock_session.set_response(200, {"payload": [{"ASIN": "B09PRICE"}]})
        result = client.get_pricing(asins=["B09PRICE"])
        assert "payload" in result

    def test_get_pricing_with_condition(self, client, mock_session):
        mock_session.set_response(200, {"payload": []})
        result = client.get_pricing(asins=["B09X"], item_condition="New", offer_type="B2C")
        assert "payload" in result

    def test_get_featured_offer_expected_price_batch(self, client, mock_session):
        mock_session.set_response(200, {"responses": [{"status": {"statusCode": 200}}]})
        requests_list = [
            {"marketplaceId": "ATVPDKIKX0DER", "asin": "B09TEST", "condition": "New"}
        ]
        result = client.get_featured_offer_expected_price_batch(requests_list)
        assert "responses" in result

    def test_get_competitive_summary_batch(self, client, mock_session):
        mock_session.set_response(200, {"responses": []})
        requests_list = [{"asin": "B09TEST", "marketplaceId": "ATVPDKIKX0DER"}]
        result = client.get_competitive_summary_batch(requests_list)
        assert "responses" in result
