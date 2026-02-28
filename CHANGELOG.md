# Changelog

## [3.0.0] — 2026-02-28

### Added
- **Product Pricing API** — competitive pricing, item/listing offers, batch FOEP & competitive summary
- **Feeds API** — create/upload/submit feeds, high-level `submit_feed()` and `submit_and_wait()`
- **Fulfillment Outbound API** (MCF) — preview, create, track, cancel fulfillment orders; returns; features
- **Notifications API** integrated into client — subscriptions, destinations (SQS/EventBridge)
- **CLI tool** (`sp-api`) — command-line access to all API modules
- **pyproject.toml** with modern Python packaging
- **Docker + docker-compose** for containerized usage
- **GitHub Actions CI** (lint + test + coverage, Python 3.9/3.11/3.12 matrix, Docker build)
- **Makefile** (install/dev/test/lint/fmt/clean/build)
- **.env.example** template
- **LICENSE** (MIT)
- Request statistics tracking (`client.stats`)
- 11 new test files, 80+ test cases total

### Changed
- Client upgraded from v2.0 to v3.0 with 10 API module mixins
- Improved error counting and request tracking
- Enhanced test infrastructure with `MockSession.set_response()` helper

## [2.0.0] — 2026-02-27

### Added
- Orders, Catalog, Inventory, Reports, Finances, Listings modules
- OAuth2 token management with auto-refresh
- Token-bucket rate limiter with per-endpoint limits
- Retry logic with exponential backoff
- Support for 20 Amazon marketplaces (NA/EU/FE)

## [1.0.0] — 2026-02-27

- Initial release
