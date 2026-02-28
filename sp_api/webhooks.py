"""
SP-API Webhook & SQS Notification Processor.

Handles Amazon SP-API push notifications:
    - SQS queue polling
    - EventBridge event processing
    - Webhook HTTP endpoint (Flask/FastAPI compatible)

Supported notification types:
    - ANY_OFFER_CHANGED
    - ORDER_STATUS_CHANGE
    - REPORT_PROCESSING_FINISHED
    - FBA_OUTBOUND_SHIPMENT_STATUS
    - FULFILLMENT_ORDER_STATUS
    - FEE_PROMOTION
    - ITEM_INVENTORY_EVENT_CHANGE

Usage:
    # SQS Polling
    processor = SQSNotificationProcessor(
        queue_url="https://sqs.us-east-1.amazonaws.com/123456789/sp-api-notifications",
        region="us-east-1",
    )

    @processor.on("ANY_OFFER_CHANGED")
    def handle_offer_change(notification):
        print(f"Offer changed for {notification.asin}")

    processor.start()  # Starts background polling

    # Or manual processing
    handler = NotificationHandler()

    @handler.on("ORDER_STATUS_CHANGE")
    def handle_order(notification):
        print(f"Order {notification.data['orderId']} → {notification.data['orderStatus']}")

    handler.process(raw_notification_dict)
"""

import json
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Notification:
    """Parsed SP-API notification."""
    notification_type: str = ""
    payload_version: str = ""
    event_time: str = ""
    notification_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_raw(cls, raw: Dict) -> "Notification":
        """Parse from raw SQS/EventBridge message body."""
        # SQS wraps in Message body
        body = raw
        if isinstance(body, str):
            body = json.loads(body)

        # SNS wrapping
        if "Message" in body and isinstance(body["Message"], str):
            try:
                body = json.loads(body["Message"])
            except (json.JSONDecodeError, TypeError):
                pass

        notification_type = (
            body.get("notificationType")
            or body.get("NotificationType")
            or body.get("eventType")
            or "UNKNOWN"
        )

        payload = body.get("payload") or body.get("Payload") or body.get("detail", {})

        return cls(
            notification_type=notification_type,
            payload_version=body.get("payloadVersion", ""),
            event_time=body.get("eventTime", ""),
            notification_id=body.get("notificationMetadata", {}).get("notificationId", ""),
            data=payload if isinstance(payload, dict) else {"value": payload},
            raw=body,
        )

    @property
    def asin(self) -> Optional[str]:
        """Extract ASIN from notification payload (if applicable)."""
        for key in ("asin", "ASIN", "offerChangeTrigger"):
            if key in self.data:
                val = self.data[key]
                if isinstance(val, dict):
                    return val.get("ASIN") or val.get("asin")
                return val
        return None

    @property
    def order_id(self) -> Optional[str]:
        for key in ("orderId", "AmazonOrderId", "amazonOrderId"):
            if key in self.data:
                return self.data[key]
        return None


class NotificationHandler:
    """
    Event-driven notification handler with type-based routing.

    Usage:
        handler = NotificationHandler()

        @handler.on("ANY_OFFER_CHANGED")
        def on_offer(notification):
            print(notification.asin)

        @handler.on("*")  # Catch-all
        def on_any(notification):
            logger.info("Got: %s", notification.notification_type)

        handler.process(raw_dict)
    """

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._processed_count = 0
        self._error_count = 0

    def on(self, notification_type: str):
        """Decorator to register a handler for a notification type."""
        def decorator(func: Callable):
            if notification_type not in self._handlers:
                self._handlers[notification_type] = []
            self._handlers[notification_type].append(func)
            return func
        return decorator

    def register(self, notification_type: str, handler: Callable):
        """Register a handler programmatically."""
        if notification_type not in self._handlers:
            self._handlers[notification_type] = []
        self._handlers[notification_type].append(handler)

    def process(self, raw: Dict) -> Notification:
        """Parse and dispatch a notification."""
        notification = Notification.from_raw(raw)
        self._processed_count += 1

        handlers = self._handlers.get(notification.notification_type, [])
        handlers.extend(self._handlers.get("*", []))

        for handler in handlers:
            try:
                handler(notification)
            except Exception as e:
                self._error_count += 1
                logger.error(
                    "Handler error for %s: %s",
                    notification.notification_type, e,
                )

        if not handlers:
            logger.debug(
                "No handler for notification type: %s",
                notification.notification_type,
            )

        return notification

    def process_batch(self, messages: List[Dict]) -> List[Notification]:
        """Process multiple notifications."""
        return [self.process(msg) for msg in messages]

    @property
    def stats(self) -> Dict:
        return {
            "processed": self._processed_count,
            "errors": self._error_count,
            "registered_types": list(self._handlers.keys()),
        }


class SQSNotificationProcessor:
    """
    SQS-based notification processor with background polling.

    Requires boto3 for AWS SQS access.

    Usage:
        processor = SQSNotificationProcessor(
            queue_url="https://sqs...",
            region="us-east-1",
        )

        @processor.on("ANY_OFFER_CHANGED")
        def handle(notification):
            print(notification)

        processor.start()
        # ... later
        processor.stop()
    """

    def __init__(
        self,
        queue_url: str,
        region: str = "us-east-1",
        poll_interval: float = 10.0,
        max_messages: int = 10,
        visibility_timeout: int = 30,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
    ):
        self.queue_url = queue_url
        self.region = region
        self.poll_interval = poll_interval
        self.max_messages = max_messages
        self.visibility_timeout = visibility_timeout
        self._aws_access_key = aws_access_key
        self._aws_secret_key = aws_secret_key

        self.handler = NotificationHandler()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sqs_client = None

    def on(self, notification_type: str):
        """Decorator to register a handler."""
        return self.handler.on(notification_type)

    def _get_sqs_client(self):
        if self._sqs_client:
            return self._sqs_client
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for SQS processing. Install with: pip install boto3"
            )
        kwargs = {"region_name": self.region}
        if self._aws_access_key and self._aws_secret_key:
            kwargs["aws_access_key_id"] = self._aws_access_key
            kwargs["aws_secret_access_key"] = self._aws_secret_key
        self._sqs_client = boto3.client("sqs", **kwargs)
        return self._sqs_client

    def _poll_once(self):
        """Poll SQS for messages and process them."""
        sqs = self._get_sqs_client()
        try:
            response = sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=self.max_messages,
                VisibilityTimeout=self.visibility_timeout,
                WaitTimeSeconds=min(int(self.poll_interval), 20),
            )
        except Exception as e:
            logger.error("SQS poll error: %s", e)
            return

        messages = response.get("Messages", [])
        for msg in messages:
            try:
                body = json.loads(msg["Body"])
                self.handler.process(body)

                # Delete on success
                sqs.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=msg["ReceiptHandle"],
                )
            except Exception as e:
                logger.error("SQS message processing error: %s", e)

    def _poll_loop(self):
        """Background polling loop."""
        while self._running:
            self._poll_once()
            if self._running:
                time.sleep(max(0, self.poll_interval - 20))

    def start(self):
        """Start background polling."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("SQS processor started: %s", self.queue_url)

    def stop(self):
        """Stop background polling."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=30)
            self._thread = None
        logger.info("SQS processor stopped")

    @property
    def stats(self) -> Dict:
        return {
            "running": self._running,
            "queue_url": self.queue_url,
            **self.handler.stats,
        }


def create_webhook_handler(handler: NotificationHandler):
    """
    Create a Flask/FastAPI-compatible webhook endpoint function.

    Usage with Flask:
        app = Flask(__name__)
        handler = NotificationHandler()

        @handler.on("ANY_OFFER_CHANGED")
        def on_offer(n): print(n.asin)

        @app.route("/webhook/sp-api", methods=["POST"])
        def sp_api_webhook():
            return create_webhook_handler(handler)(request.get_json())

    Usage with FastAPI:
        handler = NotificationHandler()
        webhook_fn = create_webhook_handler(handler)

        @app.post("/webhook/sp-api")
        async def sp_api_webhook(body: dict):
            return webhook_fn(body)
    """
    def handle_webhook(body: Dict) -> Dict:
        try:
            notification = handler.process(body)
            return {
                "status": "ok",
                "notification_type": notification.notification_type,
                "notification_id": notification.notification_id,
            }
        except Exception as e:
            logger.error("Webhook processing error: %s", e)
            return {"status": "error", "message": str(e)}

    return handle_webhook
