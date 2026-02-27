# Amazon SP-API Python SDK

🛒 Lightweight Amazon Selling Partner API client for Python. Zero bloat, just works.

## Install

```bash
pip install amazon-sp-api-lite
```

Or clone:
```bash
git clone https://github.com/platoba/Amazon-SP-API-Python.git
pip install -e .
```

## Quick Start

```python
from sp_api import SPAPI

api = SPAPI(
    refresh_token="your_refresh_token",
    client_id="your_client_id",
    client_secret="your_client_secret",
    marketplace="US"  # US/UK/DE/JP/AU + 16 more
)

# Search products
results = api.search_catalog("wireless earbuds")

# Get product details
item = api.get_catalog_item("B09XYZ1234")

# Get orders (last 7 days)
orders = api.get_orders()

# Get competitive pricing
pricing = api.get_competitive_pricing(["B09XYZ1234", "B08ABC5678"])
```

## Supported APIs

| API | Methods | Description |
|-----|---------|-------------|
| Catalog Items | `search_catalog`, `get_catalog_item` | Product search & details |
| Orders | `get_orders`, `get_order`, `get_order_items` | Order management |
| Product Pricing | `get_competitive_pricing`, `get_item_offers` | Price monitoring |
| Reports | `create_report`, `get_report`, `get_report_document` | Business reports |
| FBA Inventory | `get_inventory_summaries` | FBA stock levels |
| Listings | `get_listings_item`, `put_listings_item` | Listing management |
| Feeds | `create_feed`, `get_feed` | Bulk operations |
| Notifications | `get_subscription`, `create_subscription` | Event webhooks |

## 20 Marketplaces

US, CA, MX, BR, UK, DE, FR, IT, ES, NL, SE, PL, TR, AE, SA, IN, EG, JP, AU, SG

## Features

- ✅ Auto token refresh
- ✅ Rate limit retry (429 handling)
- ✅ All SP-API regions (NA/EU/FE)
- ✅ Zero dependencies beyond `requests`
- ✅ Type hints ready

## License

MIT

## 🔗 Related

- [MultiAffiliateTGBot](https://github.com/platoba/MultiAffiliateTGBot) - 5-platform affiliate bot
- [AI-Listing-Writer](https://github.com/platoba/AI-Listing-Writer) - AI listing generator
