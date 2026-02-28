"""
FBA Inventory API module — SP-API FBA Inventory v1.
"""

from sp_api.base import BaseAPI


class InventoryAPI(BaseAPI):
    """Amazon SP-API FBA Inventory endpoints."""

    def get_inventory_summaries(self, granularity_type="Marketplace",
                                next_token=None, start_date=None,
                                seller_skus=None, **kwargs):
        """
        Get FBA inventory summaries.

        Args:
            granularity_type: Marketplace or SingleSku.
            next_token: Pagination token.
            start_date: ISO 8601 date for inventory snapshot.
            seller_skus: List of seller SKUs to filter.
        """
        params = {
            "granularityType": granularity_type,
            "granularityId": self.marketplace_id,
            "marketplaceIds": self.marketplace_id,
        }
        if next_token:
            params["nextToken"] = next_token
        if start_date:
            params["startDateTime"] = start_date
        if seller_skus:
            params["sellerSkus"] = ",".join(seller_skus) if isinstance(seller_skus, list) else seller_skus
        params.update(kwargs)
        return self.get("/fba/inventory/v1/summaries", params)

    def get_inventory_summary_by_sku(self, seller_sku):
        """Get inventory summary for a specific SKU."""
        return self.get_inventory_summaries(
            granularity_type="SingleSku",
            seller_skus=[seller_sku],
        )

    def get_all_inventory(self, page_size=50):
        """
        Generator: iterate through all inventory pages.

        Yields:
            Each inventory summary dict from each page.
        """
        next_token = None
        while True:
            result = self.get_inventory_summaries(next_token=next_token)
            payload = result.get("payload", result)
            summaries = payload.get("inventorySummaries", [])
            yield from summaries

            pagination = payload.get("pagination", {})
            next_token = pagination.get("nextToken")
            if not next_token:
                break
