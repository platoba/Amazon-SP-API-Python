"""
Amazon SP-API Python SDK — Lightweight & Complete.

v5.1 adds: retry engine (circuit breaker + backoff strategies), validators
(ASIN/SKU/EAN/UPC/marketplace/dates), request metrics (latency/throughput/reports).
"""

from sp_api.client import SPAPIClient as SPAPI
from sp_api.client import SPAPIClient
from sp_api.exceptions import (
    SPAPIError,
    SPAPIAuthError,
    SPAPIThrottleError,
    SPAPINotFoundError,
    SPAPIValidationError,
)
from sp_api.marketplaces import MARKETPLACES, ENDPOINTS, REGION_MAP
from sp_api.rate_limiter import RateLimiter
from sp_api.cache import ResponseCache
from sp_api.batch import BatchOperations
from sp_api.export import Exporter
from sp_api.pagination import Paginator, AsyncPaginator, paginate, async_paginate
from sp_api.models import Order, Product, InventoryItem, CompetitivePrice, FinancialEvent
from sp_api.middleware import (
    MiddlewarePipeline,
    LoggingMiddleware,
    CircuitBreaker,
    MetricsMiddleware,
    RetryBudgetMiddleware,
)
from sp_api.webhooks import NotificationHandler, Notification
from sp_api.sandbox import SandboxSPAPI
from sp_api.retry import RetryPolicy, CircuitBreaker as RetryCircuitBreaker, EndpointRetryManager, BackoffStrategy
from sp_api.validators import (
    validate_asin, validate_asins, validate_sku, validate_ean, validate_upc,
    validate_marketplace, validate_date, validate_date_range, validate_order_id, validated,
)
from sp_api.metrics import MetricsCollector, MetricsReport

__version__ = "5.1.0"

__all__ = [
    # Core client
    "SPAPI",
    "SPAPIClient",
    # Async
    "AsyncSPAPI",
    # Exceptions
    "SPAPIError",
    "SPAPIAuthError",
    "SPAPIThrottleError",
    "SPAPINotFoundError",
    "SPAPIValidationError",
    # Marketplaces
    "MARKETPLACES",
    "ENDPOINTS",
    "REGION_MAP",
    # Utilities
    "RateLimiter",
    "ResponseCache",
    "BatchOperations",
    "Exporter",
    # Pagination
    "Paginator",
    "AsyncPaginator",
    "paginate",
    "async_paginate",
    # Models
    "Order",
    "Product",
    "InventoryItem",
    "CompetitivePrice",
    "FinancialEvent",
    # Middleware
    "MiddlewarePipeline",
    "LoggingMiddleware",
    "CircuitBreaker",
    "MetricsMiddleware",
    "RetryBudgetMiddleware",
    # Retry Engine
    "RetryPolicy",
    "RetryCircuitBreaker",
    "EndpointRetryManager",
    "BackoffStrategy",
    # Validators
    "validate_asin",
    "validate_asins",
    "validate_sku",
    "validate_ean",
    "validate_upc",
    "validate_marketplace",
    "validate_date",
    "validate_date_range",
    "validate_order_id",
    "validated",
    # Metrics
    "MetricsCollector",
    "MetricsReport",
    # Webhooks
    "NotificationHandler",
    "Notification",
    # Sandbox
    "SandboxSPAPI",
]


def _lazy_import_async():
    """Lazy import AsyncSPAPI to avoid requiring aiohttp at import time."""
    from sp_api.async_client import AsyncSPAPI
    return AsyncSPAPI


def __getattr__(name):
    if name == "AsyncSPAPI":
        return _lazy_import_async()
    raise AttributeError(f"module 'sp_api' has no attribute {name}")
