"""
Amazon SP-API Python SDK v2.0
Modular, production-ready Amazon Selling Partner API client.
"""

from sp_api.client import SPAPIClient
from sp_api.auth import AuthManager
from sp_api.exceptions import SPAPIError, SPAPIAuthError, SPAPIThrottleError
from sp_api.orders import OrdersAPI
from sp_api.catalog import CatalogAPI
from sp_api.inventory import InventoryAPI
from sp_api.reports import ReportsAPI
from sp_api.finances import FinancesAPI
from sp_api.listings import ListingsAPI

__version__ = "2.0.0"
__all__ = [
    "SPAPIClient",
    "AuthManager",
    "SPAPIError",
    "SPAPIAuthError",
    "SPAPIThrottleError",
    "OrdersAPI",
    "CatalogAPI",
    "InventoryAPI",
    "ReportsAPI",
    "FinancesAPI",
    "ListingsAPI",
]
