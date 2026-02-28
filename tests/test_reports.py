"""Tests for sp_api.reports — ReportsAPI."""

import pytest
from unittest.mock import patch
from sp_api.exceptions import SPAPIError
from tests.conftest import make_response


class TestReportsAPI:
    """ReportsAPI test suite."""

    def test_create_report(self, client, mock_session):
        mock_session.request.return_value = make_response({"reportId": "RPT-123"})
        result = client.create_report("GET_MERCHANT_LISTINGS_DATA")
        assert result["reportId"] == "RPT-123"

    def test_create_report_shortcut(self, client, mock_session):
        mock_session.request.return_value = make_response({"reportId": "RPT-123"})
        client.create_report("inventory")
        call_kwargs = mock_session.request.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["reportType"] == "GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA"

    def test_create_report_with_dates(self, client, mock_session):
        mock_session.request.return_value = make_response({"reportId": "RPT-123"})
        client.create_report("inventory", start_date="2024-01-01", end_date="2024-01-31")
        body = mock_session.request.call_args.kwargs.get("json") or mock_session.request.call_args[1].get("json")
        assert body["dataStartTime"] == "2024-01-01"

    def test_get_report(self, client, mock_session):
        mock_session.request.return_value = make_response({"processingStatus": "DONE"})
        result = client.get_report("RPT-123")
        assert result["processingStatus"] == "DONE"

    def test_get_reports_list(self, client, mock_session):
        mock_session.request.return_value = make_response({"reports": []})
        result = client.get_reports(report_types=["GET_MERCHANT_LISTINGS_DATA"])
        assert "reports" in result

    def test_get_report_document(self, client, mock_session):
        mock_session.request.return_value = make_response({"url": "https://..."})
        result = client.get_report_document("DOC-123")
        assert "url" in result

    def test_cancel_report(self, client, mock_session):
        mock_session.request.return_value = make_response({})
        client.cancel_report("RPT-123")
        assert "DELETE" in str(mock_session.request.call_args)

    def test_report_type_constants(self):
        from sp_api.reports import ReportsAPI
        assert "inventory" in ReportsAPI.REPORT_TYPES
        assert "active_listings" in ReportsAPI.REPORT_TYPES
        assert len(ReportsAPI.REPORT_TYPES) >= 5
