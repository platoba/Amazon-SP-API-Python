"""Tests for sp_api.finances — FinancesAPI."""

import pytest


class TestFinancesAPI:

    def test_list_financial_event_groups(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"FinancialEventGroupList": []}})
        result = client.list_financial_event_groups()
        assert "payload" in result

    def test_list_events_by_group(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"FinancialEvents": {}}})
        result = client.list_financial_events_by_group("grp-001")
        assert "payload" in result

    def test_list_events_by_order(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"FinancialEvents": {}}})
        result = client.list_financial_events_by_order("111-222-333")
        assert "payload" in result

    def test_list_all_financial_events(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"FinancialEvents": {}}})
        result = client.list_financial_events(posted_after="2026-01-01T00:00:00Z")
        assert "payload" in result

    def test_list_events_pagination(self, client, mock_session):
        mock_session.set_response(200, {"payload": {"FinancialEvents": {}, "NextToken": "abc"}})
        result = client.list_financial_events(next_token="abc")
        assert "payload" in result
