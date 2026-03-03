"""Tests for Fulfillment Outbound (MCF) API module."""



class TestFulfillmentAPI:
    """Test FulfillmentAPI methods."""

    def test_get_fulfillment_preview(self, client, mock_session):
        mock_session.set_response(200, {
            "payload": {
                "fulfillmentPreviews": [
                    {"shippingSpeedCategory": "Standard", "isFulfillable": True}
                ]
            }
        })
        result = client.get_fulfillment_preview(
            address={
                "name": "John Doe",
                "line1": "123 Main St",
                "city": "Seattle",
                "stateOrRegion": "WA",
                "postalCode": "98101",
                "countryCode": "US",
            },
            items=[
                {"sellerSku": "SKU-001", "quantity": 2, "sellerFulfillmentOrderItemId": "item-1"}
            ],
        )
        assert result["payload"]["fulfillmentPreviews"][0]["isFulfillable"] is True

    def test_get_fulfillment_preview_with_speeds(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"fulfillmentPreviews": []}})
        result = client.get_fulfillment_preview(
            address={"name": "Test", "line1": "456 St", "city": "NYC",
                     "stateOrRegion": "NY", "postalCode": "10001", "countryCode": "US"},
            items=[{"sellerSku": "X", "quantity": 1, "sellerFulfillmentOrderItemId": "i1"}],
            shipping_speed_categories=["Standard", "Expedited"],
        )
        assert "payload" in result

    def test_create_fulfillment_order(self, client, mock_session):
        mock_session.set_response(200, {})
        result = client.create_fulfillment_order(
            seller_fulfillment_order_id="FO-001",
            displayable_order_id="ORD-001",
            displayable_order_date="2026-02-28T00:00:00Z",
            displayable_order_comment="Test order",
            shipping_speed_category="Standard",
            destination_address={
                "name": "Jane", "line1": "789 Ave", "city": "LA",
                "stateOrRegion": "CA", "postalCode": "90001", "countryCode": "US",
            },
            items=[{"sellerSku": "SKU-002", "quantity": 1,
                    "sellerFulfillmentOrderItemId": "item-2"}],
        )
        assert result == {}

    def test_get_fulfillment_order(self, client, mock_session):
        mock_session.set_response(200, {
            "payload": {"sellerFulfillmentOrderId": "FO-001", "fulfillmentOrderStatus": "COMPLETE"}
        })
        result = client.get_fulfillment_order("FO-001")
        assert result["payload"]["fulfillmentOrderStatus"] == "COMPLETE"

    def test_list_all_fulfillment_orders(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"fulfillmentOrders": []}})
        result = client.list_all_fulfillment_orders()
        assert "payload" in result

    def test_cancel_fulfillment_order(self, client, mock_session):
        mock_session.set_response(200, {})
        result = client.cancel_fulfillment_order("FO-001")
        assert result == {}

    def test_get_package_tracking(self, client, mock_session):
        mock_session.set_response(200, {
            "payload": {"packageNumber": "PKG-123", "trackingNumber": "1Z999AA10123456784"}
        })
        result = client.get_package_tracking_details("PKG-123")
        assert result["payload"]["trackingNumber"] == "1Z999AA10123456784"

    def test_list_return_reason_codes(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"reasonCodeDetails": []}})
        result = client.list_return_reason_codes("SKU-001")
        assert "payload" in result

    def test_get_features(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"features": []}})
        result = client.get_features()
        assert "payload" in result

    def test_get_feature_inventory(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"skus": []}})
        result = client.get_feature_inventory("BLANK_BOX")
        assert "payload" in result

    def test_get_feature_sku(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"isEligible": True}})
        result = client.get_feature_sku("BLANK_BOX", "SKU-001")
        assert result["payload"]["isEligible"] is True
