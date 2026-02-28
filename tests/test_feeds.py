"""Tests for Feeds API module."""

import pytest
from unittest.mock import patch, MagicMock
from sp_api.exceptions import SPAPIError


class TestFeedsAPI:
    """Test FeedsAPI methods."""

    def test_create_feed_document(self, client, mock_session):
        mock_session.set_response(200, {
            "feedDocumentId": "doc-123",
            "url": "https://s3.amazonaws.com/upload-url",
        })
        result = client.create_feed_document()
        assert result["feedDocumentId"] == "doc-123"

    def test_create_feed_document_json(self, client, mock_session):
        mock_session.set_response(200, {"feedDocumentId": "doc-456", "url": "https://s3.example.com"})
        result = client.create_feed_document(content_type="application/json; charset=UTF-8")
        assert "feedDocumentId" in result

    def test_create_feed(self, client, mock_session):
        mock_session.set_response(200, {"feedId": "feed-001"})
        result = client.create_feed("pricing", "doc-123")
        assert result["feedId"] == "feed-001"

    def test_create_feed_shortcut(self, client, mock_session):
        mock_session.set_response(200, {"feedId": "feed-002"})
        result = client.create_feed("inventory", "doc-456")
        assert "feedId" in result

    def test_get_feed(self, client, mock_session):
        mock_session.set_response(200, {
            "feedId": "feed-001",
            "processingStatus": "DONE",
        })
        result = client.get_feed("feed-001")
        assert result["processingStatus"] == "DONE"

    def test_get_feeds(self, client, mock_session):
        mock_session.set_response(200, {"feeds": []})
        result = client.get_feeds(max_results=5)
        assert "feeds" in result

    def test_cancel_feed(self, client, mock_session):
        mock_session.set_response(200, {})
        result = client.cancel_feed("feed-001")
        assert result == {}

    def test_get_feed_document(self, client, mock_session):
        mock_session.set_response(200, {
            "feedDocumentId": "doc-result",
            "url": "https://s3.amazonaws.com/result",
        })
        result = client.get_feed_document("doc-result")
        assert "url" in result

    def test_feed_types_mapping(self, client):
        """Verify feed type shortcuts resolve correctly."""
        from sp_api.feeds import FeedsAPI
        assert FeedsAPI.FEED_TYPES["pricing"] == "POST_PRODUCT_PRICING_DATA"
        assert FeedsAPI.FEED_TYPES["inventory"] == "POST_INVENTORY_AVAILABILITY_DATA"
        assert FeedsAPI.FEED_TYPES["json_listings"] == "JSON_LISTINGS_FEED"

    def test_get_feeds_with_filters(self, client, mock_session):
        mock_session.set_response(200, {"feeds": [{"feedId": "f-1"}]})
        result = client.get_feeds(
            feed_types=["POST_PRODUCT_PRICING_DATA"],
            processing_statuses=["DONE", "IN_PROGRESS"],
        )
        assert "feeds" in result

    def test_get_feeds_pagination(self, client, mock_session):
        mock_session.set_response(200, {"feeds": [], "nextToken": "abc"})
        result = client.get_feeds(next_token="abc")
        assert "feeds" in result
