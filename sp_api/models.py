"""
SP-API Data Models — typed dataclasses for API responses.

Zero external dependencies (pure dataclasses).
Provides structured access, validation, and serialization.

Usage:
    from sp_api.models import Order, Product, InventoryItem

    # Parse from API response
    order = Order.from_api(api_response["payload"])
    print(order.order_id, order.status, order.total)

    # Serialize
    data = order.to_dict()
"""

import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


def _parse_datetime(value: Any) -> Optional[datetime.datetime]:
    """Parse ISO 8601 datetime string."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value
    try:
        # Handle various Amazon date formats
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
        ):
            try:
                return datetime.datetime.strptime(value, fmt)
            except ValueError:
                continue
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _parse_money(value: Any) -> Optional[float]:
    """Parse Amazon money amount dict or float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        amount = value.get("Amount") or value.get("amount") or value.get("Value")
        return float(amount) if amount is not None else None
    return None


def _parse_currency(value: Any) -> Optional[str]:
    """Extract currency code from money dict."""
    if isinstance(value, dict):
        return value.get("CurrencyCode") or value.get("currencyCode")
    return None


# ── Order Models ──────────────────────────────────────────

@dataclass
class Address:
    """Shipping/billing address."""
    name: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None
    line3: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: Optional[str] = None
    phone: Optional[str] = None

    @classmethod
    def from_api(cls, data: Optional[Dict]) -> Optional["Address"]:
        if not data:
            return None
        return cls(
            name=data.get("Name"),
            line1=data.get("AddressLine1"),
            line2=data.get("AddressLine2"),
            line3=data.get("AddressLine3"),
            city=data.get("City"),
            state=data.get("StateOrRegion"),
            postal_code=data.get("PostalCode"),
            country_code=data.get("CountryCode"),
            phone=data.get("Phone"),
        )

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class OrderItem:
    """Line item in an order."""
    asin: str = ""
    seller_sku: str = ""
    order_item_id: str = ""
    title: str = ""
    quantity: int = 0
    item_price: Optional[float] = None
    item_tax: Optional[float] = None
    currency: Optional[str] = None
    condition: Optional[str] = None
    is_gift: bool = False

    @classmethod
    def from_api(cls, data: Dict) -> "OrderItem":
        price_data = data.get("ItemPrice", {})
        tax_data = data.get("ItemTax", {})
        return cls(
            asin=data.get("ASIN", ""),
            seller_sku=data.get("SellerSKU", ""),
            order_item_id=data.get("OrderItemId", ""),
            title=data.get("Title", ""),
            quantity=int(data.get("QuantityOrdered", 0)),
            item_price=_parse_money(price_data),
            item_tax=_parse_money(tax_data),
            currency=_parse_currency(price_data),
            condition=data.get("ConditionId"),
            is_gift=data.get("IsGift", False),
        )

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Order:
    """Amazon order."""
    order_id: str = ""
    status: str = ""
    purchase_date: Optional[datetime.datetime] = None
    last_update: Optional[datetime.datetime] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    marketplace_id: str = ""
    fulfillment_channel: str = ""
    sales_channel: str = ""
    ship_service_level: str = ""
    shipping_address: Optional[Address] = None
    items: List[OrderItem] = field(default_factory=list)
    num_items_shipped: int = 0
    num_items_unshipped: int = 0
    payment_method: str = ""
    is_prime: bool = False
    is_business: bool = False
    order_type: str = ""
    buyer_email: Optional[str] = None
    _raw: Dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: Dict) -> "Order":
        total_data = data.get("OrderTotal", {})
        return cls(
            order_id=data.get("AmazonOrderId", ""),
            status=data.get("OrderStatus", ""),
            purchase_date=_parse_datetime(data.get("PurchaseDate")),
            last_update=_parse_datetime(data.get("LastUpdateDate")),
            total=_parse_money(total_data),
            currency=_parse_currency(total_data),
            marketplace_id=data.get("MarketplaceId", ""),
            fulfillment_channel=data.get("FulfillmentChannel", ""),
            sales_channel=data.get("SalesChannel", ""),
            ship_service_level=data.get("ShipServiceLevel", ""),
            shipping_address=Address.from_api(data.get("ShippingAddress")),
            num_items_shipped=int(data.get("NumberOfItemsShipped", 0)),
            num_items_unshipped=int(data.get("NumberOfItemsUnshipped", 0)),
            payment_method=data.get("PaymentMethod", ""),
            is_prime=data.get("IsPrime", False),
            is_business=data.get("IsBusinessOrder", False),
            order_type=data.get("OrderType", ""),
            buyer_email=data.get("BuyerInfo", {}).get("BuyerEmail"),
            _raw=data,
        )

    @classmethod
    def from_list(cls, data: List[Dict]) -> List["Order"]:
        return [cls.from_api(d) for d in data]

    def to_dict(self) -> Dict:
        result = asdict(self)
        result.pop("_raw", None)
        if self.purchase_date:
            result["purchase_date"] = self.purchase_date.isoformat()
        if self.last_update:
            result["last_update"] = self.last_update.isoformat()
        if self.shipping_address:
            result["shipping_address"] = self.shipping_address.to_dict()
        return result

    @property
    def is_fulfilled(self) -> bool:
        return self.status in ("Shipped", "Complete")

    @property
    def is_fba(self) -> bool:
        return self.fulfillment_channel == "AFN"


# ── Product Models ────────────────────────────────────────

@dataclass
class ProductImage:
    """Product image."""
    url: str = ""
    variant: str = ""
    width: int = 0
    height: int = 0

    @classmethod
    def from_api(cls, data: Dict) -> "ProductImage":
        return cls(
            url=data.get("link", ""),
            variant=data.get("variant", "MAIN"),
            width=data.get("width", 0),
            height=data.get("height", 0),
        )


@dataclass
class SalesRank:
    """Product sales rank in a category."""
    category: str = ""
    rank: int = 0
    link: str = ""

    @classmethod
    def from_api(cls, data: Dict) -> "SalesRank":
        return cls(
            category=data.get("title", ""),
            rank=int(data.get("rank", 0)),
            link=data.get("link", ""),
        )


@dataclass
class Product:
    """Amazon catalog product."""
    asin: str = ""
    title: str = ""
    brand: str = ""
    color: str = ""
    size: str = ""
    item_classification: str = ""
    marketplace_id: str = ""
    images: List[ProductImage] = field(default_factory=list)
    sales_ranks: List[SalesRank] = field(default_factory=list)
    _raw: Dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: Dict) -> "Product":
        summaries = data.get("summaries", [{}])
        summary = summaries[0] if summaries else {}

        images_data = data.get("images", [{}])
        image_list = images_data[0].get("images", []) if images_data else []

        ranks_data = data.get("salesRanks", [{}])
        rank_list = ranks_data[0].get("displayGroupRanks", []) if ranks_data else []

        return cls(
            asin=data.get("asin", ""),
            title=summary.get("itemName", ""),
            brand=summary.get("brand", ""),
            color=summary.get("color", ""),
            size=summary.get("size", ""),
            item_classification=summary.get("itemClassification", ""),
            marketplace_id=summary.get("marketplaceId", ""),
            images=[ProductImage.from_api(img) for img in image_list],
            sales_ranks=[SalesRank.from_api(r) for r in rank_list],
            _raw=data,
        )

    @classmethod
    def from_search(cls, response: Dict) -> List["Product"]:
        items = response.get("items", [])
        return [cls.from_api(item) for item in items]

    def to_dict(self) -> Dict:
        result = asdict(self)
        result.pop("_raw", None)
        return result

    @property
    def main_image(self) -> Optional[str]:
        for img in self.images:
            if img.variant == "MAIN":
                return img.url
        return self.images[0].url if self.images else None

    @property
    def best_rank(self) -> Optional[int]:
        if not self.sales_ranks:
            return None
        return min(r.rank for r in self.sales_ranks)


# ── Inventory Models ──────────────────────────────────────

@dataclass
class InventoryItem:
    """FBA inventory item."""
    asin: str = ""
    fn_sku: str = ""
    seller_sku: str = ""
    product_name: str = ""
    condition: str = ""
    fulfillable_quantity: int = 0
    inbound_working_quantity: int = 0
    inbound_shipped_quantity: int = 0
    inbound_receiving_quantity: int = 0
    reserved_quantity: int = 0
    researching_quantity: int = 0
    unfulfillable_quantity: int = 0
    total_quantity: int = 0
    last_updated: Optional[datetime.datetime] = None

    @classmethod
    def from_api(cls, data: Dict) -> "InventoryItem":
        details = data.get("inventoryDetails", {})
        reserved = details.get("reservedQuantity", {})
        research = details.get("researchingQuantity", {})
        unfulfill = details.get("unfulfillableQuantity", {})

        reserved_qty = sum(
            int(v) for v in reserved.values() if isinstance(v, (int, float))
        ) if isinstance(reserved, dict) else 0

        return cls(
            asin=data.get("asin", ""),
            fn_sku=data.get("fnSku", ""),
            seller_sku=data.get("sellerSku", ""),
            product_name=data.get("productName", ""),
            condition=data.get("condition", ""),
            fulfillable_quantity=int(details.get("fulfillableQuantity", 0)),
            inbound_working_quantity=int(details.get("inboundWorkingQuantity", 0)),
            inbound_shipped_quantity=int(details.get("inboundShippedQuantity", 0)),
            inbound_receiving_quantity=int(details.get("inboundReceivingQuantity", 0)),
            reserved_quantity=reserved_qty,
            total_quantity=int(data.get("totalQuantity", 0)),
            last_updated=_parse_datetime(data.get("lastUpdatedTime")),
        )

    @classmethod
    def from_list(cls, data: List[Dict]) -> List["InventoryItem"]:
        return [cls.from_api(d) for d in data]

    def to_dict(self) -> Dict:
        result = asdict(self)
        if self.last_updated:
            result["last_updated"] = self.last_updated.isoformat()
        return result

    @property
    def is_in_stock(self) -> bool:
        return self.fulfillable_quantity > 0

    @property
    def needs_restock(self) -> bool:
        return self.fulfillable_quantity <= 0 and self.total_quantity <= 0


# ── Pricing Models ────────────────────────────────────────

@dataclass
class CompetitivePrice:
    """Competitive pricing data for a product."""
    asin: str = ""
    marketplace_id: str = ""
    landed_price: Optional[float] = None
    listing_price: Optional[float] = None
    shipping_price: Optional[float] = None
    currency: Optional[str] = None
    condition: str = "New"
    belongs_to_requester: bool = False
    number_of_offer_listings: int = 0

    @classmethod
    def from_api(cls, data: Dict) -> "CompetitivePrice":
        product = data.get("Product", data)
        prices = product.get("CompetitivePricing", {})
        comp_prices = prices.get("CompetitivePrices", [])

        price_data = comp_prices[0] if comp_prices else {}
        price_info = price_data.get("Price", {})

        landed = price_info.get("LandedPrice", {})
        listing = price_info.get("ListingPrice", {})
        shipping = price_info.get("Shipping", {})

        offer_counts = prices.get("NumberOfOfferListings", [])
        total_offers = sum(
            int(o.get("Count", 0)) for o in offer_counts
        ) if isinstance(offer_counts, list) else 0

        return cls(
            asin=product.get("Identifiers", {}).get("MarketplaceASIN", {}).get("ASIN", ""),
            marketplace_id=product.get("Identifiers", {}).get("MarketplaceASIN", {}).get("MarketplaceId", ""),
            landed_price=_parse_money(landed),
            listing_price=_parse_money(listing),
            shipping_price=_parse_money(shipping),
            currency=_parse_currency(landed) or _parse_currency(listing),
            condition=price_data.get("condition", "New"),
            belongs_to_requester=price_data.get("belongsToRequester", False),
            number_of_offer_listings=total_offers,
        )

    def to_dict(self) -> Dict:
        return asdict(self)

    @property
    def margin_estimate(self) -> Optional[float]:
        """Rough margin estimate (landed - shipping)."""
        if self.landed_price and self.shipping_price:
            return self.landed_price - self.shipping_price
        return None


# ── Financial Models ──────────────────────────────────────

@dataclass
class FinancialEvent:
    """Financial event from SP-API Finances."""
    event_type: str = ""
    posted_date: Optional[datetime.datetime] = None
    order_id: str = ""
    marketplace_id: str = ""
    amount: Optional[float] = None
    currency: Optional[str] = None
    description: str = ""

    @classmethod
    def from_api(cls, data: Dict, event_type: str = "") -> "FinancialEvent":
        return cls(
            event_type=event_type,
            posted_date=_parse_datetime(data.get("PostedDate")),
            order_id=data.get("AmazonOrderId", ""),
            marketplace_id=data.get("MarketplaceId", ""),
            amount=_parse_money(data.get("TotalAmount")),
            currency=_parse_currency(data.get("TotalAmount")),
        )

    def to_dict(self) -> Dict:
        result = asdict(self)
        if self.posted_date:
            result["posted_date"] = self.posted_date.isoformat()
        return result
