"""Tests for sp_api.finances — FinancesAPI."""

import pytest
from tests.conftest import make_response


class TestFinancesAPI:
    """FinancesAPI test suite."""

    def test_list_financial_event_groups(self, client, mock_session):
        mock_session.request.return_value = make_response(
            {"payload": {"FinancialEventGroupList": []}}
        )
        result = client.list_financial_event_groups()
        assert "payload" in result

    def test_financial_event_groups_with_dates(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {}})
        client.list_financial_event_groups(
            started_after="2024-01-01T00:00:00Z",
            started_before="2024-02-01T00:00:00Z",
        )
        params = mock_session.request.call_args.kwargs.get("params") or mock_session.request.call_args[1].get("params")
        assert "2024-01-01" in str(params)

    def test_list_events_by_group(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {}})
        client.list_financial_events_by_group("GRP-123")
        assert "GRP-123" in str(mock_session.request.call_args)

    def test_list_events_by_order(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {}})
        client.list_financial_events_by_order("111-222-333")
        assert "111-222-333" in str(mock_session.request.call_args)

    def test_list_financial_events(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {}})
        client.list_financial_events(posted_after="2024-01-01T00:00:00Z")
        params = mock_session.request.call_args.kwargs.get("params") or mock_session.request.call_args[1].get("params")
        assert params.get("PostedAfter") == "2024-01-01T00:00:00Z"

    def test_max_results_capped(self, client, mock_session):
        mock_session.request.return_value = make_response({"payload": {}})
        client.list_financial_events(max_results=200)
        params = mock_session.request.call_args.kwargs.get("params") or mock_session.request.call_args[1].get("params")
        assert params["MaxResultsPerPage"] == 100
