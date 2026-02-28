"""
Product Pricing API module — SP-API Product Pricing v0 + 2022-05-01.
"""

from sp_api.base import BaseAPI


class PricingAPI(BaseAPI):
    """Amazon SP-API Product Pricing endpoints."""

    # ── v0 endpoints ──────────────────────────────────────

    def get_competitive_pricing(self, asins=None, skus=None, item_type="Asin", **kwargs):
        """
        Get competitive pricing for items.

        Args:
            asins: List of ASINs (up to 20).
            skus: List of seller SKUs (up to 20).
            item_type: "Asin" or "Sku".
        """
        params = {"MarketplaceId": self.marketplace_id, "ItemType": item_type}
        if asins:
            if isinstance(asins, str):
                asins = [asins]
            for i, asin in enumerate(asins[:20]):
                params[f"Asins.Asin.{i + 1}"] = asin
        if skus:
            if isinstance(skus, str):
                skus = [skus]
            for i, sku in enumerate(skus[:20]):
                params[f"Skus.Sku.{i + 1}"] = sku
        params.update(kwargs)
        return self.get("/products/pricing/v0/competitivePrice", params)

    def get_item_offers(self, asin, item_condition="New", customer_type="Consumer", **kwargs):
        """
        Get lowest offers for an item.

        Args:
            asin: Amazon Standard Identification Number.
            item_condition: New, Used, Collectible, Refurbished, Club.
            customer_type: Consumer or Business.
        """
        params = {
            "MarketplaceId": self.marketplace_id,
            "ItemCondition": item_condition,
            "CustomerType": customer_type,
        }
        params.update(kwargs)
        return self.get(f"/products/pricing/v0/items/{asin}/offers", params)

    def get_listing_offers(self, seller_sku, item_condition="New",
                           customer_type="Consumer", **kwargs):
        """
        Get listing-level offers for a seller SKU.

        Args:
            seller_sku: Seller's SKU.
            item_condition: Condition filter.
            customer_type: Consumer or Business.
        """
        params = {
            "MarketplaceId": self.marketplace_id,
            "ItemCondition": item_condition,
            "CustomerType": customer_type,
        }
        params.update(kwargs)
        return self.get(f"/products/pricing/v0/listings/{seller_sku}/offers", params)

    def get_pricing(self, asins=None, skus=None, item_type="Asin",
                    item_condition=None, offer_type=None, **kwargs):
        """
        Get pricing information for items.

        Args:
            asins: List of ASINs.
            skus: List of seller SKUs.
            item_type: "Asin" or "Sku".
            item_condition: New, Used, etc.
            offer_type: B2C or B2B.
        """
        params = {"MarketplaceId": self.marketplace_id, "ItemType": item_type}
        if asins:
            if isinstance(asins, str):
                asins = [asins]
            for i, asin in enumerate(asins[:20]):
                params[f"Asins.Asin.{i + 1}"] = asin
        if skus:
            if isinstance(skus, str):
                skus = [skus]
            for i, sku in enumerate(skus[:20]):
                params[f"Skus.Sku.{i + 1}"] = sku
        if item_condition:
            params["ItemCondition"] = item_condition
        if offer_type:
            params["OfferType"] = offer_type
        params.update(kwargs)
        return self.get("/products/pricing/v0/price", params)

    # ── 2022-05-01 batch endpoints ────────────────────────

    def get_featured_offer_expected_price_batch(self, requests_list, **kwargs):
        """
        Batch request for Featured Offer Expected Price (FOEP).

        Args:
            requests_list: List of dicts with keys:
                - marketplaceId, asin, condition, (optional) subcondition
        """
        body = {"requests": requests_list}
        body.update(kwargs)
        return self.post("/batches/products/pricing/2022-05-01/offer/featuredOfferExpectedPrice", body)

    def get_competitive_summary_batch(self, requests_list, **kwargs):
        """
        Batch request for competitive summary.

        Args:
            requests_list: List of dicts with asin, marketplaceId, etc.
        """
        body = {"requests": requests_list}
        body.update(kwargs)
        return self.post("/batches/products/pricing/2022-05-01/items/competitiveSummary", body)
