"""
Listings API module — SP-API Listings Items 2021-08-01.
"""

from urllib.parse import quote
from sp_api.base import BaseAPI


class ListingsAPI(BaseAPI):
    """Amazon SP-API Listings Items endpoints."""

    LISTINGS_VERSION = "2021-08-01"

    def get_listings_item(self, seller_id, sku, included_data=None, **kwargs):
        """
        Get a listings item.

        Args:
            seller_id: Seller identifier.
            sku: SKU (URL-encoded automatically).
            included_data: Comma-separated data types.
        """
        params = {
            "marketplaceIds": self.marketplace_id,
            "includedData": included_data or "summaries,attributes,issues",
        }
        params.update(kwargs)
        return self.get(
            f"/listings/{self.LISTINGS_VERSION}/items/{seller_id}/{quote(sku, safe='')}",
            params,
        )

    def put_listings_item(self, seller_id, sku, body, **kwargs):
        """
        Create or fully update a listings item.

        Args:
            seller_id: Seller identifier.
            sku: SKU.
            body: Listing data dict.
        """
        return self.put(
            f"/listings/{self.LISTINGS_VERSION}/items/{seller_id}/{quote(sku, safe='')}",
            body,
        )

    def patch_listings_item(self, seller_id, sku, patches, **kwargs):
        """
        Partially update a listings item.

        Args:
            seller_id: Seller identifier.
            sku: SKU.
            patches: List of JSON Patch operations.
        """
        body = {
            "productType": kwargs.get("product_type", "PRODUCT"),
            "patches": patches,
        }
        return self.put(
            f"/listings/{self.LISTINGS_VERSION}/items/{seller_id}/{quote(sku, safe='')}",
            body,
        )

    def delete_listings_item(self, seller_id, sku, **kwargs):
        """Delete a listings item."""
        params = {"marketplaceIds": self.marketplace_id}
        params.update(kwargs)
        return self.delete(
            f"/listings/{self.LISTINGS_VERSION}/items/{seller_id}/{quote(sku, safe='')}",
            params,
        )
