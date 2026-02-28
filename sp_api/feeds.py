"""
Feeds API module — SP-API Feeds 2021-06-30.
Submit and manage bulk data feeds (pricing updates, inventory, listings, etc.).
"""

import time
import logging
import gzip
import json

from sp_api.base import BaseAPI
from sp_api.exceptions import SPAPIError

logger = logging.getLogger(__name__)


class FeedsAPI(BaseAPI):
    """Amazon SP-API Feeds endpoints."""

    FEEDS_VERSION = "2021-06-30"

    # Common feed types
    FEED_TYPES = {
        "flat_file_listings": "POST_FLAT_FILE_INVLOADER_DATA",
        "json_listings": "JSON_LISTINGS_FEED",
        "pricing": "POST_PRODUCT_PRICING_DATA",
        "inventory": "POST_INVENTORY_AVAILABILITY_DATA",
        "order_fulfillment": "POST_ORDER_FULFILLMENT_DATA",
        "order_acknowledgement": "POST_ORDER_ACKNOWLEDGEMENT_DATA",
        "flat_file_order_ack": "POST_FLAT_FILE_ORDER_ACKNOWLEDGEMENT_DATA",
        "product_data": "POST_PRODUCT_DATA",
        "product_images": "POST_PRODUCT_IMAGE_DATA",
        "product_overrides": "POST_PRODUCT_OVERRIDES_DATA",
        "relationship": "POST_PRODUCT_RELATIONSHIP_DATA",
    }

    def create_feed_document(self, content_type="text/xml; charset=UTF-8"):
        """
        Create a feed document to get an upload URL.

        Args:
            content_type: MIME type of the feed data.

        Returns:
            Dict with feedDocumentId and url for upload.
        """
        body = {"contentType": content_type}
        return self.post(f"/feeds/{self.FEEDS_VERSION}/documents", body)

    def create_feed(self, feed_type, document_id, marketplace_ids=None, **kwargs):
        """
        Submit a feed for processing.

        Args:
            feed_type: Feed type string or shortcut key from FEED_TYPES.
            document_id: Feed document ID (from create_feed_document).
            marketplace_ids: List of marketplace IDs.
        """
        resolved_type = self.FEED_TYPES.get(feed_type, feed_type)
        body = {
            "feedType": resolved_type,
            "marketplaceIds": marketplace_ids or [self.marketplace_id],
            "inputFeedDocumentId": document_id,
        }
        body.update(kwargs)
        return self.post(f"/feeds/{self.FEEDS_VERSION}/feeds", body)

    def get_feed(self, feed_id):
        """Get feed status/metadata."""
        return self.get(f"/feeds/{self.FEEDS_VERSION}/feeds/{feed_id}")

    def get_feeds(self, feed_types=None, processing_statuses=None,
                  max_results=10, next_token=None, **kwargs):
        """List feeds with optional filters."""
        params = {}
        if feed_types:
            params["feedTypes"] = ",".join(feed_types) if isinstance(feed_types, list) else feed_types
        if processing_statuses:
            params["processingStatuses"] = ",".join(processing_statuses)
        if max_results:
            params["pageSize"] = max_results
        if next_token:
            params["nextToken"] = next_token
        params.update(kwargs)
        return self.get(f"/feeds/{self.FEEDS_VERSION}/feeds", params)

    def cancel_feed(self, feed_id):
        """Cancel a pending feed."""
        return self.delete(f"/feeds/{self.FEEDS_VERSION}/feeds/{feed_id}")

    def get_feed_document(self, document_id):
        """Get feed result document download URL."""
        return self.get(f"/feeds/{self.FEEDS_VERSION}/documents/{document_id}")

    def submit_feed(self, feed_type, content, content_type="text/xml; charset=UTF-8",
                    compress=False, **kwargs):
        """
        High-level: create document, upload content, submit feed.

        Args:
            feed_type: Feed type string or shortcut.
            content: Feed content (str or bytes).
            content_type: MIME type.
            compress: Whether to gzip the content.

        Returns:
            Feed submission response with feedId.
        """
        import requests as req

        # Step 1: Create feed document
        doc = self.create_feed_document(content_type)
        doc_id = doc.get("feedDocumentId")
        upload_url = doc.get("url")

        if not doc_id or not upload_url:
            raise SPAPIError(f"Invalid feed document response: {doc}")

        # Step 2: Upload content
        if isinstance(content, str):
            content = content.encode("utf-8")
        if compress:
            content = gzip.compress(content)
            content_type = "application/gzip"

        resp = req.put(upload_url, data=content, headers={"Content-Type": content_type})
        if resp.status_code not in (200, 201):
            raise SPAPIError(f"Feed upload failed ({resp.status_code}): {resp.text[:500]}")

        # Step 3: Submit feed
        return self.create_feed(feed_type, doc_id, **kwargs)

    def submit_json_feed(self, feed_type, data, **kwargs):
        """
        Submit a JSON feed.

        Args:
            feed_type: Feed type string.
            data: Dict/list to serialize as JSON.
        """
        content = json.dumps(data, ensure_ascii=False)
        return self.submit_feed(
            feed_type, content,
            content_type="application/json; charset=UTF-8",
            **kwargs,
        )

    def submit_and_wait(self, feed_type, content, poll_interval=30,
                        max_wait=1800, **kwargs):
        """
        Submit feed and wait for processing to complete.

        Args:
            feed_type: Feed type.
            content: Feed content.
            poll_interval: Seconds between checks.
            max_wait: Max wait time in seconds.

        Returns:
            Feed result document info.
        """
        result = self.submit_feed(feed_type, content, **kwargs)
        feed_id = result.get("feedId")
        if not feed_id:
            raise SPAPIError(f"No feedId in response: {result}")

        logger.info("Feed %s submitted, polling...", feed_id)
        start = time.time()

        while time.time() - start < max_wait:
            status_resp = self.get_feed(feed_id)
            status = status_resp.get("processingStatus", "")

            if status == "DONE":
                doc_id = status_resp.get("resultFeedDocumentId")
                if doc_id:
                    return self.get_feed_document(doc_id)
                return status_resp

            if status in ("CANCELLED", "FATAL"):
                raise SPAPIError(f"Feed {feed_id} failed: {status}")

            logger.debug("Feed %s: %s", feed_id, status)
            time.sleep(poll_interval)

        raise SPAPIError(f"Feed {feed_id} timed out after {max_wait}s")
