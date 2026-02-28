"""Tests for webhooks module."""

import json
import pytest
from sp_api.webhooks import (
    Notification,
    NotificationHandler,
    SQSNotificationProcessor,
    create_webhook_handler,
)


class TestNotification:
    """Tests for Notification parsing."""

    def test_from_raw_basic(self):
        raw = {
            "notificationType": "ANY_OFFER_CHANGED",
            "payloadVersion": "1.0",
            "eventTime": "2026-02-28T12:00:00Z",
            "notificationMetadata": {"notificationId": "notif-001"},
            "payload": {"asin": "B09XYZ1234", "offerCount": 5},
        }
        n = Notification.from_raw(raw)
        assert n.notification_type == "ANY_OFFER_CHANGED"
        assert n.payload_version == "1.0"
        assert n.notification_id == "notif-001"
        assert n.data["asin"] == "B09XYZ1234"

    def test_from_raw_sns_wrapped(self):
        inner = json.dumps({
            "notificationType": "ORDER_STATUS_CHANGE",
            "payload": {"orderId": "114-1234567"},
        })
        raw = {"Message": inner}
        n = Notification.from_raw(raw)
        assert n.notification_type == "ORDER_STATUS_CHANGE"
        assert n.data["orderId"] == "114-1234567"

    def test_from_raw_string(self):
        raw = json.dumps({
            "notificationType": "REPORT_PROCESSING_FINISHED",
            "payload": {"reportId": "report-001"},
        })
        n = Notification.from_raw(raw)
        assert n.notification_type == "REPORT_PROCESSING_FINISHED"

    def test_from_raw_event_bridge(self):
        raw = {
            "eventType": "FBA_OUTBOUND_SHIPMENT_STATUS",
            "detail": {"shipmentId": "ship-001"},
        }
        n = Notification.from_raw(raw)
        assert n.notification_type == "FBA_OUTBOUND_SHIPMENT_STATUS"

    def test_asin_extraction(self):
        n = Notification(data={"asin": "B09XYZ1234"})
        assert n.asin == "B09XYZ1234"

    def test_asin_from_offer_trigger(self):
        n = Notification(data={"offerChangeTrigger": {"ASIN": "B08ABC5678"}})
        assert n.asin == "B08ABC5678"

    def test_asin_none(self):
        n = Notification(data={"other": "data"})
        assert n.asin is None

    def test_order_id(self):
        n = Notification(data={"orderId": "114-1234567"})
        assert n.order_id == "114-1234567"

    def test_order_id_alternative_key(self):
        n = Notification(data={"AmazonOrderId": "114-9999999"})
        assert n.order_id == "114-9999999"

    def test_order_id_none(self):
        n = Notification(data={"other": "data"})
        assert n.order_id is None

    def test_unknown_type(self):
        n = Notification.from_raw({"payload": {"test": True}})
        assert n.notification_type == "UNKNOWN"


class TestNotificationHandler:
    """Tests for NotificationHandler."""

    def test_register_and_process(self):
        handler = NotificationHandler()
        results = []

        @handler.on("ANY_OFFER_CHANGED")
        def on_offer(n):
            results.append(n.notification_type)

        handler.process({
            "notificationType": "ANY_OFFER_CHANGED",
            "payload": {"asin": "TEST"},
        })
        assert results == ["ANY_OFFER_CHANGED"]

    def test_wildcard_handler(self):
        handler = NotificationHandler()
        results = []

        @handler.on("*")
        def on_any(n):
            results.append(n.notification_type)

        handler.process({"notificationType": "TYPE_A", "payload": {}})
        handler.process({"notificationType": "TYPE_B", "payload": {}})
        assert len(results) == 2

    def test_multiple_handlers(self):
        handler = NotificationHandler()
        calls = []

        @handler.on("TEST")
        def h1(n):
            calls.append("h1")

        @handler.on("TEST")
        def h2(n):
            calls.append("h2")

        handler.process({"notificationType": "TEST", "payload": {}})
        assert calls == ["h1", "h2"]

    def test_handler_error_doesnt_crash(self):
        handler = NotificationHandler()

        @handler.on("CRASH")
        def bad_handler(n):
            raise ValueError("boom")

        # Should not raise
        handler.process({"notificationType": "CRASH", "payload": {}})
        assert handler.stats["errors"] == 1

    def test_process_batch(self):
        handler = NotificationHandler()
        results = []

        @handler.on("*")
        def on_any(n):
            results.append(n.notification_type)

        messages = [
            {"notificationType": "TYPE_A", "payload": {}},
            {"notificationType": "TYPE_B", "payload": {}},
        ]
        notifications = handler.process_batch(messages)
        assert len(notifications) == 2
        assert len(results) == 2

    def test_register_programmatic(self):
        handler = NotificationHandler()
        results = []

        def on_test(n):
            results.append(n)

        handler.register("TEST_TYPE", on_test)
        handler.process({"notificationType": "TEST_TYPE", "payload": {"key": "val"}})
        assert len(results) == 1

    def test_stats(self):
        handler = NotificationHandler()

        @handler.on("A")
        def on_a(n):
            pass

        handler.process({"notificationType": "A", "payload": {}})
        handler.process({"notificationType": "A", "payload": {}})

        stats = handler.stats
        assert stats["processed"] == 2
        assert stats["errors"] == 0
        assert "A" in stats["registered_types"]

    def test_no_handler_debug_log(self):
        handler = NotificationHandler()
        # No handler registered — should not raise
        handler.process({"notificationType": "UNHANDLED", "payload": {}})
        assert handler.stats["processed"] == 1


class TestSQSNotificationProcessor:
    """Tests for SQSNotificationProcessor."""

    def test_init(self):
        proc = SQSNotificationProcessor(
            queue_url="https://sqs.us-east-1.amazonaws.com/123/test",
            region="us-east-1",
        )
        assert proc.queue_url == "https://sqs.us-east-1.amazonaws.com/123/test"
        assert proc._running is False

    def test_on_decorator(self):
        proc = SQSNotificationProcessor(queue_url="https://test")
        results = []

        @proc.on("ANY_OFFER_CHANGED")
        def handle(n):
            results.append(n)

        assert "ANY_OFFER_CHANGED" in proc.handler._handlers

    def test_stats(self):
        proc = SQSNotificationProcessor(queue_url="https://test")
        stats = proc.stats
        assert stats["running"] is False
        assert stats["queue_url"] == "https://test"


class TestWebhookHandler:
    """Tests for create_webhook_handler."""

    def test_success(self):
        handler = NotificationHandler()
        results = []

        @handler.on("TEST")
        def on_test(n):
            results.append(n)

        webhook = create_webhook_handler(handler)
        response = webhook({"notificationType": "TEST", "payload": {"key": "val"}})
        assert response["status"] == "ok"
        assert response["notification_type"] == "TEST"
        assert len(results) == 1

    def test_error_handling(self):
        handler = NotificationHandler()
        # Force an error by passing non-dict
        webhook = create_webhook_handler(handler)
        # Passing None should be handled
        response = webhook(None)
        # Should return error or handle gracefully
        assert "status" in response
