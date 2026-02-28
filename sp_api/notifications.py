"""
Notifications API module — SP-API Notifications v1.
Subscribe to and manage event notifications (order changes, listings, pricing, etc.).
"""

from sp_api.base import BaseAPI


class NotificationsAPI(BaseAPI):
    """Amazon SP-API Notifications endpoints."""

    # Common notification types
    NOTIFICATION_TYPES = {
        "any_offer_changed": "ANY_OFFER_CHANGED",
        "feed_processing_finished": "FEED_PROCESSING_FINISHED",
        "fba_outbound_shipment": "FBA_OUTBOUND_SHIPMENT_STATUS",
        "fee_promotion": "FEE_PROMOTION",
        "fulfillment_order": "FULFILLMENT_ORDER_STATUS",
        "report_processing_finished": "REPORT_PROCESSING_FINISHED",
        "branded_item_content_change": "BRANDED_ITEM_CONTENT_CHANGE",
        "item_product_type_change": "ITEM_PRODUCT_TYPE_CHANGE",
        "listings_item_status_change": "LISTINGS_ITEM_STATUS_CHANGE",
        "listings_item_issues_change": "LISTINGS_ITEM_ISSUES_CHANGE",
        "order_status_change": "ORDER_STATUS_CHANGE",
        "order_change": "ORDER_CHANGE",
        "b2b_any_offer_changed": "B2B_ANY_OFFER_CHANGED",
        "item_inventory_event_change": "ITEM_INVENTORY_EVENT_CHANGE",
    }

    def get_subscription(self, notification_type):
        """
        Get the current subscription for a notification type.

        Args:
            notification_type: Notification type string or shortcut key.
        """
        resolved = self.NOTIFICATION_TYPES.get(notification_type, notification_type)
        return self.get(f"/notifications/v1/subscriptions/{resolved}")

    def create_subscription(self, notification_type, destination_id=None,
                            payload_version="1.0", **kwargs):
        """
        Create a subscription for a notification type.

        Args:
            notification_type: Notification type string or shortcut key.
            destination_id: Destination ID to receive notifications.
            payload_version: Payload version (default "1.0").
        """
        resolved = self.NOTIFICATION_TYPES.get(notification_type, notification_type)
        body = {"payloadVersion": payload_version}
        if destination_id:
            body["destinationId"] = destination_id
        body.update(kwargs)
        return self.post(f"/notifications/v1/subscriptions/{resolved}", body)

    def delete_subscription(self, notification_type, subscription_id):
        """
        Delete a subscription.

        Args:
            notification_type: Notification type string or shortcut key.
            subscription_id: Subscription ID to delete.
        """
        resolved = self.NOTIFICATION_TYPES.get(notification_type, notification_type)
        return self.delete(
            f"/notifications/v1/subscriptions/{resolved}/{subscription_id}"
        )

    def get_destinations(self):
        """List all notification destinations."""
        return self.get("/notifications/v1/destinations")

    def create_destination(self, name, resource_spec):
        """
        Create a notification destination.

        Args:
            name: Destination name.
            resource_spec: Dict with destination details. Example for SQS:
                {"sqs": {"arn": "arn:aws:sqs:us-east-1:123456789:my-queue"}}
                For EventBridge:
                {"eventBridge": {"accountId": "123456789", "region": "us-east-1"}}
        """
        body = {"name": name, "resourceSpecification": resource_spec}
        return self.post("/notifications/v1/destinations", body)

    def get_destination(self, destination_id):
        """Get a specific destination by ID."""
        return self.get(f"/notifications/v1/destinations/{destination_id}")

    def delete_destination(self, destination_id):
        """Delete a notification destination."""
        return self.delete(f"/notifications/v1/destinations/{destination_id}")
