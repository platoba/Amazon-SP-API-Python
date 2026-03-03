"""Tests for sandbox module."""

from sp_api.sandbox import SandboxSPAPI


class TestSandboxSPAPI:
    """Tests for SandboxSPAPI mock client."""

    def setup_method(self):
        self.api = SandboxSPAPI(marketplace="US")

    def test_init(self):
        assert self.api.marketplace == "US"
        assert self.api.marketplace_id == "ATVPDKIKX0DER"

    def test_init_other_marketplace(self):
        api = SandboxSPAPI(marketplace="DE")
        assert api.marketplace == "DE"

    def test_get_orders(self):
        result = self.api.get_orders()
        assert "payload" in result
        orders = result["payload"]["Orders"]
        assert len(orders) == 5
        assert "AmazonOrderId" in orders[0]
        assert "OrderStatus" in orders[0]
        assert "OrderTotal" in orders[0]

    def test_get_orders_max_results(self):
        result = self.api.get_orders(max_results=2)
        orders = result["payload"]["Orders"]
        assert len(orders) == 2

    def test_get_order(self):
        result = self.api.get_order("114-TEST-123")
        assert result["payload"]["AmazonOrderId"] == "114-TEST-123"
        assert result["payload"]["OrderStatus"] == "Shipped"

    def test_get_order_items(self):
        result = self.api.get_order_items("114-TEST-123")
        items = result["payload"]["OrderItems"]
        assert len(items) == 2
        assert "ASIN" in items[0]
        assert "Title" in items[0]

    def test_search_catalog(self):
        result = self.api.search_catalog("wireless earbuds")
        assert "items" in result
        items = result["items"]
        assert len(items) == 5
        assert "wireless earbuds" in items[0]["summaries"][0]["itemName"]

    def test_search_catalog_page_size(self):
        result = self.api.search_catalog("test", page_size=3)
        assert len(result["items"]) == 3

    def test_get_catalog_item(self):
        result = self.api.get_catalog_item("B09XYZ1234")
        assert result["asin"] == "B09XYZ1234"
        assert "summaries" in result
        assert "images" in result

    def test_get_competitive_pricing(self):
        result = self.api.get_competitive_pricing(asins=["B09XYZ1234"])
        assert "payload" in result
        assert len(result["payload"]) == 1

    def test_get_inventory_summaries(self):
        result = self.api.get_inventory_summaries()
        summaries = result["payload"]["inventorySummaries"]
        assert len(summaries) == 3
        assert "asin" in summaries[0]
        assert "totalQuantity" in summaries[0]

    def test_create_report(self):
        result = self.api.create_report("GET_FLAT_FILE_OPEN_LISTINGS_DATA")
        assert "reportId" in result
        assert result["reportId"].startswith("report-")

    def test_get_report(self):
        result = self.api.get_report("report-test-123")
        assert result["reportId"] == "report-test-123"
        assert result["processingStatus"] == "DONE"

    def test_get_marketplace_participations(self):
        result = self.api.get_marketplace_participations()
        assert "payload" in result
        assert len(result["payload"]) == 1

    def test_list_financial_events(self):
        result = self.api.list_financial_events()
        assert "payload" in result
        events = result["payload"]["FinancialEvents"]
        assert "ShipmentEventList" in events

    def test_create_feed_document(self):
        result = self.api.create_feed_document()
        assert "feedDocumentId" in result
        assert "url" in result

    def test_create_feed(self):
        result = self.api.create_feed("POST_PRODUCT_DATA", "doc-123")
        assert "feedId" in result

    def test_stats(self):
        self.api.get_orders()
        self.api.search_catalog("test")
        stats = self.api.stats
        assert stats["total_requests"] == 2
        assert stats["mode"] == "sandbox"
        assert stats["marketplace"] == "US"

    def test_get(self):
        result = self.api.get("/test/path")
        assert result["sandbox"] is True
        assert result["path"] == "/test/path"

    def test_post(self):
        result = self.api.post("/test/path", body={"key": "val"})
        assert result["sandbox"] is True

    def test_repr(self):
        r = repr(self.api)
        assert "SandboxSPAPI" in r
        assert "US" in r

    def test_get_active_marketplaces(self):
        result = self.api.get_active_marketplaces()
        assert "payload" in result

    def test_request_count_increments(self):
        assert self.api._request_count == 0
        self.api.get_orders()
        assert self.api._request_count == 1
        self.api.search_catalog("test")
        assert self.api._request_count == 2
        self.api.get_order("123")
        assert self.api._request_count == 3
