"""
Finances API module — SP-API Finances v0.
"""

from sp_api.base import BaseAPI


class FinancesAPI(BaseAPI):
    """Amazon SP-API Finances endpoints."""

    def list_financial_event_groups(self, max_results=100, next_token=None,
                                    started_before=None, started_after=None, **kwargs):
        """
        List financial event groups.

        Args:
            max_results: Max results per page.
            next_token: Pagination token.
            started_before: ISO 8601 datetime.
            started_after: ISO 8601 datetime.
        """
        params = {"MaxResultsPerPage": min(max_results, 100)}
        if next_token:
            params["NextToken"] = next_token
        if started_before:
            params["FinancialEventGroupStartedBefore"] = started_before
        if started_after:
            params["FinancialEventGroupStartedAfter"] = started_after
        params.update(kwargs)
        return self.get("/finances/v0/financialEventGroups", params)

    def list_financial_events_by_group(self, group_id, max_results=100,
                                       next_token=None, **kwargs):
        """List financial events for a specific group."""
        params = {"MaxResultsPerPage": min(max_results, 100)}
        if next_token:
            params["NextToken"] = next_token
        params.update(kwargs)
        return self.get(f"/finances/v0/financialEventGroups/{group_id}/financialEvents", params)

    def list_financial_events_by_order(self, order_id, max_results=100,
                                       next_token=None, **kwargs):
        """List financial events for a specific order."""
        params = {"MaxResultsPerPage": min(max_results, 100)}
        if next_token:
            params["NextToken"] = next_token
        params.update(kwargs)
        return self.get(f"/finances/v0/orders/{order_id}/financialEvents", params)

    def list_financial_events(self, posted_after=None, posted_before=None,
                              max_results=100, next_token=None, **kwargs):
        """
        List all financial events.

        Args:
            posted_after: ISO 8601 datetime.
            posted_before: ISO 8601 datetime.
            max_results: Max results per page.
            next_token: Pagination token.
        """
        params = {"MaxResultsPerPage": min(max_results, 100)}
        if posted_after:
            params["PostedAfter"] = posted_after
        if posted_before:
            params["PostedBefore"] = posted_before
        if next_token:
            params["NextToken"] = next_token
        params.update(kwargs)
        return self.get("/finances/v0/financialEvents", params)
