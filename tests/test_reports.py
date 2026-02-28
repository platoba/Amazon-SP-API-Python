"""Tests for sp_api.reports — ReportsAPI."""

import pytest


class TestReportsAPI:

    def test_create_report(self, client, mock_session):
        mock_session.set_response(200, {"reportId": "rep-001"})
        result = client.create_report("inventory")
        assert result["reportId"] == "rep-001"

    def test_create_report_shortcut(self, client, mock_session):
        mock_session.set_response(200, {"reportId": "rep-002"})
        result = client.create_report("active_listings")
        assert "reportId" in result

    def test_get_report(self, client, mock_session):
        mock_session.set_response(200, {"reportId": "rep-001", "processingStatus": "IN_PROGRESS"})
        result = client.get_report("rep-001")
        assert result["processingStatus"] == "IN_PROGRESS"

    def test_get_reports(self, client, mock_session):
        mock_session.set_response(200, {"reports": []})
        result = client.get_reports(max_results=5)
        assert "reports" in result

    def test_get_report_document(self, client, mock_session):
        mock_session.set_response(200, {"reportDocumentId": "doc-1", "url": "https://s3.example.com"})
        result = client.get_report_document("doc-1")
        assert "url" in result

    def test_cancel_report(self, client, mock_session):
        mock_session.set_response(200, {})
        result = client.cancel_report("rep-001")
        assert result == {}

    def test_report_types_mapping(self, client):
        from sp_api.reports import ReportsAPI
        assert ReportsAPI.REPORT_TYPES["inventory"] == "GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA"
        assert ReportsAPI.REPORT_TYPES["active_listings"] == "GET_MERCHANT_LISTINGS_DATA"
        assert "brand_analytics" in ReportsAPI.REPORT_TYPES

    def test_get_reports_with_filters(self, client, mock_session):
        mock_session.set_response(200, {"reports": []})
        result = client.get_reports(
            report_types=["GET_MERCHANT_LISTINGS_DATA"],
            processing_statuses=["DONE"],
        )
        assert "reports" in result
