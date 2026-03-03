"""
SP-API Sandbox Mode — mock responses for testing without live API calls.

Provides realistic response fixtures for all 13 API modules.

Usage:
    from sp_api.sandbox import SandboxSPAPI

    api = SandboxSPAPI(marketplace="US")
    orders = api.get_orders()  # Returns realistic mock data
    product = api.get_catalog_item("B09XYZ1234")  # Mock product
"""

import datetime
import uuid


def _make_order_id():
    return f"114-{uuid.uuid4().hex[:7].upper()}-{uuid.uuid4().hex[:7].upper()}"


def _make_asin():
    return f"B0{uuid.uuid4().hex[:8].upper()}"


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SandboxSPAPI:
    """
    Mock SP-API client for testing.

    Returns realistic fake data without making any API calls.
    All methods mirror the real SPAPIClient interface.
    """

    VERSION = "5.0.0-sandbox"

    def __init__(self, marketplace="US", **kwargs):
        self.marketplace = marketplace
        self.marketplace_id = "ATVPDKIKX0DER" if marketplace == "US" else marketplace
        self._request_count = 0

    # ── Orders ────────────────────────────────────────────

    def get_orders(self, created_after=None, order_statuses=None,
                   max_results=10, next_token=None, **kwargs):
        self._request_count += 1
        orders = []
        for i in range(min(max_results, 5)):
            orders.append({
                "AmazonOrderId": _make_order_id(),
                "OrderStatus": ["Shipped", "Unshipped", "Pending"][i % 3],
                "PurchaseDate": _now_iso(),
                "LastUpdateDate": _now_iso(),
                "OrderTotal": {"Amount": str(29.99 + i * 10), "CurrencyCode": "USD"},
                "MarketplaceId": self.marketplace_id,
                "FulfillmentChannel": "AFN" if i % 2 == 0 else "MFN",
                "SalesChannel": "Amazon.com",
                "NumberOfItemsShipped": i + 1,
                "NumberOfItemsUnshipped": 0,
                "IsPrime": i % 2 == 0,
            })
        return {
            "payload": {
                "Orders": orders,
                "NextToken": "mock_next_token" if max_results > 5 else None,
            }
        }

    def get_order(self, order_id):
        self._request_count += 1
        return {
            "payload": {
                "AmazonOrderId": order_id,
                "OrderStatus": "Shipped",
                "PurchaseDate": _now_iso(),
                "OrderTotal": {"Amount": "49.99", "CurrencyCode": "USD"},
                "FulfillmentChannel": "AFN",
                "IsPrime": True,
            }
        }

    def get_order_items(self, order_id, next_token=None):
        self._request_count += 1
        return {
            "payload": {
                "OrderItems": [
                    {
                        "ASIN": _make_asin(),
                        "SellerSKU": f"SKU-{uuid.uuid4().hex[:6].upper()}",
                        "OrderItemId": uuid.uuid4().hex[:12],
                        "Title": "Wireless Bluetooth Earbuds",
                        "QuantityOrdered": 1,
                        "ItemPrice": {"Amount": "29.99", "CurrencyCode": "USD"},
                        "ItemTax": {"Amount": "2.40", "CurrencyCode": "USD"},
                    },
                    {
                        "ASIN": _make_asin(),
                        "SellerSKU": f"SKU-{uuid.uuid4().hex[:6].upper()}",
                        "OrderItemId": uuid.uuid4().hex[:12],
                        "Title": "USB-C Charging Cable",
                        "QuantityOrdered": 2,
                        "ItemPrice": {"Amount": "9.99", "CurrencyCode": "USD"},
                        "ItemTax": {"Amount": "0.80", "CurrencyCode": "USD"},
                    },
                ],
                "AmazonOrderId": order_id,
            }
        }

    # ── Catalog ───────────────────────────────────────────

    def search_catalog(self, keywords, included_data=None, page_size=20, **kwargs):
        self._request_count += 1
        items = []
        for i in range(min(page_size, 5)):
            items.append({
                "asin": _make_asin(),
                "summaries": [{
                    "itemName": f"{keywords} - Product {i + 1}",
                    "brand": f"Brand{i + 1}",
                    "marketplaceId": self.marketplace_id,
                    "itemClassification": "BASE_PRODUCT",
                }],
                "images": [{
                    "images": [{
                        "link": f"https://images-na.ssl-images-amazon.com/images/I/{uuid.uuid4().hex[:10]}.jpg",
                        "variant": "MAIN",
                        "width": 500,
                        "height": 500,
                    }]
                }],
                "salesRanks": [{
                    "displayGroupRanks": [{
                        "title": "Electronics",
                        "rank": 1000 + i * 500,
                    }]
                }],
            })
        return {"items": items, "numberOfResults": len(items)}

    def get_catalog_item(self, asin, included_data=None, **kwargs):
        self._request_count += 1
        return {
            "asin": asin,
            "summaries": [{
                "itemName": f"Product {asin}",
                "brand": "TestBrand",
                "marketplaceId": self.marketplace_id,
            }],
            "images": [{
                "images": [{
                    "link": f"https://images-na.ssl-images-amazon.com/images/I/{asin}.jpg",
                    "variant": "MAIN",
                    "width": 1000,
                    "height": 1000,
                }]
            }],
        }

    # ── Pricing ───────────────────────────────────────────

    def get_competitive_pricing(self, asins=None, skus=None):
        self._request_count += 1
        results = []
        items = asins or skus or [_make_asin()]
        for item in (items if isinstance(items, list) else [items]):
            results.append({
                "Product": {
                    "Identifiers": {
                        "MarketplaceASIN": {"ASIN": item, "MarketplaceId": self.marketplace_id}
                    },
                    "CompetitivePricing": {
                        "CompetitivePrices": [{
                            "Price": {
                                "LandedPrice": {"Amount": "29.99", "CurrencyCode": "USD"},
                                "ListingPrice": {"Amount": "29.99", "CurrencyCode": "USD"},
                                "Shipping": {"Amount": "0.00", "CurrencyCode": "USD"},
                            },
                            "condition": "New",
                            "belongsToRequester": True,
                        }],
                        "NumberOfOfferListings": [
                            {"Count": 15, "condition": "new"},
                            {"Count": 3, "condition": "used"},
                        ],
                    },
                }
            })
        return {"payload": results}

    # ── Inventory ─────────────────────────────────────────

    def get_inventory_summaries(self, granularity_type="Marketplace",
                                next_token=None, seller_skus=None, **kwargs):
        self._request_count += 1
        return {
            "payload": {
                "inventorySummaries": [
                    {
                        "asin": _make_asin(),
                        "fnSku": f"FN{uuid.uuid4().hex[:8].upper()}",
                        "sellerSku": f"SKU-{uuid.uuid4().hex[:6].upper()}",
                        "productName": f"Test Product {i}",
                        "condition": "NewItem",
                        "inventoryDetails": {
                            "fulfillableQuantity": 50 + i * 10,
                            "inboundWorkingQuantity": 0,
                            "inboundShippedQuantity": 20,
                            "inboundReceivingQuantity": 0,
                            "reservedQuantity": {"totalReservedQuantity": 5},
                            "unfulfillableQuantity": {"totalUnfulfillableQuantity": 0},
                        },
                        "totalQuantity": 75 + i * 10,
                        "lastUpdatedTime": _now_iso(),
                    }
                    for i in range(3)
                ],
                "pagination": {},
            }
        }

    # ── Reports ───────────────────────────────────────────

    def create_report(self, report_type, marketplace_ids=None, **kwargs):
        self._request_count += 1
        return {"reportId": f"report-{uuid.uuid4().hex[:12]}"}

    def get_report(self, report_id):
        self._request_count += 1
        return {
            "reportId": report_id,
            "reportType": "GET_FLAT_FILE_OPEN_LISTINGS_DATA",
            "processingStatus": "DONE",
            "reportDocumentId": f"doc-{uuid.uuid4().hex[:12]}",
        }

    # ── Sellers ───────────────────────────────────────────

    def get_marketplace_participations(self):
        self._request_count += 1
        return {
            "payload": [
                {
                    "marketplace": {
                        "id": self.marketplace_id,
                        "name": "Amazon.com",
                        "countryCode": "US",
                        "defaultLanguageCode": "en_US",
                        "defaultCurrencyCode": "USD",
                    },
                    "participation": {
                        "isParticipating": True,
                        "hasSuspendedListings": False,
                    },
                }
            ]
        }

    def get_active_marketplaces(self):
        return self.get_marketplace_participations()

    # ── Finances ──────────────────────────────────────────

    def list_financial_events(self, **kwargs):
        self._request_count += 1
        return {
            "payload": {
                "FinancialEvents": {
                    "ShipmentEventList": [
                        {
                            "AmazonOrderId": _make_order_id(),
                            "PostedDate": _now_iso(),
                            "MarketplaceId": self.marketplace_id,
                            "ShipmentItemList": [
                                {
                                    "SellerSKU": "SKU-001",
                                    "QuantityShipped": 1,
                                    "ItemChargeList": [{
                                        "ChargeType": "Principal",
                                        "ChargeAmount": {"Amount": "29.99", "CurrencyCode": "USD"},
                                    }],
                                }
                            ],
                        }
                    ],
                }
            }
        }

    # ── Feeds ─────────────────────────────────────────────

    def create_feed_document(self, content_type="text/xml"):
        self._request_count += 1
        return {
            "feedDocumentId": f"feed-doc-{uuid.uuid4().hex[:12]}",
            "url": f"https://tortilla-prod-na.s3.amazonaws.com/{uuid.uuid4().hex}",
        }

    def create_feed(self, feed_type, input_feed_document_id, marketplace_ids=None):
        self._request_count += 1
        return {"feedId": f"feed-{uuid.uuid4().hex[:12]}"}

    # ── Stats ─────────────────────────────────────────────

    @property
    def stats(self):
        return {
            "total_requests": self._request_count,
            "mode": "sandbox",
            "marketplace": self.marketplace,
        }

    def get(self, path, params=None):
        self._request_count += 1
        return {"sandbox": True, "path": path}

    def post(self, path, body=None, params=None):
        self._request_count += 1
        return {"sandbox": True, "path": path}

    def __repr__(self):
        return f"SandboxSPAPI(marketplace={self.marketplace!r}, requests={self._request_count})"
