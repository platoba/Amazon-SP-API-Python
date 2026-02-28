"""
Product Fees API module — SP-API Product Fees v0.
Estimate Amazon referral and FBA fees for items.
"""

from sp_api.base import BaseAPI


class ProductFeesAPI(BaseAPI):
    """Amazon SP-API Product Fees endpoints."""

    def get_my_fees_estimate_for_sku(self, seller_sku, price, currency="USD",
                                     shipping=0, is_fba=True, **kwargs):
        """
        Get fee estimate for a seller SKU.

        Args:
            seller_sku: Seller's SKU identifier.
            price: Listing price amount.
            currency: Currency code (default: USD).
            shipping: Shipping price (default: 0).
            is_fba: Whether fulfilled by Amazon (default: True).

        Returns:
            Fee estimate response.
        """
        body = {
            "FeesEstimateRequest": {
                "MarketplaceId": self.marketplace_id,
                "IsAmazonFulfilled": is_fba,
                "PriceToEstimateFees": {
                    "ListingPrice": {
                        "CurrencyCode": currency,
                        "Amount": float(price),
                    },
                    "Shipping": {
                        "CurrencyCode": currency,
                        "Amount": float(shipping),
                    },
                },
                "Identifier": seller_sku,
            }
        }
        body["FeesEstimateRequest"].update(kwargs)
        return self.post(
            f"/products/fees/v0/listings/{seller_sku}/feesEstimate",
            body=body,
        )

    def get_my_fees_estimate_for_asin(self, asin, price, currency="USD",
                                      shipping=0, is_fba=True, **kwargs):
        """
        Get fee estimate for an ASIN.

        Args:
            asin: Amazon Standard Identification Number.
            price: Listing price amount.
            currency: Currency code (default: USD).
            shipping: Shipping price (default: 0).
            is_fba: Whether fulfilled by Amazon (default: True).

        Returns:
            Fee estimate response.
        """
        body = {
            "FeesEstimateRequest": {
                "MarketplaceId": self.marketplace_id,
                "IsAmazonFulfilled": is_fba,
                "PriceToEstimateFees": {
                    "ListingPrice": {
                        "CurrencyCode": currency,
                        "Amount": float(price),
                    },
                    "Shipping": {
                        "CurrencyCode": currency,
                        "Amount": float(shipping),
                    },
                },
                "Identifier": asin,
            }
        }
        body["FeesEstimateRequest"].update(kwargs)
        return self.post(
            f"/products/fees/v0/items/{asin}/feesEstimate",
            body=body,
        )

    def get_my_fees_estimates(self, items):
        """
        Batch fee estimates for multiple items.

        Args:
            items: List of dicts with keys:
                - asin or seller_sku
                - price (float)
                - currency (str, default "USD")
                - shipping (float, default 0)
                - is_fba (bool, default True)

        Returns:
            List of fee estimate responses.
        """
        results = []
        for item in items:
            asin = item.get("asin")
            sku = item.get("seller_sku")
            price = item["price"]
            currency = item.get("currency", "USD")
            shipping = item.get("shipping", 0)
            is_fba = item.get("is_fba", True)

            if asin:
                result = self.get_my_fees_estimate_for_asin(
                    asin, price, currency, shipping, is_fba
                )
            elif sku:
                result = self.get_my_fees_estimate_for_sku(
                    sku, price, currency, shipping, is_fba
                )
            else:
                raise ValueError("Each item must have 'asin' or 'seller_sku'")
            results.append(result)
        return results

    @staticmethod
    def extract_total_fees(fee_response):
        """
        Extract total estimated fees from a fee estimate response.

        Args:
            fee_response: Response from get_my_fees_estimate_for_*.

        Returns:
            dict with fee_amount, fee_currency, and fee_breakdown.
        """
        payload = fee_response.get("payload", fee_response)
        estimate = payload.get("FeesEstimateResult", {}).get("FeesEstimate", {})
        total = estimate.get("TotalFeesEstimate", {})
        detail = estimate.get("FeeDetailList", [])

        breakdown = {}
        for fee in detail:
            fee_type = fee.get("FeeType", "unknown")
            amount = fee.get("FeeAmount", {})
            breakdown[fee_type] = {
                "amount": float(amount.get("Amount", 0)),
                "currency": amount.get("CurrencyCode", "USD"),
            }

        return {
            "total_amount": float(total.get("Amount", 0)),
            "currency": total.get("CurrencyCode", "USD"),
            "breakdown": breakdown,
        }
