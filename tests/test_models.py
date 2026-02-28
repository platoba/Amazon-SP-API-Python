"""Tests for data models module."""

import datetime
import pytest
from sp_api.models import (
    Address,
    OrderItem,
    Order,
    Product,
    ProductImage,
    SalesRank,
    InventoryItem,
    CompetitivePrice,
    FinancialEvent,
    _parse_datetime,
    _parse_money,
    _parse_currency,
)


class TestParseHelpers:
    """Tests for parse helper functions."""

    def test_parse_datetime_iso(self):
        dt = _parse_datetime("2026-02-28T12:00:00Z")
        assert dt.year == 2026
        assert dt.month == 2
        assert dt.day == 28

    def test_parse_datetime_with_ms(self):
        dt = _parse_datetime("2026-02-28T12:00:00.123Z")
        assert dt is not None

    def test_parse_datetime_with_tz(self):
        dt = _parse_datetime("2026-02-28T12:00:00+08:00")
        assert dt is not None

    def test_parse_datetime_none(self):
        assert _parse_datetime(None) is None

    def test_parse_datetime_invalid(self):
        assert _parse_datetime("not-a-date") is None

    def test_parse_datetime_passthrough(self):
        now = datetime.datetime.now()
        assert _parse_datetime(now) == now

    def test_parse_money_float(self):
        assert _parse_money(29.99) == 29.99

    def test_parse_money_int(self):
        assert _parse_money(30) == 30.0

    def test_parse_money_dict(self):
        assert _parse_money({"Amount": "29.99"}) == 29.99

    def test_parse_money_dict_amount_key(self):
        assert _parse_money({"amount": "15.50"}) == 15.50

    def test_parse_money_none(self):
        assert _parse_money(None) is None

    def test_parse_currency_from_dict(self):
        assert _parse_currency({"CurrencyCode": "USD"}) == "USD"

    def test_parse_currency_lowercase(self):
        assert _parse_currency({"currencyCode": "EUR"}) == "EUR"

    def test_parse_currency_none(self):
        assert _parse_currency(None) is None

    def test_parse_currency_not_dict(self):
        assert _parse_currency("USD") is None


class TestAddress:
    """Tests for Address model."""

    def test_from_api(self):
        data = {
            "Name": "John Doe",
            "AddressLine1": "123 Main St",
            "City": "Seattle",
            "StateOrRegion": "WA",
            "PostalCode": "98101",
            "CountryCode": "US",
        }
        addr = Address.from_api(data)
        assert addr.name == "John Doe"
        assert addr.city == "Seattle"
        assert addr.country_code == "US"

    def test_from_api_none(self):
        assert Address.from_api(None) is None

    def test_to_dict_strips_none(self):
        addr = Address(name="Test", city="NYC")
        d = addr.to_dict()
        assert "name" in d
        assert "line2" not in d


class TestOrderItem:
    """Tests for OrderItem model."""

    def test_from_api(self):
        data = {
            "ASIN": "B09XYZ1234",
            "SellerSKU": "SKU-001",
            "OrderItemId": "item-001",
            "Title": "Test Product",
            "QuantityOrdered": 2,
            "ItemPrice": {"Amount": "29.99", "CurrencyCode": "USD"},
            "ItemTax": {"Amount": "2.40", "CurrencyCode": "USD"},
        }
        item = OrderItem.from_api(data)
        assert item.asin == "B09XYZ1234"
        assert item.quantity == 2
        assert item.item_price == 29.99
        assert item.currency == "USD"

    def test_from_api_minimal(self):
        item = OrderItem.from_api({})
        assert item.asin == ""
        assert item.quantity == 0


class TestOrder:
    """Tests for Order model."""

    def test_from_api(self):
        data = {
            "AmazonOrderId": "114-1234567-1234567",
            "OrderStatus": "Shipped",
            "PurchaseDate": "2026-02-28T12:00:00Z",
            "OrderTotal": {"Amount": "49.99", "CurrencyCode": "USD"},
            "FulfillmentChannel": "AFN",
            "IsPrime": True,
            "IsBusinessOrder": False,
            "NumberOfItemsShipped": 2,
        }
        order = Order.from_api(data)
        assert order.order_id == "114-1234567-1234567"
        assert order.status == "Shipped"
        assert order.total == 49.99
        assert order.is_fba is True
        assert order.is_prime is True
        assert order.is_fulfilled is True

    def test_from_list(self):
        data = [
            {"AmazonOrderId": "111", "OrderStatus": "Shipped"},
            {"AmazonOrderId": "222", "OrderStatus": "Pending"},
        ]
        orders = Order.from_list(data)
        assert len(orders) == 2
        assert orders[0].order_id == "111"
        assert orders[1].order_id == "222"

    def test_to_dict(self):
        order = Order(order_id="123", status="Shipped", total=29.99)
        d = order.to_dict()
        assert d["order_id"] == "123"
        assert "_raw" not in d

    def test_is_fulfilled(self):
        assert Order(status="Shipped").is_fulfilled is True
        assert Order(status="Complete").is_fulfilled is True
        assert Order(status="Pending").is_fulfilled is False

    def test_is_fba(self):
        assert Order(fulfillment_channel="AFN").is_fba is True
        assert Order(fulfillment_channel="MFN").is_fba is False


class TestProduct:
    """Tests for Product model."""

    def test_from_api(self):
        data = {
            "asin": "B09XYZ1234",
            "summaries": [{"itemName": "Test Product", "brand": "TestBrand"}],
            "images": [{"images": [
                {"link": "https://img.com/main.jpg", "variant": "MAIN", "width": 500, "height": 500},
                {"link": "https://img.com/pt01.jpg", "variant": "PT01"},
            ]}],
            "salesRanks": [{"displayGroupRanks": [
                {"title": "Electronics", "rank": 1500},
                {"title": "Headphones", "rank": 200},
            ]}],
        }
        product = Product.from_api(data)
        assert product.asin == "B09XYZ1234"
        assert product.title == "Test Product"
        assert product.brand == "TestBrand"
        assert len(product.images) == 2
        assert product.main_image == "https://img.com/main.jpg"
        assert product.best_rank == 200

    def test_from_search(self):
        resp = {"items": [
            {"asin": "A1", "summaries": [{"itemName": "P1"}]},
            {"asin": "A2", "summaries": [{"itemName": "P2"}]},
        ]}
        products = Product.from_search(resp)
        assert len(products) == 2

    def test_no_images(self):
        product = Product(asin="TEST")
        assert product.main_image is None

    def test_no_ranks(self):
        product = Product(asin="TEST")
        assert product.best_rank is None

    def test_to_dict(self):
        product = Product(asin="TEST", title="Test")
        d = product.to_dict()
        assert "_raw" not in d
        assert d["asin"] == "TEST"


class TestProductImage:
    """Tests for ProductImage model."""

    def test_from_api(self):
        img = ProductImage.from_api({
            "link": "https://img.com/test.jpg",
            "variant": "MAIN",
            "width": 1000,
            "height": 1000,
        })
        assert img.url == "https://img.com/test.jpg"
        assert img.variant == "MAIN"


class TestSalesRank:
    """Tests for SalesRank model."""

    def test_from_api(self):
        rank = SalesRank.from_api({"title": "Electronics", "rank": 500})
        assert rank.category == "Electronics"
        assert rank.rank == 500


class TestInventoryItem:
    """Tests for InventoryItem model."""

    def test_from_api(self):
        data = {
            "asin": "B09XYZ1234",
            "fnSku": "FN12345",
            "sellerSku": "SKU-001",
            "productName": "Test Product",
            "condition": "NewItem",
            "inventoryDetails": {
                "fulfillableQuantity": 50,
                "inboundShippedQuantity": 20,
                "reservedQuantity": {"totalReservedQuantity": 5},
            },
            "totalQuantity": 75,
            "lastUpdatedTime": "2026-02-28T12:00:00Z",
        }
        item = InventoryItem.from_api(data)
        assert item.asin == "B09XYZ1234"
        assert item.fulfillable_quantity == 50
        assert item.total_quantity == 75
        assert item.is_in_stock is True
        assert item.needs_restock is False

    def test_from_list(self):
        items = InventoryItem.from_list([
            {"asin": "A1", "totalQuantity": 10, "inventoryDetails": {"fulfillableQuantity": 5}},
            {"asin": "A2", "totalQuantity": 0, "inventoryDetails": {"fulfillableQuantity": 0}},
        ])
        assert len(items) == 2
        assert items[0].is_in_stock is True
        assert items[1].needs_restock is True

    def test_to_dict(self):
        item = InventoryItem(asin="TEST", total_quantity=50)
        d = item.to_dict()
        assert d["asin"] == "TEST"


class TestCompetitivePrice:
    """Tests for CompetitivePrice model."""

    def test_from_api(self):
        data = {
            "Product": {
                "Identifiers": {
                    "MarketplaceASIN": {"ASIN": "B09XYZ1234", "MarketplaceId": "ATVPDKIKX0DER"}
                },
                "CompetitivePricing": {
                    "CompetitivePrices": [{
                        "Price": {
                            "LandedPrice": {"Amount": "29.99", "CurrencyCode": "USD"},
                            "ListingPrice": {"Amount": "29.99", "CurrencyCode": "USD"},
                            "Shipping": {"Amount": "3.99", "CurrencyCode": "USD"},
                        },
                        "condition": "New",
                        "belongsToRequester": True,
                    }],
                    "NumberOfOfferListings": [
                        {"Count": 15, "condition": "new"},
                    ],
                },
            }
        }
        price = CompetitivePrice.from_api(data)
        assert price.asin == "B09XYZ1234"
        assert price.landed_price == 29.99
        assert price.shipping_price == 3.99
        assert price.margin_estimate == pytest.approx(26.0)
        assert price.number_of_offer_listings == 15

    def test_no_margin(self):
        price = CompetitivePrice(asin="TEST")
        assert price.margin_estimate is None


class TestFinancialEvent:
    """Tests for FinancialEvent model."""

    def test_from_api(self):
        data = {
            "PostedDate": "2026-02-28T12:00:00Z",
            "AmazonOrderId": "114-1234567-1234567",
            "MarketplaceId": "ATVPDKIKX0DER",
            "TotalAmount": {"Amount": "29.99", "CurrencyCode": "USD"},
        }
        event = FinancialEvent.from_api(data, event_type="Shipment")
        assert event.event_type == "Shipment"
        assert event.order_id == "114-1234567-1234567"
        assert event.amount == 29.99

    def test_to_dict(self):
        event = FinancialEvent(event_type="Test", amount=10.0)
        d = event.to_dict()
        assert d["event_type"] == "Test"
