"""Tests for Notifications API module."""

import pytest


class TestNotificationsAPI:
    """Test NotificationsAPI methods."""

    def test_get_subscription(self, client, mock_session):
        mock_session.set_response(200, {
            "payload": {"subscriptionId": "sub-001", "payloadVersion": "1.0"}
        })
        result = client.get_subscription("ANY_OFFER_CHANGED")
        assert result["payload"]["subscriptionId"] == "sub-001"

    def test_get_subscription_shortcut(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"subscriptionId": "sub-002"}})
        result = client.get_subscription("order_change")
        assert "payload" in result

    def test_create_subscription(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"subscriptionId": "sub-new"}})
        result = client.create_subscription("any_offer_changed", destination_id="dest-001")
        assert result["payload"]["subscriptionId"] == "sub-new"

    def test_delete_subscription(self, client, mock_session):
        mock_session.set_response(200, {})
        result = client.delete_subscription("ANY_OFFER_CHANGED", "sub-001")
        assert result == {}

    def test_get_destinations(self, client, mock_session):
        mock_session.set_response(200, {
            "payload": [
                {"destinationId": "dest-001", "name": "my-sqs", "resourceSpecification": {}}
            ]
        })
        result = client.get_destinations()
        assert len(result["payload"]) == 1

    def test_create_destination_sqs(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"destinationId": "dest-new"}})
        result = client.create_destination(
            "my-queue",
            {"sqs": {"arn": "arn:aws:sqs:us-east-1:123456789:my-queue"}},
        )
        assert result["payload"]["destinationId"] == "dest-new"

    def test_create_destination_eventbridge(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"destinationId": "dest-eb"}})
        result = client.create_destination(
            "my-eventbridge",
            {"eventBridge": {"accountId": "123456789", "region": "us-east-1"}},
        )
        assert "payload" in result

    def test_get_destination(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"destinationId": "dest-001"}})
        result = client.get_destination("dest-001")
        assert result["payload"]["destinationId"] == "dest-001"

    def test_delete_destination(self, client, mock_session):
        mock_session.set_response(200, {})
        result = client.delete_destination("dest-001")
        assert result == {}

    def test_notification_types_mapping(self, client):
        """Verify notification type shortcuts."""
        from sp_api.notifications import NotificationsAPI
        assert NotificationsAPI.NOTIFICATION_TYPES["order_change"] == "ORDER_CHANGE"
        assert NotificationsAPI.NOTIFICATION_TYPES["any_offer_changed"] == "ANY_OFFER_CHANGED"
        assert "listings_item_status_change" in NotificationsAPI.NOTIFICATION_TYPES
