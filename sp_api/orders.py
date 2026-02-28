"""
Orders API module — SP-API Orders v0.
"""

import datetime
from sp_api.base import BaseAPI


class OrdersAPI(BaseAPI):
    """Amazon SP-API Orders endpoints."""

    def get_orders(self, created_after=None, order_statuses=None,
                   max_results=100, next_token=None, **kwargs):
        """
        List orders.

        Args:
            created_after: ISO 8601 datetime string. Defaults to 7 days ago.
            order_statuses: List of statuses (e.g., ["Shipped", "Unshipped"]).
            max_results: Max results per page (1-100).
            next_token: Pagination token.
        """
        if not created_after:
            created_after = (
                datetime.datetime.utcnow() - datetime.timedelta(days=7)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")

        params = {
            "MarketplaceIds": self.marketplace_id,
            "CreatedAfter": created_after,
            "MaxResultsPerPage": min(max_results, 100),
        }
        if order_statuses:
            params["OrderStatuses"] = ",".join(order_statuses)
        if next_token:
            params["NextToken"] = next_token
        params.update(kwargs)
        return self.get("/orders/v0/orders", params)

    def get_order(self, order_id):
        """Get a single order by ID."""
        return self.get(f"/orders/v0/orders/{order_id}")

    def get_order_items(self, order_id, next_token=None):
        """Get line items for an order."""
        params = {}
        if next_token:
            params["NextToken"] = next_token
        return self.get(f"/orders/v0/orders/{order_id}/orderItems", params or None)

    def get_order_address(self, order_id):
        """Get shipping address for an order."""
        return self.get(f"/orders/v0/orders/{order_id}/address")

    def get_order_buyer_info(self, order_id):
        """Get buyer information for an order."""
        return self.get(f"/orders/v0/orders/{order_id}/buyerInfo")

    def get_order_regulated_info(self, order_id):
        """Get regulated information for an order."""
        return self.get(f"/orders/v0/orders/{order_id}/regulatedInfo")
