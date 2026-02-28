# Changelog

## [5.1.0] - 2026-02-28

### Added
- **Retry Engine** (`sp_api/retry.py`) — 5 backoff strategies (exponential/linear/constant/fibonacci/decorrelated jitter), circuit breaker pattern (closed→open→half-open recovery), per-endpoint retry budgets via `EndpointRetryManager`, retry history tracking & statistics
- **Input Validators** (`sp_api/validators.py`) — ASIN validation (strict B0/ISBN-10 mode), bulk ASIN dedup, SKU validation (40-char limit), EAN-13/UPC-A barcode validation with check digit verification, marketplace code validation (20+ markets, GB→UK alias), ISO date & date range validation, Amazon Order ID format validation, `@validated()` decorator for auto-validation on function params
- **Request Metrics** (`sp_api/metrics.py`) — per-endpoint & global request tracking (latency P50/P95/P99, throughput RPS, error/throttle/cache-hit rates), context-managed request tracking, text/JSON/CSV report export, thread-safe collector with configurable history window
- 3 new test files: `test_retry.py` (35 tests), `test_validators.py` (63 tests), `test_metrics.py` (34 tests)

### Fixed
- **Pagination bug**: `_find_items()` now handles plain list responses without crashing on `.get()` call
- **Async test fix**: `test_request_without_context_raises` converted to proper async test (was using deprecated `get_event_loop()`)

### Stats
- Tests: 438 → 570 (+132), all passing
- New code: ~1,200 lines across 3 modules + 3 test files

## [4.0.0] - 2026-02-28

### Added
- **Sellers API module** (`sp_api/sellers.py`) — marketplace participations, account info, active marketplace filtering
- **Product Fees API module** (`sp_api/product_fees.py`) — fee estimates by ASIN/SKU, batch estimates, fee extraction helper
- **Shipping API v2 module** (`sp_api/shipping.py`) — rates, purchase labels, tracking, cancel, access points
- **Response Cache** (`sp_api/cache.py`) — TTL-based thread-safe cache with decorator support, per-endpoint TTL recommendations, eviction, stats
- **Batch Operations** (`sp_api/batch.py`) — concurrent bulk lookups for catalog/pricing/fees/inventory/orders with ThreadPoolExecutor, error handling, summarization
- **Export Utilities** (`sp_api/export.py`) — CSV/JSON/JSONL export with auto-flattening, timestamped filenames, string output mode
- 6 new test files with 60+ tests (sellers, product_fees, shipping, cache, batch, export)
- Python 3.13 support in CI matrix

### Changed
- Client now composes 13 API modules (was 10)
- Updated README with batch/cache/export docs, full API module table
- Version bumped to 4.0.0

## [3.0.0] - 2026-02-27

### Added
- 10 API modules: Orders, Catalog, Inventory, Reports, Finances, Listings, Pricing, Feeds, Fulfillment/MCF, Notifications
- CLI tool (`sp-api`) with subcommands
- Rate limiter with per-endpoint tracking
- OAuth2 auth manager with auto-refresh
- 14 test files
- Dockerfile, docker-compose.yml, Makefile
- GitHub Actions CI (lint + test + Docker build)
- 20 marketplace support

## [2.0.0] - 2026-02-27

### Added
- Initial release with core SP-API client
- Orders and Catalog modules
