# Amazon SP-API Python SDK

🛒 Lightweight Amazon Selling Partner API client for Python. 13 API modules, batch operations, response caching, CSV/JSON export, CLI tool — zero bloat.

[![CI](https://github.com/platoba/Amazon-SP-API-Python/actions/workflows/ci.yml/badge.svg)](https://github.com/platoba/Amazon-SP-API-Python/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Features

- **13 API modules**: Orders, Catalog, Pricing, Inventory, Reports, Feeds, Listings, Finances, Fulfillment/MCF, Notifications, Sellers, Product Fees, Shipping v2
- **Batch operations**: Concurrent bulk lookups for ASINs, pricing, fees, inventory
- **Response caching**: TTL-based cache with configurable per-endpoint expiry
- **Export utilities**: CSV, JSON, JSONL export with auto-flattening
- **20 marketplaces**: US, UK, DE, JP, AU + 15 more
- **Rate limiting**: Automatic rate limit handling with exponential backoff
- **CLI tool**: Full-featured command-line interface

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
    marketplace="US"  # US/UK/DE/JP/AU + 15 more
)

# Search products
results = api.search_catalog("wireless earbuds")

# Get orders (last 7 days)
orders = api.get_orders()

# Get competitive pricing
pricing = api.get_competitive_pricing(asins=["B09XYZ1234"])

# Estimate fees
fees = api.get_my_fees_estimate_for_asin("B09XYZ1234", price=29.99)

# Get seller marketplace participations
marketplaces = api.get_active_marketplaces()

# Get shipping rates
rates = api.get_rates(
    ship_from={"addressLine1": "123 Main St", "city": "Seattle", ...},
    ship_to={"addressLine1": "456 Oak Ave", "city": "Portland", ...},
    packages=[{"dimensions": {...}, "weight": {...}}],
)
```

## Batch Operations

```python
from sp_api import SPAPI, BatchOperations

api = SPAPI(...)
batch = BatchOperations(api, max_workers=5)

# Bulk catalog lookup (concurrent)
results = batch.bulk_catalog_lookup(["B09XYZ1234", "B08ABC5678", ...])

# Bulk pricing
pricing = batch.bulk_pricing(["B09XYZ1234", "B08ABC5678"])

# Bulk fee estimates
fees = batch.bulk_fee_estimates([
    {"asin": "B09XYZ1234", "price": 29.99},
    {"asin": "B08ABC5678", "price": 49.99},
])

# Summary
print(BatchOperations.summarize(results))
# → {'total': 2, 'success': 2, 'failed': 0, 'success_rate': '100.0%'}
```

## Response Caching

```python
from sp_api import ResponseCache

cache = ResponseCache(default_ttl=300)  # 5 min default

@cache.cached(ttl=3600, key_prefix="catalog_")
def get_product(asin):
    return api.get_catalog_item(asin)

# First call → API request
product = get_product("B09XYZ1234")

# Second call → cache hit (no API call)
product = get_product("B09XYZ1234")

# Stats
print(cache.stats)
# → {'total_entries': 1, 'total_hits': 1, 'hit_rate': '50.0%', ...}
```

## Export Data

```python
from sp_api import Exporter

exporter = Exporter(output_dir="./exports")

# Export orders to CSV (auto-flattens nested dicts)
orders = api.get_orders()
exporter.to_csv(orders, "orders.csv")

# Export to JSON
exporter.to_json(orders, "orders.json")

# Export to JSONL (streaming-friendly)
exporter.to_jsonl(orders, "orders.jsonl")

# Auto-timestamped export
exporter.export(orders, prefix="orders", fmt="csv")
# → exports/orders_20260228_120000.csv
```

## API Modules

| Module | Endpoints | Description |
|--------|-----------|-------------|
| **Orders** | 6 | List, get, items, address, buyer info, regulated info |
| **Catalog** | 3 | Search, get item, search by identifier |
| **Pricing** | 4 | Competitive pricing, offers, batch pricing |
| **Inventory** | 3 | FBA summaries, by-SKU, paginated iterator |
| **Reports** | 4 | Create, poll, download, list |
| **Feeds** | 4 | Submit, upload, poll, list |
| **Listings** | 3 | Create, update, delete listings |
| **Finances** | 3 | Events, groups, by-order |
| **Fulfillment** | 6 | MCF preview, create, track, cancel, returns |
| **Notifications** | 4 | Subscribe, create destination, list, delete |
| **Sellers** | 3 | Marketplace participations, account info, active marketplaces |
| **Product Fees** | 4 | Fee estimate by ASIN/SKU, batch estimates, fee extraction |
| **Shipping** | 6 | Rates, purchase, track, cancel, access points |

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

# SDK info
sp-api info
```

## Supported Marketplaces

| Region | Marketplaces |
|--------|-------------|
| **North America** | US, CA, MX, BR |
| **Europe** | UK, DE, FR, IT, ES, NL, SE, PL, TR, AE, SA, IN, EG |
| **Far East** | JP, AU, SG |

## Development

```bash
# Setup
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

## Docker

```bash
# Build
docker build -t sp-api-python .

# Run CLI
docker run --env-file .env sp-api-python catalog search "wireless earbuds"

# Docker Compose
docker compose run sp-api catalog search "wireless earbuds"
```

## License

MIT

## ASIN Monitoring

Track price, inventory, rating, and buybox changes for multiple ASINs:

```python
from sp_api import SPAPI
from sp_api.asin_monitor import ASINMonitor

api = SPAPI(...)
monitor = ASINMonitor(api, storage_path="./monitor_data")

# Capture current snapshot
asins = ["B08N5WRWNW", "B07XJ8C8F5"]
snapshots = monitor.capture_snapshot(asins)
monitor.save_snapshots(snapshots)

# Detect changes (last 24h)
changes = monitor.detect_changes("B08N5WRWNW", threshold_pct=5.0)
if changes["changes"]:
    for change in changes["changes"]:
        print(f"{change['type']}: {change}")

# Continuous monitoring
monitor.monitor_loop(asins, interval_minutes=60, duration_hours=24)
```

### CLI

```bash
# Start monitoring (60min interval)
sp-api monitor start B08N5WRWNW B07XJ8C8F5 --interval 60

# View history
sp-api monitor history B08N5WRWNW --days 7

# Detect changes
sp-api monitor changes B08N5WRWNW --threshold 5.0
```

**Use cases:**
- Competitor price tracking
- Inventory availability alerts
- Rating/review monitoring
- Buybox winner tracking
- Repricing automation triggers
