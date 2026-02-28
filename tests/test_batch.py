"""Tests for Batch Operations module."""

import pytest
from unittest.mock import MagicMock, patch
from sp_api.batch import BatchOperations


class TestBatchOperations:
    """Tests for BatchOperations."""

    def setup_method(self):
        self.client = MagicMock()
        self.batch = BatchOperations(self.client, max_workers=2, delay_between_calls=0)

    def test_bulk_catalog_lookup(self):
        """Test bulk catalog lookup."""
        self.client.get_catalog_item.return_value = {"payload": {"asin": "B001"}}
        results = self.batch.bulk_catalog_lookup(["B001", "B002"])
        assert len(results) == 2
        assert results[0]["error"] is None or results[1]["error"] is None

    def test_bulk_pricing(self):
        """Test bulk pricing lookup."""
        self.client.get_competitive_pricing.return_value = {"payload": {"price": 29.99}}
        results = self.batch.bulk_pricing(["B001", "B002"])
        assert len(results) == 2

    def test_bulk_fee_estimates(self):
        """Test bulk fee estimates."""
        self.client.get_my_fees_estimate_for_asin.return_value = {"payload": {"fee": 3.0}}
        items = [
            {"asin": "B001", "price": 29.99},
            {"asin": "B002", "price": 49.99},
        ]
        results = self.batch.bulk_fee_estimates(items)
        assert len(results) == 2

    def test_bulk_fee_estimates_with_sku(self):
        """Test bulk fee estimates with seller SKU."""
        self.client.get_my_fees_estimate_for_sku.return_value = {"payload": {"fee": 2.5}}
        items = [{"seller_sku": "SKU-001", "price": 19.99}]
        results = self.batch.bulk_fee_estimates(items)
        assert len(results) == 1
        assert results[0]["error"] is None

    def test_bulk_fee_estimates_missing_id(self):
        """Test batch fee error when missing identifier."""
        items = [{"price": 29.99}]
        results = self.batch.bulk_fee_estimates(items, on_error="skip")
        assert len(results) == 1
        assert results[0]["error"] is not None

    def test_bulk_inventory(self):
        """Test bulk inventory lookup."""
        self.client.get_inventory_summary_by_sku.return_value = {"payload": {"qty": 10}}
        results = self.batch.bulk_inventory(["SKU-001", "SKU-002"])
        assert len(results) == 2

    def test_bulk_orders_items(self):
        """Test bulk order items lookup."""
        self.client.get_order_items.return_value = {"payload": {"items": []}}
        results = self.batch.bulk_orders_items(["ORD-001", "ORD-002"])
        assert len(results) == 2

    def test_error_handling_skip(self):
        """Test error handling in skip mode."""
        self.client.get_catalog_item.side_effect = [
            {"payload": {"asin": "B001"}},
            Exception("API Error"),
        ]
        results = self.batch.bulk_catalog_lookup(["B001", "B002"], on_error="skip")
        assert len(results) == 2
        errors = [r for r in results if r["error"] is not None]
        assert len(errors) == 1

    def test_error_handling_raise(self):
        """Test error handling in raise mode."""
        self.client.get_catalog_item.side_effect = Exception("API Error")
        with pytest.raises(Exception, match="API Error"):
            self.batch.bulk_catalog_lookup(["B001"], on_error="raise")

    def test_summarize(self):
        """Test batch results summarization."""
        results = [
            {"item": "B001", "result": {"data": 1}, "error": None},
            {"item": "B002", "result": {"data": 2}, "error": None},
            {"item": "B003", "result": None, "error": "Not found"},
        ]
        summary = BatchOperations.summarize(results)
        assert summary["total"] == 3
        assert summary["success"] == 2
        assert summary["failed"] == 1
        assert "66.7%" in summary["success_rate"]
        assert len(summary["errors"]) == 1

    def test_summarize_empty(self):
        """Test summarize with empty results."""
        summary = BatchOperations.summarize([])
        assert summary["total"] == 0
        assert summary["success_rate"] == "0%"

    def test_summarize_all_success(self):
        """Test summarize with all successful results."""
        results = [
            {"item": "B001", "result": {}, "error": None},
            {"item": "B002", "result": {}, "error": None},
        ]
        summary = BatchOperations.summarize(results)
        assert summary["success_rate"] == "100.0%"
        assert summary["failed"] == 0
