"""
Batch operations module.
Efficient bulk lookups and operations across multiple ASINs/SKUs.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class BatchOperations:
    """
    Batch helper for SP-API bulk operations.

    Runs multiple API calls in parallel with rate limiting,
    error handling, and progress tracking.

    Usage:
        from sp_api import SPAPI
        from sp_api.batch import BatchOperations

        api = SPAPI(...)
        batch = BatchOperations(api)

        # Bulk catalog lookup
        results = batch.bulk_catalog_lookup(["B09XYZ1234", "B08ABC5678"])

        # Bulk pricing
        pricing = batch.bulk_pricing(["B09XYZ1234", "B08ABC5678"])

        # Bulk fee estimates
        fees = batch.bulk_fee_estimates([
            {"asin": "B09XYZ1234", "price": 29.99},
            {"asin": "B08ABC5678", "price": 49.99},
        ])
    """

    def __init__(self, client, max_workers=5, delay_between_calls=0.2):
        """
        Args:
            client: SPAPIClient instance.
            max_workers: Maximum concurrent API calls.
            delay_between_calls: Delay (seconds) between calls to respect rate limits.
        """
        self.client = client
        self.max_workers = max_workers
        self.delay = delay_between_calls

    def _execute_batch(
        self,
        items: list,
        operation: Callable,
        label: str = "batch",
        on_error: str = "skip",
    ) -> List[Dict[str, Any]]:
        """
        Execute an operation on a batch of items with concurrency control.

        Args:
            items: List of items to process.
            operation: Callable that takes a single item and returns result.
            label: Label for logging.
            on_error: "skip" to continue on errors, "raise" to stop.

        Returns:
            List of {item, result, error} dicts.
        """
        results = []
        errors = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for i, item in enumerate(items):
                if i > 0 and self.delay:
                    time.sleep(self.delay)
                future = executor.submit(operation, item)
                futures[future] = item

            for future in as_completed(futures):
                item = futures[future]
                try:
                    result = future.result()
                    results.append({
                        "item": item,
                        "result": result,
                        "error": None,
                    })
                except Exception as e:
                    errors += 1
                    logger.warning("%s error for %s: %s", label, item, e)
                    if on_error == "raise":
                        raise
                    results.append({
                        "item": item,
                        "result": None,
                        "error": str(e),
                    })

        logger.info("%s complete: %d/%d success, %d errors",
                    label, len(results) - errors, len(items), errors)
        return results

    def bulk_catalog_lookup(
        self,
        asins: List[str],
        included_data: str = "summaries,images,salesRanks",
        on_error: str = "skip",
    ) -> List[Dict[str, Any]]:
        """
        Look up multiple ASINs in the catalog.

        Args:
            asins: List of ASINs.
            included_data: Data to include.
            on_error: Error handling ("skip" or "raise").

        Returns:
            List of {item, result, error} dicts.
        """
        def lookup(asin):
            return self.client.get_catalog_item(asin, included_data=included_data)

        return self._execute_batch(asins, lookup, "catalog_lookup", on_error)

    def bulk_pricing(
        self,
        asins: List[str],
        item_type: str = "Asin",
        on_error: str = "skip",
    ) -> List[Dict[str, Any]]:
        """
        Get competitive pricing for multiple ASINs.

        Args:
            asins: List of ASINs.
            item_type: Item type for pricing API.
            on_error: Error handling.

        Returns:
            List of {item, result, error} dicts.
        """
        def get_price(asin):
            return self.client.get_competitive_pricing(asins=[asin], item_type=item_type)

        return self._execute_batch(asins, get_price, "pricing", on_error)

    def bulk_fee_estimates(
        self,
        items: List[Dict[str, Any]],
        on_error: str = "skip",
    ) -> List[Dict[str, Any]]:
        """
        Get fee estimates for multiple items.

        Args:
            items: List of dicts with asin/seller_sku, price, currency, etc.
            on_error: Error handling.

        Returns:
            List of {item, result, error} dicts.
        """
        def estimate(item):
            asin = item.get("asin")
            sku = item.get("seller_sku")
            price = item["price"]
            currency = item.get("currency", "USD")
            shipping = item.get("shipping", 0)
            is_fba = item.get("is_fba", True)

            if asin:
                return self.client.get_my_fees_estimate_for_asin(
                    asin, price, currency, shipping, is_fba
                )
            elif sku:
                return self.client.get_my_fees_estimate_for_sku(
                    sku, price, currency, shipping, is_fba
                )
            raise ValueError("Need 'asin' or 'seller_sku'")

        return self._execute_batch(items, estimate, "fee_estimates", on_error)

    def bulk_inventory(
        self,
        skus: List[str],
        on_error: str = "skip",
    ) -> List[Dict[str, Any]]:
        """
        Get inventory for multiple SKUs.

        Args:
            skus: List of seller SKUs.
            on_error: Error handling.

        Returns:
            List of {item, result, error} dicts.
        """
        def get_inv(sku):
            return self.client.get_inventory_summary_by_sku(sku)

        return self._execute_batch(skus, get_inv, "inventory", on_error)

    def bulk_orders_items(
        self,
        order_ids: List[str],
        on_error: str = "skip",
    ) -> List[Dict[str, Any]]:
        """
        Get order items for multiple orders.

        Args:
            order_ids: List of Amazon order IDs.
            on_error: Error handling.

        Returns:
            List of {item, result, error} dicts.
        """
        def get_items(order_id):
            return self.client.get_order_items(order_id)

        return self._execute_batch(order_ids, get_items, "order_items", on_error)

    @staticmethod
    def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarize batch results.

        Args:
            results: List from any bulk_* method.

        Returns:
            Summary dict with counts and error details.
        """
        success = [r for r in results if r["error"] is None]
        failed = [r for r in results if r["error"] is not None]
        return {
            "total": len(results),
            "success": len(success),
            "failed": len(failed),
            "success_rate": f"{len(success) / len(results) * 100:.1f}%" if results else "0%",
            "errors": [{"item": r["item"], "error": r["error"]} for r in failed],
        }
