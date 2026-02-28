"""
Amazon SP-API Python SDK — Lightweight & Complete.
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

__version__ = "3.0.0"

__all__ = [
    "SPAPI",
    "SPAPIClient",
    "SPAPIError",
    "SPAPIAuthError",
    "SPAPIThrottleError",
    "SPAPINotFoundError",
    "SPAPIValidationError",
    "MARKETPLACES",
    "ENDPOINTS",
    "REGION_MAP",
    "RateLimiter",
]
