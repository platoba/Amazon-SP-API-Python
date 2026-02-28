# Amazon SP-API Python SDK

🛒 Lightweight Amazon Selling Partner API client for Python. 10 API modules, CLI tool, zero bloat.

[![CI](https://github.com/platoba/Amazon-SP-API-Python/actions/workflows/ci.yml/badge.svg)](https://github.com/platoba/Amazon-SP-API-Python/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Install

```bash
pip install amazon-sp-api-lite
```

Or from source:
```bash
git clone https://github.com/platoba/Amazon-SP-API-Python.git
cd Amazon-SP-API-Python
pip install -e ".[dev]"
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

# Get orders (last 7 days)
orders = api.get_orders()

# Get competitive pricing
pricing = api.get_competitive_pricing(asins=["B09XYZ1234"])

# Submit a feed
api.submit_feed("pricing", "<xml>...</xml>")

# Create MCF fulfillment order
api.create_fulfillment_order(
    seller_fulfillment_order_id="FO-001",
    displayable_order_id="ORD-001",
    displayable_order_date="2026-02-28T00:00:00Z",
    displayable_order_comment="Thank you!",
    shipping_speed_category="Standard",
    destination_address={...},
    items=[{"sellerSku": "SKU-001", "quantity": 1, ...}],
)

# Request stats
print(api.stats)
# → {'total_requests': 4, 'total_errors': 0, 'marketplace': 'US', ...}
```

## CLI

```bash
# Set credentials via environment
export SP_REFRESH_TOKEN=your_token
export SP_CLIENT_ID=your_id
export SP_CLIENT_SECRET=your_secret

# Search catalog
sp-api catalog search "wireless earbuds"

# List orders
sp-api orders list --after 2026-02-01T00:00:00Z

# Get competitive pricing
sp-api pricing competitive B09XYZ1234,B08ABC5678

# List reports
sp-api reports list --limit 5

# Show supported APIs & marketplaces
sp-api info
```

## Supported APIs

| API | Module | Key Methods |
|-----|--------|-------------|
| **Catalog Items** | `CatalogAPI` | `search_catalog`, `get_catalog_item`, `search_catalog_by_identifier` |
| **Orders** | `OrdersAPI` | `get_orders`, `get_order`, `get_order_items`, `get_order_address` |
| **Product Pricing** | `PricingAPI` | `get_competitive_pricing`, `get_item_offers`, `get_listing_offers`, `get_pricing` |
| **Reports** | `ReportsAPI` | `create_report`, `get_report`, `create_and_wait`, `get_report_document` |
| **Feeds** | `FeedsAPI` | `submit_feed`, `submit_json_feed`, `submit_and_wait`, `get_feed` |
| **FBA Inventory** | `InventoryAPI` | `get_inventory_summaries`, `get_all_inventory` |
| **Finances** | `FinancesAPI` | `list_financial_events`, `list_financial_event_groups` |
| **Listings Items** | `ListingsAPI` | `get_listings_item`, `put_listings_item`, `patch_listings_item` |
| **Fulfillment (MCF)** | `FulfillmentAPI` | `get_fulfillment_preview`, `create_fulfillment_order`, `get_package_tracking_details` |
| **Notifications** | `NotificationsAPI` | `create_subscription`, `get_destinations`, `create_destination` |

## Marketplaces

20 supported marketplaces across 3 regions:

| Region | Marketplaces |
|--------|-------------|
| **North America** | US, CA, MX, BR |
| **Europe** | UK, DE, FR, IT, ES, NL, SE, PL, TR, AE, SA, IN, EG |
| **Far East** | JP, AU, SG |

## Features

- 🔐 **OAuth2 auto-refresh** — Thread-safe token management with configurable buffer
- ⚡ **Rate limiting** — Token-bucket algorithm with per-endpoint SP-API limits
- 🔄 **Auto-retry** — Exponential backoff for transient errors and 429s
- 📊 **Request stats** — Built-in request/error counting
- 🛠️ **CLI tool** — Command-line access to all API modules
- 📦 **Report shortcuts** — Use `"inventory"` instead of `"GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA"`
- 📤 **Feed helpers** — `submit_feed()` handles document creation + upload + submission
- 🐳 **Docker ready** — Dockerfile + docker-compose included

## Docker

```bash
# Build
docker build -t sp-api .

# Run
docker run --env-file .env sp-api catalog search "wireless earbuds"

# Via compose
docker compose run sp-api orders list
```

## Development

```bash
# Install dev dependencies
make dev

# Run tests
make test

# Run tests with coverage
make test-cov

# Lint
make lint

# Format
make fmt
```

## Project Structure

```
Amazon-SP-API-Python/
├── sp_api/
│   ├── __init__.py        # Package exports
│   ├── client.py          # SPAPIClient (main entry)
│   ├── auth.py            # OAuth2 token manager
│   ├── rate_limiter.py    # Token-bucket rate limiter
│   ├── marketplaces.py    # Marketplace constants
│   ├── exceptions.py      # Error classes
│   ├── base.py            # BaseAPI mixin
│   ├── cli.py             # CLI tool
│   ├── orders.py          # Orders API
│   ├── catalog.py         # Catalog Items API
│   ├── pricing.py         # Product Pricing API
│   ├── reports.py         # Reports API
│   ├── feeds.py           # Feeds API
│   ├── inventory.py       # FBA Inventory API
│   ├── finances.py        # Finances API
│   ├── listings.py        # Listings Items API
│   ├── fulfillment.py     # Fulfillment Outbound (MCF)
│   └── notifications.py   # Notifications API
├── tests/                 # 80+ test cases
├── pyproject.toml
├── setup.py
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── CHANGELOG.md
└── LICENSE
```

## License

MIT — see [LICENSE](LICENSE).
